# ExcelForge

ExcelForge 由 Vue 3 前端和 FastAPI 正式后端组成。正式后端唯一位于 `Debug-Table-Auto-backend/backend`，根目录不再保留重复后端或嵌套前端。

## 启动

后端：

```powershell
cd D:\ExcelForge\Debug-Table-Auto-backend\backend
$env:EXCELFORGE_MODE = "formal"
$env:EXCELFORGE_DATABASE_PATH = "D:\ExcelForge\Debug-Table-Auto-backend\backend\data\excelforge.sqlite3"
& .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

前端：

```powershell
cd D:\ExcelForge\frontend
npm.cmd run dev
```

Excel 正式生成统一使用 `POST /api/excel/process`。认证、目录、生成历史和下载接口均由同一 FastAPI 服务提供。

## 检查

```powershell
cd D:\ExcelForge\Debug-Table-Auto-backend\backend
& .\.venv\Scripts\python.exe -m pytest tests
cd D:\ExcelForge\frontend
npm.cmd test
npm.cmd run build
```
