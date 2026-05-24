#!/home/axle/venv/bin/python
from http.client import HTTPSConnection 
from json import dumps, loads
from time import sleep 
import json
import threading
from datetime import datetime
import random
import os
import shutil
import typer
from rich.console import Console, Group
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.live import Live
from rich.align import Align

app = typer.Typer()
console = Console()

BANNER = "🤖 ✨ [bold cyan]A U T O   M S G   N I   A X L E[/bold cyan] ✨ 💬"

shutdown_event = threading.Event()
channel_statuses = {}
status_lock = threading.Lock()
total_sent_global = 0
bot_run_cache = {}

# --- Helper: Screen & Time Formatting ---
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def format_seconds_to_mmss(seconds):
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes}:{secs:02d}"

# --- Profile Management Helpers ---
def get_manager():
    if os.path.exists('./config_manager.json'):
        with open('./config_manager.json', 'r') as f:
            try: 
                data = json.load(f)
                if "active_profile" in data and "active_profiles" not in data:
                    data["active_profiles"] = [data["active_profile"]]
                return data
            except Exception: pass
    return {"active_profiles": ["default"]}

def save_manager(data):
    with open('./config_manager.json', 'w') as f:
        json.dump(data, f, indent=4)

def list_profiles():
    profiles = []
    if os.path.exists('.'):
        for file in os.listdir('.'):
            if file.startswith('config_') and file.endswith('.json') and file != 'config_manager.json':
                profiles.append(file[7:-5])
    if not profiles:
        profiles = ["default"]
    return sorted(profiles)

def get_active_profile_names():
    active_list = get_manager().get("active_profiles", ["default"])
    profiles = list_profiles()
    valid_active = [p for p in active_list if p in profiles]
    if not valid_active:
        valid_active = [profiles[0]]
        mgr = get_manager()
        mgr["active_profiles"] = valid_active
        save_manager(mgr)
    return valid_active

def get_profile_filename(profile_name):
    return f"./config_{profile_name}.json"

def init_profile_system():
    active_list = get_active_profile_names()
    for active in active_list:
        filename = get_profile_filename(active)
        if active == "default" and not os.path.exists(filename) and os.path.exists('./config.json'):
            try: os.rename('./config.json', filename)
            except Exception: pass
        if not os.path.exists(filename):
            with open(filename, 'w') as f:
                json.dump({"Discord_Token": "", "Config": []}, f, indent=4)

# --- Main Configuration Handlers ---
def load_config(profile_name=None):
    init_profile_system()
    p_name = profile_name or get_active_profile_names()[0]
    filename = get_profile_filename(p_name)
    with open(filename, 'r') as f: 
        try:
            data = json.load(f)
            if "Global_Token" in data:
                data["Discord_Token"] = data.pop("Global_Token")
                with open(filename, 'w') as fw:
                    json.dump(data, fw, indent=4)
            return data
        except Exception:
            return {"Discord_Token": "", "Config": []}

def save_config(config_data, profile_name=None):
    p_name = profile_name or get_active_profile_names()[0]
    filename = get_profile_filename(p_name)
    with open(filename, 'w') as f:
        json.dump(config_data, f, indent=4)

def load_active_configs():
    p_names = get_active_profile_names()
    configs = {}
    for p in p_names:
        filename = get_profile_filename(p)
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                try:
                    data = json.load(f)
                    if "Global_Token" in data:
                        data["Discord_Token"] = data.pop("Global_Token")
                    configs[p] = data
                except Exception:
                    configs[p] = {"Discord_Token": "", "Config": []}
        else:
            configs[p] = {"Discord_Token": "", "Config": []}
    return configs

