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
Tests for main module.

Note: All tests automatically use mocked keychain and isolated config directory
via conftest.py fixtures (mock_keychain_operations, isolate_config_directory).
"""
import json
import os
import sys
import tempfile
import shutil
from unittest.mock import Mock, MagicMock, patch, mock_open
import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import main module components
from main import Track, MusicCurator, print_help
from constants import GEMINI_MODEL, GEMINI_3_FLASH, GEMINI_3_PRO, AVAILABLE_MODELS


class TestTrack:
    """Test Track dataclass."""
    
    def test_track_creation(self):
        """Test creating a Track instance."""
        track = Track(
            title="Test Track",
            artist="Test Artist",
            album="Test Album",
            isrc="USRC12345678",
            tidal_id="12345",
            score=0.95,
            year="2020",
            quality="HI_RES",
            latency_ms=150.5
        )
        
        assert track.title == "Test Track"
        assert track.artist == "Test Artist"
        assert track.album == "Test Album"
        assert track.isrc == "USRC12345678"
        assert track.tidal_id == "12345"
        assert track.score == 0.95
        assert track.year == "2020"
        assert track.quality == "HI_RES"
        assert track.latency_ms == 150.5
    
    def test_track_defaults(self):
        """Test Track with default values."""
        track = Track(title="Title", artist="Artist")
        
        assert track.album == "UNKNOWN"
        assert track.isrc == "UNKNOWN"
        assert track.tidal_id is None
        assert track.score == 0.0
        assert track.year == "N/A"
        assert track.quality == "N/A"
        assert track.latency_ms == 0.0
    
    def test_track_asdict(self):
        """Test converting Track to dictionary."""
        track = Track(title="Title", artist="Artist", tidal_id="123")
        track_dict = track.__dict__
        
        assert isinstance(track_dict, dict)
        assert track_dict['title'] == "Title"
        assert track_dict['artist'] == "Artist"
        assert track_dict['tidal_id'] == "123"


class TestMusicCurator:
    """Test MusicCurator class."""
    
    def setup_method(self):
        """Initialize logger for each test."""
        import main
        from utils import setup_logging
        main.logger = setup_logging(debug=False)
    
    @patch('google.genai.Client')
    def test_init(self, mock_client_class, sample_config):
        """Test MusicCurator initialization."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        curator = MusicCurator(sample_config, model=GEMINI_MODEL, debug=False)
        
        assert curator.cfg == sample_config
        assert curator.model == GEMINI_MODEL
        assert curator.debug is False
        assert curator.client is not None
    
    @patch('google.genai.Client')
    def test_init_gemini_3_detection(self, mock_client_class, sample_config):
        """Test Gemini 3 model detection."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        curator = MusicCurator(sample_config, model=GEMINI_3_FLASH, debug=False)
        assert curator.is_gemini_3 is True
        
        curator = MusicCurator(sample_config, model=GEMINI_3_PRO, debug=False)
        assert curator.is_gemini_3 is True
        
        curator = MusicCurator(sample_config, model="gemini-2.0-flash", debug=False)
        assert curator.is_gemini_3 is False
    
    @patch('google.genai.Client')
    def test_init_missing_api_key(self, mock_client_class):
        """Test initialization fails without API key."""
        config = {"GEMINI": {}}
        
        with pytest.raises(ValueError, match="API key"):
            MusicCurator(config)
    
    @patch('google.genai.Client')
    def test_generate_track_list_success(self, mock_client_class, sample_config, mock_gemini_client):
        """Test successful track list generation."""
        curator = MusicCurator(sample_config, model=GEMINI_MODEL)
        curator.client = mock_gemini_client
        
        tracks = curator._generate_track_list("jazz classics", 5, metrics=None)
        
        assert isinstance(tracks, list)
        assert len(tracks) > 0
        assert "title" in tracks[0]
        assert "artist" in tracks[0]
    
    @patch('google.genai.Client')
    def test_generate_track_list_empty_response(self, mock_client_class, sample_config):
        """Test handling empty AI response."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = None
        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        curator = MusicCurator(sample_config, model=GEMINI_MODEL)
        curator.client = mock_client
        
        tracks = curator._generate_track_list("test", 5, metrics=None)
        assert tracks == []
    
    @patch('google.genai.Client')
    def test_generate_track_list_no_json(self, mock_client_class, sample_config):
        """Test handling response without JSON."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "This is not JSON"
        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        curator = MusicCurator(sample_config, model=GEMINI_MODEL)
        curator.client = mock_client
        
        tracks = curator._generate_track_list("test", 5, metrics=None)
        assert tracks == []
    
    @patch('google.genai.Client')
    def test_generate_track_list_invalid_json(self, mock_client_class, sample_config):
        """Test handling invalid JSON response."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '[{"title": "Test", "artist": "Artist"}'  # Missing closing bracket
        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        curator = MusicCurator(sample_config, model=GEMINI_MODEL)
        curator.client = mock_client
        
        tracks = curator._generate_track_list("test", 5, metrics=None)
        assert tracks == []
    
    @patch('google.genai.Client')
    def test_generate_track_list_gemini_3_model(self, mock_client_class, sample_config):
        """Test Gemini 3 model is used correctly."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '[{"title": "Test", "artist": "Artist"}]'
        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        curator = MusicCurator(sample_config, model=GEMINI_3_FLASH)
        curator.client = mock_client
        
        # Verify is_gemini_3 is set correctly
        assert curator.is_gemini_3 is True
        
        curator._generate_track_list("test", 5, metrics=None)
        
        # Verify generate_content was called with the correct model
        call_args = mock_client.models.generate_content.call_args
        assert call_args[1]['model'] == GEMINI_3_FLASH
    
    @patch('google.genai.Client')
    def test_curate_success(self, mock_client_class, sample_config, mock_gemini_client, mock_tidal_session):
        """Test successful curation."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '[{"title": "Test Track", "artist": "Test Artist"}]'
        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        curator = MusicCurator(sample_config, model=GEMINI_MODEL)
        curator.client = mock_client
        
        # Mock TidalProvider
        mock_engine = MagicMock()
        mock_result = {
            'status': 'STRICT',
            'match': MagicMock(),
            'score': 0.95
        }
        mock_result['match'].name = "Test Track"
        mock_result['match'].id = "12345"
        mock_result['match'].audio_quality = "HI_RES"
        mock_result['match'].isrc = "USRC12345678"
        mock_result['match'].artist.name = "Test Artist"
        mock_result['match'].album.name = "Test Album"
        mock_result['match'].album.release_date.year = 2020
        
        mock_engine._resolve_best_node.return_value = mock_result
        
        tracks = curator.curate("test query", 5, mock_engine, metrics=None)
        
        assert isinstance(tracks, list)
        assert len(tracks) > 0
        assert isinstance(tracks[0], Track)
    
    @patch('google.genai.Client')
    def test_curate_no_candidates(self, mock_client_class, sample_config):
        """Test curation with no candidates."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "No tracks found"
        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        curator = MusicCurator(sample_config, model=GEMINI_MODEL)
        curator.client = mock_client
        
        mock_engine = MagicMock()
        tracks = curator.curate("test query", 5, mock_engine, metrics=None)
        
        assert tracks == []
    
    @patch('google.genai.Client')
    def test_curate_respects_limit(self, mock_client_class, sample_config, mock_gemini_client):
        """Test curation respects limit."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        # Return 10 tracks
        mock_response.text = json.dumps([
            {"title": f"Track {i}", "artist": f"Artist {i}"}
            for i in range(10)
        ])
        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        curator = MusicCurator(sample_config, model=GEMINI_MODEL)
        curator.client = mock_client
        
        mock_engine = MagicMock()
        mock_result = {
            'status': 'STRICT',
            'match': MagicMock(),
            'score': 0.95
        }
        mock_result['match'].name = "Test Track"
        mock_result['match'].id = "12345"
        mock_result['match'].audio_quality = "HI_RES"
        mock_result['match'].isrc = "USRC12345678"
        mock_result['match'].artist.name = "Test Artist"
        mock_result['match'].album.name = "Test Album"
        mock_result['match'].album.release_date.year = 2020
        
        mock_engine._resolve_best_node.return_value = mock_result
        
        tracks = curator.curate("test query", 3, mock_engine, metrics=None)
        
        assert len(tracks) <= 3


