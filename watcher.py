"""
CadOwl File Watcher Service
============================
Watches Input folder for new files and auto-processes them.

- DXF files: Auto-convert to CSV
- DWG files: Notify user to run AutoCAD conversion

Run with: python watcher.py
Stop with: Ctrl+C
"""

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

# Paths - watch the parent CADtoSiteOwl folder's Input/Output
SCRIPT_DIR = Path(__file__).parent.resolve()
PARENT_DIR = SCRIPT_DIR.parent  # CADtoSiteOwl folder
INPUT_FOLDER = PARENT_DIR / "Input"
OUTPUT_FOLDER = PARENT_DIR / "Output"
CONVERTER_SCRIPT = SCRIPT_DIR / "cad2siteowl.py"
LOG_FILE = SCRIPT_DIR / "watcher.log"

# Track processed files to avoid duplicates
processed_files: Set[str] = set()
processing_queue: queue.Queue = queue.Queue()


def log(message: str, level: str = "INFO"):
    """Log to console and file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] [{level}] {message}"
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


def process_dxf(file_path: Path):
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
        # Run the converter
        result = subprocess.run(
            [sys.executable, str(CONVERTER_SCRIPT)],
            cwd=str(SCRIPT_DIR),
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode == 0:
            log(f"SUCCESS: Converted {file_path.name}")
            notify_user("CadOwl", f"Converted {file_path.name} to CSV!")
            
            # Try to open output folder
            try:
                subprocess.run(["explorer", str(OUTPUT_FOLDER)], timeout=5)
            except Exception:
                pass
        else:
            log(f"FAILED: {result.stderr[:200]}", "ERROR")
            notify_user("CadOwl Error", f"Failed to convert {file_path.name}")
            
    except subprocess.TimeoutExpired:
        log(f"TIMEOUT: Conversion took too long", "ERROR")
    except Exception as e:
        log(f"ERROR: {e}", "ERROR")


def handle_dwg(file_path: Path):
    """Handle DWG file - notify user to run AutoCAD."""
    file_key = str(file_path).lower()
    
    if file_key in processed_files:
        return
    
    processed_files.add(file_key)
    log(f"New DWG detected: {file_path.name}")
    
    notify_user(
        "CadOwl - DWG Found",
        f"New DWG: {file_path.name}\nRun DWG2DXFBATCH in AutoCAD to convert."
    )
    
    print("\n" + "=" * 50)
    print("  NEW DWG FILE DETECTED!")
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
            processing_queue.put(("dxf", file_path))
        elif ext == ".dwg":
            processing_queue.put(("dwg", file_path))


def process_queue():
    """Background thread to process queued files."""
    while True:
        try:
            item = processing_queue.get(timeout=1)
            file_type, file_path = item
            
            if file_type == "dxf":
                process_dxf(file_path)
            elif file_type == "dwg":
                handle_dwg(file_path)
                
            processing_queue.task_done()
        except queue.Empty:
            continue
        except Exception as e:
            log(f"Queue error: {e}", "ERROR")


def scan_existing_files():
    """Check for existing DXF files on startup."""
    log("Scanning for existing files...")
    
    dxf_files = list(INPUT_FOLDER.glob("*.dxf"))
    dwg_files = list(INPUT_FOLDER.glob("*.dwg"))
    
    if dxf_files:
        log(f"Found {len(dxf_files)} existing DXF file(s)")
        for f in dxf_files:
            # Check if already converted
            csv_name = f.stem.split()[0]  # Get store number part
            existing_csvs = list(OUTPUT_FOLDER.glob(f"*{csv_name}*.csv"))
            if not existing_csvs:
                processing_queue.put(("dxf", f))
    
    if dwg_files:
        log(f"Found {len(dwg_files)} DWG file(s) awaiting conversion")


def main():
    """Main entry point."""
    print()
    print("=" * 60)
    print("  CadOwl File Watcher")
    print("=" * 60)
    print()
    print(f"  Watching: {INPUT_FOLDER}")
    print(f"  Output:   {OUTPUT_FOLDER}")
    print()
    print("  Drop DXF files into Input/ for auto-conversion.")
    print("  Drop DWG files and I'll remind you to run AutoCAD.")
    print()
    print("  Press Ctrl+C to stop.")
    print()
    print("=" * 60)
    print()
    
    # Ensure folders exist
    INPUT_FOLDER.mkdir(exist_ok=True)
    OUTPUT_FOLDER.mkdir(exist_ok=True)
    
    log("CadOwl watcher starting...")
    
    # Start processing thread
    processor = threading.Thread(target=process_queue, daemon=True)
    processor.start()
    
    # Scan existing files
    scan_existing_files()
    
    # Set up file watcher
    handler = CadOwlHandler()
    observer = Observer()
    observer.schedule(handler, str(INPUT_FOLDER), recursive=False)
    observer.start()
    
    log(f"Watching {INPUT_FOLDER}")
    notify_user("CadOwl", "File watcher is running!")
    
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
