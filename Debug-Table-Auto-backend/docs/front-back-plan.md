# ExcelForge 前后端联调实施计划

## 1. 目标

在现有 ExcelForge Vue 3 前端基础上，引入 Python FastAPI 后端，实现以下完整链路：

`Vue 前端解析 Excel → 前端生成测试内容 → 组装 JSON → POST 到 Python 后端 → Python 校验/处理数据 → 生成 xlsx → 以文件流返回 → 前端 Blob 下载`

本计划只定义实施步骤、接口契约、文件结构与验收条件，不在本阶段实现具体业务代码。

---

## 2. 现状与已确定约束

### 2.1 前端技术栈

现有任务书约定：

- Vue 3
- Vite
- Composition API
- `<script setup>`
- Element Plus
- Vue Router 4
- Pinia
- Axios
- SheetJS（xlsx）或 exceljs
- vuedraggable

前端职责保持不变：

- 用户鉴权
- Excel 上传
- Excel 解析
- Excel 类型判断
- 数据预览
- RuleBuilder 规则配置
- 生成测试内容
- 组装 JSON
- 调用后端接口
- 下载后端生成的 Excel 文件

### 2.2 后端职责

新增 Python 后端，负责：

- 接收前端 JSON
- 使用 Pydantic 校验数据
- 按 `sortIndex` 保持原始数据顺序
- 执行业务处理
- 后续接入数据库查询
- 使用 openpyxl 生成正式 Excel
- 以 xlsx 文件流返回前端

推荐技术栈：

- Python 3.12+
- FastAPI
- Uvicorn
- Pydantic
- openpyxl
- SQLAlchemy（仅在需要数据库时引入）

---

## 3. 当前 JSON 接口契约

当前版本不增加 `sourceData`、`generationRule` 等扩展字段。

保持一级结构只有：

```json
{
  "testLocation": {},
  "testContents": []
}
```

### 3.1 testLocation

结构：

```json
{
  "type": "站点",
  "direction": "上行",
  "startStation": "1",
  "endStation": "2"
}
```

字段要求：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `type` | string | 是 | 测试地点类型 |
| `direction` | string | 是 | 行车方向 |
| `startStation` | string | 是 | 开始站点 |
| `endStation` | string | 是 | 结束站点 |

### 3.2 testContents

数组中每条记录结构：

```json
{
  "sortIndex": 1,
  "generatedContent": "站厅B端车控室烟感N1L1D01",
  "equipmentCode": "N1L1D01",
  "equipmentType": "烟感"
}
```

字段要求：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `sortIndex` | integer | 是 | 原始 Excel 顺序索引 |
| `generatedContent` | string | 是 | 前端 RuleBuilder 最终生成的测试内容 |
| `equipmentCode` | string | 是 | 设备编码 |
| `equipmentType` | string | 是 | 设备类型 |

