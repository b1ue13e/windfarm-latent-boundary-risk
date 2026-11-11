"""Read-only legacy accounting diagnosis; never run a cache producer or fit E07."""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import platform
import sys
import zipfile
from datetime import datetime, timezone
from repo_paths import Path, repository_root

import numpy as np

ROOT = Path(repository_root())
SEEDS = (201, 202, 203, 204, 205)
DT, RHO, Q, TOL = 1.0 / 6.0, 10.0, 0.90, 1e-4
LINEAGE = Path("analyses/legacy_generation_lineage_audit_20261018")
LEGACY_HASHES = {
    "artifacts/fixed_forecast_residuals.npz": "b05b3751f45e611e073d1dfe4c4545b9775ca625e3c76e85558328cfc30a49a9",
    "artifacts/matched_budget/cached_posterior_probs.npz": "d40f0ddbaee7f4a2c89dbacdfb05be0a858897f1ce02c648b989fb8a8037cbca",
}


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def accounting(r, s, mask, mode):
    """Hold actions/masks fixed; compare arithmetic paths at the original tolerance."""
    r, s = r[mask], s[mask]
    if mode == "float64":
        r, s = r.astype(np.float64), s.astype(np.float64)
    elif mode not in ("original", "sum64_only"):
        raise ValueError(mode)
    shortage = np.maximum(s - r, 0.0)
    kwargs = {"dtype": np.float64} if mode == "sum64_only" else {}
    terms = r + RHO * shortage
    c, reserve, u = (float(np.sum(a, **kwargs) * DT) for a in (terms, r, shortage))
    gap = c - (reserve + RHO * u)
    return dict(n=int(mask.sum()), cost=c, reserve=reserve, shortage=u,
                violations=int(np.count_nonzero(s > r)), gap_kwh=gap,
                passes_original_assert=abs(gap) < TOL,
                shortage_dtype=str(shortage.dtype), cost_terms_dtype=str(terms.dtype),
                reduction_dtype=str(np.sum(terms, **kwargs).dtype),
                scaled_scalar_dtype=str((np.sum(terms, **kwargs) * DT).dtype))


def cache_inventory(path, sizes):
    """Inspect existing bytes; positional length cannot certify anchor identity."""
    rows = []
    with zipfile.ZipFile(path) as archive:
        crc_failure = archive.testzip()
    with np.load(path, allow_pickle=False) as data:
        expected = {f"p_{split}_seed{seed}" for split in sizes for seed in SEEDS}
        if set(data.files) != expected:
            raise ValueError("Unexpected cache keys")
        for key in sorted(data.files):
            a = data[key]
            split = key.split("_")[1]
            rows.append(dict(key=key, shape=list(a.shape), dtype=str(a.dtype),
                             expected_shape=[sizes[split]], shape_matches=a.shape == (sizes[split],),
                             finite=bool(np.isfinite(a).all()),
                             out_of_range=int(np.count_nonzero((a < 0) | (a > 1))),
                             minimum=float(np.nanmin(a)), maximum=float(np.nanmax(a))))
    return dict(crc_failure=crc_failure, arrays=rows,
                coordinate_identity="UNKNOWN: posterior archive contains no time/node arrays")


def source_structure(path):
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    save = [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute) and n.func.attr == "savez_compressed"]
    assertions = [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Assert)]
    csv_writes = [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Call)
                  and isinstance(n.func, ast.Attribute) and n.func.attr == "to_csv"]
    helper = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                  and n.name == "compute_slice_metrics")
    return dict(path=str(path.relative_to(ROOT)), sha256=digest(path),
                cache_save_lines=save, assertion_lines=assertions, csv_write_lines=csv_writes,
                save_before_assert_before_csv=max(save) < min(assertions) < min(csv_writes),
                helper_lines=[helper.lineno, helper.end_lineno],
                helper_has_no_calls_that_write=not any(
                    isinstance(n, ast.Attribute) and n.attr in ("save", "savez_compressed", "to_csv", "write")
                    for n in ast.walk(helper)),
                original_assert_threshold_present=' < 1e-4' in text)


def strict_csv_identity(path, columns):
    rows = list(csv.DictReader(path.open(encoding="utf-8", newline="")))
    gaps = [abs(float(r[c]) - (float(r[reserve]) + RHO * float(r[u])))
            for r in rows for c, reserve, u in columns]
    return dict(path=str(path), rows=len(rows), checks=len(gaps),
                max_abs_gap_kwh=max(gaps), failed_original_assert=sum(g >= TOL for g in gaps),
                threshold_kwh=TOL)


