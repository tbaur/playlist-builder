# Changelog

## [1.1.0] - 2026-01-18

### Added

- **Conversational Discovery** — New `chat` command for interactive, context-aware playlist building
  - Session maintains conversation history for iterative refinement
  - Commands: `/save`, `/clear`, `/tracks`, `/quit`
  - Accumulates tracks across multiple queries in a session

### Changed

- Simplified to Tidal-only (removed experimental Spotify support)
- Streamlined documentation and removed internal audit files
- Updated help text and CLI structure

### Removed

- Spotify integration (experimental feature)
- Internal development docs (AUDIT_REPORT, CODE_EVALUATION, FIXES_APPLIED)

## [1.0.0] - 2026-01-02

### Features

- AI-Powered Discovery using Google Gemini 3 models
- Quality Auditing for Hi-Res and HiFi streams
- Tidal Integration with OAuth authentication
- Forensic track matching with similarity scoring
- Real-time performance metrics

### Security

- macOS Keychain integration for all secrets
- Input validation and rate limiting
- Secure file permissions and path validation
- JSON size limits for DoS protection
