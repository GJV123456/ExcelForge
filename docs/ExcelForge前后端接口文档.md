# ExcelForge 前后端接口文档

## 1. 文档说明

本文档根据当前前端源码整理，后端应以本文档中的实际请求结构为准。

当前前端使用：

- 前端框架：Vue 3
- HTTP 客户端：Axios
- 开发服务器：Vite
- 后端建议框架：FastAPI
- 前端请求前缀：`/api`
- 开发环境默认后端地址：`http://127.0.0.1:8000`

前端相关源码位置：

- `frontend/src/api/auth.js`
- `frontend/src/api/excel.js`
- `frontend/src/utils/request.js`
- `frontend/src/views/Login.vue`
- `frontend/src/views/Workspace.vue`
- `frontend/src/utils/formalLocation.js`
- `frontend/src/utils/excelParser.js`
- `frontend/src/utils/equipmentSubtype.js`

## 2. 系统处理流程

```text
用户登录
    ↓
用户选择测试地点
    ↓
用户上传 Excel
    ↓
前端读取第一个工作表
    ↓
前端识别 Excel 类型
    ↓
前端解析每一行数据
    ↓
前端生成 generatedContent
    ↓
前端识别设备子类型和状态/动作
    ↓
前端组装 testLocation 和 testContents
    ↓
POST /api/v2/excel/process
    ↓
后端校验数据并生成 Excel 文件
    ↓
返回 Excel 二进制文件流
    ↓
前端自动下载最终导入表.xls
```

后端不需要接收原始 Excel 文件，也不需要重新解析 Excel。前端已经完成 Excel 读取、类型识别、字段提取和测试内容拼接，后端主要负责校验、业务规则处理、正式文件生成和文件返回。

## 3. 服务地址和环境配置

### 3.1 前端开发环境

前端默认通过 Vite 代理访问后端：

```text
前端地址：http://localhost:5173
后端地址：http://127.0.0.1:8000
```

前端 `vite.config.js` 中会把 `/api` 请求转发到：

```env
VITE_API_PROXY_TARGET=http://127.0.0.1:8000
```

后端启动示例：

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 3.2 生产或跨域环境

如果前端和后端不是同源部署，可以设置：

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

此时浏览器会直接请求后端地址，后端必须配置 CORS。

建议允许的开发来源：

```text
http://localhost:5173
http://127.0.0.1:5173
```

后端至少需要允许：

- `GET`
- `POST`
- `OPTIONS`

允许请求头：

- `Content-Type`
- `Authorization`

因为前端需要读取下载文件名，后端跨域时必须暴露：

```text
Content-Disposition
```

建议同时暴露：

```text
X-Request-ID
```

## 4. 认证接口

### 4.1 用户登录

```http
POST /api/auth/login
Content-Type: application/json
```

### 4.2 请求体

```json
{
  "username": "admin",
  "password": "123456",
  "agree": true,
  "remember": true
}
```

### 4.3 请求字段

| 字段 | 类型 | 是否必填 | 说明 |
|---|---|---:|---|
| `username` | string | 是 | 用户名 |
| `password` | string | 是 | 密码 |
| `agree` | boolean | 是 | 是否同意隐私条款和服务条款。当前前端默认传 `true` |
| `remember` | boolean | 是 | 是否记住密码。该字段主要由前端使用，后端可以接收但不必保存密码 |

### 4.4 成功响应

HTTP 状态码：

```text
200 OK
```

推荐响应：

```json
{
  "data": {
    "token": "eyJhbGciOi...",
    "userInfo": {
      "username": "admin",
      "name": "管理员"
    }
  }
}
```

字段说明：

| 字段 | 类型 | 说明 |
|---|---|---|
| `data.token` | string | 登录令牌。前端会保存到 `localStorage` |
| `data.userInfo` | object | 用户信息 |
| `data.userInfo.username` | string | 用户名 |
| `data.userInfo.name` | string | 用户显示名称 |

前端登录成功后保存的数据结构：

```json
{
  "token": "eyJhbGciOi...",
  "userInfo": {
    "username": "admin",
    "name": "管理员"
  }
}
```

保存位置：

```text
localStorage.excelforge_user
```

### 4.5 登录失败响应

建议返回：

```json
{
  "message": "用户名或密码错误",
  "code": "INVALID_CREDENTIALS"
}
```

