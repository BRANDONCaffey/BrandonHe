# Himpact Release Runbook（v1）

## 1. 目标（结论先行）
定义发布前检查、发布执行、回滚与上线后监控，确保每次迭代可控上线、可快速止损。

## 2. 发布前检查（Pre-Release Checklist）

### 2.1 范围与文档
- [ ] 本轮目标与验收标准已冻结（参考 `docs/quality/mvp-acceptance-criteria.md`）。
- [ ] API 契约无破坏性变更（参考 `docs/specs/api-contract.md`）。
- [ ] RIC 映射台账已更新并验证时间戳有效。

### 2.2 质量门禁
- [ ] P0 测试全部通过（参考 `docs/quality/test-matrix.md`）。
- [ ] CI 全绿，或豁免项有审批记录。
- [ ] 无 blocker 级未关闭缺陷。

### 2.3 运维可见性
- [ ] `/health`、`/status` 可用。
- [ ] 错误码可追踪（含 request_id）。
- [ ] 告警规则已启用（stale/connection/threshold）。

## 3. 发布步骤（Release Steps）
1. Integration/QA Agent 汇总最终验收报告并给出 Go/No-Go。
2. Harness Engineer 确认本轮范围无漂移。
3. 合并发布 PR（保留变更日志与风险说明）。
4. 启动应用并执行发布后冒烟：
   - 连接状态
   - 面板 1 数据可见
   - 阈值告警可触发
   - 事件日志可写
5. 记录发布时间与版本标识。

## 4. 回滚策略（Rollback）

### 4.1 触发条件
- 核心链路不可用（无法连接、核心面板无数据）。
- 数据状态错误大面积出现（stale/unentitled/error 异常激增）。
- 业务纪律违规（出现主观判断文案）。

### 4.2 回滚步骤
1. 宣布 `No-Go/回滚`，冻结新变更合并。
2. 回退到上一个稳定版本（代码与配置同时回退）。
3. 验证回退后冒烟场景（连接、面板1、事件录入、告警）。
4. 发布事故记录：根因、影响、修复计划、负责人。

## 5. 上线后监控（Post-Release Monitoring）

### 5.1 关键监控指标
- 连接成功率（session connected ratio）
- 指标 stale 比例
- `unentitled` 发生率
- 告警触发数与误触发率
- API 错误率（按 error.code）
- 面板首屏可用时间

### 5.2 告警阈值（v1 建议）
- 连接成功率 < 99%（5 分钟窗口） -> 告警
- stale 比例 > 5%（5 分钟窗口） -> 告警
- API 错误率 > 2%（5 分钟窗口） -> 告警
- `RIC_NOT_FOUND` 连续出现 >= 3 次 -> 告警

## 6. 发布后 24 小时检查
- [ ] 核心指标连续可用。
- [ ] 无新增 blocker 缺陷。
- [ ] 告警噪声可控（误报率在可接受范围）。
- [ ] 记录下一轮改进项（最多 3 条）。

## 7. 角色分工
- Harness Engineer：发布总控与决策。
- Integration/QA Agent：质量门禁与发布报告 owner。
- LSEG Workspace Agent：连接稳定性与映射异常 owner。
- Backend Agent：API/告警/数据质量 owner。
- Frontend Agent：可用性与展示纪律 owner。
