"""Bounded five-fit direct array-shortfall development runner.

Run only in PBS against a hash-sealed source archive. The fit/freeze stages never
open evaluation arrays. Historical qualification controls role selection only;
every computationally valid candidate is retained in evaluation.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from repo_paths import Path, repository_root
import platform
import sys
import time
import traceback

ROOT = Path(repository_root())
sys.path.insert(0, str(ROOT))
import joblib
import numpy as np
import scipy
from scipy import sparse
from scipy.optimize import linprog
import sklearn
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from threadpoolctl import threadpool_limits
from windfarm_moe.pitch_group_inference import (SEEDS, THRESHOLDS, comparison_labels,
    historical_definitions, historical_qualification, infer_group_family)

ARMS = ("P", "Z0", "ZD")
METHODS = ("G", "C", "A", "L")
CANDIDATES = tuple(f"{a}_{m}" for a in ARMS for m in METHODS)
STAGES = dict(fit=(19440,25193), calfit=(25200,26345), offset=(26352,27641),
              selection=(27648,30233), evaluate=(30240,35273))
S0_PARENT_MANIFEST_SHA256 = "8ce708967b8bb8bd139af622b4b1e8263eae93be1fa5a7c00b3fc1b069ff5785"
S0_PHYSICAL_SHA256 = "a2e98a6cc141a8c2328b6c5b9166ec0006b5ba78d3db0322a37c32e94359316c"
S0_NODES_SHA256 = "6f7d51a1bcb46ae18fd2bc28a1c35852460898b67880ac976a1c4b7f1171f098"


def sha(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_new(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False, ensure_ascii=False)
        stream.write("\n")


def binding(path):
    return dict(sha256=sha(path), bytes=Path(path).stat().st_size)


def cfg_s0_parent_manifest(path):
    # Kept as a compatibility helper; the actual S0 identity is immutable.
    return S0_PARENT_MANIFEST_SHA256


def array_sha(value):
    return hashlib.sha256(np.ascontiguousarray(value, dtype="<f8").tobytes()).hexdigest()


def environment():
    return dict(host=platform.node(), python=sys.version, numpy=np.__version__,
                scipy=scipy.__version__, sklearn=sklearn.__version__, joblib=joblib.__version__,
                job_id=os.environ.get("PBS_JOBID"), source_identity=os.environ.get("CAMPAIGN_RELEASE"),
                utc=datetime.now(timezone.utc).isoformat(), threads=2, argv=sys.argv,
                device="CPU", scope="Exposed WTB direct net-array development; no independent confirmation")


def config_check(cfg):
    if (cfg.get("seeds") != list(SEEDS) or cfg.get("thresholds") != THRESHOLDS
            or cfg.get("n_boot") != 20000 or cfg.get("bootstrap_seed") != 20261030
            or cfg.get("spans") != [1,3,7] or cfg.get("new_validation") is not None):
        raise ValueError("Frozen group task configuration changed")
    expected = dict(fit=[19440,25193],calfit=[25200,26345],offset=[26352,27641],
                    selection=[27648,30233],evaluate=[30240,35273])
    if cfg.get("stages") != expected:
        raise ValueError("Registered issue-clock stages differ")


def source_check(cfg):
    if not cfg.get("source_hashes"):
        raise ValueError("Unsealed source")
    for name, digest in cfg["source_hashes"].items():
        if sha(ROOT/name) != digest:
            raise ValueError("Scientific source changed: "+name)
    if sha(ROOT/"source_payload.zip") != os.environ.get("CAMPAIGN_RELEASE"):
        raise ValueError("PBS source archive identity mismatch")


def protocol_identity(cfg):
    return hashlib.sha256(json.dumps(cfg,sort_keys=True,separators=(",",":"),
        ensure_ascii=False,allow_nan=False).encode("utf-8")).hexdigest()


def load_prepared(path, expected_manifest=None, *, expected_provenance_sha256=None, evaluation=False):
    path=Path(path)
    if expected_manifest is not None and sha(path/"manifest.json") != expected_manifest:
        raise ValueError("Prepared manifest identity differs")
    manifest=read(path/"manifest.json")
    files=manifest.get("files",manifest)
    provenance_path=path/"provenance.json"
    if not provenance_path.is_file() or "provenance.json" not in files:
        raise ValueError("S0-bound provenance.json is required")
    if binding(provenance_path)!={k:files["provenance.json"][k] for k in ("sha256","bytes")}:
        raise ValueError("Prepared provenance binding differs")
    provenance=read(provenance_path)
    if expected_provenance_sha256 is not None and sha(provenance_path)!=expected_provenance_sha256:
        raise ValueError("Prepared S0 provenance SHA differs")
    required_provenance=("s0_report_sha256","parent_manifest_sha256","physical_channels_sha256",
                         "node_ids_sha256","member_count","member_ids_sha256","feature_names_sha256","phase_sources")
    if any(k not in provenance for k in required_provenance):
        raise ValueError("Prepared S0 provenance is incomplete")
    if (int(provenance["member_count"])!=134
            or provenance["parent_manifest_sha256"]!=S0_PARENT_MANIFEST_SHA256
            or provenance["physical_channels_sha256"]!=S0_PHYSICAL_SHA256
            or provenance["node_ids_sha256"]!=S0_NODES_SHA256
            or len(provenance["feature_names_sha256"])!=len(ARMS)
            or any(arm not in provenance["feature_names_sha256"] for arm in ARMS)):
        raise ValueError("Prepared source/member/feature schema differs from S0 binding")
    for arm in ARMS:
        schema_path=path/f"feature_names_{arm}.json"
        if not schema_path.is_file() or sha(schema_path)!=provenance["feature_names_sha256"][arm]:
            raise ValueError("Prepared feature-name schema identity differs: "+arm)
    phase_format=not (path/"anchors.npy").exists()
    phases=["evaluation"] if evaluation else ["fit","calfit","offset","selection"]
    required=([f"phase_{phase}.npz" for phase in phases]
              +[f"X_{arm}_{phase}.npy" for phase in phases for arm in ARMS]) if phase_format else [
              "anchors.npy","target.npy","target_mask.npy","pair_mask.npy","regime.npy","P.npy","Z0.npy","ZD.npy"]
    for name in required:
        if name not in files or binding(path/name) != {k:files[name][k] for k in ("sha256","bytes")}:
            raise ValueError("Prepared input identity differs: "+name)
    if phase_format:
        chunks={k:[] for k in ["anchors","target","target_mask","pair_mask","regime",*ARMS]}
        for phase in phases:
            with np.load(path/f"phase_{phase}.npz",allow_pickle=False) as z:
                for key in ["anchors","target_mask","pair_mask","regime"]:chunks[key].append(z[key].copy())
                chunks["target"].append(z["S_G"].copy())
                pa=z["anchors"].copy()
                expected=np.arange(*STAGES["evaluate"]) if phase=="evaluation" else np.arange(*STAGES[phase])
                if not np.array_equal(pa,expected):
                    raise ValueError("Prepared phase anchors differ: "+phase)
                source=provenance["phase_sources"].get(phase)
                if source is None or source.get("anchors_sha256")!=hashlib.sha256(np.ascontiguousarray(pa,dtype="<i8").tobytes()).hexdigest():
                    raise ValueError("Prepared phase provenance differs: "+phase)
                if source.get("forecast_sha256") is None or source.get("target_sha256") is None:
                    raise ValueError("Prepared phase must bind forecast and target source hashes: "+phase)
            for arm in ARMS:chunks[arm].append(np.load(path/f"X_{arm}_{phase}.npy",mmap_mode="r",allow_pickle=False))
        bank={k:np.concatenate(v,axis=0) for k,v in chunks.items()}
    else:
        bank={name[:-4]:np.load(path/name,mmap_mode="r",allow_pickle=False) for name in required}
        expected=np.arange(*STAGES["evaluate"])
        if not evaluation:
            raise ValueError("Historical production preparation must use phase files with per-phase provenance")
        if not np.array_equal(bank["anchors"],expected):
            raise ValueError("Evaluation anchors differ from frozen source clock")
    a,y,t,m,g=[bank[k] for k in ["anchors","target","target_mask","pair_mask","regime"]]
    if (a.ndim!=1 or a.dtype.kind not in "iu" or len(a)==0 or np.any(np.diff(a)<=0)
            or y.shape!=a.shape or t.shape!=a.shape or m.shape!=a.shape or g.shape!=a.shape
            or t.dtype!=bool or m.dtype!=bool or np.any(m&~t)
            or not np.isfinite(y[t]).all() or np.any(y[t]<0)
            or not np.isin(g,[-1,0,1,2]).all()):
        raise ValueError("Prepared group target/calendar/population invalid")
    for arm in ARMS:
        x=bank[arm]
        if x.ndim!=2 or len(x)!=len(a) or np.isinf(x).any():
            raise ValueError("Prepared causal features invalid")
    if bank["P"].shape[1]>=bank["Z0"].shape[1] or bank["Z0"].shape[1]>=bank["ZD"].shape[1]:
        raise ValueError("Nested measurement feature widths differ")
    if not np.array_equal(bank["P"],bank["Z0"][:,:bank["P"].shape[1]],equal_nan=True):
        raise ValueError("Z0 does not retain exact P context")
    if not np.array_equal(bank["P"],bank["ZD"][:,:bank["P"].shape[1]],equal_nan=True):
        raise ValueError("ZD does not retain exact P context")
    # Core API codes unknown=2; the inference family uses the named unknown
    # regime. Normalize only this categorical encoding, never the source bytes.
    bank["regime"]=np.where(np.asarray(g)==2,-1,np.asarray(g)).astype(np.int8)
    bank["path"]=path
    bank["manifest_sha256"]=sha(path/"manifest.json")
    bank["provenance"]=provenance
    return bank


def select(bank, stage):
    lo,hi=STAGES[stage]
    return (bank["anchors"]>=lo)&(bank["anchors"]<hi)


def safe_offset(score, target, mask):
    score=np.asarray(score,float);target=np.asarray(target,float);mask=np.asarray(mask,bool)
    if score.shape!=target.shape or mask.shape!=score.shape or not mask.any():
        raise ValueError("No legal offset population")
    if not np.isfinite(score).all() or not np.isfinite(target[mask]).all():
        raise ValueError("Invalid offset inputs")
    return float(np.quantile(target[mask]-score[mask],.925,method="higher"))


def make_hgb(seed, residual=False, synthetic_test=False):
    params=dict(loss="quantile",quantile=.90,max_iter=100,max_leaf_nodes=15,
        min_samples_leaf=100 if residual else 50,learning_rate=.05 if residual else .08,
        l2_regularization=1.,early_stopping=False,random_state=int(seed))
    if synthetic_test:
        params.update(max_iter=2,min_samples_leaf=2,max_leaf_nodes=3)
    return Pipeline([("imputer",SimpleImputer(strategy="constant",fill_value=0.,
                        add_indicator=True,keep_empty_features=True)),
                     ("model",HistGradientBoostingRegressor(**params))])


def linear_transform_fit(x):
    x=np.asarray(x,dtype=float)
    observed=np.isfinite(x)
    count=observed.sum(0);mean=np.divide(np.where(observed,x,0.).sum(0),count,
                                       out=np.zeros(x.shape[1]),where=count>0)
    filled=np.where(observed,x,mean)
    std=np.std(filled,axis=0);std=np.where(std>0,std,1.)
    transformed=(filled-mean)/std
    return dict(mean=mean,std=std),np.column_stack([transformed,(~observed).astype(float)])


def linear_transform(x,record):
    x=np.asarray(x,float);missing=~np.isfinite(x)
    filled=np.where(missing,record["mean"],x)
    return np.column_stack([(filled-record["mean"])/record["std"],missing.astype(float)])


def fit_linear_quantile(x,y, *, timeout_seconds=None):
    """L1 quantile LP; training-only feature and target scaling."""
    y=np.asarray(y,float)
    record,xx=linear_transform_fit(x)
    scale=float(np.std(y));scale=scale if scale>0 else 1.
    yy=y/scale
    n,p=xx.shape
    # beta = beta_plus-beta_minus; intercept is free. Residual yy-Xb = u-v.
    X=sparse.csr_matrix(xx)
    equation=sparse.hstack([sparse.csr_matrix(np.ones((n,1))),X,-X,
                             sparse.eye(n,format="csr"),-sparse.eye(n,format="csr")],format="csr")
    objective=np.r_[0.,np.full(2*p,1e-4),np.full(n,.9/n),np.full(n,.1/n)]
    options=dict(primal_feasibility_tolerance=1e-7,dual_feasibility_tolerance=1e-7)
    if timeout_seconds is not None:options["time_limit"]=float(timeout_seconds)
    fit=linprog(objective,A_eq=equation,b_eq=yy,bounds=[(None,None)]+[(0,None)]*(2*p+2*n),
                method="highs",options=options)
    if not fit.success or not np.isfinite(fit.x).all():
        raise RuntimeError("Linear quantile solve failed: "+str(fit.message))
    record.update(intercept=float(fit.x[0]),coef=fit.x[1:p+1]-fit.x[p+1:2*p+1],target_scale=scale,
        solver=dict(method="highs",status=int(fit.status),message=fit.message,
                    objective=float(fit.fun),n_iter=int(fit.nit),options=options),
        alpha=1e-4,quantile=.90)
    return record


def predict_linear(model,x):
    return model["target_scale"]*(model["intercept"]+linear_transform(x,model)@model["coef"])


def online_residual(score,target,anchors,target_valid,initial_offset, *, active_start=None):
    """Own-score residuals in the previous144 issue-origin clock, strict +7."""
    score=np.asarray(score,float);target=np.asarray(target,float);a=np.asarray(anchors,int)
    valid=np.asarray(target_valid,bool)
    if score.shape!=a.shape or target.shape!=a.shape or valid.shape!=a.shape or np.any(np.diff(a)<=0):
        raise ValueError("Invalid online trajectory")
    if not np.isfinite(score).all() or not np.isfinite(initial_offset):
        raise ValueError("Nonfinite online score/initial offset")
    actions=np.empty(len(a));offsets=np.empty(len(a));support=np.zeros(len(a),int)
    # Use only masks of labels already mature; do not inspect future validity.
    for i,t in enumerate(a):
        if active_start is not None and t<active_start:
            # Warmup stores pre-existing conditional scores/labels. No decision
            # using the full offset-block estimate is asserted at these times.
            actions[i]=max(score[i],0.);offsets[i]=0.;support[i]=0
            continue
        eligible=np.flatnonzero((a>=t-144)&(a+7<t))
        eligible=eligible[valid[eligible]]
        if len(eligible):
            if not np.isfinite(target[eligible]).all():raise ValueError("Mature target nonfinite")
            offset=float(np.quantile(target[eligible]-score[eligible],.925,method="higher"))
        else:offset=float(initial_offset)
        actions[i]=max(score[i]+offset,0.)
        offsets[i]=offset;support[i]=len(eligible)
    return actions,dict(offsets=offsets,support=support)


def daily_account(actions,target,mask,anchors):
    r=np.asarray(actions,float);y=np.asarray(target,float);m=np.asarray(mask,bool);a=np.asarray(anchors,int)
    if r.shape!=a.shape or y.shape!=a.shape or m.shape!=a.shape or not np.isfinite(r).all() or np.any(r<0):
        raise ValueError("Invalid group action/population")
    if not np.isfinite(y[m]).all() or np.any(y[m]<0):raise ValueError("Invalid scored target")
    days=np.arange(int(a[0]//144),int(a[-1]//144)+1)
    ledger=np.zeros((len(days),4));counts=np.zeros(len(days),dtype=np.int64)
    for j,day in enumerate(days):
        use=(a//144==day)&m;rr=r[use]/6.;u=np.maximum(y[use]-r[use],0.)/6.
        ledger[j]=[float(np.sum(rr+10*u)),float(np.sum(rr)),float(np.sum(u)),int(np.count_nonzero(y[use]>r[use]))]
        counts[j]=int(use.sum())
    return ledger,counts,days


def _predict_bank(models,offsets,bank,include_offset=True):
    actions={};scores={};traces={}
    for arm in ARMS:
        base=models[arm]["base"];cond=models[arm]["conditional"];linear=models[arm]["linear"]
        x=bank[arm];raw=np.maximum(np.asarray(base.predict(x),float),0.)
        condition=raw+np.asarray(cond.predict(np.column_stack([x,raw])),float)
        lin=np.maximum(predict_linear(linear,x),0.)
        for method,score in [("G",raw),("C",condition),("L",lin)]:
            role=f"{arm}_{method}";scores[role]=score
            actions[role]=np.maximum(score+offsets[role],0.) if include_offset else score
        start=STAGES["offset"][0]
        use=bank["anchors"]>=start
        online,trace=online_residual(condition[use],bank["target"][use],bank["anchors"][use],
                                     bank["target_mask"][use],offsets[f"{arm}_C"],
                                     active_start=STAGES["selection"][0])
        all_online=np.maximum(condition+offsets[f"{arm}_C"],0.);all_online[use]=online
        actions[f"{arm}_A"]=all_online;scores[f"{arm}_A"]=condition;traces[arm]=trace
    return {k:actions[k] for k in CANDIDATES},{k:scores[k] for k in CANDIDATES},traces


def _save_daily(path,actions,bank,phase):
    use=select(bank,phase);names=list(actions);rows=[];regimes={k:[] for k in ["high","low","unknown"]}
    counts=days=None;regime_counts={}
    for name in names:
        row,n,d=daily_account(actions[name][use],bank["target"][use],bank["pair_mask"][use],bank["anchors"][use])
        rows.append(row)
        if counts is None:counts,days=n,d
        elif not np.array_equal(n,counts):raise ValueError("Candidate scoring population differs")
        for group,key in [("high",1),("low",0),("unknown",-1)]:
            mask=bank["pair_mask"][use]&(bank["regime"][use]==key)
            row,n,d=daily_account(actions[name][use],bank["target"][use],mask,bank["anchors"][use])
            regimes[group].append(row);regime_counts[group]=n
    np.savez_compressed(path,ledger=np.stack(rows),counts=counts,days=days,
                        **{f"regime_{k}":np.stack(v) for k,v in regimes.items()},
                        **{f"counts_{k}":v for k,v in regime_counts.items()})
    return names


def fit_instance(cfg,out,seed, *, synthetic_test=False):
    if seed not in SEEDS:raise ValueError("Unregistered fixed fit")
    bank=load_prepared(cfg["history_prepared"],cfg.get("history_manifest_sha256"))
    if np.any(bank["anchors"]>=STAGES["evaluate"][0]):raise ValueError("History contains evaluation")
    folder=Path(out)/"fit"/f"seed{seed}"
    folder.mkdir(parents=True,exist_ok=False)
    models={};offsets={};fit=select(bank,"fit")&bank["target_mask"];cal=select(bank,"calfit")&bank["target_mask"]
    off=select(bank,"offset")&bank["target_mask"]
    if not fit.any() or not cal.any() or not off.any():raise ValueError("Historical target support absent")
    optimizations=[]
    for arm in ARMS:
        x=bank[arm];target=bank["target"]
        base=make_hgb(seed,synthetic_test=synthetic_test);base.fit(x[fit],target[fit])
        raw=np.maximum(base.predict(x),0.)
        residual=make_hgb(seed,residual=True,synthetic_test=synthetic_test)
        residual.fit(np.column_stack([x[cal],raw[cal]]),target[cal]-raw[cal])
        linear=fit_linear_quantile(x[fit],target[fit],timeout_seconds=cfg.get("linear_time_limit_seconds",30))
        condition=raw+residual.predict(np.column_stack([x,raw]))
        lin=np.maximum(predict_linear(linear,x),0.)
        for method,score in [("G",raw),("C",condition),("L",lin)]:
            offsets[f"{arm}_{method}"]=safe_offset(score[off],target[off],np.ones(off.sum(),bool))
        models[arm]=dict(base=base,conditional=residual,linear=linear)
        optimizations += [dict(arm=arm,kind=k,status="COMPLETED") for k in ["HGB_BASE","HGB_CONDITIONAL","LINEAR_QUANTILE"]]
        joblib.dump(models[arm],folder/f"{arm}.joblib")
    actions,scores,traces=_predict_bank(models,offsets,bank)
    names=_save_daily(folder/"selection_daily.npz",actions,bank,"selection")
    mask=select(bank,"selection")
    np.savez_compressed(folder/"selection_actions.npz",anchors=bank["anchors"][mask],
                        **{name:actions[name][mask] for name in names})
    write_new(folder/"offsets.json",offsets)
    write_new(folder/"receipt.json",dict(status="COMPLETED",seed=seed,names=names,
        manifest_sha256=bank["manifest_sha256"],source_hashes=cfg.get("source_hashes",{}),
        protocol_identity=protocol_identity(cfg),
        model_bindings={arm:binding(folder/f"{arm}.joblib") for arm in ARMS},offsets=binding(folder/"offsets.json"),
        selection_daily=binding(folder/"selection_daily.npz"),selection_actions=binding(folder/"selection_actions.npz"),
        optimizations=optimizations,optimization_count=9,history_qualification_filters_evaluation=False,
        evaluation_touched=False,synthetic_test=synthetic_test,environment=environment()))


def _read_fits(cfg,out):
    ledgers=[];receipts=[];counts=days=None
    for seed in SEEDS:
        folder=Path(out)/"fit"/f"seed{seed}";receipt=read(folder/"receipt.json")
        if receipt["status"]!="COMPLETED" or receipt["seed"]!=seed or receipt["evaluation_touched"]:
            raise ValueError("All five historical instances must complete")
        if (receipt["source_hashes"]!=cfg.get("source_hashes",{}) or receipt["manifest_sha256"]!=cfg["history_manifest_sha256"]
                or receipt["protocol_identity"]!=protocol_identity(cfg)):
            raise ValueError("Historical source binding differs")
        if receipt["names"]!=list(CANDIDATES):raise ValueError("Candidate order differs")
        for key,file in [("selection_daily","selection_daily.npz"),("selection_actions","selection_actions.npz"),("offsets","offsets.json")]:
            if binding(folder/file)!=receipt[key]:raise ValueError("Frozen historical output changed")
        for arm in ARMS:
            if binding(folder/f"{arm}.joblib")!=receipt["model_bindings"][arm]:raise ValueError("Model identity differs")
        with np.load(folder/"selection_daily.npz") as z:
            ledgers.append(z["ledger"])
            if counts is None:counts,days=z["counts"].copy(),z["days"].copy()
            elif not np.array_equal(counts,z["counts"]) or not np.array_equal(days,z["days"]):raise ValueError("History calendar differs")
        receipts.append(dict(path=str((folder/"receipt.json").relative_to(out)),**binding(folder/"receipt.json")))
    return np.stack(ledgers),counts,days,receipts


def _historical_select(inference,ledger,counts):
    qualification=historical_qualification(inference,list(CANDIDATES))
    points=ledger.sum(2).mean(0)/counts.sum()
    eligible=[n for n in [f"P_{m}" for m in METHODS] if qualification[n]["qualified"] is True]
    pstar=min(eligible,key=lambda n:(points[CANDIDATES.index(n),0],METHODS.index(n.split("_")[1]))) if eligible else None
    p_linear="P_L" if qualification["P_L"]["qualified"] is True else None
    pitch=[n for n in CANDIDATES if n.startswith(("Z0_","ZD_")) and qualification[n]["qualified"] is True]
    if pstar is None:zstar=None
    else:
        pitch=[pstar]+pitch
        # Exact ties favour IGNORE, then Z0, then ZD, and G/C/A/L.
        zstar=min(pitch,key=lambda n:(points[CANDIDATES.index(n),0],0 if n==pstar else 1 if n.startswith("Z0_") else 2,METHODS.index(n.split("_")[1])))
    return dict(P_STAR=pstar,Z_STAR=zstar,P_LINEAR_REF=p_linear,qualification=qualification,
                mean_points={n:points[i].tolist() for i,n in enumerate(CANDIDATES)},
                selected_ignore=pstar is not None and zstar==pstar,
                status="NO_HISTORY_P_REFERENCE" if pstar is None else "SELECTED",uses_evaluation=False)


def freeze_history(cfg,out, *, n_boot_override=None):
    out=Path(out)
    if (out/"FINAL_FREEZE.json").exists():raise FileExistsError("Historical freeze already exists")
    ledger,counts,days,receipts=_read_fits(cfg,out)
    if not counts.sum():raise ValueError("No historical scored group support")
    cstar=float(ledger[:,CANDIDATES.index("P_G"),:,0].sum(1).mean()/counts.sum())
    if not np.isfinite(cstar) or cstar<=0:raise ValueError("Group Cstar unsupported")
    definitions=historical_definitions(list(CANDIDATES))
    assert len(definitions)==132
    inference=infer_group_family(ledger,counts,list(CANDIDATES),definitions,cstar=cstar,
        n_boot=20000 if n_boot_override is None else n_boot_override,span=3,seed=20261030)
    choice=_historical_select(inference,ledger,counts)
    write_new(out/"historical_inference.json",inference);write_new(out/"HISTORY_SELECTION.json",choice)
    freeze=dict(status="FROZEN",history_receipts=receipts,history_manifest_sha256=cfg["history_manifest_sha256"],
        protocol_identity=protocol_identity(cfg),
        source_hashes=cfg.get("source_hashes",{}),Cstar_G=cstar,selection=binding(out/"HISTORY_SELECTION.json"),
        inference=binding(out/"historical_inference.json"),evaluation_touched=False,
        planned_optimization_count=45,completed_optimization_count=45,independent_confirmation=False,
        environment=environment())
    write_new(out/"FINAL_FREEZE.json",freeze)
    write_new(out/"EVALUATION_OPEN.json",dict(freeze_sha256=sha(out/"FINAL_FREEZE.json"),
        history_selection_sha256=sha(out/"HISTORY_SELECTION.json"),source_hashes=cfg.get("source_hashes",{})))


def verified_freeze(cfg,out):
    out=Path(out);f=read(out/"FINAL_FREEZE.json");opened=read(out/"EVALUATION_OPEN.json")
    if (opened["freeze_sha256"]!=sha(out/"FINAL_FREEZE.json") or f["evaluation_touched"]
            or f["protocol_identity"]!=protocol_identity(cfg)
            or f["source_hashes"]!=cfg.get("source_hashes",{})
            or f["history_manifest_sha256"]!=cfg["history_manifest_sha256"]
            or binding(out/"HISTORY_SELECTION.json")!=f["selection"]
            or binding(out/"historical_inference.json")!=f["inference"]):raise ValueError("Frozen historical barrier differs")
    _read_fits(cfg,out)
    return f


def _join_for_online(history,evaluation):
    if history["anchors"][-1]>=evaluation["anchors"][0]:raise ValueError("History/evaluation clocks overlap")
    return {k:np.concatenate([history[k],evaluation[k]],axis=0) for k in
            ["anchors","target","target_mask","pair_mask","regime",*ARMS]}


def _load_schema(cfg):
    with (ROOT/cfg["matrix_path"]).open(encoding="utf-8-sig",newline="") as f:matrix=list(csv.DictReader(f))
    with (ROOT/cfg["comparisons_path"]).open(encoding="utf-8-sig",newline="") as f:pairs=list(csv.DictReader(f))
    with (ROOT/cfg["coordinates_path"]).open(encoding="utf-8-sig",newline="") as f:coords=list(csv.DictReader(f))
    if (len(matrix),len(pairs),len(coords))!=(24,27,406):raise ValueError("Frozen full-family dimensions differ")
    return matrix,pairs,coords


def _expand_actions(candidate,evaluation,seed,selection,names):
    actions={name:np.asarray(value,float) for name,value in candidate.items()}
    available={name:True for name in candidate};aliases=[]
    for method in METHODS:
        name=f"IGNORE_P_{method}";source=f"P_{method}";actions[name]=actions[source].copy();available[name]=True;aliases.append((name,source))
    legacy=evaluation["path"]/"legacy_actions.npz"
    if legacy.exists():
        files=read(evaluation["path"]/"manifest.json");files=files.get("files",files)
        if "legacy_actions.npz" not in files or binding(legacy)!={k:files["legacy_actions.npz"][k] for k in ["sha256","bytes"]}:raise ValueError("Unbound legacy actions")
        with np.load(legacy) as z:
            for name in names:
                if name.startswith("OLD_") and name in z:
                    if z[name].shape!=(5,len(evaluation["anchors"])):raise ValueError("Legacy action dimensions differ")
                    actions[name]=np.asarray(z[name][seed-201],float);available[name]=True
    for role in ["P_STAR","Z_STAR","P_LINEAR_REF"]:
        source=selection[role]
        if source is not None:
            actions[role]=actions[source].copy();available[role]=True;aliases.append((role,source))
    for name in names:
        if name not in actions:available[name]=False
    return actions,available,aliases


def evaluate_instance(cfg,out,seed):
    out=Path(out);f=verified_freeze(cfg,out)
    history=load_prepared(cfg["history_prepared"],cfg["history_manifest_sha256"])
    evaluation=load_prepared(cfg["evaluation_prepared"],cfg["evaluation_manifest_sha256"],evaluation=True)
    a=evaluation["anchors"]
    if not np.array_equal(a,np.arange(*STAGES["evaluate"])):raise ValueError("Original evaluation issue calendar differs")
    if cfg.get("expected_evaluation_pair_count") is not None and int(evaluation["pair_mask"].sum())!=cfg["expected_evaluation_pair_count"]:raise ValueError("Evaluation pair population differs")
    models={arm:joblib.load(out/"fit"/f"seed{seed}"/f"{arm}.joblib") for arm in ARMS}
    offsets=read(out/"fit"/f"seed{seed}"/"offsets.json")
    combined=_join_for_online(history,evaluation);candidate,scores,traces=_predict_bank(models,offsets,combined)
    n=len(history["anchors"]);candidate={name:value[n:] for name,value in candidate.items()}
    matrix,pairs,coords=_load_schema(cfg);names=[x["id"] for x in matrix];choice=read(out/"HISTORY_SELECTION.json")
    actions,available,aliases=_expand_actions(candidate,evaluation,seed,choice,names)
    folder=out/"evaluate"/f"seed{seed}";folder.mkdir(parents=True,exist_ok=False)
    _save_daily(folder/"daily.npz",actions,evaluation,"evaluate")
    np.savez_compressed(folder/"actions.npz",anchors=a,**actions)
    write_new(folder/"receipt.json",dict(status="COMPLETED",seed=seed,freeze_sha256=sha(out/"FINAL_FREEZE.json"),
        source_hashes=cfg.get("source_hashes",{}),evaluation_manifest_sha256=evaluation["manifest_sha256"],
        names=list(actions),availability=available,aliases=aliases,daily=binding(folder/"daily.npz"),
        actions=binding(folder/"actions.npz"),action_sha256={name:array_sha(x) for name,x in actions.items()},
        scored_groups=int(evaluation["pair_mask"].sum()),qualification_filter=False,new_fits=0,environment=environment()))


def aggregate(cfg,out, *, n_boot_override=None):
    out=Path(out);f=verified_freeze(cfg,out);matrix,pairs,definitions=_load_schema(cfg);names=[x["id"] for x in matrix]
    data=[];regimes={k:[] for k in ["high","low","unknown"]};availability=np.ones(len(names),bool)
    aliases=None;counts=days=None;rcounts={}
    for seed in SEEDS:
        folder=out/"evaluate"/f"seed{seed}";receipt=read(folder/"receipt.json")
        if receipt["status"]!="COMPLETED" or receipt["freeze_sha256"]!=sha(out/"FINAL_FREEZE.json") or receipt["qualification_filter"]:raise ValueError("Mandatory evaluation incomplete")
        if binding(folder/"daily.npz")!=receipt["daily"] or binding(folder/"actions.npz")!=receipt["actions"]:raise ValueError("Evaluation output changed")
        present=receipt["names"]
        availability &= [receipt["availability"][name] for name in names]
        if aliases is None:aliases=receipt["aliases"]
        elif aliases!=receipt["aliases"]:raise ValueError("Frozen program aliases differ")
        with np.load(folder/"daily.npz") as z:
            values=np.full((len(names),len(z["counts"]),4),np.nan)
            rv={k:values.copy() for k in regimes}
            for i,name in enumerate(names):
                if name in present:
                    j=present.index(name);values[i]=z["ledger"][j]
                    for k in rv:rv[k][i]=z[f"regime_{k}"][j]
            data.append(values)
            for k in regimes:regimes[k].append(rv[k]);rcounts[k]=z[f"counts_{k}"].copy()
            if counts is None:counts,days=z["counts"].copy(),z["days"].copy()
            elif not np.array_equal(counts,z["counts"]) or not np.array_equal(days,z["days"]):raise ValueError("Evaluation population differs")
    ledger=np.stack(data);rledgers={k:np.stack(v) for k,v in regimes.items()}
    folder=out/"aggregate";folder.mkdir(parents=True,exist_ok=False)
    np.savez_compressed(folder/"all_daily_ledger.npz",ledger=ledger,counts=counts,days=days,
                        **{f"regime_{k}":v for k,v in rledgers.items()},**{f"counts_{k}":v for k,v in rcounts.items()})
    write_new(folder/"family.json",dict(names=names,available=availability.tolist(),pairs=pairs,coordinates=definitions,aliases=aliases))
    for span in [1,3,7]:
        inference=infer_group_family(ledger,counts,names,definitions,cstar=f["Cstar_G"],span=span,
            n_boot=20000 if n_boot_override is None else n_boot_override,seed=20261030,
            available=availability.tolist(),aliases=aliases,regime_ledgers=rledgers,regime_counts=rcounts)
        if inference["family_size"]!=406:raise ValueError("Complete inference family differs")
        inference["labels"]=comparison_labels(inference,pairs)
        write_new(folder/f"inference_span{span}.json",inference)
    files=["all_daily_ledger.npz","family.json"]+[f"inference_span{x}.json" for x in [1,3,7]]
    write_new(folder/"completion.json",dict(status="COMPLETED",files={x:binding(folder/x) for x in files},
        complete_fixed_fits=list(SEEDS),all_nominal_coordinates_retained=True,qualification_filter=False,
        source_hashes=cfg.get("source_hashes",{}),new_fits=0,independent_confirmation=False,environment=environment()))


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--protocol",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True);parser.add_argument("--stage",choices=["fit","freeze","evaluate","aggregate"],required=True)
    parser.add_argument("--seed",type=int,default=201);args=parser.parse_args()
    if not os.environ.get("PBS_JOBID"):raise ValueError("Bounded PBS allocation required")
    cfg=read(args.protocol);config_check(cfg);source_check(cfg);args.output.mkdir(parents=True,exist_ok=True)
    pc=args.output/"protocol_original.json"
    if pc.exists():
        if pc.read_bytes()!=args.protocol.read_bytes():raise ValueError("Protocol changed")
    else:
        with pc.open("xb") as stream:stream.write(args.protocol.read_bytes())
    try:
        with threadpool_limits(limits=2):
            if args.stage=="fit":fit_instance(cfg,args.output,args.seed)
            elif args.stage=="freeze":freeze_history(cfg,args.output)
            elif args.stage=="evaluate":evaluate_instance(cfg,args.output,args.seed)
            else:aggregate(cfg,args.output)
    except BaseException as exc:
        write_new(args.output/"failures"/f"{args.stage}_{args.seed}_{os.environ['PBS_JOBID']}.json",
            dict(error=repr(exc),traceback=traceback.format_exc(),environment=environment()))
        raise


if __name__=="__main__":main()
