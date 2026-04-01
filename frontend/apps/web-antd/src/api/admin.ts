import { baseRequestClient } from '#/api/request';

export interface AdminUser {
  id: string;
  username: string;
  email: string;
  roles: string[];
}

export interface AdminRole {
  id: string;
  name: string;
  display_name: string;
  description: string;
}

export async function getAdminUsersApi() {
  const res = await baseRequestClient.get<any>('/admin/users');
  const data = (res as any)?.data ?? res;
  return { users: data?.users ?? data ?? [] };
}

export async function getAdminRolesApi() {
  const res = await baseRequestClient.get<any>('/admin/roles');
  const data = (res as any)?.data ?? res;
  return { roles: data?.roles ?? data ?? [] };
}

export async function assignRoleApi(userId: string, roleId: string) {
  return baseRequestClient.post(`/admin/users/${userId}/roles`, { role_id: roleId });
}
