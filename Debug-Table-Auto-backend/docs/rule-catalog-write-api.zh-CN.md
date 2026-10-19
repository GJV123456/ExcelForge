# 测试表规则维护接口文档

文档版本：2026-09-08  
适用范围：Vue 前端对 SQLite 中“设备类型 → 测试内容 → 操作步骤 → 输出结果 → 责任专业”规则进行查询和维护。

后端只提供 JSON API，不负责页面、树形控件或交互状态。前端可以自行实现设备类型选择、树形展开、表单编辑、增加和删除按钮。

## 1. 规则层级

```text
设备类型
  └─ 测试内容规则
       └─ 操作步骤（一个或多个）
            └─ 输出结果（一个或多个）
                 └─ 责任专业（一个或多个）
```

例如“烟感”规则：

```text
烟感
├─ 现场用烟枪吹烟，触发烟感报警
│  ├─ 现场：烟感灯亮红色
│  ├─ FAS主机：收到烟感火警
│  ├─ FAS图文工作站：显示烟感火警，图元和位置显示正确
│  └─ 综合监控：收到烟感火警报警、事件、位置正确、推图功能正常
└─ 现场设备断电，模拟故障状态
   ├─ FAS主机：收到烟感故障状态
   ├─ FAS图文工作站：显示烟感故障，图元和位置显示正确
   └─ 综合监控：收到烟感故障报警、事件、位置正确、推图功能正常
```

## 2. 基础约定

- 服务地址：`http://127.0.0.1:8000`
- 前端开发时建议使用相对路径：`/api/...`
- 请求和响应均为 UTF-8 JSON。
- 字段名使用 camelCase。
- 所有列表均已按 `sortOrder`、数据库 ID 稳定排序，前端不要按文本重新排序。
- 每个响应都会包含 `X-Request-ID`。
- 当前登录 token 仅兼容现有登录流程，目录接口暂未强制鉴权。

## 3. 前端维护流程

推荐流程：

1. 调用设备类型列表接口。
2. 用户选择“烟感”等设备类型。
3. 调用测试规则列表接口，传入设备类型 code 或 name。
4. 展示返回的 `operationSteps` 树。
5. 用户编辑、删除或新增步骤/结果。
6. 点击保存时，提交该测试内容规则的完整树结构。
7. 保存成功后，使用响应中的最新 `data` 刷新页面。

注意：当前后端采用“测试内容聚合保存”，没有单独的“修改步骤 ID”或“删除结果 ID”接口。步骤和结果的增删改都通过一次 `PUT /api/catalog/test-contents/{id}` 完成。

## 4. 查询设备类型

### 请求

```http
GET /api/catalog/equipment-types?includeDisabled=false
```

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | ---: | --- |
| `includeDisabled` | boolean | 否 | 是否包含停用设备类型，默认 `false` |

