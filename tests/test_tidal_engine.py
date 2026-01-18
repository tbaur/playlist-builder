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
Tests for tidal_engine module.
"""
import json
import os
import sys
import tempfile
from unittest.mock import Mock, MagicMock, patch, mock_open
import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tidal_engine import TidalProvider
from constants import MIN_MATCH_SCORE, TrackResolutionStatus
from utils import set_config_permissions


class TestTidalProvider:
    """Test TidalProvider class."""
    
    @patch('tidal_engine.tidalapi.Session')
    def test_init(self, mock_session_class, sample_config, temp_dir):
        """Test TidalProvider initialization."""
        config_path = os.path.join(temp_dir, "config.json")
        provider = TidalProvider(sample_config, config_path, debug=False)
        
        assert provider.cfg == sample_config
        assert provider.cfg_path == config_path
        assert provider.debug is False
        assert provider.session is not None
    
    @patch('tidal_engine.tidalapi.Session')
    def test_init_debug_mode(self, mock_session_class, sample_config, temp_dir):
        """Test TidalProvider initialization with debug mode."""
        config_path = os.path.join(temp_dir, "config.json")
        provider = TidalProvider(sample_config, config_path, debug=True)
        
        assert provider.debug is True
    
    @patch('tidal_engine.tidalapi.Session')
    @patch('tidal_engine.store_tidal_session')
    @patch('tidal_engine.sys')
    def test_save_session_data(self, mock_sys, mock_store_session, mock_session_class, sample_config, temp_dir):
        """Test saving session data."""
        mock_sys.platform = "darwin"  # macOS
        mock_store_session.return_value = True
        config_path = os.path.join(temp_dir, "config.json")
        provider = TidalProvider(sample_config, config_path)
        
        provider.session.token_type = "Bearer"
        provider.session.access_token = "new_token"
        provider.session.refresh_token = "new_refresh"
        
        provider._save_session_data()
        
        # Verify store_tidal_session was called with correct data
        mock_store_session.assert_called_once()
        call_args = mock_store_session.call_args[0][0]
        assert call_args['token_type'] == "Bearer"
        assert call_args['access_token'] == "new_token"
        assert call_args['refresh_token'] == "new_refresh"
    
    @patch('tidal_engine.tidalapi.Session')
    @patch('tidal_engine.get_tidal_session')
    @patch('tidal_engine.sys')
    def test_authenticate_with_existing_session(self, mock_sys, mock_get_session, mock_session_class, sample_config, temp_dir):
        """Test authentication with existing valid session."""
        mock_sys.platform = "darwin"  # macOS
        mock_get_session.return_value = {
            'token_type': 'Bearer',
            'access_token': 'token',
            'refresh_token': 'refresh'
        }
        config_path = os.path.join(temp_dir, "config.json")
        provider = TidalProvider(sample_config, config_path)
        provider.session.check_login.return_value = True
        
        result = provider.authenticate()
        
        assert result is True
        provider.session.load_oauth_session.assert_called_once()
    
    @patch('tidal_engine.tidalapi.Session')
    def test_authenticate_requires_oauth(self, mock_session_class, sample_config, temp_dir):
        """Test authentication triggers OAuth when needed."""
        config_path = os.path.join(temp_dir, "config.json")
        provider = TidalProvider(sample_config, config_path)
        provider.session.check_login.return_value = False
        provider.session.login_oauth_simple = MagicMock()
        provider.session.token_type = "Bearer"
        provider.session.access_token = "token"
        provider.session.refresh_token = "refresh"
        
        result = provider.authenticate()
        
        assert result is True
        provider.session.login_oauth_simple.assert_called_once()
    
    @patch('tidal_engine.tidalapi.Session')
    def test_clean_text(self, mock_session_class, sample_config, temp_dir):
        """Test text cleaning function."""
        config_path = os.path.join(temp_dir, "config.json")
        provider = TidalProvider(sample_config, config_path)
        
        # Test basic cleaning
        result = provider._clean("Hello World")
        assert isinstance(result, set)
        assert "hello" in result
        assert "world" in result
        
        # Test with special characters
        result = provider._clean("Test (Remix) [2020]")
        assert "test" in result
        assert "remix" not in result  # Should be removed
        assert "2020" not in result  # Should be removed
        
        # Test empty string
        result = provider._clean("")
        assert result == set()
        
        # Test None handling
        result = provider._clean(None)
        assert result == set()
    
    @patch('tidal_engine.tidalapi.Session')
    def test_resolve_best_node_success(self, mock_session_class, sample_config, temp_dir, mock_tidal_session):
        """Test successful track resolution."""
        config_path = os.path.join(temp_dir, "config.json")
        provider = TidalProvider(sample_config, config_path)
        provider.session = mock_tidal_session
        
        result = provider._resolve_best_node("Test Track", "Test Artist")
        
        assert result['status'] == "STRICT"
        assert result['match'] is not None
        assert result['score'] > 0
    
    @patch('tidal_engine.tidalapi.Session')
    def test_resolve_best_node_no_match(self, mock_session_class, sample_config, temp_dir, mock_tidal_session):
        """Test track resolution with no match."""
        config_path = os.path.join(temp_dir, "config.json")
        provider = TidalProvider(sample_config, config_path)
        provider.session = mock_tidal_session
        provider.session.search.return_value = {'tracks': []}
        
        result = provider._resolve_best_node("Nonexistent Track", "Unknown Artist")
        
        assert result['status'] == "FAILED"
        assert result['match'] is None
        assert result['score'] == 0.0
    
    @patch('tidal_engine.tidalapi.Session')
    def test_resolve_best_node_invalid_input(self, mock_session_class, sample_config, temp_dir):
        """Test track resolution with invalid input."""
        config_path = os.path.join(temp_dir, "config.json")
        provider = TidalProvider(sample_config, config_path)
        
        result = provider._resolve_best_node("", "")
        assert result['status'] == "FAILED"
        
        result = provider._resolve_best_node(None, None)
        assert result['status'] == "FAILED"
    
    @patch('tidal_engine.tidalapi.Session')
    def test_resolve_best_node_low_score(self, mock_session_class, sample_config, temp_dir, mock_tidal_session):
        """Test track resolution filters low scores."""
        config_path = os.path.join(temp_dir, "config.json")
        provider = TidalProvider(sample_config, config_path)
        
        # Create a track with very low match score
        mock_track = MagicMock()
        mock_track.name = "Completely Different Track"
        mock_track.audio_quality = "LOSSLESS"
        mock_artist = MagicMock()
        mock_artist.name = "Different Artist"
        mock_track.artist = mock_artist
        
        provider.session = mock_tidal_session
        provider.session.search.return_value = {'tracks': [mock_track]}
        
        result = provider._resolve_best_node("Test Track", "Test Artist")
        
        # Should fail because score is too low
        assert result['status'] == "FAILED"
    
    @patch('tidal_engine.tidalapi.Session')
    def test_publish_creates_playlist(self, mock_session_class, sample_config, temp_dir, mock_tidal_session, sample_tracks_list):
        """Test publishing creates new playlist."""
        config_path = os.path.join(temp_dir, "config.json")
        provider = TidalProvider(sample_config, config_path)
        provider.session = mock_tidal_session
        provider.session.user.playlists.return_value = []  # No existing playlists
        
        provider.publish("New Playlist", sample_tracks_list, replace=False, metrics=None)
        
        provider.session.user.create_playlist.assert_called_once_with("New Playlist", "AI Generated")
    
    @patch('tidal_engine.tidalapi.Session')
    def test_publish_replaces_existing(self, mock_session_class, sample_config, temp_dir, mock_tidal_session, sample_tracks_list):
        """Test publishing replaces existing playlist."""
        config_path = os.path.join(temp_dir, "config.json")
        provider = TidalProvider(sample_config, config_path)
        
        mock_playlist = MagicMock()
        mock_playlist.name = "Existing Playlist"
        mock_item = MagicMock()
        mock_item.id = "item1"
        mock_playlist.items.return_value = [mock_item]
        
        provider.session = mock_tidal_session
        provider.session.user.playlists.return_value = [mock_playlist]
        
        provider.publish("Existing Playlist", sample_tracks_list, replace=True, metrics=None)
        
        mock_playlist.remove_by_id.assert_called_once_with("item1")
    
    @patch('tidal_engine.tidalapi.Session')
    def test_publish_empty_tracks(self, mock_session_class, sample_config, temp_dir, mock_tidal_session):
        """Test publishing with empty tracks list."""
        config_path = os.path.join(temp_dir, "config.json")
        provider = TidalProvider(sample_config, config_path)
        provider.session = mock_tidal_session
        
        provider.publish("Empty Playlist", [], replace=False, metrics=None)
        
        # Should not create playlist or add tracks
        provider.session.user.create_playlist.assert_not_called()
    
    @patch('tidal_engine.tidalapi.Session')
    def test_publish_filters_tracks_without_id(self, mock_session_class, sample_config, temp_dir, mock_tidal_session):
        """Test publishing filters tracks without tidal_id."""
        config_path = os.path.join(temp_dir, "config.json")
        provider = TidalProvider(sample_config, config_path)
        provider.session = mock_tidal_session
        
        tracks_without_id = [
            {"title": "Track 1", "artist": "Artist 1"},  # No tidal_id
            {"title": "Track 2", "artist": "Artist 2", "tidal_id": "12345"}
        ]
        
        provider.publish("Test Playlist", tracks_without_id, replace=False, metrics=None)
        
        # Should only add track with tidal_id (converted to int)
        mock_playlist = provider.session.user.create_playlist.return_value
        mock_playlist.add.assert_called_once()
        call_args = mock_playlist.add.call_args[0][0]
        assert len(call_args) == 1
        assert call_args[0] == 12345  # tidal_id is converted to int
    
    @patch('tidal_engine.tidalapi.Session')
    @patch('tidal_engine.get_tidal_session')
    @patch('tidal_engine.store_tidal_session')
    @patch('tidal_engine.sys')
    def test_authenticate_load_session_fails(self, mock_sys, mock_store_session, mock_get_session, mock_session_class, sample_config, temp_dir):
        mock_sys.platform = "darwin"
        """Test authentication when loading existing session fails."""
        mock_get_session.return_value = {
            'token_type': 'Bearer',
            'access_token': 'token',
            'refresh_token': 'refresh'
        }
        mock_store_session.return_value = True
        config_path = os.path.join(temp_dir, "config.json")
        provider = TidalProvider(sample_config, config_path)
        provider.session.load_oauth_session.side_effect = Exception("Session expired")
        provider.session.check_login.return_value = False
        provider.session.login_oauth_simple = MagicMock()
        # Set real string values, not MagicMock - use type() to ensure they're strings
        provider.session.token_type = "Bearer"
        provider.session.access_token = "new_token"
        provider.session.refresh_token = "new_refresh"
        
        result = provider.authenticate()
        assert result is True
        provider.session.login_oauth_simple.assert_called_once()
    
    @patch('tidal_engine.tidalapi.Session')
    def test_authenticate_oauth_fails(self, mock_session_class, sample_config, temp_dir):
        """Test authentication when OAuth fails."""
        config_path = os.path.join(temp_dir, "config.json")
        provider = TidalProvider(sample_config, config_path)
        provider.session.check_login.return_value = False
        provider.session.login_oauth_simple.side_effect = Exception("OAuth failed")
        
        with pytest.raises(Exception):
            provider.authenticate()
    
    @patch('tidal_engine.tidalapi.Session')
    @patch('tidal_engine.get_tidal_session')
    @patch('tidal_engine.sys')
    def test_authenticate_tidal_error(self, mock_sys, mock_get_session, mock_session_class, sample_config, temp_dir):
        mock_sys.platform = "darwin"
        """Test authentication handles TidalAPIError."""
        import tidalapi
        mock_get_session.return_value = None
        config_path = os.path.join(temp_dir, "config.json")
        provider = TidalProvider(sample_config, config_path)
        provider.session.check_login.side_effect = tidalapi.exceptions.TidalAPIError("API error")
        
        with pytest.raises(tidalapi.exceptions.TidalAPIError):
            provider.authenticate()
    
    @patch('tidal_engine.tidalapi.Session')
    def test_resolve_best_node_tidal_error(self, mock_session_class, sample_config, temp_dir):
        """Test resolve_best_node handles TidalAPIError."""
        import tidalapi
        config_path = os.path.join(temp_dir, "config.json")
        provider = TidalProvider(sample_config, config_path)
        provider.session.search.side_effect = tidalapi.exceptions.TidalAPIError("API error")
        
        result = provider._resolve_best_node("Test Track", "Test Artist")
        assert result['status'] == "FAILED"
    
    @patch('tidal_engine.tidalapi.Session')
    def test_resolve_best_node_exception_handling(self, mock_session_class, sample_config, temp_dir):
        """Test resolve_best_node handles exceptions in track processing."""
        config_path = os.path.join(temp_dir, "config.json")
        provider = TidalProvider(sample_config, config_path)
        
        # Create a track that will raise an exception when processed
        mock_track = MagicMock()
        mock_track.name = "Test Track"
        # Make artist access raise an AttributeError
        def raise_error():
            raise AttributeError("No artist")
        mock_track.artist = property(lambda self: raise_error())
        
        provider.session.search.return_value = {'tracks': [mock_track]}
        
        result = provider._resolve_best_node("Test Track", "Test Artist")
        # Should handle gracefully
        assert result['status'] in ["STRICT", "FAILED"]
    
    @patch('tidal_engine.tidalapi.Session')
    def test_resolve_best_node_empty_title_set(self, mock_session_class, sample_config, temp_dir, mock_tidal_session):
        """Test resolve_best_node with empty title set."""
        config_path = os.path.join(temp_dir, "config.json")
        provider = TidalProvider(sample_config, config_path)
        provider.session = mock_tidal_session
        
        # Create track with empty name after cleaning
        mock_track = MagicMock()
        mock_track.name = ""
        mock_track.audio_quality = "LOSSLESS"
        mock_artist = MagicMock()
        mock_artist.name = "Test Artist"
        mock_track.artist = mock_artist
        
        provider.session.search.return_value = {'tracks': [mock_track]}
        
        result = provider._resolve_best_node("", "Test Artist")
        assert result['status'] == "FAILED"
    
    @patch('tidal_engine.tidalapi.Session')
    @patch('tidal_engine.get_tidal_session')
    @patch('tidal_engine.sys')
    def test_publish_tidal_error(self, mock_sys, mock_get_session, mock_session_class, sample_config, temp_dir, mock_tidal_session, sample_tracks_list):
        mock_sys.platform = "darwin"
        """Test publish handles TidalAPIError."""
        import tidalapi
        mock_get_session.return_value = None
        config_path = os.path.join(temp_dir, "config.json")
        provider = TidalProvider(sample_config, config_path)
        provider.session = mock_tidal_session
        provider.session.check_login.return_value = True  # Authenticate succeeds
        provider.session.user.playlists.side_effect = tidalapi.exceptions.TidalAPIError("API error")
        
        with pytest.raises(tidalapi.exceptions.TidalAPIError):
            provider.publish("Test Playlist", sample_tracks_list, replace=False, metrics=None)
    
    @patch('tidal_engine.tidalapi.Session')
    @patch('tidal_engine.get_tidal_session')
    @patch('tidal_engine.sys')
    def test_publish_exception_handling(self, mock_sys, mock_get_session, mock_session_class, sample_config, temp_dir, mock_tidal_session, sample_tracks_list):
        mock_sys.platform = "darwin"
        """Test publish handles general exceptions."""
        mock_get_session.return_value = None
        config_path = os.path.join(temp_dir, "config.json")
        provider = TidalProvider(sample_config, config_path)
        provider.session = mock_tidal_session
        provider.session.check_login.return_value = True  # Authenticate succeeds
        # Make playlists() return an empty iterator (no existing playlists)
        provider.session.user.playlists.return_value = iter([])
        # Make create_playlist raise an exception
        provider.session.user.create_playlist.side_effect = Exception("Unexpected error")
        
        with pytest.raises(Exception, match="Unexpected error"):
            provider.publish("Test Playlist", sample_tracks_list, replace=False, metrics=None)
    
    @patch('tidal_engine.tidalapi.Session')
    @patch('tidal_engine.store_tidal_session')
    @patch('tidal_engine.sys')
    def test_save_session_data_sets_permissions(self, mock_sys, mock_store_session, mock_session_class, sample_config, temp_dir):
        mock_sys.platform = "darwin"
        """Test that save_session_data stores to Keychain on macOS."""
        mock_store_session.return_value = True
        config_path = os.path.join(temp_dir, "config.json")
        provider = TidalProvider(sample_config, config_path)
        
        # Create a simple object with the required attributes instead of using MagicMock
        class MockSession:
            token_type = "Bearer"
            access_token = "token"
            refresh_token = None
        
        provider.session = MockSession()
        
        provider._save_session_data()
        # Verify store_tidal_session was called (Keychain storage)
        mock_store_session.assert_called_once()
        call_args = mock_store_session.call_args[0][0]
        assert call_args['token_type'] == "Bearer"
        assert call_args['access_token'] == "token"
        assert call_args['refresh_token'] is None
    
    @patch('tidal_engine.tidalapi.Session')
    def test_resolve_best_node_no_tracks_key(self, mock_session_class, sample_config, temp_dir):
        """Test resolve_best_node when search result has no tracks key."""
        config_path = os.path.join(temp_dir, "config.json")
        provider = TidalProvider(sample_config, config_path)
        provider.session.search.return_value = {}  # No 'tracks' key
        
        result = provider._resolve_best_node("Test Track", "Test Artist")
        assert result['status'] == "FAILED"
    
    @patch('tidal_engine.tidalapi.Session')
    def test_resolve_best_node_quality_weighting(self, mock_session_class, sample_config, temp_dir, mock_tidal_session):
        """Test resolve_best_node quality weighting."""
        config_path = os.path.join(temp_dir, "config.json")
        provider = TidalProvider(sample_config, config_path)
        provider.session = mock_tidal_session
        
        # Create tracks with different qualities
        hi_res_track = MagicMock()
        hi_res_track.name = "Test Track"
        hi_res_track.audio_quality = "HI_RES"
        hi_res_track.isrc = "USRC12345678"
        hi_res_artist = MagicMock()
        hi_res_artist.name = "Test Artist"
        hi_res_track.artist = hi_res_artist
        hi_res_album = MagicMock()
        hi_res_album.name = "Test Album"
        hi_res_track.album = hi_res_album
        
        lossless_track = MagicMock()
        lossless_track.name = "Test Track"
        lossless_track.audio_quality = "LOSSLESS"
        lossless_track.isrc = "USRC12345678"
        lossless_track.artist = hi_res_artist
        lossless_track.album = hi_res_album
        
        provider.session.search.return_value = {'tracks': [lossless_track, hi_res_track]}
        
        result = provider._resolve_best_node("Test Track", "Test Artist")
        # Should prefer HI_RES
        assert result['status'] == "STRICT"
        assert "HI_RES" in result['match'].audio_quality or result['match'].audio_quality == "HI_RES"

