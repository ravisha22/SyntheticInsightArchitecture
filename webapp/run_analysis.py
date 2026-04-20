"""Run SIA analysis on collected news stories and generate predictions."""
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.adapters.mock import MockAdapter
from src.schema import init_db
from src.services.analysis_pipeline import AnalysisPipeline

DATA_DIR = Path(__file__).parent / "data"


def load_signals() -> dict:
    """Load the latest collected stories."""
    latest = DATA_DIR / "latest_stories.json"
    if not latest.exists():
        print("No stories found. Run collect_stories.py first.")
        sys.exit(1)
    return json.loads(latest.read_text(encoding="utf-8"))


def build_adapter():
    """Build the best available adapter."""
    api_key = os.environ.get("SIA_API_KEY", "")
    if api_key:
        from src.adapters.openai_api import OpenAIAdapter

        model = os.environ.get("SIA_MODEL", "gpt-4o")
        base_url = os.environ.get("SIA_BASE_URL", "https://api.openai.com/v1")
        print(f"Using OpenAI adapter: {model} @ {base_url}")
        return OpenAIAdapter({"api_key": api_key, "model": model, "base_url": base_url})
    print("Using MockAdapter (set SIA_API_KEY for real LLM analysis)")
    return MockAdapter(seed=42)


def build_predictions(report: dict, collected_at: str) -> list[dict]:
    """Extract structured predictions from the analysis report."""
    predictions = []
    chosen = report.get("prioritization", {}).get("chosen", [])
    for choice in chosen:
        target = choice.get("target", "Unknown")
        pred_id = hashlib.sha256(f"{collected_at}:{target}".encode()).hexdigest()[:12]
        predictions.append(
            {
                "id": pred_id,
                "created_at": collected_at,
                "root_cause": target,
                "severity": choice.get("tier", "unknown"),
                "signal_count": len(choice.get("issues_resolved", [])),
                "rationale": choice.get("why", ""),
                "status": "open",
                "validation_notes": "",
                "validated_at": None,
            }
        )
    return predictions


def _merge_predictions(existing: list[dict], new_predictions: list[dict]) -> list[dict]:
    by_id = {item.get("id"): item for item in existing if item.get("id")}
    for prediction in new_predictions:
        existing_item = by_id.get(prediction["id"])
        if existing_item:
            existing_item.update(
                {
                    "created_at": prediction["created_at"],
                    "root_cause": prediction["root_cause"],
                    "severity": prediction["severity"],
                    "signal_count": prediction["signal_count"],
                    "rationale": prediction["rationale"],
                }
            )
        else:
            by_id[prediction["id"]] = prediction
    return sorted(by_id.values(), key=lambda item: (item.get("created_at", ""), item.get("id", "")), reverse=True)


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    data = load_signals()
    signals = data["signals"]
    collected_at = data["collected_at"]

    print(f"Analyzing {len(signals)} signals from {collected_at}...")

    db_path = str(DATA_DIR / "analysis.db")
    adapter = build_adapter()

    pipeline_signals = []
    for sig in signals:
        pipeline_signals.append(
            {
                "signal_id": f"{sig['source']}:{sig['number']}",
                "signal_type": sig.get("signal_type", "other"),
                "source": sig.get("source", "news"),
                "title": sig["title"],
                "body": sig.get("body", ""),
                "tags": sig.get("labels", []),
                "metadata": {"url": sig.get("url", ""), "published": sig.get("published", "")},
            }
        )

    conn = init_db(db_path)
    try:
        pipeline = AnalysisPipeline(conn, adapter, config={})
        report = pipeline.run_full_pipeline(pipeline_signals, budget=5)
    finally:
        conn.close()

    predictions = build_predictions(report, collected_at)
    analysis = {
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "collected_at": collected_at,
        "signal_count": len(signals),
        "adapter": "openai" if os.environ.get("SIA_API_KEY") else "mock",
        "clusters_found": report["summary"]["clusters_found"],
        "chosen_count": report["summary"]["chosen_count"],
        "root_causes": [
            {
                "target": cluster.get("target", ""),
                "severity": cluster.get("tier", ""),
                "signal_count": len(cluster.get("issues_resolved", [])),
                "rationale": cluster.get("why", ""),
            }
            for cluster in report.get("prioritization", {}).get("chosen", [])
        ],
        "predictions": predictions,
        "stories": data.get("stories", []),
    }

    outfile = DATA_DIR / f"analysis_{collected_at}.json"
    outfile.write_text(json.dumps(analysis, indent=2, ensure_ascii=False), encoding="utf-8")

    latest = DATA_DIR / "latest_analysis.json"
    latest.write_text(json.dumps(analysis, indent=2, ensure_ascii=False), encoding="utf-8")

    ledger_path = DATA_DIR / "prediction_ledger.json"
    ledger = (
        json.loads(ledger_path.read_text(encoding="utf-8"))
        if ledger_path.exists()
        else {"predictions": []}
    )
    ledger["predictions"] = _merge_predictions(ledger.get("predictions", []), predictions)
    ledger["last_updated"] = datetime.now(timezone.utc).isoformat()
    ledger_path.write_text(json.dumps(ledger, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\nAnalysis complete:")
    print(f"  Clusters found: {report['summary']['clusters_found']}")
    print(f"  Root causes prioritized: {report['summary']['chosen_count']}")
    print(f"  Predictions created: {len(predictions)}")
    print(f"  Saved to: {outfile}")
    print(f"  Ledger updated: {ledger_path}")


if __name__ == "__main__":
    main()
