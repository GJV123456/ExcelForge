# 前端解析字段以json格式传入后端

`testLocation` 表示本次测试发生的位置

|      字段      |                       含义                       |
| :------------: | :----------------------------------------------: |
|     `type`     |      地点类型，比如 `站点`、`区间`、`全线`       |
|  `direction`   | 行车方向，比如 `上行`、`下行`。站点场景可以为空  |
| `startStation` |       开始站点。站点类型时，它就是当前站点       |
|  `endStation`  |      结束站点。站点类型时通常和开始站点一样      |
|   `stations`   | 站点列表。站点类型可支持多个站点，所以这里是数组 |

`testContents` 表示要生成测试内容的每一条设备数据。数组里每一个对象就是 Excel 里的一行数据。

|        字段         |                             含义                             |
| :-----------------: | :----------------------------------------------------------: |
| `equipmentChinese`  |            设备中文，来自 Excel 的 `设备中文` 列             |
| `signalDescription` |      信号描述，来自 Excel 的 `信号描述` 列；没有就为空       |
|  `additionalCode`   |      附加编号，来自 Excel 的 `附加编号` 列；没有就为空       |
|     `sortIndex`     |     原 Excel 中的顺序编号，用来保证后端生成文件时不乱序      |
| `generatedContent`  |                前端根据规则生成出来的测试内容                |
|   `equipmentCode`   |            设备编号，来自 Excel 的 `设备编码` 列             |
|   `equipmentType`   | 设备类型，来自 Excel 的 `设备类型` 列，比如温感、监视模块、控制模块 |
| `equipmentSubtype`  | 前端识别出来的子类型，比如 EPS、AFC、消防泵、感温电缆等；识别不到就为空 |
|  `equipmentStatus`  | 前端识别出来的状态/动作，比如 `状态反馈`、`启动控制`、`动作状态` 等；识别不到就为空 |



### 一、烟感和温感

#### 输入例表

| 设备编码 | 设备类型 |   设备中文    |
| :------: | :------: | :-----------: |
| N1L1D01  |   烟感   | 站厅B端车控室 |
| N1L1D02  |   烟感   | 站厅B端站长室 |
| N1L1D03  |   烟感   | 站厅B端站长室 |
| N1L1D22  |   温感   | 站厅B端会务室 |
| N1L1D23  |   温感   | 站厅B端会务室 |

#### json传入样例

```json
testContents:[
  {
    "equipmentChinese": "站厅B端车控室",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 1,
    "generatedContent": "站厅B端车控室烟感N1L1D01",
    "equipmentCode": "N1L1D01",
    "equipmentType": "烟感",
    "equipmentSubtype": "",
    "equipmentStatus": ""
  },
  {
    "equipmentChinese": "站厅B端会务室",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 4,
    "generatedContent": "站厅B端会务室温感N1L1D22",
    "equipmentCode": "N1L1D22",
    "equipmentType": "温感",
    "equipmentSubtype": "",
    "equipmentStatus": ""
  }
]

testLocation:{
  "type": "站点",
  "direction": "",
  "startStation": "体育馆站",
  "endStation": "体育馆站",
  "stations": [
    "体育馆站"
  ]
}
```

#### 烟感类型对应操作步骤与输出结果

![image-20260819150540028](D:\ExcelForge\docs\img\image-20260819150540028.png)

#### 温感类型对应操作步骤与输出结果

![image-20260819151652992](D:\ExcelForge\docs\img\image-20260819151652992.png)



### 二、区间手消报

#### 输入例表

| 设备编码   | 设备类型 | 设备中文              |
| ---------- | -------- | --------------------- |
| QT-N2L5M01 | 手报     | 天下路至龙山下行区间1 |
| QT-N2L5M02 | 消火栓   | 天下路至龙山下行区间1 |

#### json传入样例

```json
{
  "equipmentChinese": "天下路至龙山下行区间1",
  "signalDescription": "",
  "additionalCode": "",
  "sortIndex": 1,
  "generatedContent": "天下路至龙山下行区间1手报QT-N2L5M01报警及故障状态",
  "equipmentCode": "QT-N2L5M01",
  "equipmentType": "手报",
  "equipmentSubtype": "",
  "equipmentStatus": ""
},
{
  "equipmentChinese": "天下路至龙山下行区间1",
  "signalDescription": "",
  "additionalCode": "",
  "sortIndex": 2,
  "generatedContent": "天下路至龙山下行区间1消火栓QT-N2L5M02报警及故障状态",
  "equipmentCode": "QT-N2L5M02",
  "equipmentType": "消火栓",
  "equipmentSubtype": "",
  "equipmentStatus": ""
}

{
  "type": "区间",
  "direction": "上行",
  "startStation": "谷站",
  "endStation": "吴站",
}
```

#### 手报与消防栓对应操作步骤与输出结果

![image-20260819152024573](D:\ExcelForge\docs\img\image-20260819152024573.png)



### 三、监视模块-吸气式主机

#### 输入例表

| 设备编码 | 设备类型 | 设备中文             |
| -------- | -------- | -------------------- |
| N1L1M68  | 监视模块 | 站厅B端ASD-1预警     |
| N1L1M69  | 监视模块 | 站厅B端ASD-1火警     |
| N1L1M70  | 监视模块 | 站厅B端ASD-1故障     |
| N1L1M71  | 控制模块 | 站厅B端ASD-1远程复位 |

#### json传入样例

```json
{
  "equipmentChinese": "站厅B端ASD-1预警",
  "signalDescription": "",
  "additionalCode": "",
  "sortIndex": 1,
  "generatedContent": "站厅B端ASD-1预警监视模块N1L1M68",
  "equipmentCode": "N1L1M68",
  "equipmentType": "监视模块",
  "equipmentSubtype": "吸气式主机",
  "equipmentStatus": "预警"
},
{
  "equipmentChinese": "站厅B端ASD-1火警",
  "signalDescription": "",
  "additionalCode": "",
  "sortIndex": 2,
  "generatedContent": "站厅B端ASD-1火警监视模块N1L1M69",
  "equipmentCode": "N1L1M69",
  "equipmentType": "监视模块",
  "equipmentSubtype": "吸气式主机",
  "equipmentStatus": "火警"
},
{
  "equipmentChinese": "站厅B端ASD-1故障",
  "signalDescription": "",
  "additionalCode": "",
  "sortIndex": 3,
  "generatedContent": "站厅B端ASD-1故障监视模块N1L1M70",
  "equipmentCode": "N1L1M70",
  "equipmentType": "监视模块",
  "equipmentSubtype": "吸气式主机",
  "equipmentStatus": "故障"
},
{
  "equipmentChinese": "站厅B端ASD-1远程复位",
  "signalDescription": "",
  "additionalCode": "",
  "sortIndex": 4,
  "generatedContent": "站厅B端ASD-1远程复位控制模块N1L1M71",
  "equipmentCode": "N1L1M71",
  "equipmentType": "控制模块",
  "equipmentSubtype": "吸气式主机",
  "equipmentStatus": "远程复位"
}


{
  "type": "全线",
  "direction": "",
  "startStation": "",
  "endStation": ""
}
```



#### 对应操作步骤与输出结果

![image-20260819153050797](D:\ExcelForge\docs\img\image-20260819153050797.png)

![image-20260819153113391](D:\ExcelForge\docs\img\image-20260819153113391.png)







### 四、监视模块-感温电缆

#### 输入例表

| 设备编码 | 设备类型 | 设备中文                              |
| -------- | -------- | ------------------------------------- |
| N1L5M15  | 监视模块 | 站台B端感温电缆控制器6报警反馈        |
| N1L5M16  | 监视模块 | 站台B端感温电缆控制器6故障反馈        |
| N1L5M35  | 控制模块 | 站台B端感温电缆控制器电源（远程复位） |

#### json传入样例

