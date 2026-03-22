/**
 * Auth Store
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { authApi } from '@/api/auth'
import type { UserResponse } from '@/types/api'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const user = ref<UserResponse | null>(null)
  const isAuthenticated = ref(!!token.value)

  const login = async (username: string, password: string) => {
    const res = await authApi.login({ username, password })
    token.value = res.access_token
    isAuthenticated.value = true
    localStorage.setItem('token', res.access_token)
    await fetchProfile()
  }

  const logout = () => {
    token.value = ''
    user.value = null
    isAuthenticated.value = false
    localStorage.removeItem('token')
  }

  const fetchProfile = async () => {
    user.value = await authApi.getProfile()
  }

  return { token, user, isAuthenticated, login, logout, fetchProfile }
})
