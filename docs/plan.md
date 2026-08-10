# ExcelForge 联调联试表生成系统主实施计划

## 1. 计划目标与执行边界

本计划供后续编码 Agent 直接执行。目标是在现有 ExcelForge Vue 3 前端基础上增加 Python FastAPI 后端，接收前端已经解析和生成好的 JSON，依据 `data/raw/联调测试表导入模版.xls` 生成包含 5 张固定工作表的 BIFF8 `.xls` 成品，并通过浏览器 Blob 下载。同时建立 GitHub Actions，完成前后端检查、自动测试、Windows/Linux 打包和 GitHub Release 发布。

本计划只修订实施说明。本次不创建 Python 虚拟环境、不安装依赖、不编写前后端代码、不创建 Workflow、不修改任何 Excel 或 JSON 数据文件。

最终输出必须包含且只能包含以下工作表，名称与顺序不可改变：

1. `测试地点`
2. `测试内容`
3. `操作步骤`
4. `结果输出`
5. `参数公式`

本期 `参数公式` 只预留终止行：`参数公式!A3=end`，其他单元格为空。结果输出的测试样式必须为空；在参数公式功能正式实现前，后端不得接受或生成测试样式 1/2/3。

不在本期范围：重写现有 Vue 前端、改变前端 UI 风格、把 Excel 原文件上传到后端、数据库、多人权限系统、公网部署、参数公式计算、宏、跨工作簿公式、修改 `data/raw/` 原始文件。

## 2. 资料优先级与冲突处理

### 2.1 资料优先级

发生冲突时按以下顺序处理：

1. 用户最新反馈与本主计划。
2. `docs/prompt.md` 的五表填写规则。
3. `data/raw/联调测试表导入模版.xls` 的工作簿结构和格式。
4. `docs/front-back-plan.md` 的现有前后端边界与 v1 JSON 契约。
5. `docs/excelforge-prompt.md` 的现有前端功能和技术栈。
6. `data/excelforge/test.json` 展示的前端数据样例。
7. `data/raw/T19-综合监控与FAS联调测试表-03角江路站20251231-导入版V1/` 中的 28 份成品，仅作为共同结构和 1:N:N 关系参考。

以下资料仍明确不作为业务规则依据：

- `data/raw/【6号线测试表模版】20250813/`
- `data/raw/T19-FAS设备信息监视-烟感和温感（角江路站）.xls`

### 2.2 已识别的文档冲突及主计划结论

| 冲突 | 主计划结论 |
| --- | --- |
| `docs/front-back-plan.md` 使用 `openpyxl` 生成 `.xlsx`，原始需求要求基于 `.xls` 底表 | 最终正式接口返回 BIFF8 `.xls`；不使用 `openpyxl` 写最终文件，前端下载后缀改为 `.xls` |
| 旧联调文档要求后端接收/生成 Excel，现有前端已经负责上传和解析 | 后端只接收 JSON，不增加原始 Excel 上传接口 |
| 原主计划准备新建 Jinja2 页面，现有前端已经是 Vue 3 | 不新建第二套页面；保留并最小修改现有 Vue 前端，Release 时把 Vue 构建结果交给 FastAPI 托管 |
| 前端任务书支持地点类型 `车辆段/停车场/其他` 和方向 `双向`，`docs/prompt.md` 只允许 `全线/区间/站点` 与 `上行/下行` | 正式生成阶段按 `docs/prompt.md` 拦截未定义值；是否扩展模板规则列为实施前确认项 |
| 前端 v1 要求地点 4 字段均存在，`docs/prompt.md` 按地点类型条件必填 | 保持 v1 字段名和字段存在性不变；后端另做业务组合校验，输出时按最终确认的映射留空无关列 |
| 当前 v1 JSON 只有地点和测试内容，没有操作步骤、结果输出、责任专业 | v1 可先完成 Mock 联调，但不能据此生成可工作的正式五表；正式模式必须先明确后端规则配置或升级接口契约 |

## 3. 当前仓库与前端现状

### 3.1 当前实际文件

| 路径 | 现状与用途 |
| --- | --- |
| `README.md` | 只有项目名称和简述，后续补充前后端运行、虚拟环境、测试和 Release 说明 |
| `docs/plan.md` | 本主计划 |
| `docs/front-back-plan.md` | 已有前后端联调任务书；作为职责和 v1 契约依据，不直接照搬其中 `.xlsx/openpyxl` 结论 |
| `docs/excelforge-prompt.md` | 现有 Vue 前端任务书；说明组件、状态、上传解析、RuleBuilder、按钮、Loading 与 Blob 下载要求 |
| `docs/prompt.md` | 正式五表的填写规范 |
| `data/excelforge/test.json` | 前端 DevTools 数据展示样例，目前不是合法 JSON 文件 |
| `data/raw/联调测试表导入模版.xls` | 正式输出唯一底表，必须只读使用 |
| `data/raw/T19-综合监控与FAS联调测试表-03角江路站20251231-导入版V1/` | 28 份指定成品样本，只读回归 |
| `data/raw/输入内容.xlsx` | 用户提供的候选输入文件，前端负责解析；后端不直接读取 |

当前工作区没有 `package.json`、`src/`、`frontend/` 或任何 Vue 源码。也就是说，“已有前端”只在任务书中得到说明，尚未出现在本次仓库快照中。编码 Agent 不得据文档重新生成一套替代前端；必须先把真实前端源码同步到本仓库或切换到包含前端的正确分支，再确认实际路径。

