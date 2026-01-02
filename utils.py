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
Utility functions for playlist-builder.
"""
import os
import re
import sys
import time
import logging
import threading
from typing import Callable, TypeVar, Optional, Any, Tuple
from functools import wraps
from collections import deque
from datetime import datetime, timedelta

from constants import (
    MAX_RETRIES, RETRY_DELAY_BASE, BLUE, BOLD, RESET, MAGENTA, CYAN, GREEN, YELLOW, RED, DIM, 
    HIGH_CONFIDENCE_SCORE, MAX_QUERY_LENGTH, API_TIMEOUT_SECONDS, 
    RATE_LIMIT_REQUESTS_PER_MINUTE, CONFIG_FILE_PERMISSIONS,
    MAX_JSON_SIZE_BYTES, MAX_CONFIG_SIZE_BYTES
)

T = TypeVar('T')

def setup_logging(debug: bool = False) -> logging.Logger:
    """Configure and return logger."""
    import os
    from constants import LOG_FILE, BASE_DIR
    
    os.makedirs(BASE_DIR, exist_ok=True)
    
    level = logging.DEBUG if debug else logging.INFO
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger('playlist_builder')
    logger.setLevel(level)
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # File handler
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Console handler (only errors/warnings)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger

def retry_with_backoff(
    max_retries: int = MAX_RETRIES,
    base_delay: float = RETRY_DELAY_BASE,
    exceptions: tuple = (Exception,)
) -> Callable:
    """
    Decorator to retry function calls with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds for exponential backoff
        exceptions: Tuple of exceptions to catch and retry on
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        time.sleep(delay)
                        continue
                    raise
            raise last_exception or Exception("Retry failed")
        return wrapper
    return decorator

def validate_config(config: dict) -> tuple[bool, Optional[str]]:
    """
    Validate configuration structure.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(config, dict):
        return False, "Config must be a dictionary"
    
    if 'GEMINI' not in config:
        return False, "Missing 'GEMINI' section in config"
    
    if 'API_KEY' not in config['GEMINI']:
        return False, "Missing 'GEMINI.API_KEY' in config"
    
    api_key = config['GEMINI']['API_KEY']
    if not api_key or not isinstance(api_key, str) or len(api_key) < 10:
        return False, "Invalid or missing Gemini API key"
    
    if 'TIDAL' not in config:
        config['TIDAL'] = {'SESSION_DATA': {}}
    
    return True, None


def format_track_signal(track_quality: str, track_score: float) -> Tuple[str, int]:
    """
    Format track quality and score for display.
    
    Args:
        track_quality: Track audio quality string
        track_score: Track match score
        
    Returns:
        Tuple of (formatted signal text, visible length)
    """
    q_tag = f"{MAGENTA}H{RESET}" if "HI_RES" in track_quality else f"{CYAN}L{RESET}"
    s_color = GREEN if track_score >= HIGH_CONFIDENCE_SCORE else YELLOW
    score_str = f"{track_score:.2f}"
    # Build signal text with proper padding (10 visible chars)
    # Visible format: "H 1.00" or "L 1.00" (6 chars), pad to 10 chars
    signal_visible_len = len(f"{'H' if 'HI_RES' in track_quality else 'L'} {score_str}")
    signal_text = f"{q_tag} {s_color}{score_str}{RESET}"
    signal_padded = signal_text + " " * (10 - signal_visible_len)
    return signal_padded, signal_visible_len


def print_track_row(track_title: str, track_artist: str, track_album: str, 
                    track_isrc: str, track_year: str, signal_text: str) -> None:
    """
    Print a formatted track row in the discovery table.
    
    Args:
        track_title: Track title (max 33 chars)
        track_artist: Artist name (max 20 chars)
        track_album: Album name (max 18 chars)
        track_isrc: ISRC code (max 13 chars)
        track_year: Release year (max 5 chars)
        signal_text: Formatted signal text
    """
    import sys
    print(f"{BLUE}│{RESET} {track_title[:33]:<33}{BLUE}│{RESET} {track_artist[:20]:<20}{BLUE}│{RESET} {DIM}{track_album[:18]:<18}{RESET}{BLUE}│{RESET} {DIM}{track_isrc[:13]:<13}{RESET}{BLUE}│{RESET} {track_year:<5}{BLUE}│{RESET} {signal_text}{BLUE}│{RESET}")
    sys.stdout.flush()


def validate_query(query: str) -> tuple[bool, Optional[str]]:
    """
    Validate and sanitize user query input.
    
    Args:
        query: User input query string
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not query or not isinstance(query, str):
        return False, "Query must be a non-empty string"
    
    if len(query) > MAX_QUERY_LENGTH:
        return False, f"Query too long (max {MAX_QUERY_LENGTH} characters)"
    
    # Check for potentially dangerous patterns
    dangerous_patterns = [
        r'<script',
        r'javascript:',
        r'data:text/html',
        r'\.\./',  # Path traversal
        r'`.*`',  # Command injection patterns
        r'\$\(.*\)',  # Command substitution
    ]
    
    query_lower = query.lower()
    for pattern in dangerous_patterns:
        if re.search(pattern, query_lower):
            return False, "Query contains potentially unsafe content"
    
    return True, None


