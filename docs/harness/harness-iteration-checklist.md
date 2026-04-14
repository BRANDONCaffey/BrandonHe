# Himpact Harness Iteration Checklist

> 用途：每轮迭代都复制一份本清单，逐项打勾，确保 4 位 Agent 在正确时机使用正确 skill。

## 迭代信息
- 迭代编号：
- 目标版本：
- 时间窗口：
- 本轮主题（只选一个）：`数据可信度 / 连接稳定性 / 面板可用性 / 集成质量`
- 负责人（Harness Engineer）：

---

## Phase 0：范围冻结（Kickoff）

### Harness Engineer
- [ ] 明确本轮仅 1 个核心目标
- [ ] 定义验收标准（可测试、可量化）
- [ ] 标记 P0/P1/P2，不在本轮的需求移入 backlog

### Frontend Agent
- [ ] 使用 `github:github` 对齐本轮 UI 任务边界（Issue/PR）

### Backend Agent
- [ ] 使用 `github:github` 对齐接口与数据任务边界

### LSEG Workspace Agent
- [ ] 使用 `github:github` 对齐连接/RIC 映射任务边界

### Integration & QA Agent
- [ ] 使用 `github:github` 汇总现有 PR、阻塞与测试状态

---

## Phase 1：实现（Build）

### Frontend Agent
- [ ] 完成功能开发并本地自测
- [ ] 准备变更说明（影响面/风险）
- [ ] 使用 `github:yeet` 提交并推送 Draft PR

### Backend Agent
- [ ] 完成数据处理/接口开发并跑关键测试
- [ ] 更新数据规则（如 validation/cleaning 变更）
- [ ] 使用 `github:yeet` 提交并推送 Draft PR

### LSEG Workspace Agent
- [ ] 完成连接/重连/RIC 映射变更与本地验证
- [ ] 记录 entitlement 或映射限制
- [ ] 使用 `github:yeet` 提交并推送 Draft PR

### Integration & QA Agent
- [ ] 收集三个功能 Agent 的 PR 链接
- [ ] 建立本轮集成检查列表
- [ ] 必要时使用 `github:yeet` 提交测试基线补丁

---

## Phase 2：CI 与联调（Stabilize）

### 全体（遇到 CI 失败时）
- [ ] 使用 `github:gh-fix-ci` 拉取失败检查与日志
- [ ] 完成“失败归因 -> owner -> 修复 -> 复跑”闭环
- [ ] 在 PR 中记录根因与修复说明

### Integration & QA Agent
- [ ] 汇总失败项并维护单一缺陷清单
- [ ] 确认每个 blocker 都有 owner 与截止时间
- [ ] 输出当前联调状态（Green/Yellow/Red）

---

## Phase 3：评审闭环（Review Closure）

### Frontend Agent
- [ ] 使用 `github:gh-address-comments` 处理前端评审意见
- [ ] 每条评论给出处理结果（已改/解释/待定）

### Backend Agent
- [ ] 使用 `github:gh-address-comments` 处理后端评审意见
- [ ] 对契约变化补充兼容说明

### LSEG Workspace Agent
- [ ] 使用 `github:gh-address-comments` 处理连接/映射评审意见
- [ ] 对 RIC/entitlement 变更补充影响说明

### Integration & QA Agent
- [ ] 使用 `github:gh-address-comments` 收敛集成与测试评论
- [ ] 确认“无未回应的 blocker 评论”

---

## Phase 4：验收与发布决策（Go/No-Go）

### Integration & QA Agent（主导）
- [ ] 验收标准逐条核对（通过/豁免/失败）
- [ ] 输出发布建议：`Go` 或 `No-Go`
- [ ] 输出残余风险与上线观察项

### Harness Engineer
- [ ] 最终确认范围未漂移
- [ ] 若 `No-Go`：回写下一轮唯一核心目标
- [ ] 若 `Go`：进入发布与监控阶段

---

## 本轮必填产物（交付门禁）
- [ ] PR 列表（Frontend / Backend / LSEG / Integration）
- [ ] CI 结果截图或链接
- [ ] 缺陷清单（含 owner、优先级、截止时间）
- [ ] 验收结果表（通过/豁免/失败）
- [ ] 发布建议（Go/No-Go）

---

## 复盘（Retrospective）
- 做得好的：
- 做得不好的：
- 下轮改进动作（最多 3 条）：
- 是否需要调整 skill 使用顺序：

