#!/usr/bin/env python3
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
Playlist Builder v28.2 - Refactored & Hardened with Keychain Integration
===================================================
Target: macOS Native (Python 3.12+)
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from typing import List, Optional

# Add script directory to Python path for imports
_script_dir = os.path.dirname(os.path.abspath(__file__))
if _script_dir not in sys.path:
    sys.path.insert(0, _script_dir)

from constants import (
    BASE_DIR, VENV_DIR, CONFIG_FILE, CACHE_FILE,
    BOLD, RED, GREEN, YELLOW, CYAN, BLUE, MAGENTA, RESET, DIM, HR,
    DEFAULT_LIMIT, CHAT_DEFAULT_LIMIT, MAX_WORKERS, HIGH_CONFIDENCE_SCORE,
    GEMINI_MODEL, AVAILABLE_MODELS, GEMINI_THINKING_LEVEL,
    TrackResolutionStatus, API_TIMEOUT_SECONDS,
    MAX_CONFIG_SIZE_BYTES, MAX_JSON_SIZE_BYTES
)
from utils import (
    setup_logging, validate_config, retry_with_backoff, format_track_signal, print_track_row,
    validate_query, set_config_permissions, rate_limit, safe_json_load, validate_file_path,
    handle_error_with_exit, handle_error_with_raise, handle_warning
)
from spinner import Spinner
from metrics import MetricsCollector
from keychain_utils import (
    get_secret, store_secret, get_tidal_session, store_tidal_session,
    migrate_secrets_from_config, delete_secret
)

logger = None  # Will be initialized in main()

@dataclass
class Track:
    """Represents a music track with metadata."""
    title: str
    artist: str
    album: str = "UNKNOWN"
    isrc: str = "UNKNOWN"
    tidal_id: Optional[str] = None
    score: float = 0.0
    year: str = "N/A"
    quality: str = "N/A"
    latency_ms: float = 0.0

def print_help():
    """Display simplified help."""
    print(f"""
{BOLD}playlist-builder{RESET} - AI-powered music discovery and playlist curation

{BOLD}USAGE{RESET}
    playlist-builder {BOLD}chat{RESET} [--model <model>] [--limit <n>] [--debug]
    playlist-builder {BOLD}query{RESET} <query> [--model <model>] [--limit <n>] [--debug]
    playlist-builder {BOLD}publish{RESET} tidal --name <name> [--replace]
    playlist-builder {BOLD}keychain{RESET} <set|get|delete|list> [key] [value]
    playlist-builder {BOLD}reset{RESET} | {BOLD}rebuild{RESET}

{BOLD}COMMANDS{RESET}
    {CYAN}chat{RESET}               Interactive conversational discovery session
    {CYAN}query{RESET} <query>      One-shot track discovery using AI (Gemini)
    {CYAN}publish{RESET} tidal      Sync results to Tidal playlist
    {CYAN}keychain{RESET}            Manage secrets (macOS Keychain)
    {CYAN}reset{RESET}               Clear cache and credentials
    {CYAN}rebuild{RESET}             Reinstall virtual environment

{BOLD}OPTIONS{RESET}
    --model <model>          Gemini model (default: 3-flash)
    --limit <n>              Max tracks per query (default: 10, range: 1-100)
    --debug                  Enable debug logging

{BOLD}EXAMPLES{RESET}
    playlist-builder chat
    playlist-builder chat --model 3-pro --limit 20
    playlist-builder query "Jazz classics for late night"
    playlist-builder publish tidal --name "My Playlist"
    playlist-builder keychain set GEMINI_API_KEY
""")

