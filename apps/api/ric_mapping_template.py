from __future__ import annotations

import json
import random
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Protocol


class MappingStatus(str, Enum):
    CONFIRMED = "CONFIRMED"
    AMBIGUOUS = "AMBIGUOUS"
    FAILED = "FAILED"


class RetryableMappingError(RuntimeError):
    """Raised by providers when the request can be safely retried."""


class NonRetryableMappingError(RuntimeError):
    """Raised by providers when retrying will not help."""


@dataclass(slots=True)
class AssetMappingRequest:
    identifier_type: str
    identifier_value: str
    expected_currency: str | None = None
    expected_asset_type: str | None = None
    expected_country: str | None = None
    preferred_exchanges: tuple[str, ...] = ()
    strict_identifier_match: bool = True


@dataclass(slots=True)
class RicCandidate:
    ric: str
    isin: str | None = None
    cusip: str | None = None
    sedol: str | None = None
    ticker: str | None = None
    exchange: str | None = None
    currency: str | None = None
    asset_type: str | None = None
    country: str | None = None
    active: bool | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ValidationOutcome:
    passed: bool
    hard_failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ScoreOutcome:
    total: float
    reasons: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ScoredCandidate:
    candidate: RicCandidate
    validation: ValidationOutcome
    score: ScoreOutcome


@dataclass(slots=True)
class MappingDecision:
    status: MappingStatus
    selected_ric: str | None
    selected_score: float | None
    confidence: float
    reason: str
    attempts: int
    candidate_count: int
    validated_candidate_count: int


@dataclass(slots=True)
class RetryPolicy:
    max_attempts: int = 3
    base_delay_seconds: float = 0.2
    max_delay_seconds: float = 2.0
    jitter_ratio: float = 0.2

    def compute_sleep_seconds(self, attempt: int) -> float:
        exp_delay = min(self.max_delay_seconds, self.base_delay_seconds * (2 ** (attempt - 1)))
        low = max(0.0, 1.0 - self.jitter_ratio)
        high = 1.0 + self.jitter_ratio
        return exp_delay * random.uniform(low, high)


class RicSymbologyProvider(Protocol):
    def search_candidates(self, request: AssetMappingRequest) -> list[RicCandidate]:
        """Return candidate RICs for an input identifier."""

    def fetch_ric_profile(self, ric: str) -> RicCandidate | None:
        """Round-trip lookup for validation. Return None if unavailable."""


class CandidateValidator:
    def validate(
        self,
        request: AssetMappingRequest,
        candidate: RicCandidate,
        ric_profile: RicCandidate | None,
    ) -> ValidationOutcome:
        failures: list[str] = []
        warnings: list[str] = []

        if not candidate.ric.strip():
            failures.append("empty_ric")

        identifier_attr = request.identifier_type.lower()
        expected_identifier = _normalize_identifier(request.identifier_value)
        candidate_identifier = _normalize_identifier(getattr(candidate, identifier_attr, None))

        if candidate_identifier is None:
            message = f"candidate_missing_{identifier_attr}"
            if request.strict_identifier_match:
                failures.append(message)
            else:
                warnings.append(message)
        elif candidate_identifier != expected_identifier:
            failures.append(
                f"candidate_identifier_mismatch:{candidate_identifier}!={expected_identifier}"
            )

        self._validate_optional_field(
            failures,
            warnings,
            expected=request.expected_currency,
            actual=candidate.currency,
            name="currency",
        )
        self._validate_optional_field(
            failures,
            warnings,
            expected=request.expected_asset_type,
            actual=candidate.asset_type,
            name="asset_type",
        )
        self._validate_optional_field(
            failures,
            warnings,
            expected=request.expected_country,
            actual=candidate.country,
            name="country",
        )

        if request.preferred_exchanges:
            preferred = {_norm_text(x) for x in request.preferred_exchanges}
            exchange = _norm_text(candidate.exchange)
            if exchange and exchange not in preferred:
                warnings.append("exchange_not_preferred")

        if ric_profile is not None:
            profile_identifier = _normalize_identifier(getattr(ric_profile, identifier_attr, None))
            if profile_identifier and profile_identifier != expected_identifier:
                failures.append(
                    f"roundtrip_identifier_mismatch:{profile_identifier}!={expected_identifier}"
                )

        return ValidationOutcome(passed=len(failures) == 0, hard_failures=failures, warnings=warnings)

    @staticmethod
    def _validate_optional_field(
        failures: list[str],
        warnings: list[str],
        *,
        expected: str | None,
        actual: str | None,
        name: str,
    ) -> None:
        normalized_expected = _norm_text(expected)
        if normalized_expected is None:
            return
        normalized_actual = _norm_text(actual)
        if normalized_actual is None:
            warnings.append(f"candidate_missing_{name}")
            return
        if normalized_actual != normalized_expected:
            failures.append(f"{name}_mismatch:{normalized_actual}!={normalized_expected}")


