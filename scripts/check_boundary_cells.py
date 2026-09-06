from windfarm_moe.data import load_cache_bundle
from pathlib import Path
import numpy as np

bundle = load_cache_bundle(Path("artifacts/cache_signature_trainweight/wtb_245d_canonical"))
w_mean = bundle.metadata["physics_model_stats"]["0"]["mean"]
w_std = bundle.metadata["physics_model_stats"]["0"]["std"]

# Check test slice of physics
test_start, test_end = bundle.metadata["split_bounds"]["test"]
phys_slice = bundle.physics[test_start:test_end]
w_phys = phys_slice[..., 0]
band_cells = (np.abs(w_phys - 10.5) <= 1.0).sum()
print("Physical wind in [9.5, 11.5] on test split:", band_cells, "cells out of", w_phys.size, f"({band_cells/w_phys.size:.2%})")

mod_slice = bundle.physics_model[test_start:test_end]
w_reconstructed = mod_slice[..., 0] * w_std + w_mean
diff = np.abs(w_phys - w_reconstructed).max()
print("Max diff between raw physics and unstandardized physics_model:", diff)
