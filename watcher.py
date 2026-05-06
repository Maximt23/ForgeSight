"""
CadOwl File Watcher Service
============================
Watches Input folder for new files and auto-processes them.

- DXF files: Auto-convert to CSV
- DWG files: Notify user to run AutoCAD conversion

Run with: 
  python watcher.py              # Default FA mode
  python watcher.py --system fa   # Fire Alarm/Intrusion
  python watcher.py --system cctv # CCTV

Stop with: Ctrl+C
"""

import argparse
import sys
import time
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Set
import threading
import queue

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileMovedEvent
except ImportError:
    print("ERROR: watchdog not installed. Run: uv pip install watchdog")
    sys.exit(1)

# Base paths
SCRIPT_DIR = Path(__file__).parent.resolve()
ONEDRIVE_BASE = Path(r"C:\Users\vn59j7j\OneDrive - Walmart Inc\Master Excel Pathing\CADtoSiteOwl")

# System-specific paths
SYSTEM_PATHS = {
    "fa": {
        "name": "Fire Alarm / Intrusion",
        "icon": "🔥",
        "input": ONEDRIVE_BASE / "Input-FA",
        "output": ONEDRIVE_BASE / "Output-Fire",
        "color": "0C"  # Red
    },
    "cctv": {
        "name": "CCTV",
        "icon": "📹",
        "input": ONEDRIVE_BASE / "Input-CCTV",
        "output": ONEDRIVE_BASE / "Output-CCTV",
        "color": "0B"  # Cyan
    }
}

CONVERTER_SCRIPT = SCRIPT_DIR / "cad2siteowl_enhanced.py"
LOG_FILE = SCRIPT_DIR / "watcher.log"

# Track processed files to avoid duplicates
processed_files: Set[str] = set()
processing_queue: queue.Queue = queue.Queue()

# Global system type
current_system = "fa"


