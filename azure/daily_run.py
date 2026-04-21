"""SIA Daily Intelligence — automated analysis, dashboard generation, and delivery."""
import base64
import hashlib
import hmac
import html
import json
import logging
import os
import re
import secrets
import string
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

MODULE_DIR = Path(__file__).resolve().parent
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

from auth_middleware import SIAAuth


LOGGER = logging.getLogger("sia.daily_run")
UTC = timezone.utc
SPECIAL_CHARS = "!@#$%^&*()-_=+[]{}|;:,.<>?/~`"
DEFAULT_OPENAI_API_VERSION = "2024-10-21"
DEFAULT_EMAIL_API_VERSION = "2023-03-31"
USER_AGENT = "SIA-DailyIntelligence/1.0"
RSS_FEEDS = [
    {"name": "Reuters World", "url": "https://feeds.reuters.com/reuters/worldNews"},
    {"name": "BBC World", "url": "http://feeds.bbci.co.uk/news/world/rss.xml"},
    {"name": "Al Jazeera", "url": "https://www.aljazeera.com/xml/rss/all.xml"},
    {"name": "ABC Australia", "url": "https://www.abc.net.au/news/feed/2942460/rss.xml"},
    {"name": "AP News", "url": "https://rsshub.app/apnews/topics/apf-topnews"},
]
STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "from",
    "into",
    "over",
    "under",
    "this",
    "than",
    "have",
    "will",
    "would",
    "should",
    "could",
    "about",
    "across",
    "after",
    "before",
    "their",
    "there",
    "where",
    "when",
    "what",
    "which",
    "while",
    "through",
}
ANALYSIS_SYSTEM_PROMPT = (
    "You are the SIA systemic intelligence analyst. Given these news signals, identify systemic "
    "root causes, cluster shared weaknesses, prioritize interventions under scarcity, and make "
    "explicit predictions with timelines and falsification criteria. Return JSON with keys "
    "root_causes, predictions, narrative, and noise_filtered."
)


def utc_now() -> datetime:
    return datetime.now(UTC)


def runtime_dir() -> Path:
    path = Path(os.environ.get("SIA_WORK_DIR", Path(__file__).resolve().parent / ".runtime"))
    path.mkdir(parents=True, exist_ok=True)
    return path


def data_dir() -> Path:
    path = runtime_dir() / "data"
    path.mkdir(parents=True, exist_ok=True)
    return path


def static_dir() -> Path:
    path = runtime_dir() / "static"
    path.mkdir(parents=True, exist_ok=True)
    return path


def generate_daily_password() -> str:
    return "".join(secrets.choice(SPECIAL_CHARS) for _ in range(24))


def _clean_text(value: str) -> str:
    text = re.sub(r"<[^>]+>", "", value or "")
    return re.sub(r"\s+", " ", text).strip()


def _find_text(element: ET.Element, *names: str) -> str:
    for name in names:
        found = element.find(name)
        if found is not None and found.text:
            return _clean_text(found.text)
    return ""


def normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (title or "").lower())[:120]


def _parse_rss_items(root: ET.Element, feed_name: str) -> list[dict]:
    stories = []
    for item in root.iter("item"):
        title = _find_text(item, "title")
        if not title:
            continue
        stories.append(
            {
                "title": title,
                "body": _find_text(item, "description", "summary", "content")[:500],
                "source": feed_name,
                "url": _find_text(item, "link"),
                "published": _find_text(item, "pubDate", "published", "updated"),
            }
        )
    return stories


def _parse_atom_entries(root: ET.Element, feed_name: str) -> list[dict]:
    stories = []
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    for entry in root.findall(".//atom:entry", ns):
        title = _find_text(entry, "{http://www.w3.org/2005/Atom}title")
        if not title:
            continue
        link = ""
        for link_el in entry.findall("{http://www.w3.org/2005/Atom}link"):
            href = (link_el.attrib.get("href") or "").strip()
            rel = (link_el.attrib.get("rel") or "alternate").strip()
            if href and rel in {"alternate", ""}:
                link = href
                break
        stories.append(
            {
                "title": title,
                "body": _find_text(
                    entry,
                    "{http://www.w3.org/2005/Atom}summary",
                    "{http://www.w3.org/2005/Atom}content",
                )[:500],
                "source": feed_name,
                "url": link,
                "published": _find_text(
                    entry,
                    "{http://www.w3.org/2005/Atom}published",
                    "{http://www.w3.org/2005/Atom}updated",
                ),
            }
        )
    return stories


def fetch_feed(feed: dict, timeout: int = 20) -> list[dict]:
    try:
        response = requests.get(
            feed["url"],
            timeout=timeout,
            headers={"User-Agent": USER_AGENT},
        )
        response.raise_for_status()
        root = ET.fromstring(response.content)
    except Exception as exc:  # pragma: no cover - network variability
        LOGGER.warning("Skipping feed %s: %s", feed["name"], exc)
        return []
    stories = _parse_rss_items(root, feed["name"])
    return stories or _parse_atom_entries(root, feed["name"])


def deduplicate_stories(stories: list[dict]) -> list[dict]:
    seen = set()
    unique = []
    for story in stories:
        key = normalize_title(story.get("title", ""))
        if key and key not in seen:
            seen.add(key)
            unique.append(story)
    return unique


def extract_keywords(text: str) -> list[str]:
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9\-]{2,}", text or "")
    keywords = []
    for word in words:
        cleaned = word.lower().strip("-")
        if cleaned and cleaned not in STOPWORDS and cleaned not in keywords:
            keywords.append(cleaned)
    return keywords[:10]


