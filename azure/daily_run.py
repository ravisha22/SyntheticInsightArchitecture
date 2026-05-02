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
from collections import Counter
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

MODULE_DIR = Path(__file__).resolve().parent
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from auth_middleware import SIAAuth
from src.core.domain_registry import load_domain_profile
from src.core.persona_ensemble import load_ensemble
from src.core.prioritization_engine import PrioritizationEngine
from src.core.structural_classifier import LLMClassifier, MockClassifier


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


def _chat_completion(
    messages: list[dict], *, max_tokens: int = 2500, temperature: float = 0.2, json_mode: bool = True
) -> str:
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
            **({"response_format": {"type": "json_object"}} if json_mode else {}),
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


class DailyRunAdapter:
    """Adapter that wraps daily_run's chat helper for the core classifier."""

    def analyze(self, system: str, user: str, json_schema: dict | None = None) -> dict:
        if json_schema:
            system = f"{system}\nReturn JSON matching this schema as closely as possible:\n{json.dumps(json_schema, indent=2)}"
        raw = _chat_completion(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.0,
            json_mode=True,
        )
        return _extract_json(raw) or {}


def mood_emoji(label: str) -> str:
    return {
        "constructive": "🟢",
        "cautious": "🟡",
        "concerning": "🔴",
        "transitional": "🟠",
    }.get((label or "").strip().lower(), "⚪")


def _sort_cluster_scores(cluster_scores: dict[str, float], *, reverse: bool) -> list[tuple[str, float]]:
    return sorted(
        ((str(name), float(score)) for name, score in (cluster_scores or {}).items()),
        key=lambda item: (item[1], item[0]),
        reverse=reverse,
    )


def _normalize_priority_signal(signal: dict) -> dict:
    cluster_scores = signal.get("cluster_means") or signal.get("cluster_mean_scores") or {}
    top_clusters = {name: score for name, score in _sort_cluster_scores(cluster_scores, reverse=True)[:2]}
    bottom_clusters = {name: score for name, score in _sort_cluster_scores(cluster_scores, reverse=False)[:1]}
    normalized = {
        "signal_id": signal.get("signal_id", signal.get("title", "signal")),
        "title": signal.get("title", ""),
        "source": signal.get("source", ""),
        "url": signal.get("url", ""),
        "published": signal.get("published", ""),
        "classifier_fallback": bool(signal.get("classifier_fallback", False)),
        "priority_score": float(signal.get("priority_score", 0.0)),
        "contest_score": float(signal.get("contest_score", 0.0)),
        "category": signal.get("category", "background_noise"),
        "polarity": int(signal.get("polarity", 0)),
        "sign_agreement": float(signal.get("sign_agreement", 0.0)),
        "central_tendency": float(signal.get("central_tendency", 0.0)),
        "contestedness": float(signal.get("contestedness", 0.0)),
        "impact": float(signal.get("impact", 0.0)),
        "top_clusters": top_clusters,
        "bottom_clusters": bottom_clusters,
        "cluster_means": {name: float(score) for name, score in cluster_scores.items()},
    }
    if "priority_raw" in signal:
        normalized["priority_raw"] = float(signal.get("priority_raw", 0.0))
    if "contest_raw" in signal:
        normalized["contest_raw"] = float(signal.get("contest_raw", 0.0))
    return normalized


def _coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _priority_title(item: dict) -> str:
    return str(
        item.get("title")
        or item.get("target")
        or item.get("name")
        or item.get("root_cause")
        or ""
    ).strip()


def _normalize_priority_category(value: Any) -> str:
    raw = str(value or "").strip().lower()
    if raw in {"convergent_priority", "contested_priority", "niche_concern", "background_noise"}:
        return raw
    return {
        "high": "convergent_priority",
        "major": "contested_priority",
        "moderate": "niche_concern",
        "medium": "niche_concern",
        "low": "background_noise",
        "minor": "background_noise",
        "cosmetic": "background_noise",
    }.get(raw, raw)


def _normalize_mood_payload(payload: dict) -> dict:
    mood = payload.get("mood", {})
    if isinstance(mood, str):
        label = mood.strip().lower()
        return {"label": label, "score": 0.0, "emoji": mood_emoji(label)}
    if not isinstance(mood, dict):
        return {"label": "", "score": 0.0, "emoji": "⚪"}
    label = str(mood.get("label", "")).strip().lower()
    return {
        "label": label,
        "score": _coerce_float(mood.get("score", 0.0)),
        "emoji": mood.get("emoji") or mood_emoji(label),
    }