def log(message: str, level: str = "INFO"):
    """Log to console and file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] [{current_system.upper()}] [{level}] {message}"
    print(line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def notify_user(title: str, message: str):
    """Show Windows notification."""
    try:
        # Use PowerShell for toast notification
        ps_script = f'''
        [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
        [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
        $template = @"
        <toast>
            <visual>
                <binding template="ToastText02">
                    <text id="1">{title}</text>
                    <text id="2">{message}</text>
                </binding>
            </visual>
        </toast>
"@
        $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
        $xml.LoadXml($template)
        $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
        [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("CadOwl").Show($toast)
        '''
        subprocess.run(
            ["powershell", "-Command", ps_script],
            capture_output=True,
            timeout=5
        )
    except Exception as e:
        log(f"Notification failed: {e}", "WARN")


def process_dxf(file_path: Path, system_config: dict):
    """Process a single DXF file."""
    file_key = str(file_path).lower()
    
    if file_key in processed_files:
        return
    
    # Wait for file to finish writing
    time.sleep(1)
    
    if not file_path.exists():
        return
    
    log(f"Processing DXF: {file_path.name}")
    processed_files.add(file_key)
    
    try:
        # Run the converter with system-specific paths
        result = subprocess.run(
            [
                sys.executable, 
                str(CONVERTER_SCRIPT),
                "--input", str(system_config["input"]),
                "--output", str(system_config["output"]),
                "--system", current_system
            ],
            cwd=str(SCRIPT_DIR),
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode == 0:
            log(f"SUCCESS: Converted {file_path.name}")
            notify_user(f"CadOwl {system_config['icon']}", f"Converted {file_path.name} to CSV!")
            
            # Try to open output folder
            try:
                subprocess.run(["explorer", str(system_config["output"])], timeout=5)
            except Exception:
                pass
        else:
            log(f"FAILED: {result.stderr[:200]}", "ERROR")
            notify_user(f"CadOwl {system_config['icon']} Error", f"Failed to convert {file_path.name}")
            
    except subprocess.TimeoutExpired:
        log(f"TIMEOUT: Conversion took too long", "ERROR")
    except Exception as e:
        log(f"ERROR: {e}", "ERROR")


def handle_dwg(file_path: Path, system_config: dict):
    """Handle DWG file - notify user to run AutoCAD."""
    file_key = str(file_path).lower()
    
    if file_key in processed_files:
        return
    
    processed_files.add(file_key)
    log(f"New DWG detected: {file_path.name}")
    
    notify_user(
        f"CadOwl {system_config['icon']} - DWG Found",
        f"New DWG: {file_path.name}\nRun DWG2DXFBATCH in AutoCAD to convert."
    )
    
    print("\n" + "=" * 50)
    print(f"  NEW DWG FILE DETECTED! ({system_config['name']})")
    print("=" * 50)
    print(f"  File: {file_path.name}")
    print()
    print("  To convert, open AutoCAD and run:")
    print()
    print(f'  (load "{str(SCRIPT_DIR / "DWG2DXF.lsp").replace(chr(92), "/")}")')
    print("  DWG2DXFBATCH")
    print()
    print("  The DXF will be auto-processed when ready.")
    print("=" * 50 + "\n")


class CadOwlHandler(FileSystemEventHandler):
    """Handle file system events."""
    
    def __init__(self, system_config: dict):
        self.system_config = system_config
        super().__init__()
    
    def on_created(self, event):
        if event.is_directory:
            return
        self._handle_file(Path(event.src_path))
    
    def on_moved(self, event):
        if event.is_directory:
            return
        self._handle_file(Path(event.dest_path))
    
    def _handle_file(self, file_path: Path):
        """Route file to appropriate handler."""
        ext = file_path.suffix.lower()
        
        if ext == ".dxf":
            # Queue for processing (avoid blocking the observer)
            processing_queue.put(("dxf", file_path, self.system_config))
        elif ext == ".dwg":
            processing_queue.put(("dwg", file_path, self.system_config))


def process_queue():
    """Background thread to process queued files."""
    while True:
        try:
            item = processing_queue.get(timeout=1)
            file_type, file_path, system_config = item
            
            if file_type == "dxf":
                process_dxf(file_path, system_config)
            elif file_type == "dwg":
                handle_dwg(file_path, system_config)
                
            processing_queue.task_done()
        except queue.Empty:
            continue
        except Exception as e:
            log(f"Queue error: {e}", "ERROR")


def scan_existing_files(system_config: dict):
    """Check for existing DXF files on startup."""
    input_folder = system_config["input"]
    output_folder = system_config["output"]
    
    log("Scanning for existing files...")
    
    dxf_files = list(input_folder.glob("*.dxf"))
    dwg_files = list(input_folder.glob("*.dwg"))
    
    if dxf_files:
        log(f"Found {len(dxf_files)} existing DXF file(s)")
        for f in dxf_files:
            # Check if already converted
            csv_name = f.stem.split()[0]  # Get store number part
            existing_csvs = list(output_folder.glob(f"*{csv_name}*.csv"))
            if not existing_csvs:
                processing_queue.put(("dxf", f, system_config))
    
    if dwg_files:
        log(f"Found {len(dwg_files)} DWG file(s) awaiting conversion")


def main():
    """Main entry point."""
    global current_system
    
    parser = argparse.ArgumentParser(description="CadOwl File Watcher")
    parser.add_argument("--system", "-s", choices=["fa", "cctv"], default="fa",
                        help="System type: 'fa' for Fire Alarm/Intrusion, 'cctv' for CCTV")
    args = parser.parse_args()
    
    current_system = args.system
    system_config = SYSTEM_PATHS[current_system]
    
    input_folder = system_config["input"]
    output_folder = system_config["output"]
    
    print()
    print("=" * 60)
    print(f"  CadOwl File Watcher {system_config['icon']} {system_config['name']}")
    print("=" * 60)
    print()
    print(f"  System:   {current_system.upper()}")
    print(f"  Watching: {input_folder}")
    print(f"  Output:   {output_folder}")
    print()
    print("  Drop DXF files into Input folder for auto-conversion.")
    print("  Drop DWG files and I'll remind you to run AutoCAD.")
    print()
    print("  Press Ctrl+C to stop.")
    print()
    print("=" * 60)
    print()
    
    # Ensure folders exist
    input_folder.mkdir(parents=True, exist_ok=True)
    output_folder.mkdir(parents=True, exist_ok=True)
    
    log("CadOwl watcher starting...")
    
    # Start processing thread
    processor = threading.Thread(target=process_queue, daemon=True)
    processor.start()
    
    # Scan existing files
    scan_existing_files(system_config)
    
    # Set up file watcher
    handler = CadOwlHandler(system_config)
    observer = Observer()
    observer.schedule(handler, str(input_folder), recursive=False)
    observer.start()
    
    log(f"Watching {input_folder}")
    notify_user(f"CadOwl {system_config['icon']}", f"{system_config['name']} watcher is running!")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log("Shutting down...")
        observer.stop()
    
    observer.join()
    log("CadOwl watcher stopped.")


if __name__ == "__main__":
    main()