def collect_stories(max_stories: int = 20, topic: str | None = None) -> list[dict]:
    all_stories = []
    for feed in RSS_FEEDS:
        all_stories.extend(fetch_feed(feed))
    unique = deduplicate_stories(all_stories)
    if not topic:
        return unique[:max_stories]

    keywords = extract_keywords(topic)
    if not keywords:
        return unique[:max_stories]

    scored = []
    for story in unique:
        haystack = f"{story.get('title', '')} {story.get('body', '')}".lower()
        score = sum(haystack.count(keyword) for keyword in keywords)
        if score:
            scored.append((score, story))
    scored.sort(key=lambda item: item[0], reverse=True)
    if scored:
        return [story for _, story in scored[:max_stories]]
    return unique[:max_stories]


def stories_to_signals(stories: list[dict]) -> list[dict]:
    signals = []
    for index, story in enumerate(stories, start=1):
        signals.append(
            {
                "number": index,
                "signal_type": "community_report",
                "source": story.get("source", "news").lower().replace(" ", "-"),
                "title": story.get("title", ""),
                "body": story.get("body", ""),
                "labels": [],
                "url": story.get("url", ""),
                "published": story.get("published", ""),
            }
        )
    return signals


def _chat_completion(messages: list[dict], *, max_tokens: int = 2500, temperature: float = 0.2) -> str:
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
    deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "")
    api_key = os.environ.get("AZURE_OPENAI_KEY", "")
    api_version = os.environ.get("AZURE_OPENAI_API_VERSION", DEFAULT_OPENAI_API_VERSION)
    if not endpoint or not deployment or not api_key:
        raise RuntimeError("Azure OpenAI settings are incomplete.")

    url = f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version={api_version}"
    response = requests.post(
        url,
        headers={"api-key": api_key, "Content-Type": "application/json"},
        json={
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        },
        timeout=180,
    )
    response.raise_for_status()
    payload = response.json()
    return (
        payload.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
    )


