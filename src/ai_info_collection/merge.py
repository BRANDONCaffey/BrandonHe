from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from ai_info_collection.models import Event
from ai_info_collection.storage import SQLiteStore

_STOP_WORDS = {
    "a",
    "an",
    "the",
    "and",
    "or",
    "to",
    "of",
    "for",
    "in",
    "on",
    "at",
    "with",
    "by",
    "from",
}


@dataclass(slots=True)
class MergeStats:
    processed: int = 0
    matched_by_hint: int = 0
    matched_by_rule: int = 0
    created_new: int = 0


def _parse_datetime(value: str | None) -> datetime:
    if not value:
        return datetime.now(UTC)
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _normalized_title_key(text: str) -> str:
    lowered = text.lower()
    lowered = re.sub(r"[^a-z0-9\s]", " ", lowered)
    lowered = re.sub(r"\s+", " ", lowered).strip()
    words = [word for word in lowered.split(" ") if word and word not in _STOP_WORDS]
    return " ".join(words[:8])


def _within_days(left: datetime, right: datetime, days: int = 7) -> bool:
    return abs(left - right) <= timedelta(days=days)


def merge_events(store: SQLiteStore, limit: int = 100, dry_run: bool = False) -> MergeStats:
    stats = MergeStats()
    candidates = store.list_unmerged_canonical_documents(limit=limit)
    events = [dict(row) for row in store.list_events()]

    for row in candidates:
        stats.processed += 1
        canonical_id = row["canonical_id"]
        normalized_title = row["normalized_title"]
        published_at = _parse_datetime(row["published_at"])

        entities: list[str] = []
        try:
            entities = json.loads(row["entities_json"])
            if not isinstance(entities, list):
                entities = []
        except (TypeError, json.JSONDecodeError):
            entities = []

        metadata: dict[str, object] = {}
        try:
            metadata_json = row["metadata_json"]
            loaded = json.loads(metadata_json)
            if isinstance(loaded, dict):
                metadata = loaded
        except (TypeError, json.JSONDecodeError):
            metadata = {}

        event_hint = metadata.get("event_hint") if isinstance(metadata.get("event_hint"), str) else None
        lab_hint = metadata.get("lab_hint") if isinstance(metadata.get("lab_hint"), str) else None
        for entity in entities:
            if isinstance(entity, str) and entity.strip():
                if lab_hint is None:
                    lab_hint = entity.strip()

        # Rule 1: event_hint hit
        if event_hint:
            hint_event = store.get_event(event_hint)
            if hint_event:
                stats.matched_by_hint += 1
                if not dry_run:
                    store.update_canonical_event_id(canonical_id, event_hint)
                continue

        # Rule 2: normalized_title_key + lab_hint + 7-day window
        target_event: dict[str, object] | None = None
        target_delta: timedelta | None = None
        candidate_key = _normalized_title_key(normalized_title)
        for event_row in events:
            event_lab = event_row["related_lab"]
            if lab_hint and event_lab != lab_hint:
                continue
            event_key = _normalized_title_key(event_row["title"])
            if event_key != candidate_key:
                continue
            event_time = _parse_datetime(event_row["last_activity_at"])
            delta = abs(event_time - published_at)
            if delta > timedelta(days=7):
                continue
            if target_event is None:
                target_event = event_row
                target_delta = delta
                continue
            if target_delta is not None and delta < target_delta:
                target_event = event_row
                target_delta = delta
                continue
            if target_delta is not None and delta == target_delta and event_row["event_id"] < target_event["event_id"]:
                target_event = event_row
                target_delta = delta

        if target_event:
            stats.matched_by_rule += 1
            target_event_id = str(target_event["event_id"])
            if not dry_run:
                event_row = store.get_event(target_event_id)
                if event_row:
                    topics = json.loads(event_row["topics_json"])
                    updated_event = Event(
                        event_id=event_row["event_id"],
                        title=event_row["title"],
                        summary=event_row["summary"],
                        event_type=event_row["event_type"],
                        topics=topics,
                        related_lab=event_row["related_lab"],
                        status=event_row["status"],
                        priority=event_row["priority"],
                        created_at=_parse_datetime(event_row["created_at"]),
                        updated_at=datetime.now(UTC),
                        first_seen_at=_parse_datetime(event_row["first_seen_at"]),
                        last_activity_at=published_at,
                    )
                    store.upsert_event(updated_event)
                    target_event["last_activity_at"] = published_at.isoformat()
                    target_event["updated_at"] = datetime.now(UTC).isoformat()
                store.update_canonical_event_id(canonical_id, target_event_id)
            continue

        # Rule 3: create new Event
        new_event_id = f"event-{hashlib.sha256(canonical_id.encode('utf-8')).hexdigest()[:12]}"
        stats.created_new += 1
        if not dry_run:
            new_event = Event(
                event_id=new_event_id,
                title=normalized_title or "signal-event",
                summary=row["summary"],
                event_type="signal",
                topics=["signal"],
                related_lab=lab_hint,
                status="under_review",
                priority="p2",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
                first_seen_at=published_at,
                last_activity_at=published_at,
            )
            store.upsert_event(new_event)
            store.update_canonical_event_id(canonical_id, new_event_id)

    return stats
