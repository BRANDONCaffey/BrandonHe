from __future__ import annotations

import os
import time
from datetime import datetime

import requests
import streamlit as st

API_BASE = os.getenv("HIMPACT_API_BASE_URL", "http://127.0.0.1:8000/api/v1")

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

PANEL_METRIC_KEYS = {
    1: [
        "brent_m1",
        "brent_m2",
        "brent_m1_m2_spread",
        "wti_m1",
        "wti_m2",
        "wti_m1_m2_spread",
        "brent_wti_spread",
    ],
    2: [
        "diesel_proxy",
        "gasoline_proxy",
        "diesel_crack",
        "gasoline_crack",
    ],
    3: [
        "dxy",
        "us2y",
        "us10y",
        "gold",
    ],
    4: [
        "btcusd",
        "es_fut",
        "nq_fut",
    ],
}


def api_get(path: str, params: dict | None = None) -> dict | None:
    try:
        response = requests.get(f"{API_BASE}{path}", params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        st.error(f"API GET 失败: {path} -> {exc}")
        return None


def api_post(path: str, body: dict) -> dict | None:
    try:
        response = requests.post(f"{API_BASE}{path}", json=body, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        st.error(f"API POST 失败: {path} -> {exc}")
        return None


def api_patch(path: str, body: dict) -> dict | None:
    try:
        response = requests.patch(f"{API_BASE}{path}", json=body, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        st.error(f"API PATCH 失败: {path} -> {exc}")
        return None


def format_value(value: float | None, unit: str) -> str:
    if value is None:
        return "-"
    decimals = 3
    if abs(value) >= 1000:
        decimals = 2
    return f"{value:,.{decimals}f} {unit}"


def format_change(value: float | None, suffix: str) -> str:
    if value is None:
        return "-"
    return f"{value:+.3f}{suffix}"


def status_label(status: str) -> str:
    mapping = {
        "ok": "正常",
        "stale": "延迟",
        "unentitled": "无权限",
        "error": "错误",
    }
    return mapping.get(status, status)


def status_reason(status: str) -> str:
    mapping = {
        "ok": "实时值可用",
        "stale": "使用最近可用值或当前无新值",
        "unentitled": "当前账户对该 RIC 无权限",
        "error": "连接或数据请求失败",
    }
    return mapping.get(status, "未知状态")


def metric_map(items: list[dict]) -> dict[str, dict]:
    return {item["metric_key"]: item for item in items}


def fetch_history(metric_keys: list[str]) -> dict[str, dict[str, dict]]:
    rows: dict[str, dict[str, dict]] = {}
    if not metric_keys:
        return rows
    key_csv = ",".join(metric_keys)
    for window in ("1D", "5D", "20D"):
        payload = api_get("/metrics/history", params={"window": window, "metric_keys": key_csv})
        items = payload.get("items", []) if payload else []
        for item in items:
            key = item["metric_key"]
            rows.setdefault(key, {})
            rows[key][window] = item
    return rows


def render_panel_table(
    *,
    title: str,
    metric_keys: list[str],
    metrics: dict[str, dict],
    history: dict[str, dict[str, dict]],
) -> None:
    st.subheader(title)
    table_rows = []
    for key in metric_keys:
        item = metrics.get(key, {})
        hist = history.get(key, {})
        one = hist.get("1D", {})
        five = hist.get("5D", {})
        twenty = hist.get("20D", {})

        status = item.get("status", "error")
        row = {
            "metric_key": key,
            "display_name": item.get("display_name", key),
            "value": format_value(item.get("value"), item.get("unit", "")),
            "status": status_label(status),
            "status_reason": status_reason(status),
            "1D abs": format_change(one.get("abs_change"), ""),
            "1D %": format_change(one.get("pct_change"), "%"),
            "5D abs": format_change(five.get("abs_change"), ""),
            "5D %": format_change(five.get("pct_change"), "%"),
            "20D abs": format_change(twenty.get("abs_change"), ""),
            "20D %": format_change(twenty.get("pct_change"), "%"),
            "as_of": item.get("as_of"),
        }
        table_rows.append(row)

    st.dataframe(table_rows, use_container_width=True, hide_index=True)


def render_system_status(status_payload: dict | None) -> None:
    st.subheader("面板6：系统状态")
    if not status_payload:
        st.warning("系统状态暂不可用")
        return

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Session", status_payload.get("session_status", "unknown"))
    col2.metric("Data Mode", status_payload.get("data_source_mode", "unknown"))
    col3.metric("Active Subs", str(status_payload.get("active_subscriptions", 0)))
    stale = status_payload.get("stale_metrics", [])
    col4.metric("Stale Metrics", str(len(stale)))
    st.json(status_payload)


def render_events_panel() -> None:
    st.subheader("面板5：事件检查板")
    col_filter_1, col_filter_2, col_filter_3 = st.columns(3)
    category = col_filter_1.selectbox("分类筛选", ["ALL", *EVENT_CATEGORIES], index=0)
    query_text = col_filter_2.text_input("关键词", value="")
    confirmed_only = col_filter_3.selectbox("确认状态", ["ALL", "CONFIRMED", "UNCONFIRMED"], index=0)

    confirmed = None
    if confirmed_only == "CONFIRMED":
        confirmed = True
    elif confirmed_only == "UNCONFIRMED":
        confirmed = False

    params = {
        "limit": 100,
        "offset": 0,
        "sort": "event_time_desc",
    }
    if category != "ALL":
        params["category"] = category
    if query_text.strip():
        params["q"] = query_text.strip()
    if confirmed is not None:
        params["confirmed"] = confirmed

    payload = api_get("/events", params=params)
    items = payload.get("items", []) if payload else []
    st.caption(f"总数: {payload.get('total', 0) if payload else 0}")
    st.dataframe(items, use_container_width=True, hide_index=True)

    with st.expander("新增事件", expanded=False):
        with st.form("create_event_form"):
            event_time = st.text_input("事件时间 (ISO8601)", value=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"))
            event_category = st.selectbox("分类", EVENT_CATEGORIES, index=0)
            title = st.text_input("标题")
            source = st.text_input("来源", value="Reuters")
            region = st.text_input("地理区域", value="Middle East")
            tags = st.text_input("标签（逗号分隔）", value="")
            note = st.text_area("备注", value="")
            confirmed_flag = st.checkbox("已确认", value=False)
            workspace_ref = st.text_input("Workspace 页面引用", value="")
            submitted = st.form_submit_button("提交")
            if submitted:
                body = {
                    "event_time": event_time,
                    "category": event_category,
                    "title": title,
                    "source": source,
                    "region": region,
                    "tags": [tag.strip() for tag in tags.split(",") if tag.strip()],
                    "note": note or None,
                    "confirmed": confirmed_flag,
                    "workspace_ref": workspace_ref or None,
                }
                created = api_post("/events", body)
                if created:
                    st.success(f"事件已创建: {created.get('event_id')}")

    if items:
        with st.expander("编辑事件", expanded=False):
            event_ids = [item["event_id"] for item in items]
            selected_event_id = st.selectbox("选择事件ID", event_ids)
            with st.form("patch_event_form"):
                patch_title = st.text_input("新标题（可空）")
                patch_source = st.text_input("新来源（可空）")
                patch_region = st.text_input("新区域（可空）")
                patch_tags = st.text_input("新标签（逗号分隔，可空）")
                patch_note = st.text_area("新备注（可空）")
                patch_confirmed = st.selectbox("确认状态更新", ["NO_CHANGE", "TRUE", "FALSE"], index=0)
                patch_workspace_ref = st.text_input("新 Workspace 引用（可空）")
                patch_submit = st.form_submit_button("更新")
                if patch_submit:
                    body = {}
                    if patch_title.strip():
                        body["title"] = patch_title.strip()
                    if patch_source.strip():
                        body["source"] = patch_source.strip()
                    if patch_region.strip():
                        body["region"] = patch_region.strip()
                    if patch_tags.strip():
                        body["tags"] = [tag.strip() for tag in patch_tags.split(",") if tag.strip()]
                    if patch_note.strip():
                        body["note"] = patch_note.strip()
                    if patch_workspace_ref.strip():
                        body["workspace_ref"] = patch_workspace_ref.strip()
                    if patch_confirmed == "TRUE":
                        body["confirmed"] = True
                    elif patch_confirmed == "FALSE":
                        body["confirmed"] = False
                    if not body:
                        st.info("没有可更新字段")
                    else:
                        patched = api_patch(f"/events/{selected_event_id}", body)
                        if patched:
                            st.success(f"事件已更新: {patched.get('event_id')}")


def render_alerts() -> None:
    st.subheader("活动告警")
    payload = api_get("/alerts/active")
    alerts = payload.get("items", []) if payload else []
    if not alerts:
        st.info("当前没有活动告警")
        return
    st.dataframe(alerts, use_container_width=True, hide_index=True)
    selected = st.selectbox("选择要确认的告警", [item["alert_id"] for item in alerts])
    if st.button("确认告警"):
        result = api_post(f"/alerts/{selected}/ack", {})
        if result:
            st.success(f"已确认: {selected}")


def main() -> None:
    st.set_page_config(page_title="Himpact", layout="wide")
    st.title("Himpact v1.0 RC1（Live）")
    st.caption("客观监控：面板1-4 + 事件日志 + 系统状态")

    with st.sidebar:
        st.markdown("### 连接设置")
        st.code(API_BASE)
        auto_refresh = st.checkbox("自动刷新", value=False)
        interval = st.slider("刷新间隔（秒）", min_value=1, max_value=30, value=1, step=1)
        if st.button("立即刷新"):
            st.rerun()

    latest_payload = api_get("/metrics/latest")
    status_payload = api_get("/status", params={"refresh": "false"})
    metrics = latest_payload.get("items", []) if latest_payload else []
    mm = metric_map(metrics)

    all_keys: list[str] = []
    for _, keys in PANEL_METRIC_KEYS.items():
        all_keys.extend(keys)
    history = fetch_history(all_keys)

    render_panel_table(title="面板1：原油主屏", metric_keys=PANEL_METRIC_KEYS[1], metrics=mm, history=history)
    render_panel_table(title="面板2：成品油传导", metric_keys=PANEL_METRIC_KEYS[2], metrics=mm, history=history)
    render_panel_table(title="面板3：宏观价格传导", metric_keys=PANEL_METRIC_KEYS[3], metrics=mm, history=history)
    render_panel_table(title="面板4：风险资产响应", metric_keys=PANEL_METRIC_KEYS[4], metrics=mm, history=history)

    render_events_panel()
    render_system_status(status_payload)
    render_alerts()

    if auto_refresh:
        time.sleep(interval)
        st.rerun()


if __name__ == "__main__":
    main()
