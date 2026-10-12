import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
import time

class NoGraphQuantileMLP(nn.Module):
    def __init__(self, in_features: int = 5, hidden_dim: int = 64):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_features, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(0.05),
            nn.Linear(hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, 1),
            nn.ReLU(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x).squeeze(-1)

def pinball_loss_tensor(pred_r: torch.Tensor, target_s: torch.Tensor, tau: float = 0.90) -> torch.Tensor:
    u = target_s - pred_r
    return torch.maximum(tau * u, (tau - 1.0) * u).mean()

def test_mlp_fit():
    t0 = time.time()
    # Dummy data with real shapes
    T_val, N = 4261, 14
    T_test = 4981
    anc_val = np.random.randn(T_val, N, 4).astype(np.float32)
    s_val = np.abs(np.random.randn(T_val, N)).astype(np.float32) * 50.0
    mask_val = np.ones((T_val, N), dtype=bool)
    anc_test = np.random.randn(T_test, N, 4).astype(np.float32)

    def extract_feats(anc):
        wspd = anc[..., 0:1]
        temp = anc[..., 2:3]
        patv = anc[..., 3:4]
        w_sq = wspd ** 2
        p_ratio = np.clip(patv / 2000.0, 0.0, 1.5)
        return np.concatenate([wspd, temp, patv, w_sq, p_ratio], axis=-1)

    feats_val = extract_feats(anc_val)
    feats_test = extract_feats(anc_test)

    # 70/30 train/val split
    split_idx = int(T_val * 0.7)
    X_tr = feats_val[:split_idx].reshape(-1, 5)
    y_tr = s_val[:split_idx].reshape(-1)
    X_va = feats_val[split_idx:].reshape(-1, 5)
    y_va = s_val[split_idx:].reshape(-1)

    mean = np.mean(X_tr, axis=0, keepdims=True)
    std = np.std(X_tr, axis=0, keepdims=True) + 1e-6
    X_tr_norm = (X_tr - mean) / std
    X_va_norm = (X_va - mean) / std

    ds = TensorDataset(torch.tensor(X_tr_norm, dtype=torch.float32), torch.tensor(y_tr, dtype=torch.float32))
    loader = DataLoader(ds, batch_size=256, shuffle=True)

    model = NoGraphQuantileMLP()
    opt = torch.optim.AdamW(model.parameters(), lr=1e-3)

    for epoch in range(8):
        model.train()
        for bx, by in loader:
            opt.zero_grad()
            l = pinball_loss_tensor(model(bx), by, tau=0.90)
            l.backward()
            opt.step()

    model.eval()
    with torch.no_grad():
        X_te_norm = (feats_test.reshape(-1, 5) - mean) / std
        pred = model(torch.tensor(X_te_norm, dtype=torch.float32)).numpy().reshape(T_test, N)

    print(f"MLP training and test prediction completed in {time.time() - t0:.2f}s!")
    print(f"Test pred min: {pred.min():.2f}, mean: {pred.mean():.2f}, max: {pred.max():.2f}")

test_mlp_fit()
