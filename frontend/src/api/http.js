import axios from 'axios'
import { ElMessage } from 'element-plus'
import { auth, clearAuth } from '../stores/auth'

// CloudStudio keeps browser requests on the same origin; Vite forwards /api.
const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api'
/** @type {any} Response interceptor returns the API envelope or download Blob. */
export const http = axios.create({ baseURL: API_BASE, timeout: 15000, withCredentials:true })
http.interceptors.request.use(config => {
  if (auth.csrf) config.headers['X-CSRF-Token'] = auth.csrf
  return config
})
http.interceptors.response.use(response => response.data, error => {
  if (error.response?.status === 401) {
    clearAuth()
    if (location.pathname !== '/login') window.dispatchEvent(new Event('session-expired'))
  }
  if(!error.config?.silent)ElMessage.error(error.response?.data?.error?.message || '连接失败，请检查服务后重试')
  return Promise.reject(error)
})

// Dictionary selectors load every page instead of silently truncating at 100.
export async function allRows(resource) {
  const rows = []
  let page = 1, result
  do {
    result = await http.get(resource, { params: { page, page_size: 100 } })
    rows.push(...result.data); page++
  } while (rows.length < result.total)
  return rows
}
