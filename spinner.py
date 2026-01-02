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
Spinner utility for showing progress during long operations.
"""
import sys
import threading
import time
from typing import Optional

from constants import CYAN, RESET

class Spinner:
    """Simple spinner for terminal output."""
    
    SPINNER_CHARS = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
    
    def __init__(self, message: str = "", color: str = CYAN):
        """
        Initialize spinner.
        
        Args:
            message: Message to display with spinner
            color: ANSI color code for spinner
        """
        self.message = message
        self.color = color
        self.spinner_thread: Optional[threading.Thread] = None
        self.stop_spinner = False
        self.is_running = False
    
    def _spin(self):
        """Internal spinner animation loop."""
        index = 0
        while not self.stop_spinner:
            char = self.SPINNER_CHARS[index % len(self.SPINNER_CHARS)]
            sys.stdout.write(f'\r{self.color}{char}{RESET} {self.message}')
            sys.stdout.flush()
            time.sleep(0.1)
            index += 1
    
    def start(self, message: Optional[str] = None):
        """
        Start the spinner.
        
        Args:
            message: Optional message to update
        """
        if message:
            self.message = message
        if self.is_running:
            return
        
        self.stop_spinner = False
        self.is_running = True
        self.spinner_thread = threading.Thread(target=self._spin, daemon=True)
        self.spinner_thread.start()
    
    def stop(self, final_message: Optional[str] = None):
        """
        Stop the spinner.
        
        Args:
            final_message: Optional final message to display
        """
        if not self.is_running:
            return
        
        self.stop_spinner = True
        if self.spinner_thread:
            self.spinner_thread.join(timeout=0.5)
        
        # Clear spinner line
        sys.stdout.write('\r' + ' ' * (len(self.message) + 3) + '\r')
        sys.stdout.flush()
        
        if final_message:
            sys.stdout.write(f'{final_message}\n')
            sys.stdout.flush()
        
        self.is_running = False
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()