```json
{
  "equipmentChinese": "站台B端感温电缆控制器6报警反馈",
  "signalDescription": "",
  "additionalCode": "",
  "sortIndex": 1,
  "generatedContent": "站台B端感温电缆控制器6报警反馈监视模块N1L5M15",
  "equipmentCode": "N1L5M15",
  "equipmentType": "监视模块",
  "equipmentSubtype": "感温电缆",
  "equipmentStatus": "报警反馈"
}，
{
  "equipmentChinese": "站台B端感温电缆控制器6故障反馈",
  "signalDescription": "",
  "additionalCode": "",
  "sortIndex": 2,
  "generatedContent": "站台B端感温电缆控制器6故障反馈监视模块N1L5M16",
  "equipmentCode": "N1L5M16",
  "equipmentType": "监视模块",
  "equipmentSubtype": "感温电缆",
  "equipmentStatus": "故障反馈"
}，
{
  "equipmentChinese": "站台B端感温电缆控制器电源（远程复位）",
  "signalDescription": "",
  "additionalCode": "",
  "sortIndex": 4,
  "generatedContent": "站台B端感温电缆控制器电源（远程复位）控制模块N1L5M35",
  "equipmentCode": "N1L5M35",
  "equipmentType": "控制模块",
  "equipmentSubtype": "感温电缆",
  "equipmentStatus": "远程复位"
}

```



#### 对应操作步骤与输出结果

![image-20260819154023156](D:\ExcelForge\docs\img\image-20260819154023156.png)



### 五、监视模块-感温光纤

#### 输入例表

| 设备编码 | 设备类型 | 设备中文                     |
| -------- | -------- | ---------------------------- |
| N1L1M23  | 监视模块 | 站厅B端感温光纤综合故障      |
| N1L1M24  | 监视模块 | 龙石区间上行感温光纤报警反馈 |
| N1L1M25  | 监视模块 | 龙石区间下行感温光纤报警反馈 |

#### json传入样例

```json
{
  "equipmentChinese": "站厅B端感温光纤综合故障",
  "signalDescription": "",
  "additionalCode": "",
  "sortIndex": 1,
  "generatedContent": "站厅B端感温光纤综合故障监视模块N1L1M23",
  "equipmentCode": "N1L1M23",
  "equipmentType": "监视模块",
  "equipmentSubtype": "感温光纤",
  "equipmentStatus": "综合故障",
  "intervalName": ""
},
{
  "equipmentChinese": "龙石区间上行感温光纤报警反馈",
  "signalDescription": "",
  "additionalCode": "",
  "sortIndex": 2,
  "generatedContent": "龙石区间上行感温光纤报警反馈监视模块N1L1M24",
  "equipmentCode": "N1L1M24",
  "equipmentType": "监视模块",
  "equipmentSubtype": "感温光纤",
  "equipmentStatus": "上行感温光纤报警反馈",
  "intervalName": "龙石"
}，
{
  "equipmentChinese": "龙石区间下行感温光纤报警反馈",
  "signalDescription": "",
  "additionalCode": "",
  "sortIndex": 3,
  "generatedContent": "龙石区间下行感温光纤报警反馈监视模块N1L1M25",
  "equipmentCode": "N1L1M25",
  "equipmentType": "监视模块",
  "equipmentSubtype": "感温光纤",
  "equipmentStatus": "下行感温光纤报警反馈",
  "intervalName": "龙石"
}
```



#### 对应操作步骤与输出结果

![image-20260819155500607](D:\ExcelForge\docs\img\image-20260819155500607.png)

### 六、监视模块、控制模块-AFC

#### 输入例表

| 设备编码 | 设备类型 | 设备中文           |
| -------- | -------- | ------------------ |
| N1L1M54  | 监视模块 | 站厅B端AFC切非反馈 |
| N1L1M55  | 控制模块 | 站厅B端AFC切非     |
| N1L1M28  | 控制模块 | 站厅B端AFC状态反馈 |
| N1L1M29  | 控制模块 | 站厅B端AFC释放控制 |

#### json传入样例

```json
{
  "equipmentChinese": "站厅B端AFC切非反馈",
  "signalDescription": "",
  "additionalCode": "",
  "sortIndex": 1,
  "generatedContent": "站厅B端AFC切非反馈监视模块N1L1M54",
  "equipmentCode": "N1L1M54",
  "equipmentType": "监视模块",
  "equipmentSubtype": "AFC",
  "equipmentStatus": "AFC切非反馈"
},
{
  "equipmentChinese": "站厅B端AFC切非",
  "signalDescription": "",
  "additionalCode": "",
  "sortIndex": 2,
  "generatedContent": "站厅B端AFC切非控制模块N1L1M55",
  "equipmentCode": "N1L1M55",
  "equipmentType": "控制模块",
  "equipmentSubtype": "AFC",
  "equipmentStatus": "AFC切非"
},
{
  "equipmentChinese": "站厅B端AFC状态反馈",
  "signalDescription": "",
  "additionalCode": "",
  "sortIndex": 3,
  "generatedContent": "站厅B端AFC状态反馈控制模块N1L1M28",
  "equipmentCode": "N1L1M28",
  "equipmentType": "控制模块",
  "equipmentSubtype": "AFC",
  "equipmentStatus": "AFC状态反馈"
},
{
  "equipmentChinese": "站厅B端AFC释放控制",
  "signalDescription": "",
  "additionalCode": "",
  "sortIndex": 4,
  "generatedContent": "站厅B端AFC释放控制控制模块N1L1M29",
  "equipmentCode": "N1L1M29",
  "equipmentType": "控制模块",
  "equipmentSubtype": "AFC",
  "equipmentStatus": "AFC释放控制"
}
```



#### 对应操作步骤与输出结果

![image-20260819161631268](D:\ExcelForge\docs\img\image-20260819161631268.png)

### 七、监视模块、控制模块-EPS

#### 输入例表

| 设备编码 | 设备类型 | 设备中文                      |
| -------- | -------- | ----------------------------- |
| N1L2M28  | 监视模块 | 站厅B端应急照明BH-EPS状态反馈 |
| N1L2M29  | 控制模块 | 站厅B端应急照明BH-EPS启动控制 |

#### json传入样例

```json
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
}，
{
  "equipmentChinese": "站厅B端应急照明BH-EPS启动控制",
  "signalDescription": "",
  "additionalCode": "",
  "sortIndex": 2,
  "generatedContent": "站厅B端应急照明BH-EPS启动控制控制模块N1L2M29",
  "equipmentCode": "N1L2M29",
  "equipmentType": "控制模块",
  "equipmentSubtype": "EPS",
  "equipmentStatus": "启动控制"
}
```



#### 对应操作步骤与输出结果

![image-20260819162325336](D:\ExcelForge\docs\img\image-20260819162325336.png)

### 八、监视模块、控制模块-垂梯

#### 输入例表

| 设备编码 | 设备类型 | 设备中文                   |
| -------- | -------- | -------------------------- |
| N1L6M55  | 监视模块 | 3号出入口垂直电梯状态反馈  |
| N1L6M56  | 控制模块 | 3号出入口垂直电梯归首控制  |
| N1L6M57  | 监视模块 | 站厅公共区垂直电梯状态反馈 |
| N1L6M58  | 控制模块 | 站厅公共区垂直电梯归首控制 |

#### json传入样例

```json
{
  "equipmentChinese": "3号出入口垂直电梯状态反馈",
  "signalDescription": "",
  "additionalCode": "",
  "sortIndex": 1,
  "generatedContent": "3号出入口垂直电梯状态反馈监视模块N1L6M55",
  "equipmentCode": "N1L6M55",
  "equipmentType": "监视模块",
  "equipmentSubtype": "垂直电梯",
  "equipmentStatus": "垂直电梯状态反馈"
},
{
  "equipmentChinese": "3号出入口垂直电梯归首控制",
  "signalDescription": "",
  "additionalCode": "",
  "sortIndex": 2,
  "generatedContent": "3号出入口垂直电梯归首控制控制模块N1L6M56",
  "equipmentCode": "N1L6M56",
  "equipmentType": "控制模块",
  "equipmentSubtype": "垂直电梯",
  "equipmentStatus": "垂直电梯归首控制"
}
```



#### 对应操作步骤与输出结果

![image-20260819164546631](D:\ExcelForge\docs\img\image-20260819164546631.png)

### 九、防火阀-电动防火阀

#### 输入例表

