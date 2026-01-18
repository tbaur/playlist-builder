# Contributing

Thank you for your interest in contributing to Playlist Builder.

## Reporting Issues

1. Check [existing issues](https://github.com/tbaur/playlist-builder/issues) first
2. Include: macOS version, Python version, steps to reproduce, expected vs actual behavior

## Pull Requests

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make changes following the code style below
4. Add tests for new functionality
5. Ensure all tests pass: `pytest`
6. Submit a pull request with a clear description

## Development Setup

```bash
git clone git@github.com:YOUR_USERNAME/playlist-builder.git
cd playlist-builder
./install.sh
pip install -r requirements-test.txt
```

## Code Style

- Follow PEP 8
- Use type hints for all functions
- Add docstrings to public functions
- Maximum line length: 100 characters
- Use f-strings for formatting

## Testing

```bash
pytest                              # Run all tests
pytest tests/test_main.py -v        # Run specific file
pytest --cov=. --cov-report=html    # With coverage
```

Requirements:
- All tests must pass
- New features need tests
- Use mocking for external APIs

## Security

- Never commit secrets
- Use Keychain for sensitive data
- Validate all user inputs
- See [SECURITY.md](SECURITY.md) for details

## License

Contributions are licensed under Apache License 2.0.
