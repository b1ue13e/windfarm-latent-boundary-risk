from pathlib import Path as NativePath
from repo_paths import Path, repository_root, resolve_legacy, path_map


def test_original_and_moved_paths_are_equivalent():
    root = repository_root()
    for old, new in path_map().items():
        assert resolve_legacy(root / old) == root / new
        assert resolve_legacy(root / new) == root / new
        assert (root / new).exists(), old


def test_incremental_joins_resolve_nested_evidence():
    root = Path(repository_root())
    assert root / "experiments" / "E04" == resolve_legacy(repository_root() / "experiments/E04")
    assert (root / "docs" / "SCIENTIFIC_CONTRACT.md").is_file()


def test_external_and_temporary_roots_are_unchanged(tmp_path):
    assert Path(tmp_path) / "artifacts" / "x.csv" == tmp_path / "artifacts/x.csv"
    assert resolve_legacy(tmp_path / "experiments/E04") == tmp_path / "experiments/E04"


def test_parent_relative_protected_input_resolves_after_migration():
    root = repository_root()
    old = root / "01_当前论文/TSTE/../../docs/SCIENTIFIC_CONTRACT.md"
    assert resolve_legacy(old) == resolve_legacy(root / "docs/SCIENTIFIC_CONTRACT.md")


def test_caches_and_results_resolve_consistently_during_incremental_joins():
    root = Path(repository_root())
    for name in ("artifacts/cache_signature", "artifacts/cache_strictmask", "experiments/E04",
                 "analyses/praw_supplement_v3_execution_20261021"):
        joined = root
        for part in name.split("/"):
            joined = joined / part
        assert joined == resolve_legacy(repository_root() / name)
        assert joined.exists()


def test_new_layout_keeps_current_paper_sources_and_raw_data_separate():
    root = repository_root()
    assert (root / "01_当前论文/TSTE/manuscript.tex").is_file()
    assert (root / "02_代码/工程/windfarm_moe/independent_confirmation.py").is_file()
    assert resolve_legacy(root / "wtbdata_245days.csv") == root / "03_数据/原始/wtbdata_245days.csv"
    assert (root / "04_结果/实验/mainline_supplement_20261026/FINAL_RESULTS.json").is_file()