# --- Operational Logic Functions ---
def generate_status_table():
    renderables = []
    with status_lock:
        profiles_in_statuses = sorted(list(set(info['profile'] for info in channel_statuses.values())))
    
    for p_name in profiles_in_statuses:
        table = Table(show_header=True, header_style="bold magenta", box=None, padding=(0, 2), title=f"[bold yellow]Profile Loadout: {p_name}[/bold yellow]")
        table.add_column("Channel(s)", style="green") 
        table.add_column("Sent (Ch)", justify="center", style="bold cyan")
        table.add_column("Current Status", width=24)
        table.add_column("Last Sent", justify="right", style="dim")
        
        has_rows = False
        with status_lock:
            for key, info in sorted(channel_statuses.items()):
                if info['profile'] == p_name:
                    table.add_row(info['name'], str(info['count']), info['msg'], info['ts'])
                    has_rows = True
        if has_rows:
            renderables.append(table)
            renderables.append("") 
            
    if renderables and renderables[-1] == "":
        renderables.pop()

    return Panel(
        Align.center(Group(*renderables) if renderables else "No profiles active/running"),
        title=f"[bold white]Live Monitor[/bold white] | [bold green]Total Global Sent: {total_sent_global}[/bold green]",
        border_style="blue",
        subtitle="[dim]Press Ctrl+C to Stop[/dim]"
    )

def update_status(profile_name, name, msg, ts=None, count=None):
    key = f"{profile_name}::{name}"
    with status_lock:
        if key not in channel_statuses:
            channel_statuses[key] = {"profile": profile_name, "name": name, "msg": "", "ts": "-", "count": 0}
        channel_statuses[key]["msg"] = msg
        if ts: channel_statuses[key]["ts"] = ts
        if count is not None: channel_statuses[key]["count"] = count

def send_message_with_retry(cid, data, token, profile_name, name): 
    global total_sent_global
    try:
        conn = HTTPSConnection("discordapp.com", 443, timeout=10)
        conn.request("POST", f"/api/v9/channels/{cid}/messages", data, {"content-type": "application/json", "authorization": token}) 
        resp = conn.getcall() if False else conn.getcall() if False else conn.getcall() if False else conn.getcall() if False else conn.getresponse()
        
        if 199 < resp.status < 300: 
            total_sent_global += 1
            key = f"{profile_name}::{name}"
            with status_lock:
                channel_statuses[key]["count"] += 1
                current_count = channel_statuses[key]["count"]
            update_status(profile_name, name, "[bold green]✅ Sent[/bold green]", datetime.now().strftime('%H:%M:%S'), count=current_count)
            return True
        elif resp.status == 429:
            body = resp.read().decode()
            wait_time = int(loads(body).get('retry_after', 5))
            update_status(profile_name, name, f"[bold red]⚠ Rate Limit: {wait_time}s[/bold red]")
            sleep(wait_time)
            return False
        elif resp.status == 401:
            update_status(profile_name, name, "[bold red]❌ Err: Bad Token (401)[/bold red]")
            sleep(5)
            return False
        elif resp.status == 403:
            update_status(profile_name, name, "[bold red]❌ Err: No Perms (403)[/bold red]")
            sleep(5)
            return False
        elif resp.status == 404:
            update_status(profile_name, name, "[bold red]❌ Err: Not Found (404)[/bold red]")
            sleep(5)
            return False
        elif resp.status >= 500:
            update_status(profile_name, name, f"[bold red]❌ Err: Discord Down ({resp.status})[/bold red]")
            sleep(5)
            return False
        else:
            update_status(profile_name, name, f"[bold red]❌ Err: HTTP {resp.status}[/bold red]")
            sleep(5)
            return False 
    except Exception as e:
        err_str = str(e).lower()
        if "timeout" in err_str:
            update_status(profile_name, name, "[bold red]❌ Err: Network Timeout[/bold red]")
        elif "connection" in err_str or "getaddrinfo" in err_str or "unreachable" in err_str:
            update_status(profile_name, name, "[bold red]❌ Err: Offline/No Internet[/bold red]")
        else:
            update_status(profile_name, name, f"[bold red]❌ Err: {str(e)[:18]}[/bold red]")
        sleep(5)
        return False

