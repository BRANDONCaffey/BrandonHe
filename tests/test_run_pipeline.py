from __future__ import annotations

import io
import json
import tempfile
import threading
import time
import unittest
from contextlib import redirect_stdout
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from ai_info_collection.cli import main
from ai_info_collection.storage import SQLiteStore


class RunPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test.db"
        self.store = SQLiteStore(self.db_path)
        self.store.initialize()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _write_jsonl(self, name: str, rows: list[dict[str, object]]) -> Path:
        path = Path(self.temp_dir.name) / name
        path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")
        return path

    def test_run_pipeline_success(self) -> None:
        input_path = self._write_jsonl(
            "success.jsonl",
            [
                {
                    "source_id": "openai-news",
                    "url": "https://example.com/a",
                    "title": "OpenAI runtime update",
                    "content": "OpenAI released runtime update.",
                    "published_at": "2026-04-10T00:00:00+00:00",
                    "tags": ["release"],
                    "lab_hint": "OpenAI",
                },
                {
                    "source_id": "anthropic-news",
                    "url": "https://example.com/b",
                    "title": "Anthropic policy update",
                    "content": "Anthropic released policy update.",
                    "published_at": "2026-04-11T00:00:00+00:00",
                    "tags": ["policy"],
                    "lab_hint": "Anthropic",
                },
            ],
        )

        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["--db-path", str(self.db_path), "run-pipeline", "--input", str(input_path)])

        self.assertEqual(exit_code, 0)
        text = output.getvalue()
        self.assertIn("status=success", text)
        self.assertIn("ingest_success=2", text)
        self.assertIn("ingest_failed=0", text)
        self.assertIn("error_count=0", text)

        with self.store.connect() as conn:
            run_row = conn.execute(
                "SELECT status, ingest_success, ingest_failed FROM pipeline_runs ORDER BY started_at DESC LIMIT 1"
            ).fetchone()
            err_count = conn.execute("SELECT COUNT(*) AS c FROM pipeline_run_errors").fetchone()["c"]

        self.assertIsNotNone(run_row)
        self.assertEqual(run_row["status"], "success")
        self.assertEqual(run_row["ingest_success"], 2)
        self.assertEqual(run_row["ingest_failed"], 0)
        self.assertEqual(err_count, 0)

    def test_run_pipeline_partial_success(self) -> None:
        input_path = self._write_jsonl(
            "partial.jsonl",
            [
                {
                    "source_id": "openai-news",
                    "url": "https://example.com/a",
                    "title": "OpenAI runtime update",
                    "content": "OpenAI released runtime update.",
                    "published_at": "2026-04-10T00:00:00+00:00",
                    "tags": ["release"],
                    "lab_hint": "OpenAI",
                },
                {
                    "source_id": "openai-news",
                    "url": "https://example.com/bad",
                    "title": "Broken line",
                    "content": "missing tags",
                    "published_at": "2026-04-10T01:00:00+00:00",
                    "lab_hint": "OpenAI",
                },
            ],
        )

        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["--db-path", str(self.db_path), "run-pipeline", "--input", str(input_path)])

        self.assertEqual(exit_code, 0)
        text = output.getvalue()
        self.assertIn("status=partial_success", text)
        self.assertIn("ingest_success=1", text)
        self.assertIn("ingest_failed=1", text)
        self.assertIn("error_count=1", text)

        with self.store.connect() as conn:
            run_row = conn.execute(
                "SELECT status, ingest_success, ingest_failed FROM pipeline_runs ORDER BY started_at DESC LIMIT 1"
            ).fetchone()
            err_count = conn.execute("SELECT COUNT(*) AS c FROM pipeline_run_errors").fetchone()["c"]

        self.assertEqual(run_row["status"], "partial_success")
        self.assertEqual(run_row["ingest_success"], 1)
        self.assertEqual(run_row["ingest_failed"], 1)
        self.assertEqual(err_count, 1)

    def test_run_pipeline_failed_when_all_invalid(self) -> None:
        input_path = self._write_jsonl(
            "failed.jsonl",
            [
                {
                    "source_id": "openai-news",
                    "url": "https://example.com/bad1",
                    "title": "Broken line 1",
                    "content": "missing tags",
                    "published_at": "2026-04-10T00:00:00+00:00",
                    "lab_hint": "OpenAI",
                },
                {
                    "source_id": "openai-news",
                    "url": "https://example.com/bad2",
                    "title": "Broken line 2",
                    "content": "missing tags",
                    "published_at": "2026-04-10T01:00:00+00:00",
                    "lab_hint": "OpenAI",
                },
            ],
        )

        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["--db-path", str(self.db_path), "run-pipeline", "--input", str(input_path)])

        self.assertEqual(exit_code, 1)
        text = output.getvalue()
        self.assertIn("status=failed", text)
        self.assertIn("ingest_success=0", text)
        self.assertIn("ingest_failed=2", text)
        self.assertIn("error_count=2", text)

        with self.store.connect() as conn:
            run_row = conn.execute(
                "SELECT status, ingest_success, ingest_failed FROM pipeline_runs ORDER BY started_at DESC LIMIT 1"
            ).fetchone()
            err_count = conn.execute("SELECT COUNT(*) AS c FROM pipeline_run_errors").fetchone()["c"]

        self.assertEqual(run_row["status"], "failed")
        self.assertEqual(run_row["ingest_success"], 0)
        self.assertEqual(run_row["ingest_failed"], 2)
        self.assertEqual(err_count, 2)

    def test_run_pipeline_dry_run_keeps_business_tables_unchanged(self) -> None:
        input_path = self._write_jsonl(
            "dryrun.jsonl",
            [
                {
                    "source_id": "openai-news",
                    "url": "https://example.com/a",
                    "title": "OpenAI runtime update",
                    "content": "OpenAI released runtime update.",
                    "published_at": "2026-04-10T00:00:00+00:00",
                    "tags": ["release"],
                    "lab_hint": "OpenAI",
                },
                {
                    "source_id": "openai-news",
                    "url": "https://example.com/bad",
                    "title": "Broken line",
                    "content": "missing tags",
                    "published_at": "2026-04-10T01:00:00+00:00",
                    "lab_hint": "OpenAI",
                },
            ],
        )

        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(
                [
                    "--db-path",
                    str(self.db_path),
                    "run-pipeline",
                    "--input",
                    str(input_path),
                    "--dry-run",
                ]
            )

        self.assertEqual(exit_code, 0)
        text = output.getvalue()
        self.assertIn("dry_run=True", text)
        self.assertIn("status=partial_success", text)

        with self.store.connect() as conn:
            raw_count = conn.execute("SELECT COUNT(*) AS c FROM raw_documents").fetchone()["c"]
            canonical_count = conn.execute("SELECT COUNT(*) AS c FROM canonical_documents").fetchone()["c"]
            events_count = conn.execute("SELECT COUNT(*) AS c FROM events").fetchone()["c"]
            run_row = conn.execute(
                "SELECT status, ingest_success, ingest_failed FROM pipeline_runs ORDER BY started_at DESC LIMIT 1"
            ).fetchone()
            err_count = conn.execute("SELECT COUNT(*) AS c FROM pipeline_run_errors").fetchone()["c"]

        self.assertEqual(raw_count, 0)
        self.assertEqual(canonical_count, 0)
        self.assertEqual(events_count, 0)
        self.assertEqual(run_row["status"], "partial_success")
        self.assertEqual(run_row["ingest_success"], 1)
        self.assertEqual(run_row["ingest_failed"], 1)
        self.assertEqual(err_count, 1)

    def test_run_pipeline_duplicate_guard_blocks_second_run(self) -> None:
        input_path = self._write_jsonl(
            "dup.jsonl",
            [
                {
                    "source_id": "openai-news",
                    "url": "https://example.com/a",
                    "title": "OpenAI runtime update",
                    "content": "OpenAI released runtime update.",
                    "published_at": "2026-04-10T00:00:00+00:00",
                    "tags": ["release"],
                    "lab_hint": "OpenAI",
                },
            ],
        )
        first_out = io.StringIO()
        with redirect_stdout(first_out):
            first_exit = main(["--db-path", str(self.db_path), "run-pipeline", "--input", str(input_path)])
        self.assertEqual(first_exit, 0)

        second_out = io.StringIO()
        with redirect_stdout(second_out):
            second_exit = main(["--db-path", str(self.db_path), "run-pipeline", "--input", str(input_path)])
        self.assertEqual(second_exit, 1)
        self.assertIn("status_reason=duplicate_run_blocked", second_out.getvalue())

    def test_run_pipeline_concurrent_guard_blocks_one_runner(self) -> None:
        input_path = self._write_jsonl(
            "concurrent.jsonl",
            [
                {
                    "source_id": "openai-news",
                    "url": "https://example.com/a",
                    "title": "OpenAI runtime update",
                    "content": "OpenAI released runtime update.",
                    "published_at": "2026-04-10T00:00:00+00:00",
                    "tags": ["release"],
                    "lab_hint": "OpenAI",
                },
            ],
        )

        from ai_info_collection import pipeline as pipeline_module

        original_ingest = pipeline_module.ingest_signals

        def slow_ingest(*args, **kwargs):
            time.sleep(0.2)
            return original_ingest(*args, **kwargs)

        outputs: list[str] = []
        exits: list[int] = []

        def run_once() -> None:
            out = io.StringIO()
            with redirect_stdout(out):
                code = main(["--db-path", str(self.db_path), "run-pipeline", "--input", str(input_path)])
            outputs.append(out.getvalue())
            exits.append(code)

        with patch("ai_info_collection.pipeline.ingest_signals", side_effect=slow_ingest):
            t1 = threading.Thread(target=run_once)
            t2 = threading.Thread(target=run_once)
            t1.start()
            time.sleep(0.05)
            t2.start()
            t1.join()
            t2.join()

        self.assertEqual(len(exits), 2)
        self.assertIn(0, exits)
        self.assertIn(1, exits)
        self.assertTrue(any("status_reason=concurrent_run_blocked" in out for out in outputs))

    def test_run_pipeline_recovers_stale_running_and_continues(self) -> None:
        stale_started_at = datetime.now(UTC) - timedelta(minutes=60)
        with self.store.connect() as conn:
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
                    "run-stale",
                    stale_started_at.isoformat(),
                    None,
                    "stale.jsonl",
                    "sig-stale",
                    0,
                    100,
                    "running",
                    None,
                ),
            )

        input_path = self._write_jsonl(
            "stale-recover.jsonl",
            [
                {
                    "source_id": "openai-news",
                    "url": "https://example.com/a",
                    "title": "OpenAI runtime update",
                    "content": "OpenAI released runtime update.",
                    "published_at": "2026-04-10T00:00:00+00:00",
                    "tags": ["release"],
                    "lab_hint": "OpenAI",
                },
            ],
        )

        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["--db-path", str(self.db_path), "run-pipeline", "--input", str(input_path)])

        self.assertEqual(exit_code, 0)
        self.assertIn("status=success", output.getvalue())

        with self.store.connect() as conn:
            stale_row = conn.execute(
                "SELECT status, status_reason FROM pipeline_runs WHERE run_id = 'run-stale'"
            ).fetchone()
        self.assertIsNotNone(stale_row)
        self.assertEqual(stale_row["status"], "failed")
        self.assertEqual(stale_row["status_reason"], "stale_running_recovered")


if __name__ == "__main__":
    unittest.main()
