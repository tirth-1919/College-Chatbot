import os
import sys
import importlib.util
from pathlib import Path

# Detect actual project directory
CURRENT_DIR = Path(__file__).resolve().parent
SUBFOLDER = CURRENT_DIR / "Collage Chatbot"
if (SUBFOLDER / "backend").exists():
    PROJECT_ROOT = SUBFOLDER
else:
    PROJECT_ROOT = CURRENT_DIR

sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(str(PROJECT_ROOT))

# Execute the main orchestrator
if __name__ == "__main__":
    inner_run_path = PROJECT_ROOT / "run.py"
    spec = importlib.util.spec_from_file_location("main_run", str(inner_run_path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    module.print_banner()
    try:
        module.check_and_build_frontend()
        module.initialize_database()
        module.check_cache_and_ai()
        module.start_server()
    except KeyboardInterrupt:
        print("\nAIT AI Assistant server stopped safely.")
        sys.exit(0)
