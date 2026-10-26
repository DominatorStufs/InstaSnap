#!/usr/bin/env python3
"""
=============================================================================
InstaDownloader - All-in-One Instagram Media Downloader
=============================================================================
Features:
  • Download Reels, Posts (Photos/Videos), Carousels & Stories
  • Public Profiles & Content: Download freely without login
  • Private Profiles & Stories: Authenticate with Instagram Session ID (Cookie)
  • Verified Account Card displayed on startup (Name, Username, ID)
  • Automatic Android / Termux Storage Detection:
      Saved to: /sdcard/Download/insta-download/<target_username>/
  • Chunked stream downloader with real-time Rich progress bar & speed
  • Fully interactive CLI with zero-setup portability

Author: @DominatorStufs
=============================================================================
"""

import os
import sys
import re
import json
import time
import uuid
import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urlparse

# Ensure requests and rich are installed
try:
    import requests
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.progress import (
        Progress,
        SpinnerColumn,
        TextColumn,
        BarColumn,
        DownloadColumn,
        TransferSpeedColumn,
        TimeRemainingColumn,
    )
    from rich.prompt import Prompt, Confirm
    from rich.text import Text
    from rich import box
except ImportError:
    print("\n[!] Installing required dependencies (requests, rich)...")
    os.system(f"{sys.executable} -m pip install requests rich")
    try:
        import requests
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table
        from rich.progress import (
            Progress,
            SpinnerColumn,
            TextColumn,
            BarColumn,
            DownloadColumn,
            TransferSpeedColumn,
            TimeRemainingColumn,
        )
        from rich.prompt import Prompt, Confirm
        from rich.text import Text
        from rich import box
    except ImportError:
        print("[✗] Error: Please run: pip install requests rich")
        sys.exit(1)

console = Console()

# =============================================================================
# Constants & Storage Configuration
# =============================================================================

SESSION_FILE = Path("downloader_session.json")
APP_VERSION = "330.0.0.35.110"
USER_AGENT = (
    f"Instagram {APP_VERSION} Android (34/14; 480dpi; 1080x2400; "
    "samsung; SM-S928B; e3q; qcom; en_US; 590123456)"
)
WEB_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)

# Base64 codec alphabet for shortcode <-> media_id conversion
CODEC_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"


# =============================================================================
# Helper Functions: Codecs & File Sanitization
# =============================================================================

def shortcode_to_media_id(shortcode: str) -> int:
    """Converts an Instagram Base64 URL shortcode to numeric media ID."""
    base = len(CODEC_ALPHABET)
    num = 0
    for char in shortcode.strip():
        if char in CODEC_ALPHABET:
            num = num * base + CODEC_ALPHABET.index(char)
    return num


def media_id_to_shortcode(media_id: int) -> str:
    """Converts a numeric Instagram media ID to Base64 URL shortcode."""
    base = len(CODEC_ALPHABET)
    num = int(media_id)
    if num == 0:
        return CODEC_ALPHABET[0]
    res = []
    while num:
        res.append(CODEC_ALPHABET[num % base])
        num //= base
    return "".join(reversed(res))


def sanitize_filename(name: str) -> str:
    """Removes invalid filesystem characters."""
    return re.sub(r'[\\/*?:"<>|]', "", name).strip().replace(" ", "_")


