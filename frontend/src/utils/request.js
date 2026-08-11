import axios from 'axios'
import router from '../router'

const request = axios.create({ baseURL: import.meta.env.VITE_API_BASE_URL || '', timeout: 30000 })
request.interceptors.request.use((config) => {
  const raw = localStorage.getItem('excelforge_user')
  const token = raw ? JSON.parse(raw).token : ''
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})
request.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) { localStorage.removeItem('excelforge_user'); router.push('/login') }
    return Promise.reject(error)
  }
)
export default request
