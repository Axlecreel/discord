from http.client import HTTPSConnection 
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
from rich.prompt import Prompt
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

def display_channel_table(config):
    table = Table(title="Current Channels & Settings")
    table.add_column("ID", justify="center", style="cyan")
    table.add_column("Nickname", style="green")
    table.add_column("Channel ID", style="magenta")
    table.add_column("Interval (Min/Max)", style="yellow")
    table.add_column("Message Preview", style="white", no_wrap=True)

    for i, entry in enumerate(config["Config"]):
        m = entry["messages"][0]
        table.add_row(
            str(i+1), 
            entry["name"], 
            entry["channel_id"], 
            f"{m['min_interval']}s - {m['max_interval']}s", 
            m['content'][:30] + "..." if len(m['content']) > 30 else m['content']
        )
    console.print(table)

def get_multiline_input(prompt_text):
    console.print(f"[yellow]{prompt_text}[/yellow]")
    console.print("[dim](Type 'END' on a new line and press Enter to finish)[/dim]")
    lines = []
    while True:
        line = input()
        if line.strip().upper() == "END": break
        lines.append(line)
    return "\n".join(lines)
 
def send_message(conn, cid, data, token): 
    try: 
        conn.request("POST", f"/api/v9/channels/{cid}/messages", data, {"content-type": "application/json", "authorization": token}) 
        resp = conn.getresponse() 
        body = resp.read().decode()
        if 199 < resp.status < 300: 
            console.print(f"[bold cyan][{cid}][/bold cyan] Sent at [white]{datetime.now().strftime('%H:%M:%S')}[/white]")
            return 0
        elif resp.status == 429:
            wait_time = loads(body).get('retry_after', 5)
            mins, secs = int(wait_time // 60), int(wait_time % 60)
            time_str = f"{mins}m {secs}s" if wait_time >= 60 else f"{int(wait_time)}s"
            console.print(f"[bold red][RATE LIMITED][/bold red] {cid} wait [bold yellow]{time_str}[/bold yellow]")
            return wait_time
        return 0
    except Exception: return 0

def message_loop(msg, mini, maxi, cid, token):
    while not shutdown_event.is_set():
        send_message(HTTPSConnection("discordapp.com", 443), cid, dumps({"content": msg}), token)
        if shutdown_event.wait(timeout=random.uniform(mini, maxi)): break

def start_bot():
    config = load_config()
    if not config or not config.get("Global_Token"): return
    tok = config['Global_Token']
    shutdown_event.clear()
    for entry in config.get('Config', []):
        cid = entry["channel_id"]
        for m in entry['messages']:
            threading.Thread(target=message_loop, args=(m['content'], m['min_interval'], m['max_interval'], cid, tok), daemon=True).start()
    console.print(Panel.fit("[bold green]Botting Started![/bold green]", border_style="green"))
    try:
        while not shutdown_event.is_set(): sleep(1)
    except KeyboardInterrupt: shutdown_event.set()

def setup_wizard():
    config = load_config() or {"Global_Token": "", "Config": []}
    config["Config"].append({
        "name": Prompt.ask("Nickname"),
        "channel_id": Prompt.ask("Channel ID"),
        "messages": [{"content": get_multiline_input("Message"), "min_interval": float(Prompt.ask("Min delay")), "max_interval": float(Prompt.ask("Max delay"))}]
    })
    save_config(config)

def edit_message_wizard():
    config = load_config()
    if not config or not config["Config"]: return
    display_channel_table(config)
    choice = Prompt.ask("Select ID, 'all', or 'c' to cancel")
    if choice.lower() == 'c': return
    new_msg = get_multiline_input("Enter new message")
    if choice.lower() == 'all':
        for entry in config["Config"]: entry["messages"][0]["content"] = new_msg
    else:
        try: config["Config"][int(choice)-1]["messages"][0]["content"] = new_msg
        except: return
    save_config(config)

def interval_wizard():
    config = load_config()
    if not config or not config["Config"]: return
    display_channel_table(config)
    choice = Prompt.ask("Select ID, 'all', or 'c' to cancel")
    if choice.lower() == 'c': return
    mini, maxi = float(Prompt.ask("New Min delay")), float(Prompt.ask("New Max delay"))
    if choice.lower() == 'all':
        for entry in config["Config"]:
            entry["messages"][0]["min_interval"], entry["messages"][0]["max_interval"] = mini, maxi
    else:
        try:
            idx = int(choice) - 1
            config["Config"][idx]["messages"][0]["min_interval"], config["Config"][idx]["messages"][0]["max_interval"] = mini, maxi
        except: return
    save_config(config)

def delete_channel_wizard():
    config = load_config()
    if not config or not config["Config"]: return
    display_channel_table(config)
    choice = Prompt.ask("Select ID to delete or 'c' to cancel")
    if choice.lower() == 'c': return
    try: config["Config"].pop(int(choice)-1)
    except: return
    save_config(config)

@app.command()
def main():
    while True:
        console.print(Panel.fit(BANNER, title="Discord Automator", border_style="blue"))
        # Colored menu items restored based on image_0b471e.png
        console.print("\n1. [bold green]Start Bot[/bold green]")
        console.print("2. [bold cyan]Add New Channels[/bold cyan]")
        console.print("3. [bold magenta]Update Global Token[/bold magenta]")
        console.print("4. [bold yellow]Edit Messages[/bold yellow]")
        console.print("5. [bold blue]Change Intervals[/bold blue]")
        console.print("6. [bold red]Delete Channels[/bold red]")
        console.print("7. Exit")
        
        c = Prompt.ask("Action [1/2/3/4/5/6/7]")
        if c == "1": start_bot()
        elif c == "2": setup_wizard()
        elif c == "3": 
            config = load_config() or {"Global_Token": "", "Config": []}
            config["Global_Token"] = Prompt.ask("Token")
            save_config(config)
        elif c == "4": edit_message_wizard()
        elif c == "5": interval_wizard()
        elif c == "6": delete_channel_wizard()
        elif c == "7": break

if __name__ == '__main__':
    app()
