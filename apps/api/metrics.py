from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .config import Settings


@dataclass(slots=True)
class MetricDefinition:
    metric_key: str
    display_name: str
    unit: str
    panel: int
    source_type: str
    ric: str | None = None
    transform_fn: Callable[[float], float] | None = None
    derive_fn: Callable[[dict[str, float | None]], float | None] | None = None
    depends_on: tuple[str, ...] = ()


def build_metric_registry(settings: Settings) -> dict[str, MetricDefinition]:
    def _cents_gallon_to_usd_bbl(value: float) -> float:
        # 1 cent/gal = 0.42 USD/bbl (42 gal per barrel)
        return value * 0.42

    direct = {
        "brent_m1": MetricDefinition(
            metric_key="brent_m1",
            display_name="Brent M1",
            unit="USD/bbl",
            panel=1,
            source_type="stream",
            ric=settings.ric_brent_m1,
        ),
        "brent_m2": MetricDefinition(
            metric_key="brent_m2",
            display_name="Brent M2",
            unit="USD/bbl",
            panel=1,
            source_type="stream",
            ric=settings.ric_brent_m2,
        ),
        "wti_m1": MetricDefinition(
            metric_key="wti_m1",
            display_name="WTI M1",
            unit="USD/bbl",
            panel=1,
            source_type="stream",
            ric=settings.ric_wti_m1,
        ),
        "wti_m2": MetricDefinition(
            metric_key="wti_m2",
            display_name="WTI M2",
            unit="USD/bbl",
            panel=1,
            source_type="stream",
            ric=settings.ric_wti_m2,
        ),
        "diesel_proxy": MetricDefinition(
            metric_key="diesel_proxy",
            display_name="Diesel Proxy",
            unit="USD/bbl",
            panel=2,
            source_type="stream",
            ric=settings.ric_diesel_proxy,
            transform_fn=_cents_gallon_to_usd_bbl,
        ),
        "gasoline_proxy": MetricDefinition(
            metric_key="gasoline_proxy",
            display_name="Gasoline Proxy",
            unit="USD/bbl",
            panel=2,
            source_type="stream",
            ric=settings.ric_gasoline_proxy,
            transform_fn=_cents_gallon_to_usd_bbl,
        ),
        "dxy": MetricDefinition(
            metric_key="dxy",
            display_name="DXY",
            unit="index",
            panel=3,
            source_type="stream",
            ric=settings.ric_dxy,
        ),
        "us2y": MetricDefinition(
            metric_key="us2y",
            display_name="US 2Y",
            unit="%",
            panel=3,
            source_type="stream",
            ric=settings.ric_us2y,
        ),
        "us10y": MetricDefinition(
            metric_key="us10y",
            display_name="US 10Y",
            unit="%",
            panel=3,
            source_type="stream",
            ric=settings.ric_us10y,
        ),
        "gold": MetricDefinition(
            metric_key="gold",
            display_name="Gold",
            unit="USD/oz",
            panel=3,
            source_type="stream",
            ric=settings.ric_gold,
        ),
        "btcusd": MetricDefinition(
            metric_key="btcusd",
            display_name="BTCUSD",
            unit="USD",
            panel=4,
            source_type="stream",
            ric=settings.ric_btcusd,
        ),
        "es_fut": MetricDefinition(
            metric_key="es_fut",
            display_name="ES Future",
            unit="index",
            panel=4,
            source_type="stream",
            ric=settings.ric_es_fut,
        ),
        "nq_fut": MetricDefinition(
            metric_key="nq_fut",
            display_name="NQ Future",
            unit="index",
            panel=4,
            source_type="stream",
            ric=settings.ric_nq_fut,
        ),
    }

    def _diff(a: str, b: str):
        def fn(values: dict[str, float | None]) -> float | None:
            if values.get(a) is None or values.get(b) is None:
                return None
            return float(values[a] - values[b])

        return fn

    derived = {
        "brent_m1_m2_spread": MetricDefinition(
            metric_key="brent_m1_m2_spread",
            display_name="Brent M1-M2",
            unit="USD/bbl",
            panel=1,
            source_type="derived",
            derive_fn=_diff("brent_m1", "brent_m2"),
            depends_on=("brent_m1", "brent_m2"),
        ),
        "wti_m1_m2_spread": MetricDefinition(
            metric_key="wti_m1_m2_spread",
            display_name="WTI M1-M2",
            unit="USD/bbl",
            panel=1,
            source_type="derived",
            derive_fn=_diff("wti_m1", "wti_m2"),
            depends_on=("wti_m1", "wti_m2"),
        ),
        "brent_wti_spread": MetricDefinition(
            metric_key="brent_wti_spread",
            display_name="Brent-WTI Spread",
            unit="USD/bbl",
            panel=1,
            source_type="derived",
            derive_fn=_diff("brent_m1", "wti_m1"),
            depends_on=("brent_m1", "wti_m1"),
        ),
        "diesel_crack": MetricDefinition(
            metric_key="diesel_crack",
            display_name="Diesel Crack",
            unit="USD/bbl",
            panel=2,
            source_type="derived",
            derive_fn=_diff("diesel_proxy", "brent_m1"),
            depends_on=("diesel_proxy", "brent_m1"),
        ),
        "gasoline_crack": MetricDefinition(
            metric_key="gasoline_crack",
            display_name="Gasoline Crack",
            unit="USD/bbl",
            panel=2,
            source_type="derived",
            derive_fn=_diff("gasoline_proxy", "brent_m1"),
            depends_on=("gasoline_proxy", "brent_m1"),
        ),
    }
    return {**direct, **derived}


def direct_metric_keys(registry: dict[str, MetricDefinition]) -> list[str]:
    return [k for k, definition in registry.items() if definition.source_type == "stream"]


def metric_keys_by_panel(registry: dict[str, MetricDefinition], panel: int) -> list[str]:
    return [k for k, definition in registry.items() if definition.panel == panel]
