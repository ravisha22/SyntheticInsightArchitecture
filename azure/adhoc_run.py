"""SIA Ad-hoc Analysis — on-demand topic analysis triggered from the chat interface."""

from __future__ import annotations

import base64
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

MODULE_DIR = Path(__file__).resolve().parent
REPO_ROOT = MODULE_DIR.parent
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

try:
    from daily_run import collect_stories
except Exception:  # pragma: no cover - fallback when optional imports fail
    collect_stories = None


LOGGER = logging.getLogger("sia.adhoc")
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
UTC = timezone.utc


def utc_now() -> datetime:
    return datetime.now(UTC)


def collect_topic_stories(topic: str) -> list[dict]:
    """Gather relevant public stories so the ad-hoc run has fresh evidence."""
    if collect_stories is None:
        return []
    try:
        return collect_stories(max_stories=8, topic=topic)
    except Exception as exc:  # pragma: no cover - network variability
        LOGGER.warning("Could not collect supporting stories: %s", exc)
        return []


def build_signal_context(stories: list[dict]) -> str:
    if not stories:
        return "No supporting signals were collected automatically. Analyse the topic using general systemic reasoning."

    lines = []
    for index, story in enumerate(stories, start=1):
        lines.append(
            "\n".join(
                [
                    f"Signal {index}",
                    f"Source: {story.get('source', 'Unknown')}",
                    f"Title: {story.get('title', '')}",
                    f"Published: {story.get('published', '')}",
                    f"URL: {story.get('url', '')}",
                    f"Body: {story.get('body', '')}",
                ]
            )
        )
    return "\n\n".join(lines)


def call_openai(topic: str, stories: list[dict]) -> dict:
    """Call Azure OpenAI to analyse a custom topic."""
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
    key = os.environ.get("AZURE_OPENAI_KEY", "")
    deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
    api_version = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-10-21")

    if not endpoint or not key:
        LOGGER.error("AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_KEY required")
        return {}

    url = f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version={api_version}"
    signal_context = build_signal_context(stories)
    system_prompt = """You are the SIA systemic intelligence analyst. Given a topic and any supporting signals, produce a structured analysis following the SIA methodology:
1. Identify the key signals (what observable evidence exists)
2. Cluster them into systemic root causes
3. Assess severity of each root cause (existential / major / moderate)
4. Prioritise interventions under scarcity
5. Make explicit predictions with timelines and falsification criteria
6. Write a narrative connecting the dots

Respond with JSON:
{
  "topic": "the topic analysed",
  "report_date": "YYYY-MM-DD",
  "narrative": "3-5 paragraph analytical narrative",
  "root_causes": [
    {
      "name": "root cause name",
      "severity": "existential|major|moderate",
      "signals": ["signal 1", "signal 2"],
      "rationale": "why this matters",
      "intervention": "what should be done",
      "prediction": "what happens if unaddressed",
      "timeline": "weeks|months|years",
      "falsification": "what would prove this wrong"
    }
  ],
  "predictions": [
    {
      "root_cause": "name",
      "severity": "level",
      "prediction": "what will happen",
      "timeline": "by when",
      "falsification": "what would disprove this",
      "status": "open"
    }
  ]
}"""

    resp = requests.post(
        url,
        headers={
            "api-key": key,
            "Content-Type": "application/json",
        },
        json={
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"Analyse this topic: {topic}\n\nSupporting signals:\n{signal_context}",
                },
            ],
            "temperature": 0.4,
            "max_tokens": 4096,
            "response_format": {"type": "json_object"},
        },
        timeout=120,
    )

    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]
    return json.loads(content)


def upload_to_github(path: str, content: str) -> None:
    """Push a file to the repo via GitHub API."""
    token = os.environ.get("GITHUB_TOKEN", "")
    repo = os.environ.get("SIA_GITHUB_REPO", "")
    if not token or not repo:
        return

    api_url = f"https://api.github.com/repos/{repo}/contents/{path}"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json"}

    sha = None
    try:
        response = requests.get(api_url, headers=headers, timeout=15)
        if response.status_code == 200:
            sha = response.json().get("sha")
    except requests.RequestException:
        LOGGER.warning("Could not read current GitHub file metadata for %s", path)

    payload = {
        "message": f"chore: ad-hoc analysis {utc_now().strftime('%Y-%m-%d %H:%M')}",
        "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
        "branch": "main",
    }
    if sha:
        payload["sha"] = sha

    response = requests.put(api_url, headers=headers, json=payload, timeout=30)
    response.raise_for_status()


def write_output(content: str) -> Path:
    """Persist the latest ad-hoc result for GitHub Pages."""
    output_path = REPO_ROOT / "docs" / "adhoc.json"
    output_path.write_text(content, encoding="utf-8")
    return output_path


def main() -> None:
    topic = os.environ.get("SIA_ADHOC_TOPIC", "").strip()
    if not topic:
        LOGGER.error("SIA_ADHOC_TOPIC not set")
        raise SystemExit(1)

    LOGGER.info("Running ad-hoc analysis on: %s", topic)
    stories = collect_topic_stories(topic)
    result = call_openai(topic, stories)

    if not result:
        LOGGER.error("Analysis failed")
        raise SystemExit(1)

    timestamp = utc_now()
    result["topic"] = result.get("topic") or topic
    result["report_date"] = result.get("report_date") or timestamp.date().isoformat()
    result["analyzed_at"] = timestamp.isoformat()
    result["type"] = "adhoc"
    result["signal_count"] = len(stories)
    if stories:
        result["stories"] = stories

    output = json.dumps(result, indent=2, ensure_ascii=False)
    output_path = write_output(output)
    LOGGER.info("Results written to %s", output_path)

    upload_to_github("docs/adhoc.json", output)
    LOGGER.info("Results pushed to docs/adhoc.json")

    print(json.dumps({"topic": topic, "root_causes": len(result.get("root_causes", []))}, indent=2))


if __name__ == "__main__":
    main()
