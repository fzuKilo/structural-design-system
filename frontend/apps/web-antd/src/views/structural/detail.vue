<script setup lang="ts">
import { onMounted, onUnmounted, ref, computed } from 'vue';

import { Button as AButton, Card as ACard, Descriptions as ADescriptions, DescriptionsItem as ADescriptionsItem, Popconfirm as APopconfirm, Tag as ATag, Badge as ABadge, Alert as AAlert, message } from 'ant-design-vue';
import { useRoute, useRouter } from 'vue-router';

import { useAccessStore } from '@vben/stores';

import { cancelDesignApi, getDesignDetailApi } from '#/api/design';
import ProgressBar from '#/components/design/ProgressBar.vue';
import ResultViewer from '#/components/design/ResultViewer.vue';
import { WebSocketManager } from '#/utils/websocket';

const route = useRoute();
const router = useRouter();
const accessStore = useAccessStore();
const task = ref<any>(null);
const loading = ref(false);
const cancelling = ref(false);
const wsConnected = ref(false);
const errorMessage = ref<string>('');
const stages = ref<any[]>([]);
const progressData = ref<any>(null);
const askHumanRequest = ref<any>(null);
const schemeUpdates = ref<any[]>([]);  // 实时方案数据
let wsManager: WebSocketManager | null = null;

const taskParams = computed(() => {
  if (!task.value) return null;
  const r = task.value.result_json || {};
  return {
    designDescription: task.value.request_text,
    maxStress: r.analysis_results?.results?.max_stress_MPa ?? null,
    maxDeflection: r.analysis_results?.results?.max_displacement_mm ?? null,
    safetyFactor: r.analysis_results?.results?.safety_factor ?? null,
    complianceStatus: r.analysis_results?.code_check?.compliant ? 'compliant' : 'non_compliant',
    violations: r.analysis_results?.code_check?.violations || [],
    safetyScore: r.evaluation_report?.dimensions?.safety?.score ?? null,
    economyScore: r.evaluation_report?.dimensions?.economy?.score ?? null,
    overallScore: r.evaluation_report?.comprehensive_score ?? null,
    warnings: r.evaluation_report?.warnings || [],
    drawingStatus: r.drawing_results?.status || 'pending',
    speckleExported: r.bim_results?.status === 'success',
    ifcExported: r.ifc_results?.status === 'success',
    reportStatus: r.report_results?.status || 'pending',
  };
});

const statusColorMap: Record<string, string> = {
  pending: 'blue', running: 'orange', success: 'green', failed: 'red',
};
const statusTextMap: Record<string, string> = {
  pending: '等待中', running: '运行中', success: '已完成', failed: '失败',
};

const loadTask = async () => {
  try {
    const res = await getDesignDetailApi(route.params.id as string);
    task.value = (res as any)?.data ?? res;
    if (task.value?.status === 'failed') {
      const errorMsg = task.value.error || '';
      const isCancelled = errorMsg.includes('用户停止') || errorMsg.includes('已取消');
      const isLikelyCancelled = !errorMsg && !task.value.result_json;
      if (!isCancelled && !isLikelyCancelled && errorMsg) {
        errorMessage.value = task.value.error;
      }
    }
    // 任务完成后从 result_json 重建 stages，保留所有阶段数据
    if ((task.value?.status === 'success' || task.value?.status === 'failed') && stages.value.length === 0) {
      rebuildStagesFromResult(task.value);
    }
  } catch (error) {
    message.error('加载任务详情失败');
    errorMessage.value = '加载任务详情失败，请刷新页面重试';
  }
};

// 从 result_json.raw 重建 stages，让 ProgressBar 的 snapshot 机制正常工作
const rebuildStagesFromResult = (t: any) => {
  const raw = t?.result_json?.raw || {};
  const stageMap: Record<string, any> = {
    design_proposal: raw.design_proposal,
    fe_analysis: raw.analysis_results,
    evaluation: raw.evaluation_report,
    cad_drawing: raw.drawing_results,
    report_generation: raw.report_results,
  };
  const rebuilt: any[] = [];
  for (const [stageName, data] of Object.entries(stageMap)) {
    if (!data) continue;
    // 将 raw 数据映射为 ProgressBar snapshot 期望的字段格式
    const mappedData = mapRawToSnapshotData(stageName, data);
    rebuilt.push({ type: 'stage', stage: stageName, status: 'completed', data: mappedData });
  }
  if (rebuilt.length > 0) stages.value = rebuilt;
};

