<template>
  <div class="query-page">
    <!-- 筛选栏 -->
    <el-card class="filter-card">
      <el-form :inline="true" :model="filters" size="default">
        <el-form-item label="日期范围">
          <el-date-picker
            v-model="filters.dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            style="width: 260px"
          />
        </el-form-item>
        <el-form-item label="地区">
          <el-select v-model="filters.region" placeholder="全国" clearable style="width: 140px">
            <el-option v-for="r in regions" :key="r" :label="r" :value="r" />
          </el-select>
        </el-form-item>
        <el-form-item label="品类">
          <el-select v-model="filters.category_id" placeholder="全品类" clearable style="width: 140px">
            <el-option v-for="c in categories" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="渠道">
          <el-select v-model="filters.channel" placeholder="全渠道" clearable style="width: 120px">
            <el-option label="PC" value="PC" />
            <el-option label="Mobile" value="Mobile" />
            <el-option label="小程序" value="Miniprogram" />
          </el-select>
        </el-form-item>
        <el-form-item label="粒度">
          <el-radio-group v-model="filters.group_by">
            <el-radio-button value="day">按日</el-radio-button>
            <el-radio-button value="week">按周</el-radio-button>
            <el-radio-button value="month">按月</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="fetchData">
            <el-icon style="margin-right:4px"><Search /></el-icon>查询
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 指标卡片 -->
    <el-row :gutter="16" class="summary-row">
      <el-col :span="6" v-for="card in summaryCards" :key="card.label">
        <el-card :body-style="{ padding: '18px 20px' }">
          <div class="card-label">{{ card.label }}</div>
          <div class="card-value" :style="{ color: card.color }">{{ card.value }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表区 -->
    <el-row :gutter="16">
      <el-col :span="16">
        <el-card>
          <template #header><span>销售趋势</span></template>
          <div ref="trendChart" style="height: 320px"></div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card>
          <template #header><span>品类分布</span></template>
          <div ref="pieChart" style="height: 320px"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 地区分布 -->
    <el-card style="margin-top:16px">
      <template #header><span>地区分布</span></template>
      <el-table :data="regionData" stripe size="default" empty-text="暂无数据">
        <el-table-column prop="region" label="地区" width="160" />
        <el-table-column prop="sales" label="销售额（元）" sortable>
          <template #default="{ row }">¥{{ Number(row.sales).toLocaleString() }}</template>
        </el-table-column>
        <el-table-column prop="percentage" label="占比" width="140">
          <template #default="{ row }">{{ (row.percentage * 100).toFixed(1) }}%</template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, nextTick, watch } from 'vue'
import { Search } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { dataAPI } from '../../api'

const loading = ref(false)
const trendChart = ref(null)
const pieChart = ref(null)
let trendInstance = null
let pieInstance = null

const regions = ['广东', '北京', '上海', '浙江', '江苏', '四川', '湖北', '山东', '辽宁', '福建', '河南', '湖南', '安徽', '重庆', '陕西', '江西', '广西']
const categories = [
  { id: 1, name: '服装鞋包' }, { id: 2, name: '数码电子' }, { id: 3, name: '食品饮料' },
  { id: 4, name: '美妆个护' }, { id: 5, name: '家居生活' },
]

const filters = reactive({
  dateRange: ['2025-01-01', '2026-06-08'],
  region: null,
  category_id: null,
  channel: null,
  group_by: 'month',
})

const summaryCards = ref([
  { label: '总销售额', value: '¥0', color: '#409eff' },
  { label: '总订单量', value: '0', color: '#67c23a' },
  { label: '平均客单价', value: '¥0', color: '#e6a23c' },
  { label: '环比变化', value: '0%', color: '#f56c6c' },
])

const regionData = ref([])

async function fetchData() {
  loading.value = true
  try {
    const [start, end] = filters.dateRange
    const params = {
      start_date: start, end_date: end,
      group_by: filters.group_by,
    }
    if (filters.region) params.region = filters.region
    if (filters.category_id) params.category_id = filters.category_id
    if (filters.channel) params.channel = filters.channel

    const res = await dataAPI.querySales(params)
    const data = res.data || res
    if (data.summary) {
      summaryCards.value[0].value = '¥' + Number(data.summary.total_sales || 0).toLocaleString()
      summaryCards.value[1].value = (data.summary.total_orders || 0).toLocaleString()
      summaryCards.value[2].value = '¥' + Number(data.summary.avg_order_value || 0).toFixed(2)
      const cr = data.summary.change_rate || 0
      summaryCards.value[3].value = (cr >= 0 ? '+' : '') + (cr * 100).toFixed(1) + '%'
      summaryCards.value[3].color = cr >= 0 ? '#67c23a' : '#f56c6c'
    }

    regionData.value = data.by_region || []

    // 趋势图
    if (trendInstance && data.series) {
      trendInstance.setOption({
        tooltip: { trigger: 'axis' },
        xAxis: { type: 'category', data: data.series.map(s => s.date?.substring(0, 10)) },
        yAxis: { type: 'value' },
        series: [{
          data: data.series.map(s => s.sales), type: 'line',
          smooth: true, areaStyle: { opacity: 0.15 },
          itemStyle: { color: '#409eff' },
        }],
        grid: { left: 50, right: 20, top: 20, bottom: 30 },
      })
    }

    // 品类饼图
    if (pieInstance && data.by_category) {
      const colors = ['#409eff', '#67c23a', '#e6a23c', '#f56c6c', '#909399', '#b37feb']
      pieInstance.setOption({
        tooltip: { trigger: 'item', formatter: '{b}: {c}元 ({d}%)' },
        series: [{
          type: 'pie', radius: ['45%', '75%'], center: ['50%', '55%'],
          data: data.by_category.map((c, i) => ({
            name: c.category_name, value: c.sales,
            itemStyle: { color: colors[i % colors.length] },
          })),
          label: { formatter: '{b}\n{d}%' },
        }],
      })
    }
  } catch {
    ElMessage.warning('查询失败，请确认后端已启动')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  nextTick(() => {
    if (trendChart.value) trendInstance = echarts.init(trendChart.value)
    if (pieChart.value) pieInstance = echarts.init(pieChart.value)
    fetchData()
  })
})
</script>

<style scoped>
.query-page { padding: 0; }
.filter-card { margin-bottom: 16px; }
.summary-row { margin-bottom: 16px; }
.card-label { font-size: 13px; color: #909399; margin-bottom: 6px; }
.card-value { font-size: 24px; font-weight: 700; }
</style>
