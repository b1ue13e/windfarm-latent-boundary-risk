from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from windfarm_moe.arrival_feed import DegradationSpec, UnifiedArrivalDataset
from windfarm_moe.data import load_cache_bundle
from windfarm_moe.mechanism_intervention import _load_model_from_checkpoint
from scripts.hierarchical_bootstrap import compute_hierarchical_joint_bootstrap

BLOCK = 144
RHO = 10.0
DT = 1.0 / 6.0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output-dir", default="artifacts/strong_baseline_joint_v2")
    p.add_argument("--bootstrap", type=int, default=5000)
    p.add_argument("--random-seed", type=int, default=20261015)
    args = p.parse_args()
    out = ROOT / args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    bundle = load_cache_bundle(ROOT / "artifacts/cache_strictmask_trainweights/wtb_245d", mmap_mode="r")
    res = np.load(ROOT / "artifacts/fixed_forecast_residuals.npz")
    spec = DegradationSpec(delay_steps=0, withheld_channels=("Pab_mean", "Pab_std"))
    ds = UnifiedArrivalDataset(bundle, "test", hist_len=36, pred_len=24, degradation=spec)
    anchors = np.asarray(ds.anchor_indices)
    n_nodes = int(bundle.features.shape[1])
    # Precompute the exact transition/steady partition used by the original analysis.
    regimes = np.asarray(bundle.regime_primary[anchors], dtype=np.int64)
    diff = np.diff(regimes, axis=0, prepend=regimes[:1]) != 0
    trans = diff.copy()
    for off in range(1, 4):
        trans[off:] |= diff[:-off]
        trans[:-off] |= diff[off:]
    trans = trans.reshape(-1)
    valid_regime = np.asarray(bundle.regime_primary_valid[anchors], dtype=bool).reshape(-1)
    mask = (res["mask_test"][:, 5, :].reshape(-1) > 0.5) & valid_regime
    w_mean = float(bundle.metadata.get("feature_stats", {}).get("Wspd", {}).get("mean", 5.306463))
    w_std = float(bundle.metadata.get("feature_stats", {}).get("Wspd", {}).get("std", 3.425992))
    wspd = np.asarray(bundle.physics_model[anchors, :, 0], dtype=np.float64).reshape(-1) * w_std + w_mean
    results = {}
    for seed in (201, 202, 203, 204, 205):
        s = np.asarray(res[f"shortfall_test_seed{seed}"][:, 5, :], dtype=np.float64).reshape(-1)
        val_s = np.asarray(res[f"shortfall_val_seed{seed}"][:, 5, :], dtype=np.float64).reshape(-1)
        val_mask = np.asarray(res["mask_val"][:, 5, :], dtype=bool).reshape(-1)
        val_anchors = np.asarray(UnifiedArrivalDataset(bundle, "val", 36, 24, degradation=spec).anchor_indices)
        val_wspd = np.asarray(bundle.physics_model[val_anchors, :, 0], dtype=np.float64).reshape(-1) * w_std + w_mean
        bins = np.linspace(0.0, 25.0, 11); bins[0], bins[-1] = -np.inf, np.inf
        q = [float(np.quantile(val_s[val_mask & (val_wspd >= bins[i]) & (val_wspd < bins[i+1])], .9)) if np.sum(val_mask & (val_wspd >= bins[i]) & (val_wspd < bins[i+1])) > 20 else float(np.quantile(val_s[val_mask], .9)) for i in range(10)]
        r_b = np.asarray(q)[np.clip(np.digitize(wspd, bins[1:-1]), 0, 9)]
        ckpt_dir = ROOT / f"artifacts/dense_classifier_runs_20260904/canonical/wtb_bal_align_force_seed{seed}"
        if not ckpt_dir.exists():
            ckpt_dir = ROOT / f"artifacts/dense_classifier_runs_20260904/wtb_bal_align_force_seed{seed}"
        if not ckpt_dir.exists():
            raise FileNotFoundError(f"Missing dense-classifier checkpoint for seed {seed}")
        model = _load_model_from_checkpoint(ckpt_dir, bundle, torch.device("cuda:0" if torch.cuda.is_available() else "cpu"))
        model.eval()
        loader = DataLoader(ds, batch_size=64, shuffle=False)
        probs=[]
        device=next(model.parameters()).device
        with torch.no_grad():
            for b in loader:
                _, g, _ = model(b["x_hist"].to(device),b["edge_index_hist"].to(device),b["edge_weight_hist"].to(device),b["feature_mask_hist"].to(device),b["anchor_physics"].to(device))
                p3=g[..., :3]
                probs.append((p3[...,2]/torch.clamp(p3.sum(dim=-1),min=1e-9)).cpu().numpy())
        ptest=np.concatenate(probs).reshape(-1)
        # Validation posterior scores are recomputed with the same frozen checkpoint.
        vds=UnifiedArrivalDataset(bundle,"val",36,24,degradation=spec)
        vloader=DataLoader(vds,batch_size=64,shuffle=False)
        pvals=[]
        with torch.no_grad():
            for b in vloader:
                _,g,_=model(b["x_hist"].to(device),b["edge_index_hist"].to(device),b["edge_weight_hist"].to(device),b["feature_mask_hist"].to(device),b["anchor_physics"].to(device))
                p3=g[..., :3]; pvals.append((p3[...,2]/torch.clamp(p3.sum(dim=-1),min=1e-9)).cpu().numpy())
        pval=np.concatenate(pvals).reshape(-1)
        cuts=np.quantile(pval[val_mask],np.linspace(0,1,6)); cuts[0],cuts[-1]=-np.inf,np.inf
        qi=[float(np.quantile(val_s[val_mask & (pval>=cuts[i]) & (pval<cuts[i+1])],.9)) if np.sum(val_mask & (pval>=cuts[i]) & (pval<cuts[i+1]))>20 else float(np.quantile(val_s[val_mask],.9)) for i in range(5)]
        rc=np.asarray(qi)[np.clip(np.digitize(ptest,cuts[1:-1]),0,4)]
        diff_cost=((rc+RHO*np.maximum(s-rc,0))-(r_b+RHO*np.maximum(s-r_b,0)))*DT
        # Flattened time/node costs are regrouped by anchor day; same block draw is used for transition and steady.
        n_time=len(anchors); point=diff_cost.reshape(n_time,n_nodes)
        m=mask.reshape(n_time,n_nodes); tr=trans.reshape(n_time,n_nodes)
        n_blocks=int(np.ceil(n_time/BLOCK)); ids=np.arange(n_time)//BLOCK
        bt=np.bincount(ids,weights=np.where(m & tr,point,0).sum(axis=1),minlength=n_blocks)
        bs=np.bincount(ids,weights=np.where(m & ~tr,point,0).sum(axis=1),minlength=n_blocks)
        results[seed]=(bt,bs)
        del model
    n_blocks=len(next(iter(results.values()))[0])
    if any(len(x[0])!=n_blocks for x in results.values()): raise ValueError("Unequal block count across seeds")
    rng=np.random.default_rng(args.random_seed)
    seeds=list(results)
    boot=np.empty(args.bootstrap)
    n_seed=len(seeds)
    for i in range(args.bootstrap):
        block_idx=rng.integers(0,n_blocks,size=n_blocks)
        seed_idx=rng.integers(0,n_seed,size=n_seed)
        interactions=[]
        for si in seed_idx:
            bt,bs=results[seeds[si]]
            interactions.append(bt[block_idx].sum()-bs[block_idx].sum())
        boot[i]=np.mean(interactions)
    point=np.mean([bt.sum()-bs.sum() for bt,bs in results.values()])
    summary={"analysis":"joint bootstrap over daily blocks and training seeds","estimand":"mean across seeds of (Delta_transition - Delta_steady), with paired time blocks","n_seeds":n_seed,"n_time_blocks":n_blocks,"bootstrap_draws":args.bootstrap,"mean_interaction_kwh":float(point),"ci95_low_kwh":float(np.quantile(boot,.025)),"ci95_high_kwh":float(np.quantile(boot,.975)),"p_noninferior_P_interaction_le_0":float(np.mean(boot<=0)),"seed_interactions_kwh":{str(s):float(a.sum()-b.sum()) for s,(a,b) in results.items()},"note":"P(interaction<=0) is an empirical directional probability, not a classical p-value. The legacy interaction p=0.002 arithmetic mean is not reused."}
    (out/"strong_baseline_joint_interaction.json").write_text(__import__("json").dumps(summary,indent=2),encoding="utf-8")

if __name__=="__main__": main()
