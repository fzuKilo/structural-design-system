<template>
  <a-layout style="min-height: 100vh;">
    <a-layout-header style="background: #fff; padding: 0 24px; display: flex; align-items: center; gap: 16px;">
      <a-button @click="$router.push('/')">← 返回</a-button>
      <h2 style="margin: 0;">设计任务详情</h2>
      <a-tag :color="getStatusColor(task?.status)">{{ getStatusText(task?.status) }}</a-tag>
    </a-layout-header>

    <a-layout-content style="padding: 24px;">
      <a-row :gutter="[16, 16]">
        <!-- Request text -->
        <a-col :span="24">
          <a-card size="small">
            <template #title>设计需求</template>
            <p style="margin: 0; color: #666;">{{ task?.request_text }}</p>
          </a-card>
        </a-col>

        <!-- Progress tracker -->
        <a-col :span="24">
          <ProgressTracker :stages="taskStore.stages" />
        </a-col>

        <!-- Log area -->
        <a-col :span="24">
          <a-card title="实时日志" size="small">
            <div ref="logRef" style="height: 200px; overflow-y: auto; font-family: monospace; font-size: 13px;">
              <div v-for="(log, i) in logs" :key="i" :style="{ color: log.color }">
                [{{ log.time }}] {{ log.message }}
              </div>
              <div v-if="!logs.length" style="color: #999;">等待任务开始...</div>
            </div>
          </a-card>
        </a-col>

        <!-- Results (shown when completed) -->
        <a-col v-if="task?.status === 'success'" :span="24">
          <ResultViewer :result="task.result_json" :task-id="route.params.id as string" />
        </a-col>
      </a-row>
    </a-layout-content>

    <!-- AskHuman Modal -->
    <AskHumanModal :request="taskStore.askHumanRequest" @submit="handleAskHumanSubmit" />
  </a-layout>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { useTaskStore } from '@/stores/task'
import { useAuthStore } from '@/stores/auth'
import { designApi } from '@/api/design'
import { WebSocketManager } from '@/utils/websocket'
import { getStageMessage } from '@/utils/i18n'
import ProgressTracker from '@/components/design/ProgressTracker.vue'
import AskHumanModal from '@/components/design/AskHumanModal.vue'
import ResultViewer from '@/components/design/ResultViewer.vue'
import type { WebSocketMessage } from '@/types/task'
import axios from 'axios'

const route = useRoute()
const taskStore = useTaskStore()
const authStore = useAuthStore()
const task = ref<any>(null)
const logs = ref<{ time: string; message: string; color: string }[]>([])
const logRef = ref<HTMLElement | null>(null)
let wsManager: WebSocketManager | null = null

const getStatusColor = (status?: string) => {
  const m: any = { pending: 'blue', running: 'orange', success: 'green', failed: 'red' }
  return m[status || ''] || 'default'
}

const getStatusText = (status?: string) => {
  const m: any = { pending: '等待中', running: '运行中', success: '已完成', failed: '失败' }
  return m[status || ''] || status
}

const addLog = (message: string, color = '#333') => {
  const time = new Date().toLocaleTimeString()
  logs.value.push({ time, message, color })
  nextTick(() => {
    if (logRef.value) logRef.value.scrollTop = logRef.value.scrollHeight
  })
}

const handleWsMessage = (msg: WebSocketMessage) => {
  if (msg.type === 'stage') {
    taskStore.addStage(msg)
    const color = msg.status === 'failed' ? '#f5222d' : msg.status === 'completed' ? '#52c41a' : '#1890ff'
    addLog(getStageMessage(msg.stage, msg.status), color)
    if (msg.status === 'completed' || msg.status === 'failed') {
      loadTask()
    }
  } else if (msg.type === 'ask_human') {
    taskStore.setAskHuman(msg)
    addLog(`等待用户输入: ${msg.question}`, '#fa8c16')
  } else if (msg.type === 'result') {
    addLog(msg.status === 'success' ? '设计完成！' : '设计失败', msg.status === 'success' ? '#52c41a' : '#f5222d')
    loadTask()
  } else if (msg.type === 'error') {
    addLog(`错误: ${msg.message}`, '#f5222d')
    loadTask()
  }
}

const handleAskHumanSubmit = async (answer: string) => {
  taskStore.clearAskHuman()
  addLog(`已提交回答: ${answer}`, '#722ed1')
  try {
    await axios.post(`/api/design/${route.params.id}/respond`, { answer }, {
      headers: { Authorization: `Bearer ${authStore.token}` }
    })
  } catch {}
}

const loadTask = async () => {
  task.value = await designApi.getStatus(route.params.id as string)
}

onMounted(async () => {
  taskStore.reset()
  await loadTask()

  if (task.value?.status === 'running' || task.value?.status === 'pending') {
    wsManager = new WebSocketManager(handleWsMessage)
    wsManager.connect(route.params.id as string, authStore.token)
    addLog('已连接到任务，等待更新...', '#1890ff')
  }
})

onUnmounted(() => {
  wsManager?.disconnect()
})
</script>
