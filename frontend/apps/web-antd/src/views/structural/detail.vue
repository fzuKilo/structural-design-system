<script setup lang="ts">
import { onMounted, onUnmounted, ref, computed } from 'vue';

import { Button as AButton, Card as ACard, Descriptions as ADescriptions, DescriptionsItem as ADescriptionsItem, Popconfirm as APopconfirm, Tag as ATag, Badge as ABadge, Alert as AAlert, message } from 'ant-design-vue';
import { useRoute, useRouter } from 'vue-router';

import { useAccessStore } from '@vben/stores';

import { cancelDesignApi, getDesignDetailApi, getPendingAskApi } from '#/api/design';
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
const schemeTotalHint = ref<number>(0); // scheme_start 提前告知的总数
const savedHistory = ref<any[]>([]);   // 持久化交互历史
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
    drawingStatus: (r.files && Object.keys(r.files).length > 0) ? 'success' : (r.raw?.drawing_results?.status || 'pending'),
    speckleExported: !!(r.bim_url),
    ifcExported: !!(r.ifc_path),
    reportStatus: r.report_file ? 'success' : (r.raw?.report_results?.status || 'pending'),
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
    }  } catch (error) {
    message.error('加载任务详情失败');
    errorMessage.value = '加载任务详情失败，请刷新页面重试';
  }
};

// 从 result_json 重建 stages，让 ProgressBar 的 snapshot 机制正常工作
const rebuildStagesFromResult = (t: any) => {
  const rj = t?.result_json || {};
  const raw = rj.raw || {};

  // For running tasks: use stages_snapshot (persisted incrementally during execution)
  // For completed tasks: use raw (full result written at the end)
  const snapshot = rj.stages_snapshot || {};
  const useSnapshot = Object.keys(snapshot).length > 0;

  // 从 interaction_history 提取各阶段最后一次交互时间
  const history: any[] = rj.interaction_history || raw.interaction_history || [];
  const stageTimeMap: Record<string, string> = {};
  for (const item of history) {
    if (item.stage && item.time) stageTimeMap[item.stage] = item.time;
  }
  // drawing_results 有 metadata.generated_at，提取时间部分
  const drawingTime = raw.drawing_results?.metadata?.generated_at
    ? new Date(raw.drawing_results.metadata.generated_at).toLocaleTimeString()
    : stageTimeMap['cad_drawing'];
  // report_results 没有时间，用 completed_at 或 interaction_history 里 report_generation 的时间
  const reportTime = stageTimeMap['report_generation']
    || (t.completed_at ? new Date(t.completed_at).toLocaleTimeString() : undefined);
  const evalData = useSnapshot ? snapshot['evaluation'] : (rj.evaluation || raw.evaluation_report);
  const feData = useSnapshot ? snapshot['fe_analysis'] : raw.analysis_results;
  const dpData = useSnapshot ? snapshot['design_proposal'] : raw.design_proposal;
  const cadData = useSnapshot ? snapshot['cad_drawing'] : (raw.drawing_results || (rj.files ? { status: 'completed', files: rj.files } : null));
  const reportData = useSnapshot ? snapshot['report_generation'] : (raw.report_results || (rj.report_file ? { status: 'completed' } : null));

  // 各阶段时间映射（用于 snapshot timestamp）
  const stageTimestamps: Record<string, string | undefined> = {
    design_proposal: stageTimeMap['design_proposal'],
    fe_analysis: stageTimeMap['fe_analysis'],
    evaluation: stageTimeMap['evaluation'],
    cad_drawing: drawingTime,
    report_generation: reportTime,
  };

  const stageMap: Record<string, any> = {
    design_proposal: dpData,
    fe_analysis: feData,
    evaluation: evalData,
    cad_drawing: cadData,
    report_generation: reportData,
  };

  const rebuilt: any[] = [];
  for (const [stageName, data] of Object.entries(stageMap)) {
    if (!data) continue;
    // stages_snapshot data is already in snapshot format; raw data needs mapping
    const mappedData = useSnapshot ? data : mapRawToSnapshotData(stageName, data);
    rebuilt.push({ type: 'stage', stage: stageName, status: 'completed', data: mappedData, timestamp: stageTimestamps[stageName] });
  }
  if (rebuilt.length > 0) stages.value = rebuilt;
  // 恢复交互历史
  const interactionHistory = rj.interaction_history;
  if (interactionHistory?.length) savedHistory.value = interactionHistory;
};