| 设备编码 | 设备类型 | 设备中文              | 信号描述   | 附加编号     |
| -------- | -------- | --------------------- | ---------- | ------------ |
| FF2-B211 | 防火阀   | 站厅B端公安通信设备室 | 动作状态   | QT-N2L01-M01 |
| FF2-B211 | 防火阀   | 站厅B端公安通信设备室 | 关控制命令 | QT-N2L01-M02 |
| FF2-B212 | 防火阀   | 站厅B端公安通信设备室 | 动作状态   | QT-N2L01-M03 |
| FF2-B212 | 防火阀   | 站厅B端公安通信设备室 | 关控制命令 | QT-N2L01-M04 |

#### json传入样例

```json
{
  "equipmentChinese": "站厅B端公安通信设备室",
  "signalDescription": "动作状态",
  "additionalCode": "QT-N2L01-M01",
  "sortIndex": 1,
  "generatedContent": "站厅B端公安通信设备室防火阀FF2-B211动作状态QT-N2L01-M01",
  "equipmentCode": "FF2-B211",
  "equipmentType": "防火阀",
  "equipmentSubtype": "电动防火阀",
  "equipmentStatus": "动作状态"
},
{
  "equipmentChinese": "站厅B端公安通信设备室",
  "signalDescription": "关控制命令",
  "additionalCode": "QT-N2L01-M02",
  "sortIndex": 2,
  "generatedContent": "站厅B端公安通信设备室防火阀FF2-B211关控制命令QT-N2L01-M02",
  "equipmentCode": "FF2-B211",
  "equipmentType": "防火阀",
  "equipmentSubtype": "电动防火阀",
  "equipmentStatus": "关控制命令"
}
```



#### 对应操作步骤与输出结果

![image-20260819165842405](D:\ExcelForge\docs\img\image-20260819165842405.png)

### 十、防火阀-手动防火阀

#### 输入例表

| 设备编码 | 设备类型 | 设备中文 | 信号描述 | 附加编号  |
| -------- | -------- | -------- | -------- | --------- |
| FP1-B7   | 防火阀   | 站厅B端  | 动作状态 | N1L01-M78 |
| FP1-B1   | 防火阀   | 站厅B端  | 动作状态 | N1L01-M79 |
| FP1-B2   | 防火阀   | 站厅B端  | 动作状态 | N1L01-M80 |
| FF1-B907 | 防火阀   | 站厅B端  | 动作状态 | N1L01-M81 |

#### json传入样例

```json
{
  "equipmentChinese": "站厅B端",
  "signalDescription": "动作状态",
  "additionalCode": "N1L01-M78",
  "sortIndex": 1,
  "generatedContent": "站厅B端防火阀FP1-B7动作状态N1L01-M78",
  "equipmentCode": "FP1-B7",
  "equipmentType": "防火阀",
  "equipmentSubtype": "手动防火阀",
  "equipmentStatus": ""
}
```



#### 对应操作步骤与输出结果

![image-20260819170328321](D:\ExcelForge\docs\img\image-20260819170328321.png)

### 十一、监视模块、控制模块-防火卷帘

#### 输入例表

| 设备编码 | 设备类型 | 设备中文                           |
| -------- | -------- | ---------------------------------- |
| N1L6M45  | 监视模块 | 站厅公共区RS-1防火卷帘一次降落反馈 |
| N1L6M46  | 控制模块 | 站厅公共区RS-1防火卷帘一次降落控制 |
| N1L6M47  | 监视模块 | 站厅公共区RS-1防火卷帘二次降落反馈 |
| N1L6M48  | 控制模块 | 站厅公共区RS-1防火卷帘二次降落控制 |

#### json传入样例

```json
{
  "equipmentChinese": "站厅公共区RS-1防火卷帘一次降落反馈",
  "signalDescription": "",
  "additionalCode": "",
  "sortIndex": 1,
  "generatedContent": "站厅公共区RS-1防火卷帘一次降落反馈监视模块N1L6M45",
  "equipmentCode": "N1L6M45",
  "equipmentType": "监视模块",
  "equipmentSubtype": "防火卷帘",
  "equipmentStatus": "防火卷帘一次降落反馈"
},
{
  "equipmentChinese": "站厅公共区RS-1防火卷帘一次降落控制",
  "signalDescription": "",
  "additionalCode": "",
  "sortIndex": 2,
  "generatedContent": "站厅公共区RS-1防火卷帘一次降落控制控制模块N1L6M46",
  "equipmentCode": "N1L6M46",
  "equipmentType": "控制模块",
  "equipmentSubtype": "防火卷帘",
  "equipmentStatus": "防火卷帘一次降落控制"
},
{
  "equipmentChinese": "站厅公共区RS-1防火卷帘二次降落反馈",
  "signalDescription": "",
  "additionalCode": "",
  "sortIndex": 3,
  "generatedContent": "站厅公共区RS-1防火卷帘二次降落反馈监视模块N1L6M47",
  "equipmentCode": "N1L6M47",
  "equipmentType": "监视模块",
  "equipmentSubtype": "防火卷帘",
  "equipmentStatus": "防火卷帘二次降落反馈"
},
{
  "equipmentChinese": "站厅公共区RS-1防火卷帘二次降落控制",
  "signalDescription": "",
  "additionalCode": "",
  "sortIndex": 4,
  "generatedContent": "站厅公共区RS-1防火卷帘二次降落控制控制模块N1L6M48",
  "equipmentCode": "N1L6M48",
  "equipmentType": "控制模块",
  "equipmentSubtype": "防火卷帘",
  "equipmentStatus": "防火卷帘二次降落控制"
}
```



#### 对应操作步骤与输出结果

![image-20260819170827005](D:\ExcelForge\docs\img\image-20260819170827005.png)

### 十二、排烟机、加压送风机

#### 输入例表

| 设备编码 | 设备类型   | 设备中文 | 信号描述       |
| -------- | ---------- | -------- | -------------- |
| SEF-B601 | 排烟机     | 站厅B端  | 运行状态       |
| SEF-B601 | 排烟机     | 站厅B端  | 手自动切换状态 |
| SEF-B601 | 排烟机     | 站厅B端  | 开启控制命令   |
| FAF-B701 | 加压送风机 | 站厅B端  | 运行状态       |
| FAF-B701 | 加压送风机 | 站厅B端  | 手自动切换状态 |
| FAF-B701 | 加压送风机 | 站厅B端  | 开启控制命令   |

#### json传入样例

```json
{
  "equipmentChinese": "站厅B端",
  "signalDescription": "运行状态",
  "additionalCode": "",
  "sortIndex": 1,
  "generatedContent": "站厅B端排烟机SEF-B601运行状态",
  "equipmentCode": "SEF-B601",
  "equipmentType": "排烟机",
  "equipmentSubtype": "",
  "equipmentStatus": "运行状态"
},
{
  "equipmentChinese": "站厅B端",
  "signalDescription": "手自动切换状态",
  "additionalCode": "",
  "sortIndex": 2,
  "generatedContent": "站厅B端排烟机SEF-B601手自动切换状态",
  "equipmentCode": "SEF-B601",
  "equipmentType": "排烟机",
  "equipmentSubtype": "",
  "equipmentStatus": "手自动切换状态"
},
{
  "equipmentChinese": "站厅B端",
  "signalDescription": "开启控制命令",
  "additionalCode": "",
  "sortIndex": 3,
  "generatedContent": "站厅B端排烟机SEF-B601开启控制命令",
  "equipmentCode": "SEF-B601",
  "equipmentType": "排烟机",
  "equipmentSubtype": "",
  "equipmentStatus": "开启控制命令"
},
{
  "equipmentChinese": "站厅B端",
  "signalDescription": "运行状态",
  "additionalCode": "",
  "sortIndex": 4,
  "generatedContent": "站厅B端加压送风机FAF-B701运行状态",
  "equipmentCode": "FAF-B701",
  "equipmentType": "加压送风机",
  "equipmentSubtype": "",
  "equipmentStatus": "运行状态"
},
{
  "equipmentChinese": "站厅B端",
  "signalDescription": "手自动切换状态",
  "additionalCode": "",
  "sortIndex": 5,
  "generatedContent": "站厅B端加压送风机FAF-B701手自动切换状态",
  "equipmentCode": "FAF-B701",
  "equipmentType": "加压送风机",
  "equipmentSubtype": "",
  "equipmentStatus": "手自动切换状态"
},
{
  "equipmentChinese": "站厅B端",
  "signalDescription": "开启控制命令",
  "additionalCode": "",
  "sortIndex": 6,
  "generatedContent": "站厅B端加压送风机FAF-B701开启控制命令",
  "equipmentCode": "FAF-B701",
  "equipmentType": "加压送风机",
  "equipmentSubtype": "",
  "equipmentStatus": "开启控制命令"
}
```



