"""Historical-only paired HGB capacity controls; evaluation is a separate call."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from repo_paths import Path, repository_root
import platform
import shutil
import sys
import time

import joblib
import numpy as np
import sklearn
from threadpoolctl import threadpool_limits

ROOT = Path(repository_root())
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.run_decision_information_development import learner, subsample
from scripts.run_strong_power_calibration import get_stage
from windfarm_moe.fair_joint import fair_features

STAGES = {"fit": (19440, 25193), "calfit": (25200, 27641), "select": (27648, 30233)}
INNER = (27648, 28937)
OUTER = (28944, 30233)
SEEDS = (201, 202, 203, 204, 205)
SCHEMA = "AUTONOMOUS_CAPACITY_CACHE_V1"


def _sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")


def _record(path):
    p = Path(path)
    return {"bytes": p.stat().st_size, "sha256": _sha(p)}


def _check(path, record):
    p = Path(path)
    if not p.is_file() or p.stat().st_size != record["bytes"] or _sha(p) != record["sha256"]:
        raise ValueError("Input identity mismatch: " + str(p))


def _environment():
    return dict(python=sys.version, numpy=np.__version__, sklearn=sklearn.__version__,
                joblib=joblib.__version__, platform=platform.platform(), host=platform.node(),
                cpu=platform.processor(), pbs_job_id=os.environ.get("PBS_JOBID"),
                backend="CPU sklearn HGB; CUDA unused")


def _sources():
    names = ["scripts/autonomous_capacity_candidates.py", "scripts/run_decision_information_development.py",
             "scripts/run_strong_power_calibration.py", "windfarm_moe/fair_joint.py",
             "windfarm_moe/conditional_power_calibration.py", "windfarm_moe/dynamic_addback.py",
             "windfarm_moe/decision_information.py"]
    return {name: _sha(ROOT / name) for name in names}


def _prepared(cfg, include_evaluate=False):
    p = Path(cfg["parent_prepared"]).resolve()
    manifest_path = p / "output_manifest.json"
    if _sha(manifest_path) != cfg["parent_prepared_manifest_sha256"]:
        raise ValueError("Prepared manifest identity mismatch")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    rec = json.loads((p / "execution_receipt.json").read_text(encoding="utf-8"))
    if (rec.get("status") != "COMPLETED_DEVELOPMENT_NOT_CERTIFIED" or
            rec.get("protocol_sha256") != cfg["parent_protocol_sha256"]):
        raise ValueError("Prepared producer protocol or completion mismatch")
    names = ["physical_channels.npy", "data_manifest.json", "execution_receipt.json",
             "policy_fit_forecast.npz", "calibration_forecast.npz"]
    if include_evaluate:
        names.append("development_evaluation_forecast.npz")
    identities = {"output_manifest.json": _record(manifest_path)}
    for name in names:
        if name not in manifest:
            raise ValueError("Missing consumed prepared member: " + name)
        _check(p / name, manifest[name]); identities[name] = dict(manifest[name])
    if cfg.get("physical_channels_sha256") and identities["physical_channels.npy"]["sha256"] != cfg["physical_channels_sha256"]:
        raise ValueError("Raw physical-channel identity mismatch")
    return p, identities


def prepare_feature_cache(cfg, output):
    """Create fit/calfit/select-only .npy matrices in a new immutable cache.

    Required cfg: parent_prepared, parent_prepared_manifest_sha256,
    parent_protocol_sha256. Optional policy_indices_dir points to old seed*/
    policy_indices.npy, whose exact integer contents are checked and saved.
    No pitch probe, test forecast, Cstar, calibration scale or future statistic
    is used in feature construction.
    """
    prepared, identities = _prepared(cfg)
    for phase, span in STAGES.items():
        if phase in cfg.get("stages", {}) and tuple(cfg["stages"][phase]) != span:
            raise ValueError("Frozen historical clock changed")
    out = Path(output); out.mkdir(parents=True, exist_ok=False)
    started = time.monotonic(); files = {}; shapes = {}
    _json(out / "config.json", cfg)
    _json(out / "source_hashes.json", _sources())
    data = np.load(prepared / "physical_channels.npy", mmap_mode="r")
    for phase, (lo, hi) in STAGES.items():
        source = "policy_fit" if phase == "fit" else "calibration"
        stage = get_stage(prepared, data, source, lo, hi)
        features, _, _ = fair_features(data, stage["anchors"], stage["A"], stage["B"],
                                       np.zeros(len(stage["A"]), dtype=np.float32))
        values = {"X_P": features["FULL_DYN"], "X_Z": features["FULL_DYN_Z"],
                  **{key: stage[key] for key in ("shortfall", "mask", "anchors")}}
        for name, value in values.items():
            path = out / f"{phase}_{name}.npy"; np.save(path, value, allow_pickle=False)
            files[path.name] = _record(path); shapes[path.name] = dict(shape=list(value.shape), dtype=str(value.dtype))
        del features, stage, values
    fit_mask = np.load(out / "fit_mask.npy", mmap_mode="r").reshape(-1)
    for seed in SEEDS:
        ix = subsample(fit_mask, 120000, seed)
        if cfg.get("policy_indices_dir"):
            original = Path(cfg["policy_indices_dir"]) / f"seed{seed}" / "policy_indices.npy"
            np.testing.assert_array_equal(ix, np.load(original, allow_pickle=False))
            identities[str(original)] = _record(original)
        path = out / f"policy_indices_seed{seed}.npy"; np.save(path, ix, allow_pickle=False)
        files[path.name] = _record(path)
    for name in ("config.json", "source_hashes.json"):
        files[name] = _record(out / name)
    manifest = dict(schema=SCHEMA, status="COMPLETED", scope="HISTORICAL_ONLY",
                    stages={k:list(v) for k,v in STAGES.items()}, files=files, arrays=shapes,
                    inputs=identities, environment=_environment(), seconds=time.monotonic()-started,
                    evaluate_read=False, training_quantile=.90, maximum_fit_rows=120000)
    _json(out / "cache_manifest.json", manifest)
    return manifest


def _load_cache(cache_dir):
    cache = Path(cache_dir); info = json.loads((cache / "cache_manifest.json").read_text(encoding="utf-8"))
    if info.get("schema") != SCHEMA or info.get("status") != "COMPLETED" or info.get("evaluate_read") is not False:
        raise ValueError("Unqualified historical cache")
    if info.get("scope") not in ("HISTORICAL_ONLY", "SYNTHETIC_UNIT_TEST_ONLY"):
        raise ValueError("Unknown cache population scope")
    for name, record in info["files"].items():
        member = (cache / name).resolve()
        if not member.is_relative_to(cache.resolve()) or "evaluate" in name:
            raise ValueError("Unsafe or evaluation cache member")
        _check(member, record)
    if info["scope"] == "HISTORICAL_ONLY":
        stored_sources=json.loads((cache/"source_hashes.json").read_text(encoding="utf-8"))
        if stored_sources != _sources():
            raise ValueError("Historical cache consumer source changed")
    result = {}
    for phase, (lo, hi) in STAGES.items():
        s = {name: np.load(cache / f"{phase}_{name}.npy", mmap_mode="r", allow_pickle=False)
             for name in ("X_P", "X_Z", "shortfall", "mask", "anchors")}
        a, y, m = s["anchors"], s["shortfall"], s["mask"]
        if (a.ndim != 1 or a.dtype.kind not in "iu" or y.ndim != 2 or m.dtype != bool or
                y.shape != m.shape or len(a) != len(y) or not len(a) or
                np.any(a < lo) or np.any(a >= hi) or np.any(np.diff(a) <= 0) or
                not np.isfinite(y[m]).all() or np.any(y[m] < 0)):
            raise ValueError("Invalid historical coordinates or targets")
        if info["scope"] == "HISTORICAL_ONLY" and not np.array_equal(a, np.arange(lo,hi)):
            raise ValueError("Historical grid truncated or rearranged")
        if any(s[k].ndim != 2 or len(s[k]) != m.size or np.isinf(s[k]).any() for k in ("X_P","X_Z")):
            raise ValueError("Unpaired or infinite feature rows")
        result[phase] = s
    return cache, info, result


def _deadline(value):
    d = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if d.tzinfo is None:
        raise ValueError("deadline_utc must be timezone-aware")
    return d.astimezone(timezone.utc)


def _check_deadline(deadline):
    if datetime.now(timezone.utc) >= deadline:
        raise TimeoutError("Shared campaign deadline reached; no next fit/prediction started")


def _predict(model, x):
    return np.concatenate([model.predict(x[start:start+30000]) for start in range(0,len(x),30000)])


def _metrics(s, r, mask, anchors, span):
    m = np.asarray(mask) & ((np.asarray(anchors) >= span[0]) & (np.asarray(anchors) < span[1]))[:,None]
    n = int(m.sum())
    if not n:
        return {"C":None,"R":None,"U":None,"V":None,"N":0}
    u = np.maximum(np.asarray(s)[m] - np.asarray(r)[m], 0.) / 6.
    reserve = np.asarray(r)[m] / 6.
    return dict(C=float(np.mean(reserve+10*u)), R=float(np.mean(reserve)),
                U=float(np.mean(u)), V=float(np.mean(np.asarray(s)[m] > np.asarray(r)[m])), N=n)


def run_capacity_candidate(config, cache_dir, output, seeds, deadline_utc):
    """Fit one paired HGB setting, returning summary.json; never read evaluate.

    candidate_id is an integer. settings contains exactly the original HGB's
    five configurable parameters. Production defaults to sklearn1.9.1; tests
    can explicitly declare their local version and synthetic cache scope.
    The caller enforces global recipe and CPU-hour counters. A single sklearn
    fit is not interruptible here: the parent process must enforce hard time.
    """
    if isinstance(config.get("candidate_id"), bool) or not isinstance(config.get("candidate_id"), int):
        raise ValueError("candidate_id must be an integer")
    required = {"max_iter","max_leaf_nodes","min_samples_leaf","learning_rate","l2_regularization"}
    if set(config["settings"]) != required or config.get("quantile",.9) != .9:
        raise ValueError("Only original HGB settings at fixed quantile .90 are supported")
    if tuple(seeds) != SEEDS:
        raise ValueError("All five fixed seeds are required")
    if sklearn.__version__ != config.get("expected_sklearn_version","1.9.1"):
        raise ValueError("Declared sklearn environment mismatch")
    threads = config.get("cpu_threads",1)
    if isinstance(threads,bool) or not isinstance(threads,int) or not 1 <= threads <= 2:
        raise ValueError("cpu_threads must be1or2 and included in the shared resource budget")
    deadline = _deadline(deadline_utc); _check_deadline(deadline)
    cache, cache_info, phases = _load_cache(cache_dir)
    out = Path(output); out.mkdir(parents=True, exist_ok=False)
    start = time.monotonic(); cpu_start = time.process_time()
    rec = dict(status="RUNNING", candidate_id=config["candidate_id"], config=config,
               started_utc=datetime.now(timezone.utc).isoformat(), deadline_utc=deadline.isoformat(),
               cache_manifest_sha256=_sha(cache/"cache_manifest.json"), source_sha256=_sources(),
               environment=_environment(), scope=cache_info["scope"], seeds=list(SEEDS),
               per_seed={}, evaluate_read=False, quantile=.9, maximum_fit_rows=120000,
               cpu_threads=threads, inner=list(INNER), outer=list(OUTER),
               score_outer=bool(config.get("score_outer",False)))
    _json(out/"summary.json",rec)
    source_dir=out/"source";source_dir.mkdir()
    for name in rec["source_sha256"]:
        destination=source_dir/name;destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,destination)
    try:
        with threadpool_limits(limits=threads):
            for seed in SEEDS:
                _check_deadline(deadline)
                seed_out=out/f"seed{seed}";seed_out.mkdir()
                ix=subsample(phases["fit"]["mask"].reshape(-1),120000,seed)
                np.testing.assert_array_equal(ix,np.load(cache/f"policy_indices_seed{seed}.npy",allow_pickle=False))
                np.save(seed_out/"policy_indices.npy",ix,allow_pickle=False)
                entry=dict(models={},metrics={"inner":{},"outer":{}},policy_indices_sha256=_sha(seed_out/"policy_indices.npy"))
                rec["per_seed"][str(seed)]=entry
                for arm in ("P","Z"):
                    _check_deadline(deadline); fit_start=time.monotonic(); fit_cpu=time.process_time()
                    entry["models"][arm]=dict(status="RUNNING_FIT",fit_rows=int(len(ix)),
                        features=int(phases["fit"]["X_"+arm].shape[1]),
                        settings=dict(config["settings"]),started_utc=datetime.now(timezone.utc).isoformat())
                    _json(out/"summary.json",rec)
                    model=learner(dict(config["settings"]),seed,True)
                    model.fit(phases["fit"]["X_"+arm][ix],phases["fit"]["shortfall"].reshape(-1)[ix])
                    entry["models"][arm]["status"]="FITTED_PENDING_CALIBRATION"
                    _check_deadline(deadline)
                    model_path=seed_out/f"{arm}_model.joblib";joblib.dump(model,model_path)
                    raw_cal=np.maximum(_predict(model,phases["calfit"]["X_"+arm]),0.)
                    calmask=phases["calfit"]["mask"].reshape(-1)
                    if not calmask.any():raise ValueError("No calibration targets")
                    residual=phases["calfit"]["shortfall"].reshape(-1)[calmask]-raw_cal[calmask]
                    offset=float(np.quantile(residual,.9,method="higher"))
                    calibration=dict(method="GLOBAL_SIGNED_RESIDUAL_Q90",quantile=.9,offset=offset,
                                     calibration_rows=int(calmask.sum()),model_sha256=_sha(model_path),
                                     calibration_clock=list(STAGES["calfit"]))
                    _json(seed_out/f"{arm}_calibration.json",calibration)
                    _check_deadline(deadline)
                    raw_select=np.maximum(_predict(model,phases["select"]["X_"+arm]),0.)
                    action=np.maximum(raw_select+offset,0.).reshape(phases["select"]["mask"].shape)
                    if not np.isfinite(action).all():raise FloatingPointError("Nonfinite selected action")
                    np.save(seed_out/f"{arm}_select.npy",action,allow_pickle=False)
                    for name,span in (("inner",INNER),("outer",OUTER)):
                        entry["metrics"][name][arm]=(_metrics(phases["select"]["shortfall"],action,
                            phases["select"]["mask"],phases["select"]["anchors"],span)
                            if name=="inner" or config.get("score_outer",False) else {"status":"NOT_SCORED"})
                    entry["models"][arm].update(dict(status="COMPLETED",model_path=str(model_path.resolve()),
                        model_sha256=calibration["model_sha256"],calibration_path=str((seed_out/f"{arm}_calibration.json").resolve()),
                        select_path=str((seed_out/f"{arm}_select.npy").resolve()),fit_rows=int(len(ix)),
                        features=int(model.n_features_in_),seconds=time.monotonic()-fit_start,
                        cpu_seconds=time.process_time()-fit_cpu))
                    _json(out/"summary.json",rec)
                    del model,raw_cal,raw_select,action,residual
        rec["status"]="COMPLETED_HISTORICAL_DEVELOPMENT"
    except BaseException as exc:
        rec["status"]="DEADLINE_EXCEEDED" if isinstance(exc,TimeoutError) else "FAILED"
        rec["error"]=dict(type=type(exc).__name__,message=str(exc))
        raise
    finally:
        rec.update(finished_utc=datetime.now(timezone.utc).isoformat(),seconds=time.monotonic()-start,
                   cpu_seconds=time.process_time()-cpu_start)
        _json(out/"summary.json",rec)
        _json(out/"output_manifest.json",{p.relative_to(out).as_posix():_record(p) for p in sorted(out.rglob("*"))
                                         if p.is_file() and p.name!="output_manifest.json"})
    return rec


def predict_final(model_path, prepared_cfg, output, *, arm, expected_model_sha256):
    """Explicit final-only prediction; the parent must freeze its selection first.

    This function is never invoked by cache preparation or capacity search.
    It writes to a new directory, and records the frozen model and source
    hashes. It does not fit, select or read historical scores for selection.
    """
    if arm not in ("P","Z"):raise ValueError("Unknown frozen information arm")
    model_path=Path(model_path)
    if _sha(model_path)!=expected_model_sha256:raise ValueError("Frozen model identity mismatch")
    calibration_path=model_path.with_name(f"{arm}_calibration.json")
    calibration=json.loads(calibration_path.read_text(encoding="utf-8"))
    if calibration["model_sha256"]!=expected_model_sha256 or calibration["quantile"]!=.9:
        raise ValueError("Frozen calibration/model binding mismatch")
    prepared,identities=_prepared(prepared_cfg,include_evaluate=True)
    out=Path(output);out.mkdir(parents=True,exist_ok=False)
    data=np.load(prepared/"physical_channels.npy",mmap_mode="r")
    stage=get_stage(prepared,data,"development_evaluation",30240,35273)
    feature,_,_=fair_features(data,stage["anchors"],stage["A"],stage["B"],np.zeros(len(stage["A"]),np.float32))
    with threadpool_limits(limits=1):
        model=joblib.load(model_path)
        raw=np.maximum(_predict(model,feature["FULL_DYN" if arm=="P" else "FULL_DYN_Z"]),0.)
    action=np.maximum(raw+calibration["offset"],0.).reshape(stage["mask"].shape)
    if not np.isfinite(action).all():raise FloatingPointError("Nonfinite final action")
    for name,value in {"actions":action,**{k:stage[k] for k in ("anchors","shortfall","mask")}}.items():
        np.save(out/f"{name}.npy",value,allow_pickle=False)
    _json(out/"receipt.json",dict(status="COMPLETED_FROZEN_FINAL_DEVELOPMENT",arm=arm,
          model_sha256=expected_model_sha256,calibration_sha256=_sha(calibration_path),inputs=identities,
          source_sha256=_sources(),environment=_environment(),time_utc=datetime.now(timezone.utc).isoformat(),
          no_new_independent_confirmation=True))
    _json(out/"output_manifest.json",{p.name:_record(p) for p in sorted(out.iterdir()) if p.is_file() and p.name!="output_manifest.json"})
    return action
