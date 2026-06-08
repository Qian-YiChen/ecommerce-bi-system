<template>
  <div class="dashboard-page">
    <!-- 核心指标卡片 -->
    <el-row :gutter="20" class="stat-row">
      <el-col :span="6" v-for="card in statCards" :key="card.title">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-info">
              <div class="stat-title">{{ card.title }}</div>
              <div class="stat-value" :style="{ color: card.color }">{{ card.value }}</div>
              <div class="stat-change" :class="card.change >= 0 ? 'up' : 'down'">
                {{ card.change >= 0 ? '↑' : '↓' }} {{ Math.abs(card.change) }}% 较昨日
              </div>
            </div>
            <el-icon :size="48" :color="card.color + '20'" class="stat-icon">
              <component :is="card.icon" />
            </el-icon>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 销售趋势图 + 预测概览 -->
    <el-row :gutter="20" class="chart-row">
      <el-col :span="16">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>销售趋势</span>
              <el-radio-group v-model="trendRange" size="small">
                <el-radio value="7d">近7天</el-radio>
                <el-radio value="30d">近30天</el-radio>
                <el-radio value="90d">近90天</el-radio>
              </el-radio-group>
            </div>
          </template>
          <div ref="trendChartRef" style="height: 320px"></div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>品类分布</span>
            </div>
          </template>
          <div ref="pieChartRef" style="height: 320px"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 预警概览 -->
    <el-row :gutter="20" class="alert-row">
      <el-col :span="24">
        <el-card>
          <template #header>
            <div class="card-header">
              <span><el-icon><WarningFilled /></el-icon> 待处理预警</span>
              <el-button size="small" type="primary" @click="$router.push('/alert')">
                查看全部
              </el-button>
            </div>
          </template>
          <div class="alert-placeholder" v-if="pendingAlerts.length === 0">
            <el-empty description="暂无待处理预警" :image-size="80" />
          </div>
          <el-table v-else :data="pendingAlerts" stripe style="width: 100%" @row-click="goAlert">
            <el-table-column label="严重程度" width="80">
              <template #default="{ row }">
                <el-tag :type="row.severity === 'red' ? 'danger' : row.severity === 'orange' ? 'warning' : 'info'" size="small" effect="dark">
                  {{ row.severity === 'red' ? '严重' : row.severity === 'orange' ? '警告' : '提示' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="alert_content" label="预警内容" show-overflow-tooltip />
            <el-table-column label="触发时间" width="160">
              <template #default="{ row }">{{ formatTime(row.trigger_time) }}</template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { WarningFilled, TrendCharts, Sell, ShoppingCart, Money, Coin } from '@element-plus/icons-vue'
import { alertAPI, dataAPI } from '../../api'
import * as echarts from 'echarts'

const router = useRouter()

// ── 统计卡片 ──────────────────────────────────────────
const statCards = ref([
  { title: '总销售额', value: '加载中...', color: '#409eff', change: 0, icon: Money },
  { title: '总订单量', value: '加载中...', color: '#67c23a', change: 0, icon: ShoppingCart },
  { title: '平均客单价', value: '加载中...', color: '#e6a23c', change: 0, icon: Coin },
  { title: '毛利率', value: '加载中...', color: '#f56c6c', change: 0, icon: TrendCharts },
])

// ── 预警概览 ──────────────────────────────────────────
const pendingAlerts = ref([])
const trendRange = ref('30d')

// ── 图表 ──────────────────────────────────────────────
const trendChartRef = ref(null)
const pieChartRef = ref(null)
let trendChart = null
let pieChart = null

function initCharts() {
  // 销售趋势图
  if (trendChartRef.value) {
    trendChart = echarts.init(trendChartRef.value)
    trendChart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: {
        type: 'category',
        data: [],
        axisLine: { lineStyle: { color: '#dcdfe6' } },
      },
      yAxis: {
        type: 'value',
        splitLine: { lineStyle: { color: '#f0f2f5' } },
      },
      series: [
        {
          name: '销售额',
          type: 'line',
          smooth: true,
          data: [],
          areaStyle: { color: '#409eff20' },
          lineStyle: { color: '#409eff', width: 2 },
          itemStyle: { color: '#409eff' },
        },
      ],
    })
  }

  // 品类分布饼图
  if (pieChartRef.value) {
    pieChart = echarts.init(pieChartRef.value)
    pieChart.setOption({
      tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
      series: [
        {
          type: 'pie',
          radius: ['40%', '65%'],
          avoidLabelOverlap: true,
          itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
          label: { show: true, formatter: '{b}\n{d}%', fontSize: 11 },
          data: [],
        },
      ],
    })
  }
}

