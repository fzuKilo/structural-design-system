<template>
  <ACard size="small" class="progress-panel">
    <!-- 顶部步骤导航 -->
    <div class="steps-nav">
      <div
        v-for="(step, i) in steps"
        :key="step.key"
        class="step-item"
        :class="getStepClass(step.key)"
        @click="onStepClick(step.key)"
      >
        <div class="step-icon">
          <span v-if="getStageStatus(step.key) === 'completed'">✅</span>
          <span v-else-if="getStageStatus(step.key) === 'failed'">❌</span>
          <span v-else-if="getStageStatus(step.key) === 'skipped'">⏭</span>
          <span v-else>{{ step.icon }}</span>
        </div>
        <div class="step-title">{{ step.label }}</div>
        <div class="step-status">{{ getStepStatusText(step.key) }}</div>
        <div v-if="i < steps.length - 1" class="step-connector" />
      </div>
    </div>

    <!-- 主体两栏 -->
    <div class="main-body">
      <!-- 左侧：交互面板 -->
      <div class="left-panel">
        <!-- 查看历史阶段时：显示该阶段的交互记录 -->
        <template v-if="viewingStage">
          <div class="history-stage-header">
            📜 {{ getStageLabel(viewingStage) }} — 历史记录
            <span class="snapshot-time" style="margin-left:8px;">{{ snapshots[viewingStage]?.timestamp }}</span>
          </div>
          <div v-if="interactionHistoryByStage[viewingStage]?.length" class="interaction-history">
            <div v-for="(item, i) in interactionHistoryByStage[viewingStage]" :key="i" class="history-item">
              <div class="history-q">🔔 {{ item.question }}</div>
              <div class="history-a">✅ 您的回答：{{ item.answer }} <span class="history-time">{{ item.time }}</span></div>
            </div>
          </div>
          <div v-else style="color:#999; padding:16px 0; font-size:13px;">该阶段无交互记录（自动完成）</div>
          <div class="back-btn-wrap" style="margin-top:12px;">
            <AButton size="small" @click="viewingStage = null">← 返回当前进度</AButton>
          </div>
        </template>

        <!-- 当前进度：有 ask_human 时显示交互 UI -->
        <template v-else-if="askHumanRequest">
          <div class="ask-human-banner">🔔 需要您的确认，请查看并回复</div>
          <!-- 图片预览（可视化确认） -->
          <div v-if="askHumanRequest.image_path" class="preview-box">
            <img
              :src="`/api/file/view?path=${encodeURIComponent(askHumanRequest.image_path)}`"
              style="max-width:100%; max-height:300px; border-radius:8px; border:1px solid #d9d9d9;"
              alt="模型预览图"
            />
          </div>

          <!-- warnings 列表 -->
          <div v-if="askHumanRequest.context?.warnings?.length" class="warnings-list">
            <div v-for="(w, i) in askHumanRequest.context.warnings" :key="i" class="violation-item">
              ⚠️ {{ w }}
            </div>
          </div>

          <!-- 评估得分 -->
          <div v-if="askHumanRequest.context?.score !== undefined" class="score-summary">
            <span>综合得分：<strong style="font-size:20px;color:#1890ff;">{{ askHumanRequest.context.score }}</strong></span>
            <ATag :color="getGradeColor(askHumanRequest.context.grade)" style="margin-left:12px;">{{ askHumanRequest.context.grade }}</ATag>
          </div>

          <!-- 多方案卡片（实时显示） -->
          <div v-if="realTimeSchemes.length > 0 || askHumanRequest?.context?.proposals?.length" style="margin-bottom:16px;">
            <h3 style="font-size:14px;font-weight:600;margin-bottom:12px;">🔄 多方案优化</h3>
            <div class="schemes-container">
              <!-- 显示实时方案数据 -->
              <div
                v-for="scheme in realTimeSchemes"
                :key="scheme.index"
                class="scheme-card completed"
                :class="{ selected: selectedSchemeIdx === scheme.index - 1 }"
              >
                <div class="scheme-header-card">
                  <span class="scheme-name">{{ scheme.name }}</span>
                  <span>✅</span>
                </div>
                <div class="scheme-body">
                  <div v-for="(val, key) in scheme.metrics" :key="key" class="scheme-metric">
                    <div class="scheme-metric-label">{{ metricLabels[key] || key }}</div>
                    <div class="scheme-metric-value">{{ val }}</div>
                  </div>
                  <div class="scheme-metric">
                    <button class="select-btn" :disabled="selectedSchemeIdx === scheme.index - 1" @click="selectedSchemeIdx = scheme.index - 1">
                      {{ selectedSchemeIdx === scheme.index - 1 ? '✓已选' : '选择' }}
                    </button>
                  </div>
                </div>
              </div>

              <!-- 如果 ask_human 已到达但实时方案还没全部完成，显示等待中的方案 -->
              <div
                v-for="i in Math.max(0, (askHumanRequest?.context?.proposals?.length || 0) - realTimeSchemes.length)"
                :key="'pending-' + i"
                class="scheme-card"
              >
                <div class="scheme-header-card">
                  <span class="scheme-name">方案 {{ realTimeSchemes.length + i }}</span>
                  <span>⏳</span>
                </div>
                <div style="text-align:center;padding:16px;color:#999;">
                  <div class="spinner-small" style="margin:0 auto 8px;"></div>
                  <div>分析中...</div>
                </div>
              </div>
            </div>
          </div>

          <!-- 推荐方案说明 -->
          <div v-if="askHumanRequest.context?.recommendation" class="recommendation">
            ★ 推荐方案：{{ askHumanRequest.context.recommendation }}
          </div>

          <!-- 问题文字 -->
          <p class="question-text">{{ askHumanRequest.question }}</p>

          <!-- 选项模式 -->
          <template v-if="askHumanRequest.options?.length">
            <ARadioGroup v-model:value="answer" style="display:flex; flex-direction:column; gap:10px; margin-bottom:16px;">
              <ARadio v-for="opt in askHumanRequest.options" :key="opt" :value="opt" style="font-size:14px;">{{ opt }}</ARadio>
            </ARadioGroup>
          </template>

          <!-- 自由文本模式 -->
          <template v-else>
            <ATextarea v-model:value="answer" :rows="3" placeholder="请输入您的回答" style="margin-bottom:12px;" />
          </template>

          <AButton
            type="primary"
            :disabled="askHumanRequest.context?.proposals?.length ? selectedSchemeIdx < 0 : !answer"
            @click="submitAnswer"
          >
            {{ askHumanRequest.context?.proposals?.length ? '✅ 确认选择' : '确认提交' }}
          </AButton>
        </template>

        <!-- 无 ask_human 时显示子进度 -->
        <template v-else>
          <!-- 实时方案卡片（后端分析中，ask_human 还未到达） -->
          <div v-if="realTimeSchemes.length > 0" style="margin-bottom:16px;">
            <h3 style="font-size:14px;font-weight:600;margin-bottom:12px;">🔄 多方案优化中...</h3>
            <div class="schemes-container">
              <div
                v-for="scheme in realTimeSchemes"
                :key="scheme.index"
                class="scheme-card completed"
              >
                <div class="scheme-header-card">
                  <span class="scheme-name">{{ scheme.name }}</span>
                  <span>✅</span>
                </div>
                <div class="scheme-body">
                  <div v-for="(val, key) in scheme.metrics" :key="key" class="scheme-metric">
                    <div class="scheme-metric-label">{{ metricLabels[key] || key }}</div>
                    <div class="scheme-metric-value">{{ val }}</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <!-- 交互历史记录（全部） -->
          <div v-if="currentInteractionHistory.length" class="interaction-history">
            <div v-for="(item, i) in currentInteractionHistory" :key="i" class="history-item">
              <div class="history-q">🔔 [{{ getStageLabel(item.stage) }}] {{ item.question }}</div>
              <div class="history-a">✅ 您的回答：{{ item.answer }} <span class="history-time">{{ item.time }}</span></div>
            </div>
          </div>
          <template v-if="progressData">
            <div class="sub-stage-title">
              {{ getStageLabel(progressData.stage) }}
              <span class="sub-pct">{{ Math.round(progressData.progress * 100) }}%</span>
            </div>
            <AProgress
              :percent="Math.round(progressData.progress * 100)"
              :stroke-color="{ '0%': '#108ee9', '100%': '#87d068' }"
              :status="progressData.progress >= 1 ? 'success' : 'active'"
            />
            <div class="sub-message">{{ progressData.message }}</div>
          </template>
          <template v-else>
            <div style="color:#999; padding:20px 0;">等待任务开始...</div>
          </template>
        </template>
      </div>

      <!-- 右侧：设计状态面板 -->
      <div class="right-panel">
        <div class="panel-header">
          <span>📊 设计状态</span>
          <span v-if="viewingStage" class="history-badge">📜 历史 - {{ getStageLabel(viewingStage) }}</span>
          <span v-else class="live-badge">📍 当前进度</span>
        </div>
        <div v-if="viewingStage && snapshots[viewingStage]" class="snapshot-time">
          ⏱️ {{ snapshots[viewingStage].timestamp }}
        </div>

        <div class="params-content">
          <!-- 设计方案阶段 -->
          <template v-if="displayStage === 'design_proposal'">
            <div class="param-card">
              <div class="param-title">📋 设计需求</div>
              <div style="font-size:12px; color:#555; line-height:1.6;">{{ displayParams?.designDescription || '—' }}</div>
            </div>
            <div v-if="displayParams?.geometry || displayParams?.material" class="param-card">
              <div class="param-title">📐 设计参数</div>
              <div class="param-grid">
                <div class="param-item"><span class="param-label">结构类型</span><span class="param-value">{{ displayParams?.designType || '—' }}</span></div>
                <template v-if="displayParams?.geometry">
                  <div v-for="(val, key) in displayParams.geometry" :key="key" class="param-item">
                    <span class="param-label">{{ key }}</span>
                    <span class="param-value">{{ typeof val === 'object' ? JSON.stringify(val) : val }}</span>
                  </div>
                </template>
                <template v-if="displayParams?.material">
                  <div v-for="(val, key) in displayParams.material" :key="'mat-'+key" class="param-item">
                    <span class="param-label">{{ key }}</span>
                    <span class="param-value">{{ typeof val === 'object' ? JSON.stringify(val) : val }}</span>
                  </div>
                </template>
              </div>
            </div>
            <div v-if="displayParams?.standards?.length" class="param-card">
              <div class="param-title">📏 设计规范</div>
              <div v-for="(s, i) in displayParams.standards" :key="i" style="font-size:12px; color:#555; padding:2px 0;">• {{ s }}</div>
            </div>
          </template>

          <!-- 有限元分析阶段 -->
          <template v-else-if="displayStage === 'fe_analysis'">
            <div v-if="snapshots['design_proposal']?.data" class="param-card">
              <div class="param-title">📋 当前设计方案</div>
              <div class="param-grid">
                <div class="param-item"><span class="param-label">类型</span><span class="param-value">{{ snapshots['design_proposal'].data.type || '—' }}</span></div>
                <template v-if="snapshots['design_proposal'].data.geometry">
                  <div v-for="(val, key) in snapshots['design_proposal'].data.geometry" :key="key" class="param-item">
                    <span class="param-label">{{ key }}</span>
                    <span class="param-value">{{ typeof val === 'object' ? JSON.stringify(val) : val }}</span>
                  </div>
                </template>
                <div v-if="snapshots['design_proposal'].data.material?.material_name" class="param-item">
                  <span class="param-label">材料</span>
                  <span class="param-value">{{ snapshots['design_proposal'].data.material.material_name }}</span>
                </div>
              </div>
            </div>
            <div class="param-card">
              <div class="param-title">🔬 有限元分析结果</div>
              <div class="param-grid">
                <div class="param-item"><span class="param-label">最大应力</span><span class="param-value" :class="{ warning: (displayParams?.maxStress ?? 0) > 235 }">{{ displayParams?.maxStress != null ? displayParams.maxStress + ' MPa' : '—' }}</span></div>
                <div class="param-item"><span class="param-label">最大挠度</span><span class="param-value">{{ displayParams?.maxDeflection != null ? displayParams.maxDeflection + ' mm' : '—' }}</span></div>
                <div class="param-item"><span class="param-label">安全系数</span><span class="param-value">{{ displayParams?.safetyFactor ?? '—' }}</span></div>
                <div class="param-item"><span class="param-label">合规状态</span><span class="param-value" :class="displayParams?.complianceStatus === 'compliant' ? 'success' : displayParams?.complianceStatus === 'non_compliant' ? 'warning' : ''">{{ displayParams?.complianceStatus === 'compliant' ? '✅ 合规' : displayParams?.complianceStatus === 'non_compliant' ? '⚠️ 不合规' : '—' }}</span></div>
              </div>
              <div v-if="displayParams?.violations?.length" class="violations">
                <div v-for="(v, i) in displayParams.violations" :key="i" class="violation-item">🔴 {{ typeof v === 'string' ? v : (v.description || '') }}</div>
              </div>
            </div>
          </template>

          <!-- 设计评估阶段 -->
          <template v-else-if="displayStage === 'evaluation'">
            <div v-if="snapshots['design_proposal']?.data" class="param-card">
              <div class="param-title">📋 设计方案</div>
              <div class="param-grid">
                <div class="param-item"><span class="param-label">类型</span><span class="param-value">{{ snapshots['design_proposal'].data.type || '—' }}</span></div>
                <template v-if="snapshots['design_proposal'].data.geometry">
                  <div v-for="(val, key) in snapshots['design_proposal'].data.geometry" :key="key" class="param-item">
                    <span class="param-label">{{ key }}</span>
                    <span class="param-value">{{ typeof val === 'object' ? JSON.stringify(val) : val }}</span>
                  </div>
                </template>
                <div v-if="snapshots['design_proposal'].data.material?.material_name" class="param-item">
                  <span class="param-label">材料</span>
                  <span class="param-value">{{ snapshots['design_proposal'].data.material.material_name }}</span>
                </div>
              </div>
            </div>
            <div class="param-card">
              <div class="param-title">📊 综合评估得分</div>
              <div class="score-grid">
                <div class="score-item"><div class="score-num" :style="{ color: getScoreColor(displayParams?.safetyScore) }">{{ displayParams?.safetyScore ?? '—' }}</div><div class="score-label">安全性</div></div>
                <div class="score-item"><div class="score-num" :style="{ color: getScoreColor(displayParams?.economyScore) }">{{ displayParams?.economyScore ?? '—' }}</div><div class="score-label">经济性</div></div>
                <div class="score-item"><div class="score-num" :style="{ color: getScoreColor(displayParams?.overallScore) }">{{ displayParams?.overallScore ?? '—' }}</div><div class="score-label">综合</div></div>
              </div>
              <div v-if="displayParams?.grade" style="text-align:center; margin-top:8px;">
                <ATag :color="getGradeColor(displayParams.grade)" style="font-size:14px; padding:2px 12px;">{{ displayParams.grade }}</ATag>
              </div>
              <div v-if="displayParams?.warnings?.length" style="margin-top:8px;">
                <div v-for="(w, i) in displayParams.warnings" :key="i" class="violation-item">⚠️ {{ w }}</div>
              </div>
            </div>
          </template>

          <!-- CAD绘图阶段 -->
          <template v-else-if="displayStage === 'cad_drawing'">
            <div v-if="snapshots['design_proposal']?.data" class="param-card">
              <div class="param-title">📋 设计方案</div>
              <div class="param-grid">
                <div class="param-item"><span class="param-label">类型</span><span class="param-value">{{ snapshots['design_proposal'].data.type || '—' }}</span></div>
                <div v-if="snapshots['design_proposal'].data.material?.material_name" class="param-item">
                  <span class="param-label">材料</span>
                  <span class="param-value">{{ snapshots['design_proposal'].data.material.material_name }}</span>
                </div>
              </div>
            </div>
            <div class="param-card">
              <div class="param-title">✏️ CAD图纸</div>
              <div class="param-item" style="margin-bottom:8px;">
                <span class="param-label">状态</span>
                <span class="param-value" :class="displayParams?.drawingStatus === 'completed' ? 'success' : ''">
                  {{ displayParams?.drawingStatus === 'completed' ? '✅ DXF已生成' : displayParams?.drawingStatus === 'skipped' ? '⏭ 已跳过' : '⏳ 生成中...' }}
                </span>
              </div>
              <div v-if="displayParams?.drawingFiles?.length">
                <div class="param-label" style="margin-bottom:4px;">生成文件：</div>
                <div v-for="(f, i) in displayParams.drawingFiles" :key="i" style="font-size:12px; color:#1890ff; padding:2px 0;">📄 {{ f }}</div>
              </div>
            </div>
          </template>

          <!-- BIM/报告阶段 -->
          <template v-else-if="displayStage === 'report_generation'">
            <div class="param-card">
              <div class="param-title">🏗️ BIM导出</div>
              <div class="param-grid">
                <div class="param-item"><span class="param-label">Speckle</span><span class="param-value" :class="displayParams?.speckleExported ? 'success' : ''">{{ displayParams?.speckleExported ? '✅ 已导出' : '⏸ 未导出' }}</span></div>
                <div class="param-item"><span class="param-label">IFC</span><span class="param-value" :class="displayParams?.ifcExported ? 'success' : ''">{{ displayParams?.ifcExported ? '✅ 已生成' : '⏸ 未生成' }}</span></div>
              </div>
            </div>
            <div class="param-card">
              <div class="param-title">📄 报告</div>
              <div class="param-value" :class="displayParams?.reportStatus === 'completed' ? 'success' : ''">{{ displayParams?.reportStatus === 'completed' ? '✅ 已生成' : '⏳ 生成中' }}</div>
            </div>
          </template>

          <template v-else>
            <div class="param-card" style="text-align:center; color:#999; padding:20px;">等待任务开始...</div>
          </template>
        </div>
      </div>
    </div>
  </ACard>
