import hashlib, json
import pytest
from scripts.run_floor_addendum import load_bound_parent_protocol


def _setup_fixture(tmp_path):
    parent = tmp_path / "parent_results"
    parent.mkdir()
    src = tmp_path / "source_protocol.json"
    obj = {
        "historical_cache": "/data/hist",
        "evaluation_cache": "/data/eval",
        "historical_manifest_sha256": "abc123",
        "evaluation_manifest_sha256": "def456",
        "nested": {"alpha": 1, "beta": [2, 3]},
    }
    crlf_bytes = json.dumps(obj, indent=2).replace("\n", "\r\n").encode("utf-8")
    lf_bytes = json.dumps(obj, indent=2).replace("\r\n", "\n").encode("utf-8")
    src.write_bytes(crlf_bytes)
    (parent / "protocol.json").write_bytes(lf_bytes)
    expected_sha = hashlib.sha256(crlf_bytes).hexdigest()
    (parent / "FINAL_FREEZE.json").write_text(
        json.dumps({"protocol_sha256": expected_sha}), encoding="utf-8"
    )
    return parent, src, obj


def test_crlf_source_vs_lf_result_semantically_equal_accepted(tmp_path):
    parent, src, obj = _setup_fixture(tmp_path)
    assert src.read_bytes() != (parent / "protocol.json").read_bytes()
    parsed = load_bound_parent_protocol(parent, src)
    assert parsed == obj


def test_changed_result_field_rejected(tmp_path):
    parent, src, obj = _setup_fixture(tmp_path)
    tampered = dict(obj, historical_cache="/data/other")
    (parent / "protocol.json").write_bytes(
        json.dumps(tampered, indent=2).replace("\r\n", "\n").encode("utf-8")
    )
    with pytest.raises(ValueError, match="diverged|changed"):
        load_bound_parent_protocol(parent, src)


def test_changed_original_bytes_even_if_json_equal_rejected(tmp_path):
    parent, src, obj = _setup_fixture(tmp_path)
    # Rewrite source with LF (or extra whitespace) so JSON is identical but bytes differ from frozen SHA
    src.write_bytes((json.dumps(obj, indent=2) + "\n").encode("utf-8"))
    assert json.loads(src.read_text(encoding="utf-8")) == obj
    with pytest.raises(ValueError, match="Parent protocol identity changed"):
        load_bound_parent_protocol(parent, src)