def format_bytes(size_bytes: int) -> str:
    """Formats bytes into readable KB/MB string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MB"


def get_base_download_dir() -> Path:
    """
    Finds the user's phone Download directory on Android / Termux,
    or falls back to standard user Downloads folder on PC / Linux.
    Folder structure: .../Download/insta-download/
    """
    candidates = [
        Path("/sdcard/Download"),
        Path("/storage/emulated/0/Download"),
        Path.home() / "storage" / "shared" / "Download",
        Path.home() / "Downloads",
        Path.cwd() / "Downloads",
    ]
    for c in candidates:
        try:
            if c.exists() and os.access(str(c), os.W_OK):
                target = c / "insta-download"
                target.mkdir(parents=True, exist_ok=True)
                return target
        except Exception:
            continue

    # Default fallback to ~/Downloads/insta-download
    fallback = Path.home() / "Downloads" / "insta-download"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def get_user_download_dir(username: str) -> Path:
    """
    Returns the target folder for a specific user:
    .../Download/insta-download/<username>/
    """
    clean_user = sanitize_filename(username) or "instagram_user"
    user_dir = get_base_download_dir() / clean_user
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir


# =============================================================================
# Session & Token Management
# =============================================================================

def load_saved_session() -> str:
    """Loads saved session ID from local json or InstaSnap config.py."""
    # 1. Local session file
    if SESSION_FILE.exists():
        try:
            with open(SESSION_FILE, "r") as f:
                data = json.load(f)
                sid = data.get("session_id", "").strip()
                if sid:
                    return sid
        except Exception:
            pass

    # 2. Check if config.py from InstaSnap exists in current directory
    try:
        import config
        sid = getattr(config, "IG_SESSION_ID", "") or config.get_active_session()
        if sid and sid.strip():
            return sid.strip()
    except Exception:
        pass

    return ""


def save_session(session_id: str):
    """Saves session ID to local json and updates config.py if present."""
    session_id = session_id.strip()
    try:
        with open(SESSION_FILE, "w") as f:
            json.dump({"session_id": session_id, "updated_at": time.time()}, f, indent=2)
    except Exception:
        pass

    try:
        import config
        config.save_session(session_id)
    except Exception:
        pass


def delete_saved_session():
    """Removes stored session credentials."""
    if SESSION_FILE.exists():
        try:
            SESSION_FILE.unlink()
        except Exception:
            pass


# =============================================================================
# Core Downloader Engine
# =============================================================================

class InstagramDownloader:
    """
    All-in-one Instagram Downloader supporting Public and Private media.
    Uses official mobile Android API endpoints with session authentication.
    """

    def __init__(self, session_id: str = ""):
        self.session_id = session_id.strip()
        self.session = requests.Session()
        self.user_id = ""
        self.username = ""
        self.full_name = ""
        self.is_authenticated = False

        if self.session_id:
            self.authenticate()

    def authenticate(self) -> bool:
        """Verifies session ID cookie and retrieves account details."""
        if not self.session_id:
            self.is_authenticated = False
            return False

        # Extract numeric user_id from sessionid prefix if available
        # Format: <user_id>%3A<token>
        m = re.match(r"^(\d+)%3A", self.session_id)
        if m:
            self.user_id = m.group(1)

        headers = {
            "User-Agent": USER_AGENT,
            "Accept-Language": "en-US",
            "Accept-Encoding": "gzip, deflate",
            "Host": "i.instagram.com",
            "X-IG-App-ID": "936619743392459",
            "X-IG-Capabilities": "3brTv10=",
            "Cookie": f"sessionid={self.session_id}; ds_user_id={self.user_id};",
        }
        self.session.headers.clear()
        self.session.headers.update(headers)

        # Call accounts/current_user/?edit=true
        url = "https://i.instagram.com/api/v1/accounts/current_user/?edit=true"
        try:
            resp = self.session.get(url, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                user = data.get("user", {})
                self.username = user.get("username", "")
                self.full_name = user.get("full_name", "") or self.username
                self.user_id = str(user.get("pk", self.user_id))
                self.is_authenticated = True
                return True
        except Exception:
            pass

        self.is_authenticated = False
        return False

    def get_user_info(self, username: str) -> Optional[Dict[str, Any]]:
        """Resolves target username to user info (user_id, privacy status, full_name)."""
        username = username.strip().lstrip("@")

        if self.is_authenticated:
            url = f"https://i.instagram.com/api/v1/users/{username}/usernameinfo/"
            try:
                r = self.session.get(url, timeout=15)
                if r.status_code == 200:
                    return r.json().get("user")
            except Exception:
                pass

        # Public web fallback
        url = f"https://www.instagram.com/api/v1/users/web_profile_info/?username={username}"
        headers = {
            "User-Agent": WEB_USER_AGENT,
            "X-IG-App-ID": "936619743392459",
            "Sec-Fetch-Site": "same-origin",
        }
        try:
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code == 200:
                user = r.json().get("data", {}).get("user")
                if user:
                    return {
                        "pk": user.get("id"),
                        "username": user.get("username"),
                        "full_name": user.get("full_name"),
                        "is_private": user.get("is_private", False),
                        "profile_pic_url": user.get("profile_pic_url"),
                    }
        except Exception:
            pass

        return None

    def get_media_info(self, shortcode_or_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves media details for a Post, Reel, or Carousel."""
        clean_input = shortcode_or_id.strip()

        # Check if numeric ID or shortcode
        if clean_input.isdigit():
            media_id = clean_input
        else:
            media_id = str(shortcode_to_media_id(clean_input))

        # Primary method: Authenticated private mobile API (100% reliable for public & private)
        if self.is_authenticated:
            url = f"https://i.instagram.com/api/v1/media/{media_id}/info/"
            try:
                r = self.session.get(url, timeout=20)
                if r.status_code == 200:
                    items = r.json().get("items", [])
                    if items:
                        return items[0]
            except Exception:
                pass

        # Fallback: Public web GraphQL query
        shortcode = clean_input if not clean_input.isdigit() else media_id_to_shortcode(int(clean_input))
        url = "https://www.instagram.com/graphql/query/"
        headers = {
            "User-Agent": WEB_USER_AGENT,
            "X-IG-App-ID": "936619743392459",
        }
        params = {
            "doc_id": "8845758582119845",
            "variables": json.dumps({"shortcode": shortcode}),
        }
        try:
            r = requests.get(url, params=params, headers=headers, timeout=20)
            if r.status_code == 200:
                media = r.json().get("data", {}).get("xdt_shortcode_media")
                if media:
                    # Adapt to standard item format
                    return self._adapt_graphql_media(media)
        except Exception:
            pass

        return None

    def get_user_stories(self, user_id: str) -> List[Dict[str, Any]]:
        """Retrieves all active 24h stories for a user (Requires session authentication)."""
        if not self.is_authenticated:
            return []

        url = f"https://i.instagram.com/api/v1/feed/user/{user_id}/story/"
        try:
            r = self.session.get(url, timeout=20)
            if r.status_code == 200:
                reel = r.json().get("reel") or {}
                return reel.get("items", [])
        except Exception:
            pass

        return []

    def get_user_recent_posts(self, user_id: str, count: int = 10) -> List[Dict[str, Any]]:
        """Retrieves recent posts and reels published by a user."""
        if not self.is_authenticated:
            return []

        url = f"https://i.instagram.com/api/v1/feed/user/{user_id}/"
        try:
            r = self.session.get(url, timeout=20)
            if r.status_code == 200:
                items = r.json().get("items", [])
                return items[:count]
        except Exception:
            pass

        return []

    def _adapt_graphql_media(self, media: Dict[str, Any]) -> Dict[str, Any]:
        """Translates GraphQL format into standard mobile API dictionary."""
        owner = media.get("owner", {})
        adapted = {
            "id": media.get("id"),
            "code": media.get("shortcode"),
            "user": {
                "username": owner.get("username", "unknown"),
                "full_name": owner.get("full_name", ""),
                "pk": owner.get("id", ""),
            },
            "taken_at": media.get("taken_at_timestamp", int(time.time())),
            "media_type": 2 if media.get("is_video") else 1,
        }

        if media.get("is_video") and media.get("video_url"):
            adapted["video_versions"] = [{"url": media.get("video_url")}]
        if media.get("display_url"):
            adapted["image_versions2"] = {"candidates": [{"url": media.get("display_url")}]}

        # Carousels
        edges = media.get("edge_sidecar_to_children", {}).get("edges", [])
        if edges:
            adapted["media_type"] = 8  # Carousel
            adapted["carousel_media"] = []
            for edge in edges:
                node = edge.get("node", {})
                child = {
                    "id": node.get("id"),
                    "media_type": 2 if node.get("is_video") else 1,
                }
                if node.get("is_video") and node.get("video_url"):
                    child["video_versions"] = [{"url": node.get("video_url")}]
                if node.get("display_url"):
                    child["image_versions2"] = {"candidates": [{"url": node.get("display_url")}]}
                adapted["carousel_media"].append(child)

        return adapted


