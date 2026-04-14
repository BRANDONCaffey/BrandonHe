# Himpact API Contract（v1）

## 1. 结论（先看）
本契约是前后端联调唯一真相源。所有字段默认 JSON，时间统一 ISO8601（UTC），禁止前端依赖未声明字段。

## 2. 通用约定
- Base URL：`/api/v1`
- Content-Type：`application/json; charset=utf-8`
- 时间字段：`YYYY-MM-DDTHH:mm:ssZ`
- 数值字段：`number`（禁止字符串数值）
- 空值语义：
  - `null`：数据当前不可用
  - `status=stale`：数据过期
  - `status=unentitled`：权限不足
- `source` 语义：
  - `lseg_workspace`：Desktop Session
  - `lseg_platform`：Platform Session
  - `derived`：后端派生

### 2.1 错误响应（统一）
```json
{
  "error": {
    "code": "RIC_NOT_FOUND",
    "message": "RIC mapping not found for metric_key",
    "details": {
      "metric_key": "brent_m1"
    }
  },
  "request_id": "req_20260414_0001"
}
```

## 3. 数据模型

### 3.1 MetricPoint
```json
{
  "metric_key": "brent_m1",
  "display_name": "Brent M1",
  "value": 87.23,
  "unit": "USD/bbl",
  "as_of": "2026-04-14T09:10:00Z",
  "status": "ok",
  "source": "lseg_workspace",
  "stale_seconds": 0
}
```

### 3.2 MetricChange
```json
{
  "metric_key": "brent_m1",
  "window": "5D",
  "abs_change": 1.2,
  "pct_change": 1.39,
  "as_of": "2026-04-14T09:10:00Z"
}
```

### 3.3 EventRecord
```json
{
  "event_id": "evt_0001",
  "event_time": "2026-04-14T08:30:00Z",
  "category": "Shipping",
  "title": "Tanker reroute near Hormuz",
  "source": "Reuters",
  "region": "Middle East",
  "tags": ["tanker", "reroute"],
  "note": "Two tankers changed route",
  "confirmed": true,
  "workspace_ref": "Top News > Energy",
  "created_at": "2026-04-14T08:31:00Z",
  "updated_at": "2026-04-14T08:31:00Z"
}
```

### 3.4 AlertRecord
```json
{
  "alert_id": "alt_0001",
  "type": "threshold_cross",
  "metric_key": "brent_m1_m2_spread",
  "direction": "up",
  "threshold": 1.5,
  "current_value": 1.63,
  "triggered_at": "2026-04-14T09:11:00Z",
  "acknowledged": false
}
```

### 3.5 SystemStatus
```json
{
  "session_status": "connected",
  "last_success_update": "2026-04-14T09:10:00Z",
  "last_history_backfill": "2026-04-14T09:05:00Z",
  "active_subscriptions": 24,
  "stale_metrics": ["us10y"],
  "last_event_update": "2026-04-14T08:31:00Z",
  "session_reason": null,
  "data_source_mode": "desktop"
}
```

## 4. Endpoint Contract

### 4.1 GET `/health`
- 作用：服务健康探针。
- 200 响应：
```json
{
  "status": "ok",
  "service": "himpact-api",
  "time": "2026-04-14T09:12:00Z"
}
```

### 4.2 GET `/metrics/latest`
- Query（可选）：`panel`, `metric_keys`（逗号分隔）
- 200 响应：
```json
{
  "items": [
    {
      "metric_key": "brent_m1",
      "display_name": "Brent M1",
      "value": 87.23,
      "unit": "USD/bbl",
      "as_of": "2026-04-14T09:10:00Z",
      "status": "ok",
      "source": "lseg_workspace",
      "stale_seconds": 0
    }
  ],
  "request_id": "req_20260414_0010"
}
```

