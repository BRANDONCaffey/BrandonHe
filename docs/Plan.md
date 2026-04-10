# Plan

## 规划原则

- 先最小可行，再扩展
- 每一步都可验证
- 优先复用现有模式

## 计划模板

```md
Step 1:
预期产出：
验证方法：

Step 2:
预期产出：
验证方法：
```

## 风险模板

```md
风险：
影响：
缓解策略：
```

## Milestone 1 状态（worker）

- milestone status: completed (M1 最小补强，未扩展 M2)
- files changed:
  - src/ai_info_collection/models.py
  - src/ai_info_collection/meaning.py
  - tests/test_meaning_card.py
  - docs/Documentation.md
  - docs/Plan.md
- commands/results:
  - command: `PYTHONPATH=src python3 -m unittest discover -s tests -v`
    result: `通过（Ran 10 tests, OK）`
  - command: `PYTHONPATH=src python3 -m ai_info_collection.cli --db-path ./data.db review`
    result: `通过（退出码 0，空数据下无异常）`
  - command: `PYTHONPATH=src python3 -m ai_info_collection.cli --db-path ./data.db source-health`
    result: `通过（退出码 0，空数据下无异常）`
  - command: `PYTHONPATH=src python3 -m ai_info_collection.cli --db-path ./data.db recent-events`
    result: `通过（退出码 0，空数据下无异常）`
- decisions:
  - `framework_tags` 判定统一为“至少包含一个 `strip()` 后非空标签”。
  - 复用单一判定函数，保证 `build_meaning_card` 与 `validate` 一致。
  - 不修改 CLI 行为，不改 schema。
- known risks:
  - `MeaningCard` 在 M1 范围内的测试缺口已补齐（含 `why_it_matters`、`what_changed_now`、`what_changed_delta` 空白输入与 `validate` 状态一致性分支）。
  - 仅覆盖当前 `MeaningCard` 相关路径；其他潜在消费方若自行判定标签，可能仍存在不一致风险。
- exact next step:
  - Milestone 1 已完成；下一步进入 Milestone 2（`review` 质量闸门）范围确认与最小实现计划。

## Milestone 2 状态（worker）

- milestone status: completed (M2 review 质量闸门补齐，最小 diff)
- files changed:
  - src/ai_info_collection/storage.py
  - src/ai_info_collection/cli.py
  - tests/test_storage_and_cli.py
  - docs/Plan.md
- commands/results:
  - command: `PYTHONPATH=src python3 -m unittest tests/test_storage_and_cli.py -v`
    result: `通过（含 M2 新增用例）`
  - command: `PYTHONPATH=src python3 -m unittest discover -s tests -v`
    result: `通过（Ran 10 tests, OK）`
  - command: `PYTHONPATH=src python3 -m ai_info_collection.cli --db-path ./data.db review`
    result: `通过（退出码 0）`
  - command: `PYTHONPATH=src python3 -m ai_info_collection.cli --db-path ./data.db source-health`
    result: `通过（退出码 0）`
  - command: `PYTHONPATH=src python3 -m ai_info_collection.cli --db-path ./data.db recent-events`
    result: `通过（退出码 0）`
- decisions:
  - 不改 schema、不改命令参数，只在 storage 增加查询并在 review 输出后追加分段。
  - `missing framework_tags` 统一覆盖：脏 JSON、非 list、空 list、含空白标签（以及非字符串标签）。
  - 保持原有 `what_changed` 与 `interpretation_type` 两段输出文本不变，仅后追加两段。
- known risks:
  - `missing framework_tags` 的判定在 Python 侧执行（逐行解析 JSON），当数据量很大时会有线性扫描成本。
  - 当前测试聚焦 `review` 输出与样例命中；未覆盖更大规模数据下的性能表现。
- exact next step:
  - M2 已完成；下一步进入 Milestone 3（RawDocument + CanonicalDocument 拆分落库）范围确认与最小实现计划。

## Milestone 3 状态（worker）

- milestone status: completed (M3 Raw/Canonical 拆分落库)
- files changed:
  - src/ai_info_collection/models.py
  - src/ai_info_collection/storage.py
  - src/ai_info_collection/cli.py
  - tests/test_pipeline_m3_m6.py
  - docs/Plan.md
