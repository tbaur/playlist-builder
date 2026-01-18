# Playlist Builder

[![Tests](https://github.com/tbaur/playlist-builder/actions/workflows/test.yml/badge.svg)](https://github.com/tbaur/playlist-builder/actions/workflows/test.yml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![macOS](https://img.shields.io/badge/macOS-10.15%2B-lightgrey.svg)](https://www.apple.com/macos/)
[![Code Coverage](https://img.shields.io/badge/coverage-80%25-green.svg)](htmlcov/index.html)
[![Code Style](https://img.shields.io/badge/code%20style-PEP8-blue.svg)](https://www.python.org/dev/peps/pep-0008/)

An AI-powered music discovery tool that uses Google Gemini to ground natural language queries into real-world streaming nodes. It audits every track for audio quality, ISRC provenance, and metadata similarity before syncing to your Tidal library.

## Features

- **AI-Powered Discovery**: Uses Gemini 3 models to understand natural language music queries
- **Quality Auditing**: Automatically identifies Hi-Res (24-bit) and HiFi (16-bit) lossless streams
- **Tidal Integration**: Seamlessly syncs discovered tracks to your Tidal playlists
- **Spotify Integration** *(Experimental)*: Publish playlists to Spotify
- **Metadata Matching**: Forensic-level track matching with similarity scoring
- **Real-time Metrics**: Comprehensive performance and health reporting
- **Security Hardened**: macOS Keychain integration for secrets, input validation, rate limiting
- **Production Ready**: Comprehensive error handling, timeout management, resource cleanup
- **CI/CD Ready**: GitHub Actions workflows for automated testing

## Requirements

- Python 3.12+
- macOS (designed for native macOS experience)
- Google Gemini API key
- Tidal account

## Installation

Run the installation script:

```bash
./install.sh
```

This will:
- Create a virtual environment
- Install dependencies (`google-genai`, `tidalapi`)
- Install test dependencies (`pytest`, `pytest-cov`, etc.)
- Create a symlink for easy command access
- **On macOS**: Offer to store secrets in Keychain (recommended) or config.json

## Safe & Isolated Installation

**100% Safe to Try** - This tool is completely isolated and won't affect your system:

- ✅ **Isolated Virtual Environment**: All dependencies installed in `~/.config/playlist-builder/.venv` (your home directory)
- ✅ **User Directory Only**: All files stored in `~/.config/playlist-builder` - no system-wide changes
- ✅ **No System Python Changes**: Doesn't modify system Python, doesn't require admin privileges
- ✅ **No Global Packages**: Dependencies only in isolated venv - won't conflict with other Python projects
- ✅ **Easy to Remove**: Delete one directory to completely uninstall (see below)
- ✅ **Sandboxed**: All operations are contained within your user directory

### Complete Removal

If you want to completely remove playlist-builder:

```bash
# Remove the installation directory
rm -rf ~/.config/playlist-builder

# Remove the symlink (if created)
rm ~/local/bin/playlist-builder

# On macOS: Optionally remove Keychain entries (if you used Keychain storage)
# Open Keychain Access app and search for "com.playlist-builder" to remove entries
# Or use: playlist-builder reset (before removing directory) to clear Keychain
```

That's it! The virtual environment, all dependencies, configuration, and cache files are removed. No system files touched, no global Python packages to uninstall, no traces left behind.

**Note**: If you stored secrets in macOS Keychain, you may want to run `playlist-builder reset` before removing the directory to clear Keychain entries, or manually remove them from Keychain Access.

### Reset Configuration

To start fresh with default settings:

```bash
playlist-builder reset
```

This clears your API keys, OAuth tokens, and cache while keeping the installation intact.

## Configuration

After installation, you'll need to configure:

1. **Gemini API Key**: Get one from [Google AI Studio](https://makersuite.google.com/app/apikey)
   - The API key is securely stored in macOS Keychain (not in config files)
2. **Tidal Authentication**: Run any command to trigger OAuth flow
   - OAuth tokens are securely stored in macOS Keychain

**Security Note**: On macOS, all secrets (API keys and OAuth tokens) are stored in the macOS Keychain, not in plain text files. The `config.json` file only contains non-sensitive preferences.

## Usage

### Query for Tracks

```bash
playlist-builder query "Top audiophile recordings from April 1977"
playlist-builder query "Jazz classics" --model 3-pro --limit 20
```

### Publish to Tidal

```bash
playlist-builder publish tidal --name "My Playlist" --replace
```

### Publish to Spotify (EXPERIMENTAL)

```bash
playlist-builder publish spotify --name "My Playlist" --replace
```

> ⚠️ **Experimental**: Spotify support is experimental. You'll need to:
> 1. Create a Spotify Developer App at https://developer.spotify.com/dashboard
> 2. Set redirect URI to `http://localhost:8888/callback`
> 3. Store credentials:
>    ```bash
>    playlist-builder keychain set SPOTIFY_CLIENT_ID
>    playlist-builder keychain set SPOTIFY_CLIENT_SECRET
>    ```

### Keychain Management (macOS)

Manage secrets securely in macOS Keychain:

```bash
playlist-builder keychain set GEMINI_API_KEY              # Prompts for API key
playlist-builder keychain set CUSTOM_KEY "value"          # Store any secret
playlist-builder keychain get GEMINI_API_KEY              # Retrieve a secret
playlist-builder keychain list                            # List all stored secrets
playlist-builder keychain delete CUSTOM_KEY               # Delete a secret
```

**Note**: Keychain commands are only available on macOS. On other platforms, secrets are stored in `config.json`.

### Other Commands

```bash
playlist-builder --help              # Show help
playlist-builder reset               # Wipe credentials and cache
playlist-builder rebuild             # Rebuild virtual environment
playlist-builder --run-code-tests    # Run test suite
playlist-builder --run-code-tests --coverage --verbose  # Run tests with coverage
```

## Models

Available Gemini models:
- `3-pro` - Gemini 3 Pro (best quality)
- `3-flash` - Gemini 3 Flash (default, fast)
- `3-image` - Gemini 3 with image support
- `2-flash` - Gemini 2 Flash (legacy)
- `2-pro` - Gemini 2 Pro (legacy)

## Understanding the Signal

- **H (HI-RES)**: 24-bit / Studio Master quality stream identified
- **L (HiFi)**: 16-bit / Lossless CD-quality stream identified
- **1.00**: Forensic match. Title and Artist are perfectly aligned
- **0.75**: Normalized match. Minor naming variations were resolved

## Testing

Run the test suite:

```bash
playlist-builder --run-code-tests
# or
pytest
```

Run with coverage:

```bash
playlist-builder --run-code-tests --coverage
# or
pytest --cov=. --cov-report=html
```

### Test Statistics

- **Total Tests**: 173 tests (all passing ✅)
- **Code Coverage**: 80%
- **Test Files**: 8 comprehensive test modules
- **Coverage by Module**:
  - `spinner.py`: 100%
  - `metrics.py`: 98%
  - `constants.py`: 95%
  - `tidal_engine.py`: 85% (with Keychain integration)
  - `utils.py`: 74%
  - `main.py`: 38% (CLI entry point, tested via integration tests)
  - `keychain_utils.py`: 23% (macOS-specific, tested on macOS CI)
  - All test files: 100%

All tests pass successfully and cover critical paths including error handling, edge cases, security features, and Keychain integration.

## Project Structure

```
playlist-builder/
├── main.py              # Main orchestration and CLI
├── tidal_engine.py      # Tidal API integration
├── spotify_engine.py    # Spotify API integration (EXPERIMENTAL)
├── constants.py         # Shared constants and security settings
├── utils.py            # Utility functions (validation, rate limiting)
├── spinner.py          # Terminal spinner
├── metrics.py          # Metrics collection
├── keychain_utils.py   # macOS Keychain integration for secrets
├── install.sh          # Installation script
├── requirements.txt    # Runtime dependencies
├── requirements-test.txt  # Test dependencies
├── .github/workflows/  # CI/CD workflows
│   ├── test.yml        # Main test workflow
│   └── quick-test.yml  # Quick PR test workflow
├── tests/              # Comprehensive test suite (173 tests)
│   ├── test_main.py
│   ├── test_tidal_engine.py
│   ├── test_utils.py
│   ├── test_metrics.py
│   ├── test_spinner.py
│   ├── test_spotify_engine.py
│   ├── test_constants.py
│   ├── test_integration.py
│   └── conftest.py
├── CHANGELOG.md        # Version history
├── SECURITY.md         # Security policy
├── CONTRIBUTORS.md     # Project contributors
└── docs/               # Additional documentation
    ├── AUDIT_REPORT.md
    ├── CODE_EVALUATION.md
    ├── FIXES_APPLIED.md
    ├── TIDAL_INTEGRATION.md
    └── SPOTIFY_INTEGRATION.md
```

## Documentation

- [CHANGELOG.md](CHANGELOG.md) - Version history
- [SECURITY.md](SECURITY.md) - Security policy and reporting
- [docs/TIDAL_INTEGRATION.md](docs/TIDAL_INTEGRATION.md) - Tidal API integration details
- [docs/SPOTIFY_INTEGRATION.md](docs/SPOTIFY_INTEGRATION.md) - Spotify API integration (experimental)
- [docs/AUDIT_REPORT.md](docs/AUDIT_REPORT.md) - Security and code audit findings

## Version

**v1.0.0** - Initial Release

- ✅ All 173 tests passing with 80% code coverage
- ✅ macOS Keychain integration for secure secrets
- ✅ Enhanced security with hardened subprocess calls
- ✅ JSON size limits (DoS protection)
- ✅ Path validation (traversal/symlink protection)
- ✅ Secure API key input (getpass)
- ✅ GitHub Actions CI/CD workflows

## Contributing

We welcome contributions! Please see:
- [CONTRIBUTING.md](CONTRIBUTING.md) - Contribution guidelines
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) - Community standards
- [SECURITY.md](SECURITY.md) - Security policy and reporting

## License

Copyright 2025 tbaur

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

See [CONTRIBUTORS.md](CONTRIBUTORS.md) for a list of contributors.

