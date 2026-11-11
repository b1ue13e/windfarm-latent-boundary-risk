"""Audit legacy coordinates/masks using saved arrays only; no torch/model imports."""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from repo_paths import Path, repository_root

import numpy as np

ROOT = Path(repository_root())
SEEDS = (201, 202, 203, 204, 205)
LEGACY = {
    "artifacts/fixed_forecast_residuals.npz": "b05b3751f45e611e073d1dfe4c4545b9775ca625e3c76e85558328cfc30a49a9",
    "artifacts/matched_budget/cached_posterior_probs.npz": "d40f0ddbaee7f4a2c89dbacdfb05be0a858897f1ce02c648b989fb8a8037cbca",
}


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def exact_array(actual, expected):
    """Compare every element's bytes, including NaN payloads; never use tolerances."""
    a, b = np.asarray(actual), np.asarray(expected)
    result = dict(actual_shape=list(a.shape), expected_shape=list(b.shape),
                  actual_dtype=str(a.dtype), expected_dtype=str(b.dtype))
    if a.shape != b.shape or a.dtype != b.dtype:
        return dict(result, byte_identical=False, mismatched_element_bytes=None)
    aa, bb = np.ascontiguousarray(a), np.ascontiguousarray(b)
    av, bv = aa.view(f"V{aa.dtype.itemsize}"), bb.view(f"V{bb.dtype.itemsize}")
    different = int(np.count_nonzero(av != bv))
    result.update(byte_identical=different == 0, mismatched_element_bytes=different, elements=a.size)
    if a.dtype.kind == "f":
        both_finite = np.isfinite(a) & np.isfinite(b)
        result.update(actual_nonfinite=int((~np.isfinite(a)).sum()),
                      expected_nonfinite=int((~np.isfinite(b)).sum()),
                      max_abs_difference_on_joint_finite=float(np.max(np.abs(a[both_finite] - b[both_finite])))
                      if both_finite.any() else None)
    return result


def expected_anchors(bounds, hist=36, pred=24):
    start, end = bounds
    return np.arange(start + hist - 1, end - pred, dtype=np.int64)


def support_counts(target_mask, issue_valid, shortfall):
    future, issue = target_mask > 0.5, issue_valid > 0.5
    return dict(total=int(future.size), future_target_valid=int(future.sum()),
                issue_regime_valid=int(issue.sum()), both_valid=int((future & issue).sum()),
                target_valid_issue_invalid=int((future & ~issue).sum()),
                target_invalid_issue_valid=int((~future & issue).sum()),
                neither_valid=int((~future & ~issue).sum()),
                shortfall_nonfinite=int((~np.isfinite(shortfall)).sum()),
                nonfinite_inside_target_mask=int((~np.isfinite(shortfall) & future).sum()),
                nonfinite_inside_both_mask=int((~np.isfinite(shortfall) & future & issue).sum()))


def output_guard(path):
    path = path.resolve()
    path.relative_to((ROOT / "analyses").resolve())
    if path.exists():
        raise FileExistsError("Preserve previous audit records")
    return path


def anonymous_clock(row):
    day, slot = map(int, row)
    return dict(day=day, slot=slot, HHMM=f"{slot // 6:02}:{slot % 6 * 10:02}")


