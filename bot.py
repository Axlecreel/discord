import requests # You will need to: pip install requests
from http.client import HTTPSConnection 
from sys import stderr, executable, argv
from json import dumps, loads
from time import sleep 
import json
import threading
from datetime import datetime
import random
import os
import subprocess
import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

app = typer.Typer()
console = Console()

# --- CONFIGURATION ---
CURRENT_VERSION = "1.0"
# Replace 'YOUR_USER' and 'YOUR_REPO' with your actual GitHub details
GITHUB_RAW_URL = "https://https://raw.githubusercontent.com/Axlecreel/discord-selfbot/refs/heads/main/bot.py"
VERSION_URL = "https://raw.githubusercontent.com/Axlecreel/discord-selfbot/refs/heads/main/version.txt"

def check_for_updates():
    try:
        response = requests.get(VERSION_URL, timeout=5)
        latest_version = response.text.strip()
        
        if latest_version != CURRENT_VERSION:
            console.print(Panel(f"[bold yellow]Update Available![/bold yellow]\nLocal: {CURRENT_VERSION} | GitHub: {latest_version}", border_style="yellow"))
            if Confirm.ask("Do you want to automatically update to the latest version?"):
                update_script()
    except Exception:
        console.print("[dim]Could not check for updates (Offline or Repo private).[/dim]")

def update_script():
    try:
        console.print("[cyan]Downloading latest version...[/cyan]")
        response = requests.get(GITHUB_RAW_URL)
        if response.status_code == 200:
            with open(__file__, "w") as f:
                f.write(response.text)
            console.print("[bold green]Update successful! Restarting...[/bold green]")
            # This line re-runs the script automatically after updating
            os.execv(executable, ['python3'] + argv)
        else:
            console.print("[bold red]Failed to download update.[/bold red]")
    except Exception as e:
        console.print(f"[bold red]Update error: {e}[/bold red]")

# ... (Insert the rest of your bot.py code here: send_message, start_bot, etc.)

@app.command()
def main():
    # Run update check on launch
    check_for_updates()
    
    while True:
        # (Your existing Menu code)
        ...
