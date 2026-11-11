"""Publication checks preserve stopped research and exclude local-only assets."""
import importlib.util
from repo_paths import Path, repository_root

spec = importlib.util.spec_from_file_location("github_checkout", Path(repository_root()) / "scripts/verify_github_checkout.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_archived_research_is_valid_without_claiming_completion():
    state = dict(status="stopped", active_task=None, phase="archived_no_additional_investment")
    assert module.valid_research_state(state)
    assert state["status"] == "stopped"
    assert not module.valid_research_state(dict(state, active_task="still-running"))
    assert not module.valid_research_state(dict(state, phase="training"))
    assert not module.valid_research_state(dict(status="running"))


def test_publication_rejects_data_weights_and_packed_bundles():
    for name in ["03_数据/原始/data.csv", "04_结果/实验/model.pt", "04_结果/实验/weights.joblib",
                 "04_结果/分析/evidence.tar.gz", "04_结果/复现运行/check.json", "02_代码/__pycache__/a.pyc"]:
        assert module.forbidden_upload(name), name
    for name in ["03_数据/README.md", "04_结果/分析/primary.csv", "04_结果/审计/receipt.json", "02_代码/工程/project.py"]:
        assert not module.forbidden_upload(name), name
