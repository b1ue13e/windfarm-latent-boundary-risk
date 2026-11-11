"""Replay frozen pilot predictions and inspect event magnitudes; never fit."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from repo_paths import Path, repository_root
import platform
import sys

import joblib
import numpy as np
import sklearn
import torch
from threadpoolctl import threadpool_limits

ROOT = Path(repository_root())
sys.path.insert(0, str(ROOT))
from scripts.run_state_measurement_pilot import verify, sha, save, stage, tasks, feature
from windfarm_moe.state_measurement_review import independent_features, deficit_profile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    cfg = json.loads(args.protocol.read_text())
    frozen = args.base / "prepared"
    verify(frozen, args.protocol, "prepare")
    z = stage(frozen, "evaluation")
    data = np.load(frozen / "physical_channels.npy", mmap_mode="r")
    rows = np.linspace(0, z["forecast"].size - 1, 4096, dtype=np.int64)
    results = []
    inputs = {"prepared_manifest": sha(frozen / "manifest.json")}
    torch.set_num_threads(2)
    torch.use_deterministic_algorithms(True)
    with threadpool_limits(2):
        for i, t in enumerate(tasks(cfg)):
            if t["seed"] != 201 or t["estimator"] == "CONTROL":
                continue
            fitroot, scored = args.base / "fits" / str(i), args.base / "evaluation" / str(i)
            verify(fitroot, args.protocol, "fit")
            verify(scored, args.protocol, "evaluate")
            inputs[f"fit{i}"] = sha(fitroot / "manifest.json")
            inputs[f"evaluation{i}"] = sha(scored / "manifest.json")
            model = joblib.load(fitroot / "model.joblib")
            x = feature(data, z, t["cell"])
            independent = independent_features(data, z["anchors"], z["forecast"], t["cell"], rows)
            if not np.array_equal(np.isnan(x[rows]), np.isnan(independent)):
                raise ValueError("Independent feature missingness differs")
            if not np.allclose(x[rows], independent, atol=2e-5, rtol=1e-6, equal_nan=True):
                raise ValueError("Independent feature values differ")
            finite = np.isfinite(independent)
            feature_error = float(np.max(np.abs(x[rows][finite] - independent[finite])))
            prediction = np.maximum(model.predict(x), 0).reshape(z["shortfall"].shape)
            with np.load(scored / "actions.npz") as actions:
                raw, calibrated = actions["raw"], actions["calibrated"]
            error = np.abs(prediction - raw)
            exact = bool(np.array_equal(prediction, raw))
            pitch_splits = None
            if t["estimator"] == "HGB" and t["cell"] in ("FZ", "OZ6", "OPZ6"):
                reg = model.named_steps["regressor"]
                pitch_column = x.shape[1] - 1
                nodes = np.concatenate([p[0].nodes for p in reg._predictors])
                active = nodes["is_leaf"] == 0
                pitch_splits = dict(value_splits=int(np.sum(active & (nodes["feature_idx"] == pitch_column))),
                                    total_splits=int(active.sum()), original_pitch_column=pitch_column)
            record = dict(**t, task=i, replay_exact=exact, maximum_prediction_error=float(error.max()),
                independent_feature_rows=len(rows), feature_width=x.shape[1], maximum_feature_error=feature_error,
                pitch_tree_splits=pitch_splits,
                raw_deficits=deficit_profile(z["shortfall"], raw, z["primary_mask"]),
                calibrated_deficits=deficit_profile(z["shortfall"], calibrated, z["primary_mask"]))
            results.append(record)
            print(t["estimator"], t["cell"], "exact", exact, "maxerr", record["maximum_prediction_error"], flush=True)
            del x, prediction, model
    save(args.output / "review.json", dict(status="COMPLETED_READ_ONLY_NO_FITS", records=results,
        input_manifest_sha256=inputs, source_sha256={str(Path(__file__).relative_to(ROOT)): sha(__file__),
            "windfarm_moe/state_measurement_review.py": sha(ROOT / "windfarm_moe/state_measurement_review.py")},
        protocol_sha256=sha(args.protocol), python=sys.version, numpy=np.__version__, torch=torch.__version__,
        sklearn=sklearn.__version__, argv=sys.argv, platform=platform.platform(),
        cpu_model=Path("/proc/cpuinfo").read_text().split("model name")[-1].splitlines()[0],
        host=platform.node(), pbs_job_id=os.environ.get("PBS_JOBID"), backend="CPU2; prediction replay only",
        finished_utc=datetime.now(timezone.utc).isoformat(),
        scope="Fixed seed201, all six cells and both estimators; feature sampling by coordinate, not outcome. No new fit, calibration, q choice, threshold replacement or measurement."))


if __name__ == "__main__":
    main()
