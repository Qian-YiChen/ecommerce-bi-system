/**
 * API 封装层
 * --------
 * 基于 Axios，自动携带 JWT Token，统一处理响应格式
 * 后端地址：http://localhost:5000（Flask 默认端口）
 */

import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '../router'

const api = axios.create({
  baseURL: 'http://localhost:5000/api',
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// ── 请求拦截器：自动携带 JWT Token ─────────────────────────
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// ── 响应拦截器：统一错误处理 ────────────────────────────
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.response) {
      const { status, data } = error.response
      switch (status) {
        case 401:
          // Token 过期或无效，清除 token 并跳转登录页
          localStorage.removeItem('token')
          localStorage.removeItem('user')
          router.push('/login')
          ElMessage.error('登录已过期，请重新登录')
          break
        case 403:
          ElMessage.error('权限不足')
          break
        case 422:
          ElMessage.warning(data?.message || '请求参数有误')
          break
        case 500:
          ElMessage.error('服务器错误，请稍后重试')
          break
        default:
          ElMessage.error(data?.message || `请求失败 (${status})`)
      }
    } else if (error.request) {
      ElMessage.error('网络异常，无法连接到服务器')
    }
    return Promise.reject(error)
  }
)

// ── 认证 API ──────────────────────────────────────────
export const authAPI = {
  login(username, password) {
    return api.post('/auth/login', { username, password })
  },
  register(username, password, role) {
    return api.post('/auth/register', { username, password, role })
  },
  getMe() {
    return api.get('/auth/me')
  },
}

// ── 用户管理 API（待后端就绪）───────────────────────────
export const userAPI = {
  list(params) {
    return api.get('/admin/users', { params })
  },
  create(data) {
    return api.post('/admin/users', data)
  },
  update(id, data) {
    return api.put(`/admin/users/${id}`, data)
  },
  toggleStatus(id) {
    return api.put(`/admin/users/${id}/toggle-status`)
  },
}

// ── 预警 API ──────────────────────────────────────────
export const alertAPI = {
  getRules(params) {
    return api.get('/alert/rules', { params })
  },
  createRule(data) {
    return api.post('/alert/rules', data)
  },
  getLogs(params) {
    return api.get('/alert/logs', { params })
  },
  resolveLog(id, note) {
    return api.put(`/alert/logs/${id}/resolve`, { note })
  },
  ignoreLog(id) {
    return api.put(`/alert/logs/${id}/ignore`)
  },
}

// ── 预测 API ──────────────────────────────────────────
export const predictAPI = {
  runSales(params) {
    return api.post('/predict/sales', params)
  },
  getSalesResult(taskId) {
    return api.get(`/predict/sales/${taskId}`)
  },
  runStock(params) {
    return api.post('/predict/stock', params)
  },
}

// ── 销售数据查询 API ───────────────────────────────────
export const dataAPI = {
  querySales(params) {
    return api.get('/data/sales', { params })
  },
  exportReport(params) {
    return api.post('/data/export', params, { responseType: 'blob' })
  },
}

// ── 数据源配置 API（待后端就绪）─────────────────────────
export const datasourceAPI = {
  getStatus() {
    return api.get('/admin/datasource/status')
  },
  uploadCSV(formData) {
    return api.post('/admin/datasource/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  getUploadHistory(params) {
    return api.get('/admin/datasource/history', { params })
  },
}

export default api