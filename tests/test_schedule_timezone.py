from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "update-lottery-results.yml"

def test_schedule_uses_utc_cron_equal_to_vietnam_16_to_19_every_15_minutes():
    # GitHub evaluates schedule cron in UTC. Vietnam = UTC+7 (no DST).
    # 16:00-19:00 Vietnam time == 09:00-12:00 UTC. Off-peak minutes
    # (:07/:22/:37/:52) are used so GitHub is less likely to delay/drop runs.
    from datetime import datetime, timedelta, timezone
    from zoneinfo import ZoneInfo

    text = WORKFLOW.read_text(encoding="utf-8")
    assert "timezone:" not in re.sub(r"#.*", "", text).split("jobs:")[0]
    crons = re.findall(r'cron:\s*"([^"]+)"', text)
    assert crons == ["7,22,37,52 9-11 * * *"]

    utc_runs = [(h, m) for h in (9, 10, 11) for m in (7, 22, 37, 52)]
    vn = ZoneInfo("Asia/Ho_Chi_Minh")
    local = [
        datetime(2026, 11, 5, h, m, tzinfo=timezone.utc).astimezone(vn)
        for h, m in utc_runs
    ]
    assert len(local) == 12
    assert local[0].strftime("%H:%M") == "16:07"
    assert local[-1].strftime("%H:%M") == "18:52"
    # every run is inside 16:00-19:00 Vietnam time, exactly 15 minutes apart
    for t in local:
        assert 16 <= t.hour <= 18
    for prev, nxt in zip(local, local[1:]):
        assert nxt - prev == timedelta(minutes=15)

def test_scheduled_runs_have_midnight_safety_guard_and_manual_runs_are_allowed():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "id: schedule_guard" in text
    assert 'event != "schedule"' in text
    assert "time(16, 0)" in text and "time(19, 30)" in text
    assert "steps.schedule_guard.outputs.allowed == 'true'" in text

def test_schedule_diagnostics_include_cron_and_vietnam_local_time():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "EVENT_SCHEDULE: ${{ github.event.schedule }}" in text
    assert 'ZoneInfo("Asia/Ho_Chi_Minh")' in text
    assert "Vietnam local time" in text
