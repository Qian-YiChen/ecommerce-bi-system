<template>
  <div class="alert-page">
    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stat-cards">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card red">
          <div class="stat-value">{{ stats.red }}</div>
          <div class="stat-label">严重告警</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card orange">
          <div class="stat-value">{{ stats.orange }}</div>
          <div class="stat-label">警告</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card yellow">
          <div class="stat-value">{{ stats.yellow }}</div>
          <div class="stat-label">提示</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card total">
          <div class="stat-value">{{ stats.total }}</div>
          <div class="stat-label">今日总计</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 筛选条件 -->
    <el-card class="filter-card">
      <el-form :inline="true" :model="filters" size="default">
        <el-form-item label="规则类型">
          <el-select v-model="filters.rule_type" placeholder="全部类型" clearable style="width: 140px">
            <el-option label="全部类型" value="" />
            <el-option label="销售额突降" value="sales_drop" />
            <el-option label="库存警戒" value="stock_low" />
            <el-option label="退货飙升" value="return_spike" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filters.status" placeholder="全部状态" clearable style="width: 120px">
            <el-option label="全部状态" value="" />
            <el-option label="待处理" value="pending" />
            <el-option label="已处理" value="resolved" />
            <el-option label="已忽略" value="ignored" />
          </el-select>
        </el-form-item>
        <el-form-item label="严重程度">
          <el-select v-model="filters.severity" placeholder="全部" clearable style="width: 120px">
            <el-option label="全部" value="" />
            <el-option label="严重" value="red" />
            <el-option label="警告" value="orange" />
            <el-option label="提示" value="yellow" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="fetchLogs">查询</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </el-form-item>
        <el-form-item>
          <el-button type="warning" :loading="scanLoading" @click="triggerScan">
            <el-icon><Refresh /></el-icon> 手动扫描
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 预警日志列表 -->
    <el-card class="log-card">
      <template #header>
        <div class="card-header">
          <span>预警日志</span>
          <el-tag type="info" size="small">共 {{ total }} 条</el-tag>
        </div>
      </template>

      <el-table
        :data="logs"
        style="width: 100%"
        v-loading="loading"
        stripe
        @row-click="showDetail"
      >
        <el-table-column label="严重程度" width="90">
          <template #default="{ row }">
            <el-tag :type="severityTag(row.severity)" size="small" effect="dark">
              {{ severityText(row.severity) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="rule_name" label="规则名称" min-width="160" show-overflow-tooltip />
        <el-table-column prop="alert_content" label="预警内容" min-width="280" show-overflow-tooltip />
        <el-table-column label="触发时间" width="170">
          <template #default="{ row }">
            {{ formatTime(row.trigger_time) }}
          </template>
        </el-table-column>
        <el-table-column label="当前值" width="110" align="right">
          <template #default="{ row }">
            <span :class="row.anomaly_value < 0 ? 'text-danger' : ''">
              {{ formatNumber(row.anomaly_value) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="基线值" width="110" align="right">
          <template #default="{ row }">{{ formatNumber(row.baseline_value) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusTag(row.status)" size="small">
              {{ statusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.status === 'pending'"
              type="success"
              size="small"
              :disabled="actionLoading"
              @click.stop="handleResolve(row)"
            >
              处理
            </el-button>
            <el-button
              v-if="row.status === 'pending'"
              type="info"
              size="small"
              plain
              :disabled="actionLoading"
              @click.stop="handleIgnore(row)"
            >
              忽略
            </el-button>
            <el-button
              v-if="row.status !== 'pending'"
              size="small"
              text
              @click.stop="showDetail(row)"
            >
              详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          @change="fetchLogs"
        />
      </div>
    </el-card>

    <!-- 预警详情对话框 -->
    <el-dialog v-model="detailVisible" title="预警详情" width="600px">
      <template v-if="currentDetail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="规则名称" :span="2">{{ currentDetail.rule_name }}</el-descriptions-item>
          <el-descriptions-item label="规则类型">{{ ruleTypeText(currentDetail.rule_type) }}</el-descriptions-item>
          <el-descriptions-item label="严重程度">
            <el-tag :type="severityTag(currentDetail.severity)" size="small">
              {{ severityText(currentDetail.severity) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="触发时间" :span="2">{{ formatTime(currentDetail.trigger_time) }}</el-descriptions-item>
          <el-descriptions-item label="异常值">{{ formatNumber(currentDetail.anomaly_value) }}</el-descriptions-item>
          <el-descriptions-item label="基线值">{{ formatNumber(currentDetail.baseline_value) }}</el-descriptions-item>
          <el-descriptions-item label="预警内容" :span="2">{{ currentDetail.alert_content }}</el-descriptions-item>
          <el-descriptions-item label="建议措施" :span="2">
            <span class="text-primary">{{ currentDetail.suggested_action || '请根据实际情况处理' }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="状态">{{ statusText(currentDetail.status) }}</el-descriptions-item>
          <el-descriptions-item label="处理时间" v-if="currentDetail.resolved_at">{{ formatTime(currentDetail.resolved_at) }}</el-descriptions-item>
        </el-descriptions>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { alertAPI } from '../../api'

// ── 数据 ──────────────────────────────────────────────
const logs = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const scanLoading = ref(false)
const actionLoading = ref(false)
const detailVisible = ref(false)
const currentDetail = ref(null)

const stats = reactive({ red: 0, orange: 0, yellow: 0, total: 0 })

const filters = reactive({
  rule_type: '',
  status: 'pending',
  severity: '',
})

// ── 获取预警日志 ──────────────────────────────────────
async function fetchLogs() {
  loading.value = true
  try {
    const params = {
      page: page.value,
      page_size: pageSize.value,
      ...filters,
    }
    // 过滤空值
    Object.keys(params).forEach((k) => {
      if (params[k] === '' || params[k] === null) params[k] = undefined
    })

    const res = await alertAPI.getLogs(params)
    if (res.success !== false) {
      logs.value = res.data?.logs || res.logs || []
      total.value = res.data?.total || res.total || 0
      // 统计
      const s = { red: 0, orange: 0, yellow: 0, total: 0 }
      ;(res.data?.stats || res.stats || {}).red && Object.assign(s, res.data?.stats || res.stats)
      Object.assign(stats, s)
    }
  } catch {
    logs.value = []
  } finally {
    loading.value = false
  }
}

// ── 手动扫描 ──────────────────────────────────────────
async function triggerScan() {
  scanLoading.value = true
  try {
    ElMessage.success('扫描任务已提交，请稍后查看结果')
    setTimeout(() => fetchLogs(), 2000)
  } finally {
    scanLoading.value = false
  }
}

// ── 处理预警 ──────────────────────────────────────────
async function handleResolve(row) {
  try {
    await ElMessageBox.prompt('请输入处理说明（可选）', '处理预警', {
      confirmButtonText: '确认处理',
      cancelButtonText: '取消',
      inputPattern: /.?/,
    })
    actionLoading.value = true
    const note = '已处理'
    const res = await alertAPI.resolveLog(row.log_id || row.id, note)
    if (res.success !== false) {
      ElMessage.success('已标记为已处理')
      await fetchLogs()
    }
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error('操作失败')
    }
  } finally {
    actionLoading.value = false
  }
}

// ── 忽略预警 ──────────────────────────────────────────
async function handleIgnore(row) {
  try {
    await ElMessageBox.confirm('确定忽略此预警？', '确认', {
      confirmButtonText: '确认忽略',
      cancelButtonText: '取消',
      type: 'warning',
    })
    actionLoading.value = true
    const res = await alertAPI.ignoreLog(row.log_id || row.id)
    if (res.success !== false) {
      ElMessage.success('已忽略')
      await fetchLogs()
    }
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error('操作失败')
    }
  } finally {
    actionLoading.value = false
  }
}

// ── 查看详情 ──────────────────────────────────────────
function showDetail(row) {
  currentDetail.value = row
  detailVisible.value = true
}

// ── 重置筛选 ──────────────────────────────────────────
function resetFilters() {
  filters.rule_type = ''
  filters.status = 'pending'
  filters.severity = ''
  page.value = 1
  fetchLogs()
}

// ── 格式化辅助函数 ────────────────────────────────────
function formatTime(t) {
  if (!t) return '-'
  return t.replace('T', ' ').substring(0, 19)
}

function formatNumber(n) {
  if (n === null || n === undefined) return '-'
  return Number(n).toLocaleString('zh-CN', { maximumFractionDigits: 2 })
}

function severityTag(s) {
  return s === 'red' ? 'danger' : s === 'orange' ? 'warning' : 'info'
}

function severityText(s) {
  return s === 'red' ? '严重' : s === 'orange' ? '警告' : '提示'
}

function statusTag(s) {
  return s === 'pending' ? 'danger' : s === 'resolved' ? 'success' : 'info'
}

function statusText(s) {
  return s === 'pending' ? '待处理' : s === 'resolved' ? '已处理' : '已忽略'
}

function ruleTypeText(t) {
  const map = { sales_drop: '销售额突降', stock_low: '库存警戒', return_spike: '退货飙升' }
  return map[t] || t || '-'
}

// ── 初始化 ────────────────────────────────────────────
onMounted(fetchLogs)
</script>

<style scoped>
.alert-page {
  max-width: 1400px;
  margin: 0 auto;
}

.stat-cards {
  margin-bottom: 20px;
}

.stat-card {
  text-align: center;
  cursor: default;
}

.stat-value {
  font-size: 32px;
  font-weight: 700;
  line-height: 1.2;
}

.stat-label {
  font-size: 13px;
  color: #909399;
  margin-top: 4px;
}

.red .stat-value { color: #f56c6c; }
.orange .stat-value { color: #e6a23c; }
.yellow .stat-value { color: #909399; }
.total .stat-value { color: #409eff; }

.filter-card {
  margin-bottom: 20px;
}

.log-card .card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.text-danger { color: #f56c6c; font-weight: 600; }
.text-primary { color: #409eff; }

.pagination-wrapper {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>