from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from common.dashboard_app import run_app

run_app(Path(__file__).resolve().parent, "T1")
