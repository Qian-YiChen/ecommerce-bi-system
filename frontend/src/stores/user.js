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
        this.token = res.token
        this.user = res.user
        localStorage.setItem('token', res.token)
        localStorage.setItem('user', JSON.stringify(res.user))
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
          this.user = res
          localStorage.setItem('user', JSON.stringify(res))
        }
      } catch {
        // Token 过期，已由拦截器处理
      }
    },
  },
})