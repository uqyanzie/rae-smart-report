import os
import shutil
import subprocess
from pathlib import Path
import PyInstaller.__main__

def build_app():
    root = Path(__file__).resolve().parent.parent.parent.parent.parent
    
    # 1. Build frontend
    print("Building frontend with Vite...")
    subprocess.run(["npm", "run", "build"], cwd=root / "frontend", check=True, shell=True)
    
    # 2. Package with PyInstaller
    print("Packaging backend and frontend into standalone executable...")
    PyInstaller.__main__.run([
        str(root / "backend" / "app" / "main.py"),
        "--name=RAE-Smart-Report",
        "--onefile",
        "--windowed",
        f"--add-data={root / 'frontend' / 'dist'}{os.pathsep}frontend/dist",
        "--hidden-import=uvicorn.logging",
        "--hidden-import=uvicorn.loops",
        "--hidden-import=uvicorn.loops.auto",
        "--hidden-import=uvicorn.protocols",
        "--hidden-import=uvicorn.protocols.http",
        "--hidden-import=uvicorn.protocols.http.auto",
        "--hidden-import=uvicorn.protocols.websockets",
        "--hidden-import=uvicorn.protocols.websockets.auto",
        "--hidden-import=uvicorn.lifespan",
        "--hidden-import=uvicorn.lifespan.on",
        "--hidden-import=openpyxl",
        "--hidden-import=sqlalchemy.sql.default_comparator",
        "--clean",
        "--noconfirm",
    ])

if __name__ == "__main__":
    build_app()
