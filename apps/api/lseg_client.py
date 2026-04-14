from __future__ import annotations

import importlib
import logging
from dataclasses import dataclass
from typing import Any

from himpact_core.constants import SessionStatus

from .config import Settings, as_float

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ProbeResult:
    status: SessionStatus
    reason: str | None
    active_subscriptions: int


class _BaseLsegClient:
    source_label = "lseg"
    price_fields = ["TRDPRC_1", "CF_LAST", "BID", "ASK", "VALUE"]

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._module: Any | None = None
        self._session_open = False
        self._last_reason: str | None = None

    def _load_module(self):
        if self._module is not None:
            return self._module
        self._module = importlib.import_module("lseg.data")
        return self._module

    def fetch_prices(self, rics: list[str]) -> dict[str, float | None]:
        if not rics:
            return {}
        if not self._session_open:
            raise RuntimeError("session is not open")

        ld = self._load_module()
        try:
            result = ld.get_data(universe=rics, fields=self.price_fields)
        except Exception as exc:  # pragma: no cover - entitlement/network dependent
            raise RuntimeError(f"lseg_get_data_failed: {exc}") from exc

        price_map = self._parse_result(result, rics)
        return {ric: price_map.get(ric) for ric in rics}

    def _parse_result(self, result: Any, rics: list[str]) -> dict[str, float | None]:
        df = result.data if hasattr(result, "data") else result
        records: list[dict[str, Any]] = []
        if hasattr(df, "to_dict"):
            try:
                records = df.to_dict(orient="records")
            except TypeError:
                try:
                    records = list(df.to_dict().values())
                except Exception:
                    records = []

        if not records:
            return {ric: None for ric in rics}

        price_map: dict[str, float | None] = {ric: None for ric in rics}
        for row in records:
            instrument = row.get("Instrument") or row.get("instrument") or row.get("RIC") or row.get("ric")
            if instrument is None:
                continue
            price = None
            for field in self.price_fields:
                candidate = as_float(row.get(field))
                if candidate is not None:
                    price = candidate
                    break
            if instrument in price_map:
                price_map[instrument] = price
        return price_map


class LsegDesktopClient(_BaseLsegClient):
    source_label = "lseg_workspace"

    def probe(self, active_subscriptions: int) -> ProbeResult:
        if self._settings.disable_live:
            self._last_reason = "live_disabled"
            return ProbeResult(
                status=SessionStatus.DISCONNECTED,
                reason=self._last_reason,
                active_subscriptions=active_subscriptions,
            )

        try:
            ld = self._load_module()
        except Exception as exc:  # pragma: no cover - host env dependent
            self._last_reason = f"lseg_import_failed: {exc}"
            return ProbeResult(
                status=SessionStatus.DISCONNECTED,
                reason=self._last_reason,
                active_subscriptions=active_subscriptions,
            )

        if not self._session_open:
            try:
                if self._settings.lseg_app_key:
                    ld.open_session(self._settings.lseg_desktop_session_name, app_key=self._settings.lseg_app_key)
                else:
                    ld.open_session(self._settings.lseg_desktop_session_name)
                self._session_open = True
                self._last_reason = None
            except Exception as exc:  # pragma: no cover - workspace/env dependent
                self._last_reason = f"desktop_session_open_failed: {exc}"
                return ProbeResult(
                    status=SessionStatus.DISCONNECTED,
                    reason=self._last_reason,
                    active_subscriptions=active_subscriptions,
                )

        return ProbeResult(
            status=SessionStatus.CONNECTED,
            reason=self._last_reason,
            active_subscriptions=active_subscriptions,
        )


class LsegPlatformClient(_BaseLsegClient):
    source_label = "lseg_platform"

    def _build_config_payload(self) -> tuple[dict[str, Any] | None, str | None]:
        if not self._settings.lseg_app_key:
            return None, "missing_app_key"

        has_password_grant = bool(self._settings.lseg_username and self._settings.lseg_password)
        has_client_credentials = bool(self._settings.lseg_client_id and self._settings.lseg_client_secret)
        if not has_password_grant and not has_client_credentials:
            return None, "missing_oauth_credentials"

        session_payload: dict[str, Any] = {
            "app-key": self._settings.lseg_app_key,
            "signon_control": False,
        }
        if has_client_credentials:
            session_payload["client_id"] = self._settings.lseg_client_id
            session_payload["client_secret"] = self._settings.lseg_client_secret
            session_payload["token_scope"] = self._settings.lseg_token_scope
        else:
            session_payload["username"] = self._settings.lseg_username
            session_payload["password"] = self._settings.lseg_password

        if not self._settings.lseg_session_name.startswith("platform."):
            return None, "invalid_session_name"

        _, session_leaf = self._settings.lseg_session_name.split(".", 1)
        payload = {
            "sessions": {
                "default": self._settings.lseg_session_name,
                "platform": {session_leaf: session_payload},
            }
        }
        return payload, None

    def probe(self, active_subscriptions: int) -> ProbeResult:
        if self._settings.disable_live:
            self._last_reason = "live_disabled"
            return ProbeResult(
                status=SessionStatus.DISCONNECTED,
                reason=self._last_reason,
                active_subscriptions=active_subscriptions,
            )

        config_payload, config_error = self._build_config_payload()
        if config_error:
            self._last_reason = config_error
            return ProbeResult(
                status=SessionStatus.DISCONNECTED,
                reason=self._last_reason,
                active_subscriptions=active_subscriptions,
            )

        try:
            ld = self._load_module()
        except Exception as exc:  # pragma: no cover - host env dependent
            self._last_reason = f"lseg_import_failed: {exc}"
            return ProbeResult(
                status=SessionStatus.DISCONNECTED,
                reason=self._last_reason,
                active_subscriptions=active_subscriptions,
            )

        if not self._session_open:
            try:
                ld.get_config().set_param("sessions", config_payload["sessions"])
                ld.open_session(self._settings.lseg_session_name, app_key=self._settings.lseg_app_key)
                self._session_open = True
                self._last_reason = None
            except Exception as exc:  # pragma: no cover - auth/network dependent
                self._last_reason = f"platform_session_open_failed: {exc}"
                return ProbeResult(
                    status=SessionStatus.DISCONNECTED,
                    reason=self._last_reason,
                    active_subscriptions=active_subscriptions,
                )

        return ProbeResult(
            status=SessionStatus.CONNECTED,
            reason=self._last_reason,
            active_subscriptions=active_subscriptions,
        )


def create_lseg_client(settings: Settings):
    mode = settings.lseg_mode
    if mode == "platform":
        return LsegPlatformClient(settings=settings)
    return LsegDesktopClient(settings=settings)
