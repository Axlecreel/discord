from http.client import HTTPSConnection 
from sys import stderr 
from json import dumps, loads
from time import sleep 
import json
import threading
from datetime import datetime
import random
import os
import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table

app = typer.Typer()
console = Console()

BANNER = """
 █████╗ ██╗   ██╗████████╗ ██████╗     ███╗   ███╗███████╗ ██████╗ 
██╔══██╗██║   ██║╚══██╔══╝██╔═══██╗    ████╗ ████║██╔════╝██╔════╝ 
███████║██║   ██║   ██║   ██║   ██║    ██╔████╔██║███████╗██║  ███╗
██╔══██║██║   ██║   ██║   ██║   ██║    ██║╚██╔╝██║╚════██║██║   ██║
██║  ██║╚██████╔╝   ██║   ╚██████╔╝    ██║ ╚═╝ ██║███████║╚██████╔╝
╚═╝  ╚═╝ ╚═════╝    ╚═╝    ╚═════╝     ╚═╝     ╚═╝╚══════╝ ╚═════╝ 
"""

shutdown_event = threading.Event()

def save_config(config_data):
    with open('./config.json', 'w') as f:
        json.dump(config_data, f, indent=4)

def load_config():
    if not os.path.exists('./config.json'): return None
    with open('./config.json', 'r') as f: return json.load(f)

def get_multiline_input(prompt_text):
    console.print(f"[yellow]{prompt_text}[/yellow]")
    console.print("[dim](Paste your message. When finished, type 'END' on a new line and press Enter)[/dim]")
    lines = []
    while True:
        line = input()
        if line.strip().upper() == "END": break
        lines.append(line)
    return "\n".join(lines)

def get_connection(): return HTTPSConnection("discordapp.com", 443) 
 
def send_message(conn, cid, data, token): 
    try: 
        conn.request("POST", f"/api/v9/channels/{cid}/messages", data, {"content-type": "application/json", "authorization": token}) 
        resp = conn.getresponse() 
        body = resp.read().decode()
        ts = datetime.now().strftime('%H:%M:%S')
        
        if 199 < resp.status < 300: 
            console.print(f"[bold cyan][{cid}][/bold cyan] Sent at [white]{ts}[/white]")
            return 0
        elif resp.status == 429:
            retry_data = loads(body)
            wait_time = retry_data.get('retry_after', 5)
            
            # Formatting logic: Convert seconds to M and S
            if wait_time >= 60:
                mins = int(wait_time // 60)
                secs = int(wait_time % 60)
                time_str = f"{mins}m {secs}s"
            else:
                time_str = f"{int(wait_time)}s"
                
            console.print(f"[bold red][RATE LIMITED][/bold red] {cid} must wait [bold yellow]{time_str}[/bold yellow]")
            return wait_time
        else: 
            console.print(f"[bold red][{cid}][/bold red] Error {resp.status}")
            return 0
    except Exception as e:
        return 0

def message_loop(msg, mini, maxi, cid, token):
    while not shutdown_event.is_set():
        wait_time = send_message(get_connection(), cid, dumps({"content": msg, "tts": "false"}), token)
        
        # If rate limited, sleep for the duration Discord mandated
        if wait_time > 0:
            sleep(wait_time)
            
        if shutdown_event.wait(timeout=random.uniform(mini, maxi)): break

def token_manager():
    config = load_config() or {"Global_Token": "", "Config": []}
    new_token = Prompt.ask("Enter your Discord Token", default=config.get("Global_Token", ""))
    config["Global_Token"] = new_token
    save_config(config)
    console.print("[green]Token saved![/green]")

def setup_wizard():
    config = load_config() or {"Global_Token": "", "Config": []}
    if not config["Global_Token"]:
        token_manager()
        config = load_config()

    name = Prompt.ask("Enter a nickname for this channel (e.g. Vanguards1)")
    cid = Prompt.ask("Enter Channel ID")
    msg = get_multiline_input("Enter the message to send")
    mini = float(Prompt.ask("Min delay (seconds)", default="60"))
    maxi = float(Prompt.ask("Max delay (seconds)", default="120"))

    new_entry = {
        "name": name,
        "channel_id": cid,
        "messages": [{"content": msg, "min_interval": mini, "max_interval": maxi}]
    }
    config["Config"].append(new_entry)
    save_config(config)
    console.print(f"[green]Added {name} successfully![/green]")

def edit_message_wizard():
    config = load_config()
    if not config or not config["Config"]: return
    
    table = Table(title="Select Channel to Edit Message")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="yellow")
    for i, entry in enumerate(config["Config"]):
        table.add_row(str(i+1), entry["name"])
    console.print(table)
    
    idx = int(Prompt.ask("Select ID")) - 1
    new_msg = get_multiline_input(f"Enter new message for {config['Config'][idx]['name']}")
    config["Config"][idx]["messages"][0]["content"] = new_msg
    save_config(config)
    console.print("[green]Message updated![/green]")

