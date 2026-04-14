# Backend Agent Handoff (M1)

## 已完成
- 实现最小 API 契约：
  - `GET /api/v1/health`
  - `GET /api/v1/status`
  - `GET /api/v1/metrics/latest`
  - `GET /api/v1/metrics/history`
  - `GET/POST/PATCH /api/v1/events`
  - `GET /api/v1/alerts/active`
  - `POST /api/v1/alerts/{alert_id}/ack`
- 实现 SQLite 事件存储
- 实现数据状态透传：`ok/stale/unentitled/error`
- 实现告警最小闭环：`threshold_cross/stale_data/connection_error`

## 交付物
- `apps/api/*.py`
- `packages/core/himpact_core/*.py`
- `tests/test_api.py`

## 依赖与约束
- 依赖 Platform Session 凭证与 RIC 可用性
- 运行时不使用 mock 数据注入 metrics 链路

## 未完成/风险
- 真实凭证下未完成 30 分钟稳定性观测
- 生产级日志与指标埋点仍需补强
