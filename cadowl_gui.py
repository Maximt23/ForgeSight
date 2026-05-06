#!/usr/bin/env python3
"""
CadOwl GUI - Simple launcher with Start/Stop
Supports CCTV and Fire Alarm/Intrusion workflows
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import subprocess
import sys
from pathlib import Path

# Walmart colors
BLUE = "#0053e2"
SPARK = "#ffc220"
WHITE = "#ffffff"
GRAY_BG = "#f5f5f5"
GRAY_TEXT = "#333333"
GREEN = "#2a8703"
RED = "#ea1100"

# System-specific folder paths
CCTV_INPUT = Path(r"C:\Users\vn59j7j\OneDrive - Walmart Inc\Master Excel Pathing\CADtoSiteOwl\Stores_COPY")
FA_INPUT = Path(__file__).parent.resolve() / "Input-FA"
CCTV_OUTPUT = Path(__file__).parent.resolve() / "Output-CCTV"
FA_OUTPUT = Path(__file__).parent.resolve() / "Output-Fire"


class CadOwlApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🦉 CadOwl Converter")
        self.root.geometry("500x420")
        self.root.configure(bg=WHITE)
        self.root.resizable(False, False)
        
        # State
        self.process = None
        self.running = False
        self.script_dir = Path(__file__).parent.resolve()
        
        # Ensure folders exist
        FA_INPUT.mkdir(parents=True, exist_ok=True)
        CCTV_OUTPUT.mkdir(parents=True, exist_ok=True)
        FA_OUTPUT.mkdir(parents=True, exist_ok=True)
        
        self.setup_ui()
    
    def setup_ui(self):
        # Header
        header = tk.Frame(self.root, bg=BLUE, height=60)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        title = tk.Label(
            header, 
            text="🦉 CadOwl", 
            font=("Segoe UI", 18, "bold"),
            fg=WHITE, 
            bg=BLUE
        )
        title.pack(pady=15)
        
        # Main content
        content = tk.Frame(self.root, bg=WHITE, padx=30, pady=20)
        content.pack(fill="both", expand=True)
        
        # System type selection
        system_frame = tk.Frame(content, bg=WHITE)
        system_frame.pack(fill="x", pady=(0, 10))
        
        tk.Label(
            system_frame, 
            text="System:", 
            font=("Segoe UI", 10, "bold"),
            bg=WHITE, 
            fg=GRAY_TEXT
        ).pack(side="left")
        
        self.system_var = tk.StringVar(value="cctv")
        
        cctv_radio = ttk.Radiobutton(
            system_frame, 
            text="📹 CCTV", 
            variable=self.system_var, 
            value="cctv",
            command=self.on_system_change
        )
        cctv_radio.pack(side="left", padx=(10, 5))
        
        fa_radio = ttk.Radiobutton(
            system_frame, 
            text="🔥 Fire Alarm / Intrusion", 
            variable=self.system_var, 
            value="fa",
            command=self.on_system_change
        )
        fa_radio.pack(side="left", padx=5)
        
        # Mode selection
        mode_frame = tk.Frame(content, bg=WHITE)
        mode_frame.pack(fill="x", pady=(0, 15))
        
        tk.Label(
            mode_frame, 
            text="Mode:", 
            font=("Segoe UI", 10),
            bg=WHITE, 
            fg=GRAY_TEXT
        ).pack(side="left")
        
        self.mode_var = tk.StringVar(value="enhanced")
        
        ttk.Radiobutton(
            mode_frame, 
            text="Enhanced (with Excel)", 
            variable=self.mode_var, 
            value="enhanced"
        ).pack(side="left", padx=(10, 5))
        
        ttk.Radiobutton(
            mode_frame, 
            text="Basic (CAD only)", 
            variable=self.mode_var, 
            value="basic"
        ).pack(side="left", padx=5)
        
        # Path display
        self.path_label = tk.Label(
            content,
            text="",
            font=("Segoe UI", 8),
            bg=WHITE,
            fg="#666666",
            wraplength=380
        )
        self.path_label.pack(fill="x", pady=(0, 10))
        self.on_system_change()  # Update path display
        
        # Status
        self.status_frame = tk.Frame(content, bg=GRAY_BG, padx=15, pady=15)
        self.status_frame.pack(fill="x", pady=(0, 20))
        
        self.status_label = tk.Label(
            self.status_frame,
            text="Ready",
            font=("Segoe UI", 11),
            bg=GRAY_BG,
            fg=GRAY_TEXT
        )
        self.status_label.pack()
        
        self.status_detail = tk.Label(
            self.status_frame,
            text="Place DXF files in Input folder, then click Start",
            font=("Segoe UI", 9),
            bg=GRAY_BG,
            fg="#666666"
        )
        self.status_detail.pack(pady=(5, 0))
        
        # Buttons
        btn_frame = tk.Frame(content, bg=WHITE)
        btn_frame.pack(fill="x", pady=(0, 10))
        
        self.start_btn = tk.Button(
            btn_frame,
            text="▶  Start",
            font=("Segoe UI", 11, "bold"),
            bg=BLUE,
            fg=WHITE,
            activebackground="#0042b3",
            activeforeground=WHITE,
            relief="flat",
            padx=30,
            pady=10,
            cursor="hand2",
            command=self.start_conversion
        )
        self.start_btn.pack(side="left", expand=True, fill="x", padx=(0, 5))
        
        self.stop_btn = tk.Button(
            btn_frame,
            text="⬛  Stop",
            font=("Segoe UI", 11, "bold"),
            bg=RED,
            fg=WHITE,
            activebackground="#c40000",
            activeforeground=WHITE,
            relief="flat",
            padx=30,
            pady=10,
            cursor="hand2",
            command=self.stop_conversion,
            state="disabled"
        )
        self.stop_btn.pack(side="left", expand=True, fill="x", padx=(5, 0))
        
        # Folder buttons
        folder_frame = tk.Frame(content, bg=WHITE)
        folder_frame.pack(fill="x", pady=(10, 0))
        
        open_input_btn = tk.Button(
            folder_frame,
            text="📂 Open Input",
            font=("Segoe UI", 9),
            bg=GRAY_BG,
            fg=GRAY_TEXT,
            relief="flat",
            padx=15,
            pady=5,
            cursor="hand2",
            command=self.open_input_folder
        )
        open_input_btn.pack(side="left", expand=True, fill="x", padx=(0, 3))
        
        open_output_btn = tk.Button(
            folder_frame,
            text="📁 Open Output",
            font=("Segoe UI", 9),
            bg=GRAY_BG,
            fg=GRAY_TEXT,
            relief="flat",
            padx=15,
            pady=5,
            cursor="hand2",
            command=self.open_output_folder
        )
        open_output_btn.pack(side="left", expand=True, fill="x", padx=(3, 0))
        
        # Footer
        footer = tk.Label(
            self.root,
            text="CAD coordinates + Excel naming → SiteOwl CSV",
            font=("Segoe UI", 8),
            bg=WHITE,
            fg="#999999"
        )
        footer.pack(pady=(0, 10))
    
    def set_status(self, status: str, detail: str = "", color: str = GRAY_TEXT):
        self.status_label.config(text=status, fg=color)
        self.status_detail.config(text=detail)
    
    def get_input_folder(self) -> Path:
        """Get input folder based on selected system"""
        return CCTV_INPUT if self.system_var.get() == "cctv" else FA_INPUT
    
    def get_output_folder(self) -> Path:
        """Get output folder based on selected system"""
        return CCTV_OUTPUT if self.system_var.get() == "cctv" else FA_OUTPUT
    
    def on_system_change(self):
        """Update path display when system changes"""
        input_folder = self.get_input_folder()
        output_folder = self.get_output_folder()
        self.path_label.config(
            text=f"Input: {input_folder}\nOutput: {output_folder}"
        )
    
    def start_conversion(self):
        if self.running:
            return
        
        # Check for DXF files in system-specific folder
        input_folder = self.get_input_folder()
        if not input_folder.exists():
            input_folder.mkdir(parents=True)
        
        dxf_files = list(input_folder.glob("*.dxf"))
        if not dxf_files:
            messagebox.showwarning(
                "No DXF Files",
                f"No .dxf files found in:\n{input_folder}\n\nConvert DWG files in AutoCAD first!"
            )
            return
        
        self.running = True
        self.start_btn.config(state="disabled", bg="#cccccc")
        self.stop_btn.config(state="normal")
        self.set_status("⏳ Running...", f"Processing {len(dxf_files)} DXF file(s)", BLUE)
        
        # Run in thread
        thread = threading.Thread(target=self.run_conversion, daemon=True)
        thread.start()
    
    def run_conversion(self):
        try:
            # Select script based on mode
            if self.mode_var.get() == "enhanced":
                script = self.script_dir / "cad2siteowl_enhanced.py"
            else:
                script = self.script_dir / "cad2siteowl.py"
            
            if not script.exists():
                self.root.after(0, lambda: self.conversion_done(False, f"Script not found: {script.name}"))
                return
            
            # Run the script with input/output folder arguments
            input_folder = self.get_input_folder()
            output_folder = self.get_output_folder()
            
            self.process = subprocess.Popen(
                [sys.executable, str(script), 
                 "--input", str(input_folder),
                 "--output", str(output_folder)],
                cwd=str(self.script_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            
            output_lines = []
            for line in self.process.stdout:
                output_lines.append(line.strip())
                # Update status with last meaningful line
                if "Processing:" in line or "SUCCESS:" in line or "Found" in line:
                    self.root.after(0, lambda l=line.strip(): self.set_status("⏳ Running...", l[:60], BLUE))
            
            self.process.wait()
            
            if self.process.returncode == 0:
                self.root.after(0, lambda: self.conversion_done(True, "Check Output folder for CSV files"))
            else:
                self.root.after(0, lambda: self.conversion_done(False, "Check console for errors"))
        
        except Exception as e:
            self.root.after(0, lambda: self.conversion_done(False, str(e)))
    
    def conversion_done(self, success: bool, message: str):
        self.running = False
        self.process = None
        self.start_btn.config(state="normal", bg=BLUE)
        self.stop_btn.config(state="disabled")
        
        if success:
            self.set_status("✅ Complete!", message, GREEN)
        else:
            self.set_status("❌ Error", message, RED)
    
    def stop_conversion(self):
        if self.process:
            self.process.terminate()
            self.set_status("⛔ Stopped", "Conversion cancelled by user", RED)
        
        self.running = False
        self.start_btn.config(state="normal", bg=BLUE)
        self.stop_btn.config(state="disabled")
    
    def open_input_folder(self):
        folder = self.get_input_folder()
        folder.mkdir(parents=True, exist_ok=True)
        subprocess.Popen(f'explorer "{folder}"')
    
    def open_output_folder(self):
        folder = self.get_output_folder()
        folder.mkdir(parents=True, exist_ok=True)
        subprocess.Popen(f'explorer "{folder}"')


def main():
    root = tk.Tk()
    
    # Set icon if available
    try:
        root.iconbitmap(Path(__file__).parent / "icon.ico")
    except:
        pass
    
    app = CadOwlApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
