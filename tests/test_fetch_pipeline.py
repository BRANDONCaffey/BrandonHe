from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from ai_info_collection.cli import main
from ai_info_collection.fetch import FetchStats
from ai_info_collection.models import SignalInput
from ai_info_collection.storage import SQLiteStore


class FetchPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test.db"
        self.store = SQLiteStore(self.db_path)
        self.store.initialize()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_seed_sources_and_recent_fetch_runs(self) -> None:
        seed_output = io.StringIO()
        with redirect_stdout(seed_output):
            seed_code = main(["--db-path", str(self.db_path), "seed-sources", "--preset", "official-ai"])
        self.assertEqual(seed_code, 0)
        self.assertIn("seeded=4", seed_output.getvalue())

        with self.store.connect() as conn:
            count = conn.execute("SELECT COUNT(*) AS c FROM sources WHERE fetch_enabled = 1").fetchone()["c"]
        self.assertEqual(count, 4)

        recent_output = io.StringIO()
        with redirect_stdout(recent_output):
            recent_code = main(["--db-path", str(self.db_path), "recent-fetch-runs", "--limit", "5"])
        self.assertEqual(recent_code, 0)
        self.assertIn("(empty)", recent_output.getvalue())

    def test_fetch_sources_command_with_mocked_fetcher(self) -> None:
        main(["--db-path", str(self.db_path), "seed-sources", "--preset", "official-ai"])
        mocked_signals = [
            SignalInput(
                source_id="openai-rss",
                url="https://openai.com/news/test",
                title="OpenAI test",
                content="OpenAI content " * 20,
                published_at="2026-04-10T00:00:00+00:00",
                tags=["auto_fetch"],
                lab_hint="OpenAI",
            )
        ]
        mocked_stats = FetchStats(total_sources=1, success_sources=1, failed_sources=0, fetched_items=1, parsed_items=1)
        output = io.StringIO()
        with patch("ai_info_collection.cli.fetch_sources", return_value=(mocked_signals, mocked_stats)):
            with redirect_stdout(output):
                code = main(["--db-path", str(self.db_path), "fetch-sources", "--source-limit", "1"])
        self.assertEqual(code, 0)
        text = output.getvalue()
        self.assertIn("success_sources=1", text)
        self.assertIn("parsed_items=1", text)

    def test_run_pipeline_without_input_uses_fetch_path(self) -> None:
        signals = [
            SignalInput(
                source_id="openai-rss",
                url="https://openai.com/news/test",
                title="OpenAI runtime update",
                content="OpenAI released runtime update with technical details." * 5,
                published_at="2026-04-10T00:00:00+00:00",
                tags=["auto_fetch"],
                lab_hint="OpenAI",
            )
        ]
        mocked_stats = FetchStats(total_sources=1, success_sources=1, failed_sources=0, fetched_items=1, parsed_items=1)
        output = io.StringIO()
        with patch("ai_info_collection.pipeline.fetch_sources", return_value=(signals, mocked_stats)):
            with redirect_stdout(output):
                code = main(["--db-path", str(self.db_path), "run-pipeline", "--source-limit", "1"])

        self.assertEqual(code, 0)
        text = output.getvalue()
        self.assertIn("fetch_total=1", text)
        self.assertIn("ingest_success=1", text)
        self.assertIn("status=success", text)
        with self.store.connect() as conn:
            run_row = conn.execute(
                "SELECT fetch_total, fetch_success, fetch_failed FROM pipeline_runs ORDER BY started_at DESC LIMIT 1"
            ).fetchone()
        self.assertEqual(run_row["fetch_total"], 1)
        self.assertEqual(run_row["fetch_success"], 1)
        self.assertEqual(run_row["fetch_failed"], 0)


if __name__ == "__main__":
    unittest.main()
