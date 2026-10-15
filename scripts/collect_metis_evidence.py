"""Read-only PBS/run evidence snapshot; never promotes queue status to reproduction.

Deploy this collector under metis_execution/, outside the frozen experiment source
tree. Every invocation creates a new directory, including full command errors.
"""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import uuid


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def is_fit_receipt(name):
    return bool(re.fullmatch(
        r'(?:train_(?:forecast|aligned_force|unaligned|aligned|dense_classifier|dense)|'
        r'la_haute_borne|kelmarsh|penmanshiel)_20[1-5]',name))


def snapshot(root,qstat):
    root=Path(root).resolve()
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+uuid.uuid4().hex[:8]
    out=root/'metis_execution/monitor_snapshots'/stamp
    out.mkdir(parents=True,exist_ok=False)
    copied={};events=[];jobs={};commands=[]

    def save(source):
        source=Path(source).resolve()
        if not source.is_relative_to(root):
            events.append({'status':'OUTSIDE_WORKSPACE_NOT_COPIED','path':str(source)})
            return
        if not source.is_file():
            events.append({'status':'SOURCE_NOT_YET_AVAILABLE','path':str(source)})
            return
        rel=source.relative_to(root).as_posix()
        if rel in copied:return
        target=out/'files'/rel;target.parent.mkdir(parents=True,exist_ok=True)
        before=source.stat();shutil.copyfile(source,target);after=source.stat()
        stable=before.st_size==after.st_size and before.st_mtime_ns==after.st_mtime_ns
        copied[rel]={'source':str(source),'copy':'files/'+rel,'bytes':target.stat().st_size,
            'sha256':digest(target),'source_size_before':before.st_size,
            'source_size_after':after.st_size,'source_mtime_ns_after':after.st_mtime_ns,
            'copy_stable_during_read':stable,
            'note':'snapshot of available bytes; running output may be incomplete; stability is not experimental completion'}

    submissions=[]
    for path in sorted((root/'metis_execution').glob('pbs_jobs*.json')):
        save(path)
        try:submissions.extend(json.loads(path.read_text(encoding='utf-8')))
        except (ValueError,OSError) as e:events.append({'status':'INVALID_SUBMISSION_RECEIPT','path':str(path),'error':str(e)})
    ids=sorted({r['job_id'] for r in submissions})
    for job_id in ids:
        argv=[str(qstat),'-x','-t','-f','-F','json',job_id]
        tag=job_id.replace('[','_').replace(']','_')
        stdout=out/f'qstat_{tag}.stdout';stderr=out/f'qstat_{tag}.stderr'
        timeout=False
        with stdout.open('wb') as so,stderr.open('wb') as se:
            try:code=subprocess.run(argv,stdout=so,stderr=se,timeout=45).returncode
            except subprocess.TimeoutExpired:code=None;timeout=True
        commands.append({'argv':argv,'exit_code':code,'timed_out':timeout,
            'stdout':stdout.name,'stderr':stderr.name,
            'stdout_sha256':digest(stdout),'stderr_sha256':digest(stderr)})
        if code!=0:
            events.append({'job_id':job_id,'status':'PBS_HISTORY_UNKNOWN',
                'reason':'qstat nonzero/timeout; not proof of experiment failure or success'})
            continue
        try:details=json.loads(stdout.read_text(encoding='utf-8'))['Jobs']
        except (ValueError,KeyError) as e:
            events.append({'job_id':job_id,'status':'PBS_HISTORY_INVALID','error':str(e)});continue
        jobs.update(details)
        for actual_id,job in details.items():
            for key in ('Output_Path','Error_Path'):
                value=job.get(key)
                if value:
                    path=value.split(':',1)[-1]
                    save(Path(path) if Path(path).is_absolute() else root/path)
    for folder in ('logs','metis_execution'):
        for directory,dirs,names in os.walk(root/folder):
            dirs[:]=[name for name in dirs if name not in ('monitor_snapshots','bin','__pycache__','.git','.venv')]
            for name in sorted(names):
                path=Path(directory)/name
                if path.suffix in ('.json','.txt','.log','.sha256','.stdout','.stderr','.py','.pbs','.md'):
                    save(path)
    records=[]
    for base in sorted((root/'artifacts').glob('raw_replay*')):
        if not base.is_dir():continue
        # Supplemental experiment families have nested execution directories.
        # Preserve those receipts/logs as well as the original top-level queues.
        execution_dirs=sorted(p for p in base.rglob('execution') if p.is_dir())
        for directory in execution_dirs:
            for path in sorted(directory.glob('*/*')):
                if path.is_file() and path.suffix in ('.json','.log'):save(path)
        for pattern in ('models/*/seed*/training_history.json','models/*/seed*/training_summary.json',
                        '*/seed*/training_history.json','*/seed*/training_summary.json'):
            for path in sorted(base.glob(pattern)):save(path)
        for directory in execution_dirs:
            for path in sorted(directory.glob('*/record.json')):
                try:records.append(dict(path=str(path),**json.loads(path.read_text(encoding='utf-8'))))
                except (ValueError,OSError) as e:events.append({'status':'RUN_RECEIPT_INVALID','path':str(path),'error':str(e)})
        for name in ('coverage.json','cache_manifest.json','preprocessing_comparison.json',
                     'downstream_status.json','transfer_status.json','frozen_protocol.json','runtime.json'):
            if (base/name).is_file():save(base/name)
    # qstat returns F/exit0 for a successful stage, but scientific output validity
    # additionally requires its receipts, hashes, populations and final claim audit.
    summaries=[{'job_id':jid,'state':j.get('job_state'),'exit_status':j.get('Exit_status'),
        'comment':j.get('comment'),'stage_finished_exit0':j.get('job_state')=='F' and j.get('Exit_status')==0}
        for jid,j in sorted(jobs.items())]
    index={'recorded_utc':datetime.now(timezone.utc).isoformat(),'workspace':str(root),
        'collector_sha256':digest(__file__),'commands':commands,'jobs':summaries,
        'run_status_counts':dict(Counter(r.get('status','UNKNOWN') for r in records)),
        'fit_receipts':[{'path':r['path'],'name':r.get('name'),'status':r.get('status'),
                         'exit_code':r.get('exit_code')} for r in records
                        if is_fit_receipt(r.get('name',''))],
        'files':list(copied.values()),'events':events,'scientific_completion':False,
        'scope':'full available log/receipt bytes and scheduler state only; no scientific reproduction certificate'}
    (out/'index.json').write_text(json.dumps(index,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps({'snapshot':str(out),'parent_jobs':[j for j in summaries
        if '[' not in j['job_id'] or '[]' in j['job_id']],
        'run_status_counts':index['run_status_counts'],
        'files_copied':len(copied),'scientific_completion':False},ensure_ascii=False))
    return out


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--qstat',type=Path,default=Path('/opt/pbs/bin/qstat'))
    args=p.parse_args();snapshot(args.root,args.qstat)
