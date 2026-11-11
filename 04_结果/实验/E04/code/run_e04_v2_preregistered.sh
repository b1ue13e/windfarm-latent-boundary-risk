#!/usr/bin/env bash
set -euo pipefail
REPO=/lstr/sahara/minlpml/junyu/paper3_raw_replay_20261015
PREREG_COMMIT=64478031c8ba630edff8f57851e90de4f2bdc6cb
PREREG_FILE=/home/junyu/dsh-scratch/e04_v2_prereg/PREREGISTRATION_E04_V2.json
PREREG_HASH=BD95A16802F312B08D06CA3F04974BE47DC76316C3A3886625C95E0E5D77354C
BASE="$REPO/artifacts/raw_replay_20261015_v2/e04_strong_baseline_replay_v4"
OUT=/home/junyu/dsh-scratch/e04_v2_run
mkdir -p "$OUT/arrays" "$OUT/selector"
# Bind execution to the prereg-only commit and immutable prereg JSON before reading outputs.
cd "$REPO"
test "$(git rev-parse 64478031c8ba630edff8f57851e90de4f2bdc6cb^{commit})" = "$PREREG_COMMIT"
echo "$PREREG_HASH  $PREREG_FILE" | sha256sum -c -
# Input hashes were frozen in PREREGISTRATION_E04_V2.json; require exact matches.
sha256sum -c /home/junyu/dsh-scratch/e04_v2_prereg/remote_inputs.sha256
cp "$BASE"/seed*_full_policy_day_blocks.npz "$OUT/arrays/"
# Hash the exact copied array set; selector reads only this bundle.
sha256sum "$OUT"/arrays/*.npz > "$OUT/arrays.sha256"
sha256sum -c "$OUT/arrays.sha256"
source /home/junyu/miniconda3/bin/activate grokking
python /home/junyu/dsh-scratch/e04_v2_prereg/select_e04_v2.py --root "$OUT/arrays" --out "$OUT/selector/e04_v2_selection.json"
python - <<'PY'
import hashlib,json,pathlib,subprocess,sys
out=pathlib.Path('/home/junyu/dsh-scratch/e04_v2_run')
pre=pathlib.Path('/home/junyu/dsh-scratch/e04_v2_prereg/PREREGISTRATION_E04_V2.json')
commit='64478031c8ba630edff8f57851e90de4f2bdc6cb'
files=sorted([p for p in out.rglob('*') if p.is_file() and p.name not in {'output_manifest.json','execution_receipt.json'}])
def sh(p): return hashlib.sha256(p.read_bytes()).hexdigest()
manifest={'files':[{'path':p.relative_to(out).as_posix(),'bytes':p.stat().st_size,'sha256':sh(p)} for p in files]}
(out/'output_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
receipt={'status':'EXECUTED','exit_code':0,'git_prereg_commit':commit,'prereg_json_sha256':sh(pre),'command':'select_e04_v2.py --root arrays --out selector/e04_v2_selection.json','output_manifest_sha256':sh(out/'output_manifest.json'),'inputs_sha256':{'preregistration':sh(pre),'arrays_manifest':sh(out/'arrays.sha256')},'outputs':manifest['files']}
(out/'execution_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
PY
