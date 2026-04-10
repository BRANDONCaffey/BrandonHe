from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

from ai_info_collection.models import CanonicalDocument, Event, MeaningCard, RawDocument, Source


def _serialize_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(UTC).isoformat()


def _parse_datetime(value: str | None) -> datetime:
    if not value:
        return datetime.now(UTC)
    return datetime.fromisoformat(value)


class SQLiteStore:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def initialize(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS sources (
                    source_id TEXT PRIMARY KEY,
                    layer TEXT NOT NULL,
                    lab TEXT NOT NULL,
                    source_name TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    url TEXT NOT NULL,
                    governance_status TEXT NOT NULL,
                    trust_level TEXT NOT NULL,
                    verification_role TEXT NOT NULL,
                    owner TEXT,
                    review_frequency TEXT,
                    last_reviewed_at TEXT,
                    last_success_at TEXT,
                    last_failure_at TEXT,
                    failure_count INTEGER NOT NULL DEFAULT 0,
                    quality_score REAL,
                    notes TEXT,
                    robots_policy_checked INTEGER NOT NULL DEFAULT 0,
                    terms_risk_level TEXT NOT NULL DEFAULT 'unknown',
                    fetch_enabled INTEGER NOT NULL DEFAULT 1,
                    fetch_parser TEXT NOT NULL DEFAULT 'article',
                    fetch_selector TEXT,
                    fetch_interval_minutes INTEGER
                );

                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    topics_json TEXT NOT NULL,
                    related_lab TEXT,
                    status TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    first_seen_at TEXT NOT NULL,
                    last_activity_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS meaning_cards (
                    id TEXT PRIMARY KEY,
                    event_id TEXT NOT NULL REFERENCES events(event_id),
                    related_fact_id TEXT,
                    longform_source TEXT NOT NULL,
                    core_takeaway TEXT NOT NULL,
                    why_it_matters TEXT NOT NULL,
                    watch_next TEXT NOT NULL,
                    status TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    evidence_json TEXT NOT NULL,
                    review_notes TEXT NOT NULL,
                    reviewed_by TEXT,
                    reviewed_at TEXT,
                    interpretation_type TEXT,
                    change_scope TEXT,
                    what_changed_before TEXT NOT NULL,
                    what_changed_now TEXT NOT NULL,
                    what_changed_delta TEXT NOT NULL,
                    why_now TEXT NOT NULL,
                    implications TEXT NOT NULL,
                    counterpoints TEXT NOT NULL,
                    key_uncertainties TEXT NOT NULL,
                    framework_tags_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS raw_documents (
                    raw_id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    url TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    published_at TEXT NOT NULL,
                    fetched_at TEXT NOT NULL,
                    hash_sha256 TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS canonical_documents (
                    canonical_id TEXT PRIMARY KEY,
                    raw_id TEXT NOT NULL UNIQUE REFERENCES raw_documents(raw_id),
                    event_id TEXT REFERENCES events(event_id),
                    normalized_title TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    key_points_json TEXT NOT NULL,
                    entities_json TEXT NOT NULL,
                    canonical_version INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS pipeline_runs (
                    run_id TEXT PRIMARY KEY,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    input_path TEXT NOT NULL,
                    run_signature TEXT,
                    dry_run INTEGER NOT NULL,
                    merge_limit INTEGER NOT NULL,
                    ingest_total INTEGER NOT NULL DEFAULT 0,
                    ingest_success INTEGER NOT NULL DEFAULT 0,
                    ingest_failed INTEGER NOT NULL DEFAULT 0,
                    ingest_skipped_duplicates INTEGER NOT NULL DEFAULT 0,
                    merge_processed INTEGER NOT NULL DEFAULT 0,
                    merge_matched_by_hint INTEGER NOT NULL DEFAULT 0,
                    merge_matched_by_rule INTEGER NOT NULL DEFAULT 0,
                    merge_created_new INTEGER NOT NULL DEFAULT 0,
                    fetch_total INTEGER NOT NULL DEFAULT 0,
                    fetch_success INTEGER NOT NULL DEFAULT 0,
                    fetch_failed INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL,
                    status_reason TEXT
                );

                CREATE TABLE IF NOT EXISTS pipeline_run_errors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL REFERENCES pipeline_runs(run_id),
                    stage TEXT NOT NULL,
                    line_no INTEGER,
                    error_message TEXT NOT NULL,
                    raw_payload TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS merge_eval_runs (
                    eval_id TEXT PRIMARY KEY,
                    started_at TEXT NOT NULL,
                    finished_at TEXT NOT NULL,
                    dataset_path TEXT NOT NULL,
                    rows_total INTEGER NOT NULL,
                    event_groups_truth INTEGER NOT NULL,
                    false_merge_rate REAL NOT NULL,
                    miss_merge_rate REAL NOT NULL,
                    notes_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS fetch_runs (
                    run_id TEXT PRIMARY KEY,
                    started_at TEXT NOT NULL,
                    finished_at TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    fetched INTEGER NOT NULL DEFAULT 0,
                    parsed INTEGER NOT NULL DEFAULT 0,
                    failed INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL,
                    error_message TEXT
                );
                """
            )
            self._ensure_column(conn, "sources", "fetch_enabled", "INTEGER NOT NULL DEFAULT 1")
            self._ensure_column(conn, "sources", "fetch_parser", "TEXT NOT NULL DEFAULT 'article'")
            self._ensure_column(conn, "sources", "fetch_selector", "TEXT")
            self._ensure_column(conn, "sources", "fetch_interval_minutes", "INTEGER")
            self._ensure_column(conn, "pipeline_runs", "run_signature", "TEXT")
            self._ensure_column(conn, "pipeline_runs", "status_reason", "TEXT")
            self._ensure_column(conn, "pipeline_runs", "fetch_total", "INTEGER NOT NULL DEFAULT 0")
            self._ensure_column(conn, "pipeline_runs", "fetch_success", "INTEGER NOT NULL DEFAULT 0")
            self._ensure_column(conn, "pipeline_runs", "fetch_failed", "INTEGER NOT NULL DEFAULT 0")

    def _ensure_column(self, conn: sqlite3.Connection, table: str, column: str, column_type: str) -> None:
        existing = conn.execute(f"PRAGMA table_info({table})").fetchall()
        if any(row["name"] == column for row in existing):
            return
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")

    def upsert_source(self, source: Source) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO sources (
                    source_id, layer, lab, source_name, source_type, mode, url,
                    governance_status, trust_level, verification_role, owner,
                    review_frequency, last_reviewed_at, last_success_at, last_failure_at,
                    failure_count, quality_score, notes, robots_policy_checked, terms_risk_level,
                    fetch_enabled, fetch_parser, fetch_selector, fetch_interval_minutes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_id) DO UPDATE SET
                    layer=excluded.layer,
                    lab=excluded.lab,
                    source_name=excluded.source_name,
                    source_type=excluded.source_type,
                    mode=excluded.mode,
                    url=excluded.url,
                    governance_status=excluded.governance_status,
                    trust_level=excluded.trust_level,
                    verification_role=excluded.verification_role,
                    owner=excluded.owner,
                    review_frequency=excluded.review_frequency,
                    last_reviewed_at=excluded.last_reviewed_at,
                    last_success_at=excluded.last_success_at,
                    last_failure_at=excluded.last_failure_at,
                    failure_count=excluded.failure_count,
                    quality_score=excluded.quality_score,
                    notes=excluded.notes,
                    robots_policy_checked=excluded.robots_policy_checked,
                    terms_risk_level=excluded.terms_risk_level,
                    fetch_enabled=excluded.fetch_enabled,
                    fetch_parser=excluded.fetch_parser,
                    fetch_selector=excluded.fetch_selector,
                    fetch_interval_minutes=excluded.fetch_interval_minutes
                """,
                (
                    source.source_id,
                    source.layer,
                    source.lab,
                    source.source_name,
                    source.source_type,
                    source.mode,
                    source.url,
                    source.governance_status,
                    source.trust_level,
                    source.verification_role,
                    source.owner,
                    source.review_frequency,
                    _serialize_datetime(source.last_reviewed_at),
                    _serialize_datetime(source.last_success_at),
                    _serialize_datetime(source.last_failure_at),
                    source.failure_count,
                    source.quality_score,
                    source.notes,
                    int(source.robots_policy_checked),
                    source.terms_risk_level,
                    int(source.fetch_enabled),
                    source.fetch_parser,
                    source.fetch_selector,
                    source.fetch_interval_minutes,
                ),
            )

    def upsert_event(self, event: Event) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO events (
                    event_id, title, summary, event_type, topics_json, related_lab, status,
                    priority, created_at, updated_at, first_seen_at, last_activity_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(event_id) DO UPDATE SET
                    title=excluded.title,
                    summary=excluded.summary,
                    event_type=excluded.event_type,
                    topics_json=excluded.topics_json,
                    related_lab=excluded.related_lab,
                    status=excluded.status,
                    priority=excluded.priority,
                    updated_at=excluded.updated_at,
                    last_activity_at=excluded.last_activity_at
                """,
                (
                    event.event_id,
                    event.title,
                    event.summary,
                    event.event_type,
                    json.dumps(event.topics, ensure_ascii=False),
                    event.related_lab,
                    event.status,
                    event.priority,
                    _serialize_datetime(event.created_at),
                    _serialize_datetime(event.updated_at),
                    _serialize_datetime(event.first_seen_at),
                    _serialize_datetime(event.last_activity_at),
                ),
            )

    def get_event(self, event_id: str) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT event_id, title, summary, event_type, topics_json, related_lab, status,
                       priority, created_at, updated_at, first_seen_at, last_activity_at
                FROM events
                WHERE event_id = ?
                """,
                (event_id,),
            ).fetchone()

    def list_events(self) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT event_id, title, summary, event_type, topics_json, related_lab, status,
                       priority, created_at, updated_at, first_seen_at, last_activity_at
                FROM events
                ORDER BY updated_at DESC
                """
            ).fetchall()

    def upsert_meaning_card(self, card: MeaningCard) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO meaning_cards (
                    id, event_id, related_fact_id, longform_source, core_takeaway,
                    why_it_matters, watch_next, status, confidence, evidence_json,
                    review_notes, reviewed_by, reviewed_at, interpretation_type,
                    change_scope, what_changed_before, what_changed_now, what_changed_delta,
                    why_now, implications, counterpoints, key_uncertainties,
                    framework_tags_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    event_id=excluded.event_id,
                    related_fact_id=excluded.related_fact_id,
                    longform_source=excluded.longform_source,
                    core_takeaway=excluded.core_takeaway,
                    why_it_matters=excluded.why_it_matters,
                    watch_next=excluded.watch_next,
                    status=excluded.status,
                    confidence=excluded.confidence,
                    evidence_json=excluded.evidence_json,
                    review_notes=excluded.review_notes,
                    reviewed_by=excluded.reviewed_by,
                    reviewed_at=excluded.reviewed_at,
                    interpretation_type=excluded.interpretation_type,
                    change_scope=excluded.change_scope,
                    what_changed_before=excluded.what_changed_before,
                    what_changed_now=excluded.what_changed_now,
                    what_changed_delta=excluded.what_changed_delta,
                    why_now=excluded.why_now,
                    implications=excluded.implications,
                    counterpoints=excluded.counterpoints,
                    key_uncertainties=excluded.key_uncertainties,
                    framework_tags_json=excluded.framework_tags_json,
                    updated_at=excluded.updated_at
                """,
                (
                    card.id,
                    card.event_id,
                    card.related_fact_id,
                    card.longform_source,
                    card.core_takeaway,
                    card.why_it_matters,
                    card.watch_next,
                    card.status,
                    card.confidence,
                    json.dumps(card.evidence, ensure_ascii=False),
                    card.review_notes,
                    card.reviewed_by,
                    _serialize_datetime(card.reviewed_at),
                    card.interpretation_type,
                    card.change_scope,
                    card.what_changed_before,
                    card.what_changed_now,
                    card.what_changed_delta,
                    card.why_now,
                    card.implications,
                    card.counterpoints,
                    card.key_uncertainties,
                    json.dumps(card.framework_tags, ensure_ascii=False),
                    _serialize_datetime(card.created_at),
                    _serialize_datetime(card.updated_at),
                ),
            )

    def upsert_raw_document(self, document: RawDocument) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO raw_documents (
                    raw_id, source_id, url, title, content, published_at, fetched_at,
                    hash_sha256, metadata_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(raw_id) DO UPDATE SET
                    source_id=excluded.source_id,
                    url=excluded.url,
                    title=excluded.title,
                    content=excluded.content,
                    published_at=excluded.published_at,
                    fetched_at=excluded.fetched_at,
                    hash_sha256=excluded.hash_sha256,
                    metadata_json=excluded.metadata_json,
                    updated_at=excluded.updated_at
                """,
                (
                    document.raw_id,
                    document.source_id,
                    document.url,
                    document.title,
                    document.content,
                    _serialize_datetime(document.published_at),
                    _serialize_datetime(document.fetched_at),
                    document.hash_sha256,
                    document.metadata_json,
                    _serialize_datetime(document.created_at),
                    _serialize_datetime(document.updated_at),
                ),
            )

    def upsert_canonical_document(self, document: CanonicalDocument) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO canonical_documents (
                    canonical_id, raw_id, event_id, normalized_title, summary,
                    key_points_json, entities_json, canonical_version, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(canonical_id) DO UPDATE SET
                    raw_id=excluded.raw_id,
                    event_id=excluded.event_id,
                    normalized_title=excluded.normalized_title,
                    summary=excluded.summary,
                    key_points_json=excluded.key_points_json,
                    entities_json=excluded.entities_json,
                    canonical_version=excluded.canonical_version,
                    updated_at=excluded.updated_at
                """,
                (
                    document.canonical_id,
                    document.raw_id,
                    document.event_id,
                    document.normalized_title,
                    document.summary,
                    json.dumps(document.key_points, ensure_ascii=False),
                    json.dumps(document.entities, ensure_ascii=False),
                    document.canonical_version,
                    _serialize_datetime(document.created_at),
                    _serialize_datetime(document.updated_at),
                ),
            )

    def find_raw_document_by_hash(self, hash_sha256: str) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT raw_id, source_id, url, title, content, published_at, fetched_at,
                       hash_sha256, metadata_json, created_at, updated_at
                FROM raw_documents
                WHERE hash_sha256 = ?
                LIMIT 1
                """,
                (hash_sha256,),
            ).fetchone()

    def list_recent_raw_documents(self, limit: int = 10) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT raw_id, source_id, url, title, published_at, fetched_at, hash_sha256, updated_at
                FROM raw_documents
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

    def list_recent_canonical_documents(self, limit: int = 10) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT canonical_id, raw_id, event_id, normalized_title, canonical_version, updated_at
                FROM canonical_documents
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

    def create_pipeline_run(
        self,
        run_id: str,
        started_at: datetime,
        input_path: str,
        dry_run: bool,
        merge_limit: int,
        run_signature: str | None = None,
        status: str = "running",
        status_reason: str | None = None,
        finished_at: datetime | None = None,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO pipeline_runs (
                    run_id, started_at, finished_at, input_path, run_signature, dry_run, merge_limit,
                    ingest_total, ingest_success, ingest_failed, ingest_skipped_duplicates,
                    merge_processed, merge_matched_by_hint, merge_matched_by_rule, merge_created_new,
                    status, status_reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, 0, 0, 0, 0, 0, 0, ?, ?)
                """,
                (
                    run_id,
                    _serialize_datetime(started_at),
                    _serialize_datetime(finished_at),
                    input_path,
                    run_signature,
                    int(dry_run),
                    merge_limit,
                    status,
                    status_reason,
                ),
            )

    def update_pipeline_run_result(
        self,
        run_id: str,
        finished_at: datetime,
        ingest_total: int,
        ingest_success: int,
        ingest_failed: int,
        ingest_skipped_duplicates: int,
        merge_processed: int,
        merge_matched_by_hint: int,
        merge_matched_by_rule: int,
        merge_created_new: int,
        status: str,
        fetch_total: int = 0,
        fetch_success: int = 0,
        fetch_failed: int = 0,
        status_reason: str | None = None,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE pipeline_runs
                SET finished_at = ?,
                    ingest_total = ?,
                    ingest_success = ?,
                    ingest_failed = ?,
                    ingest_skipped_duplicates = ?,
                    merge_processed = ?,
                    merge_matched_by_hint = ?,
                    merge_matched_by_rule = ?,
                    merge_created_new = ?,
                    fetch_total = ?,
                    fetch_success = ?,
                    fetch_failed = ?,
                    status = ?,
                    status_reason = ?
                WHERE run_id = ?
                """,
                (
                    _serialize_datetime(finished_at),
                    ingest_total,
                    ingest_success,
                    ingest_failed,
                    ingest_skipped_duplicates,
                    merge_processed,
                    merge_matched_by_hint,
                    merge_matched_by_rule,
                    merge_created_new,
                    fetch_total,
                    fetch_success,
                    fetch_failed,
                    status,
                    status_reason,
                    run_id,
                ),
            )

    def reserve_pipeline_run(
        self,
        run_id: str,
        started_at: datetime,
        input_path: str,
        run_signature: str,
        dry_run: bool,
        merge_limit: int,
        duplicate_window_minutes: int = 10,
        running_timeout_minutes: int = 30,
    ) -> tuple[bool, str | None]:
        threshold = started_at - timedelta(minutes=duplicate_window_minutes)
        stale_threshold = started_at - timedelta(minutes=running_timeout_minutes)
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            running_row = conn.execute(
                """
                SELECT run_id, started_at
                FROM pipeline_runs
                WHERE status = 'running'
                ORDER BY started_at DESC
                LIMIT 1
                """
            ).fetchone()
            if running_row:
                running_started_at = _parse_datetime(running_row["started_at"])
                if running_started_at < stale_threshold:
                    conn.execute(
                        """
                        UPDATE pipeline_runs
                        SET status = 'failed',
                            status_reason = 'stale_running_recovered',
                            finished_at = ?
                        WHERE run_id = ?
                        """,
                        (_serialize_datetime(started_at), running_row["run_id"]),
                    )
                else:
                    self._insert_pipeline_run_with_conn(
                        conn=conn,
                        run_id=run_id,
                        started_at=started_at,
                        finished_at=started_at,
                        input_path=input_path,
                        run_signature=run_signature,
                        dry_run=dry_run,
                        merge_limit=merge_limit,
                        status="failed",
                        status_reason="concurrent_run_blocked",
                    )
                    conn.commit()
                    return False, "concurrent_run_blocked"

            duplicate_row = conn.execute(
                """
                SELECT run_id
                FROM pipeline_runs
                WHERE run_signature = ?
                  AND status IN ('running', 'success', 'partial_success')
                  AND started_at >= ?
                ORDER BY started_at DESC
                LIMIT 1
                """,
                (run_signature, _serialize_datetime(threshold)),
            ).fetchone()
            if duplicate_row:
                self._insert_pipeline_run_with_conn(
                    conn=conn,
                    run_id=run_id,
                    started_at=started_at,
                    finished_at=started_at,
                    input_path=input_path,
                    run_signature=run_signature,
                    dry_run=dry_run,
                    merge_limit=merge_limit,
                    status="failed",
                    status_reason="duplicate_run_blocked",
                )
                conn.commit()
                return False, "duplicate_run_blocked"

            self._insert_pipeline_run_with_conn(
                conn=conn,
                run_id=run_id,
                started_at=started_at,
                finished_at=None,
                input_path=input_path,
                run_signature=run_signature,
                dry_run=dry_run,
                merge_limit=merge_limit,
                status="running",
                status_reason=None,
            )
            conn.commit()
            return True, None

    def _insert_pipeline_run_with_conn(
        self,
        conn: sqlite3.Connection,
        run_id: str,
        started_at: datetime,
        finished_at: datetime | None,
        input_path: str,
        run_signature: str | None,
        dry_run: bool,
        merge_limit: int,
        status: str,
        status_reason: str | None,
    ) -> None:
        conn.execute(
            """
            INSERT INTO pipeline_runs (
                run_id, started_at, finished_at, input_path, run_signature, dry_run, merge_limit,
                ingest_total, ingest_success, ingest_failed, ingest_skipped_duplicates,
                merge_processed, merge_matched_by_hint, merge_matched_by_rule, merge_created_new,
                status, status_reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, 0, 0, 0, 0, 0, 0, ?, ?)
            """,
            (
                run_id,
                _serialize_datetime(started_at),
                _serialize_datetime(finished_at),
                input_path,
                run_signature,
                int(dry_run),
                merge_limit,
                status,
                status_reason,
            ),
        )

    def insert_pipeline_run_error(
        self,
        run_id: str,
        stage: str,
        line_no: int | None,
        error_message: str,
        raw_payload: str,
        created_at: datetime,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO pipeline_run_errors (
                    run_id, stage, line_no, error_message, raw_payload, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    stage,
                    line_no,
                    error_message,
                    raw_payload,
                    _serialize_datetime(created_at),
                ),
            )

    def list_recent_pipeline_runs(self, limit: int = 10) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT run_id, started_at, finished_at, input_path, run_signature, dry_run, merge_limit,
                       ingest_total, ingest_success, ingest_failed, ingest_skipped_duplicates,
                       merge_processed, merge_matched_by_hint, merge_matched_by_rule, merge_created_new,
                       fetch_total, fetch_success, fetch_failed,
                       status, status_reason
                FROM pipeline_runs
                ORDER BY started_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

    def list_fetch_sources(self, limit: int = 100, source_id: str | None = None) -> list[sqlite3.Row]:
        with self.connect() as conn:
            if source_id:
                return conn.execute(
                    """
                    SELECT source_id, lab, source_type, source_name, url, fetch_parser, fetch_selector
                    FROM sources
                    WHERE fetch_enabled = 1 AND source_id = ?
                    ORDER BY source_name
                    LIMIT ?
                    """,
                    (source_id, limit),
                ).fetchall()
            return conn.execute(
                """
                SELECT source_id, lab, source_type, source_name, url, fetch_parser, fetch_selector
                FROM sources
                WHERE fetch_enabled = 1
                ORDER BY source_name
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

    def insert_fetch_run(
        self,
        run_id: str,
        started_at: datetime,
        finished_at: datetime,
        source_id: str,
        fetched: int,
        parsed: int,
        failed: int,
        status: str,
        error_message: str | None,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO fetch_runs (
                    run_id, started_at, finished_at, source_id, fetched, parsed, failed, status, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    _serialize_datetime(started_at),
                    _serialize_datetime(finished_at),
                    source_id,
                    fetched,
                    parsed,
                    failed,
                    status,
                    error_message,
                ),
            )

    def list_recent_fetch_runs(self, limit: int = 20) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT run_id, source_id, fetched, parsed, failed, status, error_message, finished_at
                FROM fetch_runs
                ORDER BY finished_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

    def insert_merge_eval_run(
        self,
        eval_id: str,
        started_at: datetime,
        finished_at: datetime,
        dataset_path: str,
        rows_total: int,
        event_groups_truth: int,
        false_merge_rate: float,
        miss_merge_rate: float,
        notes_json: str,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO merge_eval_runs (
                    eval_id, started_at, finished_at, dataset_path, rows_total, event_groups_truth,
                    false_merge_rate, miss_merge_rate, notes_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    eval_id,
                    _serialize_datetime(started_at),
                    _serialize_datetime(finished_at),
                    dataset_path,
                    rows_total,
                    event_groups_truth,
                    false_merge_rate,
                    miss_merge_rate,
                    notes_json,
                ),
            )

    def list_unmerged_canonical_documents(self, limit: int = 100) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT c.canonical_id, c.raw_id, c.event_id, c.normalized_title, c.summary,
                       c.key_points_json, c.entities_json, c.canonical_version, c.created_at,
                       c.updated_at, r.published_at, r.metadata_json
                FROM canonical_documents c
                JOIN raw_documents r ON r.raw_id = c.raw_id
                WHERE c.event_id IS NULL OR TRIM(c.event_id) = ''
                ORDER BY c.updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

    def update_canonical_event_id(self, canonical_id: str, event_id: str) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE canonical_documents
                SET event_id = ?, updated_at = ?
                WHERE canonical_id = ?
                """,
                (event_id, _serialize_datetime(datetime.now(UTC)), canonical_id),
            )

    def list_meaning_cards_missing_what_changed(self) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT id, event_id, status, review_notes, updated_at
                FROM meaning_cards
                WHERE TRIM(what_changed_before) = ''
                   OR TRIM(what_changed_now) = ''
                   OR TRIM(what_changed_delta) = ''
                ORDER BY updated_at DESC
                """
            ).fetchall()

    def list_meaning_cards_missing_interpretation_type(self) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT id, event_id, status, review_notes, updated_at
                FROM meaning_cards
                WHERE interpretation_type IS NULL OR TRIM(interpretation_type) = ''
                ORDER BY updated_at DESC
                """
            ).fetchall()

    def list_meaning_cards_missing_why_it_matters(self) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT id, event_id, status, review_notes, updated_at
                FROM meaning_cards
                WHERE TRIM(why_it_matters) = ''
                ORDER BY updated_at DESC
                """
            ).fetchall()

    def list_meaning_cards_missing_framework_tags(self) -> list[sqlite3.Row]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT id, event_id, status, review_notes, updated_at, framework_tags_json
                FROM meaning_cards
                ORDER BY updated_at DESC
                """
            ).fetchall()

        missing: list[sqlite3.Row] = []
        for row in rows:
            tags_json = row["framework_tags_json"]
            try:
                tags = json.loads(tags_json)
            except (TypeError, json.JSONDecodeError):
                missing.append(row)
                continue

            if not isinstance(tags, list) or not tags:
                missing.append(row)
                continue

            has_valid_tag = any(isinstance(tag, str) and tag.strip() for tag in tags)
            if not has_valid_tag:
                missing.append(row)

        return missing

    def list_recent_events(self, limit: int = 10) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT event_id, title, related_lab, status, updated_at
                FROM events
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

    def list_source_health(self) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT source_id, layer, lab, source_name, governance_status, trust_level,
                       last_success_at, last_failure_at, failure_count, quality_score
                FROM sources
                ORDER BY layer, lab, source_name
                """
            ).fetchall()
