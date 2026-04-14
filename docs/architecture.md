# Himpact Architecture (v1.0 RC)

## 1. 目标
Himpact v1.0 RC 采用本地单机架构：默认依赖 LSEG Desktop Session 获取市场数据（可选切换 Platform Session），后端完成标准化与告警，前端负责六面板展示与事件录入。

## 2. 架构原则
- 本地优先：不做 server-side 共享抓取。
- 客观优先：只输出原始值、变化率、价差、状态和阈值告警。
- 契约优先：前后端以 [`docs/specs/api-contract.md`](</Users/brandon/Documents/New project 2/docs/specs/api-contract.md>) 为唯一接口真相源。
- 质量优先：数据清洗、RIC 映射、测试矩阵和发布门禁必须独立成文。

## 3. 系统分层
1. `Workspace Layer`
- 由 LSEG Workspace Agent 负责 Session 建连（Desktop 优先，Platform 可选）、健康检查、订阅管理、RIC 映射验证。

2. `Data Layer`
- 由 Backend Agent 负责接收原始流和快照，做 validation/cleaning、派生指标计算、历史窗口聚合、状态归一化。

3. `Application Layer`
- 提供本地 API：健康状态、最新指标、历史变化、事件日志、活动告警。

4. `Presentation Layer`
- 由 Frontend Agent 负责六面板 UI、告警展示、系统状态和事件录入。

5. `Quality Layer`
- 由 Integration & QA Agent 负责契约测试、异常链路测试、发布门禁和 Go/No-Go。

## 4. 核心数据流
1. Session 建连成功后订阅 v1 必选指标。
2. 原始数据进入后端采集器，按 [`docs/specs/data-quality-spec.md`](</Users/brandon/Documents/New project 2/docs/specs/data-quality-spec.md>) 执行 schema 校验、去重、乱序处理和异常标记。
3. 后端生成：
- `latest` 实时值
- `history` 1D/5D/20D 变化
- `derived metrics` 如 spread/crack
- `alerts` 阈值、stale、连接异常
4. 前端按 [`docs/specs/api-contract.md`](</Users/brandon/Documents/New project 2/docs/specs/api-contract.md>) 拉取和展示。
   - 面板1：原油主屏
   - 面板2：成品油传导
   - 面板3：宏观价格传导
   - 面板4：风险资产响应
   - 面板5：事件检查板
   - 面板6：系统状态
5. 用户手工录入事件，后端持久化到本地存储并回显到事件检查板。

## 5. 模块边界
- LSEG Workspace Agent
只负责连接、RIC、entitlement、重连和源数据语义。

- Backend Agent
只负责清洗、聚合、派生、告警、事件存储和 API 输出。

- Frontend Agent
只负责展示、交互、告警确认和文案纪律。

- Integration & QA Agent
只负责验证、回归、缺陷归因和发布裁决。

## 6. 存储与状态
- 配置与事件日志：SQLite
- 历史缓存：Parquet/CSV
- 会话状态：内存态 + `/status` 对外暴露
- RIC 台账：[`docs/specs/ric-mapping-registry.md`](</Users/brandon/Documents/New project 2/docs/specs/ric-mapping-registry.md>)

## 7. 关键失败模式
- Desktop 未启动/未登录，或 Platform Session 认证失败（App Key/OAuth）
- entitlement 不足
- RIC 映射失效
- 数据停更导致 stale
- 历史回补失败

以上失败都不能让 UI 静默失败，必须通过状态字段和告警显式暴露。

## 8. 文档索引
- 角色说明：`agents/`
- Harness 协作：[`docs/harness/`](</Users/brandon/Documents/New project 2/docs/harness>)
- 技术规范：[`docs/specs/`](</Users/brandon/Documents/New project 2/docs/specs>)
- 质量门禁：[`docs/quality/`](</Users/brandon/Documents/New project 2/docs/quality>)