# =============================================================================
# Download File Streamer with Rich Progress
# =============================================================================

def download_stream(url: str, dest_path: Path, title: str = "Downloading") -> bool:
    """Downloads a media file with chunked streaming and a live Rich progress bar."""
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = dest_path.with_suffix(f"{dest_path.suffix}.tmp")

    headers = {
        "User-Agent": WEB_USER_AGENT,
        "Accept-Encoding": "identity",
    }

    try:
        with requests.get(url, headers=headers, stream=True, timeout=30) as response:
            response.raise_for_status()
            total_size = int(response.headers.get("content-length", 0))

            with Progress(
                SpinnerColumn(spinner_name="dots12", style="bold cyan"),
                TextColumn("[bold white]{task.description}"),
                BarColumn(bar_width=None, complete_style="bold green", finished_style="bold bright_green"),
                DownloadColumn(),
                TransferSpeedColumn(),
                TimeRemainingColumn(),
                console=console,
                transient=True,
            ) as progress:
                task = progress.add_task(f"[cyan]{title}[/cyan]", total=total_size if total_size > 0 else None)
                with open(temp_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=65536):
                        if chunk:
                            f.write(chunk)
                            progress.update(task, advance=len(chunk))

        # Atomic rename once download completes
        if temp_path.exists():
            if dest_path.exists():
                dest_path.unlink()
            temp_path.rename(dest_path)
            return True

    except Exception as e:
        console.print(f"[bold red]  ✗ Download failed: {e}[/bold red]")
        if temp_path.exists():
            try:
                temp_path.unlink()
            except Exception:
                pass
        return False

    return False


