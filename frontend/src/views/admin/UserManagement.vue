<template>
  <div class="user-management">
    <!-- 操作栏 -->
    <el-card class="toolbar-card">
      <el-row :gutter="16" justify="space-between" align="middle">
        <el-col :span="12">
          <el-button type="primary" @click="openCreateDialog">
            <el-icon><Plus /></el-icon> 新建用户
          </el-button>
        </el-col>
        <el-col :span="12" style="text-align: right">
          <el-input
            v-model="searchQuery"
            placeholder="搜索用户名..."
            :prefix-icon="Search"
            clearable
            style="width: 240px"
            @input="debounceSearch"
          />
        </el-col>
      </el-row>
    </el-card>

    <!-- 用户列表 -->
    <el-card class="table-card">
      <el-table :data="users" v-loading="loading" stripe style="width: 100%">
        <el-table-column type="index" label="#" width="50" />
        <el-table-column prop="username" label="用户名" min-width="150" />
        <el-table-column label="角色" width="140">
          <template #default="{ row }">
            <el-tag :type="roleTag(row.role)" size="small" effect="plain">
              {{ roleText(row.role) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'danger'" size="small">
              {{ row.status === 1 ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="openEditDialog(row)">编辑</el-button>
            <el-button
              size="small"
              :type="row.status === 1 ? 'warning' : 'success'"
              plain
              @click="toggleStatus(row)"
            >
              {{ row.status === 1 ? '禁用' : '启用' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          @change="fetchUsers"
        />
      </div>
    </el-card>

    <!-- 创建/编辑用户对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEditing ? '编辑用户' : '新建用户'"
      width="500px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="formRules"
        label-width="80px"
        @keyup.enter="handleSubmit"
      >
        <el-form-item label="用户名" prop="username">
          <el-input
            v-model="form.username"
            :disabled="isEditing"
            placeholder="3-30个字符"
          />
        </el-form-item>
        <el-form-item label="密码" :prop="isEditing ? undefined : 'password'">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            :placeholder="isEditing ? '留空则不修改密码' : '至少6个字符'"
          />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="form.role" style="width: 100%">
            <el-option label="管理员" value="admin" />
            <el-option label="分析师" value="analyst" />
            <el-option label="运营经理" value="manager" />
            <el-option label="观察者" value="viewer" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="isEditing" label="状态">
          <el-switch
            v-model="form.status"
            :active-value="1"
            :inactive-value="0"
            active-text="启用"
            inactive-text="禁用"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="handleSubmit">
          {{ isEditing ? '保存修改' : '创建用户' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search } from '@element-plus/icons-vue'
import { userAPI, authAPI } from '../../api'

// ── 数据 ──────────────────────────────────────────────
const users = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const searchQuery = ref('')
let searchTimer = null

const dialogVisible = ref(false)
const isEditing = ref(false)
const editingId = ref(null)
const submitLoading = ref(false)
const formRef = ref(null)

const defaultForm = () => ({
  username: '',
  password: '',
  role: 'analyst',
  status: 1,
})

const form = reactive(defaultForm())

const formRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 30, message: '用户名长度3-30个字符', trigger: 'blur' },
  ],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }],
}

// ── 获取用户列表 ──────────────────────────────────────
async function fetchUsers() {
  loading.value = true
  try {
    const params = {
      page: page.value,
      page_size: pageSize.value,
    }
    if (searchQuery.value) params.username = searchQuery.value

    const res = await userAPI.list(params)
    if (res.success !== false) {
      users.value = res.data?.users || res.users || []
      total.value = res.data?.total || res.total || 0
    }
  } catch {
    users.value = []
  } finally {
    loading.value = false
  }
}

// ── 防抖搜索 ──────────────────────────────────────────
function debounceSearch() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    page.value = 1
    fetchUsers()
  }, 300)
}

// ── 打开创建对话框 ────────────────────────────────────
function openCreateDialog() {
  isEditing.value = false
  editingId.value = null
  Object.assign(form, defaultForm())
  dialogVisible.value = true
}

// ── 打开编辑对话框 ────────────────────────────────────
function openEditDialog(row) {
  isEditing.value = true
  editingId.value = row.user_id || row.id
  form.username = row.username
  form.password = ''
  form.role = row.role
  form.status = row.status
  dialogVisible.value = true
}

// ── 提交表单 ──────────────────────────────────────────
async function handleSubmit() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitLoading.value = true
  try {
    if (isEditing.value) {
      // 编辑用户 - 使用 authAPI.register 或 userAPI.update
      const data = { role: form.role, status: form.status }
      if (form.password) data.password = form.password
      const res = await userAPI.update(editingId.value, data)
      if (res.success !== false) {
        ElMessage.success('用户信息已更新')
        dialogVisible.value = false
        await fetchUsers()
      }
    } else {
      // 创建用户
      const res = await authAPI.register(form.username, form.password, form.role)
      if (res.success !== false) {
        ElMessage.success('用户创建成功')
        dialogVisible.value = false
        await fetchUsers()
      }
    }
  } catch {
    // 错误已由拦截器处理
  } finally {
    submitLoading.value = false
  }
}

// ── 切换用户状态 ──────────────────────────────────────
async function toggleStatus(row) {
  const action = row.status === 1 ? '禁用' : '启用'
  try {
    await ElMessageBox.confirm(
      `确定${action}用户「${row.username}」？`,
      '确认操作',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )
    const res = await userAPI.toggleStatus(row.user_id || row.id)
    if (res.success !== false) {
      ElMessage.success(`用户已${action}`)
      await fetchUsers()
    }
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error('操作失败')
    }
  }
}

// ── 辅助函数 ──────────────────────────────────────────
function formatTime(t) {
  if (!t) return '-'
  return t.replace('T', ' ').substring(0, 19)
}

function roleTag(role) {
  const map = { admin: 'danger', analyst: 'success', manager: 'primary', viewer: 'info' }
  return map[role] || 'info'
}

function roleText(role) {
  const map = { admin: '管理员', analyst: '分析师', manager: '运营经理', viewer: '观察者' }
  return map[role] || role
}

// ── 初始化 ────────────────────────────────────────────
onMounted(fetchUsers)
</script>

<style scoped>
.user-management {
  max-width: 1200px;
  margin: 0 auto;
}

.toolbar-card {
  margin-bottom: 20px;
}

.table-card .pagination-wrapper {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>