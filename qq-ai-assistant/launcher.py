#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
QQ AI Assistant - System Tray Launcher
"""

import os
import sys
import time
import json
import signal
import socket
import subprocess
import threading
import webbrowser
from pathlib import Path
from io import BytesIO
from typing import Optional

# ====== Config ======
PROJECT_DIR = Path(__file__).parent.resolve()
NAPCAT_DIR = PROJECT_DIR / "napcat" / "NapCat.44498.Shell"
CC_CONFIG = Path.home() / ".cc-connect" / "config.toml"
SESSION_DIR = Path.home() / ".cc-connect" / "sessions"
PORT_WS = 3001
PORT_WEB = 6099
BOT_QQ = os.environ.get("BOT_QQ", "你的QQ小号")

NAPCAT_EXE = NAPCAT_DIR / "NapCatWinBootMain.exe"
NAPCAT_VERSIONS_DIR = NAPCAT_DIR / "versions"
QRCODE_PATH = None  # type: Optional[Path]


def find_qrcode():
    """Find the qrcode.png path in NapCat versions directory."""
    if not NAPCAT_VERSIONS_DIR.exists():
        return None
    for d in NAPCAT_VERSIONS_DIR.iterdir():
        p = d / "resources" / "app" / "napcat" / "cache" / "qrcode.png"
        if p.exists():
            return p
    return None


def kill_process(name):
    """Kill a process by name."""
    try:
        subprocess.run(
            ["taskkill", "/F", "/IM", name],
            capture_output=True, timeout=5
        )
    except Exception:
        pass


def is_port_open(port):
    """Check if a TCP port is listening."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        result = s.connect_ex(('127.0.0.1', port))
        s.close()
        return result == 0
    except Exception:
        return False


def wait_port(port, timeout=120):
    """Wait for a port to become open."""
    start = time.time()
    while time.time() - start < timeout:
        if is_port_open(port):
            return True
        time.sleep(2)
    return False


def clean_sessions():
    """Delete old cc-connect session files."""
    if SESSION_DIR.exists():
        for f in SESSION_DIR.glob("*.json"):
            try:
                f.unlink()
            except Exception:
                pass


def clean_old_qr():
    """Delete old QR code image."""
    qr = find_qrcode()
    if qr and qr.exists():
        try:
            qr.unlink()
        except Exception:
            pass


# ====== Processes ======
napcat_proc = None  # type: Optional[subprocess.Popen]
cc_proc = None  # type: Optional[subprocess.Popen]