建议状态码：

- `400`：请求参数不符合业务要求
- `401`：用户名或密码错误
- `422`：请求体字段类型错误

前端登录页会优先读取：

```text
response.data.message
```

因此登录错误响应中建议提供 `message` 字段。

### 4.6 前端模拟登录注意事项

开发环境下，前端默认使用模拟登录，不会请求后端：

```env
VITE_ENABLE_MOCK_AUTH=true
```

模拟账号：

```text
用户名：admin
密码：123456
```

要测试真实后端登录，必须设置：

```env
VITE_ENABLE_MOCK_AUTH=false
```

修改 `.env.local` 后需要重新启动 Vite。

## 5. Axios 请求公共规则

前端 Axios 默认配置：

```text
baseURL = VITE_API_BASE_URL || ""
timeout = 30000 毫秒
```

当本地存储中存在 token 时，前端会自动添加：

```http
Authorization: Bearer <token>
```

示例：

```http
Authorization: Bearer eyJhbGciOi...
```

后端如果返回 `401`，前端会：

1. 删除 `localStorage.excelforge_user`
2. 跳转到 `/login`

正式后端应在需要鉴权的接口上校验 Authorization。

## 6. Excel 正式处理接口

### 6.1 当前前端实际调用的接口

```http
POST /api/v2/excel/process
Content-Type: application/json
Authorization: Bearer <token>
```

源码位置：

```text
frontend/src/api/excel.js
frontend/src/views/Workspace.vue
```

当前工作台点击“生成正式文件”后调用的是：

```javascript
processExcelV2(payload)
```

对应地址：

```text
/api/v2/excel/process
```

### 6.2 旧接口

前端还保留了一个接口方法：

```http
POST /api/excel/process
```

但当前 `Workspace.vue` 没有使用它。后端可以暂时保留该接口用于兼容旧版本，但当前正式联调应优先实现：

```text
POST /api/v2/excel/process
```

### 6.3 成功响应

成功时不要返回 JSON，而要返回 Excel 二进制文件流。

HTTP 状态码：

```text
200 OK
```

响应头建议：

```http
Content-Type: application/vnd.ms-excel
Content-Disposition: attachment; filename="最终导入表.xls"; filename*=UTF-8''%E6%9C%80%E7%BB%88%E5%AF%BC%E5%85%A5%E8%A1%A8.xls
```

前端会：

1. 将响应按 Blob 处理
2. 读取 `Content-Disposition`
3. 提取文件名
4. 创建临时下载链接
5. 自动下载文件

如果后端没有返回有效文件名，前端默认使用：

```text
最终导入表.xls
```

注意：当前前端下载工具只接受 `.xls` 文件名。后端返回 `.xlsx` 时，前端会回退到默认的 `.xls` 文件名。

## 7. Excel 处理请求体

完整结构：

```json
{
  "testLocation": {
    "type": "站点",
    "direction": "",
    "startStation": "嘉庚体育馆站",
    "endStation": "嘉庚体育馆站",
    "stations": [
      "嘉庚体育馆站"
    ]
  },
  "testContents": [
    {
      "equipmentChinese": "站厅B端会务室",
      "signalDescription": "",
      "additionalCode": "",
      "sortIndex": 1,
      "generatedContent": "站厅B端会务室温感N1L1D22",
      "equipmentCode": "N1L1D22",
      "equipmentType": "温感",
      "equipmentSubtype": "",
      "equipmentStatus": ""
    }
  ]
}
```

顶层字段：

| 字段 | 类型 | 是否必填 | 说明 |
|---|---|---:|---|
| `testLocation` | object | 是 | 测试地点 |
| `testContents` | array | 是 | Excel 数据转换后的测试内容数组 |

前端会按照 Excel 原始顺序发送 `testContents`，后端不能排序、去重或重组。

## 8. testLocation 字段

### 8.1 字段说明

| 字段 | 类型 | 是否必填 | 说明 |
|---|---|---:|---|
| `type` | string | 是 | 地点类型：`站点`、`区间`、`全线` |
| `direction` | string | 否 | 行车方向：`上行`、`下行`，也可能为空 |
| `startStation` | string | 否 | 开始站点 |
| `endStation` | string | 否 | 结束站点 |
| `stations` | array[string] | 条件必填 | 站点类型下的站点列表 |

