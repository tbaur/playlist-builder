# Security Policy

## Reporting Vulnerabilities

**Do not** open public issues for security vulnerabilities.

Report privately via:
1. GitHub Security Advisory (preferred): Repository → Security → Report a vulnerability
2. Direct email to maintainer

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

**Response timeline:**
- Acknowledgment: 48 hours
- Initial assessment: 7 days
- Updates: Every 7-14 days

## Security Features

### Keychain Integration (macOS)

All secrets stored in macOS Keychain:
- Gemini API keys
- Tidal OAuth tokens
- Automatic migration from config files

### Input Validation

- Query length limits (1-1000 characters)
- Dangerous pattern detection
- Path traversal prevention
- JSON size limits (DoS protection)

### Rate Limiting

- 60 requests/minute to APIs
- 30-second timeouts on all calls

### File Security

- Config files: 600 permissions (owner only)
- Path validation blocks symlinks and traversal
- Safe JSON loading with size checks

## Best Practices

1. **Use Keychain** — Always store secrets via `playlist-builder keychain set`
2. **Never commit config.json** — It's in `.gitignore` by default
3. **Review logs** — No secrets appear in `playlist-builder.log`
