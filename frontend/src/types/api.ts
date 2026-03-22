/**
 * API Types
 */

export interface LoginRequest {
  username: string
  password: string
}

export interface RegisterRequest {
  username: string
  email: string
  password: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  expires_in: number
}

export interface UserResponse {
  id: string
  username: string
  email: string
  quota_daily: number
  quota_monthly: number
  created_at: string
}

export interface DesignCreateRequest {
  request_text: string
}

export interface TaskResponse {
  id: string
  status: string
  request_text: string
  structure_type?: string
  created_at: string
  completed_at?: string
}

export interface TaskDetailResponse extends TaskResponse {
  result_json?: any
}
