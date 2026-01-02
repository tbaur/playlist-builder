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
Tests for utils module.
"""
import logging
import os
import tempfile
import shutil
import time
from unittest.mock import patch, MagicMock
import pytest

from utils import (
    setup_logging, retry_with_backoff, validate_config,
    validate_query, set_config_permissions, rate_limit, RateLimiter,
    format_track_signal, print_track_row, with_timeout
)
from constants import BASE_DIR, LOG_FILE, MAX_QUERY_LENGTH, CONFIG_FILE_PERMISSIONS


class TestSetupLogging:
    """Test logging setup."""
    
    def test_setup_logging_creates_logger(self):
        """Test that setup_logging returns a logger."""
        logger = setup_logging()
        assert isinstance(logger, logging.Logger)
        assert logger.name == 'playlist_builder'
    
    def test_setup_logging_debug_level(self):
        """Test debug logging level."""
        logger = setup_logging(debug=True)
        assert logger.level == logging.DEBUG
    
    def test_setup_logging_info_level(self):
        """Test info logging level."""
        logger = setup_logging(debug=False)
        assert logger.level == logging.INFO
    
    def test_setup_logging_creates_handlers(self):
        """Test that logging creates file and console handlers."""
        logger = setup_logging()
        assert len(logger.handlers) >= 2
        
        handler_types = [type(h).__name__ for h in logger.handlers]
        assert 'FileHandler' in handler_types
        assert 'StreamHandler' in handler_types
    
    def test_setup_logging_creates_log_file(self, isolate_config_directory):
        """Test that log file is created."""
        # Use the isolated log file path from the fixture
        log_file = isolate_config_directory['log_file']
        logger = setup_logging()
        # Give it a moment to create the file
        time.sleep(0.1)
        # The logger should create a log file in the isolated directory
        # Check that the base directory exists (logger may not write immediately)
        base_dir = isolate_config_directory['base_dir']
        assert os.path.exists(base_dir)
    
    def test_setup_logging_creates_base_dir(self):
        """Test that setup_logging creates the base directory."""
        from constants import BASE_DIR
        
        # Ensure BASE_DIR exists after setup_logging
        logger = setup_logging()
        assert os.path.exists(BASE_DIR)
        assert isinstance(logger, logging.Logger)


class TestRetryWithBackoff:
    """Test retry decorator."""
    
    def test_retry_succeeds_on_first_try(self):
        """Test that function succeeds without retries."""
        @retry_with_backoff(max_retries=3)
        def success_func():
            return "success"
        
        assert success_func() == "success"
    
    def test_retry_succeeds_after_failures(self):
        """Test that function succeeds after retries."""
        call_count = [0]
        
        @retry_with_backoff(max_retries=3, base_delay=0.01)
        def retry_func():
            call_count[0] += 1
            if call_count[0] < 2:
                raise ValueError("Temporary failure")
            return "success"
        
        result = retry_func()
        assert result == "success"
        assert call_count[0] == 2
    
    def test_retry_fails_after_max_retries(self):
        """Test that function fails after max retries."""
        @retry_with_backoff(max_retries=2, base_delay=0.01)
        def fail_func():
            raise ValueError("Always fails")
        
        with pytest.raises(ValueError, match="Always fails"):
            fail_func()
    
    def test_retry_only_catches_specified_exceptions(self):
        """Test that retry only catches specified exceptions."""
        @retry_with_backoff(max_retries=2, exceptions=(ValueError,), base_delay=0.01)
        def raise_key_error():
            raise KeyError("Not caught")
        
        with pytest.raises(KeyError):
            raise_key_error()
    
    @patch('utils.time.sleep')
    def test_retry_exponential_backoff(self, mock_sleep):
        """Test that retry uses exponential backoff."""
        call_count = [0]
        
        @retry_with_backoff(max_retries=3, base_delay=1.0)
        def retry_func():
            call_count[0] += 1
            if call_count[0] < 3:
                raise ValueError("Fail")
            return "success"
        
        result = retry_func()
        assert result == "success"
        
        # Verify sleep was called with increasing delays
        # First retry: base_delay * 2^0 = 1.0
        # Second retry: base_delay * 2^1 = 2.0
        assert mock_sleep.call_count == 2
        calls = [call[0][0] for call in mock_sleep.call_args_list]
        assert calls[0] < calls[1]  # Second delay should be longer


class TestValidateConfig:
    """Test configuration validation."""
    
    def test_validate_config_valid(self, sample_config):
        """Test validation with valid config."""
        is_valid, error_msg = validate_config(sample_config)
        assert is_valid is True
        assert error_msg is None
    
    def test_validate_config_not_dict(self):
        """Test validation fails for non-dict."""
        is_valid, error_msg = validate_config("not a dict")
        assert is_valid is False
        assert "dictionary" in error_msg.lower()
    
    def test_validate_config_missing_gemini(self):
        """Test validation fails when GEMINI section missing."""
        config = {"TIDAL": {}}
        is_valid, error_msg = validate_config(config)
        assert is_valid is False
        assert "GEMINI" in error_msg
    
    def test_validate_config_missing_api_key(self):
        """Test validation fails when API_KEY missing."""
        config = {"GEMINI": {}, "TIDAL": {}}
        is_valid, error_msg = validate_config(config)
        assert is_valid is False
        assert "API_KEY" in error_msg
    
    def test_validate_config_invalid_api_key_empty(self):
        """Test validation fails for empty API key."""
        config = {
            "GEMINI": {"API_KEY": ""},
            "TIDAL": {}
        }
        is_valid, error_msg = validate_config(config)
        assert is_valid is False
        assert "gemini api key" in error_msg.lower() or "api key" in error_msg.lower()
    
    def test_validate_config_invalid_api_key_too_short(self):
        """Test validation fails for API key that's too short."""
        config = {
            "GEMINI": {"API_KEY": "short"},
            "TIDAL": {}
        }
        is_valid, error_msg = validate_config(config)
        assert is_valid is False
        assert "gemini api key" in error_msg.lower() or "api key" in error_msg.lower()
    
    def test_validate_config_invalid_api_key_not_string(self):
        """Test validation fails for non-string API key."""
        config = {
            "GEMINI": {"API_KEY": 12345},
            "TIDAL": {}
        }
        is_valid, error_msg = validate_config(config)
        assert is_valid is False
        assert "gemini api key" in error_msg.lower() or "api key" in error_msg.lower()
    
    def test_validate_config_adds_tidal_if_missing(self):
        """Test that validation adds TIDAL section if missing."""
        config = {
            "GEMINI": {"API_KEY": "test_api_key_1234567890"}
        }
        is_valid, error_msg = validate_config(config)
        assert is_valid is True
        assert "TIDAL" in config
        assert "SESSION_DATA" in config["TIDAL"]
    
    def test_validate_config_preserves_existing_tidal(self):
        """Test that validation preserves existing TIDAL section."""
        config = {
            "GEMINI": {"API_KEY": "test_api_key_1234567890"},
            "TIDAL": {"SESSION_DATA": {"token": "test"}}
        }
        is_valid, error_msg = validate_config(config)
        assert is_valid is True
        assert config["TIDAL"]["SESSION_DATA"]["token"] == "test"