</template>

<script setup lang="ts">
import { ref, computed, watch, reactive } from 'vue';
import { Card as ACard, Progress as AProgress, Button as AButton, Radio as ARadio, RadioGroup as ARadioGroup, Input, Tag as ATag, Table as ATable } from 'ant-design-vue';
import { getStageLabel } from '#/utils/i18n';

const ATextarea = Input.TextArea;

const props = defineProps<{
  stages: any[];
  progressData: any | null;
  taskParams: any | null;
  askHumanRequest: any | null;
  schemeUpdates: any[];
}>();

const emit = defineEmits<{ submit: [answer: string] }>();

const steps = [
  { key: 'design_proposal', label: '设计方案', icon: '📋' },
  { key: 'fe_analysis', label: '有限元分析', icon: '🔬' },
  { key: 'evaluation', label: '设计评估', icon: '📊' },
  { key: 'cad_drawing', label: 'CAD绘图', icon: '✏️' },
  { key: 'report_generation', label: 'BIM/报告', icon: '🏗️' },
];

const answer = ref('');
const snapshots = reactive<Record<string, any>>({});
const viewingStage = ref<string | null>(null);
// 交互历史按阶段存储，key 为 stage name
const interactionHistoryByStage = reactive<Record<string, { question: string; answer: string; time: string }[]>>({});

