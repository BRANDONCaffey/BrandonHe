from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

ROOT_DIR = Path(__file__).resolve().parents[2]
CORE_DIR = ROOT_DIR / "packages" / "core"
if str(CORE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_DIR))

from himpact_core.schemas import ErrorBody, ErrorResponse, EventCreateRequest, EventPatchRequest

from .config import load_settings, request_id, utc_now_iso
from .state import HimpactState


def create_app() -> FastAPI:
    settings = load_settings()
    state = HimpactState(settings)

    app = FastAPI(title="Himpact API", version="1.0.0-rc1")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.himpact = state

    @app.exception_handler(HTTPException)
    async def handle_http_exception(_: Request, exc: HTTPException):
        rid = request_id()
        error = ErrorResponse(
            error=ErrorBody(
                code=str(exc.status_code),
                message=str(exc.detail),
                details={},
            ),
            request_id=rid,
        )
        return JSONResponse(status_code=exc.status_code, content=error.model_dump(mode="json"))

    @app.get("/api/v1/health")
    async def health():
        return {"status": "ok", "service": "himpact-api", "time": utc_now_iso()}

    @app.get("/api/v1/status")
    async def get_status(refresh: bool = Query(default=True)):
        current_state: HimpactState = app.state.himpact
        if refresh:
            current_state.get_latest(current_state.resolve_metric_keys(panel=None, metric_keys=None))
        payload = current_state.get_system_status()
        return payload.model_dump(mode="json")

    @app.get("/api/v1/metrics/latest")
    async def get_metrics_latest(
        panel: int | None = Query(default=None),
        metric_keys: str | None = Query(default=None),
    ):
        current_state: HimpactState = app.state.himpact
        keys = [item.strip() for item in metric_keys.split(",")] if metric_keys else None
        resolved = current_state.resolve_metric_keys(panel=panel, metric_keys=keys)
        items = current_state.get_latest(resolved)
        return {
            "items": [item.model_dump(mode="json") for item in items],
            "request_id": request_id(),
        }

    @app.get("/api/v1/metrics/history")
    async def get_metrics_history(
        window: str = Query(pattern="^(1D|5D|20D)$"),
        metric_keys: str | None = Query(default=None),
    ):
        current_state: HimpactState = app.state.himpact
        keys = [item.strip() for item in metric_keys.split(",")] if metric_keys else None
        resolved = current_state.resolve_metric_keys(panel=None, metric_keys=keys)
        items = current_state.get_history(window=window, metric_keys=resolved)
        return {
            "window": window,
            "items": [item.model_dump(mode="json") for item in items],
            "request_id": request_id(),
        }

    @app.get("/api/v1/events")
    async def get_events(
        category: str | None = Query(default=None),
        confirmed: bool | None = Query(default=None),
        q: str | None = Query(default=None),
        limit: int = Query(default=50, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
        sort: str = Query(default="event_time_desc", pattern="^(event_time_desc|event_time_asc)$"),
    ):
        current_state: HimpactState = app.state.himpact
        items, total = current_state.events.list(
            category=category,
            confirmed=confirmed,
            query=q,
            limit=limit,
            offset=offset,
            sort=sort,
        )
        return {
            "items": [item.model_dump(mode="json") for item in items],
            "total": total,
            "request_id": request_id(),
        }

    @app.post("/api/v1/events", status_code=201)
    async def create_event(payload: EventCreateRequest):
        current_state: HimpactState = app.state.himpact
        record = current_state.events.create(payload)
        return record.model_dump(mode="json")

    @app.patch("/api/v1/events/{event_id}")
    async def patch_event(event_id: str, payload: EventPatchRequest):
        current_state: HimpactState = app.state.himpact
        record = current_state.events.patch(event_id=event_id, payload=payload)
        if record is None:
            raise HTTPException(status_code=404, detail=f"event not found: {event_id}")
        return record.model_dump(mode="json")

    @app.get("/api/v1/alerts/active")
    async def get_active_alerts(
        metric_key: str | None = Query(default=None),
        type: str | None = Query(default=None),
    ):
        current_state: HimpactState = app.state.himpact
        alerts = current_state.alerts.active(metric_key=metric_key, alert_type=type)
        return {"items": [item.model_dump(mode="json") for item in alerts], "request_id": request_id()}

    @app.post("/api/v1/alerts/{alert_id}/ack")
    async def ack_alert(alert_id: str):
        current_state: HimpactState = app.state.himpact
        record = current_state.alerts.acknowledge(alert_id)
        if record is None:
            raise HTTPException(status_code=404, detail=f"alert not found: {alert_id}")
        return {
            "alert_id": record.alert_id,
            "acknowledged": record.acknowledged,
            "acknowledged_at": record.acknowledged_at,
        }

    return app


app = create_app()
