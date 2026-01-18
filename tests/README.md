# Test Suite

Comprehensive pytest test suite for playlist-builder.

## Running Tests

```bash
pytest                              # Run all tests
pytest -v                           # Verbose output
pytest tests/test_main.py           # Specific file
pytest --cov=. --cov-report=html    # With coverage
bash run_tests.sh                   # Using test runner
```

## Test Files

| File | Coverage |
|------|----------|
| `test_main.py` | CLI, Track, MusicCurator, ChatSession |
| `test_tidal_engine.py` | Tidal API integration |
| `test_utils.py` | Validation, rate limiting, utilities |
| `test_metrics.py` | Performance metrics |
| `test_spinner.py` | Terminal UI |
| `test_constants.py` | Configuration constants |
| `test_integration.py` | End-to-end workflows |
| `conftest.py` | Shared fixtures |

## Fixtures

Available in `conftest.py`:

- `temp_dir` — Temporary directory
- `temp_config_file` — Config file with valid settings
- `sample_config` — Configuration dictionary
- `mock_gemini_client` — Mocked Gemini API
- `mock_tidal_session` — Mocked Tidal session

## Writing Tests

```python
def test_feature_success():
    """Test that feature succeeds with valid input."""
    result = feature(valid_input)
    assert result == expected

def test_feature_handles_error():
    """Test that feature raises error on invalid input."""
    with pytest.raises(ValueError):
        feature(invalid_input)
```

Guidelines:
- Mock external APIs (Gemini, Tidal, Keychain)
- Test success and failure cases
- Use descriptive names
- Add docstrings