# =============================================================================
# Media Parsing & Dispatch Handlers
# =============================================================================

def parse_instagram_url(raw_input: str) -> Dict[str, str]:
    """Parses any Instagram URL, shortcode, or username into a structured dictionary."""
    text = raw_input.strip()

    # Match specific Story URL with media ID
    m_story_item = re.search(r"stories/([a-zA-Z0-9._]+)/(\d+)", text)
    if m_story_item:
        return {"type": "story_item", "username": m_story_item.group(1), "story_id": m_story_item.group(2)}

    # Match Story profile URL
    m_story_user = re.search(r"stories/([a-zA-Z0-9._]+)", text)
    if m_story_user:
        return {"type": "story_user", "username": m_story_user.group(1)}

    # Match Reel or Post URL
    m_code = re.search(r"(?:p|reel|reels|tv|share\/p)\/([A-Za-z0-9_-]+)", text)
    if m_code:
        return {"type": "post_or_reel", "shortcode": m_code.group(1)}

    # Match Profile URL
    m_profile = re.search(r"instagram\.com\/([a-zA-Z0-9._]+)", text)
    if m_profile and m_profile.group(1) not in ("p", "reel", "reels", "stories", "explore", "tv"):
        return {"type": "profile", "username": m_profile.group(1)}

    # Raw @username
    if text.startswith("@"):
        return {"type": "profile", "username": text.lstrip("@")}

    # Shortcode directly entered
    if len(text) in range(10, 14) and re.match(r"^[A-Za-z0-9_-]+$", text):
        return {"type": "post_or_reel", "shortcode": text}

    # Plain username entered
    if re.match(r"^[a-zA-Z0-9._]+$", text):
        return {"type": "profile", "username": text}

    return {"type": "unknown", "raw": text}


