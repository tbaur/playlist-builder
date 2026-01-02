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
Integration tests for playlist-builder.

Note: All tests automatically use mocked keychain and isolated config directory
via conftest.py fixtures (mock_keychain_operations, isolate_config_directory).
"""
import json
import os
import sys
import tempfile
import shutil
from unittest.mock import Mock, MagicMock, patch
import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import Track, MusicCurator
from tidal_engine import TidalProvider
from metrics import MetricsCollector


class TestEndToEndWorkflow:
    """Test end-to-end workflows."""
    
    def setup_method(self):
        """Initialize logger for each test."""
        import main
        from utils import setup_logging
        main.logger = setup_logging(debug=False)
    
    @patch('google.genai.Client')
    @patch('tidal_engine.tidalapi.Session')
    def test_search_and_publish_workflow(self, mock_session_class, mock_client_class, sample_config, temp_dir):
        """Test complete search and publish workflow."""
        # Setup mocks
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '[{"title": "Test Track", "artist": "Test Artist"}]'
        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        mock_session = MagicMock()
        mock_session.check_login.return_value = True
        mock_session.token_type = "Bearer"
        mock_session.access_token = "token"
        
        # Mock track search result
        mock_track = MagicMock()
        mock_track.id = "12345"
        mock_track.name = "Test Track"
        mock_track.audio_quality = "HI_RES"
        mock_track.isrc = "USRC12345678"
        mock_track.artist.name = "Test Artist"
        mock_track.album.name = "Test Album"
        mock_track.album.release_date.year = 2020
        mock_session.search.return_value = {'tracks': [mock_track]}
        
        # Mock playlist
        mock_playlist = MagicMock()
        mock_playlist.name = "Test Playlist"
        mock_playlist.items.return_value = []
        mock_user = MagicMock()
        mock_user.playlists.return_value = []
        mock_user.create_playlist.return_value = mock_playlist
        mock_session.user = mock_user
        mock_session_class.return_value = mock_session
        
        config_path = os.path.join(temp_dir, "config.json")
        with open(config_path, 'w') as f:
            json.dump(sample_config, f)
        
        # Test search
        curator = MusicCurator(sample_config)
        curator.client = mock_client
        
        engine = TidalProvider(sample_config, config_path)
        engine.session = mock_session
        
        metrics = MetricsCollector()
        tracks = curator.curate("test query", 5, engine, metrics)
        
        assert len(tracks) > 0
        assert isinstance(tracks[0], Track)
        
        # Test publish
        track_dicts = [track.__dict__ for track in tracks]
        engine.publish("Test Playlist", track_dicts, replace=False, metrics=metrics)
        
        mock_user.create_playlist.assert_called_once()
        mock_playlist.add.assert_called_once()
    
    @patch('google.genai.Client')
    @patch('tidal_engine.tidalapi.Session')
    def test_model_selection_workflow(self, mock_session_class, mock_client_class, sample_config):
        """Test different model selections work."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '[{"title": "Test", "artist": "Artist"}]'
        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        mock_session = MagicMock()
        mock_session.check_login.return_value = True
        
        # Test with Gemini 3 Flash
        curator1 = MusicCurator(sample_config, model="gemini-3-flash-preview")
        assert curator1.is_gemini_3 is True
        
        # Test with Gemini 3 Pro
        curator2 = MusicCurator(sample_config, model="gemini-3-pro-preview")
        assert curator2.is_gemini_3 is True
        
        # Test with Gemini 2
        curator3 = MusicCurator(sample_config, model="gemini-2.0-flash")
        assert curator3.is_gemini_3 is False
    
    @patch('google.genai.Client')
    @patch('tidal_engine.tidalapi.Session')
    def test_metrics_collection_workflow(self, mock_session_class, mock_client_class, sample_config):
        """Test metrics collection during workflow."""
        from metrics import MetricsCollector
        
        metrics = MetricsCollector()
        op1 = metrics.start_operation("test_op1")
        metrics.update_items(processed=10, succeeded=9, failed=1)
        metrics.add_stat("test_stat", 42)
        metrics.end_operation(success=True)
        
        assert len(metrics.operations) == 1
        assert metrics.operations[0].items_processed == 10
        assert metrics.operations[0].items_succeeded == 9
        assert metrics.operations[0].additional_stats["test_stat"] == 42
        assert metrics.operations[0].success is True
    
    @patch('google.genai.Client')
    @patch('tidal_engine.tidalapi.Session')
    def test_error_handling_workflow(self, mock_session_class, mock_client_class, sample_config):
        """Test error handling in workflow."""
        # Test API error
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = Exception("API Error")
        mock_client_class.return_value = mock_client
        
        curator = MusicCurator(sample_config)
        curator.client = mock_client
        
        # Should handle error gracefully
        with pytest.raises(Exception):
            curator._generate_track_list("test", 5)
    
    def test_config_validation_integration(self, temp_dir):
        """Test config validation in integration."""
        from utils import validate_config
        
        # Valid config
        valid_config = {
            "GEMINI": {"API_KEY": "test_key_1234567890"},
            "TIDAL": {"SESSION_DATA": {}}
        }
        is_valid, error = validate_config(valid_config)
        assert is_valid is True
        
        # Invalid config
        invalid_config = {"GEMINI": {}}
        is_valid, error = validate_config(invalid_config)
        assert is_valid is False
        assert error is not None