### 3.2 `data/excelforge/test.json` 的状态

该文件是浏览器 DevTools 展开的 JavaScript 对象文本，包含未加双引号的键、冒号分行、顶层省略号 `…` 等内容，因此不能被标准 JSON 解析器直接加载。它可用于确认字段语义和 12 条样例顺序，但不能直接作为 pytest fixture 或 HTTP 请求体。

实现时保留原文件不变，并新增合法 fixture `backend/tests/fixtures/excel_process_request.json`。fixture 必须使用双引号、完整数组和合法 UTF-8，并与该样例的字段和值逐项对应。不得通过正则“修复”当前文件后直接用于生产。

### 3.3 已确认底表结构

`data/raw/联调测试表导入模版.xls` 是 Excel 97-2003 BIFF8 工作簿。调查基线 SHA-256 为 `11E679909BA25C898A19E5DB490B6C56B89D1543114F604F26C594D84ECB53B0`。五张表均是第 1 行说明、第 2 行表头、第 3 行示例、第 4 行 `end`。

| 工作表 | 列结构 | 第 1 行合并区域 |
| --- | --- | --- |
| `测试地点` | A 地点类型；B 行车方向；C 开始站点；D 结束站点 | `A1:D1` |
| `测试内容` | A 测试内容 | 无跨列合并 |
| `操作步骤` | A 测试内容行号；B 操作步骤；C 是否变比 | `A1:C1` |
| `结果输出` | A 操作步骤行号；B 结果输出；C 责任专业；D 测试样式 | `A1:D1` |
| `参数公式` | A 结果输出行号；B 参数名称；C 计算公式；D 标准值；E 单位 | `A1:E1` |

底表无数据有效性和保护。页面校验只改善用户体验，正式约束必须由 Python 后端再次执行。

## 4. 目标架构与前后端边界

### 4.1 总体链路

```text
现有 Vue 3 前端
  ├─ 登录、上传 .xlsx、SheetJS/exceljs 解析
  ├─ 类型识别、RuleBuilder、测试内容预览
  ├─ 组装冻结的 v1 JSON
  └─ POST /api/excel/process（responseType: blob）
                         ↓
Python 3.11 + FastAPI
  ├─ Pydantic 校验 v1 JSON
  ├─ 保持数组与 sortIndex 对应关系
  ├─ 解析正式操作/结果规则
  ├─ 展开五表行号关系
  ├─ 复制并填写 BIFF8 .xls 底表
  └─ 返回 application/vnd.ms-excel
                         ↓
Vue 解析 Content-Disposition 并下载 最终导入表.xls
```

开发模式：Vue/Vite 独立运行，通过 Vite proxy 把 `/api/*` 转发至 `127.0.0.1:8000`。

Release 模式：先构建现有 Vue 前端，再由 FastAPI 托管构建后的静态文件和 SPA fallback；PyInstaller `onedir` 发布包包含 Python 运行时、后端、Vue 构建产物和唯一 Excel 底表，不需要用户安装 Python、Node、Excel 或 LibreOffice。

### 4.2 前端保持的职责

- 登录鉴权、路由守卫和 Axios token 逻辑。
- `.xlsx` 文件上传、20MB 限制、表头识别和前端解析。
- Type A/Type B 判断、原始顺序与 `sortIndex`。
- RuleBuilder 生成 `generatedContent`。
- 组装 v1 JSON、提交、Loading、Blob 下载和错误提示。

后端不重复解析前端已经读取的原始 Excel，不接收 multipart 文件，不重做 RuleBuilder，也不修改用户的 `generatedContent`。

### 4.3 后端职责

- 严格校验 v1 外部契约和业务值域。
- 保留前端数组顺序，验证而不是重排 `sortIndex`。
- 根据确认后的规则来源生成操作步骤、结果输出和责任专业。
- 计算跨表 Excel 行号并生成 `.xls`。
- 提供健康检查、结构化错误、下载文件名和日志。
- 在 Release 中托管已构建的 Vue 静态资源。

## 5. Python 解释器、venv 与依赖管理

### 5.1 已验证的本机解释器

本次只读检查确认：

- 首选：`E:\Python 11\python.exe`，Python 3.11.4，pip 24.2。
- 可选：`E:\Anaconda3\python.exe`。
- 可用 Conda 环境包括 `base`、`AI`、`codegeex-agent`、`pack`、`watermark` 等。
- `py` launcher 还列出 Python 3.14，但本项目不得用 3.14 开发或打包，旧版 BIFF8 库兼容性风险过高。

本地开发不得下载或安装另一套 Python。首选直接用现有 `E:\Python 11\python.exe` 创建标准库 `venv`。若它无法创建可用环境，才允许使用现有 Conda 解释器作为 `venv` 的基础解释器；不得以 `conda create` 环境代替项目 `venv`。

编码阶段应执行但本次不得执行的命令：

```powershell
& 'E:\Python 11\python.exe' -m venv backend\.venv
& 'backend\.venv\Scripts\python.exe' -m pip install -r backend\requirements-dev.txt
```

不要求激活虚拟环境；README 和脚本应优先使用 `backend\.venv\Scripts\python.exe` 的明确路径，避免误用全局或 Conda 当前环境。

