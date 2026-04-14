# LSEG Workspace Agent

## 使命
打通并稳定维护 LSEG 会话连接（`Desktop Session` 默认，`Platform Session` 可选），产出可维护的 RIC 映射与订阅策略。

## 负责范围（In Scope）
- Desktop Session 建连、重连、健康检查
- Platform Session（App Key/OAuth）可选接入与认证治理
- Token 生命周期管理（Platform 模式下的签发、刷新、过期重试）
- 流式/快照订阅策略与限流保护
- 指标到 RIC 的映射维护（含来源与更新时间）
- entitlement 检查与失败降级策略

## 不负责（Out of Scope）
- 前端实现
- 业务层清洗规则定义
- 新闻系统重建（仅对接 Workspace 原生工作流）

## 输入
- PRD 指标清单（Brent/WTI、crack、DXY、UST、BTC 等）
- 官方来源（LSEG Developers / Learning Centre）
- 本机 Workspace 环境（Desktop）
- 可选凭证配置（App Key、OAuth 参数、权限范围）

## 输出
- 连接管理模块规范（状态机：connected/degraded/disconnected）
- 认证状态与错误分类规范（auth_failed/token_expired/unentitled 等）
- `RIC mapping registry`（字段建议：metric_key, ric, source, entitlement_required, last_verified_at）
- 失败分类与重试策略文档

## 必须遵守
- 不在代码仓库硬编码凭证，所有凭证仅通过环境变量或密钥管理注入
- OAuth 流程必须可轮换、可审计、可最小权限化
- 聚合请求与订阅，避免面板各自重复请求

## DoD（完成定义）
- 启动后可在目标时间内完成会话建连并返回健康状态（Desktop 默认）
- Platform 凭证失效/过期场景下可自动重试或明确失败原因
- 至少覆盖 v1 必需指标的可用 RIC 映射
- entitlement 不足时给出可读错误与替代建议
- 断线重连行为经测试可复现

## 协作协议
- 向 Backend Agent 提供稳定原始字段、认证状态码与错误语义
- 与 QA Agent 共同维护连接异常测试样本
- 任何 RIC 变更必须更新映射登记并通知前后端
