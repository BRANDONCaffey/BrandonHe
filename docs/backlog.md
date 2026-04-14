# Himpact Backlog

## 当前结论（v1.0 正式门禁）
- BTCUSD + US2Y/US10Y/Gold 可用性已修复并完成 10 分钟 live 复测。
- 正式发布结论暂维持 `No-Go`，待新一轮 30 分钟门禁观测更新。
- 阻断点收敛为“门禁时长观测与正式裁决更新”。

## 使用规则
- 每个条目必须有优先级、owner、验收口径。
- P0 是阻断正式发布项；P1 是重要增强；P2 是后续优化。

## P0（正式 v1.0 阻断项）

### BG-V1-001 修复 BTCUSD 必选链路（已完成）
- Owner: LSEG Workspace Agent + Backend Agent
- 描述: 让 `btcusd` 在当前账户下稳定可用（或提供通过验收的替代映射）。
- 验收:
- 30 分钟窗口 `btcusd` 非空样本 >=95%
- 指标状态以 `ok/stale` 为主，不再长期 `error`
- `ric-mapping-registry` 更新并标记 `active` 或带批准的 fallback

### BG-V1-002 修复宏观链路（US2Y/US10Y/Gold）（已完成）
- Owner: LSEG Workspace Agent
- 描述: 复核 RIC 与 entitlement，完成可用映射或正式替代方案。
- 验收:
- `us2y/us10y/gold` 至少达成“可用或有批准替代”
- 台账包含 `last_verified_at` 与证据备注

### BG-V1-003 收敛会话状态到 connected 主导
- Owner: LSEG Workspace Agent + Integration & QA Agent
- 描述: 优化连接与订阅策略，降低长期 `degraded`。
- 验收:
- 新一轮 30 分钟观测 `connected ratio >= 99%`（按 runbook）
- API 错误率和 stale 比例继续满足门槛

### BG-V1-004 正式发布复测与裁决
- Owner: Integration & QA Agent
- 描述: 在 BG-V1-001~003 完成后，执行复测并输出最终发布裁决。
- 验收:
- 新一轮 live 观测报告归档
- 正式 Go/No-Go 报告更新为 `Go` 或附阻断说明

## P1（正式版后建议）

### BG-RC-004 历史窗口数据质量增强
- Owner: Backend Agent
- 描述: 增强 1D/5D/20D 的基线选择与异常值审计字段。

### BG-RC-005 前端可视化可读性提升
- Owner: Frontend Agent
- 描述: 在保持客观语义前提下，优化表格密度与状态提示。

## P2（后续增强）

### BG-RC-006 自动化发布巡检
- Owner: Integration & QA Agent
- 描述: 将 release runbook 的核心检查转为固定自动化任务。

### BG-RC-007 平台模式配额与限流优化
- Owner: LSEG Workspace Agent + Backend Agent
- 描述: 针对 Platform Session 增加配额保护和重试节奏控制。

## 已完成（本轮）
- [x] BG-RC-001：30 分钟 Live 稳定性观测并归档
- [x] BG-RC-002：面板2~4 entitlement 实测并回填台账
- [x] BG-RC-003：基于新证据输出正式 v1.0 Go/No-Go
- [x] BG-V1-001：BTCUSD 必选链路恢复（10分钟复测 60/60 ok）
- [x] BG-V1-002：US2Y/US10Y/Gold 可用性恢复（10分钟复测 60/60 ok）

## 当前默认执行顺序
1. BG-V1-003
2. BG-V1-004
