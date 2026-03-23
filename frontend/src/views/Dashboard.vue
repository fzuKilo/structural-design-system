<template>
  <a-layout style="min-height: 100vh;">
    <a-layout-header style="background: #fff; padding: 0 16px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
      <h2 style="margin: 0; font-size: clamp(16px, 4vw, 20px);">OpenManus 结构设计系统</h2>
      <a-space :size="8">
        <span style="display: none; font-size: 14px;">{{ authStore.user?.username }}</span>
        <a-button size="small" @click="$router.push('/profile')">设置</a-button>
        <a-button size="small" @click="handleLogout">退出</a-button>
      </a-space>
    </a-layout-header>
    <a-layout-content style="padding: 16px;">
      <a-card title="我的设计任务">
        <template #extra>
          <a-button type="primary" size="small" @click="$router.push('/design/create')">新建设计</a-button>
        </template>
        <a-table
          :dataSource="tasks"
          :columns="columns"
          :loading="loading"
          rowKey="id"
          :scroll="{ x: 800 }"
          :pagination="{ pageSize: 10, showSizeChanger: false }"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'status'">
              <a-tag :color="getStatusColor(record.status)">{{ getStatusText(record.status) }}</a-tag>
            </template>
            <template v-if="column.key === 'action'">
              <a-button type="link" @click="$router.push(`/design/${record.id}`)">查看</a-button>
            </template>
          </template>
        </a-table>
      </a-card>
    </a-layout-content>
  </a-layout>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { designApi } from '@/api/design'

const router = useRouter()
const authStore = useAuthStore()
const tasks = ref([])
const loading = ref(false)

const columns = [
  { title: '任务ID', dataIndex: 'id', key: 'id', ellipsis: true },
  { title: '需求描述', dataIndex: 'request_text', key: 'request_text', ellipsis: true },
  { title: '状态', key: 'status' },
  { title: '创建时间', dataIndex: 'created_at', key: 'created_at' },
  { title: '操作', key: 'action' }
]

const getStatusColor = (status: string) => {
  const colors: any = { pending: 'blue', running: 'orange', success: 'green', failed: 'red' }
  return colors[status] || 'default'
}

const getStatusText = (status: string) => {
  const texts: any = { pending: '等待中', running: '运行中', success: '已完成', failed: '失败' }
  return texts[status] || status
}

const loadTasks = async () => {
  loading.value = true
  try {
    tasks.value = await designApi.list()
  } finally {
    loading.value = false
  }
}

const handleLogout = () => {
  authStore.logout()
  router.push('/login')
}

onMounted(() => {
  loadTasks()
})
</script>
