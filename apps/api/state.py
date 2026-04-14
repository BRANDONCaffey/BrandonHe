from __future__ import annotations

from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta
from threading import Lock

from himpact_core.constants import MetricStatus, SessionStatus
from himpact_core.schemas import MetricChange, MetricPoint, SystemStatus

from .alerts import AlertEngine
from .config import Settings, is_entitlement_error, utc_now
from .events_repo import EventRepository
from .lseg_client import create_lseg_client
from .metrics import MetricDefinition, build_metric_registry, direct_metric_keys, metric_keys_by_panel


class HimpactState:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.registry = build_metric_registry(settings)
        self.direct_keys = direct_metric_keys(self.registry)
        self.events = EventRepository(settings.db_path)
        self.alerts = AlertEngine(settings.thresholds)
        self.lseg = create_lseg_client(settings=settings)
        self._lock = Lock()
        self._cache: dict[str, MetricPoint] = {}
        self._history: dict[str, deque[tuple[datetime, float]]] = defaultdict(lambda: deque(maxlen=12000))
        self._session_status = SessionStatus.DISCONNECTED
        self._last_success_update: datetime | None = None
        self._last_history_backfill: datetime | None = None
        self._active_subscriptions = len(self.direct_keys)
        self._last_probe_reason: str | None = None

    def resolve_metric_keys(self, panel: int | None, metric_keys: list[str] | None) -> list[str]:
        if metric_keys:
            return [key for key in metric_keys if key in self.registry]
        if panel is not None:
            return metric_keys_by_panel(self.registry, panel)
        return list(self.registry.keys())

    def get_latest(self, metric_keys: list[str]) -> list[MetricPoint]:
        with self._lock:
            probe = self.lseg.probe(active_subscriptions=self._active_subscriptions)
            self._session_status = probe.status
            self._last_probe_reason = probe.reason

            live_values: dict[str, float | None] = {}
            live_error: str | None = None
            if probe.status == SessionStatus.CONNECTED:
                try:
                    rics = [self.registry[k].ric for k in self.direct_keys if self.registry[k].ric]
                    price_map = self.lseg.fetch_prices(rics)
                    for key in self.direct_keys:
                        definition = self.registry[key]
                        if definition.ric:
                            live_values[key] = price_map.get(definition.ric)
                except Exception as exc:
                    live_error = str(exc)
                    # If the request layer fails after "open_session", session is not usable.
                    self._session_status = SessionStatus.DISCONNECTED
                    self._last_probe_reason = live_error

            now = utc_now()
            direct_points: dict[str, MetricPoint] = {}
            for key in self.direct_keys:
                definition = self.registry[key]
                direct_points[key] = self._build_direct_point(
                    metric_key=key,
                    definition=definition,
                    now=now,
                    live_value=live_values.get(key),
                    live_error=live_error,
                    session_status=self._session_status,
                )

            if self._session_status == SessionStatus.CONNECTED:
                non_ok = [point for point in direct_points.values() if point.status != MetricStatus.OK]
                if non_ok:
                    self._session_status = SessionStatus.DEGRADED
                    if not self._last_probe_reason:
                        self._last_probe_reason = f"partial_metrics:{len(non_ok)}"

            all_points = dict(direct_points)
            all_values = {k: p.value for k, p in direct_points.items()}

            for key, definition in self.registry.items():
                if definition.source_type != "derived":
                    continue
                all_points[key] = self._build_derived_point(
                    key=key,
                    definition=definition,
                    now=now,
                    all_values=all_values,
                    source_points=direct_points,
                )

            self.alerts.evaluate(list(all_points.values()), self._session_status)

            filtered = [all_points[key] for key in metric_keys if key in all_points]
            return filtered

    def get_system_status(self) -> SystemStatus:
        stale_metrics = [
            key
            for key, point in self._cache.items()
            if point.status == MetricStatus.STALE
        ]
        return SystemStatus(
            session_status=self._session_status,
            last_success_update=self._last_success_update,
            last_history_backfill=self._last_history_backfill,
            active_subscriptions=self._active_subscriptions,
            stale_metrics=stale_metrics,
            last_event_update=self.events.last_event_update(),
            session_reason=self._last_probe_reason,
            data_source_mode=self.settings.lseg_mode,
        )

    def get_history(self, window: str, metric_keys: list[str]) -> list[MetricChange]:
        day_map = {"1D": 1, "5D": 5, "20D": 20}
        days = day_map.get(window, 1)
        cutoff = datetime.now(UTC) - timedelta(days=days)
        rows: list[MetricChange] = []
        with self._lock:
            for key in metric_keys:
                samples = list(self._history.get(key, []))
                if not samples:
                    rows.append(MetricChange(metric_key=key, window=window, as_of=None))
                    continue

                current_ts, current_val = samples[-1]
                baseline = None
                for ts, value in samples:
                    if ts >= cutoff:
                        baseline = (ts, value)
                        break
                if baseline is None:
                    rows.append(MetricChange(metric_key=key, window=window, as_of=current_ts))
                    continue

                _, base_val = baseline
                abs_change = current_val - base_val
                pct_change = None if base_val == 0 else (abs_change / base_val) * 100
                rows.append(
                    MetricChange(
                        metric_key=key,
                        window=window,
                        abs_change=abs_change,
                        pct_change=pct_change,
                        as_of=current_ts,
                    )
                )
            self._last_history_backfill = datetime.now(UTC)
        return rows

    def _build_direct_point(
        self,
        *,
        metric_key: str,
        definition: MetricDefinition,
        now: datetime,
        live_value: float | None,
        live_error: str | None,
        session_status: SessionStatus,
    ) -> MetricPoint:
        cached = self._cache.get(metric_key)
        status = MetricStatus.OK
        value = live_value

        if session_status != SessionStatus.CONNECTED:
            status = MetricStatus.STALE if cached and cached.value is not None else MetricStatus.ERROR
            value = cached.value if cached else None
        elif live_error:
            status = MetricStatus.UNENTITLED if is_entitlement_error(live_error) else MetricStatus.ERROR
            if cached and cached.value is not None:
                status = MetricStatus.STALE
                value = cached.value
        elif live_value is None:
            status = MetricStatus.STALE if cached and cached.value is not None else MetricStatus.ERROR
            value = cached.value if cached else None
        elif definition.transform_fn is not None:
            try:
                value = definition.transform_fn(live_value)
            except Exception:
                status = MetricStatus.ERROR
                value = None

        as_of = now if status == MetricStatus.OK else (cached.as_of if cached else now)
        stale_seconds = 0
        if as_of is not None:
            stale_seconds = max(int((now - as_of).total_seconds()), 0)

        point = MetricPoint(
            metric_key=metric_key,
            display_name=definition.display_name,
            value=value,
            unit=definition.unit,
            as_of=as_of,
            status=status,
            source=self.lseg.source_label,
            stale_seconds=stale_seconds,
        )
        self._cache[metric_key] = point
        if point.status == MetricStatus.OK and point.value is not None:
            self._history[metric_key].append((now, point.value))
            self._last_success_update = now
        return point

    def _build_derived_point(
        self,
        *,
        key: str,
        definition: MetricDefinition,
        now: datetime,
        all_values: dict[str, float | None],
        source_points: dict[str, MetricPoint],
    ) -> MetricPoint:
        cached = self._cache.get(key)
        value = definition.derive_fn(all_values) if definition.derive_fn else None
        dependency_keys = definition.depends_on
        dependencies = [source_points[k] for k in dependency_keys if k in source_points]
        source_statuses = [p.status for p in dependencies]
        status = MetricStatus.OK
        if dependency_keys and len(dependencies) != len(dependency_keys):
            status = MetricStatus.ERROR
        elif MetricStatus.ERROR in source_statuses:
            status = MetricStatus.ERROR
        elif MetricStatus.UNENTITLED in source_statuses:
            status = MetricStatus.UNENTITLED
        elif MetricStatus.STALE in source_statuses or value is None:
            status = MetricStatus.STALE

        as_of = now if status == MetricStatus.OK else (cached.as_of if cached else now)
        stale_seconds = max(int((now - as_of).total_seconds()), 0) if as_of else 0

        point = MetricPoint(
            metric_key=key,
            display_name=definition.display_name,
            value=value,
            unit=definition.unit,
            as_of=as_of,
            status=status,
            source="derived",
            stale_seconds=stale_seconds,
        )
        self._cache[key] = point
        if point.status == MetricStatus.OK and point.value is not None:
            self._history[key].append((now, point.value))
        return point
