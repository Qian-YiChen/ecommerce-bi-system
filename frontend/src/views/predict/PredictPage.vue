<template>
  <div class="predict-page">
    <el-tabs v-model="activeTab" type="border-card">
      <!-- 销售预测 Tab -->
      <el-tab-pane label="销售预测" name="sales">
        <el-button type="primary" :loading="salesLoading" @click="loadSales" style="margin-bottom:16px">
          <el-icon style="margin-right:4px"><Refresh /></el-icon>刷新预测数据
        </el-button>
        <span style="margin-left:12px;color:#909399;font-size:13px">
          基于线性回归模型，预测未来7天各商品日销量（共24商品×7天=168条记录）
        </span>

        <el-card style="margin-top:12px">
          <template #header>预测销量趋势（TOP 6 商品）</template>
          <div ref="forecastChart" style="height: 340px"></div>
        </el-card>

        <el-card style="margin-top:16px">
          <template #header>全部预测明细</template>
          <el-table :data="paginatedForecast" stripe size="default" empty-text="暂无预测数据，请先运行ML管道">
            <el-table-column prop="product_name" label="商品名称" width="200" />
            <el-table-column prop="forecast_date" label="预测日期" width="140" sortable />
            <el-table-column prop="predicted_quantity" label="预测销量（件）" width="140" sortable />
            <el-table-column prop="model_type" label="模型" width="120" />
          </el-table>
          <el-pagination
            v-model:current-page="fcPage"
            :page-size="14"
            :total="forecastData.length"
            layout="prev, pager, next"
            style="margin-top:12px"
          />
        </el-card>
      </el-tab-pane>

      <!-- 库存补货 Tab -->
      <el-tab-pane label="库存补货建议" name="stock">
        <el-button type="warning" :loading="stockLoading" @click="loadStock" style="margin-bottom:16px">
          <el-icon style="margin-right:4px"><Refresh /></el-icon>刷新补货建议
        </el-button>
        <span style="margin-left:12px;color:#909399;font-size:13px">
          安全库存模型：95%服务水平（z=1.65），提前期3天，库存数据来自product.stock_quantity
        </span>

        <el-card style="margin-top:12px">
          <el-table :data="stockData" stripe size="default" empty-text="暂无数据">
            <el-table-column prop="product_name" label="商品名称" width="200" />
            <el-table-column prop="current_stock" label="当前库存" width="100" sortable />
            <el-table-column prop="demand_next_3_days" label="未来3天需求" width="120" sortable />
            <el-table-column prop="safety_stock" label="安全库存" width="100" sortable />
            <el-table-column prop="suggest_replenish" label="建议补货" width="120" sortable>
              <template #default="{ row }">
                <el-tag :type="row.suggest_replenish > 0 ? 'danger' : 'success'">
                  {{ row.suggest_replenish > 0 ? row.suggest_replenish : '充足' }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { predictAPI } from '../../api'

const activeTab = ref('sales')
const salesLoading = ref(false)
const stockLoading = ref(false)
const forecastData = ref([])
const stockData = ref([])
const fcPage = ref(1)
const forecastChart = ref(null)
let fcInstance = null

const paginatedForecast = computed(() => {
  const start = (fcPage.value - 1) * 14
  return forecastData.value.slice(start, start + 14)
})

async function loadSales() {
  salesLoading.value = true
  try {
    const res = await predictAPI.getSalesForecast()
    const data = res.data || res
    forecastData.value = Array.isArray(data) ? data : (data.forecast || [])
    if (forecastData.value.length > 0) {
      ElMessage.success(`已加载 ${forecastData.value.length} 条预测记录`)
      renderChart()
    } else {
      ElMessage.info('暂无预测数据，请先执行 python ml/ml_pipeline.py')
    }
  } catch {
    ElMessage.warning('加载预测失败，请确认后端已启动')
  } finally {
    salesLoading.value = false
  }
}

async function loadStock() {
  stockLoading.value = true
  try {
    const res = await predictAPI.getStockSuggestions()
    const data = res.data || res
    stockData.value = Array.isArray(data) ? data : (data.products || [])
    if (stockData.value.length > 0) {
      ElMessage.success(`已加载 ${stockData.value.length} 条补货建议`)
    }
  } catch {
    ElMessage.warning('加载失败，请确认后端已启动')
  } finally {
    stockLoading.value = false
  }
}

function renderChart() {
  if (!fcInstance || forecastData.value.length === 0) return
  // 取TOP 6商品
  const top6 = [...new Set(forecastData.value.map(f => f.product_name))].slice(0, 6)
  const dates = [...new Set(forecastData.value.map(f => f.forecast_date))].sort()
  const colors = ['#409eff', '#67c23a', '#e6a23c', '#f56c6c', '#909399', '#b37feb']

  fcInstance.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: top6, bottom: 0 },
    xAxis: { type: 'category', data: dates },
    yAxis: { type: 'value', name: '预测销量（件）' },
    series: top6.map((name, i) => ({
      name, type: 'line',
      data: dates.map(d => {
        const f = forecastData.value.find(x => x.product_name === name && x.forecast_date === d)
        return f ? f.predicted_quantity : 0
      }),
      itemStyle: { color: colors[i] },
    })),
    grid: { left: 50, right: 20, top: 20, bottom: 40 },
  })
}

onMounted(() => {
  nextTick(() => {
    if (forecastChart.value) fcInstance = echarts.init(forecastChart.value)
    loadSales()
    loadStock()
  })
})
</script>

<style scoped>
.predict-page { padding: 0; }
</style>
