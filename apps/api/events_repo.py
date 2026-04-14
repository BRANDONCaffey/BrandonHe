from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path

from himpact_core.schemas import EventCreateRequest, EventPatchRequest, EventRecord


class EventRepository:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    event_time TEXT NOT NULL,
                    category TEXT NOT NULL,
                    title TEXT NOT NULL,
                    source TEXT NOT NULL,
                    region TEXT,
                    tags TEXT NOT NULL,
                    note TEXT,
                    confirmed INTEGER NOT NULL DEFAULT 0,
                    workspace_ref TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def create(self, payload: EventCreateRequest) -> EventRecord:
        now = datetime.now(UTC)
        event_id = f"evt_{uuid.uuid4().hex[:8]}"
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO events (
                    event_id, event_time, category, title, source, region, tags,
                    note, confirmed, workspace_ref, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    payload.event_time.isoformat(),
                    payload.category,
                    payload.title,
                    payload.source,
                    payload.region,
                    json.dumps(payload.tags),
                    payload.note,
                    1 if payload.confirmed else 0,
                    payload.workspace_ref,
                    now.isoformat(),
                    now.isoformat(),
                ),
            )
            conn.commit()
        return self.get_or_raise(event_id)

    def get_or_raise(self, event_id: str) -> EventRecord:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM events WHERE event_id = ?",
                (event_id,),
            ).fetchone()
        if row is None:
            raise KeyError(event_id)
        return self._row_to_event(row)

    def patch(self, event_id: str, payload: EventPatchRequest) -> EventRecord | None:
        updates: dict[str, object] = {}
        for field_name in ("title", "source", "region", "note", "workspace_ref", "confirmed", "tags"):
            value = getattr(payload, field_name)
            if value is not None:
                if field_name == "confirmed":
                    updates[field_name] = 1 if bool(value) else 0
                elif field_name == "tags":
                    updates[field_name] = json.dumps(value)
                else:
                    updates[field_name] = value

        if not updates:
            try:
                return self.get_or_raise(event_id)
            except KeyError:
                return None

        updates["updated_at"] = datetime.now(UTC).isoformat()
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values())
        values.append(event_id)

        with self._connect() as conn:
            cursor = conn.execute(
                f"UPDATE events SET {set_clause} WHERE event_id = ?",
                values,
            )
            conn.commit()
            if cursor.rowcount == 0:
                return None
        return self.get_or_raise(event_id)

    def list(
        self,
        *,
        category: str | None,
        confirmed: bool | None,
        query: str | None,
        limit: int,
        offset: int,
        sort: str,
    ) -> tuple[list[EventRecord], int]:
        where = []
        params: list[object] = []
        if category:
            where.append("category = ?")
            params.append(category)
        if confirmed is not None:
            where.append("confirmed = ?")
            params.append(1 if confirmed else 0)
        if query:
            where.append("(title LIKE ? OR source LIKE ? OR note LIKE ? OR tags LIKE ?)")
            wildcard = f"%{query}%"
            params.extend([wildcard, wildcard, wildcard, wildcard])

        where_clause = f"WHERE {' AND '.join(where)}" if where else ""
        order_clause = "ORDER BY event_time DESC" if sort == "event_time_desc" else "ORDER BY event_time ASC"

        with self._connect() as conn:
            total_row = conn.execute(
                f"SELECT COUNT(*) AS cnt FROM events {where_clause}",
                params,
            ).fetchone()
            total = int(total_row["cnt"]) if total_row else 0
            rows = conn.execute(
                f"""
                SELECT * FROM events
                {where_clause}
                {order_clause}
                LIMIT ? OFFSET ?
                """,
                [*params, limit, offset],
            ).fetchall()

        return [self._row_to_event(row) for row in rows], total

    def last_event_update(self) -> datetime | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT updated_at FROM events ORDER BY updated_at DESC LIMIT 1"
            ).fetchone()
        if row is None:
            return None
        return datetime.fromisoformat(row["updated_at"])

    def _row_to_event(self, row: sqlite3.Row) -> EventRecord:
        return EventRecord(
            event_id=row["event_id"],
            event_time=datetime.fromisoformat(row["event_time"]),
            category=row["category"],
            title=row["title"],
            source=row["source"],
            region=row["region"],
            tags=json.loads(row["tags"]) if row["tags"] else [],
            note=row["note"],
            confirmed=bool(row["confirmed"]),
            workspace_ref=row["workspace_ref"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