class MusicCurator:
    """AI-powered music curator using Gemini."""
    
    def __init__(self, cfg: dict, model: str = GEMINI_MODEL, debug: bool = False):
        """
        Initialize curator with configuration.
        
        Args:
            cfg: Configuration dictionary
            model: Gemini model identifier
            debug: Enable debug logging
        """
        self.cfg = cfg
        self.model = model
        self.debug = debug
        self.is_gemini_3 = model.startswith("gemini-3")
        
        try:
            from google import genai
            api_key = cfg.get('GEMINI', {}).get('API_KEY')
            if not api_key:
                raise ValueError("Gemini API key not found in configuration")
            self.client = genai.Client(api_key=api_key)
            if logger:
                logger.info(f"Initialized MusicCurator with model: {model}")
        except ImportError:
            if logger:
                logger.error("google-genai package not installed")
            raise
        except Exception as e:
            if logger:
                logger.error(f"Failed to initialize Gemini client: {e}")
            raise

    @rate_limit
    @retry_with_backoff(max_retries=3, exceptions=(Exception,))
    def _generate_track_list(self, query: str, limit: int, metrics: Optional[MetricsCollector] = None) -> List[dict]:
        """Generate track list from AI query."""
        from google.genai import types
        
        spinner = Spinner("Querying Gemini AI for track candidates...")
        spinner.start()
        
        try:
            tool = types.Tool(google_search=types.GoogleSearch())
            prompt = (
                f"Identify {limit} REAL music tracks matching: '{query}'. "
                "Return a JSON array: [{\"title\": \"...\", \"artist\": \"...\"}]. "
                "If the query is ambiguous or no tracks are found, explain why briefly."
            )
            # Build config with Gemini 3 features if applicable
            config_params = {
                "tools": [tool],
                "temperature": 0.3
            }
            
            # Note: ThinkingConfig with thinking_level is not yet stable in google-genai
            # Omitting for now to ensure compatibility across versions
            if self.is_gemini_3 and logger:
                logger.debug(f"Using Gemini 3 model: {self.model}")
            
            resp = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(**config_params)
            )
            
            spinner.stop(f"{GREEN}✓{RESET} AI query completed")
            
            if not resp.text:
                if logger:
                    logger.warning("AI returned empty response")
                if metrics:
                    metrics.add_stat("ai_response", "empty")
                return []
            
            json_match = re.search(r'\[.*\]', resp.text, re.DOTALL)
            if not json_match:
                if logger:
                    logger.info(f"AI response (no JSON): {resp.text[:200]}")
                if metrics:
                    metrics.add_stat("ai_response", "no_json")
                return []
            
            candidates = json.loads(json_match.group(0))
            if not isinstance(candidates, list):
                if logger:
                    logger.warning("AI returned non-list JSON")
                if metrics:
                    metrics.add_stat("ai_response", "invalid_format")
                return []
            
            if metrics:
                metrics.add_stat("candidates_found", len(candidates))
            
            return candidates
            
        except json.JSONDecodeError as e:
            spinner.stop(f"{RED}✗{RESET} Failed to parse AI response")
            if logger:
                logger.error(f"Failed to parse AI JSON response: {e}")
            if metrics:
                metrics.add_stat("error", "json_decode")
            return []
        except Exception as e:
            spinner.stop(f"{RED}✗{RESET} AI query failed")
            if logger:
                logger.error(f"Error generating track list: {e}", exc_info=self.debug)
            if metrics:
                metrics.add_stat("error", str(e))
            raise
        finally:
            if spinner.is_running:
                spinner.stop()

    def curate(self, query: str, limit: int, engine: 'TidalProvider', metrics: Optional[MetricsCollector] = None) -> List[Track]:
        """
        Curate tracks based on query.
        
        Args:
            query: Natural language query
            limit: Maximum number of tracks to return
            engine: TidalProvider instance
            metrics: Optional metrics collector
            
        Returns:
            List of validated Track objects
        """
        if logger:
            logger.info(f"Curating tracks for query: {query} (limit: {limit})")
        
        candidates = self._generate_track_list(query, limit, metrics)
        if not candidates:
            print(f"\n{YELLOW}{BOLD}AGENT INSIGHT:{RESET}")
            print(f"{DIM}No tracks found matching your query.{RESET}\n")
            return []
        
        validated = []
        validated_lock = threading.Lock()
        failed_count = 0
        total_candidates = len(candidates)
        
        spinner = Spinner("Resolving tracks via Tidal API...")
        spinner.start()
        
        print(f"\n{YELLOW}Negotiating High-Resolution Nodes via Tidal Cluster...{RESET}")
        print(f"{BLUE}╒{'═'*35}╤{'═'*22}╤{'═'*20}╤{'═'*15}╤{'═'*7}╤{'═'*12}╕{RESET}")
        # Headers: pad visible text, then wrap with BOLD (padding happens before ANSI codes)
        h1_padded = "DISCOVERY TITLE".ljust(33)
        h2_padded = "ARTIST".ljust(20)
        h3_padded = "ALBUM".ljust(18)
        h4_padded = "ISRC".ljust(13)
        h5_padded = "YEAR".ljust(5)
        h6_padded = "SIGNAL".ljust(10)
        print(f"{BLUE}│{RESET} {BOLD}{h1_padded}{RESET}{BLUE}│{RESET} {BOLD}{h2_padded}{RESET}{BLUE}│{RESET} {BOLD}{h3_padded}{RESET}{BLUE}│{RESET} {BOLD}{h4_padded}{RESET}{BLUE}│{RESET} {BOLD}{h5_padded}{RESET}{BLUE}│{RESET} {BOLD}{h6_padded}{RESET}{BLUE}│{RESET}")
        print(f"{BLUE}╞{'═'*35}╪{'═'*22}╪{'═'*20}╪{'═'*15}╪{'═'*7}╪{'═'*12}╡{RESET}")
        sys.stdout.flush()
        
        spinner.stop()  # Stop spinner once table header is shown
        
        def process_candidate(candidate: dict) -> Optional[Track]:
            """Process a single candidate track."""
            try:
                title = candidate.get('title', '')
                artist = candidate.get('artist', '')
                
                if not title or not artist:
                    logger.warning(f"Invalid candidate: {candidate}")
                    return None
                
                t0 = time.perf_counter()
                result = engine._resolve_best_node(title, artist)
                latency_ms = (time.perf_counter() - t0) * 1000
                
                if result['status'] == TrackResolutionStatus.FAILED.value:
                    if logger:
                        logger.debug(f"Failed to resolve: {title} by {artist}")
                    return None
                
                match = result['match']
                score = result['score']
                
                # Extract year safely
                try:
                    if hasattr(match.album, 'release_date') and match.album.release_date and hasattr(match.album.release_date, 'year'):
                        year = str(match.album.release_date.year)
                    else:
                        year = "N/A"
                except (AttributeError, TypeError):
                    year = "N/A"
                
                quality = getattr(match, 'audio_quality', 'LOSSLESS')
                isrc = getattr(match, 'isrc', 'N/A')
                
                track = Track(
                    title=match.name,
                    artist=match.artist.name,
                    album=match.album.name,
                    isrc=isrc,
                    tidal_id=str(match.id),
                    score=score,
                    year=year,
                    quality=quality,
                    latency_ms=latency_ms
                )
                
                return track
                
            except Exception as e:
                if logger:
                    logger.error(f"Error processing candidate {candidate}: {e}", exc_info=self.debug)
                return None
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(process_candidate, c): c for c in candidates}
            futures_set = set(futures.keys())
            
            try:
                for future in as_completed(futures_set):
                    try:
                        # Add timeout to prevent hanging on slow API calls
                        try:
                            track = future.result(timeout=API_TIMEOUT_SECONDS * 2)  # Allow 2x timeout for concurrent ops
                        except TimeoutError:
                            if logger:
                                logger.warning("Track resolution timed out, skipping")
                            with validated_lock:
                                failed_count += 1
                            continue
                        
                        with validated_lock:
                            # Check limit first (atomic check)
                            if len(validated) >= limit:
                                # Cancel remaining futures to save resources
                                for f in futures_set:
                                    if not f.done():
                                        f.cancel()
                                break
                            
                            if track is None:
                                failed_count += 1
                                continue
                            
                            # Double-check limit after getting result (atomic check and append)
                            if len(validated) >= limit:
                                # Cancel remaining futures
                                for f in futures_set:
                                    if not f.done():
                                        f.cancel()
                                break
                            
                            validated.append(track)
                            
                            # Display track
                            signal_text, _ = format_track_signal(track.quality, track.score)
                            print_track_row(
                                track.title, track.artist, track.album,
                                track.isrc, track.year, signal_text
                            )
                            
                    except Exception as e:
                        if logger:
                            logger.error(f"Error in future result: {e}", exc_info=self.debug)
                        with validated_lock:
                            failed_count += 1
            finally:
                # Ensure all futures are cleaned up
                for future in futures_set:
                    if not future.done():
                        future.cancel()
        
        print(f"{BLUE}╘{'═'*35}╧{'═'*22}╧{'═'*20}╧{'═'*15}╧{'═'*7}╧{'═'*12}╛{RESET}")
        
        if metrics:
            metrics.update_items(
                processed=total_candidates,
                succeeded=len(validated),
                failed=failed_count
            )
            avg_latency = sum(t.latency_ms for t in validated) / len(validated) if validated else 0
            hi_res_count = sum(1 for t in validated if "HI_RES" in t.quality)
            metrics.add_stat("avg_latency_ms", avg_latency)
            metrics.add_stat("hi_res_tracks", hi_res_count)
            metrics.add_stat("hifi_tracks", len(validated) - hi_res_count)
            metrics.add_stat("avg_match_score", sum(t.score for t in validated) / len(validated) if validated else 0)
        
        if logger:
            logger.info(f"Curated {len(validated)} tracks")
        return validated