### 5.2 requirements 文件

- `backend/requirements.txt`：运行时依赖，所有直接和传递依赖固定兼容版本；至少包括 FastAPI、Uvicorn、Pydantic、配置依赖、`xlrd`、`xlwt`、`xlutils`。
- `backend/requirements-dev.txt`：第一行引用 `-r requirements.txt`，再固定 pytest、pytest-cov、httpx、Ruff、mypy、PyInstaller、pip-audit、CycloneDX 等测试与打包依赖。
- 不使用 `uv.lock`、Poetry 或 Conda environment 文件代替 `requirements.txt`。
- 更新依赖必须在干净的 `backend/.venv` 中验证，并执行测试和 `pip-audit`；禁止把全局环境的无关包通过 `pip freeze` 混入项目。

### 5.3 Git 禁止项

必须在根目录 `.gitignore` 中至少忽略：

```text
.venv/
venv/
env/
backend/.venv/
__pycache__/
*.py[cod]
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
htmlcov/
build/
dist/
backend/app/frontend_dist/
~$*.xls*
```

禁止提交或上传 GitHub：任何 venv、`site-packages` 目录、pip/Conda 缓存、下载的 wheel、解释器文件、`__pycache__`、本地日志、临时 Excel 和凭据。`requirements*.txt` 必须提交；PyInstaller 正式发布包中由工具封装的运行时依赖属于 Release 成品，不等同于提交 venv，但归档内不得出现 `.venv` 或原始 `site-packages` 目录。

GitHub Actions 使用 GitHub-hosted Runner 提供的 Python 3.11 工具缓存，并在 Runner 内创建临时 `backend/.venv`；该环境随任务销毁且绝不能作为 artifact 上传。这是云端构建环境，不改变“本机只使用现有解释器”的约束。

## 6. v1 API 契约

### 6.1 请求

接口：

```text
POST /api/excel/process
Content-Type: application/json
```

一级结构保持冻结，不添加必填字段：

```json
{
  "testLocation": {
    "type": "站点",
    "direction": "上行",
    "startStation": "1",
    "endStation": "2"
  },
  "testContents": [
    {
      "sortIndex": 1,
      "generatedContent": "站厅B端车控室烟感N1L1D01",
      "equipmentCode": "N1L1D01",
      "equipmentType": "烟感"
    }
  ]
}
```

外部字段必须保持 camelCase。Python 内部可以通过 Pydantic alias 使用 snake_case，但校验错误位置、OpenAPI 和响应必须展示现有 camelCase；不得要求前端改字段名。

### 6.2 顺序规则

- 不排序、不去重、不重组 `testContents`。
- 使用请求数组现有顺序写入测试内容。
- 校验 `sortIndex` 为正整数、无重复且按数组顺序严格递增；若不满足则返回 400，不在后端自动修复。
- `sortIndex` 是追溯键，不直接写成模板跨表引用；模板引用必须使用实际 Excel 行号。

### 6.3 成功响应

正式接口返回：

```text
HTTP 200
Content-Type: application/vnd.ms-excel
Content-Disposition: attachment; filename*=UTF-8''最终导入表.xls
```

前端必须继续使用 `responseType: 'blob'`，但下载扩展名从旧联调文档的 `.xlsx` 调整为 `.xls`，并优先解析后端 `Content-Disposition`。

### 6.4 错误与健康检查

- `GET /api/health`：返回 `200 {"status":"ok","mode":"mock|formal"}`。
- 400：地点值域、顺序、业务规则缺失、BIFF8 上限等业务错误。
- 422：Pydantic JSON 结构或类型错误。
- 500：未预期的模板或生成错误，对外只返回请求 ID 和通用信息，日志保留 traceback。

错误统一为 JSON，至少包含 `detail`、`code`、可选 `path` 和 `requestId`。前端遇到 Blob 错误响应时必须先按响应 Content-Type/文本尝试解析 JSON，不能显示 `[object Blob]`。

## 7. Mock 联调与正式生成的边界

### 7.1 Phase A：Mock 联调

在正式业务规则未齐备前，先用冻结 v1 契约打通 Vue → FastAPI → Blob 下载。Mock 模式可以配置 2 秒延迟来验证 Loading，但延迟只能由开发配置启用，生产默认必须为 0。

Mock 仍返回 `.xls`，且文件名明确为 `联调占位文件_不可导入.xls`。它可以验证收到的地点、`sortIndex`、`generatedContent`、设备编码和类型，但不得冒充满足五表规则的正式工作文件。

Mock 验收：

- 前端只发出一次 `/api/excel/process` 请求。
- Payload 与 v1 完全一致，12 条 fixture 中文和顺序不变。
- 请求期间 Loading 可见且按钮禁用，成功和失败都能关闭。
- 浏览器下载非零字节 `.xls`，Excel/WPS 可打开。
- Mock 文件和日志明确标识不可用于导入。

### 7.2 Phase B：正式生成门禁

v1 JSON 没有操作步骤、是否变比、结果输出、责任专业和测试样式，无法单独满足 `docs/prompt.md`。正式模式只能在以下两种方案中明确选择一个后启用：

