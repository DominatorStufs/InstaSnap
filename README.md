# ⚡ InstaSnap — Instagram Instant & Story Uploader

<p align="center">
  <img src="banner.png" alt="InstaSnap Banner by DominatorStufs" width="100%" />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Author-DominatorStufs-purple.svg?logo=github" alt="Author" />
  <img src="https://img.shields.io/badge/Platform-Termux%20%7C%20Linux%20%7C%20Android-green.svg" alt="Platform" />
  <img src="https://img.shields.io/badge/Python-3.9%2B-blue.svg" alt="Python" />
  <img src="https://img.shields.io/badge/Instagram-Instant%20%28QuickSnap%29%20%26%20Story-E4405F.svg?logo=instagram" alt="Instagram" />
  <img src="https://img.shields.io/badge/Architecture-100%25%20Pure%20Python-yellow.svg" alt="Pure Python" />
  <img src="https://img.shields.io/badge/License-MIT-brightgreen.svg" alt="License" />
</p>

A clean, fast, lightweight command-line suite built specifically for **Termux on Android** and Linux. **InstaSnap** allows you to extract session cookies and upload disappearing **Instagram Instants (QuickSnap)** and **Stories** with verified account confirmation, strict single-file validation, and automatic zero-trace cache purging.

---

## 📁 Project Architecture & File Roles

Here is what each file does and why it exists:

```plaintext
instasnap/
├── 🚀 instant_uploader.py   # [FRONTEND] Primary execution script to upload media
├── 🍪 cookie_extractor.py   # [FRONTEND] Standalone login tool to get session cookies
├── ⚙️  config.py             # [SETTINGS] Central configuration (session ID & audience)
├── 🧠 insta_client.py       # [ENGINE] Core Instagram mobile API backend & device emulation
├── 📦 setup.sh              # [INSTALLER] 1-Click automated Termux environment setup
├── 📋 requirements.txt      # [DEPENDENCIES] Pure Python libraries (requests, rich)
├── 🛡️  .gitignore            # [SECURITY] Prevents committing sessions and media
├── 📜 LICENSE               # [LICENSE] MIT Open-Source License
├── 📖 README.md             # [DOCS] Full user manual & documentation
└── 📁 instant/              # [MEDIA FOLDER] Temporary folder where you place photos/videos
    ├── .gitkeep             # Preserves directory in Git
    └── __init__.py          # Permanent helper file (never deleted by cleanup)
```

---

## 🌟 Key Features

- **🛡️ Live Verified Account Dashboard:**
  - Validates your session cookie with Instagram and displays your **Instagram Full Name**, **Username**, and **User ID** in an active status card before uploading.
- **🍪 1-Click Cookie Extractor (`cookie_extractor.py`):**
  - Don't want to copy cookies from your web browser? Simply run `cookie_extractor.py`, enter your username and password, and it will handle 2FA/checkpoints, extract your `sessionid`, and **automatically update `config.py`**.
- **⚡ Fast Direct Session Authentication:**
  - Once your session is saved in `config.py`, future uploads are instant—no repeated passwords or login challenges.
- **📱 Real Device Emulation (`device.json`):**
  - Emulates an authentic Samsung Galaxy S24 Ultra with persistent hardware IDs to keep your account safe.
- **🛡️ Strict Single-File Policy:**
  - Verifies that **exactly one** media file is in `instant/`. If the folder is empty or contains multiple files, it halts with clear diagnostics.
- **🧹 Zero-Trace Automatic Cleanup:**
  - Uploaded media and temporary thumbnail cache files are **immediately deleted** after upload.
  - Permanent files (`__init__.py`, `.gitkeep`) are strictly preserved.
- **🎨 Modern Terminal UI:**
  - Dynamic spinners, checkmarks (`✔`), real-time upload progress bars, and clean rounded panels—100% in pure English!

---

## 🚀 Complete Step-by-Step Usage Guide

### Step 1: Termux Environment Setup
Open Termux and run:
```bash
# Update Termux packages and install prerequisites
pkg update -y && pkg install python ffmpeg git -y

# Run the automated installer
bash setup.sh
```

---

### Step 2: Extract Your Instagram Session Cookie
Run the standalone extractor:
```bash
python cookie_extractor.py
```

1. Enter your Instagram **Username** and **Password**.
2. If Two-Factor Authentication (2FA) is enabled, enter your 6-digit SMS or Authenticator code when prompted.
3. The script extracts your `sessionid` and **automatically saves it into `config.py`**!

