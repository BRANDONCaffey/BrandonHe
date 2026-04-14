# LSEG Workspace Agent Handoff (v1.0 RC1)

## 已完成
- 保持运行策略：Desktop Session 默认，Platform Session 可选。
- RC 候选 RIC 映射已落地到台账（面板1~4）。
- 与后端配置默认值对齐，避免文档/运行时漂移。

## 交付物
- `docs/specs/ric-mapping-registry.md`
- `docs/env-setup.md`

## 依赖与约束
- entitlement 结果高度依赖账户权限与产品订阅。
- 若 Desktop 不可用，可切换 Platform；但 Platform 受配额与 OAuth 配置影响。

## 未完成/风险
- 面板2~4 多个指标仍为 `fallback`，需实测转 `active/fallback` 最终态。
- 尚未产出完整的 30 分钟 live 连接稳定性证据。
