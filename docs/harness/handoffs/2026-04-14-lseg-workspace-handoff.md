# LSEG Workspace Agent Handoff (M1)

## 已完成
- 将连接策略从 Desktop Session 切换为 Platform Session（App Key/OAuth）
- 支持两种 OAuth 认证输入：
  - `username + password`
  - `client_id + client_secret`
- 提供认证错误语义：
  - `missing_app_key`
  - `missing_oauth_credentials`
  - `invalid_session_name`
  - `platform_session_open_failed:*`
- 面板1 RIC 候选落地并可配置：
  - Brent M1/M2
  - WTI M1/M2

## 交付物
- `apps/api/lseg_client.py`
- `apps/api/config.py`
- `docs/env-setup.md`
- `docs/specs/ric-mapping-registry.md`

## 依赖与约束
- 必须由外部注入有效 App Key/OAuth 凭证
- 不在仓库存储任何明文凭证

## 未完成/风险
- 尚未拿到你的真实凭证做联调实证
- entitlement 结果仍需基于真实账户确认并回填台账