class ChatSession:
    """Interactive conversational music discovery session."""
    
    def __init__(self, config: dict, engine: 'TidalProvider', model: str = GEMINI_MODEL, 
                 limit: int = CHAT_DEFAULT_LIMIT, debug: bool = False):
        """
        Initialize chat session.
        
        Args:
            config: Configuration dictionary
            engine: TidalProvider instance for track resolution
            model: Gemini model identifier
            limit: Default track limit per query
            debug: Enable debug logging
        """
        self.config = config
        self.engine = engine
        self.model = model
        self.limit = limit
        self.debug = debug
        self.conversation_history: List[dict] = []
        self.all_tracks: List[Track] = []
        self.curator = MusicCurator(config, model=model, debug=debug)
        
        if logger:
            logger.info(f"Started chat session with model: {model}, limit: {limit}")
    
    def _build_context_prompt(self, user_message: str) -> str:
        """Build prompt with conversation context."""
        context_parts = []
        
        if self.conversation_history:
            context_parts.append("Previous conversation context:")
            for turn in self.conversation_history[-5:]:  # Last 5 turns for context
                if turn['role'] == 'user':
                    context_parts.append(f"User asked: {turn['content']}")
                elif turn['role'] == 'assistant' and 'tracks' in turn:
                    track_summary = ", ".join([f"{t['title']} by {t['artist']}" for t in turn['tracks'][:3]])
                    context_parts.append(f"Found tracks including: {track_summary}...")
            context_parts.append("")
        
        context_parts.append(f"Current request: {user_message}")
        
        return "\n".join(context_parts)
    
    def process_message(self, user_message: str, metrics: Optional[MetricsCollector] = None) -> List[Track]:
        """
        Process a user message in the conversation.
        
        Args:
            user_message: The user's natural language query
            metrics: Optional metrics collector
            
        Returns:
            List of discovered Track objects
        """
        # Build contextual query
        contextual_query = self._build_context_prompt(user_message)
        
        # Add user message to history
        self.conversation_history.append({
            'role': 'user',
            'content': user_message
        })
        
        if logger:
            logger.debug(f"Processing chat message: {user_message}")
            logger.debug(f"Context prompt: {contextual_query}")
        
        # Use curator to get tracks
        tracks = self.curator.curate(contextual_query, self.limit, self.engine, metrics)
        
        # Add response to history
        self.conversation_history.append({
            'role': 'assistant',
            'content': f"Found {len(tracks)} tracks",
            'tracks': [asdict(t) for t in tracks]
        })
        
        # Accumulate all tracks discovered in session
        self.all_tracks.extend(tracks)
        
        return tracks
    
    def get_session_tracks(self) -> List[Track]:
        """Get all tracks discovered in this session."""
        return self.all_tracks
    
    def clear_history(self):
        """Clear conversation history but keep accumulated tracks."""
        self.conversation_history = []
        if logger:
            logger.info("Cleared conversation history")
    
    def run_interactive(self):
        """Run interactive chat loop."""
        print(f"\n{HR}")
        print(f"{BOLD}PLAYLIST BUILDER CHAT{RESET}")
        print(f"{DIM}Conversational AI-powered music discovery{RESET}")
        print(f"{HR}")
        print(f"\n{CYAN}Model:{RESET} {self.model}")
        print(f"{CYAN}Tracks per query:{RESET} {self.limit}")
        print(f"\n{DIM}Type your music queries. Commands:{RESET}")
        print(f"  {YELLOW}/publish <name>{RESET}  - Publish tracks to Tidal playlist")
        print(f"  {YELLOW}/new{RESET}             - Start fresh (clear tracks & context)")
        print(f"  {YELLOW}/tracks{RESET}          - Show all discovered tracks")
        print(f"  {YELLOW}/help{RESET}            - Show help")
        print(f"  {YELLOW}/quit{RESET}            - Exit chat")
        print(f"\n{HR}\n")
        
        while True:
            try:
                # Get user input
                user_input = input(f"{GREEN}You:{RESET} ").strip()
                
                if not user_input:
                    continue
                
                # Handle commands
                if user_input.lower() == '/quit' or user_input.lower() == '/exit':
                    print(f"\n{DIM}Ending chat session...{RESET}")
                    break
                
                if user_input.lower() == '/help':
                    print(f"\n{BOLD}Chat Commands:{RESET}")
                    print(f"  {YELLOW}/publish <name>{RESET}  - Publish tracks to Tidal as playlist <name>")
                    print(f"  {YELLOW}/new{RESET}             - Clear all tracks and context (start fresh)")
                    print(f"  {YELLOW}/tracks{RESET}          - List all tracks discovered in this session")
                    print(f"  {YELLOW}/clear{RESET}           - Clear conversation context only")
                    print(f"  {YELLOW}/quit{RESET}            - Exit the chat session")
                    print(f"\n{BOLD}Tips:{RESET}")
                    print(f"  - Use natural language: \"more like the first one but jazzier\"")
                    print(f"  - Be specific: \"1970s funk with horn sections\"")
                    print(f"  - Refine: \"less electronic, more acoustic\"")
                    print(f"\n{BOLD}Workflow:{RESET}")
                    print(f"  1. Query for tracks → 2. Refine → 3. /publish \"My Playlist\"")
                    print(f"  4. /new → Start another playlist\n")
                    continue
                
                if user_input.lower() == '/clear':
                    self.clear_history()
                    print(f"{GREEN}✓{RESET} Conversation context cleared.\n")
                    continue
                
                if user_input.lower() == '/new':
                    self.all_tracks = []
                    self.conversation_history = []
                    print(f"{GREEN}✓{RESET} Cleared all tracks and context. Ready for a new playlist!\n")
                    continue
                
                if user_input.lower() == '/tracks':
                    if not self.all_tracks:
                        print(f"{YELLOW}No tracks discovered yet.{RESET}\n")
                    else:
                        print(f"\n{BOLD}Discovered Tracks ({len(self.all_tracks)} total):{RESET}")
                        for i, track in enumerate(self.all_tracks, 1):
                            quality_indicator = "H" if "HI_RES" in track.quality else "L"
                            print(f"  {i:2}. {track.title[:40]:<40} - {track.artist[:20]:<20} [{quality_indicator}]")
                        print()
                    continue
                
                if user_input.lower().startswith('/publish'):
                    parts = user_input.split(maxsplit=1)
                    if len(parts) < 2:
                        print(f"{YELLOW}Usage: /publish <playlist name>{RESET}")
                        print(f"{DIM}Example: /publish \"Late Night Jazz\"{RESET}\n")
                        continue
                    
                    playlist_name = parts[1].strip().strip('"\'')
                    if not playlist_name:
                        print(f"{RED}Error: Playlist name required.{RESET}\n")
                        continue
                    
                    if not self.all_tracks:
                        print(f"{YELLOW}No tracks to publish. Discover some music first!{RESET}\n")
                        continue
                    
                    # Publish directly to Tidal
                    print(f"\n{CYAN}Publishing {len(self.all_tracks)} tracks to Tidal...{RESET}")
                    try:
                        publish_metrics = MetricsCollector()
                        publish_metrics.start_operation("Publish to Tidal")
                        
                        tracks_data = [asdict(t) for t in self.all_tracks]
                        self.engine.publish(playlist_name, tracks_data, replace=False, metrics=publish_metrics)
                        
                        publish_metrics.end_operation(success=True)
                        print(f"{GREEN}✓{RESET} Published to Tidal: \"{playlist_name}\"")
                        print(f"{DIM}Tracks in session preserved. Use /new to start fresh.{RESET}\n")
                        
                    except Exception as e:
                        if logger:
                            logger.error(f"Publish failed: {e}", exc_info=self.debug)
                        print(f"{RED}Error publishing: {e}{RESET}\n")
                    continue
                
                # Validate query
                is_valid, error_msg = validate_query(user_input)
                if not is_valid:
                    print(f"{RED}Error: {error_msg}{RESET}\n")
                    continue
                
                # Process the message
                metrics = MetricsCollector()
                metrics.start_operation("Chat Query")
                
                print(f"\n{CYAN}AI:{RESET} Searching for tracks...\n")
                
                try:
                    tracks = self.process_message(user_input, metrics)
                    
                    if tracks:
                        print(f"\n{GREEN}✓{RESET} Found {len(tracks)} tracks.")
                        print(f"{DIM}Total in session: {len(self.all_tracks)} tracks{RESET}\n")
                    else:
                        print(f"\n{YELLOW}No tracks found for that query. Try rephrasing?{RESET}\n")
                    
                    metrics.end_operation(success=True)
                    
                except Exception as e:
                    metrics.end_operation(success=False, error=str(e))
                    if logger:
                        logger.error(f"Chat query failed: {e}", exc_info=self.debug)
                    print(f"{RED}Error: {e}{RESET}\n")
                    
            except KeyboardInterrupt:
                print(f"\n\n{DIM}Interrupted. Use /quit to exit.{RESET}\n")
                continue
            except EOFError:
                print(f"\n{DIM}Ending chat session...{RESET}")
                break
        
        # Show session summary on exit
        if self.all_tracks:
            print(f"\n{BOLD}Session Summary:{RESET}")
            print(f"  Discovered: {len(self.all_tracks)} tracks")
            print(f"  Queries: {len([h for h in self.conversation_history if h['role'] == 'user'])}")
            print(f"\n{DIM}Tip: Use /publish before /quit to save your playlist.{RESET}")


