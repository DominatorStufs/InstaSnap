#!/usr/bin/env bash
# InstaInstant Termux Environment Setup Script
# Automatically installs Python, dependencies, and configures the environment.

set -e

# Terminal Colors
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${CYAN}====================================================${NC}"
echo -e "${CYAN}        🚀 InstaSnap - Automated Termux Setup       ${NC}"
echo -e "${CYAN}====================================================${NC}"
echo ""

# Check if running in Termux or standard Linux
if [ -d "/data/data/com.termux/files/usr" ]; then
    echo -e "${YELLOW}[*] Termux environment detected.${NC}"
    echo -e "${YELLOW}[*] Updating system packages...${NC}"
    pkg update -y
    
    echo -e "${YELLOW}[*] Installing required system binaries (Python, Pip, FFmpeg, Git)...${NC}"
    pkg install -y python python-pip ffmpeg git
else
    echo -e "${YELLOW}[*] Standard Linux environment detected.${NC}"
fi

# Install Python requirements
echo -e "${YELLOW}[*] Installing Python libraries (requests, rich)...${NC}"
pip install -r requirements.txt

# Ensure instant directory exists with permanent placeholder files
mkdir -p instant
touch instant/.gitkeep
touch instant/__init__.py

# Ensure permissions
chmod +x setup.sh instant_uploader.py config.py insta_client.py cookie_extractor.py insta_downloader.py 2>/dev/null || true

echo ""
echo -e "${GREEN}====================================================${NC}"
echo -e "${GREEN}    ✅ Setup Complete! InstaSnap is ready to use.   ${NC}"
echo -e "${GREEN}====================================================${NC}"
echo ""
echo -e "Next steps:"
echo -e " 1. Extract session cookie (Username/Password):"
echo -e "    • Run: ${CYAN}python cookie_extractor.py${NC}"
echo -e " 2. Put exactly 1 photo or video into the ${CYAN}instant/${NC} folder."
echo -e " 3. Run ${CYAN}python instant_uploader.py${NC} to verify and upload!"
echo ""