1. **推荐的 v1 保持方案**：后端加载经业务确认的规则配置，按 `equipmentType` 精确匹配，必要时按 `equipmentCode` 精确覆盖，并设置一个显式默认规则。规则配置包含步骤、是否变比、结果和责任专业。
2. **后续 v2 方案**：扩展前端可视化配置，把步骤/结果设置提交到版本化的新契约；不能悄悄给 v1 增加必填字段。

在规则来源未确认、配置缺失、多个规则冲突或记录未匹配时，正式接口返回 400 `BUSINESS_RULES_NOT_CONFIGURED`/`RULE_NOT_MATCHED`，禁止生成看似成功但缺少操作/结果的文件。

## 8. 正式工作簿生成方案

### 8.1 Python 库与技术门禁

使用 `xlrd` 读取 BIFF8 和格式信息，使用 `xlutils.copy`/`xlwt` 写模板副本。`openpyxl` 不支持写 `.xls`，因此不进入正式后端运行依赖。

`xlwt/xlutils` 维护较少，必须先实现模板往返技术门禁：打开底表、复制、保存到临时目录、用 `xlrd` 重开，对比五表名称与顺序、说明/表头、合并区域、行高、列宽和有效样式属性。Microsoft Excel/WPS 人工打开时不能出现修复提示。若失败，立即停止业务实现并重新评估支持 BIFF8 的 Python 方案；不得改用 Excel COM，因为 GitHub Linux 构建和无 Excel 运行环境无法支持。

### 8.2 行号展开

1. `测试地点`：v1 只有一条，写入第 3 行；第 4 行写 `end`。
2. `测试内容`：按请求数组顺序从第 3 行写 `generatedContent`；第 `3 + 内容数` 行写 `end`。
3. `操作步骤`：按测试内容顺序，再按规则内步骤顺序展开。A 列填写父测试内容实际 Excel 行号；B 为步骤；C 只能是 `是/否`。
4. `结果输出`：按操作步骤顺序，再按规则内结果顺序展开。A 列填写父操作步骤实际 Excel 行号；B 为结果；C 为责任专业；D 本期为空。
5. `参数公式`：固定 `A3=end`，`B3:E3` 为空。

每张表数据之后必须紧接且只有一个精确小写 `end`。不能用 UsedRange 最后一行判断业务数据；读取样本时以首个 `end` 为结束。

### 8.3 模板保真与安全

- 每个请求新建只读源工作簿和独立写副本，不能缓存可变 workbook。
- 保留第 1/2 行、工作表顺序、合并区、列宽、行高、边框、字体、对齐、打印设置。
- 新数据行复用原第 3 行样式，终止行复用原第 4 行样式；避免为每格创建样式。
- 写入均为字符串/数值，不把以 `= + - @` 开头的用户文本解释为公式。
- 生成前预估每张 BIFF8 工作表不超过 65,536 行，单元格字符串不超过 Excel 上限；超限返回业务错误，不能截断。
- 输出先写 `BytesIO`，再用 `xlrd` 重开自检；源模板哈希在生成前后必须一致。
- 文件名清理控制字符、路径字符和 Windows 保留名。

## 9. 文件级实施清单

### 9.1 前端源码到位前不得创建的文件

当前仓库没有真实 Vue 源码。编码 Agent 必须先定位真实 `<frontend-root>`；它可能是仓库根目录，也可能是 `frontend/`。以下是任务书中的预期相对路径，不得在空仓库中凭空创建替代组件：

| 预期路径 | 到位后最小修改 |
| --- | --- |
| `<frontend-root>/src/api/excel.js` | 封装 `processExcel(payload)`，POST `/api/excel/process`，`responseType: 'blob'` |
| `<frontend-root>/src/utils/request.js` | 保留 token/401；让 Blob 错误可解析 JSON，不硬编码后端绝对地址 |
| `<frontend-root>/src/views/Workspace.vue` | 在现有流程末尾连接“生成正式文件”、前端校验、Loading、禁用重复提交和成功/失败提示 |
| `<frontend-root>/src/components/LoadingDialog.vue` | 如已存在则复用；只补足请求全生命周期，不重做样式 |
| `<frontend-root>/src/store/excel.js` | 只在实际需要时补充处理状态，不复制整份大 Payload |
| `<frontend-root>/vite.config.js` 或 `vite.config.ts` | 开发环境 `/api` 代理到 FastAPI；后端地址来自 env/配置 |
| `<frontend-root>/package.json` 与现有 lockfile | 仅补充缺失的 build/test 脚本；不更换包管理器，不批量升级依赖 |

### 9.2 新增后端文件

