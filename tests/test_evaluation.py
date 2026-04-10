from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from ai_info_collection.cli import main
from ai_info_collection.storage import SQLiteStore


class EvaluationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test.db"
        self.replay_path = Path(self.temp_dir.name) / "replay_1k.jsonl"
        self.store = SQLiteStore(self.db_path)
        self.store.initialize()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_generate_replay_dataset_has_expected_rows(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(
                [
                    "--db-path",
                    str(self.db_path),
                    "generate-replay-dataset",
                    "--output",
                    str(self.replay_path),
                    "--rows",
                    "1000",
                    "--seed",
                    "42",
                ]
            )

        self.assertEqual(code, 0)
        self.assertTrue(self.replay_path.exists())
        lines = self.replay_path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 1000)
        self.assertIn("rows=1000", output.getvalue())
        self.assertIn("expected_event_key", lines[0])

    def test_evaluate_merge_persists_metrics(self) -> None:
        main(
            [
                "--db-path",
                str(self.db_path),
                "generate-replay-dataset",
                "--output",
                str(self.replay_path),
                "--rows",
                "1000",
                "--seed",
                "7",
            ]
        )

        output = io.StringIO()
        with redirect_stdout(output):
            code = main(
                [
                    "--db-path",
                    str(self.db_path),
                    "evaluate-merge",
                    "--input",
                    str(self.replay_path),
                ]
            )

        self.assertEqual(code, 0)
        text = output.getvalue()
        self.assertIn("rows_total=1000", text)
        self.assertIn("false_merge_rate=", text)
        self.assertIn("miss_merge_rate=", text)

        with self.store.connect() as conn:
            row = conn.execute(
                "SELECT rows_total, event_groups_truth, false_merge_rate, miss_merge_rate FROM merge_eval_runs ORDER BY started_at DESC LIMIT 1"
            ).fetchone()

        self.assertIsNotNone(row)
        self.assertEqual(row["rows_total"], 1000)
        self.assertGreaterEqual(row["event_groups_truth"], 1)
        self.assertGreaterEqual(row["false_merge_rate"], 0.0)
        self.assertLessEqual(row["false_merge_rate"], 1.0)
        self.assertGreaterEqual(row["miss_merge_rate"], 0.0)
        self.assertLessEqual(row["miss_merge_rate"], 1.0)

    def test_evaluate_merge_returns_nonzero_when_pipeline_fails(self) -> None:
        missing_path = Path(self.temp_dir.name) / "missing.jsonl"
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(
                [
                    "--db-path",
                    str(self.db_path),
                    "evaluate-merge",
                    "--input",
                    str(missing_path),
                ]
            )

        self.assertEqual(code, 1)
        text = output.getvalue()
        self.assertIn("error=", text)
        self.assertIn("pipeline execution failed during evaluate-merge", text)

        with self.store.connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS c FROM merge_eval_runs").fetchone()
        self.assertEqual(row["c"], 0)


if __name__ == "__main__":
    unittest.main()
