#!/home/axle/myenv/bin/python
from http.client import HTTPSConnection 
from sys import stderr 
from json import dumps
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
        if line.strip().upper() == "END":
            break
        lines.append(line)
    return "\n".join(lines)

def token_manager():
    console.print(Panel.fit("[bold magenta]Global Token Manager[/bold magenta]", border_style="magenta"))
    config_data = load_config() or {"Global_Token": "", "Config": []}
    current_token = config_data.get("Global_Token", "")
    if current_token:
        console.print(f"[yellow]Current Token:[/yellow] ...{current_token[-10:]}")
        if not Confirm.ask("Update token?"): return
    new_token = Prompt.ask("Enter Global Discord Token")
    config_data["Global_Token"] = new_token
    save_config(config_data)

def edit_message_wizard():
    while True:
        config_data = load_config()
        if not config_data or not config_data.get("Config"):
            console.print("[red]No channels to edit![/red]"); break
        table = Table(title="Edit Message Menu")
        table.add_column("ID", style="cyan")
        table.add_column("Nickname", style="yellow")
        table.add_column("Current Message", style="green")
        for idx, entry in enumerate(config_data["Config"]):
            msg_preview = entry["messages"][0]["content"].replace("\n", " ")[:40]
            if len(entry["messages"][0]["content"]) > 40: msg_preview += "..."
            table.add_row(str(idx + 1), entry.get("name", "Unnamed"), msg_preview)
        console.print(table)
        choice = Prompt.ask("Enter ID to edit, 'all' to update every channel, or [bold red]'c'[/bold red] to exit")
        if choice.lower() == 'c': break
        
        if choice.lower() == 'all':
            new_content = get_multiline_input("Enter NEW message for ALL channels:")
            for entry in config_data["Config"]: entry["messages"][0]["content"] = new_content
            save_config(config_data)
            console.print("[bold green]Success: Updated ALL channels.[/bold green]\n")
        else:
            try:
                idx = int(choice) - 1
                new_content = get_multiline_input(f"Enter NEW message for {config_data['Config'][idx].get('name')}:")
                config_data["Config"][idx]["messages"][0]["content"] = new_content
                save_config(config_data)
                console.print(f"[bold green]Success: Updated channel {idx+1}.[/bold green]\n")
            except: console.print("[red]Invalid selection![/red]")

def interval_wizard():
    """New function to change Min/Max intervals using the same logic as Edit/Delete"""
    while True:
        config_data = load_config()
        if not config_data or not config_data.get("Config"):
            console.print("[red]No channels found![/red]"); break
        
        table = Table(title="Change Intervals Menu")
        table.add_column("ID", style="cyan")
        table.add_column("Nickname", style="yellow")
        table.add_column("Min Interval", style="green")
        table.add_column("Max Interval", style="green")
        
        for idx, entry in enumerate(config_data["Config"]):
            msg_data = entry["messages"][0]
            table.add_row(str(idx + 1), entry.get("name", "Unnamed"), f"{msg_data['min_interval']}s", f"{msg_data['max_interval']}s")
        
        console.print(table)
        choice = Prompt.ask("Enter ID to change, 'all' for every channel, or [bold red]'c'[/bold red] to exit")
        if choice.lower() == 'c': break

        new_min = float(Prompt.ask("Enter NEW Min interval", default="30"))
        new_max = float(Prompt.ask("Enter NEW Max interval", default="60"))

        if choice.lower() == 'all':
            for entry in config_data["Config"]:
                entry["messages"][0]["min_interval"] = new_min
                entry["messages"][0]["max_interval"] = new_max
            save_config(config_data)
            console.print("[bold green]Success: Updated ALL intervals.[/bold green]\n")
        else:
            try:
                idx = int(choice) - 1
                config_data["Config"][idx]["messages"][0]["min_interval"] = new_min
                config_data["Config"][idx]["messages"][0]["max_interval"] = new_max
                save_config(config_data)
                console.print(f"[bold green]Success: Updated intervals for {config_data['Config'][idx].get('name')}.[/bold green]\n")
            except: console.print("[red]Invalid selection![/red]")