def message_loop(msg, mini, maxi, cid, token, profile_name, name):
    while not shutdown_event.is_set():
        update_status(profile_name, name, "[bold yellow]⏳ Sending...[/bold yellow]")
        success = send_message_with_retry(cid, dumps({"content": msg}), token, profile_name, name)
        
        if success and not shutdown_event.is_set():
            sleep(2)
            delay = int(random.uniform(mini, maxi))
            for i in range(delay, 0, -1):
                if shutdown_event.is_set(): break
                update_status(profile_name, name, f"[bold yellow]⏲ Cooldown: {format_seconds_to_mmss(i)}[/bold yellow]")
                sleep(1)
        else:
            if not shutdown_event.is_set(): sleep(5)

def display_isolated_tables(active_configs, view_mode="messages", main_title="Configurations Overview"):
    flat_list = []
    global_idx = 1
    
    console.print(f"\n[bold white underline]{main_title}[/bold white underline]")
    
    for p_name, config in sorted(active_configs.items()):
        channels = config.get("Config", [])
        if not channels:
            continue
            
        table = Table(title=f"[bold yellow]Profile: {p_name}[/bold yellow]", header_style="bold magenta")
        table.add_column("ID", justify="center", style="cyan")
        table.add_column("Channel(s)", style="green")
        table.add_column("Channel ID", style="yellow")
        table.add_column("Interval Range", style="blue")
        
        if view_mode == "messages":
            table.add_column("Message Content Preview", style="white")
        else:
            table.add_column("Message Preview", style="dim white")
            
        for entry_idx, entry in enumerate(channels):
            if not entry.get("messages"):
                entry["messages"] = [{"content": "", "min_interval": 60.0, "max_interval": 90.0}]
                
            m = entry["messages"][0]
            msg = m.get("content", "")
            preview = (msg[:40] + '...') if len(msg) > 40 else msg
            
            table.add_row(
                str(global_idx), 
                entry.get("name", "Unknown"), 
                entry.get("channel_id", "Unknown"), 
                f"{m.get('min_interval', 60)}s-{m.get('max_interval', 90)}s", 
                preview
            )
            flat_list.append((p_name, entry_idx))
            global_idx += 1
            
        console.print(table)
        console.print("") 
        
    return flat_list

def select_profile_interactively(active_configs, action_title):
    """Helper to let user pick 1 profile if multiple are active."""
    p_names = sorted(list(active_configs.keys()))
    if len(p_names) <= 1:
        return p_names[0] if p_names else None
        
    clear_screen()
    console.print(f"[bold cyan]Select Profile to {action_title}:[/bold cyan]")
    for i, p in enumerate(p_names):
        channels_count = len(active_configs[p].get("Config", []))
        console.print(f"{i+1}. [bold yellow]{p}[/bold yellow] ({channels_count} channels)")
        
    choice = Prompt.ask("Choose profile ID (or 'c' to cancel)")
    if choice.lower() == 'c':
        return None
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(p_names):
            return p_names[idx]
    except ValueError:
        pass
    console.print("[bold red]Invalid Profile Selection.[/bold red]")
    sleep(1)
    return None

def fetch_channel_and_guild_info(cid, token):
    try:
        conn = HTTPSConnection("discordapp.com", 443, timeout=10)
        conn.request("GET", f"/api/v9/channels/{cid}", body=None, headers={"authorization": token})
        resp = conn.getcall() if False else conn.getcall() if False else conn.getcall() if False else conn.getresponse()
        if 199 < resp.status < 300:
            channel_data = loads(resp.read().decode())
            channel_name = channel_data.get("name", "Unknown-Channel")
            guild_id = channel_data.get("guild_id")
            slowmode = channel_data.get("rate_limit_per_user", 0)
            
            server_name = "Direct Message / Group"
            if guild_id:
                conn.request("GET", f"/api/v9/guilds/{guild_id}", body=None, headers={"authorization": token})
                g_resp = conn.getcall() if False else conn.getcall() if False else conn.getcall() if False else conn.getcall() if False else conn.getresponse()
                if 199 < g_resp.status < 300:
                    guild_data = loads(g_resp.read().decode())
                    server_name = guild_data.get("name", "Unknown Server")
            return server_name, channel_name, slowmode
    except Exception:
        pass
    return None, None, 0

