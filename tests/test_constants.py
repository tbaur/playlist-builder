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
Tests for constants module.
"""
import os
import pytest
from constants import (
    BASE_DIR, VENV_DIR, CONFIG_FILE, CACHE_FILE, LOG_FILE,
    BOLD, RED, GREEN, YELLOW, CYAN, BLUE, MAGENTA, RESET, DIM, HR,
    DEFAULT_LIMIT, MAX_WORKERS, MIN_MATCH_SCORE, HIGH_CONFIDENCE_SCORE,
    HI_RES_QUALITY_WEIGHT, LOSSLESS_QUALITY_WEIGHT, DEFAULT_QUALITY_WEIGHT,
    GEMINI_MODEL, GEMINI_3_PRO, GEMINI_3_FLASH, GEMINI_3_PRO_IMAGE,
    GEMINI_2_FLASH, GEMINI_2_PRO, AVAILABLE_MODELS,
    GEMINI_TEMPERATURE, MAX_RETRIES, RETRY_DELAY_BASE, GEMINI_THINKING_LEVEL,
    ConfigPaths
)


class TestPaths:
    """Test path constants."""
    
    def test_base_dir_is_expanded(self):
        """Test that BASE_DIR uses expanded user path."""
        assert BASE_DIR.startswith(os.path.expanduser("~"))
        assert "playlist-builder" in BASE_DIR
    
    def test_venv_dir(self):
        """Test VENV_DIR is correct."""
        assert VENV_DIR == os.path.join(BASE_DIR, ".venv")
    
    def test_config_file_path(self):
        """Test CONFIG_FILE path."""
        assert CONFIG_FILE == os.path.join(BASE_DIR, "config.json")
    
    def test_cache_file_path(self):
        """Test CACHE_FILE path."""
        assert CACHE_FILE == os.path.join(BASE_DIR, "last_query.json")
    
    def test_log_file_path(self):
        """Test LOG_FILE path."""
        assert LOG_FILE == os.path.join(BASE_DIR, "playlist-builder.log")
    
    def test_config_paths_dataclass(self):
        """Test ConfigPaths dataclass."""
        paths = ConfigPaths()
        assert paths.base_dir == BASE_DIR
        assert paths.venv_dir == VENV_DIR
        assert paths.config_file == CONFIG_FILE
        assert paths.cache_file == CACHE_FILE
        assert paths.log_file == LOG_FILE


class TestANSIColors:
    """Test ANSI color codes."""
    
    def test_all_colors_are_strings(self):
        """Test that all color constants are strings."""
        colors = [BOLD, RED, GREEN, YELLOW, CYAN, BLUE, MAGENTA, RESET, DIM]
        assert all(isinstance(c, str) for c in colors)
    
    def test_colors_start_with_escape(self):
        """Test that ANSI codes start with escape sequence."""
        assert BOLD.startswith("\033")
        assert RED.startswith("\033")
        assert GREEN.startswith("\033")
    
    def test_hr_contains_blue(self):
        """Test HR constant contains blue color."""
        assert BLUE in HR


class TestConfigurationConstants:
    """Test configuration constants."""
    
    def test_default_limit(self):
        """Test DEFAULT_LIMIT is a positive integer."""
        assert isinstance(DEFAULT_LIMIT, int)
        assert DEFAULT_LIMIT > 0
    
    def test_max_workers(self):
        """Test MAX_WORKERS is a positive integer."""
        assert isinstance(MAX_WORKERS, int)
        assert MAX_WORKERS > 0
    
    def test_match_scores(self):
        """Test match score constants."""
        assert 0 <= MIN_MATCH_SCORE <= 1
        assert 0 <= HIGH_CONFIDENCE_SCORE <= 1
        assert MIN_MATCH_SCORE < HIGH_CONFIDENCE_SCORE
    
    def test_quality_weights(self):
        """Test quality weight constants."""
        assert HI_RES_QUALITY_WEIGHT > LOSSLESS_QUALITY_WEIGHT
        assert LOSSLESS_QUALITY_WEIGHT > DEFAULT_QUALITY_WEIGHT
        assert DEFAULT_QUALITY_WEIGHT >= 0


class TestGeminiModels:
    """Test Gemini model constants."""
    
    def test_gemini_3_models_exist(self):
        """Test Gemini 3 models are defined."""
        assert GEMINI_3_PRO == "gemini-3-pro-preview"
        assert GEMINI_3_FLASH == "gemini-3-flash-preview"
        assert GEMINI_3_PRO_IMAGE == "gemini-3-pro-image-preview"
    
    def test_gemini_2_models_exist(self):
        """Test Gemini 2 models are defined."""
        assert GEMINI_2_FLASH == "gemini-2.0-flash"
        assert GEMINI_2_PRO == "gemini-2.0-pro"
    
    def test_default_model_is_gemini_3(self):
        """Test default model is Gemini 3 Flash."""
        assert GEMINI_MODEL == GEMINI_3_FLASH
        assert GEMINI_MODEL.startswith("gemini-3")
    
    def test_available_models_dict(self):
        """Test AVAILABLE_MODELS dictionary."""
        assert isinstance(AVAILABLE_MODELS, dict)
        assert "3-pro" in AVAILABLE_MODELS
        assert "3-flash" in AVAILABLE_MODELS
        assert "3-image" in AVAILABLE_MODELS
        assert "2-flash" in AVAILABLE_MODELS
        assert "2-pro" in AVAILABLE_MODELS
        
        assert AVAILABLE_MODELS["3-pro"] == GEMINI_3_PRO
        assert AVAILABLE_MODELS["3-flash"] == GEMINI_3_FLASH
    
    def test_thinking_level(self):
        """Test thinking level constant."""
        assert GEMINI_THINKING_LEVEL in ["low", "high", "medium", "minimal"]
        assert GEMINI_THINKING_LEVEL == "low"  # Default for speed


class TestAPISettings:
    """Test API settings constants."""
    
    def test_temperature(self):
        """Test temperature constant."""
        assert isinstance(GEMINI_TEMPERATURE, (int, float))
        assert 0 <= GEMINI_TEMPERATURE <= 2
    
    def test_max_retries(self):
        """Test MAX_RETRIES is positive."""
        assert isinstance(MAX_RETRIES, int)
        assert MAX_RETRIES > 0
    
    def test_retry_delay_base(self):
        """Test RETRY_DELAY_BASE is positive."""
        assert isinstance(RETRY_DELAY_BASE, (int, float))
        assert RETRY_DELAY_BASE > 0
    
    def test_reset_constant(self):
        """Test RESET constant."""
        from constants import RESET
        assert isinstance(RESET, str)
        assert RESET.startswith("\033")
    
    def test_dim_constant(self):
        """Test DIM constant."""
        from constants import DIM
        assert isinstance(DIM, str)
        assert DIM.startswith("\033")
    
    def test_security_constants(self):
        """Test security and performance constants."""
        from constants import (
            MAX_QUERY_LENGTH, API_TIMEOUT_SECONDS,
            RATE_LIMIT_REQUESTS_PER_MINUTE, CONFIG_FILE_PERMISSIONS
        )
        assert isinstance(MAX_QUERY_LENGTH, int)
        assert MAX_QUERY_LENGTH > 0
        assert isinstance(API_TIMEOUT_SECONDS, float)
        assert API_TIMEOUT_SECONDS > 0
        assert isinstance(RATE_LIMIT_REQUESTS_PER_MINUTE, int)
        assert RATE_LIMIT_REQUESTS_PER_MINUTE > 0
        assert isinstance(CONFIG_FILE_PERMISSIONS, int)

