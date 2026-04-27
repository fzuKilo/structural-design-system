<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue';

import { Button as AButton, Card as ACard, Empty as AEmpty, Table as ATable, Tag as ATag, Tooltip as ATooltip } from 'ant-design-vue';
import { useRouter } from 'vue-router';

import { getDesignListApi } from '#/api/design';

const router = useRouter();
const tasks = ref([]);
const loading = ref(false);

const structureTypeMap: Record<string, { label: string; icon: string }> = {
  truss:         { label: '桁架',   icon: '🔩' },
  frame:         { label: '框架',   icon: '🏗️' },
  simply_supported_beam: { label: '简支梁', icon: '〰️' },
  cantilever_beam:       { label: '悬臂梁', icon: '📐' },
  continuous_beam:       { label: '连续梁', icon: '〰️' },
};

const getStructureLabel = (type: string) => {
  if (!type) return '无';
  const entry = structureTypeMap[type];
  return entry ? `${entry.icon} ${entry.label}` : type;
};

const formatTime = (iso: string) => {
  if (!iso) return '—';
  const d = new Date(iso);
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  const hh = String(d.getHours()).padStart(2, '0');
  const min = String(d.getMinutes()).padStart(2, '0');
  return `${mm}-${dd} ${hh}:${min}`;
};

const columns = [
  { title: '序号',     key: 'index',          width: 70,  align: 'center' },
  { title: '结构类型', key: 'structure_type',  width: 130 },
  { title: '状态',     key: 'status',          width: 90  },
  { title: '创建时间', key: 'created_at',      width: 120 },
  { title: '操作',     key: 'action',          width: 80,  align: 'center' },
];

const statusColorMap: Record<string, string> = {
  pending: 'orange', running: 'blue', success: 'green', completed: 'green', failed: 'red',
};
const statusTextMap: Record<string, string> = {
  pending: '等待中', running: '执行中', success: '已完成', completed: '已完成', failed: '失败',
};

const getStatusColor = (status: string) => statusColorMap[status] || 'default';
const getStatusText  = (status: string) => statusTextMap[status]  || status;
const getActionText  = (status: string) => status === 'running' || status === 'pending' ? '进入' : '查看';

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
          <AButton :loading="loading" @click="fetchTasks">刷新</AButton>
          <AButton type="primary" @click="router.push('/structural/create')">新建设计</AButton>
        </div>
      </template>
      <ATable :columns="columns" :data-source="tasks" :loading="loading" row-key="id">
        <template #emptyText>
          <AEmpty description="暂无设计任务">
            <AButton type="primary" @click="router.push('/structural/create')">创建第一个设计</AButton>
          </AEmpty>
        </template>
        <template #bodyCell="{ column, record, index }">
          <template v-if="column.key === 'index'">
            <span style="color:#999;">#{{ index + 1 }}</span>
          </template>
          <template v-else-if="column.key === 'structure_type'">
            {{ getStructureLabel(record.structure_type) }}
          </template>
          <template v-else-if="column.key === 'status'">
            <ATag :color="getStatusColor(record.status)">{{ getStatusText(record.status) }}</ATag>
          </template>
          <template v-else-if="column.key === 'created_at'">
            <ATooltip :title="record.created_at">
              {{ formatTime(record.created_at) }}
            </ATooltip>
          </template>
          <template v-else-if="column.key === 'action'">
            <AButton type="link" @click="router.push(`/structural/detail/${record.id}`)">
              {{ getActionText(record.status) }}
            </AButton>
          </template>
        </template>
      </ATable>
    </ACard>
  </div>
</template>