### 8.2 站点类型

前端选择 `站点` 后：

- `direction` 固定为空字符串
- `startStation` 为站点列表第一个站点
- `endStation` 与 `startStation` 相同
- `stations` 保存所有选择的站点

示例：

```json
{
  "type": "站点",
  "direction": "",
  "startStation": "嘉庚体育馆站",
  "endStation": "嘉庚体育馆站",
  "stations": [
    "嘉庚体育馆站",
    "清水站"
  ]
}
```

当前前端校验要求：

- 至少填写一个站点
- `startStation` 和 `endStation` 必须相同

后端应保存完整的 `stations` 数组，不要只保留第一个站点。

### 8.3 区间类型

示例：

```json
{
  "type": "区间",
  "direction": "上行",
  "startStation": "嘉庚体育馆站",
  "endStation": "清水站"
}
```

当前前端校验要求：

- `startStation` 必填
- `endStation` 必填
- `direction` 可以为空

### 8.4 全线类型

示例：

```json
{
  "type": "全线",
  "direction": "",
  "startStation": "",
  "endStation": ""
}
```

当前前端会清空开始站点、结束站点和站点数组。

## 9. testContents 字段

每一个 `testContents` 对象对应 Excel 中的一行有效数据。

| 字段 | 类型 | 是否必填 | 数据来源 |
|---|---|---:|---|
| `equipmentChinese` | string | 是 | `设备中文` 列；Type A 时使用 `测试内容` |
| `signalDescription` | string | 否 | `信号描述` 列，没有时为空字符串 |
| `additionalCode` | string | 否 | `附加编号` 列，没有时为空字符串 |
| `sortIndex` | positive integer | 是 | 前端按 Excel 原始行顺序生成 |
| `generatedContent` | string | 是 | 前端根据规则拼接的最终测试内容 |
| `equipmentCode` | string | 否 | `设备编码` 列或 Type A 自动提取结果 |
| `equipmentType` | string | 是 | `设备类型` 列或 Type A 的 `类型` 列 |
| `equipmentSubtype` | string | 否 | 前端根据设备类型和文本识别的子类型 |
| `equipmentStatus` | string | 否 | 前端从设备中文或信号描述中识别的状态/动作 |

建议后端模型使用字符串默认值 `""`，不要把空字段强制改成 `null`。

### 9.1 equipmentChinese

Type B：

```text
row["设备中文"]
```

Type A：

```text
row["测试内容"]
```

### 9.2 signalDescription

如果 Excel 没有“信号描述”表头，前端仍然会发送：

```json
"signalDescription": ""
```

### 9.3 additionalCode

如果 Excel 没有“附加编号”表头，前端仍然会发送：

```json
"additionalCode": ""
```

### 9.4 sortIndex

前端从 `1` 开始按有效数据行递增：

```json
[
  { "sortIndex": 1 },
  { "sortIndex": 2 },
  { "sortIndex": 3 }
]
```

后端要求：

- 必须是正整数
- 不允许重复
- 必须按照请求数组顺序递增
- 不允许后端自行排序
- 不允许后端去重

### 9.5 generatedContent

Type B：

```text
按照前端 RuleBuilder 当前规则拼接
```

常见规则：

```text
设备中文 + 设备类型 + 设备编码
```

当表格存在可选字段时，前端可能拼接：

```text
设备中文 + 设备类型 + 设备编码 + 信号描述 + 附加编号 + 自定义文字
```

特殊模块默认只使用：

```text
设备中文
```

Type A：

```text
测试内容
```

后端不要重新拼接或修改 `generatedContent`，应把它作为前端已经确认的最终测试内容。

### 9.6 equipmentCode

Type B：

```text
row["设备编码"]
```

Type A：

前端会尝试从“测试内容”文本中自动提取设备编号，支持类似：

```text
N1L1M33
N1L1D03
FF1-B905
FP1-B7
SEF-B1
SEF-B601
603-FP1-B3
```

如果提取不到，前端发送空字符串。

### 9.7 equipmentSubtype

该字段由前端根据以下信息识别：

- `equipmentType`
- `equipmentChinese`
- `equipmentCode`
- `signalDescription`
- `generatedContent`

当前可能识别的子类型包括：

