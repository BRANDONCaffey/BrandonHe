# Backend Agent Handoff (v1.0 RC1)

## 已完成
- 指标注册从 M1 扩展到 RC（面板1~4）。
- 实现 diesel/gasoline proxy 的单位归一（cents/gal -> USD/bbl）。
- 新增派生指标：`diesel_crack`、`gasoline_crack`。
- Session 语义增强：支持 `degraded`。
- `/status` 增加：`session_reason`、`data_source_mode`。
- `GET /status` 改为全指标视角，不再只看面板1。

## 交付物
- `apps/api/config.py`
- `apps/api/metrics.py`
- `apps/api/state.py`
- `apps/api/alerts.py`
- `apps/api/main.py`
- `packages/core/himpact_core/schemas.py`

## 依赖与约束
- 运行时坚持 live-only，不回退 mock。
- 单位归一依赖代理 RIC 的行情字段语义稳定。

## 未完成/风险
- 面板2~4 entitlement 仍需账户实测确认。
- 长稳场景（30 分钟）证据尚未归档。
