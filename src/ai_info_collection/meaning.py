from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from ai_info_collection.models import (
    ChangeScope,
    InterpretationType,
    MeaningCard,
    has_non_empty_framework_tags,
)


MISSING_REASON_LABELS = {
    "insufficient_material": "材料不足",
    "unclear_time_comparison": "时间对比不清",
    "missing_prior_baseline": "缺少前态基线",
}


@dataclass(slots=True)
class MeaningCardInput:
    id: str
    event_id: str
    longform_source: str
    core_takeaway: str
    why_it_matters: str
    watch_next: str = ""
    confidence: float = 0.5
    evidence: list[str] = field(default_factory=list)
    interpretation_type: InterpretationType | None = None
    change_scope: ChangeScope | None = None
    what_changed_before: str = ""
    what_changed_now: str = ""
    what_changed_delta: str = ""
    why_now: str = ""
    implications: str = ""
    counterpoints: str = ""
    key_uncertainties: str = ""
    framework_tags: list[str] = field(default_factory=list)
    related_fact_id: str | None = None
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    missing_reason_codes: list[str] = field(default_factory=list)


def _build_review_notes(input_data: MeaningCardInput, missing_fields: list[str]) -> str:
    reasons = [
        MISSING_REASON_LABELS[code]
        for code in input_data.missing_reason_codes
        if code in MISSING_REASON_LABELS
    ]
    parts: list[str] = []
    if reasons:
        parts.append("缺失原因：" + "、".join(reasons))
    if missing_fields:
        parts.append("缺失字段：" + ", ".join(missing_fields))
    return "；".join(parts)


def build_meaning_card(input_data: MeaningCardInput) -> MeaningCard:
    missing_fields: list[str] = []
    if not input_data.why_it_matters.strip():
        missing_fields.append("why_it_matters")
    if not input_data.what_changed_before.strip():
        missing_fields.append("what_changed_before")
    if not input_data.what_changed_now.strip():
        missing_fields.append("what_changed_now")
    if not input_data.what_changed_delta.strip():
        missing_fields.append("what_changed_delta")
    if input_data.interpretation_type is None:
        missing_fields.append("interpretation_type")
    if not has_non_empty_framework_tags(input_data.framework_tags):
        missing_fields.append("framework_tags")

    review_notes = _build_review_notes(input_data, missing_fields)
    status = "draft" if missing_fields else "reviewed"

    card = MeaningCard(
        id=input_data.id,
        event_id=input_data.event_id,
        related_fact_id=input_data.related_fact_id,
        longform_source=input_data.longform_source,
        core_takeaway=input_data.core_takeaway,
        why_it_matters=input_data.why_it_matters,
        watch_next=input_data.watch_next,
        status=status,
        confidence=input_data.confidence,
        evidence=input_data.evidence,
        review_notes=review_notes,
        reviewed_by=input_data.reviewed_by,
        reviewed_at=input_data.reviewed_at if status != "draft" else None,
        interpretation_type=input_data.interpretation_type,
        change_scope=input_data.change_scope,
        what_changed_before=input_data.what_changed_before,
        what_changed_now=input_data.what_changed_now,
        what_changed_delta=input_data.what_changed_delta,
        why_now=input_data.why_now,
        implications=input_data.implications,
        counterpoints=input_data.counterpoints,
        key_uncertainties=input_data.key_uncertainties,
        framework_tags=input_data.framework_tags,
    )
    issues = card.validate()
    if issues and "draft status used for complete meaning card" not in issues:
        # Validation errors are reflected through draft status and review notes.
        pass
    if card.status == "reviewed" and not card.reviewed_at:
        card.reviewed_at = datetime.now(UTC)
    return card
