import importlib.util
import sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from run_channel_consequence_ablations import residual_at_horizon, compute_transition_recall
from run_exp03_async_benchmark import simulate_asynchronous_scada_stream


def test_h6_uses_sixth_residual_not_second():
    a = np.arange(12).reshape(2, 6, 1)
    result = residual_at_horizon({'shortfall_test_seed201': a}, 'test', 201, 6)
    assert result[:, 0].tolist() == [5, 11]


def test_invalid_adjacent_labels_do_not_create_transition_events():
    labels = np.array([1, 0, 1, 1])[:, None]
    valid = np.array([1, 0, 1, 1], dtype=bool)[:, None]
    _, legacy_n = compute_transition_recall(labels, labels, return_count=True)
    recall, n = compute_transition_recall(labels, labels, valid=valid, return_count=True)
    assert legacy_n > 0
    assert n == 0 and recall == 0


def test_async_full_archive_reconstructs_all_inputs_without_future_packets(tmp_path):
    names = ['Wspd', 'Patv_hist', 'Etmp', 'Itmp', 'Prtv']
    raw = np.arange(60, dtype=np.float32).reshape(6, 2, 5) + 17
    path = tmp_path / 'packets.npz'
    observed, missing, stats, _ = simulate_asynchronous_scada_stream(
        raw, names, mean_delay=6, max_lateness=4, seed=20261012, archive_path=path)
    z = np.load(path)
    assert z['delays'].shape == raw.shape
    for t in range(6):
        for n in range(2):
            for c in range(5):
                source = z['selected_source'][t,n,c]
                if source < 0:
                    assert observed[t,n,c] == 0
                else:
                    assert source + z['delays'][source,n,c] <= t
                    assert observed[t,n,c] == raw[source,n,c]
    assert np.array_equal(z['contaminated_features'], observed)
    assert np.array_equal(z['dropped_mask'], missing)
    assert stats['initial_value_standardized'] == 0
