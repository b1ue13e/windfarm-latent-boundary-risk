"""Synthetic network bytes only: tests never open real SCADA archives."""
import hashlib
import importlib.util
import io
from repo_paths import Path, repository_root

import pytest

SCRIPT = Path(repository_root()) / "experiments/independent_confirmation_20261019/acquire_hill_of_towie.py"
spec = importlib.util.spec_from_file_location("opaque_confirmation_acquisition", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def record(year=2025, payload=b"opaque synthetic bytes"):
    return {"year": year, "role": {2023: "train", 2024: "calibration", 2025: "locked_test"}[year],
            "name": f"{year}.zip", "bytes": len(payload),
            "url": f"https://zenodo.org/api/records/22662930/files/{year}.zip/content",
            "official_md5": hashlib.md5(payload).hexdigest()}


def test_binding_requires_fixed_years_roles_and_official_url():
    binding = {"record_id": 22662930, "measurement_access_allowed": False,
               "archives": [record(y) for y in (2023, 2024, 2025)]}
    module.validate_binding(binding)
    binding["archives"][2]["role"] = "calibration"
    with pytest.raises(ValueError, match="Year/role"):
        module.validate_binding(binding)
    binding["archives"][2] = record()
    binding["archives"][0]["url"] = "https://other.example/2023.zip"
    with pytest.raises(ValueError, match="official"):
        module.validate_binding(binding)


def test_acquisition_checks_raw_bytes_without_parser_and_refuses_overwrite(tmp_path):
    payload = b"opaque synthetic bytes"
    destination = tmp_path / "2025.zip"
    result = module.acquire_one(record(payload=payload), destination,
                                opener=lambda *a, **k: io.BytesIO(payload))
    assert result["sha256"] == hashlib.sha256(payload).hexdigest()
    assert result["role"] == "locked_test"
    assert destination.read_bytes() == payload
    with pytest.raises(FileExistsError):
        module.acquire_one(record(payload=payload), destination, opener=lambda *a, **k: io.BytesIO(payload))
    assert destination.read_bytes() == payload


def test_bad_download_preserves_failure_bytes_without_sealing_test(tmp_path):
    destination = tmp_path / "2025.zip"
    with pytest.raises(ValueError, match="MD5 mismatch"):
        module.acquire_one(record(), destination, opener=lambda *a, **k: io.BytesIO(b"wrong"))
    assert not destination.exists()
    assert destination.with_suffix(".zip.part").read_bytes() == b"wrong"
