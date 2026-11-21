import os
import threading
import tkinter as tk
from tkinter import filedialog

import shared
from shared import WIN95_FONT, WIN95_FONT_BOLD, WIN95_DEFAULT_BTN_TEXT, save_config
from download import parse_urls_from_txt
from ui_widgets import ask_preset_name_dialog, ask_delete_preset_dialog

VIDEO_QUALITIES = ["Best", "2160p (4K)", "1440p (2K)", "1080p", "720p", "480p", "360p"]
AUDIO_QUALITIES = ["320k", "192k", "128k"]
COOKIE_MODES = ["None", "Cookies File", "Browser"]
COOKIE_BROWSERS = ["chrome", "edge", "firefox", "brave", "opera", "vivaldi"]

def _is_audio_format(fmt):
    return "MP3" in fmt or "WAV" in fmt

def _qualities_for_format(fmt):
    return AUDIO_QUALITIES if _is_audio_format(fmt) else VIDEO_QUALITIES

class FetchTab(tk.Frame):
    def __init__(
        self,
        parent,
        root_window,
        popups,
        config_data,
        presets,
        get_download_path,
        set_download_path,
        on_start_download,
        on_cancel_download,
        on_log,
    ):
        super().__init__(parent, bg=shared.WIN95_BG)
        self.root = root_window
        self.popups = popups
        self.config_data = config_data
        self.presets = presets
        self.get_download_path = get_download_path
        self.set_download_path = set_download_path
        self.on_start_download = on_start_download
        self.on_cancel_download = on_cancel_download
        self.log_status = on_log

        self.batch_urls = []

        raw_q_map = self.config_data.get("quality_by_format", {})
        self.quality_by_format = dict(raw_q_map) if isinstance(raw_q_map, dict) else {}

        saved_format = self.config_data.get("selected_format", "Video (MP4)")
        self.format_var = tk.StringVar(value=saved_format)

        legacy_q = self.config_data.get("selected_quality")
        if legacy_q and saved_format not in self.quality_by_format:
            valid_q = _qualities_for_format(saved_format)
            if legacy_q in valid_q:
                self.quality_by_format[saved_format] = legacy_q

        initial_q = self._get_saved_quality_for_format(saved_format)
        self.quality_var = tk.StringVar(value=initial_q)

        self.cookie_mode_var = tk.StringVar(value=self.config_data.get("cookie_mode", "None"))
        self.cookie_file_var = tk.StringVar(value=self.config_data.get("cookie_file", ""))
        self.cookie_browser_var = tk.StringVar(value=self.config_data.get("cookie_browser", "chrome"))

        saved_preset = self.config_data.get("selected_preset", "Presets")
        self.preset_var = tk.StringVar(
            value=saved_preset if saved_preset in self.presets else "Presets"
        )

        self.auto_paste_var = tk.BooleanVar(value=self.config_data.get("auto_paste", False))
        self.auto_clear_url_var = tk.BooleanVar(value=self.config_data.get("auto_clear_url", False))
        self.dump_thumbnail_var = tk.BooleanVar(value=self.config_data.get("dump_thumbnail_separately", False))
        self.open_folder_after_var = tk.BooleanVar(value=self.config_data.get("open_folder_after", False))

        self._build_ui()
        self.set_directory_display(self.get_download_path())
        self._refresh_cookie_controls()

    def _get_saved_quality_for_format(self, fmt):
        valid_q = _qualities_for_format(fmt)
        saved = self.quality_by_format.get(fmt)
        if saved in valid_q:
            return saved
        return valid_q[0]

    def white_containers(self):
        return (
            self.combo_container,
            self.quality_container,
            self.preset_container,
            self.cookie_mode_container,
            self.cookie_browser_container,
        )

    def _build_ui(self):
        bg = shared.WIN95_BG
        white = shared.WIN95_WHITE
        text_fg = shared.WIN95_TEXT

        form = tk.Frame(self, bg=bg)
        form.pack(fill="x", side="top")

        tk.Label(form, text="Media URL:", bg=bg, fg=text_fg, font=WIN95_FONT).grid(row=0, column=0, sticky="w", pady=2)
        self.url_entry = tk.Entry(form, bg=white, fg=text_fg, bd=2, relief=tk.SUNKEN, font=WIN95_FONT)
        self.url_entry.grid(row=0, column=1, columnspan=2, sticky="ew", padx=(8, 4), pady=2)

        url_btns = tk.Frame(form, bg=bg)
        url_btns.grid(row=0, column=3, sticky="e", pady=2)
        tk.Button(
            url_btns, text="Load .txt", bg=bg, fg=text_fg, bd=1, relief=tk.RAISED, font=("MS Sans Serif", 7),
            command=self._load_txt_urls, activebackground=bg, activeforeground=text_fg
        ).pack(side="left", padx=(0, 2))
        tk.Button(
            url_btns, text="Clear", bg=bg, fg=text_fg, bd=1, relief=tk.RAISED, font=("MS Sans Serif", 7),
            command=self.clear_url_input, activebackground=bg, activeforeground=text_fg
        ).pack(side="left")

        tk.Checkbutton(
            form, text="Auto-paste URL", variable=self.auto_paste_var, bg=bg, fg=text_fg,
            selectcolor=white, font=WIN95_FONT, command=lambda: self._save_flag("auto_paste", self.auto_paste_var), activebackground=bg, activeforeground=text_fg
        ).grid(row=1, column=1, sticky="w", padx=(4, 0), pady=(0, 2))

        tk.Checkbutton(
            form, text="Auto-clear URL after download", variable=self.auto_clear_url_var, bg=bg, fg=text_fg,
            selectcolor=white, font=WIN95_FONT, command=lambda: self._save_flag("auto_clear_url", self.auto_clear_url_var), activebackground=bg, activeforeground=text_fg
        ).grid(row=1, column=2, sticky="w", padx=(4, 0), pady=(0, 2))

        tk.Label(form, text="Format / Quality:", bg=bg, fg=text_fg, font=WIN95_FONT).grid(row=2, column=0, sticky="w", pady=2)

        self.combo_container = tk.Frame(form, bg=white, bd=2, relief=tk.SUNKEN)
        self.combo_container.grid(row=2, column=1, sticky="ew", padx=(8, 4), pady=2)
        self.combo_label = tk.Label(self.combo_container, textvariable=self.format_var, bg=white, fg=text_fg, font=WIN95_FONT, anchor="w")
        self.combo_label.pack(side="left", fill="x", expand=True, padx=(2, 0))
        tk.Button(
            self.combo_container, text="▼", bg=bg, fg=text_fg, font=("MS Sans Serif", 7), bd=1, relief=tk.RAISED, width=2, height=1,
            command=self._toggle_format_menu, activebackground=bg, activeforeground=text_fg
        ).pack(side="right", fill="y")
        self.combo_label.bind("<Button-1>", lambda e: self._toggle_format_menu())

        self.quality_container = tk.Frame(form, bg=white, bd=2, relief=tk.SUNKEN)
        self.quality_container.grid(row=2, column=2, columnspan=2, sticky="w", pady=2)
        self.quality_label = tk.Label(self.quality_container, textvariable=self.quality_var, bg=white, fg=text_fg, font=WIN95_FONT, anchor="w", width=12)
        self.quality_label.pack(side="left", fill="x", expand=True, padx=(2, 0))
        tk.Button(
            self.quality_container, text="▼", bg=bg, fg=text_fg, font=("MS Sans Serif", 7), bd=1, relief=tk.RAISED, width=2, height=1,
            command=self._toggle_quality_menu, activebackground=bg, activeforeground=text_fg
        ).pack(side="right", fill="y")
        self.quality_label.bind("<Button-1>", lambda e: self._toggle_quality_menu())

        tk.Checkbutton(
            form, text="Dump thumbnail", variable=self.dump_thumbnail_var, bg=bg, fg=text_fg,
            selectcolor=white, font=WIN95_FONT, command=lambda: self._save_flag("dump_thumbnail_separately", self.dump_thumbnail_var),
            activebackground=bg, activeforeground=text_fg
        ).grid(row=3, column=1, sticky="w", padx=(4, 0), pady=1)

        tk.Label(form, text="Directory:", bg=bg, fg=text_fg, font=WIN95_FONT).grid(row=4, column=0, sticky="w", pady=2)
        self.dir_entry = tk.Entry(form, bg=white, readonlybackground=white, fg=text_fg, bd=2, relief=tk.SUNKEN, font=WIN95_FONT)
        self.dir_entry.config(state="readonly")
        self.dir_entry.grid(row=4, column=1, columnspan=2, sticky="ew", padx=(8, 4), pady=2)
        tk.Button(
            form, text="Browse...", bg=bg, fg=text_fg, bd=2, relief=tk.RAISED, font=WIN95_FONT, command=self._browse_folder, activebackground=bg, activeforeground=text_fg
        ).grid(row=4, column=3, sticky="e", pady=2)

        tk.Checkbutton(
            form, text="Open folder after download", variable=self.open_folder_after_var, bg=bg, fg=text_fg,
            selectcolor=white, font=WIN95_FONT, command=lambda: self._save_flag("open_folder_after", self.open_folder_after_var), activebackground=bg, activeforeground=text_fg
        ).grid(row=5, column=1, columnspan=2, sticky="w", padx=(4, 0), pady=1)

        tk.Label(form, text="Folder Preset:", bg=bg, fg=text_fg, font=WIN95_FONT).grid(row=6, column=0, sticky="w", pady=2)
        self.preset_container = tk.Frame(form, bg=white, bd=2, relief=tk.SUNKEN)
        self.preset_container.grid(row=6, column=1, columnspan=2, sticky="ew", padx=(8, 4), pady=2)
        self.preset_label = tk.Label(self.preset_container, textvariable=self.preset_var, bg=white, fg=text_fg, font=WIN95_FONT, anchor="w")
        self.preset_label.pack(side="left", fill="x", expand=True, padx=(2, 0))
        tk.Button(
            self.preset_container, text="▼", bg=bg, fg=text_fg, font=("MS Sans Serif", 7), bd=1, relief=tk.RAISED, width=2, height=1,
            command=self._toggle_preset_menu, activebackground=bg, activeforeground=text_fg
        ).pack(side="right", fill="y")
        self.preset_label.bind("<Button-1>", lambda e: self._toggle_preset_menu())

        p_btns = tk.Frame(form, bg=bg)
        p_btns.grid(row=6, column=3, sticky="e", pady=2)
        tk.Button(p_btns, text="Save", bg=bg, fg=text_fg, activebackground=bg, activeforeground=text_fg, bd=2, relief=tk.RAISED, font=WIN95_FONT, width=5, command=self._save_preset).pack(side="left", padx=(0, 2))
        tk.Button(p_btns, text="Delete", bg=bg, fg=text_fg, activebackground=bg, activeforeground=text_fg, bd=2, relief=tk.RAISED, font=WIN95_FONT, width=5, command=self._delete_preset).pack(side="left")

        tk.Label(form, text="Cookies:", bg=bg, fg=text_fg, font=WIN95_FONT).grid(row=7, column=0, sticky="w", pady=2)
        self.cookie_mode_container = tk.Frame(form, bg=white, bd=2, relief=tk.SUNKEN)
        self.cookie_mode_container.grid(row=7, column=1, sticky="ew", padx=(8, 4), pady=2)
        self.cookie_mode_label = tk.Label(self.cookie_mode_container, textvariable=self.cookie_mode_var, bg=white, fg=text_fg, font=WIN95_FONT, anchor="w")
        self.cookie_mode_label.pack(side="left", fill="x", expand=True, padx=(2, 0))
        tk.Button(
            self.cookie_mode_container, text="▼", bg=bg, fg=text_fg, font=("MS Sans Serif", 7), bd=1, relief=tk.RAISED, width=2, height=1,
            command=self._toggle_cookie_mode_menu,
            activebackground=bg,
            activeforeground=text_fg
        ).pack(side="right", fill="y")
        self.cookie_mode_label.bind("<Button-1>", lambda e: self._toggle_cookie_mode_menu())

        self.cookie_file_entry = tk.Entry(form, textvariable=self.cookie_file_var, bg=white, fg=text_fg, bd=2, relief=tk.SUNKEN, font=WIN95_FONT)
        self.cookie_browse_btn = tk.Button(form, text="File...", bg=bg, fg=text_fg, activebackground=bg, activeforeground=text_fg, bd=1, relief=tk.RAISED, font=WIN95_FONT, command=self._browse_cookie_file)

        self.cookie_browser_container = tk.Frame(form, bg=white, bd=2, relief=tk.SUNKEN)
        self.cookie_browser_label = tk.Label(self.cookie_browser_container, textvariable=self.cookie_browser_var, bg=white, fg=text_fg, font=WIN95_FONT, anchor="w", width=12)
        self.cookie_browser_label.pack(side="left", fill="x", expand=True, padx=(2, 0))
        tk.Button(
            self.cookie_browser_container, text="▼", bg=bg, fg=text_fg, font=("MS Sans Serif", 7), bd=1, relief=tk.RAISED, width=2, height=1,
            command=self._toggle_cookie_browser_menu, activebackground=bg, activeforeground=text_fg
        ).pack(side="right", fill="y")
        self.cookie_browser_label.bind("<Button-1>", lambda e: self._toggle_cookie_browser_menu())

        form.columnconfigure(1, weight=1)
        form.columnconfigure(2, weight=1)

        actions = tk.Frame(self, bg=bg)
        actions.pack(fill="x", pady=(8, 4))

        self.download_btn = tk.Button(
            actions, text=WIN95_DEFAULT_BTN_TEXT, bg=bg, fg=text_fg, disabledforeground=shared.WIN95_DISABLED,
            bd=2, relief=tk.RAISED, font=WIN95_FONT_BOLD, pady=3, command=self.on_start_download,
        )
        self.download_btn.pack(side="left", fill="x", expand=True, padx=(0, 4))

        self.cancel_btn = tk.Button(
            actions, text="Cancel", bg=bg, fg=text_fg, disabledforeground=shared.WIN95_DISABLED,
            bd=2, relief=tk.RAISED, font=WIN95_FONT_BOLD, pady=3, width=9, state="disabled", command=self.on_cancel_download,
        )
        self.cancel_btn.pack(side="right")

        self.progress_frame = tk.Frame(self, bg=bg)
        self.progress_label = tk.Label(self.progress_frame, text="0%", bg=bg, fg=text_fg, font=WIN95_FONT_BOLD, anchor="center")
        self.progress_label.pack(fill="x")
        self.speed_eta_label = tk.Label(self.progress_frame, text="Speed: -- KB/s  |  ETA: --:--", bg=bg, fg=text_fg, font=("MS Sans Serif", 8), anchor="center")
        self.speed_eta_label.pack(fill="x")

        self.status_box = tk.Text(self, height=10, bg=white, fg=text_fg, bd=2, relief=tk.SUNKEN, font=("Courier New", 9), state="disabled")
        self.status_box.pack(fill="both", expand=True, pady=(4, 0))

    def _save_flag(self, key, var):
        self.config_data[key] = var.get()
        save_config(self.config_data)

    def set_directory_display(self, path_str):
        self.dir_entry.config(state="normal")
        self.dir_entry.delete(0, tk.END)
        self.dir_entry.insert(0, path_str)
        self.dir_entry.config(state="readonly")

    def set_url_text(self, url):
        self.batch_urls = []
        self.url_entry.delete(0, tk.END)
        self.url_entry.insert(0, url)

    def clear_url_input(self):
        self.batch_urls = []
        self.url_entry.delete(0, tk.END)

    def get_sources(self):
        if self.batch_urls:
            return list(self.batch_urls)
        typed = self.url_entry.get().strip()
        return [typed] if typed.startswith(("http://", "https://")) else []

    def _load_txt_urls(self):
        txt_path = filedialog.askopenfilename(
            title="Select URLs Text File",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not txt_path:
            return
        try:
            urls = parse_urls_from_txt(txt_path)
            if not urls:
                self.log_status("No valid http(s) URLs found in selected .txt file.")
                return
            self.batch_urls = urls
            self.url_entry.delete(0, tk.END)
            self.url_entry.insert(0, f"[Batch: {len(urls)} URLs from {os.path.basename(txt_path)}]")
            self.log_status(f"Loaded {len(urls)} URLs from {os.path.basename(txt_path)}.")
        except Exception as e:
            self.log_status(f"Failed to read .txt file: {e}")

    def _browse_cookie_file(self):
        p = filedialog.askopenfilename(title="Select cookies.txt", filetypes=[("Text / Cookie files", "*.txt"), ("All files", "*.*")])
        if p:
            self.cookie_file_var.set(p)
            self.config_data["cookie_file"] = p
            save_config(self.config_data)

    def _refresh_cookie_controls(self):
        mode = self.cookie_mode_var.get()
        if mode == "Cookies File":
            self.cookie_file_entry.grid(row=7, column=2, sticky="ew", padx=(4, 2), pady=2)
            self.cookie_browse_btn.grid(row=7, column=3, sticky="e", pady=2)
            self.cookie_browser_container.grid_remove()
        elif mode == "Browser":
            self.cookie_file_entry.grid_remove()
            self.cookie_browse_btn.grid_remove()
            self.cookie_browser_container.grid(row=7, column=2, columnspan=2, sticky="w", padx=(4, 0), pady=2)
        else:
            self.cookie_file_entry.grid_remove()
            self.cookie_browse_btn.grid_remove()
            self.cookie_browser_container.grid_remove()

    def _toggle_format_menu(self):
        options = ["Video (MP4)", "Audio (MP3)", "Audio (MP3 + Cover)", "Audio (WAV)"]

        def pick(fmt):
            self.format_var.set(fmt)
            self.config_data["selected_format"] = fmt

            restored_q = self._get_saved_quality_for_format(fmt)
            self.quality_var.set(restored_q)
            self.quality_by_format[fmt] = restored_q
            self.config_data["quality_by_format"] = self.quality_by_format
            self.config_data["selected_quality"] = restored_q
            save_config(self.config_data)

        self.popups.toggle("format", self.combo_container, options, self.format_var.get(), pick)

    def _toggle_quality_menu(self):
        fmt = self.format_var.get()
        options = _qualities_for_format(fmt)

        def pick(q):
            self.quality_var.set(q)
            self.quality_by_format[fmt] = q
            self.config_data["quality_by_format"] = self.quality_by_format
            self.config_data["selected_quality"] = q
            save_config(self.config_data)

        self.popups.toggle("quality", self.quality_container, options, self.quality_var.get(), pick)

    def _toggle_cookie_mode_menu(self):
        def pick(m):
            self.cookie_mode_var.set(m)
            self.config_data["cookie_mode"] = m
            save_config(self.config_data)
            self._refresh_cookie_controls()

        self.popups.toggle("cookie_mode", self.cookie_mode_container, COOKIE_MODES, self.cookie_mode_var.get(), pick)

    def _toggle_cookie_browser_menu(self):
        def pick(b):
            self.cookie_browser_var.set(b)
            self.config_data["cookie_browser"] = b
            save_config(self.config_data)

        self.popups.toggle("cookie_browser", self.cookie_browser_container, COOKIE_BROWSERS, self.cookie_browser_var.get(), pick)

    def _toggle_preset_menu(self):
        options = list(self.presets.keys()) or ["No presets found"]

        def pick(name):
            if name in self.presets:
                self.preset_var.set(name)
                p = self.presets[name]
                if os.path.exists(p):
                    self.set_download_path(p)
                    self.set_directory_display(p)
                    self.config_data["presets"] = self.presets
                    self.config_data["selected_preset"] = name
                    save_config(self.config_data)

        self.popups.toggle("preset", self.preset_container, options, self.preset_var.get(), pick)

    def _browse_folder(self):
        d = filedialog.askdirectory(initialdir=self.get_download_path())
        if d:
            self.set_download_path(d)
            self.set_directory_display(d)
            self.preset_var.set("Presets")
            self.config_data["selected_preset"] = "Presets"
            save_config(self.config_data)

    def _save_preset(self):
        name = ask_preset_name_dialog(self.root)
        if name:
            clean = name.strip()
            self.presets[clean] = self.get_download_path()
            self.preset_var.set(clean)
            self.config_data["presets"] = self.presets
            self.config_data["selected_preset"] = clean
            save_config(self.config_data)
            self.log_status(f"Saved preset: {clean}")

    def _delete_preset(self):
        cur = self.preset_var.get()

        def on_deleted(_):
            self.preset_var.set("Presets")
            self.config_data["presets"] = self.presets
            self.config_data["selected_preset"] = "Presets"
            save_config(self.config_data)

        ask_delete_preset_dialog(self.root, cur, self.presets, on_deleted, self.log_status)

    def append_log(self, text):
        self.status_box.config(state="normal")
        self.status_box.insert(tk.END, text + "\n")
        self.status_box.see(tk.END)
        self.status_box.config(state="disabled")

    def clear_log(self):
        self.status_box.config(state="normal")
        self.status_box.delete("1.0", tk.END)
        self.status_box.config(state="disabled")

    def update_progress(self, percent, speed_text, eta_text, is_downloading):
        if threading.current_thread() != threading.main_thread():
            self.root.after(0, self.update_progress, percent, speed_text, eta_text, is_downloading)
            return

        clamped = max(0, min(100, int(percent)))
        self.progress_label.config(text=f"{clamped}%")
        self.speed_eta_label.config(text=f"Speed: {speed_text}  |  ETA: {eta_text}")

        if 0 <= clamped < 100 and is_downloading:
            if not self.progress_frame.winfo_ismapped():
                self.progress_frame.pack(fill="x", pady=(0, 4), before=self.status_box)
        elif clamped >= 100 and self.progress_frame.winfo_ismapped():
            self.progress_frame.pack_forget()