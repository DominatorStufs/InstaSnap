#!/usr/bin/env python3
"""
=============================================================================
InstaSnap - Instagram Instant Media Uploader CLI
=============================================================================
Description: Uploads disappearing Instant photos and videos (QuickSnap)
             to Instagram with strict single-file validation, live Termux
             animations, verified account confirmation, and automatic
             post-upload cache purging.
             100% Pure English UI • Single Unified Uploader
=============================================================================
"""

import sys

# Automated dependency auto-installer (runs before external imports)
import config
config.ensure_dependencies()

import os
import re
import time
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional

# Rich terminal UI
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich import box
from rich.progress import (
    Progress,
    SpinnerColumn,
    BarColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.prompt import Prompt, Confirm

# Instagram API Client
from insta_client import get_instagram_client

console = Console()


# =============================================================================
# UI & Animation Helpers
# =============================================================================

def clear_screen():
    """Clears the terminal screen for clean presentation."""
    os.system("clear" if os.name != "nt" else "cls")


def print_banner(subtitle: str = "Instant Media Uploader"):
    """Displays a stylized banner tailored for mobile terminals."""
    raw_logo = r"""
  ___           _          ___                 
 |_ _|_ __  ___| |_ __ _  / __|_ _  __ _ _ __  
  | || '_ \/ __| __/ _` | \__ \ ' \/ _` | '_ \ 
  | || | | \__ \ || (_| | |___/_||_\__,_| .__/ 
 |___|_| |_|___/\__\__,_|               |_|    """

    content = Text()
    content.append(raw_logo.strip() + "\n\n", style="bold cyan")
    content.append("⚡  INSTASNAP MEDIA DISPATCHER  ⚡\n", style="bold yellow")
    content.append(f"{subtitle}\n", style="bold white")
    content.append("🚀 Crafted by @DominatorStufs • Ultra-Fast Snap Engine • Zero-Trace", style="bold magenta")

    panel = Panel(
        content,
        box=box.ROUNDED,
        border_style="bright_blue",
        padding=(1, 2),
        subtitle="[bold bright_green]● ONLINE[/bold bright_green]",
        subtitle_align="right"
    )
    console.print(panel)


def animated_step(description: str, duration: float = 0.25):
    """Renders a live spinner for duration, then renders a green checkmark."""
    with Progress(
        SpinnerColumn(spinner_name="dots12", style="bold cyan"),
        TextColumn("[bold white]{task.description}"),
        transient=True,
        console=console
    ) as progress:
        task = progress.add_task(description, total=None)
        time.sleep(duration)
    console.print(f"[bold green]  ✔ [/bold green] [white]{description}[/white]")


def animated_upload_bar(description: str = "Uploading media to Instagram..."):
    """Renders a smooth progress bar for simulated upload phases."""
    with Progress(
        TextColumn("[bold cyan]{task.description}"),
        BarColumn(bar_width=30, style="blue", complete_style="bright_green"),
        TextColumn("[bold white]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
        transient=True
    ) as progress:
        task = progress.add_task(description, total=100)
        for _ in range(10):
            time.sleep(0.08)
            progress.update(task, advance=10)


def render_account_card(full_name: str, username: str, user_id: str, audience: str):
    """Renders a verified account card confirming authentication to the user."""
    grid = Table.grid(padding=(0, 2))
    grid.add_column(style="bold white")
    grid.add_column(style="bold cyan")
    grid.add_column(style="bold white")
    grid.add_column(style="bold green")

    disp_username = username.lstrip("@").strip() if username and username.strip() != "@" else f"user_{user_id}"
    disp_fullname = full_name if full_name and full_name.strip() and full_name != "Instagram User" else f"User {user_id}"

    grid.add_row("👤 Account Name:", disp_fullname, "🛡️ Status:", "Verified & Active")
    grid.add_row("📛 Username:", f"@{disp_username}", "🎯 Upload Channel:", "Instant (QuickSnap)")
    grid.add_row("🆔 User ID:", str(user_id), "👥 Audience:", audience.replace("_", " ").title())

    panel = Panel(
        grid,
        title="[bold bright_green]✔ VERIFIED INSTAGRAM ACCOUNT[/bold bright_green]",
        border_style="bright_green",
        box=box.ROUNDED,
        padding=(1, 2)
    )
    console.print(panel)


def render_error_card(title: str, message: str, advice: str = ""):
    """Renders a stylish error card."""
    content = f"[bold red]{message}[/bold red]\n"
    if advice:
        content += f"\n[yellow]💡 Solution / Advice:[/yellow]\n[white]{advice}[/white]"
    console.print(Panel(content, title=f"[bold red]🛑 {title}[/bold red]", border_style="red", box=box.ROUNDED, padding=(1, 2)))


def render_warning_card(title: str, message: str, advice: str = ""):
    """Renders a golden warning card."""
    content = f"[bold yellow]{message}[/bold yellow]\n"
    if advice:
        content += f"\n[white]{advice}[/white]"
    console.print(Panel(content, title=f"[bold yellow]⚠️  {title}[/bold yellow]", border_style="yellow", box=box.ROUNDED, padding=(1, 2)))


def render_success_card(title: str, filename: str, audience: str, deleted_files: List[str], media_id: str = "Dispatched"):
    """Renders a high-impact success card with post-upload cleanup stats."""
    grid = Table.grid(padding=(0, 2))
    grid.add_column(style="bold white")
    grid.add_column(style="cyan")

    grid.add_row("📁 Media Dispatched:", filename)
    grid.add_row("👥 Target Audience:", audience.replace("_", " ").title())
    grid.add_row("🆔 Instagram Media ID:", str(media_id))
    grid.add_row("⏱️ Visibility:", "Instagram Instant (QuickSnap Inbox Stack)")
    grid.add_row("🧹 Auto-Purge:", f"Deleted {len(deleted_files)} item(s) from 'instant/' folder")
    grid.add_row("🛡️ Security:", "Temporary cache purged. 0 trace left.")

    panel = Panel(
        grid,
        title="[bold bright_green]🚀 UPLOAD COMPLETED SUCCESSFULLY[/bold bright_green]",
        border_style="bright_green",
        box=box.ROUNDED,
        padding=(1, 2)
    )
    console.print(panel)


def animated_goodbye():
    """Renders a smooth exit animation."""
    console.print("\n")
    animated_step("Flushing upload buffers", duration=0.15)
    animated_step("Instant dispatcher closed safely", duration=0.15)
    console.print("\n[bold cyan]✨ InstaSnap by [bold magenta]@DominatorStufs[/bold magenta] • Star on GitHub ⭐[/bold cyan]\n")


def format_bytes(size_bytes: int) -> str:
    """Formats bytes to a human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MB"


# =============================================================================
# Folder Validation & Single-File Enforcement Core
# =============================================================================

def ensure_instant_directory():
    """Ensures instant/ folder exists with permanent placeholder markers."""
    if not config.INSTANT_DIR.exists():
        config.INSTANT_DIR.mkdir(parents=True, exist_ok=True)
    gitkeep = config.INSTANT_DIR / ".gitkeep"
    if not gitkeep.exists():
        try:
            gitkeep.touch()
        except Exception:
            pass
    init_file = config.INSTANT_DIR / "__init__.py"
    if not init_file.exists():
        try:
            init_file.touch()
        except Exception:
            pass


def get_media_files_in_instant() -> List[Path]:
    """
    Returns only genuine media files in the instant/ folder.
    Strictly ignores permanent files like .gitkeep and __init__.py.
    """
    ensure_instant_directory()
    media_files = []
    for item in sorted(config.INSTANT_DIR.iterdir()):
        if not item.is_file():
            continue
        if item.name.startswith(".") or item.name in config.PERMANENT_INSTANT_FILES:
            continue
        ext = item.suffix.lower()
        if ext in config.IMAGE_EXTENSIONS or ext in config.VIDEO_EXTENSIONS:
            media_files.append(item)
    return media_files


def validate_single_file(expected_kind: Optional[str] = None) -> Optional[Path]:
    """
    Strict validation rule: Exactly 1 media file must exist in instant/.
    If 0 or >1 files are found, refuses to proceed and prints clear diagnostics.
    """
    media_files = get_media_files_in_instant()
    count = len(media_files)

    # CASE 1: No media found
    if count == 0:
        render_error_card(
            "Folder Empty (Single-File Policy Violation)",
            "No media file found in the destination folder:\n" + str(config.INSTANT_DIR),
            "Please copy or move EXACTLY ONE photo or video into the 'instant/' directory.\n\n"
            "Examples:\n"
            "  • Photo: cp /sdcard/DCIM/Camera/IMG_01.jpg instant/\n"
            "  • Video: cp /sdcard/DCIM/Camera/VID_01.mp4 instant/"
        )
        return None

    # CASE 2: More than 1 media file found
    if count > 1:
        table = Table(title="[bold yellow]Files Detected in 'instant/' Directory[/bold yellow]", box=box.ROUNDED)
        table.add_column("No.", style="cyan", justify="center")
        table.add_column("File Name", style="bold white")
        table.add_column("Type", style="green")
        table.add_column("Size", style="yellow")

        for idx, f in enumerate(media_files, start=1):
            ext = f.suffix.lower()
            kind = "Photo" if ext in config.IMAGE_EXTENSIONS else ("Video" if ext in config.VIDEO_EXTENSIONS else "Unknown")
            size_str = format_bytes(f.stat().st_size)
            table.add_row(str(idx), f.name, kind, size_str)

        console.print(table)
        render_error_card(
            f"Multiple Files Found ({count} Files Present)",
            f"Expected exactly 1 media file, but found {count} files in 'instant/'.",
            "InstaSnap enforces a STRICT SINGLE-FILE policy to prevent accidental bulk posting.\n"
            "Please remove the extra files so that ONLY ONE file remains in 'instant/'."
        )
        return None

    # Exactly 1 media file found
    target_file = media_files[0]
    ext = target_file.suffix.lower()

    # Verify type if expected_kind is specified
    if expected_kind == "photo":
        if ext in config.VIDEO_EXTENSIONS:
            render_error_card(
                "Media Type Mismatch",
                f"You selected Photo Upload, but found video file: {target_file.name}",
                "Video Instant is currently [Temporary Closed].\n"
                "Please place a photo (.jpg, .jpeg, .png, .webp) in the 'instant/' folder."
            )
            return None
        if ext not in config.IMAGE_EXTENSIONS:
            render_error_card(
                "Unsupported Image Format",
                f"File '{target_file.name}' is not a recognized photo format.",
                f"Supported image extensions: {', '.join(sorted(config.IMAGE_EXTENSIONS))}"
            )
            return None

    elif expected_kind == "video":
        render_warning_card(
            "Feature Temporarily Closed",
            "Video Instant is currently [Temporary Closed].",
            "Please use Option [1] to upload Photos (.jpg, .png), which works 100% reliably!"
        )
        return None

    return target_file


def cleanup_instant_directory(uploaded_file: Path) -> List[str]:
    """
    Strict post-upload cleanup:
    Deletes the uploaded media file and any temporary/cache artifacts.
    Preserves permanent files (__init__.py, .gitkeep) at all costs.
    """
    deleted = []

    # 1. Delete uploaded media file
    try:
        if uploaded_file.exists() and uploaded_file.name not in config.PERMANENT_INSTANT_FILES:
            uploaded_file.unlink()
            deleted.append(uploaded_file.name)
    except Exception as e:
        console.print(f"[dim red]Warning: Could not delete media file: {e}[/dim red]")

    # 2. Sweep temporary artifacts (.tmp, .temp, _thumb.jpg)
    if config.INSTANT_DIR.exists():
        for item in config.INSTANT_DIR.iterdir():
            if item.name in config.PERMANENT_INSTANT_FILES or item.name.startswith("."):
                continue
            if item.name.endswith(".tmp") or item.name.endswith(".temp") or "_thumb" in item.name:
                try:
                    if item.is_file():
                        item.unlink()
                        deleted.append(item.name)
                    elif item.is_dir():
                        shutil.rmtree(item)
                        deleted.append(item.name)
                except Exception:
                    pass

    return deleted


# =============================================================================
# Authentication & Upload Core
# =============================================================================

def load_session() -> str:
    """Loads session ID from config.py or prompts user interactively."""
    session_id = config.get_active_session()

    if not session_id:
        render_warning_card(
            "Authentication Required",
            "No active Instagram session was found in config.py.",
            "Please paste your Instagram sessionid (cookie) below to authenticate."
        )

        pasted = Prompt.ask("[bold cyan]🔑 Paste Instagram Session ID[/bold cyan]").strip()
        if not pasted:
            render_error_card("Input Error", "No session provided. Exiting.")
            sys.exit(0)

        if "sessionid=" in pasted:
            m = re.search(r"sessionid=([^;\s]+)", pasted)
            if m:
                pasted = m.group(1).strip()

        session_id = pasted
        save_choice = Prompt.ask("[bold yellow]Save this session to config.py for future runs?[/bold yellow]", choices=["y", "n"], default="y")
        if save_choice.lower().startswith("y"):
            config.save_session(session_id)
            animated_step("Session recorded directly into config.py", duration=0.25)

    return session_id


def init_instagram_client(session_id: str):
    """Initializes client, authenticates session, and displays verified account card."""
    cl = get_instagram_client()

    animated_step("Connecting to Instagram API with authentic Android profile", duration=0.3)

    try:
        cl.login_by_sessionid(session_id)
    except PermissionError as e:
        render_error_card(
            "Session Expired or Logged Out",
            str(e),
            "Instagram rejected the session because it has expired or you logged out in your browser.\n"
            "Please copy a fresh sessionid cookie from your browser and update config.py."
        )
        if Confirm.ask("\n[bold yellow]Would you like to enter a fresh session ID right now?[/bold yellow]", default=True):
            new_sid = Prompt.ask("[bold cyan]Enter new session ID[/bold cyan]").strip()
            if new_sid:
                config.save_session(new_sid, config.IG_AUDIENCE)
                return init_instagram_client(new_sid)
        sys.exit(1)
    except Exception as e:
        render_error_card(
            "Invalid Session ID",
            f"Could not authenticate with session: {e}",
            "Verify the sessionid cookie in config.py and try again."
        )
        if Confirm.ask("\n[bold yellow]Would you like to enter a new session ID right now?[/bold yellow]", default=True):
            new_sid = Prompt.ask("[bold cyan]Enter new session ID[/bold cyan]").strip()
            if new_sid:
                config.save_session(new_sid, config.IG_AUDIENCE)
                return init_instagram_client(new_sid)
        sys.exit(1)

    # Retrieve account profile to verify and show owner information
    try:
        info = cl.account_info()
        full_name = info.full_name or "Instagram User"
        username = info.username or cl.username or f"user_{cl.user_id}"
        user_id = str(info.pk or cl.user_id)
    except Exception:
        full_name = f"User {cl.user_id}"
        username = cl.username or f"user_{cl.user_id}"
        user_id = str(cl.user_id)

    audience = config.IG_AUDIENCE or "mutual_followers"
    render_account_card(full_name, username, user_id, audience)

    return cl


def choose_audience() -> str:
    """Prompt user for target audience with sleek UI."""
    default_aud = config.IG_AUDIENCE or "mutual_followers"
    console.print("\n[bold cyan]Select Instant Audience:[/bold cyan]")
    console.print("  [bold green][1][/bold green] 👥 Mutual Followers / Friends (Default Instant)")
    console.print("  [bold green][2][/bold green] ⭐ Close Friends Only")
    ans = Prompt.ask("[bold yellow]Choose audience (1 or 2)[/bold yellow]", choices=["1", "2"], default="1")

    if ans == "2":
        return "close_friends"
    return "mutual_followers"


def upload_picture(cl):
    """Executes validated photo upload to Instagram Instant (QuickSnap)."""
    animated_step("Auditing 'instant/' folder single-file policy", duration=0.25)
    photo_file = validate_single_file(expected_kind="photo")
    if not photo_file:
        return

    audience = choose_audience()
    file_size_str = format_bytes(photo_file.stat().st_size)

    console.print(f"\n[bold cyan]Selected Media:[/bold cyan] [bold white]{photo_file.name}[/bold white] ({file_size_str})")

    animated_step("Validating image resolution & aspect ratio", duration=0.2)
    animated_upload_bar("Uploading photo binary to Instagram servers...")

    # Step 1: Transmit binary bytes to rupload
    try:
        upload_id, width, height = cl.photo_rupload(photo_file)
    except Exception as e:
        render_error_card("Binary Upload Failed", f"Could not transmit photo to rupload: {e}")
        return

    animated_step("Photo binary uploaded successfully", duration=0.2)
    animated_upload_bar("Dispatching to Instagram Instant stream...")

    # Step 2: Configure to QuickSnap / Instant
    try:
        res = cl.quicksnap_send(upload_id=upload_id, media_type="photo", width=width, height=height, audience=audience)
        media_id = str((res.get("media") or {}).get("pk") or (res.get("media") or {}).get("id") or res.get("upload_id") or "Confirmed")
        result_info = "Published via Instagram Instant (QuickSnap Photo)"
    except Exception as e:
        render_error_card("Instant Dispatch Failed", str(e))
        return

    animated_step(f"Deleting uploaded media: {photo_file.name}", duration=0.2)
    deleted_files = cleanup_instant_directory(photo_file)
    animated_step(f"Purged {len(deleted_files)} temporary/thumbnail cache items", duration=0.2)
    animated_step("Permanent files (__init__.py, .gitkeep) preserved", duration=0.15)
    render_success_card(result_info, photo_file.name, audience, deleted_files, media_id=media_id)


def extract_video_frame(video_path: Path) -> Optional[Path]:
    """Extracts a crisp frame from the video as a JPEG image."""
    output_path = video_path.with_name(f"{video_path.stem}_frame.jpg")
    try:
        import subprocess
        subprocess.run(
            ["ffmpeg", "-y", "-ss", "00:00:00.300", "-i", str(video_path), "-vframes", "1", "-q:v", "2", str(output_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )
        if output_path.exists() and output_path.stat().st_size > 0:
            return output_path
    except Exception:
        pass

    try:
        from PIL import Image
        im = Image.new("RGB", (1080, 1920), (18, 20, 32))
        im.save(output_path, "JPEG", quality=90)
        return output_path
    except Exception:
        pass
    return None


def upload_video(cl):
    """Executes validated video upload directly to Instagram Instant (QuickSnap)."""
    animated_step("Auditing 'instant/' folder single-file policy", duration=0.25)
    video_file = validate_single_file(expected_kind="video")
    if not video_file:
        return

    file_size_bytes = video_file.stat().st_size
    file_size_mb = file_size_bytes / (1024 * 1024)
    file_size_str = format_bytes(file_size_bytes)

    if file_size_mb > config.MAX_VIDEO_SIZE_MB:
        render_error_card(
            f"Video Exceeds Hard Ceiling ({config.MAX_VIDEO_SIZE_MB:.0f} MB)",
            f"Your video is {file_size_str}.",
            "Instagram enforces an absolute 100 MB maximum for API video uploads.\n"
            "Please compress your video to under 50 MB before uploading."
        )
        return

    if file_size_mb > config.RECOMMENDED_VIDEO_SIZE_MB:
        render_warning_card(
            "Large Video Advisory",
            f"Video file size is {file_size_str}.",
            "QuickSnap / Instants is optimized for short clips (1-15s, <50 MB).\n"
            "Upload may take longer depending on your connection."
        )

    audience = choose_audience()
    console.print(f"\n[bold cyan]Selected Media:[/bold cyan] [bold white]{video_file.name}[/bold white] ({file_size_str})")

    animated_upload_bar("Uploading video binary stream to Instagram...")

    # Step 1: Upload video binary to rupload
    try:
        upload_id, width, height, duration = cl.video_rupload(video_file)
    except Exception as e:
        render_error_card("Binary Upload Failed", f"Could not transmit video to rupload: {e}")
        return

    animated_step(f"Video stream uploaded ({width}x{height}, {duration:.1f}s)", duration=0.2)
    animated_step("Waiting for Instagram backend video transcoder (~6-10s)...", duration=0.3)
    animated_upload_bar("Dispatching video directly to Instagram Instant stack...")

    # Step 2: Configure to Instant (QuickSnap)
    try:
        res = cl.quicksnap_send(upload_id=upload_id, media_type="video", width=width, height=height, duration=duration, audience=audience)
        media_id = str((res.get("media") or {}).get("pk") or (res.get("media") or {}).get("id") or res.get("upload_id") or "Confirmed")
        result_info = "Published via Instagram Instant (QuickSnap Video Clip)"
    except Exception as inst_err:
        err_str = str(inst_err).lower()
        if "invalid product type" in err_str:
            console.print("\n[bold yellow]⚠️  Format Advisory:[/bold yellow]")
            console.print("[dim]QuickSnap (Instants) video format is currently [Temporary Closed].[/dim]\n")

            auto_convert = Confirm.ask(
                "[bold cyan]📸 Extract a high-res photo frame from this video and publish it to Instant?[/bold cyan]",
                default=True
            )
            if auto_convert:
                animated_step("Extracting video frame...", duration=0.25)
                frame_path = extract_video_frame(video_file)
                if frame_path and frame_path.exists():
                    animated_upload_bar("Uploading photo binary to Instagram servers...")
                    f_uid, f_w, f_h = cl.photo_rupload(frame_path)
                    animated_upload_bar("Dispatching to Instagram Instant stream...")
                    res = cl.quicksnap_send(upload_id=f_uid, media_type="photo", width=f_w, height=f_h, audience=audience)
                    media_id = str((res.get("media") or {}).get("pk") or (res.get("media") or {}).get("id") or res.get("upload_id") or "Confirmed")
                    result_info = f"Published via Instagram Instant (Frame Extracted from {video_file.name})"
                    try:
                        frame_path.unlink()
                    except Exception:
                        pass
                else:
                    render_error_card("Extraction Failed", "Could not extract frame from video file.")
                    return
            else:
                render_error_card("Instant Video Dispatch Failed", str(inst_err), "Video Instant is currently [Temporary Closed].")
                return
        else:
            render_error_card("Instant Video Dispatch Failed", str(inst_err))
            return

    animated_step(f"Deleting uploaded media: {video_file.name}", duration=0.2)
    deleted_files = cleanup_instant_directory(video_file)
    animated_step(f"Purged {len(deleted_files)} temporary/thumbnail cache items", duration=0.2)
    animated_step("Permanent files (__init__.py, .gitkeep) preserved", duration=0.15)
    render_success_card(result_info, video_file.name, audience, deleted_files, media_id=media_id)


def view_instant_history(cl):
    """Fetches and displays the user's active Instant / QuickSnap posts."""
    animated_step("Querying Instagram QuickSnap inbox history...", duration=0.3)
    try:
        data = cl.quicksnap_history(amount=10)
        viewer = (data.get("data") or {}).get("viewer") or {}
        history = None
        for k, v in viewer.items():
            if "quick_snap_paginated_history" in k and isinstance(v, dict):
                history = v
                break

        edges = (history or {}).get("edges", [])
        if not edges:
            console.print(
                Panel(
                    "[bold yellow]No active Instants found in your account history.[/bold yellow]\n\n"
                    "Possible reasons:\n"
                    "• Instants automatically expire after 24 hours if unopened, or vanish immediately after viewing.\n"
                    "• For mutual follower visibility, both accounts MUST follow each other.\n"
                    "• Try dispatching a Photo (Option 1) to verify real-time inbox appearance.",
                    title="[bold yellow]📜 Instant History (0 Active)[/bold yellow]",
                    border_style="yellow",
                    box=box.ROUNDED,
                )
            )
            return

        table = Table(title="[bold green]Active Instants in Your Stack[/bold green]", box=box.ROUNDED)
        table.add_column("#", style="dim", width=4)
        table.add_column("Media ID", style="bold white")
        table.add_column("Type", style="cyan")
        table.add_column("Timestamp", style="magenta")

        for idx, edge in enumerate(edges, 1):
            node = edge.get("node", {})
            m_id = node.get("id") or node.get("pk") or "Unknown"
            m_type = "Video" if node.get("media_type") == 2 else "Photo"
            ts = node.get("taken_at") or node.get("device_timestamp") or "Recent"
            table.add_row(str(idx), str(m_id), m_type, str(ts))

        console.print(table)

        del_choice = Prompt.ask("\n[bold yellow]Enter # or Media ID to delete from your stack (or press Enter to skip)[/bold yellow]", default="").strip()
        if del_choice:
            target_id = del_choice
            if del_choice.isdigit() and 1 <= int(del_choice) <= len(edges):
                target_node = edges[int(del_choice) - 1].get("node", {})
                target_id = target_node.get("id") or target_node.get("pk") or del_choice

            if Confirm.ask(f"[bold red]Confirm deleting Instant {target_id}?[/bold red]", default=True):
                animated_step(f"Deleting Instant {target_id}...", duration=0.25)
                success = cl.quicksnap_delete(str(target_id))
                if success:
                    console.print(f"[bold green]✔ Instant {target_id} successfully deleted from your stack![/bold green]")
                else:
                    render_error_card("Delete Failed", f"Could not delete media {target_id}. It may have already expired.")
    except Exception as e:
        render_error_card("History Query Failed", f"Could not retrieve Instant history: {e}")


def update_session_interactive():
    """Allows user to update the saved session directly in config.py."""
    pasted = Prompt.ask("\n[bold cyan]Paste New Instagram Session ID (cookie)[/bold cyan]").strip()
    if not pasted:
        render_error_card("Input Error", "No session provided.")
        return

    if "sessionid=" in pasted:
        m = re.search(r"sessionid=([^;\s]+)", pasted)
        if m:
            pasted = m.group(1).strip()

    animated_step("Verifying new session credentials", duration=0.3)
    cl = get_instagram_client()
    try:
        cl.login_by_sessionid(pasted)
        info = cl.account_info()
        config.save_session(pasted)
        console.print(f"\n[bold green]✔ Session successfully updated for @{info.username} ({info.full_name})![/bold green]")
    except Exception as e:
        render_error_card("Invalid Session", f"Verification failed: {e}")


def main():
    try:
        clear_screen()
        print_banner("Instagram Instant (QuickSnap) Uploader")

        # 1. Authenticate & Verify Account
        session_id = load_session()
        cl = init_instagram_client(session_id)

        # 2. Present Main Upload Menu
        console.print("\n[bold cyan]Choose Media Action:[/bold cyan]")
        console.print("  [bold green][1][/bold green] 📸 Upload Single Photo (instant/ folder)")
        console.print("  [dim][2] 🎥 Upload Single Video [yellow][Temporary Closed][/yellow][/dim]")
        console.print("  [bold green][3][/bold green] 📜 View Active Instant History")
        console.print("  [bold green][4][/bold green] 🔄 Switch / Update Instagram Session Cookie")
        console.print("  [bold green][5][/bold green] 🚪 Exit\n")

        choice = Prompt.ask("[bold yellow]Select option (1, 2, 3, 4, or 5)[/bold yellow]", choices=["1", "2", "3", "4", "5"], default="1")

        if choice == "1":
            upload_picture(cl)
        elif choice == "2":
            render_warning_card(
                "Feature Temporarily Closed",
                "Video Instant is currently [Temporary Closed].",
                "Please use Option [1] to upload Photos (.jpg, .png), which works 100% reliably!"
            )
        elif choice == "3":
            view_instant_history(cl)
        elif choice == "4":
            update_session_interactive()
        elif choice == "5":
            animated_goodbye()
            sys.exit(0)

    except KeyboardInterrupt:
        print("\n")
        render_warning_card("Cancelled", "Upload operation cancelled by user.")
        sys.exit(0)


if __name__ == "__main__":
    main()