def run_core_analysis(stories: list[dict], domain: str = "world_affairs") -> dict:
    """Run the persona-ensemble prioritisation engine on collected stories."""

    ensemble_path = PROJECT_ROOT / "configs" / "persona_ensemble.yaml"
    ensemble = load_ensemble(ensemble_path)
    domain_profile = load_domain_profile(domain)

    has_llm = all(
        [
            os.environ.get("AZURE_OPENAI_ENDPOINT", "").strip(),
            os.environ.get("AZURE_OPENAI_DEPLOYMENT", "").strip(),
            os.environ.get("AZURE_OPENAI_KEY", "").strip(),
        ]
    )
    classifier = LLMClassifier(DailyRunAdapter()) if has_llm else MockClassifier()
    fallback_classifier = MockClassifier()

    classified_signals = []
    fallback_count = 0
    for index, story in enumerate(stories, start=1):
        signal = {
            "signal_id": story.get("url") or normalize_title(story.get("title", "")) or f"story-{index}",
            "title": story.get("title", ""),
            "body": story.get("body", ""),
            "tags": extract_keywords(f"{story.get('title', '')} {story.get('body', '')}")[:6],
            "source": story.get("source", ""),
            "url": story.get("url", ""),
            "published": story.get("published", ""),
        }
        try:
            classification = classifier.classify(signal)
        except Exception as exc:
            LOGGER.warning("LLM classification failed for signal, falling back to mock: %s", exc)
            classification = fallback_classifier.classify(signal)
            classification["classifier_fallback"] = True
            fallback_count += 1
        classification["title"] = signal["title"]
        classification["source"] = signal["source"]
        classification["url"] = signal["url"]
        classification["published"] = signal["published"]
        classified_signals.append(classification)

    total_classified = len(classified_signals)
    fallback_rate = (fallback_count / total_classified) if total_classified else 0.0
    if fallback_count:
        LOGGER.warning(
            "LLM classification fallback rate: %s/%s signals (%.0f%%)",
            fallback_count,
            total_classified,
            fallback_rate * 100,
        )
    else:
        LOGGER.info("LLM classification fallback rate: 0/%s signals (0%%)", total_classified)

    result = PrioritizationEngine(ensemble, domain_profile).prioritize(classified_signals, budget=10)
    fallback_by_signal_id = {
        str(signal.get("signal_id", "")): bool(signal.get("classifier_fallback", False)) for signal in classified_signals
    }
    ranked_signals = []
    for signal in result.ranked_signals:
        enriched_signal = dict(signal)
        enriched_signal["classifier_fallback"] = fallback_by_signal_id.get(str(signal.get("signal_id", "")), False)
        ranked_signals.append(_normalize_priority_signal(enriched_signal))
    selected_signals = []
    for signal in result.selected_signals:
        enriched_signal = dict(signal)
        enriched_signal["classifier_fallback"] = fallback_by_signal_id.get(str(signal.get("signal_id", "")), False)
        selected_signals.append(_normalize_priority_signal(enriched_signal))

    non_noise_count = sum(1 for priority in ranked_signals if priority.get("category") != "background_noise")
    engine_health = {
        "non_noise_count": non_noise_count,
        "fallback_count": sum(1 for priority in ranked_signals if priority.get("classifier_fallback")),
        "total_count": len(ranked_signals),
    }
    engine_health["non_noise_ratio"] = (
        engine_health["non_noise_count"] / engine_health["total_count"] if engine_health["total_count"] else 0.0
    )
    engine_health["degraded"] = (
        engine_health["non_noise_count"] == 0
        or engine_health["fallback_count"] > engine_health["total_count"] * 0.5
    )
    if engine_health["degraded"]:
        LOGGER.warning(
            "Engine quality degraded: %s/%s fallback classifications, %s non-noise priorities",
            engine_health["fallback_count"],
            engine_health["total_count"],
            engine_health["non_noise_count"],
        )

    mood = dict(result.portfolio_mood)
    mood["emoji"] = mood_emoji(mood.get("label", ""))
    return {
        "priorities": ranked_signals,
        "selected_priorities": selected_signals,
        "mood": mood,
        "engine_health": engine_health,
        "noise_filtered": [signal["title"] for signal in ranked_signals if signal.get("category") == "background_noise"],
    }


def _priority_prediction_text(priority: dict) -> str:
    title = priority.get("title", "this signal")
    category = priority.get("category", "background_noise")
    polarity = int(priority.get("polarity", 0))
    if category == "contested_priority":
        return f"{title} is likely to trigger divergent responses as the underlying direction remains contested."
    if polarity < 0:
        return f"Pressure around {title} is likely to intensify or spill over without intervention."
    if polarity > 0:
        return f"Momentum around {title} is likely to compound if current conditions hold."
    return f"{title} is likely to remain unstable until clearer directional evidence appears."


def generate_predictions(priorities: list[dict]) -> list[dict]:
    """Create lightweight prediction entries from top-ranked priorities."""

    predictions = []
    timelines = {
        "convergent_priority": "1-2 weeks",
        "contested_priority": "2-4 weeks",
        "niche_concern": "4-8 weeks",
        "background_noise": "4-8 weeks",
    }
    severities = {
        "convergent_priority": "high",
        "contested_priority": "high",
        "niche_concern": "medium",
        "background_noise": "low",
    }
    for priority in priorities:
        if priority.get("category") == "background_noise":
            continue
        title = priority.get("title", "Unknown signal")
        predictions.append(
            {
                "root_cause": title,
                "prediction": _priority_prediction_text(priority),
                "timeline": timelines.get(priority.get("category", ""), "2-4 weeks"),
                "falsification": f"Signals tied to {title} fade or reverse without downstream spillover.",
                "severity": severities.get(priority.get("category", ""), "medium"),
            }
        )
        if len(predictions) >= 5:
            break
    return predictions


def build_legacy_root_causes(priorities: list[dict]) -> list[dict]:
    """Map engine priorities to the legacy root_causes shape."""

    severity_map = {
        "convergent_priority": "high",
        "contested_priority": "major",
        "niche_concern": "moderate",
        "background_noise": "low",
    }
    root_causes = []
    for index, priority in enumerate(
        sorted(priorities, key=lambda item: item.get("priority_score", 0.0), reverse=True)[:5],
        start=1,
    ):
        title = _priority_title(priority) or "Unknown signal"
        prediction = _priority_prediction_text(priority)
        top_clusters = ", ".join((priority.get("top_clusters") or {}).keys()) or "mixed personas"
        root_causes.append(
            {
                "id": priority.get("signal_id", normalize_title(title) or f"root-cause-{index}"),
                "rank": index,
                "target": title,
                "title": title,
                "name": title,
                "root_cause": title,
                "severity": severity_map.get(priority.get("category", ""), priority.get("category", "unknown")),
                "category": priority.get("category", "unknown"),
                "priority_score": _coerce_float(priority.get("priority_score", 0.0)),
                "contest_score": _coerce_float(priority.get("contest_score", 0.0)),
                "contestedness": _coerce_float(priority.get("contestedness", 0.0)),
                "mood": signal_direction(priority),
                "rationale": (
                    f"Classified as {category_label(priority.get('category', 'background_noise'))} "
                    f"with {signal_direction(priority)} ensemble direction and strongest pull from {top_clusters}."
                ),
                "signal_count": 1,
                "signals": [title],
                "timeline": "1-4 weeks",
                "intervention": "Monitor the structural drivers and prepare targeted mitigations around the exposed subsystem.",
                "prediction": prediction,
                "falsification": f"Signals tied to {title} fade or reverse without spillover.",
            }
        )
    return root_causes


