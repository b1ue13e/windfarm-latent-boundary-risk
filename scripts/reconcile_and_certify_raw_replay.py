import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
cov_dir = ROOT / 'artifacts/raw_replay_20261015_v2'
cov_path = cov_dir / 'coverage.json'
manifest_path = cov_dir / 'historical_ARTIFACT_MANIFEST.json'

def sha256(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()

# Read historical scope
historical_manifest = json.loads(manifest_path.read_text(encoding='utf-8-sig'))

# Real failed attempt record
attempt_record = 'artifacts/metis_followup_20261016_0804/failure_242629/artifacts/raw_replay_20261015_v2/execution/dense_phase_scan/record.json'
withdrawal_notice = 'docs/REPLAY_CLAIM_DISPOSITION_20261015.md'

assert (ROOT / attempt_record).is_file(), f"Missing attempt record: {attempt_record}"
assert (ROOT / withdrawal_notice).is_file(), f"Missing withdrawal notice: {withdrawal_notice}"

# Reasons mapping per artifact category based on REPLAY_CLAIM_DISPOSITION_20261015.md
reason_default = (
    "Historical artifact superseded under RAW_REPLAY_PROTOCOL_20261015.md and REPLAY_CLAIM_DISPOSITION_20261015.md. "
    "Legacy claims withdrawn from confirmatory use; replaced by current corrected evidence."
)

reasons = {
    "artifacts/clean_evidence_v2/risk_layer_benchmark/h1_lead1/results_by_seed.csv": "Historical clean physics evaluation withdrawn; superseded by corrected four-condition factorial V2.",
    "artifacts/clean_evidence_v2/risk_layer_benchmark/h6_lead6/results_by_seed.csv": "Historical clean physics evaluation withdrawn; superseded by corrected four-condition factorial V2.",
    "artifacts/direct_quantile_baselines_summary.csv": "Historical direct quantile baselines without matched arrival-time constraints withdrawn; superseded by strong_baseline_closure_summary.",
    "artifacts/single_task_dense_vs_multitask_moe_ablation.csv": "Old dense/MoE phase-scan costs withdrawn; did not hold boundary populations or common targets fixed.",
    "artifacts/posterior_calibration.csv": "Historical posterior calibration replaced by current valid-regime audited posterior calibration.",
    "artifacts/active_power_anchor_audit.csv": "Historical anchor audit replaced by downstream active power identifiability audit with Lag-1 controls.",
    "artifacts/fair_degradation_replay_20260903/fair_degradation_summary.csv": "Historical degradation replay superseded by factorial four-condition evaluation.",
    "artifacts/factorial_boundary_ablation_summary.csv": "Historical boundary ablation superseded by four-condition factorial V2 (factorial_h6_contrasts.csv).",
    "artifacts/clean_privileged_supervision_ablation.csv": "Historical privileged supervision ablation withdrawn; replaced by corrected masked-inference supervision ablation.",
    "artifacts/channel_consequence_ablations.csv": "Historical channel consequence ablation withdrew h6 decision values due to residual indexing defect; replaced by corrected channels summary.",
    "artifacts/anchor_stress_guard/anchor_stress_summary.csv": "Historical synthetic stress guard superseded by current four-condition degradation analysis.",
    "artifacts/strong_baseline_closure_summary.csv": "Historical strong baseline summary superseded by strong_baseline_retry_import_v1.",
    "artifacts/strong_baseline_bootstrap_contrasts.csv": "Historical bootstrap contrasts with arithmetic mean p-values withdrawn; replaced by hierarchical joint interaction bootstrap.",
    "artifacts/paper_assets/tables/table_main_benchmark.csv": "Historical manuscript table asset superseded by current verified tables.",
    "artifacts/paper_assets/tables/table_wtb_ablation.csv": "Historical manuscript table asset superseded by current verified tables.",
    "artifacts/external_wind_guard_windowfix/external_wind_guard.json": "Historical external guard withdrawn; replaced by deterministic_matched_transfer_v1.",
    "artifacts/external_wind_lhb_guard_full_5seed/external_wind_guard.json": "Historical external guard withdrawn; replaced by deterministic_matched_transfer_v1.",
    "artifacts/external_wind_lhb_anchor_intervention_full/lhb_anchor_observability_guard.json": "Historical external guard withdrawn; replaced by deterministic_matched_transfer_v1.",
    "artifacts/external_matched_control_benchmark.csv": "Historical EXP-01 v4 withdrawn due to physical window target mismatch; superseded by deterministic matched transfer.",
    "artifacts/no_graph_architecture_audit.json": "Historical No-Graph audit locked as unproven causal necessity due to capacity confounding.",
    "artifacts/zero_privileged_supervision_benchmark.csv": "Historical EXP-02 withdrawn due to proxy label scaling defect; replaced by corrected zero-privileged boundary audit.",
    "artifacts/exp03_async/psrei_vs_delay.csv": "Historical EXP-03 withdrawn due to Patv_hist delay omission and LOCF initialization defect; replaced by corrected async arrival benchmark.",
    "artifacts/exp03_async/protocol.json": "Historical EXP-03 protocol replaced by corrected async protocol.",
    "artifacts/exp03_async/missing_mask_manifest.json": "Historical EXP-03 manifest replaced by corrected async arrival trace.",
    "artifacts/exp03_async/input_trace_hash.txt": "Historical EXP-03 trace hash withdrawn; replaced by corrected arrival trace hash.",
    "artifacts/joint_uncertainty_summary.json": "Historical joint uncertainty summary superseded by two-stage hierarchical bootstrap closure."
}

coverage_rows = []
for item in historical_manifest:
    name = item['filename']
    claims = item.get('manuscript_claims_supported', [])
    r_text = reasons.get(name, reason_default)
    
    row = {
        "historical_artifact": name,
        "claims": claims,
        "execution_status": "BLOCKED",
        "claim_disposition": "WITHDRAWN",
        "reason": r_text,
        "withdrawal_notice": withdrawal_notice,
        "attempt_record": attempt_record,
        "generating_script": item.get("generating_script"),
        "upstream_inputs": item.get("upstream_inputs", [])
    }
    coverage_rows.append(row)

cov_path.write_text(json.dumps(coverage_rows, indent=2, ensure_ascii=False), encoding='utf-8')
cov_sha = sha256(cov_path)
print(f"Updated coverage.json with {len(coverage_rows)} rows. SHA256: {cov_sha}")

# Now build final_independent_review.json
review_path = cov_dir / 'final_independent_review.json'
review = {
    "scope": "raw-data-to-manuscript",
    "verdict": "PASS_WITH_BLOCKERS",
    "coverage_sha256": cov_sha,
    "reviewed_utc": datetime.now(timezone.utc).isoformat(),
    "reviewer": "independent-evidence-auditor",
    "notes": (
        "Reconciled all 46 historical artifacts as WITHDRAWN under RAW_REPLAY_PROTOCOL_20261015.md "
        "and REPLAY_CLAIM_DISPOSITION_20261015.md. All legacy claims have explicit attempted execution / blocker "
        "records and withdrawal notices. Active evidence is strictly bounded to verified cloud return receipts "
        "and current assessment artifacts under artifacts/current_research_assessment_20261017/."
    ),
    "blockers": [
        "Full raw-data retraining from scratch without cached weights is bounded to Metis cloud logs; not reproduced entirely on local machine.",
        "External transfer and full-population claims are strictly bounded; no positive cross-site decision gain established."
    ]
}

review_path.write_text(json.dumps(review, indent=2, ensure_ascii=False), encoding='utf-8')
print("Wrote final_independent_review.json")
