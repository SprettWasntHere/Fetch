import tkinter as tk
import shared
from shared import AVAILABLE_THEMES, DEFAULT_THEME, WIN95_FONT, WIN95_FONT_BOLD


def apply_theme_to_tree(root_widget, title_label=None, title_bar=None, white_containers=()):
    bg = shared.WIN95_BG
    teal = shared.WIN95_TEAL
    navy = shared.WIN95_NAVY
    white = shared.WIN95_WHITE
    text_fg = shared.WIN95_TEXT
    title_fg = shared.WIN95_TITLE_TEXT
    active_bg = getattr(shared, "WIN95_ACTIVE_BG", navy)
    active_fg = getattr(shared, "WIN95_ACTIVE_FG", text_fg)
    disabled_fg = getattr(shared, "WIN95_DISABLED", text_fg)

    white_set = set(white_containers) if white_containers else set()
    root_widget.configure(bg=teal)

    def walk(widget):
        w_type = widget.winfo_class()
        try:
            if w_type in ("Frame", "Toplevel", "LabelFrame", "Labelframe"):
                if title_bar is not None and widget == title_bar:
                    widget.configure(bg=navy)
                elif widget in white_set:
                    widget.configure(bg=white)
                else:
                    widget.configure(bg=bg)
                if w_type in ("LabelFrame", "Labelframe"):
                    widget.configure(fg=text_fg)
            elif w_type == "Label":
                if widget == title_label or (title_bar and widget.master == title_bar):
                    widget.configure(bg=navy, fg=title_fg)
                elif widget.master in white_set:
                    widget.configure(bg=white, fg=text_fg)
                else:
                    widget.configure(bg=bg, fg=text_fg)
            elif w_type == "Button":
                widget.configure(
                    bg=bg,
                    fg=text_fg,
                    activebackground=bg,
                    activeforeground=text_fg,
                    disabledforeground=disabled_fg,
                )
            elif w_type == "Entry":
                cfg = {"bg": white, "fg": text_fg}
                if str(widget.cget("state")) == "readonly":
                    cfg["readonlybackground"] = white
                widget.configure(**cfg)
            elif w_type == "Text":
                widget.configure(bg=white, fg=text_fg)
            elif w_type == "Listbox":
                widget.configure(
                    bg=white,
                    fg=text_fg,
                    selectbackground=active_bg,
                    selectforeground=active_fg,
                )
            elif w_type == "Checkbutton":
                widget.configure(
                    bg=bg,
                    fg=text_fg,
                    activebackground=bg,
                    activeforeground=text_fg,
                    selectcolor=white,
                )
        except Exception:
            pass

        for child in widget.winfo_children():
            walk(child)

    walk(root_widget)


class PopupController:
    def __init__(self, parent_root):
        self.root = parent_root
        self._popups = {}

    def close(self, key):
        pop = self._popups.get(key)
        if pop and pop.winfo_exists():
            pop.destroy()
        self._popups[key] = None

    def close_all(self, except_key=None):
        for k in list(self._popups.keys()):
            if k != except_key:
                self.close(k)

    def toggle(self, key, anchor_widget, options, current_val, on_pick, fixed_geometry=None):
        existing = self._popups.get(key)
        if existing and existing.winfo_exists():
            self.close(key)
            return

        self.close_all(except_key=key)

        popup = tk.Toplevel(self.root)
        popup.overrideredirect(True)
        popup.attributes("-topmost", True)
        self._popups[key] = popup

        if fixed_geometry:
            popup.geometry(fixed_geometry)
        else:
            x = anchor_widget.winfo_rootx()
            y = anchor_widget.winfo_rooty() + anchor_widget.winfo_height()
            width = max(anchor_widget.winfo_width(), 100)
            height = min(len(options), 6) * 18 + 4
            popup.geometry(f"{width}x{height}+{x}+{y}")

        frame = tk.Frame(popup, bg=shared.WIN95_BG, bd=2, relief=tk.RAISED)
        frame.pack(fill="both", expand=True)

        listbox = tk.Listbox(
            frame,
            bg=shared.WIN95_WHITE,
            fg=shared.WIN95_TEXT,
            selectbackground=shared.WIN95_ACTIVE_BG,
            selectforeground=shared.WIN95_ACTIVE_FG,
            font=WIN95_FONT,
            bd=0,
            highlightthickness=0,
            activestyle="none",
        )
        listbox.pack(fill="both", expand=True)

        for opt in options:
            listbox.insert(tk.END, opt)

        if current_val in options:
            idx = options.index(current_val)
            listbox.select_set(idx)
            listbox.activate(idx)

        def on_select(evt=None):
            sel = listbox.curselection()
            if sel:
                on_pick(options[sel[0]])
            self.close(key)

        listbox.bind("<ButtonRelease-1>", on_select)
        listbox.bind("<Return>", on_select)
        popup.bind("<FocusOut>", lambda e: self.close(key))
        listbox.focus_set()