// 当前阶段的交互历史（用于实时显示）
const currentInteractionHistory = computed(() => {
  const all: { question: string; answer: string; time: string; stage: string }[] = [];
  for (const [stage, items] of Object.entries(interactionHistoryByStage)) {
    for (const item of items) all.push({ ...item, stage });
  }
  return all.sort((a, b) => a.time.localeCompare(b.time));
});

// 多方案实时数据
const realTimeSchemes = ref<any[]>([]);  // 实时接收的方案数据
const selectedSchemeIdx = ref<number>(-1);

const metricLabels: Record<string, string> = {
  section: '截面(m)', material: '材料', stress: '应力(MPa)',
  displacement: '位移(mm)', safety: '安全性', economy: '经济性',
  efficiency: '结构效率', sustainability: '可持续性',
  total_score: '综合得分', grade: '等级',
};

// 监听实时方案推送
watch(() => props.schemeUpdates, (updates) => {
  if (!updates || updates.length === 0) return;

  // 按 index 排序并更新 realTimeSchemes
  const sorted = [...updates].sort((a, b) => a.index - b.index);
  realTimeSchemes.value = sorted.map(u => ({
    name: `方案 ${u.index}`,
    metrics: u.metrics,
    index: u.index,
  }));
}, { deep: true });

// 当 ask_human 包含 proposals 时，初始化选择状态
watch(() => props.askHumanRequest, (req) => {
  answer.value = req?.default || (req?.options?.[0] ?? '');
  if (req?.context?.proposals?.length) {
    // 如果没有实时数据，使用 ask_human 中的 proposals（兼容旧版本）
    if (realTimeSchemes.value.length === 0) {
      realTimeSchemes.value = req.context.proposals.map((p: any, i: number) => ({
        name: p.name,
        metrics: p.metrics,
        index: i + 1,
        recommended: p.recommended,
      }));
    }

    // 找推荐方案作为默认选中
    const recIdx = req.context.proposals.findIndex((p: any) => p.recommended);
    selectedSchemeIdx.value = recIdx >= 0 ? recIdx : 0;
  }
});

