import importlib.util
from pathlib import Path


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
