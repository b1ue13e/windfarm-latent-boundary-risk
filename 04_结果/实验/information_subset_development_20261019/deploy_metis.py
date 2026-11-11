"""Deploy an exact-byte source archive, then run allocated-node preflight."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import tarfile


def package(base, files, output, commit):
    output.mkdir(exist_ok=True, parents=True)
    manifest = output / f"deployment_manifest_{commit[:8]}.json"
    archive = output / f"source_bundle_{commit[:8]}.tar.gz"
    record = dict(git_commit=commit, files={p.as_posix(): hashlib.sha256((base / p).read_bytes()).hexdigest() for p in files},
                  note="Exact tested working-file bytes; no raw SCADA or historical outputs")
    with manifest.open("x", encoding="utf-8") as f:
        json.dump(record, f, indent=2)
    with tarfile.open(archive, "x:gz") as t:
        for p in files:
            t.add(base / p, arcname=p.as_posix())
        t.add(manifest, arcname="deployment_manifest.json")
    return archive, hashlib.sha256(archive.read_bytes()).hexdigest()


def main():
    base = Path(__file__).resolve().parents[2]
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=base, text=True).strip()
    fixed = ["windfarm_moe/__init__.py", "windfarm_moe/decision_information.py", "windfarm_moe/risk_frontier.py",
             "windfarm_moe/information_subset.py", "windfarm_moe/subset_inference.py", "scripts/run_information_subset_study.py",
             "tests/test_information_subset.py", "tests/test_information_subset_runner.py", "tests/test_subset_inference.py"]
    files = [Path(p) for p in fixed]
    for directory in ["information_subset_development_20261019", "independent_confirmation_20261019"]:
        files += [p.relative_to(base) for p in (base / "experiments" / directory).rglob("*")
                  if p.is_file() and "__pycache__" not in p.parts]
    output = base / "analyses/information_subset_execution_20261019"
    archive, digest = package(base, files, output, commit)
    root = f"/nfs/ihfs/home_metis/junyu/dsh-scratch/information_subset_20261019_{commit[:8]}"
    target = root + ".tar.gz"
    options = ["-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes", "-o", "ConnectTimeout=15"]
    subprocess.run(["scp", *options, str(archive), "metis:" + target], check=True)
    code = '''
from pathlib import Path
import hashlib,tarfile,json,subprocess
root=Path(ROOT_VALUE); archive=Path(ARCHIVE_VALUE)
assert hashlib.sha256(archive.read_bytes()).hexdigest()==DIGEST_VALUE
root.mkdir(exist_ok=False)
with tarfile.open(archive) as t:t.extractall(root,filter='data')
manifest=json.loads((root/'deployment_manifest.json').read_text())
for name,value in manifest['files'].items():
 assert hashlib.sha256((root/name).read_bytes()).hexdigest()==value,name
(root/'logs').mkdir()
source=root/'experiments/information_subset_development_20261019/run.pbs'
wrapper=root/'run_lf.pbs';wrapper.write_bytes(source.read_bytes().replace(b'\\r\\n',b'\\n'))
subprocess.run(['bash','-n',str(wrapper)],check=True)
job=subprocess.check_output(['qsub','-v',f'SUBSET_ROOT={root},SUBSET_STAGE=preflight','-l','walltime=00:30:00','-o',str(root/'logs/preflight.log'),str(wrapper)],text=True).strip()
source=root/'experiments/independent_confirmation_20261019'; binding=source/'source_binding.json'
bh=hashlib.sha256(binding.read_bytes()).hexdigest()
data=root.parent/('hill_of_towie_confirmation_20261019_'+manifest['git_commit'][:8])
with (root/'logs/data_acquisition.log').open('xb') as handle:
 proc=subprocess.Popen(['/lstr/sahara/minlpml/junyu/paper3_raw_replay_20261015/.venv/bin/python',str(source/'acquire_hill_of_towie.py'),'--binding',str(binding),'--binding-sha256',bh,'--output',str(data)],stdin=subprocess.DEVNULL,stdout=handle,stderr=subprocess.STDOUT,start_new_session=True)
record=dict(root=str(root),source_archive_sha256=DIGEST_VALUE,preflight_job=job,acquisition_pid=proc.pid,data_root=str(data),binding_sha256=bh)
(root/'deployment.json').write_text(json.dumps(record,indent=2)); print(json.dumps(record))
'''
    for token, value in [("ROOT_VALUE", root), ("ARCHIVE_VALUE", target), ("DIGEST_VALUE", digest)]:
        code = code.replace(token, repr(value))
    result = subprocess.run(["ssh", *options, "metis", "/lstr/sahara/minlpml/junyu/paper3_raw_replay_20261015/.venv/bin/python -"],
                            input=code, text=True, capture_output=True, check=True)
    with (output / f"deployment_{commit[:8]}.json").open("x", encoding="utf-8") as f:
        f.write(result.stdout)
    print(result.stdout)


if __name__ == "__main__":
    main()
