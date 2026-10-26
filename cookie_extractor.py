#!/usr/bin/env python3
"""
=============================================================================
InstaSnap - Standalone Cookie Extractor (Pure Python Edition)
=============================================================================
Purpose: Logs into Instagram with Username & Password, handles 2FA / SMS
         checkpoints, extracts the sessionid cookie, and updates config.py.
=============================================================================
"""

import sys
import getpass
from pathlib import Path

import config
config.ensure_dependencies()

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt
from rich import box

from insta_client import get_instagram_client, CheckpointRequiredError, TwoFactorRequiredError

console = Console()


def print_banner():
    banner = r"""[bold cyan]
  ___           _          ___                               
   |_ _|_ __  ___| |_ __ _  / __|_ _  __ _ _ __                
    | || '_ \/ __| __/ _` | \__ \ ' \/ _` | '_ \               
    | || | | \__ \ || (_| | |___/_||_\__,_| .__/               
   |___|_| |_|___/\__\__,_|               |_|                  
[/bold cyan]
[bold bright_yellow]  🍪  INSTASNAP COOKIE EXTRACTOR (Python Edition)  🍪[/bold bright_yellow]
[bold magenta]  🚀 Crafted by @DominatorStufs • Fast Session Extraction Engine[/bold magenta]
"""
    console.print(Panel(banner, border_style="cyan", box=box.ROUNDED))


def main():
    print_banner()

    console.print("[bold yellow][!] Note:[/bold yellow] [dim]Your credentials are sent directly to Instagram's official API to generate an active session. Nothing is stored remotely.[/dim]\n")

    username = Prompt.ask("[bold cyan]Enter Instagram Username[/bold cyan]").strip()
    if not username:
        console.print("[bold red][✗] Username cannot be empty.[/bold red]")
        sys.exit(1)

    password = getpass.getpass("Enter Instagram Password: ").strip()
    if not password:
        console.print("[bold red][✗] Password cannot be empty.[/bold red]")
        sys.exit(1)

    cl = get_instagram_client()

    console.print("\n[bold cyan][*] Submitting credentials to Instagram API...[/bold cyan]")

    logged_in = False
    try:
        logged_in = cl.login(username, password)
    except TwoFactorRequiredError as tf:
        console.print("\n[bold yellow][!] Two-Factor Authentication (2FA) is enabled on this account.[/bold yellow]")
        code = Prompt.ask("[bold cyan]Enter 6-digit 2FA security code[/bold cyan]").strip()
        try:
            logged_in = cl.login(username, password, verification_code=code)
        except Exception as e:
            console.print(f"\n[bold red][✗] 2FA verification failed: {e}[/bold red]")
            sys.exit(1)
    except CheckpointRequiredError as cp:
        console.print(f"\n[bold yellow][!] Security Checkpoint triggered: {cp.checkpoint_url or 'Review required'}[/bold yellow]")
        console.print("[dim]Open Instagram on your phone/browser and tap 'This Was Me', then retry.[/dim]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[bold red][✗] Login failed: {e}[/bold red]")
        sys.exit(1)

    if not logged_in or not cl.sessionid:
        console.print("\n[bold red][✗] Failed to obtain session ID cookie from Instagram.[/bold red]")
        sys.exit(1)

    session_id = cl.sessionid
    user_id = str(cl.user_id)

    # Fetch profile
    full_name = "Instagram User"
    resolved_username = username
    try:
        info = cl.account_info()
        full_name = info.full_name or full_name
        resolved_username = info.username or resolved_username
    except Exception:
        pass

    # Success Card
    grid = Table.grid(padding=(0, 2))
    grid.add_column(style="bold white")
    grid.add_column(style="bold cyan")
    grid.add_row("👤 Account Name :", full_name)
    grid.add_row("📛 Username     :", f"@{resolved_username}")
    grid.add_row("🆔 User ID      :", user_id)

    panel = Panel(
        grid,
        title="[bold bright_green]🎉 INSTAGRAM SESSION COOKIE EXTRACTED! 🎉[/bold bright_green]",
        border_style="bright_green",
        box=box.ROUNDED,
        padding=(1, 2)
    )
    console.print(panel)

    console.print("\n[bold yellow]🔑 YOUR EXTRACTED SESSION ID:[/bold yellow]")
    console.print(Panel(f"[bold white]{session_id}[/bold white]", border_style="yellow", box=box.ROUNDED))

    # Automatically save to config.py
    saved = config.save_session(session_id, config.IG_AUDIENCE)
    if saved:
        console.print("[bold green][✔] config.py has been automatically updated with your new session![/bold green]")
        console.print("[bold green][✔] You can now directly upload media by running:[/bold green] [bold cyan]python instant_uploader.py[/bold cyan]\n")
    else:
        console.print("[bold yellow][!] Could not auto-update config.py. Please paste the session ID above into config.py manually.[/bold yellow]\n")


if __name__ == "__main__":
    main()
