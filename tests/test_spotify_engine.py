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
Tests for spotify_engine module (EXPERIMENTAL).
"""
import json
import os
import sys
from unittest.mock import Mock, MagicMock, patch
import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from spotify_engine import SpotifyProvider, SPOTIFY_SCOPES
from constants import MIN_MATCH_SCORE, TrackResolutionStatus


class TestSpotifyProvider:
    """Test SpotifyProvider class."""
    
    def test_init(self, sample_config, temp_dir):
        """Test SpotifyProvider initialization."""
        config_path = os.path.join(temp_dir, "config.json")
        provider = SpotifyProvider(sample_config, config_path, debug=False)
        
        assert provider.cfg == sample_config
        assert provider.cfg_path == config_path
        assert provider.debug is False
        assert provider.client is None
        assert provider._user_id is None
    
    def test_init_debug_mode(self, sample_config, temp_dir):
        """Test SpotifyProvider initialization with debug mode."""
        config_path = os.path.join(temp_dir, "config.json")
        provider = SpotifyProvider(sample_config, config_path, debug=True)
        
        assert provider.debug is True
    
    @patch('spotify_engine.get_secret')
    @patch('spotify_engine.sys')
    def test_get_credentials_from_keychain(self, mock_sys, mock_get_secret, sample_config, temp_dir):
        """Test getting credentials from Keychain on macOS."""
        mock_sys.platform = "darwin"
        mock_get_secret.side_effect = lambda key, account: {
            ('spotify_client_id', 'spotify'): 'test_client_id',
            ('spotify_client_secret', 'spotify'): 'test_client_secret',
        }.get((key, account))
        
        config_path = os.path.join(temp_dir, "config.json")
        provider = SpotifyProvider(sample_config, config_path)
        
        client_id, client_secret = provider._get_credentials()
        
        assert client_id == 'test_client_id'
        assert client_secret == 'test_client_secret'
    
    def test_get_credentials_from_config(self, temp_dir):
        """Test getting credentials from config file."""
        config = {
            'SPOTIFY': {
                'CLIENT_ID': 'config_client_id',
                'CLIENT_SECRET': 'config_client_secret'
            }
        }
        config_path = os.path.join(temp_dir, "config.json")
        provider = SpotifyProvider(config, config_path)
        
        with patch('spotify_engine.sys') as mock_sys:
            mock_sys.platform = "linux"  # Not macOS
            client_id, client_secret = provider._get_credentials()
        
        assert client_id == 'config_client_id'
        assert client_secret == 'config_client_secret'
    
    def test_clean_text(self, sample_config, temp_dir):
        """Test text cleaning function."""
        config_path = os.path.join(temp_dir, "config.json")
        provider = SpotifyProvider(sample_config, config_path)
        
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
    
    def test_resolve_best_node_invalid_input(self, sample_config, temp_dir):
        """Test track resolution with invalid input."""
        config_path = os.path.join(temp_dir, "config.json")
        provider = SpotifyProvider(sample_config, config_path)
        
        result = provider._resolve_best_node("", "")
        assert result['status'] == "FAILED"
        
        result = provider._resolve_best_node(None, None)
        assert result['status'] == "FAILED"
    
    def test_resolve_best_node_no_client(self, sample_config, temp_dir):
        """Test track resolution without initialized client."""
        config_path = os.path.join(temp_dir, "config.json")
        provider = SpotifyProvider(sample_config, config_path)
        provider.client = None
        
        result = provider._resolve_best_node("Test Track", "Test Artist")
        assert result['status'] == "FAILED"
    
    def test_resolve_best_node_success(self, sample_config, temp_dir, mock_spotify_client):
        """Test successful track resolution."""
        config_path = os.path.join(temp_dir, "config.json")
        provider = SpotifyProvider(sample_config, config_path)
        provider.client = mock_spotify_client
        
        result = provider._resolve_best_node("Test Track", "Test Artist")
        
        assert result['status'] == "STRICT"
        assert result['match'] is not None
        assert result['score'] > 0
    
    def test_resolve_best_node_no_match(self, sample_config, temp_dir, mock_spotify_client):
        """Test track resolution with no match."""
        config_path = os.path.join(temp_dir, "config.json")
        provider = SpotifyProvider(sample_config, config_path)
        provider.client = mock_spotify_client
        provider.client.search.return_value = {'tracks': {'items': []}}
        
        result = provider._resolve_best_node("Nonexistent Track", "Unknown Artist")
        
        assert result['status'] == "FAILED"
        assert result['match'] is None
        assert result['score'] == 0.0
    
    def test_resolve_best_node_low_score(self, sample_config, temp_dir, mock_spotify_client):
        """Test track resolution filters low scores."""
        config_path = os.path.join(temp_dir, "config.json")
        provider = SpotifyProvider(sample_config, config_path)
        
        # Create a track with very low match score
        mock_track = {
            'id': '12345',
            'name': 'Completely Different Track',
            'artists': [{'name': 'Different Artist'}],
            'album': {'name': 'Different Album'}
        }
        
        provider.client = mock_spotify_client
        provider.client.search.return_value = {'tracks': {'items': [mock_track]}}
        
        result = provider._resolve_best_node("Test Track", "Test Artist")
        
        # Should fail because score is too low
        assert result['status'] == "FAILED"
    
    @patch('spotify_engine.get_secret')
    def test_authenticate_no_credentials(self, mock_get_secret, sample_config, temp_dir):
        """Test authentication fails without credentials."""
        mock_get_secret.return_value = None
        
        config = {'SPOTIFY': {}}  # No credentials
        config_path = os.path.join(temp_dir, "config.json")
        provider = SpotifyProvider(config, config_path)
        
        with pytest.raises(ValueError, match="Spotify credentials not configured"):
            provider.authenticate()
    
    @patch('spotify_engine.SpotifyOAuth')
    @patch('spotify_engine.spotipy.Spotify')
    @patch('spotify_engine.get_secret')
    @patch('spotify_engine.get_spotify_session')
    @patch('spotify_engine.store_spotify_session')
    def test_authenticate_success(self, mock_store, mock_get_session, mock_get_secret, 
                                   mock_spotify_class, mock_oauth_class, sample_config, temp_dir):
        """Test successful authentication."""
        # Setup mocks
        mock_get_secret.side_effect = lambda key, account: {
            ('spotify_client_id', 'spotify'): 'test_client_id',
            ('spotify_client_secret', 'spotify'): 'test_client_secret',
        }.get((key, account))
        
        mock_get_session.return_value = None  # No cached session
        
        mock_oauth = MagicMock()
        mock_oauth.get_access_token.return_value = {
            'access_token': 'test_access_token',
            'refresh_token': 'test_refresh_token',
            'expires_at': 9999999999
        }
        mock_oauth_class.return_value = mock_oauth
        
        mock_spotify = MagicMock()
        mock_spotify.current_user.return_value = {'id': 'test_user_id'}
        mock_spotify_class.return_value = mock_spotify
        
        mock_store.return_value = True
        
        config_path = os.path.join(temp_dir, "config.json")
        provider = SpotifyProvider(sample_config, config_path)
        
        with patch('spotify_engine.sys') as mock_sys:
            mock_sys.platform = "darwin"
            result = provider.authenticate()
        
        assert result is True
        assert provider.client is not None
        assert provider._user_id == 'test_user_id'
    
    def test_publish_empty_tracks(self, sample_config, temp_dir):
        """Test publishing with empty tracks list."""
        config_path = os.path.join(temp_dir, "config.json")
        provider = SpotifyProvider(sample_config, config_path)
        
        provider.publish("Empty Playlist", [], replace=False, metrics=None)
        
        # Should not error, just print warning
        assert provider.client is None  # authenticate() not called
    
    @patch('spotify_engine.SpotifyOAuth')
    @patch('spotify_engine.spotipy.Spotify')
    @patch('spotify_engine.get_secret')
    @patch('spotify_engine.get_spotify_session')
    @patch('spotify_engine.store_spotify_session')
    def test_publish_creates_playlist(self, mock_store, mock_get_session, mock_get_secret,
                                       mock_spotify_class, mock_oauth_class, 
                                       sample_config, temp_dir, sample_spotify_tracks):
        """Test publishing creates new playlist."""
        # Setup auth mocks
        mock_get_secret.side_effect = lambda key, account: {
            ('spotify_client_id', 'spotify'): 'test_client_id',
            ('spotify_client_secret', 'spotify'): 'test_client_secret',
        }.get((key, account))
        mock_get_session.return_value = None
        mock_store.return_value = True
        
        mock_oauth = MagicMock()
        mock_oauth.get_access_token.return_value = {
            'access_token': 'test_access_token',
            'refresh_token': 'test_refresh_token',
            'expires_at': 9999999999
        }
        mock_oauth_class.return_value = mock_oauth
        
        mock_spotify = MagicMock()
        mock_spotify.current_user.return_value = {'id': 'test_user_id'}
        mock_spotify.current_user_playlists.return_value = {'items': []}  # No existing playlists
        mock_spotify.user_playlist_create.return_value = {'id': 'new_playlist_id', 'name': 'New Playlist'}
        mock_spotify_class.return_value = mock_spotify
        
        config_path = os.path.join(temp_dir, "config.json")
        provider = SpotifyProvider(sample_config, config_path)
        
        with patch('spotify_engine.sys') as mock_sys:
            mock_sys.platform = "darwin"
            provider.publish("New Playlist", sample_spotify_tracks, replace=False, metrics=None)
        
        mock_spotify.user_playlist_create.assert_called_once()
        mock_spotify.playlist_add_items.assert_called_once()
    
    @patch('spotify_engine.SpotifyOAuth')
    @patch('spotify_engine.spotipy.Spotify')
    @patch('spotify_engine.get_secret')
    @patch('spotify_engine.get_spotify_session')
    @patch('spotify_engine.store_spotify_session')
    def test_publish_replaces_existing(self, mock_store, mock_get_session, mock_get_secret,
                                        mock_spotify_class, mock_oauth_class,
                                        sample_config, temp_dir, sample_spotify_tracks):
        """Test publishing replaces existing playlist."""
        # Setup auth mocks
        mock_get_secret.side_effect = lambda key, account: {
            ('spotify_client_id', 'spotify'): 'test_client_id',
            ('spotify_client_secret', 'spotify'): 'test_client_secret',
        }.get((key, account))
        mock_get_session.return_value = None
        mock_store.return_value = True
        
        mock_oauth = MagicMock()
        mock_oauth.get_access_token.return_value = {
            'access_token': 'test_access_token',
            'refresh_token': 'test_refresh_token',
            'expires_at': 9999999999
        }
        mock_oauth_class.return_value = mock_oauth
        
        existing_playlist = {'id': 'existing_id', 'name': 'Existing Playlist'}
        mock_spotify = MagicMock()
        mock_spotify.current_user.return_value = {'id': 'test_user_id'}
        mock_spotify.current_user_playlists.return_value = {'items': [existing_playlist]}
        mock_spotify.playlist_items.return_value = {'items': [
            {'track': {'uri': 'spotify:track:old_track'}}
        ]}
        mock_spotify_class.return_value = mock_spotify
        
        config_path = os.path.join(temp_dir, "config.json")
        provider = SpotifyProvider(sample_config, config_path)
        
        with patch('spotify_engine.sys') as mock_sys:
            mock_sys.platform = "darwin"
            provider.publish("Existing Playlist", sample_spotify_tracks, replace=True, metrics=None)
        
        mock_spotify.playlist_remove_all_occurrences_of_items.assert_called_once()
        mock_spotify.playlist_add_items.assert_called_once()
    
    def test_resolve_best_node_spotify_exception(self, sample_config, temp_dir):
        """Test resolve_best_node handles SpotifyException."""
        import spotipy
        config_path = os.path.join(temp_dir, "config.json")
        provider = SpotifyProvider(sample_config, config_path)
        
        mock_client = MagicMock()
        mock_client.search.side_effect = spotipy.SpotifyException(400, -1, "Bad Request")
        provider.client = mock_client
        
        result = provider._resolve_best_node("Test Track", "Test Artist")
        assert result['status'] == "FAILED"
    
    def test_resolve_best_node_empty_title_set(self, sample_config, temp_dir, mock_spotify_client):
        """Test resolve_best_node with empty title set."""
        config_path = os.path.join(temp_dir, "config.json")
        provider = SpotifyProvider(sample_config, config_path)
        provider.client = mock_spotify_client
        
        # Create track with empty name
        mock_track = {
            'id': '12345',
            'name': '',
            'artists': [{'name': 'Test Artist'}],
            'album': {'name': 'Test Album'}
        }
        
        provider.client.search.return_value = {'tracks': {'items': [mock_track]}}
        
        result = provider._resolve_best_node("", "Test Artist")
        assert result['status'] == "FAILED"


class TestSpotifyScopes:
    """Test Spotify OAuth scopes configuration."""
    
    def test_scopes_defined(self):
        """Test that required scopes are defined."""
        assert "playlist-modify-public" in SPOTIFY_SCOPES
        assert "playlist-modify-private" in SPOTIFY_SCOPES
        assert "playlist-read-private" in SPOTIFY_SCOPES

