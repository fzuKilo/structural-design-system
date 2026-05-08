import { baseRequestClient } from '#/api/request';

export interface DesignTask {
  id: string;
  status: string;
  request_text: string;
  structure_type: string;
  created_at: string;
  completed_at: string | null;
}

export interface CreateDesignParams {
  request_text: string;
  structure_type?: string;
}

export async function getDesignListApi() {
  const res = await baseRequestClient.get<any>('/design/list');
  // baseRequestClient返回完整response，取data字段
  return (res as any)?.data ?? res ?? [];
}

export async function createDesignApi(data: CreateDesignParams) {
  const res = await baseRequestClient.post<any>('/design/create', data);
  return (res as any)?.data ?? res;
}

export async function getDesignDetailApi(taskId: string) {
  const res = await baseRequestClient.get<any>(`/design/${taskId}/status`);
  return (res as any)?.data ?? res;
}

export async function cancelDesignApi(taskId: string) {
  const res = await baseRequestClient.post<any>(`/design/${taskId}/cancel`);
  return (res as any)?.data ?? res;
}

export async function deleteDesignApi(taskId: string) {
  const res = await baseRequestClient.delete<any>(`/design/${taskId}`);
  return (res as any)?.data ?? res;
}

export async function getPendingAskApi(taskId: string) {
  const res = await baseRequestClient.get<any>(`/design/${taskId}/pending-ask`);
  return (res as any)?.data ?? res;
}

export async function respondDesignApi(taskId: string, answer: string) {
  const res = await baseRequestClient.post<any>(`/design/${taskId}/respond`, { answer });
  return (res as any)?.data ?? res;
}