### 4.3 GET `/metrics/history?window=1D|5D|20D`
- Query（必填）：`window`
- Query（可选）：`metric_keys`
- 200 响应：
```json
{
  "window": "5D",
  "items": [
    {
      "metric_key": "brent_m1",
      "window": "5D",
      "abs_change": 1.2,
      "pct_change": 1.39,
      "as_of": "2026-04-14T09:10:00Z"
    }
  ],
  "request_id": "req_20260414_0011"
}
```

### 4.4 GET `/status`
- Query（可选）：`refresh=true|false`（默认 `true`，为 `false` 时仅返回当前内存状态，不额外触发取数）
- 200 响应：`SystemStatus`

### 4.5 GET `/events`
- Query（可选）：`category`, `confirmed`, `q`, `limit`, `offset`, `sort=event_time_desc|event_time_asc`
- 200 响应：
```json
{
  "items": [],
  "total": 0,
  "request_id": "req_20260414_0012"
}
```

### 4.6 POST `/events`
- 请求体：
```json
{
  "event_time": "2026-04-14T08:30:00Z",
  "category": "Shipping",
  "title": "Tanker reroute near Hormuz",
  "source": "Reuters",
  "region": "Middle East",
  "tags": ["tanker", "reroute"],
  "note": "Two tankers changed route",
  "confirmed": true,
  "workspace_ref": "Top News > Energy"
}
```
- 校验规则：`event_time/category/title/source` 必填。
- 201 响应：返回完整 `EventRecord`。

### 4.7 PATCH `/events/{event_id}`
- 作用：更新事件字段（note/confirmed/tags/title/source/region/workspace_ref）。
- 200 响应：返回更新后的 `EventRecord`。

### 4.8 GET `/alerts/active`
- Query（可选）：`metric_key`, `type`
- 200 响应：
```json
{
  "items": [],
  "request_id": "req_20260414_0013"
}
```

### 4.9 POST `/alerts/{alert_id}/ack`
- 作用：确认告警，避免重复打扰。
- 200 响应：
```json
{
  "alert_id": "alt_0001",
  "acknowledged": true,
  "acknowledged_at": "2026-04-14T09:13:00Z"
}
```

## 5. 状态与枚举
- `session_status`：`connected | degraded | disconnected`
- `metric.status`：`ok | stale | unentitled | error`
- `alert.type`：`threshold_cross | stale_data | connection_error`
- `alert.direction`：`up | down | na`
- `event.category`：
  - `Shipping`
  - `Insurance`
  - `Mines / chokepoint`
  - `Refinery outage`
  - `Product shortage`
  - `IEA`
  - `SPR`
  - `Sanctions`
  - `Escort / military`
  - `Ceasefire / talks`
  - `Asia buying`
  - `Alternative barrels`

## 5.1 v1.0 RC 指标键（面板1~4）
- 面板1：`brent_m1`, `brent_m2`, `wti_m1`, `wti_m2`, `brent_m1_m2_spread`, `wti_m1_m2_spread`, `brent_wti_spread`
- 面板2：`diesel_proxy`, `gasoline_proxy`, `diesel_crack`, `gasoline_crack`
- 面板3：`dxy`, `us2y`, `us10y`, `gold`
- 面板4：`btcusd`, `es_fut`, `nq_fut`

## 6. 验证与兼容规则
- 前端仅消费本文件声明字段。
- 后端新增字段必须“向后兼容”（只增不删），并更新本契约版本。
- 删除或重命名字段需要一次版本升级（如 `/api/v2`）。

## 7. 与 Agent 职责的关系
- Frontend Agent：严格按此契约渲染与处理空值/状态。
- Backend Agent：保证返回结构与校验规则一致。
- LSEG Workspace Agent：保证 `source/status` 语义与连接状态一致。
- Integration/QA Agent：以本文件作为契约测试基线。

## 8. 当前假设
- 鉴权在 v1 不作为强制项（默认本地单机环境）。
- `metric_key` 字典以后续 `docs/specs/ric-mapping-registry.md` 为准。
