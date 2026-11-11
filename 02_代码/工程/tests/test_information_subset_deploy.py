import importlib.util
import hashlib
import json
from repo_paths import Path, repository_root
import tarfile


def test_exact_byte_archive_posix_manifest(tmp_path):
    source = Path(repository_root()) / "experiments/information_subset_development_20261019/deploy_metis.py"
    spec = importlib.util.spec_from_file_location("subset_deploy_test", source)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    p = tmp_path / "base/dir/source.py"
    p.parent.mkdir(parents=True)
    p.write_bytes(b"exact\r\nbytes\r\n")
    archive, digest = m.package(tmp_path / "base", [Path("dir/source.py")], tmp_path / "out", "12345678abcdef")
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == digest
    with tarfile.open(archive) as t:
        manifest = json.load(t.extractfile("deployment_manifest.json"))
        assert list(manifest["files"]) == ["dir/source.py"]
        assert t.extractfile("dir/source.py").read() == p.read_bytes()