def ensure_venv():
    """Ensure virtual environment exists and is activated."""
    os.makedirs(BASE_DIR, exist_ok=True)
    
    if not os.path.exists(VENV_DIR):
        logger.info("Creating virtual environment")
        print(f"{YELLOW}Initializing sandbox environment...{RESET}")
        try:
            # Use absolute paths and validate
            venv_abs_path = os.path.abspath(VENV_DIR)
            python_exe = os.path.abspath(sys.executable)
            
            subprocess.run(
                [python_exe, "-m", "venv", venv_abs_path],
                check=True,
                capture_output=True,
                timeout=300,  # 5 minute timeout
                shell=False  # Explicit: never use shell
            )
            pip_path = os.path.join(venv_abs_path, "bin", "pip")
            
            # Validate pip path exists
            if not os.path.exists(pip_path):
                raise FileNotFoundError(f"pip not found at {pip_path}")
            
            # Install runtime dependencies from requirements.txt if available
            script_dir = os.path.dirname(os.path.abspath(__file__))
            requirements_file = os.path.join(script_dir, "requirements.txt")
            if os.path.exists(requirements_file):
                logger.info("Installing dependencies from requirements.txt")
                subprocess.run(
                    [pip_path, "install", "-r", os.path.abspath(requirements_file)],
                    check=True,
                    capture_output=True,
                    timeout=600,  # 10 minute timeout
                    shell=False  # Explicit: never use shell
                )
            else:
                # Fallback to hardcoded dependencies
                runtime_deps = ["google-genai", "tidalapi"]
                subprocess.run(
                    [pip_path, "install"] + runtime_deps,
                    check=True,
                    capture_output=True,
                    timeout=600,
                    shell=False  # Explicit: never use shell
                )
            
            # Install test dependencies if requirements-test.txt exists
            test_requirements = os.path.join(BASE_DIR, "requirements-test.txt")
            if os.path.exists(test_requirements):
                logger.info("Installing test dependencies")
                subprocess.run(
                    [pip_path, "install", "-r", os.path.abspath(test_requirements)],
                    check=True,
                    capture_output=True,
                    timeout=600,
                    shell=False  # Explicit: never use shell
                )
        except subprocess.TimeoutExpired:
            logger.error("Venv creation timed out")
            print(f"{RED}Error: Environment setup timed out.{RESET}")
            sys.exit(1)
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to create venv: {e}")
            print(f"{RED}Error: Failed to initialize environment.{RESET}")
            sys.exit(1)
        except FileNotFoundError as e:
            logger.error(f"Required file not found: {e}")
            print(f"{RED}Error: {e}{RESET}")
            sys.exit(1)
    
    # Re-execute in venv if not already there
    if sys.prefix != VENV_DIR:
        python_path = os.path.join(os.path.abspath(VENV_DIR), "bin", "python")
        script_path = os.path.abspath(__file__)
        # Validate paths exist
        if not os.path.exists(python_path):
            logger.error(f"Python not found at {python_path}")
            print(f"{RED}Error: Virtual environment Python not found.{RESET}")
            sys.exit(1)
        if not os.path.exists(script_path):
            logger.error(f"Script not found at {script_path}")
            print(f"{RED}Error: Main script not found.{RESET}")
            sys.exit(1)
        try:
            subprocess.run(
                [python_path, script_path] + sys.argv[1:], 
                check=True, 
                timeout=3600,
                shell=False  # Explicit: never use shell
            )
            sys.exit(0)
        except subprocess.TimeoutExpired:
            logger.error("Script execution timed out")
            print(f"{RED}Error: Script execution timed out.{RESET}")
            sys.exit(1)
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to execute in venv: {e}")
            sys.exit(e.returncode)