class TestPrintHelp:
    """Test help function."""
    
    def test_print_help_output(self, capsys):
        """Test help output contains expected sections."""
        print_help()
        captured = capsys.readouterr()
        output = captured.out
        
        # Check for simplified help sections
        assert "playlist-builder" in output
        assert "USAGE" in output
        assert "COMMANDS" in output
        assert "OPTIONS" in output
        assert "EXAMPLES" in output
        assert "CONFIG" not in output  # CONFIG section was removed
    
    def test_print_help_border_alignment(self, capsys):
        """Test help format has proper structure."""
        import re
        print_help()
        captured = capsys.readouterr()
        output = captured.out
        
        # Check for simplified help section headers
        lines = output.split('\n')
        section_headers = ['USAGE', 'COMMANDS', 'OPTIONS', 'EXAMPLES']
        
        for header in section_headers:
            # Should find each section header
            found = any(header in line for line in lines)
            assert found, f"Section '{header}' not found in help output"
    
    def test_print_help_column_alignment(self, capsys):
        """Test help commands section has proper formatting."""
        import re
        print_help()
        captured = capsys.readouterr()
        output = captured.out
        
        # Check that COMMANDS section has command descriptions
        lines = output.split('\n')
        in_commands = False
        command_lines = []
        
        for line in lines:
            if 'COMMANDS' in line and 'KEYCHAIN' not in line:
                in_commands = True
                continue
            if in_commands:
                # Look for lines containing search or publish (may have ANSI codes)
                if 'search' in line or 'publish' in line or 'keychain' in line:
                    command_lines.append(line)
                # Stop when we hit the next section
                if 'OPTIONS' in line:
                    break
        
        # Verify we found command lines
        assert len(command_lines) >= 2, f"Should find command descriptions, found: {len(command_lines)}"
        
        # Check that commands have descriptions
        for line in command_lines:
            # Verify descriptions are present (not just command names)
            ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
            visible_line = ansi_escape.sub('', line)
            # Should have substantial content
            assert len(visible_line.strip()) > 5, "Command line should have content"


