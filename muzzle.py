import tkinter as tk
from tkinter import filedialog
import threading
import subprocess
import os

MUZZLE_FORMATS = ["MP4", "MKV", "AVI", "MOV", "WEBM", "MP3", "WAV", "FLAC", "GIF"]

class MuzzleTab:
    def __init__(self, parent_frame, get_download_path_callback, log_callback):
        self.frame = tk.Frame(parent_frame, bg=parent_frame.cget("bg"))
        self.frame.pack(fill="both", expand=True)
        
        self.get_download_path = get_download_path_callback
        self.log = log_callback
        
        self.input_file_var = tk.StringVar()
        self.target_format_var = tk.StringVar(value="MP4")
        self.output_dir_var = tk.StringVar(value=self.get_download_path())
        
        self._build_ui()

    def _build_ui(self):
        bg = self.frame.cget("bg")
        
        self.input_frame = tk.LabelFrame(self.frame, text="Input File", bg=bg, fg="black", font=("MS Sans Serif", 8, "bold"), bd=2, relief=tk.GROOVE)
        self.input_frame.pack(fill="x", padx=4, pady=4, ipadx=4, ipady=4)

        self.input_entry = tk.Entry(self.input_frame, textvariable=self.input_file_var, bg="white", fg="black", bd=2, relief=tk.SUNKEN, font=("MS Sans Serif", 8))
        self.input_entry.pack(side="left", fill="x", expand=True, padx=(4, 2), pady=4)
        self.input_entry.bind("<KeyRelease>", lambda e: self.update_command_preview())

        self.browse_btn = tk.Button(self.input_frame, text="Browse...", bg=bg, fg="black", bd=2, relief=tk.RAISED, font=("MS Sans Serif", 8), command=self.browse_input_file)
        self.browse_btn.pack(side="right", padx=(2, 4), pady=4)

        settings_frame = tk.Frame(self.frame, bg=bg)
        settings_frame.pack(fill="x", padx=4, pady=4)

        tk.Label(settings_frame, text="Target Format:", bg=bg, fg="black", font=("MS Sans Serif", 8)).pack(side="left", padx=(0, 4))
        
        self.format_container = tk.Frame(settings_frame, bg="white", bd=2, relief=tk.SUNKEN)
        self.format_container.pack(side="left", padx=(0, 12))

        self.format_label = tk.Label(self.format_container, textvariable=self.target_format_var, bg="white", fg="black", font=("MS Sans Serif", 8), width=6, anchor="w")
        self.format_label.pack(side="left", padx=(2, 0))

        self.format_btn = tk.Button(self.format_container, text="▼", bg=bg, fg="black", font=("MS Sans Serif", 7), bd=1, relief=tk.RAISED, width=2, height=1, command=self._toggle_format_dropdown)
        self.format_btn.pack(side="right", fill="y")

        self.format_label.bind("<Button-1>", lambda e: self._toggle_format_dropdown())
        self.format_container.bind("<Button-1>", lambda e: self._toggle_format_dropdown())

        out_frame = tk.LabelFrame(self.frame, text="Output Directory", bg=bg, fg="black", font=("MS Sans Serif", 8, "bold"), bd=2, relief=tk.GROOVE)
        out_frame.pack(fill="x", padx=4, pady=4, ipadx=4, ipady=4)

        self.out_entry = tk.Entry(out_frame, textvariable=self.output_dir_var, bg="white", fg="black", bd=2, relief=tk.SUNKEN, font=("MS Sans Serif", 8))
        self.out_entry.pack(side="left", fill="x", expand=True, padx=(4, 2), pady=4)
        self.out_entry.bind("<KeyRelease>", lambda e: self.update_command_preview())

        out_browse_btn = tk.Button(out_frame, text="Browse...", bg=bg, fg="black", bd=2, relief=tk.RAISED, font=("MS Sans Serif", 8), command=self.browse_output_folder)
        out_browse_btn.pack(side="right", padx=(2, 4), pady=4)

        self.cmd_frame = tk.LabelFrame(self.frame, text="Dynamic FFmpeg Command", bg=bg, fg="black", font=("MS Sans Serif", 8, "bold"), bd=2, relief=tk.GROOVE)
        self.cmd_frame.pack(fill="both", expand=True, padx=4, pady=4, ipadx=4, ipady=4)

        self.cmd_box = tk.Text(self.cmd_frame, height=5, bg="white", fg="black", bd=2, relief=tk.SUNKEN, font=("Courier New", 8))
        self.cmd_box.pack(fill="both", expand=True, padx=4, pady=4)
        self.cmd_box.config(state="disabled")

        self.convert_btn = tk.Button(self.frame, text="Convert File", bg=bg, fg="black", bd=2, relief=tk.RAISED, font=("MS Sans Serif", 9, "bold"), command=self.start_conversion_thread)
        self.convert_btn.pack(fill="x", padx=4, pady=(4, 8))

        self.update_command_preview()

    def browse_input_file(self):
        file_path = filedialog.askopenfilename()
        if file_path:
            self.input_file_var.set(file_path)
            self.update_command_preview()

    def browse_output_folder(self):
        folder_path = filedialog.askdirectory(initialdir=self.output_dir_var.get())
        if folder_path:
            self.output_dir_var.set(folder_path)
            self.update_command_preview()

    def _toggle_format_dropdown(self):
        menu = tk.Menu(self.frame, tearoff=0, relief=tk.RAISED, bd=2)
        for fmt in MUZZLE_FORMATS:
            menu.add_command(label=fmt, command=lambda f=fmt: self._select_format(f))
        
        x = self.format_container.winfo_rootx()
        y = self.format_container.winfo_rooty() + self.format_container.winfo_height()
        menu.post(x, y)

    def _select_format(self, fmt):
        self.target_format_var.set(fmt)
        self.update_command_preview()

    def update_command_preview(self):
        current_shared = self.get_download_path()
        if not self.output_dir_var.get().strip():
            self.output_dir_var.set(current_shared)

        inp = self.input_file_var.get().strip() or "input.ext"
        fmt = self.target_format_var.get().strip().lower() or "mp4"
        out_dir = self.output_dir_var.get().strip() or current_shared
        
        base_name = os.path.splitext(os.path.basename(inp))[0]
        output_file = os.path.join(out_dir, f"{base_name}_converted.{fmt}")
        
        cmd = f"ffmpeg -i \"{inp}\" \"{output_file}\""
        
        self.cmd_box.config(state="normal")
        self.cmd_box.delete("1.0", tk.END)
        self.cmd_box.insert(tk.END, cmd)
        self.cmd_box.config(state="disabled")

    def start_conversion_thread(self):
        inp = self.input_file_var.get().strip()
        if not inp or not os.path.exists(inp):
            self.log("Muzzle Error: Please select a valid input file.")
            return
        
        self.convert_btn.config(state="disabled")
        self.log("Starting Muzzle conversion thread...")
        threading.Thread(target=self._run_conversion, daemon=True).start()

    def _run_conversion(self):
        inp = self.input_file_var.get().strip()
        fmt = self.target_format_var.get().strip().lower()
        out_dir = self.output_dir_var.get().strip() or self.get_download_path()
        
        os.makedirs(out_dir, exist_ok=True)
        base_name = os.path.splitext(os.path.basename(inp))[0]
        output_file = os.path.join(out_dir, f"{base_name}_converted.{fmt}")

        cmd = ["ffmpeg", "-y", "-i", inp, output_file]
        
        self.log(f"Executing: {' '.join(cmd)}")
        
        try:
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT, 
                universal_newlines=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            )
            
            for line in process.stdout:
                line_str = line.strip()
                if line_str:
                    pass
            
            process.wait()
            if process.returncode == 0:
                self.log(f"Muzzle conversion completed: {output_file}")
            else:
                self.log("Muzzle Error: FFmpeg process failed.")
        except Exception as e:
            self.log(f"Muzzle Exception: {e}")
        finally:
            self.frame.after(0, lambda: self.convert_btn.config(state="normal"))