def load_or_create_config() -> dict:
    """Load configuration or create new one."""
    if not os.path.exists(CONFIG_FILE):
        print(f"{HR}\n{BOLD}INITIAL SETUP{RESET}\n{HR}")
        # Use getpass for secure input (doesn't echo to terminal)
        import getpass
        api_key = getpass.getpass(f"{CYAN}Enter Gemini API Key:{RESET} ").strip()
        
        if not api_key:
            print(f"{RED}Error: API key is required.{RESET}")
            sys.exit(1)
        
        # Store API key in Keychain
        if sys.platform == "darwin":
            if not store_secret("GEMINI_API_KEY", api_key):
                print(f"{YELLOW}Warning: Failed to store API key in Keychain. Continuing anyway...{RESET}")
        else:
            print(f"{YELLOW}Warning: Keychain not available on this platform.{RESET}")
        
        config = {
            "GEMINI": {},  # API_KEY no longer stored here
            "TIDAL": {}  # SESSION_DATA no longer stored here
        }
        
        try:
            os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=2)
            # Set secure permissions on config file
            set_config_permissions(CONFIG_FILE)
            logger.info("Created new configuration file")
        except Exception as e:
            handle_error_with_exit(e, "Failed to save configuration", logger)
    
    try:
        # Use safe JSON loading with size limits
        config = safe_json_load(CONFIG_FILE, max_size_bytes=MAX_CONFIG_SIZE_BYTES)
        
        # Migrate secrets from config.json to Keychain if they exist
        if sys.platform == "darwin":
            migrate_secrets_from_config(config)
            # Clean up secrets from config after migration
            config_updated = False
            if "GEMINI" in config and "API_KEY" in config["GEMINI"]:
                config["GEMINI"].pop("API_KEY", None)
                config_updated = True
            if "TIDAL" in config and "SESSION_DATA" in config["TIDAL"]:
                session_data = config["TIDAL"].get("SESSION_DATA", {})
                if session_data and isinstance(session_data, dict) and session_data.get("access_token"):
                    config["TIDAL"]["SESSION_DATA"] = {}
                    config_updated = True
            # Save cleaned config if it was updated
            if config_updated:
                try:
                    with open(CONFIG_FILE, 'w') as f:
                        json.dump(config, f, indent=2)
                    set_config_permissions(CONFIG_FILE)
                    logger.info("Cleaned secrets from config.json after migration")
                except Exception as e:
                    logger.warning(f"Failed to save cleaned config: {e}")
        
        # Load secrets from Keychain into config dict for validation/use
        if sys.platform == "darwin":
            api_key = get_secret("GEMINI_API_KEY")
            if api_key:
                config.setdefault("GEMINI", {})["API_KEY"] = api_key
            else:
                # Fallback: check if still in config (for non-migrated configs)
                if "GEMINI" not in config or "API_KEY" not in config.get("GEMINI", {}):
                    logger.warning("Gemini API key not found in Keychain or config")
                    print(f"\n{RED}Error: Gemini API key not found.{RESET}")
                    print(f"{CYAN}Add your API key with:{RESET}")
                    print(f"  {BOLD}playlist-builder keychain set GEMINI_API_KEY{RESET}")
                    print(f"\n{DIM}Get your API key from: https://makersuite.google.com/app/apikey{RESET}\n")
                    sys.exit(1)
            
            tidal_session = get_tidal_session()
            if tidal_session:
                config.setdefault("TIDAL", {})["SESSION_DATA"] = tidal_session
            else:
                # Fallback: check if still in config
                if "TIDAL" not in config or not config.get("TIDAL", {}).get("SESSION_DATA"):
                    config.setdefault("TIDAL", {})["SESSION_DATA"] = {}
        else:
            # Non-macOS: API key must be in config file
            if "GEMINI" not in config or "API_KEY" not in config.get("GEMINI", {}):
                logger.warning("Gemini API key not found in config")
                print(f"\n{RED}Error: Gemini API key not found.{RESET}")
                print(f"{CYAN}Add your API key to:{RESET} {CONFIG_FILE}")
                print(f"\n{DIM}Get your API key from: https://makersuite.google.com/app/apikey{RESET}\n")
                sys.exit(1)
        
        is_valid, error_msg = validate_config(config)
        if not is_valid:
            logger.error(f"Invalid config: {error_msg}")
            print(f"{RED}Error: {error_msg}{RESET}")
            sys.exit(1)
        
        return config
        
    except json.JSONDecodeError as e:
        handle_error_with_exit(e, "Configuration file is corrupted", logger)
    except Exception as e:
        handle_error_with_exit(e, "Failed to load configuration", logger)

