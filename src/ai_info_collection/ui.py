from __future__ import annotations

import html
from dataclasses import dataclass
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Type

from ai_info_collection.storage import SQLiteStore


@dataclass(slots=True)
class DashboardData:
    sources_total: int
    events_total: int
    raw_total: int
    canonical_total: int
    latest_pipeline: dict[str, str]
    latest_fetch_runs: list[dict[str, str]]
    recent_events: list[dict[str, str]]


def _query_count(store: SQLiteStore, table: str) -> int:
    with store.connect() as conn:
        row = conn.execute(f"SELECT COUNT(*) AS c FROM {table}").fetchone()
    return int(row["c"]) if row else 0


def load_dashboard_data(store: SQLiteStore) -> DashboardData:
    sources_total = _query_count(store, "sources")
    events_total = _query_count(store, "events")
    raw_total = _query_count(store, "raw_documents")
    canonical_total = _query_count(store, "canonical_documents")

    latest_pipeline = {
        "run_id": "-",
        "status": "-",
        "status_reason": "-",
        "started_at": "-",
        "fetch_success": "0",
        "fetch_failed": "0",
        "ingest_success": "0",
        "ingest_failed": "0",
        "merge_processed": "0",
    }
    pipeline_rows = store.list_recent_pipeline_runs(limit=1)
    if pipeline_rows:
        row = pipeline_rows[0]
        latest_pipeline = {
            "run_id": str(row["run_id"]),
            "status": str(row["status"]),
            "status_reason": str(row["status_reason"] or "-"),
            "started_at": str(row["started_at"] or "-"),
            "fetch_success": str(row["fetch_success"] or 0),
            "fetch_failed": str(row["fetch_failed"] or 0),
            "ingest_success": str(row["ingest_success"] or 0),
            "ingest_failed": str(row["ingest_failed"] or 0),
            "merge_processed": str(row["merge_processed"] or 0),
        }

    latest_fetch_runs: list[dict[str, str]] = []
    for row in store.list_recent_fetch_runs(limit=5):
        latest_fetch_runs.append(
            {
                "source_id": str(row["source_id"]),
                "status": str(row["status"]),
                "parsed": str(row["parsed"]),
                "failed": str(row["failed"]),
                "finished_at": str(row["finished_at"] or "-"),
            }
        )

    recent_events: list[dict[str, str]] = []
    for row in store.list_recent_events(limit=5):
        recent_events.append(
            {
                "event_id": str(row["event_id"]),
                "title": str(row["title"]),
                "related_lab": str(row["related_lab"] or "-"),
                "status": str(row["status"]),
                "updated_at": str(row["updated_at"]),
            }
        )

    return DashboardData(
        sources_total=sources_total,
        events_total=events_total,
        raw_total=raw_total,
        canonical_total=canonical_total,
        latest_pipeline=latest_pipeline,
        latest_fetch_runs=latest_fetch_runs,
        recent_events=recent_events,
    )


def _render_rows(rows: list[dict[str, str]], columns: list[str], empty_text: str) -> str:
    if not rows:
        return f"<tr><td colspan='{len(columns)}'>{html.escape(empty_text)}</td></tr>"
    rendered: list[str] = []
    for row in rows:
        cells = "".join(f"<td>{html.escape(row.get(col, '-'))}</td>" for col in columns)
        rendered.append(f"<tr>{cells}</tr>")
    return "".join(rendered)


