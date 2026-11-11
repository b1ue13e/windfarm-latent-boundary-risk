"""Outcome-blind inventory of E07 temporal/node/source availability.

No prediction, calibration, target statistics or outcome-array payload loading.
Raw CSV parsing projects only identity/time columns. Unknown prior access is not
treated as evidence of an unseen confirmation window.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import sys
import zipfile
from datetime import datetime,timezone
from repo_paths import Path, repository_root

import numpy as np

FIRST=35280
LAST=40343
EXPECTED_NODES=np.arange(1,135)
RAW_SHA='6cf7613a82c61bb5cf9fcbbf22e3f6c48165fa32021eb6f1905cb2b7af4d7667'
LOCATION_SHA='15c19ceca43171dfda06e8de487d4d55eb116112904d77958aed7260c2f0d9fe'
PRUNE={'.git','.dl_env','.dl_env313','.era5_env','.venv','venv','envs','node_modules','__pycache__',
       'hf_cache','pip_cache','pypkgs','ollama','appcache','.cache','.agents','.codex'}


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda:handle.read(1024*1024),b''):
            h.update(block)
    return h.hexdigest()


def assess_coordinates(times,nodes,source_verified=False,unviewed_verified=False):
    times=np.asarray(times,dtype=np.int64)
    nodes=np.asarray(nodes,dtype=np.int64)
    expected=np.arange(FIRST,LAST+1)
    unique=np.unique(times)
    missing=np.setdiff1d(expected,unique,assume_unique=True)
    node_exact=bool(np.array_equal(nodes,EXPECTED_NODES))
    ordered=bool(len(times)>0 and np.all(np.diff(times)==1))
    structural=bool(node_exact and ordered and not len(missing))
    reasons=[]
    if len(missing):reasons.append('REQUIRED_NEW_TIME_RANGE_OR_PADDING_MISSING')
    if not node_exact:reasons.append('NODE_IDENTITY_OR_ORDER_MISMATCH')
    if not ordered:reasons.append('TIME_AXIS_NOT_CONTIGUOUS')
    if not source_verified:reasons.append('SOURCE_CONTINUATION_UNVERIFIED')
    if not unviewed_verified:reasons.append('UNVIEWED_STATUS_UNVERIFIED')
    return {'time_min_index':int(unique.min()) if len(unique) else None,
            'time_max_index':int(unique.max()) if len(unique) else None,
            'n_time_positions':len(times),'node_ids':nodes.tolist(),'node_order_exact':node_exact,
            'time_contiguous':ordered,'missing_required_time_positions':len(missing),
            'required_first_index':FIRST,'required_last_including_padding':LAST,
            'structurally_covers_E07':structural,
            'eligible_confirmatory_window':bool(structural and source_verified and unviewed_verified),
            'rejection_reasons':reasons}


def npy_header(path):
    with path.open('rb') as handle:
        version=np.lib.format.read_magic(handle)
        if version==(1,0): shape,fortran,dtype=np.lib.format.read_array_header_1_0(handle)
        elif version in ((2,0),(3,0)): shape,fortran,dtype=np.lib.format.read_array_header_2_0(handle)
        else:raise ValueError('Unsupported NPY header version')
    return {'shape':list(shape),'dtype':str(dtype),'fortran_order':bool(fortran)}


def inspect_cache(metadata_path):
    before=sha(metadata_path)
    meta=json.loads(metadata_path.read_text(encoding='utf-8-sig'))
    root=metadata_path.parent
    record={'kind':'cache','path':str(root),'metadata_sha256':before,
            'dataset':meta.get('dataset'),'metadata_num_steps':meta.get('num_steps'),
            'metadata_num_nodes':meta.get('num_nodes'),'split_bounds':meta.get('split_bounds'),
            'holdout_days':meta.get('holdout_days'),'target_payload_read':False,
            'source_metadata_only':{k:meta[k] for k in ('source_dir','source_path','window_begin','window_offset_days') if k in meta}}
    if not (meta.get('dataset')=='wtb' or meta.get('num_nodes')==134):
        return {**record,'eligible_confirmatory_window':False,'rejection_reasons':['DIFFERENT_DATASET_OR_NODE_POPULATION']}
    times=np.load(root/'time_index.npy',allow_pickle=False)
    nodes=np.load(root/'node_ids.npy',allow_pickle=False)
    if times.ndim!=2 or times.shape[1]!=2:
        raise ValueError('Expected WTB day/slot coordinates')
    if np.any(times[:,0]<1) or np.any(times[:,1]<0) or np.any(times[:,1]>=144):
        raise ValueError('Invalid day/slot coordinates')
    indices=(times[:,0].astype(np.int64)-1)*144+times[:,1].astype(np.int64)
    record.update(assess_coordinates(indices,nodes))
    record['max_day']=int(times[:,0].max())
    record['first_day_slot']=times[0].tolist();record['last_day_slot']=times[-1].tolist()
    record['time_index_sha256']=sha(root/'time_index.npy')
    record['node_ids_sha256']=sha(root/'node_ids.npy')
    target=root/'target.npy'
    if target.exists():
        record['target_header']=npy_header(target)
        if record['target_header']['shape']!=[len(times),len(nodes)]:
            record['eligible_confirmatory_window']=False
            record['rejection_reasons'].append('TARGET_HEADER_AXIS_SHAPE_MISMATCH')
    else:
        record['eligible_confirmatory_window']=False
        record['rejection_reasons'].append('TARGET_ARRAY_MISSING')
    if sha(metadata_path)!=before:
        raise ValueError('Metadata changed during read-only inspection')
    return record


def inspect_raw_csv(path):
    import pandas as pd
    before=sha(path)
    with path.open('r',encoding='utf-8-sig',newline='') as handle:
        header=next(csv.reader(handle))
    if 'location' in path.name.lower() or 'loca' in path.name.lower():
        candidates=[c for c in header if c.lower() in ('turbid','turbine_id','id')]
        nodes=pd.read_csv(path,usecols=candidates)[candidates[0]].astype(int).tolist() if candidates else []
        if sha(path)!=before:raise ValueError('Location source changed')
        return {'kind':'node_location','path':str(path),'bytes':path.stat().st_size,'sha256':before,
                'node_ids':nodes,'canonical_location_hash_match':before==LOCATION_SHA,
                'eligible_confirmatory_window':False,'rejection_reasons':['NODE_MAP_ONLY_NOT_TIME_SERIES']}
    required=['TurbID','Day','Tmstamp']
    if not all(c in header for c in required):
        return {'kind':'raw_csv','path':str(path),'raw_sha256':before,'header':header,
                'eligible_confirmatory_window':False,'rejection_reasons':['UNRECOGNIZED_WTB_TIME_ID_SCHEMA'],
                'outcome_columns_interpreted':False}
    nslots=282*144
    seen=np.zeros((134,nslots),dtype=bool)
    rows=duplicates=invalid=0;day_min=None;day_max=None;node_set=set()
    slot_min=10**9;slot_max=-1
    for chunk in pd.read_csv(path,usecols=required,chunksize=250000):
        tid=chunk['TurbID'].to_numpy(dtype=np.int64)
        days=chunk['Day'].to_numpy(dtype=np.int64)
        parsed=chunk['Tmstamp'].astype(str).str.extract(r'^(\d{1,2}):(\d{2})$')
        if parsed.isna().any().any():raise ValueError('Malformed SCADA time coordinate')
        hours=parsed[0].to_numpy(dtype=np.int64);minutes=parsed[1].to_numpy(dtype=np.int64)
        ok=(tid>=1)&(tid<=134)&(days>=1)&(hours>=0)&(hours<24)&(minutes>=0)&(minutes<60)&(minutes%10==0)
        invalid+=int((~ok).sum());rows+=len(chunk);node_set.update(int(x) for x in np.unique(tid))
        if not ok.all():raise ValueError('Invalid identity/time rows; no filtering allowed')
        pos=(days-1)*144+hours*6+minutes//10
        maxpos=int(pos.max())
        if maxpos>144*10000:raise ValueError('Unexpected source time scale; audit stopped')
        if maxpos>=nslots:
            new_slots=maxpos+1
            extended=np.zeros((134,new_slots),dtype=bool);extended[:,:nslots]=seen
            seen=extended;nslots=new_slots
        keys=(tid-1)*nslots+pos
        unique=np.unique(keys)
        duplicates+=len(keys)-len(unique)+int(seen.ravel()[unique].sum())
        seen.ravel()[unique]=True
        day_min=int(days.min()) if day_min is None else min(day_min,int(days.min()))
        day_max=int(days.max()) if day_max is None else max(day_max,int(days.max()))
        slot_min=min(slot_min,int(pos.min()));slot_max=max(slot_max,maxpos)
    time_present=seen.any(axis=0)
    record=assess_coordinates(np.flatnonzero(time_present),np.array(sorted(node_set)))
    n_unique=int(seen.sum())
    report={'kind':'raw_csv','path':str(path),'bytes':path.stat().st_size,'raw_sha256':before,
            'canonical_245d_hash_match':before==RAW_SHA,'projected_columns':required,
            'outcome_columns_interpreted':False,'rows':rows,'unique_time_node_cells':n_unique,
            'duplicate_time_node_cells':duplicates,'invalid_coordinate_rows':invalid,
            'min_day':day_min,'max_day':day_max,
            'missing_time_node_cells_in_reported_span':len(node_set)*(slot_max-slot_min+1)-n_unique,
            'all_nodes_present_at_every_required_time':bool(seen[:,FIRST:LAST+1].shape[1]==LAST-FIRST+1 and seen[:,FIRST:LAST+1].all()),
            **record}
    if duplicates:
        report['eligible_confirmatory_window']=False
        report['rejection_reasons'].append('DUPLICATE_COORDINATES')
    if not report['all_nodes_present_at_every_required_time']:
        report['structurally_covers_E07']=False
        report['eligible_confirmatory_window']=False
        report['rejection_reasons'].append('REQUIRED_NODE_TIME_CROSS_PRODUCT_MISSING')
    if sha(path)!=before:raise ValueError('Raw CSV changed during coordinate audit')
    return report


def inspect_archive(path):
    record={'kind':'archive_directory_only','path':str(path),'bytes':path.stat().st_size,
            'outcome_payloads_read':False,'eligible_confirmatory_window':False,
            'rejection_reasons':['ARCHIVE_NAME_OR_MTIME_DOES_NOT_ESTABLISH_UNSEEN_WINDOW']}
    with zipfile.ZipFile(path) as archive:
        names=[i for i in archive.infolist() if not i.is_dir()]
        members=[{'name':i.filename,'bytes':i.file_size} for i in names
                 if ('wtb' in i.filename.lower() or 'sdwpf' in i.filename.lower()) and i.filename.lower().endswith(('.csv','.json','.npy'))]
        metadata=[]
        for info in names:
            if Path(info.filename).name=='metadata.json' and info.file_size<=1000000:
                meta=json.loads(archive.read(info).decode('utf-8-sig'))
                if meta.get('dataset')=='wtb' or meta.get('num_nodes')==134:
                    metadata.append({'member':info.filename,'dataset':meta.get('dataset'),'num_steps':meta.get('num_steps'),
                                     'num_nodes':meta.get('num_nodes'),'split_bounds':meta.get('split_bounds')})
    record.update({'matching_member_names':members,'wtb_metadata_members':metadata})
    return record


def discover(roots):
    metadata=[];raw=[];archives=[];external=[];errors=[];root_records=[];visited=set()
    for root in roots:
        root=root.resolve()
        root_records.append({'path':str(root),'exists':root.exists(),'follow_symlinks':False})
        if not root.is_dir():continue
        def onerror(error):errors.append({'path':str(error.filename),'error':str(error)})
        for directory,dirs,files in os.walk(root,onerror=onerror,followlinks=False):
            dirs[:]=[name for name in dirs if name not in PRUNE and not Path(directory,name).is_symlink()]
            for name in files:
                path=Path(directory,name)
                if path.is_symlink() or str(path) in visited:continue
                visited.add(str(path));lower=name.lower();combined=path.as_posix().lower()
                if lower=='metadata.json':metadata.append(path)
                if lower.endswith('.csv') and ('wtb' in lower or 'sdwpf' in lower or
                     (lower in ('train.csv','test.csv','data.csv') and ('wtb' in combined or 'sdwpf' in combined))):raw.append(path)
                if lower.endswith('.zip') and ('wtb' in lower or 'sdwpf' in lower or lower=='windfarm_derived_artifacts_v1.0.zip'):archives.append(path)
                if lower.endswith(('.parquet','.h5','.hdf5','.nc','.csv.gz','.tar.gz')) and ('wtb' in lower or 'sdwpf' in lower):
                    errors.append({'path':str(path),'error':'Relevant non-CSV source found; metadata-only follow-up required, not certified'})
                if lower.endswith('.zip') and any(site in lower for site in ('kelmarsh','penmanshiel','haute-borne')):
                    external.append({'path':str(path),'bytes':path.stat().st_size,'status':'NOT_E07_PRIMARY_COHORT',
                                     'reason':'Different named wind farm, not registered WTB134 continuation; outcomes not opened'})
    return root_records,metadata,raw,archives,external,errors


def run(args):
    if args.output.exists():raise FileExistsError('Audit output already exists')
    started=datetime.now(timezone.utc).isoformat()
    roots,metadata_paths,raw_paths,archive_paths,external,errors=discover(args.root)
    records=[];count=0
    for path in metadata_paths:
        try:
            meta=json.loads(path.read_text(encoding='utf-8-sig'))
            if not isinstance(meta,dict):continue
            if meta.get('dataset')=='wtb' or meta.get('num_nodes')==134:
                records.append(inspect_cache(path));count+=1
            elif meta.get('dataset') in ('external_wind','kelmarsh','penmanshiel','la_haute_borne'):
                records.append({'kind':'external_cache_metadata_only','path':str(path.parent),'metadata_sha256':sha(path),
                                'dataset':meta.get('dataset'),'num_nodes':meta.get('num_nodes'),'num_steps':meta.get('num_steps'),
                                'eligible_confirmatory_window':False,'rejection_reasons':['DIFFERENT_DATASET_OR_NODE_POPULATION'],
                                'outcome_payloads_read':False})
        except Exception as exc:errors.append({'path':str(path),'error':type(exc).__name__+': '+str(exc)})
    for path in raw_paths:
        try:records.append(inspect_raw_csv(path))
        except Exception as exc:errors.append({'path':str(path),'error':type(exc).__name__+': '+str(exc)})
    for path in archive_paths:
        try:records.append(inspect_archive(path))
        except Exception as exc:errors.append({'path':str(path),'error':type(exc).__name__+': '+str(exc)})
    result={'status':'SCOPED_METADATA_AUDIT_NO_CALIBRATION','host':platform.node(),
            'started_utc':started,'finished_utc':datetime.now(timezone.utc).isoformat(),
            'python':platform.python_version(),'numpy':np.__version__,'device':'CPU metadata/coordinate IO only',
            'script_sha256':sha(Path(__file__)),'argv':[sys.executable,*sys.argv],
            'roots':roots,'pruned_directory_names':sorted(PRUNE),'walk_and_inspection_errors':errors,
            'wtb_cache_count':count,'records':records,'other_site_archive_inventory':external,
            'confirmed_eligible_window_count':sum(r.get('eligible_confirmatory_window',False) for r in records),
            'structural_future_candidate_count':sum(r.get('structurally_covers_E07',False) for r in records),
            'archive_extended_metadata_claim_count':sum(1 for r in records for m in r.get('wtb_metadata_members',[])
                                                        if isinstance(m.get('num_steps'),int) and m['num_steps']>35280),
            'required_window':{'site':'WTB','node_ids':EXPECTED_NODES.tolist(),'first':FIRST,'last_with_padding':LAST},
            'limitations':['Scope is the listed accessible roots, not all storage on either host.',
                           'No target-array payload or SCADA outcome column is interpreted.',
                           'Hashing reads bytes without examining outcome values.',
                           'Absence of access records is not proof of unviewed status.',
                           'Every structural future candidate still requires a source-continuation and prior-exposure attestation.',
                           'Archive inventories use member names and metadata only; no extracted outcomes.']}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({'output':str(args.output),'host':result['host'],'wtb_cache_count':count,
                      'raw_csv_count':sum(r['kind']=='raw_csv' for r in records),
                      'eligible':result['confirmed_eligible_window_count'],'errors':len(errors),
                      'wtb_max_days':[r.get('max_day') for r in records if r.get('kind') in ('cache','raw_csv')]}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,action='append',required=True)
    parser.add_argument('--output',type=Path,required=True)
    run(parser.parse_args())