- commands/results:
  - command: `PYTHONPATH=src python3 -m unittest tests/test_pipeline_m3_m6.py -v`
    result: `通过（Ran 7 tests, OK）`
  - command: `PYTHONPATH=src python3 -m ai_info_collection.cli --db-path ./data.db recent-raw --limit 10`
    result: `通过（退出码 0，当前空库输出 (empty)）`
  - command: `PYTHONPATH=src python3 -m ai_info_collection.cli --db-path ./data.db recent-canonical --limit 10`
    result: `通过（退出码 0，当前空库输出 (empty)）`
- decisions:
  - 新增 `raw_documents` 与 `canonical_documents`，沿用 `initialize()` 增量建表。
  - 新增最小接口 `upsert/list`，不修改现有 M1/M2 接口行为。
- known risks:
  - `raw_documents.source_id` 暂不强制外键到 `sources`，便于导入初期落地，但来源治理一致性需在后续补强。
- exact next step:
  - 进入 M4：接入 `SignalInput` JSONL 导入与 dry-run。

## Milestone 4 状态（worker）

- milestone status: completed (M4 SignalInput JSONL 导入管线)
- files changed:
  - src/ai_info_collection/models.py
  - src/ai_info_collection/ingest.py
  - src/ai_info_collection/cli.py
  - tests/test_pipeline_m3_m6.py
  - sample.jsonl
  - docs/Plan.md
- commands/results:
  - command: `PYTHONPATH=src python3 -m ai_info_collection.cli --db-path ./data.db ingest-signals --input ./sample.jsonl --dry-run`
    result: `通过（退出码 0，total=2 success=2 skipped_duplicates=0 failed=0）`
- decisions:
  - `ingest-signals` 默认按行处理，单行失败不中断全局。
  - 返回码策略：`success > 0` 返回 0，否则返回 1。
  - 去重按 `hash_sha256(content)`，同时覆盖“库内重复+同批重复”。
- known risks:
  - 当前 canonical 规则化（标题/摘要/关键词）为纯规则实现，语义质量依赖输入文本质量。
- exact next step:
  - 进入 M6：确定性事件归并与幂等验证。

## Milestone 6 状态（worker）

- milestone status: completed (M6 确定性复杂事件归并)
- files changed:
  - src/ai_info_collection/merge.py
  - src/ai_info_collection/storage.py
  - src/ai_info_collection/cli.py
  - tests/test_pipeline_m3_m6.py
  - docs/Plan.md
- commands/results:
  - command: `PYTHONPATH=src python3 -m ai_info_collection.cli --db-path ./data.db merge-events --limit 100 --dry-run`
    result: `通过（退出码 0，processed=0 matched_by_hint=0 matched_by_rule=0 created_new=0）`
  - command: `PYTHONPATH=src python3 -m unittest discover -s tests -v`
    result: `通过（Ran 17 tests, OK）`
- decisions:
  - 归并规则固定：`event_hint` 命中 -> 标题键+实验室+7天窗 -> 新建事件。
  - `merge-events` 支持 dry-run，不写库只输出统计。
- known risks:
  - 归并策略目前偏确定性规则，复杂跨标题语义归并能力有限。
- exact next step:
  - M3/M4/M6 已完成；下一步进入生产数据样本验证与规则参数调优。

## Milestone 7 状态（worker）

- milestone status: completed (`run-pipeline` 与运行结果落库)
- files changed:
  - src/ai_info_collection/storage.py
  - src/ai_info_collection/ingest.py
  - src/ai_info_collection/pipeline.py
  - src/ai_info_collection/cli.py
  - tests/test_run_pipeline.py
  - README.md
  - docs/Plan.md
- commands/results:
  - command: `PYTHONPATH=src python3 -m unittest tests/test_run_pipeline.py -v`
    result: `通过（Ran 4 tests, OK）`
  - command: `PYTHONPATH=src python3 -m ai_info_collection.cli --db-path ./data.db run-pipeline --input ./sample.jsonl --dry-run`
    result: `当前 data.db 为重复样本场景，ingest_success=0，状态 failed（符合返回码策略）`
  - command: `PYTHONPATH=src python3 -m ai_info_collection.cli --db-path ./data.db run-pipeline --input ./sample.jsonl`
    result: `当前 data.db 为重复样本场景，ingest_success=0，状态 failed（符合返回码策略）`
  - command: `PYTHONPATH=src python3 -m unittest discover -s tests -v`
    result: `通过（Ran 21 tests, OK）`
