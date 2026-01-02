# Security Policy

## Supported Versions

We actively support and provide security updates for the main branch. All security updates are applied to the main branch and will be clearly marked in the CHANGELOG.

| Version | Supported          |
| ------- | ------------------ |
| main    | :white_check_mark: |
| < 28.0  | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability, please **do not** open a public issue. Instead, please report it privately:

1. **GitHub Security Advisory** (preferred):
   - Go to the repository's "Security" tab
   - Click "Report a vulnerability"
   - Fill out the security advisory form

2. **Alternative**: If you cannot use GitHub's security advisory system, you can email the maintainer directly (contact information available on GitHub profile).

### What to Include

When reporting a vulnerability, please include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if you have one)
- Your contact information

### Response Time

We aim to:
- Acknowledge receipt within 48 hours
- Provide an initial assessment within 7 days
- Keep you updated on progress every 7-14 days

### Disclosure Policy

- We will work with you to understand and resolve the issue quickly
- We will not disclose the vulnerability publicly until a fix is available
- We will credit you in the security advisory (unless you prefer to remain anonymous)

## Security Best Practices

When using this tool:

1. **API Keys**: Always use macOS Keychain for storing secrets (recommended)
   - Use `playlist-builder keychain set GEMINI_API_KEY` to store API keys securely
   - Keychain provides encrypted, system-managed storage
   - Avoid storing API keys in plaintext `config.json` files

2. **Configuration Files**: Never commit `config.json` with secrets to version control
   - The `.gitignore` file is configured to exclude `config.json`
   - Use `config.json.template` as a reference

3. **File Permissions**: Config files are automatically set to 600 (owner read/write only)

4. **Network Security**: 
   - All API calls use HTTPS
   - OAuth tokens are stored securely in Keychain
   - Rate limiting prevents API abuse (60 requests/minute)

5. **No Admin Rights**: The tool does not require sudo/administrator privileges

6. **Keychain Access**: Keychain operations require user authentication (macOS security feature)

## Security Features

### macOS Keychain Integration ✅
All sensitive data is stored in the macOS Keychain:
- **Gemini API Keys**: Stored with service `com.playlist-builder`, account `default:GEMINI_API_KEY`
- **Tidal OAuth Tokens**: Stored with service `com.playlist-builder`, account `tidal:tidal_session`
- **Automatic Migration**: Existing secrets in `config.json` are automatically migrated to Keychain
- **Cross-Platform Fallback**: On non-macOS platforms, falls back to `config.json` with secure permissions

### Input Validation ✅
All user inputs are comprehensively validated:
- **Query Validation**: 
  - Length limits (1-1000 characters)
  - Type checking
  - Empty string rejection
  - Dangerous pattern detection (script injection, command injection, path traversal)
- **Playlist Name Validation**:
  - Length limits (1-100 characters)
  - Shell metacharacter rejection
  - Path traversal prevention
- **Limit Validation**:
  - Range validation (1-100)
  - Type checking
- **API Key Input**:
  - Secure input using `getpass.getpass()` (no echo to terminal)
  - Protects against shoulder surfing and terminal history exposure

### Rate Limiting ✅
- **API Rate Limiting**: 60 requests per minute to prevent abuse
- **Timeout Protection**: All API calls have 30-second timeouts
- **Connection Management**: Proper connection pooling and reuse

### Subprocess Security ✅
All subprocess calls include security protections:
- **Timeout Protection**: All subprocess calls have explicit timeouts
  - Keychain operations: 10 seconds
  - Venv creation: 5 minutes
  - Package installation: 10 minutes
  - Test execution: 1 hour (development only)
- **Input Validation**: All inputs validated before subprocess execution
- **Shell Injection Prevention**: 
  - All subprocess calls **explicitly** use `shell=False` (hardened in v28.3)
  - Arguments passed as lists (not strings)
  - No user input passed directly to shell
  - Absolute paths used for all executables
- **Error Handling**: Comprehensive exception handling for all subprocess failures

