# ADR 0001: Local-First Architecture

## Status
Accepted

## Date
2026-04-14

## Context
Himpact 依赖 LSEG Workspace Desktop Session 获取市场数据。根据当前产品与许可边界，Workspace 桌面会话要求本机运行、个人许可使用，并不适合 server-side 共享部署。

项目目标是尽快交付一个可运行的 MVP，用于客观监控原油、成品油、宏观、风险资产、事件日志和系统状态，而不是构建多用户平台或独立新闻系统。

## Decision
采用本地优先（local-first）架构：
- Workspace 连接、数据获取、前后端运行都默认在同一台机器上完成。
- 不建设共享后端或远程数据采集服务。
- 新闻继续留在 Workspace 原生产品中，Himpact 只记录手工事件和客观市场数据。

## Consequences

### Positive
- 与 LSEG Workspace 许可边界一致。
- 架构更简单，MVP 交付速度更快。
- 故障面更小，便于定位连接、RIC、数据质量问题。
- 更适合单用户高频监控工作流。

### Negative
- 不支持团队共享部署。
- 无法直接提供跨机器集中管理。
- 后续若扩展为多人协作产品，需要重构部署与权限模型。

## Follow-up
- 用 [`docs/specs/ric-mapping-registry.md`](</Users/brandon/Documents/New project 2/docs/specs/ric-mapping-registry.md>) 管理指标映射与 entitlement。
- 用 [`docs/quality/release-runbook.md`](</Users/brandon/Documents/New project 2/docs/quality/release-runbook.md>) 约束发布与回滚。
- 后续若要支持多用户，必须先新增新的 ADR，不得直接在 v1 上演进成 server-side 方案。
