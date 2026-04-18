"""Real-issue scenario builder for blinded SIA experiments."""
from __future__ import annotations

import json
import math
import os
import random
import re
import time
from collections import Counter
from datetime import datetime
from itertools import combinations
from pathlib import Path
from typing import Iterable

import requests

DATE_START = "2020-01-01"
DATE_END = "2022-06-30"
DEFAULT_LIMIT = 120
RANDOM_SEED = 7
PANDAS_LABELS = [
    "Bug",
    "Indexing",
    "Dtype",
    "Copy / view semantics",
    "Performance",
    "Missing-data",
    "ExtensionArray",
]
STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "can", "cannot", "could",
    "did", "do", "does", "for", "from", "get", "got", "had", "has", "have", "how",
    "if", "in", "into", "is", "it", "its", "may", "might", "more", "not", "of", "on",
    "or", "our", "should", "so", "such", "than", "that", "the", "their", "them", "then",
    "there", "these", "this", "those", "to", "too", "up", "use", "using", "was", "we",
    "were", "what", "when", "where", "which", "while", "who", "why", "will", "with",
    "would", "yet", "you", "your",
}
TOKEN_RE = re.compile(r"[a-z0-9_]+")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _cache_dir() -> Path:
    path = _repo_root() / "simulation" / "cache"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _stable_unique(values: Iterable[str]) -> list[str]:
    seen = set()
    ordered: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered


def clip_text(text: str | None, limit: int) -> str:
    text = (text or "").replace("\r", " ").replace("\n", " ").strip()
    return text[:limit]


def tokenize_title(text: str | None) -> list[str]:
    tokens: list[str] = []
    for token in TOKEN_RE.findall((text or "").lower()):
        if token in STOP_WORDS:
            continue
        if len(token) == 1 and not token.isdigit():
            continue
        tokens.append(token)
    return tokens


def issue_to_tags(title: str, labels: list[str]) -> list[str]:
    return _stable_unique(tokenize_title(title) + labels)


def cycle_from_created_at(created_at: str) -> int:
    dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    return (dt.year - 2020) * 12 + dt.month


def compute_stake_weight(issue: dict) -> float:
    comments = int(issue.get("comments", 0))
    if comments >= 10:
        return 2.0
    if comments >= 5:
        return 1.5
    return 1.0


def simplify_issue(issue: dict) -> dict:
    labels = [label["name"] for label in issue.get("labels", [])]
    return {
        "number": issue["number"],
        "title": issue["title"],
        "body": clip_text(issue.get("body", ""), 500),
        "labels": labels,
        "created_at": issue["created_at"],
        "closed_at": issue.get("closed_at"),
        "comments": issue.get("comments", 0),
    }


def prepare_issue(issue: dict) -> dict:
    prepared = dict(issue)
    prepared["description"] = clip_text(issue.get("body", ""), 200)
    prepared["tags"] = issue_to_tags(issue["title"], issue.get("labels", []))
    prepared["cycle"] = cycle_from_created_at(issue["created_at"])
    prepared["stake_weight"] = compute_stake_weight(issue)
    return prepared


def _cache_path(name: str) -> Path:
    return _cache_dir() / f"{name}.json"


class GitHubIssueFetcher:
    def __init__(self, token: str | None = None, sleep_seconds: float = 1.0):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/vnd.github+json",
                "User-Agent": "sia-blinded-test",
            }
        )
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"
        self.sleep_seconds = sleep_seconds

    def _request(self, url: str, params: dict) -> dict:
        response = self.session.get(url, params=params, timeout=30)
        if response.status_code == 403 and response.headers.get("X-RateLimit-Remaining") == "0":
            reset_at = int(response.headers.get("X-RateLimit-Reset", "0"))
            wait_seconds = max(reset_at - int(time.time()) + 1, 1)
            time.sleep(min(wait_seconds, 60))
            response = self.session.get(url, params=params, timeout=30)
        response.raise_for_status()
        remaining = response.headers.get("X-RateLimit-Remaining")
        if remaining == "0":
            reset_at = int(response.headers.get("X-RateLimit-Reset", "0"))
            wait_seconds = max(reset_at - int(time.time()) + 1, 1)
            time.sleep(min(wait_seconds, 60))
        else:
            time.sleep(self.sleep_seconds)
        return response.json()

    def search_issues(self, query: str, page: int = 1, per_page: int = 100) -> list[dict]:
        payload = self._request(
            "https://api.github.com/search/issues",
            {"q": query, "sort": "created", "order": "asc", "page": page, "per_page": per_page},
        )
        return payload.get("items", [])


def _load_cached_issues(cache_name: str) -> list[dict] | None:
    path = _cache_path(cache_name)
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as handle:
        cached = json.load(handle)
    return cached.get("issues", [])


def _write_cache(cache_name: str, issues: list[dict]) -> None:
    with _cache_path(cache_name).open("w", encoding="utf-8") as handle:
        json.dump({"issues": issues}, handle, indent=2)


