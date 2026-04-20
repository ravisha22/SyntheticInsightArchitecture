import json
import sys
from pathlib import Path

from webapp import generate_site, run_weekly


def test_generate_html_renders_sections_and_escaping():
    analysis = {
        "analyzed_at": "2025-04-01T12:00:00+00:00",
        "collected_at": "2025-04-01",
        "signal_count": 7,
        "adapter": "mock",
        "chosen_count": 2,
        "root_causes": [
            {
                "target": "security_boundary",
                "severity": "existential",
                "signal_count": 3,
                "rationale": 'Escalates across services <fast>',
            }
        ],
        "stories": [
            {
                "title": 'A <Story>',
                "source": "Reuters World",
                "url": "https://example.com/story",
                "published": "2025-04-01T11:30:00+00:00",
            }
        ],
    }
    ledger = {
        "predictions": [
            {
                "id": "abc123",
                "created_at": "2025-04-01",
                "root_cause": "security_boundary",
                "severity": "existential",
                "status": "validated",
                "validation_notes": "Confirmed by later evidence",
                "rationale": "fallback",
            }
        ]
    }

    output = generate_site.generate_html(analysis, ledger)

    assert "SIA — Systemic Intelligence Analysis" in output
    assert "Latest Analysis" in output
    assert "Prediction Ledger" in output
    assert "Powered by SIA" in output
    assert "&lt;Story&gt;" in output
    assert "status-pill validated" in output
    assert "Escalates across services &lt;fast&gt;" in output


def test_load_data_defaults_when_files_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(generate_site, "DATA_DIR", tmp_path)
    analysis, ledger = generate_site.load_data()

    assert analysis is None
    assert ledger == {"predictions": []}


def test_run_step_uses_resolved_script(monkeypatch):
    calls = []

    class Result:
        returncode = 0

    def fake_run(cmd, cwd):
        calls.append((cmd, cwd))
        return Result()

    monkeypatch.setattr(run_weekly.subprocess, "run", fake_run)
    run_weekly.run_step("Collect stories", "webapp/collect_stories.py")

    assert calls
    command, cwd = calls[0]
    assert command[0] == sys.executable
    assert Path(command[1]).name == "collect_stories.py"
    assert Path(cwd) == run_weekly.WEBAPP_DIR.parent


def test_generate_site_main_writes_index(tmp_path, monkeypatch):
    analysis = {
        "analyzed_at": "2025-04-01T12:00:00+00:00",
        "collected_at": "2025-04-01",
        "signal_count": 1,
        "adapter": "mock",
        "chosen_count": 0,
        "root_causes": [],
        "stories": [],
    }
    ledger = {"predictions": []}

    data_dir = tmp_path / "data"
    static_dir = tmp_path / "static"
    data_dir.mkdir()
    static_dir.mkdir()
    (data_dir / "latest_analysis.json").write_text(json.dumps(analysis), encoding="utf-8")
    (data_dir / "prediction_ledger.json").write_text(json.dumps(ledger), encoding="utf-8")

    monkeypatch.setattr(generate_site, "DATA_DIR", data_dir)
    monkeypatch.setattr(generate_site, "STATIC_DIR", static_dir)

    generate_site.main()

    index_path = static_dir / "index.html"
    assert index_path.exists()
    assert "No predictions have been logged yet." in index_path.read_text(encoding="utf-8")
