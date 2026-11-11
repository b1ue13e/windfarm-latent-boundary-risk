"""Export a saved daily raw estimate, without model execution or calibration."""
from pathlib import Path
import hashlib
import json
import csv
import numpy as np
import pandas as pd

Q=Path(__file__).resolve().parent;B=Q.parents[1];ROOT=B.parents[1]
source=ROOT/"experiments/mainline_supplement_20261026/p1/recovered/results/evaluate/8/raw_actions.npz"
old=json.loads((B/"qa/fig1_method_v4/SOURCE_BINDING.json").read_text())
digest=hashlib.sha256(source.read_bytes()).hexdigest();assert digest==old["sha256"]
z=np.load(source);sel=(z["anchors"]>=157824)&(z["anchors"]<157968)
d=pd.read_csv(B/"source_data/v3/decision_example.csv")
assert len(d)==144 and z["mask"][sel,0].all()
raw=z["raw"][sel,0];off=float(z["offsets"][2]);request=np.maximum(raw+off,0)
assert np.allclose(d.reserve_kw,request,rtol=0,atol=1e-10)
target=B/"source_data/v10";target.mkdir(exist_ok=True)
# Preserve the exact decimal strings in the existing export; only insert the
# saved raw output. This avoids a second float-to-text round trip for old data.
with (B/"source_data/v3/decision_example.csv").open(newline="",encoding="utf-8") as f:
    reader=csv.DictReader(f);fields=list(reader.fieldnames);rows=list(reader)
fields.insert(2,"raw_kw")
with (target/"decision_construction.csv").open("w",newline="",encoding="utf-8") as f:
    writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
    for row,value in zip(rows,raw):row["raw_kw"]=repr(float(value));writer.writerow(row)
(Q/"RAW_BINDING.json").write_text(json.dumps(dict(source=str(source.relative_to(ROOT)),
    source_sha256=digest,raw_records=len(raw),first_raw=float(raw[0]),offset=off,
    new_fits=0,new_predictions=0,new_calibrations=0,new_resampling=0),indent=2),encoding="utf-8")
print("144 saved raw estimates exported; source identity and requests match.")