### 3.3 完整请求示例

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
    },
    {
      "sortIndex": 2,
      "generatedContent": "站厅B端站长室烟感N1L1D02",
      "equipmentCode": "N1L1D02",
      "equipmentType": "烟感"
    }
  ]
}
```

### 3.4 重要规则

Agent 不得擅自：

- 修改现有字段名
- 将 camelCase 改为 snake_case
- 对 `testContents` 去重
- 对 `testContents` 自动排序
- 重组用户上传数据
- 增加未经需求确认的必填字段
- 要求前端重新上传原始 Excel 到后端

后端必须把 `sortIndex` 视为顺序依据，但正常情况下应保持前端数组现有顺序。

---

## 4. API 设计

### 4.1 主接口

```text
POST /api/excel/process
```

请求：

```text
Content-Type: application/json
```

请求体：

```text
ExcelProcessRequest
```

成功响应：

```text
HTTP 200
Content-Type:
application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
```

响应内容：

- xlsx 文件流
- 默认文件名：`最终导入表.xlsx`

### 4.2 健康检查接口

增加：

```text
GET /api/health
```

建议返回：

```json
{
  "status": "ok"
}
```

用途：

- 检查 Python 服务是否启动
- 排除前端 Axios、代理、端口和 CORS 问题

### 4.3 错误响应

后端错误统一使用 JSON，例如：

```json
{
  "detail": "文件生成失败"
}
```

至少覆盖：

- 400：业务参数错误
- 422：Pydantic 请求格式校验失败
- 500：内部处理或 Excel 生成失败

前端 Blob 请求发生错误时，不得直接把 Blob 显示为 `[object Blob]`，需要尝试读取其中的 JSON 错误信息。

---

## 5. 推荐目录结构

假设仓库根目录为：

```text
ExcelForge/
```

保持现有前端目录不破坏，在根目录新增后端：

```text
ExcelForge/
├── frontend/
│   └── ...
│
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   │
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── excel.py
│   │   │
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   └── excel.py
│   │   │
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   └── excel_processor.py
│   │   │
│   │   └── utils/
│   │       ├── __init__.py
│   │       └── excel_writer.py
│   │
│   ├── tests/
│   │   ├── test_health.py
│   │   └── test_excel_process.py
│   │
│   ├── requirements.txt
│   └── README.md
│
└── README.md
```

如果当前项目已经是 Vue 项目根目录，不要求 Agent 强制移动现有源码。

在这种情况下允许采用：

```text
项目根目录/
├── src/
├── package.json
├── vite.config.js
├── backend/
└── ...
```

Agent 应优先适配现有目录，而不是为了符合模板大规模移动文件。

---

## 6. 后端数据模型

文件：

```text
backend/app/schemas/excel.py
```

定义三个 Pydantic Model：

### 6.1 TestLocation

字段：

```text
type: str
direction: str
startStation: str
endStation: str
```

### 6.2 TestContent

字段：

```text
sortIndex: int
generatedContent: str
equipmentCode: str
equipmentType: str
```

### 6.3 ExcelProcessRequest

字段：

```text
testLocation: TestLocation
testContents: list[TestContent]
```

### 验收条件

使用当前 `test.json` 等价的标准 JSON 请求时：

- FastAPI 返回的数据模型校验成功
- 字段值不被修改
- 中文内容保持正确
- `sortIndex` 保持整数
- 数组顺序保持不变

---

## 7. FastAPI 应用入口

文件：

```text
backend/app/main.py
```

任务：

1. 创建 FastAPI 应用
2. 注册 `/api/health`
3. 注册 Excel Router
4. 配置开发环境 CORS，或配合 Vite proxy
5. 不在 `main.py` 中编写复杂 Excel 业务逻辑

推荐：

```text
/api/excel/process
```

实现放在：

```text
backend/app/api/excel.py
```

### 验收条件

运行：

```bash
uvicorn app.main:app --reload
```

后：

```text
GET /api/health
```

返回 HTTP 200。

---

## 8. 第一阶段：实现 Mock 后端

在正式业务逻辑开发前，必须先完成端到端联调。

### 8.1 Mock process 接口

文件：

```text
backend/app/api/excel.py
```

接口：

```text
POST /api/excel/process
```

Mock 阶段执行：

1. 接收 `ExcelProcessRequest`
2. 校验 `testLocation`
3. 校验 `testContents`
4. 人为延迟约 2～3 秒
5. 使用 openpyxl 生成一个简单测试 xlsx
6. 将收到的数据写入测试 Excel
7. 返回文件流

Mock 文件至少包含：

| sortIndex | generatedContent | equipmentCode | equipmentType |
|---:|---|---|---|

### 8.2 Mock 阶段目的

验证完整流程：

```text
Vue
↓
JSON
↓
Axios
↓
FastAPI
↓
Pydantic
↓
openpyxl
↓
xlsx
↓
HTTP response
↓
Blob
↓
浏览器下载
```

### 验收条件

从现有 Vue 页面点击“生成正式文件”后：

1. 浏览器发出 `POST /api/excel/process`
2. Request Payload 与当前 JSON 契约一致
3. 后端成功读取全部记录
4. 前端进入 Loading 状态
5. Loading 至少持续到后端响应
6. 后端返回有效 `.xlsx`
7. 浏览器成功下载
8. 下载后的 Excel 可以被 Excel/WPS 正常打开
9. Excel 中的记录数量等于提交的 `testContents` 数量
10. 记录顺序与前端一致

---

## 9. 前端 API 层调整

优先使用任务书已有：

```text
src/api/excel.js
```

增加或整理：

```text
processExcel(payload)
```

请求配置必须包含：

```text
POST /api/excel/process
responseType: "blob"
```

禁止在 Vue 组件中重复编写完整 Axios 请求逻辑。

### 验收条件

`Workspace.vue` 或相关业务组件只调用封装后的 API 方法。

---

## 10. “生成正式文件”按钮

当前流程必须存在一个明确的最终提交动作。

按钮建议文字：

```text
生成正式文件
```

或者：

```text
提交并生成文件
```

按钮位于前端已经完成：

- 地点配置
- Excel 解析
- 测试内容生成
- 数据预览

之后。

### 点击前校验

至少检查：

- `testLocation.type`
- `testLocation.direction`
- `testLocation.startStation`
- `testLocation.endStation`
- `testContents.length > 0`

校验失败：

- 不发送 HTTP 请求
- 使用 Element Plus Message 明确提示

### 验收条件

所有必填项有效时才允许真正调用 `/api/excel/process`。

---

## 11. Loading 流程

现有任务书要求 Element Plus `v-loading`。

建议状态：

```text
isProcessing
```

流程：

```text
点击“生成正式文件”
↓
isProcessing = true
↓
发起 Axios 请求
↓
后端处理
↓
收到 Blob 或捕获错误
↓
finally
↓
isProcessing = false
```

Loading 文案：

```text
正在处理中...
正在生成最终导入文件，请稍候
```

### Mock 测试

通过后端故意延迟 2～3 秒检查 Loading。

不得通过在前端硬编码长延迟模拟“成功处理”。

### 验收条件

- 请求发出后立即出现 Loading
- 请求未完成时不能重复点击提交
- 成功后关闭 Loading
- 失败后也必须关闭 Loading
- 网络异常时不能永久卡在 Loading

---

## 12. Blob 下载处理

前端收到响应后：

1. 创建 Blob
2. 使用 `URL.createObjectURL`
3. 创建临时 `<a>`
4. 设置 `download`
5. 触发下载
6. 删除临时 `<a>`
7. 调用 `URL.revokeObjectURL`

默认文件名：

```text
最终导入表.xlsx
```

如后端返回：

```text
Content-Disposition
```

则优先解析后端文件名。

### 验收条件

- Chrome/Edge 可以下载
- 文件后缀为 `.xlsx`
- 文件不是 0 字节
- 文件可以正常打开
- 下载后不残留无效 Object URL

---

## 13. 开发环境前后端通信

优先使用 Vite proxy，避免开发阶段反复处理 CORS。

例如逻辑上：

```text
Vue:
http://localhost:5173

