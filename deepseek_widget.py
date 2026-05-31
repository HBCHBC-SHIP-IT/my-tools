#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepSeek 余额桌面挂件 — 终端风格 · 最小化版
双击任意位置最小化，双击小按钮恢复，始终置顶可拖拽
用 pythonw 运行无终端窗口
"""

import json
import os
import subprocess
import threading
from datetime import datetime
import tkinter as tk

CONFIG_FILE = os.path.expanduser("~/.deepseek_widget_config.json")
API_BASE = "https://api.deepseek.com"
PROXY    = "socks5://127.0.0.1:10808"

# ============================================================
#  终端配色
# ============================================================
BG    = "#0a0a0a"
DIM   = "#3a3a3a"
FG    = "#b0b0b0"
CYAN  = "#00d2ff"
GREEN = "#00e676"
YELLOW= "#ffd740"
RED   = "#ff5252"
WHITE = "#e8e8e8"
FONT  = ("Cascadia Code", 9)
FONT_BOLD = ("Cascadia Code", 9, "bold")


def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def api_call(endpoint):
    url = f"{API_BASE}{endpoint}"
    cfg = load_json(CONFIG_FILE, {})
    api_key = cfg.get("api_key", "")
    cmd = [
        "curl", "-s", "-x", PROXY,
        "--connect-timeout", "10", "--max-time", "20",
        "-H", f"Authorization: Bearer {api_key}",
        url,
    ]
    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=25,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    stdout = result.stdout.strip()
    if result.returncode != 0 or not stdout:
        raise Exception("connection refused")
    data = json.loads(stdout)
    if "error" in data:
        raise Exception(data["error"].get("message", "api error"))
    return data


class TerminalWidget:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("deepseek-monitor")
        self.root.configure(bg=BG)
        self.root.attributes("-topmost", True)
        self.root.overrideredirect(True)
        self.root.resizable(False, False)

        self.api_key = load_json(CONFIG_FILE, {}).get("api_key", "")
        self.prev_balance = None
        self.drag_x = 0
        self.drag_y = 0

        self.full_win = None
        self.mini_win = None
        self.is_minimized = False

        self.build_full_ui()
        self.refresh_data()

    # ============================================================
    #  UI
    # ============================================================
    def build_full_ui(self):
        self.root.geometry("280x280")
        ws = self.root.winfo_screenwidth()
        ha = self.root.winfo_screenheight() - 48
        self.root.geometry(f"+{ws - 300}+{ha - 288}")

        outer = tk.Frame(self.root, bg=DIM, bd=0)
        outer.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        inner = tk.Frame(outer, bg=BG, bd=0)
        inner.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        # 标题栏
        bar = tk.Frame(inner, bg=BG, height=28)
        bar.pack(fill=tk.X)
        bar.pack_propagate(False)

        dots = tk.Frame(bar, bg=BG)
        dots.pack(side=tk.LEFT, padx=8)
        for c in [RED, YELLOW, GREEN]:
            d = tk.Label(dots, text="●", bg=BG, fg=c, font=("Consolas", 7))
            d.pack(side=tk.LEFT, padx=2)

        tk.Label(bar, text="deepseek-monitor", bg=BG, fg=DIM,
                 font=FONT).pack(side=tk.LEFT, padx=12)

        set_btn = tk.Label(bar, text="⚙", bg=BG, fg=DIM, font=FONT)
        set_btn.pack(side=tk.RIGHT, padx=4)
        set_btn.bind("<Button-1>", lambda e: self.open_settings())
        set_btn.bind("<Double-Button-1>", lambda e: "break")
        set_btn.bind("<Enter>", lambda e, b=set_btn: b.config(fg=WHITE))
        set_btn.bind("<Leave>", lambda e, b=set_btn: b.config(fg=DIM))

        tk.Frame(inner, bg=DIM, height=1).pack(fill=tk.X, padx=6)

        # 内容
        body = tk.Frame(inner, bg=BG)
        body.pack(fill=tk.BOTH, expand=True, padx=14, pady=(10, 6))

        # $ balance
        line1 = tk.Frame(body, bg=BG)
        line1.pack(fill=tk.X)
        tk.Label(line1, text="$", bg=BG, fg=GREEN, font=FONT_BOLD).pack(side=tk.LEFT)
        tk.Label(line1, text=" balance", bg=BG, fg=WHITE, font=FONT_BOLD).pack(side=tk.LEFT)

        self.balance_label = tk.Label(body, text="...", bg=BG, fg=GREEN,
                                      font=("Cascadia Code", 28, "bold"))
        self.balance_label.pack(anchor=tk.W, pady=(2, 0))

        self.delta_label = tk.Label(body, text="", bg=BG, fg=DIM, font=FONT)
        self.delta_label.pack(anchor=tk.W, pady=(0, 12))

        # $ detail
        line2 = tk.Frame(body, bg=BG)
        line2.pack(fill=tk.X)
        tk.Label(line2, text="$", bg=BG, fg=CYAN, font=FONT_BOLD).pack(side=tk.LEFT)
        tk.Label(line2, text=" detail", bg=BG, fg=WHITE, font=FONT_BOLD).pack(side=tk.LEFT)

        self.topped_label = tk.Label(body, text="", bg=BG, fg=CYAN, font=FONT)
        self.topped_label.pack(anchor=tk.W, pady=(4, 0))

        self.granted_label = tk.Label(body, text="", bg=BG, fg=YELLOW, font=FONT)
        self.granted_label.pack(anchor=tk.W)

        # 状态栏
        tk.Frame(inner, bg=DIM, height=1).pack(fill=tk.X, padx=6)

        bar2 = tk.Frame(inner, bg=BG, height=24)
        bar2.pack(fill=tk.X)
        bar2.pack_propagate(False)

        self.status_text = tk.Label(bar2, text="", bg=BG, fg=DIM, font=FONT)
        self.status_text.pack(side=tk.LEFT, padx=10)

        self.time_text = tk.Label(bar2, text="", bg=BG, fg=DIM, font=FONT)
        self.time_text.pack(side=tk.RIGHT, padx=10)

        self.err_label = tk.Label(body, text="", bg=BG, fg=RED, font=FONT,
                                  wraplength=230)

        self.full_win = self.root

        # 双击最小化
        for w in (self.root, outer, inner, bar, dots, body,
                  bar2, self.balance_label, self.delta_label,
                  self.topped_label, self.granted_label,
                  self.status_text, self.time_text):
            w.bind("<Double-Button-1>", lambda e: (self.minimize(), "break"))

        self.root.bind("<Button-1>", self.start_drag)
        self.root.bind("<B1-Motion>", self.do_drag)
        self.root.bind("<Button-3>", lambda e: self.open_settings())

    # ============================================================
    #  最小化
    # ============================================================
    def minimize(self):
        if self.is_minimized:
            return
        self.is_minimized = True
        fx, fy = self.root.winfo_x(), self.root.winfo_y()
        fw, fh = self.root.winfo_width(), self.root.winfo_height()
        self.root.withdraw()

        self.mini_win = tk.Toplevel(self.root)
        self.mini_win.title("ds")
        self.mini_win.configure(bg=BG)
        self.mini_win.attributes("-topmost", True)
        self.mini_win.overrideredirect(True)

        mo = tk.Frame(self.mini_win, bg=DIM, bd=0)
        mo.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        mi = tk.Frame(mo, bg=BG, bd=0)
        mi.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        row = tk.Frame(mi, bg=BG)
        row.pack(padx=10, pady=6)
        self.mini_dot = tk.Label(row, text="●", bg=BG, fg=GREEN,
                                 font=("Consolas", 7))
        self.mini_dot.pack(side=tk.LEFT, padx=(0, 6))
        self.mini_label = tk.Label(row, text=self.balance_label.cget("text"),
                                   bg=BG, fg=WHITE, font=FONT_BOLD)
        self.mini_label.pack(side=tk.LEFT)

        for w in (self.mini_win, mo, mi, row, self.mini_dot, self.mini_label):
            w.bind("<Button-1>", self.mini_start_drag)
            w.bind("<B1-Motion>", self.mini_do_drag)
            w.bind("<Double-Button-1>", self.restore_from_click)

        self.mini_win.update_idletasks()
        mw, mh = self.mini_win.winfo_reqwidth(), self.mini_win.winfo_reqheight()
        mx, my = self.clamp(self.mini_win, fx + fw - mw, fy + fh - mh)
        self.mini_win.geometry(f"+{mx}+{my}")
        self.mini_win.deiconify()

    def restore_from_click(self, event=None):
        if not self.is_minimized:
            return
        self.is_minimized = False
        if self.mini_win:
            mx, my = self.mini_win.winfo_x(), self.mini_win.winfo_y()
            mw, mh = self.mini_win.winfo_width(), self.mini_win.winfo_height()
            self.mini_win.destroy()
            self.mini_win = None
        x, y = self.clamp(self.root, mx + mw - 280, my + mh - 280)
        self.root.geometry(f"+{x}+{y}")
        self.root.deiconify()
        self.root.lift()

    def mini_start_drag(self, e):
        self.mini_dx = e.x_root - self.mini_win.winfo_x()
        self.mini_dy = e.y_root - self.mini_win.winfo_y()

    def mini_do_drag(self, e):
        x, y = self.clamp(self.mini_win, e.x_root - self.mini_dx,
                          e.y_root - self.mini_dy)
        self.mini_win.geometry(f"+{x}+{y}")

    def update_mini_label(self):
        if self.mini_win and not self.is_minimized is False:
            try:
                self.mini_label.config(text=self.balance_label.cget("text"))
                self.mini_dot.config(fg=self.balance_label.cget("fg"))
            except Exception:
                pass

    # ============================================================
    #  数据
    # ============================================================
    def refresh_data(self):
        cfg = load_json(CONFIG_FILE, {})
        self.api_key = cfg.get("api_key", "")

        if not self.api_key:
            self.balance_label.config(text="no key", fg=DIM)
            self.topped_label.config(text="topped_up  —")
            self.granted_label.config(text="granted    —")
            self.status_text.config(text="⬤ unconfigured")
            self.hide_err()
            self.update_mini_label()
        else:
            try:
                data = api_call("/user/balance")
                infos = data.get("balance_infos", [])
                total = sum(float(b.get("total_balance", 0)) for b in infos)
                topped = sum(float(b.get("topped_up_balance", 0)) for b in infos)
                granted = sum(float(b.get("granted_balance", 0)) for b in infos)

                c = GREEN if total > 10 else (YELLOW if total > 1 else RED)
                self.balance_label.config(text=f"¥{total:.2f}", fg=c)

                if self.prev_balance is not None:
                    diff = total - self.prev_balance
                    if abs(diff) > 0.0001:
                        sign, dc = ("↓", RED) if diff < 0 else ("↑", GREEN)
                        self.delta_label.config(
                            text=f"  {sign} ¥{abs(diff):.4f}", fg=dc)
                    else:
                        self.delta_label.config(text="  — unchanged", fg=DIM)

                self.prev_balance = total
                self.topped_label.config(text=f"topped_up  ¥{topped:.2f}")
                self.granted_label.config(text=f"granted    ¥{granted:.2f}")

                self.status_text.config(text="⬤ online", fg=GREEN)
                self.hide_err()
                self.update_mini_label()

            except Exception as e:
                self.balance_label.config(text="error", fg=RED)
                self.topped_label.config(text="topped_up  —")
                self.granted_label.config(text="granted    —")
                self.status_text.config(text="⬤ offline", fg=RED)
                self.show_err(f"[ERR] {e}")
                self.update_mini_label()

        self.time_text.config(text=datetime.now().strftime("%H:%M:%S"))
        self.root.after(60_000, lambda: threading.Thread(
            target=self.refresh_data, daemon=True).start())

    # ============================================================
    #  设置弹窗
    # ============================================================
    def open_settings(self):
        if hasattr(self, '_sw') and self._sw:
            try: self._sw.destroy()
            except Exception: pass

        w, h = 360, 160
        x = self.root.winfo_x() + (280 - w) // 2
        y = self.root.winfo_y() - h - 10
        if y < 0: y = self.root.winfo_y() + 290

        self._sw = tk.Toplevel(self.root)
        win = self._sw
        win.title("settings")
        win.geometry(f"{w}x{h}+{x}+{y}")
        win.configure(bg=BG)
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.focus_force()

        def close():
            win.destroy()
            self._sw = None

        win.bind("<FocusOut>", lambda e: close())
        win.bind("<Escape>", lambda e: close())

        of = tk.Frame(win, bg=DIM, bd=0)
        of.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        inf = tk.Frame(of, bg=BG, bd=0)
        inf.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        tr = tk.Frame(inf, bg=BG)
        tr.pack(fill=tk.X, padx=12, pady=(10, 4))
        tk.Label(tr, text="$ api_key", bg=BG, fg=GREEN, font=FONT_BOLD).pack(side=tk.LEFT)
        cls = tk.Label(tr, text="✕", bg=BG, fg=DIM, font=FONT)
        cls.pack(side=tk.RIGHT)
        cls.bind("<Button-1>", lambda e: close())
        cls.bind("<Enter>", lambda e, b=cls: b.config(fg=WHITE))
        cls.bind("<Leave>", lambda e, b=cls: b.config(fg=DIM))

        entry = tk.Entry(inf, show="•", width=42,
                         font=("Cascadia Code", 9),
                         bg="#111", fg=GREEN, insertbackground=GREEN,
                         bd=0, highlightthickness=1, highlightbackground=DIM)
        if self.api_key:
            entry.insert(0, self.api_key)
        entry.pack(padx=12, pady=(0, 8), ipady=3)
        entry.focus_set()

        def save():
            save_json(CONFIG_FILE, {"api_key": entry.get().strip()})
            self.api_key = entry.get().strip()
            close()
            threading.Thread(target=self.refresh_data, daemon=True).start()

        br = tk.Frame(inf, bg=BG)
        br.pack(fill=tk.X, padx=12)
        tk.Button(br, text="save & refresh", command=save,
                  bg=BG, fg=GREEN, font=FONT, bd=0,
                  activebackground="#111", activeforeground=GREEN,
                  cursor="hand2").pack(side=tk.LEFT)
        tk.Button(br, text="cancel", command=close,
                  bg=BG, fg=DIM, font=FONT, bd=0,
                  activebackground="#111", activeforeground=WHITE,
                  cursor="hand2").pack(side=tk.LEFT, padx=(8, 0))

        entry.bind("<Return>", lambda e: save())
        win.bind("<Return>", lambda e: save())

    # ============================================================
    #  工具
    # ============================================================
    @staticmethod
    def working_area(win):
        try:
            return (win.winfo_screenwidth(), win.winfo_screenheight() - 48)
        except Exception:
            return (win.winfo_screenwidth(), win.winfo_screenheight() - 48)

    def clamp(self, win, x, y):
        win.update_idletasks()
        mx, my = self.working_area(win)
        x = max(0, min(x, mx - win.winfo_width()))
        y = max(0, min(y, my - win.winfo_height()))
        return x, y

    def start_drag(self, e):
        if not self.is_minimized:
            self.drag_x = e.x_root - self.root.winfo_x()
            self.drag_y = e.y_root - self.root.winfo_y()

    def do_drag(self, e):
        if not self.is_minimized:
            x, y = self.clamp(self.root, e.x_root - self.drag_x,
                              e.y_root - self.drag_y)
            self.root.geometry(f"+{x}+{y}")

    def show_err(self, msg):
        self.err_label.config(text=msg)
        self.err_label.pack(anchor=tk.W, pady=(8, 0))

    def hide_err(self):
        self.err_label.pack_forget()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    TerminalWidget().run()
