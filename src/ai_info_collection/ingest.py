from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from ai_info_collection.models import CanonicalDocument, RawDocument, SignalInput
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
class IngestStats:
    total: int = 0
    success: int = 0
    skipped_duplicates: int = 0
    failed: int = 0


@dataclass(slots=True)
class IngestError:
    line_no: int
    error_message: str
    raw_payload: str


def _parse_datetime(value: str) -> datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _to_signal_input(data: dict[str, object]) -> SignalInput:
    required = ["source_id", "url", "title", "content", "published_at", "tags", "lab_hint"]
    missing = [field for field in required if field not in data]
    if missing:
        raise ValueError(f"missing required fields: {', '.join(missing)}")
    tags = data["tags"]
    if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
        raise ValueError("tags must be a list of strings")
    event_hint = data.get("event_hint")
    if event_hint is not None and not isinstance(event_hint, str):
        raise ValueError("event_hint must be a string when provided")
    return SignalInput(
        source_id=str(data["source_id"]),
        url=str(data["url"]),
        title=str(data["title"]),
        content=str(data["content"]),
        published_at=str(data["published_at"]),
        tags=list(tags),
        lab_hint=str(data["lab_hint"]),
        event_hint=event_hint,
    )


def _normalize_title(text: str) -> str:
    lowered = text.lower()
    lowered = re.sub(r"[^a-z0-9\s]", " ", lowered)
    lowered = re.sub(r"\s+", " ", lowered).strip()
    words = [word for word in lowered.split(" ") if word and word not in _STOP_WORDS]
    return " ".join(words[:8])


def _to_key_points(content: str) -> list[str]:
    segments = [seg.strip() for seg in re.split(r"[。.!?]\s*", content) if seg.strip()]
    return segments[:3]


def _to_summary(content: str) -> str:
    compact = re.sub(r"\s+", " ", content).strip()
    if len(compact) <= 180:
        return compact
    return compact[:177] + "..."


def ingest_signals(
    store: SQLiteStore,
    input_path: str | Path,
    dry_run: bool = False,
) -> tuple[IngestStats, list[IngestError]]:
    path = Path(input_path)
    stats = IngestStats()
    errors: list[IngestError] = []

    signal_rows: list[tuple[int, str, SignalInput, str | None]] = []
    for idx, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw_line.strip():
            continue
        stats.total += 1
        try:
            payload = json.loads(raw_line)
            if not isinstance(payload, dict):
                raise ValueError("line must be a JSON object")
            signal = _to_signal_input(payload)
            expected_event_key = payload.get("expected_event_key")
        except (json.JSONDecodeError, ValueError) as exc:
            stats.failed += 1
            errors.append(
                IngestError(
                    line_no=idx,
                    error_message=str(exc),
                    raw_payload=raw_line,
                )
            )
            continue
        signal_rows.append((idx, raw_line, signal, expected_event_key if isinstance(expected_event_key, str) else None))

    post_stats, post_errors = ingest_signal_items(
        store=store,
        items=[row[2] for row in signal_rows],
        dry_run=dry_run,
        source_context=[(line_no, raw_payload, expected) for line_no, raw_payload, _, expected in signal_rows],
    )
    stats.success += post_stats.success
    stats.skipped_duplicates += post_stats.skipped_duplicates
    stats.failed += post_stats.failed

    errors.extend(post_errors)
    return stats, errors


def ingest_signal_items(
    store: SQLiteStore,
    items: list[SignalInput],
    dry_run: bool = False,
    source_context: list[tuple[int, str, str | None]] | None = None,
) -> tuple[IngestStats, list[IngestError]]:
    stats = IngestStats(total=len(items))
    errors: list[IngestError] = []
    seen_hashes: set[str] = set()
    for idx, signal in enumerate(items, start=1):
        line_no = idx
        raw_payload = json.dumps(
            {
                "source_id": signal.source_id,
                "url": signal.url,
                "title": signal.title,
                "content": signal.content,
                "published_at": signal.published_at,
                "tags": signal.tags,
                "lab_hint": signal.lab_hint,
                "event_hint": signal.event_hint,
            },
            ensure_ascii=False,
        )
        expected_event_key: str | None = None
        if source_context and len(source_context) >= idx:
            line_no, raw_payload, expected_event_key = source_context[idx - 1]

        try:
            published_at = _parse_datetime(signal.published_at)
        except ValueError as exc:
            stats.failed += 1
            errors.append(
                IngestError(
                    line_no=line_no,
                    error_message=str(exc),
                    raw_payload=raw_payload,
                )
            )
            continue

        content_hash = hashlib.sha256(signal.content.encode("utf-8")).hexdigest()
        if content_hash in seen_hashes or store.find_raw_document_by_hash(content_hash):
            stats.skipped_duplicates += 1
            continue
        seen_hashes.add(content_hash)

        raw_id = hashlib.sha256(
            f"{signal.source_id}|{signal.url}|{signal.published_at}|{signal.title}".encode("utf-8")
        ).hexdigest()
        canonical_id = f"canon-{raw_id[:16]}"
        now = datetime.now(UTC)

        metadata = {
            "tags": signal.tags,
            "lab_hint": signal.lab_hint,
            "event_hint": signal.event_hint,
            "expected_event_key": expected_event_key,
        }
        raw_document = RawDocument(
            raw_id=raw_id,
            source_id=signal.source_id,
            url=signal.url,
            title=signal.title,
            content=signal.content,
            published_at=published_at,
            fetched_at=now,
            hash_sha256=content_hash,
            metadata_json=json.dumps(metadata, ensure_ascii=False),
            created_at=now,
            updated_at=now,
        )
        canonical_document = CanonicalDocument(
            canonical_id=canonical_id,
            raw_id=raw_id,
            event_id=None,
            normalized_title=_normalize_title(signal.title),
            summary=_to_summary(signal.content),
            key_points=_to_key_points(signal.content),
            entities=[signal.lab_hint],
            canonical_version=1,
            created_at=now,
            updated_at=now,
        )

        if not dry_run:
            store.upsert_raw_document(raw_document)
            store.upsert_canonical_document(canonical_document)

        stats.success += 1

    return stats, errors
