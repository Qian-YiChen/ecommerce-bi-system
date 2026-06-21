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
// 后端路由:
//   GET    /api/alert/rules            → {success, data: [{rule_id, rule_name, ...}]}
//   POST   /api/alert/rules            → {success, data: {rule_id}, message}
//   PUT    /api/alert/rules/<id>       → {success, data: null, message}
//   GET    /api/alert/logs             → {success, data: {logs, pagination: {total,...}}}
//   PUT    /api/alert/logs/<id>/resolve → {success, data: null, message}
//   POST   /api/alert/scan             → {success, data: [...alerts], message}
export const alertAPI = {
  getRules: wrapWithDemo(
    (params) => api.get('/alert/rules', { params }),
    () => ({ success: true, data: mockData.alertRules || [] })
  ),
  createRule: wrapWithDemo(
    (data) => api.post('/alert/rules', data),
    () => ({ success: true, data: { rule_id: 99 }, message: '规则创建成功' })
  ),
  updateRule: wrapWithDemo(
    (id, data) => api.put(`/alert/rules/${id}`, data),
    () => ({ success: true, message: '规则更新成功' })
  ),
  getLogs: wrapWithDemo(
    (params) => api.get('/alert/logs', { params }),
    (params) => {
      let logs = [...mockData.alerts]
      if (params?.status) logs = logs.filter((l) => l.status === params.status)
      if (params?.severity) logs = logs.filter((l) => l.severity === params.severity)
      return {
        success: true,
        data: { logs, pagination: { total: logs.length, page: 1, per_page: 20, total_pages: 1 } },
      }
    }
  ),
  // 对真实 API 响应做归一化：后端 data: {logs, pagination} → 顶层 {logs, total}
  getLogsNormalized: wrapWithDemo(
    async (params) => {
      const res = await api.get('/alert/logs', { params })
      if (res.success && res.data) {
        return {
          success: true,
          logs: res.data.logs || [],
          total: res.data.pagination?.total || 0,
          stats: res.data.stats || {},
        }
      }
      return res
    },
    (params) => {
      let logs = [...mockData.alerts]
      if (params?.status) logs = logs.filter((l) => l.status === params.status)
      if (params?.severity) logs = logs.filter((l) => l.severity === params.severity)
      return { success: true, logs, total: logs.length, stats: mockData.alertStats }
    }
  ),
  resolveLog: wrapWithDemo(
    (id) => api.put(`/alert/logs/${id}/resolve`),
    () => ({ success: true, message: '已标记为已处理' })
  ),
  // ignoreLog 复用 resolve 端点（后端无独立 ignore 路由）
  ignoreLog: wrapWithDemo(
    (id) => api.put(`/alert/logs/${id}/resolve`),
    () => ({ success: true, message: '已忽略' })
  ),
  scanNow: wrapWithDemo(
    () => api.post('/alert/scan'),
    () => ({ success: true, data: [], message: '扫描完成，未发现异常' })
  ),
}

// ── 预测 API ──────────────────────────────────────────
// 后端路由（同步返回，无需 task 轮询）：
//   GET  /api/predict/sales → {success, data: [{product_id, product_name,
//        forecast_date, predicted_quantity, model_type}, ...]}
//   GET  /api/predict/stock → {success, data: [{product_id, product_name,
//        current_stock, demand_next_3_days, safety_stock, suggest_replenish}, ...]}
export const predictAPI = {
  getSalesForecast: wrapWithDemo(
    () => api.get('/predict/sales'),
    () => ({
      success: true,
      data: Array.from({ length: 168 }, (_, i) => ({
        product_id: (i % 24) + 1,
        product_name: ['纯棉简约T恤女','法式碎花连衣裙','高腰阔腿牛仔裤女','商务免烫衬衫男',
          '轻薄羽绒服男','复古跑步鞋','真皮商务皮鞋男','无线蓝牙耳机Pro','快充数据线套装',
          '手机防窥钢化膜','机械键盘青轴87键','无线静音鼠标','智能手环NFC版','每日坚果礼盒750g',
          '抹茶夹心饼干240g','手撕牛肉干五香味200g','冷萃咖啡液12颗装','冻干柠檬片罐装',
          '氨基酸洁面乳120g','玻尿酸补水面膜5片装','雾面哑光口红','纯棉四件套1.8m床',
          '不粘锅三件套','保温杯500ml不锈钢'][i % 24],
        forecast_date: new Date(Date.now() + (Math.floor(i / 24) + 1) * 86400000)
          .toISOString().substring(0, 10),
        predicted_quantity: 5 + Math.floor(Math.random() * 30),
        model_type: 'linear',
      })),
    })
  ),
  getStockSuggestions: wrapWithDemo(
    () => api.get('/predict/stock'),
    () => ({
      success: true,
      data: [
        { product_id: 1, product_name: '纯棉T恤', current_stock: 80, demand_next_3_days: 12, safety_stock: 6, suggest_replenish: 0 },
        { product_id: 3, product_name: '高腰阔腿牛仔裤女', current_stock: 55, demand_next_3_days: 45, safety_stock: 15, suggest_replenish: 5 },
        { product_id: 8, product_name: '无线蓝牙耳机Pro', current_stock: 65, demand_next_3_days: 200, safety_stock: 80, suggest_replenish: 215 },
        { product_id: 14, product_name: '每日坚果礼盒750g', current_stock: 85, demand_next_3_days: 60, safety_stock: 20, suggest_replenish: 0 },
      ],
    })
  ),
}

