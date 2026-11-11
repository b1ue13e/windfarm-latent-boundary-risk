"""Opaque download with published checksum; never opens the measurement ZIP."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time
import urllib.request


def main():
    directory = Path(__file__).resolve().parent
    target = directory / '2026.zip'
    partial = directory / '2026.zip.partial'
    receipt = directory / 'acquisition_receipt.json'
    if receipt.exists():
        raise FileExistsError('Prior acquisition receipt is immutable')
    record = dict(start_utc=datetime.now(timezone.utc).isoformat(),
                  url='https://zenodo.org/api/records/22662930/files/2026.zip/content',
                  expected_bytes=553982874, expected_md5='42a2264187912ca63214bacfbc8d4905',
                  archive_listed=False, measurements_read=False, argv=sys.argv)
    try:
        if target.exists() or partial.exists():
            raise FileExistsError('Archive or partial already exists; preserve it for inspection')
        sha, md5, size = hashlib.sha256(), hashlib.md5(), 0
        request = urllib.request.Request(record['url'], headers={'User-Agent':'research-reproducibility/1.0'})
        with urllib.request.urlopen(request, timeout=45) as source, partial.open('xb') as f:
            while True:
                block = source.read(1024 * 1024)
                if not block:
                    break
                f.write(block)
                sha.update(block)
                md5.update(block)
                size += len(block)
        if size != record['expected_bytes'] or md5.hexdigest() != record['expected_md5']:
            raise ValueError('Opaque archive differs from published identity')
        partial.rename(target)
        record.update(status='SEALED_ACQUISITION_VERIFIED', bytes=size, md5=md5.hexdigest(), sha256=sha.hexdigest())
    except BaseException as exc:
        record.update(status='FAILED_PRESERVED', error=repr(exc))
        raise
    finally:
        record['finished_utc'] = datetime.now(timezone.utc).isoformat()
        with receipt.open('x') as f:
            json.dump(record, f, indent=2)
        print(json.dumps(record), flush=True)


if __name__ == '__main__':
    main()