- `吸气式主机`
- `感温电缆`
- `感温光纤`
- `AFC`
- `EPS`
- `垂直电梯`
- `防火卷帘`
- `400V切非`
- `消防泵`
- `防火门`
- `门禁`
- `电气火灾、消防电源、应急疏散`
- `声光报警器`
- `PA`
- `消火栓点灯`
- `主机手自动、人工确认`
- `气灭测试`
- `区间电话`
- `站内电话`

识别不到时发送：

```json
"equipmentSubtype": ""
```

### 9.8 equipmentStatus

前端优先从 `equipmentChinese` 和 `equipmentCode` 组合文本中识别；如果没有识别到，再从 `signalDescription` 中识别。

识别不到时发送：

```json
"equipmentStatus": ""
```

当前业务中可能出现的状态/动作包括：

- `预警`
- `火警`
- `故障`
- `远程复位`
- `报警反馈`
- `故障反馈`
- `综合故障`
- `上行感温光纤报警反馈`
- `下行感温光纤报警反馈`
- `AFC切非反馈`
- `AFC切非`
- `AFC状态反馈`
- `AFC释放控制`
- `状态反馈`
- `启动控制`
- `垂直电梯状态反馈`
- `垂直电梯归首控制`
- `防火卷帘一次降落反馈`
- `防火卷帘一次降落控制`
- `防火卷帘二次降落反馈`
- `防火卷帘二次降落控制`
- `消防泵手/自动反馈`
- `消防泵动作反馈`
- `消防泵故障反馈`
- `压力开关动作反馈`
- `流量开关动作反馈`
- `高水位报警反馈`
- `低水位报警反馈`
- `最低水位报警反馈`
- `稳压泵动作反馈`
- `稳压泵故障反馈`
- `消防泵启动控制`
- `巡检柜报警反馈`
- `信号阀动作反馈`
- `水流指示器动作反馈`
- `门禁释放反馈`
- `门禁释放`
- `动作状态`
- `监视模块故障状态`
- `开控制命令`
- `控制模块故障状态`
- `关控制命令`

后端不要因为该字段为空而拒绝整个请求，除非具体业务规则明确要求必须有状态。

## 10. Excel 类型说明

### 10.1 Type A：人工处理版

必需表头：

```text
测试内容
类型
```

示例：

| 测试内容 | 类型 |
|---|---|
| 站厅B端车控室烟感N1L1D01 | 烟感 |

前端转换结果：

```json
{
  "equipmentChinese": "站厅B端车控室烟感N1L1D01",
  "signalDescription": "",
  "additionalCode": "",
  "sortIndex": 1,
  "generatedContent": "站厅B端车控室烟感N1L1D01",
  "equipmentCode": "N1L1D01",
  "equipmentType": "烟感",
  "equipmentSubtype": "",
  "equipmentStatus": ""
}
```

Type A 的 `equipmentCode` 由前端尝试从 `测试内容` 中提取。

### 10.2 Type B：原始设备版

必需表头：

```text
设备编码
设备类型
设备中文
```

可选表头：

```text
信号描述
附加编号
```

示例：

| 设备编码 | 设备类型 | 设备中文 | 信号描述 | 附加编号 |
|---|---|---|---|---|
| N1L2M28 | 监视模块 | 站厅B端应急照明BH-EPS状态反馈 |  |  |

前端默认规则通常为：

```text
设备中文 + 设备类型 + 设备编码
```

如果存在 `信号描述` 或 `附加编号` 表头，用户可以在前端规则编辑器中添加这些字段。

## 11. 感温光纤特殊字段

当前前端会额外识别 `intervalName`，例如：

```text
角石区间上行
```

识别结果：

```json
{
  "intervalName": "角石"
}
```

但需要特别注意：

```text
intervalName 目前只用于前端实时预览，不会放进 testContents 请求体。
```

如果后端后续需要这个字段，需要前端额外修改 payload 组装逻辑，当前后端不能假设一定能收到 `intervalName`。

## 12. 请求示例

### 12.1 普通温感数据

```json
{
  "testLocation": {
    "type": "站点",
    "direction": "",
    "startStation": "嘉庚体育馆站",
    "endStation": "嘉庚体育馆站",
    "stations": [
      "嘉庚体育馆站"
    ]
  },
  "testContents": [
    {
      "equipmentChinese": "站厅B端会务室",
      "signalDescription": "",
      "additionalCode": "",
      "sortIndex": 1,
      "generatedContent": "站厅B端会务室温感N1L1D22",
      "equipmentCode": "N1L1D22",
      "equipmentType": "温感",
      "equipmentSubtype": "",
      "equipmentStatus": ""
    }
  ]
}
```

