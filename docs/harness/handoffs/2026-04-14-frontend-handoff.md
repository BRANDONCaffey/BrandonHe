# Frontend Agent Handoff (M1)

## 已完成
- 实现 M1 UI 页面：
  - 面板1（Brent/WTI 主链路）
  - 系统状态面板
  - 事件检查板（筛选/新增/编辑）
  - 活动告警展示与确认
- UI 仅通过 API 访问数据，不直连 LSEG
- 缺失或异常数据按状态展示，不渲染伪数据

## 交付物
- `apps/ui/streamlit_app.py`

## 依赖与约束
- 依赖 `HIMPACT_API_BASE_URL` 指向可用 API
- 依赖后端返回 `status` 字段语义一致

## 未完成/风险
- 尚未做真实 live 数据下的长时间可用性观察
- 视觉层仍为 MVP 样式，后续可迭代
