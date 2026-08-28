import ctypes
import json
import os
import random
import shutil
import sys
import threading
from time import sleep
import tkinter as tk
from tkinter import filedialog

CONFIG_FILE = "config.json"
APP_TITLE = "Fetch"
SIZE_X = 540
SIZE_Y = 400

WIN95_BG = "#C0C0C0"
WIN95_TEAL = "#008080"
WIN95_NAVY = "#000080"
WIN95_WHITE = "#FFFFFF"
WIN95_FONT = ("MS Sans Serif", 9)
WIN95_FONT_BOLD = ("MS Sans Serif", 9, "bold")

WIN95_DEFAULT_BTN_TEXT = "Download"

DOWNLOAD_TEXTS = [
    "Fetching...",
    "Retrieving...",
    "Chasing Down...",
    "Rawr!"
]


def resource_path(relative_path="."):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    
    if relative_path in ("icon.ico", "icon.png"):
        relative_path = os.path.join("media", relative_path)
    
    return os.path.join(base_path, relative_path)

def fix_win95_taskbar(root):
    try:
        import ctypes
        GWL_EXSTYLE = -20
        WS_EX_APPWINDOW = 0x00040000
        WS_EX_TOOLWINDOW = 0x00000080
        
        hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
        style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        style = style & ~WS_EX_TOOLWINDOW
        style = style | WS_EX_APPWINDOW
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
        
        root.withdraw()
        root.deiconify()
    except Exception:
        pass

def load_saved_directory():
    default_dir = os.path.join(os.path.expanduser("~"), "Downloads")
    return default_dir


def get_random_bright_color():
    r = random.randint(33, 255)
    g = random.randint(33, 255)
    b = random.randint(33, 255)
    return f"#{r:02X}{g:02X}{b:02X}"


