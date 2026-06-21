from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SKILLS_DIR = ROOT / "stock-track-agent" / "skills"

if str(SKILLS_DIR) not in sys.path:
    sys.path.insert(0, str(SKILLS_DIR))

from new_stock_tracker import run_stock_track_agent  # noqa: E402


if __name__ == "__main__":
    run_stock_track_agent(root=ROOT)
