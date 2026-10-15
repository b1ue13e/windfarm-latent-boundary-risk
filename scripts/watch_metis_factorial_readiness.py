"""One-shot control-plane watcher: audit real inputs in PBS before any release.

No experiment source/data changes; every control command keeps full output/error.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import subprocess
import time
import traceback


def replacement_dependency(current,audit_job):
    if current.get('Hold_Types')!='s':raise ValueError('Unexpected user/operator/other hold; do not change dependencies')
    parsed={};raw={}
    for segment in current.get('depend','').split(','):
        parts=segment.split(':');kind=parts[0]
        if kind in parsed or len(parts)<2:raise ValueError('Unknown dependency form')
        parsed[kind]={job.split('@',1)[0] for job in parts[1:]};raw[kind]=segment
    if set(parsed)!={'afterok','beforeok'}:raise ValueError('Unexpected dependency type')
    if parsed['afterok'] not in ({'242595.cm'},{'242601.cm','242595.cm'}):
        raise ValueError('New/unknown prerequisite; refuse to replace')
    if parsed['beforeok']!={'242603.cm'}:raise ValueError('Unexpected downstream dependency')
    return 'afterok:242601.cm:'+audit_job+','+raw['beforeok']


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace',type=Path,required=True)
    p.add_argument('--tool-dir',type=Path,required=True)
    p.add_argument('--probe',action='store_true')
    a=p.parse_args();root=a.workspace.resolve();tool=a.tool_dir.resolve()
    base=root/'artifacts/raw_replay_20261015_v2'
    required=[base/'execution'/f'train_{family}_{seed}/record.json'
        for family in ('forecast','unaligned','aligned','dense_classifier') for seed in range(201,206)]
    required.append(base/'execution/fixed_residuals/record.json')
    state=root/'metis_execution/factorial_readiness_control.json'
    def write(data):
        data.update(recorded_utc=datetime.now(timezone.utc).isoformat(),scientific_completion=False)
        tmp=state.with_suffix('.json.tmp');tmp.write_text(json.dumps(data,indent=2));tmp.replace(state)
    def availability():
        pending=[];failed=[]
        for path in required:
            if not path.exists():pending.append(str(path));continue
            r=json.loads(path.read_text())
            if r.get('status')=='FAILED':failed.append(str(path))
            elif r.get('status')!='EXECUTED' or r.get('exit_code')!=0:pending.append(str(path))
        return pending,failed
    if a.probe:
        pending,failed=availability();print(json.dumps({'status':'PROBE_ONLY','pending_receipts':len(pending),'failed_receipts':failed,'scientific_completion':False}));return
    journal=root/'metis_execution/pbs_jobs_factorial_readiness.json'
    if journal.exists():raise FileExistsError('Existing audit/release attempt; preserve and inspect before retry')
    deadline=time.monotonic()+24*3600
    try:
        while True:
            pending,failed=availability()
            if failed:write({'status':'BLOCKED_REQUIRED_EXECUTION_FAILED','failed_receipts':failed});return
            if not pending:break
            write({'status':'WAITING_FOR_REQUIRED_EXECUTION_RECEIPTS','pending_count':len(pending)})
            if time.monotonic()>deadline:raise TimeoutError('Input readiness wait exceeded24h')
            time.sleep(60)
        manifest=json.loads((tool/'source_manifest.json').read_text())
        for row in manifest['files']:
            if hashlib.sha256((tool/row['name']).read_bytes()).hexdigest()!=row['sha256']:
                raise ValueError('Readiness tool/source manifest mismatch')
        stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        logs=root/'metis_execution/readiness_control_logs'/stamp;logs.mkdir(parents=True,exist_ok=False)
        argv=['/opt/pbs/bin/qsub','-N','p3_fact_ready','-o',str(logs/'audit.stdout'),str(tool/'run_readiness_audit.pbs')]
        cp=subprocess.run(argv,cwd=root,text=True,capture_output=True)
        (logs/'qsub.stdout').write_text(cp.stdout);(logs/'qsub.stderr').write_text(cp.stderr)
        if cp.returncode:raise RuntimeError('Readiness PBS submission failed')
        job=cp.stdout.strip()
        journal.write_text(json.dumps([{'stage':'factorial-readiness-audit','job_id':job,
            'argv':argv,'execution_status':'SUBMITTED_NOT_EXECUTED','scientific_completion':False}],indent=2))
        write({'status':'AUDIT_SUBMITTED_NOT_VERIFIED','job_id':job})
        while True:
            cmd=['/opt/pbs/bin/qstat','-x','-f','-F','json',job]
            q=subprocess.run(cmd,text=True,capture_output=True)
            tag=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
            (logs/(tag+'_qstat.stdout')).write_text(q.stdout);(logs/(tag+'_qstat.stderr')).write_text(q.stderr)
            details=json.loads(q.stdout).get('Jobs',{}).get(job,{}) if q.returncode==0 else {}
            if details.get('job_state')=='F':
                if details.get('Exit_status')!=0:write({'status':'BLOCKED_AUDIT_FAILED','job_id':job});return
                break
            if time.monotonic()>deadline:raise TimeoutError('Readiness audit wait exceeded24h')
            time.sleep(60)
        report_path=root/'metis_execution/fit_audits/factorial_readiness_attempt2/report.json'
        report=json.loads(report_path.read_text())
        if (report.get('mode')!='factorial-readiness' or report.get('readiness')!='INPUTS_VERIFIED' or
            report.get('pbs_job_id')!=job or report.get('pending') or report.get('failures') or
            len(report.get('results',[]))!=20 or not report.get('canonical')):
            raise ValueError('Readiness report does not qualify for release')
        if report['audit_program']['sha256']!=manifest['audit_program_sha256']:
            raise ValueError('Readiness report used a different audit program')
        before=subprocess.run(['/opt/pbs/bin/qstat','-x','-f','-F','json','242602[].cm'],text=True,capture_output=True)
        (logs/'factorial_before.stdout').write_text(before.stdout);(logs/'factorial_before.stderr').write_text(before.stderr)
        if before.returncode:raise RuntimeError('Cannot inspect current factorial dependency')
        current=json.loads(before.stdout)['Jobs']['242602[].cm']
        if not current.get('Job_Owner','').startswith('junyu@') or current.get('Job_Name')!='p3_fact_v2':
            raise RuntimeError('Refuse to change an unrelated job')
        if current['job_state']!='H':
            write({'status':'NO_DEPENDENCY_CHANGE_ALREADY_RELEASED','job_id':'242602[].cm',
                'observed_state':current['job_state'],'audit_job_id':job});return
        dependency=replacement_dependency(current,job)
        cmd=['/opt/pbs/bin/qalter','-W','depend='+dependency,'242602[].cm']
        change=subprocess.run(cmd,text=True,capture_output=True)
        (logs/'qalter.stdout').write_text(change.stdout);(logs/'qalter.stderr').write_text(change.stderr)
        after=subprocess.run(['/opt/pbs/bin/qstat','-x','-f','-F','json','242602[].cm'],text=True,capture_output=True)
        (logs/'factorial_after.stdout').write_text(after.stdout);(logs/'factorial_after.stderr').write_text(after.stderr)
        receipt={'status':'DEPENDENCY_UPDATE_ACCEPTED_NOT_EXECUTION' if change.returncode==0 else 'DEPENDENCY_UPDATE_FAILED',
            'audit_job_id':job,'audit_report':str(report_path),'audit_report_sha256':hashlib.sha256(report_path.read_bytes()).hexdigest(),
            'argv':cmd,'exit_code':change.returncode,'after_qstat_exit':after.returncode,
            'followup':'Inspect actual queue/hold/run state; this is not a training or scientific result'}
        (logs/'release_receipt.json').write_text(json.dumps(receipt,indent=2))
        write(receipt)
        if change.returncode:raise RuntimeError('Dependency update failed; no forced release')
    except Exception:
        write({'status':'BLOCKED_CONTROL_ERROR','traceback':traceback.format_exc()})
        raise


if __name__=='__main__':main()
