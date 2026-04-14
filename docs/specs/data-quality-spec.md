# Himpact Data Quality Spec（v1）

## 1. 目标（结论先行）
本规范定义 Himpact v1 的数据 validation/cleaning 最低标准，保证前端展示“客观、可追溯、可解释”。

## 2. 适用范围
- 实时指标：Brent/WTI、成品油 proxy/crack、DXY、US2Y/US10Y、BTC（及启用的可选指标）。
- 非实时：1D/5D/20D 变化、系统状态、事件日志元数据。

## 3. 数据校验（Validation）

### 3.1 Schema 校验（强制）
- `metric_key`：非空字符串，必须存在于 registry。
- `value`：number 或 `null`（禁止字符串数值）。
- `unit`：非空字符串，且与 `metric_key` 预期单位一致。
- `as_of`：ISO8601 UTC。
- `status`：`ok | stale | unentitled | error`。
- `source`：`lseg_workspace | lseg_platform | derived | manual`。

### 3.2 业务校验（强制）
- 指标唯一性：同一 `metric_key + as_of` 不允许重复写入。
- 时间单调性：同一指标流的 `as_of` 不得倒退；倒退数据记为 `error` 并丢弃。
- 枚举合法性：任何未知 `status/type/category` 进入错误队列。

## 4. 数据清洗（Cleaning）

### 4.1 缺失值策略
- 实时流缺失：`value=null`，`status=stale`，保留最后一条 `ok` 数据用于只读展示。
- 历史窗口缺失：该窗口返回 `null` 并附状态，不做隐式补值。
- `unentitled`：保持 `value=null`，禁止 fallback 到其他指标替代。

### 4.2 异常值策略
- 规则 1（硬阈值）：超出指标物理/业务合理区间 -> `status=error`，进入异常日志。
- 规则 2（跳变阈值）：单点变化超过配置阈值 -> 标记 `suspect=true`，不自动丢弃。
- 规则 3（连续异常）：连续 N 次异常触发告警 `stale_data` 或 `connection_error`。

### 4.3 去重与乱序
- 以 `metric_key + as_of` 去重，保留首条合法记录。
- 允许小窗口乱序（默认 3 秒）；超窗乱序丢弃并记日志。

## 5. 时间戳统一策略
- 系统内部存储：UTC。
- API 对外：UTC ISO8601。
- 前端显示：可本地化，但不得改变 API 语义。
- 刷新节奏：实时 UI 1 秒刷新；历史 5 分钟回补。

## 6. 单位统一策略
- 单位由 registry 固定，不允许前端推断。
- 同类指标单位必须一致（例如收益率统一为 `%` 或 `bp`，不得混用）。
- 派生指标（如 crack/spread）需明确单位并在文档登记。

## 7. 可追溯性与审计
每条入库数据建议保留：
- `ingest_id`
- `source`
- `raw_value`
- `clean_value`
- `rule_applied`（命中的校验/清洗规则）
- `processed_at`

## 8. 错误码建议
- `SCHEMA_INVALID`
- `RIC_NOT_FOUND`
- `UNENTITLED`
- `OUT_OF_RANGE`
- `TIMESTAMP_ROLLBACK`
- `DUPLICATE_POINT`
- `LATE_ARRIVAL`

## 9. 角色责任
- Backend Agent：规则实现与日志落地 owner。
- LSEG Workspace Agent：源数据语义、连接状态与 entitlement 语义 owner。
- Frontend Agent：仅按 `status` 展示，不做数据修复。
- Integration/QA Agent：按本规范设计异常场景用例并验收。

## 10. 最低验收门槛
- 所有上线指标通过 schema 校验。
- 缺失/无权限/异常可区分显示。
- 时间戳与单位无冲突。
- 异常数据可追溯到具体规则与来源。
