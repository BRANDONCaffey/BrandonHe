from __future__ import annotations

from fastapi.testclient import TestClient


def build_client(tmp_path, monkeypatch):
    monkeypatch.setenv("HIMPACT_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("HIMPACT_DISABLE_LIVE", "1")
    monkeypatch.setenv("HIMPACT_LSEG_MODE", "desktop")
    from apps.api.main import create_app

    return TestClient(create_app())


def test_health_endpoint(tmp_path, monkeypatch):
    client = build_client(tmp_path, monkeypatch)
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "himpact-api"


def test_events_crud(tmp_path, monkeypatch):
    client = build_client(tmp_path, monkeypatch)
    create_payload = {
        "event_time": "2026-04-14T08:30:00Z",
        "category": "Shipping",
        "title": "Test event",
        "source": "Reuters",
        "region": "Middle East",
        "tags": ["test"],
        "note": "note",
        "confirmed": False,
        "workspace_ref": "Top News > Energy",
    }
    create_response = client.post("/api/v1/events", json=create_payload)
    assert create_response.status_code == 201
    event_id = create_response.json()["event_id"]

    patch_response = client.patch(
        f"/api/v1/events/{event_id}",
        json={"confirmed": True, "note": "updated"},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["confirmed"] is True

    list_response = client.get("/api/v1/events", params={"q": "Test", "limit": 10, "offset": 0})
    assert list_response.status_code == 200
    assert list_response.json()["total"] >= 1


def test_live_disabled_returns_status_only(tmp_path, monkeypatch):
    client = build_client(tmp_path, monkeypatch)
    response = client.get("/api/v1/metrics/latest", params={"panel": 1})
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) >= 4
    for item in items:
        assert item["status"] in {"ok", "stale", "unentitled", "error"}
    assert all(item["value"] is None for item in items)

    alerts_response = client.get("/api/v1/alerts/active")
    assert alerts_response.status_code == 200
    alert_items = alerts_response.json()["items"]
    assert any(alert["type"] == "connection_error" for alert in alert_items)


def test_panel_metric_coverage_for_rc(tmp_path, monkeypatch):
    client = build_client(tmp_path, monkeypatch)

    panel_expectations = {
        1: {
            "brent_m1",
            "brent_m2",
            "wti_m1",
            "wti_m2",
            "brent_m1_m2_spread",
            "wti_m1_m2_spread",
            "brent_wti_spread",
        },
        2: {"diesel_proxy", "gasoline_proxy", "diesel_crack", "gasoline_crack"},
        3: {"dxy", "us2y", "us10y", "gold"},
        4: {"btcusd", "es_fut", "nq_fut"},
    }

    for panel, expected_keys in panel_expectations.items():
        response = client.get("/api/v1/metrics/latest", params={"panel": panel})
        assert response.status_code == 200
        got_keys = {item["metric_key"] for item in response.json()["items"]}
        assert expected_keys == got_keys


def test_status_contains_mode_and_reason(tmp_path, monkeypatch):
    client = build_client(tmp_path, monkeypatch)
    response = client.get("/api/v1/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["session_status"] in {"connected", "degraded", "disconnected"}
    assert payload["data_source_mode"] == "desktop"
    assert "session_reason" in payload

    response_no_refresh = client.get("/api/v1/status", params={"refresh": "false"})
    assert response_no_refresh.status_code == 200


def test_platform_missing_credentials_returns_error_state(tmp_path, monkeypatch):
    monkeypatch.setenv("HIMPACT_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("HIMPACT_DISABLE_LIVE", "0")
    monkeypatch.setenv("HIMPACT_LSEG_MODE", "platform")
    monkeypatch.delenv("HIMPACT_LSEG_APP_KEY", raising=False)
    monkeypatch.delenv("HIMPACT_LSEG_USERNAME", raising=False)
    monkeypatch.delenv("HIMPACT_LSEG_PASSWORD", raising=False)
    monkeypatch.delenv("HIMPACT_LSEG_CLIENT_ID", raising=False)
    monkeypatch.delenv("HIMPACT_LSEG_CLIENT_SECRET", raising=False)
    from apps.api.main import create_app

    client = TestClient(create_app())
    response = client.get("/api/v1/metrics/latest", params={"panel": 1})
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) >= 4
    assert all(item["status"] in {"error", "stale", "unentitled", "ok"} for item in items)
    assert all(item["value"] is None for item in items)
