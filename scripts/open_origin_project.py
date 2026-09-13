"""
open_origin_project.py
Quick utility to launch Origin 2024b GUI and open the master paper_figures.opju project.
"""

import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
OPJU_PATH = ROOT_DIR / "artifacts" / "origin_data" / "paper_figures.opju"

def main():
    if not OPJU_PATH.exists():
        print(f"Error: {OPJU_PATH} does not exist yet. Run `python scripts/build_origin_figures.py` first.")
        sys.exit(1)
    
    print(f"Opening Origin project in GUI: {OPJU_PATH}")
    os.startfile(str(OPJU_PATH.resolve()))

if __name__ == "__main__":
    main()
