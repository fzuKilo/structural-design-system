<script setup lang="ts">
import { onMounted, onUnmounted, nextTick, ref } from 'vue';

import { Button as AButton, Card as ACard, Descriptions as ADescriptions, DescriptionsItem as ADescriptionsItem, Popconfirm as APopconfirm, Tag as ATag, Badge as ABadge, Alert as AAlert, message } from 'ant-design-vue';
import { useRoute, useRouter } from 'vue-router';

import { useAccessStore } from '@vben/stores';

import { cancelDesignApi, getDesignDetailApi } from '#/api/design';
import AskHumanModal from '#/components/design/AskHumanModal.vue';
import ProgressTracker from '#/components/design/ProgressTracker.vue';
import ResultViewer from '#/components/design/ResultViewer.vue';
import { getStageMessage, getStatusColor } from '#/utils/i18n';
import { WebSocketManager } from '#/utils/websocket';

const route = useRoute();
const router = useRouter();
const accessStore = useAccessStore();
const task = ref<any>(null);
const loading = ref(false);
const cancelling = ref(false);
const wsConnected = ref(false);
const errorMessage = ref<string>('');
const logs = ref<{ time: string; message: string; color: string }[]>([]);
const logRef = ref<HTMLElement | null>(null);
const stages = ref<any[]>([]);
const askHumanRequest = ref<any>(null);
let wsManager: WebSocketManager | null = null;

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
  try {
    const res = await getDesignDetailApi(route.params.id as string);
    task.value = (res as any)?.data ?? res;
    if (task.value?.status === 'failed' && task.value?.error) {
      errorMessage.value = task.value.error;
    }
  } catch (error) {
    message.error('加载任务详情失败');
    errorMessage.value = '加载任务详情失败，请刷新页面重试';
  }
};

const connectWs = () => {
  const token = accessStore.accessToken;

  const handleWsMessage = (msg: any) => {
    if (msg.type === 'stage') {
      stages.value.push(msg);
      const color = getStatusColor(msg.status);
      const message = getStageMessage(msg.stage, msg.status);
      addLog(message, color);
      if (msg.status === 'completed' || msg.status === 'failed') loadTask();
    } else if (msg.type === 'ask_human') {
      askHumanRequest.value = msg;
      addLog(`等待用户输入: ${msg.question}`, '#fa8c16');
    } else if (msg.type === 'result') {
      addLog(msg.status === 'success' ? '设计完成！' : '设计失败', msg.status === 'success' ? '#52c41a' : '#f5222d');
      loadTask();
    }
  };

  const handleWsOpen = () => {
    wsConnected.value = true;
    addLog('已连接，等待任务更新...', '#1890ff');
  };

  const handleWsClose = () => {
    wsConnected.value = false;
    addLog('连接已断开', '#999');
  };

  wsManager = new WebSocketManager(handleWsMessage, handleWsOpen, handleWsClose);
  wsManager.connect(route.params.id as string, token);
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

const handleCancel = async () => {
  cancelling.value = true;
  try {
    await cancelDesignApi(route.params.id as string);
    addLog('任务已取消', '#f5222d');
    message.success('任务已成功取消');
    wsManager?.disconnect();
    wsManager = null;
    await loadTask();
  } catch (error) {
    message.error('取消任务失败');
    addLog('取消任务失败', '#f5222d');
  } finally {
    cancelling.value = false;
  }
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

onUnmounted(() => { wsManager?.disconnect(); });
</script>

<template>
  <div class="p-4">
    <div class="mb-4 flex flex-wrap items-center gap-2">
      <AButton @click="router.push('/structural')">← 返回列表</AButton>
      <ATag v-if="task" :color="statusColorMap[task.status]">
        {{ statusTextMap[task.status] || task.status }}
      </ATag>
      <ABadge v-if="task && (task.status === 'running' || task.status === 'pending')" :status="wsConnected ? 'processing' : 'default'" :text="wsConnected ? 'WebSocket已连接' : 'WebSocket未连接'" />
      <APopconfirm
        v-if="task && (task.status === 'running' || task.status === 'pending')"
        title="确认停止该任务吗？停止后无法恢复。"
        ok-text="停止"
        cancel-text="取消"
        ok-type="danger"
        @confirm="handleCancel"
      >
        <AButton size="small" danger :loading="cancelling">停止任务</AButton>
      </APopconfirm>
    </div>

    <AAlert v-if="errorMessage" type="error" :message="errorMessage" closable class="mb-3" @close="errorMessage = ''" />

    <template v-if="task">
      <ACard size="small" class="mb-3">
        <template #title>设计需求</template>
        <p style="margin: 0; color: #666;">{{ task.request_text }}</p>
      </ACard>

      <ProgressTracker :stages="stages" class="mb-3" />

      <ACard title="实时日志" size="small" class="mb-3">
        <div ref="logRef" style="height: 240px; overflow-y: auto; font-family: monospace; font-size: 13px; line-height: 1.6;">
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