# --- Application Configuration Wizards ---
def start_bot():
    clear_screen()
    selected_profiles = get_active_profile_names()
                
    if not selected_profiles:
        console.print("[bold red]No active profiles selected to run.[/bold red]")
        sleep(2)
        return
        
    shutdown_event.clear()
    channel_statuses.clear()
    
    has_running_channels = False
    for p_name in selected_profiles:
        filename = get_profile_filename(p_name)
        if not os.path.exists(filename):
            continue
        with open(filename, 'r') as f:
            try: config = json.load(f)
            except Exception: continue
        
        tok = config.get("Discord_Token")
        if not tok or not tok.strip():
            console.print(f"[bold red]Warning: No Discord Token set for profile '{p_name}'. Skipping.[/bold red]")
            sleep(1.5)
            continue
            
        for entry in config.get('Config', []):
            if not entry.get("messages"): continue
            has_running_channels = True
            update_status(p_name, entry["name"], "[dim]Wait...[/dim]", count=0)
            threading.Thread(
                target=message_loop, 
                args=(entry['messages'][0]['content'], entry['messages'][0]['min_interval'], entry['messages'][0]['max_interval'], entry["channel_id"], tok, p_name, entry["name"]), 
                daemon=True
            ).start()
            
    if not has_running_channels:
        console.print("[bold red]No active channels to run across selected profiles![/bold red]")
        sleep(2)
        return
        
    clear_screen()
    with Live(generate_status_table(), refresh_per_second=2) as live:
        try:
            while not shutdown_event.is_set():
                live.update(generate_status_table())
                sleep(0.5)
        except KeyboardInterrupt:
            shutdown_event.set()

def setup_wizard():
    while True:
        clear_screen()
        active_p_names = get_active_profile_names()
        if len(active_p_names) > 1:
            console.print("[bold cyan]Select active profile to add new channel to:[/bold cyan]")
            for i, p in enumerate(active_p_names):
                console.print(f"{i+1}. {p}")
            p_choice = Prompt.ask("Choose profile ID", choices=[str(i+1) for i in range(len(active_p_names))])
            target_profile = active_p_names[int(p_choice) - 1]
        else:
            target_profile = active_p_names[0]

        config = load_config(target_profile)
        tok = config.get("Discord_Token")
        
        if not tok or not tok.strip():
            console.print(f"[bold red]Error: Cannot add channels without a Discord Token for profile '{target_profile}'. Update token first.[/bold red]")
            sleep(2)
            return
        
        cid = Prompt.ask("Channel ID (or 'c' to cancel)")
        if cid.lower() == 'c': break
        
        with console.status("[bold cyan]Fetching channel and server details...[/bold cyan]"):
            server_name, channel_name, slowmode = fetch_channel_and_guild_info(cid, tok)
        
        msg = ""
        if config.get("Config") and Prompt.ask("Copy message from an existing channel? (y/n)", default="n") == "y":
            flat_list = display_isolated_tables({target_profile: config}, "messages", "Choose channel to copy from")
            if flat_list:
                choice = Prompt.ask("Select ID to copy from")
                try:
                    idx = int(choice) - 1
                    if 0 <= idx < len(flat_list):
                        _, entry_idx = flat_list[idx]
                        msg = config["Config"][entry_idx]["messages"][0]["content"]
                except:
                    console.print("[bold red]Invalid Selection.[/bold red]")
        
        if not msg:
            msg = get_multiline_input("Message content")
            if msg.lower() == 'c': continue
        
        if server_name and channel_name:
            console.print(f"[bold green]✓ Connected: [yellow]{server_name}[/yellow] | #{channel_name}[/bold green]")
            if slowmode > 0:
                console.print(f"[bold yellow]⚠ Slowmode detected: {slowmode}s. Suggested min delay: {max(60, slowmode+5)}s[/bold yellow]")
            default_name = channel_name
        else:
            console.print("[bold yellow]⚠ Could not fetch details.[/bold yellow]\n")
            default_name = ""

        name = Prompt.ask("Channel(s)", default=default_name)
        
        suggested_min = str(max(60, slowmode + 5))
        mini = float(Prompt.ask("Min delay", default=suggested_min))
        maxi = float(Prompt.ask("Max delay", default=str(float(mini) + 30)))

        config["Config"].append({"name": name, "channel_id": cid, "messages": [{"content": msg, "min_interval": mini, "max_interval": maxi}]})
        save_config(config, target_profile)
        console.print("[bold green]Channel added![/bold green]")
        
        if Prompt.ask("Add another channel? (y/n)", default="y") == "n":
            break