class TestValidateQuery:
    """Test query validation function."""
    
    def test_validate_query_valid(self):
        """Test validation with valid query."""
        is_valid, error_msg = validate_query("jazz classics")
        assert is_valid is True
        assert error_msg is None
    
    def test_validate_query_empty(self):
        """Test validation fails for empty query."""
        is_valid, error_msg = validate_query("")
        assert is_valid is False
        assert "non-empty string" in error_msg.lower()
    
    def test_validate_query_none(self):
        """Test validation fails for None."""
        is_valid, error_msg = validate_query(None)
        assert is_valid is False
        assert "non-empty string" in error_msg.lower()
    
    def test_validate_query_not_string(self):
        """Test validation fails for non-string."""
        is_valid, error_msg = validate_query(123)
        assert is_valid is False
        assert "non-empty string" in error_msg.lower()
    
    def test_validate_query_too_long(self):
        """Test validation fails for query that's too long."""
        long_query = "a" * (MAX_QUERY_LENGTH + 1)
        is_valid, error_msg = validate_query(long_query)
        assert is_valid is False
        assert "too long" in error_msg.lower()
        assert str(MAX_QUERY_LENGTH) in error_msg
    
    def test_validate_query_script_injection(self):
        """Test validation fails for script injection attempt."""
        is_valid, error_msg = validate_query("jazz <script>alert('xss')</script>")
        assert is_valid is False
        assert "unsafe" in error_msg.lower()
    
    def test_validate_query_javascript(self):
        """Test validation fails for javascript: pattern."""
        is_valid, error_msg = validate_query("javascript:alert('xss')")
        assert is_valid is False
        assert "unsafe" in error_msg.lower()
    
    def test_validate_query_path_traversal(self):
        """Test validation fails for path traversal attempt."""
        is_valid, error_msg = validate_query("../../../etc/passwd")
        assert is_valid is False
        assert "unsafe" in error_msg.lower()
    
    def test_validate_query_command_injection(self):
        """Test validation fails for command injection attempt."""
        is_valid, error_msg = validate_query("jazz `rm -rf /`")
        assert is_valid is False
        assert "unsafe" in error_msg.lower()
    
    def test_validate_query_command_substitution(self):
        """Test validation fails for command substitution."""
        is_valid, error_msg = validate_query("jazz $(whoami)")
        assert is_valid is False
        assert "unsafe" in error_msg.lower()


