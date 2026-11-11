"""Bind read-only inventory evidence without inventing a confirmatory dataset."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from datetime import datetime,timezone
from pathlib import Path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def evaluate_inventory_reports(reports):
    structural=sum(r['structural_future_candidate_count'] for r in reports)
    eligible=sum(r['confirmed_eligible_window_count'] for r in reports)
    errors=sum(len(r['walk_and_inspection_errors']) for r in reports)
    if eligible:
        # A metadata collector alone cannot authorize a binding without receipts.
        return 'POSITIVE_CLAIM_REQUIRES_INDEPENDENT_SOURCE_AND_EXPOSURE_RECEIPTS'
    if structural:
        return 'STRUCTURAL_CANDIDATE_REQUIRES_BLINDED_FOLLOWUP'
    if errors:
        return 'NO_VERIFIED_WINDOW_SEARCH_HAS_UNRESOLVED_ERRORS'
    return 'NO_ELIGIBLE_WINDOW_FOUND_IN_AUDITED_SCOPES'


def run(args):
    if args.output.exists():raise FileExistsError('Existing audit manifest is read-only')
    root=args.workspace.resolve()
    collector=root/'scripts/audit_e07_window_inventory.py'
    files=[args.local,args.remote,args.archive,collector,root/'docs/EXTERNAL_RELEASE_METADATA.md',
           root/'experiments/E07_history_only_recalibration/protocol.json']
    before={str(p):sha(p) for p in files}
    if sha(args.remote)!=args.remote_report_sha256:
        raise ValueError('Transferred remote inventory hash differs from remote attestation')
    reports=[json.loads(p.read_text(encoding='utf-8')) for p in (args.local,args.remote)]
    if any(r['script_sha256']!=sha(collector) for r in reports):
        raise ValueError('Collector source differs between hosts')
    finding=evaluate_inventory_reports(reports)
    raws=[];rejections=[]
    for inventory in reports:
        for r in inventory['records']:
            if r.get('projected_columns'):
                raws.append({'host':inventory['host'],**r})
            if r.get('kind') in ('cache','raw_csv','external_cache_metadata_only') and (r.get('max_day') is not None or r.get('kind')=='external_cache_metadata_only'):
                rejections.append({'host':inventory['host'],'kind':r['kind'],'path':r['path'],
                                   'max_day':r.get('max_day'),'nodes':len(r.get('node_ids',[])) or r.get('num_nodes'),
                                   'missing_required_time_positions':r.get('missing_required_time_positions'),
                                   'reasons':';'.join(r['rejection_reasons'])})
    if len(raws)!=2 or len({r['raw_sha256'] for r in raws})!=1:
        raise ValueError('Expected one coordinate-audited canonical WTB mirror per host')
    if not all(r['canonical_245d_hash_match'] and r['rows']==4727520 and r['unique_time_node_cells']==4727520
               and r['duplicate_time_node_cells']==0 and r['missing_time_node_cells_in_reported_span']==0
               and r['node_order_exact'] for r in raws):
        raise ValueError('Available canonical raw source failed identity/grid verification')
    archive=json.loads(args.archive.read_text(encoding='utf-8'))
    doc=(root/'docs/EXTERNAL_RELEASE_METADATA.md').read_text(encoding='utf-8')
    declared={}
    for section in re.split(r'(?m)^### ',doc):
        path=re.search(r'\*\*Path\*\*: `([^`]+)`',section)
        digest=re.search(r'\*\*SHA256\*\*: `([0-9a-f]{64})`',section)
        if path and digest:declared[path.group(1)]=digest.group(1)
    mismatches=[{'member':m['name'],'documented_sha256':declared.get(m['name']),
                 'measured_sha256':m['sha256'],'status':'MISMATCH_PRESERVED_NOT_REPAIRED'}
                for m in archive['members'] if declared.get(m['name'])!=m['sha256']]
    plan=json.loads((root/'experiments/E07_history_only_recalibration/protocol.json').read_text(encoding='utf-8'))
    if plan['activation']['prospective_collection_spec_manifest_sha256'] is not None:
        raise ValueError('Unexpected existing confirmatory data binding')
    historical={'raw_sha256':raws[0]['raw_sha256'],'bytes':raws[0]['bytes'],'nodes':134,
                'rows':4727520,'day_range':[1,245],'time_index_range':[0,35279],
                'mirrors':[{'host':r['host'],'path':r['path']} for r in raws],
                'source_role':'verified existing history only; not a new test-window binding'}
    manifest={'status':finding,'prepared_utc':datetime.now(timezone.utc).isoformat(),
              'kind':'AVAILABILITY_AUDIT_MANIFEST_NOT_CONFIRMATORY_DATA_MANIFEST',
              'confirmed_eligible_window_count':0,'confirmatory_data_manifest':None,
              'historical_source':historical,
              'required_new_window':{'issue_first':35280,'issue_last':40319,'padding_last':40343,
                                     'missing_issue_positions':5040,'missing_padding_positions':24,
                                     'missing_node_time_cells':5064*134},
              'inventory_summary':[{'host':r['host'],'roots':r['roots'],'wtb_cache_count':r['wtb_cache_count'],
                                    'structural_future_candidate_count':r['structural_future_candidate_count'],
                                    'inspection_error_count':len(r['walk_and_inspection_errors']),
                                    'excluded_other_site_archives':len(r['other_site_archive_inventory'])} for r in reports],
              'rejection_table':rejections,'legacy_release_member_hash_discrepancies':mismatches,
              'gap_ledger':[
                  {'id':'G1','status':'MISSING_IN_AUDITED_SCOPES','item':'WTB issue indices35280-40319 plus padding40320-40343'},
                  {'id':'G2','status':'UNBOUND','item':'New source continuity to the same physical134 nodes and original indexed clock'},
                  {'id':'G3','status':'UNVERIFIED','item':'Positive prior-exposure/collection-access evidence for any new window'},
                  {'id':'G4','status':'UNBOUND','item':'Actual event/label/QC arrival timestamps for future history-only chronology'},
                  {'id':'G5','status':'INTENTIONALLY_NOT_EXECUTED','item':'Recalibration offsets or performance evaluation; not run by this audit'}],
              'calibration_run':False,'new_test_outcomes_interpreted':False,
              'source_file_hashes_before':before,
              'argv':[sys.executable,*sys.argv], 'script_sha256':sha(Path(__file__)),
              'scope_limitations':['Not an exhaustive search of all mounted/shared storage.',
                                   'Roots, pruned directories, name filters and errors are in each inventory.',
                                   'Unknown prior access cannot be promoted to an unviewed confirmation status.',
                                   'Other wind farms, shifted labels, artificial padding or legacy holdout names cannot replace the registered WTB continuation.']}
    after={str(p):sha(p) for p in files}
    if before!=after:raise ValueError('Input evidence changed during finalization')
    manifest['source_file_hashes_after']=after
    manifest['input_files_unchanged']=True
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    target=args.output.with_name('candidate_rejections.csv')
    if target.exists():raise FileExistsError('Rejection ledger already exists')
    with target.open('w',encoding='utf-8',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(rejections[0]));writer.writeheader();writer.writerows(rejections)
    print(json.dumps({'status':finding,'historical_source_sha256':historical['raw_sha256'],
                      'release_member_hash_mismatches':len(mismatches),'confirmation_bound':False},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('workspace','local','remote','archive','output'):parser.add_argument('--'+key,type=Path,required=True)
    parser.add_argument('--remote-report-sha256',required=True)
    run(parser.parse_args())
