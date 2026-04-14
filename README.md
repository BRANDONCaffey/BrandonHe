# BrandonHe

Himpact project workspace.

## Docs
- Main index: [docs/README.md](</Users/brandon/Documents/New project 2/docs/README.md>)
- Architecture: [docs/architecture.md](</Users/brandon/Documents/New project 2/docs/architecture.md>)
- Env setup: [docs/env-setup.md](</Users/brandon/Documents/New project 2/docs/env-setup.md>)
- Agent roles: [agents/](</Users/brandon/Documents/New project 2/agents>)
- Project subagents: [.claude/agents/](</Users/brandon/Documents/New project 2/.claude/agents>)

## Run (v1.0 RC1)
1. Install dependencies:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e ".[dev,live]"
```
2. Start API:
```bash
PYTHONPATH="packages/core:." uvicorn apps.api.main:app --host 127.0.0.1 --port 8000 --reload
```
3. Start UI in another terminal:
```bash
PYTHONPATH="packages/core:." streamlit run apps/ui/streamlit_app.py
```

## Required Live Credentials (Desktop First)
- `HIMPACT_LSEG_MODE=desktop`
- `HIMPACT_LSEG_DESKTOP_SESSION_NAME=desktop.workspace`
- `HIMPACT_LSEG_APP_KEY` (Eikon Data API key)

## Optional Platform Mode
- `HIMPACT_LSEG_MODE=platform`
- `HIMPACT_LSEG_APP_KEY`
- `HIMPACT_LSEG_USERNAME` + `HIMPACT_LSEG_PASSWORD`
- or `HIMPACT_LSEG_CLIENT_ID` + `HIMPACT_LSEG_CLIENT_SECRET`

## RC Scope
- 面板1：原油主屏（Brent/WTI + spreads）
- 面板2：成品油传导（diesel/gasoline proxy + cracks）
- 面板3：宏观价格传导（DXY、US2Y、US10Y、Gold）
- 面板4：风险资产响应（BTCUSD、ES、NQ）
- 面板5：事件日志（新增/编辑/筛选/搜索）
- 面板6：系统状态（session、stale、更新时间）