// ── 窗口自适应 ────────────────────────────────────────
function handleResize() {
  trendChart?.resize()
  pieChart?.resize()
}

// ── 获取仪表盘数据 ────────────────────────────────────
async function fetchDashboardData() {
  try {
    // 获取销售摘要
    const res = await dataAPI.querySales({
      start_date: '2025-01-01',
      end_date: '2026-06-08',
      group_by: 'month',
    })
    if (res.success !== false) {
      const data = res.data || res
      if (data.summary) {
        statCards.value[0].value = '¥' + Number(data.summary.total_sales || 0).toLocaleString()
        statCards.value[1].value = (data.summary.total_orders || 0).toLocaleString()
        statCards.value[2].value = '¥' + Number(data.summary.avg_order_value || 0).toFixed(2)
        statCards.value[3].value = (data.summary.margin_rate || 0) + '%'
        statCards.value[0].change = ((data.summary.change_rate || 0) * 100).toFixed(1)
      }
      // 更新图表
      if (data.series && trendChart) {
        trendChart.setOption({
          xAxis: { data: data.series.map((s) => s.date?.substring(0, 10)) },
          series: [{ data: data.series.map((s) => s.sales) }],
        })
      }
      if (data.by_category && pieChart) {
        const colors = ['#409eff', '#67c23a', '#e6a23c', '#f56c6c', '#909399', '#b37feb']
        pieChart.setOption({
          series: [{
            data: data.by_category.map((c, i) => ({
              name: c.category_name,
              value: c.sales,
              itemStyle: { color: colors[i % colors.length] },
            })),
          }],
        })
      }
    }
  } catch {
    // 后端未就绪时使用占位数据
    statCards.value[0].value = '¥0'
    statCards.value[1].value = '0'
    statCards.value[2].value = '¥0'
    statCards.value[3].value = '0%'
  }

  // 获取待处理预警
  try {
    const alertRes = await alertAPI.getLogs({ status: 'pending', page_size: 5 })
    if (alertRes.success !== false) {
      pendingAlerts.value = alertRes.data?.logs || alertRes.logs || []
    }
  } catch {
    pendingAlerts.value = []
  }
}

function formatTime(t) {
  if (!t) return '-'
  return t.replace('T', ' ').substring(0, 19)
}

function goAlert() {
  router.push('/alert')
}

onMounted(() => {
  initCharts()
  fetchDashboardData()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  trendChart?.dispose()
  pieChart?.dispose()
})
</script>

<style scoped>
.dashboard-page {
  max-width: 1400px;
  margin: 0 auto;
}

.stat-row {
  margin-bottom: 20px;
}

.stat-card {
  cursor: default;
}

.stat-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stat-title {
  font-size: 13px;
  color: #909399;
  margin-bottom: 6px;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  margin-bottom: 4px;
}

.stat-change {
  font-size: 12px;
}

.stat-change.up { color: #f56c6c; }
.stat-change.down { color: #67c23a; }

.stat-icon {
  opacity: 0.6;
}

.chart-row {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.alert-row {
  margin-bottom: 20px;
}
</style>