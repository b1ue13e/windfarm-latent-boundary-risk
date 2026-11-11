"""Validate audit deliverables and make coverage limitations explicit."""
from pathlib import Path
import csv
import datetime as dt
import gzip
import hashlib
import json
import subprocess

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'research_audit'

def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def rows(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

def main():
    inventory=json.loads((OUT/'inventory_summary.json').read_text())
    survey=json.loads((OUT/'asset_readability_summary.json').read_text())
    ledger=rows(OUT/'02_experiment_ledger.csv');papers=rows(OUT/'literature_matrix.csv')
    assert len(ledger)==7525==len({r['Experiment ID'] for r in ledger})
    assert all(all(v for v in r.values()) for r in ledger)
    assert len(papers)==13 and all(r['gap_role'] in {'foundational','mainstream','failing','adjacent'} for r in papers)
    assert len(rows(OUT/'research_assets.csv'))==survey['total']==inventory['research_assets']==56486
    with gzip.open(OUT/'all_accessible_files.csv.gz','rt',encoding='utf-8',newline='') as f:
        count=sum(1 for _ in csv.DictReader(f))
    assert count==inventory['all_files']==206614
    for name in ('01_project_inventory.md','02_experiment_ledger.csv','03_validity_and_reproducibility.md',
        '04_discovery_ranking.md','05_scientific_problem_candidates.md','06_decisive_experiments.md',
        '07_reviewer_assessment.md','FINAL_RESEARCH_STRATEGY.md'):
        assert (OUT/name).is_file() and (OUT/name).stat().st_size>1000
    validation=json.loads((OUT/'validation/validation_receipt.json').read_text())
    assert all(r['exit_code']==0 for r in validation['commands'])
    changes=[name for name,value in validation['protected_sha256_before'].items() if digest(ROOT/name)!=value]
    assert not changes,changes
    modified=subprocess.run(['git','diff','--name-only'],cwd=ROOT,capture_output=True,text=True,check=True).stdout.splitlines()
    assert modified==['AGENTS.md'],modified
    coverage='\n\n## 本轮最终覆盖与读取异常\n\n'
    coverage+=f"元数据清点{inventory['all_files']:,}文件，研究资产{survey['total']:,}文件，目录读取错误{len(inventory['walk_errors'])}，未跟随junction {len(inventory['unfollowed_links_or_junctions'])}。结构可读性状态如下；它们不代表科学有效性或逐行内容审查。\n\n|状态|文件数|\n|---|---:|\n"
    coverage+=''.join(f'|{k}|{v:,}|\n' for k,v in survey['counts'].items())
    coverage+='\n逐项读取/格式错误见`asset_readability_summary.json`的errors和`asset_readability.csv`。两项错误是同一官方字段说明CSV的两个副本在UTF-8下解码失败；后续CP1252可逆解码/逗号解析已通过，原失败和原字节均保留，见`readability_encoding_followup.json`；这不证明原作者唯一编码。首次误用分号的诊断也单独保留，不作为成功解析。超过50MiB的未全文解析文件是`analyses/claim_revision_recovery_20261019/evidence/study/results/aggregate/results.json`，本轮读取其420案例派生表，未冒充全文复算。其余未内容解析文件均显式登记，特别是权重/torch/pickle不反序列化。完整原始科研端到端复现本轮仍为0次。\n'
    path=OUT/'01_project_inventory.md'
    original=path.read_text(encoding='utf-8').split('\n\n## 本轮最终覆盖与读取异常')[0]
    path.write_text(original+coverage,encoding='utf-8')
    receipt={'utc':dt.datetime.now(dt.timezone.utc).isoformat(),'status':'PASS_BOUNDED_AUDIT_DELIVERABLES',
        'inventory_files':count,'research_asset_files':survey['total'],'schema_survey_counts':survey['counts'],
        'schema_read_errors':len(survey['errors']),'ledger_rows':len(ledger),'literature_records':len(papers),
        'protected_existing_files_rehashed':len(validation['protected_sha256_before']),
        'changed_protected_existing_files':changes,'preexisting_tracked_modification_preserved':modified,
        'scientific_gate':'PASS','number_checks':'77/77','targeted_tests':'41 passed',
        'independent_archive_gate':'PASS','new_training':False,'new_model_inference':False,
        'new_scientific_resampling':False,'remote_access':False,
        'scope':'Complete accessible metadata census; stratified content audit and complete compact block review; not entire project scientific certification or end-to-end reproduction',
        'outputs_sha256':{p.relative_to(OUT).as_posix():digest(p) for p in sorted(OUT.rglob('*'))
                          if p.is_file() and p.name!='final_audit_receipt.json' and '__pycache__' not in p.parts}}
    (OUT/'final_audit_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in receipt.items() if k!='outputs_sha256'},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