watch(() => props.stages, (newStages) => {
  for (const s of newStages) {
    if ((s.status === 'completed' || s.status === 'skipped') && s.data) {
      // 始终用最新数据覆盖（支持优化后方案更新）
      snapshots[s.stage] = {
        timestamp: new Date().toLocaleTimeString(),
        data: s.data,
      };
    } else if ((s.status === 'completed' || s.status === 'skipped') && !snapshots[s.stage]) {
      snapshots[s.stage] = {
        timestamp: new Date().toLocaleTimeString(),
        data: null,
      };
    }
  }
}, { deep: true });

const latestByStage = computed(() => {
  const map: Record<string, any> = {};
  for (const s of props.stages) map[s.stage] = s;
  return map;
});

const activeStage = computed(() => {
  let last = '';
  for (const step of steps) { if (latestByStage.value[step.key]) last = step.key; }
  return last;
});

const displayStage = computed(() => viewingStage.value || activeStage.value);

// 从 snapshot data 映射为面板字段
function mapSnapshotData(d: any) {
  if (!d) return null;
  return {
    designDescription: d.description,
    designType: d.type,
    geometry: d.geometry,
    material: d.material,
    standards: d.standards,
    // fe_analysis
    maxStress: d.max_stress_MPa,
    maxDeflection: d.max_displacement_mm,
    safetyFactor: d.safety_factor,
    complianceStatus: d.compliant === true ? 'compliant' : d.compliant === false ? 'non_compliant' : null,
    violations: d.violations,
    // evaluation
    overallScore: d.comprehensive_score,
    safetyScore: d.safety_score,
    economyScore: d.economy_score,
    efficiencyScore: d.efficiency_score,
    sustainabilityScore: d.sustainability_score,
    grade: d.grade,
    warnings: d.warnings,
    // cad_drawing
    drawingStatus: d.status,
    drawingFiles: d.files,
    // report_generation
    reportStatus: d.report_status,
    speckleExported: d.speckle_exported,
    ifcExported: d.ifc_exported,
  };
}

