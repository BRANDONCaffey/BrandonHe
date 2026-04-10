from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path

from ai_info_collection.evaluation import evaluate_merge, generate_replay_dataset
from ai_info_collection.fetch import fetch_sources, seed_sources
from ai_info_collection.ingest import ingest_signals
from ai_info_collection.merge import merge_events
from ai_info_collection.pipeline import PipelineRunResult, run_pipeline
from ai_info_collection.storage import SQLiteStore
from ai_info_collection.ui import start_ui


def _format_rows(rows: list[dict] | list[object], columns: list[str]) -> str:
    if not rows:
        return "(empty)"
    dict_rows = [{col: str(row[col] if row[col] is not None else "") for col in columns} for row in rows]
    widths = {
        col: max(len(col), *(len(row[col]) for row in dict_rows))
        for col in columns
    }
    header = " | ".join(col.ljust(widths[col]) for col in columns)
    divider = "-+-".join("-" * widths[col] for col in columns)
    body = [
        " | ".join(row[col].ljust(widths[col]) for col in columns)
        for row in dict_rows
    ]
    return "\n".join([header, divider, *body])


def cmd_review(store: SQLiteStore) -> int:
    missing_what_changed = store.list_meaning_cards_missing_what_changed()
    missing_interpretation = store.list_meaning_cards_missing_interpretation_type()
    missing_why_it_matters = store.list_meaning_cards_missing_why_it_matters()
    missing_framework_tags = store.list_meaning_cards_missing_framework_tags()
    print("== MeaningCards missing what_changed ==")
    print(_format_rows(missing_what_changed, ["id", "event_id", "status", "review_notes", "updated_at"]))
    print()
    print("== MeaningCards missing interpretation_type ==")
    print(_format_rows(missing_interpretation, ["id", "event_id", "status", "review_notes", "updated_at"]))
    print()
    print("== MeaningCards missing why_it_matters ==")
    print(_format_rows(missing_why_it_matters, ["id", "event_id", "status", "review_notes", "updated_at"]))
    print()
    print("== MeaningCards missing framework_tags ==")
    print(_format_rows(missing_framework_tags, ["id", "event_id", "status", "review_notes", "updated_at"]))
    return 0


def cmd_source_health(store: SQLiteStore) -> int:
    rows = store.list_source_health()
    print(
        _format_rows(
            rows,
            [
                "source_id",
                "layer",
                "lab",
                "source_name",
                "governance_status",
                "trust_level",
                "last_success_at",
                "last_failure_at",
                "failure_count",
                "quality_score",
            ],
        )
    )
    return 0


def cmd_recent_events(store: SQLiteStore, limit: int) -> int:
    rows = store.list_recent_events(limit=limit)
    print(_format_rows(rows, ["event_id", "title", "related_lab", "status", "updated_at"]))
    return 0


def cmd_recent_raw(store: SQLiteStore, limit: int) -> int:
    rows = store.list_recent_raw_documents(limit=limit)
    print(_format_rows(rows, ["raw_id", "source_id", "title", "published_at", "updated_at"]))
    return 0


def cmd_recent_canonical(store: SQLiteStore, limit: int) -> int:
    rows = store.list_recent_canonical_documents(limit=limit)
    print(_format_rows(rows, ["canonical_id", "raw_id", "event_id", "normalized_title", "updated_at"]))
    return 0


def cmd_ingest_signals(store: SQLiteStore, input_path: str, dry_run: bool) -> int:
    stats, errors = ingest_signals(store=store, input_path=input_path, dry_run=dry_run)
    print("== Ingest Signals ==")
    print(f"dry_run={dry_run}")
    print(f"total={stats.total}")
    print(f"success={stats.success}")
    print(f"skipped_duplicates={stats.skipped_duplicates}")
    print(f"failed={stats.failed}")
    if errors:
        print("errors:")
        for err in errors:
            print(f"- line={err.line_no}: {err.error_message}")
    return 0 if stats.success > 0 else 1


def cmd_merge_events(store: SQLiteStore, limit: int, dry_run: bool) -> int:
    stats = merge_events(store=store, limit=limit, dry_run=dry_run)
    print("== Merge Events ==")
    print(f"dry_run={dry_run}")
    print(f"processed={stats.processed}")
    print(f"matched_by_hint={stats.matched_by_hint}")
    print(f"matched_by_rule={stats.matched_by_rule}")
    print(f"created_new={stats.created_new}")
    return 0


