"""Restore missing per-run target.npy / mask.npy from the windowed cache.

Some run metrics dirs keep pred.npy + anchor_index.npy but have had the bulky
target.npy / mask.npy removed by space-saving cleanup. Those two arrays are an
exact function of the cache: for an anchor time ``t`` and horizon ``P`` the
target window is ``cache_target[t+1 : t+1+P]`` (the t+1 supervision boundary).

This utility reconstructs them losslessly and refuses to write unless the
reconstruction reproduces the run's stored ``overall.rmse`` (when available),
so it cannot silently corrupt evidence.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

METRICS_SUBDIRS = ("val_metrics", "test_metrics", "holdout_metrics")


def _discover_caches(root: Path) -> list[Path]:
    caches: list[Path] = []
    for base in sorted(root.glob("artifacts/cache*")):
        for cache_dir in [base, *sorted(p.parent for p in base.glob("**/target.npy"))]:
            if (cache_dir / "target.npy").exists() and (cache_dir / "target_mask.npy").exists():
                if cache_dir not in caches:
                    caches.append(cache_dir)
    return caches


def _stored_rmse(metrics_dir: Path) -> float | None:
    mpath = metrics_dir / "metrics.json"
    if not mpath.exists():
        return None
    try:
        data = json.loads(mpath.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    overall = data.get("overall", {})
    rmse = overall.get("rmse") if isinstance(overall, dict) else None
    return float(rmse) if isinstance(rmse, (int, float)) else None


def _reconstruct(metrics_dir: Path, cache_dir: Path) -> tuple[np.ndarray, np.ndarray] | None:
    pred = np.load(metrics_dir / "pred.npy", mmap_mode="r")
    anchor_index = np.load(metrics_dir / "anchor_index.npy")
    _, horizon, nodes = pred.shape
    cache_t = np.load(cache_dir / "target.npy", mmap_mode="r")
    cache_m = np.load(cache_dir / "target_mask.npy", mmap_mode="r")
    if cache_t.shape[1] != nodes:
        return None
    idx = anchor_index[:, None] + 1 + np.arange(horizon)[None, :]
    if int(idx.max()) >= cache_t.shape[0]:
        return None
    target = np.asarray(cache_t)[idx].astype(np.float32)
    mask = np.asarray(cache_m)[idx].astype(np.float32)
    return target, mask


def _verify(pred_path: Path, target: np.ndarray, mask: np.ndarray, stored_rmse: float | None) -> bool:
    if stored_rmse is None:
        return True
    pred = np.load(pred_path)
    valid = mask > 0.5
    if not valid.any():
        return False
    diff = (pred - target)[valid]
    rmse = float(np.sqrt(np.mean(diff**2)))
    return abs(rmse - stored_rmse) < 0.1


def restore_metrics_dir(metrics_dir: Path, caches: list[Path], dry_run: bool) -> str:
    if not (metrics_dir / "pred.npy").exists() or not (metrics_dir / "anchor_index.npy").exists():
        return "skip_no_pred_or_anchor"
    have_target = (metrics_dir / "target.npy").exists()
    have_mask = (metrics_dir / "mask.npy").exists()
    if have_target and have_mask:
        return "ok_present"
    stored = _stored_rmse(metrics_dir)
    for cache_dir in caches:
        rec = _reconstruct(metrics_dir, cache_dir)
        if rec is None:
            continue
        target, mask = rec
        if not _verify(metrics_dir / "pred.npy", target, mask, stored):
            continue
        if dry_run:
            return f"would_restore_from[{cache_dir.name}]"
        np.save(metrics_dir / "target.npy", target)
        np.save(metrics_dir / "mask.npy", mask)
        return f"restored_from[{cache_dir.relative_to(cache_dir.parents[2])}]"
    return "FAIL_no_matching_validated_cache"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root-dir", default=".")
    parser.add_argument(
        "--run-table",
        default="artifacts/strictmask_combined_reviewer_stats/reviewer_stat_pack_run_table.csv",
        help="CSV with a run_dir column; restores those runs. Use --scan to ignore.",
    )
    parser.add_argument("--scan", action="store_true", help="Scan all artifacts run dirs instead of a run table.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    root = Path(args.root_dir).resolve()
    caches = _discover_caches(root)
    if not caches:
        raise SystemExit("No caches with target.npy + target_mask.npy found under artifacts/cache*.")

    run_dirs: list[Path] = []
    table_path = root / args.run_table
    if not args.scan and table_path.exists():
        import pandas as pd

        for raw in pd.read_csv(table_path)["run_dir"].astype(str).unique():
            p = (root / raw) if not Path(raw).is_absolute() else Path(raw)
            if p.exists():
                run_dirs.append(p)
    else:
        seen: set[Path] = set()
        for sub in METRICS_SUBDIRS:
            for m in root.glob(f"artifacts/**/{sub}"):
                if (m / "pred.npy").exists():
                    seen.add(m.parent)
        run_dirs = sorted(seen)

    results: dict[str, int] = {}
    failures: list[str] = []
    for run_dir in run_dirs:
        for sub in METRICS_SUBDIRS:
            md = run_dir / sub
            if not md.exists():
                continue
            status = restore_metrics_dir(md, caches, args.dry_run)
            key = status.split("[")[0]
            results[key] = results.get(key, 0) + 1
            if status.startswith("FAIL"):
                failures.append(str(md))

    print(f"Caches: {[c.name for c in caches]}")
    print(f"Run dirs scanned: {len(run_dirs)}")
    for key in sorted(results):
        print(f"  {key}: {results[key]}")
    if failures:
        print("FAILURES:")
        for f in failures:
            print(f"  {f}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
