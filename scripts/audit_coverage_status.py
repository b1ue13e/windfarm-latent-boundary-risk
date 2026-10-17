import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
cov_path = ROOT / "artifacts/raw_replay_20261015_v2/coverage.json"
coverage = json.loads(cov_path.read_text(encoding="utf-8"))

print(f"Total historical artifacts: {len(coverage)}")
for idx, item in enumerate(coverage, 1):
    art = item["historical_artifact"]
    script = item.get("generating_script", "None")
    claims_cnt = len(item.get("claims", []))
    print(f"[{idx:02d}] {art} (script: {script}, claims: {claims_cnt})")
