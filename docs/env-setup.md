# Himpact Environment Setup (v1.0 RC)

## 1. 目标
建立本机可运行的 Himpact 双进程环境：`FastAPI`（后端）+ `Streamlit`（前端），并优先接入 LSEG `Desktop Session` Live 数据（可选切换 Platform Session）。

## 2. 前置条件
- Python `3.12+`
- 本机已登录并运行 Workspace Desktop（Desktop 模式）
- 可选：可用的 LSEG Platform 凭证（App Key + OAuth）
- 终端可使用 `pip`

## 3. 安装步骤
```bash
cd "/Users/brandon/Documents/New project 2"
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e ".[dev,live]"
```

如果 `lseg-data` 安装失败，可先安装基础依赖：
```bash
pip install -e ".[dev]"
```

## 4. 环境变量
创建 `.env`（可选），支持以下变量：

```bash
HIMPACT_API_HOST=127.0.0.1
HIMPACT_API_PORT=8000
HIMPACT_DB_PATH=./himpact.db
HIMPACT_API_BASE_URL=http://127.0.0.1:8000/api/v1

# LSEG Desktop Session（默认）
HIMPACT_LSEG_MODE=desktop
HIMPACT_LSEG_DESKTOP_SESSION_NAME=desktop.workspace
HIMPACT_LSEG_APP_KEY=YOUR_EIKON_API_KEY

# 仅当使用 platform 模式时启用
# HIMPACT_LSEG_MODE=platform
# HIMPACT_LSEG_SESSION_NAME=platform.himpact
# OAuth 方式二选一
# A) Password Grant
# HIMPACT_LSEG_USERNAME=YOUR_USERNAME
# HIMPACT_LSEG_PASSWORD=YOUR_PASSWORD

# B) Client Credentials Grant
# HIMPACT_LSEG_CLIENT_ID=YOUR_CLIENT_ID
# HIMPACT_LSEG_CLIENT_SECRET=YOUR_CLIENT_SECRET
# HIMPACT_LSEG_TOKEN_SCOPE=trapi

# RIC 映射（面板1~4，默认候选）
HIMPACT_RIC_BRENT_M1=LCOc1
HIMPACT_RIC_BRENT_M2=LCOc2
HIMPACT_RIC_WTI_M1=CLc1
HIMPACT_RIC_WTI_M2=CLc2
HIMPACT_RIC_DIESEL_PROXY=HOc1
HIMPACT_RIC_GASOLINE_PROXY=RBc1
HIMPACT_RIC_DXY=.DXY
HIMPACT_RIC_US2Y=US2YT=RR
HIMPACT_RIC_US10Y=US10YT=RR
HIMPACT_RIC_GOLD=XAU=
HIMPACT_RIC_BTCUSD=BTC=
HIMPACT_RIC_ES_FUT=ESc1
HIMPACT_RIC_NQ_FUT=NQc1

# 可选：阈值配置（JSON）
HIMPACT_THRESHOLDS_JSON={"brent_m1":{"up":90,"down":70},"wti_m1":{"up":85,"down":65}}
```

## 5. 启动命令
后端：
```bash
source .venv/bin/activate
PYTHONPATH="packages/core:." uvicorn apps.api.main:app --host 127.0.0.1 --port 8000 --reload
```

前端（新终端）：
```bash
source .venv/bin/activate
PYTHONPATH="packages/core:." streamlit run apps/ui/streamlit_app.py
```

## 6. 健康检查
1. 打开 `http://127.0.0.1:8000/api/v1/health`，应返回 `status=ok`。
2. 打开 Streamlit 页面，确认可见：
- 面板1（原油主屏）
- 面板2（成品油传导）
- 面板3（宏观价格传导）
- 面板4（风险资产响应）
- 面板5（事件日志）
- 面板6（系统状态）
3. 若会话未就绪（Desktop 未连接或 Platform 凭证错误），应显示 `disconnected`、`unentitled` 或 `error`，而不是崩溃。

## 7. 常见问题
- `No module named lseg`：先确认安装 `pip install -e ".[live]"`。
- Desktop 模式连接失败：确认 Workspace Desktop 已登录且在本机运行。
- Platform 模式连接失败：检查 `HIMPACT_LSEG_APP_KEY` 与 OAuth 凭证是否完整。
- 指标无值：先检查 entitlement 与 RIC 是否匹配。