def _extract_json(text: str) -> dict:
    text = (text or "").strip()
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass

    match = re.search(r"```json\s*(.*?)```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            return {}
    return {}


def heuristic_analysis(stories: list[dict]) -> dict:
    root_causes = []
    predictions = []
    for index, story in enumerate(stories[:3], start=1):
        target = story.get("title", f"root-cause-{index}")[:90]
        severity = ["high", "medium", "medium"][min(index - 1, 2)]
        root_causes.append(
            {
                "rank": index,
                "name": target,
                "severity": severity,
                "signals": [story.get("title", "")],
                "timeline": "2-4 weeks",
                "rationale": story.get("body", "")[:220] or "Derived from repeated signal pressure.",
                "intervention": "Increase monitoring and targeted mitigations in the most exposed subsystem.",
                "prediction": f"Pressure around {target} will intensify unless mitigated.",
                "falsification": "Signals dissipate without downstream disruptions.",
            }
        )
        predictions.append(
            {
                "root_cause": target,
                "prediction": f"Pressure around {target} will intensify unless mitigated.",
                "timeline": "2-4 weeks",
                "falsification": "Signals dissipate without downstream disruptions.",
                "severity": severity,
            }
        )
    return {
        "root_causes": root_causes,
        "predictions": predictions,
        "narrative": "Azure OpenAI configuration was unavailable, so a heuristic local analysis was generated.",
        "noise_filtered": [story.get("title", "") for story in stories[3:6]],
    }


def analyze_stories(stories: list[dict]) -> dict:
    story_lines = []
    for index, story in enumerate(stories, start=1):
        story_lines.append(
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
    user_prompt = (
        "Analyse the following news signals. Return JSON with:\n"
        "- root_causes: list of {rank, name, severity, signals, timeline, rationale, intervention, prediction, falsification}\n"
        "- predictions: list of {root_cause, prediction, timeline, falsification, severity}\n"
        "- narrative: string\n"
        "- noise_filtered: list of strings\n\n"
        + "\n\n".join(story_lines)
    )

    try:
        raw = _chat_completion(
            [
                {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ]
        )
        parsed = _extract_json(raw)
        if parsed:
            return parsed
    except Exception as exc:  # pragma: no cover - exercised only with live AOAI
        LOGGER.warning("Azure OpenAI analysis failed, using heuristic fallback: %s", exc)
    return heuristic_analysis(stories)


def parse_iso_date(value: str | None) -> datetime | None:
    if not value:
        return None
    candidates = [str(value).strip()]
    if candidates[0].endswith("Z"):
        candidates.append(candidates[0][:-1] + "+00:00")
    if len(candidates[0]) == 10:
        candidates.append(candidates[0] + "T00:00:00+00:00")
    for candidate in candidates:
        try:
            dt = datetime.fromisoformat(candidate)
            return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
        except ValueError:
            continue
    return None


def compute_maturity_date(created_at: str, timeline: str) -> str | None:
    created = parse_iso_date(created_at)
    if created is None:
        return None
    timeline_text = (timeline or "").lower().strip()
    match = re.search(r"(\d+)(?:\s*-\s*(\d+))?\s*(day|days|week|weeks|month|months|year|years)", timeline_text)
    if not match:
        return None
    amount = int(match.group(2) or match.group(1))
    unit = match.group(3)
    if unit.startswith("day"):
        delta = timedelta(days=amount)
    elif unit.startswith("week"):
        delta = timedelta(weeks=amount)
    elif unit.startswith("month"):
        delta = timedelta(days=amount * 30)
    else:
        delta = timedelta(days=amount * 365)
    return (created + delta).date().isoformat()


def make_prediction_id(created_at: str, root_cause: str, prediction: str) -> str:
    raw = f"{created_at}|{root_cause}|{prediction}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def merge_predictions(existing: list[dict], new_predictions: list[dict], created_at: str) -> list[dict]:
    merged = {item.get("id"): dict(item) for item in existing if item.get("id")}
    for prediction in new_predictions:
        root_cause = prediction.get("root_cause") or prediction.get("name") or "Unknown"
        prediction_text = prediction.get("prediction") or prediction.get("statement") or ""
        prediction_id = make_prediction_id(created_at, root_cause, prediction_text)
        entry = {
            "id": prediction_id,
            "created_at": created_at,
            "root_cause": root_cause,
            "prediction": prediction_text,
            "timeline": prediction.get("timeline", ""),
            "maturity_date": prediction.get("maturity_date") or compute_maturity_date(created_at, prediction.get("timeline", "")),
            "falsification": prediction.get("falsification", ""),
            "severity": prediction.get("severity", "unknown"),
            "status": prediction.get("status", "open"),
            "validation_notes": prediction.get("validation_notes", ""),
            "validated_at": prediction.get("validated_at"),
        }
        if prediction_id in merged:
            merged[prediction_id].update({k: v for k, v in entry.items() if v not in (None, "")})
        else:
            merged[prediction_id] = entry
    return sorted(
        merged.values(),
        key=lambda item: (item.get("maturity_date") or "", item.get("created_at") or "", item.get("id") or ""),
        reverse=True,
    )


def build_prediction_schedule(ledger: dict) -> dict:
    schedule = []
    for prediction in ledger.get("predictions", []):
        maturity_date = prediction.get("maturity_date") or compute_maturity_date(
            prediction.get("created_at", ""),
            prediction.get("timeline", ""),
        )
        if maturity_date:
            schedule.append(
                {
                    "id": prediction.get("id"),
                    "root_cause": prediction.get("root_cause", ""),
                    "maturity_date": maturity_date,
                    "status": prediction.get("status", "open"),
                }
            )
    schedule.sort(key=lambda item: (item["maturity_date"], item["id"]))
    return {"generated_at": utc_now().isoformat(), "schedule": schedule}


def _keyword_overlap_score(story: dict, topic: str) -> int:
    haystack = f"{story.get('title', '')} {story.get('body', '')}".lower()
    return sum(haystack.count(keyword) for keyword in extract_keywords(topic))


def validate_prediction(prediction: dict, fresh_stories: list[dict]) -> dict:
    evidence = [
        f"- {story.get('source', 'Unknown')}: {story.get('title', '')} ({story.get('url', '')})"
        for story in fresh_stories[:8]
    ]
    prompt = (
        "Evaluate whether the prediction matured as validated, falsified, partially_validated, or expired. "
        "Return JSON with keys status, notes, and evidence_used.\n\n"
        f"Prediction root cause: {prediction.get('root_cause', '')}\n"
        f"Prediction: {prediction.get('prediction', '')}\n"
        f"Falsification criteria: {prediction.get('falsification', '')}\n"
        f"Timeline: {prediction.get('timeline', '')}\n"
        "Fresh signals:\n"
        + ("\n".join(evidence) if evidence else "No fresh signals found.")
    )
    try:
        raw = _chat_completion(
            [
                {"role": "system", "content": "Return only JSON with status, notes, and evidence_used."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=800,
            temperature=0.0,
        )
        parsed = _extract_json(raw)
        if parsed:
            return {
                "status": parsed.get("status", "partially_validated"),
                "validation_notes": parsed.get("notes", ""),
                "evidence_used": parsed.get("evidence_used", evidence[:5]),
            }
    except Exception as exc:  # pragma: no cover - live AOAI only
        LOGGER.warning("Prediction validation fallback used: %s", exc)

    score = sum(_keyword_overlap_score(story, prediction.get("root_cause", "")) for story in fresh_stories)
    if score >= 3:
        status = "validated"
        notes = "Fresh signals materially overlapped with the predicted topic."
    elif fresh_stories:
        status = "partially_validated"
        notes = "Some related signals appeared, but confirmation is mixed."
    else:
        status = "expired"
        notes = "No fresh related signals were found by the maturity date."
    return {"status": status, "validation_notes": notes, "evidence_used": evidence[:5]}


def validate_matured_predictions(ledger: dict, today: str) -> list[dict]:
    results = []
    for prediction in ledger.get("predictions", []):
        maturity_date = prediction.get("maturity_date") or compute_maturity_date(
            prediction.get("created_at", ""),
            prediction.get("timeline", ""),
        )
        if prediction.get("status", "open") != "open" or not maturity_date or maturity_date > today:
            continue

        fresh_stories = collect_stories(max_stories=10, topic=prediction.get("root_cause", ""))
        validation = validate_prediction(prediction, fresh_stories)
        prediction["maturity_date"] = maturity_date
        prediction["status"] = validation["status"]
        prediction["validation_notes"] = validation["validation_notes"]
        prediction["validated_at"] = utc_now().isoformat()
        prediction["evidence_used"] = validation.get("evidence_used", [])
        results.append(prediction)
    return results


def escape(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def format_human_date(value: str | None) -> str:
    parsed = parse_iso_date(value)
    if parsed is None:
        return value or "Unknown"
    return parsed.astimezone(UTC).strftime("%d %b %Y")


def build_dashboard_html(report: dict, ledger: dict, dashboard_url: str, login_url: str) -> str:
    root_causes = report.get("root_causes", [])
    stories = report.get("stories", [])
    predictions = ledger.get("predictions", [])
    narrative = report.get("narrative", "")
    severity_classes = {
        "existential": "severity-existential",
        "critical": "severity-existential",
        "high": "severity-existential",
        "major": "severity-major",
        "medium": "severity-moderate",
        "moderate": "severity-moderate",
        "low": "severity-moderate",
    }
    status_classes = {
        "validated": "status-validated",
        "partially_validated": "status-partial",
        "falsified": "status-falsified",
        "expired": "status-expired",
        "open": "status-open",
    }
    root_rows = []
    cards = []
    for index, cause in enumerate(root_causes, start=1):
        signals = [str(s) for s in cause.get("signals", [])]
        severity = str(cause.get("severity", "unknown")).strip().lower()
        severity_class = severity_classes.get(severity, "severity-moderate")
        root_rows.append(
            f"<tr><td data-label='Rank'>{index}</td><td data-label='Name'>{escape(cause.get('name', 'Unknown'))}</td><td data-label='Severity'>{escape(cause.get('severity', 'unknown'))}</td>"
            f"<td data-label='Signals'>{escape(', '.join(signals[:3]))}</td><td data-label='Timeline'>{escape(cause.get('timeline', ''))}</td><td data-label='Rationale'>{escape(cause.get('rationale', ''))}</td></tr>"
        )
        cards.append(
            f"<article class='detail-block {severity_class}'>"
            f"<p class='detail-kicker'>{escape(cause.get('severity', 'unknown'))}</p>"
            f"<h3>{index}. {escape(cause.get('name', 'Unknown'))}</h3>"
            f"<p><span>Intervention</span>{escape(cause.get('intervention', ''))}</p>"
            f"<p><span>Prediction</span>{escape(cause.get('prediction', ''))}</p>"
            f"<p><span>Falsification</span>{escape(cause.get('falsification', ''))}</p>"
            "</article>"
        )
    # Strip body snippets from stories for public display — only show title + source + link
    public_stories = []
    for story in stories:
        public_stories.append({
            "title": story.get("title", "Untitled"),
            "source": story.get("source", "Unknown"),
            "url": story.get("url", ""),
            "published": story.get("published", ""),
        })

    story_rows = [
        f"<tr><td data-label='Headline'><a href='{escape(s['url'])}' target='_blank' rel='noreferrer'>{escape(s['title'])}</a></td><td data-label='Source'>{escape(s['source'])}</td><td data-label='Published'>{escape(format_human_date(s.get('published')))}</td></tr>"
        for s in public_stories
    ]
    prediction_rows = [
        f"<tr><td data-label='Root cause'>{escape(item.get('root_cause', 'Unknown'))}</td><td data-label='Status'><span class='status-pill {status_classes.get(str(item.get('status', 'open')).strip().lower(), 'status-open')}'>{escape(item.get('status', 'open'))}</span></td><td data-label='Maturity'>{escape(item.get('maturity_date', ''))}</td><td data-label='Notes'>{escape(item.get('validation_notes', item.get('prediction', '')))}</td></tr>"
        for item in predictions
    ]

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex, nofollow, noarchive">
  <title>SIA — Systemic Intelligence Analysis</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    :root {{
      --paper: #faf9f6;
      --paper-line: #dfd8cc;
      --ink: #1a1a1a;
      --muted: #6d675f;
      --accent: #8f4d3f;
      --existential: #a4493d;
      --major: #b27a3f;
      --moderate: #8a8379;
      --pill-bg: #f1ece4;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--paper);
      color: var(--ink);
      font-family: 'Inter', 'Helvetica Neue', Arial, sans-serif;
      line-height: 1.68;
      -webkit-font-smoothing: antialiased;
    }}
    .page {{
      max-width: 780px;
      margin: 0 auto;
      padding: 48px 24px 56px;
    }}
    a {{
      color: var(--accent);
      text-decoration: none;
      border-bottom: 1px solid rgba(143, 77, 63, 0.28);
    }}
    a:hover {{ border-bottom-color: var(--accent); }}
    section {{
      padding: 0 0 34px;
      margin: 0 0 34px;
      border-bottom: 1px solid var(--paper-line);
    }}
    .mark-row {{
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 16px;
    }}
    .mark {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-width: 72px;
      padding: 8px 12px 7px;
      border: 1px solid var(--ink);
      font-family: Georgia, 'Times New Roman', serif;
      font-size: 1.65rem;
      font-weight: 700;
      letter-spacing: 0.12em;
      line-height: 1;
    }}
    .issue-date {{
      color: var(--muted);
      font-size: 0.95rem;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }}
    h1, h2, h3 {{
      margin: 0;
      font-family: Georgia, 'Times New Roman', serif;
      color: var(--ink);
      font-weight: 700;
    }}
    h1 {{
      font-size: clamp(2.45rem, 5vw, 3.35rem);
      line-height: 1.05;
      margin-bottom: 10px;
      letter-spacing: -0.03em;
    }}
    h2 {{
      font-size: 1.55rem;
      line-height: 1.2;
      margin-bottom: 16px;
      letter-spacing: -0.02em;
    }}
    h3 {{
      font-size: 1.1rem;
      line-height: 1.3;
      margin-bottom: 10px;
    }}
    .dek {{
      max-width: 64ch;
      margin: 0 0 10px;
      color: var(--muted);
      font-size: 1rem;
    }}
    .meta-line {{
      margin: 18px 0 0;
      color: var(--muted);
      font-size: 0.95rem;
    }}
    .narrative {{
      margin: 0;
      white-space: pre-line;
      font-size: 1.05rem;
      line-height: 1.74;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.96rem;
    }}
    th, td {{
      padding: 12px 0;
      text-align: left;
      vertical-align: top;
      border-bottom: 1px solid var(--paper-line);
    }}
    th {{
      padding-top: 0;
      color: var(--muted);
      font-size: 0.78rem;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}
    tbody tr:last-child td {{ border-bottom: 0; }}
    .detail-list {{
      margin-top: 20px;
      display: grid;
      gap: 14px;
    }}
    .detail-block {{
      padding-left: 18px;
      border-left: 3px solid var(--moderate);
    }}
    .detail-block p {{
      margin: 8px 0 0;
    }}
    .detail-block span {{
      display: block;
      margin-bottom: 3px;
      color: var(--muted);
      font-size: 0.77rem;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}
    .detail-kicker {{
      margin: 0 0 8px;
      color: var(--muted);
      font-size: 0.78rem;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}
    .severity-existential {{ border-left-color: var(--existential); }}
    .severity-major {{ border-left-color: var(--major); }}
    .severity-moderate {{ border-left-color: var(--moderate); }}
    .status-pill {{
      display: inline-flex;
      align-items: center;
      padding: 4px 10px;
      border-radius: 999px;
      background: var(--pill-bg);
      color: var(--ink);
      font-size: 0.78rem;
      font-weight: 600;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }}
    .status-validated {{ background: rgba(85, 111, 83, 0.13); color: #556f53; }}
    .status-partial {{ background: rgba(178, 122, 63, 0.14); color: #8a5d2d; }}
    .status-falsified {{ background: rgba(164, 73, 61, 0.13); color: #8b3f34; }}
    .status-expired, .status-open {{ background: var(--pill-bg); color: #6e665d; }}
    .sources td:first-child a {{ font-weight: 500; }}
    .attribution {{
      margin: 14px 0 0;
      color: var(--muted);
      font-size: 0.84rem;
    }}
    footer {{
      color: var(--muted);
      font-size: 0.84rem;
    }}
    @media (max-width: 640px) {{
      .page {{ padding: 32px 18px 40px; }}
      .mark-row {{ flex-direction: column; align-items: flex-start; }}
      table, thead, tbody, th, td, tr {{ display: block; }}
      thead {{
        position: absolute;
        width: 1px;
        height: 1px;
        padding: 0;
        margin: -1px;
        overflow: hidden;
        clip: rect(0, 0, 0, 0);
        white-space: nowrap;
        border: 0;
      }}
      tr {{
        padding: 10px 0;
        border-bottom: 1px solid var(--paper-line);
      }}
      td {{
        border: 0;
        padding: 4px 0;
      }}
      td::before {{
        content: attr(data-label);
        display: block;
        color: var(--muted);
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin-bottom: 2px;
      }}
      tbody tr:last-child {{ border-bottom: 0; }}
    }}
  </style>
</head>
<body>
  <div class="page">
    <section>
      <div class="mark-row">
        <div class="mark">SIA</div>
        <div class="issue-date">{escape(report.get("report_date", ""))}</div>
      </div>
      <h1>Systemic Intelligence Analysis</h1>
      <p class="dek">SIA (Synthetic Insight Architecture) is a general-purpose problem intelligence system. It collects signals from diverse public sources — news reports, field observations, institutional data — and runs them through a multi-stage analysis pipeline that identifies shared systemic root causes, clusters compounding risks, prioritises interventions under real-world scarcity constraints, and tracks explicit predictions against outcomes over time. Rather than summarising individual stories, it looks for the structural patterns that connect them: the feedback loops, cascade risks, and institutional failures that determine what actually happens next. The system is validated across six domains including geopolitical conflict, economic resilience, and historical hindcasting. <a href="https://github.com/ravisha22/SyntheticInsightArchitecture">View the project and methodology on GitHub&nbsp;→</a></p>
      <p class="meta-line">{len(stories)} stories analysed · {len(root_causes)} root causes · {len(predictions)} predictions</p>
    </section>

    <section>
      <h2>Narrative</h2>
      <p class="narrative">{escape(narrative)}</p>
    </section>

    <section>
      <h2>Root causes</h2>
      <table>
        <thead><tr><th>Rank</th><th>Name</th><th>Severity</th><th>Signals</th><th>Timeline</th><th>Rationale</th></tr></thead>
        <tbody>{''.join(root_rows) or '<tr><td colspan="6">No root causes available.</td></tr>'}</tbody>
      </table>
      <div class="detail-list">{''.join(cards) or '<p>No detailed cards available.</p>'}</div>
    </section>

    <section>
      <h2>Prediction ledger</h2>
      <table>
        <thead><tr><th>Root cause</th><th>Status</th><th>Maturity</th><th>Notes</th></tr></thead>
        <tbody>{''.join(prediction_rows) or '<tr><td colspan="4">No predictions logged.</td></tr>'}</tbody>
      </table>
    </section>

    <section>
      <h2>Sources</h2>
      <table class="sources">
        <thead><tr><th>Headline</th><th>Source</th><th>Published</th></tr></thead>
        <tbody>{''.join(story_rows) or '<tr><td colspan="3">No stories available.</td></tr>'}</tbody>
      </table>
      <p class="attribution">Headlines sourced from publicly available RSS feeds. Click through for full articles. SIA uses headlines and short summaries for systemic pattern analysis only — no article content is republished.</p>
    </section>

    <footer>
      <a href="https://github.com/ravisha22/SyntheticInsightArchitecture">Synthetic Insight Architecture</a> — predictions are systemic analysis, not financial or political advice.
    </footer>
  </div>
</body>
</html>"""


def build_email_html(report: dict, ledger: dict, matured_predictions: list[dict], daily_password: str, login_url: str, dashboard_url: str) -> str:
    date_label = escape(report.get("report_date", ""))
    root_causes = report.get("root_causes", [])
    matured_markup = ""
    if matured_predictions:
        items = "".join(
            f"<tr><td>{escape(item.get('root_cause', 'Unknown'))}</td><td>{escape(item.get('status', 'open'))}</td>"
            f"<td>{escape(item.get('validation_notes', ''))}</td></tr>"
            for item in matured_predictions
        )
        matured_markup = (
            "<h2 style='margin-top:32px;'>Prediction validations</h2>"
            "<table style='width:100%;border-collapse:collapse;'>"
            "<tr><th align='left'>Prediction</th><th align='left'>Status</th><th align='left'>Notes</th></tr>"
            f"{items}</table>"
        )

    root_rows = "".join(
        f"<tr><td>{index}</td><td>{escape(cause.get('name', 'Unknown'))}</td><td>{escape(cause.get('severity', 'unknown'))}</td>"
        f"<td>{escape(', '.join(str(s) for s in cause.get('signals', [])[:3]))}</td><td>{escape(cause.get('timeline', ''))}</td><td>{escape(cause.get('rationale', ''))}</td></tr>"
        for index, cause in enumerate(root_causes, start=1)
    ) or "<tr><td colspan='6'>No root causes identified.</td></tr>"

    detail_cards = "".join(
        "<div style='background:#f8fafc;border:1px solid #cbd5e1;border-radius:14px;padding:16px;margin:12px 0;'>"
        f"<h3 style='margin-top:0;'>{escape(cause.get('name', 'Unknown'))}</h3>"
        f"<p><strong>Intervention:</strong> {escape(cause.get('intervention', ''))}</p>"
        f"<p><strong>Prediction:</strong> {escape(cause.get('prediction', ''))}</p>"
        f"<p><strong>Falsification:</strong> {escape(cause.get('falsification', ''))}</p>"
        "</div>"
        for cause in root_causes
    )

    return f"""<html>
<body style="margin:0;background:#e2e8f0;font-family:Segoe UI,Arial,sans-serif;color:#0f172a;">
  <div style="max-width:900px;margin:0 auto;padding:24px;">
    <div style="background:#0f172a;color:#f8fafc;border-radius:20px;padding:28px;">
      <p style="margin:0 0 8px 0;text-transform:uppercase;letter-spacing:.08em;color:#93c5fd;">SIA Daily Intelligence</p>
      <h1 style="margin:0 0 8px 0;">{date_label}</h1>
      <p style="margin:0;">Daily systemic intelligence summary and validation digest.</p>
    </div>

    <div style="background:#ffffff;border-radius:20px;padding:24px;margin-top:18px;">
      <h2>Summary</h2>
      <ul>
        <li>{len(report.get('stories', []))} stories analysed</li>
        <li>{len(root_causes)} root causes prioritised</li>
        <li>{len(ledger.get('predictions', []))} predictions tracked</li>
      </ul>

      <h2>Narrative</h2>
      <p>{escape(report.get('narrative', ''))}</p>

      <h2>Root causes</h2>
      <table style="width:100%;border-collapse:collapse;">
        <tr>
          <th align="left">Rank</th><th align="left">Name</th><th align="left">Severity</th>
          <th align="left">Signals</th><th align="left">Timeline</th><th align="left">Rationale</th>
        </tr>
        {root_rows}
      </table>

      <h2>Detail cards</h2>
      {detail_cards or "<p>No detail cards available.</p>"}
      {matured_markup}

      <h2 style='margin-top:32px;'>Access</h2>
      <p><strong>Today's password:</strong> <code>{escape(daily_password)}</code></p>
      <p><strong>Dashboard:</strong> <a href="{escape(dashboard_url)}">{escape(dashboard_url)}</a></p>
      <p><strong>Direct login:</strong> <a href="{escape(login_url)}">{escape(login_url)}</a></p>
    </div>

    <div style="color:#475569;font-size:12px;padding:16px 4px;">
      Generated automatically by SIA. Validate sensitive operational conclusions before acting.
    </div>
  </div>
</body>
</html>"""


def _upload_github_file(path: str, content: str) -> None:
    """Push a file to the repo via the GitHub API."""
    token = os.environ.get("GITHUB_TOKEN", "")
    repo = os.environ.get("SIA_GITHUB_REPO", "ravisha22/SyntheticInsightArchitecture")
    if not token:
        return

    import base64

    api_url = f"https://api.github.com/repos/{repo}/contents/{path}"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json"}

    sha = None
    try:
        resp = requests.get(api_url, headers=headers, timeout=15)
        if resp.status_code == 200:
            sha = resp.json().get("sha")
    except Exception:
        pass

    payload = {
        "message": f"chore: update {path} {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
        "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
        "branch": "main",
    }
    if sha:
        payload["sha"] = sha

    try:
        resp = requests.put(api_url, headers=headers, json=payload, timeout=30)
        if resp.status_code in (200, 201):
            LOGGER.info("GitHub file updated: %s", path)
        else:
            LOGGER.warning("GitHub file update failed for %s: %s", path, resp.status_code)
    except Exception as exc:
        LOGGER.warning("GitHub file update error for %s: %s", path, exc)


def _upload_to_github_pages(html_content: str) -> None:
    """Push dashboard HTML to docs/index.html via the GitHub API."""
    token = os.environ.get("GITHUB_TOKEN", "")
    repo = os.environ.get("SIA_GITHUB_REPO", "ravisha22/SyntheticInsightArchitecture")
    if not token:
        LOGGER.warning("GITHUB_TOKEN not set; skipping GitHub Pages update")
        return

    LOGGER.info("Attempting GitHub Pages update for repo %s (token: %s...)", repo, token[:4])

    import base64

    api_url = f"https://api.github.com/repos/{repo}/contents/docs/index.html"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    # Get current file SHA (needed for update)
    sha = None
    try:
        resp = requests.get(api_url, headers=headers, timeout=15)
        LOGGER.info("GitHub GET status: %s", resp.status_code)
        if resp.status_code == 200:
            sha = resp.json().get("sha")
        else:
            LOGGER.warning("GitHub GET response: %s", resp.text[:300])
    except Exception as exc:
        LOGGER.warning("GitHub GET failed: %s", exc)

    payload = {
        "message": f"chore: update dashboard {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
        "content": base64.b64encode(html_content.encode("utf-8")).decode("ascii"),
        "branch": "main",
    }
    if sha:
        payload["sha"] = sha

    try:
        resp = requests.put(api_url, headers=headers, json=payload, timeout=30)
        LOGGER.info("GitHub PUT status: %s", resp.status_code)
        if resp.status_code in (200, 201):
            LOGGER.info("GitHub Pages dashboard updated successfully")
        else:
            LOGGER.warning("GitHub Pages update failed: %s %s", resp.status_code, resp.text[:300])
    except Exception as exc:
        LOGGER.warning("GitHub Pages update error: %s", exc)


def _get_blob_service():
    connection_string = os.environ.get("BLOB_CONNECTION_STRING", "")
    if not connection_string:
        return None
    from azure.storage.blob import BlobServiceClient

    return BlobServiceClient.from_connection_string(connection_string)


def load_json_document(filename: str, default: dict, container: str | None = None) -> dict:
    service = _get_blob_service()
    if service:
        container_name = container or os.environ.get("SIA_DATA_CONTAINER", "sia-data")
        blob_client = service.get_blob_client(container=container_name, blob=filename)
        try:
            return json.loads(blob_client.download_blob().readall().decode("utf-8"))
        except Exception:
            return default
    path = data_dir() / filename
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


def save_json_document(filename: str, data: dict, container: str | None = None) -> None:
    payload = json.dumps(data, indent=2, ensure_ascii=False)
    service = _get_blob_service()
    if service:
        container_name = container or os.environ.get("SIA_DATA_CONTAINER", "sia-data")
        container_client = service.get_container_client(container_name)
        try:
            container_client.create_container()
        except Exception:
            pass
        container_client.upload_blob(name=filename, data=payload.encode("utf-8"), overwrite=True)
    (data_dir() / filename).write_text(payload, encoding="utf-8")


def upload_static_blob(name: str, content: str, content_type: str) -> None:
    service = _get_blob_service()
    target = static_dir() / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    if not service:
        return
    from azure.storage.blob import ContentSettings

    container_name = os.environ.get("SIA_STATIC_CONTAINER", "$web")
    container_client = service.get_container_client(container_name)
    blob_client = container_client.get_blob_client(name)
    blob_client.upload_blob(
        content.encode("utf-8"),
        overwrite=True,
        content_settings=ContentSettings(content_type=content_type),
    )


def _parse_connection_string(connection_string: str) -> dict:
    parts = {}
    for item in connection_string.split(";"):
        if "=" in item:
            key, value = item.split("=", 1)
            parts[key.strip().lower()] = value.strip()
    return parts


def _send_email_rest(to_email: str, subject: str, html_body: str, connection_string: str) -> None:
    sender = os.environ.get("SIA_EMAIL_SENDER", "")
    parts = _parse_connection_string(connection_string)
    endpoint = parts.get("endpoint", "").rstrip("/")
    access_key = parts.get("accesskey", "")
    if not sender or not endpoint or not access_key:
        raise RuntimeError("ACS REST fallback requires endpoint, access key, and SIA_EMAIL_SENDER.")

    body = {
        "senderAddress": sender,
        "content": {"subject": subject, "html": html_body},
        "recipients": {"to": [{"address": to_email}]},
    }
    payload = json.dumps(body, separators=(",", ":")).encode("utf-8")
    parsed_endpoint = urlparse(endpoint)
    path = "/emails:send"
    request_url = f"{endpoint}{path}?api-version={os.environ.get('ACS_EMAIL_API_VERSION', DEFAULT_EMAIL_API_VERSION)}"
    content_hash = base64.b64encode(hashlib.sha256(payload).digest()).decode("utf-8")
    request_date = format_datetime(utc_now(), usegmt=True)
    string_to_sign = "\n".join(
        [
            "POST",
            path,
            request_date,
            str(len(payload)),
            "application/json",
            content_hash,
        ]
    )
    signature = base64.b64encode(
        hmac.new(base64.b64decode(access_key), string_to_sign.encode("utf-8"), hashlib.sha256).digest()
    ).decode("utf-8")
    authorization = f"HMAC-SHA256 SignedHeaders=x-ms-date;host;x-ms-content-sha256&Signature={signature}"
    response = requests.post(
        request_url,
        data=payload,
        headers={
            "Authorization": authorization,
            "Content-Type": "application/json",
            "Host": parsed_endpoint.netloc,
            "x-ms-date": request_date,
            "x-ms-content-sha256": content_hash,
        },
        timeout=60,
    )
    response.raise_for_status()


def send_email(to_email: str, subject: str, html_body: str, connection_string: str) -> None:
    if not to_email or not connection_string:
        preview = runtime_dir() / "email_preview.html"
        preview.write_text(html_body, encoding="utf-8")
        LOGGER.info("Email settings missing; saved preview to %s", preview)
        return

    try:
        from azure.communication.email import EmailClient

        sender = os.environ.get("SIA_EMAIL_SENDER", "")
        if not sender:
            raise RuntimeError("SIA_EMAIL_SENDER is required for ACS email delivery.")
        client = EmailClient.from_connection_string(connection_string)
        poller = client.begin_send(
            {
                "senderAddress": sender,
                "content": {"subject": subject, "html": html_body},
                "recipients": {"to": [{"address": to_email}]},
            }
        )
        result = poller.result()
        LOGGER.info("Email send completed: %s", result)
        return
    except ImportError:
        LOGGER.info("azure-communication-email not installed, using REST fallback.")

    _send_email_rest(to_email, subject, html_body, connection_string)


def ensure_auth_state() -> tuple[SIAAuth, str]:
    auth_state = load_json_document("auth_state.json", {"failed_attempts": {}, "daily_passwords": {}, "magic_links": {}})
    auth_path = runtime_dir() / "auth_state.json"
    auth_path.write_text(json.dumps(auth_state, indent=2), encoding="utf-8")
    auth = SIAAuth(str(auth_path))
    today = utc_now().strftime("%Y-%m-%d")
    if today not in auth.state.get("daily_passwords", {}):
        auth.state.setdefault("daily_passwords", {})[today] = generate_daily_password()
        auth._save_state()
    daily_password = auth.state["daily_passwords"][today]
    save_json_document("auth_state.json", auth.state)
    return auth, daily_password


def run_daily_pipeline() -> dict:
    logging.basicConfig(level=logging.INFO)
    report_date = utc_now().strftime("%Y-%m-%d")
    dashboard_url = os.environ.get("SIA_DASHBOARD_URL", "")
    login_base_url = os.environ.get("SIA_LOGIN_URL", dashboard_url.rstrip("/") if dashboard_url else "")

    stories = collect_stories(max_stories=20)
    analysis = analyze_stories(stories)
    ledger = load_json_document("prediction_ledger.json", {"predictions": [], "last_updated": None})
    merged_predictions = merge_predictions(ledger.get("predictions", []), analysis.get("predictions", []), report_date)
    ledger["predictions"] = merged_predictions
    ledger["last_updated"] = utc_now().isoformat()

    matured_predictions = validate_matured_predictions(ledger, report_date)
    schedule = build_prediction_schedule(ledger)

    auth, daily_password = ensure_auth_state()
    login_url = auth.generate_magic_link(login_base_url) if login_base_url else ""
    save_json_document("auth_state.json", auth.state)

    report = {
        "report_date": report_date,
        "generated_at": utc_now().isoformat(),
        "story_count": len(stories),
        "stories": stories,
        "signals": stories_to_signals(stories),
        "root_causes": analysis.get("root_causes", []),
        "predictions": analysis.get("predictions", []),
        "narrative": analysis.get("narrative", ""),
        "noise_filtered": analysis.get("noise_filtered", []),
        "matured_predictions": matured_predictions,
    }

    save_json_document("latest_analysis.json", report)
    save_json_document("prediction_ledger.json", ledger)
    save_json_document("prediction_schedule.json", schedule)

    dashboard_html = build_dashboard_html(report, ledger, dashboard_url, login_url)
    email_html = build_email_html(report, ledger, matured_predictions, daily_password, login_url, dashboard_url)

    # Upload dashboard and analysis data to GitHub Pages
    _upload_to_github_pages(dashboard_html)
    _upload_github_file("docs/data.json", json.dumps(report, indent=2, ensure_ascii=False))
    try:
        upload_static_blob("index.html", dashboard_html, "text/html; charset=utf-8")
        upload_static_blob("robots.txt", "User-agent: *\nDisallow: /\n", "text/plain; charset=utf-8")
        config_path = Path(__file__).resolve().parent / "staticwebapp.config.json"
        if config_path.exists():
            upload_static_blob("staticwebapp.config.json", config_path.read_text(encoding="utf-8"), "application/json")
    except Exception as exc:
        LOGGER.warning("Blob upload skipped (RBAC not configured): %s", exc)

    send_email(
        os.environ.get("RECIPIENT_EMAIL", ""),
        f"SIA Daily Intelligence — {report_date}",
        email_html,
        os.environ.get("ACS_CONNECTION_STRING", ""),
    )

    summary = {
        "report_date": report_date,
        "stories": len(stories),
        "root_causes": len(report["root_causes"]),
        "predictions": len(ledger["predictions"]),
        "matured_predictions": len(matured_predictions),
        "dashboard_url": dashboard_url,
        "login_url": login_url,
    }
    LOGGER.info("SIA daily pipeline complete: %s", summary)
    return summary


def main() -> int:
    summary = run_daily_pipeline()
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
