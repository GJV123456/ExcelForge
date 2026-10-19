# ExcelForge 规则数据库接口文档（前端开发版）

文档版本：2026-08-12

适用后端：`backend` 分支当前实现

## 1. 接口用途与边界

规则数据库用于保存以下可复用关系：

```text
设备类型
  └─ 测试内容
       └─ 操作步骤
            └─ 结果输出
                 └─ 一个或多个责任专业
```

当前后端使用 SQLite，首次请求目录接口时只创建空表，不预置业务规则。
当前接口仅支持读取，不支持前端新增、修改、删除或导入规则。

本文包含：

- 登录兼容接口；
- 设备类型查询；
- 测试内容及其操作步骤、结果输出、责任专业的嵌套查询；
- 成功生成记录、成品 SHA-256 与 Excel 行号对应关系查询；
- 与现有 v2 Excel 生成请求的字段对应关系；
- 通用错误处理和 Axios 调用示例。

## 2. 基础约定

### 2.1 服务地址

开发环境建议继续通过 Vite proxy 请求相对地址：

```text
/api/*
```

后端本地默认地址通常为：

```text
http://127.0.0.1:8000
```

FastAPI 调试文档：

```text
GET /docs
```

### 2.2 数据格式

- 请求与 JSON 响应使用 UTF-8；
- JSON 字段保持 camelCase；
- 布尔查询参数请发送 `true` 或 `false`；
- 列表顺序已经由后端按数据库中的 `sortOrder` 和内部 ID 稳定排序；
- 前端不应再自行按中文文本重排或去重。

### 2.3 请求 ID

每个响应都包含：

```text
X-Request-ID: <请求标识>
```

前端记录错误日志时应同时记录该值，便于定位后端日志。

## 3. 账号与登录接口

空数据库首次使用时先创建首个账号，注册成功会返回会话；已有账号后注册接口关闭。

### 3.1 首次创建账号

```http
POST /api/auth/register
Content-Type: application/json
```

```json
{
  "username": "operator",
  "password": "secret123",
  "confirmPassword": "secret123",
  "displayName": "操作员",
  "agree": true
}
```

### 3.2 登录

### 3.3 请求

```http
POST /api/auth/login
Content-Type: application/json
```

请求体：

```json
{
  "username": "operator",
  "password": "secret123",
  "agree": true,
  "remember": false
}
```

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | ---: | --- |
| `username` | string | 是 | 用户名，去除首尾空白后不能为空 |
| `password` | string | 是 | 密码，去除首尾空白后不能为空 |
| `agree` | boolean | 是 | 必须为 `true` |
| `remember` | boolean | 是 | 控制数据库会话有效期，不保存明文密码 |

### 3.4 成功响应

```http
HTTP/1.1 200 OK
Content-Type: application/json
```

```json
{
  "data": {
    "token": "后端生成的不透明 token",
    "userInfo": {
      "username": "operator",
      "name": "操作员"
    }
  }
}
```

前端应从以下位置读取：

```js
const token = response.data.data.token
const userInfo = response.data.data.userInfo
```

如果项目的 Axios 响应拦截器已经返回 `response.data`，则相应改为：

```js
const token = response.data.token
const userInfo = response.data.userInfo
```

### 3.5 登录错误

| HTTP 状态 | `code` | 含义 |
| ---: | --- | --- |
| 400 | `AUTH_AGREEMENT_REQUIRED` | 未同意条款 |
| 401 | `AUTH_INVALID_CREDENTIALS` | 用户名或密码错误 |
| 422 | `REQUEST_VALIDATION_ERROR` | 字段缺失或类型错误 |
| 409 | `AUTH_REGISTRATION_CLOSED` | 数据库已有首个账号，不能重复初始化 |

密码使用 PBKDF2-SHA256 摘要存储在 SQLite 中；修改密码会吊销该用户已有会话，退出登录会吊销当前会话。

## 4. 获取设备类型

### 4.1 请求

```http
GET /api/catalog/equipment-types
```

