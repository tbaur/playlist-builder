# Playlist Builder

[![Tests](https://github.com/tbaur/playlist-builder/actions/workflows/test.yml/badge.svg)](https://github.com/tbaur/playlist-builder/actions/workflows/test.yml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![macOS](https://img.shields.io/badge/macOS-14%2B-lightgrey.svg)](https://www.apple.com/macos/)

AI-powered music discovery that uses Google Gemini to transform natural language queries into curated Tidal playlists. Every track is verified for audio quality, ISRC provenance, and metadata accuracy.

## Features

- **Conversational Discovery** — Interactive chat mode for iterative playlist building with context awareness
- **AI-Powered Search** — Gemini 3 models understand complex music queries in natural language
- **Quality Auditing** — Prioritizes Hi-Res (24-bit) and HiFi (16-bit) lossless streams
- **Tidal Integration** — Direct sync to your Tidal playlists with OAuth authentication
- **Forensic Matching** — Token-based similarity scoring ensures accurate track resolution
- **Secure by Default** — API keys and tokens stored in macOS Keychain

## Requirements

- macOS 14+
- Python 3.12+
- [Google Gemini API key](https://makersuite.google.com/app/apikey)
- Tidal HiFi subscription

## Installation

```bash
./install.sh
```

This creates an isolated environment in `~/.config/playlist-builder` with no system-wide changes.

### Complete Removal

```bash
rm -rf ~/.config/playlist-builder
rm ~/local/bin/playlist-builder
# Optionally clear Keychain: playlist-builder reset (before removal)
```

## Usage

### Interactive Chat Mode

Start a conversational session for iterative discovery:

```bash
playlist-builder chat
playlist-builder chat --model 3-pro --limit 20
```

Chat commands:
- `/tracks` — Show all discovered tracks
- `/remove <pattern>` — Remove tracks by artist or title (e.g., `/remove elif`)
- `/new` — Clear tracks & context, start a new playlist
- `/clear` — Clear conversation context only
- `/publish <name>` — Publish to Tidal (replace, or use `--append`)
- `/quit` — Exit chat (or Ctrl+C)

**Workflow:** Query → `/remove` unwanted → `/publish "My Playlist"` → `/new` → repeat

**Smart detection:** If you type "I don't like <artist>", the chat will offer to remove those tracks instead of running a new query.

### Single Query

For one-shot discovery:

```bash
playlist-builder query "Jazz classics from the 1960s"
playlist-builder query "Ambient electronic for focus" --limit 20
```

### Publish to Tidal

```bash
playlist-builder publish tidal --name "My Playlist"
playlist-builder publish tidal --name "My Playlist" --replace
```

### Keychain Management

```bash
playlist-builder keychain set GEMINI_API_KEY
playlist-builder keychain list
playlist-builder keychain delete GEMINI_API_KEY
```

### Other Commands

```bash
playlist-builder --help    # Show help
playlist-builder reset     # Clear credentials and cache
playlist-builder rebuild   # Reinstall virtual environment
```

## Models

| Model | Description |
|-------|-------------|
| `3-flash` | Gemini 3 Flash (default, fast) |
| `3-pro` | Gemini 3 Pro (best quality) |
| `2-flash` | Gemini 2 Flash (legacy) |
| `2-pro` | Gemini 2 Pro (legacy) |

## Understanding the Signal

| Indicator | Meaning |
|-----------|---------|
| **H** | HI-RES: 24-bit / Studio Master quality |
| **L** | HiFi: 16-bit / CD-quality lossless |
| **1.00** | Perfect match score |
| **0.75+** | High confidence match |

## Testing

```bash
pytest                                    # Run all tests
pytest --cov=. --cov-report=html          # With coverage report
bash run_tests.sh                         # Using test runner
```

## Project Structure

```
playlist-builder/
├── main.py              # CLI and orchestration
├── tidal_engine.py      # Tidal API integration
├── constants.py         # Configuration constants
├── utils.py             # Utility functions
├── keychain_utils.py    # macOS Keychain integration
├── spinner.py           # Terminal UI
├── metrics.py           # Performance metrics
├── tests/               # Test suite
└── docs/                # Documentation
```

## Security

- API keys and OAuth tokens stored in macOS Keychain
- Config files restricted to owner read/write (600)
- Input validation on all user queries
- Rate limiting (60 requests/minute)
- No secrets in logs or error messages

See [SECURITY.md](SECURITY.md) for vulnerability reporting.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

Apache License 2.0 — See [LICENSE](LICENSE)

Copyright 2025 tbaur