def check_output(path):
    path = path.resolve()
    path.relative_to((ROOT / "analyses").resolve())
    if path.exists():
        raise FileExistsError("Audit destination already exists; preserve prior records")
    return path


def run(output):
    output = check_output(output)
    cache_dir = ROOT / "artifacts/cache_strictmask_trainweights/wtb_245d"
    csv_dir = ROOT / "artifacts/matched_budget"
    protected = [ROOT / p for p in LEGACY_HASHES]
    for prior in ("legacy_release_hash_audit_20261018", "legacy_generation_lineage_audit_20261018"):
        protected += [p for p in (ROOT / "analyses" / prior).rglob("*") if p.is_file()]
    protected += [cache_dir / f for f in ("metadata.json", "physics_model.npy", "regime_primary.npy",
                                         "regime_primary_valid.npy", "node_ids.npy", "time_index.npy")]
    protected += [p for p in csv_dir.iterdir() if p.suffix in (".csv", ".json")]
    protected += [p for p in (ROOT / "experiments/E07_history_only_recalibration").rglob("*") if p.is_file()]
    before = {p.relative_to(ROOT).as_posix(): digest(p) for p in dict.fromkeys(protected)}
    for rel, expected in LEGACY_HASHES.items():
        if before[rel] != expected:
            raise ValueError("Legacy input identity mismatch: " + rel)
    meta = json.loads((cache_dir / "metadata.json").read_text(encoding="utf-8"))
    physics = np.load(cache_dir / "physics_model.npy", mmap_mode="r")
    regimes = np.load(cache_dir / "regime_primary.npy", mmap_mode="r")
    valid = np.load(cache_dir / "regime_primary_valid.npy", mmap_mode="r")
    nodes = np.load(cache_dir / "node_ids.npy", mmap_mode="r")
    if not np.array_equal(nodes, np.arange(1, 135)):
        raise ValueError("Node order mismatch")
    metrics, csv_differences, policy_records = [], [], []
    archived = list(csv.DictReader((csv_dir / "baseline_reproduction.csv").open(encoding="utf-8")))
    with np.load(ROOT / "artifacts/fixed_forecast_residuals.npz", allow_pickle=False) as residual, \
            np.load(csv_dir / "cached_posterior_probs.npz", allow_pickle=False) as posterior:
        va, ta = (residual[f"anchor_indices_{s}"] for s in ("val", "test"))
        if not (np.array_equal(va, np.arange(25955, 30216)) and
                np.array_equal(ta, np.arange(30275, 35256))):
            raise ValueError("Legacy residual anchor mismatch")
        inventory = cache_inventory(csv_dir / "cached_posterior_probs.npz",
                                    {"val": len(va) * len(nodes), "test": len(ta) * len(nodes)})
        if inventory["crc_failure"] or not all(a["finite"] and a["shape_matches"]
                                                and a["out_of_range"] == 0 for a in inventory["arrays"]):
            raise ValueError("Cache structural/finite diagnostic failed")
        w = meta["feature_stats"]["Wspd"]
        wv, wt = (np.asarray(physics[a, :, 0], dtype=np.float32).reshape(-1) * w["std"] + w["mean"]
                  for a in (va, ta))
        mv = residual["mask_val"][:, 5, :].reshape(-1) > 0.5
        mt = (residual["mask_test"][:, 5, :].reshape(-1) > 0.5) & np.asarray(valid[ta], dtype=bool).reshape(-1)
        reg = np.asarray(regimes[ta])
        changed = np.diff(reg, axis=0, prepend=reg[:1]) != 0
        circular = np.zeros_like(changed)
        for offset in range(-3, 4):
            circular |= np.roll(changed, offset, axis=0)
        bounded = changed.copy()
        for offset in range(1, 4):
            bounded[offset:] |= changed[:-offset]
            bounded[:-offset] |= changed[offset:]
        masks = {name: {"Transition": mt & t.reshape(-1), "Steady": mt & ~t.reshape(-1), "Full": mt}
                 for name, t in (("original_circular", circular), ("later_bounded", bounded))}
        counts = {k: {s: int(m.sum()) for s, m in v.items()} for k, v in masks.items()}
        if counts["original_circular"] != {"Transition": 139684, "Steady": 245521, "Full": 385205}:
            raise ValueError("Original logged population does not match present inputs")
        if counts["later_bounded"] != {"Transition": 139653, "Steady": 245552, "Full": 385205}:
            raise ValueError("Later logged population does not match present inputs")
        for seed in SEEDS:
            sv, st = (residual[f"shortfall_{s}_seed{seed}"][:, 5, :].reshape(-1) for s in ("val", "test"))
            pv, pt = (posterior[f"p_{s}_seed{seed}"] for s in ("val", "test"))
            # Re-evaluate only the recorded historical formula for arithmetic diagnosis.
            # No parameter search, new policy, E07 calibration, or saved action replacement.
            q_global = float(np.quantile(sv[mv], Q))
            wind_edges = np.linspace(0., 25., 11)
            wind_edges[0], wind_edges[-1] = -np.inf, np.inf
            post_edges = np.quantile(pv[mv], np.linspace(0., 1., 6))
            post_edges[0], post_edges[-1] = -np.inf, np.inf
            for policy, edges, xv, xt in (("B", wind_edges, wv, wt), ("C", post_edges, pv, pt)):
                reserve = np.zeros_like(st)
                thresholds = []
                for lo, hi in zip(edges[:-1], edges[1:]):
                    group = mv & (xv >= lo) & (xv < hi)
                    threshold = float(np.quantile(sv[group], Q)) if group.sum() > 20 else q_global
                    thresholds.append(threshold)
                    reserve[(xt >= lo) & (xt < hi)] = threshold
                policy_records.append(dict(seed=seed, policy=policy, thresholds=thresholds,
                                           diagnostic_reserve_sha256=hashlib.sha256(reserve.tobytes()).hexdigest()))
                for population, slices in masks.items():
                    for slice_name, mask in slices.items():
                        for mode in ("original", "sum64_only", "float64"):
                            row = dict(seed=seed, policy=policy, population=population,
                                       slice=slice_name, mode=mode, **accounting(reserve, st, mask, mode))
                            metrics.append(row)
                            if mode == "float64" and population == "later_bounded":
                                saved = next(r for r in archived if r["seed"] == str(seed) and r["slice"] == slice_name)
                                prefix = "base" if policy == "B" else "post"
                                for k, col in (("reserve", "reserve_kwh"), ("shortage", "shortage_kwh"), ("cost", "psrei_kwh")):
                                    old = float(saved[f"{prefix}_{col}"])
                                    csv_differences.append(dict(seed=seed, policy=policy, slice=slice_name,
                                                               metric=k, observed=row[k], archived=old,
                                                               exact_float_equal=row[k] == old, delta=row[k] - old))
    checks = [strict_csv_identity(csv_dir / "baseline_reproduction.csv", [
        (f"{p}_psrei_kwh", f"{p}_reserve_kwh", f"{p}_shortage_kwh") for p in ("base", "post")])]
    for filename, suffix in (("exact_matched_budget_frontier.csv", ""), ("validation_calibrated_frontier.csv", "_test")):
        checks.append(strict_csv_identity(csv_dir / filename, [
            (f"PSREI_{p}{suffix}_kwh", f"R_{p}{suffix}_kwh", f"U_{p}{suffix}_kwh") for p in ("base", "post")]))
    after = {rel: digest(ROOT / rel) for rel in before}
    if before != after:
        raise ValueError("Protected input changed during diagnosis")
    protocol = json.loads((ROOT / "experiments/E07_history_only_recalibration/protocol.json").read_text(encoding="utf-8"))
    a = protocol["activation"]
    if any(a[k] is not None for k in ("base_policy_bundle_manifest_sha256", "calibration_bundle_manifest_sha256",
                                     "prospective_collection_spec_manifest_sha256")):
        raise ValueError("E07 activation binding changed")
    structure = [source_structure(ROOT / LINEAGE / "evidence" / f"run_matched_budget_frontier.py_before_step{s}.txt")
                 for s in (125, 151, 506)]
    output.mkdir(parents=True)
    result = dict(environment=dict(utc=datetime.now(timezone.utc).isoformat(), python=sys.version,
                                   numpy=np.__version__, platform=platform.platform(), device="CPU only; no model execution",
                                   command=sys.argv, seeds=SEEDS, q=Q, rho=RHO, dt=DT, original_assert_tolerance=TOL,
                                   random_sampling="none"),
                  source_structure=structure, cache_inventory=inventory, masks=counts,
                  metrics=metrics, diagnostic_policy_summaries=policy_records,
                  archived_csv_comparison=csv_differences, archived_csv_identity_checks=checks,
                  protected_inputs=[dict(path=rel, before_sha256=h, after_sha256=after[rel], unchanged=True)
                                    for rel, h in before.items()],
                  E07="UNCHANGED_UNACTIVATED", original_result_replacements=0,
                  limitation="Current-array arithmetic diagnosis; historical exact failure operands, output SHA256 at generation, dependencies and environment remain UNKNOWN")
    (output / "diagnostic.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(f"Wrote independent diagnosis to {output}; {len(before)} input hashes unchanged")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    run(parser.parse_args().output_dir)
