import json
import subprocess
import sys
from repo_paths import Path, repository_root

import pytest

ROOT = Path(repository_root())
E04_CODE = ROOT / "experiments" / "E04" / "code"
sys.path.insert(0, str(E04_CODE))

from e04_provenance import (  # noqa: E402
    MANIFEST_NAME,
    RECEIPT_NAME,
    verify_e04_receipt,
    write_execution_plan,
    write_execution_receipt,
    write_output_manifest,
)


def make_bundle(tmp_path: Path):
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    prereg = tmp_path / "preregistration.json"
    prereg.write_text('{"experiment_id":"E04-v2"}\n', encoding="utf-8")
    outputs = []
    for seed in range(201, 206):
        path = bundle / f"seed{seed}_full_policy_day_blocks.npz"
        path.write_bytes(f"seed={seed}\n".encode("ascii"))
        outputs.append(path)
    inputs = [("preregistration", prereg)]
    names = [path.name for path in outputs]
    plan = write_execution_plan(bundle, argv=["python", "replay.py"], inputs=inputs, output_names=names)
    manifest = write_output_manifest(bundle, outputs)
    receipt = write_execution_receipt(
        bundle,
        argv=["python", "replay.py"],
        inputs=inputs,
        output_manifest=manifest,
        plan_path=plan,
    )
    return bundle, prereg, outputs, plan, manifest, receipt


def test_complete_e04_bundle_is_verified_and_exposes_hashes(tmp_path):
    bundle, prereg, outputs, plan, manifest, receipt = make_bundle(tmp_path)

    verified = verify_e04_receipt(
        receipt,
        preregistration=prereg,
        expected_output_names=[path.name for path in outputs],
    )

    assert verified["receipt_sha256"]
    assert verified["execution_plan_sha256"]
    assert verified["output_manifest_sha256"]
    assert Path(verified["output_manifest_path"]).name == MANIFEST_NAME
    assert Path(verified["receipt_path"]).name == RECEIPT_NAME


def test_output_tampering_is_rejected(tmp_path):
    bundle, prereg, outputs, _, _, receipt = make_bundle(tmp_path)
    outputs[0].write_bytes(b"tampered\n")

    with pytest.raises(ValueError, match="Evidence hash mismatch"):
        verify_e04_receipt(receipt, preregistration=prereg, expected_output_names=[p.name for p in outputs])


def test_receipt_cannot_change_command_after_preexecution_plan(tmp_path):
    bundle, prereg, outputs, plan, manifest, receipt = make_bundle(tmp_path)
    data = json.loads(receipt.read_text(encoding="utf-8"))
    data["argv"] = ["python", "different.py"]
    receipt.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="command/input binding"):
        verify_e04_receipt(receipt, preregistration=prereg, expected_output_names=[p.name for p in outputs])


def test_missing_or_extra_outputs_are_not_accepted(tmp_path):
    bundle, prereg, outputs, plan, manifest, receipt = make_bundle(tmp_path)
    extra = bundle / "unregistered.txt"
    extra.write_text("extra\n", encoding="utf-8")

    with pytest.raises(ValueError, match="output set mismatch"):
        verify_e04_receipt(receipt, preregistration=prereg, expected_output_names=[p.name for p in outputs] + [extra.name])

    receipt.unlink()
    with pytest.raises(ValueError, match="execution receipt missing"):
        verify_e04_receipt(receipt, preregistration=prereg)


def test_preregistration_hash_is_bound_to_receipt(tmp_path):
    bundle, prereg, outputs, _, _, receipt = make_bundle(tmp_path)
    prereg.write_text('{"experiment_id":"changed"}\n', encoding="utf-8")

    with pytest.raises(ValueError, match="Preregistration hash"):
        verify_e04_receipt(receipt, preregistration=prereg, expected_output_names=[p.name for p in outputs])


def test_receipt_reports_the_bundle_consumed_by_selector(tmp_path):
    bundle, prereg, outputs, _, _, receipt = make_bundle(tmp_path)
    verified = verify_e04_receipt(receipt, preregistration=prereg, expected_output_names=[p.name for p in outputs])
    assert Path(verified["bundle_root"]).resolve() == bundle.resolve()


def test_selector_fails_closed_without_receipt(tmp_path):
    bundle, prereg, outputs, _, _, receipt = make_bundle(tmp_path)
    receipt.unlink()
    selector = E04_CODE / "select_e04_v2.py"
    result = subprocess.run(
        [sys.executable, str(selector), "--root", str(bundle), "--out", str(tmp_path / "selection.json"),
         "--receipt", str(receipt), "--preregistration", str(prereg)],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "execution receipt missing" in result.stderr
