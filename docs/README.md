# Himpact Docs Index

## 目录说明
- [`architecture.md`](</Users/brandon/Documents/New project 2/docs/architecture.md>)
系统架构、模块边界、数据流、失败模式。

- [`env-setup.md`](</Users/brandon/Documents/New project 2/docs/env-setup.md>)
本机环境搭建、依赖安装、启动与健康检查。

- [`adr/`](</Users/brandon/Documents/New project 2/docs/adr>)
关键架构与产品决策记录。

- [`harness/`](</Users/brandon/Documents/New project 2/docs/harness>)
Harness Engineer 的迭代流程、skill 使用 SOP、执行清单。
  - 最新 RC 运行记录：[`harness/runs/2026-04-14-v1-rc-iteration-checklist.md`](</Users/brandon/Documents/New project 2/docs/harness/runs/2026-04-14-v1-rc-iteration-checklist.md>)
  - 最新 RC 发布建议：[`harness/runs/2026-04-14-v1-rc-go-no-go-report.md`](</Users/brandon/Documents/New project 2/docs/harness/runs/2026-04-14-v1-rc-go-no-go-report.md>)
  - v1 正式观测报告：[`harness/runs/2026-04-14-v1-live-observation-report.md`](</Users/brandon/Documents/New project 2/docs/harness/runs/2026-04-14-v1-live-observation-report.md>)
  - v1 正式发布裁决：[`harness/runs/2026-04-14-v1-go-no-go-report.md`](</Users/brandon/Documents/New project 2/docs/harness/runs/2026-04-14-v1-go-no-go-report.md>)
  - v1 RIC 修复报告：[`harness/runs/2026-04-14-v1-ric-remediation-report.md`](</Users/brandon/Documents/New project 2/docs/harness/runs/2026-04-14-v1-ric-remediation-report.md>)

- [`specs/`](</Users/brandon/Documents/New project 2/docs/specs>)
接口契约、数据质量规范、RIC 映射台账。

- [`quality/`](</Users/brandon/Documents/New project 2/docs/quality>)
MVP 验收标准、测试矩阵、发布 runbook。

- [`backlog.md`](</Users/brandon/Documents/New project 2/docs/backlog.md>)
当前执行优先级与 owner 分配。

## 推荐阅读顺序
1. [`architecture.md`](</Users/brandon/Documents/New project 2/docs/architecture.md>)
2. [`specs/api-contract.md`](</Users/brandon/Documents/New project 2/docs/specs/api-contract.md>)
3. [`specs/data-quality-spec.md`](</Users/brandon/Documents/New project 2/docs/specs/data-quality-spec.md>)
4. [`quality/mvp-acceptance-criteria.md`](</Users/brandon/Documents/New project 2/docs/quality/mvp-acceptance-criteria.md>)
5. [`harness/agent-skill-sop.md`](</Users/brandon/Documents/New project 2/docs/harness/agent-skill-sop.md>)

## Agent 入口
- 人类可读角色说明：[`../agents/`](</Users/brandon/Documents/New project 2/agents>)
- Anthropic 风格项目级 agent 入口：[`../.claude/agents/`](</Users/brandon/Documents/New project 2/.claude/agents>)

## 特殊助手
- PRD -> Harness 文档助手：[`../agents/prd-harness-doc-assistant-agent.md`](</Users/brandon/Documents/New project 2/agents/prd-harness-doc-assistant-agent.md>)