- decisions:
  - `run-pipeline` 固定编排 `ingest -> merge -> summary`，并落库 `pipeline_runs/pipeline_run_errors`。
  - 错误条目按 ingest 逐行落库（line_no + error_message + raw_payload）。
  - 返回码策略：`ingest_success > 0` 返回 0，否则返回 1。
- known risks:
  - merge 阶段异常当前仅记录运行级失败状态，不做逐条错误拆分。
  - `run_id` 采用时间戳+哈希，默认可读且概率唯一，但未做跨进程强一致协调。
- exact next step:
  - 用真实业务样本验证 pipeline 运行日志质量，并补充运行记录查询命令。

## Milestone 8 状态（worker）

- milestone status: completed (并发/重复防护 + 1k 回放评估)
- files changed:
  - src/ai_info_collection/storage.py
  - src/ai_info_collection/pipeline.py
  - src/ai_info_collection/ingest.py
  - src/ai_info_collection/evaluation.py
  - src/ai_info_collection/cli.py
  - tests/test_run_pipeline.py
  - tests/test_evaluation.py
  - README.md
  - docs/Plan.md
- commands/results:
  - command: `PYTHONPATH=src python3 -m unittest tests/test_run_pipeline.py -v`
    result: `通过（Ran 7 tests, OK）`
  - command: `PYTHONPATH=src python3 -m unittest tests/test_evaluation.py -v`
    result: `通过（Ran 3 tests, OK）`
  - command: `PYTHONPATH=src python3 -m unittest discover -s tests -v`
    result: `通过（Ran 27 tests, OK）`
  - command: `PYTHONPATH=src python3 -m ai_info_collection.cli --db-path ./data.db run-pipeline --input ./sample.jsonl --dry-run`
    result: `失败（退出码 1；当前 data.db 下 failed，status_reason=ingest_no_success）`
  - command: `PYTHONPATH=src python3 -m ai_info_collection.cli --db-path ./data.db generate-replay-dataset --output ./replay_1k.jsonl --rows 1000 --seed 42`
    result: `成功（rows=1000, seed=42）`
  - command: `PYTHONPATH=src python3 -m ai_info_collection.cli --db-path ./data.db evaluate-merge --input ./replay_1k.jsonl`
    result: `成功（rows_total=1000, event_groups_truth=200, false_merge_rate=0.000000, miss_merge_rate=0.800000）`
- decisions:
  - 并发保护采用 SQLite `BEGIN IMMEDIATE` 互斥保留运行槽位。
  - 运行锁新增陈旧恢复：`running` 超过 30 分钟自动标记 `stale_running_recovered` 后放行新运行。
  - 重复运行判重键采用 `sha256(input_path|dry_run|merge_limit)`，默认 10 分钟窗口。
  - 1k 回放评估采用内置合成真值数据集，并落库误并率/漏并率。
- known risks:
  - 锁粒度仅针对同一 `db_path` 实例，不覆盖跨数据库并发。
  - 评估数据为合成样本，需后续补充真实标注集验证外推性。
- exact next step:
  - 基于真实业务样本补充误并/漏并趋势监控与阈值告警。

## Milestone 9 状态（worker）

- milestone status: completed (Scrapling 在线抓取 + RSS 拉取 + 网页解析接入)
- files changed:
  - pyproject.toml
  - src/ai_info_collection/models.py
  - src/ai_info_collection/storage.py
  - src/ai_info_collection/ingest.py
  - src/ai_info_collection/pipeline.py
  - src/ai_info_collection/cli.py
  - src/ai_info_collection/fetch.py
  - src/ai_info_collection/scrapling_adapter.py
  - tests/test_fetch_pipeline.py
  - README.md
  - docs/Plan.md