def cmd_run_pipeline(
    store: SQLiteStore,
    input_path: str,
    merge_limit: int,
    dry_run: bool,
    source_limit: int,
    source_id: str | None,
    fetch_dry_run: bool,
) -> int:
    result = run_pipeline(
        store=store,
        input_path=input_path if input_path else None,
        merge_limit=merge_limit,
        dry_run=dry_run,
        source_limit=source_limit,
        source_id=source_id,
        fetch_dry_run=fetch_dry_run,
    )
    _print_pipeline_summary("Run Pipeline", result, dry_run=dry_run, fetch_dry_run=fetch_dry_run)
    return result.exit_code


def _print_pipeline_summary(title: str, result: PipelineRunResult, dry_run: bool, fetch_dry_run: bool) -> None:
    print(f"== {title} ==")
    print(f"run_id={result.run_id}")
    print(f"status={result.status}")
    print(f"status_reason={result.status_reason}")
    print(f"dry_run={dry_run}")
    print(f"fetch_dry_run={fetch_dry_run}")
    print(f"fetch_total={result.fetch_stats.total_sources}")
    print(f"fetch_success={result.fetch_stats.success_sources}")
    print(f"fetch_failed={result.fetch_stats.failed_sources}")
    print(f"ingest_total={result.ingest_stats.total}")
    print(f"ingest_success={result.ingest_stats.success}")
    print(f"ingest_failed={result.ingest_stats.failed}")
    print(f"ingest_skipped_duplicates={result.ingest_stats.skipped_duplicates}")
    print(f"merge_processed={result.merge_stats.processed}")
    print(f"merge_matched_by_hint={result.merge_stats.matched_by_hint}")
    print(f"merge_matched_by_rule={result.merge_stats.matched_by_rule}")
    print(f"merge_created_new={result.merge_stats.created_new}")
    print(f"error_count={result.error_count}")
    if result.status_reason in {"concurrent_run_blocked", "duplicate_run_blocked"}:
        print(f"blocked_by={result.status_reason}")


def _resolve_start_mode(mode: str | None) -> str:
    if mode in {"offline", "online"}:
        return mode
    print("Choose startup mode:")
    print("1) offline  (use sample.jsonl)")
    print("2) online   (seed official sources then fetch)")
    try:
        answer = input("Select mode [1/2, default 1]: ").strip().lower()
    except EOFError:
        answer = ""
    mapping = {
        "1": "offline",
        "offline": "offline",
        "2": "online",
        "online": "online",
    }
    resolved = mapping.get(answer, "offline")
    if answer and answer not in mapping:
        print("Invalid choice, fallback to offline.")
    return resolved


def cmd_start(
    store: SQLiteStore,
    mode: str | None,
    source_limit: int,
    merge_limit: int,
    dry_run: bool,
    fetch_log_limit: int,
    force_new_db: bool,
) -> int:
    resolved_mode = _resolve_start_mode(mode)
    run_store = store
    if resolved_mode == "online":
        if force_new_db:
            print("force_new_db_ignored=True (online mode)")
        seeded = seed_sources(store=store, preset="official-ai")
        print(f"seeded_sources={seeded}")
        result = run_pipeline(
            store=run_store,
            input_path=None,
            merge_limit=merge_limit,
            dry_run=dry_run,
            source_limit=source_limit,
            source_id=None,
            fetch_dry_run=False,
        )
    else:
        if force_new_db:
            base = Path(store.db_path)
            timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
            suffix = "".join(base.suffixes) or ".db"
            stem = base.name[:-len(suffix)] if base.name.endswith(suffix) else base.stem
            fresh_name = f"{stem}.offline.{timestamp}{suffix}"
            fresh_path = base.with_name(fresh_name)
            run_store = SQLiteStore(fresh_path)
            run_store.initialize()
            print(f"using_new_db={run_store.db_path}")
        input_path = Path("sample.jsonl")
        if not input_path.exists():
            print("sample.jsonl not found in repository root.")
            return 1
        result = run_pipeline(
            store=run_store,
            input_path=str(input_path),
            merge_limit=merge_limit,
            dry_run=dry_run,
            source_limit=source_limit,
            source_id=None,
            fetch_dry_run=False,
        )

    _print_pipeline_summary("Start", result, dry_run=dry_run, fetch_dry_run=False)
    print()
    print("== Recent Fetch Logs ==")
    rows = run_store.list_recent_fetch_runs(limit=fetch_log_limit)
    print(_format_rows(rows, ["run_id", "source_id", "fetched", "parsed", "failed", "status", "finished_at"]))
    return result.exit_code