def _balanced_issue_selection(issues: list[dict], labels: list[str], limit: int) -> list[dict]:
    ordered = sorted(issues, key=lambda issue: (issue["created_at"], issue["number"]))
    buckets = {
        label: [issue for issue in ordered if label in issue.get("labels", [])]
        for label in labels
    }
    indices = {label: 0 for label in labels}
    selected: dict[int, dict] = {}

    while len(selected) < limit:
        progressed = False
        for label in labels:
            bucket = buckets[label]
            while indices[label] < len(bucket) and bucket[indices[label]]["number"] in selected:
                indices[label] += 1
            if indices[label] >= len(bucket):
                continue
            issue = bucket[indices[label]]
            selected[issue["number"]] = issue
            indices[label] += 1
            progressed = True
            if len(selected) >= limit:
                break
        if not progressed:
            break

    for issue in ordered:
        selected.setdefault(issue["number"], issue)
        if len(selected) >= limit:
            break

    return sorted(selected.values(), key=lambda issue: (issue["created_at"], issue["number"]))


def fetch_label_filtered_issues(
    repo: str,
    labels: list[str],
    limit: int = DEFAULT_LIMIT,
    start: str = DATE_START,
    end: str = DATE_END,
    cache_name: str = "pandas_real",
) -> list[dict]:
    cached = _load_cached_issues(cache_name)
    if cached:
        return [prepare_issue(issue) for issue in cached[:limit]]

    fetcher = GitHubIssueFetcher(os.getenv("GITHUB_TOKEN"))
    unique_issues: dict[int, dict] = {}
    pages = {label: 1 for label in labels}
    exhausted: set[str] = set()

    while len(unique_issues) < limit and len(exhausted) < len(labels):
        for label in labels:
            if label in exhausted:
                continue
            query = (
                f'repo:{repo} is:issue is:closed created:{start}..{end} '
                f'label:"{label}"'
            )
            items = fetcher.search_issues(query, page=pages[label], per_page=100)
            if not items:
                exhausted.add(label)
                continue
            for item in items:
                if "pull_request" in item:
                    continue
                unique_issues[item["number"]] = simplify_issue(item)
            pages[label] += 1
            if len(items) < 100 or pages[label] > 3:
                exhausted.add(label)
            if len(unique_issues) >= limit * 2:
                break

    issues = _balanced_issue_selection(list(unique_issues.values()), labels, limit)
    _write_cache(cache_name, issues)
    return [prepare_issue(issue) for issue in issues]


def fetch_closed_issues(
    repo: str,
    limit: int = 100,
    start: str = DATE_START,
    end: str = DATE_END,
    cache_name: str = "nonconvergent_requests",
) -> list[dict]:
    cached = _load_cached_issues(cache_name)
    if cached:
        return [prepare_issue(issue) for issue in cached[:limit]]

    fetcher = GitHubIssueFetcher(os.getenv("GITHUB_TOKEN"))
    issues: list[dict] = []
    page = 1

    while len(issues) < limit:
        query = f"repo:{repo} is:issue is:closed created:{start}..{end}"
        items = fetcher.search_issues(query, page=page, per_page=100)
        if not items:
            break
        for item in items:
            if "pull_request" in item:
                continue
            issues.append(simplify_issue(item))
            if len(issues) >= limit:
                break
        if len(items) < 100:
            break
        page += 1

    issues = sorted(issues, key=lambda issue: (issue["created_at"], issue["number"]))[:limit]
    _write_cache(cache_name, issues)
    return [prepare_issue(issue) for issue in issues]


def issue_to_event(issue: dict) -> dict:
    return {
        "cycle": issue["cycle"],
        "type": "tension",
        "data": {
            "title": issue["title"],
            "description": issue["description"],
            "stake_weight": issue["stake_weight"],
            "tags": issue["tags"],
            "issue_number": issue["number"],
            "labels": issue["labels"],
        },
    }


def shuffle_issue_tags(issues: list[dict], seed: int = RANDOM_SEED) -> list[dict]:
    rng = random.Random(seed)
    shuffled = [dict(issue) for issue in issues]
    all_tags = [tag for issue in shuffled for tag in issue["tags"]]
    rng.shuffle(all_tags)

    cursor = 0
    for issue in shuffled:
        tag_count = len(issue["tags"])
        reassigned = _stable_unique(all_tags[cursor:cursor + tag_count])
        cursor += tag_count
        issue["tags"] = reassigned or issue["tags"][:1]
    return shuffled


def _is_token_tag(tag: str) -> bool:
    return bool(tag) and " " not in tag and "/" not in tag


def _tag_document_frequency(issues: list[dict]) -> Counter:
    frequencies: Counter = Counter()
    for issue in issues:
        frequencies.update(set(issue["tags"]))
    return frequencies


def _idf(total_issues: int, count: int) -> float:
    return math.log((total_issues + 1) / (count + 1)) + 1.0