def download_media_item(downloader: InstagramDownloader, item: Dict[str, Any], custom_prefix: str = "") -> List[Path]:
    """
    Downloads a single media object (Photo, Video, Reel, or Carousel)
    into: .../Download/insta-download/<owner_username>/
    """
    owner = item.get("user") or {}
    username = owner.get("username") or "instagram_user"
    user_dir = get_user_download_dir(username)

    media_id = str(item.get("id") or item.get("pk") or int(time.time()))
    shortcode = item.get("code") or (media_id_to_shortcode(int(media_id)) if media_id.isdigit() else media_id[:11])
    taken_at = item.get("taken_at") or int(time.time())
    date_str = datetime.datetime.fromtimestamp(taken_at).strftime("%Y%m%d_%H%M%S")

    saved_paths: List[Path] = []
    media_type = item.get("media_type", 1)

    # -------------------------------------------------------------------------
    # Case A: Carousel / Album (media_type == 8)
    # -------------------------------------------------------------------------
    if media_type == 8 and item.get("carousel_media"):
        carousel_items = item.get("carousel_media", [])
        console.print(f"\n[bold cyan]📦 Multi-Media Carousel Detected ({len(carousel_items)} items):[/bold cyan]")

        for idx, child in enumerate(carousel_items, 1):
            c_type = child.get("media_type", 1)
            is_vid = c_type == 2 or bool(child.get("video_versions"))
            ext = "mp4" if is_vid else "jpg"

            url = ""
            if is_vid and child.get("video_versions"):
                url = child["video_versions"][0].get("url")
            elif child.get("image_versions2", {}).get("candidates"):
                url = child["image_versions2"]["candidates"][0].get("url")

            if not url:
                continue

            fname = f"{username}_carousel_{date_str}_{shortcode}_{idx}.{ext}"
            dest = user_dir / fname
            label = f"Item {idx}/{len(carousel_items)} ({ext.upper()})"

            if download_stream(url, dest, title=label):
                saved_paths.append(dest)
                console.print(f"  [bold green]✔[/bold green] Saved: [white]{fname}[/white] ({format_bytes(dest.stat().st_size)})")

    # -------------------------------------------------------------------------
    # Case B: Video / Reel (media_type == 2)
    # -------------------------------------------------------------------------
    elif media_type == 2 or item.get("video_versions"):
        url = item.get("video_versions", [{}])[0].get("url")
        if not url and item.get("image_versions2", {}).get("candidates"):
            # Fallback cover
            url = item["image_versions2"]["candidates"][0].get("url")
            ext = "jpg"
        else:
            ext = "mp4"

        if url:
            tag = custom_prefix or ("story" if "story" in custom_prefix else "reel")
            fname = f"{username}_{tag}_{date_str}_{shortcode}.{ext}"
            dest = user_dir / fname

            if download_stream(url, dest, title=f"Downloading {tag.title()}"):
                saved_paths.append(dest)
                console.print(f"  [bold green]✔[/bold green] Saved: [white]{fname}[/white] ({format_bytes(dest.stat().st_size)})")

    # -------------------------------------------------------------------------
    # Case C: Single Photo (media_type == 1)
    # -------------------------------------------------------------------------
    else:
        url = ""
        candidates = item.get("image_versions2", {}).get("candidates", [])
        if candidates:
            url = candidates[0].get("url")

        if url:
            tag = custom_prefix or "photo"
            fname = f"{username}_{tag}_{date_str}_{shortcode}.jpg"
            dest = user_dir / fname

            if download_stream(url, dest, title=f"Downloading {tag.title()}"):
                saved_paths.append(dest)
                console.print(f"  [bold green]✔[/bold green] Saved: [white]{fname}[/white] ({format_bytes(dest.stat().st_size)})")

    return saved_paths


# =============================================================================
# Interactive Workflow Actions
# =============================================================================

def handle_url_download(downloader: InstagramDownloader):
    """Processes any Instagram URL (Reel, Post, Carousel, or Story)."""
    raw_url = Prompt.ask("\n[bold cyan]🔗 Enter or Paste Instagram URL (Reel / Post / Story)[/bold cyan]").strip()
    if not raw_url:
        return

    parsed = parse_instagram_url(raw_url)
    p_type = parsed.get("type")

    # 1. Post or Reel URL
    if p_type == "post_or_reel":
        shortcode = parsed["shortcode"]
        console.print(f"\n[dim][*] Fetching media details for shortcode: [bold white]{shortcode}[/bold white]...[/dim]")
        item = downloader.get_media_info(shortcode)

        if not item:
            console.print(
                Panel(
                    "[bold red]Could not retrieve media details.[/bold red]\n\n"
                    "Possible causes:\n"
                    "• The post is from a [bold yellow]Private Account[/bold yellow].\n"
                    "• Instagram temporarily rate-limited anonymous web scraping.\n\n"
                    "💡 [bold green]Solution:[/bold green] Set your Instagram Session Token (Option [4]) "
                    "to download private & public media with 100% reliability!",
                    title="[bold red]Fetch Failed[/bold red]",
                    border_style="red",
                    box=box.ROUNDED,
                )
            )
            return

        saved = download_media_item(downloader, item)
        if saved:
            render_success_panel(saved, item.get("user", {}).get("username", "user"))

    # 2. Story URL
    elif p_type in ("story_item", "story_user"):
        username = parsed["username"]
        handle_story_download_flow(downloader, target_username=username, target_story_id=parsed.get("story_id"))

    # 3. Profile URL
    elif p_type == "profile":
        handle_profile_posts_flow(downloader, target_username=parsed["username"])

    else:
        console.print("[bold red][✗] Unrecognized Instagram URL format. Please enter a valid Reel, Post, or Story link.[/bold red]")


