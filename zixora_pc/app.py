"""zixora VPN for Windows — tkinter UI (v0.1 scaffold).

Screens: Home / Servers / Settings (bottom tab bar, like Android).
- Home: logo (aspect preserved), big Connect button, status,
  live up/down + elapsed, subscription card (days-left + traffic
  bar ONLY when the panel sends userinfo).
- Servers: list of names + protocol ONLY — addresses are never
  shown on rows. Tap a row to select it.
- Settings: sublink paste + fetch, TUN/system-proxy toggle,
  auto-connect toggle, support contact @ZixoracustomerserviceBot.

No fake state: if not connected, traffic is 0 and elapsed is 0.
If the core binary is missing, Connect shows the error, it does
not pretend to connect.
"""

import os
import sys
import tkinter as tk
from tkinter import messagebox, ttk

from . import branding, config as config_mod
from .core import CoreManager, fetch_sublink, is_admin
from .subscription import days_left, format_bytes, parse_userinfo, traffic_usage


def resource_path(rel):
    """Resolve a bundled file both in source runs and PyInstaller."""
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return os.path.join(base, rel)
    # Source run: repo root is the parent of the zixora_pc package.
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(root, rel)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Zixora VPN")
        self.geometry("420x640")
        self.configure(bg=branding.NAVY)
        self.resizable(False, False)
        self.cfg = config_mod.load()
        self.core = CoreManager()
        self.servers = []
        self.userinfo = {}
        self.selected = None
        self._build()
        # Closing the window must disconnect first, or the system
        # proxy would be left pointing at a dead local port.
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._tick()

    def _on_close(self):
        try:
            self.core.stop()
        except Exception:
            pass
        self.destroy()

    # ---------- layout ----------
    def _build(self):
        self.logo_label = tk.Label(self, bg=branding.NAVY)
        self.logo_label.pack(pady=(12, 4))
        self._load_logo()
        tk.Label(self, text="Zixora VPN", font=("Segoe UI", 20, "bold"),
                 fg=branding.WHITE, bg=branding.NAVY).pack()

        self.pages = {}
        for name in ("Home", "Servers", "Settings"):
            frame = tk.Frame(self, bg=branding.NAVY)
            self.pages[name] = frame
        self._build_home()
        self._build_servers()
        self._build_settings()

        nav = tk.Frame(self, bg=branding.PRIMARY)
        nav.pack(side="bottom", fill="x")
        for name in ("Home", "Servers", "Settings"):
            btn = tk.Button(nav, text=name, bg=branding.PRIMARY,
                            fg=branding.WHITE, relief="flat",
                            font=("Segoe UI", 11, "bold"),
                            command=lambda n=name: self.show(n))
            btn.pack(side="left", expand=True, fill="x")
        self.show("Home")

    def _load_logo(self):
        """Show the Z logo preserving aspect ratio (never stretched).
        Tk PhotoImage subsample uses integer factors, which keep the
        ratio intact; we pick the factor that fits a 280x156 box."""
        try:
            path = resource_path(branding.LOGO_PATH)
            img = tk.PhotoImage(file=path)
            factor = max(1, min(img.width() // 280 + 1,
                                img.height() // 156 + 1))
            img = img.subsample(factor, factor)
            self._logo_img = img  # keep a reference
            self.logo_label.configure(image=img)
        except Exception:
            self.logo_label.configure(text="Z", font=("Segoe UI", 40, "bold"),
                                      fg=branding.WHITE)

    def show(self, name):
        for frame in self.pages.values():
            frame.pack_forget()
        self.pages[name].pack(fill="both", expand=True, padx=16, pady=8)

    # ---------- Home ----------
    def _build_home(self):
        f = self.pages["Home"]
        self.status_label = tk.Label(f, text="Disconnected",
                                     font=("Segoe UI", 12),
                                     fg=branding.LIGHT, bg=branding.NAVY)
        self.status_label.pack(pady=6)
        self.connect_btn = tk.Button(
            f, text="CONNECT", font=("Segoe UI", 16, "bold"),
            bg=branding.PRIMARY, fg=branding.WHITE, relief="flat",
            width=20, height=2, command=self._toggle_connect)
        self.connect_btn.pack(pady=10)
        self.stats_label = tk.Label(f, text="↑ 0.0 B   ↓ 0.0 B   •   00:00",
                                    font=("Segoe UI", 11),
                                    fg=branding.WHITE, bg=branding.NAVY)
        self.stats_label.pack(pady=4)
        # Subscription card (hidden pieces stay hidden if no data).
        card = tk.Frame(f, bg=branding.GLASS, padx=12, pady=10)
        card.pack(fill="x", pady=12)
        self.sub_label = tk.Label(card, text="Subscription",
                                  font=("Segoe UI", 11, "bold"),
                                  fg=branding.NAVY, bg=branding.GLASS)
        self.sub_label.pack(anchor="w")
        self.days_label = tk.Label(card, text="",
                                   font=("Segoe UI", 11),
                                   fg=branding.NAVY, bg=branding.GLASS)
        self.days_label.pack(anchor="w")
        self.traffic_label = tk.Label(card, text="",
                                      font=("Segoe UI", 11),
                                      fg=branding.NAVY, bg=branding.GLASS)
        self.traffic_label.pack(anchor="w")
        self._refresh_sub_card()

    def _refresh_sub_card(self):
        d = days_left(self.userinfo)
        self.days_label.configure(
            text=f"Days left: {d}" if d is not None else "")
        t = traffic_usage(self.userinfo)
        if t:
            used, total, pct = t
            self.traffic_label.configure(
                text=f"Traffic: {format_bytes(used)} / {format_bytes(total)}"
                     f" ({pct:.0f}%)")
        else:
            self.traffic_label.configure(text="")

    # ---------- Servers ----------
    def _build_servers(self):
        f = self.pages["Servers"]
        tk.Label(f, text="Servers (addresses hidden)",
                 font=("Segoe UI", 11, "bold"),
                 fg=branding.WHITE, bg=branding.NAVY).pack(anchor="w")
        self.server_list = tk.Listbox(f, font=("Segoe UI", 11),
                                      bg=branding.WHITE, fg=branding.NAVY,
                                      height=18)
        self.server_list.pack(fill="both", expand=True, pady=8)
        self.server_list.bind("<<ListboxSelect>>", self._on_select_server)
        hint = tk.Label(f, text="Paste your sublink in Settings, then "
                        "pick a server here.",
                        font=("Segoe UI", 10),
                        fg=branding.LIGHT, bg=branding.NAVY, wraplength=360)
        hint.pack()

    def _on_select_server(self, _event):
        idx = self.server_list.curselection()
        if not idx or idx[0] >= len(self.servers):
            return
        self.selected = self.servers[idx[0]]
        self.cfg["selected_server"] = self.selected.name
        config_mod.save(self.cfg)
        self.status_label.configure(
            text=f"Selected: {self.selected.name} (not connected)")

    # ---------- Settings ----------
    def _build_settings(self):
        f = self.pages["Settings"]
        tk.Label(f, text="Subscription link",
                 font=("Segoe UI", 11, "bold"),
                 fg=branding.WHITE, bg=branding.NAVY).pack(anchor="w")
        self.sublink_entry = tk.Entry(f, font=("Segoe UI", 10), width=50)
        self.sublink_entry.insert(0, self.cfg.get("sublink", ""))
        self.sublink_entry.pack(fill="x", pady=4)
        tk.Button(f, text="Fetch servers", bg=branding.PRIMARY,
                  fg=branding.WHITE, relief="flat",
                  command=self._fetch_servers).pack(pady=4, anchor="w")
        self.fetch_label = tk.Label(f, text="", font=("Segoe UI", 10),
                                    fg=branding.LIGHT, bg=branding.NAVY)
        self.fetch_label.pack(anchor="w")
        self.tun_var = tk.BooleanVar(value=bool(self.cfg.get("tun_mode")))
        tk.Checkbutton(f, text="TUN mode (needs administrator)",
                       variable=self.tun_var, bg=branding.NAVY,
                       fg=branding.WHITE, selectcolor=branding.NAVY,
                       command=self._save_settings).pack(anchor="w", pady=6)
        self.auto_var = tk.BooleanVar(value=bool(self.cfg.get("auto_connect")))
        tk.Checkbutton(f, text="Auto-connect on start",
                       variable=self.auto_var, bg=branding.NAVY,
                       fg=branding.WHITE, selectcolor=branding.NAVY,
                       command=self._save_settings).pack(anchor="w")
        tk.Label(f, text="Support: @ZixoracustomerserviceBot (Telegram)",
                 font=("Segoe UI", 11, "bold"),
                 fg=branding.LIGHT, bg=branding.NAVY,
                 wraplength=360).pack(pady=16, anchor="w")
        if not is_admin():
            tk.Label(f, text="Note: not running as administrator — "
                     "TUN mode is unavailable in this session.",
                     font=("Segoe UI", 10), fg=branding.MID,
                     bg=branding.NAVY, wraplength=360).pack(anchor="w")

    def _save_settings(self):
        self.cfg["tun_mode"] = self.tun_var.get()
        self.cfg["auto_connect"] = self.auto_var.get()
        config_mod.save(self.cfg)

    def _fetch_servers(self):
        url = self.sublink_entry.get().strip()
        if not url:
            messagebox.showwarning("Sublink", "Paste your sublink first.")
            return
        try:
            servers, userinfo = fetch_sublink(url)
        except Exception as exc:
            messagebox.showerror("Fetch failed", str(exc))
            return
        self.servers = servers
        self.userinfo = parse_userinfo(userinfo)
        self.cfg["sublink"] = url
        config_mod.save(self.cfg)
        self.server_list.delete(0, tk.END)
        for srv in servers:
            # Name + protocol ONLY. Never the address.
            self.server_list.insert(tk.END, f"{srv.name}  •  {srv.protocol}")
        self.fetch_label.configure(text=f"{len(servers)} servers loaded.")
        self._refresh_sub_card()
        if servers and self.selected is None:
            self.selected = servers[0]
        self.show("Servers")

    # ---------- connect / tick ----------
    def _toggle_connect(self):
        if self.core.is_running():
            self.core.stop()
            self.connect_btn.configure(text="CONNECT")
            self.status_label.configure(text="Disconnected")
            return
        if self.selected is None:
            messagebox.showwarning("No server",
                                  "Pick a server on the Servers tab first.")
            self.show("Servers")
            return
        ok, msg = self.core.start(self.selected,
                                  tun_mode=self.tun_var.get())
        if not ok:
            messagebox.showerror("Connect failed", msg)
            return
        self.connect_btn.configure(text="DISCONNECT")
        self.status_label.configure(text=f"Connected: {self.selected.name}")

    def _tick(self):
        """1-second UI refresh: elapsed + traffic (real zeros until
        the core API is wired — never invented numbers)."""
        if self.core.is_running():
            up, down = self.core.traffic()
            el = self.core.elapsed()
            mm, ss = divmod(el, 60)
            self.stats_label.configure(
                text=f"↑ {format_bytes(up)}   ↓ {format_bytes(down)}"
                     f"   •   {mm:02d}:{ss:02d}")
        else:
            self.stats_label.configure(text="↑ 0.0 B   ↓ 0.0 B   •   00:00")
        self.after(1000, self._tick)


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
