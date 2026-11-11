"""Refresh an explicit safe-payload inventory after author-approved packaging.

This is not evidence generation or public release. Refreshing a manifest cannot
authenticate the provenance of changed material; run verify_package.py afterward.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

HERE=Path(__file__).resolve().parent
TOP_FILES={"README.md","FIELD_GUIDE.md","PUBLICATION_GAPS.md","PROVENANCE.json",
           "verify_package.py","test_package.py","refresh_manifest.py"}
DIRECTORIES={"data":{ ".json",".csv"},"protocol":{ ".json"},"csv":{ ".csv"},"figure_data":{ ".json",".csv"},
             "figures":{ ".pdf",".png",".svg"},"documents":{ ".pdf",".md",".tex",".bib",".csl"},
             "source_static":{ ".py"}}
EXCLUDE_DIRS={"__pycache__",".pytest_cache","generated_reports","reports"}
EXCLUDE_FILES={"MANIFEST.json","PORTABILITY_CHECK.json","verification_report.json","report.json"}


def safe_payload(root):
    result={}
    for path in sorted(root.rglob("*")):
        relative=path.relative_to(root)
        if any(part in EXCLUDE_DIRS for part in relative.parts) or path.name in EXCLUDE_FILES:
            continue
        if path.is_symlink():
            raise ValueError(f"Symlinks cannot enter the portable package: {relative.as_posix()}")
        if not path.is_file():
            continue
        if not path.resolve().is_relative_to(root.resolve()):
            raise ValueError("Payload escapes package directory")
        allowed=(len(relative.parts)==1 and path.name in TOP_FILES)or(
            len(relative.parts)>1 and relative.parts[0]in DIRECTORIES and path.suffix.lower()in DIRECTORIES[relative.parts[0]])
        if not allowed:
            raise ValueError(f"Unapproved payload type or location: {relative.as_posix()}")
        data=path.read_bytes()
        # Scan both textual and binary payloads for common private deployment strings.
        text=data.decode("utf-8",errors="ignore")
        personal_windows=r"(?i)[a-z]:[/\\](?:Users|\u8bba\u65873)[/\\]"
        private_cluster=r"/(?:ls"+r"tr|home)/[^\s\"']+"
        inline_credential=r"https?://[^\s/]+:[^\s/]+@"
        host_identifier=r"\bc"+r"n\d{1,4}\b"
        for name,pattern in [("personal Windows path",personal_windows),("private cluster path",private_cluster),
                             ("inline credentials",inline_credential),("cluster host identifier",host_identifier)]:
            if re.search(pattern,text):
                raise ValueError(f"Sensitive {name} found in {relative.as_posix()}")
        result[relative.as_posix()]={"bytes":len(data),"sha256":hashlib.sha256(data).hexdigest()}
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check",action="store_true",help="Compare safe inventory with the saved manifest without writing")
    args=parser.parse_args()
    try:
        payload={"schema":2,"status":"LOCAL_PREPUBLICATION_CANDIDATE_NOT_PUBLISHED",
                 "excludes":["MANIFEST.json","bytecode/test caches","generated reports including PORTABILITY_CHECK.json"],
                 "files":safe_payload(HERE)}
        path=HERE/"MANIFEST.json"
        if args.check:
            if json.loads(path.read_text(encoding="utf-8"))!=payload:
                raise ValueError("Manifest differs from current safe payload; inspect changes before refreshing")
        else:
            path.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
        print(json.dumps({"status":"PASS_MANIFEST_CHECK"if args.check else"MANIFEST_REFRESHED",
                          "files":len(payload["files"]),"published":False}));return 0
    except (ValueError,OSError)as error:
        print(json.dumps({"status":"FAIL","error":str(error)}));return 1


if __name__=="__main__":
    sys.exit(main())
