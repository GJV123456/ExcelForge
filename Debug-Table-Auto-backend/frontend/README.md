# ExcelForge 前端

Vue 3 + Vite + Element Plus 前端。源码位于仓库的 `frontend/` 目录，Excel
上传与解析仍在浏览器中完成，生成请求统一发送到 FastAPI 后端。

## 安装与测试

在仓库根目录执行：

```powershell
cd frontend
npm.cmd ci
npm.cmd test
npm.cmd run build
```

`node_modules/`、`dist/`、`.env*`（`.env.example` 除外）、日志、IDE 和操作
系统文件均由 Git 忽略。

## 本地联调

先从仓库根目录启动后端：

```powershell
& 'backend\.venv\Scripts\python.exe' -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

再启动前端：

```powershell
cd frontend
npm.cmd run dev
```

浏览器访问 `http://127.0.0.1:5173/`。前端请求相对路径
`/api/v2/excel/process`，Vite 默认代理到 `http://127.0.0.1:8000`。如需改变代理
目标，复制 `.env.example` 为 `.env.local` 并设置：

```env
VITE_API_PROXY_TARGET=http://127.0.0.1:8000
```

开发环境默认保留模拟登录，用户名 `admin`、密码 `123456`。Excel 处理不再
使用浏览器本地 Mock；Mock/Formal 模式由后端统一控制。

正式生成前需在启动后端前设置：

```powershell
$env:EXCELFORGE_MODE='formal'
```

## Excel 处理接口

```http
POST /api/v2/excel/process
Content-Type: application/json
```

请求使用 v2 camelCase 契约；v1 的既有字段保持不变，每条测试内容新增显式的
`operationSteps`：

```json
{
  "testLocation": {
    "type": "站点",
    "direction": "",
    "startStation": "A站",
    "endStation": "A站"
  },
  "testContents": [
    {
      "sortIndex": 1,
      "generatedContent": "站厅B端车控室烟感N1L1D01",
      "equipmentCode": "N1L1D01",
      "equipmentType": "烟感",
      "operationSteps": [
        {
          "description": "执行测试",
          "ratioChange": "否",
          "results": [
            {
              "description": "确认测试结果",
              "responsibleDisciplines": ["FAS", "综合监控"]
            }
          ]
        }
      ]
    }
  ]
}
```

前端使用 Blob 接收 BIFF8 `.xls`，优先采用后端 `Content-Disposition` 文件
名。后端 JSON 错误即使以 Blob 返回，也会还原并显示 `detail`，不会显示
`[object Blob]`。

页面按设备类型提供操作步骤、是否变比、结果输出和责任专业配置，不预填业务
规则。地点只允许站点、区间和全线；选择站点时只输入一次站名，提交时开始站点
和结束站点均填写该站名。