def run(output):
    output = output_guard(output)
    cache = ROOT / "artifacts/cache_strictmask_trainweights/wtb_245d"
    forecast = ROOT / "artifacts/trainweight_full_rerun_20260830"
    classifier = ROOT / "artifacts/dense_classifier_runs_20260904/canonical"
    cache_names = ("metadata.json", "target.npy", "target_mask.npy", "regime_primary.npy",
                   "regime_primary_valid.npy", "node_ids.npy", "time_index.npy")
    protected = [ROOT / p for p in LEGACY] + [cache / p for p in cache_names]
    for dirname in ("legacy_release_hash_audit_20261018", "legacy_generation_lineage_audit_20261018",
                    "legacy_posterior_accounting_audit_20261018"):
        protected += [p for p in (ROOT / "analyses" / dirname).rglob("*") if p.is_file()]
    protected += [p for p in (ROOT / "experiments/E07_history_only_recalibration").rglob("*") if p.is_file()]
    for seed in SEEDS:
        for split in ("val", "test"):
            directory = forecast / f"wtb_full_seed{seed}/{split}_metrics"
            protected += [directory / f"{f}.npy" for f in
                          ("anchor_index", "target", "mask", "regime_primary", "regime_primary_valid", "pred")
                          if (directory / f"{f}.npy").exists()]
    before = {p.relative_to(ROOT).as_posix(): digest(p) for p in dict.fromkeys(protected)}
    for p, h in LEGACY.items():
        if before[p] != h:
            raise ValueError("Legacy identity mismatch: " + p)
    meta = json.loads((cache / "metadata.json").read_text(encoding="utf-8"))
    target, target_mask, regime, valid, nodes, clock = (
        np.load(cache / f"{f}.npy", mmap_mode="r", allow_pickle=False)
        for f in ("target", "target_mask", "regime_primary", "regime_primary_valid", "node_ids", "time_index"))
    time_expected = np.column_stack((np.arange(len(clock)) // 144 + 1, np.arange(len(clock)) % 144)).astype(clock.dtype)
    clock_comparison = exact_array(clock, time_expected)
    node_comparison = exact_array(nodes, np.arange(1, 135, dtype=nodes.dtype))
    splits, shortfalls, historical, posterior_rows = {}, [], [], []
    residual_node_parts = []
    with np.load(ROOT / "artifacts/fixed_forecast_residuals.npz", allow_pickle=False) as residual, \
            np.load(ROOT / "artifacts/matched_budget/cached_posterior_probs.npz", allow_pickle=False) as posterior:
        residual_keys, posterior_keys = residual.files, posterior.files
        for split in ("val", "test"):
            anchors = residual[f"anchor_indices_{split}"]
            expected = expected_anchors(meta["split_bounds"][split])
            future_indices = anchors[:, None] + np.arange(1, 7)[None, :]
            yt, mask, z = (residual[f"{p}_{split}"] for p in ("ytrue", "mask", "z_label"))
            yt_expected = np.asarray(target[future_indices], dtype=np.float32)
            mask_expected = np.asarray(target_mask[future_indices], dtype=np.float32)
            z_expected = np.asarray(regime[anchors], dtype=np.int64)
            issue_valid = np.asarray(valid[anchors], dtype=np.float32)
            residual_node_parts += [yt, mask]
            horizons = []
            for h in range(6):
                horizons.append(dict(horizon=h + 1, target_offset_steps=h + 1,
                                     ytrue_vs_current_future_target=exact_array(yt[:, h], yt_expected[:, h]),
                                     mask_vs_current_future_target_mask=exact_array(mask[:, h], mask_expected[:, h])))
            # These wrong-coordinate comparisons do not alter any asset.
            one_step_late = np.asarray(target[future_indices + 1], dtype=np.float32)
            coordinate_contract = np.column_stack((np.repeat(anchors, len(nodes)), np.tile(nodes, len(anchors))))
            split_record = dict(anchor_comparison=exact_array(anchors, expected),
                                issue_first=anonymous_clock(clock[anchors[0]]), issue_last=anonymous_clock(clock[anchors[-1]]),
                                target_h6_first=anonymous_clock(clock[anchors[0] + 6]),
                                target_h6_last=anonymous_clock(clock[anchors[-1] + 6]),
                                target_comparison=exact_array(yt, yt_expected), mask_comparison=exact_array(mask, mask_expected),
                                issue_label_comparison=exact_array(z, z_expected), horizons=horizons,
                                wrong_future_offset_plus_one=exact_array(yt, one_step_late),
                                reversed_node_order=exact_array(yt, yt_expected[:, :, ::-1]),
                                expected_flat_contract=dict(elements=len(anchors) * len(nodes),
                                    formula="k=row*134+node_column; posterior intended at issue anchor; residual h target at anchor+h",
                                    derived_coordinate_sha256=hashlib.sha256(coordinate_contract.tobytes()).hexdigest(),
                                    evidence_level="DERIVED_EXPECTATION_ONLY; not coordinates saved with posterior"))
            for seed in SEEDS:
                yhat, sf = (residual[f"{p}_{split}_seed{seed}"] for p in ("yhat", "shortfall"))
                expected_sf = np.maximum(yhat - yt, 0.0) * mask
                support = support_counts(mask[:, 5], issue_valid, sf[:, 5])
                shortfalls.append(dict(seed=seed, split=split,
                                       formula_comparison=exact_array(sf, expected_sf),
                                       per_horizon_mask_support=[dict(horizon=h + 1, **support_counts(mask[:, h], issue_valid, sf[:, h]))
                                                                 for h in range(6)], h6_support=support))
                pp = posterior[f"p_{split}_seed{seed}"]
                posterior_rows.append(dict(seed=seed, split=split, shape=list(pp.shape), dtype=str(pp.dtype),
                                           length_matches_expected=pp.shape == (len(anchors) * len(nodes),),
                                           finite=bool(np.isfinite(pp).all()),
                                           source_requested_order="sequential windows, node columns, concatenate axis0 then reshape(-1)",
                                           actual_per_value_coordinate_binding="UNKNOWN; probability-only array"))
                directory = forecast / f"wtb_full_seed{seed}/{split}_metrics"
                fields = {"anchor_index": anchors, "target": yt, "mask": mask, "regime_primary": z,
                          "regime_primary_valid": issue_valid, "pred": yhat}
                for name, expected_field in fields.items():
                    p = directory / f"{name}.npy"
                    if p.exists():
                        saved = np.load(p, mmap_mode="r", allow_pickle=False)
                        selected = saved[:, :6] if name in ("target", "mask", "pred") else saved
                        historical.append(dict(seed=seed, split=split, field=name,
                                               reference=p.relative_to(ROOT).as_posix(),
                                               comparison=exact_array(selected, expected_field)))
                    else:
                        historical.append(dict(seed=seed, split=split, field=name, status="MISSING_REFERENCE_UNKNOWN"))
            h6 = next(r for r in shortfalls if r["split"] == split and r["seed"] == 201)["h6_support"]
            split_record["historical_effective_mask"] = dict(
                rule="target_mask_h6 only" if split == "val" else "target_mask_h6 AND issue_regime_valid",
                selected_count=h6["future_target_valid"] if split == "val" else h6["both_valid"],
                target_valid_issue_invalid=h6["target_valid_issue_invalid"],
                comparison_to_same_rule_on_both_splits="Different original rules; no mask replacement performed")
            splits[split] = split_record
    node_fingerprints = []
    for j, node_id in enumerate(nodes):
        h = hashlib.sha256()
        for a in residual_node_parts:
            h.update(np.ascontiguousarray(a[:, :, j]).tobytes())
        node_fingerprints.append(dict(column=j, current_cache_node_id=int(node_id),
                                      saved_target_mask_signature=h.hexdigest()))
    classifier_files = [p.relative_to(ROOT).as_posix() for p in classifier.rglob("*") if p.is_file()]
    classifier_arrays = [p for p in classifier_files if p.endswith((".npy", ".npz"))]
    after = {p: digest(ROOT / p) for p in before}
    if before != after:
        raise ValueError("Protected input changed")
    protocol = json.loads((ROOT / "experiments/E07_history_only_recalibration/protocol.json").read_text(encoding="utf-8"))
    a = protocol["activation"]
    if any(a[k] is not None for k in ("base_policy_bundle_manifest_sha256", "calibration_bundle_manifest_sha256",
                                     "prospective_collection_spec_manifest_sha256")):
        raise ValueError("E07 is not unactivated")
    result = dict(environment=dict(utc=datetime.now(timezone.utc).isoformat(), command=sys.argv, python=sys.version,
                                   numpy=np.__version__, platform=platform.platform(), device="CPU; no model imports or calls",
                                   seeds=SEEDS, random_sampling="none", comparison="exact element bytes; no tolerance"),
                  clock_comparison=clock_comparison, node_id_comparison=node_comparison,
                  residual_keys=residual_keys, posterior_keys=posterior_keys, splits=splits,
                  residual_shortfall_checks=shortfalls, archived_forecast_array_comparisons=historical,
                  posterior_shape_checks=posterior_rows, node_fingerprints=node_fingerprints,
                  distinct_target_mask_node_signatures=len({x["saved_target_mask_signature"] for x in node_fingerprints}),
                  classifier_reference_search=dict(root=str(classifier.relative_to(ROOT)), files=classifier_files,
                                                   array_files=classifier_arrays,
                                                   scope="This canonical producer-input directory only; absent reference is not global absence"),
                  evidence_levels=dict(residual_target_mask_vs_current_cache="DIRECT_ARRAY_COMPARISON",
                                       source_intended_posterior_order="SOURCE_CONTRACT; application to actual values is INFERRED",
                                       actual_posterior_value_to_time_node_binding="UNKNOWN without saved coordinates or independent exact reference",
                                       prior_90_matching_aggregates="Not independent per-value coordinate evidence"),
                  E07="UNCHANGED_UNACTIVATED", raw_result_replacements=0,
                  protected_inputs=[dict(path=p, before_sha256=h, after_sha256=after[p], unchanged=True)
                                    for p, h in before.items()])
    output.mkdir(parents=True)
    (output / "alignment.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(f"Saved alignment audit; {len(before)} protected inputs unchanged; no inference or asset replacement")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    run(parser.parse_args().output_dir)