- commands/results:
  - command: `PYTHONPATH=src python3 -m unittest discover -s tests -v`
    result: `通过（Ran 30 tests, OK）`
  - command: `PYTHONPATH=src python3 -m ai_info_collection.cli --db-path ./data.db seed-sources --preset official-ai`
    result: `通过（seeded=4）`
  - command: `PYTHONPATH=src python3 -m ai_info_collection.cli --db-path ./data.db fetch-sources --source-limit 5`
    result: `失败（退出码 1；当前环境下 success_sources=0, failed_sources=4）`
  - command: `PYTHONPATH=src python3 -m ai_info_collection.cli --db-path ./data.db run-pipeline --source-limit 5`
    result: `失败（退出码 1；status=failed, status_reason=ingest_no_success, fetch_failed=4）`
  - command: `PYTHONPATH=src python3 -m ai_info_collection.cli --db-path ./data.db recent-fetch-runs --limit 10`
    result: `通过（可见 fetch_runs 失败记录明细）`
- decisions:
  - `run-pipeline` 默认改为在线抓取入口（`sources` 驱动），保留 `--input` 作为离线回放兼容路径。
  - 抓取模式默认采用 Scrapling `Fetcher` 静态抓取，`source_type=rss` 使用 RSS 解析。
  - 新增 `seed-sources/fetch-sources/recent-fetch-runs` 命令与 `fetch_runs` 落库，形成抓取可观测性闭环。
- known risks:
  - 在线抓取依赖网络可达与目标站点可访问性；离线或受限网络环境下会全部失败。
  - 当前网页正文提取采用规则化方案（selector/article/body），复杂页面仍可能解析不足。
  - Scrapling 依赖未安装时 web 抓取将失败（错误会写入 `fetch_runs.error_message`）。
- exact next step:
  - 在可联网环境安装依赖并验证官方源抓取成功率，随后按失败类型补齐 source 级 selector 与 parser 配置。

## Milestone 9.1 状态（worker）

- milestone status: blocked by external DNS/network on current machine
- files changed:
  - docs/Plan.md
- runtime config changes (data.db):
  - installed dependency: `scrapling[fetchers]>=0.3.0`
  - source fallback applied:
    - `openai-rss`: `rss -> web`, `url=https://openai.com/news/`, `fetch_parser=article`, `fetch_selector=article`
    - `anthropic-rss`: `rss -> web`, `url=https://www.anthropic.com/news`, `fetch_parser=article`, `fetch_selector=article`
- commands/results:
  - command: `python3 -m pip install "scrapling[fetchers]>=0.3.0"`
    result: `通过（安装完成）`
  - command: `PYTHONPATH=src python3 -c "from scrapling.fetchers import Fetcher; print('ok')"`
    result: `通过（输出 ok）`
  - command: `DNS/HTTP 探测（openai.com, www.anthropic.com, deepmind.google, ai.meta.com）`
    result: `失败（统一报错：Could not resolve host / nodename nor servname）`
  - command: `PYTHONPATH=src python3 -m ai_info_collection.cli --db-path ./data.db fetch-sources --source-limit 5`
    result: `失败（退出码 1；total_sources=4, success_sources=0, failed_sources=4）`
  - command: `PYTHONPATH=src python3 -m ai_info_collection.cli --db-path ./data.db run-pipeline --source-limit 5`
    result: `失败（退出码 1；status=failed, status_reason=ingest_no_success, fetch_failed=4）`
  - command: `PYTHONPATH=src python3 -m ai_info_collection.cli --db-path ./data.db recent-fetch-runs --limit 10`
    result: `通过（可见每个 source 的失败记录与 error_message）`
  - command: `PYTHONPATH=src python3 -m unittest discover -s tests -v`
    result: `通过（Ran 30 tests, OK）`
- decisions:
  - 先消除依赖问题，再按 `fetch_runs.error_message` 逐源修复。
  - 按策略对 RSS 源执行官方网页降级（`rss -> web`）。
  - 识别为单一外部阻断：当前机器 DNS 无法解析目标域名，非代码逻辑故障。
- known risks:
  - 在 DNS 未恢复前，在线抓取与 pipeline 在线模式无法达成 `status=success`。
  - 当前已修 source 配置只能在网络恢复后验证真实抓取成功率与 selector 质量。
- exact next step:
  - 修复本机 DNS/网络后，重新执行 `fetch-sources --source-limit 5` 与 `run-pipeline --source-limit 5`，并确认 `fetch_runs` 至少 1 条 `status=success`。
