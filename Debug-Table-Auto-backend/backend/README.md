# ExcelForge 正式后端

本目录是唯一运行后端。它提供认证、目录、正式 Excel 生成、生成历史和健康检查接口。

```powershell
cd D:\ExcelForge\Debug-Table-Auto-backend\backend
$env:EXCELFORGE_MODE = "formal"
$env:EXCELFORGE_DATABASE_PATH = "D:\ExcelForge\Debug-Table-Auto-backend\backend\data\excelforge.sqlite3"
& .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

测试：`& .\.venv\Scripts\python.exe -m pytest tests`