def interval_wizard():
    config = load_config()
    if not config or not config["Config"]: return
    
    console.print("\n1. Edit Single Channel\n2. Edit ALL Channels")
    mode = Prompt.ask("Choice", choices=["1", "2"])
    
    mini = float(Prompt.ask("New Min delay (seconds)"))
    maxi = float(Prompt.ask("New Max delay (seconds)"))

    if mode == "1":
        table = Table(title="Select Channel")
        for i, entry in enumerate(config["Config"]): table.add_row(str(i+1), entry["name"])
        console.print(table)
        idx = int(Prompt.ask("Select ID")) - 1
        config["Config"][idx]["messages"][0]["min_interval"] = mini
        config["Config"][idx]["messages"][0]["max_interval"] = maxi
    else:
        for entry in config["Config"]:
            entry["messages"][0]["min_interval"] = mini
            entry["messages"][0]["max_interval"] = maxi
            
    save_config(config)
    console.print("[green]Intervals updated![/green]")

def delete_channel_wizard():
    config = load_config()
    if not config or not config["Config"]: return
    
    table = Table(title="Delete Channels")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="red")
    for i, entry in enumerate(config["Config"]):
        table.add_row(str(i+1), entry["name"])
    console.print(table)
    
    idx_str = Prompt.ask("Enter ID to delete (or 'all' to wipe everything)")
    
    if idx_str.lower() == "all":
        if Confirm.ask("[bold red]Are you sure you want to delete ALL channels?[/bold red]"):
            config["Config"] = []
            console.print("[red]All channels deleted.[/red]")
    else:
        idx = int(idx_str) - 1
        deleted_name = config["Config"].pop(idx)["name"]
        console.print(f"[red]Deleted {deleted_name}[/red]")
    
    save_config(config)

def start_bot():
    config_data = load_config()
    if not config_data or not config_data.get("Global_Token"): 
        console.print("[red]No token found. Please add a token first.[/red]")
        return
    tok = config_data.get('Global_Token')
    shutdown_event.clear()
    threads = []
    for entry in config_data.get('Config', []):
        cid = entry.get("channel_id")
        nick = entry.get("name", "Unnamed")
        for m in entry['messages']:
            console.print(f"[green]Starting:[/green] [bold yellow]{nick}[/bold yellow]")
            t = threading.Thread(target=message_loop, args=(m['content'], m['min_interval'], m['max_interval'], cid, tok), daemon=True)
            threads.append(t); t.start()
    
    console.print(Panel.fit("[bold green]Botting Started![/bold green]\n[bold white]Press Ctrl + C to stop[/bold white]", border_style="green"))
    try:
        while not shutdown_event.is_set(): sleep(1)
    except KeyboardInterrupt: shutdown_event.set()

@app.command()
def main():
    while True:
        console.print(Panel.fit(BANNER, title="Discord Automator", border_style="blue"))
        console.print("\n1. [bold green]Start Bot[/bold green]\n2. [bold cyan]Add New Channels[/bold cyan]\n3. [bold magenta]Update Global Token[/bold magenta]\n4. [bold yellow]Edit Messages[/bold yellow]\n5. [bold blue]Change Intervals[/bold blue]\n6. [bold red]Delete Channels[/bold red]\n7. [bold white]Exit[/bold white]")
        choice = Prompt.ask("Action", choices=["1", "2", "3", "4", "5", "6", "7"])
        if choice == "1": start_bot()
        elif choice == "2": setup_wizard()
        elif choice == "3": token_manager()
        elif choice == "4": edit_message_wizard()
        elif choice == "5": interval_wizard()
        elif choice == "6": delete_channel_wizard()
        elif choice == "7": break

if __name__ == '__main__': app()
