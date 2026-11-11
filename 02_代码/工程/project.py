"""One entry point for project tools and historical evidence lookup."""
import argparse
import os
import subprocess
import sys
from pathlib import Path
from repo_paths import repository_root, resolve_legacy


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["locate", "cli", "scientific-gate", "number-gate", "build-paper"])
    args = parser.parse_args(sys.argv[1:2])
    rest = sys.argv[2:]
    root = repository_root()
    engineering = Path(__file__).parent
    env = dict(os.environ, PYTHONPATH=os.pathsep.join([str(engineering), str(engineering / "scripts"), os.environ.get("PYTHONPATH", "")]))
    if args.command == "locate":
        parser.exit(message=str(resolve_legacy(rest[0])) + "\n")
    if args.command == "cli":
        command = [sys.executable, str(engineering / "main.py"), *rest]
    elif args.command == "build-paper":
        command = [sys.executable, str(root / "01_当前论文/TSTE/qa/build_pdfs.py"), *rest]
    elif args.command == "scientific-gate":
        command = [sys.executable, str(engineering / "scripts/verify_scientific_claim_gate.py"), *rest]
    else:
        # Read the existing frozen number ledger; do not regenerate statistics.
        from scripts import verify_tste_number_consistency as audit
        output = Path(os.environ["REPRODUCTION_OUTPUT_DIR"]) / "numbers" if "REPRODUCTION_OUTPUT_DIR" in os.environ else root / "04_结果/运行缓存/目录迁移验收/numbers"
        output.mkdir(parents=True, exist_ok=True)
        import shutil
        shutil.copyfile(resolve_legacy("artifacts/tste_number_consistency_audit/tste_number_consistency_audit.csv"), output / "tste_number_consistency_audit.csv")
        audit.HAS_PANDAS = False
        audit.run_number_consistency_audit(root=audit.Path(root), output_dir=output)
        import json
        result = json.loads((output / "tste_number_consistency_audit.json").read_text(encoding="utf-8"))
        print(result["status"])
        return 0 if result["status"] == "complete_tste_number_consistency" else 1
    return subprocess.call(command, cwd=root, env=env)


if __name__ == "__main__":
    raise SystemExit(main())
