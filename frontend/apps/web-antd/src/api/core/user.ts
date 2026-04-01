import type { UserInfo } from '@vben/types';

import { baseRequestClient } from '#/api/request';

/**
 * 获取用户信息 - 对接FastAPI /api/auth/profile
 */
export async function getUserInfoApi(): Promise<UserInfo> {
  const res = await baseRequestClient.get<any>('/auth/profile');
  console.log('[getUserInfoApi] 完整响应:', res);

  // baseRequestClient可能返回 res 或 res.data
  const data = res?.data ?? res;
  console.log('[getUserInfoApi] 提取数据:', data);

  return {
    userId: data.id,
    username: data.username,
    realName: data.username,
    avatar: '',
    roles: data.roles ?? [],
    homePath: '/structural',
  };
}
