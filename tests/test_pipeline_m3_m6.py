from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import UTC, datetime, timedelta
from pathlib import Path

from ai_info_collection.cli import main
from ai_info_collection.models import CanonicalDocument, Event, RawDocument
from ai_info_collection.storage import SQLiteStore


class PipelineM3M6Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test.db"
        self.store = SQLiteStore(self.db_path)
        self.store.initialize()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_m3_recent_raw_and_recent_canonical_commands(self) -> None:
        now = datetime.now(UTC)
        raw = RawDocument(
            raw_id="raw-1",
            source_id="src-1",
            url="https://example.com/raw-1",
            title="Raw Title",
            content="Raw Content",
            published_at=now,
            fetched_at=now,
            hash_sha256="hash-1",
            metadata_json=json.dumps({"lab_hint": "OpenAI"}, ensure_ascii=False),
            created_at=now,
            updated_at=now,
        )
        canonical = CanonicalDocument(
            canonical_id="canon-1",
            raw_id="raw-1",
            event_id=None,
            normalized_title="raw title",
            summary="summary",
            key_points=["point-1"],
            entities=["OpenAI"],
            canonical_version=1,
            created_at=now,
            updated_at=now,
        )
        self.store.upsert_raw_document(raw)
        self.store.upsert_canonical_document(canonical)

        raw_output = io.StringIO()
        with redirect_stdout(raw_output):
            raw_exit = main(["--db-path", str(self.db_path), "recent-raw", "--limit", "5"])

        canonical_output = io.StringIO()
        with redirect_stdout(canonical_output):
            canonical_exit = main(["--db-path", str(self.db_path), "recent-canonical", "--limit", "5"])

        self.assertEqual(raw_exit, 0)
        self.assertEqual(canonical_exit, 0)
        self.assertIn("raw-1", raw_output.getvalue())
        self.assertIn("canon-1", canonical_output.getvalue())

    def test_m4_ingest_signals_dry_run_and_dedup(self) -> None:
        input_path = Path(self.temp_dir.name) / "signals.jsonl"
        lines = [
            {
                "source_id": "src-1",
                "url": "https://example.com/1",
                "title": "OpenAI 发布更新",
                "content": "同一内容用于去重。",
                "published_at": "2026-04-10T00:00:00+00:00",
                "tags": ["release"],
                "lab_hint": "OpenAI",
            },
            {
                "source_id": "src-1",
                "url": "https://example.com/2",
                "title": "OpenAI 更新复读",
                "content": "同一内容用于去重。",
                "published_at": "2026-04-10T01:00:00+00:00",
                "tags": ["release"],
                "lab_hint": "OpenAI",
            },
            {
                "source_id": "src-1",
                "url": "https://example.com/3",
                "title": "无效行",
                "content": "缺少 tags",
                "published_at": "2026-04-10T02:00:00+00:00",
                "lab_hint": "OpenAI",
            },
        ]
        input_path.write_text("\n".join(json.dumps(line, ensure_ascii=False) for line in lines), encoding="utf-8")

        dry_output = io.StringIO()
        with redirect_stdout(dry_output):
            dry_exit = main(["--db-path", str(self.db_path), "ingest-signals", "--input", str(input_path), "--dry-run"])

        self.assertEqual(dry_exit, 0)
        dry_text = dry_output.getvalue()
        self.assertIn("total=3", dry_text)
        self.assertIn("success=1", dry_text)
        self.assertIn("skipped_duplicates=1", dry_text)
        self.assertIn("failed=1", dry_text)
        with self.store.connect() as conn:
            dry_raw_count = conn.execute("SELECT COUNT(*) AS c FROM raw_documents").fetchone()["c"]
            dry_canonical_count = conn.execute("SELECT COUNT(*) AS c FROM canonical_documents").fetchone()["c"]
        self.assertEqual(dry_raw_count, 0)
        self.assertEqual(dry_canonical_count, 0)

        write_output = io.StringIO()
        with redirect_stdout(write_output):
            write_exit = main(["--db-path", str(self.db_path), "ingest-signals", "--input", str(input_path)])

        self.assertEqual(write_exit, 0)
        with self.store.connect() as conn:
            raw_count = conn.execute("SELECT COUNT(*) AS c FROM raw_documents").fetchone()["c"]
            canonical_count = conn.execute("SELECT COUNT(*) AS c FROM canonical_documents").fetchone()["c"]

        self.assertEqual(raw_count, 1)
        self.assertEqual(canonical_count, 1)

    def test_m6_merge_events_hint_rule_new_and_idempotent(self) -> None:
        now = datetime.now(UTC)
        hint_event = Event(
            event_id="event-hint",
            title="hint event",
            summary="hint",
            event_type="signal",
            topics=["signal"],
            related_lab="OpenAI",
            status="under_review",
            priority="p2",
            created_at=now,
            updated_at=now,
            first_seen_at=now,
            last_activity_at=now,
        )
        rule_event = Event(
            event_id="event-rule",
            title="openai gpt 5 update",
            summary="rule",
            event_type="signal",
            topics=["signal"],
            related_lab="OpenAI",
            status="under_review",
            priority="p2",
            created_at=now,
            updated_at=now,
            first_seen_at=now - timedelta(days=1),
            last_activity_at=now - timedelta(days=1),
        )
        none_lab_event = Event(
            event_id="event-no-lab",
            title="openai gpt 5 update",
            summary="no-lab",
            event_type="signal",
            topics=["signal"],
            related_lab=None,
            status="under_review",
            priority="p2",
            created_at=now,
            updated_at=now,
            first_seen_at=now,
            last_activity_at=now,
        )
        self.store.upsert_event(hint_event)
        self.store.upsert_event(rule_event)
        self.store.upsert_event(none_lab_event)

        def add_doc(raw_id: str, canonical_id: str, normalized_title: str, metadata: dict[str, object]) -> None:
            self.store.upsert_raw_document(
                RawDocument(
                    raw_id=raw_id,
                    source_id="src-1",
                    url=f"https://example.com/{raw_id}",
                    title=normalized_title,
                    content="content",
                    published_at=now,
                    fetched_at=now,
                    hash_sha256=f"hash-{raw_id}",
                    metadata_json=json.dumps(metadata, ensure_ascii=False),
                    created_at=now,
                    updated_at=now,
                )
            )
            self.store.upsert_canonical_document(
                CanonicalDocument(
                    canonical_id=canonical_id,
                    raw_id=raw_id,
                    event_id=None,
                    normalized_title=normalized_title,
                    summary="summary",
                    key_points=["k1"],
                    entities=[str(metadata.get("lab_hint", ""))],
                    canonical_version=1,
                    created_at=now,
                    updated_at=now,
                )
            )

        add_doc("raw-hint", "canon-hint", "openai hint", {"event_hint": "event-hint", "lab_hint": "OpenAI"})
        add_doc("raw-rule", "canon-rule", "openai gpt 5 update", {"lab_hint": "OpenAI"})
        add_doc("raw-new", "canon-new", "anthropic safety report", {"lab_hint": "Anthropic"})

        dry_output = io.StringIO()
        with redirect_stdout(dry_output):
            dry_exit = main(["--db-path", str(self.db_path), "merge-events", "--limit", "100", "--dry-run"])

        self.assertEqual(dry_exit, 0)
        self.assertIn("processed=3", dry_output.getvalue())
        with self.store.connect() as conn:
            dry_unmerged_count = conn.execute(
                "SELECT COUNT(*) AS c FROM canonical_documents WHERE event_id IS NULL OR TRIM(event_id) = ''"
            ).fetchone()["c"]
        self.assertEqual(dry_unmerged_count, 3)

        write_output = io.StringIO()
        with redirect_stdout(write_output):
            write_exit = main(["--db-path", str(self.db_path), "merge-events", "--limit", "100"])

        self.assertEqual(write_exit, 0)
        text = write_output.getvalue()
        self.assertIn("matched_by_hint=1", text)
        self.assertIn("matched_by_rule=1", text)
        self.assertIn("created_new=1", text)

        with self.store.connect() as conn:
            unmerged_count = conn.execute(
                "SELECT COUNT(*) AS c FROM canonical_documents WHERE event_id IS NULL OR TRIM(event_id) = ''"
            ).fetchone()["c"]
            event_count = conn.execute("SELECT COUNT(*) AS c FROM events").fetchone()["c"]

        self.assertEqual(unmerged_count, 0)
        self.assertEqual(event_count, 4)

        rerun_output = io.StringIO()
        with redirect_stdout(rerun_output):
            rerun_exit = main(["--db-path", str(self.db_path), "merge-events", "--limit", "100"])

        self.assertEqual(rerun_exit, 0)
        self.assertIn("processed=0", rerun_output.getvalue())
        self.assertIn("created_new=0", rerun_output.getvalue())

    def test_m6_merge_rule_window_boundary(self) -> None:
        now = datetime.now(UTC)
        boundary_event = Event(
            event_id="event-boundary",
            title="openai boundary update",
            summary="boundary",
            event_type="signal",
            topics=["signal"],
            related_lab="OpenAI",
            status="under_review",
            priority="p2",
            created_at=now,
            updated_at=now,
            first_seen_at=now - timedelta(days=8),
            last_activity_at=now - timedelta(days=7, minutes=1),
        )
        self.store.upsert_event(boundary_event)
        self.store.upsert_raw_document(
            RawDocument(
                raw_id="raw-boundary",
                source_id="src-1",
                url="https://example.com/raw-boundary",
                title="openai boundary update",
                content="boundary-content",
                published_at=now,
                fetched_at=now,
                hash_sha256="hash-boundary",
                metadata_json=json.dumps({"lab_hint": "OpenAI"}, ensure_ascii=False),
                created_at=now,
                updated_at=now,
            )
        )
        self.store.upsert_canonical_document(
            CanonicalDocument(
                canonical_id="canon-boundary",
                raw_id="raw-boundary",
                event_id=None,
                normalized_title="openai boundary update",
                summary="boundary",
                key_points=["k1"],
                entities=["OpenAI"],
                canonical_version=1,
                created_at=now,
                updated_at=now,
            )
        )

        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["--db-path", str(self.db_path), "merge-events", "--limit", "100"])

        self.assertEqual(exit_code, 0)
        self.assertIn("created_new=1", output.getvalue())

    def test_m6_merge_rule_window_exactly_seven_days_matches(self) -> None:
        now = datetime.now(UTC)
        boundary_event = Event(
            event_id="event-boundary-7d",
            title="openai exact boundary update",
            summary="boundary",
            event_type="signal",
            topics=["signal"],
            related_lab="OpenAI",
            status="under_review",
            priority="p2",
            created_at=now,
            updated_at=now,
            first_seen_at=now - timedelta(days=10),
            last_activity_at=now - timedelta(days=7),
        )
        self.store.upsert_event(boundary_event)
        self.store.upsert_raw_document(
            RawDocument(
                raw_id="raw-boundary-7d",
                source_id="src-1",
                url="https://example.com/raw-boundary-7d",
                title="openai exact boundary update",
                content="boundary-content",
                published_at=now,
                fetched_at=now,
                hash_sha256="hash-boundary-7d",
                metadata_json=json.dumps({"lab_hint": "OpenAI"}, ensure_ascii=False),
                created_at=now,
                updated_at=now,
            )
        )
        self.store.upsert_canonical_document(
            CanonicalDocument(
                canonical_id="canon-boundary-7d",
                raw_id="raw-boundary-7d",
                event_id=None,
                normalized_title="openai exact boundary update",
                summary="boundary",
                key_points=["k1"],
                entities=["OpenAI"],
                canonical_version=1,
                created_at=now,
                updated_at=now,
            )
        )

        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["--db-path", str(self.db_path), "merge-events", "--limit", "100"])

        self.assertEqual(exit_code, 0)
        self.assertIn("matched_by_rule=1", output.getvalue())
        self.assertIn("created_new=0", output.getvalue())

    def test_m6_merge_lab_mismatch_does_not_match_rule(self) -> None:
        now = datetime.now(UTC)
        existing_event = Event(
            event_id="event-lab-mismatch",
            title="openai shared title",
            summary="mismatch",
            event_type="signal",
            topics=["signal"],
            related_lab="OpenAI",
            status="under_review",
            priority="p2",
            created_at=now,
            updated_at=now,
            first_seen_at=now,
            last_activity_at=now,
        )
        self.store.upsert_event(existing_event)
        self.store.upsert_raw_document(
            RawDocument(
                raw_id="raw-lab-mismatch",
                source_id="src-1",
                url="https://example.com/raw-lab-mismatch",
                title="openai shared title",
                content="content",
                published_at=now,
                fetched_at=now,
                hash_sha256="hash-lab-mismatch",
                metadata_json=json.dumps({"lab_hint": "Anthropic"}, ensure_ascii=False),
                created_at=now,
                updated_at=now,
            )
        )
        self.store.upsert_canonical_document(
            CanonicalDocument(
                canonical_id="canon-lab-mismatch",
                raw_id="raw-lab-mismatch",
                event_id=None,
                normalized_title="openai shared title",
                summary="summary",
                key_points=["k1"],
                entities=["Anthropic"],
                canonical_version=1,
                created_at=now,
                updated_at=now,
            )
        )

        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["--db-path", str(self.db_path), "merge-events", "--limit", "100"])

        self.assertEqual(exit_code, 0)
        self.assertIn("matched_by_rule=0", output.getvalue())
        self.assertIn("created_new=1", output.getvalue())

    def test_m6_merge_ignores_batch_order_for_existing_event_match(self) -> None:
        now = datetime.now(UTC)
        existing_event = Event(
            event_id="event-existing",
            title="openai agent runtime update",
            summary="existing",
            event_type="signal",
            topics=["signal"],
            related_lab="OpenAI",
            status="under_review",
            priority="p2",
            created_at=now - timedelta(days=2),
            updated_at=now - timedelta(days=2),
            first_seen_at=now - timedelta(days=2),
            last_activity_at=now - timedelta(days=2),
        )
        self.store.upsert_event(existing_event)

        def add_candidate(raw_id: str, canonical_id: str, published_at: datetime) -> None:
            self.store.upsert_raw_document(
                RawDocument(
                    raw_id=raw_id,
                    source_id="src-1",
                    url=f"https://example.com/{raw_id}",
                    title="openai agent runtime update",
                    content=f"content-{raw_id}",
                    published_at=published_at,
                    fetched_at=published_at,
                    hash_sha256=f"hash-{raw_id}",
                    metadata_json=json.dumps({"lab_hint": "OpenAI"}, ensure_ascii=False),
                    created_at=published_at,
                    updated_at=published_at,
                )
            )
            self.store.upsert_canonical_document(
                CanonicalDocument(
                    canonical_id=canonical_id,
                    raw_id=raw_id,
                    event_id=None,
                    normalized_title="openai agent runtime update",
                    summary="summary",
                    key_points=["k1"],
                    entities=["OpenAI"],
                    canonical_version=1,
                    created_at=published_at,
                    updated_at=published_at,
                )
            )

        add_candidate("raw-order-1", "canon-order-1", now)
        add_candidate("raw-order-2", "canon-order-2", now + timedelta(hours=2))

        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["--db-path", str(self.db_path), "merge-events", "--limit", "100"])

        self.assertEqual(exit_code, 0)
        text = output.getvalue()
        self.assertIn("matched_by_rule=2", text)
        self.assertIn("created_new=0", text)
        with self.store.connect() as conn:
            rows = conn.execute(
                "SELECT canonical_id, event_id FROM canonical_documents WHERE canonical_id IN (?, ?) ORDER BY canonical_id",
                ("canon-order-1", "canon-order-2"),
            ).fetchall()
        self.assertEqual(rows[0]["event_id"], "event-existing")
        self.assertEqual(rows[1]["event_id"], "event-existing")


if __name__ == "__main__":
    unittest.main()
