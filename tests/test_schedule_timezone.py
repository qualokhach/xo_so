from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "update-lottery-results.yml"

def test_schedule_uses_vietnam_timezone_and_expected_window():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert 'timezone: "Asia/Ho_Chi_Minh"' in text
    crons = re.findall(r'cron:\s*"([^"]+)"', text)
    assert crons == ["5,20,35,50 16-18 * * *", "5 19 * * *"]

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
