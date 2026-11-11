"""Recover a completed immutable campaign; never submit or modify a job."""
import base64,hashlib,io,json,subprocess,zipfile
from repo_paths import Path, repository_root


def main():
    local=Path('experiments/mixture_closed_loop_20261024')
    deployment=json.loads((local/'deployment.json').read_text());root=deployment['remote_root']
    code=f'''import pathlib,json,zipfile,io,base64,hashlib,subprocess,datetime
r=pathlib.Path({root!r});p=r/'results/campaign';state=json.loads((p/'state.json').read_text()) if (p/'state.json').exists() else {{'status':'PREFLIGHT_PENDING'}}
q=subprocess.run(['qstat','-xf','252766.cm'],capture_output=True,text=True);fields={{}}
for line in q.stdout.splitlines():
 if '=' in line:
  k,v=line.strip().split('=',1)
  if k.strip() in ['job_state','Exit_status','resources_used.cput','resources_used.walltime','resources_used.ncpus','resources_used.mem','exec_host']:fields[k.strip()]=v.strip()
summary=dict(status=state['status'],phase_receipts=state.get('phase_receipts',[]),elapsed_seconds=state.get('elapsed_seconds'),pbs=fields,queried_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
if fields.get('job_state')=='F':
 files=[f for f in p.rglob('*') if f.is_file()]+[f for f in (r/'runtime').glob('*') if f.is_file()]+list(r.glob('*.o*'))+[r/'deployment.json',r/'submission.json',r/'DEPLOYMENT_MANIFEST.json']
 b=io.BytesIO()
 with zipfile.ZipFile(b,'w',zipfile.ZIP_DEFLATED) as z:
  for f in files:z.write(f,f.relative_to(r))
  z.writestr('RECOVERY_MEMBERS.json',json.dumps({{str(f.relative_to(r)):hashlib.sha256(f.read_bytes()).hexdigest() for f in files}}))
 payload=b.getvalue();summary.update(payload=base64.b64encode(payload).decode(),sha256=hashlib.sha256(payload).hexdigest())
print(json.dumps(summary))
'''
    result=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=20','metis',
        '/lstr/sahara/minlpml/junyu/paper3_raw_replay_20261015/.venv/bin/python','-'],
        input=code,text=True,capture_output=True,timeout=180)
    if result.returncode:raise RuntimeError(result.stderr)
    record=json.loads(result.stdout);payload=record.pop('payload',None)
    (local/'latest_status.json').write_text(json.dumps(record,indent=2))
    if payload is not None:
        data=base64.b64decode(payload);assert hashlib.sha256(data).hexdigest()==record['sha256']
        archive=local/'recovered_results.zip';archive.write_bytes(data)
        folder=local/'recovered';folder.mkdir(exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for name in z.namelist():
                target=(folder/name).resolve()
                if not target.is_relative_to(folder.resolve()):raise ValueError('Invalid archive path')
                if target.exists() and target.read_bytes()!=z.read(name):raise ValueError('Existing result differs')
            z.extractall(folder)
        members=json.loads((folder/'RECOVERY_MEMBERS.json').read_text())
        assert all(hashlib.sha256((folder/k).read_bytes()).hexdigest()==v for k,v in members.items())
        record.update(recovered_files=len(members),recovery_bytes=len(data))
        (local/'recovery_receipt.json').write_text(json.dumps(record,indent=2))
    print(json.dumps(record,indent=2))


if __name__=='__main__':main()
