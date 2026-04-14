# Himpact v1.0 RC Iteration Checklist Record

## 迭代信息
- 迭代编号：v1.0-RC1
- 目标版本：1.0.0-rc1
- 时间窗口：2026-04-14
- 本轮主题：面板可用性 + 连接状态语义收口
- 负责人（Harness Engineer）：Codex + Brandon

---

## Phase 0：范围冻结（Kickoff）

### Harness Engineer
- [x] 明确本轮核心目标（v1.0 RC：补齐面板2~4 + 保持 Live First）
- [x] 以 `docs/specs/api-contract.md` 锁定接口范围
- [x] 将未验证的生产门禁保留在 backlog P0

### Frontend Agent
- [x] 确认 UI 扩展范围（面板2~4 + 历史变化 + 状态原因）

### Backend Agent
- [x] 确认指标注册扩展与状态语义（`connected/degraded/disconnected`）

### LSEG Workspace Agent
- [x] 确认 RC 候选 RIC 与 entitlement 风险标记

### Integration & QA Agent
- [x] 确认 RC 用例基线与测试扩展范围

---

## Phase 1：实现（Build）

### Frontend Agent
- [x] 面板2/3/4 渲染落地
- [x] 1D/5D/20D 变化展示落地
- [x] 状态原因显示（ok/stale/unentitled/error）

### Backend Agent
- [x] 指标注册扩展到面板2/3/4
- [x] crack 派生指标落地
- [x] Session `degraded` 语义落地
- [x] `SystemStatus` 增加 `session_reason` 与 `data_source_mode`

### LSEG Workspace Agent
- [x] 更新 RC 候选映射台账
- [x] 保持 Desktop 默认 + Platform 可选
- [x] 标注 entitlement 待实测项

### Integration & QA Agent
- [x] 扩展 API 单测覆盖到面板1~4
- [x] 运行自动化回归（6 passed）

---

## Phase 2：CI 与联调（Stabilize）

### 全体
- [x] 本地 `pytest` 通过
- [x] 无接口破坏性变更
- [x] 文档与代码同步更新

### Integration & QA Agent
- [x] 联调状态：`Yellow`（代码达到 RC，待 Live 长稳证据）
- [x] blocker 责任链明确（entitlement 与 30 分钟观测）

---

## Phase 3：评审闭环（Review Closure）

### Frontend Agent
- [x] 与 API 契约字段对齐

### Backend Agent
- [x] 兼容性检查（新增字段为向后兼容）

### LSEG Workspace Agent
- [x] RIC registry 与运行时默认值一致

### Integration & QA Agent
- [x] 形成 RC 版 Go/No-Go 报告

---

## Phase 4：验收与发布决策（Go/No-Go）

### Integration & QA Agent（主导）
- [x] 验收标准逐条对齐到 RC 范围
- [x] 发布建议：`Go (RC 内测)` / `No-Go (生产)`
- [x] 输出残余风险与观察项

### Harness Engineer
- [x] 确认本轮范围未漂移
- [x] 将生产门禁回写 backlog P0

---

## 本轮必填产物（交付门禁）
- [x] 变更文件清单
- [x] 测试结果（`pytest: 6 passed`）
- [x] RC Go/No-Go 报告
- [x] 四个 Agent handoff 文档
- [x] backlog 更新与下一步顺序

---

## 复盘（Retrospective）
- 做得好的：代码与契约同轮收口，RC 范围清晰。
- 做得不好的：真实 entitlement 与长稳观测还没形成证据闭环。
- 下轮改进动作：
  1. 当天完成 30 分钟 live 观测并归档。
  2. 将面板2~4 entitlement 结果从 fallback 收敛到 active/fallback 最终态。
  3. 输出正式生产 Go/No-Go（非 RC 内测）。
