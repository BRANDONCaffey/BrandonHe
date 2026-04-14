from __future__ import annotations

import uuid
from datetime import UTC, datetime

from himpact_core.constants import AlertDirection, AlertType, MetricStatus, SessionStatus
from himpact_core.schemas import AlertRecord, MetricPoint


class AlertEngine:
    def __init__(self, thresholds: dict[str, dict[str, float]]) -> None:
        self._thresholds = thresholds
        self._alerts: dict[str, AlertRecord] = {}
        self._last_values: dict[str, float] = {}

    def evaluate(self, metrics: list[MetricPoint], session_status: SessionStatus) -> None:
        now = datetime.now(UTC)
        if session_status == SessionStatus.DISCONNECTED:
            self._emit_once(
                alert_type=AlertType.CONNECTION_ERROR,
                metric_key="workspace_session",
                direction=AlertDirection.NA,
                threshold=None,
                current_value=None,
                now=now,
            )

        for metric in metrics:
            if metric.status == MetricStatus.STALE:
                self._emit_once(
                    alert_type=AlertType.STALE_DATA,
                    metric_key=metric.metric_key,
                    direction=AlertDirection.NA,
                    threshold=None,
                    current_value=metric.value,
                    now=now,
                )

            if metric.status != MetricStatus.OK or metric.value is None:
                continue

            previous = self._last_values.get(metric.metric_key)
            self._last_values[metric.metric_key] = metric.value

            rule = self._thresholds.get(metric.metric_key, {})
            up = rule.get("up")
            down = rule.get("down")
            if previous is None:
                continue

            if up is not None and previous < float(up) <= metric.value:
                self._emit_once(
                    alert_type=AlertType.THRESHOLD_CROSS,
                    metric_key=metric.metric_key,
                    direction=AlertDirection.UP,
                    threshold=float(up),
                    current_value=metric.value,
                    now=now,
                )
            if down is not None and previous > float(down) >= metric.value:
                self._emit_once(
                    alert_type=AlertType.THRESHOLD_CROSS,
                    metric_key=metric.metric_key,
                    direction=AlertDirection.DOWN,
                    threshold=float(down),
                    current_value=metric.value,
                    now=now,
                )

    def active(self, metric_key: str | None = None, alert_type: str | None = None) -> list[AlertRecord]:
        rows = [alert for alert in self._alerts.values() if not alert.acknowledged]
        if metric_key:
            rows = [alert for alert in rows if alert.metric_key == metric_key]
        if alert_type:
            rows = [alert for alert in rows if alert.type.value == alert_type]
        rows.sort(key=lambda item: item.triggered_at, reverse=True)
        return rows

    def acknowledge(self, alert_id: str) -> AlertRecord | None:
        alert = self._alerts.get(alert_id)
        if alert is None:
            return None
        alert.acknowledged = True
        alert.acknowledged_at = datetime.now(UTC)
        self._alerts[alert_id] = alert
        return alert

    def _emit_once(
        self,
        *,
        alert_type: AlertType,
        metric_key: str,
        direction: AlertDirection,
        threshold: float | None,
        current_value: float | None,
        now: datetime,
    ) -> None:
        for alert in self._alerts.values():
            if (
                not alert.acknowledged
                and alert.type == alert_type
                and alert.metric_key == metric_key
                and alert.direction == direction
            ):
                return
        alert_id = f"alt_{uuid.uuid4().hex[:8]}"
        self._alerts[alert_id] = AlertRecord(
            alert_id=alert_id,
            type=alert_type,
            metric_key=metric_key,
            direction=direction,
            threshold=threshold,
            current_value=current_value,
            triggered_at=now,
            acknowledged=False,
        )
