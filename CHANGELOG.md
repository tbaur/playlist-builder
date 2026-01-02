# Changelog

All notable changes to playlist-builder will be documented in this file.

## [1.0.0] - 2026-01-02 - Initial Release

### Features

- **AI-Powered Discovery**: Uses Google Gemini 3 models to understand natural language music queries
- **Quality Auditing**: Automatically identifies Hi-Res (24-bit) and HiFi (16-bit) lossless streams
- **Tidal Integration**: Seamlessly syncs discovered tracks to your Tidal playlists
- **Spotify Integration** *(Experimental)*: Publish playlists to Spotify
- **Metadata Matching**: Forensic-level track matching with similarity scoring
- **Real-time Metrics**: Comprehensive performance and health reporting

### Security

- **macOS Keychain Integration**: All secrets (API keys, OAuth tokens) stored securely in Keychain
- Input validation and sanitization for user queries
- Secure config file permissions (600)
- Rate limiting (60 requests/minute) to prevent API abuse
- Subprocess security with absolute path validation
- JSON size limits for DoS protection
- Path validation for traversal/symlink protection
- Secure API key input (getpass)

### Performance

- Configurable timeouts (30s default) for all API calls
- Concurrent track resolution with ThreadPoolExecutor
- Timeout handling for concurrent operations
- Proper resource cleanup with future cancellation
- Connection management and reuse

### Reliability

- Enhanced error handling with specific exception types
- Timeout handling for subprocess operations
- Proper resource cleanup with try/finally blocks
- Edge case validation (empty responses, malformed data)
- Path validation before file operations
- Retry logic with exponential backoff

### Code Quality

- Comprehensive test suite (173 tests, 80% coverage, all passing)
- Complete type hints throughout codebase
- Enhanced docstrings with parameter information
- GitHub Actions CI/CD workflows for automated testing

### Documentation

- Comprehensive README with usage examples
- Security policy (SECURITY.md)
- Code of conduct (CODE_OF_CONDUCT.md)
- Contribution guidelines (CONTRIBUTING.md)
- API integration docs (TIDAL_INTEGRATION.md, SPOTIFY_INTEGRATION.md)
