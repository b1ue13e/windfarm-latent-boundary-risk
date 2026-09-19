#!/usr/bin/env python3
"""
init_research_project.py - Initialize a standardized academic research project structure.
Usage:
    python init_research_project.py [project_name]
"""

import os
import sys
import argparse
from pathlib import Path

# Ensure UTF-8 output on Windows terminals
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

PROJECT_STRUCTURE = {
    "configs": ["default.yaml"],
    "data": ["raw/.gitkeep", "processed/.gitkeep"],
    "src": [
        "__init__.py",
        "data_loader.py",
        "models/__init__.py",
        "models/baseline.py",
        "models/ours.py",
        "losses.py",
        "trainer.py",
        "evaluator.py",
        "utils.py"
    ],
    "experiments": [
        "run_baseline.py",
        "run_ours.py",
        "run_ablation.py"
    ],
    "logs": [".gitkeep"],
    "checkpoints": [".gitkeep"],
    "results": ["metrics/.gitkeep", "figures/.gitkeep", "tables/.gitkeep"],
    "scripts": ["run_all.sh", "generate_tables.py"]
}

def init_project(target_dir: Path):
    print(f"Initializing standardized research project at: {target_dir.resolve()}")
    target_dir.mkdir(parents=True, exist_ok=True)
    
    for folder, files in PROJECT_STRUCTURE.items():
        folder_path = target_dir / folder
        folder_path.mkdir(parents=True, exist_ok=True)
        for rel_file in files:
            file_path = folder_path / rel_file
            file_path.parent.mkdir(parents=True, exist_ok=True)
            if not file_path.exists():
                file_path.touch()
                print(f"  [+] Created: {folder}/{rel_file}")
                
    readme_path = target_dir / "README.md"
    if not readme_path.exists():
        readme_content = f"""# {target_dir.name}

## Project Overview
Standardized research repository initialized with research-workflow structure.

## Directory Layout
- `configs/`: Experiment configurations (hyperparameters, paths).
- `data/`: Raw and processed dataset splits.
- `src/`: Modular implementation of loaders, models, loss functions, and trainer.
- `experiments/`: Experiment runner entrypoints.
- `results/`: Formatted outputs, metrics JSON, LaTeX tables, and plots.
"""
        readme_path.write_text(readme_content, encoding="utf-8")
        print("  [+] Created: README.md")

    print("\nProject structure initialized successfully!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize academic research repository.")
    parser.add_argument("name", nargs="?", default="my_research_project", help="Project directory name")
    args = parser.parse_args()
    init_project(Path(args.name))
