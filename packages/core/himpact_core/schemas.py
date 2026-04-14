from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from .constants import AlertDirection, AlertType, MetricStatus, SessionStatus


class MetricPoint(BaseModel):
    metric_key: str
    display_name: str
    value: float | None = None
    unit: str
    as_of: datetime | None = None
    status: MetricStatus
    source: str
    stale_seconds: int = 0
    suspect: bool | None = None


class MetricChange(BaseModel):
    metric_key: str
    window: str
    abs_change: float | None = None
    pct_change: float | None = None
    as_of: datetime | None = None


class EventCreateRequest(BaseModel):
    event_time: datetime
    category: str
    title: str
    source: str
    region: str | None = None
    tags: list[str] = Field(default_factory=list)
    note: str | None = None
    confirmed: bool = False
    workspace_ref: str | None = None


class EventPatchRequest(BaseModel):
    title: str | None = None
    source: str | None = None
    region: str | None = None
    tags: list[str] | None = None
    note: str | None = None
    confirmed: bool | None = None
    workspace_ref: str | None = None


class EventRecord(BaseModel):
    event_id: str
    event_time: datetime
    category: str
    title: str
    source: str
    region: str | None = None
    tags: list[str] = Field(default_factory=list)
    note: str | None = None
    confirmed: bool = False
    workspace_ref: str | None = None
    created_at: datetime
    updated_at: datetime


class AlertRecord(BaseModel):
    alert_id: str
    type: AlertType
    metric_key: str
    direction: AlertDirection
    threshold: float | None = None
    current_value: float | None = None
    triggered_at: datetime
    acknowledged: bool = False
    acknowledged_at: datetime | None = None


class SystemStatus(BaseModel):
    session_status: SessionStatus
    last_success_update: datetime | None = None
    last_history_backfill: datetime | None = None
    active_subscriptions: int = 0
    stale_metrics: list[str] = Field(default_factory=list)
    last_event_update: datetime | None = None
    session_reason: str | None = None
    data_source_mode: str | None = None


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    error: ErrorBody
    request_id: str