// ── 销售数据查询 API ───────────────────────────────────
// 后端路由:
//   GET /api/data/sales?start_date&end_date&... → {success, data: {summary, series, by_category, by_region}}
function roundCurrency(value) {
  return Math.round(value * 100) / 100
}

function buildMockSalesData(params = {}) {
  const base = mockData.sales
  const hasFilters = Boolean(params.region || params.category_id || params.channel)

  if (!hasFilters && (!params.group_by || params.group_by === 'month')) {
    return base
  }

  const regionMultiplierMap = {
    广东: 0.26,
    北京: 0.2,
    上海: 0.18,
    浙江: 0.14,
    江苏: 0.12,
  }
  const categoryMultiplierMap = {
    1: 0.36,
    2: 0.3,
    3: 0.18,
    4: 0.1,
    5: 0.06,
  }
  const channelMultiplierMap = {
    PC: 0.34,
    Mobile: 0.41,
    Miniprogram: 0.25,
  }
  const groupMultiplierMap = {
    day: 0.18,
    week: 0.52,
    month: 1,
  }

  const regionMultiplier = params.region ? (regionMultiplierMap[params.region] || 0.11) : 1
  const categoryMultiplier = params.category_id ? (categoryMultiplierMap[params.category_id] || 0.12) : 1
  const channelMultiplier = params.channel ? (channelMultiplierMap[params.channel] || 0.2) : 1
  const groupMultiplier = groupMultiplierMap[params.group_by] || 1

  let totalMultiplier = regionMultiplier * categoryMultiplier * channelMultiplier * groupMultiplier

  // 无筛选仅切换粒度时，保留总体规模，只调整序列展示。
  if (!hasFilters) {
    totalMultiplier = 1
  }

  const summary = {
    ...base.summary,
    total_sales: roundCurrency(base.summary.total_sales * totalMultiplier),
    total_orders: Math.max(1, Math.round(base.summary.total_orders * totalMultiplier)),
    avg_order_value: roundCurrency(base.summary.avg_order_value * (hasFilters ? 0.9 + totalMultiplier * 0.8 : 1)),
    change_rate: hasFilters ? -0.08 + totalMultiplier * 0.25 : base.summary.change_rate,
    margin_rate: roundCurrency(Math.max(18, base.summary.margin_rate - (hasFilters ? 4.5 : 0))),
  }

  const series = base.series.map((item) => ({
    ...item,
    sales: roundCurrency(item.sales * totalMultiplier),
    orders: Math.max(1, Math.round(item.orders * totalMultiplier)),
  }))

  let byCategory = base.by_category.map((item) => ({
    ...item,
    sales: roundCurrency(item.sales * totalMultiplier),
  }))

  if (params.category_id) {
    byCategory = byCategory.filter((_, index) => index + 1 === Number(params.category_id))
  }

  const categoryTotal = byCategory.reduce((sum, item) => sum + item.sales, 0) || 1
  byCategory = byCategory.map((item) => ({
    ...item,
    percentage: item.sales / categoryTotal,
  }))

  let byRegion = base.by_region.map((item) => ({
    ...item,
    sales: roundCurrency(item.sales * totalMultiplier),
  }))

  if (params.region) {
    byRegion = byRegion.filter((item) => item.region === params.region)
  }

  const regionTotal = byRegion.reduce((sum, item) => sum + item.sales, 0) || 1
  byRegion = byRegion.map((item) => ({
    ...item,
    percentage: item.sales / regionTotal,
  }))

  return {
    summary,
    series,
    by_category: byCategory,
    by_region: byRegion,
  }
}

export const dataAPI = {
  querySales: wrapWithDemo(
    (params) => api.get('/data/sales', { params }),
    (params) => ({ success: true, ...buildMockSalesData(params) })
  ),
}

// ── 报表导出 API ─────────────────────────────────────
// 后端路由:
//   POST /api/report/generate  → {success, data: {filename, download_url}}
//   GET  /api/report/download/<filename> → 文件流
export const reportAPI = {
  generate: wrapWithDemo(
    (body) => api.post('/report/generate', body),
    () => ({ success: true, data: { filename: 'report.xlsx', download_url: '/api/report/download/report.xlsx' }, message: '报表生成成功' })
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
