# Tidal Integration

## Overview

Playlist Builder integrates with Tidal to:
- Search and resolve tracks with quality-aware matching
- Create and manage playlists in your Tidal account
- Prioritize Hi-Res and Lossless audio quality

## Authentication

### OAuth Flow

1. Run any command that requires Tidal access
2. Browser opens for Tidal authorization
3. Tokens stored securely in macOS Keychain

### Session Storage

**macOS (Recommended)**
```
Keychain Service: com.playlist-builder
Account: tidal:tidal_session
```

**Other Platforms**
```json
// config.json
{
  "TIDAL": {
    "SESSION_DATA": { "access_token": "...", "refresh_token": "..." }
  }
}
```

## Track Resolution

### Matching Algorithm

1. Query: `"{title}" {artist}`
2. Title tokenization and cleaning
3. Artist anchor matching
4. Jaccard similarity scoring
5. Quality weighting (Hi-Res > Lossless > Standard)

### Quality Weights

| Quality | Weight | Description |
|---------|--------|-------------|
| HI_RES | 10 | 24-bit / Studio Master |
| LOSSLESS | 5 | 16-bit / CD Quality |
| Standard | 0 | Compressed |

### Minimum Score

Tracks must score above 0.40 to be considered valid matches.

## Usage

```bash
# Discover and cache tracks
playlist-builder query "Jazz classics"

# Interactive discovery
playlist-builder chat

# Publish to Tidal
playlist-builder publish tidal --name "Jazz Classics"

# Replace existing playlist
playlist-builder publish tidal --name "Jazz Classics" --replace
```

## Error Handling

| Error | Solution |
|-------|----------|
| OAuth failed | Re-run to trigger new flow |
| Session expired | Clear Keychain, re-authenticate |
| Rate limiting | Automatic retry with backoff |

## Testing

```bash
pytest tests/test_tidal_engine.py -v
```
