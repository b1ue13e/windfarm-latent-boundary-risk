"""Read-only scientific replay, with all new outputs kept outside frozen bundles."""
from pathlib import Path as NativePath
import argparse
import csv
from datetime import datetime
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from zoneinfo import ZoneInfo

ROOT = NativePath(__file__).resolve().parents[1]
ENGINEERING = ROOT / "02_代码/工程"
sys.path[:0] = [str(ENGINEERING), str(ENGINEERING / "scripts")]
from repo_paths import Path, resolve_legacy

PAPER = Path(ROOT / "01_当前论文/TSTE")


def output_directory(kind, supplied=None):
    directory = NativePath(supplied).resolve() if supplied else ROOT / "04_结果/复现运行" / (
        datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%d_%H%M%S_%f") + "_" + kind)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def run_logged(command, output, name, env=None):
    result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True)
    (output / (name + ".txt")).write_bytes(result.stdout + result.stderr)
    print(name, "PASS" if result.returncode == 0 else "FAIL", flush=True)
    return dict(command=command, exit_code=result.returncode)


def verify(output):
    env = dict(os.environ, PYTHONPATH=os.pathsep.join([str(ENGINEERING), str(ENGINEERING / "scripts")]),
               PYTHONDONTWRITEBYTECODE="1", REPRODUCTION_OUTPUT_DIR=str(output), PYTHONIOENCODING="utf-8")
    commands = [
        ("draft", [sys.executable, str(PAPER / "qa/verify_draft.py")]),
        ("figures", [sys.executable, str(PAPER / "qa/figure_rebuild_v14/verify_v14.py")]),
        ("scientific-gate", [sys.executable, str(ROOT / "project.py"), "scientific-gate"]),
        ("number-gate", [sys.executable, str(ROOT / "project.py"), "number-gate"]),
        ("paths", [sys.executable, "-m", "pytest", str(ENGINEERING / "tests/test_repository_paths.py"), "-q", "-p", "no:cacheprovider"]),
    ]
    results = {name: run_logged(command, output, name, env) for name, command in commands}
    report = dict(status="PASS" if all(r["exit_code"] == 0 for r in results.values()) else "FAIL", checks=results,
                  new_training=False, new_inference=False, new_resampling=False)
    (output / "verification.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0 if report["status"] == "PASS" else 1


def reproduce_results(output):
    import numpy as np
    import pandas as pd
    sources = {
        "measurement": Path(ROOT / "analyses/praw_supplement_v3_execution_20261021/primary_comparisons.csv"),
        "confirmation_2025": Path(ROOT / "analyses/independent_confirmation_execution_20261019/derived/summary.json"),
        "validation_2026": Path(ROOT / "experiments/mainline_supplement_20261026/FINAL_RESULTS.json"),
    }
    # Rebuild point accounting from every stored daily numerator and denominator;
    # retain the previously calculated confidence intervals without resampling.
    daily = pd.read_csv(PAPER / "source_data/v2/cross_year_daily.csv")
    summary = pd.read_csv(PAPER / "source_data/v2/cross_year_summary.csv")
    accounting = []
    for (year, arm), group in daily.groupby(["year", "arm"]):
        original = summary[(summary.year == year) & (summary.arm == arm)].iloc[0]
        row = dict(year=int(year), arm=arm)
        for metric in ["C", "R", "U", "V"]:
            value = float(np.mean([np.nansum(g[metric] * g.N) / g.N.sum() for _, g in group.groupby("seed")]))
            assert abs(value - float(original[metric])) < 1e-10, (year, arm, metric)
            row[metric] = value
        accounting.append(row)
    pd.DataFrame(accounting).to_csv(output / "cross_year_reconstructed.csv", index=False)
    fits = pd.read_csv(PAPER / "source_data/v2/measurement_fit.csv")
    assert np.allclose(fits.C, fits.R + 10 * fits.U, rtol=0, atol=1e-10)
    fits.groupby(["estimator", "arm"])[["C", "R", "U", "V"]].mean().to_csv(output / "measurement_reconstructed.csv")
    for name, path in sources.items():
        shutil.copy2(path, output / (name + path.suffix))
    for name in ["measurement_contrasts.csv", "cross_year_summary.csv"]:
        shutil.copy2(PAPER / "source_data/v2" / name, output / name)
    manifest = {name: dict(path=str(path.relative_to(ROOT)), sha256=hashlib.sha256(path.read_bytes()).hexdigest())
                for name, path in sources.items()}
    report = dict(status="PASS", cross_year_rows=len(accounting), measurement_fit_rows=len(fits),
                  sources=manifest, confidence_intervals="Copied unchanged; no new resampling",
                  new_training=False, new_inference=False)
    (output / "results_receipt.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("Stored point accounting reproduced; original intervals retained.", flush=True)
    return 0


def redraw(output):
    sys.path.insert(0, str(PAPER / "figure_code"))
    spec = importlib.util.spec_from_file_location("current_paper_figures", PAPER / "figure_code/figures_v14.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.OUT, module.QA = output / "figures", output / "qa"
    module.OUT.mkdir(exist_ok=True)
    module.QA.mkdir(exist_ok=True)
    for name in ["architecture", "decision_example", "measurement", "crossyear", "temporal"]:
        getattr(module, name)()
        print("Redrew", name, flush=True)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["verify", "reproduce-results", "redraw"])
    parser.add_argument("--output-dir")
    args = parser.parse_args(argv)
    output = output_directory(args.command, args.output_dir)
    code = {"verify": verify, "reproduce-results": reproduce_results, "redraw": redraw}[args.command](output)
    print("Output:", output, flush=True)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
