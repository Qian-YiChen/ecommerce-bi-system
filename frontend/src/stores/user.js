/**
 * 用户状态管理
 * -----------
 * 管理登录状态、用户信息、角色权限
 */
import { defineStore } from 'pinia'
import { authAPI } from '../api'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    user: JSON.parse(localStorage.getItem('user') || 'null'),
  }),

  getters: {
    isLoggedIn: (state) => !!state.token,
    isAdmin: (state) => state.user?.role === 'admin',
    username: (state) => state.user?.username || '',
    role: (state) => state.user?.role || '',
  },

  actions: {
    async login(username, password) {
      const res = await authAPI.login(username, password)
      if (res.success) {
        // 后端统一格式: {success, data: {token, user}, message}
        // 兼容 mock: {success, token, user}
        const token = res.data?.token || res.token
        const user = res.data?.user || res.user
        this.token = token
        this.user = user
        localStorage.setItem('token', token)
        localStorage.setItem('user', JSON.stringify(user))
      }
      return res
    },

    logout() {
      this.token = ''
      this.user = null
      localStorage.removeItem('token')
      localStorage.removeItem('user')
    },

    async fetchUserInfo() {
      try {
        const res = await authAPI.getMe()
        if (res.success !== false) {
          // 后端格式: {success, data: {user_id, username, role}, message}
          const user = res.data || res
          this.user = user
          localStorage.setItem('user', JSON.stringify(user))
        }
      } catch {
        // Token 过期，已由拦截器处理
      }
    },
  },
})