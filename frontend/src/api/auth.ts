/**
 * Authentication API
 */
import request from '@/utils/request'
import type { LoginRequest, RegisterRequest, TokenResponse, UserResponse } from '@/types/api'

export const authApi = {
  login: (data: LoginRequest) =>
    request.post<any, TokenResponse>('/auth/login', data),

  register: (data: RegisterRequest) =>
    request.post<any, UserResponse>('/auth/register', data),

  getProfile: () =>
    request.get<any, UserResponse>('/auth/profile')
}
