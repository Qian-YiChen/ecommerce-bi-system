/**
 * 路由配置
 * -------
 * 包含路由守卫：未登录自动跳转登录页
 * 管理员页面需要 admin 角色
 */
import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/login/LoginPage.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/',
    component: () => import('../components/layout/AppLayout.vue'),
    meta: { requiresAuth: true },
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('../views/dashboard/DashboardPage.vue'),
        meta: { title: '仪表盘', icon: 'Odometer' },
      },
      {
        path: 'alert',
        name: 'Alert',
        component: () => import('../views/alert/AlertPage.vue'),
        meta: { title: '预警中心', icon: 'WarningFilled' },
      },
      {
        path: 'admin/users',
        name: 'AdminUsers',
        component: () => import('../views/admin/UserManagement.vue'),
        meta: { title: '用户管理', icon: 'User', roles: ['admin'] },
      },
      {
        path: 'admin/datasource',
        name: 'AdminDatasource',
        component: () => import('../views/admin/DatasourceConfig.vue'),
        meta: { title: '数据源配置', icon: 'DataBoard', roles: ['admin'] },
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// ── 路由守卫 ──────────────────────────────────────────
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  const user = JSON.parse(localStorage.getItem('user') || 'null')

  // 未登录跳转登录页
  if (to.meta.requiresAuth && !token) {
    return next('/login')
  }

  // 已登录访问登录页，跳转仪表盘
  if (to.path === '/login' && token) {
    return next('/dashboard')
  }

  // 检查角色权限
  if (to.meta.roles && user) {
    if (!to.meta.roles.includes(user.role)) {
      ElMessage?.error?.('权限不足')
      return next('/dashboard')
    }
  }

  next()
})

export default router