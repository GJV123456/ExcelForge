# ExcelForge 前端启动说明

这是 ExcelForge 的前端项目，使用 Vue 3 + Vite + Element Plus 开发。

## 1. 拉取代码

如果还没有克隆项目：

```bash
git clone https://github.com/BG2FOU/Debug-Table-Auto.git
cd Debug-Table-Auto
```

如果已经克隆过项目，先更新代码：

```bash
git fetch
```

## 2. 切换到前端分支

```bash
git checkout frontend
```

确认当前分支：

```bash
git branch
```

看到 `* frontend` 就说明切换成功。

## 3. 安装依赖

```bash
npm install
```

项目的依赖会根据 `package.json` 和 `package-lock.json` 自动安装。

如果在 Windows PowerShell 里遇到 `npm.ps1` 执行策略报错，可以改用：

```powershell
npm.cmd install
```

## 4. 启动前端

```bash
npm run dev
```

如果 PowerShell 报执行策略错误，改用：

```powershell
npm.cmd run dev
```

启动成功后，终端会显示类似：

```text
Local: http://localhost:5173/
```

打开这个地址即可访问前端页面。

## 5. 默认登录

开发环境默认开启模拟登录，可以使用：

```text
用户名：admin
密码：123456
```

## 6. 后端接口联调

如果只是看前端页面和模拟下载，不需要额外配置。

如果要真实请求后端接口，在项目根目录新建 `.env.local`：

```env
VITE_ENABLE_MOCK_AUTH=true
VITE_ENABLE_MOCK_PROCESS=false
VITE_API_BASE_URL=http://localhost:8080
```

其中：

- `VITE_ENABLE_MOCK_AUTH=true`：登录仍使用前端模拟账号。
- `VITE_ENABLE_MOCK_PROCESS=false`：Excel 处理请求会发给真实后端。
- `VITE_API_BASE_URL=http://localhost:8080`：后端服务地址，按实际端口修改。

修改 `.env.local` 后，需要重新启动前端服务。

## 7. 当前主要接口

登录接口：

```http
POST /api/auth/login
```

Excel 处理接口：

```http
POST /api/excel/process
```

提交 Excel 处理时，前端会发送类似数据：

```json
{
  "testLocation": {
    "type": "站点",
    "direction": "上行",
    "startStation": "A站",
    "endStation": "B站"
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

后端需要返回 Excel 文件流，前端会自动下载为：

```text
最终导入表.xlsx
```

## 8. F12 查看接口请求

1. 打开浏览器页面。
2. 按 `F12`。
3. 切换到 `Network`。
4. 点击 `Fetch/XHR`。
5. 点击页面里的“提交后端处理并下载”。
6. 查看 `process` 请求。

重点看：

- `Headers`：请求地址、请求方法、Authorization。
- `Payload`：前端提交给后端的 JSON。
- `Response`：后端返回结果。
- `Status`：状态码。

如果看到 `404`，通常说明前端已经发出请求，但当前地址没有对应后端接口。

## 9. 注意事项

- `node_modules/` 不会提交到 Git，需要自己执行 `npm install`。

