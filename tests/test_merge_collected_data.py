import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import merge_collected_data as merge


def valid_record(date, draw_no):
    return {
        "kind": "vietlott", "product": "MEGA 6/45", "product_id": "mega645",
        "date": date, "draw_no": str(draw_no),
        "prizes": [{"name": "Bộ số trúng thưởng", "numbers": ["01", "02", "03", "04", "05", "06"]}],
    }


def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")


def test_merge_preserves_local_new_records_and_remote_wins_duplicate(tmp_path, monkeypatch):
    snap = tmp_path / "snapshot"
    target = tmp_path / "target"
    local_old = valid_record("2026-10-20", 1)
    local_new = valid_record("2026-10-22", 2)
    remote_old = {**local_old, "source_id": "remote-locked"}
    dump(snap / "archive" / "2026-10.json", {"schema_version": 3, "records": {"old": local_old, "new": local_new}})
    dump(target / "archive" / "2026-10.json", {"schema_version": 3, "records": {"old": remote_old}})
    dump(snap / "archive-quarantine.json", {"schema_version": 1, "records": {"q1": {"x": 1}}})
    dump(target / "archive-quarantine.json", {"schema_version": 1, "records": {"q0": {"x": 0}}})

    # The actual collector validator requires additional product metadata/prize constraints;
    # use real validation contract by monkeypatching only for this merge-algorithm isolation test.
    monkeypatch.setattr(merge.fetch_results, "record_valid", lambda rec: isinstance(rec, dict) and bool(rec.get("date")))
    monkeypatch.setattr(sys, "argv", ["merge_collected_data.py", "--snapshot", str(snap), "--target", str(target)])
    merge.main()
    got = json.loads((target / "archive" / "2026-10.json").read_text(encoding="utf-8"))["records"]
    assert set(got) == {"old", "new"}
    assert got["old"]["source_id"] == "remote-locked"
    q = json.loads((target / "archive-quarantine.json").read_text(encoding="utf-8"))["records"]
    assert set(q) == {"q0", "q1"}


def test_merge_does_not_add_invalid_local_record(tmp_path, monkeypatch):
    snap = tmp_path / "snapshot"
    target = tmp_path / "target"
    dump(snap / "archive" / "2026-10.json", {"schema_version": 3, "records": {"bad": {"no_date": True}}})
    monkeypatch.setattr(merge.fetch_results, "record_valid", lambda rec: False)
    monkeypatch.setattr(sys, "argv", ["merge_collected_data.py", "--snapshot", str(snap), "--target", str(target)])
    merge.main()
    got = json.loads((target / "archive" / "2026-10.json").read_text(encoding="utf-8"))["records"]
    assert got == {}
