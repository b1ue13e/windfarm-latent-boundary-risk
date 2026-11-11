import importlib.util
from repo_paths import Path, repository_root
import json
import tarfile


def test_compact_export_checks_exact_bytes_and_refuses_replacement(tmp_path):
    import pytest
    path = Path(repository_root()) / "scripts/export_information_subset_evidence.py"
    spec = importlib.util.spec_from_file_location("subset_export_test", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    p = tmp_path / "fixture.json"
    p.write_bytes(b'{"synthetic_fixture":true}\r\n')
    out = tmp_path / "compact.tar.gz"
    receipt = m.export_members({"nested/fixture.json": p}, out)
    assert receipt["members"] == 1
    with tarfile.open(out) as t:
        manifest = json.load(t.extractfile("export_manifest.json"))
        assert manifest["nested/fixture.json"]["sha256"] == m.sha(p)
        assert t.extractfile("nested/fixture.json").read() == p.read_bytes()
    with pytest.raises(FileExistsError):
        m.export_members({"nested/fixture.json": p}, out)
