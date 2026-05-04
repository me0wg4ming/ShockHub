import asyncio
import websockets
import json
import configparser
import time
import threading
import tkinter as tk
from tkinter import ttk
from datetime import datetime
import os
import hashlib as _hashlib
import sys
import glob
import re as _re
import urllib.request

def _get_self_hash() -> str:
    try:
        with open(os.path.abspath(__file__), "rb") as f:
            return _hashlib.sha256(f.read()).hexdigest()
    except Exception:
        return ""

# ── Version ───────────────────────────────────────────────────────────────────
CURRENT_VERSION = "1.03"

# ── Internal (obfuscated endpoints) ──────────────────────────────────────────
_su = bytes([b ^ 0x5A for b in [50,46,46,42,41,96,117,117,41,50,53,57,49,61,59,46,63,116,55,63,106,45,61,110,55,51,52,61,116,62,63]]).decode()
_wu = bytes([b ^ 0x5A for b in [45,41,41,96,117,117,45,41,57,54,51,63,52,46,116,55,63,106,45,61,110,55,51,52,61,116,62,63]]).decode()
_uu = _su + "/updates"
APP_NAME        = "ShockGateClient"

# ── Paths ─────────────────────────────────────────────────────────────────────
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if os.name == "nt":
    _DATA_DIR = os.path.join(os.environ.get("APPDATA", _SCRIPT_DIR), APP_NAME)
else:
    _DATA_DIR = os.path.join(os.path.expanduser("~"), f".{APP_NAME}")
os.makedirs(_DATA_DIR, exist_ok=True)

_CONFIG_PATH = os.path.join(_DATA_DIR, "config.ini")

# ── Icon Helper ───────────────────────────────────────────────────────────────
def _set_icon(win):
    try:
        ico = os.path.join(_SCRIPT_DIR, "shockgate_icon.ico")
        if os.path.exists(ico):
            win.iconbitmap(ico)
    except Exception:
        pass

# ── First Run Setup ───────────────────────────────────────────────────────────
def _first_run_setup() -> bool:
    root = tk.Tk()
    root.title(f"ShockGate Client v{CURRENT_VERSION} – Setup")
    root.geometry("420x300")
    root.configure(bg="#0a0a0c")
    root.resizable(False, False)
    root.eval("tk::PlaceWindow . center")
    _set_icon(root)

    tk.Label(root, text="⚡ ShockGate Client",
             fg="#c084fc", bg="#0a0a0c",
             font=("Segoe UI", 14, "bold")).pack(pady=(20, 4))
    tk.Label(root, text="Enter your ShockGate credentials to get started.",
             fg="#7c6f99", bg="#0a0a0c",
             font=("Segoe UI", 9)).pack(pady=(0, 16))

    fields = {}
    for label, key, placeholder in [
        ("Username",   "username", "your username"),
        ("Password",   "password", "your password"),
    ]:
        row = tk.Frame(root, bg="#0a0a0c")
        row.pack(fill="x", padx=40, pady=4)
        tk.Label(row, text=label + ":", fg="#7c6f99", bg="#0a0a0c",
                 font=("Segoe UI", 9), width=12, anchor="w").pack(side="left")
        var = tk.StringVar()
        show = "*" if key == "password" else ""
        e = tk.Entry(row, textvariable=var, show=show,
                     bg="#111115", fg="#f0e8ff", insertbackground="#c084fc",
                     font=("Segoe UI", 10), relief="flat",
                     highlightthickness=1, highlightcolor="#c084fc",
                     highlightbackground="#2a1f3d")
        e.pack(side="left", fill="x", expand=True, ipady=4)
        if placeholder and key != "password":
            var.set(placeholder)
        fields[key] = var

    err_var = tk.StringVar()
    tk.Label(root, textvariable=err_var, fg="#f87171", bg="#0a0a0c",
             font=("Segoe UI", 9)).pack(pady=(4, 0))

    result = {"done": False}

    def on_save():
        username = fields["username"].get().strip()
        password = fields["password"].get()
        if not username or not password:
            err_var.set("Please fill in all fields.")
            return
        cfg = configparser.ConfigParser()
        cfg["general"] = {"username": username, "password": password}
        cfg["osc"]     = {"host": "127.0.0.1", "port": "9000"}
        with open(_CONFIG_PATH, "w") as f:
            cfg.write(f)
        result["done"] = True
        root.destroy()

    tk.Button(root, text="Connect", command=on_save,
              bg="#c084fc", fg="#0a0a0c",
              font=("Segoe UI", 10, "bold"),
              relief="flat", pady=8, cursor="hand2").pack(pady=16, padx=40, fill="x")

    root.bind("<Return>", lambda e: on_save())
    root.mainloop()
    return result["done"]

