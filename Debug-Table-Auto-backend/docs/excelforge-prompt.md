# ExcelForge 前端项目开发需求文档
## 一、项目名称
ExcelForge —— Excel 数据格式转换与测试内容生成工具

## 二、项目概述
### 2.1 项目背景
本项目用于解决人工整理 Excel 测试数据效率低、格式不统一的问题。
用户通过上传 Excel 文件，系统自动识别 Excel 数据类型，并根据用户配置的规则生成标准化测试内容数据，最终提交后端生成符合系统导入要求的 Excel 文件。

### 2.2 项目定位
本项目采用：前后端分离架构

前端主要负责：
- 用户登录鉴权
- Excel 文件上传
- Excel 文件解析
- Excel 数据预览
- 数据类型判断
- 动态测试内容生成规则配置
- JSON 数据组装
- 调用后端接口
- 下载后端返回的 Excel 文件

后端主要负责：
- 数据业务处理
- 数据库查询
- 生成正式导入 Excel 文件
- 返回文件流

## 三、技术栈要求
前端框架
Vue 3
Composition API
<script setup>
构建工具
Vite
UI框架
Element Plus
路由管理
Vue Router 4
状态管理
Pinia
网络请求
Axios
Excel解析

使用：xlsx (SheetJS) 或：exceljs 拖拽功能

使用：vuedraggable

要求：兼容 Vue3

## 四、项目目录结构
```
src
│
├── api
│   ├── auth.js
│   └── excel.js
│
├── components
│   ├── UploadExcel.vue
│   ├── RuleBuilder.vue
│   ├── LocationForm.vue
│   ├── ExcelPreview.vue
│   └── LoadingDialog.vue
│
├── router
│   └── index.js
│
├── store
│   ├── user.js
│   └── excel.js
│
├── utils
│   ├── request.js
│   └── excelParser.js
│
├── views
│   ├── Login.vue
│   ├── Layout.vue
│   └── Workspace.vue
│
├── App.vue
└── main.js
```

## 五、路由设计
### 5.1 登录页面

路径：`/login`

页面：`Login.vue`

功能：
- 用户名输入
- 密码输入
- 登录按钮

登录成功：

保存：
- token
- 用户信息

跳转：/

### 5.2 主工作台
路径：`/`

结构：
```
Layout.vue

    |
    |
    └── Workspace.vue
```

要求：
必须登录才能访问。

## 六、用户鉴权设计
### 6.1 Token存储

Pinia：`store/user.js`

保存：
```
{
 token:"",
 userInfo:{}
}
```

同时同步：`localStorage`

### 6.2 路由守卫

`router.beforeEach`

规则：

存在：token
允许访问。

不存在：
跳转：`/login`

## 七、Axios封装要求

文件：
`utils/request.js`

请求拦截器
自动添加：
Authorization:
Bearer token

格式：
```
Authorization: Bearer xxxxxx
```

响应拦截器

处理：401

执行：
- 清除token
- 清除用户信息
- 跳转登录页

## 八、核心工作台 Workspace

页面：

`Workspace.vue`

包含三个核心模块。

### 模块一：测试地点配置
组件：
LocationForm.vue
字段
地点类型

字段：`type`
类型：下拉选择。
示例：
- 站点
- 区间
- 车辆段
- 停车场
- 其他
必填。

行车方向
字段：`direction`
选项：
- 上行
- 下行
- 双向
必填。

开始站点
字段：`startStation`
必填。

结束站点
字段：`endStation`
必填。

### 模块二：Excel上传与解析

组件：

`UploadExcel.vue`
文件要求

支持：`.xlsx`

限制：
文件大小：≤20MB

上传方式支持：
- 点击上传
- 拖拽上传
- Excel类型自动识别

读取第一行表头。

### 类型A：人工处理版

表头包含：

测试内容
类型

示例：
```
测试内容	类型
消防设备报警测试	消防
```

处理：
直接解析。

### 类型B：原始设备版

