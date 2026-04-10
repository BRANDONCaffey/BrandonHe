# AI Info Collection 使用指南（最新版）

## 1. 这是什么

这是一个“采集 -> 入库 -> 归并 -> 审查”的本地可运行系统，支持：
- 离线模式：用本地 JSONL 快速跑通主流程。
- 在线模式：抓取内置官方源（RSS/Web）后自动入库与归并。

## 2. 环境准备

- Python 3.11+（建议）
- 在仓库根目录执行命令
- 通用前缀：`PYTHONPATH=src`

在线抓取可选依赖（仅在线模式需要）：

```bash
python3 -m pip install "scrapling[fetchers]>=0.3.0"
```

## 3. 一键启动（推荐）

### 3.1 离线先跑通

```bash
PYTHONPATH=src python3 -m ai_info_collection.cli --db-path ./data.db start --mode offline
```

如果你遇到旧运行锁（如 `concurrent_run_blocked`），直接用：

```bash
PYTHONPATH=src python3 -m ai_info_collection.cli --db-path ./data.db start --mode offline --force-new-db
```

这会自动切到一个时间戳新库，例如 `data.offline.20260410113000.db`，避免被旧库状态阻断。

### 3.2 在线采集模式（有网时）

```bash
PYTHONPATH=src python3 -m ai_info_collection.cli --db-path ./data.db start --mode online --source-limit 5
```

在线模式会自动：
1. 写入官方源种子（`official-ai`，幂等）
2. 执行主流程（抓取 -> 入库 -> 归并）
3. 打印抓取日志

## 4. 输出怎么看

每次 `start` 结束会看到两段核心输出：
- `== Start ==`：本次运行摘要（`run_id/status/fetch/ingest/merge`）
- `== Recent Fetch Logs ==`：最近抓取日志（来源、成功/失败、时间）

重点字段：
- `status=success|partial_success|failed`
- `status_reason`：失败/拦截原因
- `fetch_success/fetch_failed`
- `ingest_success/ingest_failed`

## 5. 常用查看命令

```bash
PYTHONPATH=src python3 -m ai_info_collection.cli --db-path ./data.db recent-fetch-runs --limit 10
PYTHONPATH=src python3 -m ai_info_collection.cli --db-path ./data.db recent-events --limit 10
PYTHONPATH=src python3 -m ai_info_collection.cli --db-path ./data.db source-health
PYTHONPATH=src python3 -m ai_info_collection.cli --db-path ./data.db review
```

## 6. 本地 UI（离线可开）

```bash
PYTHONPATH=src python3 -m ai_info_collection.cli --db-path ./data.db ui --host 127.0.0.1 --port 8765 --offline
```

浏览器访问：`http://127.0.0.1:8765`

## 7. 常见问题

### Q1：在线模式全失败

常见原因是网络或 DNS 解析失败。先检查：
- 是否能访问目标域名
- 是否安装了 Scrapling 依赖

失败详情以 `recent-fetch-runs` 的 `error_message` 为准。

### Q2：为什么离线也被拦截

旧库中可能存在运行锁状态。使用 `--force-new-db` 可立即绕过。

## 8. 回归测试

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```