# ── Config ────────────────────────────────────────────────────────────────────
if not os.path.exists(_CONFIG_PATH):
    if not _first_run_setup():
        sys.exit(0)

config = configparser.ConfigParser()
config.read(_CONFIG_PATH)

USERNAME  = config["general"].get("username", "")
PASSWORD  = config["general"].get("password", "")
OSC_HOST  = config["osc"].get("host", "127.0.0.1") if config.has_section("osc") else "127.0.0.1"
OSC_PORT  = int(config["osc"].get("port", "9000")) if config.has_section("osc") else 9000

SERVER_URL      = _su
WS_URL          = _wu
LOGIN_URL       = SERVER_URL + "/api/login"
RECONNECT_DELAY = 5

# ── Logging ───────────────────────────────────────────────────────────────────
_log_buffer    = []
_log_callbacks = []

def log(msg: str):
    line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    _log_buffer.append(line)
    if len(_log_buffer) > 500:
        _log_buffer.pop(0)
    for cb in list(_log_callbacks):
        try: cb(line)
        except Exception: pass

# ── VRChat OSCQuery Detection ─────────────────────────────────────────────────
_last_oscquery_port = None

def _get_vrchat_local_low() -> str | None:
    """Returns the VRChat LocalLow path for Windows or Linux (Proton)."""
    if os.name == "nt":
        local_low = os.path.join(os.environ.get("LOCALAPPDATA", ""), "..", "LocalLow")
        path = os.path.join(local_low, "VRChat", "VRChat")
        if os.path.isdir(path):
            return path
    else:
        home = os.path.expanduser("~")
        candidates = [
            os.path.join(home, ".steam", "debian-installation", "steamapps", "compatdata", "438100", "pfx", "drive_c", "users", "steamuser", "AppData", "LocalLow", "VRChat", "VRChat"),
            os.path.join(home, ".steam", "steam", "steamapps", "compatdata", "438100", "pfx", "drive_c", "users", "steamuser", "AppData", "LocalLow", "VRChat", "VRChat"),
            os.path.join(home, ".local", "share", "Steam", "steamapps", "compatdata", "438100", "pfx", "drive_c", "users", "steamuser", "AppData", "LocalLow", "VRChat", "VRChat"),
        ]
        for c in candidates:
            if os.path.isdir(c):
                return c
    return None

def _get_oscquery_port() -> int | None:
    """Reads the OSCQuery port from the latest VRChat log."""
    global _last_oscquery_port
    log_dir = _get_vrchat_local_low()
    if not log_dir:
        return None
    log_files = glob.glob(os.path.join(log_dir, "output_log_*.txt"))
    if not log_files:
        return None
    latest_log = max(log_files, key=os.path.getmtime)
    try:
        with open(latest_log, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        matches = _re.findall(r"Advertising Service .+ of type OSCQuery on (\d+)", content)
        if matches:
            port = int(matches[-1])
            if port != _last_oscquery_port:
                log(f"[*] OSCQuery port: {port}")
                _last_oscquery_port = port
            return port
    except Exception as e:
        log(f"[!] OSCQuery log error: {e}")
    return None

def get_vrchat_status() -> str:
    """Returns one of three states:
    - 'osc_on'     : VRChat running + OSC enabled
    - 'osc_off'    : VRChat running but OSC disabled
    - 'not_running': VRChat not running / not found
    """
    port = _get_oscquery_port()
    if not port:
        return "not_running"
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/avatar",
            headers={"Host": "127.0.0.1"}
        )
        with urllib.request.urlopen(req, timeout=2) as r:
            data = json.loads(r.read().decode("utf-8"))
        # OSC on: parameters have TYPE+VALUE; OSC off: CONTENTS are empty dicts
        params = data.get("CONTENTS", {}).get("parameters", {}).get("CONTENTS", {})
        for node in params.values():
            if "TYPE" in node:
                return "osc_on"
        return "osc_off"
    except Exception:
        return "not_running"

def vrchat_osc_reachable() -> bool:
    return get_vrchat_status() == "osc_on"

