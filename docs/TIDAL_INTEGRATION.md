# Tidal Integration

This document describes the Tidal music service integration in playlist-builder.

## Overview

The Tidal integration allows playlist-builder to:
- Search for tracks on Tidal with quality-aware matching
- Create and manage playlists in your Tidal account
- Prioritize Hi-Res and Lossless audio quality tracks

## Architecture

### TidalProvider Class

Located in `tidal_engine.py`, the `TidalProvider` class handles all Tidal API interactions.

```python
class TidalProvider:
    def __init__(self, cfg: Dict, cfg_path: str, debug: bool = False)
    def authenticate(self) -> bool
    def publish(self, name: str, tracks: List[Dict], replace: bool, metrics: Any) -> None
```

### Key Methods

| Method | Description |
|--------|-------------|
| `authenticate()` | Handles OAuth login flow with session caching |
| `_resolve_best_node()` | Searches Tidal for best matching track |
| `_clean()` | Normalizes text for fuzzy matching |
| `publish()` | Creates/updates playlist with resolved tracks |
| `_save_session_data()` | Persists OAuth tokens to Keychain |

## Authentication

### OAuth Flow

Tidal uses OAuth 2.0 for authentication. The flow is:

1. Check for cached session in Keychain (macOS) or config.json
2. If valid session exists, load and verify it
3. If session expired or missing, trigger browser-based OAuth
4. Save new tokens to Keychain for future use

### Session Storage

**macOS (Recommended)**
```
Keychain Service: com.playlist-builder
Account: tidal:tidal_session
Data: JSON with token_type, access_token, refresh_token
```

**Other Platforms**
```json
// config.json
{
  "TIDAL": {
    "SESSION_DATA": {
      "token_type": "Bearer",
      "access_token": "...",
      "refresh_token": "..."
    }
  }
}
```

## Track Resolution

### Matching Algorithm

1. **Search Query**: Builds query as `"{title}" {artist}`
2. **Title Tokenization**: Cleans and tokenizes track names
3. **Artist Anchor**: Uses first word of artist name for matching
4. **Score Calculation**: Jaccard similarity on title tokens
5. **Quality Weighting**: Prioritizes Hi-Res > Lossless > Standard

### Quality Weights

| Quality | Weight | Description |
|---------|--------|-------------|
| HI_RES | 10 | 24-bit / Studio Master |
| LOSSLESS | 5 | 16-bit / CD Quality |
| Standard | 0 | Compressed audio |

### Minimum Match Score

Tracks must score above `MIN_MATCH_SCORE` (0.40) to be considered valid matches.

## Playlist Management

### Creating Playlists

```python
target_playlist = session.user.create_playlist(name, "AI Generated")
```

### Replacing Existing Playlists

When `--replace` flag is used:
1. Find existing playlist by name
2. Remove all tracks from playlist
3. Add new resolved tracks

### Adding Tracks

```python
target_playlist.add(track_ids)  # List of Tidal track IDs
```

## Usage

### Basic Search and Publish

```bash
# Search for tracks (caches results)
playlist-builder search "Jazz classics from the 1960s"

# Publish to Tidal
playlist-builder publish tidal --name "Jazz Classics"

# Replace existing playlist
playlist-builder publish tidal --name "Jazz Classics" --replace
```

### Debug Mode

```bash
playlist-builder search "query" --debug
```

Enables verbose logging for troubleshooting authentication and track resolution.

## Error Handling

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `TidalAPIError` | API rate limiting or invalid request | Retry with backoff |
| `OAuth failed` | User cancelled or timeout | Re-run to trigger new OAuth flow |
| `Session expired` | Refresh token invalid | Clear Keychain and re-authenticate |

### Retry Logic

The `_resolve_best_node` method uses exponential backoff:
- Max retries: 3
- Base delay: 1 second
- Handles transient API failures

## Dependencies

- `tidalapi>=0.7.0` - Official Tidal API client

## Security Considerations

1. **OAuth tokens** stored in macOS Keychain (encrypted)
2. **Config file** permissions set to 600 (owner read/write only)
3. **No plaintext secrets** in code or logs
4. **Session data** validated before use

## Testing

Tests are located in `tests/test_tidal_engine.py`:

```bash
# Run Tidal tests only
pytest tests/test_tidal_engine.py -v

# Run with coverage
pytest tests/test_tidal_engine.py --cov=tidal_engine
```

### Test Coverage

- Provider initialization
- Authentication flows (cached, expired, new)
- Track resolution (success, failure, edge cases)
- Playlist operations (create, replace, add tracks)
- Error handling

