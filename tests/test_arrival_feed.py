"""Unit tests for the causally symmetric UnifiedArrivalDataset."""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pytest
import torch

from windfarm_moe.arrival_feed import (
    DegradationSpec,
    UnifiedArrivalDataset,
    extract_symmetric_rule_input,
    simulate_markov_gilbert_lags,
)
from windfarm_moe.data import RegimeWindowDataset, load_cache_bundle


CACHE_DIRS = [
    Path("artifacts/cache_strictmask/wtb_245d"),
    Path("artifacts/cache_strictmask_trainweights/wtb_245d"),
    Path("artifacts/cache_signature_trainweight/wtb_245d_canonical"),
]


@pytest.fixture(scope="module")
def wtb_bundle():
    cache_dir = None
    for c in CACHE_DIRS:
        if c.exists() and (c / "metadata.json").exists():
            cache_dir = c
            break
    if cache_dir is None:
        pytest.skip("No valid WTB cache directory found.")
    return load_cache_bundle(cache_dir, mmap_mode="r")


def test_clean_equivalence(wtb_bundle):
    base_ds = RegimeWindowDataset(wtb_bundle, "test", hist_len=36, pred_len=24)
    feed_ds = UnifiedArrivalDataset(wtb_bundle, "test", hist_len=36, pred_len=24, degradation=DegradationSpec(delay_steps=0))

    assert len(base_ds) == len(feed_ds)
    item_base = base_ds[0]
    item_feed = feed_ds[0]

    assert torch.equal(item_base["x_hist"], item_feed["x_hist"])
    assert torch.equal(item_base["anchor_physics"], item_feed["anchor_physics"])
    assert item_feed["lag_applied"] == 0


def test_symmetric_stalled_delay(wtb_bundle):
    delay = 6
    feed_ds = UnifiedArrivalDataset(
        wtb_bundle,
        "test",
        hist_len=36,
        pred_len=24,
        degradation=DegradationSpec(
            delay_steps=delay,
            corrupted_channels=("Wspd", "Pab_mean"),
            history_policy="stalled",
        ),
    )
    base_ds = RegimeWindowDataset(wtb_bundle, "test", hist_len=36, pred_len=24)

    item_feed = feed_ds[10]
    item_base = base_ds[10]

    H = item_feed["x_hist"].shape[0]
    feat_names = list(wtb_bundle.metadata["feature_names"])
    wspd_idx = feat_names.index("Wspd")
    pab_idx = feat_names.index("Pab_mean")

    # In feed_ds, readings at step H-1 (anchor) must equal readings at H-1-delay
    stalled_step = H - 1 - delay
    assert torch.equal(
        item_feed["x_hist"][H - 1, :, wspd_idx],
        item_feed["x_hist"][stalled_step, :, wspd_idx],
    )
    assert torch.equal(
        item_feed["x_hist"][H - 1, :, pab_idx],
        item_feed["x_hist"][stalled_step, :, pab_idx],
    )

    # In base_ds (the clean stream), the reading at H-1 should NOT equal H-1-delay in general
    assert not torch.equal(
        item_base["x_hist"][H - 1, :, wspd_idx],
        item_base["x_hist"][stalled_step, :, wspd_idx],
    )

    # Check that rule input extracted matches anchor_physics
    w_rule, p_rule = extract_symmetric_rule_input(item_feed, wtb_bundle.metadata)
    phy_names = list(wtb_bundle.metadata.get("physics_names", []))
    assert torch.equal(w_rule, item_feed["anchor_physics"][:, phy_names.index("Wspd")])
    assert torch.equal(p_rule, item_feed["anchor_physics"][:, phy_names.index("Pab_mean")])


