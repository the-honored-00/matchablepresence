#!/usr/bin/env python3
"""Fetch the Anime News Network RSS feed and write news.json for the site."""

import html
import json
import logging
import os
import re
import sys
import tempfile
from calendar import timegm
from datetime import datetime, timezone

import feedparser
import requests

RSS_URL = "https://www.animenewsnetwork.com/all/rss.xml"
USER_AGENT = "matchablepresence-news/1.0"
TIMEOUT = 15
MAX_ITEMS = 60
MAX_SUMMARY = 140

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "news.json")

IMAGE_EXT = re.compile(r"\.(jpe?g|png|webp|gif)(\?|$)", re.IGNORECASE)
DEFAULT_SUMMARY = "Read the full update on Anime News Network."

log = logging.getLogger("news")

def _looks_like_image(url, mime=""):
    return bool(url) and (mime.startswith("image/") or bool(IMAGE_EXT.search(url)))

def extract_image(entry):
    for media in entry.get("media_content", []) or []:
        url = media.get("url", "")
        if _looks_like_image(url, media.get("type", "")):
            return url

    for thumb in entry.get("media_thumbnail", []) or []:
        if thumb.get("url"):
            return thumb["url"]

    for enc in entry.get("enclosures", []) or []:
        url = enc.get("href", "")
        if _looks_like_image(url, enc.get("type", "")):
            return url

    raw = ""
    if entry.get("content"):
        raw = entry.content[0].get("value", "")
    raw = raw or entry.get("summary", "")
    match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', raw)
    if match:
        url = match.group(1)
        return "https:" + url if url.startswith("//") else url

    return ""

def clean_text(text):
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()

def shorten(text, limit=MAX_SUMMARY):
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0] or text[:limit]
    return cut.rstrip(".,;:") + "…"

def parse_date(entry):
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed:
        return datetime.fromtimestamp(timegm(parsed), tz=timezone.utc).isoformat()
    return datetime.now(timezone.utc).isoformat()

def fetch_items():
    response = requests.get(RSS_URL, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
    response.raise_for_status()

    feed = feedparser.parse(response.content)
    if feed.bozo and not feed.entries:
        raise RuntimeError(f"Could not parse feed: {feed.get('bozo_exception')}")

    items = []
    for entry in feed.entries:
        link = (entry.get("link") or "").strip()
        title = clean_text(entry.get("title", ""))
        if not link or not title:
            continue

        summary = clean_text(entry.get("summary", "")) or DEFAULT_SUMMARY
        items.append({
            "id": link,
            "title": title,
            "link": link,
            "summary": shorten(summary),
            "image": extract_image(entry),
            "published": parse_date(entry),
        })
    return items

def load_existing():
    if not os.path.exists(DATA_PATH):
        return []
    try:
        with open(DATA_PATH, encoding="utf-8") as f:
            return json.load(f).get("items", [])
    except (json.JSONDecodeError, OSError) as exc:
        log.warning("Could not read existing news.json (%s); starting fresh.", exc)
        return []

def merge(new_items, old_items):
    by_id = {}
    for item in old_items + new_items:
        by_id[item["id"]] = item
    merged = sorted(by_id.values(), key=lambda i: i["published"], reverse=True)
    return merged[:MAX_ITEMS]

def save(items):
    payload = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "items": items,
    }
    fd, tmp_path = tempfile.mkstemp(dir=BASE_DIR, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, DATA_PATH)

def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        new_items = fetch_items()
    except Exception:
        log.exception("Fetching the feed failed")
        return 1

    if not new_items:
        log.error("Feed returned no usable items")
        return 1

    items = merge(new_items, load_existing())
    save(items)
    log.info("Saved %d items (%d fetched this run)", len(items), len(new_items))
    return 0

if __name__ == "__main__":
    sys.exit(main())