可选查询参数：

| 参数 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `includeDisabled` | boolean | `false` | 是否包含已停用设备类型；普通业务页面不要开启 |

示例：

```http
GET /api/catalog/equipment-types?includeDisabled=false
```

### 4.2 成功响应

```json
{
  "data": [
    {
      "id": 1,
      "code": "SMOKE",
      "name": "烟感",
      "description": "",
      "sortOrder": 1,
      "isEnabled": true
    }
  ],
  "meta": {
    "count": 1
  }
}
```

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | integer | 数据库内部 ID，不应作为前端永久枚举值 |
| `code` | string | 稳定业务代码，建议作为下拉选项值和查询条件 |
| `name` | string | 中文显示名，也是 v2 请求中的 `equipmentType` 候选值 |
| `description` | string | 说明，可能为空字符串 |
| `sortOrder` | integer | 后端排序值 |
| `isEnabled` | boolean | 是否启用 |
| `meta.count` | integer | 本次返回的记录数，不是分页总数 |

## 5. 获取测试规则列表

### 5.1 请求

```http
GET /api/catalog/test-contents
```

可选查询参数：

| 参数 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `equipmentType` | string | 无 | 按设备类型 `code` 或 `name` 精确匹配；英文代码不区分大小写 |
| `includeDisabled` | boolean | `false` | 是否包含停用记录；普通业务页面不要开启 |

示例：

```http
GET /api/catalog/test-contents?equipmentType=SMOKE
```

也可以使用中文名称：

```http
GET /api/catalog/test-contents?equipmentType=%E7%83%9F%E6%84%9F
```

### 5.2 成功响应

```json
{
  "data": [
    {
      "id": 1,
      "code": "SMOKE_STANDARD",
      "content": "站厅B端车控室烟感",
      "description": "",
      "revision": 1,
      "sortOrder": 1,
      "isEnabled": true,
      "equipmentType": {
        "id": 1,
        "code": "SMOKE",
        "name": "烟感"
      },
      "operationSteps": [
        {
          "id": 1,
          "description": "触发设备报警",
          "ratioChange": "否",
          "sortOrder": 1,
          "results": [
            {
              "id": 1,
              "description": "系统正确显示报警",
              "sortOrder": 1,
              "responsibleDisciplines": [
                {
                  "id": 1,
                  "code": "FAS",
                  "name": "FAS"
                }
              ]
            }
          ]
        }
      ]
    }
  ],
  "meta": {
    "count": 1
  }
}
```

### 5.3 测试规则字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | integer | 测试内容内部 ID |
| `code` | string | 稳定的测试规则代码 |
| `content` | string | 可复用测试内容文本或模板 |
| `description` | string | 规则说明，可能为空 |
| `revision` | integer | 规则修订号 |
| `sortOrder` | integer | 规则展示顺序 |
| `isEnabled` | boolean | 是否启用 |
| `equipmentType` | object | 关联设备类型摘要 |
| `operationSteps` | array | 操作步骤，已排序；可能为空数组 |

### 5.4 操作步骤字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | integer | 操作步骤内部 ID |
| `description` | string | 操作步骤文本 |
| `ratioChange` | string | 只会是 `是` 或 `否` |
| `sortOrder` | integer | 操作步骤顺序 |
| `results` | array | 该步骤对应的结果输出；可能为空数组 |

### 5.5 结果输出字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | integer | 结果输出内部 ID |
| `description` | string | 预期结果文本 |
| `sortOrder` | integer | 结果顺序 |
| `responsibleDisciplines` | array | 一个或多个责任专业；数据未完整配置时可能为空 |

### 5.6 责任专业字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | integer | 责任专业内部 ID |
| `code` | string | 稳定业务代码 |
| `name` | string | 显示名；提交 v2 时使用此值 |

## 6. 获取单条测试规则

### 6.1 请求

```http
GET /api/catalog/test-contents/{id}
```

示例：

```http
GET /api/catalog/test-contents/1
```

### 6.2 成功响应

