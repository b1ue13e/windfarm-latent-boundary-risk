import numpy as np
import pytest
from windfarm_moe.subset_inference import streamed_envelopes
from windfarm_moe.risk_frontier import shared_block_draws, simultaneous_envelope


def fixture():
    rng = np.random.default_rng(16)
    counts = np.full(12, 100.)
    return dict(costs=rng.uniform(100, 200, (2, 3, 12)),
                violations=rng.integers(0, 20, (2, 3, 12)).astype(float), counts=counts)


def test_streamed_matches_full_joint_paired_envelope():
    g = fixture()
    w, h = shared_block_draws(12, 400, 3, 42)
    c = g["costs"].mean(axis=0).sum(axis=-1) / 1200
    dc = w @ g["costs"].mean(axis=0).T / (w @ g["counts"])[:, None]
    r = g["violations"].sum(axis=-1) / 1200
    dr = np.einsum("bd,skd->bsk", w, g["violations"]) / (w @ g["counts"])[:, None, None]
    ratio, d = c[:, None] / c[None, :] - 1, dc[:, :, None] / dc[:, None, :] - 1
    exact = np.concatenate([np.zeros(r.size, bool), np.eye(3, dtype=bool).ravel()])
    full = simultaneous_envelope(np.concatenate([r.ravel(), ratio.ravel()]),
                                np.column_stack([dr.reshape(400, -1), d.reshape(400, -1)]), .05, exact)
    s = streamed_envelopes([g], 400, 3, 42, .05, chunk_size=2)
    assert s["draw_sha256"] == h
    np.testing.assert_allclose(s["critical"], full["critical"], rtol=1e-12)
    np.testing.assert_allclose(s["groups"][0]["risk_upper"], full["upper"][:r.size].reshape(r.shape))
    np.testing.assert_allclose(s["groups"][0]["relative_ratio_upper"], full["upper"][r.size:].reshape(3, 3), atol=1e-14)


def test_duplicating_instances_does_not_create_weather_replicates():
    g = fixture()
    double = {**g, "costs": np.tile(g["costs"], (2, 1, 1)), "violations": np.tile(g["violations"], (2, 1, 1))}
    a, b = [streamed_envelopes([x], 400, 3, 42, .05) for x in (g, double)]
    np.testing.assert_allclose(a["critical"], b["critical"])
    np.testing.assert_allclose(a["groups"][0]["relative_ratio_upper"], b["groups"][0]["relative_ratio_upper"])


def test_unobserved_events_are_unknown_and_only_algebra_exact_is_exact():
    g = fixture()
    g["violations"][:] = 0
    g["costs"][:, 1] = g["costs"][:, 0]
    a = streamed_envelopes([g], 400, 3, 42, .05)["groups"][0]
    np.testing.assert_array_equal(a["risk_upper"], np.ones((2, 3)))
    assert np.isinf(a["relative_ratio_upper"][0, 1])
    g["exact_pair"] = np.eye(3, dtype=bool)
    g["exact_pair"][0, 1] = g["exact_pair"][1, 0] = True
    b = streamed_envelopes([g], 400, 3, 42, .05)["groups"][0]
    assert b["relative_ratio_upper"][0, 1] == 0


def test_groups_share_population_or_fail():
    g, h = fixture(), fixture()
    h["counts"] = h["counts"] + 1
    with pytest.raises(ValueError, match="Unpaired"):
        streamed_envelopes([g, h], 400, 3, 42, .05)
