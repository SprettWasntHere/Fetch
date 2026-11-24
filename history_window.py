import os
import tkinter as tk
import shared
from shared import WIN95_FONT, WIN95_FONT_BOLD, load_history, clear_history, open_notepad_with_file


class HistoryWindow:
    def __init__(self, parent, fallback_dir, on_use_url, on_log):
        self.parent = parent
        self.fallback_dir = fallback_dir
        self.on_use_url = on_use_url
        self.on_log = on_log
        self.win = None
        self._widgets = {}
        self._redraw_thumb = None
        self._refresh_history = None
        self._applying_theme = False

    def apply_theme(self):
        if not self.win or not self.win.winfo_exists() or self._applying_theme:
            return

        self._applying_theme = True
        try:
            bg = shared.WIN95_BG
            navy = shared.WIN95_NAVY
            white = shared.WIN95_WHITE
            text_fg = shared.WIN95_TEXT
            title_fg = shared.WIN95_TITLE_TEXT
            shadow_fg = getattr(shared, "WIN95_DISABLED", "#808080")

            self.win.configure(bg=shared.WIN95_TEAL)

            for w in self._widgets.get("bg", ()):
                if w.winfo_exists():
                    w.configure(bg=bg)

            for w in self._widgets.get("white", ()):
                if w.winfo_exists():
                    w.configure(bg=white)

            for w in self._widgets.get("navy", ()):
                if w.winfo_exists():
                    w.configure(bg=navy)

            for w in self._widgets.get("title_label", ()):
                if w.winfo_exists():
                    w.configure(bg=navy, fg=title_fg)

            for w in self._widgets.get("btn", ()):
                if w.winfo_exists():
                    w.configure(
                        bg=bg,
                        fg=text_fg,
                        activebackground=bg,
                        activeforeground=text_fg,
                    )

            for lb in self._widgets.get("listbox", ()):
                if lb.winfo_exists():
                    lb.configure(
                        bg=white,
                        fg=text_fg,
                        selectbackground=shared.WIN95_ACTIVE_BG,
                        selectforeground=shared.WIN95_ACTIVE_FG,
                    )

            self._widgets["colors"] = {
                "bg": bg,
                "white": white,
                "text_fg": text_fg,
                "shadow_fg": shadow_fg,
            }

            if callable(self._redraw_thumb):
                self.win.after_idle(self._redraw_thumb)
        finally:
            self._applying_theme = False

    def show(self):
        if self.win and self.win.winfo_exists():
            if callable(self._refresh_history):
                self._refresh_history()
            self.apply_theme()
            self.win.lift()
            return

        bg = shared.WIN95_BG
        navy = shared.WIN95_NAVY
        white = shared.WIN95_WHITE
        text_fg = shared.WIN95_TEXT
        title_fg = shared.WIN95_TITLE_TEXT
        shadow_fg = getattr(shared, "WIN95_DISABLED", "#808080")

        win = tk.Toplevel(self.parent)
        self.win = win
        win.overrideredirect(True)
        win.configure(bg=shared.WIN95_TEAL)
        win.geometry(f"620x360+{self.parent.winfo_rootx() - 30}+{self.parent.winfo_rooty() + 60}")

        bg_widgets = []
        white_widgets = []
        navy_widgets = []
        title_labels = []
        btns = []
        listboxes = []

        outer = tk.Frame(win, bg=bg, bd=2, relief=tk.RAISED)
        outer.pack(fill="both", expand=True, padx=2, pady=2)
        bg_widgets.append(outer)

        tbar = tk.Frame(outer, bg=navy, height=22)
        tbar.pack(fill="x", side="top", padx=2, pady=2)
        navy_widgets.append(tbar)

        tlabel = tk.Label(tbar, text="Download History", bg=navy, fg=title_fg, font=WIN95_FONT_BOLD)
        tlabel.pack(side="left", padx=4)
        title_labels.append(tlabel)

        close_btn = tk.Button(
            tbar,
            text="✕",
            bg=bg,
            fg=text_fg,
            font=("MS Sans Serif", 7, "bold"),
            bd=1,
            relief=tk.RAISED,
            width=2,
            height=1,
            command=win.destroy,
            activebackground=bg,
            activeforeground=text_fg,
        )
        close_btn.pack(side="right", padx=2, pady=2)
        btns.append(close_btn)

        drag = {"x": 0, "y": 0}

        def start_drag(e):
            drag["x"], drag["y"] = e.x, e.y

        def move_drag(e):
            win.geometry(f"+{win.winfo_x() + (e.x - drag['x'])}+{win.winfo_y() + (e.y - drag['y'])}")

        for w in (tbar, tlabel):
            w.bind("<ButtonPress-1>", start_drag)
            w.bind("<B1-Motion>", move_drag)

        body = tk.Frame(outer, bg=bg)
        body.pack(fill="both", expand=True, padx=8, pady=8)
        bg_widgets.append(body)

        list_frame = tk.Frame(body, bg=white, bd=2, relief=tk.SUNKEN)
        list_frame.pack(fill="both", expand=True)
        white_widgets.append(list_frame)

        sb_frame = tk.Frame(list_frame, bg=bg, width=16)
        sb_frame.pack(side="right", fill="y")
        sb_frame.pack_propagate(False)
        bg_widgets.append(sb_frame)

        sb_canvas = tk.Canvas(
            sb_frame,
            bg=bg,
            bd=0,
            highlightthickness=0,
        )
        bg_widgets.append(sb_canvas)

        def scroll_step(delta):
            h_listbox.yview_scroll(delta, "units")
            redraw_thumb()

        up_btn = tk.Button(
            sb_frame,
            text="▲",
            bg=bg,
            fg=text_fg,
            activebackground=bg,
            activeforeground=text_fg,
            font=("MS Sans Serif", 6),
            bd=1,
            relief=tk.RAISED,
            highlightthickness=0,
            command=lambda: scroll_step(-1),
        )
        up_btn.pack(side="top", fill="x", ipady=1)
        btns.append(up_btn)

        down_btn = tk.Button(
            sb_frame,
            text="▼",
            bg=bg,
            fg=text_fg,
            activebackground=bg,
            activeforeground=text_fg,
            font=("MS Sans Serif", 6),
            bd=1,
            relief=tk.RAISED,
            highlightthickness=0,
            command=lambda: scroll_step(1),
        )
        down_btn.pack(side="bottom", fill="x", ipady=1)
        btns.append(down_btn)

        sb_canvas.pack(fill="both", expand=True)

        thumb_state = {"y": 0, "h": 20, "drag_y": 0}

        def _thumb_geometry():
            first, last = h_listbox.yview()
            total_h = max(sb_canvas.winfo_height(), 1)
            visible_span = max(0.0, min(1.0, last - first))
            if visible_span >= 1.0:
                return 0, total_h, visible_span
            thumb_h = max(int(total_h * visible_span), 16)
            thumb_h = min(thumb_h, total_h)
            max_top = max(total_h - thumb_h, 0)
            max_first = max(1.0 - visible_span, 1e-9)
            thumb_y = int((first / max_first) * max_top)
            thumb_y = max(0, min(thumb_y, max_top))
            return thumb_y, thumb_h, visible_span

        def redraw_thumb(*_):
            if not sb_canvas.winfo_exists() or not h_listbox.winfo_exists():
                return
            c = self._widgets.get("colors", {
                "bg": bg,
                "white": white,
                "text_fg": text_fg,
                "shadow_fg": shadow_fg,
            })
            cur_bg = c["bg"]
            cur_white = c["white"]
            cur_fg = c["text_fg"]
            cur_shadow = c["shadow_fg"]

            total_h = max(sb_canvas.winfo_height(), 1)
            w = max(sb_canvas.winfo_width(), 1)
            sb_canvas.delete("all")

            for y in range(0, total_h, 2):
                sb_canvas.create_line(0, y, w, y, fill=cur_white if y % 4 == 0 else cur_bg)

            thumb_y, thumb_h, visible_span = _thumb_geometry()
            thumb_state["y"] = thumb_y
            thumb_state["h"] = thumb_h

            if visible_span < 1.0 and thumb_h < total_h:
                sb_canvas.create_rectangle(
                    1,
                    thumb_y,
                    w - 1,
                    thumb_y + thumb_h,
                    fill=cur_bg,
                    outline=cur_fg,
                    width=1,
                )
                sb_canvas.create_line(2, thumb_y + 1, w - 2, thumb_y + 1, fill=cur_white)
                sb_canvas.create_line(2, thumb_y + 1, 2, thumb_y + thumb_h - 1, fill=cur_white)
                sb_canvas.create_line(
                    2,
                    thumb_y + thumb_h - 2,
                    w - 2,
                    thumb_y + thumb_h - 2,
                    fill=cur_shadow,
                )
                sb_canvas.create_line(
                    w - 2,
                    thumb_y + 1,
                    w - 2,
                    thumb_y + thumb_h - 1,
                    fill=cur_shadow,
                )

        self._redraw_thumb = redraw_thumb

        def _move_thumb_to(new_y):
            first, last = h_listbox.yview()
            visible_span = max(0.0, min(1.0, last - first))
            if visible_span >= 1.0:
                return
            total_h = max(sb_canvas.winfo_height(), 1)
            thumb_h = thumb_state["h"]
            movable = max(total_h - thumb_h, 1)
            clamped_y = max(0, min(movable, new_y))
            ratio = clamped_y / movable
            max_top_fraction = max(0.0, 1.0 - visible_span)
            h_listbox.yview_moveto(ratio * max_top_fraction)
            redraw_thumb()

        def on_sb_press(e):
            y0, h0 = thumb_state["y"], thumb_state["h"]
            if y0 <= e.y <= y0 + h0:
                thumb_state["drag_y"] = e.y - y0
            else:
                thumb_state["drag_y"] = h0 // 2
                _move_thumb_to(e.y - thumb_state["drag_y"])

        def on_sb_drag(e):
            _move_thumb_to(e.y - thumb_state["drag_y"])

        sb_canvas.bind("<ButtonPress-1>", on_sb_press)
        sb_canvas.bind("<B1-Motion>", on_sb_drag)
        sb_canvas.bind("<Configure>", redraw_thumb)

        h_listbox = tk.Listbox(
            list_frame,
            bg=white,
            fg=text_fg,
            selectbackground=shared.WIN95_ACTIVE_BG,
            selectforeground=shared.WIN95_ACTIVE_FG,
            font=("Courier New", 8),
            bd=0,
            highlightthickness=0,
            yscrollcommand=lambda f, l: redraw_thumb(f, l),
        )
        h_listbox.pack(side="left", fill="both", expand=True)
        listboxes.append(h_listbox)

        h_listbox.bind("<Configure>", redraw_thumb)
        h_listbox.bind("<MouseWheel>", lambda e: win.after_idle(redraw_thumb))
        h_listbox.bind("<Button-4>", lambda e: win.after_idle(redraw_thumb))
        h_listbox.bind("<Button-5>", lambda e: win.after_idle(redraw_thumb))

        entries = []

        def populate_history():
            entries.clear()
            entries.extend(load_history())
            h_listbox.delete(0, tk.END)
            for item in entries:
                h_listbox.insert(
                    tk.END,
                    f"[{item.get('timestamp', '')}] [{item.get('status', '')}] "
                    f"{item.get('title', '')} | {item.get('format', '')} ({item.get('quality', '')})",
                )
            win.after_idle(redraw_thumb)

        self._refresh_history = populate_history
        populate_history()

        btn_bar = tk.Frame(body, bg=bg)
        btn_bar.pack(fill="x", pady=(6, 0))
        bg_widgets.append(btn_bar)

        def selected_item():
            sel = h_listbox.curselection()
            if not sel:
                return None
            idx = sel[0]
            return entries[idx] if 0 <= idx < len(entries) else None

        def use_url():
            item = selected_item()
            if item and item.get("url"):
                self.on_use_url(item["url"])
                self.on_log(f"Loaded URL from history: {item['url']}")

        def open_folder():
            try:
                item = selected_item()
                folder = item.get("path") if item else self.fallback_dir
                if folder and os.path.exists(folder) and os.name == "nt":
                    os.startfile(folder)
            except:
                pass

        def open_history_file():
            try:
                if os.path.exists(shared.HISTORY_FILE) and os.name == "nt":
                    open_notepad_with_file(shared.HISTORY_FILE) # I might replace this lol
            except:
                pass

        def clear_all():
            clear_history()
            entries.clear()
            h_listbox.delete(0, tk.END)
            win.after_idle(redraw_thumb)

        use_btn = tk.Button(
            btn_bar,
            text="Use URL",
            bg=bg,
            fg=text_fg,
            activebackground=bg,
            activeforeground=text_fg,
            bd=2,
            relief=tk.RAISED,
            font=WIN95_FONT,
            command=use_url,
        )
        use_btn.pack(side="left", padx=(0, 4))
        btns.append(use_btn)

        open_btn = tk.Button(
            btn_bar,
            text="Open Folder",
            bg=bg,
            fg=text_fg,
            activebackground=bg,
            activeforeground=text_fg,
            bd=2,
            relief=tk.RAISED,
            font=WIN95_FONT,
            command=open_folder,
        )
        open_btn.pack(side="left", padx=(0, 4))
        btns.append(open_btn)

        open_history_file_btn = tk.Button(
            btn_bar,
            text="Open History File",
            bg=bg,
            fg=text_fg,
            activebackground=bg,
            activeforeground=text_fg,
            bd=2,
            relief=tk.RAISED,
            font=WIN95_FONT,
            command=open_history_file,
        )
        open_history_file_btn.pack(side="left", padx=(0, 4))
        btns.append(open_history_file_btn)

        clear_btn = tk.Button(
            btn_bar,
            text="Clear History",
            bg=bg,
            fg=text_fg,
            activebackground=bg,
            activeforeground=text_fg,
            bd=2,
            relief=tk.RAISED,
            font=WIN95_FONT,
            command=clear_all,
        )
        clear_btn.pack(side="right")
        btns.append(clear_btn)

        self._widgets = {
            "bg": bg_widgets,
            "white": white_widgets,
            "navy": navy_widgets,
            "title_label": title_labels,
            "btn": btns,
            "listbox": listboxes,
            "colors": {
                "bg": bg,
                "white": white,
                "text_fg": text_fg,
                "shadow_fg": shadow_fg,
            },
        }

        map_event = "<" + "Map" + ">"
        focus_event = "<" + "FocusIn" + ">"
        win.bind(map_event, lambda e: self.apply_theme())
        win.bind(focus_event, lambda e: self.apply_theme())