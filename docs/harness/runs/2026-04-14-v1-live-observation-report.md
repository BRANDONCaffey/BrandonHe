# Himpact v1.0 Live Observation Report (30 min)

## 结论
- 观测窗口已完整执行（30 分钟，Desktop Session live）。
- 链路稳定性：`degraded` 为主，未出现持续断链。
- 面板2~4 entitlement 结果已可落账：部分 `active`，部分保持 `fallback`。

## 观测信息
- 开始时间（UTC）：2026-04-13T23:20:39Z
- 结束时间（UTC）：2026-04-13T23:50:48Z
- 持续时长：1808.368 秒（约 30 分钟）
- 采样间隔：10 秒
- 样本数：180
- 原始证据：[`docs/harness/runs/2026-04-14-v1-live-observation.json`](</Users/brandon/Documents/New project 2/docs/harness/runs/2026-04-14-v1-live-observation.json>)

## Runbook KPI 对照

| KPI | 实测值 | Runbook 阈值 | 结果 |
|---|---:|---:|---|
| 连接成功率（connected ratio） | 0.00% | >= 99% | 未达标 |
| degraded 比例 | 99.44% | 记录项 | 需关注 |
| disconnected 比例 | 0.56% | 越低越好 | 可接受 |
| stale 比例 | 0.22% | <= 5% | 通过 |
| unentitled 比例 | 0.00% | 记录项 | 通过 |
| API 错误率 | 0.00% | <= 2% | 通过 |
| 最大活动告警数 | 8 | 记录项 | 需关注 |
| 首屏可用时间 | ~0 秒 | 越低越好 | 通过 |

## 面板2~4 entitlement 观测结果

| metric_key | 面板 | 30m 状态统计 | 非空样本 | 结论 | 台账状态 |
|---|---:|---|---:|---|---|
| diesel_proxy | 2 | ok:179, stale:1 | 180/180 | 可用 | active |
| gasoline_proxy | 2 | ok:179, stale:1 | 180/180 | 可用 | active |
| dxy | 3 | ok:37, error:143 | 37/180 | 间歇可用 | active |
| us2y | 3 | error:180 | 0/180 | 当前不可用 | fallback |
| us10y | 3 | error:180 | 0/180 | 当前不可用 | fallback |
| gold | 3 | error:180 | 0/180 | 当前不可用 | fallback |
| btcusd | 4 | error:180 | 0/180 | 当前不可用（必选项） | fallback |
| es_fut | 4 | ok:179, stale:1 | 180/180 | 可用 | active |
| nq_fut | 4 | ok:179, stale:1 | 180/180 | 可用 | active |

## 关键发现
1. Live 数据链路稳定，但整体保持 `degraded`，说明“可连通 + 部分指标不可用”是当前常态。
2. 面板2（diesel/gasoline）和面板4（ES/NQ）可用性良好。
3. 面板3中的 DXY 仅间歇可用，US2Y/US10Y/Gold 在该账户下持续不可用。
4. BTCUSD（v1 必选）在观测窗口内持续不可用，直接影响正式 v1.0 发布。

## 建议动作
1. 先处理 `btcusd`、`us2y`、`us10y`、`gold` 的 RIC/entitlement 复核与替代策略。
2. 针对 DXY 增加降级说明（间歇可用）并监控其 error 比例。
3. 在下一轮观测中加入“RIC 替代候选”A/B 验证，目标是把会话从长期 `degraded` 收敛到 `connected`。
