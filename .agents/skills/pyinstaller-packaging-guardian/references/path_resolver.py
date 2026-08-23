import os
import sys
from pathlib import Path

def get_bundle_dir() -> Path:
    """
    Returns the base directory of bundled assets.
    In packaged mode: returns sys._MEIPASS (temporary extraction folder).
    In dev mode: returns the repository root.
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent.parent.parent

def get_writable_app_dir(app_name: str = "RAESmartReport") -> Path:
    """
    Returns a guaranteed writable user directory for persistent database storage.
    On Windows: %LOCALAPPDATA%/RAESmartReport
    Fallback: Directory containing the .exe or project root.
    """
    if sys.platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            target_dir = Path(local_app_data) / app_name
            target_dir.mkdir(parents=True, exist_ok=True)
            return target_dir
            
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent.parent.parent

def get_database_path(db_name: str = "app_data.db") -> str:
    """Returns absolute path to the persistent SQLite database."""
    return str(get_writable_app_dir() / db_name)