def delete_channel_wizard():
    while True:
        config_data = load_config()
        if not config_data or not config_data.get("Config"):
            console.print("[yellow]No channels found to delete![/yellow]"); break
        table = Table(title="Channel Deletion Menu")
        table.add_column("ID", style="cyan")
        table.add_column("Nickname", style="yellow")
        table.add_column("Channel ID", style="magenta")
        table.add_column("Saved Message", style="green")
        for idx, entry in enumerate(config_data["Config"]):
            msg = entry["messages"][0]["content"].replace("\n", " ")[:30]
            if len(entry["messages"][0]["content"]) > 30: msg += "..."
            table.add_row(str(idx + 1), str(entry.get("name")), str(entry.get("channel_id")), msg)
        console.print(table)
        del_idx = Prompt.ask("Enter ID to delete, 'all' to clear everything, or [bold red]'c'[/bold red] to exit")
        if del_idx.lower() == 'c': break
        if del_idx.lower() == 'all':
            if Confirm.ask("[bold red]Delete ALL channels?[/bold red]"):
                config_data["Config"] = []
                save_config(config_data); break
            else: continue
        try:
            index = int(del_idx) - 1
            removed = config_data["Config"].pop(index)
            save_config(config_data); console.print(f"[red]Deleted: {removed.get('name')}[/red]\n")
        except: console.print("[red]Invalid ID![/red]")

def setup_wizard():
    console.print(Panel.fit("[bold blue]Add New Channels[/bold blue]", border_style="blue"))
    config_data = load_config()
    if not config_data or not config_data.get("Global_Token"):
        token_manager(); config_data = load_config()
    last_message = None
    adding = True
    while adding:
        name = Prompt.ask("\nNickname")
        channel_id = Prompt.ask("Channel ID")
        if last_message and Confirm.ask(f"Use previous message?"):
            content = last_message
        else:
            content = get_multiline_input("Enter message content:")
            last_message = content
        mini = float(Prompt.ask("Min delay", default="30"))
        maxi = float(Prompt.ask("Max delay", default="60"))
        config_data["Config"].append({"name": str(name), "channel_id": str(channel_id), "messages": [{"content": content, "min_interval": mini, "max_interval": maxi}]})
        adding = Confirm.ask("Add another?")
    save_config(config_data)

def get_connection(): return HTTPSConnection("discordapp.com", 443) 
 
def send_message(conn, cid, data, token): 
    try: 
        conn.request("POST", f"/api/v9/channels/{cid}/messages", data, {"content-type": "application/json", "authorization": token}) 
        resp = conn.getresponse() 
        ts = datetime.now().strftime('%H:%M:%S')
        if 199 < resp.status < 300: console.print(f"[bold cyan][{cid}][/bold cyan] Sent at [white]{ts}[/white]")
        else: console.print(f"[bold red][{cid}][/bold red] Error {resp.status}")
    except: pass

def message_loop(msg, mini, maxi, cid, token):
    while not shutdown_event.is_set():
        try:
            send_message(get_connection(), cid, dumps({"content": msg, "tts": "false"}), token)
            if shutdown_event.wait(timeout=random.uniform(mini, maxi)): break
        except: break

def start_bot():
    config_data = load_config()
    if not config_data or not config_data.get("Global_Token"): return
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
    
    console.print(Panel.fit("[bold green]Botting Started![/bold green]\n[bold white]Press Ctrl + C to stop botting[/bold white]", border_style="green"))
    
    try:
        while not shutdown_event.is_set(): sleep(1)
    except KeyboardInterrupt: shutdown_event.set()

@app.command()
def main():
    while True:
        console.print(Panel.fit(BANNER, title="Discord Automator", border_style="blue"))
        console.print("\n1. [bold green]Start Bot[/bold green]")
        console.print("2. [bold cyan]Add New Channels[/bold cyan]")
        console.print("3. [bold magenta]Update Global Token[/bold magenta]")
        console.print("4. [bold yellow]Edit Messages[/bold yellow]")
        console.print("5. [bold blue]Change Intervals[/bold blue]")
        console.print("6. [bold red]Delete Channels[/bold red]")
        console.print("7. [bold white]Exit[/bold white]")
        
        choice = Prompt.ask("Action", choices=["1", "2", "3", "4", "5", "6", "7"])
        if choice == "1": start_bot()
        elif choice == "2": setup_wizard()
        elif choice == "3": token_manager()
        elif choice == "4": edit_message_wizard()
        elif choice == "5": interval_wizard()
        elif choice == "6": delete_channel_wizard()
        elif choice == "7": break

if __name__ == '__main__': app()
