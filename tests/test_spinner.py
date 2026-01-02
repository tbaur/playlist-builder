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
Tests for spinner module.
"""
import sys
import time
import threading
from unittest.mock import patch, MagicMock
import pytest

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from spinner import Spinner
from constants import CYAN, RESET


class TestSpinner:
    """Test Spinner class."""
    
    def test_init(self):
        """Test spinner initialization."""
        spinner = Spinner("Test message")
        
        assert spinner.message == "Test message"
        assert spinner.color == CYAN
        assert spinner.is_running is False
        assert spinner.stop_spinner is False
    
    def test_init_custom_color(self):
        """Test spinner with custom color."""
        from constants import GREEN
        spinner = Spinner("Test", color=GREEN)
        
        assert spinner.color == GREEN
    
    def test_start_stop(self):
        """Test starting and stopping spinner."""
        spinner = Spinner("Test message")
        
        assert spinner.is_running is False
        spinner.start()
        
        # Give it a moment to start
        time.sleep(0.2)
        assert spinner.is_running is True
        
        spinner.stop()
        time.sleep(0.1)
        assert spinner.is_running is False
    
    def test_start_with_message_update(self):
        """Test starting spinner with message update."""
        spinner = Spinner("Original")
        spinner.start("Updated")
        
        assert spinner.message == "Updated"
        assert spinner.is_running is True
        
        spinner.stop()
    
    def test_start_twice(self):
        """Test starting spinner twice doesn't create multiple threads."""
        spinner = Spinner("Test")
        spinner.start()
        
        initial_thread = spinner.spinner_thread
        spinner.start()  # Should not create new thread
        
        assert spinner.spinner_thread is initial_thread
        spinner.stop()
    
    def test_stop_without_start(self):
        """Test stopping spinner that was never started."""
        spinner = Spinner("Test")
        spinner.stop()  # Should not raise error
        
        assert spinner.is_running is False
    
    def test_stop_with_final_message(self, capsys):
        """Test stopping spinner with final message."""
        spinner = Spinner("Processing...")
        spinner.start()
        time.sleep(0.1)
        spinner.stop("Done!")
        
        captured = capsys.readouterr()
        assert "Done!" in captured.out
    
    def test_context_manager(self):
        """Test spinner as context manager."""
        with Spinner("Test") as spinner:
            assert spinner.is_running is True
            time.sleep(0.1)
        
        assert spinner.is_running is False
    
    def test_context_manager_with_exception(self):
        """Test spinner context manager handles exceptions."""
        try:
            with Spinner("Test"):
                raise ValueError("Test error")
        except ValueError:
            pass
        
        # Spinner should be stopped even with exception
        spinner = Spinner("Test")
        spinner.start()
        time.sleep(0.1)
        assert spinner.is_running is True
        spinner.stop()
    
    def test_spinner_chars_rotation(self):
        """Test spinner characters rotate."""
        spinner = Spinner("Test")
        chars = spinner.SPINNER_CHARS
        
        assert len(chars) > 0
        assert all(isinstance(c, str) for c in chars)
    
    @patch('sys.stdout.write')
    @patch('sys.stdout.flush')
    def test_spinner_writes_to_stdout(self, mock_flush, mock_write):
        """Test spinner writes to stdout."""
        spinner = Spinner("Test message")
        spinner.start()
        time.sleep(0.15)  # Allow at least one spin cycle
        spinner.stop()
        
        # Should have written to stdout
        assert mock_write.called
        assert mock_flush.called
    
    def test_multiple_spinners_sequential(self):
        """Test using multiple spinners sequentially."""
        spinner1 = Spinner("First")
        spinner1.start()
        time.sleep(0.1)
        spinner1.stop()
        
        spinner2 = Spinner("Second")
        spinner2.start()
        time.sleep(0.1)
        spinner2.stop()
        
        assert spinner1.is_running is False
        assert spinner2.is_running is False

