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
Spotify API integration engine (EXPERIMENTAL).

This module provides experimental support for publishing playlists to Spotify.
"""
import json
import logging
import os
import re
import sys
import time
from typing import Dict, Optional, Any, List

import spotipy
from spotipy.oauth2 import SpotifyOAuth

from constants import (
    BOLD, GREEN, YELLOW, CYAN, RED, BLUE, MAGENTA, RESET, DIM,
    MIN_MATCH_SCORE, TrackResolutionStatus
)
from utils import retry_with_backoff, set_config_permissions, handle_error_with_raise
from spinner import Spinner
from keychain_utils import store_spotify_session, get_spotify_session, get_secret

logger = logging.getLogger('playlist_builder.spotify')

# Spotify OAuth scopes required for playlist management
SPOTIFY_SCOPES = "playlist-modify-public playlist-modify-private playlist-read-private"


class SpotifyProvider:
    """Provider for Spotify music service (EXPERIMENTAL)."""
    
    def __init__(self, cfg: Dict[str, Any], cfg_path: str, debug: bool = False):
        """
        Initialize Spotify provider.
        
        Args:
            cfg: Configuration dictionary
            cfg_path: Path to configuration file
            debug: Enable debug logging
        """
        self.client: Optional[spotipy.Spotify] = None
        self.cfg = cfg
        self.cfg_path = cfg_path
        self.debug = debug
        self._user_id: Optional[str] = None
        
        if debug:
            logger.setLevel(logging.DEBUG)

    def _get_credentials(self) -> tuple[Optional[str], Optional[str]]:
        """
        Get Spotify credentials from Keychain or config.
        
        Returns:
            Tuple of (client_id, client_secret)
        """
        # Try Keychain first (macOS)
        if sys.platform == "darwin":
            client_id = get_secret("spotify_client_id", account="spotify")
            client_secret = get_secret("spotify_client_secret", account="spotify")
            if client_id and client_secret:
                return client_id, client_secret
        
        # Fallback to config
        spotify_cfg = self.cfg.get('SPOTIFY', {})
        return spotify_cfg.get('CLIENT_ID'), spotify_cfg.get('CLIENT_SECRET')

    def _save_session_data(self, token_info: Dict[str, Any]):
        """Save session data to Keychain."""
        try:
            if sys.platform == "darwin":
                if store_spotify_session(token_info):
                    logger.info("Saved Spotify session data to Keychain")
                else:
                    logger.warning("Failed to save session data to Keychain")
            else:
                # Fallback to config file for non-macOS
                self.cfg.setdefault('SPOTIFY', {})['SESSION_DATA'] = token_info
                os.makedirs(os.path.dirname(self.cfg_path), exist_ok=True)
                with open(self.cfg_path, 'w') as f:
                    json.dump(self.cfg, f, indent=2)
                set_config_permissions(self.cfg_path)
                logger.info("Saved Spotify session data to config file (non-macOS)")
        except Exception as e:
            logger.error(f"Failed to save session data: {e}")
            raise

    def authenticate(self) -> bool:
        """
        Authenticate with Spotify API.
        
        Returns:
            True if authenticated successfully
        """
        try:
            client_id, client_secret = self._get_credentials()
            
            if not client_id or not client_secret:
                print(f"{RED}Error: Spotify credentials not configured.{RESET}")
                print(f"{YELLOW}Set credentials using:{RESET}")
                print(f"  playlist-builder keychain set SPOTIFY_CLIENT_ID")
                print(f"  playlist-builder keychain set SPOTIFY_CLIENT_SECRET")
                print(f"\n{DIM}Get credentials from: https://developer.spotify.com/dashboard{RESET}")
                raise ValueError("Spotify credentials not configured")
            
            # Check for existing session
            session_data = None
            if sys.platform == "darwin":
                session_data = get_spotify_session()
            else:
                session_data = self.cfg.get('SPOTIFY', {}).get('SESSION_DATA')
            
            # Create OAuth handler with cache
            auth_manager = SpotifyOAuth(
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri="http://localhost:8888/callback",
                scope=SPOTIFY_SCOPES,
                cache_handler=None,  # We handle caching ourselves
                open_browser=True
            )
            
            # Try to use cached token
            if session_data:
                try:
                    auth_manager.token_info = session_data
                    if auth_manager.is_token_expired(session_data):
                        logger.info("Refreshing expired Spotify token")
                        session_data = auth_manager.refresh_access_token(session_data['refresh_token'])
                        self._save_session_data(session_data)
                except Exception as e:
                    logger.warning(f"Failed to use cached token: {e}")
                    session_data = None
            
            # Get new token if needed
            if not session_data:
                logger.info("OAuth handshake required")
                print(f"{YELLOW}Spotify OAuth Handshake Required...{RESET}")
                print(f"{DIM}A browser window will open for authentication.{RESET}")
                
                session_data = auth_manager.get_access_token(as_dict=True)
                self._save_session_data(session_data)
            
            # Create Spotify client
            self.client = spotipy.Spotify(auth=session_data['access_token'])
            
            # Verify authentication and get user ID
            user_info = self.client.current_user()
            self._user_id = user_info['id']
            logger.info(f"Authenticated as Spotify user: {self._user_id}")
            
            return True
            
        except spotipy.SpotifyException as e:
            handle_error_with_raise(e, "Spotify API error", logger)
        except Exception as e:
            handle_error_with_raise(e, "Spotify authentication failed", logger, debug=self.debug)
        
        return False

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
        Resolve best matching track from Spotify.
        
        Args:
            title: Track title
            artist: Artist name
            
        Returns:
            Dictionary with status, match, and score
        """
        if not title or not artist:
            logger.warning(f"Invalid input: title={title}, artist={artist}")
            return {"status": TrackResolutionStatus.FAILED.value, "match": None, "score": 0.0}
        
        if not self.client:
            logger.error("Spotify client not initialized")
            return {"status": TrackResolutionStatus.FAILED.value, "match": None, "score": 0.0}
        
        query = f'track:"{title}" artist:{artist}'
        logger.debug(f"Searching Spotify: {query}")
        
        try:
            results = self.client.search(q=query, type='track', limit=10)
            
            if not results or 'tracks' not in results or not results['tracks']['items']:
                logger.debug(f"No tracks found for: {query}")
                return {"status": TrackResolutionStatus.FAILED.value, "match": None, "score": 0.0}
            
            req_title_set = self._clean(title)
            anchor = re.sub(r'[^a-z0-9]', '', artist.lower().split()[0]) if artist else ""
            
            candidates = []
            
            for track in results['tracks']['items']:
                try:
                    track_title_set = self._clean(track['name'])
                    
                    # Calculate similarity score
                    if not req_title_set:
                        score = 0.0
                    else:
                        intersection = req_title_set.intersection(track_title_set)
                        score = len(intersection) / len(req_title_set)
                    
                    # Check artist anchor match
                    track_artists = ' '.join([a['name'] for a in track['artists']])
                    artist_name_clean = re.sub(r'[^a-z0-9]', '', track_artists.lower())
                    artist_match = anchor in artist_name_clean if anchor else True
                    
                    # Filter by minimum score and artist match
                    if artist_match and score > MIN_MATCH_SCORE:
                        candidates.append({
                            "match": track,
                            "score": score,
                        })
                except (KeyError, TypeError) as e:
                    logger.warning(f"Error processing track: {e}")
                    continue
                except Exception as e:
                    logger.error(f"Unexpected error processing track: {e}", exc_info=self.debug)
                    continue
            
            if candidates:
                # Sort by score (descending)
                best = sorted(candidates, key=lambda x: x['score'], reverse=True)[0]
                logger.debug(f"Best match: {best['match']['name']} (score: {best['score']:.2f})")
                return {
                    "status": TrackResolutionStatus.STRICT.value,
                    "match": best['match'],
                    "score": best['score']
                }
            else:
                logger.debug(f"No candidates met criteria for: {query}")
                return {"status": TrackResolutionStatus.FAILED.value, "match": None, "score": 0.0}
                
        except spotipy.SpotifyException as e:
            logger.error(f"Spotify API error: {e}")
            return {"status": TrackResolutionStatus.FAILED.value, "match": None, "score": 0.0}
        except Exception as e:
            logger.error(f"Error resolving track {title} by {artist}: {e}", exc_info=self.debug)
            return {"status": TrackResolutionStatus.FAILED.value, "match": None, "score": 0.0}

    def publish(self, name: str, tracks: List[Dict[str, Any]], replace: bool = False, metrics: Optional[Any] = None) -> None:
        """
        Publish tracks to a Spotify playlist.
        
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
        
        with Spinner("Authenticating with Spotify..."):
            self.authenticate()
        
        if not self.client or not self._user_id:
            print(f"{RED}Error: Not authenticated with Spotify.{RESET}")
            return
        
        logger.info(f"Publishing {len(tracks)} tracks to playlist: {name}")
        print(f"\n{BLUE}{'━'*120}{RESET}\n{BOLD}SYNCING TO SPOTIFY:{RESET} {CYAN}{name}{RESET} {YELLOW}(EXPERIMENTAL){RESET}\n{BLUE}{'━'*120}{RESET}")
        
        valid_uris = []
        skipped_count = 0
        start_time = time.perf_counter()
        track_display_data = []
        
        # Process tracks - resolve from cache or search
        spinner = Spinner("Resolving tracks on Spotify...")
        spinner.start()
        
        for track in tracks:
            # Check if we have a spotify_id already
            spotify_id = track.get('spotify_id')
            
            if not spotify_id:
                # Try to resolve the track on Spotify
                title = track.get('title', '')
                artist = track.get('artist', '')
                
                if title and artist:
                    result = self._resolve_best_node(title, artist)
                    if result['status'] == TrackResolutionStatus.STRICT.value and result['match']:
                        spotify_id = result['match']['id']
                        score = result['score']
                    else:
                        skipped_count += 1
                        continue
                else:
                    skipped_count += 1
                    continue
            else:
                score = track.get('score', 0.0)
            
            uri = f"spotify:track:{spotify_id}"
            valid_uris.append(uri)
            
            title_display = track.get('title', 'Unknown')[:33]
            artist_display = track.get('artist', 'Unknown')[:25]
            
            track_display_data.append({
                'title': title_display,
                'artist': artist_display,
                'score': score if 'score' in dir() else track.get('score', 0.0)
            })
        
        spinner.stop()
        
        # Print the table
        print(f"{BLUE}╒{'═'*35}╤{'═'*27}╤{'═'*52}╕{RESET}")
        h1_padded = "CACHE OBJECT TITLE".ljust(33)
        h2_padded = "TARGET ARTIST".ljust(25)
        h3_padded = "SIGNAL NODE STATUS".ljust(50)
        print(f"{BLUE}│{RESET} {BOLD}{h1_padded}{RESET}{BLUE}│{RESET} {BOLD}{h2_padded}{RESET}{BLUE}│{RESET} {BOLD}{h3_padded}{RESET}{BLUE}│{RESET}")
        print(f"{BLUE}╞{'═'*35}╪{'═'*27}╪{'═'*52}╡{RESET}")
        
        for track_data in track_display_data:
            status_visible_len = len(f"DEPLOYED (Spotify | Sim: {track_data['score']:.2f})")
            status_text = f"{GREEN}DEPLOYED{RESET} ({CYAN}Spotify{RESET} | Sim: {track_data['score']:.2f})"
            status_padded = status_text + " " * (50 - status_visible_len)
            print(f"{BLUE}│{RESET} {track_data['title']:<33}{BLUE}│{RESET} {track_data['artist']:<25}{BLUE}│{RESET} {status_padded}{BLUE}│{RESET}")
        
        print(f"{BLUE}╘{'═'*35}╧{'═'*27}╧{'═'*52}╛{RESET}")
        
        if not valid_uris:
            logger.warning("No valid track URIs to publish")
            print(f"{YELLOW}Warning: No valid tracks to publish.{RESET}")
            if metrics:
                metrics.update_items(processed=len(tracks), succeeded=0, failed=len(tracks))
            return
        
        try:
            # Find or create playlist
            target_playlist = None
            with Spinner("Locating playlist..."):
                try:
                    playlists = self.client.current_user_playlists(limit=50)
                    for playlist in playlists['items']:
                        if playlist['name'] == name:
                            target_playlist = playlist
                            break
                except Exception as e:
                    handle_error_with_raise(e, "Failed to access playlists", logger)
            
            if target_playlist and replace:
                logger.info(f"Replacing existing playlist: {name}")
                with Spinner("Clearing existing playlist..."):
                    try:
                        # Get all tracks in playlist and remove them
                        playlist_tracks = self.client.playlist_items(target_playlist['id'])
                        if playlist_tracks['items']:
                            track_uris = [{'uri': item['track']['uri']} for item in playlist_tracks['items'] if item['track']]
                            if track_uris:
                                self.client.playlist_remove_all_occurrences_of_items(target_playlist['id'], track_uris)
                    except Exception as e:
                        handle_error_with_raise(e, "Failed to clear existing playlist", logger)
            
            if not target_playlist:
                logger.info(f"Creating new playlist: {name}")
                with Spinner("Creating playlist..."):
                    try:
                        target_playlist = self.client.user_playlist_create(
                            self._user_id, 
                            name, 
                            public=False,
                            description="AI Generated by playlist-builder"
                        )
                    except Exception as e:
                        handle_error_with_raise(e, "Failed to create playlist", logger)
            
            # Add tracks (Spotify allows max 100 at a time)
            logger.info(f"Adding {len(valid_uris)} tracks to playlist")
            with Spinner(f"Adding {len(valid_uris)} tracks to playlist..."):
                try:
                    # Add in batches of 100
                    for i in range(0, len(valid_uris), 100):
                        batch = valid_uris[i:i+100]
                        self.client.playlist_add_items(target_playlist['id'], batch)
                    
                    elapsed = time.perf_counter() - start_time
                    logger.info(f"Successfully published {len(valid_uris)} tracks in {elapsed:.2f}s")
                    print(f"\n{GREEN}{BOLD}✔ SUCCESS:{RESET} {len(valid_uris)} nodes committed to Spotify.")
                    
                    if metrics:
                        metrics.update_items(
                            processed=len(tracks),
                            succeeded=len(valid_uris),
                            failed=skipped_count
                        )
                        metrics.add_stat("playlist_created", target_playlist is not None)
                        metrics.add_stat("playlist_replaced", replace and target_playlist is not None)
                        metrics.add_stat("publish_duration_seconds", elapsed)
                except Exception as e:
                    handle_error_with_raise(e, "Failed to add tracks to playlist", logger)
                
        except spotipy.SpotifyException as e:
            handle_error_with_raise(e, "Spotify API error", logger)
        except Exception as e:
            handle_error_with_raise(e, "Publish failed", logger, debug=self.debug)