def handle_story_download_flow(downloader: InstagramDownloader, target_username: str = "", target_story_id: str = ""):
    """Downloads all active stories for a given username."""
    if not target_username:
        target_username = Prompt.ask("\n[bold cyan]📖 Enter Target Username for Story Download[/bold cyan]").strip().lstrip("@")
    if not target_username:
        return

    # Check authentication requirement for stories
    if not downloader.is_authenticated:
        console.print(
            Panel(
                "[bold yellow]⚠️ Stories Require an Active Session Token[/bold yellow]\n\n"
                "Instagram's backend enforces authentication to access user stories.\n"
                "You can authenticate instantly by providing your [bold cyan]sessionid[/bold cyan] cookie.",
                border_style="yellow",
                box=box.ROUNDED,
            )
        )
        if Confirm.ask("[bold green]Would you like to enter your session ID right now?[/bold green]", default=True):
            set_session_interactive(downloader)
            if not downloader.is_authenticated:
                return
        else:
            return

    console.print(f"\n[dim][*] Resolving user profile: @{target_username}...[/dim]")
    user_info = downloader.get_user_info(target_username)
    if not user_info:
        console.print(f"[bold red][✗] User '@{target_username}' not found or account is unavailable.[/bold red]")
        return

    user_id = str(user_info.get("pk") or user_info.get("id"))
    is_private = user_info.get("is_private", False)

    if is_private:
        console.print(f"[bold yellow]🔒 Account @{target_username} is Private.[/bold yellow] Accessing via your authenticated session...")

    console.print(f"[dim][*] Querying active stories for @{target_username}...[/dim]")
    stories = downloader.get_user_stories(user_id)

    if not stories:
        console.print(
            Panel(
                f"[bold yellow]No active stories found for @{target_username}.[/bold yellow]\n\n"
                "Possible reasons:\n"
                "• User hasn't posted a story in the last 24 hours.\n"
                "• Story was posted to Close Friends only and you are not on the list.\n"
                "• Account is private and your logged-in account does not follow them.",
                title="[bold yellow]0 Stories Found[/bold yellow]",
                border_style="yellow",
                box=box.ROUNDED,
            )
        )
        return

    # Filter for specific story_id if requested
    if target_story_id:
        stories = [s for s in stories if str(s.get("id") or s.get("pk")).startswith(target_story_id)] or stories

    console.print(f"\n[bold green]✔ Found {len(stories)} active story item(s) for @{target_username}![/bold green]")
    all_saved: List[Path] = []

    for idx, story in enumerate(stories, 1):
        console.print(f"\n[bold cyan]Downloading Story {idx}/{len(stories)}:[/bold cyan]")
        saved = download_media_item(downloader, story, custom_prefix="story")
        all_saved.extend(saved)

    if all_saved:
        render_success_panel(all_saved, target_username)


def handle_profile_posts_flow(downloader: InstagramDownloader, target_username: str = ""):
    """Downloads recent posts / reels from a user's profile."""
    if not target_username:
        target_username = Prompt.ask("\n[bold cyan]🎥 Enter Target Username for Media Download[/bold cyan]").strip().lstrip("@")
    if not target_username:
        return

    if not downloader.is_authenticated:
        console.print("[dim][*] Checking public profile details...[/dim]")

    user_info = downloader.get_user_info(target_username)
    if not user_info:
        console.print(f"[bold red][✗] Could not find account '@{target_username}'.[/bold red]")
        return

    user_id = str(user_info.get("pk") or user_info.get("id"))
    is_private = user_info.get("is_private", False)

    if is_private and not downloader.is_authenticated:
        console.print(
            Panel(
                f"[bold red]🔒 Account @{target_username} is Private[/bold red]\n\n"
                "Private profile media cannot be downloaded without login.\n"
                "Please add your Instagram Session Token (Option [4]) to access private profiles you follow.",
                title="[bold red]Private Profile Guard[/bold red]",
                border_style="red",
                box=box.ROUNDED,
            )
        )
        return

    amount_str = Prompt.ask("[bold yellow]How many recent posts/reels to download?[/bold yellow]", default="5")
    try:
        amount = max(1, min(50, int(amount_str)))
    except ValueError:
        amount = 5

    console.print(f"\n[dim][*] Fetching {amount} recent items for @{target_username}...[/dim]")
    posts = downloader.get_user_recent_posts(user_id, count=amount)

    if not posts:
        console.print(f"[bold yellow][!] No posts or reels found for @{target_username}.[/bold yellow]")
        return

    console.print(f"[bold green]✔ Retrieved {len(posts)} items. Starting download...[/bold green]")
    all_saved: List[Path] = []

    for idx, post in enumerate(posts, 1):
        console.print(f"\n[bold cyan]Processing Post {idx}/{len(posts)}:[/bold cyan]")
        saved = download_media_item(downloader, post)
        all_saved.extend(saved)

    if all_saved:
        render_success_panel(all_saved, target_username)


