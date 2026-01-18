# Contributing to Playlist Builder

Thank you for your interest in contributing to Playlist Builder! This document provides guidelines and instructions for contributing.

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in [Issues](https://github.com/tbaur/playlist-builder/issues)
2. If not, create a new issue with:
   - Clear title and description
   - Steps to reproduce
   - Expected vs actual behavior
   - macOS version and Python version
   - Relevant error messages or logs

### Suggesting Features

1. Check [Issues](https://github.com/tbaur/playlist-builder/issues) for existing proposals
2. Open a new issue with:
   - Clear description of the feature
   - Use case and motivation
   - Potential implementation approach (if you have ideas)

### Pull Requests

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/your-feature-name`
3. **Make your changes**:
   - Follow the existing code style
   - Add tests for new functionality
   - Update documentation as needed
   - Ensure all tests pass
4. **Commit your changes**: Use clear, descriptive commit messages
5. **Push to your fork**: `git push origin feature/your-feature-name`
6. **Open a Pull Request**: Provide a clear description of changes

## Development Setup

### Prerequisites

- Python 3.12+
- macOS (recommended, for Keychain integration)
- Git
- Google Gemini API key
- Tidal account (optional, for testing Tidal integration)

### Setup

```bash
# Clone your fork
git clone git@github.com:YOUR_USERNAME/playlist-builder.git
cd playlist-builder

# Run installation script
./install.sh

# Or manually create virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-test.txt
```

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html --cov-report=term-missing

# Run specific test file
pytest tests/test_main.py -v

# Or use the test runner script
bash run_tests.sh
```

### Code Style

- Follow PEP 8 style guidelines
- Use type hints for all functions
- Add docstrings to all public functions
- Keep functions focused and small
- Use descriptive variable names
- Maximum line length: 100 characters

### Test Requirements

- New features must include tests
- Aim for high test coverage (currently 85%, targeting 90%)
- Tests should be fast and isolated
- Use mocking for external dependencies (Gemini API, Tidal API, Keychain)
- All tests must pass before submitting PR

## Project Structure

```
playlist-builder/
├── main.py              # Main orchestration and CLI
├── tidal_engine.py      # Tidal API integration
├── constants.py         # Shared constants and security settings
├── utils.py             # Utility functions (validation, rate limiting)
├── spinner.py           # Terminal spinner
├── metrics.py           # Metrics collection
├── keychain_utils.py    # macOS Keychain integration
├── install.sh           # Installation script
├── run_tests.sh         # Test runner script
├── requirements.txt     # Runtime dependencies
├── requirements-test.txt # Test dependencies
├── .github/workflows/   # CI/CD workflows
│   ├── test.yml         # Main test workflow
│   └── quick-test.yml   # Quick PR test workflow
├── tests/               # Comprehensive test suite (155 tests)
│   ├── test_main.py
│   ├── test_tidal_engine.py
│   ├── test_utils.py
│   ├── test_metrics.py
│   ├── test_spinner.py
│   ├── test_constants.py
│   ├── test_integration.py
│   └── conftest.py
└── docs/                # Documentation
    ├── AUDIT_REPORT.md
    ├── CHANGELOG.md
    ├── CODE_EVALUATION.md
    └── FIXES_APPLIED.md
```

## Areas for Contribution

### High Priority

- **Cross-platform support**: Windows and Linux implementations for Keychain alternatives
- **Additional music providers**: Spotify, Apple Music, YouTube Music integration
- **Performance improvements**: Faster track matching, better caching
- **Documentation**: Examples, tutorials, video guides

### Medium Priority

- **New features**: 
  - Playlist management (edit, merge, deduplicate)
  - Advanced search filters (genre, year, quality)
  - Batch operations
  - Export/import functionality
- **Test coverage**: Increase coverage to 90%+
- **Error handling**: Better error messages and recovery
- **Logging**: Enhanced structured logging features

### Low Priority

- **UI improvements**: Better CLI output formatting, progress bars
- **Code refactoring**: Cleanup and optimization
- **Documentation**: Additional examples and use cases

## Code Review Process

1. All PRs require review before merging
2. Maintainers will review for:
   - Code quality and style
   - Test coverage
   - Documentation updates
   - Backward compatibility
   - Security implications
3. Address feedback promptly
4. Squash commits if requested

## Testing Guidelines

### Unit Tests

- Test individual functions in isolation
- Mock external dependencies (APIs, file system, Keychain)
- Cover edge cases and error conditions
- Use descriptive test names

Example:
```python
def test_validate_query_with_valid_input():
    """Test that valid queries pass validation."""
    result = validate_query("Jazz classics")
    assert result == "Jazz classics"

def test_validate_query_with_empty_string():
    """Test that empty queries raise ValueError."""
    with pytest.raises(ValueError, match="Query cannot be empty"):
        validate_query("")
```

### Integration Tests

- Test interactions between modules
- Use mocking sparingly
- Test realistic workflows
- Verify end-to-end functionality

### Test Coverage

- Aim for 90%+ coverage
- Focus on critical paths
- Don't sacrifice quality for coverage numbers
- Use `pytest --cov` to measure coverage

## Security Considerations

When contributing, please keep security in mind:

1. **Never commit secrets**: API keys, tokens, passwords
2. **Validate all inputs**: User queries, file paths, API responses
3. **Use Keychain for secrets**: On macOS, always use Keychain for sensitive data
4. **Handle errors gracefully**: Don't expose sensitive information in error messages
5. **Follow secure coding practices**: Input validation, output encoding, proper error handling

See [docs/SECURITY.md](docs/SECURITY.md) for detailed security guidelines.

## Documentation

When adding new features:

1. Update `README.md` with usage examples
2. Update `docs/CHANGELOG.md` with changes
3. Add docstrings to all new functions
4. Update man page style help in `main.py` if adding CLI commands
5. Update test documentation in `tests/README.md`

## Commit Message Guidelines

Use clear, descriptive commit messages:

```
Add support for Spotify integration

- Implement Spotify API client
- Add OAuth flow for Spotify
- Add tests for Spotify provider
- Update documentation

Fixes #123
```

Format:
- First line: Brief summary (50 chars or less)
- Blank line
- Detailed description (wrap at 72 chars)
- Reference issues/PRs if applicable

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0, the same license as the project.

## Questions?

- Open an issue for discussion
- Check existing documentation in `docs/`
- Review [README.md](README.md) for project overview
- Check [SECURITY.md](SECURITY.md) for security guidelines

## Recognition

Contributors will be recognized in:
- [docs/CONTRIBUTORS.md](docs/CONTRIBUTORS.md) file
- Release notes in [docs/CHANGELOG.md](docs/CHANGELOG.md)
- GitHub contributors page

Thank you for contributing! 🎉