class CandidateScorer:
    def score(self, request: AssetMappingRequest, candidate: RicCandidate) -> ScoreOutcome:
        score = 0.0
        reasons: list[str] = []

        identifier_attr = request.identifier_type.lower()
        expected_identifier = _normalize_identifier(request.identifier_value)
        candidate_identifier = _normalize_identifier(getattr(candidate, identifier_attr, None))

        if candidate_identifier == expected_identifier:
            score += 100
            reasons.append("identifier_exact:+100")
        elif candidate_identifier is None:
            score -= 40
            reasons.append("identifier_missing:-40")
        else:
            score -= 90
            reasons.append("identifier_mismatch:-90")

        score += _score_field_match(
            expected=request.expected_currency,
            actual=candidate.currency,
            field_name="currency",
            match_reward=20,
            mismatch_penalty=20,
            reasons=reasons,
        )
        score += _score_field_match(
            expected=request.expected_asset_type,
            actual=candidate.asset_type,
            field_name="asset_type",
            match_reward=15,
            mismatch_penalty=15,
            reasons=reasons,
        )
        score += _score_field_match(
            expected=request.expected_country,
            actual=candidate.country,
            field_name="country",
            match_reward=10,
            mismatch_penalty=10,
            reasons=reasons,
        )

        preferred = {_norm_text(x) for x in request.preferred_exchanges}
        exchange = _norm_text(candidate.exchange)
        if preferred:
            if exchange in preferred:
                score += 25
                reasons.append("exchange_preferred:+25")
            elif exchange is not None:
                score -= 5
                reasons.append("exchange_not_preferred:-5")

        if candidate.active is True:
            score += 5
            reasons.append("active:+5")
        elif candidate.active is False:
            score -= 15
            reasons.append("inactive:-15")

        if bool(candidate.metadata.get("primary_quote")):
            score += 8
            reasons.append("primary_quote:+8")

        return ScoreOutcome(total=score, reasons=reasons)


