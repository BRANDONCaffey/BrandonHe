from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import ANY, patch

from ai_info_collection.cli import main
from ai_info_collection.fetch import FetchStats
from ai_info_collection.ingest import IngestStats
from ai_info_collection.merge import MergeStats
from ai_info_collection.models import SignalInput
from ai_info_collection.pipeline import PipelineRunResult
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

    def test_start_offline_uses_sample_jsonl_and_prints_fetch_logs(self) -> None:
        fake_result = PipelineRunResult(
            run_id="run-offline",
            status="success",
            status_reason=None,
            fetch_stats=FetchStats(),
            ingest_stats=IngestStats(total=2, success=2, skipped_duplicates=0, failed=0),
            merge_stats=MergeStats(processed=2, matched_by_hint=0, matched_by_rule=1, created_new=1),
            error_count=0,
            exit_code=0,
        )
        output = io.StringIO()
        with patch("ai_info_collection.cli.run_pipeline", return_value=fake_result) as mocked_pipeline:
            with redirect_stdout(output):
                code = main(["--db-path", str(self.db_path), "start", "--mode", "offline"])

        self.assertEqual(code, 0)
        call_kwargs = mocked_pipeline.call_args.kwargs
        self.assertEqual(call_kwargs["input_path"], "sample.jsonl")
        self.assertIn("== Start ==", output.getvalue())
        self.assertIn("== Recent Fetch Logs ==", output.getvalue())
        self.assertIn("run_id=run-offline", output.getvalue())

    def test_start_online_seeds_sources_then_runs_pipeline(self) -> None:
        fake_result = PipelineRunResult(
            run_id="run-online",
            status="success",
            status_reason=None,
            fetch_stats=FetchStats(total_sources=4, success_sources=3, failed_sources=1, fetched_items=12, parsed_items=8),
            ingest_stats=IngestStats(total=8, success=8, skipped_duplicates=0, failed=0),
            merge_stats=MergeStats(processed=8, matched_by_hint=2, matched_by_rule=3, created_new=3),
            error_count=0,
            exit_code=0,
        )
        output = io.StringIO()
        with patch("ai_info_collection.cli.seed_sources", return_value=4) as mocked_seed:
            with patch("ai_info_collection.cli.run_pipeline", return_value=fake_result) as mocked_pipeline:
                with redirect_stdout(output):
                    code = main(
                        [
                            "--db-path",
                            str(self.db_path),
                            "start",
                            "--mode",
                            "online",
                            "--source-limit",
                            "3",
                        ]
                    )

        self.assertEqual(code, 0)
        mocked_seed.assert_called_once_with(store=ANY, preset="official-ai")
        call_kwargs = mocked_pipeline.call_args.kwargs
        self.assertIsNone(call_kwargs["input_path"])
        self.assertEqual(call_kwargs["source_limit"], 3)
        self.assertIn("seeded_sources=4", output.getvalue())
        self.assertIn("run_id=run-online", output.getvalue())

    def test_start_without_mode_prompts_once_and_routes_to_online(self) -> None:
        fake_result = PipelineRunResult(
            run_id="run-interactive",
            status="success",
            status_reason=None,
            fetch_stats=FetchStats(total_sources=1, success_sources=1, failed_sources=0, fetched_items=2, parsed_items=2),
            ingest_stats=IngestStats(total=2, success=2, skipped_duplicates=0, failed=0),
            merge_stats=MergeStats(processed=2, matched_by_hint=1, matched_by_rule=0, created_new=1),
            error_count=0,
            exit_code=0,
        )
        with patch("builtins.input", return_value="2"):
            with patch("ai_info_collection.cli.seed_sources", return_value=4):
                with patch("ai_info_collection.cli.run_pipeline", return_value=fake_result) as mocked_pipeline:
                    code = main(["--db-path", str(self.db_path), "start"])
        self.assertEqual(code, 0)
        self.assertIsNone(mocked_pipeline.call_args.kwargs["input_path"])

    def test_start_offline_force_new_db_uses_fresh_store(self) -> None:
        fake_result = PipelineRunResult(
            run_id="run-fresh-db",
            status="success",
            status_reason=None,
            fetch_stats=FetchStats(),
            ingest_stats=IngestStats(total=2, success=2, skipped_duplicates=0, failed=0),
            merge_stats=MergeStats(processed=2, matched_by_hint=0, matched_by_rule=0, created_new=2),
            error_count=0,
            exit_code=0,
        )
        output = io.StringIO()
        with patch("ai_info_collection.cli.run_pipeline", return_value=fake_result) as mocked_pipeline:
            with redirect_stdout(output):
                code = main(
                    [
                        "--db-path",
                        str(self.db_path),
                        "start",
                        "--mode",
                        "offline",
                        "--force-new-db",
                    ]
                )
        self.assertEqual(code, 0)
        used_store = mocked_pipeline.call_args.kwargs["store"]
        self.assertNotEqual(Path(used_store.db_path), self.db_path)
        self.assertIn(".offline.", Path(used_store.db_path).name)
        self.assertTrue(Path(used_store.db_path).exists())
        self.assertIn("using_new_db=", output.getvalue())


if __name__ == "__main__":
    unittest.main()
