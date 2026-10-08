// 联调项目入口配置。新增项目时在这里注册项目名称和可用子系统。
export const integrationProjects = [
  {
    code: 'T19',
    name: 'T19 综合监控与 FAS 联调',
    description: '生成文档属于具体联调项目的子系统',
    workspaceTitle: '测试内容生成工作台',
    configRoute: '/config'
  }
]

export const getIntegrationProject = (code) => integrationProjects.find((item) => item.code === code)
