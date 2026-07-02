import axios from 'axios'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 120000,
})
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('访问令牌')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})
api.interceptors.response.use((response) => response, (error) => {
  if (error.response?.status === 401 && location.pathname !== '/login') {
    localStorage.removeItem('访问令牌'); localStorage.removeItem('当前用户'); location.href = '/login'
  }
  return Promise.reject(error)
})

export const getErrorMessage = (error) => error.response?.data?.detail || error.message || '请求失败'