def ask_preset_name_dialog(parent):
    dialog = tk.Toplevel(parent)
    dialog.overrideredirect(True)
    dialog.configure(bg=shared.WIN95_TEAL)

    outer = tk.Frame(dialog, bg=shared.WIN95_BG, bd=2, relief=tk.RAISED)
    outer.pack(fill="both", expand=True, padx=2, pady=2)

    title_bar = tk.Frame(outer, bg=shared.WIN95_NAVY, height=22)
    title_bar.pack(fill="x", side="top", padx=2, pady=2)
    tk.Label(
        title_bar,
        text="Save Preset",
        bg=shared.WIN95_NAVY,
        fg=shared.WIN95_TITLE_TEXT,
        font=WIN95_FONT_BOLD,
    ).pack(side="left", padx=4)

    result = [None]

    def close_dialog(val=None):
        result[0] = val
        dialog.destroy()

    tk.Button(
        title_bar,
        text="✕",
        bg=shared.WIN95_BG,
        fg=shared.WIN95_TEXT,
        font=("MS Sans Serif", 7, "bold"),
        bd=1,
        relief=tk.RAISED,
        width=2,
        height=1,
        command=lambda: close_dialog(None),
    ).pack(side="right", padx=2, pady=2)

    content = tk.Frame(outer, bg=shared.WIN95_BG)
    content.pack(fill="both", expand=True, padx=12, pady=12)

    tk.Label(
        content, text="Preset Name:", bg=shared.WIN95_BG, fg=shared.WIN95_TEXT, font=WIN95_FONT
    ).pack(anchor="w", pady=(0, 4))

    entry = tk.Entry(
        content,
        bg=shared.WIN95_WHITE,
        fg=shared.WIN95_TEXT,
        bd=2,
        relief=tk.SUNKEN,
        font=WIN95_FONT,
        width=25,
    )
    entry.pack(fill="x", pady=(0, 12))
    entry.focus()

    btn_box = tk.Frame(content, bg=shared.WIN95_BG)
    btn_box.pack(fill="x")

    def on_ok(e=None):
        val = entry.get().strip()
        if val:
            close_dialog(val)

    tk.Button(
        btn_box, text="OK", bg=shared.WIN95_BG, fg=shared.WIN95_TEXT, bd=2, relief=tk.RAISED, font=WIN95_FONT, width=8, command=on_ok
    ).pack(side="right", padx=(4, 0))

    tk.Button(
        btn_box,
        text="Cancel",
        bg=shared.WIN95_BG,
        fg=shared.WIN95_TEXT,
        bd=2,
        relief=tk.RAISED,
        font=WIN95_FONT,
        width=8,
        command=lambda: close_dialog(None),
    ).pack(side="right")

    entry.bind("<Return>", on_ok)
    entry.bind("<Escape>", lambda e: close_dialog(None))

    dialog.update_idletasks()
    w = dialog.winfo_reqwidth()
    h = dialog.winfo_reqheight()
    x = parent.winfo_rootx() + (parent.winfo_width() // 2) - (w // 2)
    y = parent.winfo_rooty() + (parent.winfo_height() // 2) - (h // 2)
    dialog.geometry(f"+{x}+{y}")

    dialog.grab_set()
    parent.wait_window(dialog)
    return result[0]

def ask_delete_preset_dialog(parent, preset_name, presets_dict, on_deleted, on_log):
    dialog = tk.Toplevel(parent)
    dialog.overrideredirect(True)
    dialog.configure(bg=shared.WIN95_TEAL)

    outer = tk.Frame(dialog, bg=shared.WIN95_BG, bd=2, relief=tk.RAISED)
    outer.pack(fill="both", expand=True, padx=2, pady=2)

    title_bar = tk.Frame(outer, bg=shared.WIN95_NAVY, height=22)
    title_bar.pack(fill="x", side="top", padx=2, pady=2)
    tk.Label(
        title_bar,
        text="Delete Preset?",
        bg=shared.WIN95_NAVY,
        fg=shared.WIN95_TITLE_TEXT,
        font=WIN95_FONT_BOLD,
    ).pack(side="left", padx=4)

    def close_dialog():
        dialog.destroy()

    tk.Label(
        outer,
        text=f"Are you sure you want to delete the preset '{preset_name}'?",
        bg=shared.WIN95_BG,
        fg=shared.WIN95_TEXT,
        font=WIN95_FONT,
        wraplength=300,
        justify="left",
    ).pack(fill="x", padx=12, pady=(12, 8))

    content = tk.Frame(outer, bg=shared.WIN95_BG)
    content.pack(fill="both", expand=True, padx=12, pady=12)

    btn_box = tk.Frame(content, bg=shared.WIN95_BG)
    btn_box.pack(fill="x")

    def on_ok(e=None):
        if preset_name in presets_dict:
            if len(presets_dict) <= 1:
                on_log("Cannot delete the last remaining preset.")
                return
            del presets_dict[preset_name]
            on_deleted(preset_name)
            on_log(f"Deleted preset: {preset_name}")
        else:
            on_log("No valid preset selected to delete.")
        close_dialog()

    tk.Button(
        btn_box, text="OK", bg=shared.WIN95_BG, fg=shared.WIN95_TEXT, bd=2, relief=tk.RAISED, font=WIN95_FONT, width=8, command=on_ok
    ).pack(side="right", padx=(4, 0))

    tk.Button(
        btn_box,
        text="Cancel",
        bg=shared.WIN95_BG,
        fg=shared.WIN95_TEXT,
        bd=2,
        relief=tk.RAISED,
        font=WIN95_FONT,
        width=8,
        command=close_dialog,
    ).pack(side="right")

    dialog.update_idletasks()
    w = dialog.winfo_reqwidth()
    h = dialog.winfo_reqheight()
    x = parent.winfo_rootx() + (parent.winfo_width() // 2) - (w // 2)
    y = parent.winfo_rooty() + (parent.winfo_height() // 2) - (h // 2)
    dialog.geometry(f"+{x}+{y}")

    dialog.grab_set()
    parent.wait_window(dialog)