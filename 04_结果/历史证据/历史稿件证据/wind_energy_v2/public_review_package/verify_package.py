"""Audit archived numbers with the Python standard library; never fit or resample.

This checks stored envelopes and deterministic decisions, not nominal coverage.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
STATUSES = ("NO_CERTIFIED_SUFFICIENT_POLICY", "MINIMUM_UNRESOLVED", "FINITE_FAMILY_MINIMUM_IDENTIFIED")


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def load(root, relative):
    return json.loads((root / relative).read_text(encoding="utf-8"))


def rows(root, relative):
    with (root / relative).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def close(left, right):
    return math.isclose(float(left), float(right), rel_tol=1e-11, abs_tol=1e-12)


def verify_manifest(root):
    manifest = load(root, "MANIFEST.json")
    checked = 0
    for relative, expected in manifest["files"].items():
        path = (root / relative).resolve()
        require(path.is_relative_to(root.resolve()), "Manifest path escapes package")
        require(path.is_file(), f"Missing file: {relative}")
        require(path.stat().st_size == expected["bytes"], f"Size mismatch: {relative}")
        require(sha(path) == expected["sha256"], f"SHA256 mismatch: {relative}")
        checked += 1
    return checked


def near_optimal(group, indices, historical, epsilon, cap=.10):
    """Reapply only the stored-bound inequalities; no uncertainty is generated."""
    lo, hi, upper = group["risk_lower"], group["risk_upper"], group["relative_ratio_upper"]
    possible = [i for i, j in enumerate(indices) if all(row[j] <= cap for row in lo)]
    qualified = [i for i, j in enumerate(indices) if historical[i] and all(row[j] <= cap for row in hi)]
    required = [max((upper[j][indices[k]] for k in possible), default=math.inf) for j in indices]
    eligible = [i for i in qualified if required[i] <= epsilon]
    resource = [tuple(group["resources"][j]) for j in indices]
    minimum = min((resource[i] for i in eligible), default=None)
    chosen = [i for i in eligible if resource[i] == minimum]
    return possible, qualified, required, eligible, chosen


def minimum_audit(group, indices, chosen, epsilon, cap=.10):
    if not chosen:
        return dict(status=STATUSES[0], chosen=[], smaller=[], excluded=[], unresolved=[])
    lo, hi, lower = group["risk_lower"], group["risk_upper"], group["relative_ratio_lower"]
    resource = [tuple(group["resources"][j]) for j in indices]
    smaller = [i for i, item in enumerate(resource) if item < resource[chosen[0]]]
    feasible = [i for i, j in enumerate(indices) if all(row[j] <= cap for row in hi)]
    excluded, unresolved = [], []
    for i in smaller:
        j = indices[i]
        seeds = [s for s, row in enumerate(lo) if row[j] > cap]
        if seeds:
            excluded.append(dict(index=i, reason="RISK_LOWER_ABOVE_CAP", witness_seed_indices=seeds))
            continue
        witnesses = [k for k in feasible if lower[j][indices[k]] > epsilon]
        if witnesses:
            k = max(witnesses, key=lambda k: lower[j][indices[k]])
            excluded.append(dict(index=i, reason="COST_LOWER_EXCEEDS_MARGIN_VS_FEASIBLE", witness_policy=k,
                                 ratio_lower=lower[j][indices[k]]))
        else:
            unresolved.append(i)
    return dict(status=STATUSES[1] if unresolved else STATUSES[2], chosen=chosen,
                smaller=smaller, excluded=excluded, unresolved=unresolved)


def verify_primary(root):
    primary = load(root, "data/confirmation/primary.json")
    p = primary["bounds"]["groups"][0]
    require(primary["labels"] == ["P1/HGB/q0.95", "WPQ36/HGB/q0.95"], "Primary labels changed")
    require(not primary["uses_test_selection"], "Primary claims test selection")
    require(primary["bounds"]["coordinate_family_size"] == 14, "Primary family changed")
    require(primary["verdict"]["epsilon"] == .02, "Primary margin changed")
    require(0 < p["relative_ratio_lower"][0][1] <= p["relative_ratio_upper"][0][1] <= .02, "Primary cost duty fails")
    require(all(max(row) <= .10 for row in p["risk_upper"]), "Primary risk duty fails")
    choices = load(root, "data/history/choices.json")
    require(primary["choices_sha256"] == sha(root / "data/history/choices.json"), "Primary historical choices hash mismatch")
    require(choices["uses_confirmation"] is False, "Historical selection claims confirmation use")
    history = choices["groups"][0]
    require(history["labels"][history["reference_index"]] == primary["labels"][1], "Frozen reference mismatch")
    require([history["labels"][i] for i in history["sets"]["0.02"]["original_indices"]] == primary["labels"][:1], "Primary historical choice mismatch")
    freeze = load(root, "protocol/freeze_public_projection.json")
    unlock = load(root, "protocol/unlock_public_projection.json")
    require(freeze["historical_only"] is True, "Freeze not historical-only")
    require(freeze["created_utc"] < unlock["event"]["utc"], "Package creation not before unlock")
    original = {r["package_path"]: r for r in load(root, "PROVENANCE.json")["sources"]}
    require(unlock["event"]["freeze_sha256"] == original["protocol/freeze_public_projection.json"]["original_sha256"], "Original freeze identity mismatch")
    require(unlock["event"]["protocol_sha256"] == original["protocol/confirmation_protocol.json"]["original_sha256"], "Original protocol identity mismatch")
    for row in rows(root, "figure_data/fig2_primary_confirmation.csv"):
        if row["panel"] == "a":
            for column, field in [("point", "relative_ratio_point"), ("lower", "relative_ratio_lower"), ("upper", "relative_ratio_upper")]:
                require(close(row[column], 100 * p[field][0][1]), "Figure 2 cost field mismatch")
        else:
            i = int(row["seed"]) - 201
            j = primary["labels"].index(row["label"])
            for column in ("point", "lower", "upper"):
                require(close(row[column], 100 * p[f"risk_{column}"][i][j]), "Figure 2 risk field mismatch")
    return dict(labels=primary["labels"], cost_premium_percent=100*p["relative_ratio_point"][0][1],
                interval_percent=[100*p["relative_ratio_lower"][0][1],100*p["relative_ratio_upper"][0][1]],
                max_instance_risk_upper_percent=100*max(r[0] for r in p["risk_upper"]),
                family_size=14, historical_choice_binding="PASS")


def verify_secondary(root):
    csv_cases = {(int(r["span"]), r["condition"], float(r["epsilon"])): r for r in rows(root, "csv/towie_all_90_cases.csv")}
    counts, historical_counts = Counter(), Counter()
    bridge = None
    for span in (1, 3, 7):
        for group in load(root, f"data/confirmation/secondary_span{span}.json")["results"]:
            indices = list(range(len(group["labels"])))
            require(group["coordinate_family_size"] == 74500, "Secondary family size changed")
            for case in group["secondary_retrospective_full_q"]:
                epsilon = case["epsilon"]
                possible, qualified, required, eligible, chosen = near_optimal(group, indices, [True]*len(indices), epsilon)
                stored = case["sufficient_set"]
                for key, actual in [("possible_feasible_indices", possible), ("risk_qualified_indices", qualified), ("eligible_indices", eligible), ("minimum_resource_indices", chosen)]:
                    require(stored[key] == actual, f"Secondary stored-bound decision mismatch: {key}")
                require(all(close(a,b) for a,b in zip(stored["required_relative_tolerance"], required)), "Secondary required-cost bridge mismatch")
                audit = minimum_audit(group, indices, chosen, epsilon)
                require(audit == case["minimum_audit"], "Secondary exclusion audit mismatch")
                row = csv_cases[(span, group["condition"],epsilon)]
                require(row["minimum_status"] == audit["status"], "Secondary CSV classification mismatch")
                counts[audit["status"]] += 1
                fixed = group["historical_frozen_assessment"][str(epsilon)]
                require(row["historical_fixed_status"] == fixed["status"], "Historical fixed CSV mismatch")
                historical_counts[fixed["status"]] += 1
                if span == 3 and group["condition"] == "pitch_withheld" and epsilon == .02:
                    require(chosen == [41] and group["labels"][41] == "P1/HGB/q0.925", "Secondary q identity mismatch")
                    require(42 not in eligible and group["labels"][42] == "P1/HGB/q0.95", "Primary must not enter full-q sufficient set")
                    require(len(audit["smaller"]) == len(audit["excluded"]) == 15, "15 smaller exclusions not closed")
                    reasons = Counter(r["reason"] for r in audit["excluded"])
                    require(reasons == {"RISK_LOWER_ABOVE_CAP":2,"COST_LOWER_EXCEEDS_MARGIN_VS_FEASIBLE":13}, "Exclusion reasons changed")
                    bridge = dict(q925_required_upper_percent=100*required[41], q950_required_upper_percent=100*required[42],
                                  q925_resource=group["resources"][41], smaller=15, exclusion_reasons=dict(reasons),
                                  meaning="q0.95 is not certified against the full family; this is not a proof that its true regret exceeds 2%.")
    require(len(csv_cases) == 90 and counts == dict(zip(STATUSES, [18,26,46])), "90-case counts mismatch")
    require(historical_counts == {"ALL_FROZEN_CANDIDATES_CONFIRMED":63,"NO_HISTORICAL_SELECTION":24,"CONFIRMATION_NOT_ESTABLISHED":3}, "Historical fixed classifications mismatch")
    return dict(counts=dict(counts), historical_fixed=dict(historical_counts), cost_bridge=bridge,
                scope="90 dependent assessments; spans are separate envelopes, not independent confirmations.")


def verify_wtb(root):
    classifications = {(r["condition"],int(r["budget"]),int(r["span"]),r["analysis"],float(r["epsilon"])):r for r in rows(root,"csv/wtb_all_420_minimum_cases.csv")}
    necessity = load(root,"data/wtb/necessity.json")["results"]
    stored_audits = {(r["condition"],r["budget"],r["span"],r["analysis"],r["epsilon"]):r for r in necessity}
    counts = Counter()
    for group in load(root,"data/wtb/aggregate.json")["results"]:
        for analysis in ("primary_historical_recipe","secondary_retrospective_grid"):
            if analysis.startswith("primary"):
                indices=[r["index"] for r in group["historical_choices"]]
                historical=[r["qualified"] for r in group["historical_choices"]]
            else:
                indices=list(range(len(group["labels"])));historical=[True]*len(indices)
            for case in group[analysis]:
                key=(group["condition"],group["budget"],group["span"],analysis,case["epsilon"])
                possible,qualified,required,eligible,chosen=near_optimal(group,indices,historical,case["epsilon"])
                require(case["eligible_indices"]==eligible and case["minimum_resource_indices"]==chosen,"WTB sufficiency mismatch")
                require(case["possible_feasible_indices"]==possible and case["risk_qualified_indices"]==qualified,"WTB risk-set mismatch")
                audit=minimum_audit(group,indices,chosen,case["epsilon"])
                saved=stored_audits[key]
                require(all(audit[k]==saved[k] for k in audit),"WTB necessity audit mismatch")
                row=classifications[key]
                require(row["status"]==audit["status"] and int(row["smaller_count"])==len(audit["smaller"]),"WTB CSV mismatch")
                counts[audit["status"]]+=1
    require(len(classifications)==420 and counts=={STATUSES[0]:367,STATUSES[1]:53},"420-case counts mismatch")
    sufficient=rows(root,"csv/wtb_all_420_sufficiency_cases.csv")
    main=[r for r in sufficient if int(r["span"])==3 and float(r["epsilon"])==.02]
    require(len(main)==28 and all(r["status"]=="NO_IDENTIFIED_POLICY" and int(r["risk_qualified_count"])>0 for r in main),"WTB primary 28-case boundary mismatch")
    return dict(counts=dict(counts), primary_28_no_sufficient=28,
                scope="Classification from stored bounds; no new fit, prediction, bootstrap, or coverage certification.")


def verify_ledger(root):
    d=load(root,"data/ledger/derived.json");p=d["policies"];seed=rows(root,"data/ledger/policy_seed_ledger.csv")
    require(len(seed)==10 and "host" not in seed[0],"Seed ledger projection invalid")
    for policy in ("P1","WPQ36"):
        selected=[r for r in seed if r["policy"]==policy]
        require(len(selected)==5 and {int(r["seed"]) for r in selected}==set(range(201,206)),"Fixed instances mismatch")
        for metric in ("cost_mean","reserve_mean","shortage_mean","violation_rate"):
            require(close(sum(float(r[metric]) for r in selected)/5,p[policy][metric]),f"Seed mean differs: {metric}")
        require(all(int(float(r["count"]))==1059248 for r in selected),"Shared scoring count mismatch")
    u=100*(p["P1"]["shortage_mean"]/p["WPQ36"]["shortage_mean"]-1)
    require(close(u,2.1843491567971496),"Shortage severity point change mismatch")
    return dict(shortage_increase_percent=u,measurement="Archived point accounting, no new U interval or significance test.")


def verify_fig3_v2(root):
    """Check every V2 plotted row against the archived group, not only hashes."""
    source = "data/confirmation/secondary_span3.json"
    group = next(g for g in load(root, source)["results"] if g["condition"] == "pitch_withheld")
    case = next(c for c in group["secondary_retrospective_full_q"] if c["epsilon"] == .02)
    sufficient, audit = case["sufficient_set"], case["minimum_audit"]
    data = rows(root,"figure_data/v2/fig3_secondary_minimality.csv")
    metadata = load(root,"figure_data/v2/fig3_field_manifest.json")
    cap = load(root,"protocol/confirmation_protocol.json")["v_max"]
    require(len(data)==17 and [int(r["index"]) for r in data[:2]]==[41,42],"V2 Figure 3 must contain two bounds plus fifteen exclusions")
    require(metadata["source_sha256"]==sha(root/source),"V2 Figure 3 metadata binds different aggregate")
    require(metadata["epsilon_unchanged"]==case["epsilon"] and metadata["event_rate_cap_unchanged"]==cap,"V2 Figure 3 threshold metadata mismatch")
    require(metadata["span_days"]==3 and metadata["coordinate_family"]==group["coordinate_family_size"],"V2 Figure 3 family metadata mismatch")
    require(metadata["exclusion_witness_indices"]==[171,181],"V2 Figure 3 witness metadata mismatch")
    for row, record in zip(data[:2],metadata["sufficiency_rows"]):
        i=int(row["index"])
        possible=sufficient["possible_feasible_indices"]
        k=max(possible,key=lambda j:group["relative_ratio_upper"][i][j])
        expected={
            "worst_paired_cost_upper_percent":100*group["relative_ratio_upper"][i][k],
            "max_instance_risk_upper_percent":100*max(r[i] for r in group["risk_upper"]),
            "cost_tolerance_percent":100*case["epsilon"],"risk_cap_percent":100*cap,
            "controlling_competitor_index":k,
            "competitor_max_risk_upper_percent":100*max(r[k] for r in group["risk_upper"]),
        }
        for field,value in expected.items():
            require(float(row[field])==value,f"V2 Figure 3 numeric field differs from archived JSON: {field}")
            require(record[field]==value,f"V2 Figure 3 field manifest differs: {field}")
        for field,value in {
            "cost_upper_certified":sufficient["required_relative_tolerance"][i]<=case["epsilon"],
            "sufficient":i in sufficient["eligible_indices"],
            "competitor_possibly_feasible":k in possible,
            "competitor_risk_qualified":k in sufficient["risk_qualified_indices"],
        }.items():
            require(row[field]==str(value) and record[field]==value,f"V2 Figure 3 qualification mismatch: {field}")
        require(row["label"]==record["label"]==group["labels"][i],"V2 Figure 3 candidate label mismatch")
        require(row["controlling_competitor"]==record["controlling_competitor"]==group["labels"][k],"V2 Figure 3 competitor mismatch")
        for field in ("cost_source_field","risk_source_field","cap_source","competitor_source_field","source","interpretation"):
            require(row[field]==record[field],f"V2 Figure 3 field pointer mismatch: {field}")
        require(float(row["worst_paired_cost_upper_percent"])==100*sufficient["required_relative_tolerance"][i],"V2 Figure 3 stored required tolerance mismatch")
    exclusions=data[2:]
    require([int(r["index"])for r in exclusions]==audit["smaller"],"V2 Figure 3 omitted or reordered smaller candidate")
    for row,witness in zip(exclusions,audit["excluded"]):
        i=witness["index"]
        require(row["panel"]=="c" and row["label"]==group["labels"][i] and row["reason"]==witness["reason"],"V2 Figure 3 exclusion identity mismatch")
        if witness["reason"]=="RISK_LOWER_ABOVE_CAP":
            seeds=witness["witness_seed_indices"]
            require(row["witness_seed_indices"]==";".join(map(str,seeds)),"V2 Figure 3 risk witness instances mismatch")
            actual=[float(v) for v in row["witness_risk_lower_percent"].split(";")]
            expected=[100*group["risk_lower"][s][i]for s in seeds]
            require(actual==expected and all(v>100*cap for v in actual),"V2 Figure 3 risk exclusion values mismatch")
            require(row["witness_policy"]==row["witness_index"]==row["ratio_lower"]=="","Risk witness cannot be relabelled cost witness")
        else:
            k=witness["witness_policy"]
            require(int(row["witness_index"])==k and row["witness_policy"]==group["labels"][k],"V2 Figure 3 cost witness identity mismatch")
            require(float(row["ratio_lower"])==witness["ratio_lower"]==group["relative_ratio_lower"][i][k]>case["epsilon"],"V2 Figure 3 cost exclusion value mismatch")
            maximum=max(r[k]for r in group["risk_upper"])
            require(maximum<=cap and row["witness_risk_qualified"]=="True" and float(row["witness_max_risk_upper_percent"])==100*maximum,"V2 Figure 3 cost witness not risk qualified")
    require(Counter(r["reason"]for r in exclusions)=={"RISK_LOWER_ABOVE_CAP":2,"COST_LOWER_EXCEEDS_MARGIN_VS_FEASIBLE":13},"V2 Figure 3 exclusion counts changed")
    return dict(status="PASS_FIELD_BY_FIELD",rows=17,sufficiency_rows=2,excluded_smaller_candidates=15,
                cost_witnesses_risk_qualified=True,controlling_upper_competitor="PQ36/HGB/q0.9",
                controlling_competitor_is_only_possibly_feasible=True,
                scope="Fields and witness duties match archived JSON. Pixel identity or full figure reconstruction is not certified.")


def audit(root):
    count=verify_manifest(root)
    provenance=load(root,"PROVENANCE.json")
    for item in provenance["sources"]:
        require(sha(root/item["package_path"])==item["package_sha256"],"Provenance package hash mismatch")
        if item["transformation"]=="BYTE_IDENTICAL":
            require(item["original_sha256"]==item["package_sha256"],"Claimed byte-identical source differs")
    return dict(status="PASS_ARCHIVED_RECORD_AUDIT",files_sha256_checked=count,
                primary=verify_primary(root),secondary=verify_secondary(root),wtb=verify_wtb(root),ledger=verify_ledger(root),
                fig3_v2=verify_fig3_v2(root),
                not_certified=["Training or inference reproduction","Resampling reproduction or nominal interval coverage","A real operational interface or deployment benefit","Public hosting, licences, or author approvals"],
                new_training=False,new_inference=False,new_calibration=False,new_resampling=False,new_measurement_download=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,help="Optional report file; stdout is the default")
    args=parser.parse_args()
    try:
        report=audit(HERE)
    except (ValueError,KeyError,OSError) as error:
        print(json.dumps(dict(status="FAIL",error=str(error)),indent=2));return 1
    result=json.dumps(report,indent=2)+"\n"
    if args.output:args.output.write_text(result,encoding="utf-8")
    print(result,end="");return 0


if __name__=="__main__":
    sys.exit(main())