def show_win95_popup(parent, title, message):
    popup = tk.Toplevel(parent)
    popup.overrideredirect(True)
    popup.configure(bg=WIN95_BG)
    popup.attributes("-topmost", True)

    outer = tk.Frame(popup, bg=WIN95_BG, bd=2, relief=tk.RAISED)
    outer.pack(fill="both", expand=True, padx=2, pady=2)

    title_bar = tk.Frame(outer, bg=WIN95_NAVY, height=22)
    title_bar.pack(fill="x", side="top", padx=2, pady=2)

    t_label = tk.Label(
        title_bar,
        text=title,
        bg=WIN95_NAVY,
        fg=WIN95_WHITE,
        font=WIN95_FONT_BOLD
    )
    t_label.pack(side="left", padx=4)

    close_btn = tk.Button(
        title_bar,
        text="✕",
        bg=WIN95_BG,
        fg="black",
        font=("MS Sans Serif", 7, "bold"),
        bd=1,
        relief=tk.RAISED,
        width=2,
        height=1,
        command=popup.destroy
    )
    close_btn.pack(side="right", padx=2, pady=2)

    body = tk.Frame(outer, bg=WIN95_BG)
    body.pack(fill="both", expand=True, padx=12, pady=12)

    msg_label = tk.Label(
        body,
        text=message,
        bg=WIN95_BG,
        fg="black",
        font=WIN95_FONT,
        wraplength=260,
        justify="center"
    )
    msg_label.pack(pady=(4, 12))

    ok_btn = tk.Button(
        body,
        text="OK",
        bg=WIN95_BG,
        bd=2,
        relief=tk.RAISED,
        font=WIN95_FONT,
        width=8,
        command=popup.destroy
    )
    ok_btn.pack()

    popup.update_idletasks()
    p_w = popup.winfo_width()
    p_h = popup.winfo_height()
    parent_x = parent.winfo_rootx()
    parent_y = parent.winfo_rooty()
    parent_w = parent.winfo_width()
    parent_h = parent.winfo_height()

    x = parent_x + (parent_w // 2) - (p_w // 2)
    y = parent_y + (parent_h // 2) - (p_h // 2)
    popup.geometry(f"+{x}+{y}")

    popup.grab_set()


class MediaDownloaderApp:

    def __init__(self):
        self.root = tk.Tk()
        self.root.title(APP_TITLE)
        self.root.overrideredirect(True)
        self.root.configure(bg=WIN95_TEAL)

        ico_path = resource_path("media/icon.ico")
        if os.path.exists(ico_path):
            try:
                self.root.iconbitmap(ico_path)
            except Exception:
                pass

        self.download_path = load_saved_directory()
        self.app_icon_img = None
        self.text_index = 0
        self.dropdown_popup = None

        self._build_win95_ui()
        self._center_window(SIZE_X, SIZE_Y)
        fix_win95_taskbar(self.root)

    def _center_window(self, width, height):
        self.root.update_idletasks()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def _build_win95_ui(self):
        self.outer_frame = tk.Frame(self.root, bg=WIN95_BG, bd=2, relief=tk.RAISED)
        self.outer_frame.pack(fill="both", expand=True, padx=2, pady=2)

        self.title_bar = tk.Frame(self.outer_frame, bg=WIN95_NAVY, height=22)
        self.title_bar.pack(fill="x", side="top", padx=2, pady=2)

        ico_path = resource_path("media/icon.ico")
        png_path = resource_path("media/icon.png")

        if os.path.exists(png_path) or os.path.exists(ico_path):
            try:
                img_file = png_path if os.path.exists(png_path) else ico_path
                img = tk.PhotoImage(file=img_file)
                self.app_icon_img = img.subsample(max(1, img.width() // 16))
                self.icon_label = tk.Label(
                    self.title_bar, image=self.app_icon_img, bg=WIN95_NAVY
                )
            except Exception:
                self.icon_label = tk.Label(
                    self.title_bar, text="", bg=WIN95_NAVY, fg=WIN95_WHITE, font=("MS Sans Serif", 9)
                )
        else:
            self.icon_label = tk.Label(
                self.title_bar, text="", bg=WIN95_NAVY, fg=WIN95_WHITE, font=("MS Sans Serif", 9)
            )

        self.icon_label.pack(side="left", padx=(4, 2))

        self.title_label = tk.Label(
            self.title_bar,
            text=APP_TITLE,
            bg=WIN95_NAVY,
            fg=WIN95_WHITE,
            font=WIN95_FONT_BOLD,
        )
        self.title_label.pack(side="left", padx=2)

        self.close_btn = tk.Button(
            self.title_bar,
            text="✕",
            bg=WIN95_BG,
            fg="black",
            font=("MS Sans Serif", 7, "bold"),
            bd=1,
            relief=tk.RAISED,
            width=2,
            height=1,
            command=self.close_app,
        )
        self.close_btn.pack(side="right", padx=2, pady=2)

        for widget in (self.title_bar, self.title_label, self.icon_label):
            widget.bind("<ButtonPress-1>", self._start_move)
            widget.bind("<B1-Motion>", self._on_move)

        content_area = tk.Frame(self.outer_frame, bg=WIN95_BG)
        content_area.pack(fill="both", expand=True, padx=10, pady=10)

        form_frame = tk.Frame(content_area, bg=WIN95_BG)
        form_frame.pack(fill="x", side="top")

        tk.Label(
            form_frame, text="Media URL:", bg=WIN95_BG, font=WIN95_FONT
        ).grid(row=0, column=0, sticky="w", pady=4)

        self.url_entry = tk.Entry(
            form_frame,
            bg=WIN95_WHITE,
            fg="black",
            bd=2,
            relief=tk.SUNKEN,
            font=WIN95_FONT,
        )
        self.url_entry.grid(row=0, column=1, columnspan=2, sticky="ew", padx=(8, 0), pady=4)
        self.url_entry.focus()

        tk.Label(
            form_frame, text="Media Format:", bg=WIN95_BG, font=WIN95_FONT
        ).grid(row=1, column=0, sticky="w", pady=4)

        self.format_var = tk.StringVar(value="Video (MP4)")

        self.combo_container = tk.Frame(form_frame, bg=WIN95_WHITE, bd=2, relief=tk.SUNKEN)
        self.combo_container.grid(row=1, column=1, sticky="w", padx=(8, 0), pady=4)

        self.combo_label = tk.Label(
            self.combo_container,
            textvariable=self.format_var,
            bg=WIN95_WHITE,
            fg="black",
            font=WIN95_FONT,
            anchor="w",
            width=18,
            cursor="arrow",
        )
        self.combo_label.pack(side="left", fill="x", expand=True, padx=(2, 0))

        self.combo_btn = tk.Button(
            self.combo_container,
            text="▼",
            bg=WIN95_BG,
            activebackground=WIN95_BG,
            font=("MS Sans Serif", 7),
            bd=1,
            relief=tk.RAISED,
            width=2,
            height=1,
            command=self._toggle_instant_dropdown,
        )
        self.combo_btn.pack(side="right", fill="y")

        self.combo_label.bind("<Button-1>", lambda e: self._toggle_instant_dropdown())
        self.combo_container.bind("<Button-1>", lambda e: self._toggle_instant_dropdown())

        tk.Label(
            form_frame, text="Save Directory:", bg=WIN95_BG, font=WIN95_FONT
        ).grid(row=2, column=0, sticky="w", pady=4)

        self.dir_entry = tk.Entry(
            form_frame,
            bg=WIN95_BG,
            fg="black",
            bd=2,
            relief=tk.SUNKEN,
            font=WIN95_FONT,
        )
        self.dir_entry.insert(0, self.download_path)
        self.dir_entry.config(state="readonly")
        self.dir_entry.grid(row=2, column=1, sticky="ew", padx=(8, 4), pady=4)

        browse_btn = tk.Button(
            form_frame,
            text="Browse...",
            bg=WIN95_BG,
            bd=2,
            relief=tk.RAISED,
            font=WIN95_FONT,
            command=self.browse_folder,
        )
        browse_btn.grid(row=2, column=2, sticky="e", pady=4)

        form_frame.columnconfigure(1, weight=1)

        self.download_btn = tk.Button(
            content_area,
            text=WIN95_DEFAULT_BTN_TEXT,
            bg=WIN95_BG,
            fg="#000000",
            disabledforeground="#000000",
            bd=2,
            relief=tk.RAISED,
            font=WIN95_FONT_BOLD,
            pady=3,
            command=self.start_download_thread,
        )
        self.download_btn.pack(fill="x", pady=(10, 8))

        self.status_box = tk.Text(
            content_area,
            height=9,
            bg=WIN95_WHITE,
            fg="black",
            bd=2,
            relief=tk.SUNKEN,
            font=("Courier New", 9),
            state="disabled",
        )
        self.status_box.pack(fill="both", expand=True)

    def close_app(self):
        self.root.destroy()

    def _toggle_instant_dropdown(self):
        if hasattr(self, "dropdown_popup") and self.dropdown_popup and self.dropdown_popup.winfo_exists():
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
            popup_frame,
            bg=WIN95_WHITE,
            fg="black",
            selectbackground=WIN95_NAVY,
            selectforeground=WIN95_WHITE,
            font=WIN95_FONT,
            bd=0,
            highlightthickness=0,
            activestyle="none",
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
                self.format_var.set(options[sel[0]])
            if self.dropdown_popup:
                self.dropdown_popup.destroy()
                self.dropdown_popup = None

        listbox.bind("<ButtonRelease-1>", on_select)
        listbox.bind("<Return>", on_select)
        self.dropdown_popup.bind("<FocusOut>", lambda e: self._close_dropdown_delay())
        listbox.focus_set()

    def _close_dropdown_delay(self):
        if hasattr(self, "dropdown_popup") and self.dropdown_popup:
            self.dropdown_popup.destroy()
            self.dropdown_popup = None

    def _start_move(self, event):
        self._x = event.x
        self._y = event.y

    def _on_move(self, event):
        deltax = event.x - self._x
        deltay = event.y - self._y
        x = self.root.winfo_x() + deltax
        y = self.root.winfo_y() + deltay
        self.root.geometry(f"+{x}+{y}")

    def browse_folder(self):
        selected_dir = filedialog.askdirectory(initialdir=self.download_path)
        if selected_dir:
            self.download_path = selected_dir
            self.dir_entry.config(state="normal")
            self.dir_entry.delete(0, tk.END)
            self.dir_entry.insert(0, self.download_path)
            self.dir_entry.config(state="readonly")

    def log_status(self, text):
        if threading.current_thread() != threading.main_thread():
            self.root.after(0, self._append_log, text)
        else:
            self._append_log(text)

    def _append_log(self, text):
        self.status_box.config(state="normal")
        self.status_box.insert(tk.END, text + "\n")
        self.status_box.see(tk.END)
        self.status_box.config(state="disabled")

    def _update_button_style(self):
        self.text_index = (self.text_index + 1) % len(DOWNLOAD_TEXTS)
        new_text = DOWNLOAD_TEXTS[self.text_index]
        new_color = get_random_bright_color()
        self.download_btn.config(text=new_text, bg=new_color)

    def _reset_button_style(self):
        self.download_btn.config(text=WIN95_DEFAULT_BTN_TEXT, bg=WIN95_BG)

    def start_download_thread(self):
        url = self.url_entry.get().strip()
        if not url:
            show_win95_popup(self.root, "Missing URL", "Please enter a valid media URL.")
            return

        self._update_button_style()
        self.url_entry.delete(0, tk.END)
        self.download_btn.config(state="disabled")
        self.status_box.config(state="normal")
        self.status_box.delete("1.0", tk.END)
        self.status_box.config(state="disabled")

        threading.Thread(target=self.run_download, args=(url,), daemon=True).start()

    def run_download(self, url):
        import yt_dlp

        format_choice = self.format_var.get()
        audio_format = None
        embed_cover = False

        if "MP3" in format_choice:
            audio_format = "mp3"
            if "Cover" in format_choice:
                embed_cover = True
        elif "WAV" in format_choice:
            audio_format = "wav"

        def ydl_hook(d):
            if d['status'] == 'downloading':
                filename = os.path.basename(d.get('filename', 'file'))
                if not getattr(self, '_current_download_logged', False):
                    self.log_status(f"Downloading: {filename}")
                    self._current_download_logged = True
            elif d['status'] == 'finished':
                filename = os.path.basename(d.get('filename', 'file'))
                self.log_status(f"Finished: {filename}")
                self._current_download_logged = False

        self.log_status(f"Analyzing URL: {url}")
        is_playlist = False
        try:
            with yt_dlp.YoutubeDL({'quiet': True, 'extract_flat': 'in_playlist'}) as ydl:
                info = ydl.extract_info(url, download=False)
                if info:
                    if 'entries' in info or info.get('_type') in ['playlist', 'multi_video']:
                        is_playlist = True
                    elif info.get('playlist_title') or info.get('album'):
                        is_playlist = True
        except Exception:
            pass

        if is_playlist:
            outtmpl = os.path.join(self.download_path, '%(playlist_title|playlist|album)s', '%(title)s.%(ext)s')
        else:
            outtmpl = os.path.join(self.download_path, '%(title)s.%(ext)s')

        ydl_opts = {
            "outtmpl": outtmpl,
            "quiet": True,
            "no_warnings": True,
            "progress_hooks": [ydl_hook],
        }

        bundled_ffmpeg_dir = resource_path("bin")
        if shutil.which("ffmpeg", path=bundled_ffmpeg_dir):
            ydl_opts["ffmpeg_location"] = bundled_ffmpeg_dir

        if audio_format:
            ydl_opts.update({
                "format": "bestaudio/best",
                "embedmetadata": True,
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": audio_format,
                    "preferredquality": "192",
                }],
            })

            if embed_cover:
                ydl_opts.update({
                    "writethumbnail": True,
                    "embedthumbnail": True,
                    "postprocessor_args": [
                        "-id3v2_version", "3",
                        "-write_id3v1", "1"
                    ],
                })
                ydl_opts["postprocessors"].append({"key": "EmbedThumbnail"})
        else:
            ydl_opts["format"] = "bestvideo+bestaudio/best"
            ydl_opts["merge_output_format"] = "mp4"

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            self.log_status("\nMedia fetched successfully!")
            self.log_status(f"Saved to: {self.download_path}")

            self.print_art()

        except Exception as e:
            self.log_status(f"\nAn error occurred: {e}")
        finally:
            self.root.after(0, self._reset_button_style)
            self.root.after(0, lambda: self.download_btn.config(state="normal"))

    def print_art(self):
        paw_print = [
            "⠀⠀⠀⠀⣀⡀",
            "⢠⣤⡀⣾⣿⣿⠀⣤⣤⡄",
            "⢿⣿⡇⠘⠛⠁⢸⣿⣿⠃",
            "⠈⣉⣤⣾⣿⣿⡆⠉⣴⣶⣶",
            "⣾⣿⣿⣿⣿⣿⣿⡀⠻⠟⠃",
            "⠙⠛⠻⢿⣿⣿⣿⡇",
            "⠀⠀⠀⠀⠈⠙⠋⠁",
        ]
        self.log_status("")
        for line in paw_print:
            self.log_status(line)
            sleep(0.02)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = MediaDownloaderApp()
    app.run()