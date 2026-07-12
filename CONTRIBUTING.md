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
6. Submit a pull request with a **Conventional Commit** title

### Commit / PR titles

Follow [Conventional Commits](https://www.conventionalcommits.org). PR titles
drive automated releases via release-please, so use prefixes like:

- `feat:` — New feature
- `fix:` — Bug fix
- `docs:` — Documentation only
- `test:` — Test changes
- `refactor:` — Code refactoring
- `chore:` / `ci:` — Maintenance (no release)

Example: `feat: add /shuffle chat command`

> `CHANGELOG.md` is generated automatically by release-please from your
> Conventional Commit / PR titles — do not edit it by hand for routine
> releases. See [RELEASING.md](RELEASING.md).

### PR checklist

- [ ] Tests added/updated
- [ ] Tests pass (`pytest`)
- [ ] Documentation updated if needed
- [ ] Descriptive PR title (Conventional Commits)

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
