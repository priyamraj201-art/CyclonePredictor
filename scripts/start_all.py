"""Convenience Launcher: Start both FastAPI Backend and Vite Frontend simultaneously."""

import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import subprocess
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent


def main():
    print("=" * 65)
    print("   CYCLONE AI SYSTEM — DUAL SERVICE LAUNCHER")
    print("   Backend:  http://localhost:8000 (FastAPI Swagger Docs at /docs)")
    print("   Frontend: http://localhost:5173 (Mission-Control Dashboard)")
    print("=" * 65)

    backend_cmd = [sys.executable, "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
    frontend_dir = ROOT_DIR / "frontend"

    print("\n[1/2] Spawning FastAPI Inference Server...")
    backend_proc = subprocess.Popen(backend_cmd, cwd=ROOT_DIR)

    time.sleep(2)

    print("[2/2] Spawning Vite React Dashboard...")
    if sys.platform == "win32":
        frontend_proc = subprocess.Popen(["npm.cmd", "run", "dev"], cwd=frontend_dir)
    else:
        frontend_proc = subprocess.Popen(["npm", "run", "dev"], cwd=frontend_dir)

    print("\n>> BOTH SERVICES ARE RUNNING! Press Ctrl+C to terminate both.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nTerminating services...")
        backend_proc.terminate()
        frontend_proc.terminate()
        backend_proc.wait()
        frontend_proc.wait()
        print("Done.")


if __name__ == "__main__":
    main()
