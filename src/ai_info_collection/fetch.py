from __future__ import annotations

import hashlib
import re
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

from ai_info_collection.models import SignalInput, Source
from ai_info_collection.scrapling_adapter import fetch_html
from ai_info_collection.storage import SQLiteStore


@dataclass(slots=True)
class FetchStats:
    total_sources: int = 0
    success_sources: int = 0
    failed_sources: int = 0
    fetched_items: int = 0
    parsed_items: int = 0


def _utc_iso_now() -> str:
    return datetime.now(UTC).isoformat()


def _strip_tags(html: str) -> str:
    text = re.sub(r"(?is)<script.*?>.*?</script>", " ", html)
    text = re.sub(r"(?is)<style.*?>.*?</style>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _normalize_published(value: str) -> str:
    text = value.strip()
    if not text:
        return _utc_iso_now()
    if text.endswith("Z") and "T" in text:
        return text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC).isoformat()
    except ValueError:
        pass
    try:
        parsed = parsedate_to_datetime(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC).isoformat()
    except (TypeError, ValueError):
        return _utc_iso_now()


def _extract_by_selector(html: str, selector: str | None) -> str:
    if not selector:
        return ""
    selector = selector.strip()
    if not selector:
        return ""
    if selector.startswith("#"):
        token = re.escape(selector[1:])
        match = re.search(
            rf'(?is)<([a-z0-9]+)\b[^>]*\bid=["\'][^"\']*{token}[^"\']*["\'][^>]*>(.*?)</\1>',
            html,
        )
        return _strip_tags(match.group(2)) if match else ""
    if selector.startswith("."):
        token = re.escape(selector[1:])
        match = re.search(
            rf'(?is)<([a-z0-9]+)\b[^>]*\bclass=["\'][^"\']*{token}[^"\']*["\'][^>]*>(.*?)</\1>',
            html,
        )
        return _strip_tags(match.group(2)) if match else ""
    tag = re.escape(selector.lower())
    match = re.search(rf"(?is)<{tag}\b[^>]*>(.*?)</{tag}>", html)
    return _strip_tags(match.group(1)) if match else ""


def _extract_article_text(html: str, selector: str | None) -> str:
    selected = _extract_by_selector(html, selector)
    if selected:
        return selected
    article_match = re.search(r"(?is)<article\b[^>]*>(.*?)</article>", html)
    if article_match:
        return _strip_tags(article_match.group(1))
    body_match = re.search(r"(?is)<body\b[^>]*>(.*?)</body>", html)
    if body_match:
        return _strip_tags(body_match.group(1))
    return _strip_tags(html)


def _fetch_rss(url: str) -> list[dict[str, str]]:
    with urllib.request.urlopen(url, timeout=20) as resp:
        payload = resp.read()
    root = ET.fromstring(payload)
    items: list[dict[str, str]] = []

    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        content = (item.findtext("description") or "").strip()
        published = (item.findtext("pubDate") or "").strip()
        if title and link and content:
            items.append(
                {
                    "title": title,
                    "url": link,
                    "content": _strip_tags(content),
                    "published_at": _normalize_published(published),
                }
            )

    ns = {"atom": "http://www.w3.org/2005/Atom"}
    for entry in root.findall(".//atom:entry", ns):
        title = (entry.findtext("atom:title", default="", namespaces=ns) or "").strip()
        content = (
            entry.findtext("atom:content", default="", namespaces=ns)
            or entry.findtext("atom:summary", default="", namespaces=ns)
            or ""
        ).strip()
        published = (
            entry.findtext("atom:updated", default="", namespaces=ns)
            or entry.findtext("atom:published", default="", namespaces=ns)
            or ""
        ).strip()
        link = ""
        for link_node in entry.findall("atom:link", ns):
            href = link_node.attrib.get("href", "").strip()
            if href:
                link = href
                break
        if title and link and content:
            items.append(
                {
                    "title": title,
                    "url": link,
                    "content": _strip_tags(content),
                    "published_at": _normalize_published(published),
                }
            )
    return items