def set_session_interactive(downloader: InstagramDownloader):
    """Prompts user to enter or update sessionid cookie with instant verification."""
    console.print(
        Panel(
            "[bold cyan]🔑 Instagram Session ID (Cookie) Setup[/bold cyan]\n\n"
            "• Your session token enables downloading from [bold white]Private Profiles[/bold white] you follow\n"
            "  and unlocks [bold white]Instagram Stories[/bold white] with 100% reliability.\n"
            "• To get your cookie: Open Instagram in your browser -> Developer Tools -> Application -> Cookies -> sessionid\n"
            "• Or run: [bold green]python cookie_extractor.py[/bold green] to extract it automatically!",
            box=box.ROUNDED,
            border_style="cyan",
        )
    )

    new_sid = Prompt.ask("[bold yellow]Paste Instagram sessionid (or press Enter to cancel)[/bold yellow]").strip()
    if not new_sid:
        return

    # Clean up "sessionid=" prefix if copied with key
    if "sessionid=" in new_sid:
        m = re.search(r"sessionid=([^;\s]+)", new_sid)
        if m:
            new_sid = m.group(1).strip()

    console.print("[dim][*] Verifying session token with Instagram servers...[/dim]")
    test_dl = InstagramDownloader(new_sid)

    if test_dl.is_authenticated:
        save_session(new_sid)
        downloader.session_id = new_sid
        downloader.authenticate()
        console.print(f"\n[bold green]✔ Session verified! Welcome, @{downloader.username} ({downloader.full_name})![/bold green]\n")
    else:
        console.print("\n[bold red][✗] Session verification failed. Cookie may be expired or invalid.[/bold red]\n")


def view_downloads_folder():
    """Displays the download directory location and list of downloaded user folders."""
    base_dir = get_base_download_dir()
    console.print(f"\n[bold cyan]📁 Base Download Directory:[/bold cyan] [bold white]{base_dir.resolve()}[/bold white]")

    subdirs = [p for p in base_dir.iterdir() if p.is_dir()] if base_dir.exists() else []
    if not subdirs:
        console.print("[dim]No downloaded items found yet.[/dim]\n")
        return

    table = Table(title="[bold green]Downloaded Media by User[/bold green]", box=box.ROUNDED)
    table.add_column("#", style="dim", width=4)
    table.add_column("Username / Folder", style="bold cyan")
    table.add_column("Files", style="bold white", justify="right")
    table.add_column("Total Size", style="magenta", justify="right")

    for idx, s in enumerate(subdirs, 1):
        files = [f for f in s.iterdir() if f.is_file() and not f.name.endswith(".tmp")]
        total_sz = sum(f.stat().st_size for f in files)
        table.add_row(str(idx), s.name, str(len(files)), format_bytes(total_sz))

    console.print(table)
    console.print(f"[dim]⚡ To browse files in Termux: cd '{base_dir}'[/dim]\n")


# =============================================================================
# UI Panels & Cards
# =============================================================================

def render_banner():
    """Renders the top branding banner."""
    raw_logo = r"""
   ___           _          ___  _     
  |_ _|_ _  ___| |_ __ _  |   \| |   
   | || ' \(_-<|  _/ _` | | |) | |__ 
  |___|_||_/__/ \__\__,_| |___/|____|"""

    content = Text()
    content.append(raw_logo.strip() + "\n\n", style="bold cyan")
    content.append("⚡  INSTAGRAM ALL-IN-ONE DOWNLOADER  ⚡\n", style="bold yellow")
    content.append("Reels • Posts • Stories • Carousels (Public & Private)\n", style="bold white")
    content.append("🚀 Crafted by @DominatorStufs • Fast • Reliable • Pure Python", style="bold magenta")

    panel = Panel(
        content,
        box=box.ROUNDED,
        border_style="bright_blue",
        padding=(1, 2),
        subtitle="[bold bright_green]● ONLINE[/bold bright_green]",
        subtitle_align="right",
    )
    console.print(panel)