def update_token_wizard():
    active_configs = load_active_configs()
    if not active_configs:
        clear_screen()
        console.print("[bold red]No active profiles found![/bold red]")
        sleep(2)
        return

    p_names = sorted(list(active_configs.keys()))
    target_profile = None
    update_all = False

    if len(p_names) > 1:
        clear_screen()
        console.print("[bold cyan]Select Profile to Update Discord Token:[/bold cyan]")
        for i, p in enumerate(p_names):
            console.print(f"{i+1}. [bold yellow]{p}[/bold yellow]")
        console.print(f"{len(p_names)+1}. [bold green]All Active Profiles[/bold green]")
        
        choice = Prompt.ask("Choose profile ID (or 'c' to cancel)")
        if choice.lower() == 'c':
            return
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(p_names):
                target_profile = p_names[idx]
            elif idx == len(p_names):
                update_all = True
            else:
                console.print("[bold red]Invalid Selection.[/bold red]")
                sleep(1)
                return
        except ValueError:
            console.print("[bold red]Invalid Selection.[/bold red]")
            sleep(1)
            return
    else:
        target_profile = p_names[0]

    clear_screen()
    if update_all:
        prompt_msg = "Enter new Discord Token for ALL active profiles (or 'c' to cancel)"
    else:
        prompt_msg = f"Enter new Discord Token for profile '{target_profile}' (or 'c' to cancel)"
        
    new_token = Prompt.ask(prompt_msg)
    if new_token.lower() == 'c': return

    if update_all:
        for p_name in p_names:
            config = load_config(p_name)
            config["Discord_Token"] = new_token
            save_config(config, p_name)
        console.print("[bold green]Discord Token successfully updated for all active profiles![/bold green]")
    else:
        config = load_config(target_profile)
        config["Discord_Token"] = new_token
        save_config(config, target_profile)
        console.print(f"[bold green]Discord Token successfully updated for profile '{target_profile}'![/bold green]")
    sleep(1.5)

def edit_message_wizard():
    while True:
        active_configs = load_active_configs()
        total_channels = sum(len(c.get("Config", [])) for c in active_configs.values())
        if total_channels == 0:
            clear_screen()
            console.print("[bold red]No channels found in any active profile! Please add a channel first.[/bold red]")
            sleep(2)
            return
            
        target_profile = select_profile_interactively(active_configs, "Edit Messages")
        if not target_profile:
            return
            
        clear_screen()
        isolated_config = {target_profile: active_configs[target_profile]}
        flat_list = display_isolated_tables(isolated_config, "messages", f"Channels inside profile: {target_profile}")
        
        if not flat_list:
            console.print("[bold red]No layout configurations found inside this profile.[/bold red]")
            sleep(2)
            continue

        choice = Prompt.ask("Select ID, 'all', or 'c' to cancel")
        if choice.lower() == 'c': continue
        
        if choice.lower() == 'all':
            new_msg = get_multiline_input(f"Enter new message for ALL channels in profile '{target_profile}'")
            if new_msg.lower() == 'c': continue
            config = active_configs[target_profile]
            for entry in config.get("Config", []): 
                if "messages" not in entry or not entry["messages"]:
                    entry["messages"] = [{"content": ""}]
                entry["messages"][0]["content"] = new_msg
            save_config(config, target_profile)
            console.print(f"[bold green]All messages updated inside profile '{target_profile}'![/bold green]")
            sleep(1.5)
        else:
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(flat_list):
                    p_name, entry_idx = flat_list[idx]
                    config = active_configs[p_name]
                    new_msg = get_multiline_input(f"Enter new message for {config['Config'][entry_idx]['name']}")
                    if new_msg.lower() == 'c': continue
                    config["Config"][entry_idx]["messages"][0]["content"] = new_msg
                    save_config(config, p_name)
                    console.print("[bold green]Message updated successfully![/bold green]")
                    sleep(1)
                else:
                    console.print("[bold red]Invalid ID.[/bold red]"); sleep(1)
            except ValueError:
                console.print("[bold red]Invalid input.[/bold red]"); sleep(1)

