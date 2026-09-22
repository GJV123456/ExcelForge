# Debug-Table-Auto
Subway Joint Debugging and Testing System Project List - Working Automation

项目目录：

- `frontend/`：Vue 3 前端，负责登录、Excel 上传解析、RuleBuilder、提交和下载。
- `backend/`：Python 3.11 + FastAPI 后端，负责 v1 Mock、v2 正式校验和 BIFF8 `.xls` 生成。
- `data/raw/联调测试表导入模版.xls`：经确认的正式输出底表，只读使用。

本地开发请分别参阅 `frontend/README.md` 和 `backend/README.md`。v1 Mock
链路与 v2 正式生成链路均已接通；正式模式通过可视化配置显式提交操作步骤、
结果输出和责任专业，不向冻结的 v1 契约增加字段。

## Windows 本地发布

```powershell
cd frontend
npm.cmd run build
cd ..\backend
& '.\.venv\Scripts\python.exe' ..\scripts\build_release.py
& '.\.venv\Scripts\python.exe' ..\scripts\verify_release.py
```

发布目录为 `build/release/DebugTableAuto/`，ZIP 位于同级目录。最终用户直接运行
`DebugTableAuto.exe`；程序默认以 formal 模式启动并打开本地页面。正式底表
`联调测试表导入模版.xls` 必须和可执行文件位于同一目录，可在不重新打包程序的
情况下替换为经批准且通过哈希门禁的版本。

GitHub Release 只会在目标为 `main` 的 Pull Request 被成功合并后创建；直接
push、未合并关闭 PR 均不会发布。每次发布前必须提升根目录 `VERSION`，否则已有
版本门禁会拒绝重复发布。Release 包含带 `DebugTableAuto.exe` 的 Windows x64
完整 ZIP、Linux x64 `.deb`、独立导入模板、CycloneDX SBOM 和 SHA-256 清单。
