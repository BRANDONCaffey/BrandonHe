# Himpact Harness Engineer：Agent Skill 使用 SOP

## 结论（先看）
本项目统一采用 4 个 GitHub skills：
- `github:github`
- `github:gh-fix-ci`
- `github:yeet`
- `github:gh-address-comments`

并将其分配到 4 位 Agent 的固定工作流中，确保“开发 -> CI -> Review -> 发布”闭环。

## 全局规则（所有 Agent）
- 默认先用 `github:github` 做上下文对齐（仓库、PR、Issue、分支状态）。
- 任何 CI 失败优先走 `github:gh-fix-ci`，禁止凭感觉直接改。
- 需要发布变更时统一走 `github:yeet`，保证 commit/push/draft PR 规范化。
- 收到评审意见后统一走 `github:gh-address-comments` 做逐条闭环。

---

## 1) Frontend Agent SOP

### Skills 分配
- 主技能：`github:github`
- 次技能：`github:yeet`
- 触发型技能：`github:gh-fix-ci`、`github:gh-address-comments`

### 触发条件
- 开工前：需要确认当前 PR/Issue 范围、UI 任务边界。
- 提交前：前端改动已完成并通过本地检查。
- CI 挂掉：前端相关检查失败（build/lint/test）。
- 收到评论：PR 中出现前端改动相关 review comment。

### 命令节奏
1. `github:github`：拉取任务上下文并确认本轮目标。
2. 本地完成 UI 改动与自测。
3. `github:yeet`：提交、推送、创建/更新 Draft PR。
4. 若 CI 失败，`github:gh-fix-ci`：读日志 -> 定位 -> 修复 -> 复跑。
5. 若有 review 评论，`github:gh-address-comments`：逐条处理并回填说明。

### 交付物
- 前端变更 PR（含截图或录屏链接）
- 变更说明（影响面、风险点）
- 评论闭环记录（已处理/待确认）

---

## 2) Backend Agent SOP

### Skills 分配
- 主技能：`github:github`
- 次技能：`github:gh-fix-ci`
- 发布技能：`github:yeet`
- 评审闭环：`github:gh-address-comments`

### 触发条件
- 开工前：确认接口契约、Issue/PR 依赖关系。
- CI 失败：单元测试、契约测试、数据校验相关失败。
- 准备合并：后端改动完成并需发布 PR。
- 评审反馈：涉及 validation/cleaning/API 行为的评论。

### 命令节奏
1. `github:github`：确认后端任务与基线分支。
2. 本地完成数据与接口改动，先跑关键测试。
3. `github:yeet`：规范提交并推送 PR。
4. `github:gh-fix-ci`：处理 CI 失败（按日志逐项修复）。
5. `github:gh-address-comments`：处理评审意见并更新 PR 讨论。

### 交付物
- API/数据处理变更 PR
- CI 通过记录
- 数据质量规则更新说明（若有）

---

## 3) LSEG Workspace Agent SOP

### Skills 分配
- 主技能：`github:github`
- 次技能：`github:gh-fix-ci`
- 发布技能：`github:yeet`
- 评审闭环：`github:gh-address-comments`

### 触发条件
- 开工前：确认 RIC 映射、连接模块相关任务。
- CI 失败：连接测试、集成测试、mock/contract 失败。
- 准备发布：连接或映射改动需要进入 PR。
- 评论出现：涉及 entitlement、重连策略、RIC 变更评论。

### 命令节奏
1. `github:github`：确认当前连接模块任务与未决问题。
2. 本地验证连接逻辑、错误处理与映射更新。
3. `github:yeet`：提交并推送 PR（注明映射变更）。
4. `github:gh-fix-ci`：修复连接/集成相关 CI 问题。
5. `github:gh-address-comments`：回复并落实审查建议。

### 交付物
- 连接/映射变更 PR
- 映射变更说明（影响指标、回滚方式）
- CI 通过与已知限制清单

---

## 4) Integration & QA Agent SOP

### Skills 分配
- 主技能：`github:github`
- 主技能：`github:gh-fix-ci`
- 发布技能：`github:yeet`
- 评审闭环：`github:gh-address-comments`

### 触发条件
- 每轮联调开始：需要汇总 PR 状态与阻塞项。
- 任一检查失败：需要统一定位并分派 owner。
- 联调完成：需要生成集成 PR 或发布结论。
- 评审期：需要收敛跨 Agent 评论并追踪关闭。

### 命令节奏
1. `github:github`：汇总所有相关 PR/Issue/检查状态。
2. `github:gh-fix-ci`：按失败项归因并推动修复闭环。
3. 必要时 `github:yeet`：提交测试基线/修复补丁并更新 PR。
4. `github:gh-address-comments`：统一处理集成/测试类评论。
5. 输出 Go/No-Go 结论。

### 交付物
- 集成测试报告
- 缺陷归属清单（owner + 截止时间）
- 发布建议（Go/No-Go）

---

## 统一执行模板（每个 Agent 每轮都要填）
- 本轮目标：
- 使用的 skill：
- 触发原因：
- 执行结果：
- 产出链接（PR/Issue/CI）：
- 未解决风险：

## 默认优先级
1. `github:github`（对齐上下文）
2. `github:yeet`（规范发布）
3. `github:gh-fix-ci`（失败修复）
4. `github:gh-address-comments`（评审闭环）