def render_dashboard(data: DashboardData, offline_mode: bool = False) -> str:
    now = datetime.now(UTC).isoformat()
    pipeline = data.latest_pipeline
    fetch_rows = _render_rows(
        data.latest_fetch_runs,
        ["source_id", "status", "parsed", "failed", "finished_at"],
        "No fetch runs yet.",
    )
    event_rows = _render_rows(
        data.recent_events,
        ["event_id", "title", "related_lab", "status", "updated_at"],
        "No events yet.",
    )
    offline_chip = "<span class='chip'>offline mode</span>" if offline_mode else ""
    quickstart = """
    <section class="panel">
      <h2>Quick Start</h2>
      <p class="muted">Offline-safe commands:</p>
      <pre>PYTHONPATH=src python3 -m ai_info_collection.cli --db-path ./data.db ingest-signals --input ./sample.jsonl
PYTHONPATH=src python3 -m ai_info_collection.cli --db-path ./data.db merge-events --limit 100
PYTHONPATH=src python3 -m ai_info_collection.cli --db-path ./data.db recent-events --limit 10
PYTHONPATH=src python3 -m ai_info_collection.cli --db-path ./data.db review</pre>
    </section>
    """

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>AI Info Collection</title>
  <style>
    :root {{
      --bg: #f5f8ff;
      --card: #ffffff;
      --ink: #132238;
      --muted: #53677f;
      --line: #d8e2f0;
      --accent: #1460ff;
    }}
    body {{
      margin: 0;
      font-family: "Avenir Next", "Helvetica Neue", sans-serif;
      background: radial-gradient(circle at 20% 0%, #e7f0ff 0, #f5f8ff 45%, #f8fbff 100%);
      color: var(--ink);
    }}
    .wrap {{
      max-width: 1100px;
      margin: 0 auto;
      padding: 24px;
    }}
    .hero {{
      background: linear-gradient(135deg, #0f3f98, #1460ff);
      color: #fff;
      padding: 20px;
      border-radius: 16px;
      box-shadow: 0 8px 30px rgba(10, 55, 130, 0.25);
    }}
    .hero h1 {{ margin: 0 0 8px; font-size: 28px; }}
    .hero p {{ margin: 0; opacity: 0.95; }}
    .grid {{
      margin-top: 18px;
      display: grid;
      grid-template-columns: repeat(4, minmax(120px, 1fr));
      gap: 12px;
    }}
    .kpi {{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 14px;
    }}
    .kpi .label {{ color: var(--muted); font-size: 12px; }}
    .kpi .value {{ margin-top: 6px; font-size: 26px; font-weight: 700; }}
    .panel {{
      margin-top: 16px;
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 16px;
    }}
    .panel h2 {{ margin: 0 0 12px; font-size: 18px; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
    }}
    th, td {{
      text-align: left;
      border-bottom: 1px solid var(--line);
      padding: 8px 6px;
      vertical-align: top;
    }}
    th {{ color: var(--muted); font-weight: 600; }}
    .muted {{ color: var(--muted); font-size: 13px; }}
    .chip {{
      display: inline-block;
      border-radius: 99px;
      background: #e8f0ff;
      color: #1247b8;
      padding: 4px 10px;
      font-size: 12px;
      margin-right: 6px;
    }}
    pre {{
      margin: 8px 0 0;
      padding: 10px;
      border-radius: 10px;
      background: #f4f8ff;
      border: 1px solid var(--line);
      overflow-x: auto;
      font-size: 12px;
      line-height: 1.5;
    }}
    @media (max-width: 820px) {{
      .grid {{ grid-template-columns: repeat(2, minmax(120px, 1fr)); }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <h1>AI Info Collection</h1>
      <p>Local dashboard for pipeline health, fetch status, and recent events.</p>
      <div style="margin-top:10px;">
        <span class="chip">updated: {html.escape(now)}</span>
        <span class="chip">latest run: {html.escape(pipeline["status"])}</span>
        {offline_chip}
      </div>
    </section>

    <section class="grid">
      <article class="kpi"><div class="label">Sources</div><div class="value">{data.sources_total}</div></article>
      <article class="kpi"><div class="label">Events</div><div class="value">{data.events_total}</div></article>
      <article class="kpi"><div class="label">Raw Docs</div><div class="value">{data.raw_total}</div></article>
      <article class="kpi"><div class="label">Canonical Docs</div><div class="value">{data.canonical_total}</div></article>
    </section>

    <section class="panel">
      <h2>Latest Pipeline Run</h2>
      <p class="muted">run_id: {html.escape(pipeline["run_id"])}</p>
      <p class="muted">status: {html.escape(pipeline["status"])} | reason: {html.escape(pipeline["status_reason"])} | started_at: {html.escape(pipeline["started_at"])}</p>
      <p class="muted">fetch ok/fail: {html.escape(pipeline["fetch_success"])}/{html.escape(pipeline["fetch_failed"])} |
      ingest ok/fail: {html.escape(pipeline["ingest_success"])}/{html.escape(pipeline["ingest_failed"])} |
      merged: {html.escape(pipeline["merge_processed"])}</p>
    </section>
    {quickstart}

    <section class="panel">
      <h2>Recent Fetch Runs</h2>
      <table>
        <thead><tr><th>source_id</th><th>status</th><th>parsed</th><th>failed</th><th>finished_at</th></tr></thead>
        <tbody>{fetch_rows}</tbody>
      </table>
    </section>

    <section class="panel">
      <h2>Recent Events</h2>
      <table>
        <thead><tr><th>event_id</th><th>title</th><th>related_lab</th><th>status</th><th>updated_at</th></tr></thead>
        <tbody>{event_rows}</tbody>
      </table>
    </section>
  </div>
</body>
</html>
"""


def create_ui_server(
    store: SQLiteStore,
    host: str = "127.0.0.1",
    port: int = 8765,
    offline_mode: bool = False,
) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path not in ("/", "/index.html"):
                self.send_response(404)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"Not Found")
                return
            page = render_dashboard(load_dashboard_data(store), offline_mode=offline_mode).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(page)))
            self.end_headers()
            self.wfile.write(page)

        def log_message(self, format: str, *args: object) -> None:  # noqa: A003
            return

    handler_class: Type[BaseHTTPRequestHandler] = Handler
    return ThreadingHTTPServer((host, port), handler_class)


def start_ui(store: SQLiteStore, host: str = "127.0.0.1", port: int = 8765, offline_mode: bool = False) -> None:
    server = create_ui_server(store=store, host=host, port=port, offline_mode=offline_mode)
    mode_text = " (offline mode)" if offline_mode else ""
    print(f"UI started at http://{host}:{port}{mode_text}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
