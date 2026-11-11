"""Compact immutable confirmation evidence; no raw annual SCADA export."""
import argparse
from repo_paths import Path, repository_root
import hashlib
import json
import tarfile


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():
        raise ValueError('Never overwrite exported evidence')
    args.output.mkdir(parents=True)
    results=args.root/'results'
    if not (results/'aggregate/manifest.json').exists():
        raise ValueError('Aggregate not complete')
    files=[p for p in args.root.rglob('*') if p.is_file() and (
           p.suffix in ('.py','.pbs') or p.name in ('deployment_manifest.json','preflight_receipt.json','REVIEW_RELEASE.json')
           or (p.suffix in ('.json','.npz','.npy') and p.is_relative_to(results)
               and p.name not in ('raw_actions.npz','physical_channels.npy','point_fit_indices.npy','fit_indices.npy','raw_2024_boundary.npz')
               and not p.name.endswith('forecaster.joblib'))
           or (p.name=='protocol.json' and p.is_relative_to(args.root/'experiments')))]
    # No annual ZIP, physical arrays or model pickle is selected by these rules.
    manifest={str(p.relative_to(args.root)):dict(bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(files)}
    with tarfile.open(args.output/'compact_evidence.tar.gz','x:gz') as archive:
        for p in sorted(files):
            archive.add(p,arcname=str(p.relative_to(args.root)))
        payload=json.dumps(manifest,indent=2).encode()
        import io
        info=tarfile.TarInfo('export_manifest.json');info.size=len(payload)
        archive.addfile(info,io.BytesIO(payload))
    packet=args.output/'compact_evidence.tar.gz'
    (args.output/'receipt.json').write_text(json.dumps(dict(bytes=packet.stat().st_size,sha256=sha(packet),members=len(manifest),
        scope='Compact evidence; full physical/action arrays, fit indices and models retained on Metis, no annual SCADA in package'),indent=2))
    print((args.output/'receipt.json').read_text())


if __name__=='__main__':
    main()
