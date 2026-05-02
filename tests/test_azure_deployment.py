import importlib.util
from pathlib import Path
from types import SimpleNamespace


REPO_ROOT = Path(__file__).resolve().parents[1]


def load_module(relative_path: str, module_name: str):
    module_path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


daily_run = load_module("azure/daily_run.py", "azure_daily_run")
auth_middleware = load_module("azure/auth_middleware.py", "azure_auth_middleware")


def test_compute_maturity_date_uses_upper_bound():
    assert daily_run.compute_maturity_date("2026-04-20", "6-8 weeks") == "2026-06-15"
    assert daily_run.compute_maturity_date("2026-04-20", "3 months") == "2026-07-19"


def test_merge_predictions_adds_ids_and_schedule():
    merged = daily_run.merge_predictions(
        [],
        [
            {
                "root_cause": "supply fragility",
                "prediction": "Delays worsen",
                "timeline": "2-4 weeks",
                "falsification": "Lead times improve",
                "severity": "high",
            }
        ],
        "2026-04-20",
    )

    assert len(merged) == 1
    assert merged[0]["id"]
    assert merged[0]["maturity_date"] == "2026-05-18"
    assert merged[0]["status"] == "open"


def test_build_prediction_schedule_orders_entries():
    schedule = daily_run.build_prediction_schedule(
        {
            "predictions": [
                {"id": "b", "root_cause": "second", "status": "open", "maturity_date": "2026-06-01"},
                {"id": "a", "root_cause": "first", "status": "open", "maturity_date": "2026-05-01"},
            ]
        }
    )

    assert [item["id"] for item in schedule["schedule"]] == ["a", "b"]


def test_generate_daily_password_and_magic_link(tmp_path):
    auth = auth_middleware.SIAAuth(str(tmp_path / "auth_state.json"))
    password = auth.generate_daily_password()
    token_link = auth.generate_magic_link("https://example.com/chat")
    token = token_link.split("token=")[1]

    assert len(password) == 24
    assert all(char in daily_run.SPECIAL_CHARS for char in password)
    assert auth.validate_magic_link(token) is True
    assert auth.validate_magic_link(token) is False


def test_build_legacy_root_causes_preserves_chat_page_fields():
    causes = daily_run.build_legacy_root_causes(
        [
            {
                "signal_id": "alpha",
                "title": "Signal Alpha",
                "category": "contested_priority",
                "priority_score": 1.2,
                "contest_score": 0.8,
                "contestedness": 0.4,
                "sign_agreement": 0.4,
                "polarity": -1,
                "top_clusters": {"security": 1.0},
            }
        ]
    )

    assert causes[0]["target"] == "Signal Alpha"
    assert causes[0]["title"] == "Signal Alpha"
    assert causes[0]["name"] == "Signal Alpha"
    assert causes[0]["priority_score"] == 1.2
    assert causes[0]["contestedness"] == 0.4


def test_generate_narrative_uses_structured_engine_context(monkeypatch):
    captured = {}

    def fake_chat(messages, **_kwargs):
        captured["messages"] = messages
        return "Narrative"

    monkeypatch.setattr(daily_run, "_chat_completion", fake_chat)

    result = daily_run.generate_narrative(
        [{"title": "Story A", "source": "Reuters", "published": "2026-01-01"}],
        [
            {
                "title": "Signal Alpha",
                "category": "contested_priority",
                "priority_score": 1.1,
                "contest_score": 0.7,
                "contestedness": 0.5,
                "sign_agreement": 0.45,
                "polarity": -1,
                "top_clusters": {"security": 1.0},
                "bottom_clusters": {"equity": -0.2},
            }
        ],
        {"label": "cautious", "score": 0.2, "emoji": "🟡"},
    )

    assert result == "Narrative"
    prompt = captured["messages"][1]["content"]
    assert '"selected_priorities"' in prompt
    assert '"portfolio_mood"' in prompt
    assert '"supporting_signals"' in prompt
    assert '"contestedness": 0.5' in prompt
    assert '"title": "Story A"' in prompt


def test_build_email_subject_uses_mood_emoji_and_all_category_counts():
    subject = daily_run.build_email_subject(
        {
            "mood": {"label": "transitional", "score": 0.1},
            "selected_priorities": [
                {"category": "convergent_priority"},
                {"category": "contested_priority"},
                {"category": "niche_concern"},
                {"category": "background_noise"},
            ],
        }
    )

    assert "🟠" in subject
    assert "1 convergent" in subject
    assert "1 contested" in subject
    assert "1 niche" in subject
    assert "1 noise" in subject


def test_compute_delta_normalizes_legacy_root_causes_and_mood():
    delta = daily_run.compute_delta(
        {
            "stories": [{"title": "Story A"}],
            "priorities": [{"title": "Signal Alpha", "category": "contested_priority", "priority_score": 1.1}],
            "mood": {"label": "concerning", "score": -0.4},
        },
        {
            "stories": [{"title": "Story B"}],
            "root_causes": [{"target": "Signal Alpha", "severity": "high", "priority_score": 0.6}],
            "mood": "cautious",
        },
    )

    assert delta["is_first_run"] is False
    assert delta["category_changes"] == ["Signal Alpha: convergent_priority → contested_priority"]
    assert delta["priority_score_changes"] == ["Signal Alpha: 0.60 → 1.10"]
    assert "cautious (0.00) to concerning (-0.40)" in delta["mood_shift"]