| 路径 | 具体内容 |
| --- | --- |
| `backend/requirements.txt` | 固定运行依赖；作为源码运行和打包运行依赖清单 |
| `backend/requirements-dev.txt` | 引用运行依赖并固定测试、质量、安全、PyInstaller 与 SBOM 工具 |
| `backend/pyproject.toml` | 只放 pytest、coverage、Ruff、mypy 配置；依赖仍以 requirements 文件为准 |
| `backend/README.md` | 使用本机现有解释器创建 venv、明确路径运行、配置、测试、排错说明 |
| `backend/app/__init__.py` | Python 包标识，不产生启动副作用 |
| `backend/app/__main__.py` | 源码和 PyInstaller 启动入口；启动 Uvicorn，默认绑定 `127.0.0.1`，支持 `--host`、`--port`、`--no-browser` 和优雅退出 |
| `backend/app/main.py` | FastAPI app factory、路由、请求 ID、开发 CORS、Release 静态文件与 SPA fallback；API 路由优先于前端 fallback |
| `backend/app/config.py` | 环境变量配置：模式、模板路径、规则路径、请求/行数限制、mock 延迟、host/port |
| `backend/app/resource_paths.py` | 统一解析源码目录、外部配置和 PyInstaller `_MEIPASS`/onedir 中的 Vue 产物、底表与规则资源 |
| `backend/app/exceptions.py` | 业务异常、统一错误结构和 traceback 隔离 |
| `backend/app/api/__init__.py` | API 包标识 |
| `backend/app/api/excel.py` | `GET /api/health`、`POST /api/excel/process`，只负责 HTTP 编排和流响应 |
| `backend/app/schemas/__init__.py` | Schema 包标识 |
| `backend/app/schemas/excel.py` | TestLocation、TestContent、ExcelProcessRequest；v1 camelCase alias、额外字段策略、类型约束 |
| `backend/app/domain/__init__.py` | 内部领域包标识 |
| `backend/app/domain/workbook.py` | 与 HTTP 解耦的地点、测试内容、步骤、结果和展开行模型 |
| `backend/app/services/__init__.py` | 服务包标识 |
| `backend/app/services/excel_processor.py` | v1 请求校验、顺序追溯、mock/formal 分流、正式领域模型组装 |
| `backend/app/services/rule_resolver.py` | 正式模式的设备类型精确匹配、设备编码覆盖、默认规则、冲突/未匹配错误 |
| `backend/app/utils/__init__.py` | 工具包标识 |
| `backend/app/utils/template_provider.py` | 解析外部、仓库和 PyInstaller 资源路径；验证模板结构；每次返回独立源 |
| `backend/app/utils/xls_writer.py` | 复制模板、写五表、样式复用、`end`、跨表行号、重开自检、返回 BytesIO |
| `backend/config/rules.example.json` | 规则配置结构示例，不虚构生产业务值；实际规则必须经确认 |
| `backend/config/rules.json`（正式规则确认后） | 经业务确认的正式步骤/结果/责任专业规则；只有确认采用后端规则方案且内容不敏感时提交并打包 |
| `backend/tests/conftest.py` | TestClient、临时配置、临时输出和隔离规则 fixture |
| `backend/tests/fixtures/excel_process_request.json` | 由 `data/excelforge/test.json` 语义整理出的合法、完整 UTF-8 v1 请求 |
| `backend/tests/test_health.py` | 健康检查和模式字段测试 |
| `backend/tests/test_schema.py` | v1 字段、camelCase、中文、额外字段、类型和错误路径测试 |
| `backend/tests/test_excel_process.py` | 有效请求、400/422/500、Blob MIME/文件名、顺序和并发测试 |
| `backend/tests/test_rule_resolver.py` | 精确匹配、覆盖、默认、冲突、未匹配和 1:N:N 测试 |
| `backend/tests/test_xls_writer.py` | 五表、行号、`end`、参数公式、样式、上限、重开和源哈希测试 |
| `backend/tests/test_template_roundtrip.py` | BIFF8 复制保真前置门禁 |
| `backend/tests/test_completed_workbook_contract.py` | 只读检查指定成品目录的共同五表与引用契约，不修改样本 |

### 9.3 打包与 GitHub 文件

| 路径 | 具体内容 |
| --- | --- |
| `.gitignore` | 忽略 venv、依赖包、缓存、前端/后端构建目录、Excel 锁文件和本地配置；不得忽略 requirements 文件或整个 `data/` |
| `VERSION` | 单一发布版本；tag 去掉 `v` 后必须与之相同 |
| `packaging/debug_table_auto.spec` | PyInstaller `onedir`，精确收集后端、Vue 构建产物和唯一 `.xls` 底表；不能通配整个 `data/raw/` |
| `scripts/build_release.py` | 校验前端已构建、调用 PyInstaller、复制 README/LICENSE、生成平台归档；使用当前 venv 的 `sys.executable` |
| `scripts/verify_release.py` | 启动发布程序、健康检查、发送合法 v1 请求、验证下载 `.xls`、结束进程 |
| `scripts/generate_checksums.py` | 为最终资产生成确定排序的 `SHA256SUMS.txt` |
| `.github/workflows/ci.yml` | 前端构建检查、后端 venv/requirements 测试、安全审计、模板门禁和 Windows 打包 dry-run |
| `.github/workflows/release.yml` | tag/manual dry-run，Windows/Linux 原生构建、冒烟、SBOM、校验和和 GitHub Release |
| `.github/dependabot.yml` | 每周检查 npm、pip 和 GitHub Actions，禁止自动合并 |

### 9.4 修改文件

| 路径 | 修改内容 |
| --- | --- |
| `README.md` | 说明现有前端位置、Python 解释器、venv、requirements、前后端启动、Mock/Formal、测试、打包、Release 和校验和 |

### 9.5 保持不变与删除

保持不变：`docs/prompt.md`、`docs/front-back-plan.md`、`docs/excelforge-prompt.md`、`data/excelforge/test.json`、全部 `data/raw/` 文件、`.gitattributes`、`LICENSE`。

删除文件：无。不得删除用户的 Excel 锁文件；只通过 `.gitignore` 防止误提交。

## 10. 分阶段实施步骤与验收条件