def test_markov_gilbert_synchrony(wtb_bundle):
    feed_ds = UnifiedArrivalDataset(
        wtb_bundle,
        "test",
        hist_len=36,
        pred_len=24,
        degradation=DegradationSpec(
            use_markov_gilbert=True,
            p_gb=0.15,
            p_bb=0.70,
            max_lag=6,
            random_seed=42,
        ),
    )

    # Find an item where lag > 0
    found_lag = False
    for i in range(min(100, len(feed_ds))):
        item = feed_ds[i]
        lag = item["lag_applied"]
        if lag > 0:
            found_lag = True
            H = item["x_hist"].shape[0]
            feat_names = list(wtb_bundle.metadata["feature_names"])
            wspd_idx = feat_names.index("Wspd")
            stalled_step = max(0, H - 1 - lag)
            # Check stalled history matches
            assert torch.equal(
                item["x_hist"][H - 1, :, wspd_idx],
                item["x_hist"][stalled_step, :, wspd_idx],
            )
            break
    assert found_lag, "Expected at least one burst lag > 0 in 100 steps."


def test_all_channels_and_mask_synchrony(wtb_bundle):
    delay = 3
    feed_ds = UnifiedArrivalDataset(
        wtb_bundle,
        "test",
        hist_len=36,
        pred_len=24,
        degradation=DegradationSpec(
            delay_steps=delay,
            corrupted_channels=("all",),
            history_policy="stalled",
        ),
    )
    item = feed_ds[5]
    H = item["x_hist"].shape[0]
    stalled_step = H - 1 - delay

    # All feature channels must be stalled
    for feat_idx in range(item["x_hist"].shape[-1]):
        assert torch.equal(
            item["x_hist"][H - 1, :, feat_idx],
            item["x_hist"][stalled_step, :, feat_idx],
        )
        assert torch.equal(
            item["feature_mask_hist"][H - 1, :, feat_idx],
            item["feature_mask_hist"][stalled_step, :, feat_idx],
        )

    # Dynamic edge graphs must also be stalled
    if "edge_index_hist" in item:
        assert torch.equal(
            item["edge_index_hist"][H - 1],
            item["edge_index_hist"][stalled_step],
        )
        assert torch.equal(
            item["edge_weight_hist"][H - 1],
            item["edge_weight_hist"][stalled_step],
        )


def test_channel_withholding(wtb_bundle):
    feat_names = list(wtb_bundle.metadata["feature_names"])
    pab_idx = feat_names.index("Pab_mean")
    wspd_idx = feat_names.index("Wspd")
    phy_names = list(wtb_bundle.metadata.get("physics_names", []))
    phy_pab_idx = phy_names.index("Pab_mean")

    base_ds = RegimeWindowDataset(wtb_bundle, "test", hist_len=36, pred_len=24)
    item_base = base_ds[10]

    # Test 1: delay_steps=0 with withheld pitch
    feed_clean_ds = UnifiedArrivalDataset(
        wtb_bundle,
        "test",
        hist_len=36,
        pred_len=24,
        degradation=DegradationSpec(delay_steps=0, withheld_channels=("Pab_mean",)),
    )
    item_clean = feed_clean_ds[10]
    assert torch.all(item_clean["x_hist"][:, :, pab_idx] == 0.0)
    assert torch.all(item_clean["feature_mask_hist"][:, :, pab_idx] == 0.0)
    assert torch.all(item_clean["anchor_physics"][:, phy_pab_idx] == 0.0)
    # Other channels should match base
    assert torch.equal(item_clean["x_hist"][:, :, wspd_idx], item_base["x_hist"][:, :, wspd_idx])

    # Test 2: delay_steps=6 with withheld pitch and stalled other channels
    feed_stale_ds = UnifiedArrivalDataset(
        wtb_bundle,
        "test",
        hist_len=36,
        pred_len=24,
        degradation=DegradationSpec(
            delay_steps=6,
            corrupted_channels=("all",),
            withheld_channels=("Pab_mean",),
            history_policy="stalled",
        ),
    )
    item_stale = feed_stale_ds[10]
    assert torch.all(item_stale["x_hist"][:, :, pab_idx] == 0.0)
    assert torch.all(item_stale["feature_mask_hist"][:, :, pab_idx] == 0.0)
    assert torch.all(item_stale["anchor_physics"][:, phy_pab_idx] == 0.0)

    # Wspd should be stalled
    H = item_stale["x_hist"].shape[0]
    stalled_step = H - 1 - 6
    assert torch.equal(
        item_stale["x_hist"][H - 1, :, wspd_idx],
        item_stale["x_hist"][stalled_step, :, wspd_idx],
    )