响应中的 `data` 是第 5 节所述的一条完整测试规则，不再包含 `meta`：

```json
{
  "data": {
    "id": 1,
    "code": "SMOKE_STANDARD",
    "content": "站厅B端车控室烟感",
    "description": "",
    "revision": 1,
    "sortOrder": 1,
    "isEnabled": true,
    "equipmentType": {
      "id": 1,
      "code": "SMOKE",
      "name": "烟感"
    },
    "operationSteps": []
  }
}
```

不存在或已停用时：

```http
HTTP/1.1 404 Not Found
```

```json
{
  "detail": "测试内容不存在或未启用",
  "code": "CATALOG_TEST_CONTENT_NOT_FOUND",
  "requestId": "请求 ID"
}
```

单条接口当前没有 `includeDisabled` 参数。

## 7. 与 v2 Excel 生成接口的对应关系

目录接口返回“可复用规则”，现有正式 Excel 接口接收“具体设备的生成实例”。二者不要直接
整体透传。

```http
POST /api/excel/process
```

主要字段对应：

| 目录接口字段 | v2 请求字段 | 处理说明 |
| --- | --- | --- |
| `equipmentType.name` | `equipmentType` | 使用显示名 |
| `operationSteps[].description` | `operationSteps[].description` | 直接复制 |
| `operationSteps[].ratioChange` | `operationSteps[].ratioChange` | 直接复制 |
| `operationSteps[].results[].description` | `operationSteps[].results[].description` | 直接复制 |
| `responsibleDisciplines[].name` | `responsibleDisciplines[]` | 从对象数组映射成名称字符串数组 |
| `sortOrder` | 无直接对应 | 只控制规则展示/展开顺序 |

以下字段仍由现有前端业务流程负责：

- `sortIndex`：原始 Excel 设备行顺序，不等于数据库的 `sortOrder`；
- `generatedContent`：具体设备最终生成内容；
- `equipmentCode`：来自用户上传的设备记录；
- `testLocation`：来自地点配置页面。

特别注意：数据库的 `content` 当前只是可复用文本/模板字段，后端尚未定义占位符语法或自动
拼接规则。前端在业务规则得到确认前，不应自行猜测如何把 `content` 与设备编码拼接成
`generatedContent`。

正式生成成功响应会增加：

```text
X-Generation-ID: 生成记录 UUID
```

只有生成文件自检成功且数据库事务完整提交后，后端才返回文件。前端如需在下载后展示或查询
追溯记录，应保存该响应头；不要从文件名反推数据库记录。

责任专业映射示例：

```js
const operationSteps = catalogItem.operationSteps.map((step) => ({
  description: step.description,
  ratioChange: step.ratioChange,
  results: step.results.map((result) => ({
    description: result.description,
    responsibleDisciplines: result.responsibleDisciplines.map(
      (discipline) => discipline.name,
    ),
  })),
}))
```

## 8. 查询生成历史与对应关系

### 8.1 历史列表

```http
GET /api/generations?limit=50&offset=0
```

| 参数 | 类型 | 默认值 | 说明 |
| --- | --- | ---: | --- |
| `limit` | integer | 50 | 返回数量，范围 1～200 |
| `offset` | integer | 0 | 跳过数量，必须大于等于 0 |

列表按生成时间倒序返回。`meta.count` 是本页实际条数，不是全部历史总数。
`counts.disciplines` 表示责任专业关联项出现次数，不是去重后的专业数量。

```json
{
  "data": [
    {
      "id": "7aa88944-1a25-49f2-88d7-7ea19a6a5cab",
      "requestId": "HTTP 请求 ID",
      "generatedAt": "2026-08-12T22:30:00+08:00",
      "filename": "最终导入表_角江路站_类型A_类型B_20260812223000.xls",
      "outputSha256": "64 位大写 SHA-256",
      "testLocation": {
        "type": "站点",
        "direction": "",
        "startStation": "角江路站",
        "endStation": "角江路站"
      },
      "counts": {
        "testContents": 2,
        "operationSteps": 3,
        "resultOutputs": 9,
        "disciplines": 11
      }
    }
  ],
  "meta": {"count": 1}
}
```