表头包含：
- 设备编码
- 设备类型
- 设备中文

示例：
```
设备编码	设备类型	设备中文
N1L1M01	手报	报警器
```

进入规则生成模块。

## 九、Excel数据处理规则
重要约束
保持原Excel顺序

禁止：
- 排序
- 去重
- 重组

必须保持：Excel原始上下顺序。

每条数据增加：
```
{
sortIndex:1
}
```
用于锁定顺序。

## 十、模块三：动态测试内容生成器

组件：

`RuleBuilder.vue`

仅 Type B 使用。

功能要求:

用户可以：
- 拖动字段
    - 设备编码
    - 设备类型
    - 设备中文
- 调整顺序。

同时支持：插入自定义文字。

例如：

规则：
```
设备类型
+
设备编码
+
设备中文
+
报警测试
```

生成：
`手报N1L1M01报警器报警测试`

## 十一、规则数据结构

统一保存为：
```
[
 {
  "type":"field",
  "value":"设备类型"
 },
 {
  "type":"field",
  "value":"设备编码"
 },
 {
  "type":"text",
  "value":"报警测试"
 }
]
```

## 十二、实时预览
规则变化时：
自动刷新。

读取 Excel 前5条数据。

展示：
```
序号	生成内容
1	手报N1L1M01报警测试
2	消火栓N1L1M02报警测试
```

空值处理

如果字段为空：

显示：

[空]

禁止报错。

## 十三、提交后端数据格式

点击：

生成正式文件

发送：

POST

`/api/excel/process`

Payload：
```
{
 "testLocation":{
   "type":"站点",
   "direction":"上行",
   "startStation":"A站",
   "endStation":"B站"
 },
 "testContents":[
 {
  "sortIndex":1,
  "generatedContent":"手报N1L1M01报警测试",
  "equipmentCode":"N1L1M01",
  "equipmentType":"手报"
 }
 ]
}
```

## 十四、文件下载流程

请求时：

Axios：

必须：

responseType:"blob"

流程：
```
提交JSON
↓
显示处理中动画
↓
等待Blob
↓
生成下载链接
↓
下载：
最终导入表.xlsx
↓
关闭动画
↓
提示成功
```

## 十五、处理中动画

使用：`Element Plus：v-loading`

显示：
正在处理中...
正在生成最终导入文件，请稍候

## 十六、状态管理设计
`user.js`

保存：
```
{
token,
userInfo
}
```

`excel.js`
保存：
```
{
file:null,
excelType:"",
headers:[],
rows:[],
rules:[],
preview:[]
}
```

## 十七、错误处理

必须支持：

文件错误

提示：

仅支持xlsx文件
Excel格式错误

提示：

未检测到有效表头
网络错误

提示：

服务器连接失败
后端处理失败

提示：

文件生成失败

## 十八、开发顺序
### 第一阶段
项目初始化：

Vue3
Vite
Element Plus
Router
Pinia
Axios

### 第二阶段
完成基础框架：

登录页
Layout
路由守卫
Axios拦截

### 第三阶段
完成Excel功能：

上传
解析
类型判断
数据预览

### 第四阶段
完成核心功能：

RuleBuilder拖拽
自定义文字
实时预览

### 第五阶段

接口联调：

JSON提交
Blob下载
Loading动画

## 十九、最终目标

完成一个：
`ExcelForge —— Excel数据格式转换与测试内容生成平台`

实现：
`上传Excel → 自动识别 → 规则生成 → 数据转换 → 后端处理 → 下载正式导入文件`


这是我的任务书。你可以看看大概的内容，以及我要做的东西。


数据处理界面，上传文件时提示未检测到有效表头，提示词不够明确，标准要提示出来，哪一个表头错了。最后提交数据后不应该有一个生成的按钮什么的吗？就是我们前端处理完了，现在到后端进行处理了。我们给后端提供数据，就是点击处理后就进行接口请求把数据传给后端。而且那个处理中的动画我要怎么检查。我现在后端还没有写，我要怎么检验》
