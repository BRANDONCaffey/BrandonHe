from __future__ import annotations

import unittest

from ai_info_collection.meaning import MeaningCardInput, build_meaning_card


class MeaningCardGenerationTests(unittest.TestCase):
    def test_complete_meaning_card_is_reviewed(self) -> None:
        card = build_meaning_card(
            MeaningCardInput(
                id="meaning-1",
                event_id="event-1",
                longform_source="https://example.com/podcast",
                core_takeaway="模型从 demo 走向稳定产品化。",
                why_it_matters="这说明竞争从展示能力转向交付能力。",
                watch_next="关注后续 API 和定价变化。",
                interpretation_type="product_shift",
                change_scope="product",
                what_changed_before="之前核心能力主要停留在演示和测试环境。",
                what_changed_now="现在能力被放进正式产品和对外接口。",
                what_changed_delta="变化在于能力从可展示样品变成可交付产品能力。",
                why_now="因为官方开始把能力放入稳定发布节奏。",
                implications="后续会影响 API 采用和竞争节奏。",
                counterpoints="目前仍可能只覆盖部分用户。",
                key_uncertainties="真实稳定性和成本结构仍待观察。",
                framework_tags=["deployment", "competition"],
                evidence=["官方播客原话", "发布页说明"],
            )
        )
        self.assertEqual(card.status, "reviewed")
        self.assertTrue(card.why_it_matters)
        self.assertTrue(card.what_changed_before)
        self.assertTrue(card.what_changed_now)
        self.assertTrue(card.what_changed_delta)
        self.assertGreaterEqual(len(card.framework_tags), 1)

    def test_missing_what_changed_forces_draft_and_reason(self) -> None:
        card = build_meaning_card(
            MeaningCardInput(
                id="meaning-2",
                event_id="event-2",
                longform_source="https://example.com/interview",
                core_takeaway="访谈强调 agent 很重要。",
                why_it_matters="说明团队资源配置可能变化。",
                watch_next="继续看产品发布。",
                interpretation_type="narrative_shift",
                framework_tags=["agents"],
                missing_reason_codes=["missing_prior_baseline"],
            )
        )
        self.assertEqual(card.status, "draft")
        self.assertIn("缺少前态基线", card.review_notes)
        self.assertIn("what_changed_before", card.review_notes)

    def test_missing_interpretation_type_is_draft(self) -> None:
        card = build_meaning_card(
            MeaningCardInput(
                id="meaning-3",
                event_id="event-3",
                longform_source="https://example.com/talk",
                core_takeaway="研究重点发生变化。",
                why_it_matters="会影响评测与路线判断。",
                watch_next="看下一次论文或发布。",
                what_changed_before="之前重点是扩大上下文长度。",
                what_changed_now="现在重点转向 agent 执行能力。",
                what_changed_delta="焦点从单模型能力扩展转向工作流执行。",
                framework_tags=["agents"],
                missing_reason_codes=["unclear_time_comparison"],
            )
        )
        self.assertEqual(card.status, "draft")
        self.assertIn("interpretation_type", card.review_notes)

    def test_whitespace_framework_tags_is_draft(self) -> None:
        card = build_meaning_card(
            MeaningCardInput(
                id="meaning-4",
                event_id="event-4",
                longform_source="https://example.com/update",
                core_takeaway="结论完整但标签是空白。",
                why_it_matters="需要防止空白标签绕过校验。",
                interpretation_type="product_shift",
                what_changed_before="之前需要至少一个有效框架标签。",
                what_changed_now="现在输入了只有空格的标签。",
                what_changed_delta="规则应将其视为缺失。",
                framework_tags=["   "],
            )
        )
        self.assertEqual(card.status, "draft")
        self.assertIn("framework_tags", card.review_notes)

    def test_whitespace_why_it_matters_forces_draft_and_review_notes(self) -> None:
        card = build_meaning_card(
            MeaningCardInput(
                id="meaning-5",
                event_id="event-5",
                longform_source="https://example.com/note",
                core_takeaway="核心结论存在，但意义字段为空白。",
                why_it_matters="   ",
                interpretation_type="product_shift",
                what_changed_before="之前该能力在内测。",
                what_changed_now="现在能力进入公开发布。",
                what_changed_delta="从内测转为公开可用。",
                framework_tags=["deployment"],
            )
        )
        self.assertEqual(card.status, "draft")
        self.assertIn("why_it_matters", card.review_notes)

    def test_whitespace_what_changed_now_forces_draft_and_review_notes(self) -> None:
        card = build_meaning_card(
            MeaningCardInput(
                id="meaning-6",
                event_id="event-6",
                longform_source="https://example.com/post",
                core_takeaway="变化描述缺少当前态。",
                why_it_matters="会影响我们判断变化是否真实发生。",
                interpretation_type="market_shift",
                what_changed_before="之前仅少数地区提供。",
                what_changed_now="   ",
                what_changed_delta="从局部试点扩展到更广范围。",
                framework_tags=["distribution"],
            )
        )
        self.assertEqual(card.status, "draft")
        self.assertIn("what_changed_now", card.review_notes)

    def test_whitespace_what_changed_delta_forces_draft_and_review_notes(self) -> None:
        card = build_meaning_card(
            MeaningCardInput(
                id="meaning-7",
                event_id="event-7",
                longform_source="https://example.com/brief",
                core_takeaway="变化差异字段为空白。",
                why_it_matters="缺少差异会降低可解释性。",
                interpretation_type="capability_shift",
                what_changed_before="之前主要依赖人工流程。",
                what_changed_now="现在引入自动化执行链路。",
                what_changed_delta="   ",
                framework_tags=["automation"],
            )
        )
        self.assertEqual(card.status, "draft")
        self.assertIn("what_changed_delta", card.review_notes)

    def test_validate_rejects_draft_status_for_complete_card(self) -> None:
        card = build_meaning_card(
            MeaningCardInput(
                id="meaning-8",
                event_id="event-8",
                longform_source="https://example.com/report",
                core_takeaway="字段完整但状态被手动改为 draft。",
                why_it_matters="用于覆盖状态一致性分支。",
                interpretation_type="research_shift",
                what_changed_before="之前研究重点在扩展训练数据。",
                what_changed_now="现在研究重点转向推理效率优化。",
                what_changed_delta="从数据规模转向推理效率。",
                framework_tags=["efficiency"],
            )
        )
        card.status = "draft"

        issues = card.validate()

        self.assertIn("draft status used for complete meaning card", issues)


if __name__ == "__main__":
    unittest.main()