### File Security ✅ (Enhanced in v28.3)
- **Secure Permissions**: Config files automatically set to 600 (owner read/write only)
- **Path Validation**: Comprehensive validation with `validate_file_path()`:
  - Symlink detection and blocking
  - Path traversal prevention (`..`, null bytes)
  - Dangerous path blocking (`/etc/`, `/proc/`, Windows system directories)
  - Absolute path normalization
- **JSON Size Limits**: Protection against DoS attacks:
  - Config files: 1MB maximum (`MAX_CONFIG_SIZE_BYTES`)
  - Cache files: 10MB maximum (`MAX_JSON_SIZE_BYTES`)
  - Size validation before loading
- **Safe JSON Loading**: `safe_json_load()` function combines:
  - File size validation
  - Path security checks
  - Type validation (must be dict)
  - Proper error handling
- **Directory Creation**: Safe directory creation with proper permissions

### Error Handling ✅
- **Specific Exception Types**: Custom exceptions for different error scenarios
- **Resource Cleanup**: Proper cleanup with try/finally blocks
- **Timeout Handling**: Graceful handling of timeouts in concurrent operations
- **No Sensitive Data in Logs**: API keys and tokens never logged

## Security Functions (v28.3)

The application includes dedicated security functions for enhanced protection:

### `safe_json_load(file_path, max_size_bytes)`
Safely loads JSON files with comprehensive security checks:
- **Size Validation**: Checks file size before loading to prevent DoS
- **Path Validation**: Calls `validate_file_path()` to ensure path security
- **Type Validation**: Ensures loaded data is a dictionary
- **Error Handling**: Provides detailed error messages for troubleshooting

Usage:
```python
from utils import safe_json_load
from constants import MAX_CONFIG_SIZE_BYTES

config = safe_json_load(CONFIG_FILE, max_size_bytes=MAX_CONFIG_SIZE_BYTES)
```

### `validate_file_path(file_path, allow_symlinks=False)`
Validates file paths for security issues:
- **Symlink Detection**: Blocks symlinks by default to prevent attacks
- **Path Traversal**: Detects `..`, null bytes, and other traversal attempts
- **Dangerous Paths**: Blocks access to system directories
- **Absolute Path**: Converts to absolute path for consistent checking

Usage:
```python
from utils import validate_file_path

# Will raise ValueError if path is insecure
validate_file_path("/path/to/file.json")
```

Protected system paths include:
- `/etc/` - Unix system configuration
- `/proc/` - Unix process information
- `/sys/` - Unix kernel interface
- `C:\Windows\` - Windows system files
- `C:\Program Files\` - Windows applications

## Known Security Considerations

### API Key Storage
- **Recommended**: Use macOS Keychain (default on macOS)
- **Alternative**: Store in `config.json` with 600 permissions (non-macOS platforms)
- **Migration**: Automatic migration from `config.json` to Keychain on first run

### Network Communication
- All API calls use HTTPS
- OAuth tokens refreshed automatically
- No sensitive data transmitted in URLs

### Local Storage
- Cache files (`last_search.json`) contain track metadata only, no secrets
- Log files (`playlist-builder.log`) do not contain sensitive information
- All files stored in `~/.config/playlist-builder` with secure permissions

## Security Updates

Security updates will be applied to the main branch and will be clearly marked in the CHANGELOG.

### v28.3 (2025-12-30) - Security Hardening Round 2
- ✅ **Secure API Key Input**: Uses `getpass.getpass()` (no terminal echo)
- ✅ **JSON Size Limits**: DoS protection with 1MB/10MB limits
- ✅ **Path Validation**: Comprehensive symlink and traversal protection
- ✅ **Hardened Subprocess Calls**: Explicit `shell=False` on all calls
- ✅ **Safe JSON Loading**: `safe_json_load()` with size and security checks
- ✅ **Path Security Function**: `validate_file_path()` for comprehensive validation

### v28.0-28.2 - Initial Security Enhancements
- ✅ macOS Keychain integration for all secrets
- ✅ Input validation and sanitization
- ✅ Rate limiting (60 requests/minute)
- ✅ Subprocess security with timeout protection
- ✅ Secure file permissions (600)
- ✅ Automatic secret migration from config.json to Keychain

See [AUDIT_REPORT.md](AUDIT_REPORT.md) for detailed security audit findings.

