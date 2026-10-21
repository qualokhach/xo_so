import json
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
HISTORY = ROOT / "data" / "history"

def test_history_manifest_matches_partitions():
    manifest = json.loads((HISTORY / "index.json").read_text(encoding="utf-8"))
    count = 0
    seen = set()
    for item in manifest["months"]:
        path = ROOT / item["url"]
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["month"] == item["month"]
        assert data["record_count"] == item["record_count"]
        assert len(data["records"]) == item["record_count"]
        for key, rec in data["records"].items():
            assert key == rec["key"]
            assert rec["date"].startswith(item["month"])
            assert rec["kind"] in {"xsmb", "xsmt", "xsmn", "vietlott"}
            assert rec.get("prizes")
            assert key not in seen
            seen.add(key)
        count += len(data["records"])
    assert count == manifest["record_count"]

def test_no_max3d_plus_fabrication():
    manifest = json.loads((HISTORY / "index.json").read_text(encoding="utf-8"))
    assert manifest["coverage"]["max_3d_plus"]["available"] is False
    for path in HISTORY.glob("*.json"):
        if path.name in {"index.json", "audit.json"}:
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        for rec in data["records"].values():
            product = rec.get("product", "")
            assert product != "MAX 3D+"

def test_lotto_only_last_30_days():
    manifest = json.loads((HISTORY / "index.json").read_text(encoding="utf-8"))
    start = manifest["coverage"]["lotto_5_35"]["retained_from"]
    for path in HISTORY.glob("*.json"):
        if path.name in {"index.json", "audit.json"}:
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        for rec in data["records"].values():
            if rec.get("product_id") == "LOTTO_5_35":
                assert rec["date"] >= start
                assert rec["date"] <= "2026-10-21"

def test_three_digit_prizes_preserve_leading_zeros():
    checked = 0
    for path in HISTORY.glob("*.json"):
        if path.name in {"index.json", "audit.json"}:
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        for rec in data["records"].values():
            if rec.get("product_id") in {"MAX_3D", "MAX_3D_PRO"}:
                for prize in rec["prizes"]:
                    for n in prize["numbers"]:
                        assert isinstance(n, str)
                        assert len(n) == 3 and n.isdigit()
                        checked += 1
    assert checked > 0

def test_month_files_are_separate_from_live_archive():
    assert HISTORY.exists()
    assert not any(HISTORY.glob("*.json")) is False
    # The routine collector uses data/archive; immutable imported history lives under data/history.
    collector = (ROOT / "scripts" / "fetch_results.py").read_text(encoding="utf-8")
    assert 'data/archive/' in collector
    assert "data/history/" not in collector


def test_frontend_loads_history_partition_on_date_selection():
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "data/history/'+month+'.json" in html
    assert "async function loadArchiveMonth(date)" in html
    assert "$('draw-date').addEventListener('change'" in html

def test_scheduled_workflow_does_not_stage_history():
    workflow = (ROOT / ".github" / "workflows" / "update-lottery-results.yml").read_text(encoding="utf-8")
    stage_lines = [line.strip() for line in workflow.splitlines() if "git add" in line]
    assert stage_lines
    assert all("data/history" not in line for line in stage_lines)

def test_frontend_rejects_stations_from_other_regions():
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "const STATIONS_BY_REGION={" in html
    assert "return !!allowed && allowed.has(name);" in html
    # A station must not be shown under another region even if an upstream record's kind is wrong.
    assert "xsmt:new Set(['thuathienhue'" in html
    assert "xsmn:new Set(['hochiminh'" in html
    assert "dongthap" not in html.split("xsmt:new Set(",1)[1].split("]),",1)[0]


def test_imported_traditional_history_has_region_consistent_stations():
    central = {"thuathienhue","hue","kontum","khanhhoa","danang","quangnam","quangngai","binhdinh","phuyen","ninhthuan","daklak","daknong","gialai","quangtri","quangbinh"}
    south = {"hochiminh","tphochiminh","tphcm","saigon","bariavungtau","dongnai","cantho","soctrang","angiang","binhduong","binhphuoc","binhthuan","baclieu","bentre","camau","dongthap","haugiang","kiengiang","longan","tiengiang","travinh","vinhlong","tayninh","vungtau","dalat","lamdong"}
    import unicodedata, re
    def norm(value):
        value=str(value).replace("Đ","D").replace("đ","d")
        value=unicodedata.normalize("NFKD", value).encode("ascii","ignore").decode("ascii").casefold()
        return re.sub(r"[^a-z0-9]+", "", value)
    checked=0
    for path in HISTORY.glob("*.json"):
        if path.name in {"index.json","audit.json"}: continue
        data=json.loads(path.read_text(encoding="utf-8"))
        for rec in data["records"].values():
            if rec.get("kind") not in {"xsmt","xsmn"}: continue
            station=norm(rec.get("station") or rec.get("title"))
            assert station in (central if rec["kind"]=="xsmt" else south), (path.name,rec.get("kind"),rec.get("station"))
            checked+=1
    assert checked > 0