*(Note: You only need to run this once or whenever your session cookie expires).*

---

### Step 3: Put Media in `instant/`
Copy or move **exactly one** photo or video into the `instant/` folder:

- **Supported Photos:** `.jpg`, `.jpeg`, `.png`, `.webp`, `.heic`
- **Supported Videos:** `.mp4`, `.mov`, `.m4v`, `.mkv` (recommended under 50 MB, 1-15 seconds)

```bash
# Example copying a photo from your phone storage in Termux:
cp /sdcard/DCIM/Camera/IMG_01.jpg instant/

# Example copying a video:
cp /sdcard/DCIM/Camera/VID_01.mp4 instant/
```

---

### Step 4: Dispatch Your Instant / Story
Run the uploader:
```bash
python instant_uploader.py
```

1. **Verified Dashboard:** The script connects to Instagram and displays your verified account card:
   ```text
   ╭──────────────────────── ✔ VERIFIED INSTAGRAM ACCOUNT ────────────────────────╮
   │                                                                              │
   │  👤 Account Name:  Your Full Name     🛡️ Status:         Verified & Active   │
   │  📛 Username:      @your_username     🎯 Upload          Instant             │
   │                                       Channel:           (QuickSnap)         │
   │  🆔 User ID:       17148601793        👥 Audience:       Mutual Followers    │
   │                                                                              │
   ╰──────────────────────────────────────────────────────────────────────────────╯
   ```
2. **Select Action:**
   - `[1]` 📸 Upload Single Photo (`instant/` folder)
   - `[2]` 🎥 Upload Single Video (`instant/` folder)
   - `[3]` 🔄 Switch / Update Instagram Session Cookie
   - `[4]` 🚪 Exit
3. **Choose Audience:**
   - `[1]` 👥 Mutual Followers / Friends (Default Instant)
   - `[2]` ⭐ Close Friends Only
4. **Auto-Purge:** As soon as Instagram confirms publication, the media file in `instant/` is automatically deleted!

---

## ⚙️ Configuration Reference (`config.py`)

Settings are stored directly in `config.py` without requiring any `.env` file:

```python
# Instagram Authentication & Credentials
IG_SESSION_ID = "17148601793%3AQx7982..."  # Automatically populated by cookie_extractor.py

# Default Target Audience for Instants:
#   • "mutual_followers" -> Shows to mutual followers (Friends who follow each other)
#   • "close_friends"    -> Shows ONLY to your Instagram Close Friends list
IG_AUDIENCE = "mutual_followers"

# Media Upload Limits
MAX_VIDEO_SIZE_MB = 100.0           # Absolute ceiling enforced by Instagram API
RECOMMENDED_VIDEO_SIZE_MB = 50.0    # Optimal QuickSnap limit (1-15s clips)
```

---

## 🛡️ Single-File Policy & Error Guard

| Scenario | Script Behavior | Resolution |
| :--- | :--- | :--- |
| **0 files in `instant/`** | ⚠️ Displays yellow warning panel: `FOLDER IS EMPTY` | Move 1 photo or video into `instant/`. |
| **>1 files in `instant/`** | 🛑 Displays red error table listing all files: `STRICT POLICY VIOLATION` | Delete extra files until only 1 remains. |
| **Video placed, Picture selected** | 🛑 Displays `TYPE MISMATCH: Found video, selected Picture` | Select option `[2]` or replace with a photo. |
| **Photo placed, Video selected** | 🛑 Displays `TYPE MISMATCH: Found photo, selected Video` | Select option `[1]` or replace with a video. |
| **`__init__.py` in `instant/`** | 🔒 Fully ignored by file counter and protected from deletion | Remains permanently in folder. |
| **Upload succeeds** | ✅ Media file and all temporary cache files deleted immediately | Folder is reset clean for next run. |

---

## ❓ Frequently Asked Questions (FAQ)

**Q1: What is the difference between QuickSnap (Instant) and Story?**  
Instagram Instants (QuickSnaps) appear in the direct message inbox stack for mutual followers or close friends and disappear after viewing. If an account has QuickSnap restricted, InstaSnap automatically falls back to standard Instagram Stories.

**Q2: How often do I need to run `cookie_extractor.py`?**  
Only once! Once extracted, the session is saved in `config.py` and reused for all future runs. You only run it again if you log out of Instagram or change your password.

---

## 📜 License
This project is open-source and released under the [MIT License](LICENSE).
