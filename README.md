# AI Info Collection

最小可运行的 AI 信息采集与归并系统（支持离线导入与在线抓取）。

## 快速开始（二选一）

```bash
# 离线模式（固定 sample.jsonl）
PYTHONPATH=src python3 -m ai_info_collection.cli --db-path ./data.db start --mode offline

# 如果当前 data.db 有历史锁，使用全新数据库一键跑通
PYTHONPATH=src python3 -m ai_info_collection.cli --db-path ./data.db start --mode offline --force-new-db

# 在线模式（自动写入官方源种子，然后抓取->导入->归并）
PYTHONPATH=src python3 -m ai_info_collection.cli --db-path ./data.db start --mode online --source-limit 5
```

运行结束后会自动输出：
- 本次运行摘要（run_id/status/fetch/ingest/merge）
- 最近抓取日志（`fetch_runs`）

## 常用命令

```bash
PYTHONPATH=src python3 -m ai_info_collection.cli --db-path ./data.db recent-fetch-runs --limit 10
PYTHONPATH=src python3 -m ai_info_collection.cli --db-path ./data.db recent-events --limit 10
PYTHONPATH=src python3 -m ai_info_collection.cli --db-path ./data.db review
PYTHONPATH=src python3 -m ai_info_collection.cli --db-path ./data.db ui --host 127.0.0.1 --port 8765 --offline
```

## 测试

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## 说明

- `start` 是统一入口：
  - `--mode offline`：离线回放 `sample.jsonl`
  - `--mode online`：在线抓取（内置 `official-ai` 源）
  - 不传 `--mode`：终端一次交互选择
  - `--force-new-db`：仅离线模式有效，用时间戳新库规避旧锁状态
- 在线抓取依赖网络与 DNS；若环境不可解析域名，在线模式会失败并在抓取日志中记录错误原因。
- 详细中文使用手册见 [docs/UsageGuide.zh-CN.md](docs/UsageGuide.zh-CN.md)。
