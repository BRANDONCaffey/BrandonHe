from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from ai_info_collection.cli import main
from ai_info_collection.meaning import MeaningCardInput, build_meaning_card
from ai_info_collection.models import Event, Source
from ai_info_collection.storage import SQLiteStore


class StorageAndCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test.db"
        self.store = SQLiteStore(self.db_path)
        self.store.initialize()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_review_lists_missing_meaning_fields(self) -> None:
        self.store.upsert_event(
            Event(
                event_id="event-1",
                title="OpenAI product shift",
                summary="Release cadence changed",
                event_type="release",
                topics=["deployment"],
                related_lab="OpenAI",
                status="under_review",
                priority="p1",
            )
        )
        draft_card = build_meaning_card(
            MeaningCardInput(
                id="meaning-1",
                event_id="event-1",
                longform_source="https://example.com/episode",
                core_takeaway="团队在重构产品叙事。",
                why_it_matters="这会改变市场预期。",
                framework_tags=["competition"],
                missing_reason_codes=["insufficient_material"],
            )
        )
        self.store.upsert_meaning_card(draft_card)

        missing_why_card = build_meaning_card(
            MeaningCardInput(
                id="meaning-why-empty",
                event_id="event-1",
                longform_source="https://example.com/why-empty",
                core_takeaway="结论已形成。",
                why_it_matters="   ",
                framework_tags=["competition"],
                interpretation_type="market_shift",
                what_changed_before="以前节奏慢",
                what_changed_now="现在节奏快",
                what_changed_delta="发布频次提升",
            )
        )
        self.store.upsert_meaning_card(missing_why_card)

        missing_framework_card = build_meaning_card(
            MeaningCardInput(
                id="meaning-framework-blank",
                event_id="event-1",
                longform_source="https://example.com/framework-blank",
                core_takeaway="框架待补齐。",
                why_it_matters="影响对比框架选择。",
                framework_tags=["   "],
                interpretation_type="market_shift",
                what_changed_before="以前策略保守",
                what_changed_now="现在策略激进",
                what_changed_delta="窗口期缩短",
            )
        )
        self.store.upsert_meaning_card(missing_framework_card)

        dirty_framework_json_card = build_meaning_card(
            MeaningCardInput(
                id="meaning-framework-dirty",
                event_id="event-1",
                longform_source="https://example.com/framework-dirty",
                core_takeaway="存储层脏数据样例。",
                why_it_matters="验证 review 质量闸门。",
                framework_tags=["competition"],
                interpretation_type="market_shift",
                what_changed_before="以前仅有单一来源",
                what_changed_now="现在多来源对照",
                what_changed_delta="证据一致性提升",
            )
        )
        self.store.upsert_meaning_card(dirty_framework_json_card)
        with self.store.connect() as conn:
            conn.execute(
                "UPDATE meaning_cards SET framework_tags_json = ? WHERE id = ?",
                ("not-json", "meaning-framework-dirty"),
            )

        mixed_framework_tags_card = build_meaning_card(
            MeaningCardInput(
                id="meaning-framework-mixed",
                event_id="event-1",
                longform_source="https://example.com/framework-mixed",
                core_takeaway="混合标签场景。",
                why_it_matters="只要有一个有效标签就应视为通过。",
                framework_tags=["   ", "competition"],
                interpretation_type="market_shift",
                what_changed_before="之前标签规则不清晰。",
                what_changed_now="现在规则明确为至少一个有效标签。",
                what_changed_delta="混合标签不应被误判缺失。",
            )
        )
        self.store.upsert_meaning_card(mixed_framework_tags_card)

        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["--db-path", str(self.db_path), "review"])

        text = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("MeaningCards missing what_changed", text)
        self.assertIn("meaning-1", text)
        self.assertIn("MeaningCards missing interpretation_type", text)
        self.assertIn("MeaningCards missing why_it_matters", text)
        self.assertIn("meaning-why-empty", text)
        self.assertIn("MeaningCards missing framework_tags", text)
        self.assertIn("meaning-framework-blank", text)
        self.assertIn("meaning-framework-dirty", text)
        self.assertNotIn("meaning-framework-mixed", text)

    def test_source_health_and_recent_events_commands(self) -> None:
        self.store.upsert_source(
            Source(
                source_id="openai-news",
                layer="fact",
                lab="OpenAI",
                source_name="OpenAI News",
                source_type="blog",
                mode="dynamic_feed",
                url="https://openai.com/news/",
                quality_score=0.95,
            )
        )
        self.store.upsert_event(
            Event(
                event_id="event-2",
                title="Anthropic eval change",
                summary="Updated evaluation framing",
                event_type="research",
                topics=["evals"],
                related_lab="Anthropic",
                status="verified",
                priority="p2",
            )
        )

        source_output = io.StringIO()
        with redirect_stdout(source_output):
            source_exit = main(["--db-path", str(self.db_path), "source-health"])
        recent_output = io.StringIO()
        with redirect_stdout(recent_output):
            recent_exit = main(["--db-path", str(self.db_path), "recent-events", "--limit", "5"])

        self.assertEqual(source_exit, 0)
        self.assertEqual(recent_exit, 0)
        self.assertIn("openai-news", source_output.getvalue())
        self.assertIn("event-2", recent_output.getvalue())


if __name__ == "__main__":
    unittest.main()
