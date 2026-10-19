#!/usr/bin/env python3
"""
=============================================================================
InstaSnap - Central Configuration & Settings
=============================================================================
Description: Stores your Instagram session, audience settings, folder paths,
             and single-file policies directly inside this file.
             No .env file required!
=============================================================================
"""

import sys
import json
import re
import importlib
import subprocess
import time
from pathlib import Path

# =============================================================================
# INSTAGRAM AUTHENTICATION & CREDENTIALS
# =============================================================================
IG_SESSION_ID = ""

# Target Audience for Instants:
#   • "mutual_followers" -> Shows to mutual followers (Friends who follow you back)
#   • "close_friends"    -> Shows ONLY to your Instagram Close Friends list
IG_AUDIENCE = "mutual_followers"  # Options: "mutual_followers" or "close_friends"

# =============================================================================
# DIRECTORY PATHS & STORAGE
# =============================================================================
ROOT_DIR = Path(__file__).resolve().parent
BASE_DIR = ROOT_DIR
CONFIG_FILE = Path(__file__).resolve()
SESSION_FILE = ROOT_DIR / "session.json"
DEVICE_FILE = ROOT_DIR / "device.json"
INSTANT_DIR = ROOT_DIR / "instant"

# =============================================================================
# MEDIA POLICIES & LIMITS
# =============================================================================
MAX_VIDEO_SIZE_MB = 100.0           # Absolute ceiling enforced by Instagram API
RECOMMENDED_VIDEO_SIZE_MB = 50.0    # Optimal QuickSnap limit (1-15s clips)
MAX_RECOMMENDED_DURATION_SEC = 15   # Standard QuickSnap clip duration

# Supported formats
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".mkv"}

# Permanent helper files inside instant/ that MUST NEVER be deleted or counted as media
PERMANENT_INSTANT_FILES = {".gitkeep", "__init__.py"}

# Instagram QuickSnap Endpoint & Navigation Constants
QUICKSNAP_CLIENT_ENDPOINT = "InsightsHostImpl:quick_snap_audience_picker"

# Required pure-Python dependencies (Zero C/Rust compilation needed for Termux)
REQUIRED_PACKAGES = {
    "requests": "requests>=2.31.0",
    "rich": "rich>=13.7.0",
}


def ensure_dependencies():
    """
    Checks if all required Python dependencies are installed.
    If any package is missing, automatically downloads and installs it via pip on the fly.
    """
    missing = []
    for module_name, pip_spec in REQUIRED_PACKAGES.items():
        try:
            importlib.import_module(module_name)
        except ImportError:
            missing.append(pip_spec)

    if missing:
        CYAN = "\033[0;36m"
        YELLOW = "\033[1;33m"
        GREEN = "\033[0;32m"
        RED = "\033[0;31m"
        DIM = "\033[2m"
        RESET = "\033[0m"

        print(f"\n{CYAN}======================================================{RESET}")
        print(f"{YELLOW}   🚀 InstaSnap - Automated Dependency Resolver       {RESET}")
        print(f"{CYAN}======================================================{RESET}")
        print(f"{YELLOW}[*] Missing package(s) detected:{RESET}")
        for pkg in missing:
            print(f"    • {pkg}")
        print(f"\n{CYAN}[*] Downloading and installing required libraries...{RESET}")
        print(f"{DIM}    (This happens only once and takes a few moments in Termux){RESET}\n")

        try:
            cmd = [sys.executable, "-m", "pip", "install", *missing]
            subprocess.run(cmd, check=True)
            importlib.invalidate_caches()
            print(f"\n{GREEN}[✔] All dependencies installed successfully!{RESET}")
            print(f"{CYAN}[*] Launching InstaSnap application...{RESET}\n")
            time.sleep(1)
        except Exception as e:
            print(f"\n{RED}[✗] Automatic installation failed: {e}{RESET}")
            print("Please run manually: bash setup.sh or pip install -r requirements.txt\n")
            sys.exit(1)


def get_active_session() -> str:
    """
    Retrieves the active session ID from config variables or session.json.
    """
    global IG_SESSION_ID
    if IG_SESSION_ID and IG_SESSION_ID.strip():
        return IG_SESSION_ID.strip()

    if SESSION_FILE.exists():
        try:
            with open(SESSION_FILE, "r") as f:
                data = json.load(f)
                sess = (data.get("cookies") or {}).get("sessionid") or (data.get("authorization_data") or {}).get("sessionid")
                if sess:
                    IG_SESSION_ID = sess
                    return sess
        except Exception:
            pass

    return ""


def save_session(session_id: str, audience: str = "mutual_followers") -> bool:
    """
    Directly writes and updates the session ID and audience inside config.py.
    """
    global IG_SESSION_ID, IG_AUDIENCE
    IG_SESSION_ID = session_id.strip()
    IG_AUDIENCE = audience.strip()

    try:
        content = CONFIG_FILE.read_text(encoding="utf-8")

        def replace_var(text, var_name, new_val, comment=""):
            pattern = rf'^{var_name}\s*=\s*.*$'
            comment_str = f"  {comment}" if comment else ""
            repl = f'{var_name} = {json.dumps(new_val)}{comment_str}'
            if re.search(pattern, text, flags=re.MULTILINE):
                return re.sub(pattern, lambda m: repl, text, flags=re.MULTILINE)
            return text + f'\n{repl}'

        content = replace_var(content, "IG_SESSION_ID", IG_SESSION_ID)
        content = replace_var(content, "IG_AUDIENCE", IG_AUDIENCE, '# Options: "mutual_followers" or "close_friends"')

        CONFIG_FILE.write_text(content, encoding="utf-8")
        return True
    except Exception as e:
        print(f"[!] Warning: Could not update config.py directly: {e}")
        return False
