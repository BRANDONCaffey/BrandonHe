# Himpact v1.0 Formal Go/No-Go Report

## 最终结论
- 正式 v1.0 生产发布：`No-Go`
- RC/内测环境：`Go（带风险）`

> 说明：本报告基于 2026-04-13T23:20:39Z ~ 23:50:48Z 的首轮 30 分钟观测。  
> 2026-04-14 已完成 BTCUSD/US2Y/US10Y/Gold 修复（见 `2026-04-14-v1-ric-remediation-report.md`），需再执行一轮 30 分钟门禁观测后更新正式裁决。

## 证据来源
- 30 分钟 live 观测报告：[`docs/harness/runs/2026-04-14-v1-live-observation-report.md`](</Users/brandon/Documents/New project 2/docs/harness/runs/2026-04-14-v1-live-observation-report.md>)
- 原始采样数据：[`docs/harness/runs/2026-04-14-v1-live-observation.json`](</Users/brandon/Documents/New project 2/docs/harness/runs/2026-04-14-v1-live-observation.json>)
- RIC 台账：[`docs/specs/ric-mapping-registry.md`](</Users/brandon/Documents/New project 2/docs/specs/ric-mapping-registry.md>)

## Go/No-Go 判定依据

### 已通过
1. API 错误率 0.00%，满足 runbook 阈值（<=2%）。
2. stale 比例 0.22%，满足 runbook 阈值（<=5%）。
3. 面板2关键指标（diesel/gasoline）可用，ES/NQ 可用。
4. 文档与台账闭环完整（观测 -> 台账 -> 报告）。

### 未通过（阻断项）
1. `connected ratio` 为 0%，不满足 runbook 的连接成功率门槛（>=99%）。
2. BTCUSD（v1 必选）在 30 分钟窗口 `0/180` 非空，持续 `error`。
3. US2Y / US10Y / Gold 均 `0/180` 非空，面板3核心链路不完整。

## 风险清单（按严重度）
1. P0：必选指标 BTCUSD 不可用，导致风险资产面板主链路缺失。
2. P0：会话长期 `degraded`，生产可观测性与稳定性门槛未达标。
3. P1：宏观链路（US2Y/US10Y/Gold）持续不可用，影响面板3解释力。
4. P1：DXY 间歇可用（37/180），需要降级策略与替代 RIC。

## 进入正式 Go 的必要条件
1. BTCUSD 达到稳定可用（建议 >=95% 样本非空，且状态 `ok/stale`）。
2. 会话状态在观测窗口内以 `connected` 为主（达到 runbook 门槛）。
3. US2Y/US10Y/Gold 至少完成“可用或有明确替代”的闭环。
4. 再跑一次 30 分钟观测并复核通过。

## Owner 与下一步
- LSEG Workspace Agent：复核 `btcusd/us2y/us10y/gold` 的 RIC 与权限，并给出替代映射。
- Backend Agent：保持状态语义与降级逻辑稳定，补充 error 原因可读性。
- Frontend Agent：在不可用场景强化占位说明，避免误判。
- Integration & QA Agent：执行下一轮 30 分钟复测并输出最终发布裁决。
