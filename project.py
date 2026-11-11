"""Run repository tools from the workspace root, independent of working directory."""
from pathlib import Path
import argparse
import os
import runpy
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
ENGINEERING = ROOT / "02_代码/工程"
sys.path[:0] = [str(ENGINEERING.parent), str(ENGINEERING), str(ENGINEERING / "scripts")]


def main():
    parser = argparse.ArgumentParser(description="Current paper, source code, data and frozen results: one reproduction entry point.")
    parser.add_argument("command", choices=["verify", "reproduce-results", "redraw", "build-paper", "run-script", "locate", "cli", "scientific-gate", "number-gate"],
                        help="verify checks saved evidence; reproduce-results rebuilds point tables; redraw/build-paper write separate outputs")
    args = parser.parse_args(sys.argv[1:2])
    rest = sys.argv[2:]
    if args.command in {"verify", "reproduce-results", "redraw"}:
        from reproduction import main as reproduce
        return reproduce([args.command, *rest])
    if args.command == "run-script":
        if not rest or rest[0] in {"-h", "--help"}:
            print("python project.py run-script scripts/<name>.py [original arguments]\nAlso accepts a canonical or historical repository-relative script path.")
            return 0
        from repo_paths import resolve_legacy
        script = resolve_legacy(ROOT / rest[0])
        if not script.is_file():
            parser.error("Script does not exist: " + str(script))
        env = dict(os.environ, PYTHONPATH=os.pathsep.join([str(ENGINEERING), str(ENGINEERING / "scripts"), str(script.parent)]),
                   PYTHONDONTWRITEBYTECODE="1")
        return subprocess.call([sys.executable, str(script), *rest[1:]], cwd=ROOT, env=env)
    if args.command == "build-paper" and "--output-dir" not in rest:
        from reproduction import output_directory
        sys.argv.extend(["--output-dir", str(output_directory("build-paper"))])
    # Existing engineering CLI and immutable-number gates keep their semantics.
    os.chdir(ROOT)
    runpy.run_path(str(ENGINEERING / "project.py"), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