def _fetch_web(url: str, selector: str | None) -> list[dict[str, str]]:
    html = fetch_html(url)
    title_match = re.search(r"(?is)<title[^>]*>(.*?)</title>", html)
    title = _strip_tags(title_match.group(1)) if title_match else url
    content = _extract_article_text(html, selector)
    if len(content) < 120:
        raise RuntimeError("web content too short after parsing")
    return [
        {
            "title": title or url,
            "url": url,
            "content": content,
            "published_at": _utc_iso_now(),
        }
    ]


def _to_signal(source_row: dict[str, object], raw: dict[str, str]) -> SignalInput:
    source_id = str(source_row["source_id"])
    lab_hint = str(source_row["lab"])
    title = raw["title"].strip()
    content = raw["content"].strip()
    return SignalInput(
        source_id=source_id,
        url=raw["url"].strip(),
        title=title[:300] if len(title) > 300 else title,
        content=content,
        published_at=raw["published_at"].strip() or _utc_iso_now(),
        tags=["auto_fetch"],
        lab_hint=lab_hint,
        event_hint=None,
    )


def fetch_sources(
    store: SQLiteStore,
    limit: int = 20,
    source_id: str | None = None,
    dry_run: bool = False,
) -> tuple[list[SignalInput], FetchStats]:
    rows = [dict(row) for row in store.list_fetch_sources(limit=limit, source_id=source_id)]
    stats = FetchStats(total_sources=len(rows))
    signals: list[SignalInput] = []

    for row in rows:
        started_at = datetime.now(UTC)
        run_seed = f"{started_at.isoformat()}|{row['source_id']}".encode("utf-8")
        run_id = f"fetch-{hashlib.sha256(run_seed).hexdigest()[:12]}"
        fetched = 0
        parsed = 0
        failed = 0
        status = "success"
        error_message: str | None = None
        try:
            parser = str(row.get("fetch_parser") or "")
            source_type = str(row.get("source_type") or "")
            url = str(row.get("url") or "")
            if source_type == "rss" or parser == "rss":
                records = _fetch_rss(url)
            else:
                records = _fetch_web(url, str(row.get("fetch_selector") or ""))
            fetched = len(records)
            for record in records:
                signal = _to_signal(row, record)
                signals.append(signal)
                parsed += 1
            stats.success_sources += 1
            stats.fetched_items += fetched
            stats.parsed_items += parsed
        except Exception as exc:
            failed = 1
            status = "failed"
            error_message = str(exc)
            stats.failed_sources += 1
        finally:
            store.insert_fetch_run(
                run_id=run_id,
                started_at=started_at,
                finished_at=datetime.now(UTC),
                source_id=str(row["source_id"]),
                fetched=fetched,
                parsed=parsed,
                failed=failed,
                status=status,
                error_message=error_message,
            )
    return signals, stats


def seed_sources(store: SQLiteStore, preset: str = "official-ai") -> int:
    if preset != "official-ai":
        raise ValueError(f"unsupported preset: {preset}")
    sources = [
        Source(
            source_id="openai-rss",
            layer="signal",
            lab="OpenAI",
            source_name="OpenAI News RSS",
            source_type="rss",
            mode="auto_fetch",
            url="https://openai.com/news/rss.xml",
            fetch_parser="rss",
        ),
        Source(
            source_id="anthropic-rss",
            layer="signal",
            lab="Anthropic",
            source_name="Anthropic News RSS",
            source_type="rss",
            mode="auto_fetch",
            url="https://www.anthropic.com/news/rss.xml",
            fetch_parser="rss",
        ),
        Source(
            source_id="deepmind-blog",
            layer="signal",
            lab="Google DeepMind",
            source_name="DeepMind Blog",
            source_type="web",
            mode="auto_fetch",
            url="https://deepmind.google/discover/blog/",
            fetch_parser="article",
            fetch_selector="article",
        ),
        Source(
            source_id="meta-ai-blog",
            layer="signal",
            lab="Meta AI",
            source_name="Meta AI Blog",
            source_type="web",
            mode="auto_fetch",
            url="https://ai.meta.com/blog/",
            fetch_parser="article",
            fetch_selector="article",
        ),
    ]
    for source in sources:
        store.upsert_source(source)
    return len(sources)