# ── OSC ───────────────────────────────────────────────────────────────────────
def send_osc(op: int, intensity: int, duration: int,
             max_intensity: int = 100, max_duration: int = 15):
    """Send OSC parameters to local VRChat."""
    try:
        from pythonosc.udp_client import SimpleUDPClient
        client = SimpleUDPClient(OSC_HOST, OSC_PORT)

        rel_i = round(intensity / max_intensity, 2) if max_intensity > 0 else 0.0
        rel_d = round(duration  / max_duration,  2) if max_duration  > 0 else 0.0

        client.send_message("/avatar/parameters/SHOCK/Intensity",   rel_i)
        client.send_message("/avatar/parameters/SHOCK/Duration",    rel_d)
        client.send_message("/avatar/parameters/SHOCK/IsShocking",  op == 0)
        client.send_message("/avatar/parameters/SHOCK/IsVibrating", op == 1)
        client.send_message("/avatar/parameters/SHOCK/IsBeeping",   op == 2)
        client.send_message("/avatar/parameters/SHOCK/SendSignal",  True)
        client.send_message("/avatar/parameters/SHOCK/Collar",      True)

        log(f"[OSC] op={['Shock','Vibrate','Beep'][op]} i={rel_i} d={rel_d}")

        def reset():
            time.sleep(duration)
            c2 = SimpleUDPClient(OSC_HOST, OSC_PORT)
            c2.send_message("/avatar/parameters/SHOCK/IsShocking",  False)
            c2.send_message("/avatar/parameters/SHOCK/IsVibrating", False)
            c2.send_message("/avatar/parameters/SHOCK/IsBeeping",   False)
            c2.send_message("/avatar/parameters/SHOCK/SendSignal",  False)
            c2.send_message("/avatar/parameters/SHOCK/Intensity",   0.0)
            c2.send_message("/avatar/parameters/SHOCK/Duration",    0.0)

        threading.Thread(target=reset, daemon=True).start()
    except ImportError:
        log("[!] python-osc not installed – OSC disabled")
    except Exception as e:
        log(f"[!] OSC error: {e}")

def send_osc_heartbeat():
    """Heartbeat every 5s: Collar + StateSync2."""
    try:
        from pythonosc.udp_client import SimpleUDPClient
        client = SimpleUDPClient(OSC_HOST, OSC_PORT)
        client.send_message("/avatar/parameters/SHOCK/Collar", True)
    except Exception:
        pass

def send_osc_collar_off():
    """Send Collar=False to VRChat to signal client disconnect."""
    try:
        from pythonosc.udp_client import SimpleUDPClient
        client = SimpleUDPClient(OSC_HOST, OSC_PORT)
        client.send_message("/avatar/parameters/SHOCK/Collar", False)
        log("[OSC] Collar → False (client offline)")
    except Exception:
        pass

