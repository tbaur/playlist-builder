#!/bin/bash
# ==============================================================================
# PLAYLIST-BUILDER v28.0 INSTALLER
# Target: macOS / Linux (Python 3.12+)
# ==============================================================================

BOLD='\033[1m'
GREEN='\033[32m'
CYAN='\033[36m'
YELLOW='\033[33m'
RED='\033[31m'
MAGENTA='\033[35m'
DIM='\033[2m'
RESET='\033[0m'
HR="${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"

INSTALL_DIR="$HOME/.config/playlist-builder"
BIN_DEST="$HOME/local/bin/playlist-builder"

echo -e "${CYAN}${BOLD}┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓${RESET}"
echo -e "${CYAN}${BOLD}┃           PLAYLIST-BUILDER PRODUCTION DEPLOYMENT             ┃${RESET}"
echo -e "${CYAN}${BOLD}┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛${RESET}"

# 1. Pre-flight Check
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: python3 not found. Please install Python 3.12+${RESET}"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_VERSION="3.12"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo -e "${RED}Error: Python 3.12+ required. Found: $PYTHON_VERSION${RESET}"
    exit 1
fi

# 2. Create Directory Architecture
echo -e "${CYAN}Creating application home at ${INSTALL_DIR}...${RESET}"
mkdir -p "$INSTALL_DIR"

# 3. Deploy Source Code
REQUIRED_FILES=("main.py" "tidal_engine.py" "spotify_engine.py" "constants.py" "utils.py" "spinner.py" "metrics.py" "keychain_utils.py")
MISSING_FILES=()

for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        MISSING_FILES+=("$file")
    fi
done

