import ctypes
import os
import random
import sys
import threading
import json
from time import sleep
import tkinter as tk
from tkinter import filedialog

from download import run_download
from texts import DOWNLOAD_TEXTS

APP_TITLE = "Fetch"
APP_VERSION = "1.4"
SIZE_X = 540
SIZE_Y = 440
CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".fetch_presets.json")

WIN95_BG = "#C0C0C0"
WIN95_TEAL = "#008080"
WIN95_NAVY = "#000080"
WIN95_WHITE = "#FFFFFF"
WIN95_FONT = ("MS Sans Serif", 9)
WIN95_FONT_BOLD = ("MS Sans Serif", 9, "bold")

WIN95_DEFAULT_BTN_TEXT = "Download"

def resource_path(relative_path="."):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    
    if relative_path in ("icon.ico", "icon.png", "art.txt"):
        relative_path = os.path.join("assets", relative_path)
    
    return os.path.join(base_path, relative_path)


def fix_win95_taskbar(root):
    try:
        GWL_EXSTYLE = -20
        WS_EX_APPWINDOW = 0x00040000
        WS_EX_TOOLWINDOW = 0x00000080
        
        hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
        style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        style = (style & ~WS_EX_TOOLWINDOW) | WS_EX_APPWINDOW
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
        
        root.withdraw()
        root.deiconify()
    except Exception:
        pass


def get_random_bright_color():
    min_brightness = 150
    max_brightness = 255
    return f"#{random.randint(min_brightness, max_brightness):02X}{random.randint(min_brightness, max_brightness):02X}{random.randint(min_brightness, max_brightness):02X}"


class MediaDownloaderApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(APP_TITLE)
        self.root.overrideredirect(True)
        self.root.configure(bg=WIN95_TEAL)

        ico_path = resource_path("assets/icon.ico")
        if os.path.exists(ico_path):
            try:
                self.root.iconbitmap(ico_path)
            except Exception:
                pass

        self.presets = self.load_presets()
        default_dl = os.path.join(os.path.expanduser("~"), "Downloads")
        if not self.presets:
            self.presets = {"Downloads Folder": default_dl}

        self.download_path = default_dl
        self.app_icon_img = None
        self.text_index = 0
        self.dropdown_popup = None
        self.preset_popup = None

        self._build_win95_ui()
        self._center_window(SIZE_X, SIZE_Y)
        fix_win95_taskbar(self.root)

    def _center_window(self, width, height):
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def _build_win95_ui(self):
        self.outer_frame = tk.Frame(self.root, bg=WIN95_BG, bd=2, relief=tk.RAISED)
        self.outer_frame.pack(fill="both", expand=True, padx=2, pady=2)

        self.title_bar = tk.Frame(self.outer_frame, bg=WIN95_NAVY, height=22)
        self.title_bar.pack(fill="x", side="top", padx=2, pady=2)

        ico_path = resource_path("assets/icon.ico")
        png_path = resource_path("assets/icon.png")

        if os.path.exists(png_path) or os.path.exists(ico_path):
            try:
                img_file = png_path if os.path.exists(png_path) else ico_path
                img = tk.PhotoImage(file=img_file)
                self.app_icon_img = img.subsample(max(1, img.width() // 16))
                self.icon_label = tk.Label(self.title_bar, image=self.app_icon_img, bg=WIN95_NAVY)
            except Exception:
                self.icon_label = tk.Label(self.title_bar, text="", bg=WIN95_NAVY, fg=WIN95_WHITE, font=WIN95_FONT)
        else:
            self.icon_label = tk.Label(self.title_bar, text="", bg=WIN95_NAVY, fg=WIN95_WHITE, font=WIN95_FONT)

        self.icon_label.pack(side="left", padx=(4, 2))

        self.title_label = tk.Label(self.title_bar, text=APP_TITLE, bg=WIN95_NAVY, fg=WIN95_WHITE, font=WIN95_FONT_BOLD)
        self.title_label.pack(side="left", padx=2)

        self.close_btn = tk.Button(
            self.title_bar, text="✕", bg=WIN95_BG, fg="black", font=("MS Sans Serif", 7, "bold"),
            bd=1, relief=tk.RAISED, width=2, height=1, command=self.close_app
        )
        self.close_btn.pack(side="right", padx=2, pady=2)

        for widget in (self.title_bar, self.title_label, self.icon_label):
            widget.bind("<ButtonPress-1>", self._start_move)
            widget.bind("<B1-Motion>", self._on_move)

        version_frame = tk.Frame(self.outer_frame, bg=WIN95_BG, bd=1)
        version_frame.pack(fill="x", side="bottom", padx=2, pady=(0, 2))

        self.version_label = tk.Label(version_frame, text=f" v{APP_VERSION} ", bg=WIN95_BG, fg="black", font=("MS Sans Serif", 8), anchor="w")
        self.version_label.pack(side="left")

        content_area = tk.Frame(self.outer_frame, bg=WIN95_BG)
        content_area.pack(fill="both", expand=True, padx=10, pady=10)

        form_frame = tk.Frame(content_area, bg=WIN95_BG)
        form_frame.pack(fill="x", side="top")

        tk.Label(form_frame, text="Media URL:", bg=WIN95_BG, font=WIN95_FONT).grid(row=0, column=0, sticky="w", pady=4)

        self.url_entry = tk.Entry(form_frame, bg=WIN95_WHITE, fg="black", bd=2, relief=tk.SUNKEN, font=WIN95_FONT)
        self.url_entry.grid(row=0, column=1, columnspan=2, sticky="ew", padx=(8, 0), pady=4)
        self.url_entry.focus()

        tk.Label(form_frame, text="Media Format:", bg=WIN95_BG, font=WIN95_FONT).grid(row=1, column=0, sticky="w", pady=4)

        self.format_var = tk.StringVar(value="Video (MP4)")

        self.combo_container = tk.Frame(form_frame, bg=WIN95_WHITE, bd=2, relief=tk.SUNKEN)
        self.combo_container.grid(row=1, column=1, sticky="w", padx=(8, 0), pady=4)

        self.combo_label = tk.Label(
            self.combo_container, textvariable=self.format_var, bg=WIN95_WHITE, fg="black",
            font=WIN95_FONT, anchor="w", width=18, cursor="arrow"
        )
        self.combo_label.pack(side="left", fill="x", expand=True, padx=(2, 0))

        self.combo_btn = tk.Button(
            self.combo_container, text="▼", bg=WIN95_BG, activebackground=WIN95_BG,
            font=("MS Sans Serif", 7), bd=1, relief=tk.RAISED, width=2, height=1,
            command=self._toggle_instant_dropdown
        )
        self.combo_btn.pack(side="right", fill="y")

        self.combo_label.bind("<Button-1>", lambda e: self._toggle_instant_dropdown())
        self.combo_container.bind("<Button-1>", lambda e: self._toggle_instant_dropdown())

        tk.Label(form_frame, text="Download Directory:", bg=WIN95_BG, font=WIN95_FONT).grid(row=2, column=0, sticky="w", pady=4)

        self.dir_entry = tk.Entry(form_frame, bg=WIN95_BG, fg="black", bd=2, relief=tk.SUNKEN, font=WIN95_FONT)
        self.dir_entry.insert(0, self.download_path)
        self.dir_entry.config(state="readonly")
        self.dir_entry.grid(row=2, column=1, sticky="ew", padx=(8, 4), pady=4)

        browse_btn = tk.Button(form_frame, text="Browse...", bg=WIN95_BG, bd=2, relief=tk.RAISED, font=WIN95_FONT, command=self.browse_folder)
        browse_btn.grid(row=2, column=2, sticky="e", pady=4)

        self.preset_var = tk.StringVar(value="Presets")
        self.preset_container = tk.Frame(form_frame, bg=WIN95_WHITE, bd=2, relief=tk.SUNKEN)
        self.preset_container.grid(row=3, column=1, sticky="w", padx=(8, 4), pady=4)

        self.preset_label = tk.Label(
            self.preset_container, textvariable=self.preset_var, bg=WIN95_WHITE, fg="black",
            font=WIN95_FONT, anchor="w", width=18, cursor="arrow"
        )
        self.preset_label.pack(side="left", fill="x", expand=True, padx=(2, 0))

        self.preset_btn = tk.Button(
            self.preset_container, text="▼", bg=WIN95_BG, activebackground=WIN95_BG,
            font=("MS Sans Serif", 7), bd=1, relief=tk.RAISED, width=2, height=1,
            command=self._toggle_preset_dropdown
        )
        self.preset_btn.pack(side="right", fill="y")

        self.preset_label.bind("<Button-1>", lambda e: self._toggle_preset_dropdown())
        self.preset_container.bind("<Button-1>", lambda e: self._toggle_preset_dropdown())

        preset_btn_frame = tk.Frame(form_frame, bg=WIN95_BG)
        preset_btn_frame.grid(row=3, column=2, sticky="e", pady=4)

        save_preset_btn = tk.Button(preset_btn_frame, text="Save", bg=WIN95_BG, bd=2, relief=tk.RAISED, font=WIN95_FONT, width=5, command=self.save_current_as_preset)
        save_preset_btn.pack(side="left", padx=(0, 2))

        delete_preset_btn = tk.Button(preset_btn_frame, text="Delete", bg=WIN95_BG, bd=2, relief=tk.RAISED, font=WIN95_FONT, width=5, command=self.delete_current_preset)
        delete_preset_btn.pack(side="left")
        
        form_frame.columnconfigure(1, weight=1)

        self.download_btn = tk.Button(
            content_area, text=WIN95_DEFAULT_BTN_TEXT, bg=WIN95_BG, fg="#000000",
            disabledforeground="#000000", bd=2, relief=tk.RAISED, font=WIN95_FONT_BOLD,
            pady=3, command=self.start_download_thread
        )
        self.download_btn.pack(fill="x", pady=(10, 8))

        self.progress_label = tk.Label(
            content_area, text="0%", bg=WIN95_BG, fg="black", bd=2, font=WIN95_FONT, anchor="center"
        )

        self.status_box = tk.Text(
            content_area, height=9, bg=WIN95_WHITE, fg="black", bd=2,
            relief=tk.SUNKEN, font=("Courier New", 9), state="disabled"
        )
        self.status_box.pack(fill="both", expand=True)

    def close_app(self):
        self.root.destroy()

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
            popup_frame, bg=WIN95_WHITE, fg="black", selectbackground=WIN95_NAVY,
            selectforeground=WIN95_WHITE, font=WIN95_FONT, bd=0, highlightthickness=0, activestyle="none"
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

    def load_presets(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def save_presets(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.presets, f, indent=4)
        except Exception:
            pass

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
            popup_frame, bg=WIN95_WHITE, fg="black", selectbackground=WIN95_NAVY,
            selectforeground=WIN95_WHITE, font=WIN95_FONT, bd=0, highlightthickness=0, activestyle="none"
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

        ico_path = resource_path("assets/icon.ico")
        png_path = resource_path("assets/icon.png")

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

        title_lbl = tk.Label(title_bar, text="Save Preset", bg=WIN95_NAVY, fg=WIN95_WHITE, font=WIN95_FONT_BOLD)
        title_lbl.pack(side="left", padx=2)

        result = [None]

        def close_dialog(val=None):
            result[0] = val
            dialog.destroy()

        close_btn = tk.Button(
            title_bar, text="✕", bg=WIN95_BG, fg="black", font=("MS Sans Serif", 7, "bold"),
            bd=1, relief=tk.RAISED, width=2, height=1, command=lambda: close_dialog(None)
        )
        close_btn.pack(side="right", padx=2, pady=2)

        content = tk.Frame(outer, bg=WIN95_BG)
        content.pack(fill="both", expand=True, padx=12, pady=12)

        tk.Label(content, text="Preset Name:", bg=WIN95_BG, font=WIN95_FONT).pack(anchor="w", pady=(0, 4))

        entry = tk.Entry(content, bg=WIN95_WHITE, fg="black", bd=2, relief=tk.SUNKEN, font=WIN95_FONT, width=25)
        entry.pack(fill="x", pady=(0, 12))
        entry.focus()

        btn_box = tk.Frame(content, bg=WIN95_BG)
        btn_box.pack(fill="x")

        def on_ok(e=None):
            val = entry.get().strip()
            if val:
                close_dialog(val)

        ok_btn = tk.Button(btn_box, text="OK", bg=WIN95_BG, bd=2, relief=tk.RAISED, font=WIN95_FONT, width=8, command=on_ok)
        ok_btn.pack(side="right", padx=(4, 0))

        cancel_btn = tk.Button(btn_box, text="Cancel", bg=WIN95_BG, bd=2, relief=tk.RAISED, font=WIN95_FONT, width=8, command=lambda: close_dialog(None))
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

    def save_current_as_preset(self):
        preset_name = self._ask_preset_name()
        if preset_name:
            name = preset_name.strip()
            self.presets[name] = self.download_path
            self.save_presets()
            self.preset_var.set(name)
            self.log_status(f"Saved preset: {name}")

    def delete_current_preset(self):
        current_name = self.preset_var.get()
        if current_name in self.presets:
            if len(self.presets) <= 1:
                self.log_status("Cannot delete the last remaining preset.")
                return
            del self.presets[current_name]
            self.save_presets()
            self.preset_var.set("Presets")
            self.log_status(f"Deleted preset: {current_name}")
        else:
            self.log_status("No valid preset selected to delete.")

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
        self.text_index = random.choice(DOWNLOAD_TEXTS)
        self.download_btn.config(text=self.text_index, bg=get_random_bright_color())

    def _reset_button_style(self):
        self.download_btn.config(text=WIN95_DEFAULT_BTN_TEXT, bg=WIN95_BG)

    def set_progress(self, percent):
        def _update():
            clamped_percent = max(0, min(100, int(percent)))
            self.progress_label.config(text=f"{clamped_percent}%")

            if 0 < clamped_percent < 100:
                if not self.progress_label.winfo_ismapped():
                    self.progress_label.pack(fill="x", pady=(0, 8), before=self.status_box)
            else:
                if clamped_percent >= 100 and self.progress_label.winfo_ismapped():
                    self.progress_label.pack_forget()
            
        if threading.current_thread() != threading.main_thread():
            self.root.after(0, _update)
        else:
            _update()

    def start_download_thread(self):
        url = self.url_entry.get().strip()
        if not url:
            return

        self._update_button_style()
        self.url_entry.delete(0, tk.END)
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
            self.root.after(0, self._reset_button_style)
            self.root.after(0, lambda: self.download_btn.config(state="normal"))

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