### 8.2 单次生成详情

```http
GET /api/generations/{generationId}
```

详情在上述摘要字段之外增加 `testContents` 嵌套快照。关键字段：

| 字段 | 说明 |
| --- | --- |
| `sequenceIndex` | 在当次请求或父级数组中的 1 起始顺序 |
| `sortIndex` | 前端上传设备的原始顺序索引 |
| `excelRowNumber` | 对应工作表中的 Excel 可见行号，从 1 开始 |
| `generatedContent` | 生成时的测试内容快照 |
| `operationSteps` | 生成时的步骤快照及其 `操作步骤` 表行号 |
| `results` | 生成时的结果快照及其 `结果输出` 表行号 |
| `responsibleDisciplines` | 生成时的责任专业名称和顺序快照 |

```json
{
  "data": {
    "id": "7aa88944-1a25-49f2-88d7-7ea19a6a5cab",
    "requestId": "HTTP 请求 ID",
    "generatedAt": "2026-08-12T22:30:00+08:00",
    "filename": "最终导入表_角江路站_类型A_20260812223000.xls",
    "outputSha256": "64 位大写 SHA-256",
    "testLocation": {
      "type": "站点",
      "direction": "",
      "startStation": "角江路站",
      "endStation": "角江路站"
    },
    "counts": {
      "testContents": 1,
      "operationSteps": 1,
      "resultOutputs": 1,
      "disciplines": 1
    },
    "testContents": [
      {
        "sequenceIndex": 1,
        "sortIndex": 1,
        "generatedContent": "内容A",
        "equipmentCode": "A01",
        "equipmentType": "类型A",
        "excelRowNumber": 3,
        "operationSteps": [
          {
            "sequenceIndex": 1,
            "description": "步骤A1",
            "ratioChange": "否",
            "excelRowNumber": 3,
            "results": [
              {
                "sequenceIndex": 1,
                "description": "结果A11",
                "excelRowNumber": 3,
                "responsibleDisciplines": [
                  {"sequenceIndex": 1, "name": "FAS"}
                ]
              }
            ]
          }
        ]
      }
    ]
  }
}
```

不存在时返回 HTTP 404 和错误码 `GENERATION_NOT_FOUND`。

## 9. Axios 调用示例

以下示例使用原始 Axios 响应结构；如果项目拦截器已经解包 `response.data`，调用处需要减少
一层 `.data`。

```js
import axios from 'axios'

export function login(form) {
  return axios.post('/api/auth/login', form)
}

export function getEquipmentTypes(params = {}) {
  return axios.get('/api/catalog/equipment-types', { params })
}

export function getTestContents(params = {}) {
  return axios.get('/api/catalog/test-contents', { params })
}

export function getTestContent(id) {
  return axios.get(`/api/catalog/test-contents/${encodeURIComponent(id)}`)
}

export function getGenerations(params = {}) {
  return axios.get('/api/generations', { params })
}

export function getGeneration(id) {
  return axios.get(`/api/generations/${encodeURIComponent(id)}`)
}
```

页面调用示例：

```js
const response = await getTestContents({
  equipmentType: selectedEquipmentTypeCode,
  includeDisabled: false,
})

const rules = response.data.data
```

## 10. 通用错误响应

业务错误和校验错误统一为 JSON：

```json
{
  "detail": "可展示给用户的错误说明",
  "code": "稳定错误代码",
  "requestId": "请求 ID",
  "path": ["可选", "字段路径"]
}
```

前端错误提示优先级建议：

```js
const message =
  error.response?.data?.detail ||
  error.response?.data?.message ||
  '服务器请求失败'
```

| HTTP 状态 | 含义 |
| ---: | --- |
| 400 | 业务条件不满足 |
| 401 | 登录凭据错误 |
| 404 | 目录记录不存在或未启用 |
| 422 | 参数缺失、类型错误或路径参数格式错误 |
| 500 | 后端未预期错误 |
| 503 | 登录凭据尚未配置 |

