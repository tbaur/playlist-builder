# Copyright 2025 tbaur
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
macOS Keychain utilities for secure secret storage.
"""
import json
import logging
import subprocess
import sys
from typing import Optional, Dict, Any

logger = logging.getLogger('playlist_builder.keychain')

# Keychain service name
KEYCHAIN_SERVICE = "com.playlist-builder"

def _run_security_command(args: list, input_data: Optional[str] = None) -> tuple[bool, str]:
    """
    Run a security command-line tool command.
    
    Args:
        args: Arguments to pass to security command
        input_data: Optional input data to pass via stdin
        
    Returns:
        Tuple of (success, output)
    """
    try:
        cmd = ["security"] + args
        result = subprocess.run(
            cmd,
            input=input_data.encode() if input_data else None,
            capture_output=True,
            text=True,
            timeout=10,
            shell=False  # Explicit: never use shell
        )
        return result.returncode == 0, result.stdout.strip()
    except subprocess.TimeoutExpired:
        logger.error("Security command timed out")
        return False, "Command timed out"
    except FileNotFoundError:
        logger.error("security command not found (not on macOS?)")
        return False, "security command not found"
    except Exception as e:
        logger.error(f"Error running security command: {e}")
        return False, str(e)

def store_secret(key: str, value: str, account: str = "default") -> bool:
    """
    Store a secret in macOS Keychain.
    
    Args:
        key: Secret key identifier
        value: Secret value to store
        account: Account identifier (default: "default")
        
    Returns:
        True if successful, False otherwise
    """
    if sys.platform != "darwin":
        logger.warning("Keychain storage only available on macOS")
        return False
    
    # Use generic password item with service, account, and key
    # Format: service=KEYCHAIN_SERVICE, account=f"{account}:{key}"
    full_account = f"{account}:{key}"
    
    # Try to delete existing item first (ignore errors)
    _run_security_command([
        "delete-generic-password",
        "-s", KEYCHAIN_SERVICE,
        "-a", full_account
    ])
    
    # Add new item
    success, _ = _run_security_command([
        "add-generic-password",
        "-s", KEYCHAIN_SERVICE,
        "-a", full_account,
        "-w", value,
        "-U"  # Update if exists
    ])
    
    if success:
        logger.debug(f"Stored secret in keychain: {key}")
    else:
        logger.error(f"Failed to store secret in keychain: {key}")
    
    return success

def get_secret(key: str, account: str = "default") -> Optional[str]:
    """
    Retrieve a secret from macOS Keychain.
    
    Args:
        key: Secret key identifier
        account: Account identifier (default: "default")
        
    Returns:
        Secret value if found, None otherwise
    """
    if sys.platform != "darwin":
        logger.warning("Keychain retrieval only available on macOS")
        return None
    
    full_account = f"{account}:{key}"
    success, output = _run_security_command([
        "find-generic-password",
        "-s", KEYCHAIN_SERVICE,
        "-a", full_account,
        "-w"  # Print password only
    ])
    
    if success and output:
        logger.debug(f"Retrieved secret from keychain: {key}")
        return output
    else:
        logger.debug(f"Secret not found in keychain: {key}")
        return None

def delete_secret(key: str, account: str = "default") -> bool:
    """
    Delete a secret from macOS Keychain.
    
    Args:
        key: Secret key identifier
        account: Account identifier (default: "default")
        
    Returns:
        True if successful, False otherwise
    """
    if sys.platform != "darwin":
        logger.warning("Keychain deletion only available on macOS")
        return False
    
    full_account = f"{account}:{key}"
    success, _ = _run_security_command([
        "delete-generic-password",
        "-s", KEYCHAIN_SERVICE,
        "-a", full_account
    ])
    
    if success:
        logger.debug(f"Deleted secret from keychain: {key}")
    else:
        logger.debug(f"Secret not found in keychain for deletion: {key}")
    
    return success

def store_tidal_session(session_data: Dict[str, Any]) -> bool:
    """
    Store Tidal session data in Keychain.
    
    Args:
        session_data: Dictionary containing token_type, access_token, refresh_token
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Store as JSON string
        json_data = json.dumps(session_data)
        return store_secret("tidal_session", json_data, account="tidal")
    except Exception as e:
        logger.error(f"Failed to store Tidal session: {e}")
        return False

def get_tidal_session() -> Optional[Dict[str, Any]]:
    """
    Retrieve Tidal session data from Keychain.
    
    Returns:
        Dictionary containing session data, or None if not found
    """
    try:
        json_data = get_secret("tidal_session", account="tidal")
        if json_data:
            return json.loads(json_data)
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Tidal session data: {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to retrieve Tidal session: {e}")
        return None

def migrate_secrets_from_config(config: Dict[str, Any]) -> bool:
    """
    Migrate secrets from config.json to Keychain.
    
    Args:
        config: Configuration dictionary from config.json
        
    Returns:
        True if migration successful, False otherwise
    """
    if sys.platform != "darwin":
        logger.warning("Keychain migration only available on macOS")
        return False
    
    migrated = False
    
    # Migrate Gemini API key
    if "GEMINI" in config and "API_KEY" in config["GEMINI"]:
        api_key = config["GEMINI"].get("API_KEY")
        if api_key and len(api_key) >= 10:
            if store_secret("gemini_api_key", api_key):
                migrated = True
                logger.info("Migrated Gemini API key to Keychain")
    
    # Migrate Tidal session data
    if "TIDAL" in config and "SESSION_DATA" in config["TIDAL"]:
        session_data = config["TIDAL"].get("SESSION_DATA", {})
        if session_data and isinstance(session_data, dict):
            # Only migrate if there's actual session data
            if session_data.get("access_token"):
                if store_tidal_session(session_data):
                    migrated = True
                    logger.info("Migrated Tidal session data to Keychain")
    
    return migrated

