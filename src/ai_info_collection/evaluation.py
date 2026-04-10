from __future__ import annotations

import hashlib
import json
import random
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from ai_info_collection.pipeline import run_pipeline
from ai_info_collection.storage import SQLiteStore


@dataclass(slots=True)
class MergeEvalResult:
    eval_id: str
    rows_total: int
    event_groups_truth: int
    false_merge_rate: float
    miss_merge_rate: float


def _new_eval_id(dataset_path: str) -> str:
    now = datetime.now(UTC)
    seed = f"{now.isoformat()}|{dataset_path}".encode("utf-8")
    return f"eval-{now.strftime('%Y%m%d%H%M%S')}-{hashlib.sha256(seed).hexdigest()[:8]}"


def generate_replay_dataset(output_path: str | Path, rows: int = 1000, seed: int = 42) -> int:
    rng = random.Random(seed)
    labs = ["OpenAI", "Anthropic", "Google", "Meta"]
    topics = ["agent", "safety", "policy", "release", "research", "api"]
    groups = max(1, rows // 5)
    lines: list[str] = []

    for idx in range(rows):
        group_id = idx % groups
        lab = labs[group_id % len(labs)]
        topic = topics[group_id % len(topics)]
        variation = idx // groups
        item = {
            "source_id": f"{lab.lower()}-news",
            "url": f"https://example.com/{lab.lower()}/{group_id}/{variation}",
            "title": f"{lab} {topic} update {group_id}",
            "content": f"{lab} announced {topic} update for cluster {group_id}. variant {variation}.",
            "published_at": f"2026-04-{(group_id % 27) + 1:02d}T00:00:00+00:00",
            "tags": [topic, "benchmark"],
            "lab_hint": lab,
            "expected_event_key": f"cluster-{group_id}",
        }
        # inject a small controllable noise rate for realism
        if rng.random() < 0.03:
            item["title"] = item["title"] + " special"
        lines.append(json.dumps(item, ensure_ascii=False))

    path = Path(output_path)
    path.write_text("\n".join(lines), encoding="utf-8")
    return rows


def evaluate_merge(
    store: SQLiteStore,
    input_path: str | Path,
    dry_run: bool = False,
) -> MergeEvalResult:
    started = datetime.now(UTC)
    eval_id = _new_eval_id(str(input_path))
    pipeline_result = None

    with tempfile.TemporaryDirectory() as temp_dir:
        isolated_db = Path(temp_dir) / "eval.db"
        eval_store = SQLiteStore(isolated_db)
        eval_store.initialize()
        pipeline_result = run_pipeline(
            store=eval_store,
            input_path=str(input_path),
            merge_limit=10000,
            dry_run=dry_run,
        )
        if pipeline_result.exit_code != 0:
            raise RuntimeError(
                f"pipeline execution failed during evaluate-merge: "
                f"status={pipeline_result.status}, reason={pipeline_result.status_reason}"
            )

        with eval_store.connect() as conn:
            rows = conn.execute(
                """
                SELECT c.canonical_id, c.event_id, r.metadata_json
                FROM canonical_documents c
                JOIN raw_documents r ON r.raw_id = c.raw_id
                """
            ).fetchall()

    total = len(rows)
    if total == 0:
        result = MergeEvalResult(
            eval_id=eval_id,
            rows_total=0,
            event_groups_truth=0,
            false_merge_rate=0.0,
            miss_merge_rate=0.0,
        )
        store.insert_merge_eval_run(
            eval_id=eval_id,
            started_at=started,
            finished_at=datetime.now(UTC),
            dataset_path=str(input_path),
            rows_total=0,
            event_groups_truth=0,
            false_merge_rate=0.0,
            miss_merge_rate=0.0,
            notes_json=json.dumps({"dry_run": dry_run}, ensure_ascii=False),
        )
        return result

    truth_by_sample: dict[str, str] = {}
    pred_by_sample: dict[str, str] = {}
    for row in rows:
        cid = row["canonical_id"]
        predicted = row["event_id"] if row["event_id"] else f"UNMERGED::{cid}"
        meta = json.loads(row["metadata_json"]) if row["metadata_json"] else {}
        truth = meta.get("expected_event_key") if isinstance(meta, dict) else None
        if not isinstance(truth, str) or not truth:
            truth = f"UNKNOWN::{cid}"
        truth_by_sample[cid] = truth
        pred_by_sample[cid] = predicted

    pred_groups: dict[str, list[str]] = {}
    truth_groups: dict[str, list[str]] = {}
    for sid, pred in pred_by_sample.items():
        pred_groups.setdefault(pred, []).append(sid)
    for sid, truth in truth_by_sample.items():
        truth_groups.setdefault(truth, []).append(sid)

    false_merge_samples = 0
    for sample_ids in pred_groups.values():
        truths = {truth_by_sample[sid] for sid in sample_ids}
        if len(truths) > 1:
            false_merge_samples += len(sample_ids)

    miss_merge_samples = 0
    for sample_ids in truth_groups.values():
        preds = [pred_by_sample[sid] for sid in sample_ids]
        if len(set(preds)) <= 1:
            continue
        freq: dict[str, int] = {}
        for pred in preds:
            freq[pred] = freq.get(pred, 0) + 1
        majority = max(freq.values())
        miss_merge_samples += len(sample_ids) - majority

    false_merge_rate = false_merge_samples / total
    miss_merge_rate = miss_merge_samples / total

    store.insert_merge_eval_run(
        eval_id=eval_id,
        started_at=started,
        finished_at=datetime.now(UTC),
        dataset_path=str(input_path),
        rows_total=total,
        event_groups_truth=len(truth_groups),
        false_merge_rate=false_merge_rate,
        miss_merge_rate=miss_merge_rate,
        notes_json=json.dumps({"dry_run": dry_run}, ensure_ascii=False),
    )

    return MergeEvalResult(
        eval_id=eval_id,
        rows_total=total,
        event_groups_truth=len(truth_groups),
        false_merge_rate=false_merge_rate,
        miss_merge_rate=miss_merge_rate,
    )
