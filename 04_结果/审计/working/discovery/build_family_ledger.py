"""Declare audited families and their evidence status; no experiment mutation."""
from pathlib import Path
import csv

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
rows=[]
def add(fid,family,status,path,n,result,limit):
    rows.append(dict(family_id=fid,experiment_family=family,status=status,
        artifact_path=str(ROOT/path),content_rows_reviewed=n,result_summary=result,
        interpretation_limit=limit,reviewer='C',epistemic_status='VERIFIED_FILE_CONTENT'))

add('F01','Legacy dense/MoE ablation','HISTORICAL_DESCRIPTIVE','artifacts/strictmask_ablation_routing_controls_gate/_aggregated_suite_runs/wtb_test_aggregated_runs.csv',50,
    'Dense RMSE231.4236; routed bal_align_force236.1305; high alignment NMI does not imply lower RMSE',
    'Training/architecture histories differ; no equivalence or graph causality claim; not current common-target decision comparison')
add('F02','Legacy consequence ablation','SUPERSEDED_WITH_INVALID_H6_COSTS','artifacts/channel_consequence_ablations.csv',10,
    'C2 NMI.46124 vs full.22586; historical transition recall.62863',
    'Legacy h6 residual-index error and direct fixed-cost comparator; recall denominator invalid; use corrected branch for bounded numbers')
add('F03','Corrected consequence ablation','EXECUTED_RECEIPT_BOUND_BOUNDED','artifacts/raw_replay_20261015_v2/channels/summary.csv',10,
    'C2 NMI.461250 ARI.646926 transition recall.769703; C9 NMI.462723; full NMI.225834',
    'Exact output hash/size matches record; does not close model-generation or causal necessity; do not reinstate old62.9% interpretation')
add('F04','Legacy Phase scan','SUPERSEDED_NONCOMMON_TARGET','artifacts/boundary_phase_scan/phase_scan_results_by_seed.csv',150,
    'Many apparent representations/recalibration advantages depend on target/population/channel condition',
    'Do not use dense/MoE or cross-delay cost differences as common-target evidence; historical within-condition comparisons only')
add('F05','Corrected Phase fixed-target scan','EXECUTED_BOUNDED_REANALYSIS','artifacts/raw_replay_20261015_v2/downstream_recovery_v1_attempt1/phase_aggregate/phase_scan_results_by_seed.csv',150,
    'h6/all/lag6 shortage21.344206 ->22.409736; h1/all/lag6 22.387709 ->21.408892',
    'No universal recalibration gain; boundary diagnostic population remains limited; old66.5% is not this common-target result')
add('F06','E01 old external pitchmasked-v4','INVALID_WRONG_PHYSICAL_WINDOW','artifacts/exp01_pitchmasked_v4/exp01_pitchmasked_v3_seed_results.csv',20,
    'Old Penmanshiel h6 -315399.62 and Kelmarsh +352433.95 are reproducible arithmetic records',
    'Forecast/target physical-window mismatch invalidates both positive and negative decision interpretation')
add('F07','E01 deterministic bounded transfer','CANONICAL_LIMITED','artifacts/metis_external_deterministic_20261015_attempt1/audit_report.json',20,
    'h6 Kelmarsh +6322.6976; Penmanshiel +356014.3979; no established cost gain',
    'Existing weights/local forecasts/calibration/current windows; not universal transfer or full EXP01 certification')
add('F08','E02 old zero privileged','SUPERSEDED_PHYSICAL_SCALER_AND_VERDICT_DEFECT','artifacts/exp02-zero-privileged-supervision/v1/zero_privileged_supervision_benchmark.csv',60,
    'eps50 h1 stored delta -365903.99; h6 +3435465.40; old report used inverted p-field',
    'Cannot use as current protocol-deficit theorem; old pval is directional probability; no averaging CI endpoints')
add('F09','E02 corrected zero privileged','EXECUTED_RECEIPT_BOUND_NOT_STABLE_ADVANTAGE','artifacts/raw_replay_20261015_v2/exp02/results.csv',60,
    'eps50 raw paired mean h1 -394230.7969; h6 -113225.6573; h6 violation8.7957% vs10.3589%',
    'Main eps50; eps20/100 sensitivity. h1/h6 registered endpoints; no reconstructed joint CI; numerical sign change does not prove stable superiority')
add('F10','E03 old async','WITHDRAWN_CAUSAL_INGRESS_AND_TRACE_DEFECT','artifacts/exp03_async/psrei_vs_delay.csv',70,
    'Old70 rows retained',
    'Initial unarrived value/full packet trace defects; field delay prevalence UNKNOWN')
add('F11','E03 corrected async','EXECUTED_RECEIPT_BOUND_SUMMARY_ONLY','artifacts/raw_replay_20261015_v2/exp03/psrei_vs_delay.csv',70,
    '7 delays x5 seeds x2 horizons CSV exists and hash/size bound to exit0 receipt',
    'This review did not audit all packet records or reconstruct joint crossover; no new async superiority claim')
add('F12','Old strong baseline closure','SUPERSEDED','artifacts/strong_baseline_joint_v2/strong_baseline_closure_summary.csv',15,
    'Old Full posterior penalty+523044; old interaction interval noncrossing',
    'Cannot use as newest effect or current significance')
add('F13','Current strong baseline closure','CANONICAL_CANDIDATE_PENDING_DEEP_AUDIT','artifacts/raw_replay_20261015_v2/strong_baseline_retry_import_v1/strong_baseline_closure_summary.csv',15,
    'Full+445639; transition+71204; steady+374436; joint interaction CI crosses0',
    'No plant-wide posterior PSREI superiority; lower transition violation at higher reserve/cost is trade-off')
