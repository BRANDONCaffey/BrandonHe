from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal


MeaningCardStatus = Literal["draft", "reviewed", "published", "stale"]
InterpretationType = Literal[
    "capability_shift",
    "product_shift",
    "research_shift",
    "market_shift",
    "org_shift",
    "policy_shift",
    "narrative_shift",
]
ChangeScope = Literal["model", "api", "product", "lab", "ecosystem", "industry"]


def utc_now() -> datetime:
    return datetime.now(UTC)


def has_non_empty_framework_tags(framework_tags: list[str]) -> bool:
    return any(tag.strip() for tag in framework_tags)


@dataclass(slots=True)
class Event:
    event_id: str
    title: str
    summary: str
    event_type: str
    topics: list[str]
    related_lab: str | None
    status: str
    priority: str
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    first_seen_at: datetime = field(default_factory=utc_now)
    last_activity_at: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class Source:
    source_id: str
    layer: str
    lab: str
    source_name: str
    source_type: str
    mode: str
    url: str
    governance_status: str = "active"
    trust_level: str = "official"
    verification_role: str = "multi_role"
    owner: str | None = None
    review_frequency: str | None = None
    last_reviewed_at: datetime | None = None
    last_success_at: datetime | None = None
    last_failure_at: datetime | None = None
    failure_count: int = 0
    quality_score: float | None = None
    notes: str | None = None
    robots_policy_checked: bool = False
    terms_risk_level: str = "unknown"
    fetch_enabled: bool = True
    fetch_parser: str = "article"
    fetch_selector: str | None = None
    fetch_interval_minutes: int | None = None


@dataclass(slots=True)
class MeaningCard:
    id: str
    event_id: str
    related_fact_id: str | None
    longform_source: str
    core_takeaway: str
    why_it_matters: str
    watch_next: str
    status: MeaningCardStatus
    confidence: float
    evidence: list[str]
    review_notes: str
    reviewed_by: str | None
    reviewed_at: datetime | None
    interpretation_type: InterpretationType | None
    change_scope: ChangeScope | None
    what_changed_before: str
    what_changed_now: str
    what_changed_delta: str
    why_now: str
    implications: str
    counterpoints: str
    key_uncertainties: str
    framework_tags: list[str]
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def validate(self) -> list[str]:
        issues: list[str] = []
        if not self.why_it_matters.strip():
            issues.append("missing why_it_matters")
        if not self.what_changed_before.strip():
            issues.append("missing what_changed_before")
        if not self.what_changed_now.strip():
            issues.append("missing what_changed_now")
        if not self.what_changed_delta.strip():
            issues.append("missing what_changed_delta")
        if not has_non_empty_framework_tags(self.framework_tags):
            issues.append("missing framework_tags")
        if self.interpretation_type is None:
            issues.append("missing interpretation_type")

        if issues and self.status != "draft":
            issues.append("invalid status for incomplete meaning card")
        if not issues and self.status == "draft":
            issues.append("draft status used for complete meaning card")
        return issues


@dataclass(slots=True)
class RawDocument:
    raw_id: str
    source_id: str
    url: str
    title: str
    content: str
    published_at: datetime
    fetched_at: datetime
    hash_sha256: str
    metadata_json: str
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class CanonicalDocument:
    canonical_id: str
    raw_id: str
    event_id: str | None
    normalized_title: str
    summary: str
    key_points: list[str]
    entities: list[str]
    canonical_version: int
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class SignalInput:
    source_id: str
    url: str
    title: str
    content: str
    published_at: str
    tags: list[str]
    lab_hint: str
    event_hint: str | None = None
