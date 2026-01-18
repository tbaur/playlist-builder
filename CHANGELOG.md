# Changelog

## [1.1.0] - 2026-01-18

### Added

- **Conversational Discovery** — New `chat` command for interactive, context-aware playlist building
  - Session maintains conversation history for iterative refinement
  - Accumulates tracks across multiple queries in a session
  - In-chat commands: `/tracks`, `/remove`, `/new`, `/clear`, `/publish`, `/quit`
- **In-Chat Publishing** — Publish directly from chat with `/publish <name>`
  - Replaces playlist by default, use `--append` to add to existing
- **Smart Track Filtering** — `/remove <pattern>` filters tracks by artist or title
- **Refinement Detection** — Phrases like "I don't like elif" prompt to remove instead of query
- **Readline Support** — Up/down arrow history and line editing in chat

### Changed

- Simplified to Tidal-only (removed Spotify support)
- Renamed `search` command to `query` for clarity
- Cache file renamed from `last_search.json` to `last_query.json`
- Streamlined documentation and removed internal audit files
- Graceful Ctrl+C handling (no stack traces)

### Removed

- Spotify integration and all related code
- `--run-code-tests` and `--coverage` CLI flags (use pytest directly)
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