if [ ${#MISSING_FILES[@]} -ne 0 ]; then
    echo -e "${RED}Error: Missing required files: ${MISSING_FILES[*]}${RESET}"
    exit 1
fi

echo -e "${CYAN}Deploying source files...${RESET}"
for file in "${REQUIRED_FILES[@]}"; do
    cp "$file" "$INSTALL_DIR/$file"
    echo -e "  ${GREEN}✓${RESET} $file"
done

chmod +x "$INSTALL_DIR/main.py"

# Copy .gitignore if it exists
if [ -f ".gitignore" ]; then
    cp ".gitignore" "$INSTALL_DIR/.gitignore"
fi

# Copy test files if they exist
if [ -d "tests" ]; then
    echo -e "${CYAN}Copying test suite...${RESET}"
    cp -r tests "$INSTALL_DIR/"
fi

# Copy test configuration files if they exist
for test_file in "pytest.ini" "requirements-test.txt" "run_tests.sh"; do
    if [ -f "$test_file" ]; then
        cp "$test_file" "$INSTALL_DIR/$test_file"
        if [ "$test_file" = "run_tests.sh" ]; then
            chmod +x "$INSTALL_DIR/$test_file"
        fi
    fi
done

# 4. Setup Configuration
CONFIG_FILE="$INSTALL_DIR/config.json"
CONFIG_TEMPLATE="config.json.template"

if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "\n${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
    echo -e "${CYAN}${BOLD}                    INITIAL CONFIGURATION SETUP${RESET}"
    echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}\n"
    
    # Copy template if it exists, otherwise create default
    if [ -f "$CONFIG_TEMPLATE" ]; then
        cp "$CONFIG_TEMPLATE" "$CONFIG_FILE"
        echo -e "${GREEN}✓${RESET} Created config.json from template"
    else
        # Create default config structure
        cat > "$CONFIG_FILE" << 'EOF'
{
  "GEMINI": {
    "API_KEY": ""
  },
  "TIDAL": {
    "ENABLED": true,
    "SESSION_DATA": {}
  },
  "PREFERENCES": {
    "DEFAULT_PROVIDER": "tidal"
  }
}
EOF
        echo -e "${GREEN}✓${RESET} Created default config.json"
    fi
    
    # Set secure permissions: owner read/write only (600)
    chmod 600 "$CONFIG_FILE"
    echo -e "${GREEN}✓${RESET} Set secure permissions on config.json (600)"
    
    # Detect macOS for Keychain option
    USE_KEYCHAIN=false
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo -e "\n${CYAN}${BOLD}Secret Storage Options${RESET}"
        echo -e "${GREEN}1.${RESET} macOS Keychain (recommended - secure, encrypted)"
        echo -e "${GREEN}2.${RESET} config.json file (less secure, plain text)"
        echo -ne "${CYAN}Choose storage method (1/2) [1]: ${RESET}"
        read -r STORAGE_CHOICE
        
        if [ -z "$STORAGE_CHOICE" ] || [ "$STORAGE_CHOICE" = "1" ]; then
            USE_KEYCHAIN=true
            echo -e "${GREEN}✓${RESET} Will use macOS Keychain for secure storage"
        else
            echo -e "${YELLOW}⚠${RESET}  Will use config.json (plain text - less secure)"
        fi
    fi
    
    # Prompt for Gemini API Key
    echo -e "\n${YELLOW}Gemini API Key Required${RESET}"
    echo -e "${DIM}Get your API key from: https://makersuite.google.com/app/apikey${RESET}"
    echo -ne "${CYAN}Enter Gemini API Key: ${RESET}"
    read -r GEMINI_KEY
    
    if [ -z "$GEMINI_KEY" ]; then
        echo -e "${YELLOW}Warning: No API key provided. You can add it later with:${RESET}"
        if [ "$USE_KEYCHAIN" = true ]; then
            echo -e "${CYAN}  playlist-builder keychain set GEMINI_API_KEY <key>${RESET}"
        else
            echo -e "${CYAN}  Edit $CONFIG_FILE manually${RESET}"
        fi
    else
        # Store API key based on chosen method
        python3 << PYEOF
import json
import sys
import os
sys.path.insert(0, "$INSTALL_DIR")

try:
    use_keychain = "$USE_KEYCHAIN" == "true"
    api_key = "$GEMINI_KEY"
    
    if use_keychain:
        # Import keychain_utils and store in Keychain
        from keychain_utils import store_secret
        if store_secret("GEMINI_API_KEY", api_key):
            print("✓ API key saved to macOS Keychain")
        else:
            print("Error: Failed to save to Keychain", file=sys.stderr)
            sys.exit(1)
    else:
        # Store in config.json (legacy method)
        with open("$CONFIG_FILE", 'r') as f:
            config = json.load(f)
        
        config['GEMINI']['API_KEY'] = api_key
        
        with open("$CONFIG_FILE", 'w') as f:
            json.dump(config, f, indent=2)
        
        print("✓ API key saved to config.json")
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
PYEOF
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓${RESET} Gemini API key configured"
        else
            echo -e "${RED}Error: Failed to save API key.${RESET}"
            if [ "$USE_KEYCHAIN" = true ]; then
                echo -e "${DIM}You can add it later with: playlist-builder keychain set GEMINI_API_KEY <key>${RESET}"
            else
                echo -e "${DIM}Please edit $CONFIG_FILE manually.${RESET}"
            fi
        fi
    fi
    
    # Tidal Authentication Setup
    echo -e "\n${YELLOW}Tidal Authentication${RESET}"
    echo -e "${DIM}You'll need to authenticate with Tidal on first use.${RESET}"
    echo -e "${DIM}This will open a browser for OAuth authentication.${RESET}"
    echo -ne "${CYAN}Would you like to authenticate with Tidal now? (y/N): ${RESET}"
    read -r AUTH_NOW
    
    if [[ "$AUTH_NOW" =~ ^[Yy]$ ]]; then
        echo -e "${CYAN}Setting up Tidal authentication...${RESET}"
        echo -e "${DIM}This will open your browser for OAuth login...${RESET}"
        echo -e "${DIM}Note: Authentication will complete after venv is created.${RESET}"
        echo -e "${DIM}You can also authenticate later by running: playlist-builder search \"test\"${RESET}"
    else
        echo -e "${DIM}You can authenticate later by running: playlist-builder search \"test\"${RESET}"
    fi
    
    # Ensure permissions are secure even if file already existed
    chmod 600 "$CONFIG_FILE"
    
    echo -e "\n${GREEN}${BOLD}✓ Configuration setup complete!${RESET}"
else
    echo -e "${CYAN}Configuration file already exists at $CONFIG_FILE${RESET}"
    echo -e "${DIM}Skipping configuration setup...${RESET}"
    # Ensure existing config has secure permissions
    chmod 600 "$CONFIG_FILE"
    echo -e "${GREEN}✓${RESET} Verified secure permissions on existing config.json (600)"
fi

# 5. Bootstrap Virtual Environment
echo -e "${CYAN}Initializing isolated sandbox (.venv)...${RESET}"
if ! python3 -m venv "$INSTALL_DIR/.venv"; then
    echo -e "${RED}Error: Failed to create virtual environment${RESET}"
    exit 1
fi

"$INSTALL_DIR/.venv/bin/pip" install --upgrade pip --quiet
if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Failed to upgrade pip${RESET}"
    exit 1
fi

"$INSTALL_DIR/.venv/bin/pip" install google-genai tidalapi spotipy --quiet
if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Failed to install runtime dependencies${RESET}"
    exit 1
fi

# Install test dependencies if requirements-test.txt exists
if [ -f "$INSTALL_DIR/requirements-test.txt" ]; then
    echo -e "${CYAN}Installing test dependencies...${RESET}"
    "$INSTALL_DIR/.venv/bin/pip" install -r "$INSTALL_DIR/requirements-test.txt" --quiet
    if [ $? -ne 0 ]; then
        echo -e "${YELLOW}Warning: Failed to install test dependencies (tests may not run)${RESET}"
    fi
fi

# 6. User-local Symlink
echo -e "${CYAN}Linking binary to user-local path...${RESET}"
mkdir -p "$(dirname "$BIN_DEST")"
if ln -sf "$INSTALL_DIR/main.py" "$BIN_DEST"; then
    echo -e "${GREEN}✓${RESET} Symlink created at $BIN_DEST"
    if ! echo "$PATH" | grep -q "$HOME/local/bin"; then
        echo -e "${YELLOW}Note: Add ${CYAN}$HOME/local/bin${YELLOW} to your PATH${RESET}"
        echo -e "${DIM}Add this to your ~/.zshrc or ~/.bashrc:${RESET}"
        echo -e "${CYAN}export PATH=\"\$HOME/local/bin:\$PATH\"${RESET}"
    fi
else
    echo -e "${YELLOW}Warning: Failed to create symlink. You may need to add ${INSTALL_DIR} to your PATH${RESET}"
fi

# 7. Final Instructions
echo -e "\n${GREEN}${BOLD}✔ INSTALLATION COMPLETE${RESET}"
echo -e "${HR}"
echo -e "${BOLD}NEXT STEPS:${RESET}"
echo -e "1. Run ${CYAN}playlist-builder search \"query\"${RESET} to begin."

# Check if API key is already configured (works on re-runs too)
API_KEY_SET=false

# Check Keychain first (macOS only)
if [[ "$OSTYPE" == "darwin"* ]]; then
    # Try to read from Keychain using security command
    # Account format is "default:GEMINI_API_KEY" (see keychain_utils.py)
    if security find-generic-password -s "com.playlist-builder" -a "default:GEMINI_API_KEY" -w 2>/dev/null | grep -q .; then
        API_KEY_SET=true
    fi
fi

# If not in Keychain, check config.json
if [ "$API_KEY_SET" = false ] && [ -f "$CONFIG_FILE" ]; then
    # Check if config.json has a non-empty API key
    if grep -q '"API_KEY": *"[^"]\+' "$CONFIG_FILE" 2>/dev/null; then
        API_KEY_SET=true
    fi
fi

# Show instructions only if key is not set
if [ "$API_KEY_SET" = false ]; then
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo -e "2. Add your ${MAGENTA}Gemini API Key${RESET} with: ${CYAN}playlist-builder keychain set GEMINI_API_KEY${RESET}"
    else
        echo -e "2. Add your ${MAGENTA}Gemini API Key${RESET} to: $CONFIG_FILE"
    fi
fi

echo -e "3. Tidal OAuth will trigger automatically during the first search."
echo -e "4. ${DIM}(Optional)${RESET} For Spotify support: ${CYAN}playlist-builder keychain set SPOTIFY_CLIENT_ID${RESET}"
echo -e "   ${DIM}Get credentials at: https://developer.spotify.com/dashboard${RESET}"
echo -e "\n${DIM}System config stored in: $INSTALL_DIR${RESET}\n"