def set_config_permissions(file_path: str) -> None:
    """
    Set secure permissions on configuration file.
    
    Args:
        file_path: Path to configuration file
    """
    try:
        os.chmod(file_path, CONFIG_FILE_PERMISSIONS)
    except (OSError, PermissionError) as e:
        logging.getLogger('playlist_builder').warning(f"Failed to set config file permissions: {e}")


class RateLimiter:
    """Simple token bucket rate limiter."""
    
    def __init__(self, max_requests: int = RATE_LIMIT_REQUESTS_PER_MINUTE, window_seconds: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum requests allowed in time window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: deque = deque()
        self.lock = threading.Lock()
    
    def acquire(self) -> bool:
        """
        Try to acquire a token for a request.
        
        Returns:
            True if request allowed, False if rate limited
        """
        with self.lock:
            now = datetime.now()
            # Remove old requests outside the window
            while self.requests and (now - self.requests[0]).total_seconds() > self.window_seconds:
                self.requests.popleft()
            
            if len(self.requests) >= self.max_requests:
                return False
            
            self.requests.append(now)
            return True
    
    def wait_if_needed(self) -> None:
        """Wait if rate limited, then acquire token."""
        while not self.acquire():
            # Calculate wait time until oldest request expires
            with self.lock:
                if self.requests:
                    oldest = self.requests[0]
                    wait_time = self.window_seconds - (datetime.now() - oldest).total_seconds()
                    if wait_time > 0:
                        time.sleep(min(wait_time, 1.0))  # Sleep in small increments
                    else:
                        # Oldest request expired, remove it and retry
                        if self.requests:
                            self.requests.popleft()
                else:
                    # No requests, should be able to acquire
                    break


# Global rate limiter instance
_rate_limiter = RateLimiter()


def rate_limit(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator to rate limit function calls.
    
    Args:
        func: Function to rate limit
        
    Returns:
        Wrapped function with rate limiting
    """
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        _rate_limiter.wait_if_needed()
        return func(*args, **kwargs)
    return wrapper


def with_timeout(timeout_seconds: float = API_TIMEOUT_SECONDS):
    """
    Decorator to add timeout to function calls.
    
    Args:
        timeout_seconds: Timeout in seconds
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            import signal
            
            def timeout_handler(signum: int, frame: Any) -> None:
                raise TimeoutError(f"Operation timed out after {timeout_seconds} seconds")
            
            # Set signal handler (Unix only)
            if hasattr(signal, 'SIGALRM'):
                old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(int(timeout_seconds))
                try:
                    result = func(*args, **kwargs)
                finally:
                    signal.alarm(0)
                    signal.signal(signal.SIGALRM, old_handler)
                return result
            else:
                # Windows or no signal support - just call function
                # Note: For Windows, would need threading.Timer approach
                return func(*args, **kwargs)
        return wrapper
    return decorator


def safe_json_load(file_path: str, max_size_bytes: int = MAX_JSON_SIZE_BYTES) -> dict:
    """
    Safely load JSON file with size validation.
    
    Args:
        file_path: Path to JSON file
        max_size_bytes: Maximum allowed file size in bytes
        
    Returns:
        Parsed JSON data as dictionary
        
    Raises:
        ValueError: If file is too large or invalid JSON
        FileNotFoundError: If file doesn't exist
    """
    import json
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Check file size before loading
    file_size = os.path.getsize(file_path)
    if file_size > max_size_bytes:
        raise ValueError(
            f"File too large: {file_size} bytes (max {max_size_bytes} bytes)"
        )
    
    # Validate path (no symlinks, no traversal)
    validate_file_path(file_path)
    
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        if not isinstance(data, dict):
            raise ValueError("JSON file must contain an object")
        
        return data
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")


def validate_file_path(file_path: str, allow_symlinks: bool = False) -> None:
    """
    Validate file path for security issues.
    
    Args:
        file_path: Path to validate
        allow_symlinks: Whether to allow symlinks (default: False)
        
    Raises:
        ValueError: If path is insecure
    """
    # Convert to absolute path
    abs_path = os.path.abspath(file_path)
    
    # Check for symlinks
    if not allow_symlinks and os.path.islink(file_path):
        raise ValueError("Symlinks are not allowed")
    
    # Check for path traversal attempts
    # Ensure the resolved path is within expected directories
    # (This is a basic check - more sophisticated checks may be needed)
    if ".." in file_path:
        raise ValueError("Path traversal detected")
    
    # Check for null bytes (directory traversal attempt)
    if "\x00" in file_path:
        raise ValueError("Null byte in path")
    
    # Validate path doesn't contain dangerous patterns
    dangerous_patterns = [
        r'/etc/',
        r'/proc/',
        r'/sys/',
        r'C:\\Windows\\',
        r'C:\\Program Files\\',
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, abs_path, re.IGNORECASE):
            raise ValueError(f"Access to {abs_path} is not allowed")


def handle_error_with_exit(
    error: Exception,
    message: str,
    logger: Optional[logging.Logger] = None,
    exit_code: int = 1,
    debug: bool = False
) -> None:
    """
    Common error handling pattern: log, print, and exit.
    
    Args:
        error: The exception that occurred
        message: User-friendly error message
        logger: Optional logger instance
        exit_code: Exit code to use (default: 1)
        debug: Whether to include traceback in logging
    """
    if logger:
        logger.error(f"{message}: {error}", exc_info=debug)
    print(f"{RED}Error: {message}{RESET}")
    sys.exit(exit_code)


def handle_error_with_raise(
    error: Exception,
    message: str,
    logger: Optional[logging.Logger] = None,
    debug: bool = False
) -> None:
    """
    Common error handling pattern: log, print, and raise.
    
    Args:
        error: The exception that occurred
        message: User-friendly error message
        logger: Optional logger instance
        debug: Whether to include traceback in logging
        
    Raises:
        The original exception (re-raised)
    """
    if logger:
        logger.error(f"{message}: {error}", exc_info=debug)
    print(f"{RED}Error: {message}{RESET}")
    raise


def handle_warning(
    message: str,
    logger: Optional[logging.Logger] = None,
    details: Optional[str] = None
) -> None:
    """
    Common warning pattern: log and print warning.
    
    Args:
        message: Warning message
        logger: Optional logger instance
        details: Optional detailed message for logging
    """
    if logger:
        if details:
            logger.warning(f"{message}: {details}")
        else:
            logger.warning(message)
    print(f"{YELLOW}Warning: {message}{RESET}")