/api/*
↓ proxy

FastAPI:
http://127.0.0.1:8000
```

前端代码继续请求：

```text
/api/excel/process
```

而不是在业务代码中硬编码：

```text
http://127.0.0.1:8000/api/excel/process
```

### 验收条件

切换后端地址时只需修改 Vite/env 配置，不需要修改 Vue 业务组件。

---

## 14. 正式数据处理层

Mock 链路通过以后，再实现：

```text
backend/app/services/excel_processor.py
```

职责：

```text
ExcelProcessRequest
↓
读取 testLocation
↓
遍历 testContents
↓
业务规则处理
↓
数据库查询（以后需要时）
↓
生成目标数据结构
↓
交给 excel_writer
```

原则：

- API 层不直接堆积业务规则
- Excel 写入逻辑与业务数据处理逻辑分离
- 不修改前端定义的原始 `sortIndex`
- 不擅自排序
- 不擅自去重

### 验收条件

业务处理前后的每条数据都能通过 `sortIndex` 对应回原始 Excel 行。

---

## 15. Excel 生成层

文件：

```text
backend/app/utils/excel_writer.py
```

职责：

- 创建 Workbook
- 写入正式模板
- 写入处理结果
- 设置必要单元格值
- 保存临时文件或 BytesIO
- 返回给 API 层

不要在该文件中：

- 查询数据库
- 解析 HTTP 请求
- 判断登录权限
- 实现 Vue 相关逻辑

---

## 16. 临时文件策略

优先考虑：

```text
io.BytesIO
```

直接在内存中生成 xlsx。

如果后续正式模板较复杂，也允许使用：

```text
tempfile.NamedTemporaryFile
```

但必须确保：

- 请求完成后可以清理临时文件
- 不使用固定共享文件名
- 并发请求不会互相覆盖

---

## 17. 错误处理

### 前端至少区分

#### 网络错误

```text
服务器连接失败
```

#### 后端 HTTP 错误

```text
文件生成失败
```

如果后端返回具体 `detail`，优先展示后端信息。

#### 参数错误

例如：

```text
测试地点信息不完整
```

或者：

```text
没有可提交的测试内容
```

### 后端

不得把 Python traceback 直接作为正常 API 响应返回给用户。

日志中可以保留 traceback。

---

## 18. 数据量与性能约束

当前架构仍采用：

```text
Excel 在前端解析
↓
JSON 发送给 Python
```

第一版不改成上传原始 Excel 给后端。

需要注意：

`.xlsx` 文件大小不等于解压并转成 JSON 后的数据大小。

Agent 应：

1. 保留现有前端 20MB xlsx 限制
2. 不对大 JSON 做重复深拷贝
3. 不在多个 Pinia state 中重复保存同一份完整数据
4. 不在后端日志中打印完整大型 Payload
5. 对异常大的请求预留后端限制配置

本阶段无需设计分片上传。

---

## 19. 自动化测试

### 19.1 后端测试

文件：

```text
backend/tests/test_health.py
backend/tests/test_excel_process.py
```

至少覆盖：

#### health

```text
GET /api/health
→ 200
```

#### 有效 Payload

```text
POST /api/excel/process
→ 200
→ Content-Type 为 xlsx
```

#### 缺少 testLocation

```text
→ 422
```

#### testContents 类型错误

```text
→ 422
```

#### sortIndex 类型错误

```text
→ 422
```

#### 中文内容

确保：

```text
站厅B端车控室烟感N1L1D01
```

传输后不乱码。

---

## 20. 手工联调检查

使用浏览器 DevTools → Network。

点击：

```text
生成正式文件
```

检查：

### Request URL

```text
/api/excel/process
```

### Request Method

```text
POST
```

### Request Payload

确认：

```text
testLocation
testContents
```

均存在。

确认：

```text
sortIndex
generatedContent
equipmentCode
equipmentType
```

均存在。

### Response

确认：

```text
200
```

并且返回 xlsx。

---

## 21. 当前 JSON 契约冻结规则

在完成第一版前后端联调之前，视以下格式为 v1 契约：

```json
{
  "testLocation": {
    "type": "string",
    "direction": "string",
    "startStation": "string",
    "endStation": "string"
  },
  "testContents": [
    {
      "sortIndex": 1,
      "generatedContent": "string",
      "equipmentCode": "string",
      "equipmentType": "string"
    }
  ]
}
```

只有出现明确业务需求后，才允许新增类似：

```text
equipmentName
sourceData
generationRule
```

本阶段 Agent 不主动加入这些字段。

---

## 22. 实施顺序

### Phase 1：确认现有前端

检查：

```text
src/api/excel.js
src/utils/request.js
src/views/Workspace.vue
src/store/excel.js
vite.config.*
```

确认现有提交代码和数据结构。

**验收：**

明确最终 Payload 的实际构造位置。

---

### Phase 2：创建 FastAPI 骨架

建立：

```text
backend/app/main.py
backend/app/api/excel.py
backend/app/schemas/excel.py
```

增加：

```text
GET /api/health
```

**验收：**

FastAPI 正常启动，health 返回 200。

---

### Phase 3：实现 Pydantic Schema

严格映射当前 JSON。

**验收：**

当前 Payload 可以通过校验。

---

### Phase 4：实现 Mock `/api/excel/process`

接收 JSON，等待约 2～3 秒，生成测试 xlsx。

**验收：**

curl/Postman 可以得到可打开的 xlsx。

---

### Phase 5：前端 Axios 联调

修改或完善：

```text
src/api/excel.js
```

配置：

```text
responseType: "blob"
```

**验收：**

浏览器能收到后端 xlsx。

---

### Phase 6：实现最终提交按钮

把：

```text
前端规则生成完成
```

连接到：

```text
POST /api/excel/process
```

**验收：**

点击一次产生一次 API 请求。

---

### Phase 7：验证 Loading

使用 Mock 后端延迟。

**验收：**

请求期间 Loading 可见，成功或失败均能关闭。

---

### Phase 8：验证下载

**验收：**

成功下载：

```text
最终导入表.xlsx
```

且能打开。

---

### Phase 9：替换 Mock 业务

实现：

```text
backend/app/services/excel_processor.py
backend/app/utils/excel_writer.py
```

**验收：**

不修改 API 契约即可替换 Mock。

---

## 23. Definition of Done

本阶段完成必须同时满足：

- [ ] Vue 不再只是本地预览，存在明确的“生成正式文件”操作
- [ ] 点击后发送 `POST /api/excel/process`
- [ ] Request Body 使用当前 v1 JSON
- [ ] Python FastAPI 可以正确解析
- [ ] Pydantic 数据模型与前端完全对应
- [ ] 中文不乱码
- [ ] `sortIndex` 顺序保持
- [ ] 后端可以生成 `.xlsx`
- [ ] 前端使用 `responseType: "blob"`
- [ ] 浏览器可以正常下载文件
- [ ] 请求期间显示 Loading
- [ ] 成功后关闭 Loading
- [ ] 错误后也关闭 Loading
- [ ] 后端错误能被前端合理提示
- [ ] API 层、业务处理层、Excel 写入层已解耦
- [ ] 当前接口未擅自加入 `sourceData` / `generationRule`
- [ ] 至少完成 health 与 process 的基础后端测试

---

## 24. Agent 执行限制

执行本计划的编码 Agent 必须遵守：

1. 先阅读现有代码，再修改。
2. 不重构与本任务无关的前端代码。
3. 不改变现有 UI 风格。
4. 不改变现有 Excel 前端解析方案。
5. 不改变当前 JSON 字段名称。
6. 不擅自增加接口必填字段。
7. 不删除 `sortIndex`。
8. 不排序或去重用户数据。
9. 优先先打通 Mock 全链路，再开发正式业务。
10. 每个 Phase 完成后执行对应验收。
11. 如果现有项目路径与本计划示例不同，适配现有路径，不为匹配计划而大规模迁移目录。
12. 如果正式 Excel 的列结构或业务规则尚未明确，停止在 `excel_processor` 的业务实现边界，不猜测业务规则；保持 Mock/基础生成能力即可。

---

## 25. 本计划使用的输入资料

当前需求基础：

```text
/mnt/data/excelforge-prompt.md
/mnt/data/test.json
```

其中 `test.json` 展示的内容更接近浏览器 DevTools 展开的 JavaScript 对象表示。

Agent 实际发送 HTTP 请求时必须保证为合法 JSON，即字段名由双引号包裹，并由 Axios 使用 `application/json` 正常序列化。

