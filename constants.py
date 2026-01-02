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
Shared constants and utilities for playlist-builder.
"""
import os
import sys
from dataclasses import dataclass
from enum import Enum

# --- PATHS ---
BASE_DIR = os.path.expanduser("~/.config/playlist-builder")
VENV_DIR = os.path.join(BASE_DIR, ".venv")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
CACHE_FILE = os.path.join(BASE_DIR, "last_search.json")
LOG_FILE = os.path.join(BASE_DIR, "playlist-builder.log")

# --- ANSI COLOR CODES ---
BOLD = "\033[1m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
RESET = "\033[0m"
DIM = "\033[2m"

# --- PYTHON VERSION CHECK ---
MIN_PYTHON_VERSION = (3, 12)
if sys.version_info < MIN_PYTHON_VERSION:
    sys.exit(f"Error: Python {MIN_PYTHON_VERSION[0]}.{MIN_PYTHON_VERSION[1]}+ required. Found: {sys.version}")

# --- CONFIGURATION CONSTANTS ---
DEFAULT_LIMIT = 10
# Auto-detect optimal worker count, but cap at reasonable maximum
try:
    import multiprocessing
    MAX_WORKERS = min(multiprocessing.cpu_count() or 4, 16)
except (ImportError, AttributeError):
    MAX_WORKERS = 8  # Fallback
MIN_MATCH_SCORE = 0.40
HIGH_CONFIDENCE_SCORE = 0.85
HI_RES_QUALITY_WEIGHT = 10
LOSSLESS_QUALITY_WEIGHT = 5
DEFAULT_QUALITY_WEIGHT = 0

# --- API SETTINGS ---
# Gemini 3 models (default to Flash for speed and cost efficiency)
GEMINI_3_PRO = "gemini-3-pro-preview"
GEMINI_3_FLASH = "gemini-3-flash-preview"
GEMINI_3_PRO_IMAGE = "gemini-3-pro-image-preview"

# Legacy Gemini 2 models (for backward compatibility)
GEMINI_2_FLASH = "gemini-2.0-flash"
GEMINI_2_PRO = "gemini-2.0-pro"

# Default model (Gemini 3 Flash - best balance of speed, cost, and capability)
GEMINI_MODEL = GEMINI_3_FLASH

# Available models for selection
AVAILABLE_MODELS = {
    "3-pro": GEMINI_3_PRO,
    "3-flash": GEMINI_3_FLASH,
    "3-image": GEMINI_3_PRO_IMAGE,
    "2-flash": GEMINI_2_FLASH,
    "2-pro": GEMINI_2_PRO,
}

GEMINI_TEMPERATURE = 0.3
MAX_RETRIES = 3
RETRY_DELAY_BASE = 1.0  # seconds

# Thinking level for Gemini 3 (low for faster responses, high for complex reasoning)
# Default to low for music discovery use case (simple instruction following)
GEMINI_THINKING_LEVEL = "low"

# --- SECURITY & PERFORMANCE CONSTANTS ---
MAX_QUERY_LENGTH = 1000  # Maximum length for user queries
API_TIMEOUT_SECONDS = 30.0  # Default timeout for API calls
RATE_LIMIT_REQUESTS_PER_MINUTE = 60  # Rate limit for API calls
CONFIG_FILE_PERMISSIONS = 0o600  # Read/write for owner only
MAX_JSON_SIZE_BYTES = 10 * 1024 * 1024  # 10MB max for JSON files
MAX_CONFIG_SIZE_BYTES = 1 * 1024 * 1024  # 1MB max for config files

# --- UI CONSTANTS ---
HR = f"{BLUE}{'━'*120}{RESET}"

# --- STATUS ENUMS ---
class TrackResolutionStatus(str, Enum):
    """Status values for track resolution."""
    STRICT = "STRICT"
    FAILED = "FAILED"

@dataclass
class ConfigPaths:
    """Configuration file paths."""
    base_dir: str = BASE_DIR
    venv_dir: str = VENV_DIR
    config_file: str = CONFIG_FILE
    cache_file: str = CACHE_FILE
    log_file: str = LOG_FILE

