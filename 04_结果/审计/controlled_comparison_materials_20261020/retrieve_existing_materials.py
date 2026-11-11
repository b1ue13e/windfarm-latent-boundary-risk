"""Copy manifest-bound existing files via read-only SFTP; never execute research."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import threading

import paramiko

BASE = Path(__file__).resolve().parent
WORKSPACE = BASE.parent.parent
LOCK = threading.Lock()


def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def transfer_group(group, rows):
    config = paramiko.SSHConfig()
    with (Path.home() / ".ssh/config").open() as handle:
        config.parse(handle)
    host = config.lookup("metis")
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.load_host_keys(str(Path.home() / ".ssh/known_hosts"))
    client.set_missing_host_key_policy(paramiko.RejectPolicy())
    client.connect(host["hostname"], port=int(host.get("port", 22)),
                   username=host["user"], key_filename=host.get("identityfile"),
                   allow_agent=False, look_for_keys=False, timeout=20)
    sftp = paramiko.SFTPClient.from_transport(client.get_transport(),
                                             window_size=16 * 1024 * 1024,
                                             max_packet_size=256 * 1024)
    log = BASE / ("TRANSFER_" + group + ".jsonl")
    completed = 0
    try:
        for row in rows:
            relative = PurePosixPath(row["relative"])
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError("Unsafe manifest-relative path")
            target = BASE / "recovered" / group / Path(*relative.parts)
            if not target.resolve().is_relative_to((BASE / "recovered").resolve()):
                raise ValueError("Output escaped recovery directory")
            target.parent.mkdir(parents=True, exist_ok=True)
            remote = row["remote_root"].rstrip("/") + "/" + relative.as_posix()
            if target.exists():
                if target.stat().st_size != row["bytes"] or digest(target) != row["sha256"]:
                    raise ValueError("Existing local target differs: " + str(relative))
                status = "ALREADY_VERIFIED"
            else:
                if sftp.stat(remote).st_size != row["bytes"]:
                    raise ValueError("Remote size differs: " + str(relative))
                partial = target.with_name(target.name + ".part")
                if partial.exists():
                    raise ValueError("Partial transfer retained; no silent overwrite: " + str(partial))
                sftp.get(remote, str(partial), prefetch=True,
                         max_concurrent_prefetch_requests=32)
                if partial.stat().st_size != row["bytes"] or digest(partial) != row["sha256"]:
                    raise ValueError("Downloaded bytes failed historical identity: " + str(relative))
                partial.rename(target)
                status = "COPIED_EXISTING_BYTES_VERIFIED"
            result = dict(row, status=status,
                          local=target.relative_to(WORKSPACE).as_posix(),
                          checked_utc=datetime.now(timezone.utc).isoformat())
            with LOCK:
                with log.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(result) + "\n")
            completed += 1
            if completed % 20 == 0 or completed == len(rows):
                print(json.dumps({"group": group, "verified_files": completed,
                                  "total_files": len(rows)}), flush=True)
    finally:
        sftp.close()
        client.close()
    return {"group": group, "verified_files": completed,
            "bytes": sum(row["bytes"] for row in rows)}


def main():
    plan = json.loads((BASE / "TRANSFER_PLAN.json").read_text(encoding="utf-8"))
    groups = {}
    for row in plan["files"]:
        groups.setdefault(row["group"], []).append(row)
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(transfer_group, key, rows)
                   for key, rows in groups.items()]
        results = [future.result() for future in futures]
    (BASE / "TRANSFER_COMPLETE.json").write_text(json.dumps({
        "status": "ALL_SELECTED_EXISTING_FILES_COPIED_AND_HISTORICAL_SHA256_VERIFIED",
        "groups": results, "new_measurements_or_research_execution": False
    }, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results), flush=True)


if __name__ == "__main__":
    main()
