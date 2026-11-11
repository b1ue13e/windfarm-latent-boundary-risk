"""Export sealed outputs after independent acceptance; no new measurements or fit."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import zipfile


def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()


def main():
    b=Path(__file__).resolve().parent
    audit=json.loads((b/'independent_audit.json').read_text())
    assert audit['status']=='PASS_INDEPENDENT_ACTION_AND_SOURCE_REPLAY'
    jobs={}
    for n in (254015,254016,254017,254018):
        txt=subprocess.check_output(['qstat','-xf',str(n)+'.cm'],text=True)
        data={}
        for name in ('Job_Name','job_state','Exit_status','resources_used.cput','resources_used.walltime','resources_used.ncpus','resources_used.mem','exec_host'):
            m=re.search(r'^\s*'+re.escape(name)+r'\s*=\s*(.+)$',txt,re.M)
            if m:data[name]=m.group(1).strip()
        jobs[str(n)+'.cm']=data
    assert all(x.get('Exit_status')=='0' for x in jobs.values()),jobs
    def seconds(s):
        h,m,v=map(int,s.split(':'));return h*3600+m*60+v
    allocated=sum(seconds(d['resources_used.walltime'])*int(d['resources_used.ncpus']) for d in jobs.values())
    cpu=sum(seconds(d['resources_used.cput']) for d in jobs.values())
    assert allocated<=14400
    budget=dict(max_allocated_cpu_seconds=14400,used_allocated_cpu_seconds=allocated,pbs_reported_cpu_seconds=cpu,jobs=jobs,
                new_fits=0,frozen_policy_instances=10,additional_candidates=0,utc=datetime.now(timezone.utc).isoformat())
    with (b/'BUDGET_FINAL.json').open('x') as f:json.dump(budget,f,indent=2)
    files=[p for p in (b/'results').rglob('*') if p.is_file() and p.name not in ('physical_channels.npy','confirmation.npz')]
    files += [b/n for n in ('independent_audit.json','BUDGET_FINAL.json','protocol.json','adapter.py','test_mainline_2026_adapter.py',
                            'audit_results.py','identity_packet.json','acquisition_receipt.json','freeze_after_preflight.py')]
    records={str(p.relative_to(b)):dict(bytes=p.stat().st_size,sha256=sha(p)) for p in files}
    package=b/'accepted_evidence.zip'
    with zipfile.ZipFile(package,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for p in sorted(files):z.write(p,p.relative_to(b).as_posix())
        z.writestr('EXPORT_MEMBERS.json',json.dumps(records,indent=2))
    receipt=dict(bytes=package.stat().st_size,sha256=sha(package),members=len(files)+1,
                 raw_source_zip_included=False,physical_channels_included=False,
                 raw_actions_preserved=True,utc=datetime.now(timezone.utc).isoformat())
    with (b/'EXPORT_RECEIPT.json').open('x') as f:json.dump(receipt,f,indent=2)
    print(json.dumps(dict(export=receipt,budget=budget)))


if __name__=='__main__':main()
