#!/usr/bin/env python3
"""Merge a collected data snapshot into the latest checked-out repository safely.

Remote records win on duplicate keys (immutable/locked history); locally collected
records are preserved when their keys do not exist remotely. Invalid records are
never merged into active partitions. Quarantine records are unioned for audit.
"""
import argparse
import json
import os
from pathlib import Path
from datetime import datetime, timezone
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_results


def read_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", required=True, help="Directory containing the collected data snapshot")
    parser.add_argument("--target", default="data", help="Target data directory in current checkout")
    args = parser.parse_args()
    snapshot = Path(args.snapshot)
    target = Path(args.target)

    # Use the exact validator from the collector used by this workflow.
    added = 0
    kept_remote = 0
    for snap_path in sorted((snapshot / "archive").glob("*.json")):
        rel = snap_path.relative_to(snapshot)
        target_path = target / rel
        local_obj = read_json(snap_path, {})
        remote_obj = read_json(target_path, {"schema_version": 3, "records": {}})
        local_records = local_obj.get("records", {}) if isinstance(local_obj, dict) else {}
        remote_records = remote_obj.get("records", {}) if isinstance(remote_obj, dict) else {}
        if not isinstance(local_records, dict): local_records = {}
        if not isinstance(remote_records, dict): remote_records = {}
        merged = dict(remote_records)
        for key, rec in local_records.items():
            if key in merged:
                kept_remote += 1
                continue
            if isinstance(rec, dict) and fetch_results.record_valid(rec):
                merged[key] = rec
                added += 1
        payload = dict(remote_obj) if isinstance(remote_obj, dict) else {"schema_version": 3}
        payload["schema_version"] = 3
        payload["updated_at_vietnam"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        payload["records"] = dict(sorted(merged.items(), key=lambda kv: (kv[1].get("date", ""), kv[0]), reverse=True))
        write_json(target_path, payload)

    # Union quarantine entries. Remote entries win on key collisions to avoid rewriting audit history.
    snap_q = read_json(snapshot / "archive-quarantine.json", {"schema_version": 1, "records": {}})
    targ_q_path = target / "archive-quarantine.json"
    targ_q = read_json(targ_q_path, {"schema_version": 1, "records": {}})
    qremote = targ_q.get("records", {}) if isinstance(targ_q, dict) else {}
    qlocal = snap_q.get("records", {}) if isinstance(snap_q, dict) else {}
    if not isinstance(qremote, dict): qremote = {}
    if not isinstance(qlocal, dict): qlocal = {}
    qmerged = dict(qremote)
    for key, value in qlocal.items(): qmerged.setdefault(key, value)
    if qmerged:
        write_json(targ_q_path, {"schema_version": 1, "records": qmerged})

    print(f"Merged snapshot safely: preserved_new_valid_records={added}; remote_wins_on_duplicate_keys={kept_remote}; quarantine_records={len(qmerged)}")


if __name__ == "__main__":
    main()