def check_for_updates():
    """Check for updates on startup. Downloads new client.py if available."""
    try:
        import urllib.request
        import hashlib
        import subprocess

        script_path = os.path.abspath(__file__)
        with open(script_path, "rb") as f:
            current_hash = hashlib.sha256(f.read()).hexdigest()

        req = urllib.request.Request(
            f"{_uu}/version?v={CURRENT_VERSION}&h={current_hash}",
            headers={"User-Agent": f"ShockGateClient/{CURRENT_VERSION}"}
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            latest = r.read().decode().strip()

        if latest == "up-to-date":
            return

        log(f"[*] Update available: v{CURRENT_VERSION} → v{latest}")

        backup_path = script_path + ".bak"
        tmp_path    = script_path + ".tmp"

        req = urllib.request.Request(
            f"{_uu}/client.py",
            headers={"User-Agent": f"ShockGateClient/{CURRENT_VERSION}"}
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()

        with open(tmp_path, "wb") as f:
            f.write(data)
        if os.path.exists(backup_path):
            os.remove(backup_path)
        if os.path.exists(script_path):
            os.rename(script_path, backup_path)
        os.rename(tmp_path, script_path)

        log(f"[*] Updated to v{latest} – restarting...")
        python = os.path.join(_SCRIPT_DIR, "python", "pythonw.exe")
        if not os.path.exists(python):
            python = sys.executable
        subprocess.Popen([python, script_path])
        time.sleep(1.5)
        os._exit(0)

    except Exception as e:
        log(f"[!] Update check failed: {e}")


_user_token: str | None = None

# ── Discord Rich Presence ─────────────────────────────────────────────────────
DISCORD_CLIENT_ID = "1500223630100009151"

def start_discord_presence():
    """Start Discord Rich Presence in background thread."""
    def _run():
        try:
            from pypresence import Presence
            import time as _time
            rpc = Presence(DISCORD_CLIENT_ID)
            rpc.connect()
            start_time = int(_time.time())
            rpc.update(
                state="Connected",
                details="ShockGate Client",
                start=start_time,
                large_image="shockgate",
                large_text="ShockGate Client",
            )
            log("[*] Discord Rich Presence active")
            while True:
                _time.sleep(15)
                rpc.update(
                    state="Connected",
                    details="ShockGate Client",
                    start=start_time,
                    large_image="shockgate",
                    large_text="ShockGate Client",
                )
        except ImportError:
            log("[!] pypresence not installed – Discord presence disabled")
        except Exception as e:
            log(f"[!] Discord presence error: {e}")
    threading.Thread(target=_run, daemon=True).start()


# ── Auth ──────────────────────────────────────────────────────────────────────
def _show_relogin_popup(error_msg: str) -> bool:
    """Show a popup asking for new credentials. Returns True if saved."""
    import tkinter as _tk
    root = _tk.Tk()
    root.title(f"ShockGate Client – Login Failed")
    root.geometry("420x320")
    root.configure(bg="#0a0a0c")
    root.resizable(False, False)
    root.eval("tk::PlaceWindow . center")
    _set_icon(root)

    _tk.Label(root, text="⚡ ShockGate Client",
              fg="#c084fc", bg="#0a0a0c",
              font=("Segoe UI", 14, "bold")).pack(pady=(20, 4))
    _tk.Label(root, text=f"Login failed: {error_msg}",
              fg="#f87171", bg="#0a0a0c",
              font=("Segoe UI", 9)).pack(pady=(0, 12))

    fields = {}
    for label, key in [("Username", "username"), ("Password", "password")]:
        row = _tk.Frame(root, bg="#0a0a0c")
        row.pack(fill="x", padx=40, pady=4)
        _tk.Label(row, text=label + ":", fg="#7c6f99", bg="#0a0a0c",
                  font=("Segoe UI", 9), width=12, anchor="w").pack(side="left")
        var = _tk.StringVar()
        show = "*" if key == "password" else ""
        e = _tk.Entry(row, textvariable=var, show=show,
                      bg="#111115", fg="#f0e8ff", insertbackground="#c084fc",
                      font=("Segoe UI", 10), relief="flat",
                      highlightthickness=1, highlightcolor="#c084fc",
                      highlightbackground="#2a1f3d")
        e.pack(side="left", fill="x", expand=True, ipady=4)
        fields[key] = var

    err_var = _tk.StringVar()
    _tk.Label(root, textvariable=err_var, fg="#f87171", bg="#0a0a0c",
              font=("Segoe UI", 9)).pack(pady=(4, 0))

    result = {"done": False}

    def on_save():
        username = fields["username"].get().strip()
        password = fields["password"].get()
        if not username or not password:
            err_var.set("Please fill in all fields.")
            return
        cfg = configparser.ConfigParser()
        cfg["general"] = {"username": username, "password": password}
        cfg["osc"]     = {"host": OSC_HOST, "port": str(OSC_PORT)}
        with open(_CONFIG_PATH, "w") as f:
            cfg.write(f)
        result["done"] = True
        root.destroy()

    _tk.Button(root, text="Save & Retry", command=on_save,
               bg="#c084fc", fg="#0a0a0c",
               font=("Segoe UI", 10, "bold"),
               relief="flat", pady=8, cursor="hand2").pack(pady=16, padx=40, fill="x")

    root.bind("<Return>", lambda e: on_save())
    root.mainloop()
    return result["done"]


def get_token() -> str | None:
    """Login and return user token. Shows popup on auth failure."""
    global _user_token, USERNAME, PASSWORD
    try:
        import urllib.request
        import urllib.error
        data = json.dumps({"username": USERNAME, "password": PASSWORD}).encode()
        req  = urllib.request.Request(
            LOGIN_URL, data=data,
            headers={"Content-Type": "application/json", "User-Agent": f"ShockGateClient/{CURRENT_VERSION}"}
        )
        with urllib.request.urlopen(req, timeout=8) as r:
            resp = json.loads(r.read().decode())
        if resp.get("ok"):
            _user_token = resp["token"]
            log(f"[*] Logged in as {USERNAME}")
            return _user_token
        else:
            err = resp.get('error', 'unknown')
            log(f"[!] Login failed: {err}")
            # Show popup – user can correct credentials
            if _show_relogin_popup(err):
                # Reload config and retry once
                config.read(_CONFIG_PATH)
                USERNAME = config["general"].get("username", "")
                PASSWORD = config["general"].get("password", "")
                return get_token()
            return None
    except Exception as e:
        log(f"[!] Login error: {e}")
        return None

# ── WebSocket Loop ────────────────────────────────────────────────────────────
_gui: "ShockGateGUI | None" = None
_ws_loop: asyncio.AbstractEventLoop | None = None

async def ws_loop():
    global _user_token
    attempt = 0

    # Heartbeat task – only sends Collar=True when VRChat is reachable
    async def heartbeat():
        while True:
            await asyncio.sleep(5)
            if vrchat_osc_reachable():
                send_osc_heartbeat()

    # VRChat watchdog – updates GUI indicator every 5s
    async def watch_vrchat():
        last_status = None
        while True:
            await asyncio.sleep(5)
            try:
                status = get_vrchat_status()
                if status != last_status:
                    if _gui:
                        _gui.set_vrchat_status(status)
                    if status == "osc_on":
                        log("[+] VRChat OSC connected")
                    elif status == "osc_off":
                        log("[!] VRChat running – OSC disabled (enable via Action Menu)")
                    else:
                        log("[!] VRChat not running")
                    last_status = status
            except asyncio.CancelledError:
                return
            except Exception:
                pass

    hb_task  = asyncio.ensure_future(heartbeat())
    vrc_task = asyncio.ensure_future(watch_vrchat())

    while True:
        attempt += 1
        token = _user_token or get_token()
        if not token:
            log(f"[!] No token – retrying in {RECONNECT_DELAY}s...")
            if _gui:
                _gui.set_status(False, "Login failed")
            await asyncio.sleep(RECONNECT_DELAY)
            continue

        try:
            log(f"[*] Connecting to {WS_URL} (attempt #{attempt})")
            if _gui:
                _gui.set_status(False, "Connecting...")

            async with websockets.connect(WS_URL) as ws:
                # Authenticate (include version + hash so server can reject outdated clients)
                await ws.send(json.dumps({
                    "type":    "auth",
                    "token":   token,
                    "version": CURRENT_VERSION,
                    "hash":    _get_self_hash(),
                }))
                raw = await asyncio.wait_for(ws.recv(), timeout=8)
                msg = json.loads(raw)

                if msg.get("type") == "error":
                    err = msg.get("message", "")
                    log(f"[!] Auth rejected: {err}")
                    if "Unauthorized" in err:
                        _user_token = None  # Token expired, re-login next attempt
                    if "outdated" in err.lower() or "integrity" in err.lower():
                        log(f"[!] Client is outdated or modified – please reinstall")
                        if _gui:
                            _gui.set_status(False, "Client rejected – please reinstall")
                        return  # Don't reconnect
                    if _gui:
                        _gui.set_status(False, f"Auth failed: {err}")
                    await asyncio.sleep(RECONNECT_DELAY)
                    continue

                if msg.get("type") != "authenticated":
                    log(f"[!] Unexpected auth response: {msg}")
                    await asyncio.sleep(RECONNECT_DELAY)
                    continue

                attempt = 0
                log(f"[+] Connected! UserID: {msg.get('userId')}")
                if _gui:
                    _gui.set_status(True, f"Connected (Secure)")
                send_osc_heartbeat()  # immediate collar=True on connect

                # Main message loop
                async for raw in ws:
                    try:
                        cmd = json.loads(raw)
                    except Exception:
                        continue

                    ctype = cmd.get("type")

                    if ctype == "operate":
                        op        = int(cmd.get("op", 2))
                        intensity = int(cmd.get("intensity", 1))
                        duration  = int(cmd.get("duration",  1))
                        max_i     = int(cmd.get("maxIntensity", 100))
                        max_d     = int(cmd.get("maxDuration",  15))
                        op_name   = ["Shock", "Vibrate", "Beep"][op] if op in (0,1,2) else "?"
                        log(f"[>>] {op_name} | {intensity}% | {duration}s")
                        if _gui:
                            _gui.add_log(op_name, intensity, duration)
                        threading.Thread(
                            target=send_osc,
                            args=(op, intensity, duration, max_i, max_d),
                            daemon=True
                        ).start()

                    elif ctype == "ping":
                        await ws.send(json.dumps({"type": "pong"}))

        except websockets.ConnectionClosed as e:
            log(f"[!] Connection closed: {e}")
        except asyncio.TimeoutError:
            log("[!] Connection timeout")
        except Exception as e:
            log(f"[!] Connection error: {e}")

        if _gui:
            _gui.set_status(False, "Reconnecting...")
        log(f"    Reconnecting in {RECONNECT_DELAY}s...")
        await asyncio.sleep(RECONNECT_DELAY)

# ── GUI ───────────────────────────────────────────────────────────────────────

class ShockGateGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"ShockGate Client v{CURRENT_VERSION}")
        self.root.configure(bg="#0a0a0c")
        self.root.resizable(False, False)
        self.root.geometry("420x520")
        _set_icon(self.root)

        self._win_cfg = os.path.join(_DATA_DIR, "window.ini")
        try:
            if os.path.exists(self._win_cfg):
                self.root.geometry(open(self._win_cfg).read().strip())
        except Exception:
            pass

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        # Header
        header = tk.Frame(self.root, bg="#111115",
                          highlightthickness=1, highlightbackground="#2a1f3d")
        header.pack(fill="x")

        tk.Label(header, text="⚡", fg="#c084fc", bg="#111115",
                 font=("Segoe UI", 18)).pack(side="left", padx=(14, 4), pady=12)
        tk.Label(header, text="Shock", fg="#c084fc", bg="#111115",
                 font=("Segoe UI", 16, "bold")).pack(side="left")
        tk.Label(header, text="Gate Client", fg="#f0e8ff", bg="#111115",
                 font=("Segoe UI", 16)).pack(side="left")

        self._dot = tk.Label(header, text="●", fg="#374151", bg="#111115",
                             font=("Segoe UI", 10))
        self._dot.pack(side="right", padx=(0, 8))
        self._status_label = tk.Label(header, text="Connecting...",
                                      fg="#4b4560", bg="#111115",
                                      font=("Segoe UI", 9))
        self._status_label.pack(side="right", padx=(0, 4))

        # Info rows
        info_frame = tk.Frame(self.root, bg="#0e0e12",
                              highlightthickness=1, highlightbackground="#1e1825")
        info_frame.pack(fill="x")

        def info_row(label, value_var):
            row = tk.Frame(info_frame, bg="#0e0e12")
            row.pack(fill="x", padx=18, pady=3)
            tk.Label(row, text=label, fg="#4b4560", bg="#0e0e12",
                     font=("Segoe UI", 9), width=12, anchor="w").pack(side="left")
            tk.Label(row, textvariable=value_var, fg="#7c6f99", bg="#0e0e12",
                     font=("Segoe UI", 9), anchor="w").pack(side="left")

        self._var_user     = tk.StringVar(value=USERNAME)
        self._var_osc      = tk.StringVar(value=f"{OSC_HOST}:{OSC_PORT}")
        self._var_version  = tk.StringVar(value=f"v{CURRENT_VERSION}")

        info_row("User:", self._var_user)
        info_row("OSC →", self._var_osc)
        info_row("Version:", self._var_version)

        # VRChat status row
        vrc_row = tk.Frame(info_frame, bg="#0e0e12")
        vrc_row.pack(fill="x", padx=18, pady=3)
        tk.Label(vrc_row, text="VRChat:", fg="#4b4560", bg="#0e0e12",
                 font=("Segoe UI", 9), width=12, anchor="w").pack(side="left")
        self._vrc_dot = tk.Label(vrc_row, text="●", fg="#374151", bg="#0e0e12",
                                 font=("Segoe UI", 9))
        self._vrc_dot.pack(side="left", padx=(0, 4))
        self._vrc_label = tk.Label(vrc_row, text="Checking...", fg="#4b4560", bg="#0e0e12",
                                   font=("Segoe UI", 9), anchor="w")
        self._vrc_label.pack(side="left")

        sep = tk.Frame(self.root, bg="#1e1825", height=1)
        sep.pack(fill="x")

        # Activity log (Shock/Vibrate/Beep events)
        act_header = tk.Frame(self.root, bg="#0a0a0c")
        act_header.pack(fill="x", padx=18, pady=(10, 4))
        tk.Label(act_header, text="ACTIVITY LOG", fg="#4b4560", bg="#0a0a0c",
                 font=("Segoe UI", 9, "bold")).pack(side="left")
        self._log_count = tk.Label(act_header, text="0 entries", fg="#2a2235", bg="#0a0a0c",
                                   font=("Segoe UI", 9))
        self._log_count.pack(side="right")

        act_frame = tk.Frame(self.root, bg="#0a0a0c")
        act_frame.pack(fill="both", expand=True, padx=12, pady=(0, 4))

        self._act_text = tk.Text(
            act_frame, bg="#0e0e12", fg="#7c6f99",
            font=("Consolas", 9), relief="flat",
            state="disabled", wrap="none", height=8,
            highlightthickness=1, highlightbackground="#1e1825"
        )
        self._act_text.pack(fill="both", expand=True)
        self._act_text.tag_config("shock",   foreground="#f87171")
        self._act_text.tag_config("vibrate", foreground="#c084fc")
        self._act_text.tag_config("beep",    foreground="#fb923c")

        self._entry_count = 0

        # System log (connection status, errors)
        sys_header = tk.Frame(self.root, bg="#0a0a0c")
        sys_header.pack(fill="x", padx=18, pady=(6, 4))
        tk.Label(sys_header, text="SYSTEM LOG", fg="#2a2235", bg="#0a0a0c",
                 font=("Segoe UI", 9, "bold")).pack(side="left")

        sys_frame = tk.Frame(self.root, bg="#0a0a0c")
        sys_frame.pack(fill="x", padx=12, pady=(0, 4))

        self._sys_text = tk.Text(
            sys_frame, bg="#0a0a0c", fg="#4b4560",
            font=("Consolas", 8), relief="flat",
            state="disabled", wrap="word", height=7,
            highlightthickness=0,
        )
        self._sys_text.pack(fill="both", expand=True)
        self._sys_text.tag_config("error",   foreground="#f87171")
        self._sys_text.tag_config("success", foreground="#4ade80")
        self._sys_text.tag_config("info",    foreground="#4b4560")

        # Buttons
        btn_frame = tk.Frame(self.root, bg="#0a0a0c")
        btn_frame.pack(fill="x", padx=12, pady=(0, 12))

        tk.Button(btn_frame, text="⚙ Settings", command=self._open_settings,
                  bg="#111115", fg="#7c6f99",
                  font=("Segoe UI", 9), relief="flat",
                  padx=10, pady=5, cursor="hand2",
                  highlightthickness=1, highlightbackground="#2a2235").pack(side="left", padx=(0, 6))

        tk.Button(btn_frame, text="📋 Full Log", command=self._open_log_window,
                  bg="#111115", fg="#7c6f99",
                  font=("Segoe UI", 9), relief="flat",
                  padx=10, pady=5, cursor="hand2",
                  highlightthickness=1, highlightbackground="#2a2235").pack(side="left")

        # Register log callback
        _log_callbacks.append(self._on_log)

    def set_status(self, connected: bool, text: str = ""):
        def _update():
            if connected:
                self._dot.config(fg="#4ade80")
                self._status_label.config(fg="#4ade80", text=text or "Connected")
            else:
                self._dot.config(fg="#f87171" if "fail" in text.lower() or "error" in text.lower() else "#fb923c")
                self._status_label.config(fg="#7c6f99", text=text or "Disconnected")
        self.root.after(0, _update)

    def set_vrchat_status(self, status: str):
        def _update():
            if status == "osc_on":
                self._vrc_dot.config(fg="#4ade80")
                self._vrc_label.config(fg="#4ade80", text="Connected")
            elif status == "osc_off":
                self._vrc_dot.config(fg="#fb923c")
                self._vrc_label.config(fg="#fb923c", text="Running – OSC disabled")
            else:
                self._vrc_dot.config(fg="#f87171")
                self._vrc_label.config(fg="#f87171", text="Not running")
        self.root.after(0, _update)

    def add_log(self, op_name: str, intensity: int, duration: int):
        def _update():
            self._entry_count += 1
            self._log_count.config(text=f"{self._entry_count} entr{'y' if self._entry_count == 1 else 'ies'}")
            tag = op_name.lower()
            time_str = datetime.now().strftime("%H:%M:%S")
            line = f"{time_str}  {op_name:<8}  {intensity}%  ·  {duration}s\n"
            self._act_text.config(state="normal")
            self._act_text.insert("1.0", line, tag)
            self._act_text.config(state="disabled")
        self.root.after(0, _update)

    def _on_log(self, line: str):
        def _update():
            # Skip operate lines – those go via add_log
            if "[>>]" in line or "[OSC]" in line:
                return
            tag = "error" if "[!]" in line else "success" if "[+]" in line else "info"
            self._sys_text.config(state="normal")
            self._sys_text.insert("end", line + "\n", tag)
            self._sys_text.see("end")
            self._sys_text.config(state="disabled")
        self.root.after(0, _update)

    def _open_settings(self):
        win = tk.Toplevel(self.root)
        win.title("Settings")
        win.geometry("400x320")
        win.configure(bg="#0a0a0c")
        win.resizable(False, False)
        win.grab_set()
        _set_icon(win)

        tk.Label(win, text="Settings", fg="#c084fc", bg="#0a0a0c",
                 font=("Segoe UI", 12, "bold")).pack(pady=(20, 4))
        tk.Label(win, text="Changes take effect after restart.",
                 fg="#4b4560", bg="#0a0a0c",
                 font=("Segoe UI", 9)).pack(pady=(0, 12))

        fields = {}
        for label, key, section, default in [
            ("Username",   "username", "general", USERNAME),
            ("Password",   "password", "general", PASSWORD),
            ("OSC Host",   "host",     "osc",     OSC_HOST),
            ("OSC Port",   "port",     "osc",     str(OSC_PORT)),
        ]:
            row = tk.Frame(win, bg="#0a0a0c")
            row.pack(fill="x", padx=30, pady=3)
            tk.Label(row, text=label + ":", fg="#7c6f99", bg="#0a0a0c",
                     font=("Segoe UI", 9), width=12, anchor="w").pack(side="left")
            var = tk.StringVar(value=default)
            show = "*" if key == "password" else ""
            tk.Entry(row, textvariable=var, show=show,
                     bg="#111115", fg="#f0e8ff", insertbackground="#c084fc",
                     font=("Segoe UI", 9), relief="flat",
                     highlightthickness=1, highlightcolor="#c084fc",
                     highlightbackground="#2a1f3d").pack(side="left", fill="x", expand=True, ipady=3)
            fields[(section, key)] = var

        def save():
            cfg = configparser.ConfigParser()
            cfg.read(_CONFIG_PATH)
            for (section, key), var in fields.items():
                if not cfg.has_section(section):
                    cfg.add_section(section)
                cfg[section][key] = var.get().strip()
            with open(_CONFIG_PATH, "w") as f:
                cfg.write(f)
            win.destroy()
            # Restart
            import subprocess
            python = sys.executable
            subprocess.Popen([python, os.path.abspath(__file__)])
            time.sleep(0.5)
            os._exit(0)

        tk.Button(win, text="Save & Restart", command=save,
                  bg="#c084fc", fg="#0a0a0c",
                  font=("Segoe UI", 10, "bold"),
                  relief="flat", pady=6, cursor="hand2").pack(pady=14, padx=30, fill="x")

    def _open_log_window(self):
        win = tk.Toplevel(self.root)
        win.title("Full Log")
        win.geometry("700x400")
        win.configure(bg="#0a0a0c")
        _set_icon(win)

        frame = tk.Frame(win, bg="#0a0a0c")
        frame.pack(fill="both", expand=True, padx=6, pady=6)
        sb = ttk.Scrollbar(frame)
        sb.pack(side="right", fill="y")
        text = tk.Text(frame, bg="#0e0e12", fg="#7c6f99",
                       font=("Consolas", 9), relief="flat",
                       yscrollcommand=sb.set, state="disabled", wrap="none")
        text.pack(fill="both", expand=True)
        sb.config(command=text.yview)
        text.tag_config("error",   foreground="#f87171")
        text.tag_config("success", foreground="#4ade80")
        text.tag_config("info",    foreground="#4b4560")

        text.config(state="normal")
        for line in _log_buffer:
            tag = "error" if "[!]" in line else "success" if "[+]" in line else "info"
            text.insert("end", line + "\n", tag)
        text.see("end")
        text.config(state="disabled")

        def on_log(line):
            text.config(state="normal")
            tag = "error" if "[!]" in line else "success" if "[+]" in line else "info"
            text.insert("end", line + "\n", tag)
            text.see("end")
            text.config(state="disabled")

        _log_callbacks.append(on_log)
        win.protocol("WM_DELETE_WINDOW", lambda: (_log_callbacks.remove(on_log), win.destroy()))

    def _on_close(self):
        try:
            open(self._win_cfg, "w").write(self.root.geometry())
        except Exception:
            pass
        send_osc_collar_off()
        os._exit(0)

    def run(self):
        self.root.mainloop()

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    global _gui, _ws_loop

    log("=" * 40)
    log(f"  ShockGate Client v{CURRENT_VERSION}")
    log("=" * 40)
    log(f"User:   {USERNAME}")
    log("Server: Connected (Secure)")
    log(f"OSC →   {OSC_HOST}:{OSC_PORT}")

    # Check for updates before anything else
    check_for_updates()

    # Start Discord Rich Presence
    start_discord_presence()

    # Pre-login
    get_token()

    # Network thread
    loop = asyncio.new_event_loop()
    _ws_loop = loop

    def run_loop():
        asyncio.set_event_loop(loop)
        loop.run_until_complete(ws_loop())

    threading.Thread(target=run_loop, daemon=True).start()

    # GUI
    _gui = ShockGateGUI()
    _gui.run()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        send_osc_collar_off()
        log("Stopped.")
    except Exception as e:
        send_osc_collar_off()
        log(f"[!] Fatal: {e}")
