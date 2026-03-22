/**
 * Design API
 */
import request from '@/utils/request'
import type { DesignCreateRequest, TaskResponse, TaskDetailResponse } from '@/types/api'

export const designApi = {
  create: (data: DesignCreateRequest) =>
    request.post<any, TaskResponse>('/design/create', data),

  list: () =>
    request.get<any, TaskResponse[]>('/design/list'),

  getStatus: (taskId: string) =>
    request.get<any, TaskDetailResponse>(`/design/${taskId}/status`)
}