def start_napcat():
    """Start NapCat QQ. Capture stdout for chat monitoring."""
    global napcat_proc
    kill_process("NapCatWinBootMain.exe")
    kill_process("QQ.exe")
    time.sleep(2)
    clean_old_qr()
    clean_sessions()

    try:
        napcat_proc = subprocess.Popen(
            [str(NAPCAT_EXE)],
            cwd=str(NAPCAT_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        t = threading.Thread(target=_napcat_output, daemon=True)
        t.start()
        return True
    except Exception as e:
        print("[ERROR] Failed to start NapCat: {}".format(e))
        return False


def _napcat_output():
    """Read NapCat stdout and print chat messages in a clean format."""
    for line in iter(napcat_proc.stdout.readline, ""):
        if not line:
            break
        line = line.strip()
        # Only show user-facing messages: received, sent, login, errors
        if "接收" in line or "发送" in line:
            # NapCat format: 06-01 17:46:29 [info] 小小韩 | 接收 <- 私聊 (1196515210) 你好
            # Extract the useful part
            if "|" in line:
                parts = line.split("|", 1)
                content = parts[1].strip() if len(parts) > 1 else line
            else:
                content = line

            # Add readable prefix
            if "接收" in content:
                content = content.replace("接收 <-", "←")
            if "发送" in content:
                content = content.replace("发送 ->", "→")

            # Clean up the QQ number display
            content = content.replace("私聊", "")  # remove "私聊"
            content = content.replace("群聊", "")  # remove "群聊"
            content = " ".join(content.split())  # normalize spaces

            print(content)
        elif "下线" in line or "KickedOffLine" in line:
            print("[!] QQ kicked offline - need re-login")
        elif "登录" in line and ("成功" in line or "失败" in line):
            print("[NapCat] " + line.split("|")[-1].strip() if "|" in line else line)


CC_CMD = str(Path.home() / "AppData" / "Roaming" / "npm" / "cc-connect.cmd")


def _cc_output(proc):
    """Read cc-connect stdout and print important lines only."""
    for line in iter(proc.stdout.readline, ""):
        if not line:
            break
        line = line.strip()
        if not line:
            continue
        # Skip verbose technical lines
        if "turn complete" in line or "input_tokens" in line:
            continue
        if "session: loaded" in line or "cron:" in line:
            continue
        if "api server" in line or "acquired instance" in line:
            continue
        if "config loaded" in line:
            continue
        # Show meaningful status lines
        if any(kw in line for kw in [
            "connected to", "platform ready", "engine started",
            "is running", "failed", "error", "ERROR", "ERROR",
            "stopped", "restart"
        ]):
            # Extract just the msg part for cleaner display
            if "msg=" in line:
                idx = line.index("msg=")
                msg = line[idx + 4:].strip().strip('"')
                print("[cc] " + msg)
            else:
                print("[cc] " + line)


def start_cc_connect():
    """Start cc-connect with visible output."""
    global cc_proc
    try:
        kill_process("node.exe")
        time.sleep(1)
        cc_proc = subprocess.Popen(
            [CC_CMD, "--force"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        t = threading.Thread(
            target=_cc_output, args=(cc_proc,),
            daemon=True
        )
        t.start()
        return True
    except Exception as e:
        print("[ERROR] Failed to start cc-connect: {}".format(e))
        return False


def stop_all():
    """Stop all processes."""
    global napcat_proc, cc_proc
    if cc_proc:
        try:
            cc_proc.terminate()
        except Exception:
            pass
        cc_proc = None
    kill_process("cc-connect.exe")
    time.sleep(1)
    if napcat_proc:
        try:
            napcat_proc.terminate()
        except Exception:
            pass
        napcat_proc = None
    kill_process("NapCatWinBootMain.exe")
    kill_process("QQ.exe")


def show_qrcode_in_terminal():
    """Display QR code and open the PNG image."""
    qr = find_qrcode()
    if not qr or not qr.exists():
        print("[!] No QR code found yet. Please wait...")
        return

    # Open the PNG image with default viewer - this is scannable
    try:
        os.startfile(str(qr))
        print("[QR] Opened QR code image for scanning")
    except Exception as e:
        print("[!] Cant open QR image: {}".format(e))
        print("[!] Open manually: " + str(qr))

    # Also print ASCII art version as fallback
    try:
        from PIL import Image
        img = Image.open(qr)
        img = img.resize((50, 25), Image.NEAREST)
        img = img.convert('L')

        chars = "█▓▒░ "
        result = []
        for y in range(img.height):
            line = ""
            for x in range(img.width):
                pixel = img.getpixel((x, y))
                idx = int(pixel / 256 * len(chars))
                line += chars[min(idx, len(chars) - 1)]
            result.append(line)

        print("\n" + "=" * 50)
        print("  Scan the QR image that just opened")
        print("  Bot QQ: " + BOT_QQ)
        print("=" * 50 + "\n")
        for line in result:
            print(line)
        print("\n" + "=" * 50 + "\n")
    except Exception:
        pass


# ====== Tray Icon ======
def create_tray_icon():
    """Create a simple tray icon."""
    from PIL import Image, ImageDraw

    img = Image.new('RGBA', (64, 64), color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Head
    draw.ellipse([8, 4, 56, 52], fill=(30, 40, 60), outline=(80, 180, 240))
    # Eyes
    draw.ellipse([18, 18, 28, 30], fill=(80, 200, 255))
    draw.ellipse([36, 18, 46, 30], fill=(80, 200, 255))
    # Eye glow
    draw.ellipse([22, 20, 25, 24], fill="white")
    draw.ellipse([40, 20, 43, 24], fill="white")
    # Mouth
    draw.arc([24, 34, 40, 46], 0, -180, fill=(80, 180, 240), width=2)
    # Antenna
    draw.line([32, 4, 32, 0], fill=(80, 200, 255), width=2)
    draw.ellipse([27, -2, 37, 8], fill=(80, 200, 255))

    return img


# ====== State ======
state = {
    "running": False,
    "napcat_ready": False,
    "cc_ready": False,
    "qr_shown": False,
}


def cc_running():
    """Check if cc-connect is running."""
    try:
        r = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq node.exe"],
            capture_output=True, text=True, timeout=3
        )
        # There might be multiple node.exe processes;
        # cc-connect holds a .lock file when running
        lock = Path.home() / ".cc-connect" / ".config.toml.lock"
        return lock.exists()
    except Exception:
        return False


def launch():
    """Full launch sequence."""
    global state
    state["running"] = True
    state["qr_shown"] = False

    def run():
        if not start_napcat():
            print("[ERROR] NapCat failed to start")
            state["running"] = False
            return

        qr_shown = False
        start_time = time.time()

        while time.time() - start_time < 120:
            if is_port_open(PORT_WS):
                state["napcat_ready"] = True
                break

            if not qr_shown:
                time.sleep(8)
                qr = find_qrcode()
                if qr and qr.exists():
                    print("\n" + "!" * 50)
                    print("  Auto-login failed - Need QR scan!")
                    print("!" * 50)
                    show_qrcode_in_terminal()
                    qr_shown = True
                    state["qr_shown"] = True

            time.sleep(2)

        if not state["napcat_ready"]:
            print("[ERROR] Timeout waiting for QQ login")
            state["running"] = False
            return

        if start_cc_connect():
            state["cc_ready"] = True
            print("[OK] QQ AI is ONLINE!")
        else:
            print("[ERROR] cc-connect failed to start")
            state["running"] = False

    t = threading.Thread(target=run, daemon=True)
    t.start()


def restart():
    """Restart everything."""
    print("[*] Restarting...")
    stop_all()
    time.sleep(2)
    clean_sessions()
    clean_old_qr()
    launch()


# ====== Tray ======
def run_tray():
    """Main entry point."""
    import pystray as pt

    icon_img = create_tray_icon()

    def on_launch():
        launch()

    def on_restart():
        restart()

    def on_stop():
        stop_all()

    def on_qr():
        show_qrcode_in_terminal()

    def on_edit_persona():
        claude_md = PROJECT_DIR / "CLAUDE.md"
        if claude_md.exists():
            os.startfile(str(claude_md))
        else:
            print("[!] CLAUDE.md not found")

    def on_edit_config():
        p = str(Path.home() / ".cc-connect" / "config.toml")
        if os.path.exists(p):
            os.startfile(p)
        else:
            print("[!] config.toml not found")

    def on_open_dir():
        os.startfile(str(PROJECT_DIR))

    def on_exit():
        stop_all()
        tray_icon.stop()

    menu = pt.Menu(
        pt.MenuItem("Status: Starting...", None, enabled=False),
        pt.Menu.SEPARATOR,
        pt.MenuItem("Launch QQ AI", on_launch),
        pt.MenuItem("Restart QQ AI", on_restart),
        pt.MenuItem("Stop QQ AI", on_stop),
        pt.Menu.SEPARATOR,
        pt.MenuItem("Show QR Code", on_qr),
        pt.Menu.SEPARATOR,
        pt.MenuItem("Edit Persona (CLAUDE.md)", on_edit_persona),
        pt.MenuItem("Edit Config (config.toml)", on_edit_config),
        pt.MenuItem("Open Project Folder", on_open_dir),
        pt.Menu.SEPARATOR,
        pt.MenuItem("Exit", on_exit),
    )

    tray_icon = pt.Icon("qq-ai", icon_img, "Xiao Bingbing - QQ AI", menu)

    def update_status():
        while tray_icon.visible:
            try:
                nc = is_port_open(PORT_WS)
                ccr = cc_running()
                if nc and ccr:
                    tray_icon.title = "Xiao Bingbing - Online"
                elif nc:
                    tray_icon.title = "Xiao Bingbing - QQ Ready"
                else:
                    tray_icon.title = "Xiao Bingbing - Offline"
            except Exception:
                pass
            time.sleep(5)

    threading.Thread(target=update_status, daemon=True).start()

    print("[*] Auto-launching QQ AI...")
    launch()

    print("\n" + "=" * 50)
    print("  Xiao Bingbing QQ AI Assistant")
    print("  Tray icon is in the taskbar")
    print("=" * 50)
    print("  Right-click tray icon: Launch / Stop / Edit")
    print("  QR code will show here if needed")
    print("=" * 50 + "\n")

    tray_icon.run()


if __name__ == "__main__":
    run_tray()
