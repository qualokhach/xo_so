from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "update-lottery-results.yml"

def test_schedule_uses_utc_cron_equal_to_vietnam_16_to_19_every_15_minutes():
    # GitHub evaluates schedule cron in UTC. Vietnam = UTC+7 (no DST).
    # 16:00-19:00 Vietnam time, every 15 minutes, == 09:00-12:00 UTC.
    from datetime import datetime, timedelta, timezone
    from zoneinfo import ZoneInfo

    text = WORKFLOW.read_text(encoding="utf-8")
    assert "timezone:" not in re.sub(r"#.*", "", text).split("jobs:")[0]
    crons = re.findall(r'cron:\s*"([^"]+)"', text)
    assert crons == ["0,15,30,45 9-11 * * *", "0 12 * * *"]

    # Expand the cron entries and convert to Vietnam local time.
    utc_runs = [(h, m) for h in (9, 10, 11) for m in (0, 15, 30, 45)] + [(12, 0)]
    vn = ZoneInfo("Asia/Ho_Chi_Minh")
    local = [
        datetime(2026, 11, 5, h, m, tzinfo=timezone.utc).astimezone(vn).strftime("%H:%M")
        for h, m in utc_runs
    ]
    expected = []
    t = datetime(2026, 11, 5, 16, 0)
    while t <= datetime(2026, 11, 5, 19, 0):
        expected.append(t.strftime("%H:%M"))
        t += timedelta(minutes=15)
    assert local == expected
    assert len(local) == 13

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
