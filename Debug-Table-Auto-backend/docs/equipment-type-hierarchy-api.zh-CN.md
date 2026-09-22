# 设备类型与子类型接口

规则管理页面使用两层设备目录：设备类型（父类型）→ 子类型。`equipmentStatus` 仍可存在于 Excel 解析后的原始数据中，但不属于规则目录，不参与规则保存、展示或匹配。

## 获取完整树

```http
GET /api/catalog/equipment-hierarchy
```

可选参数：`includeDisabled=true` 同时返回停用的父类型和子类型。默认只返回启用项。

响应示例：

```json
{
  "data": [
    {
      "id": 61,
      "code": "TYPE_FIRE_DAMPER",
      "name": "防火阀",
      "description": "",
      "sortOrder": 0,
      "isEnabled": true,
      "subtypes": [
        {
          "id": 1,
          "parentEquipmentTypeId": 61,
          "code": "61_01",
          "name": "手动防火阀",
          "sortOrder": 1,
          "isEnabled": true
        },
        {
          "id": 2,
          "parentEquipmentTypeId": 61,
          "code": "61_02",
          "name": "电动防火阀",
          "sortOrder": 2,
          "isEnabled": true
        }
      ]
    }
  ],
  "meta": {"count": 1}
}
```

`meta.count` 是父类型数量。历史上被导入为独立顶层类型、但已配置为子类型的名称会从该树形响应中隐藏，数据库中的原记录仍保留。

## 按父类型获取子类型

```http
GET /api/catalog/equipment-types/{equipmentTypeId}/subtypes
```

响应格式为 `{ "data": [...], "meta": {"count": n} }`。父类型不存在或已停用（且未传 `includeDisabled=true`）返回 `404`，错误码为 `CATALOG_EQUIPMENT_TYPE_NOT_FOUND`。

## 当前已初始化的关系

- 防火阀：手动防火阀、电动防火阀
- 监视模块：吸气式主机、感温电缆、感温光纤、AFC、EPS、垂直电梯、防火卷帘、400V切非、消防泵、防火门、门禁、电气火灾、消防电源、应急疏散
- 控制模块：吸气式主机、感温电缆、AFC、EPS、垂直电梯、防火卷帘、400V切非、消防泵、PA、门禁、电气火灾、消防电源、应急疏散、声光报警器、消火栓点灯、主机手自动、人工确认
- 特殊模块：气灭测试、区间电话、站内电话

## 数据库初始化

已随当前数据库执行：

```powershell
python backend/scripts/seed_equipment_hierarchy.py --database backend/data/excelforge.sqlite3
```

重新执行该命令是幂等的，只会补充或恢复上述关系，不会删除规则。
