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
Pytest configuration and shared fixtures.

CRITICAL: This file ensures all tests run safely without touching:
- Real macOS Keychain (API keys, Tidal sessions)
- Real config directory (~/.config/playlist-builder)
"""
import json
import os
import tempfile
import shutil
from unittest.mock import Mock, MagicMock, patch
import pytest

# Add parent directory to path for imports
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Initialize logger for tests (main.py uses a global logger)
import logging
logging.basicConfig(level=logging.WARNING)  # Suppress most logging during tests


# =============================================================================
# CRITICAL SAFETY FIXTURES - Prevent tests from touching real resources
# =============================================================================

@pytest.fixture(autouse=True)
def mock_keychain_operations():
    """
    CRITICAL: Auto-mock all keychain operations to prevent tests from:
    - Deleting real API keys
    - Reading/writing real secrets
    - Corrupting production Tidal sessions
    
    This fixture runs automatically for ALL tests.
    """
    # In-memory store for test secrets
    test_keychain = {}
    
    def mock_store_secret(key, value, account="default"):
        test_keychain[f"{account}:{key}"] = value
        return True
    
    def mock_get_secret(key, account="default"):
        return test_keychain.get(f"{account}:{key}")
    
    def mock_delete_secret(key, account="default"):
        full_key = f"{account}:{key}"
        if full_key in test_keychain:
            del test_keychain[full_key]
            return True
        return False
    
    def mock_store_tidal_session(session_data):
        test_keychain["tidal:tidal_session"] = json.dumps(session_data)
        return True
    
    def mock_get_tidal_session():
        data = test_keychain.get("tidal:tidal_session")
        if data:
            return json.loads(data)
        return None
    
    def mock_migrate_secrets(config):
        return False
    
    def mock_store_spotify_session(session_data):
        test_keychain["spotify:spotify_session"] = json.dumps(session_data)
        return True
    
    def mock_get_spotify_session():
        data = test_keychain.get("spotify:spotify_session")
        if data:
            return json.loads(data)
        return None
    
    with patch.multiple(
        'keychain_utils',
        store_secret=mock_store_secret,
        get_secret=mock_get_secret,
        delete_secret=mock_delete_secret,
        store_tidal_session=mock_store_tidal_session,
        get_tidal_session=mock_get_tidal_session,
        store_spotify_session=mock_store_spotify_session,
        get_spotify_session=mock_get_spotify_session,
        migrate_secrets_from_config=mock_migrate_secrets,
    ):
        # Also patch in main module if it imports these directly
        with patch.multiple(
            'main',
            store_secret=mock_store_secret,
            get_secret=mock_get_secret,
            delete_secret=mock_delete_secret,
            store_tidal_session=mock_store_tidal_session,
            get_tidal_session=mock_get_tidal_session,
            migrate_secrets_from_config=mock_migrate_secrets,
            create=True,
        ):
            yield test_keychain


@pytest.fixture(autouse=True)
def isolate_config_directory(tmp_path, monkeypatch):
    """
    CRITICAL: Redirect all config directory access to a temp directory.
    This prevents tests from reading/writing to ~/.config/playlist-builder.
    """
    # Create isolated test config directory
    test_config_dir = tmp_path / "playlist-builder-test"
    test_config_dir.mkdir(parents=True, exist_ok=True)
    
    # Override constants module paths
    test_base_dir = str(test_config_dir)
    test_venv_dir = str(test_config_dir / ".venv")
    test_config_file = str(test_config_dir / "config.json")
    test_cache_file = str(test_config_dir / "last_query.json")
    test_log_file = str(test_config_dir / "playlist-builder.log")
    
    # Patch constants module
    monkeypatch.setattr('constants.BASE_DIR', test_base_dir)
    monkeypatch.setattr('constants.VENV_DIR', test_venv_dir)
    monkeypatch.setattr('constants.CONFIG_FILE', test_config_file)
    monkeypatch.setattr('constants.CACHE_FILE', test_cache_file)
    monkeypatch.setattr('constants.LOG_FILE', test_log_file)
    
    yield {
        'base_dir': test_base_dir,
        'venv_dir': test_venv_dir,
        'config_file': test_config_file,
        'cache_file': test_cache_file,
        'log_file': test_log_file,
    }


# =============================================================================
# STANDARD TEST FIXTURES
# =============================================================================

@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def temp_config_file(temp_dir):
    """Create a temporary config file."""
    config_path = os.path.join(temp_dir, "config.json")
    config = {
        "GEMINI": {
            "API_KEY": "test_api_key_1234567890"
        },
        "TIDAL": {
            "SESSION_DATA": {}
        }
    }
    with open(config_path, 'w') as f:
        json.dump(config, f)
    return config_path


@pytest.fixture
def sample_config():
    """Return a sample configuration dictionary."""
    return {
        "GEMINI": {
            "API_KEY": "test_api_key_1234567890"
        },
        "TIDAL": {
            "SESSION_DATA": {
                "token_type": "Bearer",
                "access_token": "test_access_token",
                "refresh_token": "test_refresh_token"
            }
        }
    }


@pytest.fixture
def mock_gemini_client():
    """Mock Gemini API client."""
    with patch('google.genai.Client') as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        # Mock response
        mock_response = MagicMock()
        mock_response.text = '[{"title": "Test Track", "artist": "Test Artist"}]'
        mock_client.models.generate_content.return_value = mock_response
        
        yield mock_client


@pytest.fixture
def mock_tidal_session():
    """Mock Tidal API session."""
    mock_session = MagicMock()
    mock_session.check_login.return_value = True
    mock_session.token_type = "Bearer"
    mock_session.access_token = "test_access_token"
    mock_session.refresh_token = "test_refresh_token"
    
    # Mock search results
    mock_track = MagicMock()
    mock_track.id = "12345"
    mock_track.name = "Test Track"
    mock_track.audio_quality = "HI_RES"
    mock_track.isrc = "USRC12345678"
    
    mock_artist = MagicMock()
    mock_artist.name = "Test Artist"
    mock_track.artist = mock_artist
    
    mock_album = MagicMock()
    mock_album.name = "Test Album"
    mock_release_date = MagicMock()
    mock_release_date.year = 2020
    mock_album.release_date = mock_release_date
    mock_track.album = mock_album
    
    mock_session.search.return_value = {
        'tracks': [mock_track]
    }
    
    # Mock playlist operations
    mock_playlist = MagicMock()
    mock_playlist.name = "Test Playlist"
    mock_playlist.items.return_value = []
    mock_user = MagicMock()
    mock_user.playlists.return_value = [mock_playlist]
    mock_user.create_playlist.return_value = mock_playlist
    mock_session.user = mock_user
    
    return mock_session


@pytest.fixture
def sample_track_data():
    """Sample track data for testing."""
    return {
        "title": "Test Track",
        "artist": "Test Artist",
        "album": "Test Album",
        "isrc": "USRC12345678",
        "tidal_id": "12345",
        "score": 0.95,
        "year": "2020",
        "quality": "HI_RES",
        "latency_ms": 150.5
    }


@pytest.fixture
def sample_tracks_list(sample_track_data):
    """List of sample tracks."""
    return [sample_track_data.copy()]


@pytest.fixture
def mock_spotify_client():
    """Mock Spotify API client."""
    mock_client = MagicMock()
    
    # Mock search results
    mock_track = {
        'id': '12345',
        'name': 'Test Track',
        'uri': 'spotify:track:12345',
        'artists': [{'name': 'Test Artist'}],
        'album': {
            'name': 'Test Album',
            'release_date': '2020-01-01'
        }
    }
    
    mock_client.search.return_value = {
        'tracks': {'items': [mock_track]}
    }
    
    # Mock user info
    mock_client.current_user.return_value = {'id': 'test_user_id'}
    
    # Mock playlist operations
    mock_client.current_user_playlists.return_value = {'items': []}
    mock_client.user_playlist_create.return_value = {
        'id': 'new_playlist_id',
        'name': 'Test Playlist'
    }
    mock_client.playlist_items.return_value = {'items': []}
    
    return mock_client


@pytest.fixture
def sample_spotify_tracks():
    """Sample tracks with spotify_id for testing."""
    return [
        {
            "title": "Test Track",
            "artist": "Test Artist",
            "album": "Test Album",
            "spotify_id": "12345",
            "score": 0.95
        }
    ]
