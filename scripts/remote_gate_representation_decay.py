import argparse
import json
import time
from pathlib import Path
import numpy as np
import pandas as pd
import torch
from sklearn.metrics import normalized_mutual_info_score, adjusted_rand_score
from scipy.stats import wasserstein_distance

from windfarm_moe.config import ModelConfig
from windfarm_moe.data import load_cache_bundle
from windfarm_moe.model import RegimeAwareForecaster
from scripts.remote_iec_density_multiyear_eval import WindowedDataset, run_inference_on_slice

def run_farm_gate_decay(farm: str, seeds: list[int], gpu_id: int, out_dir: Path):
    repo = Path("/root/paper3_audit_rerun_20260830")
    device = torch.device(f"cuda:{gpu_id}" if torch.cuda.is_available() else "cpu")
    
    if farm == "kelmarsh":
        cache_dir = repo / "artifacts/cache_external_wind/external_wind_kelmarsh_chronological"
        model_root = repo / "artifacts/signature_gate_farms_runs_20260903/kelmarsh/canonical"
        steps_per_year = 52560
        n_years = 9
    elif farm == "penmanshiel":
        cache_dir = repo / "artifacts/cache_external_wind/external_wind_penmanshiel_chronological"
        model_root = repo / "artifacts/signature_gate_farms_runs_20260903/penmanshiel/canonical"
        steps_per_year = 52560
        n_years = 9
    else:
        raise ValueError(farm)

    print(f"[GPU {gpu_id}] Loading {farm} cache from {cache_dir}...")
    bundle = load_cache_bundle(cache_dir)
    num_steps = bundle.features.shape[0]
    num_turbines = bundle.features.shape[1]
    
    regime_primary = bundle.regime_primary
    regime_valid = bundle.regime_primary_valid > 0.5

    all_rows = []

    for seed in seeds:
        ckpt_path = model_root / f"wtb_bal_align_force_seed{seed}" / "best_model.pt"
        if not ckpt_path.exists():
            print(f"[GPU {gpu_id}] Warning: checkpoint {ckpt_path} not found!")
            continue
        print(f"[GPU {gpu_id}] Loading {farm} seed {seed} checkpoint...")
        ckpt = torch.load(ckpt_path, map_location="cpu")
        mcfg = ModelConfig(**ckpt["model_config"])
        model = RegimeAwareForecaster(
            feature_dim=bundle.features.shape[-1],
            pred_len=24,
            mode="moe_full_no_aux",
            config=mcfg,
        ).to(device)
        model.load_state_dict(ckpt["model_state"])
        model.eval()

        print(f"[GPU {gpu_id}] Running forward inference for {farm} seed {seed} ({num_steps} steps)...")
        t0 = time.time()
        inf = run_inference_on_slice(model, bundle, 0, num_steps, device, batch_size=512)
        print(f"[GPU {gpu_id}] Inference finished in {time.time() - t0:.1f}s")

        gates = inf["gate"] # (N_anchors, N_turbines, 4)
        anchors = inf["anchor_idx"]
        anchor_to_local = {a: i for i, a in enumerate(anchors)}

        year_slices = []
        for y in range(n_years):
            t_start = y * steps_per_year
            t_end = min((y + 1) * steps_per_year, num_steps)
            step_indices = [anchor_to_local[s] for s in range(t_start, t_end) if s in anchor_to_local]
            if not step_indices:
                continue
            g_y = gates[step_indices]
            anc_y = anchors[step_indices]
            
            reg_y = regime_primary[anc_y]
            val_y = regime_valid[anc_y]
            
            pred_reg_y = np.argmax(g_y, axis=-1).flatten()
            true_reg_y = reg_y.flatten()
            valid_mask_y = val_y.flatten()
            p_pitch_y = g_y[..., 2].flatten()
            
            sel = valid_mask_y & (true_reg_y >= 0)
            if sel.sum() > 100:
                nmi_gt = float(normalized_mutual_info_score(true_reg_y[sel], pred_reg_y[sel]))
                ari_gt = float(adjusted_rand_score(true_reg_y[sel], pred_reg_y[sel]))
            else:
                nmi_gt = float("nan")
                ari_gt = float("nan")

            # Regime shares
            denom = max(len(pred_reg_y), 1)
            shares = [(pred_reg_y == k).sum() / denom for k in range(4)]
            
            year_slices.append({
                "year_idx": y + 1,
                "calendar_year": 2016 + y,
                "n_steps": t_end - t_start,
                "n_anchors": len(step_indices),
                "nmi_gt": nmi_gt,
                "ari_gt": ari_gt,
                "p_pitch": p_pitch_y,
                "gates": g_y,
                "shares": shares,
                "mean_p_pitch": float(p_pitch_y.mean()),
            })

        # Reference Year 1 (baseline commissioning year)
        base_y = year_slices[0]
        base_p_pitch = base_y["p_pitch"]
        base_nmi = base_y["nmi_gt"]

        for ys in year_slices:
            w1_pitch = float(wasserstein_distance(ys["p_pitch"], base_p_pitch))
            inv_w1_pitch = float(1.0 / (1.0 + w1_pitch))
            
            # Multi-expert mean Wasserstein distance
            w1_list = []
            for k in range(4):
                w1_k = float(wasserstein_distance(ys["gates"][..., k].flatten(), base_y["gates"][..., k].flatten()))
                w1_list.append(w1_k)
            mean_w1 = float(np.mean(w1_list))
            inv_mean_w1 = float(1.0 / (1.0 + mean_w1))
            
            rel_nmi = float(ys["nmi_gt"] / base_nmi) if base_nmi > 0 else float("nan")
            tv_dist = 0.5 * float(np.sum(np.abs(np.array(ys["shares"]) - np.array(base_y["shares"]))))

            row = {
                "farm": farm,
                "seed": seed,
                "year_idx": ys["year_idx"],
                "calendar_year": ys["calendar_year"],
                "n_steps": ys["n_steps"],
                "n_anchors": ys["n_anchors"],
                "nmi_ground_truth": ys["nmi_gt"],
                "ari_ground_truth": ys["ari_gt"],
                "relative_nmi": rel_nmi,
                "wasserstein_pitch": w1_pitch,
                "inverse_wasserstein_pitch": inv_w1_pitch,
                "mean_wasserstein_all": mean_w1,
                "inverse_wasserstein_all": inv_mean_w1,
                "total_variation_share": tv_dist,
                "mean_p_pitch": ys["mean_p_pitch"],
                "idle_share": ys["shares"][0],
                "mppt_share": ys["shares"][1],
                "pitch_share": ys["shares"][2],
                "trans_share": ys["shares"][3],
            }
            all_rows.append(row)
            print(f"[{farm} s{seed}] Year {ys['year_idx']} ({ys['calendar_year']}): NMI={ys['nmi_gt']:.4f} (rel={rel_nmi:.3f}), W1_pitch={w1_pitch:.4f}, InvW={inv_w1_pitch:.4f}")

    df = pd.DataFrame(all_rows)
    out_file = out_dir / f"{farm}_gpu{gpu_id}_gate_decay.csv"
    df.to_csv(out_file, index=False)
    print(f"[GPU {gpu_id}] Saved {len(df)} rows to {out_file}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--farm", default="kelmarsh")
    parser.add_argument("--seeds", default="201,202,203,204,205")
    parser.add_argument("--gpu-id", type=int, default=0)
    parser.add_argument("--output-dir", default="/root/paper3_audit_rerun_20260830/artifacts/multiyear_gate_representation_audit")
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    seeds = [int(s) for s in args.seeds.split(",")]
    run_farm_gate_decay(args.farm, seeds, args.gpu_id, out_dir)

if __name__ == "__main__":
    main()
