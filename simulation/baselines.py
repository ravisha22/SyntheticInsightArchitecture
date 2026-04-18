"""Simple comparison baselines for blinded SIA experiments."""
from __future__ import annotations

import re
from collections import Counter
from itertools import combinations

STOP_WORDS = {
    "the",
    "and",
    "for",
    "with",
    "after",
    "before",
    "from",
    "into",
    "that",
    "this",
    "when",
    "what",
    "same",
    "across",
    "between",
    "still",
    "uses",
}


def tokenize_title(title: str) -> list[str]:
    return [
        token
        for token in re.findall(r"[a-z0-9]+", title.lower())
        if len(token) > 3 and token not in STOP_WORDS
    ]


def keyword_frequency(issues: list[dict], top_n: int = 20) -> dict:
    counts: Counter = Counter()
    issue_terms: dict[int, list[str]] = {}
    for issue in issues:
        terms = tokenize_title(issue["title"])
        issue_terms[issue["number"]] = terms
        counts.update(terms)

    top_terms = [{"term": term, "count": count} for term, count in counts.most_common(top_n)]
    groups = []
    for term_info in top_terms[:10]:
        term = term_info["term"]
        members = [
            issue["number"]
            for issue in issues
            if term in issue_terms[issue["number"]]
        ]
        if len(members) < 3:
            continue
        groups.append({"term": term, "count": len(members), "issues": members[:20]})
        if len(groups) == 5:
            break

    return {"top_terms": top_terms, "groups": groups}


def label_cooccurrence(issues: list[dict], top_clusters: int = 3) -> dict:
    pair_counts: Counter = Counter()
    issue_labels = {issue["number"]: sorted(set(issue["labels"])) for issue in issues}

    for labels in issue_labels.values():
        for pair in combinations(labels, 2):
            pair_counts[pair] += 1

    clusters = []
    seen_signatures: set[tuple[str, ...]] = set()
    for pair, count in pair_counts.most_common(15):
        supporting = [
            issue_number
            for issue_number, labels in issue_labels.items()
            if pair[0] in labels and pair[1] in labels
        ]
        third_counts: Counter = Counter()
        for issue_number in supporting:
            labels = issue_labels[issue_number]
            for label in labels:
                if label not in pair:
                    third_counts[label] += 1
        cluster_labels = list(pair)
        if third_counts:
            third_label, third_count = third_counts.most_common(1)[0]
            if third_count >= 2:
                cluster_labels.append(third_label)
        signature = tuple(sorted(cluster_labels))
        if signature in seen_signatures:
            continue
        seen_signatures.add(signature)
        clusters.append(
            {
                "labels": cluster_labels,
                "count": count,
                "issues": supporting[:20],
            }
        )
        if len(clusters) >= top_clusters:
            break

    return {
        "pairs": [{"labels": list(pair), "count": count} for pair, count in pair_counts.most_common(10)],
        "clusters": clusters,
    }


def run_baselines(issues: list[dict]) -> dict:
    keywords = keyword_frequency(issues)
    labels = label_cooccurrence(issues)
    return {"keyword_frequency": keywords, "label_cooccurrence": labels}
