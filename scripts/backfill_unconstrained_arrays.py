import numpy as np

from windfarm_moe.data import load_cache_bundle


def main() -> None:
    bundle = load_cache_bundle("artifacts/cache_strictmask/wtb_245d", mmap_mode="r")
    out_dir = "artifacts/strictmask_ablation_rerun_wtb_full/wtb_unconstrained_seed201/test_metrics"
    anchors = np.load(f"{out_dir}/anchor_index.npy").astype(np.int64)
    H = int(bundle.metadata["pred_len"])
    idx = anchors[:, None] + np.arange(1, H + 1)[None, :]
    target = np.asarray(bundle.target[idx], dtype=np.float32)
    mask = np.asarray(bundle.target_mask[idx], dtype=np.float32)
    np.save(f"{out_dir}/target.npy", target)
    np.save(f"{out_dir}/mask.npy", mask)
    print("saved target/mask:", target.shape, mask.shape)


if __name__ == "__main__":
    main()
