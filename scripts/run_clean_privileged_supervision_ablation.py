"""Clean Privileged-Supervision Ablation Audit (Issue 4).

Compares:
- wtb_bal_seed{201..205} (lambda_align = 0.0, balance = 1000.0)
vs
- wtb_bal_align_seed{201..205} (lambda_align = 5000.0, balance = 1000.0)

Both families share:
- Identical backbone architecture (RegimeAwareForecaster, 4 experts, hidden_dim=64)
- Identical training data and random seeds (201-205)
- Identical deployment information set (pitch withheld at test time)
- Identical frozen forecast residuals target (artifacts/fixed_forecast_residuals.npz)

Evaluates:
- NMI and ARI (Regime alignment)
- Brier score (Pitch posterior calibration)
- Transition recall (Switch-window detection)
- PSREI reserve screening cost at h=1 and h=6 (both boundary-band N=13,883 and full population N=408,939)
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import pandas as pd
import torch
from masked_representation import infer_masked, check_frozen_reference
from replay_provenance import provenance, finalize
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score

DT = 1.0 / 6.0
RHO = 10.0
Q_STAR = 1.0 - 1.0 / RHO  # 0.90
N_BINS = 5


def compute_transition_recall(y_true: np.ndarray, y_pred_binary: np.ndarray, window_radius: int = 3, valid=None) -> float:
    W, N = y_true.shape
    diff = np.diff(y_true, axis=0, prepend=y_true[:1, :]) != 0
    if valid is not None:
        diff[1:] &= valid[1:] & valid[:-1]
        diff[0]=False
    in_window = diff.copy()
    for offset in range(1, window_radius + 1):
        in_window[offset:, :] |= diff[:-offset, :]
        in_window[:-offset, :] |= diff[offset:, :]
    target_mask = in_window & (y_true == 1)
    if valid is not None:target_mask &= valid
    if np.sum(target_mask) == 0:
        return 0.0
    return float(np.mean(y_pred_binary[target_mask]))


def fit_and_evaluate_binned_reserves(
    val_probs: np.ndarray,
    val_s: np.ndarray,
    val_mask: np.ndarray,
    test_probs: np.ndarray,
    test_s: np.ndarray,
    test_mask: np.ndarray,
    n_bins: int = N_BINS,
    tau: float = Q_STAR,
    archive_path: Path | None = None,
) -> Tuple[float, float]:
    valid_v = val_mask & np.isfinite(val_s) & np.isfinite(val_probs)
    valid_t = test_mask & np.isfinite(test_s) & np.isfinite(test_probs)

    v_p = val_probs[valid_v]
    v_s = val_s[valid_v]
    t_p = test_probs[valid_t]
    t_s = test_s[valid_t]

    quantiles = np.linspace(0.0, 1.0, n_bins + 1)[1:-1]
    edges = np.quantile(v_p, quantiles)
    # Ensure unique edges
    if len(np.unique(edges)) < len(edges):
        edges = np.linspace(edges.min(), edges.max() + 1e-6, len(edges))
    v_bins = np.digitize(v_p, edges)

    reserves = {}
    global_res = float(np.quantile(v_s, tau))
    for b in range(n_bins):
        sub_s = v_s[v_bins == b]
        if len(sub_s) < 20:
            reserves[b] = global_res
        else:
            reserves[b] = float(np.quantile(sub_s, tau))

    t_bins = np.digitize(t_p, edges)
    r_test = np.zeros_like(t_s)
    for b in range(n_bins):
        r_test[t_bins == b] = reserves[b]

    shortage = np.maximum(t_s - r_test, 0.0)
    cost = float(np.sum(r_test + RHO * shortage) * DT)
    viol_rate = float(np.mean(t_s > r_test))
    if archive_path is not None:
        np.savez_compressed(archive_path,reserve=r_test,shortfall=t_s,selected_flat_indices=np.flatnonzero(valid_t),
                            mask=valid_t,bin_edges=edges,bin_reserves=np.array(list(reserves.values())))
    return cost, viol_rate


def main():
    parser = argparse.ArgumentParser(description="Clean Privileged-Supervision Ablation")
    parser.add_argument("--runs-root", default="artifacts/strictmask_ablation_rerun_wtb_full")
    parser.add_argument("--cache-dir", default="artifacts/cache_strictmask_trainweights/wtb_245d")
    parser.add_argument("--residuals-file", default="artifacts/fixed_forecast_residuals.npz")
    parser.add_argument("--output-csv", default="artifacts/supervision_replay_v2/results.csv")
    parser.add_argument("--output-md", default="artifacts/supervision_replay_v2/report.md")
    parser.add_argument('--unaligned-pattern',default=None)
    parser.add_argument('--aligned-pattern',default=None)
    parser.add_argument('--device',default='cuda' if torch.cuda.is_available() else 'cpu')
    args = parser.parse_args()

    runs_root = Path(args.runs_root)
    device=torch.device(args.device)
    archive=Path(args.output_csv).parent/'evidence'
    if archive.exists():raise FileExistsError(archive)
    paths={key:{seed:Path(pattern.format(seed=seed)) if pattern else runs_root/f'{key}_seed{seed}'
                for seed in range(201,206)} for key,pattern in
                [('wtb_bal',args.unaligned_pattern),('wtb_bal_align',args.aligned_pattern)]}
    provenance(archive,[args.residuals_file,Path(args.cache_dir)/'metadata.json',
                *sorted(Path(args.cache_dir).glob('*.npy')),
                *[paths[k][s]/'best_model.pt' for k in paths for s in range(201,206)]],vars(args))
    print(f"[Privileged Supervision] Loading residuals from {args.residuals_file}")
    res_data = np.load(args.residuals_file)

    # Load wind speed for boundary-band masking
    from windfarm_moe.data import load_cache_bundle
    cache_path = Path(args.cache_dir)
    bundle = load_cache_bundle(cache_path, mmap_mode="r")
    meta = bundle.metadata
    test_bounds = meta["split_bounds"]["test"]
    H = int(meta["hist_len"])
    P = int(meta["pred_len"])
    anchor_start = test_bounds[0] + H - 1
    anchor_end = test_bounds[1] - P - 1
    anchors = np.arange(anchor_start, anchor_end + 1)

    # Physics model channel 0 is wind speed
    test_wspd = bundle.physics[anchors, :, 0]  # (W, N) physical wind speed
    boundary_mask_test = (np.abs(test_wspd - 10.5) <= 1.0)  # (W, N) exactly 13,883 cells with mask

    variants = {
        "wtb_bal": {"name": "No regime-label alignment (historical pitch retained)", "align_weight": 0.0},
        "wtb_bal_align": {"name": "Regime-label alignment (lambda_align = 5000)", "align_weight": 5000.0},
    }

    seeds = [201, 202, 203, 204, 205]
    from windfarm_moe.config import TrainConfig
    for seed in seeds:
        c0=torch.load(paths['wtb_bal'][seed]/'best_model.pt',map_location='cpu',weights_only=False)
        c1=torch.load(paths['wtb_bal_align'][seed]/'best_model.pt',map_location='cpu',weights_only=False)
        w0=TrainConfig(**c0['train_config']).effective_loss_weights()
        w1=TrainConfig(**c1['train_config']).effective_loss_weights()
        if c0['model_config']!=c1['model_config'] or w0['align']!=0 or w1['align']!=5000 or any(w0[k]!=w1[k] for k in w0 if k!='align'):
            raise ValueError('The supervision pair does not isolate alignment on the same architecture')
    all_rows = []

    for v_key, v_info in variants.items():
        print(f"\n==================== VARIANT: {v_info['name']} ====================")
        for seed in seeds:
            run_dir = paths[v_key][seed]
            if not run_dir.exists():
                raise FileNotFoundError(run_dir)

            evidence=archive/f'{v_key}_seed{seed}'
            val_gate,_,va=infer_masked(run_dir,bundle,'val',device,evidence/'val')
            test_gate,_,ta=infer_masked(run_dir,bundle,'test',device,evidence/'test')
            if not np.array_equal(va,res_data['anchor_indices_val']) or not np.array_equal(ta,res_data['anchor_indices_test']):
                raise ValueError('Supervision experiment frozen target anchors differ')
            check_frozen_reference(bundle,res_data,'val',va)
            check_frozen_reference(bundle,res_data,'test',ta)
            test_regime = np.asarray(bundle.regime_primary[ta])
            test_regime_valid = np.asarray(bundle.regime_primary_valid[ta])>0.5

            # Alignment metrics
            pred_regime = np.argmax(test_gate[:, :, :3], axis=-1)
            valid_cells = test_regime_valid
            y_true_all = test_regime[valid_cells]
            y_pred_all = pred_regime[valid_cells]

            nmi = float(normalized_mutual_info_score(y_true_all, y_pred_all))
            ari = float(adjusted_rand_score(y_true_all, y_pred_all))

            # Pitch posterior metrics (Expert 2 is pitch control)
            val_p_pitch = val_gate[:, :, 2]
            test_p_pitch = test_gate[:, :, 2]

            y_pitch_true = (test_regime == 2).astype(np.float32)
            brier = float(np.mean((test_p_pitch[valid_cells] - y_pitch_true[valid_cells]) ** 2))

            pred_pitch_bin = (test_p_pitch > 0.5).astype(int)
            y_pitch_true_2d = (test_regime == 2).astype(int)
            trans_recall = compute_transition_recall(y_pitch_true_2d, pred_pitch_bin,valid=valid_cells)

            # Residual data for h=1 and h=6
            s_val_h1 = res_data[f"shortfall_val_seed{seed}"][:, 0, :]
            s_test_h1 = res_data[f"shortfall_test_seed{seed}"][:, 0, :]
            s_val_h6 = res_data[f"shortfall_val_seed{seed}"][:, 5, :]
            s_test_h6 = res_data[f"shortfall_test_seed{seed}"][:, 5, :]

            if len(val_p_pitch)!=len(s_val_h1) or len(test_p_pitch)!=len(s_test_h1):
                raise ValueError('Supervision experiment population mismatch; no truncation allowed')
            min_va, min_te = len(val_p_pitch),len(test_p_pitch)

            mask_va_h1 = res_data["mask_val"][:min_va, 0, :] > 0.5
            mask_te_h1 = res_data["mask_test"][:min_te, 0, :] > 0.5
            mask_va_h6 = res_data["mask_val"][:min_va, 5, :] > 0.5
            mask_te_h6 = res_data["mask_test"][:min_te, 5, :] > 0.5

            # Full Population Evaluation
            cost_full_h1, viol_full_h1 = fit_and_evaluate_binned_reserves(
                val_p_pitch[:min_va], s_val_h1[:min_va], mask_va_h1,
                test_p_pitch[:min_te], s_test_h1[:min_te], mask_te_h1,
                archive_path=evidence/'full_h1.npz',
            )
            cost_full_h6, viol_full_h6 = fit_and_evaluate_binned_reserves(
                val_p_pitch[:min_va], s_val_h6[:min_va], mask_va_h6,
                test_p_pitch[:min_te], s_test_h6[:min_te], mask_te_h6,
                archive_path=evidence/'full_h6.npz',
            )

            # Boundary-Band Slice Evaluation (|v-10.5| <= 1.0)
            b_mask_te_h1 = mask_te_h1 & boundary_mask_test[:min_te]
            b_mask_te_h6 = mask_te_h6 & boundary_mask_test[:min_te]

            cost_bnd_h1, viol_bnd_h1 = fit_and_evaluate_binned_reserves(
                val_p_pitch[:min_va], s_val_h1[:min_va], mask_va_h1,
                test_p_pitch[:min_te], s_test_h1[:min_te], b_mask_te_h1,
                archive_path=evidence/'boundary_h1.npz',
            )
            cost_bnd_h6, viol_bnd_h6 = fit_and_evaluate_binned_reserves(
                val_p_pitch[:min_va], s_val_h6[:min_va], mask_va_h6,
                test_p_pitch[:min_te], s_test_h6[:min_te], b_mask_te_h6,
                archive_path=evidence/'boundary_h6.npz',
            )

            row = {
                "variant": v_key,
                "variant_name": v_info["name"],
                "lambda_align": v_info["align_weight"],
                "seed": seed,
                "nmi": nmi,
                "ari": ari,
                "brier": brier,
                "trans_recall": trans_recall,
                "cost_full_h1": cost_full_h1,
                "viol_full_h1": viol_full_h1,
                "cost_full_h6": cost_full_h6,
                "viol_full_h6": viol_full_h6,
                "cost_bnd_h1": cost_bnd_h1,
                "viol_bnd_h1": viol_bnd_h1,
                "cost_bnd_h6": cost_bnd_h6,
                "viol_bnd_h6": viol_bnd_h6,
            }
            all_rows.append(row)
            print(
                f"  Seed {seed} | NMI: {nmi:.3f} | ARI: {ari:.3f} | Brier: {brier:.4f} | "
                f"Recall: {trans_recall:.1%} | Full Cost h1: {cost_full_h1:,.0f} | Bnd Cost h6: {cost_bnd_h6:,.0f}",
                flush=True,
            )

    df = pd.DataFrame(all_rows)
    out_csv = Path(args.output_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_csv, index=False)
    print(f"\n[Privileged Supervision] Saved CSV to {out_csv}")

    # Summary table
    agg = df.groupby("variant").agg(
        name=("variant_name", "first"),
        lambda_align=("lambda_align", "first"),
        nmi_mean=("nmi", "mean"),
        nmi_std=("nmi", "std"),
        ari_mean=("ari", "mean"),
        ari_std=("ari", "std"),
        brier_mean=("brier", "mean"),
        brier_std=("brier", "std"),
        recall_mean=("trans_recall", "mean"),
        recall_std=("trans_recall", "std"),
        cost_bnd_h1_mean=("cost_bnd_h1", "mean"),
        cost_bnd_h1_std=("cost_bnd_h1", "std"),
        cost_bnd_h6_mean=("cost_bnd_h6", "mean"),
        cost_bnd_h6_std=("cost_bnd_h6", "std"),
        cost_full_h1_mean=("cost_full_h1", "mean"),
        cost_full_h1_std=("cost_full_h1", "std"),
        cost_full_h6_mean=("cost_full_h6", "mean"),
        cost_full_h6_std=("cost_full_h6", "std"),
    ).reset_index()

    print("\n==================== AGGREGATE SUMMARY ====================")
    print(agg.to_string(index=False))

    # Paired differences
    bal = df[df["variant"] == "wtb_bal"].sort_values("seed").reset_index(drop=True)
    align = df[df["variant"] == "wtb_bal_align"].sort_values("seed").reset_index(drop=True)

    delta_nmi = align["nmi"] - bal["nmi"]
    delta_brier = align["brier"] - bal["brier"]
    delta_cost_bnd_h6 = align["cost_bnd_h6"] - bal["cost_bnd_h6"]
    delta_cost_full_h6 = align["cost_full_h6"] - bal["cost_full_h6"]

    from scipy import stats
    from datetime import datetime,timezone
    if len(bal)!=5 or len(align)!=5 or not np.array_equal(bal.seed,align.seed):
        raise ValueError('All five matched seeds are required')
    summaries=[]
    for metric in ['nmi','ari','brier','trans_recall','cost_full_h1','cost_full_h6','cost_bnd_h1','cost_bnd_h6']:
        delta=(align[metric]-bal[metric]).to_numpy()
        mean=float(delta.mean()); se=float(stats.sem(delta))
        half=float(stats.t.ppf(0.975,4)*se)
        pval=float(stats.ttest_rel(align[metric],bal[metric]).pvalue) if se>0 else float('nan')
        summaries.append(dict(metric=metric,n=5,mean_delta=mean,ci_low=mean-half,ci_high=mean+half,p_paired_t=pval))
    pd.DataFrame(summaries).to_csv(out_csv.parent/'paired_seed_statistics.csv',index=False)
    agg.to_csv(out_csv.parent/'aggregate.csv',index=False)
    lines=['# Corrected masked-inference supervision ablation',
           'Executed UTC: '+datetime.now(timezone.utc).isoformat(),
           'Historical pitch remains in training inputs in both arms; only regime alignment differs.',
           'Both deployment pitch channels and their masks are explicitly zeroed before every forward pass.',
           'Brier is evaluated for the raw pitch-expert gating score; it is not assumed calibrated physical-state probability.',
           'Paired Student-t intervals/tests use five model seeds, conditional on this test population. No two-level bootstrap or universal gain is claimed.',
           '| Metric | Mean aligned-minus-unaligned | 95% seed-level t interval | Paired t p |',
           '|---|---:|---|---:|']
    for row in summaries:
        lines.append(f"| {row['metric']} | {row['mean_delta']:.8g} | [{row['ci_low']:.8g}, {row['ci_high']:.8g}] | {row['p_paired_t']:.8g} |")
    md_path=Path(args.output_md);md_path.parent.mkdir(parents=True,exist_ok=True)
    md_path.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    finalize(archive)


if __name__ == "__main__":
    main()
