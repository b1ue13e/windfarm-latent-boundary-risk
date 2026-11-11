"""PBS dispatcher; exact source archive and environment are recorded per job."""
from pathlib import Path
import os
import subprocess
import sys

root = Path(__file__).resolve().parents[2]
stage = os.environ["SUBSET_STAGE"]
if stage == "preflight":
    subprocess.run([sys.executable, "-m", "pytest", "tests/test_information_subset.py",
                    "tests/test_information_subset_runner.py", "tests/test_subset_inference.py", "-q"], cwd=root, check=True)
else:
    command = [sys.executable, str(root / "scripts/run_information_subset_study.py"), stage,
               "--protocol", str(root / "experiments/information_subset_development_20261019/protocol.json"),
               "--output", str(root / "results")]
    if stage in ("historical", "evaluate"):
        command += ["--task-index", os.environ.get("SUBSET_TASK_INDEX", os.environ.get("PBS_ARRAY_INDEX", "0"))]
    subprocess.run(command, cwd=root, check=True)
