"""Inspect saved yhat differences and provenance; no model or torch imports."""
from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from repo_paths import Path, repository_root

import numpy as np

ROOT = Path(repository_root())
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.audit_legacy_cache_alignment import digest, exact_array

SEEDS = (201, 202, 203, 204, 205)


def possible_batch_sizes(windows, batches):
    """Integer batch sizes consistent with a complete, non-dropping loader."""
    return [b for b in range(1, windows + 1) if (windows + b - 1) // b == batches]


def ulp_summary(a, b):
    if a.dtype != np.float32 or b.dtype != np.float32 or a.shape != b.shape:
        raise ValueError("ULP description requires same-shaped float32 arrays")
    finite = np.isfinite(a) & np.isfinite(b)
    x, y = np.ascontiguousarray(a[finite]), np.ascontiguousarray(b[finite])

    def order(v):
        u = v.view(np.uint32)
        return np.where(u & np.uint32(0x80000000), ~u, u | np.uint32(0x80000000)).astype(np.uint64)

    kx, ky = order(x), order(y)
    distance = np.maximum(kx, ky) - np.minimum(kx, ky)
    bins = [(0, 0), (1, 1), (2, 2), (3, 4), (5, 8), (9, 16), (17, 32), (33, 64)]
    hist = {f"{lo}..{hi}": int(((distance >= lo) & (distance <= hi)).sum()) for lo, hi in bins}
    hist[">64"] = int((distance > 64).sum())
    delta = x.astype(np.float64) - y.astype(np.float64)
    return dict(joint_finite=int(finite.sum()), excluded_nonfinite=int((~finite).sum()),
                max_ULP=int(distance.max()) if len(distance) else None, histogram=hist,
                mean_abs_difference=float(np.abs(delta).mean()) if len(delta) else None,
                rms_difference=float(np.sqrt(np.mean(delta * delta))) if len(delta) else None,
                interpretation="Descriptive only; ULP size is not a matching tolerance or causal identification")


class RemoveDenseClassifierBranch(ast.NodeTransformer):
    """Static specialization only for the recorded mode=moe_phys_full."""
    def visit_Assign(self, node):
        if any(ast.unparse(t) == "self.is_dense_classifier" for t in node.targets):
            return None
        return self.generic_visit(node)

    def visit_If(self, node):
        if ast.unparse(node.test) == "self.is_dense_classifier":
            result = []
            for item in node.orelse:
                value = self.visit(item)
                if value is not None:
                    result.extend(value if isinstance(value, list) else [value])
            return result
        return self.generic_visit(node)


def moe_source_comparison(old_text, new_text):
    old, new = ast.parse(old_text), ast.parse(new_text)
    specialized = RemoveDenseClassifierBranch().visit(copy.deepcopy(new))
    return dict(raw_source_equal=old_text == new_text,
                full_module_AST_after_recorded_mode_specialization_equal=
                ast.dump(old, include_attributes=False) == ast.dump(specialized, include_attributes=False),
                assumption="All five inspected checkpoint train_configs have mode=moe_phys_full; this is static source evidence, not runtime identity")


def run(output):
    output = output.resolve()
    output.relative_to((ROOT / "analyses").resolve())
    if output.exists():
        raise FileExistsError("Preserve prior audit output")
    audit_root = output.parent
    previous = ROOT / "analyses/legacy_cache_alignment_audit_20261018/run_v1/alignment.json"
    alignment = json.loads(previous.read_text(encoding="utf-8"))
    protected = [ROOT / r["path"] for r in alignment["protected_inputs"]]
    protected += [p for p in previous.parent.parent.rglob("*") if p.is_file()]
    runs = ROOT / "artifacts/trainweight_full_rerun_20260830"
    cache = ROOT / "artifacts/cache_strictmask_trainweights/wtb_245d"
    source_cache = ROOT / "artifacts/cache_strictmask/wtb_245d"
    names = ["features.npy", "feature_mask.npy", "physics.npy", "physics_model.npy", "edge_index.npy", "edge_weight.npy",
             "target.npy", "target_mask.npy", "regime_primary.npy", "regime_primary_valid.npy", "time_index.npy", "node_ids.npy"]
    for name in names:
        protected += [p for p in (cache / name, source_cache / name) if p.exists()]
    for seed in SEEDS:
        directory = runs / f"wtb_full_seed{seed}"
        protected += [directory / "best_model.pt"]
        protected += [p for p in directory.rglob("*") if p.is_file() and p.suffix in (".json", ".npy")]
    protected += [ROOT / "artifacts/raw_replay_20261015_v2/frozen_protocol.json",
                  audit_root / "current_checkpoint_inspection.json"]
    before = {p.relative_to(ROOT).as_posix(): digest(p) for p in dict.fromkeys(protected)}
    checkpoints = json.loads((audit_root / "current_checkpoint_inspection.json").read_text(encoding="utf-8"))
    for checkpoint in checkpoints["current_checkpoints"]:
        if digest(ROOT / checkpoint["path"]) != checkpoint["file_sha256"]:
            raise ValueError("Checkpoint changed after metadata inspection")
        if checkpoint["train_config"]["mode"] != "moe_phys_full":
            raise ValueError("Static specialization does not apply to this mode")
    raw = np.load(cache / "physics.npy", mmap_mode="r", allow_pickle=False)
    normalized = np.load(cache / "physics_model.npy", mmap_mode="r", allow_pickle=False)
    rows, input_refs, batch_rows, summaries = [], [], [], []
    with np.load(ROOT / "artifacts/fixed_forecast_residuals.npz", allow_pickle=False) as residual:
        for seed in SEEDS:
            summary_path = runs / f"wtb_full_seed{seed}/training_summary.json"
            summaries.append(dict(seed=seed, training_summary_exists=summary_path.exists()))
            for split in ("val", "test"):
                directory = runs / f"wtb_full_seed{seed}/{split}_metrics"
                pred = np.load(directory / "pred.npy", mmap_mode="r", allow_pickle=False)[:, :6]
                yhat = residual[f"yhat_{split}_seed{seed}"]
                comparison = exact_array(pred, yhat)
                rows.append(dict(seed=seed, split=split, exact_comparison=comparison,
                                 ULP_description=ulp_summary(pred, yhat),
                                 per_horizon=[dict(horizon=h + 1, **exact_array(pred[:, h], yhat[:, h])) for h in range(6)]))
                anchors = residual[f"anchor_indices_{split}"]
                physical = np.load(directory / "anchor_physics.npy", mmap_mode="r", allow_pickle=False)
                input_refs.append(dict(seed=seed, split=split, saved_raw_physics=exact_array(physical, raw[anchors]),
                                       saved_vs_model_normalized_physics=exact_array(physical, normalized[anchors]),
                                       note="evaluate_model saves bundle.physics after evaluation; actual loader input is physics_model; not a model-input trace"))
                metrics = json.loads((directory / "metrics.json").read_text(encoding="utf-8"))
                n, batches = metrics["efficiency"]["num_windows"], metrics["efficiency"]["num_batches"]
                batch_rows.append(dict(seed=seed, split=split, windows=n, archived_num_batches=batches,
                                       possible_complete_loader_batch_sizes=possible_batch_sizes(n, batches),
                                       checkpoint_batch_size=next(x["train_config"]["batch_size"] for x in checkpoints["current_checkpoints"] if x["seed"] == seed),
                                       recovered_residual_source_batch_size=64,
                                       residual_expected_batches=(n + 63) // 64,
                                       original_tail_at16=n % 16, residual_tail_at64=n % 64,
                                       evidence="batch16 supported by config+batch counts; residual64 specified by recovered source; no causal batch ablation performed"))
    input_copies = []
    for name in names:
        a, b = cache / name, source_cache / name
        input_copies.append(dict(name=name, current_trainweight_sha256=digest(a) if a.exists() else None,
                                 current_strict_source_sha256=digest(b) if b.exists() else None,
                                 same_current_bytes=a.exists() and b.exists() and digest(a) == digest(b),
                                 historical_execution_binding="UNKNOWN; present copy equality does not prove original consumed inputs"))
    source = audit_root / "source_snapshots"
    comparison = moe_source_comparison((source / "90528db0_model.py.txt").read_text(encoding="utf-8"),
                                       (source / "621bb8b_model.py.txt").read_text(encoding="utf-8"))
    after = {p: digest(ROOT / p) for p in before}
    if after != before:
        raise ValueError("Protected asset changed")
    protocol = json.loads((ROOT / "experiments/E07_history_only_recalibration/protocol.json").read_text(encoding="utf-8"))
    a = protocol["activation"]
    if any(a[k] is not None for k in ("base_policy_bundle_manifest_sha256", "calibration_bundle_manifest_sha256", "prospective_collection_spec_manifest_sha256")):
        raise ValueError("E07 activation changed")
    output.mkdir(parents=True)
    result = dict(environment=dict(utc=datetime.now(timezone.utc).isoformat(), command=sys.argv, python=sys.version,
                                   numpy=np.__version__, platform=platform.platform(), device="CPU saved-array inspection; no model imports/calls",
                                   seeds=SEEDS, randomness="none"),
                  prediction_comparisons=rows, raw_physics_references=input_refs, batch_evidence=batch_rows,
                  current_input_copy_comparisons=input_copies, training_summary_availability=summaries,
                  model_source_comparison=comparison, exact_matching_criterion="unchanged: same dtype/shape/element bytes; no allclose",
                  conclusion="All original non-exact matches retained; floating-point/batch mechanism is a candidate, historical causal separation remains UNKNOWN",
                  model_inference_calls=0, E07="UNCHANGED_UNACTIVATED",
                  protected_inputs=[dict(path=p, before_sha256=h, after_sha256=after[p], unchanged=True) for p, h in before.items()])
    (output / "diagnostic.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"Saved yhat provenance diagnosis; {len(before)} protected hashes unchanged; no inference")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    run(parser.parse_args().output_dir)
