# 站点目录接口

责任专业由后端目录接口提供，前端不需要写死。使用 `GET /api/catalog/disciplines` 获取责任专业；规则结果中的 `responsibleDisciplines` 同样由后端返回。

站点目录使用 SQLite 的 `stations` 表，已初始化嘉庚体育馆站、东安站、美峰站、洪塘头站、潘涂站、官浔站、智谷云谷站、后吴站、西湖站、第三医院站、杜桥站、祥桥站、小西门站、同安一中站、同翔高新城站、寨阳站、洪塘头停车场站、寨阳车辆段。

## 查询

```http
GET /api/catalog/stations
GET /api/catalog/stations?includeDisabled=true
```

响应：

```json
{
  "data": [
    {
      "id": 1,
      "code": "STATION_001",
      "name": "嘉庚体育馆站",
      "description": "",
      "sortOrder": 1,
      "isEnabled": true
    }
  ],
  "meta": {"count": 18}
}
```

## 新增

```http
POST /api/catalog/stations
Content-Type: application/json
```

```json
{
  "code": "STATION_019",
  "name": "新站点",
  "description": "",
  "sortOrder": 19,
  "isEnabled": true
}
```

## 修改

```http
PUT /api/catalog/stations/{stationId}
```

请求体与新增相同。`code` 和 `name` 均不能与其他站点重复。

## 删除

```http
DELETE /api/catalog/stations/{stationId}
```

成功返回 `204 No Content`；不存在返回 `404`，错误码 `CATALOG_STATION_NOT_FOUND`。

## 责任专业

```http
GET /api/catalog/disciplines
POST /api/catalog/disciplines
PUT /api/catalog/disciplines/{disciplineId}
DELETE /api/catalog/disciplines/{disciplineId}
```

责任专业接口的请求和响应结构与原规则目录一致，字段为 `id`、`code`、`name`、`description`、`sortOrder`、`isEnabled`。