## 11. 当前限制

1. 数据库初始为空，需要后续通过经确认的数据维护方式填充。
2. 当前没有新增、编辑、删除、CSV 导入或导出接口。
3. 规则目录当前没有分页、关键词模糊搜索、ETag 或增量同步；规则列表返回符合条件的全部
   数据。生成历史使用 `limit/offset`，但当前不返回全量总数。
4. `includeDisabled=true` 主要供后端诊断。设备类型和测试内容会返回 `isEnabled`，但当前嵌套
   操作步骤、结果输出、责任专业没有返回各自的 `isEnabled`，因此普通前端页面必须保持
   `includeDisabled=false`。
5. 登录 token 尚未在后端接口上执行鉴权。
6. `content` 到 `generatedContent` 的模板规则尚未定义。
7. 生成历史保存提交快照和 Excel 行号，但 v2 请求尚未携带规则目录的稳定 ID，因此不会按
   文本猜测并回填目录规则外键。

## 12. CSV 作为后端数据库的可行性

### 12.1 结论

可以使用 CSV，但不建议将“多份 CSV 文件”直接作为当前系统的长期主数据库。更合适的方案是：

```text
人工维护 CSV
  ↓ 一次性完整校验
导入 SQLite
  ↓
现有只读目录 API
```

这样既保留 Excel/CSV 易编辑、易审核的优点，也保留 SQLite 的外键、唯一约束、事务和稳定查询。

### 12.2 纯 CSV 至少需要的文件

若完全改为 CSV，为保留现有关系，至少需要：

| CSV 文件 | 对应数据 |
| --- | --- |
| `equipment_types.csv` | 设备类型 |
| `test_contents.csv` | 测试内容，并关联设备类型 |
| `operation_steps.csv` | 操作步骤，并关联测试内容 |
| `result_outputs.csv` | 结果输出，并关联操作步骤 |
| `disciplines.csv` | 责任专业 |
| `result_output_disciplines.csv` | 结果输出与责任专业的多对多关系 |

单个 CSV 无法自然表达一条测试内容包含多步骤、每步包含多结果、每个结果又包含多个责任专业的
关系，除非在单元格中引入 JSON 或自定义分隔符；这种做法会让校验、转义和人工维护更困难。

### 12.3 纯 CSV 的适用条件

只有同时满足以下条件时，纯 CSV 才比较合适：

- 数据量小；
- 运行时只读；
- 同一时刻只有一个维护者；
- 可以在服务启动时一次性加载到内存；
- 可以接受修改 CSV 后重启服务；
- 不需要跨多文件的在线事务和审计记录。

### 12.4 纯 CSV 必须补充的机制

如果以后确认采用纯 CSV，后端仍必须实现：

1. UTF-8 编码约定，面向 Excel 人工编辑时建议 UTF-8 BOM；
2. 稳定业务 `code` 作为跨文件关联键，不能依赖易变化的行号；
3. 启动时检查重复 code、缺失外键、重复 sortOrder、非法 `ratioChange`；
4. 六份文件全部校验成功后才切换新数据，不能逐文件覆盖；
5. 版本清单和每个 CSV 的 SHA-256，防止文件组合版本不一致；
6. 写临时目录后原子切换，避免前端读到一半新、一半旧的数据；
7. 明确 Windows 可执行文件目录和 Linux 用户数据目录的写权限差异。

这些机制本质上是在 CSV 外重新实现数据库已经提供的一部分能力。

### 12.5 推荐决策

- 主存储：继续使用当前 SQLite；
- 人工整理：后续提供 6 份固定列的 CSV 模板；
- 导入方式：后端管理命令或受鉴权的管理接口完成全量校验、事务导入；
- 前端业务页面：继续只调用本文的只读 API，不直接读取 CSV；
- CSV 列结构、覆盖策略和责任人确认前，不实现导入功能。

