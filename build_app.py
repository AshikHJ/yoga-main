import os
import shutil
import stat
import subprocess
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

def force_remove_readonly(func, path, exc_info):
    """Clear the readonly bit and retry deletion."""
    os.chmod(path, stat.S_IWRITE)
    func(path)

def clean_dir(d: Path):
    if d.exists():
        for _ in range(3):
            try:
                shutil.rmtree(d, onerror=force_remove_readonly)
                break
            except Exception:
                time.sleep(0.5)

def build():
    print("=" * 60)
    print("       Building KI.AI Standalone Windows Application")
    print("=" * 60)

    # 1. Clean previous build artifacts
    dist_dir = BASE_DIR / "dist"
    build_dir = BASE_DIR / "build"
    clean_dir(dist_dir)
    clean_dir(build_dir)

    # 2. PyInstaller command for Desktop Native App
    pyinstaller_desktop_cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--name=KI_AI_Yoga_Assistant",
        "--add-data=data;data",
        "--add-data=assets;assets",
        "--add-data=database/schema.sql;database",
        "--add-data=templates;templates",
        "--hidden-import=PySide6.QtSvg",
        "--hidden-import=PySide6.QtCore",
        "--hidden-import=PySide6.QtWidgets",
        "--hidden-import=PySide6.QtGui",
        "--hidden-import=mediapipe",
        "--hidden-import=cv2",
        "--hidden-import=pyttsx3",
        "--hidden-import=pyttsx3.drivers",
        "--hidden-import=pyttsx3.drivers.sapi5",
        "--hidden-import=matplotlib",
        "--hidden-import=flask",
        "--hidden-import=flask_cors",
        "app.py"
    ]

    print("\n[1/2] Building Desktop Application (app.py)...")
    res1 = subprocess.run(pyinstaller_desktop_cmd, cwd=str(BASE_DIR))
    if res1.returncode != 0:
        print("Desktop build failed!")
        return False

    print("\n[2/2] Build successful! Output located at dist/KI_AI_Yoga_Assistant/")
    print("\nTo launch the desktop app, run:")
    print("  dist\\KI_AI_Yoga_Assistant\\KI_AI_Yoga_Assistant.exe")
    return True

if __name__ == "__main__":
    success = build()
    sys.exit(0 if success else 1)
