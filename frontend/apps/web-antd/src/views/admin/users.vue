<script setup lang="ts">
import { onMounted, ref } from 'vue';

import { Button as AButton, Card as ACard, message, Modal as AModal, Select as ASelect, SelectOption as ASelectOption, Table as ATable, Tag as ATag } from 'ant-design-vue';

import { assignRoleApi, getAdminRolesApi, getAdminUsersApi } from '#/api/admin';
import type { AdminRole, AdminUser } from '#/api/admin';

const users = ref<AdminUser[]>([]);
const roles = ref<AdminRole[]>([]);
const loading = ref(false);
const modalVisible = ref(false);
const selectedUserId = ref('');
const selectedRoleId = ref('');

const columns = [
  { title: '用户名', dataIndex: 'username', key: 'username' },
  { title: '邮箱', dataIndex: 'email', key: 'email' },
  { title: '角色', key: 'roles' },
  { title: '操作', key: 'action' },
];

const roleColorMap: Record<string, string> = {
  admin: 'red',
  user: 'blue',
  guest: 'default',
};

const roleNameMap: Record<string, string> = {
  admin: '管理员',
  user: '普通用户',
  guest: '访客',
};

const fetchUsers = async () => {
  loading.value = true;
  try {
    const res = await getAdminUsersApi();
    users.value = res.users;
  } finally {
    loading.value = false;
  }
};

const fetchRoles = async () => {
  const res = await getAdminRolesApi();
  roles.value = res.roles;
};

const showRoleModal = (user: AdminUser) => {
  selectedUserId.value = user.id;
  selectedRoleId.value = '';
  modalVisible.value = true;
};

const handleAssignRole = async () => {
  if (!selectedRoleId.value) {
    message.warning('请选择角色');
    return;
  }
  try {
    await assignRoleApi(selectedUserId.value, selectedRoleId.value);
    message.success('角色分配成功');
    modalVisible.value = false;
    fetchUsers();
  } catch {
    message.error('分配失败');
  }
};

onMounted(() => {
  fetchUsers();
  fetchRoles();
});
</script>

<template>
  <div class="p-4">
    <h2 class="mb-4 text-lg font-semibold">用户管理</h2>
    <ACard>
      <ATable :columns="columns" :data-source="users" :loading="loading" row-key="id">
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'roles'">
            <ATag
              v-for="role in record.roles"
              :key="role"
              :color="roleColorMap[role] || 'default'"
            >
              {{ roleNameMap[role] || role }}
            </ATag>
          </template>
          <template v-else-if="column.key === 'action'">
            <AButton type="link" @click="showRoleModal(record)">分配角色</AButton>
          </template>
        </template>
      </ATable>
    </ACard>

    <AModal v-model:open="modalVisible" title="分配角色" @ok="handleAssignRole">
      <ASelect v-model:value="selectedRoleId" style="width: 100%" placeholder="请选择角色">
        <ASelectOption v-for="role in roles" :key="role.id" :value="role.id">
          {{ role.display_name }}
        </ASelectOption>
      </ASelect>
    </AModal>
  </div>
</template>