def render_account_card(downloader: InstagramDownloader):
    """Renders the active account verification card or Guest mode card."""
    if downloader.is_authenticated:
        grid = Table.grid(padding=(0, 2))
        grid.add_column(style="bold white", width=18)
        grid.add_column(style="bold cyan", width=24)
        grid.add_column(style="bold white", width=16)
        grid.add_column(style="bold green", width=24)

        grid.add_row("👤 Logged-in As :", downloader.full_name[:22], "🛡️ Status     :", "Verified & Active")
        grid.add_row("📛 Username     :", f"@{downloader.username}", "🔑 Auth Type   :", "Session Token (Cookie)")
        grid.add_row("🆔 User ID      :", str(downloader.user_id), "🎯 Access Mode :", "Full (Public + Private)")

        panel = Panel(
            grid,
            title="[bold bright_green]✔ ACTIVE INSTAGRAM SESSION[/bold bright_green]",
            border_style="bright_green",
            box=box.ROUNDED,
            padding=(1, 2),
        )
    else:
        grid = Table.grid(padding=(0, 2))
        grid.add_column(style="bold white", width=18)
        grid.add_column(style="bold yellow", width=44)

        grid.add_row("👤 Status       :", "Guest Mode (Not Logged In)")
        grid.add_row("🎯 Access Mode  :", "Public Reels & Posts Only")
        grid.add_row("💡 Quick Tip    :", "Set Session Token (Option 4) to unlock Private Media & Stories!")

        panel = Panel(
            grid,
            title="[bold yellow]🌐 PUBLIC / GUEST MODE[/bold yellow]",
            border_style="yellow",
            box=box.ROUNDED,
            padding=(1, 2),
        )

    console.print(panel)


def render_success_panel(saved_files: List[Path], username: str):
    """Renders a beautiful summary panel after successful download."""
    user_dir = get_user_download_dir(username)
    total_size = sum(f.stat().st_size for f in saved_files if f.exists())

    grid = Table.grid(padding=(0, 2))
    grid.add_column(style="bold white", width=20)
    grid.add_column(style="bold cyan")

    grid.add_row("👤 Account Owner     :", f"@{username}")
    grid.add_row("📦 Files Downloaded  :", f"{len(saved_files)} file(s) ({format_bytes(total_size)})")
    grid.add_row("📁 Saved In Folder   :", str(user_dir.resolve()))

    panel = Panel(
        grid,
        title="[bold bright_green]🎉 DOWNLOAD COMPLETED SUCCESSFULLY 🎉[/bold bright_green]",
        border_style="bright_green",
        box=box.ROUNDED,
        padding=(1, 2),
    )
    console.print("\n")
    console.print(panel)
    console.print("\n")


# =============================================================================
# Main Interactive Loop
# =============================================================================

def main():
    try:
        os.system("clear" if os.name != "nt" else "cls")
        render_banner()

        # Initialize downloader & check session
        saved_sid = load_saved_session()
        downloader = InstagramDownloader(saved_sid)
        render_account_card(downloader)

        while True:
            console.print("[bold cyan]Choose Action:[/bold cyan]")
            console.print("  [bold green][1][/bold green] 🔗 Download by URL (Reel, Post, Carousel, or Story Link)")
            console.print("  [bold green][2][/bold green] 📖 Download User Stories (Enter Username)")
            console.print("  [bold green][3][/bold green] 🎥 Download User Recent Posts/Reels (Enter Username)")
            console.print("  [bold green][4][/bold green] 🔑 Set / Switch Instagram Session Cookie")
            console.print("  [bold green][5][/bold green] 📁 View Download Directory & Saved Files")
            console.print("  [bold green][6][/bold green] 🚪 Exit\n")

            choice = Prompt.ask(
                "[bold yellow]Select option (1, 2, 3, 4, 5, or 6)[/bold yellow]",
                choices=["1", "2", "3", "4", "5", "6"],
                default="1",
            )

            if choice == "1":
                handle_url_download(downloader)
            elif choice == "2":
                handle_story_download_flow(downloader)
            elif choice == "3":
                handle_profile_posts_flow(downloader)
            elif choice == "4":
                set_session_interactive(downloader)
                render_account_card(downloader)
            elif choice == "5":
                view_downloads_folder()
            elif choice == "6":
                console.print("\n[bold cyan]✨ InstaDownloader by [bold magenta]@DominatorStufs[/bold magenta] • Star on GitHub ⭐[/bold cyan]\n")
                sys.exit(0)

            console.print("-" * 60)

    except KeyboardInterrupt:
        console.print("\n\n[bold yellow]Operation cancelled by user. Goodbye![/bold yellow]\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
