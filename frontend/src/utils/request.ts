/**
 * Axios Request Configuration
 */
import axios from 'axios'
import { message } from 'ant-design-vue'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

const request = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000
})

// Request interceptor
request.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor
request.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const status = error.response?.status
    const detail = error.response?.data?.detail

    if (status === 401) {
      message.error('登录已过期，请重新登录')
      localStorage.removeItem('token')
      window.location.href = '/login'
    } else if (status === 403) {
      message.error(detail || '无权限访问')
    } else if (status === 404) {
      message.error(detail || '资源不存在')
    } else if (status === 500) {
      message.error('服务器错误，请稍后重试')
    } else if (error.code === 'ECONNABORTED') {
      message.error('请求超时，请检查网络')
    } else if (!error.response) {
      message.error('网络连接失败，请检查网络')
    } else {
      message.error(detail || '请求失败，请重试')
    }

    return Promise.reject(error)
  }
)

export default request
