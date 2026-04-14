from __future__ import annotations

from enum import Enum


class SessionStatus(str, Enum):
    CONNECTED = "connected"
    DEGRADED = "degraded"
    DISCONNECTED = "disconnected"


class MetricStatus(str, Enum):
    OK = "ok"
    STALE = "stale"
    UNENTITLED = "unentitled"
    ERROR = "error"


class AlertType(str, Enum):
    THRESHOLD_CROSS = "threshold_cross"
    STALE_DATA = "stale_data"
    CONNECTION_ERROR = "connection_error"


class AlertDirection(str, Enum):
    UP = "up"
    DOWN = "down"
    NA = "na"


EVENT_CATEGORIES = [
    "Shipping",
    "Insurance",
    "Mines / chokepoint",
    "Refinery outage",
    "Product shortage",
    "IEA",
    "SPR",
    "Sanctions",
    "Escort / military",
    "Ceasefire / talks",
    "Asia buying",
    "Alternative barrels",
]