// 将 result_json.raw 各阶段数据映射为 snapshot 期望的字段
const mapRawToSnapshotData = (stage: string, raw: any): any => {
  if (stage === 'design_proposal') {
    return {
      type: raw.type,
      description: raw.description || '',
      geometry: raw.geometry || {},
      material: raw.material || {},
      standards: raw.standards || [],
    };
  }
  if (stage === 'fe_analysis') {
    const results = raw.results || {};
    const check = raw.code_check || {};
    return {
      max_stress_MPa: results.max_stress_MPa,
      max_displacement_mm: results.max_displacement_mm,
      safety_factor: check.safety_factors?.stress,
      compliant: check.compliant,
      violations: check.violations || [],
    };
  }
  if (stage === 'evaluation') {
    const dims = raw.dimensions || {};
    return {
      comprehensive_score: raw.comprehensive_score,
      safety_score: dims.safety?.score,
      economy_score: dims.economy?.score,
      efficiency_score: dims.structural_efficiency?.score,
      sustainability_score: dims.sustainability?.score,
      grade: raw.grade,
      warnings: raw.warnings || [],
    };
  }
  if (stage === 'cad_drawing') {
    return {
      status: raw.status,
      files: raw.files ? Object.values(raw.files) : [],
    };
  }
  if (stage === 'report_generation') {
    return {
      report_status: raw.status || 'completed',
    };
  }
  return raw;
};

const wsReconnectInfo = ref<{ attempt: number; delay: number } | null>(null);
const wsMaxRetriesReached = ref(false);

const connectWs = () => {
  const token = accessStore.accessToken;

  const handleWsMessage = (msg: any) => {
    if (msg.type === 'stage') {
      stages.value.push(msg);
      if (msg.status === 'completed' || msg.status === 'failed' || msg.status === 'skipped') loadTask();
    } else if (msg.type === 'progress') {
      progressData.value = msg;
    } else if (msg.type === 'ask_human') {
      askHumanRequest.value = msg;
    } else if (msg.type === 'scheme_ready') {
      // 实时方案数据推送
      schemeUpdates.value.push(msg);
    } else if (msg.type === 'result' || msg.type === 'cancelled' || msg.type === 'error') {
      loadTask();
    }
  };

  const handleWsOpen = () => {
    wsConnected.value = true;
    wsReconnectInfo.value = null;
    wsMaxRetriesReached.value = false;
  };

  const handleWsClose = () => { wsConnected.value = false; };

  const handleWsReconnecting = (attempt: number, delay: number) => {
    wsReconnectInfo.value = { attempt, delay };
  };

  const handleWsMaxRetries = () => { wsMaxRetriesReached.value = true; };

  wsManager = new WebSocketManager(handleWsMessage, handleWsOpen, handleWsClose, handleWsReconnecting, handleWsMaxRetries);
  // 重置实时状态，防止上次数据残留
  stages.value = [];
  schemeUpdates.value = [];
  askHumanRequest.value = null;
  wsManager.connect(route.params.id as string, token);
};

const handleAskHumanSubmit = async (answer: string) => {
  askHumanRequest.value = null;
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
      <span v-if="wsReconnectInfo" style="color: #fa8c16; font-size: 12px;">
        重连中 {{ wsReconnectInfo.attempt }}/10（{{ wsReconnectInfo.delay / 1000 }}s 后）
      </span>
      <span v-if="wsMaxRetriesReached" style="color: #f5222d; font-size: 12px;">
        连接失败，请检查网络
      </span>
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

      <ProgressBar
        :stages="stages"
        :progress-data="progressData"
        :task-params="taskParams"
        :ask-human-request="askHumanRequest"
        :scheme-updates="schemeUpdates"
        class="mb-3"
        @submit="handleAskHumanSubmit"
      />

      <ResultViewer v-if="task.status === 'success'" :result="task.result_json" :task-id="(route.params.id as string)" />

      <!-- CAD 预览图 -->
      <ACard v-if="task.status === 'success' && task.result_json?.preview_image" title="模型预览" size="small" class="mb-3">
        <img
          :src="`/api/design/${route.params.id}/preview`"
          alt="模型预览图"
          style="max-width: 100%; cursor: zoom-in;"
          @click="previewVisible = true"
        />
      </ACard>
    </template>
  </div>
</template>