def generate_narrative(stories: list[dict], priorities: list[dict], mood: dict) -> str:
    """Use LLM to write narrative informed by engine priorities."""

    top_priorities = priorities[:5]
    context = {
        "portfolio_mood": {
            "label": mood.get("label", "cautious"),
            "emoji": mood.get("emoji", "⚪"),
            "score": _coerce_float(mood.get("score", 0.0)),
            "contested_share": _coerce_float(mood.get("contested_share", 0.0)),
        },
        "selected_priorities": [
            {
                "title": _priority_title(priority) or "Unknown",
                "category": priority.get("category", "unknown"),
                "priority_score": _coerce_float(priority.get("priority_score", 0.0)),
                "contestedness": _coerce_float(priority.get("contestedness", 0.0)),
                "contest_score": _coerce_float(priority.get("contest_score", 0.0)),
                "direction": signal_direction(priority),
                "sign_agreement": _coerce_float(priority.get("sign_agreement", 0.0)),
                "top_clusters": priority.get("top_clusters", {}),
                "bottom_clusters": priority.get("bottom_clusters", {}),
            }
            for priority in top_priorities
        ],
        "supporting_signals": [
            {
                "title": story.get("title", ""),
                "source": story.get("source", ""),
                "published": story.get("published", ""),
            }
            for story in stories[:8]
        ],
    }

    prompt = f"""You are writing the daily SIA intelligence briefing narrative.

Use this structured engine output and keep the analysis grounded in the supplied signals:
{json.dumps(context, indent=2, ensure_ascii=False)}

Write a 3-5 paragraph narrative that:
1. Opens with the overall mood and what it means
2. Explains WHY the top signals matter structurally (not just what happened)
3. Notes any contested signals where the ensemble disagreed on direction
4. Connects the signals to longer-term trajectories
5. Closes with what to watch for next

Write as an editorial briefing, not a news summary. Focus on undertones, not headlines."""

    try:
        raw = _chat_completion(
            [
                {"role": "system", "content": "You are the SIA editorial intelligence analyst."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=1200,
            json_mode=False,
        )
        if raw.strip():
            return raw.strip()
    except Exception as exc:  # pragma: no cover - live AOAI only
        LOGGER.warning("Narrative generation fallback used: %s", exc)

    if not priorities:
        return "The portfolio is quiet today, with no structurally significant priorities emerging from the signal set."

    lead = priorities[0]
    contested = [priority for priority in priorities if priority.get("category") == "contested_priority"]
    return (
        f"Today reads as {mood.get('label', 'cautious')} {mood.get('emoji', '⚪')}: the ensemble sees "
        f"{lead.get('title', 'the leading signal')} as the clearest structural priority. "
        f"The emphasis is less about headline volume than about compounding exposure across multiple value clusters. "
        f"{'Several signals remain directionally contested, suggesting unstable adaptation rather than settled change. ' if contested else ''}"
        f"Watch whether these pressures broaden into adjacent systems over the next reporting cycle."
    )


def _priority_key(item: dict) -> str:
    signal_id = str(item.get("signal_id") or item.get("id") or item.get("url") or "").strip()
    if signal_id and signal_id != "signal":
        parsed = urlparse(signal_id)
        normalized_url = f"{parsed.netloc}{parsed.path}".rstrip("/")
        return normalized_url or signal_id
    return normalize_title(_priority_title(item))


def _priority_records(payload: dict) -> list[dict]:
    priorities = payload.get("priorities") or payload.get("selected_priorities")
    if priorities:
        normalized = []
        for item in priorities:
            title = _priority_title(item)
            if not title:
                continue
            normalized.append(
                {
                    **item,
                    "signal_id": item.get("signal_id") or item.get("id") or item.get("url", ""),
                    "title": title,
                    "category": _normalize_priority_category(item.get("category", item.get("severity", ""))),
                    "priority_score": _coerce_float(item.get("priority_score", item.get("priority_raw", 0.0))),
                    "contestedness": _coerce_float(item.get("contestedness", item.get("contest_score", 0.0))),
                }
            )
        return normalized
    legacy = []
    for cause in payload.get("root_causes", []):
        title = _priority_title(cause)
        if not title:
            continue
        legacy.append(
            {
                "signal_id": cause.get("signal_id") or cause.get("id") or cause.get("url", ""),
                "title": title,
                "category": _normalize_priority_category(cause.get("category", cause.get("severity", "unknown"))),
                "priority_score": _coerce_float(cause.get("priority_score", 0.0)),
                "contestedness": _coerce_float(cause.get("contestedness", cause.get("contest_score", 0.0))),
            }
        )
    return [item for item in legacy if _priority_key(item)]


def _signal_freshness(current: dict, previous: dict) -> tuple[int, int, int]:
    prev_titles = {s.get("title", "").lower() for s in previous.get("stories", [])}
    curr_titles = {s.get("title", "").lower() for s in current.get("stories", [])}
    new_stories = len(curr_titles - prev_titles)
    carried_stories = len(curr_titles & prev_titles)
    total_stories = len(current.get("stories", []))
    return new_stories, carried_stories, total_stories


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


def compute_delta(current: dict, previous: dict) -> dict:
    """Compare today's analysis against yesterday's."""
    previous_priorities = {_priority_key(item): item for item in _priority_records(previous)}
    current_priorities = {_priority_key(item): item for item in _priority_records(current)}
    if not previous_priorities:
        return {"is_first_run": True, "summary": "First analysis run — no prior data to compare.", "structural_shifts": []}

    new_convergent = [
        item["title"]
        for key, item in current_priorities.items()
        if key not in previous_priorities and item.get("category") == "convergent_priority"
    ]
    new_contested = [
        item["title"]
        for key, item in current_priorities.items()
        if key not in previous_priorities and item.get("category") == "contested_priority"
    ]
    removed_priorities = [item.get("title", "") for key, item in previous_priorities.items() if key not in current_priorities]
    category_changes = []
    priority_score_changes = []
    for key, item in current_priorities.items():
        if key in previous_priorities:
            prev_category = _normalize_priority_category(previous_priorities[key].get("category", previous_priorities[key].get("severity", "")))
            curr_category = _normalize_priority_category(item.get("category", item.get("severity", "")))
            if prev_category and curr_category and prev_category != curr_category:
                category_changes.append(f"{item.get('title', 'Unknown')}: {prev_category} → {curr_category}")
            prev_score = _coerce_float(previous_priorities[key].get("priority_score", 0.0))
            curr_score = _coerce_float(item.get("priority_score", 0.0))
            if abs(curr_score - prev_score) >= 0.25:
                priority_score_changes.append(
                    f"{item.get('title', 'Unknown')}: {prev_score:.2f} → {curr_score:.2f}"
                )

    previous_mood_payload = _normalize_mood_payload(previous)
    current_mood_payload = _normalize_mood_payload(current)
    previous_mood = previous_mood_payload.get("label", "")
    current_mood = current_mood_payload.get("label", "")
    structural_shifts = []
    mood_shift = ""
    if previous_mood and current_mood:
        if previous_mood != current_mood:
            mood_shift = (
                f"Mood shifted from {previous_mood} ({previous_mood_payload.get('score', 0.0):.2f}) "
                f"to {current_mood} ({current_mood_payload.get('score', 0.0):.2f})"
            )
            structural_shifts.append(f"Mood shifted: {previous_mood} → {current_mood}")
        elif abs(current_mood_payload.get("score", 0.0) - previous_mood_payload.get("score", 0.0)) >= 0.10:
            mood_shift = (
                f"Mood intensity moved within {current_mood}: "
                f"{previous_mood_payload.get('score', 0.0):.2f} → {current_mood_payload.get('score', 0.0):.2f}"
            )

    previous_categories = Counter(item.get("category", "background_noise") for item in _priority_records(previous))
    current_categories = Counter(item.get("category", "background_noise") for item in _priority_records(current))
    for category in ("convergent_priority", "contested_priority", "niche_concern"):
        previous_count = previous_categories.get(category, 0)
        current_count = current_categories.get(category, 0)
        if previous_count != current_count:
            structural_shifts.append(f"{category}: {previous_count} → {current_count}")
    structural_shifts.extend(f"Category change — {change}" for change in category_changes)
    structural_shifts.extend(f"Priority score movement — {change}" for change in priority_score_changes)

    new_stories, carried_stories, total_stories = _signal_freshness(current, previous)
    continuing_priorities = [item.get("title", "") for key, item in current_priorities.items() if key in previous_priorities]

    parts = []
    if new_convergent:
        parts.append(f"{len(new_convergent)} new convergent priorities emerged: {', '.join(new_convergent)}")
    if new_contested:
        parts.append(f"{len(new_contested)} new contested priorities emerged: {', '.join(new_contested)}")
    if removed_priorities:
        parts.append(f"{len(removed_priorities)} priorities dropped: {', '.join(removed_priorities)}")
    if category_changes:
        parts.append(f"Priority category shifted: {'; '.join(category_changes)}")
    if priority_score_changes:
        parts.append(f"Priority intensity moved: {'; '.join(priority_score_changes)}")
    if mood_shift:
        parts.append(mood_shift)
    if structural_shifts:
        parts.append(f"Structural shifts: {'; '.join(structural_shifts)}")
    if not parts:
        parts.append(f"Priority mix broadly stable — {len(continuing_priorities)} priorities carried from yesterday")
    parts.append(f"Signal freshness: {new_stories} new, {carried_stories} carried, {total_stories} total")

    return {
        "is_first_run": False,
        "new_convergent": new_convergent,
        "new_contested": new_contested,
        "removed_priorities": removed_priorities,
        "category_changes": category_changes,
        "priority_score_changes": priority_score_changes,
        "mood_shift": mood_shift,
        "structural_shifts": structural_shifts,
        "continuing_priorities": continuing_priorities,
        "new_stories": new_stories,
        "carried_stories": carried_stories,
        "total_stories": total_stories,
        "summary": " · ".join(parts),
    }


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


def prediction_age_text(prediction: dict, today: str) -> str:
    """Generate a human-readable age/status string for a prediction."""
    created = prediction.get("created_at", "")
    maturity = prediction.get("maturity_date", "")
    status = prediction.get("status", "open")

    if status == "validated":
        return "✓ Validated"
    if status == "falsified":
        return "✗ Falsified"

    if not created:
        return str(status)

    try:
        created_dt = datetime.fromisoformat(created[:10])
        today_dt = datetime.fromisoformat(today[:10])
        elapsed = (today_dt - created_dt).days
    except (ValueError, TypeError):
        return str(status)

    if maturity:
        try:
            maturity_dt = datetime.fromisoformat(maturity[:10])
            remaining = (maturity_dt - today_dt).days
            if remaining <= 0:
                return f"Matured — {elapsed} days elapsed, awaiting validation"
            return f"{elapsed} days elapsed, {remaining} days to maturity"
        except (ValueError, TypeError):
            pass

    return f"{elapsed} days elapsed"


def category_badge_class(category: str) -> str:
    return {
        "convergent_priority": "category-convergent",
        "contested_priority": "category-contested",
        "niche_concern": "category-niche",
        "background_noise": "category-noise",
    }.get((category or "").strip().lower(), "category-noise")


def category_label(category: str) -> str:
    return str(category or "background_noise").replace("_", " ").title()


def signal_direction(priority: dict) -> str:
    polarity = int(priority.get("polarity", 0))
    agreement = float(priority.get("sign_agreement", 0.0))
    if agreement < 0.6:
        return "↔ mixed"
    if polarity > 0:
        return "↗ positive"
    if polarity < 0:
        return "↘ negative"
    return "→ flat"


def build_email_subject(report: dict) -> str:
    priorities = report.get("selected_priorities") or report.get("priorities", [])
    mood = _normalize_mood_payload(report)
    convergent = sum(1 for item in priorities if item.get("category") == "convergent_priority")
    contested = sum(1 for item in priorities if item.get("category") == "contested_priority")
    niche = sum(1 for item in priorities if item.get("category") == "niche_concern")
    noise = sum(1 for item in priorities if item.get("category") == "background_noise")
    return (
        f"[SIA] {mood.get('emoji', '⚪')} {str(mood.get('label', 'unknown')).title()} — "
        f"{convergent} convergent · {contested} contested · {niche} niche · {noise} noise"
    )


def _render_priority_cards(priorities: list[dict], empty_message: str) -> str:
    cards = []
    for priority in priorities:
        cards.append(
            "<div style='background:#f8fafc;border:1px solid #cbd5e1;border-radius:14px;padding:14px;margin:12px 0;'>"
            f"<p style='margin:0 0 8px 0;'><span style='display:inline-block;padding:4px 10px;border-radius:999px;background:#e2e8f0;'>"
            f"{escape(category_label(priority.get('category', 'background_noise')))}</span></p>"
            f"<h3 style='margin:0 0 8px 0;'>{escape(priority.get('title', 'Unknown'))}</h3>"
            f"<p style='margin:0 0 6px 0;'><strong>Priority:</strong> {priority.get('priority_score', 0.0):.2f} "
            f"· <strong>Contestedness:</strong> {priority.get('contestedness', 0.0):.2f}</p>"
            f"<p style='margin:0;'><strong>Direction:</strong> {escape(signal_direction(priority))}</p>"
            "</div>"
        )
    return "".join(cards) or f"<p>{escape(empty_message)}</p>"


def _render_delta_html(delta: dict) -> str:
    """Render the delta comparison as structured HTML with proper formatting."""
    if delta.get("is_first_run"):
        return "<p>First analysis run — no prior data to compare.</p>"

    lines = []
    new_convergent = delta.get("new_convergent", [])
    new_contested = delta.get("new_contested", [])
    removed_priorities = delta.get("removed_priorities", [])
    category_changes = delta.get("category_changes", [])
    priority_score_changes = delta.get("priority_score_changes", [])
    continuing = delta.get("continuing_priorities", [])
    mood_shift = delta.get("mood_shift", "")
    structural_shifts = delta.get("structural_shifts", [])

    if (
        not new_convergent
        and not new_contested
        and not removed_priorities
        and not category_changes
        and not priority_score_changes
        and not mood_shift
        and not structural_shifts
    ):
        lines.append(
            f"<p style='margin:0 0 8px;'><strong>No major reprioritisation</strong> — "
            f"{len(continuing)} priorities carried from yesterday.</p>"
        )
    else:
        if new_convergent:
            items = "".join(f"<li>{escape(item)}</li>" for item in new_convergent)
            lines.append(
                "<p style='margin:0 0 4px;'><strong>Act now:</strong></p>"
                f"<ul style='margin:0 0 8px 20px;padding:0;'>{items}</ul>"
            )
        if new_contested:
            items = "".join(f"<li>{escape(item)}</li>" for item in new_contested)
            lines.append(
                "<p style='margin:0 0 4px;'><strong>Watch closely:</strong></p>"
                f"<ul style='margin:0 0 8px 20px;padding:0;'>{items}</ul>"
            )
        if removed_priorities:
            items = "".join(f"<li>{escape(item)}</li>" for item in removed_priorities)
            lines.append(
                "<p style='margin:0 0 4px;'><strong>Priorities dropped:</strong></p>"
                f"<ul style='margin:0 0 8px 20px;padding:0;'>{items}</ul>"
            )
        if category_changes:
            items = "".join(f"<li>{escape(item)}</li>" for item in category_changes)
            lines.append(
                "<p style='margin:0 0 4px;'><strong>Category shifts:</strong></p>"
                f"<ul style='margin:0 0 8px 20px;padding:0;'>{items}</ul>"
            )
        if priority_score_changes:
            items = "".join(f"<li>{escape(item)}</li>" for item in priority_score_changes)
            lines.append(
                "<p style='margin:0 0 4px;'><strong>Priority intensity:</strong></p>"
                f"<ul style='margin:0 0 8px 20px;padding:0;'>{items}</ul>"
            )
        if mood_shift:
            lines.append(f"<p style='margin:0 0 8px;'><strong>{escape(mood_shift)}</strong>.</p>")
        if structural_shifts:
            items = "".join(f"<li>{escape(item)}</li>" for item in structural_shifts)
            lines.append(
                "<p style='margin:0 0 4px;'><strong>Structural shifts:</strong></p>"
                f"<ul style='margin:0 0 8px 20px;padding:0;'>{items}</ul>"
            )

    new_s = delta.get("new_stories", 0)
    carried_s = delta.get("carried_stories", 0)
    total_s = delta.get("total_stories", 0)
    lines.append(
        f"<p style='margin:0;'><strong>Signal freshness:</strong> {new_s} new, "
        f"{carried_s} carried, {total_s} total.</p>"
    )
    return "".join(lines)


def build_dashboard_html(report: dict, ledger: dict, dashboard_url: str, login_url: str, previous: dict) -> str:
    priorities = report.get("priorities", [])
    mood = report.get("mood", {})
    stories = report.get("stories", [])
    predictions = ledger.get("predictions", [])
    narrative = report.get("narrative", "")
    today = str(report.get("report_date", ""))
    delta = report.get("delta", {})
    delta_html = _render_delta_html(delta)
    engine_health = report.get("engine_health", {})
    degraded_banner = ""
    if engine_health.get("degraded"):
        degraded_banner = (
            "<div style=\"background:#fef2f2;border:2px solid #ef4444;border-radius:12px;padding:16px;margin:16px 0;\">"
            f"<strong>⚠ Engine quality degraded</strong> — {int(engine_health.get('fallback_count', 0))}/{int(engine_health.get('total_count', 0))} "
            "signals used fallback classifier. Priorities may not reflect real structural patterns today."
            "</div>"
        )
    prev_titles = {s.get("title", "").lower() for s in previous.get("stories", [])}
    status_classes = {
        "validated": "status-validated",
        "partially_validated": "status-partial",
        "falsified": "status-falsified",
        "expired": "status-expired",
        "open": "status-open",
    }
    priority_rows = []
    for priority in priorities:
        priority_rows.append(
            f"<tr><td data-label='Signal'>{escape(priority.get('title', 'Unknown'))}</td>"
            f"<td data-label='Priority'>{priority.get('priority_score', 0.0):.2f}</td>"
            f"<td data-label='Contestedness'>{priority.get('contestedness', 0.0):.2f}</td>"
            f"<td data-label='Category'><span class='category-pill {category_badge_class(priority.get('category', ''))}'>{escape(category_label(priority.get('category', '')))}</span></td>"
            f"<td data-label='Direction'>{escape(signal_direction(priority))}</td></tr>"
        )
    contested_rows = []
    for priority in [item for item in priorities if float(item.get("sign_agreement", 0.0)) < 0.6]:
        contested_rows.append(
            f"<tr><td data-label='Signal'>{escape(priority.get('title', 'Unknown'))}</td>"
            f"<td data-label='Agreement'>{priority.get('sign_agreement', 0.0):.2f}</td>"
            f"<td data-label='Contestedness'>{priority.get('contestedness', 0.0):.2f}</td>"
            f"<td data-label='Note'>{escape(signal_direction(priority))}</td></tr>"
        )
    heatmap_rows = []
    for priority in priorities[:8]:
        top_clusters = ", ".join(f"{name} {score:.2f}" for name, score in priority.get("top_clusters", {}).items()) or "—"
        bottom_clusters = ", ".join(f"{name} {score:.2f}" for name, score in priority.get("bottom_clusters", {}).items()) or "—"
        heatmap_rows.append(
            f"<tr><td data-label='Signal'>{escape(priority.get('title', 'Unknown'))}</td>"
            f"<td data-label='Highest'>{escape(top_clusters)}</td>"
            f"<td data-label='Lowest'>{escape(bottom_clusters)}</td></tr>"
        )
    # Strip body snippets from stories for public display — only show title + source + link
    public_stories = []
    for story in stories:
        public_stories.append(
            {
                "title": story.get("title", "Untitled"),
                "source": story.get("source", "Unknown"),
                "url": story.get("url", ""),
                "published": story.get("published", ""),
            }
        )

    story_rows = []
    for story in public_stories:
        is_new = story["title"].lower() not in prev_titles
        badge = (
            "<span style='color:#22c55e;font-size:0.8rem;'>● new</span>"
            if is_new
            else "<span style='color:#94a3b8;font-size:0.8rem;'>↩ carried</span>"
        )
        story_rows.append(
            f"<tr><td data-label='Headline'><a href='{escape(story['url'])}' target='_blank' rel='noreferrer'>{escape(story['title'])}</a> {badge}</td>"
            f"<td data-label='Source'>{escape(story['source'])}</td><td data-label='Published'>{escape(format_human_date(story.get('published')))}</td></tr>"
        )
    prediction_rows = [
        f"<tr><td data-label='Root cause'>{escape(item.get('root_cause', 'Unknown'))}</td>"
        f"<td data-label='Status'><span class='status-pill {status_classes.get(str(item.get('status', 'open')).strip().lower(), 'status-open')}'>{escape(item.get('status', 'open'))}</span></td>"
        f"<td data-label='Created'>{escape(format_human_date(item.get('created_at')))}</td>"
        f"<td data-label='Timeline'>{escape(item.get('timeline', ''))}</td>"
        f"<td data-label='Maturity'>{escape(format_human_date(item.get('maturity_date')))}</td>"
        f"<td data-label='Tracking'>{escape(prediction_age_text(item, today))}</td>"
        f"<td data-label='Notes'>{escape(item.get('validation_notes', item.get('prediction', '')))}</td></tr>"
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
     .delta-note {{
       margin: 18px 0 0;
       padding: 12px 14px;
       background: #f0f4f8;
       border-left: 4px solid #8f4d3f;
       color: #52606d;
       font-size: 0.9rem;
     }}
     .mood-banner {{
       display: inline-flex;
       align-items: center;
       gap: 10px;
       margin-top: 16px;
       padding: 10px 14px;
       border-radius: 999px;
       background: #f4efe6;
       color: var(--ink);
       font-weight: 600;
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
     .category-pill {{
       display: inline-flex;
       align-items: center;
       padding: 4px 10px;
       border-radius: 999px;
       font-size: 0.78rem;
       font-weight: 600;
     }}
     .category-convergent {{ background: rgba(34, 197, 94, 0.14); color: #166534; }}
     .category-contested {{ background: rgba(245, 158, 11, 0.16); color: #9a6700; }}
     .category-niche {{ background: rgba(59, 130, 246, 0.14); color: #1d4ed8; }}
     .category-noise {{ background: var(--pill-bg); color: #6e665d; }}
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
       <p class="meta-line">{len(stories)} stories analysed · {len(priorities)} priorities surfaced · {len(predictions)} predictions tracked</p>
        <div class="mood-banner"><span style="font-size:1.25rem;">{escape(mood.get("emoji", "⚪"))}</span> {escape(str(mood.get("label", "unknown")).title())} · score {float(mood.get("score", 0.0)):.2f}</div>
       {degraded_banner}
        <div class="delta-note"><strong>Since yesterday:</strong><br>{delta_html}</div>
      </section>

     <section>
       <h2>Narrative</h2>
       <p class="narrative">{escape(narrative)}</p>
     </section>

     <section>
       <h2>Priorities</h2>
       <table>
         <thead><tr><th>Signal</th><th>Priority</th><th>Contestedness</th><th>Category</th><th>Direction</th></tr></thead>
         <tbody>{''.join(priority_rows) or '<tr><td colspan="5">No priorities available.</td></tr>'}</tbody>
       </table>
     </section>

     <section>
       <h2>Contested signals</h2>
       <table>
         <thead><tr><th>Signal</th><th>Agreement</th><th>Contestedness</th><th>Note</th></tr></thead>
         <tbody>{''.join(contested_rows) or '<tr><td colspan="4">No materially contested signals.</td></tr>'}</tbody>
       </table>
     </section>

     <section>
       <h2>Cluster heatmap</h2>
       <table>
         <thead><tr><th>Signal</th><th>Highest scoring clusters</th><th>Lowest scoring clusters</th></tr></thead>
         <tbody>{''.join(heatmap_rows) or '<tr><td colspan="3">No cluster data available.</td></tr>'}</tbody>
       </table>
     </section>

     <section>
       <h2>Prediction ledger</h2>
       <table>
         <thead><tr><th>Root cause</th><th>Status</th><th>Created</th><th>Timeline</th><th>Maturity</th><th>Tracking</th><th>Notes</th></tr></thead>
         <tbody>{''.join(prediction_rows) or '<tr><td colspan="7">No predictions logged.</td></tr>'}</tbody>
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


def build_email_html(
    report: dict,
    ledger: dict,
    matured_predictions: list[dict],
    daily_password: str,
    login_url: str,
    dashboard_url: str,
    previous: dict,
) -> str:
    date_label = escape(report.get("report_date", ""))
    priorities = report.get("priorities", [])
    mood = report.get("mood", {})
    today = str(report.get("report_date", ""))
    delta = report.get("delta", {})
    delta_html = _render_delta_html(delta)
    engine_health = report.get("engine_health", {})
    degraded_banner = ""
    if engine_health.get("degraded"):
        degraded_banner = (
            "<div style=\"background:#fef2f2;border:2px solid #ef4444;border-radius:12px;padding:16px;margin:16px 0;\">"
            f"<strong>⚠ Engine quality degraded</strong> — {int(engine_health.get('fallback_count', 0))}/{int(engine_health.get('total_count', 0))} "
            "signals used fallback classifier. Priorities may not reflect real structural patterns today."
            "</div>"
        )
    prev_titles = {s.get("title", "").lower() for s in previous.get("stories", [])}
    act_now = [item for item in priorities if item.get("category") == "convergent_priority"][:5]
    watch_closely = [item for item in priorities if item.get("category") == "contested_priority"][:5]
    niche_concerns = [item for item in priorities if item.get("category") == "niche_concern"][:5]
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

    prediction_rows = "".join(
        f"<tr><td>{escape(item.get('root_cause', 'Unknown'))}</td>"
        f"<td>{escape(item.get('status', 'open'))}</td>"
        f"<td>{escape(format_human_date(item.get('created_at')))}</td>"
        f"<td>{escape(item.get('timeline', ''))}</td>"
        f"<td>{escape(format_human_date(item.get('maturity_date')))}</td>"
        f"<td>{escape(prediction_age_text(item, today))}</td>"
        f"<td>{escape(item.get('validation_notes', item.get('prediction', '')))}</td></tr>"
        for item in ledger.get("predictions", [])
    ) or "<tr><td colspan='7'>No predictions logged.</td></tr>"

    story_rows = "".join(
        f"<tr><td><a href='{escape(story.get('url', ''))}'>{escape(story.get('title', 'Untitled'))}</a> "
        f"{'🆕' if story.get('title', '').lower() not in prev_titles else '↩'}</td>"
        f"<td>{escape(story.get('source', 'Unknown'))}</td>"
        f"<td>{escape(format_human_date(story.get('published')))}</td></tr>"
        for story in report.get("stories", [])
    ) or "<tr><td colspan='3'>No stories available.</td></tr>"

    return f"""<html>
<body style="margin:0;background:#e2e8f0;font-family:Segoe UI,Arial,sans-serif;color:#0f172a;">
  <div style="max-width:900px;margin:0 auto;padding:24px;">
    <div style="background:#0f172a;color:#f8fafc;border-radius:20px;padding:28px;">
      <p style="margin:0 0 8px 0;text-transform:uppercase;letter-spacing:.08em;color:#93c5fd;">SIA Daily Intelligence</p>
      <h1 style="margin:0 0 8px 0;">{date_label}</h1>
      <p style="margin:0;">Daily systemic intelligence summary and validation digest.</p>
      <p style="margin:16px 0 0 0;display:inline-flex;align-items:center;gap:8px;background:#1e293b;border-radius:999px;padding:10px 14px;">
        <span style="font-size:20px;">{escape(mood.get("emoji", "⚪"))}</span>
        <span>{escape(str(mood.get("label", "unknown")).title())} · score {float(mood.get("score", 0.0)):.2f}</span>
      </p>
    </div>

    <div style="background:#ffffff;border-radius:20px;padding:24px;margin-top:18px;">
      <h2>Summary</h2>
      <ul>
        <li>{len(report.get('stories', []))} stories analysed</li>
        <li>{len(priorities)} priorities surfaced</li>
        <li>{len(ledger.get('predictions', []))} predictions tracked</li>
      </ul>
      <div style="margin:18px 0 0;padding:14px 16px;background:#f0f4f8;border-left:4px solid #8f4d3f;color:#374151;font-size:14px;line-height:1.6;">
        <strong style="display:block;margin-bottom:8px;color:#1a1a1a;">Since yesterday:</strong>
        {delta_html}
      </div>
      {degraded_banner}

      <h2>Act now</h2>
      {_render_priority_cards(act_now, "No convergent priorities today.")}

      <h2>Watch closely</h2>
      {_render_priority_cards(watch_closely, "No contested priorities today.")}

      <h2>Niche concerns</h2>
      {_render_priority_cards(niche_concerns, "No niche concerns rose above the background today.")}

      <h2>Narrative</h2>
      <p>{escape(report.get('narrative', ''))}</p>
      {matured_markup}

      <h2 style='margin-top:32px;'>Delta</h2>
      <div style="padding:14px 16px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:14px;">
        {delta_html}
      </div>

      <h2 style='margin-top:32px;'>Prediction ledger</h2>
      <table style="width:100%;border-collapse:collapse;">
        <tr>
          <th align="left">Root cause</th><th align="left">Status</th><th align="left">Created</th>
          <th align="left">Timeline</th><th align="left">Maturity</th><th align="left">Tracking</th><th align="left">Notes</th>
        </tr>
        {prediction_rows}
      </table>

      <h2 style='margin-top:32px;'>Signals analysed</h2>
      <table style="width:100%;border-collapse:collapse;">
        <tr><th align="left">Headline</th><th align="left">Source</th><th align="left">Published</th></tr>
        {story_rows}
      </table>

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


def _load_from_github(path: str) -> dict | None:
    """Load a JSON file from the GitHub repo (persists across ephemeral CI runners)."""
    token = os.environ.get("GITHUB_TOKEN", "")
    repo = os.environ.get("SIA_GITHUB_REPO", "")
    if not token or not repo:
        return None
    try:
        api_url = f"https://api.github.com/repos/{repo}/contents/{path}"
        resp = requests.get(api_url, headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3.raw",
        }, timeout=15)
        if resp.status_code == 200:
            return json.loads(resp.text)
    except Exception:
        pass
    return None


def run_daily_pipeline() -> dict:
    logging.basicConfig(level=logging.INFO)
    # Use AEST (UTC+10) for the report date since the cron runs at 20:00 UTC = 6:00 AM AEST next day
    aest = timezone(timedelta(hours=10))
    report_date = datetime.now(aest).strftime("%Y-%m-%d")
    dashboard_url = os.environ.get("SIA_DASHBOARD_URL", "")
    login_base_url = os.environ.get("SIA_LOGIN_URL", dashboard_url.rstrip("/") + "/chat.html" if dashboard_url else "")

    # Load previous analysis from GitHub (persists) then local fallback
    previous = _load_from_github("docs/data.json") or load_json_document("latest_analysis.json", {})
    LOGGER.info("Previous analysis loaded: report_date=%s", previous.get("report_date", "none"))

    # Load prediction ledger from GitHub (persists) then local fallback
    ledger = _load_from_github("docs/prediction_ledger.json") or load_json_document("prediction_ledger.json", {"predictions": [], "last_updated": None})

    stories = collect_stories(max_stories=20)
    core_analysis = run_core_analysis(stories)
    priorities = core_analysis.get("priorities", [])
    selected_priorities = core_analysis.get("selected_priorities") or priorities[:10]
    mood = core_analysis.get("mood", {"label": "cautious", "score": 0.0, "emoji": "🟡"})
    narrative = generate_narrative(stories, selected_priorities, mood)
    predictions = generate_predictions(selected_priorities)

    merged_predictions = merge_predictions(ledger.get("predictions", []), predictions, report_date)
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
        "priorities": priorities,
        "selected_priorities": selected_priorities,
        "mood": mood,
        "root_causes": build_legacy_root_causes(priorities),
        "predictions": predictions,
        "narrative": narrative,
        "noise_filtered": core_analysis.get("noise_filtered", []),
        "matured_predictions": matured_predictions,
    }
    report["delta"] = compute_delta(report, previous)

    save_json_document("latest_analysis.json", report)
    save_json_document("prediction_ledger.json", ledger)
    save_json_document("prediction_schedule.json", schedule)

    dashboard_html = build_dashboard_html(report, ledger, dashboard_url, login_url, previous)
    email_html = build_email_html(
        report,
        ledger,
        matured_predictions,
        daily_password,
        login_url,
        dashboard_url,
        previous,
    )

    # Upload dashboard and analysis data to GitHub Pages
    _upload_to_github_pages(dashboard_html)
    _upload_github_file("docs/data.json", json.dumps(report, indent=2, ensure_ascii=False))
    _upload_github_file("docs/prediction_ledger.json", json.dumps(ledger, indent=2, ensure_ascii=False))
    # chat_config.json contains the Azure OpenAI API key. The file is not linked from the public dashboard,
    # robots.txt blocks crawlers, and the chat page is token-gated. Rotate the key if compromised.
    chat_config = {
        "endpoint": os.environ.get("AZURE_OPENAI_ENDPOINT", ""),
        "deployment": os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o"),
        "api_version": os.environ.get("AZURE_OPENAI_API_VERSION", "2024-10-21"),
        "key": os.environ.get("AZURE_OPENAI_KEY", ""),
    }
    if chat_config["endpoint"] and chat_config["key"]:
        _upload_github_file("docs/chat_config.json", json.dumps(chat_config))
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
        build_email_subject(report),
        email_html,
        os.environ.get("ACS_CONNECTION_STRING", ""),
    )

    summary = {
        "report_date": report_date,
        "stories": len(stories),
        "priorities": len(priorities),
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
