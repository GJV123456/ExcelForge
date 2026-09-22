import request from '../utils/request'

// 开发阶段默认使用模拟登录，生产环境始终调用真实后端。
const useMockAuth = import.meta.env.DEV && import.meta.env.VITE_ENABLE_MOCK_AUTH !== 'false'

export const login = (data) => {
  if (useMockAuth) {
    if (data.username !== 'admin' || data.password !== '123456') {
      return Promise.reject(new Error('账号或密码错误'))
    }
    return Promise.resolve({
      data: { data: { token: 'mock-token-excelforge', userInfo: { username: 'admin', name: '管理员' } } }
    })
  }
  return request.post('/api/auth/login', data)
}