const displayParams = computed(() => {
  const stage = displayStage.value;
  if (!stage) return props.taskParams;

  // 优先用 snapshot（已完成阶段的数据）
  if (snapshots[stage]?.data) return mapSnapshotData(snapshots[stage].data);

  // 运行中阶段：用 taskParams（任务完成后有数据）或 null
  return props.taskParams;
});

const getStageStatus = (key: string) => latestByStage.value[key]?.status || 'pending';

const getStepClass = (key: string) => ({
  completed: getStageStatus(key) === 'completed',
  active: getStageStatus(key) === 'started' || getStageStatus(key) === 'running',
  failed: getStageStatus(key) === 'failed',
  skipped: getStageStatus(key) === 'skipped',
  viewing: viewingStage.value === key,
  clickable: !!snapshots[key] || !!latestByStage.value[key],
});

const statusTextMap: Record<string, string> = { completed: '✅ 完成', started: '⏳ 进行中', running: '⏳ 进行中', failed: '❌ 失败', skipped: '⏭ 跳过' };
const getStepStatusText = (key: string) => statusTextMap[getStageStatus(key)] || '⏸ 等待';

const onStepClick = (key: string) => {
  // 有 snapshot 或有 stage 记录都可以点击查看历史
  if (snapshots[key] || latestByStage.value[key]) {
    viewingStage.value = viewingStage.value === key ? null : key;
  }
};