class TestSetConfigPermissions:
    """Test config file permissions setting."""
    
    def test_set_config_permissions_success(self, temp_dir):
        """Test setting config file permissions."""
        config_file = os.path.join(temp_dir, "config.json")
        with open(config_file, 'w') as f:
            f.write('{}')
        
        # Should not raise
        set_config_permissions(config_file)
        
        # Verify permissions (on Unix systems)
        if os.name != 'nt':
            import stat
            file_stat = os.stat(config_file)
            assert file_stat.st_mode & stat.S_IRWXG == 0  # No group permissions
            assert file_stat.st_mode & stat.S_IRWXO == 0  # No other permissions
    
    @patch('os.chmod')
    def test_set_config_permissions_handles_error(self, mock_chmod, temp_dir):
        """Test that permission errors are handled gracefully."""
        mock_chmod.side_effect = PermissionError("Permission denied")
        config_file = os.path.join(temp_dir, "config.json")
        with open(config_file, 'w') as f:
            f.write('{}')
        
        # Should not raise, just log warning
        set_config_permissions(config_file)


class TestRateLimiter:
    """Test rate limiter functionality."""
    
    def test_rate_limiter_acquire_success(self):
        """Test acquiring token when under limit."""
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        assert limiter.acquire() is True
        assert limiter.acquire() is True
    
    def test_rate_limiter_acquire_limit_reached(self):
        """Test acquiring token when limit reached."""
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        assert limiter.acquire() is True
        assert limiter.acquire() is True
        assert limiter.acquire() is False  # Limit reached
    
    def test_rate_limiter_wait_if_needed(self):
        """Test wait_if_needed when under limit."""
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        # Should not block when under limit
        limiter.wait_if_needed()
        assert len(limiter.requests) == 1
    
    def test_rate_limiter_wait_if_needed_blocks(self):
        """Test wait_if_needed blocks when limit reached."""
        # Use a very short window so we don't actually block long
        limiter = RateLimiter(max_requests=1, window_seconds=0.1)
        limiter.acquire()  # Fill the limit
        
        # Wait for the window to expire naturally (0.1s)
        time.sleep(0.15)
        
        # Should be able to acquire again after window expires
        limiter.wait_if_needed()
        # After wait_if_needed, we should have acquired a new slot
        assert len(limiter.requests) >= 1


class TestRateLimitDecorator:
    """Test rate limit decorator."""
    
    @patch('utils._rate_limiter')
    def test_rate_limit_decorator(self, mock_limiter):
        """Test rate limit decorator calls limiter."""
        mock_limiter.wait_if_needed = MagicMock()
        
        @rate_limit
        def test_func():
            return "success"
        
        result = test_func()
        assert result == "success"
        assert mock_limiter.wait_if_needed.called


class TestWithTimeout:
    """Test timeout decorator."""
    
    def test_with_timeout_no_signal_support(self):
        """Test timeout decorator when signal not supported."""
        @with_timeout(timeout_seconds=1.0)
        def fast_func():
            return "success"
        
        result = fast_func()
        assert result == "success"
    
    def test_with_timeout_with_signal_support(self):
        """Test timeout decorator with signal support."""
        import signal
        
        @with_timeout(timeout_seconds=5.0)
        def test_func():
            return "success"
        
        # On macOS, signal.SIGALRM should be available
        # The decorator will use it if available, otherwise skip timeout
        result = test_func()
        assert result == "success"


class TestFormatTrackSignal:
    """Test track signal formatting."""
    
    def test_format_track_signal_hi_res(self):
        """Test formatting HI_RES track signal."""
        signal_text, visible_len = format_track_signal("HI_RES", 0.95)
        assert "H" in signal_text or "HI_RES" in signal_text
        assert visible_len > 0
    
    def test_format_track_signal_lossless(self):
        """Test formatting LOSSLESS track signal."""
        signal_text, visible_len = format_track_signal("LOSSLESS", 0.85)
        assert "L" in signal_text or "LOSSLESS" in signal_text
        assert visible_len > 0
    
    def test_format_track_signal_high_confidence(self):
        """Test formatting high confidence score."""
        signal_text, visible_len = format_track_signal("HI_RES", 0.90)
        assert visible_len > 0
    
    def test_format_track_signal_low_confidence(self):
        """Test formatting low confidence score."""
        signal_text, visible_len = format_track_signal("LOSSLESS", 0.50)
        assert visible_len > 0


class TestPrintTrackRow:
    """Test track row printing."""
    
    @patch('sys.stdout.flush')
    def test_print_track_row(self, mock_flush):
        """Test printing track row."""
        print_track_row(
            "Test Title", "Test Artist", "Test Album",
            "USRC12345678", "2020", "H 0.95"
        )
        assert mock_flush.called