### 响应

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
  "meta": { "count": 1 }
}
```

前端下拉框建议保存 `id` 和 `code`，显示 `name`。查询规则时可使用 `code` 或 `name`。

### 新增设备类型及完整层级

设备类型、子类型和状态/动作可以一次提交保存。父类型 `code` 和子类型 `code` 不需要前端填写，后端会在事务中自动生成；状态/动作名称由前端配置。任一层级失败时整次提交回滚。

```http
POST /api/catalog/equipment-types
Content-Type: application/json
```

```json
{
  "name": "监视模块",
  "description": "",
  "sortOrder": 10,
  "isEnabled": true,
  "subtypes": [
    {
      "name": "吸气式主机",
      "sortOrder": 1,
      "isEnabled": true,
      "statuses": ["预警", "火警", "故障", "远程复位"]
    }
  ]
}
```

响应中的父类型 `code` 和子类型 `code` 仅用于查询、关联和展示，不应再次做成可编辑输入框。已有设备类型更新时不传 `subtypes`，后端会保留原有子类型，避免旧页面保存基础资料时覆盖层级数据。

## 5. 查询设备类型下的规则

### 请求

```http
GET /api/catalog/test-contents?equipmentType=烟感&includeDisabled=false
```

`equipmentType` 可传设备类型 `code`（如 `SMOKE`）或中文名称（如 `烟感`），不区分大小写。

### 响应

```json
{
  "data": [
    {
      "id": 1,
      "code": "RULE_SMOKE",
      "content": "烟感",
      "description": "",
      "revision": 1,
      "sortOrder": 1,
      "isEnabled": true,
      "equipmentSubtype": "",
      "equipmentStatus": "",
      "equipmentType": {
        "id": 1,
        "code": "SMOKE",
        "name": "烟感"
      },
      "operationSteps": [
        {
          "id": 1,
          "description": "现场用烟枪吹烟，触发烟感报警",
          "ratioChange": "否",
          "sortOrder": 1,
          "results": [
            {
              "id": 1,
              "description": "现场：烟感灯亮红色",
              "sortOrder": 1,
              "responsibleDisciplines": [
                { "id": 1, "code": "AUTOMATION", "name": "自动化" }
              ]
            }
          ]
        }
      ]
    }
  ],
  "meta": { "count": 1 }
}
```

### 前端展示建议

- 设备类型下拉框：使用 `equipment-types`。
- 设备类型选中后：使用 `test-contents?equipmentType=...`。
- 一个设备类型可能有多条测试内容规则，前端应展示 `data` 中的全部规则。
- 操作步骤使用 `operationSteps` 展开。
- 输出结果使用某个步骤的 `results` 展开。
- GET 返回的 `id` 只用于识别记录；写入时不要把 `id` 放入写请求体。

## 6. 查询单条规则

```http
GET /api/catalog/test-contents/{testContentId}
```

成功响应：

```json
{ "data": { "id": 1, "content": "烟感", "operationSteps": [] } }
```

不存在时返回：

```http
404 Not Found
```

```json
{
  "detail": "测试内容不存在或未启用",
  "code": "CATALOG_TEST_CONTENT_NOT_FOUND",
  "requestId": "..."
}
```

## 7. 新增测试内容规则

通常规则数据已由管理员导入；如果前端需要新增一条“测试内容规则”，调用：

```http
POST /api/catalog/test-contents
Content-Type: application/json
```

请求体：

```json
{
  "equipmentTypeId": 1,
  "code": "SMOKE_CUSTOM_01",
  "content": "烟感自定义规则",
  "equipmentSubtype": "",
  "equipmentStatus": "",
  "description": "",
  "revision": 1,
  "sortOrder": 2,
  "isEnabled": true,
  "operationSteps": [
    {
      "description": "现场用烟枪吹烟，触发烟感报警",
      "ratioChange": "否",
      "sortOrder": 1,
      "isEnabled": true,
      "results": [
        {
          "description": "现场：烟感灯亮红色",
          "sortOrder": 1,
          "isEnabled": true,
          "responsibleDisciplineIds": [1]
        }
      ]
    }
  ]
}
```

成功响应：`200 OK`，返回 `{ "data": <完整测试内容规则> }`。

## 8. 修改、增加、删除操作步骤和输出结果

### 请求

```http
PUT /api/catalog/test-contents/{testContentId}
Content-Type: application/json
```

请求体必须提交该规则的完整内容和完整步骤树。例如修改烟感第二条操作步骤，并给它增加一个输出结果：

```json
{
  "equipmentTypeId": 1,
  "code": "RULE_SMOKE",
  "content": "烟感",
  "equipmentSubtype": "",
  "equipmentStatus": "",
  "description": "",
  "revision": 2,
  "sortOrder": 1,
  "isEnabled": true,
  "operationSteps": [
    {
      "description": "现场用烟枪吹烟，触发烟感报警",
      "ratioChange": "否",
      "sortOrder": 1,
      "isEnabled": true,
      "results": [
        {
          "description": "现场：烟感灯亮红色",
          "sortOrder": 1,
          "isEnabled": true,
          "responsibleDisciplineIds": [1]
        },
        {
          "description": "FAS主机：收到烟感火警",
          "sortOrder": 2,
          "isEnabled": true,
          "responsibleDisciplineIds": [1]
        }
      ]
    },
    {
      "description": "现场设备断电，模拟故障状态（已修改）",
      "ratioChange": "否",
      "sortOrder": 2,
      "isEnabled": true,
      "results": [
        {
          "description": "FAS主机：收到烟感故障状态",
          "sortOrder": 1,
          "isEnabled": true,
          "responsibleDisciplineIds": [1]
        },
        {
          "description": "FAS图文工作站：显示烟感故障，图元和位置显示正确",
          "sortOrder": 2,
          "isEnabled": true,
          "responsibleDisciplineIds": [1]
        },
        {
          "description": "综合监控：收到烟感故障报警、事件、位置正确、推图功能正常",
          "sortOrder": 3,
          "isEnabled": true,
          "responsibleDisciplineIds": [1]
        },
        {
          "description": "新增故障确认结果",
          "sortOrder": 4,
          "isEnabled": true,
          "responsibleDisciplineIds": [1]
        }
      ]
    }
  ]
}
```

### 三种操作如何表达

| 前端操作 | 请求体做法 |
| --- | --- |
| 修改操作步骤 | 修改对应 `operationSteps[index].description` 等字段 |
| 删除操作步骤 | 从 `operationSteps` 数组移除，然后重新编号 `sortOrder` |
| 新增操作步骤 | 向 `operationSteps` 数组追加对象 |
| 修改输出结果 | 修改对应 `results[index].description` 或责任专业 |
| 删除输出结果 | 从步骤的 `results` 数组移除，然后重新编号 `sortOrder` |
| 新增输出结果 | 向步骤的 `results` 数组追加对象 |

后端保存时会在一个 SQLite 事务中重建该测试内容下的操作步骤、输出结果和责任专业关联。保存成功后，响应中的子项 ID 可能与保存前不同，前端应使用响应数据替换本地树。

### 最少数量限制

- 至少一个操作步骤；
- 每个操作步骤至少一个输出结果；
- 每个输出结果至少一个责任专业；
- `ratioChange` 只能是 `是` 或 `否`；
- 同一规则内 `operationSteps[].sortOrder` 不能重复；
- 同一步骤内 `results[].sortOrder` 不能重复；
- 同一结果内 `responsibleDisciplineIds` 不能重复。

成功响应：`200 OK`，返回保存后的完整规则。

## 9. 删除测试内容规则

```http
DELETE /api/catalog/test-contents/{testContentId}
```

成功响应：`204 No Content`。

删除的是整条测试内容规则及其全部操作步骤、输出结果和责任专业关联，不是只删除一条步骤。前端删除前应弹出确认框。

如果只想删除一个操作步骤或一个输出结果，不调用 DELETE，而是使用第 8 节的 PUT 提交删减后的完整树。

## 10. 责任专业接口

### 查询责任专业

```http
GET /api/catalog/disciplines?includeDisabled=false
```

响应示例：

```json
{
  "data": [
    {
      "id": 1,
      "code": "AUTOMATION",
      "name": "自动化",
      "description": "",
      "sortOrder": 1,
      "isEnabled": true
    }
  ],
  "meta": { "count": 1 }
}
```

结果输出保存时提交 `responsibleDisciplineIds`，不要提交责任专业名称。页面显示使用返回的 `name`。

### 新增/修改/删除责任专业

后端同时提供：

```http
POST   /api/catalog/disciplines
PUT    /api/catalog/disciplines/{disciplineId}
DELETE /api/catalog/disciplines/{disciplineId}
```

写入字段：

```json
{
  "code": "AUTOMATION",
  "name": "自动化",
  "description": "",
  "sortOrder": 1,
  "isEnabled": true
}
```

已有结果引用的责任专业不能直接删除，建议先将其停用。

## 11. 通用错误响应

```json
{
  "detail": "可展示给用户的错误说明",
  "code": "稳定错误代码",
  "requestId": "请求 ID",
  "path": ["可选", "字段路径"]
}
```

常见错误：

| HTTP | code | 说明 |
| ---: | --- | --- |
| 404 | `CATALOG_TEST_CONTENT_NOT_FOUND` | 测试内容不存在 |
| 404 | `CATALOG_EQUIPMENT_TYPE_NOT_FOUND` | 设备类型不存在 |
| 404 | `CATALOG_DISCIPLINE_NOT_FOUND` | 责任专业不存在 |
| 409 | `CATALOG_TEST_CONTENT_CODE_CONFLICT` | 测试内容 code 重复 |
| 409 | `CATALOG_OPERATION_STEP_SORT_CONFLICT` | 操作步骤 sortOrder 重复 |
| 409 | `CATALOG_RESULT_OUTPUT_SORT_CONFLICT` | 输出结果 sortOrder 重复 |
| 409 | `CATALOG_DISCIPLINE_SORT_CONFLICT` | 责任专业顺序重复 |
| 422 | `REQUEST_VALIDATION_ERROR` | 字段类型、必填项或数组约束错误 |

## 12. Axios 调用示例

```js
export function getEquipmentTypes(params = {}) {
  return request.get('/api/catalog/equipment-types', { params })
}

export function getTestContents(params = {}) {
  return request.get('/api/catalog/test-contents', { params })
}

export function getDisciplines(params = {}) {
  return request.get('/api/catalog/disciplines', { params })
}

export function createTestContent(data) {
  return request.post('/api/catalog/test-contents', data)
}

export function updateTestContent(id, data) {
  return request.put(`/api/catalog/test-contents/${id}`, data)
}

export function deleteTestContent(id) {
  return request.delete(`/api/catalog/test-contents/${id}`)
}
```

## 13. 与正式导出接口的关系

```http
POST /api/excel/process
```

正式导出请求只需要提交前端解析好的 `testContents`。当某条记录没有传 `operationSteps` 时，后端会按 `equipmentSubtype` 优先、`equipmentType` 兜底，从 SQLite 读取最新规则并自动补全。

因此：

- 规则维护页面修改成功后，不需要修改导出接口；
- 下一次导出会自动使用数据库中的最新步骤和输出结果；
- 前端导出时不要把规则编辑页面的临时草稿混入请求，除非明确要覆盖数据库规则。