### 步骤 0：同步并审计真实前端

操作：执行 `git status --short`；定位包含 `package.json`、Vue `src/` 和 lockfile 的真实前端；核对 `src/api/excel.*`、`src/utils/request.*`、`src/views/Workspace.vue`、`src/store/excel.*` 和 Vite 配置；不移动目录、不重构。

验收条件：记录 `<frontend-root>` 的真实绝对/仓库相对路径；确认最终 Payload 的构造点、按钮现状、Loading 状态、Axios 实例和包管理器；若源码仍缺失则停止前端与 Release 实施，不创建伪前端。

### 步骤 1：建立 venv、requirements 和质量基线

操作：用 `E:\Python 11\python.exe -m venv backend\.venv` 创建标准 venv；用该 venv 的 Python 安装 `backend/requirements-dev.txt`；添加 `.gitignore` 和环境文档。

验收条件：所有 Python 命令的 `sys.executable` 均指向 `backend\.venv\Scripts\python.exe`；`python --version` 为 3.11.x；`pip check` 通过；`git status` 不出现 `.venv`、site-packages、缓存或已安装依赖。

### 步骤 2：完成 BIFF8 模板技术门禁

操作：先实现 `test_template_roundtrip.py` 和最小 `template_provider/xls_writer` 复制能力，不写业务数据。

验收条件：复制品可被 `xlrd`、Excel/WPS 无修复提示打开；五表名称/顺序、说明、表头、合并区、尺寸和有效样式通过；源模板 SHA-256 未改变。失败则停止后续正式生成开发。

### 步骤 3：创建 FastAPI 骨架和 v1 Schema

操作：实现 app factory、健康检查、统一异常和 v1 Pydantic 模型；外部字段严格保持 camelCase。

验收条件：`backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend` 启动成功；健康检查 200；合法 fixture 通过；缺字段、错误类型、额外字段和非法中文数据返回明确 422/400；数组和值不被修改。

### 步骤 4：Mock 后端联调

操作：实现开发专用 Mock `.xls` 返回和可配置延迟；前端仅做 API 封装、按钮、Loading、Blob 下载/错误解析和 Vite proxy。

验收条件：真实 Vue 页面点击一次只发一次请求；Request Payload 与 v1 一致；2 秒 Mock 延迟期间 Loading 可见；成功/失败均关闭；下载 `联调占位文件_不可导入.xls` 可打开；前端未改变上传解析、RuleBuilder、排序和 UI 风格。

### 步骤 5：确认正式规则来源

操作：在后端规则配置与 v2 可视化契约中作出业务选择；确认操作步骤、是否变比、结果、责任专业、默认/覆盖策略，并形成有效 fixture。

验收条件：每个 `equipmentType`/覆盖设备都有唯一规则或明确默认；每条内容至少一步，每步至少一项结果；规则缺失/冲突预期已定义；未完成时正式模式保持禁用。

### 步骤 6：实现正式处理和五表写入

操作：完成规则解析、领域展开、五表行号、样式复用、终止行、自检和 `.xls` 流响应；不改变 v1 请求顺序。

验收条件：第 11.1 节确定性用例所有行号准确；参数公式只有 `A3=end`；正式文件无示例行、额外表或测试样式；模板哈希不变；两个并发请求内容互不串扰。

### 步骤 7：完成正式前端下载

操作：把 Mock 模式切换入口和正式错误提示接入现有前端；解析 `.xls` 文件名；未配置规则时显示后端 detail。

验收条件：用户完成前端已有流程后可生成正式 `.xls`；网络、422、业务 400、500 均有明确提示；错误 Blob 不显示 `[object Blob]`；请求期间不可重复提交。

### 步骤 8：整合 Vue 静态构建和本地 Release

操作：用现有 lockfile 构建 Vue；构建脚本将产物复制到被忽略的 `backend/app/frontend_dist/` staging；PyInstaller 收集 staging、后端和唯一底表。

验收条件：删除源码、Node modules 和 `backend/.venv` 后，Windows 发布目录仍能启动并打开 Vue 页面、调用本地 API 和生成 `.xls`；发布归档不包含 `.venv`、site-packages 原目录、测试业务样本或整个 `data/raw/`。

### 步骤 9：实现 GitHub CI 与 Release

操作：按第 12 节创建两个 Workflow；所有 Action 固定 commit SHA；Runner 内使用 Python 3.11 创建临时 venv并安装 requirements，不上传 venv。

验收条件：PR CI 的前端、后端、模板、安全和打包任务全绿；手动 dry-run 产生可下载 artifacts 但不发布；`v*` tag 仅在全部平台冒烟成功后创建含 Windows/Linux 包、SHA-256 和 SBOM 的 Release。

### 步骤 10：最终回归和交付

操作：执行自动化与人工验收，更新 README，检查 Git diff 和 Release 内容清单。

验收条件：另一名开发者能仅依据 README 用本机已有 Python 创建 venv、安装 requirements、运行前后端和测试；无 Python 用户能使用 Release；Git 中没有 venv/依赖包/缓存；所有原始资料未被修改。

## 11. 测试与验收方案

### 11.1 最小确定性正式生成用例

准备：1 个站点地点，2 条测试内容。内容 A 有 2 步（结果数 4、3），内容 B 有 1 步（结果数 2），责任专业覆盖单选与多选，是否变比均明确为 `否`。

