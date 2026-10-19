# ExcelForge 前端

Vue 3 + Vite + Element Plus 前端，源码位于 `frontend/`。Excel 在浏览器中解析，正式生成统一提交到 `POST /api/excel/process`。

先按根目录 README 启动正式后端，再执行：

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev
```

Vite 默认将 `/api` 代理到 `http://127.0.0.1:8000`，可通过 `VITE_API_PROXY_TARGET` 覆盖。
