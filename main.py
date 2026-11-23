import os
import random
import threading
from time import sleep
import tkinter as tk

from download import run_download
from texts import DOWNLOAD_TEXTS
from autoupdater import *
import shared
from shared import (
    FETCH_TITLE,
    APP_VERSION,
    SIZE_X,
    SIZE_Y,
    WIN95_FONT,
    WIN95_FONT_BOLD,
    WIN95_DEFAULT_BTN_TEXT,
    AVAILABLE_THEMES,
    load_config,
    save_config,
    resource_path,
    fix_fetch_taskbar,
)
from ui_widgets import PopupController, apply_theme_to_tree
from history_window import HistoryWindow
from fetch_tab import FetchTab
import converter_tab

class MediaDownloaderApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(FETCH_TITLE)
        self.root.overrideredirect(True)
        self.root.configure(bg=shared.WIN95_TEAL)

        ico_path = resource_path("icon.ico")
        if os.path.exists(ico_path):
            try:
                self.root.iconbitmap(ico_path)
            except Exception:
                pass

        self.config_data = load_config()
        self.presets = self.config_data.get("presets", {})
        default_dl = os.path.join(os.path.expanduser("~"), "Downloads")
        if not self.presets:
            self.presets = {"Downloads Folder": default_dl}

        saved_preset = self.config_data.get("selected_preset", "Presets")
        self.download_path = (
            self.presets[saved_preset] if saved_preset in self.presets else default_dl
        )

        self.cancel_event = threading.Event()
        self.is_downloading = False
        self.app_icon_img = None
        self.popups = PopupController(self.root)
        self.history_win = HistoryWindow(
            self.root,
            fallback_dir=lambda: self.download_path,
            on_use_url=lambda u: self.fetch_tab.set_url_text(u),
            on_log=self.log_status,
        )

        self._build_ui()
        self._center_window(SIZE_X, SIZE_Y)
        fix_fetch_taskbar(self.root)
        self.root.bind("<FocusIn>", self._check_clipboard_url)

    def _center_window(self, width, height):
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def _build_ui(self):
        bg = shared.WIN95_BG
        navy = shared.WIN95_NAVY
        text_fg = shared.WIN95_TEXT
        title_fg = shared.WIN95_TITLE_TEXT

        self.outer_frame = tk.Frame(self.root, bg=bg, bd=2, relief=tk.RAISED)
        self.outer_frame.pack(fill="both", expand=True, padx=2, pady=2)

        self.title_bar = tk.Frame(self.outer_frame, bg=navy, height=22)
        self.title_bar.pack(fill="x", side="top", padx=2, pady=2)

        ico_path = resource_path("icon.ico")
        png_path = resource_path("icon.png")
        if os.path.exists(png_path) or os.path.exists(ico_path):
            try:
                img = tk.PhotoImage(file=png_path if os.path.exists(png_path) else ico_path)
                self.app_icon_img = img.subsample(max(1, img.width() // 16))
                self.icon_label = tk.Label(self.title_bar, image=self.app_icon_img, bg=navy)
            except Exception:
                self.icon_label = tk.Label(self.title_bar, text="■", bg=navy, fg=shared.WIN95_WHITE, font=WIN95_FONT)
        else:
            self.icon_label = tk.Label(self.title_bar, text="■", bg=navy, fg=shared.WIN95_WHITE, font=WIN95_FONT)
        self.icon_label.pack(side="left", padx=(4, 2))

        self.title_label = tk.Label(self.title_bar, text=FETCH_TITLE, bg=navy, fg=title_fg, font=WIN95_FONT_BOLD)
        self.title_label.pack(side="left", padx=2)

        tk.Button(
            self.title_bar, text="✕", bg=bg, fg=text_fg, font=("MS Sans Serif", 7, "bold"),
            bd=1, relief=tk.RAISED, width=2, height=1, command=self.close_app, activebackground=bg, activeforeground=text_fg
        ).pack(side="right", padx=2, pady=2)

        for w in (self.title_bar, self.title_label, self.icon_label):
            w.bind("<ButtonPress-1>", self._start_move)
            w.bind("<B1-Motion>", self._on_move)

        # Bottom bar
        footer = tk.Frame(self.outer_frame, bg=bg, bd=1)
        footer.pack(fill="x", side="bottom", padx=2, pady=(0, 2))

        tk.Label(footer, text=f" v{APP_VERSION} ", bg=bg, fg=text_fg, font=("MS Sans Serif", 8), anchor="w").pack(side="left")
        tk.Button(
            footer, text="Check for Updates", bg=bg, fg=text_fg, bd=1, relief=tk.RAISED, font=("MS Sans Serif", 7),
            command=lambda: threading.Thread(target=self._check_updates_bg, daemon=True).start(), activebackground=bg, activeforeground=text_fg
        ).pack(side="left", padx=(4, 0))
        tk.Button(
            footer, text="History", bg=bg, fg=text_fg, bd=1, relief=tk.RAISED, font=("MS Sans Serif", 7),
            command=self.history_win.show, activebackground=bg, activeforeground=text_fg
        ).pack(side="left", padx=(4, 0))

        self.theme_var = tk.StringVar(value=self.config_data.get("selected_theme", "Windows 95"))
        tk.Button(
            footer, textvariable=self.theme_var, bg=bg, fg=text_fg, bd=1, relief=tk.RAISED, font=("MS Sans Serif", 7),
            command=self._toggle_theme_menu, activebackground=bg, activeforeground=text_fg
        ).pack(side="right", padx=2)
        tk.Label(footer, text="Theme:", bg=bg, fg=text_fg, font=("MS Sans Serif", 7)).pack(side="right", padx=(4, 0))

        # Main tab area
        body = tk.Frame(self.outer_frame, bg=bg)
        body.pack(fill="both", expand=True, padx=8, pady=8)

        tab_bar = tk.Frame(body, bg=bg)
        tab_bar.pack(fill="x", pady=(0, 4))

        self.fetch_tab_btn = tk.Button(
            tab_bar, text=" Fetch ", bg=bg, fg=text_fg, bd=2, relief=tk.SUNKEN, font=WIN95_FONT_BOLD,
            command=lambda: self.switch_tab("fetch"), activebackground=bg, activeforeground=text_fg
        )
        self.fetch_tab_btn.pack(side="left", padx=(0, 2))

        self.converter_tab_btn = tk.Button(
            tab_bar, text=" Unfinished Converter ", bg=bg, fg=text_fg, bd=2, relief=tk.RAISED, font=WIN95_FONT,
            command=lambda: self.switch_tab("converter"), activebackground=bg, activeforeground=text_fg
        )
        self.converter_tab_btn.pack(side="left")

        container = tk.Frame(body, bg=bg, bd=2, relief=tk.GROOVE)
        container.pack(fill="both", expand=True)

        self.fetch_tab = FetchTab(
            container,
            root_window=self.root,
            popups=self.popups,
            config_data=self.config_data,
            presets=self.presets,
            get_download_path=lambda: self.download_path,
            set_download_path=lambda p: setattr(self, "download_path", p),
            on_start_download=self.start_download_thread,
            on_cancel_download=self.cancel_download,
            on_log=self.log_status,
        )
        self.fetch_tab.pack(fill="both", expand=True, padx=4, pady=4)

        self.converter_frame = tk.Frame(container, bg=bg)
        self.converter_tab_obj = converter_tab.ConverterTab(self.converter_frame, lambda: self.download_path, self.log_status)

    def switch_tab(self, tab_name):
        self.fetch_tab.pack_forget()
        self.converter_frame.pack_forget()
        if tab_name == "fetch":
            self.fetch_tab_btn.config(relief=tk.SUNKEN, font=WIN95_FONT_BOLD)
            self.converter_tab_btn.config(relief=tk.RAISED, font=WIN95_FONT)
            self.fetch_tab.pack(fill="both", expand=True, padx=4, pady=4)
        else:
            self.converter_tab_btn.config(relief=tk.SUNKEN, font=WIN95_FONT_BOLD)
            self.fetch_tab_btn.config(relief=tk.RAISED, font=WIN95_FONT)
            self.converter_frame.pack(fill="both", expand=True, padx=4, pady=4)
        self.apply_theme(self.theme_var.get())

    def _toggle_theme_menu(self):
        options = list(AVAILABLE_THEMES.keys())
        w, h = 140, len(options) * 18 + 4
        x = self.root.winfo_rootx() + self.root.winfo_width() - w - 10
        y = self.root.winfo_rooty() + self.root.winfo_height() - h - 24

        def pick(name):
            self.theme_var.set(name)
            self.config_data["selected_theme"] = name
            save_config(self.config_data)
            self.apply_theme(name)

        self.popups.toggle(
            "theme", self.root, options, self.theme_var.get(), pick, fixed_geometry=f"{w}x{h}+{x}+{y}"
        )

    def apply_theme(self, theme_name):
        chosen = AVAILABLE_THEMES.get(theme_name, {})
        for k, v in chosen.items():
            if hasattr(shared, k):
                setattr(shared, k, v)
        self.root.configure(bg=shared.WIN95_TEAL)
        apply_theme_to_tree(
            self.root,
            title_label=self.title_label,
            title_bar=self.title_bar,
            white_containers=self.fetch_tab.white_containers(),
        )
        if hasattr(self, "history_win") and self.history_win:
            self.history_win.apply_theme()

    def _check_updates_bg(self):
        try:
            self.log_status("Checking for Fetch updates...")
            new_ver, download_url, asset_name = check_for_updates(APP_VERSION, GITHUB_OWNER, GITHUB_REPO)
            if new_ver:
                self.log_status(f"New Fetch version {new_ver} found! Downloading update...")
                download_and_execute_update(
                    download_url, asset_name,
                    progress_callback=lambda p: self.fetch_tab.update_progress(p, "-- KB/s", "--:--", True),
                    log_callback=self.log_status,
                )
            else:
                self.log_status("Fetch is up to date!")
        except Exception as e:
            self.log_status(f"Auto-update check failed: {e}")

    def _check_clipboard_url(self, event=None):
        if event and event.widget != self.root:
            return
        if not self.fetch_tab.auto_paste_var.get():
            return
        try:
            clip = self.root.clipboard_get().strip()
            if clip.startswith(("http://", "https://")) and not self.fetch_tab.url_entry.get():
                self.fetch_tab.set_url_text(clip)
                self.log_status("Auto-pasted URL from clipboard.")
        except Exception:
            pass

    def _start_move(self, event):
        self._x, self._y = event.x, event.y

    def _on_move(self, event):
        self.root.geometry(f"+{self.root.winfo_x() + (event.x - self._x)}+{self.root.winfo_y() + (event.y - self._y)}")

    def cancel_download(self):
        if self.is_downloading:
            self.cancel_event.set()
            self.fetch_tab.cancel_btn.config(state="disabled")
            self.log_status("Stopping download...")

    def log_status(self, text):
        self.root.after(0, self.fetch_tab.append_log, text)

    def start_download_thread(self):
        sources = self.fetch_tab.get_sources()
        if not sources:
            return

        self.cancel_event.clear()
        self.is_downloading = True
        self.fetch_tab.download_btn.config(text=random.choice(DOWNLOAD_TEXTS), state="disabled")
        self.fetch_tab.cancel_btn.config(state="normal")
        self.fetch_tab.clear_log()
        self.fetch_tab.update_progress(0, "-- KB/s", "--:--", True)

        fmt = self.fetch_tab.format_var.get()
        qual = self.fetch_tab.quality_var.get()
        c_mode = self.fetch_tab.cookie_mode_var.get()
        c_file = self.fetch_tab.cookie_file_var.get().strip()
        c_browser = self.fetch_tab.cookie_browser_var.get().strip()
        dump_thumb = self.fetch_tab.dump_thumbnail_var.get()

        def worker():
            ok = False
            try:
                ok = run_download(
                    sources,
                    fmt,
                    self.download_path,
                    self.log_status,
                    resource_path,
                    progress_callback=lambda pct, spd, eta: self.fetch_tab.update_progress(pct, spd, eta, self.is_downloading),
                    dump_thumbnail=dump_thumb,
                    quality_choice=qual,
                    cookie_mode=c_mode,
                    cookie_file=c_file,
                    cookie_browser=c_browser,
                    cancel_event=self.cancel_event,
                )
            finally:
                self.is_downloading = False
                self.root.after(0, self.fetch_tab.progress_frame.pack_forget)
                if ok:
                    self.print_art_final()
                    if self.fetch_tab.auto_clear_url_var.get():
                        self.root.after(0, self.fetch_tab.clear_url_input)
                    if self.fetch_tab.open_folder_after_var.get() and os.name == "nt":
                        try:
                            os.startfile(self.download_path)
                        except Exception as e:
                            self.log_status(f"Failed to open folder: {e}")

                self.root.after(0, lambda: self.fetch_tab.download_btn.config(text=WIN95_DEFAULT_BTN_TEXT, state="normal"))
                self.root.after(0, lambda: self.fetch_tab.cancel_btn.config(state="disabled"))

        threading.Thread(target=worker, daemon=True).start()

    def print_art_final(self):
        art_path = resource_path("art.txt")
        if not os.path.exists(art_path):
            self.log_status("Art file not found.")
            return
        with open(art_path, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
        self.log_status("")
        for line in lines:
            self.log_status(line)
            sleep(0.02)

    def close_app(self):
        self.cancel_event.set()
        self.root.destroy()

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    MediaDownloaderApp().run()