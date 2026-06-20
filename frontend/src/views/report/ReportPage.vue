<template>
  <div class="report-page">
    <el-row :gutter="16">
      <el-col :span="12">
        <!-- 生成报表 -->
        <el-card>
          <template #header><span>📊 生成报表</span></template>
          <el-form label-width="100px" size="default">
            <el-form-item label="报表类型">
              <el-select v-model="form.report_type" style="width:100%">
                <el-option label="日报" value="daily" />
                <el-option label="周报" value="weekly" />
                <el-option label="月报" value="monthly" />
                <el-option label="自定义" value="custom" />
              </el-select>
            </el-form-item>
            <el-form-item label="导出格式">
              <el-radio-group v-model="form.format">
                <el-radio-button value="excel">Excel (.xlsx)</el-radio-button>
                <el-radio-button value="csv">CSV (.csv)</el-radio-button>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="日期范围">
              <el-date-picker
                v-model="form.dateRange"
                type="daterange"
                range-separator="至"
                start-placeholder="开始"
                end-placeholder="结束"
                value-format="YYYY-MM-DD"
                style="width:100%"
              />
            </el-form-item>
            <el-form-item label="粒度">
              <el-radio-group v-model="form.group_by">
                <el-radio-button value="day">按日</el-radio-button>
                <el-radio-button value="week">按周</el-radio-button>
                <el-radio-button value="month">按月</el-radio-button>
              </el-radio-group>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="generating" @click="generateReport" style="width:100%">
                <el-icon style="margin-right:4px"><Document /></el-icon>生成报表
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <el-col :span="12">
        <!-- 下载区 -->
        <el-card>
          <template #header><span>📥 下载报表</span></template>
          <div v-if="generatedFiles.length === 0" class="empty-hint">
            <el-icon :size="48" color="#c0c4cc"><FolderOpened /></el-icon>
            <p>暂无已生成的报表</p>
            <p style="font-size:12px;color:#c0c4cc">在左侧选择参数后点击"生成报表"</p>
          </div>
          <div v-for="f in generatedFiles" :key="f.filename" class="file-item">
            <div class="file-info">
              <el-icon color="#409eff"><Document /></el-icon>
              <span style="margin-left:8px">{{ f.filename }}</span>
            </div>
            <el-button type="primary" size="small" @click="downloadFile(f)">
              下载
            </el-button>
          </div>
        </el-card>

        <!-- 报表历史 -->
        <el-card style="margin-top:16px">
          <template #header><span>⏱ 生成历史</span></template>
          <el-timeline v-if="history.length > 0">
            <el-timeline-item
              v-for="(h, i) in history"
              :key="i"
              :timestamp="h.time"
              :type="h.status === 'success' ? 'success' : 'danger'"
            >
              {{ h.message }}
            </el-timeline-item>
          </el-timeline>
          <div v-else class="empty-hint" style="padding:20px">
            <p style="color:#c0c4cc">暂无生成记录</p>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { Document, FolderOpened } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { reportAPI } from '../../api'

const generating = ref(false)
const generatedFiles = ref([])
const history = ref([])

const form = reactive({
  report_type: 'monthly',
  format: 'excel',
  dateRange: ['2025-01-01', '2026-06-08'],
  group_by: 'month',
})

async function generateReport() {
  if (!form.dateRange || form.dateRange.length !== 2) {
    ElMessage.warning('请选择日期范围')
    return
  }
  generating.value = true
  try {
    const [start, end] = form.dateRange
    const res = await reportAPI.generate({
      report_type: form.report_type,
      format: form.format,
      params: {
        start_date: start,
        end_date: end,
        group_by: form.group_by,
      },
    })
    if (res.success !== false) {
      const data = res.data || res
      const file = {
        filename: data.filename || `report_${form.report_type}_${Date.now()}.${form.format === 'excel' ? 'xlsx' : 'csv'}`,
        download_url: data.download_url || '',
      }
      generatedFiles.value.unshift(file)
      history.value.unshift({
        time: new Date().toLocaleString(),
        status: 'success',
        message: `生成成功：${file.filename}`,
      })
      ElMessage.success('报表生成成功')
    }
  } catch {
    history.value.unshift({
      time: new Date().toLocaleString(),
      status: 'error',
      message: '生成失败，请确认后端已启动',
    })
    ElMessage.error('报表生成失败')
  } finally {
    generating.value = false
  }
}

function downloadFile(file) {
  const base = 'http://localhost:5000'
  window.open(base + file.download_url, '_blank')
}
</script>

<style scoped>
.report-page { padding: 0; }
.empty-hint { text-align: center; padding: 40px 0; color: #909399; }
.file-item { display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid #ebeef5; }
.file-info { display: flex; align-items: center; }
</style>
