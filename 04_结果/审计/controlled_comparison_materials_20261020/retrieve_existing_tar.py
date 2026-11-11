"""Read existing manifest-bound M files through an SSH tar stream, without remote writes."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import shlex
import subprocess
import tarfile
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parent
WORKSPACE = BASE.parent.parent


def sha(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def main():
    plan = json.loads((BASE / "TRANSFER_PLAN.json").read_text())
    for group in ["M_controls", "M_pilot"]:
        group_rows = [row for row in plan["files"] if row["group"] == group]
        for attempt in range(1, 4):
            pending = []
            for row in group_rows:
                rel = PurePosixPath(row["relative"])
                if rel.is_absolute() or ".." in rel.parts:
                    raise ValueError("Unsafe manifest path")
                target = BASE / "recovered" / group / Path(*rel.parts)
                if target.exists():
                    if target.stat().st_size != row["bytes"] or sha(target) != row["sha256"]:
                        raise ValueError("Existing target identity failed")
                else:
                    pending.append(row)
            if not pending:
                break
            expected = {row["relative"]: row for row in pending}
            command = "tar -cf - -C " + shlex.quote(pending[0]["remote_root"]) + " -- "
            command += " ".join(shlex.quote(row["relative"]) for row in pending)
            proc = subprocess.Popen(["ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
                                     "-o", "ConnectTimeout=15", "metis", command],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            received = 0
            try:
                with tarfile.open(fileobj=proc.stdout, mode="r|") as archive:
                    for member in archive:
                        if not member.isfile() or member.name not in expected:
                            raise ValueError("Unexpected streamed member")
                        row = expected.pop(member.name)
                        if member.size != row["bytes"]:
                            raise ValueError("Streamed size differs from historical manifest")
                        target = BASE / "recovered" / group / Path(*PurePosixPath(member.name).parts)
                        if not target.resolve().is_relative_to((BASE / "recovered").resolve()):
                            raise ValueError("Output path escaped recovery root")
                        target.parent.mkdir(parents=True, exist_ok=True)
                        partial = target.with_name(target.name + ".part")
                        digest = hashlib.sha256()
                        with archive.extractfile(member) as source, partial.open("wb") as output:
                            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                                digest.update(chunk)
                                output.write(chunk)
                        if digest.hexdigest() != row["sha256"] or partial.stat().st_size != row["bytes"]:
                            raise ValueError("Streamed bytes differ from historical manifest")
                        partial.rename(target)
                        record = dict(row, status="COPIED_EXISTING_BYTES_VERIFIED", transport="read-only SSH tar stream",
                                      local=target.relative_to(WORKSPACE).as_posix(),
                                      checked_utc=datetime.now(timezone.utc).isoformat())
                        with (BASE / ("TRANSFER_" + group + ".jsonl")).open("a", encoding="utf-8") as handle:
                            handle.write(json.dumps(record) + "\n")
                        received += 1
                        if received % 20 == 0 or received == len(pending):
                            print(json.dumps({"group": group, "attempt": attempt,
                                              "new_verified_files": received, "pending_at_start": len(pending)}), flush=True)
                error = proc.stderr.read().decode(errors="replace")
                if proc.wait() != 0 or expected:
                    raise OSError("Incomplete SSH stream: " + error[:300])
            except (OSError, EOFError, tarfile.TarError) as exc:
                proc.kill()
                proc.wait()
                print(json.dumps({"group": group, "attempt": attempt, "transport_retry": type(exc).__name__,
                                  "verified_files_retained": received}), flush=True)
                if attempt == 3:
                    raise
        else:
            raise OSError("Incomplete group")
    print("M existing-file stream transfer finished; no research executed.", flush=True)


if __name__ == "__main__":
    main()
