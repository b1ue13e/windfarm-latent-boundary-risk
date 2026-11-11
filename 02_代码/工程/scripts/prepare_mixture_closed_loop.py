"""Freeze this bounded campaign from existing metadata, before new execution."""
import json,hashlib
from repo_paths import Path, repository_root
import sys
ROOT=Path(repository_root());sys.path.insert(0,str(ROOT))
from windfarm_moe.mixture_campaign_design import recipes_for_loop,comparison_family


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    old=ROOT/'research_audit/autonomous_optimization_20261022/results'
    review=ROOT/'research_audit/autonomous_optimization_review_20261024'
    target=ROOT/'experiments/mixture_closed_loop_20261024';target.mkdir(exist_ok=True)
    planned=json.loads((old/'online_candidates.json').read_text())
    completed=[json.loads(p.read_text()) for p in (old/'inner_results').glob('*.json')]
    outer={row['recipe']['recipe_id'] for row in json.loads((old/'outer_results.json').read_text())}
    recipes=recipes_for_loop(planned,completed,outer)
    parent_path=review/'bridge_intervals/intervals_span3.json'
    info=json.loads(parent_path.read_text());names=info['policy_names'];fd=info['family_definition']
    parent=dict(policy_names=names,available=info['available'],
        comparisons=[(names[l],names[r]) for l,r in fd['comparisons']],
        aliases=[(names[l],names[r]) for l,r in fd['frozen_aliases']])
    family=comparison_family(recipes,parent)
    source_files=['windfarm_moe/actual_mixture_update.py','windfarm_moe/mixture_campaign_design.py',
        'windfarm_moe/static_convex_bundle.py','windfarm_moe/delayed_risk_aggregation.py',
        'windfarm_moe/delayed_risk_batch.py','windfarm_moe/delayed_calibration_baselines.py',
        'windfarm_moe/autonomous_campaign_inference.py','scripts/run_mixture_closed_loop.py']
    cfg=dict(study_id='actual_mixture_closed_loop_20261024_v1',max_candidates=200,
        planned_candidates=198,retry_candidate_reserve=2,max_cpu_seconds=14400,
        allocated_cpus=2,job_wall_seconds=6900,preflight_cpu_reserve_seconds=600,
        source_commit='PBS_CAMPAIGN_RELEASE_AND_BYTE_HASHES',seeds=[201,202,203,204,205],
        historical_cache='/lstr/sahara/minlpml/junyu/autonomous_risk_20261022_7d25a81fa/results/campaign/expert_cache/historical_extended',
        historical_manifest_sha256=planned[0]['expert_set_digest'],
        evaluation_cache='/lstr/sahara/minlpml/junyu/autonomous_risk_20261022_7d25a81fa/results/campaign/expert_cache/evaluate',
        evaluation_manifest_sha256=json.loads((review/'bridge_source_manifest.json').read_text())['sha256'],
        parent_ledger='parent_evidence/merged_daily_ledger.npz',
        parent_ledger_sha256=sha(review/'bridge_intervals/merged_daily_ledger.npz'),parent_family=parent,
        source_files=source_files,recipes=recipes,comparisons=family['comparisons'],
        nominal_family_size=family['nominal_family_size'],
        full_aliases=family['aliases'],source_metadata=dict(planned=sha(old/'online_candidates.json'),
            outer=sha(old/'outer_results.json'),parent=sha(parent_path)),
        episodes=dict(inner=dict(fit=[27648,28080],score=[28087,28937]),
            outer=dict(fit=[27648,28937],score=[28944,30233]),
            evaluate=dict(fit=[27648,30233],score=[30240,35273])),
        feedback_rule='source_anchor+7<decision_anchor',
        episode_scope='New matched methods restart after a mature prefix; no fabricated actions in purge gaps. Legacy probes retain their original history and are not causal update ablations.',
        shared_initialization=dict(smoothing=.01,canonicalization='once before both fixed and online',
            fit_goals=['COST','CAP'],cap='mean historical uncovered power of fixed REF',
            fallback='Declared reference weights on numerical initializer errors; never hide status',
            expected_convex_fits_all_episodes=60,expected_final_full_history_fits=20),
        scientific_constants=dict(rho=10,dt_hours=1/6,important_cost_gain=.01,cost_noninferiority=.01,
            signed_H_cap=.001,absolute_risk_cap=.1,alpha=.05,cstar_reporting_only=42.058880543674675),
        actual_update=dict(gradient='actual stored past mixture C/100 and signed10U/100',
            kink_subgradient=0,projection='simplex; permits reactivating zero weights',
            schedule='eta/(1+source_issue_elapsed/144)^power; same schedule for severity step',
            severity_learning_target=0,strict_V='Separate unchanged endpoint, no differentiable guarantee'),
        evaluation='All198 recipes x5 fixed fits x2 arms in each episode; no qualification filter; all failures retained',
        ranking='Historical minimumC and minimum_maxV roles per family; all recipes nevertheless evaluated',
        stopping='No performance early-stop. Stop on hard shared allocation, integrity failure, or unresolvable numeric failure; preserve incomplete states',
        inference=dict(spans=[3,1,7],n_boot=20000,seed=20261022,
            family='old346 plus all new qualification and predeclared comparison duties',
            selection_adjusted=False,independent_confirmation=False,coverage_certified=False),
        no_new_measurements=True,no_paper_edits=True,old_outputs_readonly=True)
    assert 2*cfg['job_wall_seconds']+cfg['preflight_cpu_reserve_seconds']==14400
    (target/'protocol.json').write_text(json.dumps(cfg,indent=2)+'\n')
    (target/'family.json').write_text(json.dumps(family,indent=2)+'\n')
    print('Frozen recipes',len(recipes),'policies',len(family['names']),'endpoints',family['nominal_family_size'])


if __name__=='__main__':main()