### 12.2 监视模块 EPS

```json
{
  "testLocation": {
    "type": "全线",
    "direction": "",
    "startStation": "",
    "endStation": ""
  },
  "testContents": [
    {
      "equipmentChinese": "站厅B端应急照明BH-EPS状态反馈",
      "signalDescription": "",
      "additionalCode": "",
      "sortIndex": 1,
      "generatedContent": "站厅B端应急照明BH-EPS状态反馈监视模块N1L2M28",
      "equipmentCode": "N1L2M28",
      "equipmentType": "监视模块",
      "equipmentSubtype": "EPS",
      "equipmentStatus": "状态反馈"
    }
  ]
}
```

### 12.3 带信号描述和附加编号

```json
{
  "testLocation": {
    "type": "区间",
    "direction": "上行",
    "startStation": "嘉庚体育馆站",
    "endStation": "清水站"
  },
  "testContents": [
    {
      "equipmentChinese": "站台B端风机",
      "signalDescription": "动作状态",
      "additionalCode": "1",
      "sortIndex": 1,
      "generatedContent": "站台B端风机风阀N1L1M01动作状态1",
      "equipmentCode": "N1L1M01",
      "equipmentType": "风阀",
      "equipmentSubtype": "",
      "equipmentStatus": "动作状态"
    }
  ]
}
```

### 12.4 特殊模块

```json
{
  "testLocation": {
    "type": "站点",
    "direction": "",
    "startStation": "嘉庚体育馆站",
    "endStation": "嘉庚体育馆站",
    "stations": [
      "嘉庚体育馆站"
    ]
  },
  "testContents": [
    {
      "equipmentChinese": "厅A照明配电室内2号消防电话分机",
      "signalDescription": "",
      "additionalCode": "",
      "sortIndex": 1,
      "generatedContent": "厅A照明配电室内2号消防电话分机",
      "equipmentCode": "",
      "equipmentType": "特殊模块",
      "equipmentSubtype": "站内电话",
      "equipmentStatus": ""
    }
  ]
}
```

## 13. 后端校验要求

### 13.1 顶层校验

后端应校验：

- 请求体必须是 JSON
- `testLocation` 必须存在
- `testContents` 必须是数组
- `testContents` 不能为空

### 13.2 地点校验

建议规则：

- `type` 只能是 `站点`、`区间`、`全线`
- `站点` 类型必须有至少一个 `stations`
- `站点` 类型的 `startStation` 和 `endStation` 应与首个站点一致
- `区间` 类型必须有 `startStation` 和 `endStation`
- `全线` 类型的开始和结束站点应为空
- `direction` 允许为空
- `direction` 非空时只能是 `上行` 或 `下行`

### 13.3 测试内容校验

建议规则：

- `sortIndex` 必须是大于 0 的整数
- 按请求数组顺序严格递增
- `generatedContent` 应为字符串
- 设备编号、子类型、状态允许为空字符串
- 不允许后端改变数组顺序
- 不允许后端删除重复数据

### 13.4 字符串处理

后端建议：

- 对字段做首尾空格清理
- 保留字段内部空格
- 空值统一为 `""`
- 不要把空字符串强制改成 `null`
- 不要把用户内容当成 Excel 公式执行

## 14. 错误响应格式

推荐统一格式：

```json
{
  "detail": "地点类型不能为空",
  "code": "INVALID_LOCATION_TYPE",
  "path": [
    "testLocation",
    "type"
  ],
  "requestId": "9c4c2f1d-5bd7-4a01-a9a2-7a7ec9a1a111"
}
```

字段说明：

| 字段 | 类型 | 说明 |
|---|---|---|
| `detail` | string | 前端会优先显示该字段 |
| `code` | string | 稳定的错误代码，便于后续处理 |
| `path` | array | 错误字段路径，可选 |
| `requestId` | string | 请求追踪编号，可选但建议提供 |

前端当前会根据 HTTP 状态码显示以下兜底提示：

