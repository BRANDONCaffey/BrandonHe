# AI Info Collection

Minimal scaffold for a three-layer AI intelligence collection project.

## Run tests

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## CLI examples

```bash
PYTHONPATH=src python3 -m ai_info_collection.cli --db-path ./data.db review
PYTHONPATH=src python3 -m ai_info_collection.cli --db-path ./data.db source-health
PYTHONPATH=src python3 -m ai_info_collection.cli --db-path ./data.db recent-events
PYTHONPATH=src python3 -m ai_info_collection.cli --db-path ./data.db recent-raw --limit 10
PYTHONPATH=src python3 -m ai_info_collection.cli --db-path ./data.db recent-canonical --limit 10
PYTHONPATH=src python3 -m ai_info_collection.cli --db-path ./data.db ingest-signals --input ./sample.jsonl --dry-run
PYTHONPATH=src python3 -m ai_info_collection.cli --db-path ./data.db merge-events --limit 100 --dry-run
PYTHONPATH=src python3 -m ai_info_collection.cli --db-path ./data.db seed-sources --preset official-ai
PYTHONPATH=src python3 -m ai_info_collection.cli --db-path ./data.db fetch-sources --source-limit 5
PYTHONPATH=src python3 -m ai_info_collection.cli --db-path ./data.db run-pipeline --source-limit 5
PYTHONPATH=src python3 -m ai_info_collection.cli --db-path ./data.db run-pipeline --source-limit 5 --fetch-dry-run
PYTHONPATH=src python3 -m ai_info_collection.cli --db-path ./data.db recent-fetch-runs --limit 10
PYTHONPATH=src python3 -m ai_info_collection.cli --db-path ./data.db generate-replay-dataset --output ./replay_1k.jsonl --rows 1000 --seed 42
PYTHONPATH=src python3 -m ai_info_collection.cli --db-path ./data.db evaluate-merge --input ./replay_1k.jsonl
PYTHONPATH=src python3 -m ai_info_collection.cli --db-path ./data.db ui --host 127.0.0.1 --port 8765 --offline
```

## Notes

- `run-pipeline` now defaults to online fetch mode from `sources` (you can still pass `--input` for offline replay).
- online fetching uses Scrapling `Fetcher` for web sources and RSS parsing for feed sources.
- `run-pipeline` includes concurrency and duplicate-run guards (same run signature within a short window is blocked).
- stale `running` records older than 30 minutes are auto-recovered as `stale_running_recovered` before a new run starts.
- Pipeline run summaries are stored in `pipeline_runs`, and ingest line errors are stored in `pipeline_run_errors`.
- source fetch run details are stored in `fetch_runs`.
- Merge evaluation summaries are stored in `merge_eval_runs` (including `rows_total`, `event_groups_truth`, `false_merge_rate`, `miss_merge_rate`).
- local dashboard UI is available at `ui` command (`/` route only, read-only overview).
- offline startup supported: use `ui --offline` to show offline-safe quick-start commands.
