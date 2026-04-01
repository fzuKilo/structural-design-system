import type { RouteRecordRaw } from 'vue-router';

import { BasicLayout } from '@vben/layouts';

const routes: RouteRecordRaw[] = [
  {
    component: BasicLayout,
    meta: {
      icon: 'lucide:pencil-ruler',
      order: 1,
      title: '结构设计',
    },
    name: 'Structural',
    path: '/structural',
    children: [
      {
        name: 'StructuralList',
        path: '/structural',
        component: () => import('#/views/structural/index.vue'),
        meta: {
          icon: 'lucide:list',
          title: '我的设计',
        },
      },
      {
        name: 'StructuralCreate',
        path: '/structural/create',
        component: () => import('#/views/structural/create.vue'),
        meta: {
          icon: 'lucide:plus-circle',
          title: '新建设计',
        },
      },
      {
        name: 'StructuralDetail',
        path: '/structural/detail/:id',
        component: () => import('#/views/structural/detail.vue'),
        meta: {
          hideInMenu: true,
          title: '设计详情',
        },
      },
    ],
  },
  {
    component: BasicLayout,
    meta: {
      authority: ['admin'],
      icon: 'lucide:shield',
      order: 2,
      title: '系统管理',
    },
    name: 'Admin',
    path: '/admin',
    children: [
      {
        name: 'AdminUsers',
        path: '/admin/users',
        component: () => import('#/views/admin/users.vue'),
        meta: {
          authority: ['admin'],
          icon: 'lucide:users',
          title: '用户管理',
        },
      },
      {
        name: 'AdminRoles',
        path: '/admin/roles',
        component: () => import('#/views/admin/roles.vue'),
        meta: {
          authority: ['admin'],
          icon: 'lucide:key',
          title: '角色管理',
        },
      },
    ],
  },
];

export default routes;
