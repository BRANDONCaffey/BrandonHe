from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ai_info_collection.models import Event, Source
from ai_info_collection.storage import SQLiteStore
from ai_info_collection.ui import load_dashboard_data, render_dashboard


class UiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test.db"
        self.store = SQLiteStore(self.db_path)
        self.store.initialize()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_render_dashboard_contains_core_sections(self) -> None:
        self.store.upsert_source(
            Source(
                source_id="openai-news",
                layer="signal",
                lab="OpenAI",
                source_name="OpenAI News",
                source_type="web",
                mode="auto_fetch",
                url="https://openai.com/news/",
            )
        )
        self.store.upsert_event(
            Event(
                event_id="event-1",
                title="Model release",
                summary="release",
                event_type="signal",
                topics=["release"],
                related_lab="OpenAI",
                status="under_review",
                priority="p2",
            )
        )

        data = load_dashboard_data(self.store)
        html = render_dashboard(data, offline_mode=True)
        self.assertIn("AI Info Collection", html)
        self.assertIn("Recent Fetch Runs", html)
        self.assertIn("Recent Events", html)
        self.assertIn("offline mode", html)
        self.assertIn("Offline-safe commands", html)
        self.assertIn("Sources", html)
        self.assertIn(">1</div></article>", html)
        self.assertIn("event-1", html)


if __name__ == "__main__":
    unittest.main()
