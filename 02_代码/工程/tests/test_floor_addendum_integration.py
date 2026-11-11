import json, time
import numpy as np
import scripts.run_floor_addendum as mod


def test_floor_addendum_historical_helpers(tmp_path, monkeypatch):
    cache, out = tmp_path / "cache", tmp_path / "out"
    cache.mkdir()
    out.mkdir()
    a = np.arange(12, dtype=np.int64)
    y = np.tile([[2.0, 4.0]], (12, 1))
    y[8:12, 1] = 4.5
    m = np.ones((12, 2), dtype=bool)
    m[9, 1] = False
    np.save(cache / "anchors.npy", a)
    np.save(cache / "shortfall.npy", y)
    np.save(cache / "mask.npy", m)
    for arm, vals in [("P", (3.0, 5.0)), ("Z", (5.0, 3.0))]:
        x = np.empty((12, 2, 9), dtype=float)
        x[:, :, 0] = 1.0
        x[:, :, 1:5] = vals[0]
        x[:, :, 5:] = vals[1]
        np.save(cache / f"{arm}_seed201.npy", x)

    monkeypatch.setitem(mod.PHASES, "inner", (8, 12, 1))
    online_arm = dict(eta=0.03, schedule_power=0.5, severity_step=0.0, cost_scale=100.0)
    cfg = dict(
        historical_cache=str(cache),
        anchor_config=dict(method="tracker", target_event_rate=0.05, step_size=0.03),
        online_config=dict(P=online_arm, Z=online_arm),
    )

    mod.profile_task((cfg, str(out), 201, False))
    b = np.load(out / "profiles/historical_seed201.npy")[(a >= 8) & (a < 12)]
    ye, me = y[8:12], m[8:12]
    b_u = np.maximum(ye - b, 0.0)[me] / 6.0
    b_v = (ye > b)[me]

    for arm in ["P", "Z"]:
        mod.fit_task((cfg, str(out), "inner", 201, arm, time.time() + 60))
        ret = mod.eval_task((cfg, str(out), "inner", 201, arm, time.time() + 60))
        init = json.loads((out / f"initializers/inner/{arm}_seed201.json").read_text())
        receipt = json.loads((out / f"instances/inner/{arm}_seed201/receipt.json").read_text())
        daily = np.load(out / f"instances/inner/{arm}_seed201/daily.npz")
        assert ret["completed"] == 2 and ret["expected"] == 2
        assert receipt["completed"] == 2 and receipt["expected"] == 2
        assert not receipt["qualification_filter"] and receipt["science_target_unchanged"]
        assert init["last_label_release"] < init["episode_start"]
        assert daily["ledger"].shape == (2, 1, 4)
        assert int(daily["counts"].sum()) == int(me.sum())
        np.testing.assert_allclose(daily["ledger"][0], daily["ledger"][1], rtol=0, atol=0)

        xe = np.load(cache / f"{arm}_seed201.npy")[8:12]
        w = np.asarray(init["canonical_initial"])
        inc = np.concatenate([np.zeros((*b.shape, 1)), np.maximum(xe - b[:, :, None], 0.0)], axis=-1)
        static = b + np.sum(inc * w, axis=-1)
        r_m, y_m, yr_m = static[me], ye[me], np.maximum(ye - b, 0.0)[me]
        u_orig = np.maximum(y_m - r_m, 0.0) / 6.0
        expected = np.array([[np.sum(r_m / 6.0 + 10.0 * u_orig), np.sum(r_m / 6.0), np.sum(u_orig), np.sum(y_m > r_m)]])
        np.testing.assert_allclose(daily["ledger"][0], expected, rtol=1e-12, atol=1e-12)
        assert daily["ledger"][0, 0, 3] > np.sum(yr_m > r_m)
        assert daily["ledger"][0, 0, 2] <= float(np.sum(b_u)) and daily["ledger"][0, 0, 3] <= float(np.sum(b_v))
