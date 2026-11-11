"""Test exact action replay and detection of internally inconsistent accounting."""
import json
from repo_paths import Path, repository_root

import numpy as np
import pytest

from scripts.audit_decision_information_actions import audit_run
from scripts.run_decision_information_development import digest
from windfarm_moe.decision_information import block_totals


def test_audit_reconstructs_float64_actions_and_rejects_bad_totals(tmp_path):
    run = tmp_path / "seed201/fresh"
    run.mkdir(parents=True)
    protocol_path = tmp_path / "protocol.json"
    protocol_path.write_text(json.dumps({"variants": ["probe"], "task": {
        "horizon_steps": 6, "commitment_age_steps": 6}}))
    anchors = np.array([144, 145, 288])
    shortfall = np.array([[0.9, 0.3], [2.0, 1.0], [0.0, 0.2]], dtype=np.float64)
    reserve = np.nextafter(shortfall, 0.0)
    mask = np.ones_like(shortfall, dtype=bool)
    np.savez(run / "evaluation_coordinates.npz", anchors=anchors, shortfall=shortfall,
             mask=mask, target_indices=anchors + 6, publication_indices=anchors - 6)
    np.savez(run / "evaluation_actions.npz", probe=reserve, probe_raw=reserve)
    totals = block_totals(shortfall, reserve, mask, anchors)
    entries = {f"probe__{version}__{name}": value for version in ("raw", "calibrated")
               for name, value in totals.items()}
    np.savez(run / "block_totals.npz", **entries)
    root = Path(repository_root())
    sources = [root / "scripts/run_decision_information_development.py", root / "windfarm_moe/decision_information.py"]
    (run / "execution_receipt.json").write_text(json.dumps({
        "status": "COMPLETED_DEVELOPMENT_NOT_CERTIFIED", "protocol_sha256": digest(protocol_path),
        "arguments": {"stage": "run", "seed": 201, "condition": "fresh"},
        "source_sha256": {str(p): digest(p) for p in sources}}))

    def seal():
        (run / "output_manifest.json").write_text(json.dumps({
            p.name: {"bytes": p.stat().st_size, "sha256": digest(p)}
            for p in run.iterdir() if p.is_file() and p.name != "output_manifest.json"}))

    seal()
    assert audit_run(run, protocol_path)["exact_block_array_checks"] == 12
    entries["probe__raw__violation_sum"] = entries["probe__raw__violation_sum"] + 1
    np.savez(run / "block_totals.npz", **entries)
    seal()
    with pytest.raises(ValueError, match="Exact accounting failed"):
        audit_run(run, protocol_path)
