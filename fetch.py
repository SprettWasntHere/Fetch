import os
import random
import threading
from time import sleep
import tkinter as tk
from tkinter import filedialog

from download import run_download
from texts import DOWNLOAD_TEXTS
from autoupdater import *
from shared import *

import muzzle

class MediaDownloaderApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(FETCH_TITLE)
        self.root.overrideredirect(True)
        self.root.configure(bg=WIN95_TEAL)

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

        saved_preset_name = self.config_data.get("selected_preset", "Presets")
        
        if saved_preset_name in self.presets:
            self.download_path = self.presets[saved_preset_name]
            initial_preset_display = saved_preset_name
        else:
            self.download_path = default_dl
            initial_preset_display = "Presets"

        saved_format = self.config_data.get("selected_format", "Video (MP4)")
        self.format_var = tk.StringVar(value=saved_format)

        self.preset_var = tk.StringVar(value="Presets")

        saved_auto_paste = self.config_data.get("auto_paste", False)
        self.auto_paste_var = tk.BooleanVar(value=saved_auto_paste)
        self.auto_clear_url_var = tk.BooleanVar(
            value=self.config_data.get("auto_clear_url", False)
        )

        self.app_icon_img = None
        self.text_index = 0
        self.dropdown_popup = None
        self.preset_popup = None
        self.theme_popup = None

        self._build_fetch_ui()
        self.preset_var.set(initial_preset_display)
        self.dir_entry.config(state="normal")
        self.dir_entry.delete(0, tk.END)
        self.dir_entry.insert(0, self.download_path)
        self.dir_entry.config(state="readonly")
        
        self._center_window(SIZE_X, SIZE_Y)
        fix_fetch_taskbar(self.root)
        self.root.bind("<FocusIn>", self._check_clipboard_url)
        self.cancel_event = threading.Event()

    def _check_app_updates_background(self):
        try:
            self.log_status("Checking for Fetch updates...")
            new_ver, download_url, asset_name = check_for_updates(
                APP_VERSION, GITHUB_OWNER, GITHUB_REPO
            )
            if new_ver:
                self.log_status(
                    f"New Fetch version {new_ver} found! Downloading update..."
                )
                download_and_execute_update(
                    download_url,
                    asset_name,
                    progress_callback=self.set_progress,
                    log_callback=self.log_status
                )

            else:
                self.log_status("Fetch is up to date!")

        except Exception as e:
            self.log_status(f"Auto-update check failed: {e}")
            self.set_progress(100)

    def _check_app_updates_button(self):
        threading.Thread(
            target=self._check_app_updates_background, daemon=True
        ).start()

    def _on_auto_paste_toggle(self):
        self.config_data["auto_paste"] = self.auto_paste_var.get()
        save_config(self.config_data)

    def _update_open_folder_after(self):
        self.config_data["open_folder_after"] = self.open_folder_after_var.get()
        save_config(self.config_data)

    def _update_auto_clear_url(self):
        self.config_data["auto_clear_url"] = self.auto_clear_url_var.get()
        save_config(self.config_data)

    def _check_clipboard_url(self, event=None):
        if event and event.widget != self.root:
            return
        if not self.auto_paste_var.get():
            return
        try:
            clipboard_content = self.root.clipboard_get().strip()
            if clipboard_content.startswith(("http://", "https://")) and not self.url_entry.get():
                self.url_entry.insert(0, clipboard_content)
                self.log_status(f"Auto-pasted URL from clipboard.")
        except Exception:
            pass

    def _center_window(self, width, height):
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def _build_fetch_ui(self):
        self.outer_frame = tk.Frame(self.root, bg=WIN95_BG, bd=2, relief=tk.RAISED)
        self.outer_frame.pack(fill="both", expand=True, padx=2, pady=2)

        self.title_bar = tk.Frame(self.outer_frame, bg=WIN95_NAVY, height=22)
        self.title_bar.pack(fill="x", side="top", padx=2, pady=2)

        ico_path = resource_path("icon.ico")
        png_path = resource_path("icon.png")

        if os.path.exists(png_path) or os.path.exists(ico_path):
            try:
                img_file = png_path if os.path.exists(png_path) else ico_path
                img = tk.PhotoImage(file=img_file)
                self.app_icon_img = img.subsample(max(1, img.width() // 16))
                self.icon_label = tk.Label(self.title_bar, image=self.app_icon_img, bg=WIN95_NAVY)
            except Exception:
                self.icon_label = tk.Label(self.title_bar, text="■", bg=WIN95_NAVY, fg=WIN95_WHITE, font=WIN95_FONT)
        else:
            self.icon_label = tk.Label(self.title_bar, text="■", bg=WIN95_NAVY, fg=WIN95_WHITE, font=WIN95_FONT)

        self.icon_label.pack(side="left", padx=(4, 2))

        self.title_label = tk.Label(self.title_bar, text=FETCH_TITLE, bg=WIN95_NAVY, fg=WIN95_TITLE_TEXT, font=WIN95_FONT_BOLD)
        self.title_label.pack(side="left", padx=2)

        self.close_btn = tk.Button(
            self.title_bar, text="✕", bg=WIN95_BG, fg=WIN95_TEXT, font=("MS Sans Serif", 7, "bold"), activebackground=WIN95_BG, activeforeground=WIN95_TEXT,
            bd=1, relief=tk.RAISED, width=2, height=1, command=self.close_app
        )
        self.close_btn.pack(side="right", padx=2, pady=2)

        for widget in (self.title_bar, self.title_label, self.icon_label):
            widget.bind("<ButtonPress-1>", self._start_move)
            widget.bind("<B1-Motion>", self._on_move)

        version_frame = tk.Frame(self.outer_frame, bg=WIN95_BG, bd=1)
        version_frame.pack(fill="x", side="bottom", padx=2, pady=(0, 2))

        self.version_label = tk.Label(version_frame, text=f" v{APP_VERSION} ", bg=WIN95_BG, fg=WIN95_TEXT, font=("MS Sans Serif", 8), anchor="w")
        self.version_label.pack(side="left")

        self.check_update_button = tk.Button(
            version_frame, text="Check for Updates", bg=WIN95_BG, fg=WIN95_TEXT, activebackground=WIN95_BG, activeforeground=WIN95_TEXT,
            bd=1, relief=tk.RAISED, font=("MS Sans Serif", 7), command=self._check_app_updates_button
        )
        self.check_update_button.pack(side="left", padx=(4, 0))

        current_theme_name = self.config_data.get("selected_theme", "Windows 95")
        self.theme_var = tk.StringVar(value=current_theme_name)
        
        theme_btn = tk.Button(
            version_frame, textvariable=self.theme_var, bg=WIN95_BG, fg=WIN95_TEXT, activebackground=WIN95_BG, activeforeground=WIN95_TEXT,
            bd=1, relief=tk.RAISED, font=("MS Sans Serif", 7), command=self._toggle_theme_dropdown
        )
        theme_btn.pack(side="right", padx=2)

        theme_label = tk.Label(version_frame, text="Theme:", bg=WIN95_BG, fg=WIN95_TEXT, font=("MS Sans Serif", 7))
        theme_label.pack(side="right", padx=(4, 0))

        content_area = tk.Frame(self.outer_frame, bg=WIN95_BG)
        content_area.pack(fill="both", expand=True, padx=10, pady=10)

        tab_header = tk.Frame(content_area, bg=WIN95_BG)
        tab_header.pack(fill="x", pady=(0, 4))

        self.fetch_tab_btn = tk.Button(tab_header, text=" Fetch ", bg=WIN95_BG, fg=WIN95_TEXT, activebackground=WIN95_BG, activeforeground=WIN95_TEXT, bd=2, relief=tk.SUNKEN, font=WIN95_FONT_BOLD, command=lambda: self.switch_tab("fetch"))
        self.fetch_tab_btn.pack(side="left", padx=(0, 2))

        self.muzzle_tab_btn = tk.Button(tab_header, text=" Muzzle ", bg=WIN95_BG, fg=WIN95_TEXT, activebackground=WIN95_BG, activeforeground=WIN95_TEXT, bd=2, relief=tk.RAISED, font=WIN95_FONT, command=lambda: self.switch_tab("muzzle"))
        self.muzzle_tab_btn.pack(side="left")

        self.tab_container = tk.Frame(content_area, bg=WIN95_BG, bd=2, relief=tk.GROOVE)
        self.tab_container.pack(fill="both", expand=True)

        self.fetch_frame = tk.Frame(self.tab_container, bg=WIN95_BG)
        self._build_fetch_tab_contents(self.fetch_frame)

        self.muzzle_frame = tk.Frame(self.tab_container, bg=WIN95_BG)
        self.muzzle_tab_obj = muzzle.MuzzleTab(self.muzzle_frame, lambda: self.download_path, self.log_status)

        self.fetch_frame.pack(fill="both", expand=True, padx=4, pady=4)

        content_area = tk.Frame(self.outer_frame, bg=WIN95_BG)
        content_area.pack(fill="both", expand=True, padx=10, pady=10)

    def switch_tab(self, tab_name):
        self.fetch_frame.pack_forget()
        self.muzzle_frame.pack_forget()

        if tab_name == "fetch":
            self.fetch_tab_btn.config(relief=tk.SUNKEN, font=WIN95_FONT_BOLD)
            self.muzzle_tab_btn.config(relief=tk.RAISED, font=WIN95_FONT)
            self.fetch_frame.pack(fill="both", expand=True, padx=4, pady=4)
        elif tab_name == "muzzle":
            self.muzzle_tab_btn.config(relief=tk.SUNKEN, font=WIN95_FONT_BOLD)
            self.fetch_tab_btn.config(relief=tk.RAISED, font=WIN95_FONT)
            self.muzzle_frame.pack(fill="both", expand=True, padx=4, pady=4)

    def _build_fetch_tab_contents(self, parent):
        form_frame = tk.Frame(parent, bg=WIN95_BG)
        form_frame.pack(fill="x", side="top")

        tk.Label(form_frame, text="Media URL:", bg=WIN95_BG, fg=WIN95_TEXT, font=WIN95_FONT).grid(row=0, column=0, sticky="w", pady=4)

        self.clear_url_button = tk.Button(
            form_frame, text="Clear Url", bg=WIN95_BG, fg=WIN95_TEXT, activebackground=WIN95_BG, activeforeground=WIN95_TEXT,
            bd=1, relief=tk.RAISED, font=("MS Sans Serif", 7), command=lambda: self.url_entry.delete(0, tk.END)
        )
        self.clear_url_button.grid(row=0, column=3, sticky="e", padx=(4, 0), pady=4)

        self.url_entry = tk.Entry(form_frame, bg=WIN95_WHITE, fg=WIN95_TEXT, bd=2, relief=tk.SUNKEN, font=WIN95_FONT)
        self.url_entry.grid(row=0, column=1, columnspan=2, sticky="ew", padx=(8, 0), pady=4)

        self.auto_paste_chk = tk.Checkbutton(
            form_frame, text="Auto-paste URL from clipboard", variable=self.auto_paste_var,
            bg=WIN95_BG, fg=WIN95_TEXT, activebackground=WIN95_BG, activeforeground=WIN95_TEXT,
            selectcolor=WIN95_WHITE, font=WIN95_FONT, command=self._on_auto_paste_toggle
        )
        self.auto_paste_chk.grid(row=1, column=1, columnspan=2, sticky="w", padx=(6, 0), pady=(0, 4))

        self.auto_clear_url_chk = tk.Checkbutton(
            form_frame, text="Auto-clear URL", variable=self.auto_clear_url_var,
            bg=WIN95_BG, fg=WIN95_TEXT, activebackground=WIN95_BG, activeforeground=WIN95_TEXT,
            selectcolor=WIN95_WHITE, font=WIN95_FONT, command=self._update_auto_clear_url
        )
        self.auto_clear_url_chk.grid(row=1, column=2, sticky="w", padx=(4, 0), pady=(0, 4))

        tk.Label(form_frame, text="Media Format:", bg=WIN95_BG, fg=WIN95_TEXT, font=WIN95_FONT).grid(row=2, column=0, sticky="w", pady=4)

        self.combo_container = tk.Frame(form_frame, bg=WIN95_WHITE, bd=2, relief=tk.SUNKEN)
        self.combo_container.grid(row=2, column=1, sticky="w", padx=(8, 0), pady=4)

        self.combo_label = tk.Label(
            self.combo_container, textvariable=self.format_var, bg=WIN95_WHITE, fg=WIN95_TEXT,
            font=WIN95_FONT, anchor="w", width=18, cursor="arrow"
        )
        self.combo_label.pack(side="left", fill="x", expand=True, padx=(2, 0))

        self.combo_btn = tk.Button(
            self.combo_container, text="▼", bg=WIN95_BG, fg=WIN95_TEXT, activebackground=WIN95_BG, activeforeground=WIN95_TEXT,
            font=("MS Sans Serif", 7), bd=1, relief=tk.RAISED, width=2, height=1,
            command=self._toggle_instant_dropdown
        )
        self.combo_btn.pack(side="right", fill="y")

        self.combo_label.bind("<Button-1>", lambda e: self._toggle_instant_dropdown())
        self.combo_container.bind("<Button-1>", lambda e: self._toggle_instant_dropdown())

        tk.Label(form_frame, text="Download Directory:", bg=WIN95_BG, fg=WIN95_TEXT, font=WIN95_FONT).grid(row=3, column=0, sticky="w", pady=4)

        self.dir_entry = tk.Entry(form_frame, bg=WIN95_WHITE, readonlybackground=WIN95_WHITE, fg=WIN95_TEXT, bd=2, relief=tk.SUNKEN, font=WIN95_FONT)
        self.dir_entry.insert(0, self.download_path)
        self.dir_entry.config(state="readonly")
        self.dir_entry.grid(row=3, column=1, columnspan=2, sticky="ew", padx=(8, 4), pady=4)

        self.open_folder_after_var = tk.BooleanVar(
            value=self.config_data.get("open_folder_after", False)
        )
        self.open_dir_chk = tk.Checkbutton(
            form_frame, text="Open folder after download", variable=self.open_folder_after_var,
            bg=WIN95_BG, fg=WIN95_TEXT, activebackground=WIN95_BG, activeforeground=WIN95_TEXT,
            selectcolor=WIN95_WHITE, font=WIN95_FONT, command=lambda: self._update_open_folder_after()
        )
        self.open_dir_chk.grid(row=4, column=1, sticky="w", padx=(4, 0), pady=4)

        browse_btn = tk.Button(form_frame, text="Browse...", bg=WIN95_BG, fg=WIN95_TEXT, activebackground=WIN95_BG, activeforeground=WIN95_TEXT, bd=2, relief=tk.RAISED, font=WIN95_FONT, command=self.browse_folder)
        browse_btn.grid(row=3, column=3, sticky="e", pady=4)

        tk.Label(form_frame, text="Folder Presets:", bg=WIN95_BG, fg=WIN95_TEXT, font=WIN95_FONT).grid(row=5, column=0, sticky="w", pady=4)

        self.preset_container = tk.Frame(form_frame, bg=WIN95_WHITE, bd=2, relief=tk.SUNKEN)
        self.preset_container.grid(row=5, column=1, columnspan=2, sticky="w", padx=(8, 4), pady=4)

        self.preset_label = tk.Label(
            self.preset_container, textvariable=self.preset_var, bg=WIN95_WHITE, fg=WIN95_TEXT,
            font=WIN95_FONT, anchor="w", width=18, cursor="arrow"
        )
        self.preset_label.pack(side="left", fill="x", expand=True, padx=(2, 0))

        self.preset_btn = tk.Button(
            self.preset_container, text="▼", bg=WIN95_BG, fg=WIN95_TEXT, activebackground=WIN95_BG, activeforeground=WIN95_TEXT,
            font=("MS Sans Serif", 7), bd=1, relief=tk.RAISED, width=2, height=1,
            command=self._toggle_preset_dropdown
        )
        self.preset_btn.pack(side="right", fill="y")

        self.preset_label.bind("<Button-1>", lambda e: self._toggle_preset_dropdown())
        self.preset_container.bind("<Button-1>", lambda e: self._toggle_preset_dropdown())

        preset_btn_frame = tk.Frame(form_frame, bg=WIN95_BG)
        preset_btn_frame.grid(row=5, column=3, sticky="e", pady=4)

        save_preset_btn = tk.Button(preset_btn_frame, text="Save", bg=WIN95_BG, fg=WIN95_TEXT, activebackground=WIN95_BG, activeforeground=WIN95_TEXT, bd=2, relief=tk.RAISED, font=WIN95_FONT, width=5, command=self.save_current_as_preset)
        save_preset_btn.pack(side="left", padx=(0, 2))

        delete_preset_btn = tk.Button(preset_btn_frame, text="Delete", bg=WIN95_BG, fg=WIN95_TEXT, activebackground=WIN95_BG, activeforeground=WIN95_TEXT, bd=2, relief=tk.RAISED, font=WIN95_FONT, width=5, command=self._ask_delete_confirmation)
        delete_preset_btn.pack(side="left")
        
        form_frame.columnconfigure(1, weight=1)

        self.download_btn = tk.Button(
            parent, text=WIN95_DEFAULT_BTN_TEXT, bg=WIN95_BG, fg=WIN95_TEXT,
            disabledforeground=WIN95_DISABLED, bd=2, relief=tk.RAISED, font=WIN95_FONT_BOLD, activebackground=WIN95_BG, activeforeground=WIN95_TEXT,
            pady=3, command=self.start_download_thread
        )
        self.download_btn.pack(fill="x", pady=(10, 8))

        self.progress_label = tk.Label(
            parent, text="0%", bg=WIN95_BG, fg=WIN95_TEXT, bd=2, font=WIN95_FONT, anchor="center"
        )

        self.status_box = tk.Text(
            parent, height=9, bg=WIN95_WHITE, fg=WIN95_TEXT, bd=2,
            relief=tk.SUNKEN, font=("Courier New", 9), state="disabled"
        )
        self.status_box.pack(fill="both", expand=True)

    def close_app(self):
        self.root.destroy()

    def _toggle_theme_dropdown(self):
        if self.theme_popup and self.theme_popup.winfo_exists():
            self.theme_popup.destroy()
            self.theme_popup = None
            return

        options = list(AVAILABLE_THEMES.keys())

        self.theme_popup = tk.Toplevel(self.root)
        self.theme_popup.overrideredirect(True)
        self.theme_popup.attributes("-topmost", True)

        x = self.root.winfo_rootx() + self.root.winfo_width() - 150
        y = self.root.winfo_rooty() + self.root.winfo_height() - 50
        width = 140
        height = len(options) * 18 + 4

        self.theme_popup.geometry(f"{width}x{height}+{x}+{y}")

        popup_frame = tk.Frame(self.theme_popup, bg=WIN95_BG, bd=2, relief=tk.RAISED)
        popup_frame.pack(fill="both", expand=True)

        listbox = tk.Listbox(
            popup_frame, bg=WIN95_WHITE, fg=WIN95_TEXT, selectbackground=WIN95_ACTIVE_BG,
            selectforeground=WIN95_ACTIVE_FG, font=WIN95_FONT, bd=0, highlightthickness=0, activestyle="none"
        )
        listbox.pack(fill="both", expand=True)

        for opt in options:
            listbox.insert(tk.END, opt)

        current = self.theme_var.get()
        if current in options:
            idx = options.index(current)
            listbox.select_set(idx)
            listbox.activate(idx)

        def on_select(evt=None):
            sel = listbox.curselection()
            if sel:
                selected_theme_name = options[sel[0]]
                self.theme_var.set(selected_theme_name)
                
                self.config_data["selected_theme"] = selected_theme_name
                save_config(self.config_data)
                
                self.apply_theme(selected_theme_name)

            if self.theme_popup:
                self.theme_popup.destroy()
                self.theme_popup = None

        listbox.bind("<ButtonRelease-1>", on_select)
        listbox.bind("<Return>", on_select)
        self.theme_popup.bind("<FocusOut>", lambda e: self._close_theme_delay())
        listbox.focus_set()

    def apply_theme(self, theme_name):
        global THEME, WIN95_BG, WIN95_TEAL, WIN95_NAVY, WIN95_WHITE, WIN95_TEXT, WIN95_DISABLED, WIN95_TITLE_TEXT, WIN95_ACTIVE_FG, WIN95_ACTIVE_BG
        
        if theme_name in AVAILABLE_THEMES:
            THEME = AVAILABLE_THEMES[theme_name]
        else:
            THEME = DEFAULT_THEME

        WIN95_BG = THEME["WIN95_BG"]
        WIN95_TEAL = THEME["WIN95_TEAL"]
        WIN95_NAVY = THEME["WIN95_NAVY"]
        WIN95_WHITE = THEME["WIN95_WHITE"]
        WIN95_TEXT = THEME["WIN95_TEXT"]
        WIN95_DISABLED = THEME["WIN95_DISABLED"]
        WIN95_TITLE_TEXT = THEME["WIN95_TITLE_TEXT"]
        WIN95_ACTIVE_FG = THEME["WIN95_ACTIVE_FG"]
        WIN95_ACTIVE_BG = THEME["WIN95_ACTIVE_BG"]

        self.root.configure(bg=WIN95_TEAL)

        def update_widget_colors(widget):
            w_type = widget.winfo_class()
            try:
                if w_type in ("Frame", "Toplevel", "LabelFrame", "Labelframe"):
                    widget.configure(bg=WIN95_BG)
                    if w_type in ("LabelFrame", "Labelframe"):
                        widget.configure(fg=WIN95_TEXT)
                elif w_type == "Label":
                    if widget == self.title_label or widget.master == self.title_bar:
                        widget.configure(bg=WIN95_NAVY, fg=WIN95_TITLE_TEXT)
                    else:
                        widget.configure(bg=WIN95_BG, fg=WIN95_TEXT)
                elif w_type == "Button":
                    widget.configure(bg=WIN95_BG, fg=WIN95_TEXT, activebackground=WIN95_BG, activeforeground=WIN95_TEXT)
                elif w_type == "Entry":
                    widget.configure(bg=WIN95_WHITE, fg=WIN95_TEXT, readonlybackground=WIN95_WHITE)
                elif w_type == "Text":
                    widget.configure(bg=WIN95_WHITE, fg=WIN95_TEXT)
                elif w_type == "Listbox":
                    widget.configure(bg=WIN95_WHITE, fg=WIN95_TEXT, selectbackground=WIN95_NAVY, selectforeground=WIN95_TEXT)
                elif w_type == "Checkbutton":
                    widget.configure(bg=WIN95_BG, fg=WIN95_TEXT, activebackground=WIN95_BG, activeforeground=WIN95_TEXT, selectcolor=WIN95_WHITE)
            except Exception:
                pass

            for child in widget.winfo_children():
                update_widget_colors(child)

        update_widget_colors(self.root)
        
        self.outer_frame.configure(bg=WIN95_BG)
        self.title_bar.configure(bg=WIN95_NAVY)
        self.title_label.configure(bg=WIN95_NAVY, fg=WIN95_TITLE_TEXT)
        self.combo_container.configure(bg=WIN95_WHITE)
        self.combo_label.configure(bg=WIN95_WHITE, fg=WIN95_TEXT)
        self.preset_container.configure(bg=WIN95_WHITE)
        self.preset_label.configure(bg=WIN95_WHITE, fg=WIN95_TEXT)
        self.auto_paste_chk.configure(bg=WIN95_BG, fg=WIN95_TEXT, selectcolor=WIN95_WHITE)

    def _close_theme_delay(self):
        if self.theme_popup:
            self.theme_popup.destroy()
            self.theme_popup = None

    def _toggle_instant_dropdown(self):
        if self.dropdown_popup and self.dropdown_popup.winfo_exists():
            self.dropdown_popup.destroy()
            self.dropdown_popup = None
            return

        options = ["Video (MP4)", "Audio (MP3)", "Audio (MP3 + Cover)", "Audio (WAV)"]

        self.dropdown_popup = tk.Toplevel(self.root)
        self.dropdown_popup.overrideredirect(True)
        self.dropdown_popup.attributes("-topmost", True)

        x = self.combo_container.winfo_rootx()
        y = self.combo_container.winfo_rooty() + self.combo_container.winfo_height()
        width = self.combo_container.winfo_width()
        height = len(options) * 18 + 4

        self.dropdown_popup.geometry(f"{width}x{height}+{x}+{y}")

        popup_frame = tk.Frame(self.dropdown_popup, bg=WIN95_BG, bd=2, relief=tk.RAISED)
        popup_frame.pack(fill="both", expand=True)

        listbox = tk.Listbox(
            popup_frame, bg=WIN95_WHITE, fg=WIN95_TEXT, selectbackground=WIN95_ACTIVE_BG,
            selectforeground=WIN95_ACTIVE_FG, font=WIN95_FONT, bd=0, highlightthickness=0, activestyle="none"
        )
        listbox.pack(fill="both", expand=True)

        for opt in options:
            listbox.insert(tk.END, opt)

        current = self.format_var.get()
        if current in options:
            idx = options.index(current)
            listbox.select_set(idx)
            listbox.activate(idx)

        def on_select(evt=None):
            sel = listbox.curselection()
            if sel:
                selected_format = options[sel[0]]
                self.format_var.set(selected_format)
                
                self.config_data["selected_format"] = selected_format
                save_config(self.config_data)
                
            if self.dropdown_popup:
                self.dropdown_popup.destroy()
                self.dropdown_popup = None

        listbox.bind("<ButtonRelease-1>", on_select)
        listbox.bind("<Return>", on_select)
        self.dropdown_popup.bind("<FocusOut>", lambda e: self._close_dropdown_delay())
        listbox.focus_set()

    def _close_dropdown_delay(self):
        if self.dropdown_popup:
            self.dropdown_popup.destroy()
            self.dropdown_popup = None

    def _close_preset_delay(self):
        if self.preset_popup:
            self.preset_popup.destroy()
            self.preset_popup = None

    def _start_move(self, event):
        self._x = event.x
        self._y = event.y

    def _on_move(self, event):
        x = self.root.winfo_x() + (event.x - self._x)
        y = self.root.winfo_y() + (event.y - self._y)
        self.root.geometry(f"+{x}+{y}")

    def browse_folder(self):
        selected_dir = filedialog.askdirectory(initialdir=self.download_path)
        if selected_dir:
            self.download_path = selected_dir
            self.dir_entry.config(state="normal")
            self.dir_entry.delete(0, tk.END)
            self.dir_entry.insert(0, self.download_path)
            self.dir_entry.config(state="readonly")
            self.preset_var.set("Presets")

            self.config_data["selected_preset"] = "Presets"
            save_config(self.config_data)

    def save_presets(self):
        self.config_data["presets"] = self.presets
        self.config_data["selected_preset"] = self.preset_var.get()
        save_config(self.config_data)

    def _toggle_preset_dropdown(self):
        if self.preset_popup and self.preset_popup.winfo_exists():
            self.preset_popup.destroy()
            self.preset_popup = None
            return

        if self.dropdown_popup and self.dropdown_popup.winfo_exists():
            self.dropdown_popup.destroy()
            self.dropdown_popup = None

        options = list(self.presets.keys())
        if not options:
            options = ["No presets found"]

        self.preset_popup = tk.Toplevel(self.root)
        self.preset_popup.overrideredirect(True)
        self.preset_popup.attributes("-topmost", True)

        x = self.preset_container.winfo_rootx()
        y = self.preset_container.winfo_rooty() + self.preset_container.winfo_height()
        width = self.preset_container.winfo_width()
        height = min(len(options), 5) * 18 + 4

        self.preset_popup.geometry(f"{width}x{height}+{x}+{y}")

        popup_frame = tk.Frame(self.preset_popup, bg=WIN95_BG, bd=2, relief=tk.RAISED)
        popup_frame.pack(fill="both", expand=True)

        listbox = tk.Listbox(
            popup_frame, bg=WIN95_WHITE, fg=WIN95_TEXT, selectbackground=WIN95_ACTIVE_BG,
            selectforeground=WIN95_ACTIVE_FG, font=WIN95_FONT, bd=0, highlightthickness=0, activestyle="none"
        )
        listbox.pack(fill="both", expand=True)

        for opt in options:
            listbox.insert(tk.END, opt)

        def on_select(evt=None):
            sel = listbox.curselection()
            if sel:
                selected_name = options[sel[0]]

                if selected_name in self.presets:
                    self.preset_var.set(selected_name)
                    path = self.presets[selected_name]

                    if os.path.exists(path):
                        self.download_path = path
                        self.dir_entry.config(state="normal")
                        self.dir_entry.delete(0, tk.END)
                        self.dir_entry.insert(0, self.download_path)
                        self.dir_entry.config(state="readonly")

                        self.save_presets()

            if self.preset_popup:
                self.preset_popup.destroy()
                self.preset_popup = None

        listbox.bind("<ButtonRelease-1>", on_select)
        listbox.bind("<Return>", on_select)
        self.preset_popup.bind("<FocusOut>", lambda e: self._close_preset_delay())
        listbox.focus_set()

    def _ask_preset_name(self):
        dialog = tk.Toplevel(self.root)
        dialog.overrideredirect(True)
        dialog.configure(bg=WIN95_TEAL)

        outer = tk.Frame(dialog, bg=WIN95_BG, bd=2, relief=tk.RAISED)
        outer.pack(fill="both", expand=True, padx=2, pady=2)

        title_bar = tk.Frame(outer, bg=WIN95_NAVY, height=22)
        title_bar.pack(fill="x", side="top", padx=2, pady=2)

        ico_path = resource_path("icon.ico")
        png_path = resource_path("icon.png")

        if os.path.exists(png_path) or os.path.exists(ico_path):
            try:
                img_file = png_path if os.path.exists(png_path) else ico_path
                img = tk.PhotoImage(file=img_file)
                icon_img = img.subsample(max(1, img.width() // 16))
                icon_lbl = tk.Label(title_bar, image=icon_img, bg=WIN95_NAVY)
                icon_lbl.image = icon_img
                icon_lbl.pack(side="left", padx=(4, 2))
            except Exception:
                pass

        title_lbl = tk.Label(title_bar, text="Save Preset", bg=WIN95_NAVY, fg=WIN95_TITLE_TEXT, font=WIN95_FONT_BOLD)
        title_lbl.pack(side="left", padx=2)

        result = [None]

        def close_dialog(val=None):
            result[0] = val
            dialog.destroy()

        close_btn = tk.Button(
            title_bar, text="✕", bg=WIN95_BG, fg=WIN95_TEXT, activebackground=WIN95_BG, activeforeground=WIN95_TEXT, font=("MS Sans Serif", 7, "bold"),
            bd=1, relief=tk.RAISED, width=2, height=1, command=lambda: close_dialog(None)
        )
        close_btn.pack(side="right", padx=2, pady=2)

        content = tk.Frame(outer, bg=WIN95_BG)
        content.pack(fill="both", expand=True, padx=12, pady=12)

        tk.Label(content, text="Preset Name:", bg=WIN95_BG, fg=WIN95_TEXT, font=WIN95_FONT).pack(anchor="w", pady=(0, 4))

        entry = tk.Entry(content, bg=WIN95_WHITE, fg=WIN95_TEXT, bd=2, relief=tk.SUNKEN, font=WIN95_FONT, width=25)
        entry.pack(fill="x", pady=(0, 12))
        entry.focus()

        btn_box = tk.Frame(content, bg=WIN95_BG)
        btn_box.pack(fill="x")

        def on_ok(e=None):
            val = entry.get().strip()
            if val:
                close_dialog(val)

        ok_btn = tk.Button(btn_box, text="OK", bg=WIN95_BG, fg=WIN95_TEXT, activebackground=WIN95_BG, activeforeground=WIN95_TEXT, bd=2, relief=tk.RAISED, font=WIN95_FONT, width=8, command=on_ok)
        ok_btn.pack(side="right", padx=(4, 0))

        cancel_btn = tk.Button(btn_box, text="Cancel", bg=WIN95_BG, fg=WIN95_TEXT, activebackground=WIN95_BG, activeforeground=WIN95_TEXT, bd=2, relief=tk.RAISED, font=WIN95_FONT, width=8, command=lambda: close_dialog(None))
        cancel_btn.pack(side="right")

        entry.bind("<Return>", on_ok)
        entry.bind("<Escape>", lambda e: close_dialog(None))

        dialog.update_idletasks()
        w = dialog.winfo_reqwidth()
        h = dialog.winfo_reqheight()
        x = self.root.winfo_rootx() + (self.root.winfo_width() // 2) - (w // 2)
        y = self.root.winfo_rooty() + (self.root.winfo_height() // 2) - (h // 2)
        dialog.geometry(f"+{x}+{y}")

        dialog.grab_set()
        self.root.wait_window(dialog)
        return result[0]

    def _ask_delete_confirmation(self):
        current_preset_name = self.preset_var.get()

        dialog = tk.Toplevel(self.root)
        dialog.overrideredirect(True)
        dialog.configure(bg=WIN95_TEAL)

        outer = tk.Frame(dialog, bg=WIN95_BG, bd=2, relief=tk.RAISED)
        outer.pack(fill="both", expand=True, padx=2, pady=2)

        title_bar = tk.Frame(outer, bg=WIN95_NAVY, height=22)
        title_bar.pack(fill="x", side="top", padx=2, pady=2)

        ico_path = resource_path("icon.ico")
        png_path = resource_path("icon.png")

        if os.path.exists(png_path) or os.path.exists(ico_path):
            try:
                img_file = png_path if os.path.exists(png_path) else ico_path
                img = tk.PhotoImage(file=img_file)
                icon_img = img.subsample(max(1, img.width() // 16))
                icon_lbl = tk.Label(title_bar, image=icon_img, bg=WIN95_NAVY)
                icon_lbl.image = icon_img
                icon_lbl.pack(side="left", padx=(4, 2))
            except Exception:
                pass

        title_lbl = tk.Label(title_bar, text="Delete Preset?", bg=WIN95_NAVY, fg=WIN95_TITLE_TEXT, font=WIN95_FONT_BOLD)
        title_lbl.pack(side="left", padx=2)

        result = [None]

        def close_dialog(val=None):
            result[0] = val
            dialog.destroy()

        text_lbl = tk.Label(outer, text=f"Are you sure you want to delete the preset '{current_preset_name}'?", bg=WIN95_BG, fg=WIN95_TEXT, font=WIN95_FONT, wraplength=300, justify="left")
        text_lbl.pack(fill="x", padx=12, pady=(12, 8))

        close_btn = tk.Button(
            title_bar, text="✕", bg=WIN95_BG, fg=WIN95_TEXT, activebackground=WIN95_BG, activeforeground=WIN95_TEXT, font=("MS Sans Serif", 7, "bold"),
            bd=1, relief=tk.RAISED, width=2, height=1, command=lambda: close_dialog(None)
        )
        close_btn.pack(side="right", padx=2, pady=2)

        content = tk.Frame(outer, bg=WIN95_BG)
        content.pack(fill="both", expand=True, padx=12, pady=12)

        btn_box = tk.Frame(content, bg=WIN95_BG)
        btn_box.pack(fill="x")

        def on_ok(e=None):
            if current_preset_name in self.presets:
                if len(self.presets) <= 1:
                    self.log_status("Cannot delete the last remaining preset.")
                    return
                
                del self.presets[current_preset_name]
                self.save_presets()
                self.preset_var.set("Presets")
                self.log_status(f"Deleted preset: {current_preset_name}")
                close_dialog(None)
            else:
                self.log_status("No valid preset selected to delete.")
                close_dialog(None)

        ok_btn = tk.Button(btn_box, text="OK", bg=WIN95_BG, fg=WIN95_TEXT, activebackground=WIN95_BG, activeforeground=WIN95_TEXT, bd=2, relief=tk.RAISED, font=WIN95_FONT, width=8, command=on_ok)
        ok_btn.pack(side="right", padx=(4, 0))

        cancel_btn = tk.Button(btn_box, text="Cancel", bg=WIN95_BG, fg=WIN95_TEXT, activebackground=WIN95_BG, activeforeground=WIN95_TEXT, bd=2, relief=tk.RAISED, font=WIN95_FONT, width=8, command=lambda: close_dialog(None))
        cancel_btn.pack(side="right")

        dialog.update_idletasks()
        w = dialog.winfo_reqwidth()
        h = dialog.winfo_reqheight()
        x = self.root.winfo_rootx() + (self.root.winfo_width() // 2) - (w // 2)
        y = self.root.winfo_rooty() + (self.root.winfo_height() // 2) - (h // 2)
        dialog.geometry(f"+{x}+{y}")

        dialog.grab_set()
        self.root.wait_window(dialog)
        return result[0]

    def save_current_as_preset(self):
        preset_name = self._ask_preset_name()
        if preset_name:
            name = preset_name.strip()
            self.presets[name] = self.download_path
            self.save_presets()
            self.preset_var.set(name)
            self.log_status(f"Saved preset: {name}")

    def log_status(self, text):
        if threading.current_thread() != threading.main_thread():
            self.root.after(0, self._append_log, text)
        else:
            self.root.after(0, lambda: self._append_log(text))

    def _append_log(self, text):
        self.status_box.config(state="normal")
        self.status_box.insert(tk.END, text + "\n")
        self.status_box.see(tk.END)
        self.status_box.config(state="disabled")

    def _update_button_style(self):
        self.text_index = random.choice(DOWNLOAD_TEXTS)
        self.download_btn.config(text=self.text_index, bg=WIN95_BG, fg=WIN95_TEXT, disabledforeground=WIN95_TEXT)

    def _reset_button_style(self):
        self.download_btn.config(text=WIN95_DEFAULT_BTN_TEXT, bg=WIN95_BG)

    def set_progress(self, percent):
        if threading.current_thread() != threading.main_thread():
            self.root.after(0, lambda: self.set_progress(percent))
            return

        clamped_percent = max(0, min(100, int(percent)))
        self.progress_label.config(text=f"{clamped_percent}%")

        if 0 < clamped_percent < 100:
            if not self.progress_label.winfo_ismapped():
                self.progress_label.pack(fill="x", pady=(0, 8), before=self.status_box)
        else:
            if clamped_percent >= 100 and self.progress_label.winfo_ismapped():
                self.progress_label.pack_forget()

    def start_download_thread(self):
        url = self.url_entry.get().strip()
        if not url:
            return

        self._update_button_style()
        self.download_btn.config(state="disabled")
        self.set_progress(0)
        
        self.status_box.config(state="normal")
        self.status_box.delete("1.0", tk.END)
        self.status_box.config(state="disabled")

        format_choice = self.format_var.get()
        
        def background_task():
            run_download(
                url, 
                format_choice, 
                self.download_path, 
                self.log_status, 
                resource_path, 
                progress_callback=self.set_progress
            )
            self.print_art_final()
            if self.auto_clear_url_var.get():
                self.root.after(0, lambda: self.url_entry.delete(0, tk.END))
            self.root.after(0, self._reset_button_style)
            self.root.after(0, lambda: self.download_btn.config(state="normal"))

            if self.open_folder_after_var.get():
                try:
                    if os.name == "nt":
                        os.startfile(self.download_path)
                except Exception as e:
                    self.log_status(f"Failed to open folder: {e}")

        threading.Thread(target=background_task, daemon=True).start()

    def print_art_final(self):
        art_path = resource_path("art.txt")

        if not os.path.exists(art_path):
            self.log_status("Art file not found.")
            return
        
        with open(art_path, "r", encoding="utf-8") as f:
            paw_print = f.read().splitlines()
        
        self.log_status("")
        for line in paw_print:
            self.log_status(line)
            sleep(0.02)

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = MediaDownloaderApp()
    app.run()