add('F14','E04 formal selector','NO_FEASIBLE_POLICY','experiments/E04/results/e04_v2/e04_v2_selection.json','4 policies',
    'B/C/D/D10 riskUCB .1141939/.1173145/.1141829/.1138942 all>.10',
    'No certification is not proof all true policies unsafe or a complex model necessary')
add('F15','E05 selector frequency','CONDITIONAL_DIAGNOSTIC','experiments/E05/results/selector_stability.json','10000 archived draws summary',
    '6464/10000 no feasible frequency .6464',
    'Not future failure probability or nested UCB selector pass probability; no new resampling in this audit')
add('F16','E06 receipt-bound final bundle','BOUND_IDENTITY_NOT_SCIENTIFIC_CERTIFICATION','experiments/E06/remote_e06_final/e06_final_bundle/e04_selection.json','selection inspected',
    'Later receipt-bound E04/E06 branch kept distinct from legacy provenance gap',
    'Reviewer C did not rerun remote or all receipt chains; full certification not upgraded')
add('F17','E04 complete risk slices','DESCRIPTIVE_POSTHOC','analyses/e04_complete_policy_comparison_20261018/v2/risk_matrix.csv','selected rows',
    'Boundary B/C7.6517%/6.4533%; future down>150kW39.1393%/42.9878%',
    'Ex-post ramp not online policy; repeated five-seed populations not independent rows; no causal mechanism claim')
add('F18','E07 historical-only recalibration','INACTIVE_NOT_EXECUTED','experiments/E07_history_only_recalibration/protocol.json','protocol',
    'DRAFT_NOT_EXECUTED_PENDING_ACTIVATION_MANIFESTS; WTBday246-280 source unavailable in bound scope',
    'A data qualification gap is not a performance failure; no substitute farm activation')
add('F19','20261018 decision information','COMPLETED_DEVELOPMENT','analyses/decision_information_execution_20261018/evidence/results/aggregate/all_metrics.csv',480,
    'B-A -7.6888%; pitchscoreC-B -.2071%; calibrated B/C risk11.5666%/11.4220%',
    'New commitment target, viewed WTB; cannot overwrite old target; score gains not robust against simple/shuffled controls')
add('F20','20261018 risk frontier historical recipe','COMPLETED_DEVELOPMENT_PRIMARY_FAILURE','analyses/risk_cost_frontier_execution_20261018/evidence/results/aggregate/frontier_results.json','registered spans/cases',
    'No pitch_withheld/fresh candidate at epsilon<=5%',
    'Cannot replace failed historical recipe with test-known fullq capability')
add('F21','20261018 risk frontier all35 policies','RESULT_INFORMED_SECONDARY','analyses/risk_cost_frontier_execution_20261018/secondary_evidence/results/model_class_results.json','registered spans/cases',
    'B family in2% sensitivities; delay60 B@.95 at5%',
    'Explicitly post-result secondary capability; not independent confirmation or all-channel necessity')
add('F22','20261019 information lattice development','COMPLETED_420_SHARED_CASES','analyses/claim_revision_recovery_20261019/derived/all_decision_cases.csv',420,
    '367 no certified sufficient;53 minimum unresolved;0 finite-family minima; primary28/28 no2% sufficient',
    '420 are overlapping decisions, not replications; no inference all true policies infeasible')
add('F23','20261019 nested sample curves','DEVELOPMENT_DESCRIPTIVE','analyses/claim_revision_recovery_20261019/derived/withheld_selected_curves.csv',176,
    'PQ1/HGB at10k/40k/120k/360k cost32.7465/32.6479/32.6380/32.6701',
    'Nonmonotonic selected-q curves; training compute also changes; not Bayes sufficiency/sample-complexity theorem')
add('F24','Independent-year fixed-reference confirmation','PRIMARY_CONFIRMED_NONINFERIOR_COSTLIER','analyses/independent_confirmation_execution_20261019/recovered/results/aggregate/primary.json','550 bundles block sums; 550 policy point means/2750 risks',
    'P1/HGB/q.95 cost67.020403 vs WPQ36/HGB/q.95 66.644430; +.564147% CI[.357468%,.770827%]',
    'RiskUCB6.2025%/6.2004%; fixed-reference2% passes; no cost superiority or primary minimum claim')
add('F25','Independent-year allq minimality','PREDECLARED_SECONDARY_RETROSPECTIVE','analyses/independent_confirmation_execution_20261019/recovered/results/aggregate/secondary_span3.json','all6 groups; 90 CSV cases across3 spans',
    'pitch_withheld P1/HGB/q.925 cost65.739232 UCB9.7699%;15/15 smaller excluded; total46 identified26 unresolved18 no sufficient',
    'Differentq from primary. Finite recipe/resource order only; common forecast already contains W/P; not sensor/parameter/FLOPs minimum')
add('F26','Independent-year historical selection failure','PRESERVED_SECONDARY_FAILURE','analyses/independent_confirmation_execution_20261019/derived/secondary_cases.csv',90,
    '63 confirmed24 no historical selection3 not confirmed(delay3,.5%,all3spans)',
    'Shared data; failure cannot be erased by fullq success')
add('F27','Imported unrelated optimizer assets','EXCLUDED_TOPIC_CONTAMINATION','experiments/E06/remote_j02/e01_output/matched_state_results.csv','header and selected rows',
    'AdamW/Split-Muon/weight_norm optimizer experiment content',
    'Not wind E01 evidence despite directory name; no inference of malicious origin')
add('F28','PROJECT old mediation checklist','CONTRADICTS_CURRENT_CONTRACT','PROJECT.md','line53',
    'SectionV still calls48.4% transition excess saving VERIFIED',
    'Current interaction CI crosses0 and current posterior costs more; this checklist is not scientific evidence')
with (OUT/'family_ledger.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
print(f'{len(rows)} family branches documented')