def cmd_fetch_sources(store: SQLiteStore, source_limit: int, source_id: str | None, dry_run: bool) -> int:
    _, stats = fetch_sources(
        store=store,
        limit=source_limit,
        source_id=source_id,
        dry_run=dry_run,
    )
    print("== Fetch Sources ==")
    print(f"dry_run={dry_run}")
    print(f"source_limit={source_limit}")
    print(f"source_id={source_id}")
    print(f"total_sources={stats.total_sources}")
    print(f"success_sources={stats.success_sources}")
    print(f"failed_sources={stats.failed_sources}")
    print(f"fetched_items={stats.fetched_items}")
    print(f"parsed_items={stats.parsed_items}")
    return 0 if stats.parsed_items > 0 else 1


def cmd_seed_sources(store: SQLiteStore, preset: str) -> int:
    seeded = seed_sources(store=store, preset=preset)
    print("== Seed Sources ==")
    print(f"preset={preset}")
    print(f"seeded={seeded}")
    return 0


def cmd_recent_fetch_runs(store: SQLiteStore, limit: int) -> int:
    rows = store.list_recent_fetch_runs(limit=limit)
    print(
        _format_rows(
            rows,
            ["run_id", "source_id", "fetched", "parsed", "failed", "status", "finished_at"],
        )
    )
    return 0


def cmd_generate_replay_dataset(output_path: str, rows: int, seed: int) -> int:
    generated = generate_replay_dataset(output_path=output_path, rows=rows, seed=seed)
    print("== Generate Replay Dataset ==")
    print(f"output={output_path}")
    print(f"rows={generated}")
    print(f"seed={seed}")
    return 0


def cmd_evaluate_merge(store: SQLiteStore, input_path: str, dry_run: bool) -> int:
    try:
        result = evaluate_merge(store=store, input_path=input_path, dry_run=dry_run)
    except Exception as exc:
        print("== Evaluate Merge ==")
        print(f"dataset={input_path}")
        print(f"error={exc}")
        print(f"dry_run={dry_run}")
        return 1
    print("== Evaluate Merge ==")
    print(f"eval_id={result.eval_id}")
    print(f"dataset={input_path}")
    print(f"rows_total={result.rows_total}")
    print(f"event_groups_truth={result.event_groups_truth}")
    print(f"false_merge_rate={result.false_merge_rate:.6f}")
    print(f"miss_merge_rate={result.miss_merge_rate:.6f}")
    print(f"dry_run={dry_run}")
    return 0


