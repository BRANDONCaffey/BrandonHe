from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class Settings:
    api_host: str
    api_port: int
    db_path: Path
    thresholds: dict[str, dict[str, float]]
    ric_brent_m1: str
    ric_brent_m2: str
    ric_wti_m1: str
    ric_wti_m2: str
    ric_diesel_proxy: str
    ric_gasoline_proxy: str
    ric_dxy: str
    ric_us2y: str
    ric_us10y: str
    ric_gold: str
    ric_btcusd: str
    ric_es_fut: str
    ric_nq_fut: str
    disable_live: bool
    lseg_mode: str
    lseg_desktop_session_name: str
    lseg_session_name: str
    lseg_app_key: str | None
    lseg_username: str | None
    lseg_password: str | None
    lseg_client_id: str | None
    lseg_client_secret: str | None
    lseg_token_scope: str


def _load_thresholds() -> dict[str, dict[str, float]]:
    raw = os.getenv("HIMPACT_THRESHOLDS_JSON", "").strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        return {}
    return {}


def load_settings() -> Settings:
    def maybe(name: str) -> str | None:
        raw = os.getenv(name, "").strip()
        return raw or None

    return Settings(
        api_host=os.getenv("HIMPACT_API_HOST", "127.0.0.1"),
        api_port=int(os.getenv("HIMPACT_API_PORT", "8000")),
        db_path=Path(os.getenv("HIMPACT_DB_PATH", "./himpact.db")),
        thresholds=_load_thresholds(),
        ric_brent_m1=os.getenv("HIMPACT_RIC_BRENT_M1", "LCOc1"),
        ric_brent_m2=os.getenv("HIMPACT_RIC_BRENT_M2", "LCOc2"),
        ric_wti_m1=os.getenv("HIMPACT_RIC_WTI_M1", "CLc1"),
        ric_wti_m2=os.getenv("HIMPACT_RIC_WTI_M2", "CLc2"),
        ric_diesel_proxy=os.getenv("HIMPACT_RIC_DIESEL_PROXY", "HOc1"),
        ric_gasoline_proxy=os.getenv("HIMPACT_RIC_GASOLINE_PROXY", "RBc1"),
        ric_dxy=os.getenv("HIMPACT_RIC_DXY", ".DXY"),
        ric_us2y=os.getenv("HIMPACT_RIC_US2Y", "US2YT=RR"),
        ric_us10y=os.getenv("HIMPACT_RIC_US10Y", "US10YT=RR"),
        ric_gold=os.getenv("HIMPACT_RIC_GOLD", "XAU="),
        ric_btcusd=os.getenv("HIMPACT_RIC_BTCUSD", "BTC="),
        ric_es_fut=os.getenv("HIMPACT_RIC_ES_FUT", "ESc1"),
        ric_nq_fut=os.getenv("HIMPACT_RIC_NQ_FUT", "NQc1"),
        disable_live=os.getenv("HIMPACT_DISABLE_LIVE", "0") == "1",
        lseg_mode=os.getenv("HIMPACT_LSEG_MODE", "desktop").strip().lower(),
        lseg_desktop_session_name=os.getenv("HIMPACT_LSEG_DESKTOP_SESSION_NAME", "desktop.workspace"),
        lseg_session_name=os.getenv("HIMPACT_LSEG_SESSION_NAME", "platform.himpact"),
        lseg_app_key=maybe("HIMPACT_LSEG_APP_KEY"),
        lseg_username=maybe("HIMPACT_LSEG_USERNAME"),
        lseg_password=maybe("HIMPACT_LSEG_PASSWORD"),
        lseg_client_id=maybe("HIMPACT_LSEG_CLIENT_ID"),
        lseg_client_secret=maybe("HIMPACT_LSEG_CLIENT_SECRET"),
        lseg_token_scope=os.getenv("HIMPACT_LSEG_TOKEN_SCOPE", "trapi"),
    )


def utc_now_iso() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def utc_now():
    from datetime import UTC, datetime

    return datetime.now(UTC)


def request_id() -> str:
    from datetime import UTC, datetime

    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S_%f")
    return f"req_{ts}"


def is_entitlement_error(message: str) -> bool:
    lowered = message.lower()
    return "entitlement" in lowered or "permission" in lowered or "not authorized" in lowered


def as_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        if not math.isfinite(number):
            return None
        return number
    try:
        number = float(str(value).strip())
        if not math.isfinite(number):
            return None
        return number
    except (TypeError, ValueError):
        return None