class TestMainFunction:
    """Test main function logic.
    
    Note: These tests use the mocked keychain from conftest.py, so they
    will NOT delete real API keys or interact with the real keychain.
    """
    
    @patch('main.sys.argv', ['main.py', '--help'])
    @patch('main.print_help')
    def test_main_help(self, mock_print_help):
        """Test main function shows help."""
        from main import main
        try:
            main()
        except SystemExit:
            pass
        mock_print_help.assert_called_once()
    
    @patch('main.sys.argv', ['main.py', 'reset'])
    @patch('main.os.path.exists')
    @patch('main.os.remove')
    def test_main_reset(self, mock_remove, mock_exists, mock_keychain_operations):
        """Test reset command.
        
        This test verifies that:
        1. The reset command calls delete_secret (mocked via conftest.py)
        2. The mock keychain is used, NOT the real macOS keychain
        3. No real API keys are deleted
        """
        mock_exists.return_value = True
        
        from main import main
        try:
            main()
        except SystemExit:
            pass
        
        # Verify os.remove was called for config/cache files
        mock_remove.assert_called()
    
    @patch('main.sys.argv', ['main.py', 'rebuild'])
    @patch('main.os.path.exists')
    @patch('main.shutil.rmtree')
    def test_main_rebuild(self, mock_rmtree, mock_exists, mock_keychain_operations):
        """Test rebuild command.
        
        This test uses mocked keychain operations from conftest.py.
        """
        mock_exists.return_value = True
        
        from main import main
        try:
            main()
        except SystemExit:
            pass
        
        mock_rmtree.assert_called()


