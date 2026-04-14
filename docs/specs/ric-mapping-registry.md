# Himpact RIC Mapping Registry（v1）

## 1. 目标（结论先行）
维护 `metric_key -> RIC -> entitlement -> last_verified_at` 可追溯台账，作为 LSEG 对接唯一登记源。

## 2. 使用规则
- 本表是“登记台账”，不是运行时代码。
- 任一映射变更必须更新 `last_verified_at` 与 `verification_source`。
- 不确定映射必须标记 `pending`，禁止直接上线。

## 3. 字段定义
- `metric_key`：系统内部唯一指标键。
- `panel`：所属面板（1~6）。
- `display_name`：展示名。
- `ric`：LSEG RIC。
- `entitlement_required`：`yes | no | unknown`。
- `status`：`active | fallback | pending | deprecated`。
- `verification_source`：验证来源（LSEG Developers/Learning Centre/Workspace 实测）。
- `last_verified_at`：最后验证时间（UTC ISO8601）。
- `owner`：默认 `lseg-workspace-agent`。
- `notes`：限制、替代方案、风险说明。

## 4. Registry 表（初始模板）

| metric_key | panel | display_name | ric | entitlement_required | status | verification_source | last_verified_at | owner | notes |
|---|---|---|---|---|---|---|---|---|---|
| brent_m1 | 1 | Brent M1 | LCOc1 | unknown | fallback | config-default | 2026-04-14T00:00:00Z | lseg-workspace-agent | 默认候选，需本机 entitlement 最终确认 |
| brent_m2 | 1 | Brent M2 | LCOc2 | unknown | fallback | config-default | 2026-04-14T00:00:00Z | lseg-workspace-agent | 默认候选，需本机 entitlement 最终确认 |
| brent_m1_m2_spread | 1 | Brent M1-M2 | derived | no | active | internal-derived | 2026-04-14T00:00:00Z | backend-agent | 由 brent_m1/brent_m2 派生 |
| wti_m1 | 1 | WTI M1 | CLc1 | unknown | fallback | config-default | 2026-04-14T00:00:00Z | lseg-workspace-agent | 默认候选，需本机 entitlement 最终确认 |
| wti_m2 | 1 | WTI M2 | CLc2 | unknown | fallback | config-default | 2026-04-14T00:00:00Z | lseg-workspace-agent | 默认候选，需本机 entitlement 最终确认 |
| wti_m1_m2_spread | 1 | WTI M1-M2 | derived | no | active | internal-derived | 2026-04-14T00:00:00Z | backend-agent | 由 wti_m1/wti_m2 派生 |
| brent_wti_spread | 1 | Brent-WTI Spread | derived | no | active | internal-derived | 2026-04-14T00:00:00Z | backend-agent | 由 brent_m1/wti_m1 派生 |
| diesel_proxy | 2 | Diesel Proxy | HOc1 | yes | active | workspace-live-remediation | 2026-04-14T00:06:54Z | lseg-workspace-agent | 修复后10m复测：60/60 ok；运行时换算 cents/gal -> USD/bbl |
| gasoline_proxy | 2 | Gasoline Proxy | RBc1 | yes | active | workspace-live-remediation | 2026-04-14T00:06:54Z | lseg-workspace-agent | 修复后10m复测：60/60 ok；运行时换算 cents/gal -> USD/bbl |
| diesel_crack | 2 | Diesel Crack | derived | no | active | internal-derived | 2026-04-14T00:00:00Z | backend-agent | diesel_proxy - brent_m1 |
| gasoline_crack | 2 | Gasoline Crack | derived | no | active | internal-derived | 2026-04-14T00:00:00Z | backend-agent | gasoline_proxy - brent_m1 |
| dxy | 3 | DXY | .DXY | yes | active | workspace-live-remediation | 2026-04-14T00:06:54Z | lseg-workspace-agent | 修复后10m复测：60/60 ok |
| us2y | 3 | US 2Y | US2YT=RR | yes | active | workspace-live-remediation | 2026-04-14T00:06:54Z | lseg-workspace-agent | 修复后10m复测：60/60 ok；问题根因是 TRDPRC_1 空值，CF_LAST 可用 |
| us10y | 3 | US 10Y | US10YT=RR | yes | active | workspace-live-remediation | 2026-04-14T00:06:54Z | lseg-workspace-agent | 修复后10m复测：60/60 ok；问题根因是 TRDPRC_1 空值，CF_LAST 可用 |
| gold | 3 | Gold | XAU= | yes | active | workspace-live-remediation | 2026-04-14T00:06:54Z | lseg-workspace-agent | 修复后10m复测：60/60 ok；问题根因是 TRDPRC_1 空值，CF_LAST 可用 |
| btcusd | 4 | BTCUSD | BTC= | yes | active | workspace-live-remediation | 2026-04-14T00:06:54Z | lseg-workspace-agent | 修复后10m复测：60/60 ok；问题根因是 TRDPRC_1 空值，CF_LAST 可用（必选项已恢复） |
| es_fut | 4 | ES Future | ESc1 | yes | active | workspace-live-remediation | 2026-04-14T00:06:54Z | lseg-workspace-agent | 修复后10m复测：60/60 ok |
| nq_fut | 4 | NQ Future | NQc1 | yes | active | workspace-live-remediation | 2026-04-14T00:06:54Z | lseg-workspace-agent | 修复后10m复测：60/60 ok |

## 5. 变更流程（强制）
1. LSEG Workspace Agent 提交映射变更 PR。
2. Backend Agent 确认单位/派生依赖未破坏。
3. Integration/QA Agent 验证契约与回归。
4. 更新 `last_verified_at` 并记录证据链接。

## 6. 最低验收门槛
- MVP 必选指标均非 `pending`（至少具备 active 或明确 fallback）。
- 每条 active 映射都有 `last_verified_at`。
- entitlement 不足项有替代或占位策略说明。
