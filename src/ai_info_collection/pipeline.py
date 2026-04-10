from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from ai_info_collection.fetch import FetchStats, fetch_sources
from ai_info_collection.ingest import IngestError, IngestStats, ingest_signal_items, ingest_signals
from ai_info_collection.merge import MergeStats, merge_events
from ai_info_collection.storage import SQLiteStore


@dataclass(slots=True)
class PipelineRunResult:
    run_id: str
    status: str
    status_reason: str | None
    fetch_stats: FetchStats
    ingest_stats: IngestStats
    merge_stats: MergeStats
    error_count: int
    exit_code: int


def _new_run_id(seed_text: str) -> str:
    now = datetime.now(UTC)
    seed = f"{now.isoformat()}|{seed_text}".encode("utf-8")
    short_hash = hashlib.sha256(seed).hexdigest()[:8]
    return f"run-{now.strftime('%Y%m%d%H%M%S')}-{short_hash}"


def _run_signature(seed_text: str, dry_run: bool, merge_limit: int) -> str:
    seed = f"{seed_text}|{int(dry_run)}|{merge_limit}".encode("utf-8")
    return hashlib.sha256(seed).hexdigest()


def run_pipeline(
    store: SQLiteStore,
    input_path: str | Path | None = None,
    merge_limit: int = 100,
    dry_run: bool = False,
    source_limit: int = 20,
    source_id: str | None = None,
    fetch_dry_run: bool = False,
) -> PipelineRunResult:
    input_path_str = str(input_path) if input_path is not None else f"sources://{source_id or 'all'}?limit={source_limit}"
    started_at = datetime.now(UTC)
    run_id = _new_run_id(input_path_str)
    signature = _run_signature(seed_text=input_path_str, dry_run=dry_run or fetch_dry_run, merge_limit=merge_limit)

    reserved, blocked_reason = store.reserve_pipeline_run(
        run_id=run_id,
        started_at=started_at,
        input_path=input_path_str,
        run_signature=signature,
        dry_run=dry_run,
        merge_limit=merge_limit,
    )
    if not reserved:
        return PipelineRunResult(
            run_id=run_id,
            status="failed",
            status_reason=blocked_reason,
            fetch_stats=FetchStats(),
            ingest_stats=IngestStats(),
            merge_stats=MergeStats(),
            error_count=0,
            exit_code=1,
        )

    fetch_stats = FetchStats()
    ingest_stats = IngestStats()
    merge_stats = MergeStats()
    ingest_errors: list[IngestError] = []
    status_reason: str | None = None

    try:
        effective_dry_run = dry_run or fetch_dry_run
        if input_path is not None:
            ingest_stats, ingest_errors = ingest_signals(store=store, input_path=input_path_str, dry_run=effective_dry_run)
        else:
            signals, fetch_stats = fetch_sources(
                store=store,
                limit=source_limit,
                source_id=source_id,
                dry_run=effective_dry_run,
            )
            ingest_stats, ingest_errors = ingest_signal_items(
                store=store,
                items=signals,
                dry_run=effective_dry_run,
            )
        for err in ingest_errors:
            store.insert_pipeline_run_error(
                run_id=run_id,
                stage="ingest",
                line_no=err.line_no,
                error_message=err.error_message,
                raw_payload=err.raw_payload,
                created_at=datetime.now(UTC),
            )

        merge_stats = merge_events(store=store, limit=merge_limit, dry_run=effective_dry_run)

        if ingest_stats.success == 0:
            status = "failed"
            status_reason = "ingest_no_success"
            exit_code = 1
        elif ingest_stats.failed > 0:
            status = "partial_success"
            status_reason = "ingest_partial_failure"
            exit_code = 0
        else:
            status = "success"
            status_reason = None
            exit_code = 0

    except Exception as exc:
        status = "failed"
        status_reason = "pipeline_exception"
        exit_code = 1
        store.insert_pipeline_run_error(
            run_id=run_id,
            stage="pipeline",
            line_no=None,
            error_message=str(exc),
            raw_payload=json.dumps({"input_path": input_path_str, "dry_run": dry_run}, ensure_ascii=False),
            created_at=datetime.now(UTC),
        )

    store.update_pipeline_run_result(
        run_id=run_id,
        finished_at=datetime.now(UTC),
        ingest_total=ingest_stats.total,
        ingest_success=ingest_stats.success,
        ingest_failed=ingest_stats.failed,
        ingest_skipped_duplicates=ingest_stats.skipped_duplicates,
        merge_processed=merge_stats.processed,
        merge_matched_by_hint=merge_stats.matched_by_hint,
        merge_matched_by_rule=merge_stats.matched_by_rule,
        merge_created_new=merge_stats.created_new,
        fetch_total=fetch_stats.total_sources,
        fetch_success=fetch_stats.success_sources,
        fetch_failed=fetch_stats.failed_sources,
        status=status,
        status_reason=status_reason,
    )

    return PipelineRunResult(
        run_id=run_id,
        status=status,
        status_reason=status_reason,
        fetch_stats=fetch_stats,
        ingest_stats=ingest_stats,
        merge_stats=merge_stats,
        error_count=len(ingest_errors),
        exit_code=exit_code,
    )