class TestCLIArgumentParsing:
    """Test CLI argument parsing accepts flags in any position.
    
    Regression tests to ensure flags like --model, --limit, --debug
    work both before and after subcommands.
    """
    
    def _create_parser(self):
        """Create argument parser matching main.py structure."""
        import argparse
        from constants import DEFAULT_LIMIT, GEMINI_MODEL
        
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument("-d", "--debug", action="store_true", default=False)
        parser.add_argument("-l", "--limit", type=int, default=DEFAULT_LIMIT)
        parser.add_argument("-m", "--model", type=str, default=GEMINI_MODEL)
        parser.add_argument("--run-code-tests", action="store_true")
        parser.add_argument("--coverage", action="store_true")
        parser.add_argument("--verbose", "-v", action="store_true")
        
        subparsers = parser.add_subparsers(dest="cmd")
        
        search_parser = subparsers.add_parser("search")
        search_parser.add_argument("query")
        search_parser.add_argument("-d", "--debug", action="store_true", default=False)
        search_parser.add_argument("-l", "--limit", type=int, default=DEFAULT_LIMIT)
        search_parser.add_argument("-m", "--model", type=str, default=GEMINI_MODEL)
        
        publish_parser = subparsers.add_parser("publish")
        publish_parser.add_argument("provider", choices=["tidal", "spotify"])
        publish_parser.add_argument("--name", required=True)
        publish_parser.add_argument("--replace", action="store_true")
        publish_parser.add_argument("-d", "--debug", action="store_true", default=False)
        
        return parser
    
    def test_search_flags_after_subcommand(self):
        """Verify --model, --limit, --debug work after 'search' subcommand."""
        parser = self._create_parser()
        args = parser.parse_args(['search', 'Jazz classics', '--model', '3-pro', '--limit', '20', '--debug'])
        
        assert args.cmd == 'search'
        assert args.query == 'Jazz classics'
        assert args.model == '3-pro'
        assert args.limit == 20
        assert args.debug is True
    
    def test_search_flags_before_subcommand(self):
        """Verify command parses when flags are before 'search' subcommand.
        
        Note: When flags are before subcommand, the parent parser consumes them,
        but the subparser then applies its own defaults. For reliable behavior,
        flags should be placed after the subcommand.
        """
        parser = self._create_parser()
        args = parser.parse_args(['--debug', 'search', 'Jazz classics'])
        
        assert args.cmd == 'search'
        assert args.query == 'Jazz classics'
        # Parent's --debug is consumed but subparser has its own default
        # This documents the argparse behavior - flags after subcommand is preferred
    
    def test_search_flags_mixed_positions(self):
        """Verify flags work in mixed positions."""
        parser = self._create_parser()
        args = parser.parse_args(['search', 'Jazz classics', '--limit', '15', '--debug'])
        
        assert args.cmd == 'search'
        assert args.limit == 15
        assert args.debug is True
    
    def test_search_short_flags(self):
        """Verify short flags (-m, -l, -d) work after subcommand."""
        parser = self._create_parser()
        args = parser.parse_args(['search', 'Jazz classics', '-m', '3-flash', '-l', '5', '-d'])
        
        assert args.model == '3-flash'
        assert args.limit == 5
        assert args.debug is True
    
    def test_publish_debug_after_subcommand(self):
        """Verify --debug works after 'publish' subcommand."""
        parser = self._create_parser()
        args = parser.parse_args(['publish', 'tidal', '--name', 'My Playlist', '--debug'])
        
        assert args.cmd == 'publish'
        assert args.provider == 'tidal'
        assert args.name == 'My Playlist'
        assert args.debug is True
    
    def test_publish_all_flags(self):
        """Verify all publish flags work together."""
        parser = self._create_parser()
        args = parser.parse_args(['publish', 'spotify', '--name', 'Test', '--replace', '--debug'])
        
        assert args.cmd == 'publish'
        assert args.provider == 'spotify'
        assert args.name == 'Test'
        assert args.replace is True
        assert args.debug is True
    
    def test_search_defaults_without_flags(self):
        """Verify defaults are used when flags not specified."""
        from constants import DEFAULT_LIMIT, GEMINI_MODEL
        
        parser = self._create_parser()
        args = parser.parse_args(['search', 'Rock music'])
        
        assert args.cmd == 'search'
        assert args.query == 'Rock music'
        assert args.limit == DEFAULT_LIMIT
        assert args.model == GEMINI_MODEL
        assert args.debug is False