def interval_wizard():
    while True:
        active_configs = load_active_configs()
        total_channels = sum(len(c.get("Config", [])) for c in active_configs.values())
        if total_channels == 0:
            clear_screen()
            console.print("[bold red]No channels found in any active profile![/bold red]")
            sleep(2)
            return
            
        target_profile = select_profile_interactively(active_configs, "Change Intervals")
        if not target_profile:
            return
            
        clear_screen()
        isolated_config = {target_profile: active_configs[target_profile]}
        flat_list = display_isolated_tables(isolated_config, "intervals", f"Channels inside profile: {target_profile}")
        
        if not flat_list:
            console.print("[bold red]No active channels found inside this profile.[/bold red]")
            sleep(2)
            continue

        choice = Prompt.ask("Select ID, 'all', or 'c' to cancel")
        if choice.lower() == 'c': continue
        
        try:
            mini = float(Prompt.ask("New Min interval (seconds)"))
            maxi = float(Prompt.ask("New Max interval (seconds)"))
            
            if choice.lower() == 'all':
                config = active_configs[target_profile]
                for entry in config.get("Config", []):
                    if "messages" not in entry or not entry["messages"]:
                        entry["messages"] = [{"content": ""}]
                    entry["messages"][0]["min_interval"], entry["messages"][0]["max_interval"] = mini, maxi
                save_config(config, target_profile)
            elif choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(flat_list):
                    p_name, entry_idx = flat_list[idx]
                    config = active_configs[p_name]
                    config["Config"][entry_idx]["messages"][0]["min_interval"] = mini
                    config["Config"][entry_idx]["messages"][0]["max_interval"] = maxi
                    save_config(config, p_name)
                else:
                    console.print("[bold red]Invalid selection.[/bold red]"); sleep(1); continue
            else:
                console.print("[bold red]Invalid selection.[/bold red]"); sleep(1); continue
                
            console.print("[bold green]Intervals updated successfully![/bold green]")
            sleep(1.5)
        except ValueError:
            console.print("[bold red]Please enter valid numbers.[/bold red]"); sleep(1)

def delete_channel_wizard():
    while True:
        active_configs = load_active_configs()
        total_channels = sum(len(c.get("Config", [])) for c in active_configs.values())
        if total_channels == 0:
            clear_screen()
            console.print("[bold red]No channels found in any active profile![/bold red]")
            sleep(2)
            return
            
        target_profile = select_profile_interactively(active_configs, "Delete Channels")
        if not target_profile:
            return
            
        clear_screen()
        isolated_config = {target_profile: active_configs[target_profile]}
        flat_list = display_isolated_tables(isolated_config, "messages", f"Channels inside profile: {target_profile}")
        
        if not flat_list:
            console.print("[bold red]No channels discovered to remove in this profile.[/bold red]")
            sleep(2)
            continue

        console.print("[dim]Use 'all' to delete ALL channels inside this profile layout loadout.[/dim]")
        choice = Prompt.ask("Select ID, 'all', or 'c' to cancel")
        if choice.lower() == 'c': continue
        
        if choice.lower() == 'all':
            confirm = Prompt.ask(f"[bold red]Are you absolutely sure you want to delete ALL channels inside profile '{target_profile}'?[/bold red] (y/n)", choices=["y", "n"], default="n")
            if confirm.lower() == 'y':
                config = active_configs[target_profile]
                config["Config"] = []
                save_config(config, target_profile)
                console.print(f"[bold green]All channels wiped clean inside profile '{target_profile}'.[/bold green]")
                sleep(1.5)
            continue

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(flat_list):
                p_name, entry_idx = flat_list[idx]
                config = active_configs[p_name]
                target_name = config["Config"][entry_idx]["name"]
                confirm = Prompt.ask(f"Delete '[bold red]{target_name}[/bold red]' from profile '{p_name}'? (y/n)", choices=["y", "n"], default="n")
                if confirm.lower() == 'y':
                    config["Config"].pop(entry_idx)
                    save_config(config, p_name)
                    console.print(f"[bold green]Successfully deleted '{target_name}' from profile '{p_name}'.[/bold green]")
                    sleep(1.5)
            else:
                console.print("[bold red]ID out of range.[/bold red]"); sleep(1)
        except ValueError:
            console.print("[bold red]Invalid input.[/bold red]"); sleep(1)

