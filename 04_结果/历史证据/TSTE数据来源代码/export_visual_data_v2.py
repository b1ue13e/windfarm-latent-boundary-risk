"""Extract descriptive figure data from preserved daily accounts; no model or bootstrap."""
from pathlib import Path as NativePath
import sys
_PROJECT_ROOT = next(p for p in NativePath(__file__).resolve().parents if (p / "AGENTS.md").is_file())
sys.path.insert(0, str(_PROJECT_ROOT / "02_公共资源/工程"))
from repo_paths import Path, repository_root
import csv
import hashlib
import json
import numpy as np

BASE = Path(__file__).resolve().parents[1]
ROOT = Path(repository_root())
OUT = BASE / "source_data/v2"
QA = BASE / "qa/visual_redesign_20261027"
OUT.mkdir(parents=True, exist_ok=True)
QA.mkdir(parents=True, exist_ok=True)
source_hashes = {}

def source(rel):
    p=ROOT/rel
    source_hashes[rel]=hashlib.sha256(p.read_bytes()).hexdigest()
    return p

def write(name,rows):
    with (OUT/name).open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

wtb_daily=[];wtb_fit=[]
origin="analyses/praw_supplement_v3_execution_20261021"
means=list(csv.DictReader(source(origin+"/mean_metrics.csv").open(encoding="utf-8-sig")))
for est,start in [("HGB",0),("MLP",5)]:
    for arm in ("O6","OZ6","Praw","OP6"):
        records=[]
        for i in range(start,start+5):
            if arm=="Praw":
                z=np.load(source(origin+f"/metis_results/results/fits/{i}/evaluation_blocks.npz"))
                d={k:z[k] for k in ["C","R","U","V","N","days"]}
            else:
                z=np.load(source(origin+f"/metis_results/results/accounting/{i}/daily_totals.npz"))
                d={k:z[f"E_P|{arm}|{k}"] for k in ["C","R","U","V","N","days"]}
            assert len(d["days"])==35 and int(d["N"].sum())==671538
            assert np.allclose(d["C"],d["R"]+10*d["U"],rtol=0,atol=1e-6)
            records.append(d)
            wtb_fit.append(dict(estimator=est,arm=arm,seed=201+i-start,
                                **{k:float(d[k].sum()/d["N"].sum()) for k in ["C","R","U","V"]}))
        assert all(np.array_equal(x["days"],records[0]["days"]) and np.array_equal(x["N"],records[0]["N"]) for x in records)
        row=next(x for x in means if x["estimator"]==est and x["arm"]==arm)
        for k in ["C","R","U","V"]:
            derived=np.mean([d[k].sum()/d["N"].sum() for d in records])
            assert abs(derived-float(row[k]))<1e-9,(est,arm,k,derived,row[k])
        for j,day in enumerate(records[0]["days"]):
            n=records[0]["N"][j]
            wtb_daily.append(dict(estimator=est,arm=arm,day=int(day)+1,N=int(n),
                **{k:float(np.mean([d[k][j]/n for d in records])) for k in ["C","R","U","V"]}))
write("measurement_fit.csv",wtb_fit);write("measurement_daily.csv",wtb_daily)
contrasts=[r for r in csv.DictReader(source(origin+"/primary_comparisons.csv").open(encoding="utf-8-sig"))
           if r["span"]=="3" and r["metric"]=="D_C" and r["comparison"] in ["Praw-minus-O6","Praw-minus-OZ6","Praw-minus-OP6"]]
assert len(contrasts)==6
write("measurement_contrasts.csv",contrasts)

protocol=json.loads(source("experiments/mainline_supplement_20261026/p1/protocol.json").read_text(encoding="utf-8"))
primary25=json.loads(source("analyses/independent_confirmation_execution_20261019/recovered/results/aggregate/primary.json").read_text(encoding="utf-8"))
primary26=json.loads(source("experiments/mainline_supplement_20261026/p1/recovered/results/aggregate/primary.json").read_text(encoding="utf-8"))
cross=[];fit_rows=[];day_rows=[]
for year,folder,primary in [(2025,"analyses/independent_confirmation_execution_20261019/recovered/results/evaluate",primary25),
                           (2026,"experiments/mainline_supplement_20261026/p1/recovered/results/evaluate",primary26)]:
    store={"P1":[],"WPQ36":[]}
    for item in protocol["selected_tasks"]:
        i=item["task_index"];task=item["task"]
        z=np.load(source(folder+f"/{i}/blocks.npz"));q=2
        d={k:z[f"{q}__{name}"] for k,name in [("days","block_ids"),("N","count"),("C","loss_sum"),("R","reserve_sum"),("U","shortage_sum"),("V","violation_sum")]}
        assert len(d["days"])==(365 if year==2025 else 120)
        assert int(d["N"].sum())==(1059248 if year==2025 else 361326)
        assert np.allclose(d["C"],d["R"]+10*d["U"],rtol=0,atol=1e-6)
        store[task["subset"]].append(d)
        fit_rows.append(dict(year=year,arm=task["subset"],seed=task["seed"],
            **{k:float(d[k].sum()/d["N"].sum()) for k in ["C","R","U","V"]}))
    for arm,records in store.items():
        assert len(records)==5
        totals={k:float(np.mean([d[k].sum()/d["N"].sum() for d in records])) for k in ["C","R","U","V"]}
        index=0 if arm=="P1" else 1
        assert abs(totals["C"]-primary["bounds"]["groups"][0]["mean_cost"][index])<1e-9
        cross.append(dict(year=year,arm=arm,raw_columns=5 if arm=="P1" else 112,**totals))
        for j,day in enumerate(records[0]["days"]):
            date=str(np.datetime64("2023-01-01")+np.timedelta64(int(day),"D"))
            for s,d in enumerate(records):
                assert np.array_equal(d["N"],store["P1"][s]["N"]) and np.array_equal(d["days"],store["P1"][s]["days"])
                day_rows.append(dict(year=year,arm=arm,seed=201+s,date=date,day=int(day),N=int(d["N"][j]),
                    **{k:float(d[k][j]/d["N"][j]) if d["N"][j]>0 else float("nan") for k in ["C","R","U","V"]}))
    p=primary["bounds"]["groups"][0]
    cross[-2].update(cost_delta=float(p["relative_ratio_point"][0][1]),
        cost_low=float(p["relative_ratio_lower"][0][1]),cost_high=float(p["relative_ratio_upper"][0][1]),
        risk_upper=float(max(v[0] for v in p["risk_upper"])))
    cross[-1].update(cost_delta=0.0,cost_low=0.0,cost_high=0.0,
        risk_upper=float(max(v[1] for v in p["risk_upper"])))
write("cross_year_summary.csv",cross);write("cross_year_fits.csv",fit_rows);write("cross_year_daily.csv",day_rows)
receipt=dict(source_hashes=source_hashes,new_fits=0,new_calibrations=0,new_bootstrap=0,
    extraction="All prespecified days and five fixed fits. Daily quantities are means over valid turbine intervals; then five-fit means for plotting. No days omitted.",
    original_uncertainty="Original paired simultaneous intervals are copied verbatim; displayed fit ranges are descriptive, not confidence intervals.",
    output_rows={"measurement_fit":len(wtb_fit),"measurement_daily":len(wtb_daily),"cross_year_daily":len(day_rows)})
(QA/"DATA_RECEIPT.json").write_text(json.dumps(receipt,indent=2),encoding="utf-8")
print("Verified and exported",receipt["output_rows"])