#### 对应操作步骤与输出结果

![image-20260819171441860](D:\ExcelForge\docs\img\image-20260819171441860.png)

![image-20260819171457845](D:\ExcelForge\docs\img\image-20260819171457845.png)

### 十三、风阀

#### 输入例表

| 设备编码  | 设备类型 | 设备中文 | 信号描述 |
| --------- | -------- | -------- | -------- |
| DT1-B701  | 风阀     | 站厅B端  | 动作状态 |
| DT1-B1001 | 风阀     | 站厅B端  | 动作状态 |
| DT1-B603  | 风阀     | 站厅B端  | 动作状态 |
| DT1-B702  | 风阀     | 站厅B端  | 动作状态 |
| DT1-B1101 | 风阀     | 站厅B端  | 动作状态 |

#### json传入样例

```json
{
  "equipmentChinese": "站厅B端",
  "signalDescription": "动作状态",
  "additionalCode": "",
  "sortIndex": 1,
  "generatedContent": "站厅B端风阀DT1-B701动作状态",
  "equipmentCode": "DT1-B701",
  "equipmentType": "风阀",
  "equipmentSubtype": "",
  "equipmentStatus": "动作状态"
}
```



#### 对应操作步骤与输出结果

![image-20260819172300654](D:\ExcelForge\docs\img\image-20260819172300654.png)



### 十四、监视模块、控制模块-400v切非

#### 输入例表

| 设备编码 | 设备类型 | 设备中文                  | 附加编号        |
| -------- | -------- | ------------------------- | --------------- |
| P111-10  | 监视模块 | B端供电房间双切箱切非反馈 | _N1L09-M01_MK-1 |
| P111-10  | 控制模块 | B端供电房间双切箱切非     | _N1L09-M02_MK-1 |
| P210-10  | 监视模块 | B端供电房间双切箱切非反馈 | _N1L09-M03_MK-1 |
| P210-10  | 控制模块 | B端供电房间双切箱切非     | _N1L09-M04_MK-1 |

#### json传入样例

```json
{
  "equipmentChinese": "B端供电房间双切箱切非反馈",
  "signalDescription": "",
  "additionalCode": "_N1L09-M01_MK-1",
  "sortIndex": 1,
  "generatedContent": "B端供电房间双切箱切非反馈监视模块P111-10_N1L09-M01_MK-1",
  "equipmentCode": "P111-10",
  "equipmentType": "监视模块",
  "equipmentSubtype": "400V切非",
  "equipmentStatus": "切非反馈"
}，

{
  "equipmentChinese": "B端供电房间双切箱切非",
  "signalDescription": "",
  "additionalCode": "_N1L09-M02_MK-1",
  "sortIndex": 2,
  "generatedContent": "B端供电房间双切箱切非控制模块P111-10_N1L09-M02_MK-1",
  "equipmentCode": "P111-10",
  "equipmentType": "控制模块",
  "equipmentSubtype": "400V切非",
  "equipmentStatus": "切非"
}
```



#### 对应操作步骤与输出结果

![image-20260819172836649](D:\ExcelForge\docs\img\image-20260819172836649.png)



### 十五、控制模块-声光报警器

#### 输入例表

| 设备编码 | 设备类型 | 设备中文               |
| -------- | -------- | ---------------------- |
| N1L1M30  | 控制模块 | 站厅B端SG3声光报警控制 |
| N1L3M30  | 控制模块 | 站厅B端SG4声光报警控制 |
| N1L8M53  | 控制模块 | 站台公共区SG7声光控制  |
| N1L10M41 | 控制模块 | 声光交替模块           |
| N1L10M91 | 控制模块 | 声光交替模块(备用)     |
| N1L8M65  | 控制模块 | 站台A端SG6声光报警控制 |

#### json传入样例

```json
[
  {
    "equipmentChinese": "站厅B端SG3声光报警控制",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 1,
    "generatedContent": "站厅B端SG3声光报警控制控制模块N1L1M30",
    "equipmentCode": "N1L1M30",
    "equipmentType": "控制模块",
    "equipmentSubtype": "声光报警器",
    "equipmentStatus": "声光报警控制"
  },
  {
    "equipmentChinese": "站厅B端SG4声光报警控制",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 2,
    "generatedContent": "站厅B端SG4声光报警控制控制模块N1L3M30",
    "equipmentCode": "N1L3M30",
    "equipmentType": "控制模块",
    "equipmentSubtype": "声光报警器",
    "equipmentStatus": "声光报警控制"
  }
]


{
  "type": "站点",
  "direction": "",
  "startStation": "嘉庚体育馆站",
  "endStation": "嘉庚体育馆站",
  "stations": [
    "嘉庚体育馆站"
  ]
}
```



#### 对应操作步骤与输出结果

![image-20260907085838901](D:\ExcelForge\docs\img\image-20260907085838901.png)

### 十六、监视模块-消防泵

#### 输入例表

| 设备编码 | 设备类型 | 设备中文                 |
| -------- | -------- | ------------------------ |
| N1L2M65  | 监视模块 | 站厅B端消防泵手/自动反馈 |
| N1L2M66  | 监视模块 | 站厅B端1#消防泵动作反馈  |
| N1L2M67  | 监视模块 | 站厅B端1#消防泵故障反馈  |
| N1L2M70  | 监视模块 | 站厅B端压力开关动作反馈  |
| N1L2M71  | 监视模块 | 站厅B端流量开关动作反馈  |

#### json传入样例

