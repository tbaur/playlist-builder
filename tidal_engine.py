# Copyright 2025 tbaur
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Tidal API integration engine.
"""
import json
import logging
import os
import re
import sys
import time
from typing import Dict, Optional, Any, List

import tidalapi

from constants import (
    BOLD, GREEN, YELLOW, CYAN, RED, BLUE, MAGENTA, RESET, DIM,
    MIN_MATCH_SCORE, HI_RES_QUALITY_WEIGHT, LOSSLESS_QUALITY_WEIGHT, DEFAULT_QUALITY_WEIGHT,
    TrackResolutionStatus
)
from utils import retry_with_backoff, set_config_permissions, handle_error_with_raise
from spinner import Spinner
from keychain_utils import store_tidal_session, get_tidal_session

logger = logging.getLogger('playlist_builder.tidal')

class TidalProvider:
    """Provider for Tidal music service."""
    
    def __init__(self, cfg: Dict[str, Any], cfg_path: str, debug: bool = False):
        """
        Initialize Tidal provider.
        
        Args:
            cfg: Configuration dictionary
            cfg_path: Path to configuration file
            debug: Enable debug logging
        """
        self.session = tidalapi.Session()
        self.cfg = cfg
        self.cfg_path = cfg_path
        self.debug = debug
        
        if debug:
            logger.setLevel(logging.DEBUG)

    def _save_session_data(self):
        """Save session data to Keychain."""
        try:
            # Get token values from session
            token_type = getattr(self.session, 'token_type', None)
            access_token = getattr(self.session, 'access_token', None)
            refresh_token = getattr(self.session, 'refresh_token', None)
            
            # Ensure values are strings or None (filters out Mock objects and other non-string types)
            if token_type is not None and not isinstance(token_type, str):
                token_type = None
            if access_token is not None and not isinstance(access_token, str):
                access_token = None
            if refresh_token is not None and not isinstance(refresh_token, str):
                refresh_token = None
            
            # Ensure we have at least token_type and access_token
            if not token_type or not access_token:
                logger.warning("Missing required session data, skipping save")
                return
            
            session_data = {
                'token_type': token_type,
                'access_token': access_token,
                'refresh_token': refresh_token
            }
            
            if sys.platform == "darwin":
                if store_tidal_session(session_data):
                    logger.info("Saved Tidal session data to Keychain")
                else:
                    logger.warning("Failed to save session data to Keychain")
            else:
                # Fallback to config file for non-macOS
                self.cfg.setdefault('TIDAL', {})['SESSION_DATA'] = session_data
                os.makedirs(os.path.dirname(self.cfg_path), exist_ok=True)
                with open(self.cfg_path, 'w') as f:
                    json.dump(self.cfg, f, indent=2)
                set_config_permissions(self.cfg_path)
                logger.info("Saved Tidal session data to config file (non-macOS)")
        except Exception as e:
            logger.error(f"Failed to save session data: {e}")
            raise

    def authenticate(self) -> bool:
        """
        Authenticate with Tidal API.
        
        Returns:
            True if authenticated successfully
        """
        try:
            # Load session data from Keychain
            if sys.platform == "darwin":
                session_data = get_tidal_session() or {}
            else:
                # Fallback to config file for non-macOS
                session_data = self.cfg.get('TIDAL', {}).get('SESSION_DATA', {})
            
            if session_data.get('access_token'):
                try:
                    self.session.load_oauth_session(
                        session_data['token_type'],
                        session_data['access_token'],
                        session_data.get('refresh_token')
                    )
                    logger.debug("Loaded existing OAuth session from Keychain")
                except Exception as e:
                    logger.warning(f"Failed to load existing session: {e}")
                    # Continue to re-authenticate
            
            if not self.session.check_login():
                logger.info("OAuth handshake required")
                print(f"{YELLOW}OAuth Handshake Required...{RESET}")
                
                try:
                    self.session.login_oauth_simple()
                    self._save_session_data()
                    logger.info("OAuth authentication successful")
                    return True
                except Exception as e:
                    handle_error_with_raise(e, "Tidal authentication failed", logger)
            else:
                logger.debug("Already authenticated")
                return True
                
        except tidalapi.exceptions.TidalAPIError as e:
            handle_error_with_raise(e, "Tidal API error", logger)
        except Exception as e:
            handle_error_with_raise(e, "Authentication failed", logger, debug=self.debug)

    def _clean(self, text: str) -> set:
        """
        Clean and tokenize text for matching.
        
        Args:
            text: Input text
            
        Returns:
            Set of cleaned tokens
        """
        if not text:
            return set()
        
        # Remove parenthetical content and brackets
        cleaned = re.sub(r'[\(\[].*?[\)\]]', '', text.lower())
        # Remove non-alphanumeric characters except spaces
        cleaned = re.sub(r'[^a-z0-9\s]', '', cleaned)
        # Split into tokens
        return set(cleaned.split())

    @retry_with_backoff(max_retries=3, exceptions=(Exception,))
    def _resolve_best_node(self, title: str, artist: str) -> Dict[str, Any]:
        """
        Resolve best matching track from Tidal.
        
        Args:
            title: Track title
            artist: Artist name
            
        Returns:
            Dictionary with status, match, and score
        """
        if not title or not artist:
            logger.warning(f"Invalid input: title={title}, artist={artist}")
            return {"status": TrackResolutionStatus.FAILED.value, "match": None, "score": 0.0}
        
        query = f'"{title}" {artist}'
        logger.debug(f"Searching Tidal: {query}")
        
        try:
            res = self.session.search(query, models=[tidalapi.media.Track])
            
            if not res or 'tracks' not in res or not res['tracks']:
                logger.debug(f"No tracks found for: {query}")
                return {"status": TrackResolutionStatus.FAILED.value, "match": None, "score": 0.0}
            
            req_title_set = self._clean(title)
            anchor = re.sub(r'[^a-z0-9]', '', artist.lower().split()[0]) if artist else ""
            
            candidates = []
            
            for track in res['tracks']:
                try:
                    track_title_set = self._clean(track.name)
                    
                    # Calculate similarity score
                    if not req_title_set:
                        score = 0.0
                    else:
                        intersection = req_title_set.intersection(track_title_set)
                        score = len(intersection) / len(req_title_set)
                    
                    # Check artist anchor match
                    artist_name_clean = re.sub(r'[^a-z0-9]', '', track.artist.name.lower())
                    artist_match = anchor in artist_name_clean if anchor else True
                    
                    # Filter by minimum score and artist match
                    if artist_match and score > MIN_MATCH_SCORE:
                        # Quality weighting
                        quality = getattr(track, 'audio_quality', 'LOSSLESS')
                        if "HI_RES" in quality:
                            q_weight = HI_RES_QUALITY_WEIGHT
                        elif "LOSSLESS" in quality:
                            q_weight = LOSSLESS_QUALITY_WEIGHT
                        else:
                            q_weight = DEFAULT_QUALITY_WEIGHT
                        
                        candidates.append({
                            "match": track,
                            "score": score,
                            "q_weight": q_weight
                        })
                except (AttributeError, KeyError, TypeError) as e:
                    logger.warning(f"Error processing track {track.name}: {e}")
                    continue
                except Exception as e:
                    logger.error(f"Unexpected error processing track {track.name}: {e}", exc_info=self.debug)
                    continue
            
            if candidates:
                # Sort by quality weight (descending), then score (descending)
                best = sorted(candidates, key=lambda x: (x['q_weight'], x['score']), reverse=True)[0]
                logger.debug(f"Best match: {best['match'].name} (score: {best['score']:.2f})")
                return {
                    "status": TrackResolutionStatus.STRICT.value,
                    "match": best['match'],
                    "score": best['score']
                }
            else:
                logger.debug(f"No candidates met criteria for: {query}")
                return {"status": TrackResolutionStatus.FAILED.value, "match": None, "score": 0.0}
                
        except tidalapi.exceptions.TidalAPIError as e:
            logger.error(f"Tidal API error: {e}")
            return {"status": TrackResolutionStatus.FAILED.value, "match": None, "score": 0.0}
        except Exception as e:
            logger.error(f"Error resolving track {title} by {artist}: {e}", exc_info=self.debug)
            return {"status": TrackResolutionStatus.FAILED.value, "match": None, "score": 0.0}

    def publish(self, name: str, tracks: List[Dict[str, Any]], replace: bool = False, metrics: Optional[Any] = None) -> None:
        """
        Publish tracks to a Tidal playlist.
        
        Args:
            name: Playlist name
            tracks: List of track dictionaries
            replace: Whether to replace existing playlist
            metrics: Optional metrics collector
        """
        if not tracks:
            logger.warning("No tracks to publish")
            print(f"{YELLOW}Warning: No tracks to publish.{RESET}")
            return
        
        with Spinner("Authenticating with Tidal..."):
            self.authenticate()
        
        logger.info(f"Publishing {len(tracks)} tracks to playlist: {name}")
        print(f"\n{BLUE}{'━'*120}{RESET}\n{BOLD}SYNCING TO TIDAL:{RESET} {CYAN}{name}{RESET}\n{BLUE}{'━'*120}{RESET}")
        
        valid_ids = []
        skipped_count = 0
        start_time = time.perf_counter()
        track_display_data = []  # Store track data for display
        
        # Process tracks with spinner
        spinner = Spinner("Processing tracks...")
        spinner.start()
        
        for track in tracks:
            tidal_id = track.get('tidal_id')
            if not tidal_id:
                logger.debug(f"Skipping track without tidal_id: {track.get('title', 'Unknown')}")
                skipped_count += 1
                continue
            
            valid_ids.append(tidal_id)
            quality = track.get('quality', '')
            q_tag = f"{MAGENTA}HI-RES{RESET}" if "HI_RES" in quality else f"{CYAN}HiFi{RESET}"
            score = track.get('score', 0.0)
            
            title = track.get('title', 'Unknown')[:33]
            artist = track.get('artist', 'Unknown')[:25]
            
            # Store for display after spinner stops
            track_display_data.append({
                'title': title,
                'artist': artist,
                'q_tag': q_tag,
                'score': score
            })
        
        spinner.stop()
        
        # Now print the table with all tracks
        print(f"{BLUE}╒{'═'*35}╤{'═'*27}╤{'═'*52}╕{RESET}")
        # Headers: pad visible text, then wrap with BOLD (padding happens before ANSI codes)
        h1_padded = "CACHE OBJECT TITLE".ljust(33)
        h2_padded = "TARGET ARTIST".ljust(25)
        h3_padded = "SIGNAL NODE STATUS".ljust(50)
        print(f"{BLUE}│{RESET} {BOLD}{h1_padded}{RESET}{BLUE}│{RESET} {BOLD}{h2_padded}{RESET}{BLUE}│{RESET} {BOLD}{h3_padded}{RESET}{BLUE}│{RESET}")
        print(f"{BLUE}╞{'═'*35}╪{'═'*27}╪{'═'*52}╡{RESET}")
        
        for track_data in track_display_data:
            # Format status column with proper padding (50 visible chars)
            # Build visible text to calculate padding needed
            q_visible = "HI-RES" if "HI-RES" in track_data['q_tag'] else "HiFi"
            status_visible_len = len(f"DEPLOYED ({q_visible} | Sim: {track_data['score']:.2f})")
            status_text = f"{GREEN}DEPLOYED{RESET} ({track_data['q_tag']} | Sim: {track_data['score']:.2f})"
            status_padded = status_text + " " * (50 - status_visible_len)
            print(f"{BLUE}│{RESET} {track_data['title']:<33}{BLUE}│{RESET} {track_data['artist']:<25}{BLUE}│{RESET} {status_padded}{BLUE}│{RESET}")
        
        print(f"{BLUE}╘{'═'*35}╧{'═'*27}╧{'═'*52}╛{RESET}")
        
        if not valid_ids:
            logger.warning("No valid track IDs to publish")
            print(f"{YELLOW}Warning: No valid tracks to publish.{RESET}")
            if metrics:
                metrics.update_items(processed=len(tracks), succeeded=0, failed=len(tracks))
            return
        
        try:
            # Find or create playlist
            target_playlist = None
            with Spinner("Locating playlist..."):
                try:
                    for playlist in self.session.user.playlists():
                        if playlist.name == name:
                            target_playlist = playlist
                            break
                except Exception as e:
                    handle_error_with_raise(e, "Failed to access playlists", logger)
            
            if target_playlist and replace:
                logger.info(f"Replacing existing playlist: {name}")
                with Spinner("Clearing existing playlist..."):
                    try:
                        for item in target_playlist.items():
                            target_playlist.remove_by_id(item.id)
                    except Exception as e:
                        handle_error_with_raise(e, "Failed to clear existing playlist", logger)
            
            if not target_playlist:
                logger.info(f"Creating new playlist: {name}")
                with Spinner("Creating playlist..."):
                    try:
                        target_playlist = self.session.user.create_playlist(name, "AI Generated")
                    except Exception as e:
                        handle_error_with_raise(e, "Failed to create playlist", logger)
            
            # Add tracks
            logger.info(f"Adding {len(valid_ids)} tracks to playlist")
            with Spinner(f"Adding {len(valid_ids)} tracks to playlist..."):
                try:
                    target_playlist.add(valid_ids)
                    elapsed = time.perf_counter() - start_time
                    logger.info(f"Successfully published {len(valid_ids)} tracks in {elapsed:.2f}s")
                    print(f"\n{GREEN}{BOLD}✔ SUCCESS:{RESET} {len(valid_ids)} nodes committed.")
                    
                    if metrics:
                        metrics.update_items(
                            processed=len(tracks),
                            succeeded=len(valid_ids),
                            failed=skipped_count
                        )
                        metrics.add_stat("playlist_created", target_playlist is not None)
                        metrics.add_stat("playlist_replaced", replace and target_playlist is not None)
                        metrics.add_stat("publish_duration_seconds", elapsed)
                except Exception as e:
                    handle_error_with_raise(e, "Failed to add tracks to playlist", logger)
                
        except tidalapi.exceptions.TidalAPIError as e:
            handle_error_with_raise(e, "Tidal API error", logger)
        except Exception as e:
            handle_error_with_raise(e, "Publish failed", logger, debug=self.debug)
