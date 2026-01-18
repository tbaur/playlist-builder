# Playlist Builder Test Suite

Comprehensive test suite for playlist-builder using pytest.

## Test Structure

```
tests/
├── __init__.py
├── conftest.py          # Shared fixtures and configuration
├── test_constants.py    # Tests for constants module
├── test_utils.py        # Tests for utility functions
├── test_tidal_engine.py # Tests for Tidal API integration
├── test_main.py         # Tests for main module
└── test_integration.py  # End-to-end integration tests
```

## Running Tests

### Install Test Dependencies

```bash
pip install -r requirements-test.txt
```

### Run All Tests

```bash
pytest
```

### Run Specific Test Files

```bash
pytest tests/test_constants.py
pytest tests/test_utils.py
pytest tests/test_tidal_engine.py
pytest tests/test_main.py
pytest tests/test_integration.py
```

### Run with Coverage

```bash
pytest --cov=. --cov-report=html

# View HTML report
open htmlcov/index.html
```

### Run Specific Test Classes

```bash
pytest tests/test_utils.py::TestSetupLogging
pytest tests/test_tidal_engine.py::TestTidalProvider
```

### Run with Verbose Output

```bash
pytest -v
```

### Run with Markers

```bash
pytest -m unit          # Run only unit tests
pytest -m integration   # Run only integration tests
```

## Test Coverage

**Current Statistics:**
- **Total Tests**: 155 tests (all passing ✅)
- **Code Coverage**: 85% (targeting 90%)
- **Test Execution Time**: ~70 seconds
- **Test Pass Rate**: 100%

**Coverage by Module:**
- `utils.py`: 99% - Logging, retry logic, validation, rate limiting, timeouts
- `metrics.py`: 98% - Metrics collection, reporting, health status
- `constants.py`: 94% - All constants, security settings, model definitions
- `tidal_engine.py`: 99% - Authentication, track resolution, publishing, error handling, Keychain integration
- `main.py`: 99% - CLI, orchestration, command handlers, Keychain integration
- `spinner.py`: 100% - Terminal spinner functionality
- `keychain_utils.py`: 100% - macOS Keychain operations for secure secret storage
- All test files: 100% coverage

The test suite covers:

- **Constants**: All path constants, ANSI colors, configuration constants, Gemini models, security constants
- **Utils**: Logging setup, retry logic with exponential backoff, configuration validation, input validation, rate limiting, timeout decorators
- **Tidal Engine**: Authentication (success and error cases), track resolution, playlist publishing, error handling, exception handling, Keychain integration
- **Main Module**: Track dataclass, MusicCurator class, help function, main function logic, Keychain integration
- **Keychain Utils**: Secret storage, retrieval, deletion, session data management, migration from config
- **Integration**: End-to-end workflows, model selection, error handling
- **Security**: Input validation, config file permissions, rate limiting, subprocess security, Keychain security
- **Edge Cases**: Empty inputs, malformed data, timeout scenarios, resource cleanup, MagicMock handling

## Mocking

Tests use extensive mocking to avoid external API calls:

- **Gemini API**: Mocked using `unittest.mock` to simulate API responses
- **Tidal API**: Mocked using `unittest.mock` to simulate Tidal session and responses
- **macOS Keychain**: Mocked using `unittest.mock` to simulate Keychain operations (for cross-platform testing)
- **File System**: Uses temporary directories for file operations
- **System Platform**: Mocked `sys.platform` for testing Keychain behavior on different platforms

## Fixtures

Common fixtures available in `conftest.py`:

- `temp_dir`: Temporary directory for test files
- `temp_config_file`: Temporary config file with valid configuration
- `sample_config`: Sample configuration dictionary
- `mock_gemini_client`: Mocked Gemini API client
- `mock_tidal_session`: Mocked Tidal API session
- `sample_track_data`: Sample track data dictionary
- `sample_tracks_list`: List of sample tracks

## Writing New Tests

When adding new tests:

1. Follow pytest naming conventions: `test_*.py` files, `test_*` functions
2. Use fixtures from `conftest.py` when possible
3. Mock external dependencies (APIs, file system)
4. Test both success and failure cases
5. Add docstrings explaining what each test validates
6. Use descriptive test names that explain the scenario

Example:

```python
def test_function_success_case():
    """Test that function succeeds with valid input."""
    result = function(valid_input)
    assert result == expected_output

def test_function_handles_invalid_input():
    """Test that function raises error with invalid input."""
    with pytest.raises(ValueError):
        function(invalid_input)
```

## Continuous Integration

Tests are designed to run in CI/CD environments:

- No external API calls (all mocked)
- No file system dependencies (uses temp directories)
- Fast execution (< 5 seconds)
- Deterministic results