```json
[
  {
    "equipmentChinese": "站厅B端消防泵手/自动反馈",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 1,
    "generatedContent": "站厅B端消防泵手/自动反馈监视模块N1L2M65",
    "equipmentCode": "N1L2M65",
    "equipmentType": "监视模块",
    "equipmentSubtype": "消防泵",
    "equipmentStatus": "消防泵手/自动反馈"
  },
  {
    "equipmentChinese": "站厅B端1#消防泵动作反馈",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 2,
    "generatedContent": "站厅B端1#消防泵动作反馈监视模块N1L2M66",
    "equipmentCode": "N1L2M66",
    "equipmentType": "监视模块",
    "equipmentSubtype": "消防泵",
    "equipmentStatus": "消防泵动作反馈"
  },
  {
    "equipmentChinese": "站厅B端1#消防泵故障反馈",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 3,
    "generatedContent": "站厅B端1#消防泵故障反馈监视模块N1L2M67",
    "equipmentCode": "N1L2M67",
    "equipmentType": "监视模块",
    "equipmentSubtype": "消防泵",
    "equipmentStatus": "消防泵故障反馈"
  },
  {
    "equipmentChinese": "站厅B端压力开关动作反馈",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 4,
    "generatedContent": "站厅B端压力开关动作反馈监视模块N1L2M70",
    "equipmentCode": "N1L2M70",
    "equipmentType": "监视模块",
    "equipmentSubtype": "消防泵",
    "equipmentStatus": "压力开关动作反馈"
  },
  {
    "equipmentChinese": "站厅B端流量开关动作反馈",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 5,
    "generatedContent": "站厅B端流量开关动作反馈监视模块N1L2M71",
    "equipmentCode": "N1L2M71",
    "equipmentType": "监视模块",
    "equipmentSubtype": "消防泵",
    "equipmentStatus": "流量开关动作反馈"
  },
  {
    "equipmentChinese": "站厅B端高水位报警反馈",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 6,
    "generatedContent": "站厅B端高水位报警反馈监视模块N1L2M72",
    "equipmentCode": "N1L2M72",
    "equipmentType": "监视模块",
    "equipmentSubtype": "消防泵",
    "equipmentStatus": "高水位报警反馈"
  },
  {
    "equipmentChinese": "站厅B端低水位报警反馈",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 7,
    "generatedContent": "站厅B端低水位报警反馈监视模块N1L2M73",
    "equipmentCode": "N1L2M73",
    "equipmentType": "监视模块",
    "equipmentSubtype": "消防泵",
    "equipmentStatus": "低水位报警反馈"
  },
  {
    "equipmentChinese": "站厅B端最低水位报警反馈",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 8,
    "generatedContent": "站厅B端最低水位报警反馈监视模块N1L2M74",
    "equipmentCode": "N1L2M74",
    "equipmentType": "监视模块",
    "equipmentSubtype": "消防泵",
    "equipmentStatus": "最低水位报警反馈"
  },
  {
    "equipmentChinese": "站厅B端1#稳压泵动作反馈",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 9,
    "generatedContent": "站厅B端1#稳压泵动作反馈监视模块N1L2M75",
    "equipmentCode": "N1L2M75",
    "equipmentType": "监视模块",
    "equipmentSubtype": "消防泵",
    "equipmentStatus": "稳压泵动作反馈"
  },
  {
    "equipmentChinese": "站厅B端1#稳压泵故障反馈",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 10,
    "generatedContent": "站厅B端1#稳压泵故障反馈监视模块N1L2M76",
    "equipmentCode": "N1L2M76",
    "equipmentType": "监视模块",
    "equipmentSubtype": "消防泵",
    "equipmentStatus": "稳压泵故障反馈"
  },
  {
    "equipmentChinese": "站厅B端消防泵启动控制",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 11,
    "generatedContent": "站厅B端消防泵启动控制控制模块N1L2M79",
    "equipmentCode": "N1L2M79",
    "equipmentType": "控制模块",
    "equipmentSubtype": "消防泵",
    "equipmentStatus": "消防泵启动控制"
  },
  {
    "equipmentChinese": "站厅B端巡检柜报警反馈",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 12,
    "generatedContent": "站厅B端巡检柜报警反馈监视模块N1L2M80",
    "equipmentCode": "N1L2M80",
    "equipmentType": "监视模块",
    "equipmentSubtype": "消防泵",
    "equipmentStatus": "巡检柜报警反馈"
  },
  {
    "equipmentChinese": "站厅公共区XHF-1信号阀动作反馈",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 13,
    "generatedContent": "站厅公共区XHF-1信号阀动作反馈监视模块N1L6M49",
    "equipmentCode": "N1L6M49",
    "equipmentType": "监视模块",
    "equipmentSubtype": "消防泵",
    "equipmentStatus": "信号阀动作反馈"
  },
  {
    "equipmentChinese": "站厅公共区SLF-1水流指示器动作反馈",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 14,
    "generatedContent": "站厅公共区SLF-1水流指示器动作反馈监视模块N1L6M50",
    "equipmentCode": "N1L6M50",
    "equipmentType": "监视模块",
    "equipmentSubtype": "消防泵",
    "equipmentStatus": "水流指示器动作反馈"
  }
]

{
  "type": "站点",
  "direction": "",
  "startStation": "嘉庚体育馆站",
  "endStation": "嘉庚体育馆站",
  "stations": [
    "嘉庚体育馆站"
  ]
}
```



#### 对应操作步骤与输出结果

![image-20260907094532681](D:\ExcelForge\docs\img\image-20260907094532681.png)

![image-20260907094557936](D:\ExcelForge\docs\img\image-20260907094557936.png)

![image-20260907094633217](D:\ExcelForge\docs\img\image-20260907094633217.png)

### 十七、控制模块-PA

#### 输入例表

| 设备编码 | 设备类型 | 设备中文              |
| -------- | -------- | --------------------- |
| N1L1M32  | 控制模块 | 站厅B端PA广播         |
| N1L1M33  | 控制模块 | 站厅B端PA广播状态保持 |
| N1L10M42 | 控制模块 | 广播交替模块          |
| N1L10M92 | 控制模块 | 广播交替模块(备用)    |

#### json传入样例

```json
[
  {
    "equipmentChinese": "站厅B端PA广播",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 1,
    "generatedContent": "站厅B端PA广播控制模块N1L1M32",
    "equipmentCode": "N1L1M32",
    "equipmentType": "控制模块",
    "equipmentSubtype": "PA",
    "equipmentStatus": "PA广播"
  },
  {
    "equipmentChinese": "站厅B端PA广播状态保持",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 2,
    "generatedContent": "站厅B端PA广播状态保持控制模块N1L1M33",
    "equipmentCode": "N1L1M33",
    "equipmentType": "控制模块",
    "equipmentSubtype": "PA",
    "equipmentStatus": "PA广播状态保持"
  },
  {
    "equipmentChinese": "广播交替模块",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 3,
    "generatedContent": "广播交替模块控制模块N1L10M42",
    "equipmentCode": "N1L10M42",
    "equipmentType": "控制模块",
    "equipmentSubtype": "PA",
    "equipmentStatus": "广播交替模块"
  },
  {
    "equipmentChinese": "广播交替模块(备用)",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 4,
    "generatedContent": "广播交替模块(备用)控制模块N1L10M92",
    "equipmentCode": "N1L10M92",
    "equipmentType": "控制模块",
    "equipmentSubtype": "PA",
    "equipmentStatus": "广播交替模块"
  }
]
```



#### 对应操作步骤与输出结果

![image-20260907094958598](D:\ExcelForge\docs\img\image-20260907094958598.png)

### 十八、监视模块-防火门

#### 输入例表

| 设备编码   | 设备类型 | 设备中文                   |
| ---------- | -------- | -------------------------- |
| QT-N2L5M45 | 监视模块 | 角龟区间联络通道防火门反馈 |
| QT-N2L5M47 | 监视模块 | 角龟区间联络通道DI备用     |
| QT-N2L5M46 | 监视模块 | 角龟区间联络通道防火门反馈 |
| QT-N2L5M48 | 监视模块 | 角龟区间联络通道DI备用     |

#### json传入样例

```json
[
  {
    "equipmentChinese": "角龟区间联络通道防火门反馈",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 1,
    "generatedContent": "角龟区间联络通道防火门反馈监视模块QT-N2L5M45",
    "equipmentCode": "QT-N2L5M45",
    "equipmentType": "监视模块",
    "equipmentSubtype": "防火门",
    "equipmentStatus": ""
  },
  {
    "equipmentChinese": "角龟区间联络通道DI备用",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 2,
    "generatedContent": "角龟区间联络通道DI备用监视模块QT-N2L5M47",
    "equipmentCode": "QT-N2L5M47",
    "equipmentType": "监视模块",
    "equipmentSubtype": "防火门",
    "equipmentStatus": ""
  },
  {
    "equipmentChinese": "角龟区间联络通道防火门反馈",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 3,
    "generatedContent": "角龟区间联络通道防火门反馈监视模块QT-N2L5M46",
    "equipmentCode": "QT-N2L5M46",
    "equipmentType": "监视模块",
    "equipmentSubtype": "防火门",
    "equipmentStatus": ""
  },
  {
    "equipmentChinese": "角龟区间联络通道DI备用",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 4,
    "generatedContent": "角龟区间联络通道DI备用监视模块QT-N2L5M48",
    "equipmentCode": "QT-N2L5M48",
    "equipmentType": "监视模块",
    "equipmentSubtype": "防火门",
    "equipmentStatus": ""
  }
]
```



#### 对应操作步骤与输出结果

![image-20260907095308574](D:\ExcelForge\docs\img\image-20260907095308574.png)

### 十九、监视模块、控制模块-门禁释放

#### 输入例表

| 设备编码 | 设备类型 | 设备中文                         |
| -------- | -------- | -------------------------------- |
| N1L1M13  | 监视模块 | A端设备区门禁释放反馈            |
| N1L1M14  | 控制模块 | A端设备区门禁释放                |
| N1L1M17  | 监视模块 | 疏散通道门禁释放反馈             |
| N1L1M18  | 控制模块 | 疏散通道门禁释放                 |
| N1L1M19  | 监视模块 | 进入轨行区边门门禁释放反馈DI备用 |

#### json传入样例