// 将 result_json.raw 各阶段数据映射为 snapshot 期望的字段
const mapRawToSnapshotData = (stage: string, raw: any): any => {
  if (stage === 'design_proposal') {
    return {
      type: raw.type,
      description: raw.description || '',
      geometry: raw.geometry || {},
      material: raw.material || {},
      loads: raw.loads || {},
      constraints: raw.constraints || {},
      standards: raw.standards || [],
    };
  }
  if (stage === 'fe_analysis') {
    // result_json.raw.analysis_results 结构：{ results: { max_stress_MPa, ... }, code_check: { ... } }
    // stage broadcast 结构：直接扁平字段
    const results = raw.results || {};
    const check = raw.code_check || {};
    return {
      max_stress_MPa: results.max_stress_MPa ?? raw.max_stress_MPa,
      max_displacement_mm: results.max_displacement_mm ?? raw.max_displacement_mm,
      safety_factor: check.safety_factors?.stress ?? raw.safety_factor,
      compliant: check.compliant ?? raw.compliant,
      violations: check.violations ?? raw.violations ?? [],
    };
  }
  if (stage === 'evaluation') {
    const dims = raw.dimensions || {};
    return {
      // 兼容嵌套结构（result_json）和扁平结构（stage broadcast）
      comprehensive_score: raw.comprehensive_score ?? raw.overall_score,
      safety_score: dims.safety?.score ?? raw.safety_score,
      economy_score: dims.economy?.score ?? raw.economy_score,
      efficiency_score: dims.structural_efficiency?.score ?? raw.efficiency_score,
      sustainability_score: dims.sustainability?.score ?? raw.sustainability_score,
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
    const rj = task.value?.result_json || {};
    return {
      report_status: raw.status || 'completed',
      speckle_exported: !!(rj.bim_url),
      ifc_exported: !!(rj.ifc_path),
    };
  }
  return raw;
};

const wsReconnectInfo = ref<{ attempt: number; delay: number } | null>(null);
const wsMaxRetriesReached = ref(false);

const connectWs = () => {
  const token = accessStore.accessToken;

  const handleWsMessage = (msg: any) => {
    console.log('[WebSocket] Received message:', msg.type, msg);
    if (msg.type === 'stage') {
      stages.value.push(msg);
      if (msg.status === 'completed' || msg.status === 'failed' || msg.status === 'skipped') loadTask();
    } else if (msg.type === 'progress') {
      progressData.value = msg;
    } else if (msg.type === 'ask_human') {
      askHumanRequest.value = msg;
      // evaluation 阶段之后的交互不需要显示方案卡片，清空实时方案数据
      if (msg.stage && msg.stage !== 'evaluation') {
        schemeUpdates.value = [];
        schemeTotalHint.value = 0;
      }
      // 同步后端携带的历史记录到 savedHistory（用于 ProgressBar 恢复）
      if (msg.interaction_history?.length) {
        savedHistory.value = msg.interaction_history;
      }
    } else if (msg.type === 'interaction_history') {
        savedHistory.value = msg.interaction_history;
    } else if (msg.type === 'scheme_start') {
      schemeTotalHint.value = msg.total;
    } else if (msg.type === 'scheme_ready') {
      // 实时方案数据推送
      schemeUpdates.value.push(msg);
    } else if (msg.type === 'result' || msg.type === 'cancelled' || msg.type === 'error') {
      loadTask();
      localStorage.setItem('task_list_refresh', Date.now().toString());
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
  // 只在没有已有数据时才重置状态（避免重新进入页面时清空已积累的阶段数据）
  if (stages.value.length === 0) {
    schemeUpdates.value = [];
    schemeTotalHint.value = 0;
    askHumanRequest.value = null;
  }
  wsManager.connect(route.params.id as string, token);
};

const restorePendingAsk = async () => {
  try {
    const data = await getPendingAskApi(route.params.id as string);
    console.log('[restorePendingAsk] response:', data);
    if (data?.pending && data?.ask_human) {
      const msg = data.ask_human;
      askHumanRequest.value = msg;
      if (msg.stage && msg.stage !== 'evaluation') {
        schemeUpdates.value = [];
        schemeTotalHint.value = 0;
      }
      console.log('[restorePendingAsk] restored askHumanRequest:', msg);
    } else {
      console.log('[restorePendingAsk] no pending ask found');
    }
  } catch (e) {
    console.error('[restorePendingAsk] error:', e);
  }
};

const handleAskHumanSubmit = async (answer: string) => {
  // 先清空 askHumanRequest，确保 ProgressBar 立即切换出 ask_human 分支（避免图片残留）
  const prevRequest = askHumanRequest.value;
  askHumanRequest.value = null;
  // 立即在本地追加这次问答记录，不等后端下一条消息
  if (prevRequest) {
    savedHistory.value = [
      ...savedHistory.value,
      {
        stage: prevRequest.stage,
        question: prevRequest.question,
        answer,
        time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
        options: prevRequest.options || [],
        context: prevRequest.context || null,
      },
    ];
  }
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
      // 先从 interaction_history 恢复已完成的阶段，再连 WS
      if (stages.value.length === 0) {
        rebuildStagesFromResult(task.value);
      }
      // 主动查询挂起的 ask_human，不完全依赖 WS 重连恢复
      await restorePendingAsk();
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
        :scheme-total-hint="schemeTotalHint"
        :saved-interaction-history="savedHistory"
        class="mb-3"
        @submit="handleAskHumanSubmit"
      />

      <ResultViewer v-if="task.status === 'success'" :result="task.result_json" :task-id="(route.params.id as string)" />

    </template>
  </div>
</template>
