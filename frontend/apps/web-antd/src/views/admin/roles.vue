<script setup lang="ts">
import { onMounted, ref } from 'vue';

import { Card as ACard, Table as ATable, Tag as ATag } from 'ant-design-vue';

import { getAdminRolesApi } from '#/api/admin';
import type { AdminRole } from '#/api/admin';

const roles = ref<AdminRole[]>([]);
const loading = ref(false);

const columns = [
  { title: '角色', key: 'name' },
  { title: '描述', dataIndex: 'description', key: 'description' },
];

const roleColorMap: Record<string, string> = {
  admin: 'red',
  user: 'blue',
};

const fetchRoles = async () => {
  loading.value = true;
  try {
    const res = await getAdminRolesApi();
    roles.value = res.roles;
  } finally {
    loading.value = false;
  }
};

onMounted(fetchRoles);
</script>

<template>
  <div class="p-4">
    <h2 class="mb-4 text-lg font-semibold">角色管理</h2>
    <ACard>
      <ATable :columns="columns" :data-source="roles" :loading="loading" row-key="id">
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'name'">
            <ATag :color="roleColorMap[record.name] || 'default'">
              {{ record.display_name }}
            </ATag>
          </template>
        </template>
      </ATable>
    </ACard>
  </div>
</template>