```json
[
  {
    "equipmentChinese": "A端设备区门禁释放反馈",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 1,
    "generatedContent": "A端设备区门禁释放反馈监视模块N1L1M13",
    "equipmentCode": "N1L1M13",
    "equipmentType": "监视模块",
    "equipmentSubtype": "门禁",
    "equipmentStatus": "门禁释放反馈"
  },
  {
    "equipmentChinese": "A端设备区门禁释放",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 2,
    "generatedContent": "A端设备区门禁释放控制模块N1L1M14",
    "equipmentCode": "N1L1M14",
    "equipmentType": "控制模块",
    "equipmentSubtype": "门禁",
    "equipmentStatus": "门禁释放"
  },
  {
    "equipmentChinese": "疏散通道门禁释放反馈",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 3,
    "generatedContent": "疏散通道门禁释放反馈监视模块N1L1M17",
    "equipmentCode": "N1L1M17",
    "equipmentType": "监视模块",
    "equipmentSubtype": "门禁",
    "equipmentStatus": "门禁释放反馈"
  },
  {
    "equipmentChinese": "疏散通道门禁释放",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 4,
    "generatedContent": "疏散通道门禁释放控制模块N1L1M18",
    "equipmentCode": "N1L1M18",
    "equipmentType": "控制模块",
    "equipmentSubtype": "门禁",
    "equipmentStatus": "门禁释放"
  },
  {
    "equipmentChinese": "进入轨行区边门门禁释放反馈DI备用",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 5,
    "generatedContent": "进入轨行区边门门禁释放反馈DI备用监视模块N1L1M19",
    "equipmentCode": "N1L1M19",
    "equipmentType": "监视模块",
    "equipmentSubtype": "门禁",
    "equipmentStatus": "门禁释放反馈"
  }
]
```



#### 对应操作步骤与输出结果

![image-20260907095529866](D:\ExcelForge\docs\img\image-20260907095529866.png)

### 二十、控制模块、监视模块-电气火灾、消防电源、应急疏散

#### 输入例表



| 设备编码 | 设备类型 | 设备中文                              |
| -------- | -------- | ------------------------------------- |
| N1L1M21  | 监视模块 | 站厅B端电气火灾监控报警               |
| N1L1M22  | 监视模块 | 站厅B端电气火灾监控故障反馈           |
| N1L1M43  | 监视模块 | 站厅B端消防电源监控系统报警           |
| N1L1M44  | 监视模块 | 站厅B端消防电源监控系统故障反馈       |
| N1L1M35  | 监视模块 | 站厅B端应急照明及疏散指示系统状态反馈 |
| N1L1M36  | 控制模块 | 站厅B端应急照明及疏散指示系统模式控制 |
| N1L1M37  | 监视模块 | 应急照明及疏散指示系统状态反馈DI备用  |
| N1L1M38  | 控制模块 | 应急照明及疏散指示系统模式控制DO备用  |



#### json传入样例

```json
[
  {
    "equipmentChinese": "站厅B端电气火灾监控报警",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 1,
    "generatedContent": "站厅B端电气火灾监控报警监视模块N1L1M21",
    "equipmentCode": "N1L1M21",
    "equipmentType": "监视模块",
    "equipmentSubtype": "电气火灾、消防电源、应急疏散",
    "equipmentStatus": "电气火灾监控报警"
  },
  {
    "equipmentChinese": "站厅B端电气火灾监控故障反馈",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 2,
    "generatedContent": "站厅B端电气火灾监控故障反馈监视模块N1L1M22",
    "equipmentCode": "N1L1M22",
    "equipmentType": "监视模块",
    "equipmentSubtype": "电气火灾、消防电源、应急疏散",
    "equipmentStatus": "电气火灾监控故障反馈"
  },
  {
    "equipmentChinese": "站厅B端消防电源监控系统报警",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 3,
    "generatedContent": "站厅B端消防电源监控系统报警监视模块N1L1M43",
    "equipmentCode": "N1L1M43",
    "equipmentType": "监视模块",
    "equipmentSubtype": "电气火灾、消防电源、应急疏散",
    "equipmentStatus": "消防电源监控系统报警"
  },
  {
    "equipmentChinese": "站厅B端消防电源监控系统故障反馈",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 4,
    "generatedContent": "站厅B端消防电源监控系统故障反馈监视模块N1L1M44",
    "equipmentCode": "N1L1M44",
    "equipmentType": "监视模块",
    "equipmentSubtype": "电气火灾、消防电源、应急疏散",
    "equipmentStatus": "消防电源监控系统故障反馈"
  },
  {
    "equipmentChinese": "站厅B端应急照明及疏散指示系统状态反馈",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 5,
    "generatedContent": "站厅B端应急照明及疏散指示系统状态反馈监视模块N1L1M35",
    "equipmentCode": "N1L1M35",
    "equipmentType": "监视模块",
    "equipmentSubtype": "电气火灾、消防电源、应急疏散",
    "equipmentStatus": "应急照明及疏散指示系统状态反馈"
  },
  {
    "equipmentChinese": "站厅B端应急照明及疏散指示系统模式控制",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 6,
    "generatedContent": "站厅B端应急照明及疏散指示系统模式控制控制模块N1L1M36",
    "equipmentCode": "N1L1M36",
    "equipmentType": "控制模块",
    "equipmentSubtype": "电气火灾、消防电源、应急疏散",
    "equipmentStatus": "应急照明及疏散指示系统模式控制"
  },
  {
    "equipmentChinese": "应急照明及疏散指示系统状态反馈DI备用",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 7,
    "generatedContent": "应急照明及疏散指示系统状态反馈DI备用监视模块N1L1M37",
    "equipmentCode": "N1L1M37",
    "equipmentType": "监视模块",
    "equipmentSubtype": "电气火灾、消防电源、应急疏散",
    "equipmentStatus": "应急照明及疏散指示系统状态反馈"
  },
  {
    "equipmentChinese": "应急照明及疏散指示系统模式控制DO备用",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 8,
    "generatedContent": "应急照明及疏散指示系统模式控制DO备用控制模块N1L1M38",
    "equipmentCode": "N1L1M38",
    "equipmentType": "控制模块",
    "equipmentSubtype": "电气火灾、消防电源、应急疏散",
    "equipmentStatus": "应急照明及疏散指示系统模式控制"
  }
]
```



#### 对应操作步骤与输出结果

![image-20260907100009472](D:\ExcelForge\docs\img\image-20260907100009472.png)



### 二十一、特殊模块-气灭测试

#### 输入例表

| 设备编码 | 设备类型 | 设备中文                                      |
| -------- | -------- | --------------------------------------------- |
|          | 特殊模块 | 站厅B端弱电综合设备室气灭测试（含远程控制盒） |
|          | 特殊模块 | 站厅A端环控电控室气灭测试（含远程控制盒）     |
|          | 特殊模块 | 站厅A端照明配电室气灭测试                     |
|          | 特殊模块 | 站台A端照明配电室气灭测试                     |
|          | 特殊模块 | 站台B端照明配电室气灭测试                     |
|          | 特殊模块 | 站厅B端公安通信设备室气灭测试                 |
|          | 特殊模块 | 站厅B端信号设备室气灭测试                     |
|          | 特殊模块 | 站厅B端弱电综合电源室气灭测试（含远程控制盒） |
|          | 特殊模块 | 站厅B端民用通信设备室气灭测试（含远程控制盒） |
|          | 特殊模块 | 站厅B端环控照配室气灭测试（含远程控制盒）     |
|          | 特殊模块 | 站台B端站台门控制室气灭测试                   |
|          | 特殊模块 | 站台B端400V开关室气灭测试（含远程控制盒）     |
|          | 特殊模块 | 站台B端控制室气灭测试（含远程控制盒）         |
|          | 特殊模块 | 站台B端35KV开关室气灭测试（含远程控制盒）     |
|          | 特殊模块 | 站台B端1#整流变室气灭测试（含远程控制盒）     |
|          | 特殊模块 | 站台B端2#整流变室气灭测试（含远程控制盒）     |
|          | 特殊模块 | 站台B端再生能源室气灭测试（含远程控制盒）     |

#### json传入样例