def cmd_ui(store: SQLiteStore, host: str, port: int, offline: bool) -> int:
    start_ui(store=store, host=host, port=port, offline_mode=offline)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AI info collection CLI")
    parser.add_argument("--db-path", default="data.db", help="SQLite database path")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("review", help="Show MeaningCard completeness issues")
    subparsers.add_parser("source-health", help="Show source governance and health")

    recent_events = subparsers.add_parser("recent-events", help="Show recently updated events")
    recent_events.add_argument("--limit", type=int, default=10)

    recent_raw = subparsers.add_parser("recent-raw", help="Show recently ingested raw documents")
    recent_raw.add_argument("--limit", type=int, default=10)

    recent_canonical = subparsers.add_parser("recent-canonical", help="Show recently canonicalized documents")
    recent_canonical.add_argument("--limit", type=int, default=10)

    ingest_cmd = subparsers.add_parser("ingest-signals", help="Ingest SignalInput JSONL into raw/canonical tables")
    ingest_cmd.add_argument("--input", required=True, help="Path to JSONL file")
    ingest_cmd.add_argument("--dry-run", action="store_true", help="Parse and validate only, do not write")

    merge_cmd = subparsers.add_parser("merge-events", help="Merge canonical documents into events")
    merge_cmd.add_argument("--limit", type=int, default=100)
    merge_cmd.add_argument("--dry-run", action="store_true", help="Plan merge only, do not write")

    pipeline_cmd = subparsers.add_parser("run-pipeline", help="Run fetch -> ingest -> merge pipeline and persist run")
    pipeline_cmd.add_argument("--input", required=False, default="", help="Optional JSONL path for offline replay")
    pipeline_cmd.add_argument("--merge-limit", type=int, default=100)
    pipeline_cmd.add_argument("--dry-run", action="store_true", help="Execute pipeline in dry-run mode")
    pipeline_cmd.add_argument("--source-limit", type=int, default=20)
    pipeline_cmd.add_argument("--source-id", help="Run pipeline for a single source_id")
    pipeline_cmd.add_argument("--fetch-dry-run", action="store_true", help="Fetch/parse only; do not write business tables")

    fetch_cmd = subparsers.add_parser("fetch-sources", help="Fetch enabled sources and parse into signal items")
    fetch_cmd.add_argument("--source-limit", type=int, default=20)
    fetch_cmd.add_argument("--source-id", help="Fetch a single source_id")
    fetch_cmd.add_argument("--dry-run", action="store_true")

    seed_cmd = subparsers.add_parser("seed-sources", help="Seed built-in source presets")
    seed_cmd.add_argument("--preset", default="official-ai")

    recent_fetch = subparsers.add_parser("recent-fetch-runs", help="Show recent fetch run history")
    recent_fetch.add_argument("--limit", type=int, default=10)

    start_cmd = subparsers.add_parser("start", help="One-command startup for offline/online main flow")
    start_cmd.add_argument("--mode", choices=["offline", "online"], help="Startup mode; prompt once if omitted")
    start_cmd.add_argument("--source-limit", type=int, default=5, help="Source limit for online mode")
    start_cmd.add_argument("--merge-limit", type=int, default=100)
    start_cmd.add_argument("--dry-run", action="store_true")
    start_cmd.add_argument("--fetch-log-limit", type=int, default=10)
    start_cmd.add_argument(
        "--force-new-db",
        action="store_true",
        help="Offline mode only: use a fresh timestamped database file to avoid stale run locks",
    )

    replay_cmd = subparsers.add_parser("generate-replay-dataset", help="Generate synthetic replay dataset with labels")
    replay_cmd.add_argument("--output", required=True, help="Output JSONL path")
    replay_cmd.add_argument("--rows", type=int, default=1000)
    replay_cmd.add_argument("--seed", type=int, default=42)

    eval_cmd = subparsers.add_parser("evaluate-merge", help="Replay dataset and compute false/miss merge rates")
    eval_cmd.add_argument("--input", required=True, help="Replay JSONL path")
    eval_cmd.add_argument("--dry-run", action="store_true", help="Evaluate under dry-run pipeline mode")

    ui_cmd = subparsers.add_parser("ui", help="Start local dashboard UI")
    ui_cmd.add_argument("--host", default="127.0.0.1")
    ui_cmd.add_argument("--port", type=int, default=8765)
    ui_cmd.add_argument("--offline", action="store_true", help="Render UI with offline-first quick start hints")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    store = SQLiteStore(Path(args.db_path))
    store.initialize()

    if args.command == "review":
        return cmd_review(store)
    if args.command == "source-health":
        return cmd_source_health(store)
    if args.command == "recent-events":
        return cmd_recent_events(store, args.limit)
    if args.command == "recent-raw":
        return cmd_recent_raw(store, args.limit)
    if args.command == "recent-canonical":
        return cmd_recent_canonical(store, args.limit)
    if args.command == "ingest-signals":
        return cmd_ingest_signals(store, args.input, args.dry_run)
    if args.command == "merge-events":
        return cmd_merge_events(store, args.limit, args.dry_run)
    if args.command == "run-pipeline":
        return cmd_run_pipeline(
            store=store,
            input_path=args.input,
            merge_limit=args.merge_limit,
            dry_run=args.dry_run,
            source_limit=args.source_limit,
            source_id=args.source_id,
            fetch_dry_run=args.fetch_dry_run,
        )
    if args.command == "fetch-sources":
        return cmd_fetch_sources(store, args.source_limit, args.source_id, args.dry_run)
    if args.command == "seed-sources":
        return cmd_seed_sources(store, args.preset)
    if args.command == "recent-fetch-runs":
        return cmd_recent_fetch_runs(store, args.limit)
    if args.command == "start":
        return cmd_start(
            store=store,
            mode=args.mode,
            source_limit=args.source_limit,
            merge_limit=args.merge_limit,
            dry_run=args.dry_run,
            fetch_log_limit=args.fetch_log_limit,
            force_new_db=args.force_new_db,
        )
    if args.command == "generate-replay-dataset":
        return cmd_generate_replay_dataset(args.output, args.rows, args.seed)
    if args.command == "evaluate-merge":
        return cmd_evaluate_merge(store, args.input, args.dry_run)
    if args.command == "ui":
        return cmd_ui(store, args.host, args.port, args.offline)

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