const getScoreColor = (score: number | null) => {
  if (score == null) return '#999';
  return score >= 80 ? '#52c41a' : score >= 70 ? '#faad14' : '#f5222d';
};

const getGradeColor = (grade: string) => {
  if (!grade) return 'default';
  if (grade.startsWith('A')) return 'green';
  if (grade.startsWith('B')) return 'blue';
  if (grade.startsWith('C')) return 'orange';
  return 'red';
};

const proposalColumns = computed(() => {
  if (!props.askHumanRequest?.context?.proposals?.length) return [];
  const metrics = props.askHumanRequest.context.proposals[0]?.metrics || {};
  const metricLabels: Record<string, string> = {
    section: '截面', material: '材料',
    stress: '最大应力', displacement: '最大挠度',
    safety: '安全性', economy: '经济性',
    total_score: '综合得分', grade: '等级',
  };
  return [
    { title: '方案', key: 'name', dataIndex: 'name', width: 100 },
    ...Object.keys(metrics).map(k => ({ title: metricLabels[k] || k, key: k, dataIndex: ['metrics', k], width: 100 })),
  ];
});

const submitAnswer = () => {
  let submitted = '';
  if (props.askHumanRequest?.context?.proposals?.length) {
    submitted = String(selectedSchemeIdx.value);
  } else {
    if (!answer.value) return;
    submitted = answer.value.split(' - ')[0].trim();
  }
  // 按阶段存储交互记录
  const stage = activeStage.value || 'unknown';
  if (!interactionHistoryByStage[stage]) interactionHistoryByStage[stage] = [];
  interactionHistoryByStage[stage].push({
    question: props.askHumanRequest?.question || '',
    answer: submitted,
    time: new Date().toLocaleTimeString(),
  });
  emit('submit', submitted);
  answer.value = '';
};
</script>