| 工作表 | 预期 |
| --- | --- |
| `测试地点` | 第 3 行为地点，`A4=end` |
| `测试内容` | `A3=内容A`、`A4=内容B`、`A5=end` |
| `操作步骤` | A3:A5 为 `3,3,4`，`A6=end` |
| `结果输出` | 9 条；A 列为四个 `3`、三个 `4`、两个 `5`，`A12=end` |
| `参数公式` | `A3=end`，B3:E3 为空 |

### 11.2 后端自动化测试

- Schema：合法 v1、camelCase、中文、缺失/额外字段、`sortIndex` 类型/重复/乱序。
- API：health、Mock/Formal、MIME、Content-Disposition、400/422/500、请求 ID、并发。
- 规则：设备类型精确匹配、设备编码覆盖、默认、冲突、未匹配、多步骤/多结果。
- Excel：模板往返、五表、表头/样式、行号、`end`、参数公式、BIFF8 行数与文本边界、重开。
- 资料：合法 fixture 保持 `data/excelforge/test.json` 的 12 条语义和顺序；指定成品只读契约测试。
- 安全：公式前缀文本、路径文件名、异常大请求、日志不打印完整 Payload。

### 11.3 前端联调验收

- 表头错误应说明 Type A 需要 `测试内容/类型`，Type B 需要 `设备编码/设备类型/设备中文`，并明确缺失或错误表头。
- 生成按钮仅在地点和测试内容有效时可提交。
- Axios 统一 API 层请求，业务组件不重复配置。
- Loading 与实际请求生命周期一致，不用前端定时器伪造。
- 成功下载 `.xls`；错误 Blob 能还原 JSON detail；Object URL 被释放。
- 保持原 Excel 顺序，不去重、不重排，不在多个 Pinia 状态复制大型数据。

### 11.4 人工兼容验收

- Chrome/Edge 完成提交和下载。
- Microsoft Excel 打开 `.xls` 无扩展名警告或修复提示；如目标使用 WPS，再用 WPS 检查五表、中文、边框和列宽。
- Windows 无 Python 环境运行 Release。
- Linux GitHub Runner 黑盒启动、health、请求、下载和 `xlrd` 重开。
- 生成前后模板 SHA-256 相同。

## 12. GitHub Actions 与 Release 方案

### 12.1 `.github/workflows/ci.yml`

触发：默认分支 push、pull_request、workflow_dispatch。顶层只授予 `contents: read`，设置 concurrency、timeout，Action 固定完整 commit SHA。

Jobs：

1. `frontend`：确认真实前端和 lockfile；使用固定 Node LTS、`npm ci`（或现有包管理器的 frozen install）、lint/test/build。Windows 本地 PowerShell 应使用现有 `E:\NODE\npm.cmd`，CI 使用标准命令。
2. `backend-quality`：Runner Python 3.11 → `python -m venv backend/.venv` → venv Python 安装 `requirements-dev.txt` → Ruff、mypy、`pip check`、`pip-audit`。
3. `backend-test`：Ubuntu/Windows 矩阵创建各自临时 venv，pytest 覆盖率门槛 85%，含模板往返和契约测试。
4. `repository-hygiene`：`git ls-files` 检查无 `.venv`、site-packages、pyc、缓存、Excel 锁和本地配置；检查 `data/raw/` 未被构建任务修改。
5. `package-dry-run`：依赖前端和后端成功；Windows 构建 PyInstaller onedir 并执行黑盒冒烟，只上传发布归档，不上传 `backend/.venv` 或构建缓存。

### 12.2 `.github/workflows/release.yml`

- `workflow_dispatch`：完整 Windows/Linux 矩阵构建和 artifacts，绝不创建 Release。
- push `v*` tag：严格校验 SemVer，标签去掉 `v` 后与根目录 `VERSION` 一致；Mock 模式或规则未配置时禁止正式发布。
- `build`：Windows/Linux 原生 Runner 分别创建临时 venv、安装 requirements-dev、构建前端、PyInstaller 打包、黑盒冒烟。
- `collect`：只下载平台归档，生成 `SHA256SUMS.txt` 和 CycloneDX SBOM，扫描归档禁止项，并确认包内底表哈希。
- `publish`：只在 tag 事件且所有前置 job 成功后运行，单独授予 `contents: write`，使用 `gh release create --verify-tag`，不覆盖现有 Release。
- 可选 `attest`：仓库支持时单独授予 `id-token: write`、`attestations: write`，生成 provenance。

发布资产：

- `Debug-Table-Auto-<version>-windows-x64.zip`
- `Debug-Table-Auto-<version>-linux-x64.tar.gz`
- `Debug-Table-Auto-<version>-sbom.cdx.json`
- `SHA256SUMS.txt`

发布包允许包含 PyInstaller 封装后的运行依赖；禁止包含项目 venv、原始 site-packages 目录、pip/Conda 缓存、Node modules、源码测试 fixture、其他业务 Excel 或凭据。

## 13. 风险、兼容性与待确认事项

### 13.1 主要风险与缓解

