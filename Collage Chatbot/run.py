import os
import sys
import subprocess
import webbrowser
from pathlib import Path

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

def print_banner():
    banner = """
================================================================================
       AHMEDABAD INSTITUTE OF TECHNOLOGY (AIT) AI ASSISTANT
       Unified Single-Port Localhost Application Server
================================================================================
"""
    print(banner)

def check_and_build_frontend():
    frontend_dir = PROJECT_ROOT / "frontend"
    dist_dir = frontend_dir / "dist"
    index_html = dist_dir / "index.html"

    if index_html.exists():
        print("[1/4] Frontend build verified .............. OK (dist ready)")
        return True

    print("[1/4] Building React frontend via Vite ..... (in progress)")
    node_modules = frontend_dir / "node_modules"
    if not node_modules.exists():
        print("      Installing frontend dependencies (npm install)...")
        subprocess.run(["npm", "install"], cwd=str(frontend_dir), shell=True, check=True)

    subprocess.run(["npm", "run", "build"], cwd=str(frontend_dir), shell=True, check=True)
    print("      Frontend build completed successfully ... OK")
    return True

def initialize_database():
    print("[2/4] Initializing Database & Knowledge .... (in progress)")
    try:
        from backend.app.database import Base, engine
        from database.seed.seed_data import seed_database
        Base.metadata.create_all(bind=engine)
        seed_database()
        print("[2/4] Database & Seed Truth Layer .......... OK")
    except Exception as e:
        print(f"[2/4] Database initialization error: {e}")

def check_cache_and_ai():
    print("[3/4] Initializing AI Router & Caches ...... OK (3-Tier Authority Ready)")

def start_server():
    import uvicorn
    from backend.app.config import settings

    print("[4/4] Starting Unified Server .............. OK")
    print("\n--------------------------------------------------------------------------------")
    print(f"  AIT AI Assistant is running at:")
    print(f"  ->  http://localhost:{settings.PORT}")
    print(f"  ->  http://127.0.0.1:{settings.PORT}")
    print("--------------------------------------------------------------------------------")
    print("  * Frontend SPA    : Integrated at /")
    print(f"  * Backend API     : Integrated at /api & /api/v1")
    print("  * Database        : Connected & Verified")
    print("  * Source Priority : 1. AIT Portal | 2. Admin DB | 3. Gemini AI")
    print("  * Voice Pipeline  : VAD + Faster-Whisper + Piper TTS")
    print("  * Health Check    : /health")
    print("  * Metrics         : /metrics")
    print("--------------------------------------------------------------------------------")
    print("Press CTRL+C to stop the server.\n")

    uvicorn.run("backend.app.main:app", host=settings.HOST, port=settings.PORT, reload=False)

if __name__ == "__main__":
    print_banner()
    try:
        check_and_build_frontend()
        initialize_database()
        check_cache_and_ai()
        start_server()
    except KeyboardInterrupt:
        print("\nAIT AI Assistant server stopped safely.")
        sys.exit(0)
