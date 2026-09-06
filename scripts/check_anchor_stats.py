import numpy as np
a = np.load("artifacts/dense_classifier_runs_20260904/canonical/wtb_bal_align_force_seed201/val_metrics/anchor_physics.npy")
print("val_metrics anchor min, max, mean:", float(a[..., 0].min()), float(a[..., 0].max()), float(a[..., 0].mean()))
b = np.load("artifacts/cache_signature_trainweight/wtb_245d_canonical/physics.npy")
print("cache physics min, max, mean:", float(b[..., 0].min()), float(b[..., 0].max()), float(b[..., 0].mean()))
c = np.load("artifacts/cache_signature_trainweight/wtb_245d_canonical/physics_model.npy")
print("cache physics_model min, max, mean:", float(c[..., 0].min()), float(c[..., 0].max()), float(c[..., 0].mean()))
