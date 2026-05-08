import { baseRequestClient, requestClient } from '#/api/request';

export namespace AuthApi {
  export interface LoginParams {
    password?: string;
    username?: string;
  }

  export interface LoginResult {
    accessToken: string;
  }

  export interface RefreshTokenResult {
    data: string;
    status: number;
  }
}

/**
 * 登录 - 对接FastAPI后端
 * 使用 baseRequestClient 绕过响应拦截器（FastAPI不返回code/data格式）
 */
export async function loginApi(data: AuthApi.LoginParams) {
  const { username, password } = data;
  const res = await baseRequestClient.post<any>(
    '/auth/login',
    { username, password },
  );
  const token = res?.access_token ?? res?.data?.access_token ?? res?.accessToken;
  return { accessToken: token };
}

/**
 * 刷新accessToken
 */
export async function refreshTokenApi() {
  const res = await baseRequestClient.post<any>('/auth/refresh');
  const token = res?.access_token ?? res?.data?.access_token ?? res?.accessToken;
  return { data: token, status: 200 } as AuthApi.RefreshTokenResult;
}

/**
 * 注册
 */
export async function registerApi(data: { username: string; email: string; password: string }) {
  return baseRequestClient.post<any>('/auth/register', data);
}

/**
 * 退出登录
 */
export async function logoutApi() {
  return Promise.resolve();
}

/**
 * 获取用户权限码 - 返回角色列表
 * 使用 baseRequestClient 绕过响应拦截器
 */
export async function getAccessCodesApi() {
  const res = await baseRequestClient.get<{
    id: string;
    username: string;
    roles: string[];
  }>('/auth/profile');
  return res.roles ?? [];
}
