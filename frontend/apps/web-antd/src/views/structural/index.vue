<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue';

import { Button as AButton, Card as ACard, Empty as AEmpty, Table as ATable, Tag as ATag } from 'ant-design-vue';
import { useRouter } from 'vue-router';

import { getDesignListApi } from '#/api/design';

const router = useRouter();
const tasks = ref([]);
const loading = ref(false);

const columns = [
  { title: '任务ID', dataIndex: 'id', key: 'id', ellipsis: true, width: 200 },
  { title: '结构类型', dataIndex: 'structure_type', key: 'structure_type' },
  { title: '状态', key: 'status' },
  { title: '创建时间', dataIndex: 'created_at', key: 'created_at' },
  { title: '操作', key: 'action' },
];

const statusColorMap: Record<string, string> = {
  pending: 'orange',
  running: 'blue',
  success: 'green',
  completed: 'green',
  failed: 'red',
};

const statusTextMap: Record<string, string> = {
  pending: '等待中',
  running: '执行中',
  success: '已完成',
  completed: '已完成',
  failed: '失败',
};

const getStatusColor = (status: string) => statusColorMap[status] || 'default';
const getStatusText = (status: string) => statusTextMap[status] || status;

const fetchTasks = async () => {
  loading.value = true;
  try {
    const res = await getDesignListApi();
    tasks.value = res as any;
  } finally {
    loading.value = false;
  }
};

const onStorageChange = (e: StorageEvent) => {
  if (e.key === 'task_list_refresh') fetchTasks();
};

onMounted(() => {
  fetchTasks();
  window.addEventListener('storage', onStorageChange);
});

onUnmounted(() => {
  window.removeEventListener('storage', onStorageChange);
});
</script>

<template>
  <div class="p-4">
    <ACard title="我的设计任务">
      <template #extra>
        <div class="flex gap-2">
          <AButton :loading="loading" @click="fetchTasks">
            刷新
          </AButton>
          <AButton type="primary" @click="router.push('/structural/create')">
            新建设计
          </AButton>
        </div>
      </template>
      <ATable :columns="columns" :data-source="tasks" :loading="loading" row-key="id">
        <template #emptyText>
          <AEmpty description="暂无设计任务">
            <AButton type="primary" @click="router.push('/structural/create')">
              创建第一个设计
            </AButton>
          </AEmpty>
        </template>
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'status'">
            <ATag :color="getStatusColor(record.status)">
              {{ getStatusText(record.status) }}
            </ATag>
          </template>
          <template v-else-if="column.key === 'action'">
            <AButton type="link" @click="router.push(`/structural/detail/${record.id}`)">
              查看
            </AButton>
          </template>
        </template>
      </ATable>
    </ACard>
  </div>
</template>
