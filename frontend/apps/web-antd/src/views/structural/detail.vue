<script setup lang="ts">
import { onMounted, onUnmounted, nextTick, ref } from 'vue';

import { Button as AButton, Card as ACard, Descriptions as ADescriptions, DescriptionsItem as ADescriptionsItem, Tag as ATag } from 'ant-design-vue';
import { useRoute, useRouter } from 'vue-router';

import { useAccessStore } from '@vben/stores';

import { getDesignDetailApi } from '#/api/design';
import AskHumanModal from '#/components/design/AskHumanModal.vue';
import ProgressTracker from '#/components/design/ProgressTracker.vue';
import ResultViewer from '#/components/design/ResultViewer.vue';

const route = useRoute();
const router = useRouter();
const accessStore = useAccessStore();
const task = ref<any>(null);
const loading = ref(false);
const logs = ref<{ time: string; message: string; color: string }[]>([]);
const logRef = ref<HTMLElement | null>(null);
const stages = ref<any[]>([]);
const askHumanRequest = ref<any>(null);
let ws: WebSocket | null = null;

const statusColorMap: Record<string, string> = {
  pending: 'blue', running: 'orange', success: 'green', failed: 'red',
};
const statusTextMap: Record<string, string> = {
  pending: '等待中', running: '运行中', success: '已完成', failed: '失败',
};

const addLog = (message: string, color = '#333') => {
  const time = new Date().toLocaleTimeString();
  logs.value.push({ time, message, color });
  nextTick(() => { if (logRef.value) logRef.value.scrollTop = logRef.value.scrollHeight; });
};

const loadTask = async () => {
  const res = await getDesignDetailApi(route.params.id as string);
  task.value = (res as any)?.data ?? res;
};

const connectWs = () => {
  const token = accessStore.accessToken;
  const wsUrl = `ws://localhost:8000/ws/design/${route.params.id}?token=${token}`;
  ws = new WebSocket(wsUrl);
  ws.onopen = () => addLog('已连接，等待任务更新...', '#1890ff');
  ws.onmessage = (e) => {
    const msg = JSON.parse(e.data);
    if (msg.type === 'stage') {
      stages.value.push(msg);
      const color = msg.status === 'failed' ? '#f5222d' : msg.status === 'completed' ? '#52c41a' : '#1890ff';
      addLog(`[${msg.stage}] ${msg.status}`, color);
      if (msg.status === 'completed' || msg.status === 'failed') loadTask();
    } else if (msg.type === 'ask_human') {
      askHumanRequest.value = msg;
      addLog(`等待用户输入: ${msg.question}`, '#fa8c16');
    } else if (msg.type === 'result') {
      addLog(msg.status === 'success' ? '设计完成！' : '设计失败', msg.status === 'success' ? '#52c41a' : '#f5222d');
      loadTask();
    }
  };
  ws.onclose = () => addLog('连接已断开', '#999');
};

const handleAskHumanSubmit = async (answer: string) => {
  askHumanRequest.value = null;
  addLog(`已提交回答: ${answer}`, '#722ed1');
  const token = accessStore.accessToken;
  await fetch(`/api/design/${route.params.id}/respond`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify({ answer }),
  });
};

onMounted(async () => {
  loading.value = true;
  try {
    await loadTask();
    if (task.value?.status === 'running' || task.value?.status === 'pending') {
      connectWs();
    }
  } finally {
    loading.value = false;
  }
});

onUnmounted(() => { ws?.close(); });
</script>

<template>
  <div class="p-4">
    <div class="mb-4 flex items-center gap-2">
      <AButton @click="router.push('/structural')">← 返回列表</AButton>
      <ATag v-if="task" :color="statusColorMap[task.status]">
        {{ statusTextMap[task.status] || task.status }}
      </ATag>
    </div>

    <template v-if="task">
      <ACard size="small" class="mb-3">
        <template #title>设计需求</template>
        <p style="margin: 0; color: #666;">{{ task.request_text }}</p>
      </ACard>

      <ProgressTracker :stages="stages" class="mb-3" />

      <ACard title="实时日志" size="small" class="mb-3">
        <div ref="logRef" style="height: 180px; overflow-y: auto; font-family: monospace; font-size: 13px;">
          <div v-for="(log, i) in logs" :key="i" :style="{ color: log.color }">
            [{{ log.time }}] {{ log.message }}
          </div>
          <div v-if="!logs.length" style="color: #999;">等待任务开始...</div>
        </div>
      </ACard>

      <ResultViewer v-if="task.status === 'success'" :result="task.result_json" :task-id="(route.params.id as string)" />
    </template>

    <AskHumanModal :request="askHumanRequest" @submit="handleAskHumanSubmit" />
  </div>
</template>
