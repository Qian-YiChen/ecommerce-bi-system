<template>
  <div class="app-layout">
    <!-- 左侧导航 -->
    <el-menu
      :default-active="activeMenu"
      class="sidebar"
      :collapse="isCollapse"
      background-color="#001529"
      text-color="#ffffffbf"
      active-text-color="#fff"
      router
    >
      <div class="sidebar-header">
        <img src="/favicon.svg" alt="logo" class="logo" />
        <span v-show="!isCollapse" class="title">电商BI系统</span>
      </div>

      <el-menu-item index="/dashboard">
        <el-icon><Odometer /></el-icon>
        <template #title>仪表盘</template>
      </el-menu-item>

      <el-menu-item index="/alert">
        <el-icon><WarningFilled /></el-icon>
        <template #title>预警中心</template>
      </el-menu-item>

      <!-- 管理员菜单 -->
      <template v-if="isAdmin">
        <el-sub-menu index="admin">
          <template #title>
            <el-icon><Setting /></el-icon>
            <span>系统管理</span>
          </template>
          <el-menu-item index="/admin/users">
            <el-icon><User /></el-icon>
            <span>用户管理</span>
          </el-menu-item>
          <el-menu-item index="/admin/datasource">
            <el-icon><DataBoard /></el-icon>
            <span>数据源配置</span>
          </el-menu-item>
        </el-sub-menu>
      </template>
    </el-menu>

    <!-- 主内容区 -->
    <div class="main-container">
      <!-- 顶部导航栏 -->
      <header class="top-header">
        <el-button
          class="collapse-btn"
          :icon="isCollapse ? 'Expand' : 'Fold'"
          text
          @click="toggleCollapse"
        />
        <span class="page-title">{{ currentPageTitle }}</span>
        <div class="header-right">
          <el-dropdown trigger="click" @command="handleCommand">
            <span class="user-info">
              <el-avatar :size="32" icon="UserFilled" />
              <span class="username">{{ userStore.username }}</span>
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">
                  <el-icon><InfoFilled /></el-icon>个人信息
                </el-dropdown-item>
                <el-dropdown-item divided command="logout">
                  <el-icon><SwitchButton /></el-icon>退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <!-- 页面内容 -->
      <main class="content">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '../../stores/user'
import {
  Odometer, WarningFilled, Setting, User, DataBoard,
  UserFilled, ArrowDown, InfoFilled, SwitchButton,
} from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const isCollapse = ref(false)
const isAdmin = computed(() => userStore.isAdmin)

const activeMenu = computed(() => route.path)

const currentPageTitle = computed(() => route.meta?.title || '')

function toggleCollapse() {
  isCollapse.value = !isCollapse.value
}

function handleCommand(command) {
  if (command === 'logout') {
    userStore.logout()
    router.push('/login')
  }
}
</script>

<style scoped>
.app-layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

.sidebar {
  height: 100vh;
  overflow-y: auto;
  overflow-x: hidden;
  border-right: none;
  transition: width 0.3s;
}

.sidebar:not(.el-menu--collapse) {
  width: 220px;
}

.sidebar.el-menu--collapse {
  width: 64px;
}

.sidebar-header {
  display: flex;
  align-items: center;
  padding: 16px 20px;
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  gap: 10px;
  border-bottom: 1px solid #ffffff1a;
}

.logo {
  width: 28px;
  height: 28px;
}

.title {
  white-space: nowrap;
}

.main-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #f0f2f5;
}

.top-header {
  display: flex;
  align-items: center;
  padding: 0 20px;
  height: 56px;
  background: #fff;
  box-shadow: 0 1px 4px #0000000d;
  gap: 12px;
  z-index: 100;
}

.collapse-btn {
  font-size: 18px;
}

.page-title {
  font-size: 16px;
  font-weight: 500;
  color: #303133;
}

.header-right {
  margin-left: auto;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.username {
  font-size: 14px;
  color: #303133;
}

.content {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}
</style>