def profile_manager_wizard():
    while True:
        clear_screen()
        active_list = get_active_profile_names()
        profiles = list_profiles()
        
        table = Table(title="Profile & Loadout Configuration Manager", header_style="bold magenta")
        table.add_column("ID", justify="center", style="cyan")
        table.add_column("Profile Name", style="green")
        table.add_column("Channels Connected", justify="center", style="blue")
        table.add_column("Discord Token State", style="white")
        table.add_column("Active State", justify="center", style="magenta")
        
        for i, p in enumerate(profiles):
            status = "[bold yellow]● Active[/bold yellow]" if p in active_list else "[dim]Inactive[/dim]"
            p_file = get_profile_filename(p)
            channels_count = "0"
            token_status = "[bold red]Missing[/bold red]"
            
            if os.path.exists(p_file):
                try:
                    with open(p_file, 'r') as f:
                        p_data = json.load(f)
                        channels_count = str(len(p_data.get("Config", [])))
                        tok = p_data.get("Discord_Token", "")
                        if tok and tok.strip():
                            token_status = f"[bold green]Configured[/bold green]"
                except Exception: pass
                
            table.add_row(str(i+1), p, channels_count, token_status, status)
            
        console.print(table)
        console.print("\n1. [bold green]Toggle Active Status (Run Concurrently)[/bold green]\n2. [bold cyan]Create New[/bold cyan]\n3. [bold yellow]Rename[/bold yellow]\n4. [bold blue]Clone[/bold blue]\n5. [bold red]Delete Profile[/bold red]\n6. [bold white]Go Back[/bold white]")
        choice = Prompt.ask("Action", choices=["1","2","3","4","5","6"])
        
        if choice == "1":
            idx_str = Prompt.ask("Toggle Active Status for Profile ID")
            try:
                idx = int(idx_str) - 1
                if 0 <= idx < len(profiles):
                    target_p = profiles[idx]
                    mgr = get_manager()
                    current_active = mgr.get("active_profiles", ["default"])
                    if target_p in current_active:
                        if len(current_active) > 1:
                            current_active.remove(target_p)
                        else:
                            console.print("[bold red]At least one profile must remain active![/bold red]")
                            sleep(1.5)
                    else:
                        current_active.append(target_p)
                    mgr["active_profiles"] = current_active
                    save_manager(mgr)
            except (ValueError, IndexError): pass
        elif choice == "2":
            new_name = Prompt.ask("New Profile Name").strip()
            if not new_name: continue
            clean_name = "".join([c for c in new_name if c.isalnum() or c in ('-', '_')])
            filename = get_profile_filename(clean_name)
            if not os.path.exists(filename):
                with open(filename, 'w') as f:
                    json.dump({"Discord_Token": "", "Config": []}, f, indent=4)
        elif choice == "3":
            idx_str = Prompt.ask("Rename Profile ID")
            try:
                idx = int(idx_str) - 1
                if 0 <= idx < len(profiles):
                    old_name = profiles[idx]
                    new_name = Prompt.ask("Enter new name").strip()
                    if new_name:
                        new_name = "".join([c for c in new_name if c.isalnum() or c in ('-', '_')])
                        os.rename(get_profile_filename(old_name), get_profile_filename(new_name))
                        mgr = get_manager()
                        current_active = mgr.get("active_profiles", ["default"])
                        current_active = [new_name if x == old_name else x for x in current_active]
                        mgr["active_profiles"] = current_active
                        save_manager(mgr)
            except (ValueError, IndexError): pass
        elif choice == "4":
            idx_str = Prompt.ask("Clone Profile ID")
            try:
                idx = int(idx_str) - 1
                if 0 <= idx < len(profiles):
                    old_name = profiles[idx]
                    new_name = Prompt.ask("Enter new cloned name").strip()
                    if new_name:
                        new_name = "".join([c for c in new_name if c.isalnum() or c in ('-', '_')])
                        new_filename = get_profile_filename(new_name)
                        shutil.copy(get_profile_filename(old_name), new_filename)
                        
                        if Prompt.ask("Do you want to change the Discord token for this cloned profile? (y/n)", choices=["y", "n"], default="n") == "y":
                            tok_new = Prompt.ask("Enter new Discord Token")
                            if os.path.exists(new_filename):
                                with open(new_filename, 'r') as f:
                                    try: p_data = json.load(f)
                                    except Exception: p_data = {"Discord_Token": "", "Config": []}
                                p_data["Discord_Token"] = tok_new
                                with open(new_filename, 'w') as f:
                                    json.dump(p_data, f, indent=4)
                                console.print("[bold green]Token updated in cloned profile![/bold green]")
                                sleep(1.5)
            except (ValueError, IndexError): pass
        elif choice == "5":
            idx_str = Prompt.ask("Delete Profile ID")
            try:
                idx = int(idx_str) - 1
                if 0 <= idx < len(profiles) and len(profiles) > 1:
                    del_name = profiles[idx]
                    confirm = Prompt.ask(f"Are you sure you want to delete profile '[bold red]{del_name}[/bold red]'? (y/n)", choices=["y", "n"], default="n")
                    if confirm == "y":
                        os.remove(get_profile_filename(del_name))
                        mgr = get_manager()
                        current_active = mgr.get("active_profiles", ["default"])
                        current_active = [p for p in current_active if p != del_name]
                        if not current_active:
                            remaining = [p for p in profiles if p != del_name]
                            current_active = [remaining[0]] if remaining else ["default"]
                        mgr["active_profiles"] = current_active
                        save_manager(mgr)
                        console.print(f"[bold green]Profile '{del_name}' deleted successfully.[/bold green]")
                        sleep(1.5)
            except (ValueError, IndexError): pass
        elif choice == "6": break