```json
[
  {
    "equipmentChinese": "站厅B端弱电综合设备室气灭测试（含远程控制盒）",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 1,
    "generatedContent": "站厅B端弱电综合设备室气灭测试（含远程控制盒）",
    "equipmentCode": "",
    "equipmentType": "特殊模块",
    "equipmentSubtype": "气灭测试",
    "equipmentStatus": ""
  },
  {
    "equipmentChinese": "站厅A端环控电控室气灭测试（含远程控制盒）",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 2,
    "generatedContent": "站厅A端环控电控室气灭测试（含远程控制盒）",
    "equipmentCode": "",
    "equipmentType": "特殊模块",
    "equipmentSubtype": "气灭测试",
    "equipmentStatus": ""
  },
  {
    "equipmentChinese": "站厅A端照明配电室气灭测试",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 3,
    "generatedContent": "站厅A端照明配电室气灭测试",
    "equipmentCode": "",
    "equipmentType": "特殊模块",
    "equipmentSubtype": "气灭测试",
    "equipmentStatus": ""
  },
  {
    "equipmentChinese": "站台A端照明配电室气灭测试",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 4,
    "generatedContent": "站台A端照明配电室气灭测试",
    "equipmentCode": "",
    "equipmentType": "特殊模块",
    "equipmentSubtype": "气灭测试",
    "equipmentStatus": ""
  },
  {
    "equipmentChinese": "站台B端照明配电室气灭测试",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 5,
    "generatedContent": "站台B端照明配电室气灭测试",
    "equipmentCode": "",
    "equipmentType": "特殊模块",
    "equipmentSubtype": "气灭测试",
    "equipmentStatus": ""
  },
  {
    "equipmentChinese": "站厅B端公安通信设备室气灭测试",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 6,
    "generatedContent": "站厅B端公安通信设备室气灭测试",
    "equipmentCode": "",
    "equipmentType": "特殊模块",
    "equipmentSubtype": "气灭测试",
    "equipmentStatus": ""
  },
  {
    "equipmentChinese": "站厅B端信号设备室气灭测试",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 7,
    "generatedContent": "站厅B端信号设备室气灭测试",
    "equipmentCode": "",
    "equipmentType": "特殊模块",
    "equipmentSubtype": "气灭测试",
    "equipmentStatus": ""
  },
  {
    "equipmentChinese": "站厅B端弱电综合电源室气灭测试（含远程控制盒）",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 8,
    "generatedContent": "站厅B端弱电综合电源室气灭测试（含远程控制盒）",
    "equipmentCode": "",
    "equipmentType": "特殊模块",
    "equipmentSubtype": "气灭测试",
    "equipmentStatus": ""
  },
  {
    "equipmentChinese": "站厅B端民用通信设备室气灭测试（含远程控制盒）",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 9,
    "generatedContent": "站厅B端民用通信设备室气灭测试（含远程控制盒）",
    "equipmentCode": "",
    "equipmentType": "特殊模块",
    "equipmentSubtype": "气灭测试",
    "equipmentStatus": ""
  },
  {
    "equipmentChinese": "站厅B端环控照配室气灭测试（含远程控制盒）",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 10,
    "generatedContent": "站厅B端环控照配室气灭测试（含远程控制盒）",
    "equipmentCode": "",
    "equipmentType": "特殊模块",
    "equipmentSubtype": "气灭测试",
    "equipmentStatus": ""
  },
  {
    "equipmentChinese": "站台B端站台门控制室气灭测试",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 11,
    "generatedContent": "站台B端站台门控制室气灭测试",
    "equipmentCode": "",
    "equipmentType": "特殊模块",
    "equipmentSubtype": "气灭测试",
    "equipmentStatus": ""
  },
  {
    "equipmentChinese": "站台B端400V开关室气灭测试（含远程控制盒）",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 12,
    "generatedContent": "站台B端400V开关室气灭测试（含远程控制盒）",
    "equipmentCode": "",
    "equipmentType": "特殊模块",
    "equipmentSubtype": "气灭测试",
    "equipmentStatus": ""
  },
  {
    "equipmentChinese": "站台B端控制室气灭测试（含远程控制盒）",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 13,
    "generatedContent": "站台B端控制室气灭测试（含远程控制盒）",
    "equipmentCode": "",
    "equipmentType": "特殊模块",
    "equipmentSubtype": "气灭测试",
    "equipmentStatus": ""
  },
  {
    "equipmentChinese": "站台B端35KV开关室气灭测试（含远程控制盒）",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 14,
    "generatedContent": "站台B端35KV开关室气灭测试（含远程控制盒）",
    "equipmentCode": "",
    "equipmentType": "特殊模块",
    "equipmentSubtype": "气灭测试",
    "equipmentStatus": ""
  },
  {
    "equipmentChinese": "站台B端1#整流变室气灭测试（含远程控制盒）",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 15,
    "generatedContent": "站台B端1#整流变室气灭测试（含远程控制盒）",
    "equipmentCode": "",
    "equipmentType": "特殊模块",
    "equipmentSubtype": "气灭测试",
    "equipmentStatus": ""
  },
  {
    "equipmentChinese": "站台B端2#整流变室气灭测试（含远程控制盒）",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 16,
    "generatedContent": "站台B端2#整流变室气灭测试（含远程控制盒）",
    "equipmentCode": "",
    "equipmentType": "特殊模块",
    "equipmentSubtype": "气灭测试",
    "equipmentStatus": ""
  },
  {
    "equipmentChinese": "站台B端再生能源室气灭测试（含远程控制盒）",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 17,
    "generatedContent": "站台B端再生能源室气灭测试（含远程控制盒）",
    "equipmentCode": "",
    "equipmentType": "特殊模块",
    "equipmentSubtype": "气灭测试",
    "equipmentStatus": ""
  }
]
```



#### 对应操作步骤与输出结果

![image-20260907100925291](D:\ExcelForge\docs\img\image-20260907100925291.png)

![image-20260907100953759](D:\ExcelForge\docs\img\image-20260907100953759.png)

![image-20260907101024732](D:\ExcelForge\docs\img\image-20260907101024732.png)

### 二十二、控制模块-消防栓点灯

#### 输入例表

| 设备编码 | 设备类型 | 设备中文                 |
| -------- | -------- | ------------------------ |
| N1L1M39  | 控制模块 | 区间QX1消火栓按钮点灯    |
| N1L1M40  | 控制模块 | 区间QX2消火栓按钮点灯    |
| N1L1M46  | 控制模块 | 站厅B端FX4消火栓按钮点灯 |
| N1L8M66  | 控制模块 | 站台A端FX8消火栓按钮点灯 |

#### json传入样例

```json
[
  {
    "equipmentChinese": "区间QX1消火栓按钮点灯",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 1,
    "generatedContent": "区间QX1消火栓按钮点灯控制模块N1L1M39",
    "equipmentCode": "N1L1M39",
    "equipmentType": "控制模块",
    "equipmentSubtype": "消火栓点灯",
    "equipmentStatus": ""
  },
  {
    "equipmentChinese": "区间QX2消火栓按钮点灯",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 2,
    "generatedContent": "区间QX2消火栓按钮点灯控制模块N1L1M40",
    "equipmentCode": "N1L1M40",
    "equipmentType": "控制模块",
    "equipmentSubtype": "消火栓点灯",
    "equipmentStatus": ""
  },
  {
    "equipmentChinese": "站厅B端FX4消火栓按钮点灯",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 3,
    "generatedContent": "站厅B端FX4消火栓按钮点灯控制模块N1L1M46",
    "equipmentCode": "N1L1M46",
    "equipmentType": "控制模块",
    "equipmentSubtype": "消火栓点灯",
    "equipmentStatus": ""
  },
  {
    "equipmentChinese": "站台A端FX8消火栓按钮点灯",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 4,
    "generatedContent": "站台A端FX8消火栓按钮点灯控制模块N1L8M66",
    "equipmentCode": "N1L8M66",
    "equipmentType": "控制模块",
    "equipmentSubtype": "消火栓点灯",
    "equipmentStatus": ""
  }
]
```



#### 对应操作步骤与输出结果

![image-20260907101557355](D:\ExcelForge\docs\img\image-20260907101557355.png)



### 二十三、控制模块-主机手自动、人工确认

#### 输入例表

| 设备编码   | 设备类型 | 设备中文             |
| ---------- | -------- | -------------------- |
| N1L1M51    | 控制模块 | FAS主机人工确定按钮  |
| N1L1M53    | 控制模块 | FAS主机自动状态按钮  |
| QT-N2L3M10 | 控制模块 | 气灭主机自动状态按钮 |
| N1L1M52    | 控制模块 | FAS主机综合火警      |

#### json传入样例