class RicMappingRepository:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ric_mapping_results (
                    mapping_id TEXT PRIMARY KEY,
                    identifier_type TEXT NOT NULL,
                    identifier_value TEXT NOT NULL,
                    status TEXT NOT NULL,
                    selected_ric TEXT,
                    selected_score REAL,
                    confidence REAL NOT NULL,
                    reason TEXT NOT NULL,
                    attempt_count INTEGER NOT NULL,
                    candidate_count INTEGER NOT NULL,
                    validated_candidate_count INTEGER NOT NULL,
                    error_code TEXT,
                    error_message TEXT,
                    top_candidates_json TEXT NOT NULL,
                    request_payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def save(
        self,
        *,
        request: AssetMappingRequest,
        decision: MappingDecision,
        scored_candidates: list[ScoredCandidate],
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> str:
        mapping_id = f"map_{uuid.uuid4().hex[:10]}"
        now = datetime.now(UTC).isoformat()
        top_candidates = [self._candidate_row(c) for c in scored_candidates[:5]]
        request_payload = {
            "identifier_type": request.identifier_type,
            "identifier_value": request.identifier_value,
            "expected_currency": request.expected_currency,
            "expected_asset_type": request.expected_asset_type,
            "expected_country": request.expected_country,
            "preferred_exchanges": list(request.preferred_exchanges),
            "strict_identifier_match": request.strict_identifier_match,
        }

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO ric_mapping_results (
                    mapping_id, identifier_type, identifier_value, status, selected_ric,
                    selected_score, confidence, reason, attempt_count, candidate_count,
                    validated_candidate_count, error_code, error_message, top_candidates_json,
                    request_payload_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    mapping_id,
                    request.identifier_type,
                    request.identifier_value,
                    decision.status.value,
                    decision.selected_ric,
                    decision.selected_score,
                    decision.confidence,
                    decision.reason,
                    decision.attempts,
                    decision.candidate_count,
                    decision.validated_candidate_count,
                    error_code,
                    error_message,
                    json.dumps(top_candidates),
                    json.dumps(request_payload),
                    now,
                ),
            )
            conn.commit()
        return mapping_id

    def latest(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM ric_mapping_results
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def _candidate_row(scored: ScoredCandidate) -> dict[str, Any]:
        return {
            "ric": scored.candidate.ric,
            "score": scored.score.total,
            "passed": scored.validation.passed,
            "hard_failures": scored.validation.hard_failures,
            "warnings": scored.validation.warnings,
            "reasons": scored.score.reasons,
            "exchange": scored.candidate.exchange,
            "currency": scored.candidate.currency,
            "asset_type": scored.candidate.asset_type,
            "country": scored.candidate.country,
        }


class RicMapper:
    def __init__(
        self,
        *,
        provider: RicSymbologyProvider,
        repository: RicMappingRepository,
        retry_policy: RetryPolicy | None = None,
        validator: CandidateValidator | None = None,
        scorer: CandidateScorer | None = None,
        ambiguity_gap: float = 8.0,
        sleep_fn: Any = time.sleep,
    ) -> None:
        self.provider = provider
        self.repository = repository
        self.retry_policy = retry_policy or RetryPolicy()
        self.validator = validator or CandidateValidator()
        self.scorer = scorer or CandidateScorer()
        self.ambiguity_gap = ambiguity_gap
        self.sleep_fn = sleep_fn

    def map(self, request: AssetMappingRequest) -> MappingDecision:
        candidates, attempts, error = self._search_with_retry(request)
        if error is not None:
            decision = MappingDecision(
                status=MappingStatus.FAILED,
                selected_ric=None,
                selected_score=None,
                confidence=0.0,
                reason="provider_error",
                attempts=attempts,
                candidate_count=0,
                validated_candidate_count=0,
            )
            self.repository.save(
                request=request,
                decision=decision,
                scored_candidates=[],
                error_code=error.__class__.__name__,
                error_message=str(error),
            )
            return decision

        scored_candidates = self._score_and_validate(request, candidates)
        decision = self._decide(attempts, scored_candidates)
        self.repository.save(request=request, decision=decision, scored_candidates=scored_candidates)
        return decision

    def _search_with_retry(
        self,
        request: AssetMappingRequest,
    ) -> tuple[list[RicCandidate], int, Exception | None]:
        attempts = 0
        while attempts < self.retry_policy.max_attempts:
            attempts += 1
            try:
                return self.provider.search_candidates(request), attempts, None
            except Exception as exc:
                if not self._is_retryable(exc) or attempts >= self.retry_policy.max_attempts:
                    return [], attempts, exc
                self.sleep_fn(self.retry_policy.compute_sleep_seconds(attempts))

        return [], attempts, RuntimeError("unexpected_retry_exit")

    @staticmethod
    def _is_retryable(exc: Exception) -> bool:
        return isinstance(exc, (TimeoutError, ConnectionError, RetryableMappingError))

    def _score_and_validate(
        self,
        request: AssetMappingRequest,
        candidates: list[RicCandidate],
    ) -> list[ScoredCandidate]:
        scored: list[ScoredCandidate] = []
        for candidate in candidates:
            profile = None
            try:
                profile = self.provider.fetch_ric_profile(candidate.ric)
            except Exception:
                profile = None
            validation = self.validator.validate(request, candidate, profile)
            score = self.scorer.score(request, candidate)
            scored.append(
                ScoredCandidate(
                    candidate=candidate,
                    validation=validation,
                    score=score,
                )
            )

        scored.sort(key=lambda item: item.score.total, reverse=True)
        return scored

    def _decide(self, attempts: int, scored_candidates: list[ScoredCandidate]) -> MappingDecision:
        candidate_count = len(scored_candidates)
        validated = [item for item in scored_candidates if item.validation.passed]
        validated.sort(key=lambda item: item.score.total, reverse=True)

        if not scored_candidates:
            return MappingDecision(
                status=MappingStatus.FAILED,
                selected_ric=None,
                selected_score=None,
                confidence=0.0,
                reason="no_candidates",
                attempts=attempts,
                candidate_count=0,
                validated_candidate_count=0,
            )

        if not validated:
            return MappingDecision(
                status=MappingStatus.FAILED,
                selected_ric=None,
                selected_score=None,
                confidence=0.0,
                reason="all_candidates_failed_validation",
                attempts=attempts,
                candidate_count=candidate_count,
                validated_candidate_count=0,
            )

        top = validated[0]
        second = validated[1] if len(validated) > 1 else None

        if second is not None and (top.score.total - second.score.total) <= self.ambiguity_gap:
            return MappingDecision(
                status=MappingStatus.AMBIGUOUS,
                selected_ric=top.candidate.ric,
                selected_score=top.score.total,
                confidence=_score_to_confidence(top.score.total),
                reason="top_scores_too_close",
                attempts=attempts,
                candidate_count=candidate_count,
                validated_candidate_count=len(validated),
            )

        return MappingDecision(
            status=MappingStatus.CONFIRMED,
            selected_ric=top.candidate.ric,
            selected_score=top.score.total,
            confidence=_score_to_confidence(top.score.total),
            reason="single_best_candidate",
            attempts=attempts,
            candidate_count=candidate_count,
            validated_candidate_count=len(validated),
        )


class InMemoryDemoProvider:
    """Demo provider used for local testing. Replace with real LSEG calls in production."""

    def __init__(
        self,
        *,
        search_map: dict[tuple[str, str], list[RicCandidate]],
        ric_profiles: dict[str, RicCandidate] | None = None,
        transient_failures: int = 0,
    ) -> None:
        self.search_map = search_map
        self.ric_profiles = ric_profiles or {}
        self.transient_failures = transient_failures

    def search_candidates(self, request: AssetMappingRequest) -> list[RicCandidate]:
        if self.transient_failures > 0:
            self.transient_failures -= 1
            raise RetryableMappingError("temporary upstream timeout")

        key = (request.identifier_type.upper(), _normalize_identifier(request.identifier_value))
        return list(self.search_map.get(key, []))

    def fetch_ric_profile(self, ric: str) -> RicCandidate | None:
        return self.ric_profiles.get(ric)


# Example integration shape for real LSEG provider:
# 1) Use lseg.data.content.symbol_conversion for identifier -> candidate RIC list.
# 2) Use ld.get_data(universe=[ric], fields=["TR.ISIN", "CF_CURR", "TR.AssetCategory", ...])
#    to build round-trip profiles consumed by CandidateValidator.


def _norm_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip().upper()
    return text or None


def _normalize_identifier(value: str | None) -> str | None:
    normalized = _norm_text(value)
    if normalized is None:
        return None
    return normalized.replace(" ", "")


def _score_field_match(
    *,
    expected: str | None,
    actual: str | None,
    field_name: str,
    match_reward: float,
    mismatch_penalty: float,
    reasons: list[str],
) -> float:
    normalized_expected = _norm_text(expected)
    if normalized_expected is None:
        return 0.0

    normalized_actual = _norm_text(actual)
    if normalized_actual is None:
        reasons.append(f"{field_name}_missing:0")
        return 0.0

    if normalized_actual == normalized_expected:
        reasons.append(f"{field_name}_match:+{int(match_reward)}")
        return match_reward

    reasons.append(f"{field_name}_mismatch:-{int(mismatch_penalty)}")
    return -mismatch_penalty


def _score_to_confidence(score: float) -> float:
    # Map score range roughly [-100, 170+] into [0, 1].
    confidence = (score + 100.0) / 270.0
    return max(0.0, min(1.0, round(confidence, 4)))
