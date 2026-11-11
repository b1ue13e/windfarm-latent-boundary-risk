"""Allocated-stage launcher with an explicit immutable worker grid."""
import json
import os
from pathlib import Path
import subprocess
import sys


root = Path(os.environ["FRONTIER_ROOT"])
os.chdir(root)
if not os.environ.get("PBS_JOBID"):
    raise RuntimeError("Numerical execution requires a PBS allocation")
protocol = root / "experiments/risk_cost_frontier_development_20261018/protocol.json"
settings = json.loads(protocol.read_text())
stage = os.environ["FRONTIER_STAGE"]
grid = [(s, c) for s in settings["seeds"] for c in settings["conditions"]]
if stage == "smoke":
    subprocess.run([sys.executable, "-m", "pytest", "tests/test_risk_frontier.py", "tests/test_risk_frontier_runner.py",
                    "tests/test_decision_information.py", "tests/test_decision_information_actions.py", "-q"], check=True)
    stage, seed, condition = "historical", 201, "pitch_withheld"
elif stage == "historical":
    remaining = [(s, c) for s, c in grid if (s, c) != (201, "pitch_withheld")]
    seed, condition = remaining[int(os.environ["PBS_ARRAY_INDEX"])]
elif stage == "evaluate":
    seed, condition = grid[int(os.environ["PBS_ARRAY_INDEX"])]
else:
    seed, condition = 201, "pitch_withheld"
output = (root / f"results/{stage}/seed{seed}/{condition}") if stage in ("historical", "evaluate") else root / "results" / stage
args = [sys.executable, "-u", str(root / "scripts/run_risk_cost_frontier.py"), stage,
        "--protocol", str(protocol), "--output", str(output), "--seed", str(seed), "--condition", condition,
        "--historical", str(root / "results/historical"), "--choice", str(root / "results/choose"),
        "--runs", str(root / "results/evaluate")]
os.execv(sys.executable, args)