| 风险 | 影响 | 缓解 |
| --- | --- | --- |
| 真实前端源码不在当前仓库 | 无法安全联调或打包 | 步骤 0 必须同步/定位；禁止按任务书伪造替代前端 |
| v1 不含操作和结果规则 | 无法生成合法正式五表 | Mock 与 Formal 分离；正式模式以规则来源确认为门禁 |
| 文档 `.xlsx` 与底表 `.xls` 冲突 | 下载或下游格式错误 | 主计划固定 `.xls`、MIME 和后缀；前后端测试共同断言 |
| `xlwt/xlutils` 老旧 | 格式丢失、Python 升级困难 | 固定 Python 3.11；模板往返前置门禁；写入层隔离 |
| 地点值域不一致 | 前端允许但后端无法映射 | 前端选项和 `docs/prompt.md` 对齐前拦截并提示；业务确认后再扩展 |
| `test.json` 非法且含省略格式 | 测试误判或解析失败 | 保留原文件，创建合法完整 fixture，不做运行时修复 |
| venv/依赖被误提交 | 仓库膨胀和环境污染 | `.gitignore`、CI hygiene、artifact 白名单、README 明确命令 |
| 本地误用 Python 3.14/Conda 当前环境 | BIFF8 库不兼容 | 显式使用 `E:\Python 11\python.exe` 和 venv Python 路径 |
| PyInstaller 漏收 Vue 或中文模板 | Release 页面/生成失败 | staging 明确、spec 白名单、双平台黑盒测试、模板哈希 |
| PyInstaller 归档误报杀毒 | Windows 用户无法运行 | onedir、校验和/SBOM、后续代码签名；保留日志诊断入口 |
| Action/发布权限过大 | 供应链风险 | 固定 SHA、默认只读、发布 job 最小写权限、tag 校验/审批 |
| BIFF8 65,536 行和样式上限 | 大数据生成失败 | 生成前精确计数、样式复用、容量配置和边界测试 |

### 13.2 兼容性约束

- 本地后端开发：Windows，现有 Python 3.11，标准 `venv`。
- 前端开发：使用真实项目现有 Node/包管理器和 lockfile；当前机器已存在 Node 24.12.0 与 `npm.cmd` 11.6.2，但应以项目声明的 Node LTS 为准。
- 前端上传目前按任务书只保证 `.xlsx`；原始需求的 `.xls` 输入是否继续支持必须确认。
- 正式输出仅 `.xls`；不能把 `.xlsx` 改名为 `.xls`。
- Release 首期 Windows x64、Linux x64；macOS/ARM 和 Windows 代码签名另行确认。
- 源码模式需要 venv；Release 用户不需要 Python/Node/Excel/LibreOffice。

### 13.3 实施前待确认

1. **真实前端源码位置/分支**：当前仓库没有 Vue 文件，这是开始实施的首个阻塞项。
2. **正式操作/结果规则来源**：采用后端规则配置保持 v1，还是设计版本化 v2 可视化契约？推荐先用经确认的后端配置打通正式生成，再单独规划 v2。
3. **规则具体内容**：每种 `equipmentType` 的步骤、是否变比、结果和责任专业；设备编码覆盖和默认规则。
4. **地点类型与方向值域**：是否扩展支持 `车辆段/停车场/其他/双向`，以及它们如何写入当前四列表格。
5. **站点 D 列**：`docs/prompt.md` 要求结束站点留空，多数指定成品重复填写开始站点；推荐规范优先留空。
6. **前端 v1 是否继续四字段全必填**：可保持字段存在，但页面是否应按地点类型条件禁用并发送空字符串。
7. **输入格式**：现有前端任务只支持 `.xlsx`，原需求是否仍要求 `.xls` 两列表输入。
8. **Mock 延迟**：仅开发模式默认 2 秒，正式模式 0 秒，是否接受。
9. **生产鉴权**：前端带 Bearer token，但后端是否需要校验 token；本地单机版可暂不验证，公网部署必须验证。
10. **容量目标**：最大测试内容/步骤/结果数和期望响应时间。
11. **Release 平台和签名**：是否只需 Windows x64，是否具备代码签名证书；Linux 是否需要正式发布。

## 14. 完成定义

只有同时满足以下条件才算完成：

- 复用真实 Vue 前端，没有生成第二套页面或破坏现有鉴权、上传、解析和 RuleBuilder。
- 前端按冻结 v1 JSON 调用 `/api/excel/process`，保持 camelCase、数组顺序、`sortIndex` 和中文。
- Mock 联调和正式生成明确隔离；正式规则缺失时不会输出伪成品。
- Python 后端完全运行在 `backend/.venv`，本地解释器来自现有 `E:\Python 11\python.exe` 或经批准的现有 Conda Python。
- `backend/requirements.txt` 和 `backend/requirements-dev.txt` 完整可复现；Git 和 GitHub artifacts 中没有 venv、site-packages 原目录、缓存或解释器。
- 输出确为从指定底表复制的合法 BIFF8 `.xls`，五表、格式、跨表行号和 `end` 正确，参数公式只有终止行。
- Vue Loading、错误 Blob、文件名和 `.xls` 下载在 Chrome/Edge 正常。
- 自动化测试、Excel/WPS 人工验收、Windows/Linux 打包冒烟通过。
- PR CI 全绿；手动 Workflow 只生成 dry-run artifacts；`v*` tag 能产生带校验和和 SBOM 的正式 GitHub Release。
- `data/raw/`、`data/excelforge/test.json`、三份需求文档以及用户已有工作树改动未被修改、删除或误提交。
