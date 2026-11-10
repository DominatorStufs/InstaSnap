# ⚡ InstaSnap --- Instagram Instant (QuickSnap) Uploader

![InstaSnap Banner](banner.png)

![Author](https://img.shields.io/badge/Author-DominatorStufs-purple.svg?logo=github) ![Platform](https://img.shields.io/badge/Platform-Termux%20%7C%20Linux%20%7C%20Android-green.svg) ![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg) ![Instagram](https://img.shields.io/badge/Instagram-Instant%20%28QuickSnap%29-E4405F.svg?logo=instagram) ![Architecture](https://img.shields.io/badge/Architecture-Python-yellow.svg) ![License](https://img.shields.io/badge/License-MIT-brightgreen.svg)

[![XERJ Corpus Hub Contributor](https://hub.xerj.org/contributors/DominatorStufs/badge.svg)](https://hub.xerj.org/contributors/DominatorStufs)

**InstaSnap** is a command-line toolkit designed for Termux on Android and Linux. It provides tools for working with Instagram media, including an Instant (QuickSnap) uploader and a downloader for Reels, posts, carousels, and stories.

> **Important:** Instagram may change or restrict its services and APIs at any time. This project is independent and is not affiliated with, endorsed by, or supported by Instagram or Meta. Use it only with accounts and content you are authorized to access, and follow Instagram's terms and applicable laws.

------------------------------------------------------------------------

## 🌐 Featured on XERJ Corpus Hub

InstaSnap has been included in the **XERJ Corpus Hub**, an open reference collection intended to help developers and AI coding agents discover real-world open-source implementations.

-   **Contributor:** DominatorStufs
-   **Project:** InstaSnap
-   **Contributor profile:** [DominatorStufs on XERJ](https://hub.xerj.org/contributors/DominatorStufs)
-   **Repository:** [DominatorStufs/InstaSnap](https://github.com/DominatorStufs/InstaSnap)

The XERJ listing makes the project discoverable as a code reference. It does not imply endorsement by XERJ, Instagram, or Meta.

------------------------------------------------------------------------

## 🎬 Live Product Walkthrough

Watch the project walkthrough:

https://github.com/user-attachments/assets/99dce6ee-6e8a-40d4-8d4d-c6cbb79816cb

------------------------------------------------------------------------

## 📁 Project Architecture & File Roles

``` text
instasnap/
├── instant_uploader.py   # Instagram Instant (QuickSnap) uploader
├── insta_downloader.py   # Reels, posts, carousels, and stories downloader
├── cookie_extractor.py   # Login/session extraction helper
├── config.py             # Local settings (may contain sensitive session data)
├── insta_client.py       # Core Instagram client and request handling
├── setup.sh              # Termux/Linux setup script
├── requirements.txt      # Python dependencies
├── .gitignore            # Excludes local secrets and temporary files
├── LICENSE               # MIT license
├── README.md             # Project documentation
└── instant/              # Temporary upload media folder
    ├── .gitkeep
    └── __init__.py
```

The exact files in your checkout may differ. Keep local credentials, generated device identifiers, and temporary media out of version control.

------------------------------------------------------------------------

## 🌟 Key Features

-   **Account status display:** Checks the configured session and displays account information when the service responds successfully.
-   **Session helper:** `cookie_extractor.py` can obtain a session for local use and update the local configuration.
-   **Session-based authentication:** Reuses a locally stored session rather than asking for credentials on every run.
-   **Device configuration:** Supports persistent device settings where implemented by the client.
-   **Single-file upload validation:** The uploader checks that the `instant/` folder contains exactly one eligible media file before proceeding.
-   **Temporary-file cleanup:** Removes upload media and temporary cache files after a successful upload, while preserving designated helper files.
-   **Terminal interface:** Uses terminal status panels, progress indicators, and prompts.
-   **Media downloader:** Supports downloading supported public media and, where authorized and available, content accessible to the signed-in account.

Feature availability depends on Instagram's current service behavior and the implementation in the checked-out version.

------------------------------------------------------------------------

## 🚀 Installation & Usage

### Step 1: Prepare Termux

Update packages and install prerequisites:

``` bash
pkg update -y
pkg install python ffmpeg git -y
```

Clone the repository and enter its directory:

``` bash
git clone https://github.com/DominatorStufs/InstaSnap.git
cd InstaSnap
```

Run the setup script:

``` bash
bash setup.sh
```

If you already have the repository, update it with your preferred Git workflow rather than cloning it again.

### Step 2: Configure your Instagram session

Run the helper:

``` bash
python cookie_extractor.py
```

Follow the prompts shown by the program. If two-factor authentication or an Instagram checkpoint is requested, complete it only through the expected, trusted flow.

**Session security:** - A session cookie is equivalent to a credential. Anyone who obtains it may be able to access your account. - Never send your session cookie, password, 2FA code, or `config.py` to anyone. - Never paste live credentials into GitHub issues, screenshots, logs, or public chat. - Store credentials only on a device you control. - If you believe a session has been exposed, log out/revoke active sessions through Instagram's account security settings and create a new session only if needed. - Do not commit a populated `config.py`. Keep secrets in local, ignored files.

### Step 3: Add one media file

Place exactly one supported photo or video in the `instant/` folder.

**Supported photo extensions:** `.jpg`, `.jpeg`, `.png`, `.webp`, `.heic`

**Supported video extensions:** `.mp4`, `.mov`, `.m4v`, `.mkv`

Example:

``` bash
cp /sdcard/DCIM/Camera/IMG_01.jpg instant/
```

Or:

``` bash
cp /sdcard/DCIM/Camera/VID_01.mp4 instant/
```

The actual supported formats and size/duration limits depend on the current implementation and Instagram's restrictions.

### Step 4: Run the uploader

``` bash
python instant_uploader.py
```

Follow the on-screen prompts. Depending on the current version, the program may offer actions such as:

1.  Upload a photo
2.  Upload a video (if enabled)
3.  View or manage Instant history
4.  Update the configured session
5.  Exit

Choose the audience and other options only as presented by the application. Do not assume that a successful local request guarantees Instagram will publish or deliver the media.

------------------------------------------------------------------------

## ⚙️ Configuration Reference

The project uses `config.py` for local settings. The following is a **safe example only**; do not replace it with a real session value in this README:

``` python
# Local Instagram authentication.
# Keep the real value private and do not commit it.
IG_SESSION_ID = "YOUR_INSTAGRAM_SESSION_ID"

# Default audience setting:
# "mutual_followers" or "close_friends", if supported by your version.
IG_AUDIENCE = "mutual_followers"

# Example media settings, if supported by your version.
MAX_VIDEO_SIZE_MB = 100.0
RECOMMENDED_VIDEO_SIZE_MB = 50.0
```

Do not publish actual usernames, numeric account IDs, session cookies, passwords, access tokens, or device identifiers in examples.

------------------------------------------------------------------------

## 🛡️ Upload Validation & Cleanup

  --------------------------------------------------------------------------------------------------------------------
  Situation                           Expected handling
  ----------------------------------- --------------------------------------------------------------------------------
  No eligible files in `instant/`     The uploader should report that the folder is empty.

  More than one eligible media file   The uploader should stop and ask you to leave one file.

  Unsupported file type               The uploader should reject the file or report the unsupported format.

  Upload succeeds                     Temporary media/cache cleanup may run according to the implementation.

  Upload fails                        Check the error output before retrying; verify whether temporary files remain.
  --------------------------------------------------------------------------------------------------------------------

Always keep a separate backup of original media. Automatic cleanup is not a substitute for a backup.

------------------------------------------------------------------------

## 📥 InstaDownloader --- Reels, Posts & Stories

Run the downloader:

``` bash
python insta_downloader.py
```

The project includes a downloader intended for supported Instagram media types, including:

-   Public Reels, posts, and carousels.
-   Stories and private-account media only when the signed-in account is authorized to view them and the implementation supports the request.
-   Organized downloads in a dedicated folder where supported.
-   Progress information during downloads.

Respect creators' rights and privacy. Do not download, redistribute, or publish content without permission where permission is required.

------------------------------------------------------------------------

## ❓ Frequently Asked Questions

**Q1: What is an Instagram Instant (QuickSnap)?**

Instagram features and names can change over time. InstaSnap's uploader is intended to work with the Instant/QuickSnap workflow implemented by this project. Availability depends on Instagram's current service behavior.

**Q2: Do I need to obtain a session every time?**

The project is designed to reuse a locally stored session while it remains valid. Instagram may expire or revoke sessions, in which case you may need to authenticate again.

**Q3: Is it safe to share my `config.py`?**

No, not if it contains a real session cookie or other credentials. Keep it private and excluded from Git.

**Q4: Does XERJ inclusion mean Instagram officially supports this project?**

No. XERJ inclusion is a separate code-discovery listing. InstaSnap is an independent project and is not affiliated with Instagram or Meta.

------------------------------------------------------------------------

## 🔐 Repository Security Checklist

Before pushing changes to GitHub, verify that:

-   [ ] No real Instagram session cookie is present in tracked files.
-   [ ] No passwords, 2FA codes, access tokens, or private keys are present.
-   [ ] Local configuration and device files containing secrets are ignored.
-   [ ] Temporary media and downloaded private content are not committed.
-   [ ] Previous commits have been checked for accidentally committed secrets.

Example `.gitignore` entries (adjust to your actual project structure):

``` gitignore
# Local credentials and configuration
config.py
.env
.env.*
device.json
session*
*cookie*

# Python
__pycache__/
*.py[cod]
.venv/
venv/

# Temporary media and caches
instant/*
!instant/.gitkeep
!instant/__init__.py
*.tmp
*.cache
```

**Important:** If a secret was committed in the past, adding it to `.gitignore` does not remove it from Git history. Revoke or rotate the exposed credential first, then clean the repository history if appropriate.

------------------------------------------------------------------------

## 🤝 Community & Recognition

-   **XERJ Contributor Profile:** [DominatorStufs](https://hub.xerj.org/contributors/DominatorStufs)
-   **XERJ Corpus Hub:** [hub.xerj.org](https://hub.xerj.org/)
-   **GitHub Repository:** [DominatorStufs/InstaSnap](https://github.com/DominatorStufs/InstaSnap)

If you find a problem or have a suggestion, please open an issue in the GitHub repository. Do not include credentials, session cookies, or private account information in an issue.

------------------------------------------------------------------------

## 📜 License

This project is released under the [MIT License](LICENSE).

------------------------------------------------------------------------

**Made with ⚡ by [DominatorStufs](https://github.com/DominatorStufs)**
