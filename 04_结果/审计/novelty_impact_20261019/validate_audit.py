"""Check frozen claims, numerical sources, metadata and bounded audit deliverables."""
from pathlib import Path
import ast
import collections
import csv
import datetime as dt
import hashlib
import json
import platform
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
WORK=Path(__file__).resolve().parent
AUDIT=ROOT/'research_audit'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    freeze=json.loads((WORK/'claim_freeze.json').read_text(encoding='utf-8'))
    checked={}
    for name,value in freeze['sources_sha256'].items():
        actual=sha(ROOT/name);assert actual==value,name;checked[name]=actual
    with (AUDIT/'13_prior_art_comparison.csv').open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
    assert len(rows)==119 and len({r['Paper_ID'] for r in rows})==17
    assert all(n==7 for n in collections.Counter(r['Paper_ID'] for r in rows).values())
    allowed={'DIRECT OVERLAP','STRONG OVERLAP','PARTIAL OVERLAP','RELATED','UNCERTAIN'}
    assert all(r['Overlap'] in allowed for r in rows)
    assert all(r['Gap_Role'] in {'foundational','mainstream','failing','adjacent'} for r in rows)
    assert all(r['Evidence_Locator'] and r['URL'].startswith('https://') for r in rows)
    assert all('ABSTRACT' not in r['Read_Level'] for r in rows if r['Overlap'] in {'DIRECT OVERLAP','STRONG OVERLAP'})
    metadata=json.loads((WORK/'registry_metadata_verification.json').read_text(encoding='utf-8'))
    assert sum(r['status']=='TITLE_MATCH' for r in metadata['results'])==15
    assert sum(r['status']=='NO_DOI_DECLARED' for r in metadata['results'])==2
    assert sha(WORK/'prior_art_registry_before_dimension_refinement.json')==metadata['registry_sha256']
    old=json.loads((WORK/'prior_art_registry_before_dimension_refinement.json').read_text(encoding='utf-8'))
    new=json.loads((WORK/'prior_art_registry.json').read_text(encoding='utf-8'))
    assert [{k:v for k,v in r.items() if k!='dimension_overlaps'} for r in new]==old
    p=json.loads((WORK/'reviewer_p/practical_receipt.json').read_text(encoding='utf-8'))
    assert p['all_inputs_unchanged'] and all(p['frozen_claim_source_matches'].values())
    for name,value in p['sources_sha256_before'].items():
        path=Path(name)
        if not path.is_absolute():path=ROOT/path
        assert sha(path)==value,name
    n=json.loads((WORK/'reviewer_p/number_gate/tste_number_consistency_audit.json').read_text(encoding='utf-8'))
    assert n['status']=='complete_tste_number_consistency' and n['n_checks']==77 and n['n_failed']==0
    # The existing captured log uses a Windows console encoding; the gate marker is ASCII.
    assert b'SCIENTIFIC_CLAIM_GATE: PASS' in (WORK/'reviewer_p/scientific_gate.txt').read_bytes()
    for name in ('08_claim_inventory.md','09_prior_art_threats.md','10_novelty_audit.md','11_scientific_significance.md',
                 '12_practical_impact.md','13_prior_art_comparison.csv','FINAL_NOVELTY_AND_IMPACT_VERDICT.md'):
        assert (AUDIT/name).is_file() and (AUDIT/name).stat().st_size>1000
    for f in WORK.rglob('*.py'):ast.parse(f.read_text(encoding='utf-8-sig'),filename=str(f))
    final=(AUDIT/'FINAL_NOVELTY_AND_IMPACT_VERDICT.md').read_text(encoding='utf-8')
    short=final.split('## 300字内科研价值摘要\n\n')[1].strip();assert len(short)<=300
    output=WORK/'independent_archive_gate_final.json'
    if output.exists():raise FileExistsError('Retain previous validation; choose a new output if rerunning.')
    result=subprocess.run([sys.executable,'scripts/verify_independent_confirmation_gate.py','--output',str(output)],
                          cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    (WORK/'independent_archive_gate_final_stdout.txt').write_bytes(result.stdout)
    assert result.returncode==0,result.stdout.decode('utf-8','replace')[-2000:]
    receipt=dict(utc=dt.datetime.now(dt.timezone.utc).isoformat(),argv=sys.argv,python=sys.version,platform=platform.platform(),
        status='PASS_BOUNDED_NOVELTY_IMPACT_AUDIT',frozen_sources_checked=checked,claim_inventory_unchanged=True,
        comparison_papers=17,comparison_rows=119,doi_titles_verified=15,official_no_doi_records=2,
        practical_inputs_rechecked=len(p['sources_sha256_before']),scientific_gate='PASS',number_gate='77/77',
        independent_archive_gate='PASS',summary_characters=len(short),research_decision='REPOSITION',practical_impact='UNPROVEN',
        no_new_training=True,no_new_model_inference=True,no_new_scientific_resampling=True,no_remote_access=True,
        scope='Claim scope, references, deterministic reaggregation and document consistency. No originality-exclusivity, interval-coverage or field-value certificate.')
    paths=[AUDIT/x for x in ('08_claim_inventory.md','09_prior_art_threats.md','10_novelty_audit.md','11_scientific_significance.md',
           '12_practical_impact.md','13_prior_art_comparison.csv','FINAL_NOVELTY_AND_IMPACT_VERDICT.md')]
    paths += [f for f in WORK.rglob('*') if f.is_file() and f.name!='validation_receipt.json' and '__pycache__' not in f.parts
              and f.suffix.lower() not in {'.pdf','.html'} and not (f.parent.name=='reviewer_n' and f.suffix=='.txt')
              and not f.name.startswith('root_web_retrievals')]
    receipt['deliverable_sha256']={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(paths)}
    (WORK/'validation_receipt_final.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in receipt.items() if k not in ('deliverable_sha256','frozen_sources_checked')},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