def main():
    """Main entry point."""
    global logger
    
    # Help guard
    if len(sys.argv) == 1 or sys.argv[1] in ["-h", "--help"]:
        print_help()
        sys.exit(0)
    
    # Parse arguments
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("-d", "--debug", action="store_true", help="Enable debug logging")
    parser.add_argument(
        "-l", "--limit", 
        type=int, 
        default=DEFAULT_LIMIT, 
        help="Maximum tracks to return (1-100)"
    )
    parser.add_argument(
        "-m", "--model",
        type=str,
        default=GEMINI_MODEL,
        help=f"Gemini model to use (default: {GEMINI_MODEL}). "
             f"Options: {', '.join(AVAILABLE_MODELS.keys())}"
    )
    
    subparsers = parser.add_subparsers(dest="cmd", help="Command")
    
    # Chat command - interactive conversational session
    chat_parser = subparsers.add_parser("chat", help="Interactive conversational discovery")
    chat_parser.add_argument("-d", "--debug", action="store_true", help="Enable debug logging")
    chat_parser.add_argument(
        "-l", "--limit",
        type=int,
        default=CHAT_DEFAULT_LIMIT,
        help=f"Max tracks per query (default: {CHAT_DEFAULT_LIMIT})"
    )
    chat_parser.add_argument(
        "-m", "--model",
        type=str,
        default=GEMINI_MODEL,
        help=f"Gemini model to use (default: {GEMINI_MODEL})"
    )
    
    query_parser = subparsers.add_parser("query", help="Query AI for tracks")
    query_parser.add_argument("query", help="Query to ask the AI")
    query_parser.add_argument("-d", "--debug", action="store_true", help="Enable debug logging")
    query_parser.add_argument(
        "-l", "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help="Maximum tracks to return (1-100)"
    )
    query_parser.add_argument(
        "-m", "--model",
        type=str,
        default=GEMINI_MODEL,
        help=f"Gemini model to use (default: {GEMINI_MODEL})"
    )
    
    publish_parser = subparsers.add_parser("publish", help="Publish playlist")
    publish_parser.add_argument("provider", choices=["tidal"], help="Music provider")
    publish_parser.add_argument("--name", required=True, help="Playlist name")
    publish_parser.add_argument("--replace", action="store_true", help="Replace existing playlist")
    publish_parser.add_argument("-d", "--debug", action="store_true", help="Enable debug logging")
    
    # Keychain management commands (macOS only)
    keychain_parser = subparsers.add_parser("keychain", help="Manage secrets in macOS Keychain")
    keychain_subparsers = keychain_parser.add_subparsers(dest="keychain_cmd", help="Keychain command")
    
    keychain_set = keychain_subparsers.add_parser("set", help="Store a secret in Keychain")
    keychain_set.add_argument("key", help="Secret key name (e.g., GEMINI_API_KEY)")
    keychain_set.add_argument("value", nargs='?', help="Secret value (will prompt if not provided)")
    
    keychain_get = keychain_subparsers.add_parser("get", help="Retrieve a secret from Keychain")
    keychain_get.add_argument("key", help="Secret key name")
    
    keychain_delete = keychain_subparsers.add_parser("delete", help="Delete a secret from Keychain")
    keychain_delete.add_argument("key", help="Secret key name")
    
    keychain_subparsers.add_parser("list", help="List stored secret keys (not values)")
    
    subparsers.add_parser("reset", help="Reset configuration")
    subparsers.add_parser("rebuild", help="Rebuild virtual environment")
    
    args = parser.parse_args()
    
    # Initialize logging
    logger = setup_logging(args.debug)
    
    # Validate limit
    if args.limit < 1 or args.limit > 100:
        logger.error(f"Invalid limit: {args.limit} (must be 1-100)")
        print(f"{RED}Error: Limit must be between 1 and 100.{RESET}")
        sys.exit(1)
    
    # Resolve and validate model
    model = args.model
    if model in AVAILABLE_MODELS:
        model = AVAILABLE_MODELS[model]
    elif model not in AVAILABLE_MODELS.values():
        # Check if it's a valid full model name (for backward compatibility)
        valid_models = list(AVAILABLE_MODELS.values())
        if not any(model.startswith(m.split("-")[0]) for m in valid_models):
            logger.warning(f"Unknown model '{args.model}', using default: {GEMINI_MODEL}")
            print(f"{YELLOW}Warning: Unknown model '{args.model}', using default: {GEMINI_MODEL}{RESET}")
            model = GEMINI_MODEL
        else:
            logger.info(f"Using custom model: {model}")
    
    # Handle keychain commands
    if args.cmd == "keychain":
        if sys.platform != "darwin":
            print(f"{RED}Error: Keychain commands are only available on macOS.{RESET}")
            sys.exit(1)
        
        if not args.keychain_cmd:
            print(f"{RED}Error: Please specify a keychain command (set, get, delete, list).{RESET}")
            print(f"{DIM}Usage: playlist-builder keychain <command>{RESET}")
            sys.exit(1)
        
        if args.keychain_cmd == "set":
            value = args.value
            if not value:
                # Prompt for value if not provided
                import getpass
                value = getpass.getpass(f"Enter value for {args.key}: ")
            
            if not value:
                print(f"{RED}Error: No value provided.{RESET}")
                sys.exit(1)
            
            if store_secret(args.key, value):
                print(f"{GREEN}✓{RESET} Secret '{args.key}' stored in Keychain")
                logger.info(f"Stored secret: {args.key}")
            else:
                print(f"{RED}Error: Failed to store secret in Keychain.{RESET}")
                sys.exit(1)
        
        elif args.keychain_cmd == "get":
            value = get_secret(args.key)
            if value:
                print(f"{GREEN}✓{RESET} Secret '{args.key}': {value}")
            else:
                print(f"{YELLOW}Secret '{args.key}' not found in Keychain.{RESET}")
                sys.exit(1)
        
        elif args.keychain_cmd == "delete":
            if delete_secret(args.key):
                print(f"{GREEN}✓{RESET} Secret '{args.key}' deleted from Keychain")
                logger.info(f"Deleted secret: {args.key}")
            else:
                print(f"{YELLOW}Secret '{args.key}' not found or could not be deleted.{RESET}")
                sys.exit(1)
        
        elif args.keychain_cmd == "list":
            # List known secret keys
            known_keys = ["GEMINI_API_KEY"]
            print(f"{CYAN}{BOLD}Keychain Secrets:{RESET}")
            for key in known_keys:
                if get_secret(key):
                    print(f"  {GREEN}✓{RESET} {key} (stored)")
                else:
                    print(f"  {DIM}○{RESET} {key} (not stored)")
            
            # Check for Tidal session
            if get_tidal_session():
                print(f"  {GREEN}✓{RESET} TIDAL_SESSION (stored)")
            else:
                print(f"  {DIM}○{RESET} TIDAL_SESSION (not stored)")
        
        sys.exit(0)
    
    # Handle reset command
    if args.cmd == "reset":
        try:
            # Clear Keychain secrets
            if sys.platform == "darwin":
                delete_secret("GEMINI_API_KEY")
                delete_secret("tidal_session", account="tidal")
                logger.info("Cleared secrets from Keychain")
            
            # Remove config and cache files
            for f in [CONFIG_FILE, CACHE_FILE]:
                if os.path.exists(f):
                    os.remove(f)
                    logger.info(f"Removed {f}")
            print(f"{GREEN}✔ Soft Reset Complete.{RESET}")
        except Exception as e:
            handle_error_with_exit(e, f"Reset failed: {e}", logger, exit_code=0)
        sys.exit(0)
    
    # Handle rebuild command
    if args.cmd == "rebuild":
        try:
            if os.path.exists(VENV_DIR):
                shutil.rmtree(VENV_DIR)
                logger.info("Removed virtual environment")
            print(f"{GREEN}✔ Hard Rebuild Triggered.{RESET}")
            print(f"{YELLOW}Virtual environment will be recreated with test dependencies on next command.{RESET}")
        except Exception as e:
            handle_error_with_exit(e, f"Rebuild failed: {e}", logger, exit_code=0)
        sys.exit(0)
    
    # Ensure venv exists
    ensure_venv()
    
    # Load configuration
    config = load_or_create_config()
    
    # Import engine after venv is ready
    try:
        from tidal_engine import TidalProvider
    except ImportError as e:
        logger.error(f"Failed to import TidalProvider: {e}")
        print(f"{RED}Error: Failed to import tidal engine. Try 'rebuild' command.{RESET}")
        sys.exit(1)
    
    engine = TidalProvider(config, CONFIG_FILE, args.debug)
    
    # Execute commands
    if args.cmd == "chat":
        # Authenticate with Tidal first
        print(f"\n{CYAN}Initializing chat session...{RESET}")
        try:
            with Spinner("Authenticating with Tidal..."):
                engine.authenticate()
            
            # Create and run chat session
            chat_session = ChatSession(
                config=config,
                engine=engine,
                model=model,
                limit=args.limit,
                debug=args.debug
            )
            chat_session.run_interactive()
            
        except Exception as e:
            logger.error(f"Chat session failed: {e}", exc_info=args.debug)
            print(f"{RED}Error: {e}{RESET}")
            sys.exit(1)
    
    elif args.cmd == "query":
        # Validate query input
        is_valid, error_msg = validate_query(args.query)
        if not is_valid:
            print(f"{RED}Error: {error_msg}{RESET}")
            sys.exit(1)
        
        metrics = MetricsCollector()
        op_metrics = metrics.start_operation("Query & Discovery")
        
        print(f"\n{HR}\n{BOLD}AI DISCOVERY:{RESET} {CYAN}{args.query}{RESET}")
        print(f"{BOLD}MODEL:{RESET} {CYAN}{model}{RESET}\n{HR}")
        try:
            with Spinner("Authenticating with Tidal..."):
                engine.authenticate()
            
            curator = MusicCurator(config, model=model, debug=args.debug)
            tracks = curator.curate(args.query, args.limit, engine, metrics)
            
            if tracks:
                try:
                    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
                    with open(CACHE_FILE, 'w') as f:
                        json.dump([asdict(t) for t in tracks], f, indent=2)
                    logger.info(f"Cached {len(tracks)} tracks")
                    print(f"\n{GREEN}{BOLD}✔ AI Query Cached.{RESET}")
                except Exception as e:
                    handle_warning("Failed to cache results", logger, str(e))
            
            metrics.end_operation(success=True)
            metrics.print_summary()
            
        except Exception as e:
            metrics.end_operation(success=False, error=str(e))
            logger.error(f"Query failed: {e}", exc_info=args.debug)
            print(f"{RED}Error: Query failed: {e}{RESET}")
            metrics.print_summary()
            sys.exit(1)
            
    elif args.cmd == "publish":
        if not os.path.exists(CACHE_FILE):
            print(f"{RED}Error: No tracks to publish. Run 'chat' or 'query' first.{RESET}")
            sys.exit(1)
        
        # Validate playlist name
        if not args.name or not isinstance(args.name, str):
            print(f"{RED}Error: Playlist name is required.{RESET}")
            sys.exit(1)
        if len(args.name) > 100:
            print(f"{RED}Error: Playlist name too long (max 100 characters).{RESET}")
            sys.exit(1)
        # Sanitize playlist name (remove dangerous characters)
        sanitized_name = re.sub(r'[<>:"/\\|?*]', '', args.name).strip()
        if not sanitized_name:
            print(f"{RED}Error: Invalid playlist name.{RESET}")
            sys.exit(1)
        
        # Use Tidal engine
        publish_engine = engine
        op_name = "Publish to Tidal"
        
        metrics = MetricsCollector()
        op_metrics = metrics.start_operation(op_name)
        
        try:
            # Cache file stores tracks as a list, not dict, so we need special handling
            if not os.path.exists(CACHE_FILE):
                raise FileNotFoundError("Cache file not found")
            
            # Validate file size
            file_size = os.path.getsize(CACHE_FILE)
            if file_size > MAX_JSON_SIZE_BYTES:
                raise ValueError(f"Cache file too large: {file_size} bytes")
            
            validate_file_path(CACHE_FILE)
            
            with open(CACHE_FILE, 'r') as f:
                tracks = json.load(f)
            # Validate tracks data
            if not isinstance(tracks, list):
                raise ValueError("Cache file does not contain a list of tracks")
            publish_engine.publish(sanitized_name, tracks, args.replace, metrics)
            metrics.end_operation(success=True)
            metrics.print_summary()
        except json.JSONDecodeError as e:
            metrics.end_operation(success=False, error=f"Invalid cache file: {e}")
            metrics.print_summary()
            handle_error_with_exit(e, "Cache file is corrupted", logger, debug=args.debug)
        except Exception as e:
            metrics.end_operation(success=False, error=str(e))
            metrics.print_summary()
            handle_error_with_exit(e, f"Publish failed: {e}", logger, debug=args.debug)

if __name__ == "__main__":
    main()