def get_multiline_input(prompt_text):
    console.print(f"[yellow]{prompt_text}[/yellow] [dim](Type 'END' to save, 'c' to cancel)[/dim]")
    lines = []
    while True:
        line = input()
        if line.strip().lower() == 'c': return 'c'
        if line.strip().upper() == "END": break
        lines.append(line)
    return "\n".join(lines)

@app.command()
def main():
    init_profile_system()
    while True:
        clear_screen()
        active_p_list = ", ".join(get_active_profile_names())
        display_title = f"Discord Automator | Active Loadouts: [bold yellow]{active_p_list}[/bold yellow]"
        console.print(Panel.fit(BANNER, title=display_title, border_style="blue"))
        console.print("\n1. [bold green]Start Bot[/bold green]\n2. [bold cyan]Add New Channels[/bold cyan]\n3. [bold magenta]Update Discord Token[/bold magenta]\n4. [bold yellow]Edit Messages[/bold yellow]\n5. [bold blue]Change Intervals[/bold blue]\n6. [bold red]Delete Channels[/bold red]\n7. [bold white]Profile Manager[/bold white]\n8. Exit")
        c = Prompt.ask("Action", choices=["1","2","3","4","5","6","7","8"])
        if c == "1": start_bot()
        elif c == "2": setup_wizard()
        elif c == "3": update_token_wizard()
        elif c == "4": edit_message_wizard()
        elif c == "5": interval_wizard()
        elif c == "6": delete_channel_wizard()
        elif c == "7": profile_manager_wizard()
        elif c == "8": break

if __name__ == '__main__':
    app()