| 状态码 | 前端提示 |
|---:|---|
| `400` | 请求内容不符合业务要求 |
| `422` | 提交参数校验失败 |
| `500` 及以上 | 文件生成失败 |
| 其他 | 请求处理失败 |

如果后端返回的 JSON 中有非空字符串 `detail`，前端会优先显示 `detail`。

## 15. 处理失败示例

### 15.1 地点类型错误

```http
HTTP/1.1 400 Bad Request
Content-Type: application/json
```

```json
{
  "detail": "地点类型只能是站点、区间或全线",
  "code": "INVALID_LOCATION_TYPE",
  "path": ["testLocation", "type"]
}
```

### 15.2 请求体结构错误

```http
HTTP/1.1 422 Unprocessable Entity
Content-Type: application/json
```

```json
{
  "detail": "提交参数校验失败",
  "code": "VALIDATION_ERROR",
  "path": ["testContents", 0, "sortIndex"]
}
```

### 15.3 文件生成失败

```http
HTTP/1.1 500 Internal Server Error
Content-Type: application/json
```

```json
{
  "detail": "正式文件生成失败",
  "code": "FILE_GENERATION_FAILED",
  "requestId": "9c4c2f1d-5bd7-4a01-a9a2-7a7ec9a1a111"
}
```

## 16. 健康检查接口

虽然当前前端没有主动调用健康检查，但建议后端提供：

```http
GET /api/health
```

成功响应：

```json
{
  "status": "ok",
  "service": "ExcelForge backend",
  "version": "1.0.0"
}
```

## 17. 生成历史接口建议

当前前端页面会在生成成功后刷新近期记录，并支持查看和重新下载：

```http
GET /api/generations
GET /api/generations/{generationId}
GET /api/generations/{generationId}/download
```

建议记录：

- 生成编号
- 请求编号
- 生成时间
- 文件名
- 地点信息
- 数据条数
- 设备类型
- 生成结果
- 错误信息

`POST /api/v2/excel/process` 成功时会返回 `X-Generation-ID` 响应头。后端
会保存本次生成的完整 `.xls` 二进制内容，历史下载接口直接返回该文件，
不会再次执行规则匹配。旧记录如果没有保存文件内容，下载时返回
`GENERATION_FILE_NOT_FOUND`。

## 18. CORS 和联调检查清单

前后端联调时，如果浏览器 F12 的 Network 中没有请求，先检查：

1. 前端是否设置了 `VITE_ENABLE_MOCK_AUTH=false`
2. 当前按钮是否调用 `/api/v2/excel/process`
3. 后端是否运行在 `127.0.0.1:8000`
4. Vite 代理目标是否正确
5. 浏览器是否出现 CORS 错误
6. 请求方法是否为 `POST`
7. Request Payload 是否包含 `testLocation` 和 `testContents`
8. 后端是否返回 `application/vnd.ms-excel`
9. 响应是否为非空 Blob
10. `Content-Disposition` 是否包含 `.xls` 文件名

典型成功请求：

```text
POST http://localhost:5173/api/v2/excel/process
```

开发环境下浏览器看到的是前端代理地址，但实际会被 Vite 转发到：

```text
http://127.0.0.1:8000/api/v2/excel/process
```

## 19. 后端实现建议

推荐目录：

```text
backend/
├── app/
│   ├── main.py
│   ├── api/
│   │   ├── auth.py
│   │   └── excel.py
│   ├── schemas/
│   │   ├── auth.py
│   │   └── excel.py
│   ├── services/
│   │   ├── auth_service.py
│   │   └── excel_service.py
│   └── utils/
│       └── response.py
├── tests/
├── requirements.txt
└── README.md
```

FastAPI 请求模型建议直接使用 camelCase 字段，以便和前端保持一致，或者使用 Pydantic alias 映射，但对外 JSON 字段必须保持 camelCase。

## 20. 当前接口结论

当前前端真正需要后端优先实现的接口只有两个：

```text
POST /api/auth/login
POST /api/v2/excel/process
```

其中：

- 登录接口返回 JSON
- Excel 处理接口返回 Excel Blob
- Excel 处理接口接收 JSON，不接收 multipart 文件
- 前端已经负责 Excel 解析
- 后端必须保留 testContents 原始顺序
- 后端必须接收空字符串字段
- 后端必须正确处理中文文件名
- 后端必须支持 `Authorization: Bearer <token>`
