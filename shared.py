import os
import sys
import json
import ctypes

FETCH_TITLE = "Fetch"
APP_VERSION = "1.6.0"

SIZE_X = 540
SIZE_Y = 470

CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".fetch_presets.json")

def resource_path(relative_path="."):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    
    if relative_path.startswith("./"):
        relative_path = relative_path[2:]

    if relative_path in ("icon.ico", "icon.png", "art.txt"):
        relative_path = os.path.join("assets", relative_path)
        
    return os.path.join(base_path, relative_path)

DEFAULT_THEME = {
    "WIN95_BG": "#C0C0C0",
    "WIN95_TEAL": "#008080",
    "WIN95_NAVY": "#000080",
    "WIN95_WHITE": "#FFFFFF",
    "WIN95_TEXT": "#000000",
    "WIN95_DISABLED": "#000000",
    "WIN95_TITLE_TEXT": "#FFFFFF",
    "WIN95_ACTIVE_FG": "#FFFFFF",
    "WIN95_ACTIVE_BG": "#000080"
}

def load_available_themes():
    themes = {"Windows 95": DEFAULT_THEME}
    themes_dir = resource_path("themes")
    if os.path.exists(themes_dir) and os.path.isdir(themes_dir):
        for filename in os.listdir(themes_dir):
            if filename.endswith(".json"):
                theme_name = filename[:-5].replace("_", " ").title()
                path = os.path.join(themes_dir, filename)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        themes[theme_name] = {**DEFAULT_THEME, **data}
                except Exception:
                    pass
    return themes

AVAILABLE_THEMES = load_available_themes()

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_config(config_data):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4)
    except Exception:
        pass

def load_theme():
    config = load_config()
    saved_theme_name = config.get("selected_theme", "Windows 95")
    if saved_theme_name in AVAILABLE_THEMES:
        return AVAILABLE_THEMES[saved_theme_name]
    return DEFAULT_THEME

THEME = load_theme()

WIN95_BG = THEME["WIN95_BG"]
WIN95_TEAL = THEME["WIN95_TEAL"]
WIN95_NAVY = THEME["WIN95_NAVY"]
WIN95_WHITE = THEME["WIN95_WHITE"]
WIN95_TEXT = THEME["WIN95_TEXT"]
WIN95_DISABLED = THEME["WIN95_DISABLED"]
WIN95_TITLE_TEXT = THEME.get("WIN95_TITLE_TEXT", "#FFFFFF")
WIN95_ACTIVE_FG = THEME.get("WIN95_ACTIVE_FG", "#FFFFFF")
WIN95_ACTIVE_BG = THEME.get("WIN95_ACTIVE_BG", "#000080")

WIN95_FONT = ("MS Sans Serif", 9)
WIN95_FONT_BOLD = ("MS Sans Serif", 9, "bold")

WIN95_DEFAULT_BTN_TEXT = "Download"

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