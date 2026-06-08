/**
 * Mock 数据模块
 * -----------
 * 当后端未启动时，提供示例数据让前端页面展示效果
 */

// ── 模拟用户 ──────────────────────────────────────────
const mockUser = {
  user_id: 1,
  username: 'admin',
  role: 'admin',
}

// ── 模拟 Token ────────────────────────────────────────
function generateMockToken() {
  const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }))
  const payload = btoa(
    JSON.stringify({
      sub: '1',
      username: 'admin',
      role: 'admin',
      exp: Math.floor(Date.now() / 1000) + 7200,
    })
  )
  return `mock.${header}.${payload}.signature`
}

// ── 模拟预警数据 ───────────────────────────────────────
const mockAlerts = [
  {
    log_id: 1,
    rule_id: 1,
    rule_name: '全品类销售额突降告警',
    rule_type: 'sales_drop',
    severity: 'red',
    alert_content: '全品类销售额较7日均线下降35.2%',
    anomaly_value: -35.2,
    baseline_value: 45000.0,
    current_value: 29160.0,
    trigger_time: '2026-06-07T14:00:00',
    status: 'pending',
    suggested_action: '建议排查是否有大促后回落或商品下架',
  },
  {
    log_id: 2,
    rule_id: 3,
    rule_name: '库存警戒线告警',
    rule_type: 'stock_low',
    severity: 'orange',
    alert_content: 'iPhone 15 Pro 库存仅剩50件，低于安全库存线',
    anomaly_value: 50.0,
    baseline_value: 200.0,
    current_value: 50.0,
    trigger_time: '2026-06-07T15:00:00',
    status: 'pending',
    suggested_action: '建议立即补货，避免缺货影响销售',
  },
  {
    log_id: 3,
    rule_id: 4,
    rule_name: '退货率飙升告警',
    rule_type: 'return_spike',
    severity: 'yellow',
    alert_content: '退货率较30日均值上升65.3%',
    anomaly_value: 65.3,
    baseline_value: 5.2,
    current_value: 8.6,
    trigger_time: '2026-06-07T16:00:00',
    status: 'pending',
    suggested_action: '建议检查近期商品质量或物流问题',
  },
  {
    log_id: 4,
    rule_id: 2,
    rule_name: '服装品类销售额突降告警',
    rule_type: 'sales_drop',
    severity: 'red',
    alert_content: '服装品类销售额较7日均线下降28.5%',
    anomaly_value: -28.5,
    baseline_value: 12000.0,
    current_value: 8580.0,
    trigger_time: '2026-06-06T10:00:00',
    status: 'resolved',
    resolved_at: '2026-06-07T09:00:00',
    suggested_action: '已处理',
  },
  {
    log_id: 5,
    rule_id: 5,
    rule_name: '电子产品品类告警',
    rule_type: 'sales_drop',
    severity: 'orange',
    alert_content: '华为Mate 60 Pro销售额下降22.1%',
    anomaly_value: -22.1,
    baseline_value: 35000.0,
    current_value: 27265.0,
    trigger_time: '2026-06-05T08:00:00',
    status: 'ignored',
    suggested_action: '已忽略',
  },
]

const mockAlertStats = { red: 2, orange: 2, yellow: 1, total: 5 }

// ── 模拟销售数据 ───────────────────────────────────────
const mockSalesData = {
  summary: {
    total_sales: 1248567.89,
    total_orders: 5678,
    avg_order_value: 219.85,
    change_rate: 0.123,
    margin_rate: 38.5,
  },
  series: [
    { date: '2026-01', sales: 98000, orders: 420 },
    { date: '2026-02', sales: 85000, orders: 380 },
    { date: '2026-03', sales: 102000, orders: 450 },
    { date: '2026-04', sales: 115000, orders: 510 },
    { date: '2026-05', sales: 128000, orders: 580 },
    { date: '2026-06-01', sales: 42000, orders: 190 },
    { date: '2026-06-02', sales: 38500, orders: 175 },
    { date: '2026-06-03', sales: 41200, orders: 188 },
    { date: '2026-06-04', sales: 39500, orders: 180 },
    { date: '2026-06-05', sales: 43800, orders: 200 },
    { date: '2026-06-06', sales: 35600, orders: 162 },
    { date: '2026-06-07', sales: 29160, orders: 135 },
  ],
  by_category: [
    { category_name: '服装', sales: 450000, percentage: 0.36 },
    { category_name: '电子产品', sales: 380000, percentage: 0.30 },
    { category_name: '食品', sales: 220000, percentage: 0.18 },
    { category_name: '美妆', sales: 120000, percentage: 0.10 },
    { category_name: '其他', sales: 78567, percentage: 0.06 },
  ],
  by_region: [
    { region: '广东', sales: 320000, percentage: 0.26 },
    { region: '北京', sales: 250000, percentage: 0.20 },
    { region: '上海', sales: 230000, percentage: 0.18 },
    { region: '浙江', sales: 180000, percentage: 0.14 },
    { region: '江苏', sales: 150000, percentage: 0.12 },
    { region: '其他', sales: 118567, percentage: 0.10 },
  ],
}

// ── 模拟用户列表 ───────────────────────────────────────
const mockUsers = [
  { user_id: 1, username: 'admin', role: 'admin', status: 1, created_at: '2026-06-01T00:00:00' },
  { user_id: 2, username: 'test_analyst', role: 'analyst', status: 1, created_at: '2026-06-01T00:00:00' },
  { user_id: 3, username: 'test_manager', role: 'manager', status: 1, created_at: '2026-06-01T00:00:00' },
  { user_id: 4, username: 'test_viewer', role: 'viewer', status: 1, created_at: '2026-06-01T00:00:00' },
  { user_id: 5, username: 'zhangsan', role: 'analyst', status: 1, created_at: '2026-06-05T00:00:00' },
  { user_id: 6, username: 'disabled_user', role: 'analyst', status: 0, created_at: '2026-06-01T00:00:00' },
]

// ── 模拟数据源状态 ─────────────────────────────────────
const mockDatasourceStatus = {
  online: true,
  host: 'localhost:3306',
  database: 'ecommerce_bi',
  table_count: 10,
  total_records: 15234,
}

const mockImportHistory = [
  { file_name: 'sales_2025.csv', target_table: 'sales_record', record_count: 8500, import_time: '2026-06-01T10:30:00', status: 'success', message: '导入成功' },
  { file_name: 'products_v2.xlsx', target_table: 'product', record_count: 230, import_time: '2026-06-02T14:00:00', status: 'success', message: '导入成功' },
  { file_name: 'customers_2025.csv', target_table: 'customer', record_count: 5200, import_time: '2026-06-03T09:15:00', status: 'success', message: '导入成功' },
  { file_name: 'inventory_march.xlsx', target_table: 'inventory', record_count: 0, import_time: '2026-06-04T16:45:00', status: 'fail', message: '字段不匹配，导入失败' },
]

// ── 导出 Mock 数据 ────────────────────────────────────
export const mockData = {
  user: mockUser,
  token: generateMockToken,
  alerts: mockAlerts,
  alertStats: mockAlertStats,
  sales: mockSalesData,
  users: mockUsers,
  datasource: mockDatasourceStatus,
  importHistory: mockImportHistory,
}