def build_data_derived_seed_specs(
    issues: list[dict],
    max_seeds: int = 6,
    min_support: int = 5,
) -> list[dict]:
    tag_df = _tag_document_frequency(issues)
    total = max(len(issues), 1)
    candidate_tags = {
        tag
        for tag, count in tag_df.items()
        if count >= min_support
        and count < total * 0.45
        and not tag.isdigit()
        and (len(tag) >= 4 or not _is_token_tag(tag))
    }
    pair_scores: list[tuple[float, tuple[str, str], list[dict]]] = []

    for first, second in combinations(sorted(candidate_tags), 2):
        supporting = [
            issue
            for issue in issues
            if first in issue["tags"] and second in issue["tags"]
        ]
        if len(supporting) < min_support:
            continue
        score = len(supporting) * (_idf(total, tag_df[first]) + _idf(total, tag_df[second]))
        pair_scores.append((score, (first, second), supporting))

    pair_scores.sort(key=lambda item: (-item[0], item[1]))
    seed_specs: list[dict] = []
    used_tag_sets: list[set[str]] = []

    for _, pair, supporting in pair_scores:
        tag_scores: Counter = Counter()
        for issue in supporting:
            for tag in set(issue["tags"]):
                weight = _idf(total, tag_df[tag])
                if _is_token_tag(tag):
                    weight += 0.2
                tag_scores[tag] += weight
        cluster_tags = [pair[0], pair[1]]
        cluster_tags.extend(
            tag
            for tag, _ in sorted(tag_scores.items(), key=lambda item: (-item[1], item[0]))
            if tag not in pair
        )
        cluster_tags = _stable_unique(cluster_tags)[:5]
        cluster_set = set(cluster_tags)
        if any(len(cluster_set & existing) >= 3 for existing in used_tag_sets):
            continue
        cycles = sorted(issue["cycle"] for issue in supporting)
        seed_specs.append(
            {
                "description": "Recurring issue cluster around: " + ", ".join(cluster_tags),
                "tags": cluster_tags,
                "cycle": cycles[0],
                "support_count": len(supporting),
                "issue_numbers": [issue["number"] for issue in supporting],
            }
        )
        used_tag_sets.append(cluster_set)
        if len(seed_specs) >= max_seeds:
            break

    return seed_specs


def derive_neutral_seed_tags(
    issues: list[dict],
    description: str,
    top_n: int = 4,
) -> list[str]:
    description_tokens = set(tokenize_title(description))
    tag_df = _tag_document_frequency(issues)
    total = max(len(issues), 1)
    supporting = [
        issue
        for issue in issues
        if description_tokens & set(tokenize_title(issue["title"]))
        or description_tokens & {label.lower() for label in issue["labels"]}
    ]
    supporting = supporting or issues
    tag_scores: Counter = Counter()
    for issue in supporting:
        for tag in set(issue["tags"]):
            bonus = 1.5 if tag.lower() in description_tokens else 1.0
            if _is_token_tag(tag):
                bonus += 0.2
            tag_scores[tag] += bonus * _idf(total, tag_df[tag])
    ordered = [
        tag
        for tag, _ in sorted(tag_scores.items(), key=lambda item: (-item[1], item[0]))
        if _is_token_tag(tag)
    ]
    return _stable_unique(ordered)[:top_n]


def estimate_seed_cycle(issues: list[dict], tags: list[str], fallback: int = 6) -> int:
    supporting_cycles = [
        issue["cycle"]
        for issue in issues
        if set(tags) & set(issue["tags"])
    ]
    if not supporting_cycles:
        return fallback
    supporting_cycles.sort()
    return supporting_cycles[len(supporting_cycles) // 2]


def build_seed_events(seed_specs: list[dict]) -> list[dict]:
    return [
        {"cycle": spec["cycle"], "type": "seed", "data": {"description": spec["description"], "tags": spec["tags"]}}
        for spec in seed_specs
    ]


def load_pandas_issues(limit: int = DEFAULT_LIMIT) -> list[dict]:
    return fetch_label_filtered_issues(
        repo="pandas-dev/pandas",
        labels=PANDAS_LABELS,
        limit=limit,
        cache_name=f"pandas_real_v2_{limit}",
    )


def build_pandas_scenario(
    limit: int = DEFAULT_LIMIT,
    include_data_derived_seeds: bool = True,
    shuffle_tags: bool = False,
) -> dict:
    issues = load_pandas_issues(limit)
    issues = shuffle_issue_tags(issues) if shuffle_tags else issues
    events = [issue_to_event(issue) for issue in issues]
    seed_specs: list[dict] = []
    if include_data_derived_seeds:
        seed_specs = build_data_derived_seed_specs(issues)
        events.extend(build_seed_events(seed_specs))
    return {
        "issues": issues,
        "events": sorted(events, key=lambda event: (event["cycle"], event["type"] != "tension")),
        "seed_specs": seed_specs,
    }


def build_tag_shuffle_control(limit: int = DEFAULT_LIMIT) -> dict:
    return build_pandas_scenario(limit=limit, include_data_derived_seeds=True, shuffle_tags=True)
