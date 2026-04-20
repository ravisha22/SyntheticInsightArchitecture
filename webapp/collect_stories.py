"""Collect top news stories from RSS feeds and convert to SIA signals."""
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import requests

FEEDS = [
    {"name": "Reuters World", "url": "https://feeds.reuters.com/reuters/worldNews"},
    {"name": "BBC World", "url": "http://feeds.bbci.co.uk/news/world/rss.xml"},
    {"name": "Al Jazeera", "url": "https://www.aljazeera.com/xml/rss/all.xml"},
    {"name": "ABC Australia", "url": "https://www.abc.net.au/news/feed/2942460/rss.xml"},
    {"name": "AP News", "url": "https://rsshub.app/apnews/topics/apf-topnews"},
]

DATA_DIR = Path(__file__).parent / "data"
USER_AGENT = "SIA-NewsCollector/1.0"


def _clean_text(value: str) -> str:
    text = re.sub(r"<[^>]+>", "", value or "")
    return re.sub(r"\s+", " ", text).strip()


def _find_text(element: ET.Element, *names: str) -> str:
    for name in names:
        found = element.find(name)
        if found is not None and found.text:
            return _clean_text(found.text)
    return ""


def _parse_rss_items(root: ET.Element, feed_name: str) -> list[dict]:
    stories = []
    for item in root.iter("item"):
        title = _find_text(item, "title")
        if not title:
            continue

        link = _find_text(item, "link")
        pub = _find_text(item, "pubDate", "published", "updated")
        desc = _find_text(item, "description", "summary", "content")
        stories.append(
            {
                "title": title,
                "body": desc[:500],
                "source": feed_name,
                "url": link,
                "published": pub,
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

        summary = _find_text(
            entry,
            "{http://www.w3.org/2005/Atom}summary",
            "{http://www.w3.org/2005/Atom}content",
        )
        published = _find_text(
            entry,
            "{http://www.w3.org/2005/Atom}published",
            "{http://www.w3.org/2005/Atom}updated",
        )
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
                "body": summary[:500],
                "source": feed_name,
                "url": link,
                "published": published,
            }
        )
    return stories


def fetch_feed(feed: dict, timeout: int = 15) -> list[dict]:
    """Fetch and parse an RSS or Atom feed, return list of story dicts."""
    try:
        resp = requests.get(
            feed["url"],
            timeout=timeout,
            headers={"User-Agent": USER_AGENT},
        )
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
    except Exception as exc:
        print(f"  [SKIP] {feed['name']}: {exc}")
        return []

    stories = _parse_rss_items(root, feed["name"])
    if stories:
        return stories
    return _parse_atom_entries(root, feed["name"])


def deduplicate(stories: list[dict]) -> list[dict]:
    """Remove duplicate stories by normalized title."""
    seen = set()
    unique = []
    for story in stories:
        key = re.sub(r"[^a-z0-9]", "", story["title"].lower())[:80]
        if key and key not in seen:
            seen.add(key)
            unique.append(story)
    return unique


def stories_to_signals(stories: list[dict], max_signals: int = 20) -> list[dict]:
    """Convert raw stories to SIA signal format."""
    signals = []
    for index, story in enumerate(stories[:max_signals], start=1):
        signals.append(
            {
                "number": index,
                "signal_type": "community_report",
                "source": story["source"].lower().replace(" ", "-"),
                "title": story["title"],
                "body": story["body"],
                "labels": [],
                "url": story.get("url", ""),
                "published": story.get("published", ""),
            }
        )
    return signals


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print("Collecting stories from RSS feeds...")

    all_stories = []
    for feed in FEEDS:
        print(f"  Fetching: {feed['name']}")
        stories = fetch_feed(feed)
        print(f"    Got {len(stories)} stories")
        all_stories.extend(stories)

    unique = deduplicate(all_stories)
    print(f"\nTotal unique stories: {len(unique)}")

    top = unique[:20]
    signals = stories_to_signals(top)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    output = {
        "collected_at": timestamp,
        "story_count": len(top),
        "signal_count": len(signals),
        "stories": top,
        "signals": signals,
    }

    outfile = DATA_DIR / f"stories_{timestamp}.json"
    outfile.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved to: {outfile}")

    latest = DATA_DIR / "latest_stories.json"
    latest.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Updated: {latest}")


if __name__ == "__main__":
    main()