```json
[
  {
    "equipmentChinese": "FAS主机人工确定按钮",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 1,
    "generatedContent": "FAS主机人工确定按钮控制模块N1L1M51",
    "equipmentCode": "N1L1M51",
    "equipmentType": "控制模块",
    "equipmentSubtype": "主机手自动、人工确认",
    "equipmentStatus": "FAS主机人工确定按钮"
  },
  {
    "equipmentChinese": "FAS主机自动状态按钮",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 2,
    "generatedContent": "FAS主机自动状态按钮控制模块N1L1M53",
    "equipmentCode": "N1L1M53",
    "equipmentType": "控制模块",
    "equipmentSubtype": "主机手自动、人工确认",
    "equipmentStatus": "FAS主机自动状态按钮"
  },
  {
    "equipmentChinese": "气灭主机自动状态按钮",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 3,
    "generatedContent": "气灭主机自动状态按钮控制模块QT-N2L3M10",
    "equipmentCode": "QT-N2L3M10",
    "equipmentType": "控制模块",
    "equipmentSubtype": "主机手自动、人工确认",
    "equipmentStatus": "气灭主机自动状态按钮"
  },
  {
    "equipmentChinese": "FAS主机综合火警",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 4,
    "generatedContent": "FAS主机综合火警控制模块N1L1M52",
    "equipmentCode": "N1L1M52",
    "equipmentType": "控制模块",
    "equipmentSubtype": "主机手自动、人工确认",
    "equipmentStatus": "FAS主机综合火警"
  }
]
```



#### 对应操作步骤与输出结果

![image-20260907102012175](D:\ExcelForge\docs\img\image-20260907102012175.png)



### 二十四、特殊模块-区间消防电话、插孔电话

#### 输入例表

| 设备编码 | 设备类型 | 设备中文                               |
| -------- | -------- | -------------------------------------- |
|          | 特殊模块 | 角江至石美下行区间插孔50号消防电话插孔 |
|          | 特殊模块 | 角江至石美上行区间插孔51号消防电话插孔 |
|          | 特殊模块 | 角江至角中上行区间插孔52号消防电话插孔 |
|          | 特殊模块 | 角江至角中下行区间插孔53号消防电话插孔 |
|          | 特殊模块 | 站台下行轨行区插孔54号消防电话插孔     |
|          | 特殊模块 | 站台上行轨行区插孔55号消防电话插孔     |

#### json传入样例

```json
[
  {
    "equipmentChinese": "角江至石美下行区间插孔50号消防电话插孔",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 1,
    "generatedContent": "角江至石美下行区间插孔50号消防电话插孔",
    "equipmentCode": "",
    "equipmentType": "特殊模块",
    "equipmentSubtype": "区间电话",
    "equipmentStatus": ""
  },
  {
    "equipmentChinese": "角江至石美上行区间插孔51号消防电话插孔",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 2,
    "generatedContent": "角江至石美上行区间插孔51号消防电话插孔",
    "equipmentCode": "",
    "equipmentType": "特殊模块",
    "equipmentSubtype": "区间电话",
    "equipmentStatus": ""
  },
  {
    "equipmentChinese": "角江至角中上行区间插孔52号消防电话插孔",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 3,
    "generatedContent": "角江至角中上行区间插孔52号消防电话插孔",
    "equipmentCode": "",
    "equipmentType": "特殊模块",
    "equipmentSubtype": "区间电话",
    "equipmentStatus": ""
  },
  {
    "equipmentChinese": "角江至角中下行区间插孔53号消防电话插孔",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 4,
    "generatedContent": "角江至角中下行区间插孔53号消防电话插孔",
    "equipmentCode": "",
    "equipmentType": "特殊模块",
    "equipmentSubtype": "区间电话",
    "equipmentStatus": ""
  },
  {
    "equipmentChinese": "站台下行轨行区插孔54号消防电话插孔",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 5,
    "generatedContent": "站台下行轨行区插孔54号消防电话插孔",
    "equipmentCode": "",
    "equipmentType": "特殊模块",
    "equipmentSubtype": "站内电话",
    "equipmentStatus": ""
  },
  {
    "equipmentChinese": "站台上行轨行区插孔55号消防电话插孔",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 6,
    "generatedContent": "站台上行轨行区插孔55号消防电话插孔",
    "equipmentCode": "",
    "equipmentType": "特殊模块",
    "equipmentSubtype": "站内电话",
    "equipmentStatus": ""
  }
]
```



#### 对应操作步骤与输出结果

![image-20260907102840433](D:\ExcelForge\docs\img\image-20260907102840433.png)



### 二十五、特殊模块-站内消防电话

#### 输入例表

| 设备编码 | 设备类型 | 设备中文                         |
| -------- | -------- | -------------------------------- |
|          | 特殊模块 | 厅A设备区走廊插孔1号消防电话插孔 |
|          | 特殊模块 | 厅A照明配电室内2号消防电话分机   |
|          | 特殊模块 | 厅A照明配电室外3号消防电话分机   |
|          | 特殊模块 | 厅A排烟机房室内4号消防电话分机   |
|          | 特殊模块 | 厅A环控机房室内5号消防电话分机   |
|          | 特殊模块 | 厅A新风机房室内6号消防电话分机   |
|          | 特殊模块 | 厅A环控电控室内7号消防电话分机   |
|          | 特殊模块 | 厅A环控电控室外8号消防电话分机   |
|          | 特殊模块 | 厅A气瓶间室内9号消防电话分机     |

#### json传入样例

```json
[
  {
    "equipmentChinese": "厅A设备区走廊插孔1号消防电话插孔",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 1,
    "generatedContent": "厅A设备区走廊插孔1号消防电话插孔",
    "equipmentCode": "",
    "equipmentType": "特殊模块",
    "equipmentSubtype": "站内电话",
    "equipmentStatus": ""
  },
  {
    "equipmentChinese": "厅A照明配电室内2号消防电话分机",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 2,
    "generatedContent": "厅A照明配电室内2号消防电话分机",
    "equipmentCode": "",
    "equipmentType": "特殊模块",
    "equipmentSubtype": "站内电话",
    "equipmentStatus": ""
  },
  {
    "equipmentChinese": "厅A照明配电室外3号消防电话分机",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 3,
    "generatedContent": "厅A照明配电室外3号消防电话分机",
    "equipmentCode": "",
    "equipmentType": "特殊模块",
    "equipmentSubtype": "站内电话",
    "equipmentStatus": ""
  },
  {
    "equipmentChinese": "厅A排烟机房室内4号消防电话分机",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 4,
    "generatedContent": "厅A排烟机房室内4号消防电话分机",
    "equipmentCode": "",
    "equipmentType": "特殊模块",
    "equipmentSubtype": "站内电话",
    "equipmentStatus": ""
  },
  {
    "equipmentChinese": "厅A环控机房室内5号消防电话分机",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 5,
    "generatedContent": "厅A环控机房室内5号消防电话分机",
    "equipmentCode": "",
    "equipmentType": "特殊模块",
    "equipmentSubtype": "站内电话",
    "equipmentStatus": ""
  },
  {
    "equipmentChinese": "厅A新风机房室内6号消防电话分机",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 6,
    "generatedContent": "厅A新风机房室内6号消防电话分机",
    "equipmentCode": "",
    "equipmentType": "特殊模块",
    "equipmentSubtype": "站内电话",
    "equipmentStatus": ""
  },
  {
    "equipmentChinese": "厅A环控电控室内7号消防电话分机",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 7,
    "generatedContent": "厅A环控电控室内7号消防电话分机",
    "equipmentCode": "",
    "equipmentType": "特殊模块",
    "equipmentSubtype": "站内电话",
    "equipmentStatus": ""
  },
  {
    "equipmentChinese": "厅A环控电控室外8号消防电话分机",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 8,
    "generatedContent": "厅A环控电控室外8号消防电话分机",
    "equipmentCode": "",
    "equipmentType": "特殊模块",
    "equipmentSubtype": "站内电话",
    "equipmentStatus": ""
  },
  {
    "equipmentChinese": "厅A气瓶间室内9号消防电话分机",
    "signalDescription": "",
    "additionalCode": "",
    "sortIndex": 9,
    "generatedContent": "厅A气瓶间室内9号消防电话分机",
    "equipmentCode": "",
    "equipmentType": "特殊模块",
    "equipmentSubtype": "站内电话",
    "equipmentStatus": ""
  }
]
```



#### 对应操作步骤与输出结果

![image-20260907103425169](D:\ExcelForge\docs\img\image-20260907103425169.png)