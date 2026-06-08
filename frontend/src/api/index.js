/**
 * API 封装层
 * --------
 * 基于 Axios，自动携带 JWT Token，统一处理响应格式
 * 演示模式下自动返回 mock 数据，无需后端
 * 后端地址：http://localhost:5000（Flask 默认端口）
 */

import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '../router'
import { mockData } from './mock'

const api = axios.create({
  baseURL: 'http://localhost:5000/api',
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// ── 检查是否为演示模式 ──────────────────────────────
function isDemoMode() {
  return localStorage.getItem('demo_mode') === 'true'
}

// ── 延迟辅助：模拟网络延迟 ────────────────────────────
function delay(ms = 300) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

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
    // 演示模式下不显示网络错误
    if (isDemoMode()) return Promise.reject(error)

    if (error.response) {
      const { status, data } = error.response
      switch (status) {
        case 401:
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

// ── 包装函数：演示模式下返回 mock 数据 ────────────────
function wrapWithDemo(realFn, mockFn) {
  return async (...args) => {
    if (isDemoMode()) {
      await delay()
      return mockFn(...args)
    }
    try {
      return await realFn(...args)
    } catch (err) {
      // 后端不可达时 fallback 到 mock
      if (err.code === 'ERR_NETWORK' || err.message?.includes('Network')) {
        await delay()
        return mockFn(...args)
      }
      throw err
    }
  }
}

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

// ── 用户管理 API ─────────────────────────────────────
export const userAPI = {
  list: wrapWithDemo(
    (params) => api.get('/admin/users', { params }),
    () => ({ success: true, users: mockData.users, total: mockData.users.length })
  ),
  create: wrapWithDemo(
    (data) => api.post('/admin/users', data),
    (data) => ({ success: true, message: `用户 ${data.username} 创建成功` })
  ),
  update: wrapWithDemo(
    (id, data) => api.put(`/admin/users/${id}`, data),
    () => ({ success: true, message: '用户信息已更新' })
  ),
  toggleStatus: wrapWithDemo(
    (id) => api.put(`/admin/users/${id}/toggle-status`),
    () => ({ success: true, message: '用户状态已切换' })
  ),
}

// ── 预警 API ──────────────────────────────────────────
export const alertAPI = {
  getRules: wrapWithDemo(
    (params) => api.get('/alert/rules', { params }),
    () => ({ success: true, rules: [] })
  ),
  createRule: wrapWithDemo(
    (data) => api.post('/alert/rules', data),
    () => ({ success: true, message: '规则创建成功' })
  ),
  getLogs: wrapWithDemo(
    (params) => api.get('/alert/logs', { params }),
    (params) => {
      let logs = [...mockData.alerts]
      // 模拟筛选
      if (params?.status) {
        logs = logs.filter((l) => l.status === params.status)
      }
      if (params?.severity) {
        logs = logs.filter((l) => l.severity === params.severity)
      }
      if (params?.rule_type) {
        logs = logs.filter((l) => l.rule_type === params.rule_type)
      }
      return {
        success: true,
        logs,
        total: logs.length,
        stats: mockData.alertStats,
      }
    }
  ),
  resolveLog: wrapWithDemo(
    (id, note) => api.put(`/alert/logs/${id}/resolve`, { note }),
    () => ({ success: true, message: '已标记为已处理' })
  ),
  ignoreLog: wrapWithDemo(
    (id) => api.put(`/alert/logs/${id}/ignore`),
    () => ({ success: true, message: '已忽略' })
  ),
}

// ── 预测 API ──────────────────────────────────────────
export const predictAPI = {
  runSales: wrapWithDemo(
    (params) => api.post('/predict/sales', params),
    () => ({ success: true, task_id: 'mock-task-001', message: '预测任务已提交' })
  ),
  getSalesResult: wrapWithDemo(
    (taskId) => api.get(`/predict/sales/${taskId}`),
    () => ({
      success: true,
      model_used: 'linear_regression',
      mape: 0.152,
      confidence: 'medium',
      forecast: Array.from({ length: 30 }, (_, i) => ({
        date: new Date(Date.now() + (i + 1) * 86400000).toISOString().substring(0, 10),
        predicted_sales: 30000 + Math.random() * 15000,
        lower_bound: 25000 + Math.random() * 10000,
        upper_bound: 35000 + Math.random() * 20000,
      })),
    })
  ),
  runStock: wrapWithDemo(
    (params) => api.post('/predict/stock', params),
    () => ({
      success: true,
      products: [
        { product_id: 1, product_name: '纯棉T恤', current_stock: 500, predicted_demand: 620, safety_stock: 150, suggested_replenish: 270, risk_level: 'warning' },
        { product_id: 3, product_name: 'iPhone 15 Pro', current_stock: 50, predicted_demand: 200, safety_stock: 100, suggested_replenish: 250, risk_level: 'danger' },
        { product_id: 5, product_name: '薯片大礼包', current_stock: 1000, predicted_demand: 800, safety_stock: 300, suggested_replenish: 100, risk_level: 'safe' },
      ],
    })
  ),
}

// ── 销售数据查询 API ───────────────────────────────────
export const dataAPI = {
  querySales: wrapWithDemo(
    (params) => api.get('/data/sales', { params }),
    () => ({ success: true, ...mockData.sales })
  ),
  exportReport: wrapWithDemo(
    (params) => api.post('/data/export', params, { responseType: 'blob' }),
    () => ({ success: true, message: '报表已生成', download_url: '/mock/report.pdf' })
  ),
}

// ── 数据源配置 API ──────────────────────────────────
export const datasourceAPI = {
  getStatus: wrapWithDemo(
    () => api.get('/admin/datasource/status'),
    () => ({ success: true, ...mockData.datasource })
  ),
  getUploadHistory: wrapWithDemo(
    (params) => api.get('/admin/datasource/history', { params }),
    () => ({ success: true, records: mockData.importHistory })
  ),
  uploadCSV: wrapWithDemo(
    (formData) => api.post('/admin/datasource/upload', formData),
    () => ({ success: true, data: { record_count: 1234 }, message: '导入成功' })
  ),
}

export default api
