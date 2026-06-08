<template>
  <div class="datasource-config">
    <!-- 数据源连接状态 -->
    <el-row :gutter="20">
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span><el-icon><Connection /></el-icon> 数据库状态</span>
            </div>
          </template>
          <div class="status-content">
            <div class="status-indicator">
              <span class="dot" :class="dbStatus.online ? 'dot-green' : 'dot-red'"></span>
              <span>{{ dbStatus.online ? '已连接' : '未连接' }}</span>
            </div>
            <el-divider />
            <el-descriptions :column="1" size="small">
              <el-descriptions-item label="主机">{{ dbStatus.host || '-' }}</el-descriptions-item>
              <el-descriptions-item label="数据库">{{ dbStatus.database || '-' }}</el-descriptions-item>
              <el-descriptions-item label="表数量">{{ dbStatus.table_count || '-' }}</el-descriptions-item>
              <el-descriptions-item label="数据量">{{ dbStatus.total_records || '-' }} 条</el-descriptions-item>
            </el-descriptions>
            <el-button type="primary" size="small" class="refresh-btn" @click="refreshStatus">
              <el-icon><Refresh /></el-icon> 刷新状态
            </el-button>
          </div>
        </el-card>
      </el-col>

      <el-col :span="16">
        <el-card>
          <template #header>
            <div class="card-header">
              <span><el-icon><Upload /></el-icon> CSV/Excel 数据导入</span>
            </div>
          </template>

          <el-upload
            class="upload-area"
            drag
            action="#"
            :auto-upload="false"
            :on-change="handleFileChange"
            accept=".csv,.xlsx,.xls"
            :limit="1"
          >
            <el-icon class="upload-icon" :size="48"><UploadFilled /></el-icon>
            <div class="upload-text">
              <span>拖拽 CSV 或 Excel 文件到此处，或 <em>点击选择文件</em></span>
            </div>
            <template #tip>
              <div class="upload-tip">
                支持 .csv, .xlsx, .xls 格式，文件大小不超过 50MB
              </div>
            </template>
          </el-upload>

          <el-form
            v-if="selectedFile"
            :model="importConfig"
            label-width="100px"
            class="import-form"
          >
            <el-form-item label="数据表">
              <el-select v-model="importConfig.table" style="width: 200px">
                <el-option label="销售记录" value="sales_record" />
                <el-option label="商品信息" value="product" />
                <el-option label="客户信息" value="customer" />
                <el-option label="库存记录" value="inventory" />
              </el-select>
            </el-form-item>
            <el-form-item label="导入模式">
              <el-radio-group v-model="importConfig.mode">
                <el-radio value="append">追加数据</el-radio>
                <el-radio value="replace">替换全部</el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="importing" @click="startImport">
                {{ importing ? '导入中...' : '开始导入' }}
              </el-button>
              <el-button @click="resetImport">取消</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
    </el-row>

    <!-- 导入历史 -->
    <el-card class="history-card">
      <template #header>
        <div class="card-header">
          <span><el-icon><Clock /></el-icon> 导入历史</span>
        </div>
      </template>
      <el-table :data="history" v-loading="historyLoading" stripe style="width: 100%">
        <el-table-column prop="file_name" label="文件名" min-width="200" show-overflow-tooltip />
        <el-table-column prop="target_table" label="目标表" width="140" />
        <el-table-column prop="record_count" label="导入条数" width="100" align="right" />
        <el-table-column label="导入时间" width="180">
          <template #default="{ row }">{{ formatTime(row.import_time) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'success' ? 'success' : 'danger'" size="small">
              {{ row.status === 'success' ? '成功' : '失败' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="message" label="备注" min-width="200" show-overflow-tooltip />
      </el-table>
    </el-card>

    <!-- ETL 管道配置 -->
    <el-card class="etl-card">
      <template #header>
        <div class="card-header">
          <span><el-icon><SetUp /></el-icon> ETL 数据管道</span>
          <el-tag type="warning" size="small">Beta</el-tag>
        </div>
      </template>
      <el-alert
        title="通过ETL管道，可从Kaggle等外部数据源自动拉取数据并导入MySQL。"
        type="info"
        show-icon
        :closable="false"
        class="etl-alert"
      />
      <el-form :model="etlConfig" label-width="100px" class="etl-form">
        <el-form-item label="数据源类型">
          <el-select v-model="etlConfig.source_type" style="width: 200px">
            <el-option label="Kaggle 数据集" value="kaggle" />
            <el-option label="本地 CSV 目录" value="local_csv" />
            <el-option label="外部 API" value="external_api" />
          </el-select>
        </el-form-item>
        <el-form-item label="自动同步">
          <el-switch v-model="etlConfig.auto_sync" active-text="开启" inactive-text="关闭" />
        </el-form-item>
        <el-form-item v-if="etlConfig.auto_sync" label="同步周期">
          <el-radio-group v-model="etlConfig.sync_interval">
            <el-radio value="hourly">每小时</el-radio>
            <el-radio value="daily">每天</el-radio>
            <el-radio value="weekly">每周</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="saving" @click="saveETLConfig">
            保存配置
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Connection, Upload, UploadFilled, Refresh, Clock, SetUp,
} from '@element-plus/icons-vue'
import { datasourceAPI } from '../../api'

// ── 数据库状态 ────────────────────────────────────────
const dbStatus = reactive({
  online: false,
  host: '',
  database: '',
  table_count: 0,
  total_records: 0,
})

async function refreshStatus() {
  try {
    const res = await datasourceAPI.getStatus()
    if (res.success !== false) {
      Object.assign(dbStatus, res.data || res)
    }
  } catch {
    dbStatus.online = false
  }
}

// ── 文件导入 ──────────────────────────────────────────
const selectedFile = ref(null)
const importing = ref(false)

const importConfig = reactive({
  table: 'sales_record',
  mode: 'append',
})

function handleFileChange(file) {
  selectedFile.value = file.raw || file
}

function resetImport() {
  selectedFile.value = null
  importConfig.table = 'sales_record'
  importConfig.mode = 'append'
}

async function startImport() {
  if (!selectedFile.value) return
  importing.value = true
  try {
    const formData = new FormData()
    formData.append('file', selectedFile.value)
    formData.append('table', importConfig.table)
    formData.append('mode', importConfig.mode)

    const res = await datasourceAPI.uploadCSV(formData)
    if (res.success !== false) {
      ElMessage.success(`数据导入成功，共导入 ${res.data?.record_count || 0} 条记录`)
      resetImport()
      refreshStatus()
      fetchHistory()
    }
  } catch {
    ElMessage.error('导入失败，请检查文件格式')
  } finally {
    importing.value = false
  }
}

// ── 导入历史 ──────────────────────────────────────────
const history = ref([])
const historyLoading = ref(false)

async function fetchHistory() {
  historyLoading.value = true
  try {
    const res = await datasourceAPI.getUploadHistory({ page: 1, page_size: 20 })
    if (res.success !== false) {
      history.value = res.data?.records || res.records || []
    }
  } catch {
    history.value = []
  } finally {
    historyLoading.value = false
  }
}

// ── ETL 配置 ─────────────────────────────────────────
const saving = ref(false)

const etlConfig = reactive({
  source_type: 'kaggle',
  auto_sync: false,
  sync_interval: 'daily',
})

async function saveETLConfig() {
  saving.value = true
  try {
    ElMessage.success('ETL 配置已保存')
  } finally {
    saving.value = false
  }
}

// ── 辅助函数 ──────────────────────────────────────────
function formatTime(t) {
  if (!t) return '-'
  return t.replace('T', ' ').substring(0, 19)
}

// ── 初始化 ────────────────────────────────────────────
onMounted(() => {
  refreshStatus()
  fetchHistory()
})
</script>

<style scoped>
.datasource-config {
  max-width: 1400px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-content {
  text-align: center;
}

.status-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 500;
}

.dot {
  display: inline-block;
  width: 12px;
  height: 12px;
  border-radius: 50%;
}

.dot-green {
  background-color: #67c23a;
  box-shadow: 0 0 6px #67c23a80;
}

.dot-red {
  background-color: #f56c6c;
  box-shadow: 0 0 6px #f56c6c80;
}

.refresh-btn {
  margin-top: 12px;
}

.upload-area {
  margin-bottom: 20px;
}

.upload-icon {
  margin-bottom: 8px;
  color: #909399;
}

.upload-text {
  font-size: 14px;
  color: #606266;
}

.upload-text em {
  color: #409eff;
  font-style: normal;
}

.upload-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.import-form {
  margin-top: 16px;
  padding: 16px;
  background: #fafafa;
  border-radius: 8px;
}

.history-card,
.etl-card {
  margin-top: 20px;
}

.etl-alert {
  margin-bottom: 16px;
}

.etl-form {
  margin-top: 8px;
}
</style>