<style scoped>
.progress-panel { margin-bottom: 12px; }

/* 去掉 ACard body 的默认 padding，让 grid 撑满 */
:deep(.ant-card-body) { padding: 0; }

.steps-nav {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 16px 16px 20px;
  overflow-x: auto;
  border-bottom: 1px solid #f0f0f0;
}

.step-item {
  flex: 1;
  text-align: center;
  position: relative;
  cursor: default;
  min-width: 80px;
}
.step-item.clickable { cursor: pointer; }
.step-item.clickable:hover .step-icon { transform: scale(1.08); }

.step-icon {
  width: 48px; height: 48px;
  border-radius: 50%;
  border: 3px solid #dee2e6;
  background: white;
  margin: 0 auto 8px;
  display: flex; align-items: center; justify-content: center;
  font-size: 20px;
  transition: all 0.3s;
}
.step-item.completed .step-icon { border-color: #52c41a; background: #f6ffed; }
.step-item.active .step-icon { border-color: #1890ff; animation: pulse 2s infinite; }
.step-item.failed .step-icon { border-color: #f5222d; background: #fff1f0; }
.step-item.skipped .step-icon { border-color: #d9d9d9; background: #f5f5f5; opacity: 0.6; }
.step-item.viewing .step-icon { box-shadow: 0 0 0 3px rgba(23,162,184,0.4); }

@keyframes pulse {
  0% { box-shadow: 0 0 0 0 rgba(24,144,255,0.4); }
  70% { box-shadow: 0 0 0 8px rgba(24,144,255,0); }
  100% { box-shadow: 0 0 0 0 rgba(24,144,255,0); }
}

.step-title { font-size: 12px; font-weight: 600; color: #495057; margin-bottom: 2px; }
.step-status { font-size: 11px; color: #6c757d; }

.step-connector {
  position: absolute; top: 24px; right: -50%;
  width: 100%; height: 2px; background: #dee2e6; z-index: 0;
}

.main-body {
  display: grid;
  grid-template-columns: 1fr 380px;
  gap: 0;
  border-top: 1px solid #f0f0f0;
  min-height: 220px;
}

.left-panel { padding: 16px; border-right: 1px solid #f0f0f0; }

.preview-box { margin-bottom: 16px; text-align: center; background: #f0f7ff; padding: 16px; border-radius: 8px; }

.warnings-list { margin-bottom: 12px; }
.violation-item { font-size: 13px; color: #fa8c16; padding: 3px 0; }

.score-summary { margin-bottom: 12px; padding: 12px; background: #f5f5f5; border-radius: 6px; }

.recommendation { margin-bottom: 12px; padding: 10px 12px; background: #e6f7ff; border-left: 4px solid #1890ff; border-radius: 4px; font-size: 13px; color: #333; }

.question-text { font-size: 16px; font-weight: 500; color: #1890ff; margin-bottom: 16px; white-space: pre-wrap; }

.sub-stage-title { font-size: 14px; font-weight: 600; color: #333; margin-bottom: 10px; display: flex; justify-content: space-between; }
.sub-pct { color: #1890ff; }
.sub-message { margin-top: 8px; font-size: 13px; color: #666; }

.right-panel { padding: 12px 16px; background: #fafafa; overflow-y: auto; max-height: 600px; }

.panel-header { font-size: 13px; font-weight: 600; color: #333; margin-bottom: 4px; display: flex; align-items: center; justify-content: space-between; }
.history-badge { font-size: 11px; background: #17a2b8; color: white; padding: 2px 8px; border-radius: 10px; }
.live-badge { font-size: 11px; background: #e9ecef; color: #6c757d; padding: 2px 8px; border-radius: 10px; }
.snapshot-time { font-size: 11px; color: #6c757d; margin-bottom: 8px; }

.params-content { margin-top: 8px; }
.param-card { background: white; border-radius: 8px; padding: 12px; margin-bottom: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
.param-title { font-size: 12px; font-weight: 600; color: #495057; margin-bottom: 8px; padding-bottom: 6px; border-bottom: 1px solid #f0f0f0; }
.param-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
.param-item { display: flex; flex-direction: column; gap: 2px; }
.param-label { font-size: 11px; color: #999; }
.param-value { font-size: 13px; color: #333; font-weight: 500; }
.param-value.success { color: #52c41a; }
.param-value.warning { color: #faad14; }
.score-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; text-align: center; }
.score-num { font-size: 26px; font-weight: bold; }
.score-label { font-size: 12px; color: #666; }
.violations { margin-top: 8px; }
.back-btn-wrap { margin-top: 8px; text-align: center; }

@media (max-width: 768px) {
  .main-body { grid-template-columns: 1fr; }
  .left-panel { border-right: none; border-bottom: 1px solid #f0f0f0; }
}

.interaction-history { margin-bottom: 12px; }
.history-item { background: #f6ffed; border: 1px solid #b7eb8f; border-radius: 6px; padding: 8px 10px; margin-bottom: 6px; }
.history-q { font-size: 12px; color: #666; margin-bottom: 4px; }
.history-a { font-size: 13px; color: #389e0d; font-weight: 500; }
.history-time { font-size: 11px; color: #999; margin-left: 8px; }

.history-stage-header {
  font-size: 13px;
  font-weight: 600;
  color: #17a2b8;
  padding: 8px 0 12px;
  border-bottom: 1px solid #e9ecef;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
}

.ask-human-banner {  background: #fff7e6;
  border: 1px solid #ffd591;
  border-radius: 6px;
  padding: 8px 12px;
  font-size: 13px;
  color: #d46b08;
  font-weight: 600;
  margin-bottom: 12px;
  animation: pulse-banner 1.5s ease-in-out infinite;
}
@keyframes pulse-banner {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

.schemes-container { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 12px; }

.scheme-card {
  border: 2px solid #dee2e6;
  border-radius: 8px;
  padding: 10px 12px;
  transition: all 0.3s;
}
.scheme-card.optimizing { border-color: #1890ff; background: #f0f7ff; }
.scheme-card.completed { border-color: #d9d9d9; }
.scheme-card.selected { border-color: #52c41a; background: #f6ffed; }

.scheme-header-card { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.scheme-name { font-size: 13px; font-weight: 600; }
.scheme-badge { font-size: 11px; background: #faad14; color: white; padding: 1px 6px; border-radius: 8px; margin-left: 6px; }

.optimizing-text { display: flex; align-items: center; gap: 8px; font-size: 13px; color: #1890ff; margin-bottom: 6px; }
.spinner-small {
  width: 14px; height: 14px;
  border: 2px solid #d9d9d9;
  border-top-color: #1890ff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.progress-bar-container { height: 6px; background: #e9ecef; border-radius: 3px; overflow: hidden; }
.progress-bar-fill { height: 100%; background: linear-gradient(90deg, #108ee9, #87d068); transition: width 0.05s linear; }

.scheme-body { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 8px; }
.scheme-metric { display: flex; flex-direction: column; gap: 2px; }
.scheme-metric-label { font-size: 11px; color: #999; }
.scheme-metric-value { font-size: 13px; font-weight: 600; color: #333; }

.select-btn {
  padding: 3px 10px; border-radius: 4px; border: 1px solid #1890ff;
  background: white; color: #1890ff; cursor: pointer; font-size: 12px;
}
.select-btn:disabled { border-color: #52c41a; color: #52c41a; cursor: default; }
</style>