def test_build_dashboard_html_keeps_contestedness_separate_from_priority_and_direction():
    html = daily_run.build_dashboard_html(
        {
            "report_date": "2026-01-01",
            "stories": [],
            "priorities": [
                {
                    "title": "Signal Alpha",
                    "priority_score": 1.2,
                    "contest_score": 0.9,
                    "contestedness": 0.4,
                    "category": "contested_priority",
                    "sign_agreement": 0.45,
                    "polarity": -1,
                    "top_clusters": {"security": 1.0},
                    "bottom_clusters": {"equity": -0.3},
                }
            ],
            "narrative": "Narrative",
            "mood": {"label": "cautious", "score": 0.1, "emoji": "🟡"},
            "delta": {"is_first_run": True},
        },
        {"predictions": []},
        "",
        "",
        {"stories": []},
    )

    assert "<th>Direction</th>" in html
    assert ">0.40</td>" in html
    assert ">↔ mixed</td>" in html


def test_run_core_analysis_falls_back_and_marks_degraded(monkeypatch):
    class RaisingClassifier:
        def __init__(self, *_args, **_kwargs):
            pass

        def classify(self, _signal):
            raise RuntimeError("429")

    class LocalMockClassifier:
        def classify(self, signal):
            return {
                "signal_id": signal["signal_id"],
                "title": signal["title"],
                "dimensions": {},
                "meta": {},
            }

    class FakeEngine:
        def __init__(self, *_args, **_kwargs):
            pass

        def prioritize(self, classified_signals, budget=10):
            assert budget == 10
            assert classified_signals[0]["classifier_fallback"] is True
            return SimpleNamespace(
                ranked_signals=[
                    {
                        "signal_id": classified_signals[0]["signal_id"],
                        "title": classified_signals[0]["title"],
                        "category": "background_noise",
                        "priority_score": 0.0,
                        "contest_score": 0.0,
                        "contestedness": 0.0,
                        "sign_agreement": 1.0,
                        "polarity": 0,
                        "central_tendency": 0.0,
                        "impact": 0.0,
                        "cluster_means": {},
                    }
                ],
                selected_signals=[],
                portfolio_mood={"label": "cautious", "score": 0.0},
            )

    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "gpt")
    monkeypatch.setenv("AZURE_OPENAI_KEY", "secret")
    monkeypatch.setattr(daily_run, "LLMClassifier", RaisingClassifier)
    monkeypatch.setattr(daily_run, "MockClassifier", LocalMockClassifier)
    monkeypatch.setattr(daily_run, "PrioritizationEngine", FakeEngine)
    monkeypatch.setattr(daily_run, "load_ensemble", lambda _path: object())
    monkeypatch.setattr(daily_run, "load_domain_profile", lambda _domain: {})

    report = daily_run.run_core_analysis(
        [{"title": "Signal Alpha", "body": "Body", "url": "https://example.com/story", "source": "Reuters"}]
    )

    assert report["priorities"][0]["classifier_fallback"] is True
    assert report["engine_health"]["fallback_count"] == 1
    assert report["engine_health"]["non_noise_count"] == 0
    assert report["engine_health"]["degraded"] is True


def test_compute_delta_uses_signal_id_for_stable_priority_keys_and_structural_shifts():
    delta = daily_run.compute_delta(
        {
            "stories": [{"title": "Story A"}],
            "priorities": [
                {
                    "signal_id": "https://example.com/story?utm_source=today",
                    "title": "Signal Alpha updated headline",
                    "category": "contested_priority",
                    "priority_score": 1.1,
                }
            ],
            "mood": {"label": "concerning", "score": -0.4},
        },
        {
            "stories": [{"title": "Story B"}],
            "priorities": [
                {
                    "signal_id": "https://example.com/story?utm_source=yesterday",
                    "title": "Signal Alpha original headline",
                    "category": "convergent_priority",
                    "priority_score": 0.6,
                }
            ],
            "mood": {"label": "cautious", "score": 0.0},
        },
    )

    assert delta["new_convergent"] == []
    assert delta["removed_priorities"] == []
    assert delta["category_changes"] == ["Signal Alpha updated headline: convergent_priority → contested_priority"]
    assert delta["priority_score_changes"] == ["Signal Alpha updated headline: 0.60 → 1.10"]
    assert "Mood shifted: cautious → concerning" in delta["structural_shifts"]
    assert "convergent_priority: 1 → 0" in delta["structural_shifts"]
    assert "contested_priority: 0 → 1" in delta["structural_shifts"]


def test_degraded_engine_banner_renders_in_email_and_dashboard():
    report = {
        "report_date": "2026-01-01",
        "stories": [],
        "priorities": [],
        "narrative": "Narrative",
        "mood": {"label": "cautious", "score": 0.1, "emoji": "🟡"},
        "delta": {"is_first_run": True, "structural_shifts": []},
        "engine_health": {"degraded": True, "fallback_count": 3, "total_count": 4},
    }

    email_html = daily_run.build_email_html(report, {"predictions": []}, [], "pw", "", "", {"stories": []})
    dashboard_html = daily_run.build_dashboard_html(report, {"predictions": []}, "", "", {"stories": []})

    assert "⚠ Engine quality degraded" in email_html
    assert "3/4 signals used fallback classifier" in email_html
    assert "⚠ Engine quality degraded" in dashboard_html
    assert "3/4 signals used fallback classifier" in dashboard_html
