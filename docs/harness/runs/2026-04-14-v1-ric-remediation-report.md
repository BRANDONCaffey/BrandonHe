# Himpact v1 RIC Remediation Report (BTCUSD / US2Y / US10Y / Gold)

## 结论
- `btcusd`（必选）已恢复可用。
- `us2y/us10y/gold` 已确认在当前账户可用。
- 本轮问题主因是取数字段选择（`TRDPRC_1` 单字段）而非纯 entitlement 缺失。

## 根因分析
- 旧实现只请求 `TRDPRC_1`，对以下 RIC 返回空值：`BTC=`, `US2YT=RR`, `US10YT=RR`, `XAU=`。
- 同一 RIC 在 `CF_LAST` 字段可返回有效价格，因此状态被误判为 `error`。

## 修复动作
1. 后端 LSEG 取数改为多字段回退：`TRDPRC_1 -> CF_LAST -> BID -> ASK -> VALUE`。
2. 数值转换增强：过滤 `NaN/Inf`，避免脏值进入 `ok` 状态。

## 代码变更
- [`apps/api/lseg_client.py`](</Users/brandon/Documents/New project 2/apps/api/lseg_client.py>)
- [`apps/api/config.py`](</Users/brandon/Documents/New project 2/apps/api/config.py>)

## 复测证据
- 复测窗口（UTC）：2026-04-13T23:56:54Z ~ 2026-04-14T00:06:54Z（10分钟）
- 样本：60（10秒间隔）
- 会话状态：`connected = 60/60`
- 关键指标状态：
  - `btcusd = ok 60/60`
  - `us2y = ok 60/60`
  - `us10y = ok 60/60`
  - `gold = ok 60/60`
- 原始证据：[`docs/harness/runs/2026-04-14-v1-ric-remediation-observation.json`](</Users/brandon/Documents/New project 2/docs/harness/runs/2026-04-14-v1-ric-remediation-observation.json>)

## 台账回填
- 已更新 [`docs/specs/ric-mapping-registry.md`](</Users/brandon/Documents/New project 2/docs/specs/ric-mapping-registry.md>)：
  - `btcusd/us2y/us10y/gold` 状态改为 `active`
  - `last_verified_at` 更新到 `2026-04-14T00:06:54Z`
  - `verification_source` 更新为 `workspace-live-remediation`

## 风险与后续
- 仍建议再跑一次 30 分钟正式门禁观测，以更新正式 v1.0 Go/No-Go。
