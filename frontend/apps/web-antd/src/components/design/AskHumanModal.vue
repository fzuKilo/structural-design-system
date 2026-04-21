<template>
  <AModal
    :open="!!request"
    title="🔔 需要您的确认"
    :footer="null"
    :closable="false"
    :maskClosable="false"
    :width="900"
    :z-index="2000"
    :style="{ top: '20px' }"
  >
    <template v-if="request">
      <div style="padding: 16px 0;">
        <!-- 图片预览 -->
        <div v-if="request.image_path" style="margin-bottom: 20px; text-align: center;">
          <img
            :src="`/api/file/view?path=${encodeURIComponent(request.image_path)}`"
            style="max-width: 100%; max-height: 400px; border-radius: 4px; border: 1px solid #d9d9d9;"
            alt="模型预览图"
          />
        </div>

        <!-- Context: Warnings -->
        <div v-if="request.context?.warnings?.length" style="margin-bottom: 20px;">
          <AAlert
            v-for="(warning, idx) in request.context.warnings"
            :key="idx"
            :message="warning"
            type="warning"
            show-icon
            style="margin-bottom: 8px;"
          />
        </div>

        <!-- Context: Score and Grade -->
        <div v-if="request.context?.score !== undefined" style="margin-bottom: 20px; padding: 16px; background: #f5f5f5; border-radius: 4px;">
          <div style="display: flex; align-items: center; gap: 24px;">
            <div>
              <span style="font-size: 14px; color: #666;">综合得分：</span>
              <span style="font-size: 24px; font-weight: bold; color: #1890ff;">{{ request.context.score }}</span>
            </div>
            <div>
              <span style="font-size: 14px; color: #666;">等级：</span>
              <ATag :color="getGradeColor(request.context.grade)" style="font-size: 18px; padding: 4px 12px;">
                {{ request.context.grade }}
              </ATag>
            </div>
          </div>
        </div>

        <!-- Context: Proposal Comparison Table -->
        <div v-if="request.context?.proposals?.length" style="margin-bottom: 20px;">
          <ATable
            :columns="proposalColumns"
            :data-source="request.context.proposals"
            :pagination="false"
            size="small"
            bordered
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'name'">
                <span :style="{ fontWeight: record.recommended ? 'bold' : 'normal' }">
                  {{ record.name }}
                  <span v-if="record.recommended" style="color: #faad14;">★</span>
                </span>
              </template>
              <template v-else>
                {{ record.metrics[column.key] || '-' }}
              </template>
            </template>
          </ATable>
        </div>

        <!-- Context: Recommendation -->
        <div v-if="request.context?.recommendation" style="margin-bottom: 20px; padding: 12px; background: #e6f7ff; border-left: 4px solid #1890ff; border-radius: 4px;">
          <span style="font-weight: 500; color: #1890ff;">★ 推荐方案：</span>
          <span style="color: #333;">{{ request.context.recommendation }}</span>
        </div>

        <!-- Context: FE Analysis violations and current params -->
        <div v-if="request.context?.violations" style="margin-bottom: 16px; padding: 12px; background: #fff2f0; border-left: 4px solid #ff4d4f; border-radius: 4px;">
          <div style="font-weight: 500; color: #ff4d4f; margin-bottom: 6px;">⚠️ 违规详情</div>
          <pre style="margin: 0; font-size: 13px; color: #333; white-space: pre-wrap;">{{ request.context.violations }}</pre>
        </div>
        <div v-if="request.context?.max_stress" style="margin-bottom: 16px; padding: 12px; background: #f5f5f5; border-radius: 4px;">
          <div style="font-weight: 500; margin-bottom: 6px;">📊 关键结果</div>
          <div style="display: flex; flex-wrap: wrap; gap: 16px; font-size: 13px;">
            <span v-if="request.context.max_stress"><b>最大应力：</b>{{ request.context.max_stress }}</span>
            <span v-if="request.context.max_displacement"><b>最大位移：</b>{{ request.context.max_displacement }}</span>
            <span v-if="request.context.max_moment"><b>最大弯矩：</b>{{ request.context.max_moment }}</span>
          </div>
          <div style="display: flex; flex-wrap: wrap; gap: 16px; font-size: 13px; margin-top: 6px;">
            <span v-if="request.context.current_span"><b>跨度：</b>{{ request.context.current_span }}</span>
            <span v-if="request.context.current_section"><b>截面：</b>{{ request.context.current_section }}</span>
            <span v-if="request.context.current_material"><b>材料：</b>{{ request.context.current_material }}</span>
          </div>
        </div>

        <!-- Context: Suggestions (array) -->
        <div v-if="request.context?.suggestions?.length" style="margin-bottom: 16px; padding: 12px; background: #f6ffed; border-left: 4px solid #52c41a; border-radius: 4px;">
          <div style="font-weight: 500; color: #389e0d; margin-bottom: 6px;">💡 改进建议</div>
          <ul style="margin: 0; padding-left: 20px; font-size: 13px; color: #333;">
            <li v-for="(s, i) in request.context.suggestions" :key="i" style="margin-bottom: 4px;">{{ s }}</li>
          </ul>
        </div>

        <!-- Context: Suggestions text (LLM generated, string) -->
        <div v-if="request.context?.suggestions_text" style="margin-bottom: 16px; padding: 12px; background: #f6ffed; border-left: 4px solid #52c41a; border-radius: 4px;">
          <div style="font-weight: 500; color: #389e0d; margin-bottom: 6px;">💡 LLM 改进建议</div>
          <pre style="margin: 0; font-size: 13px; color: #333; white-space: pre-wrap; font-family: inherit;">{{ request.context.suggestions_text }}</pre>
        </div>

        <!-- Context: Generic fields (fallback for any unhandled context fields) -->
        <div v-if="otherContextFields.length" style="margin-bottom: 16px;">
          <div v-for="field in otherContextFields" :key="field.key" style="margin-bottom: 12px; padding: 12px; background: #fafafa; border-left: 4px solid #d9d9d9; border-radius: 4px;">
            <div style="font-weight: 500; color: #595959; margin-bottom: 6px;">{{ formatContextKey(field.key) }}</div>
            <div v-if="typeof field.value === 'object' && !Array.isArray(field.value)" style="font-size: 13px; color: #333;">
              <div v-for="(val, key) in field.value" :key="key" style="padding: 4px 0; border-bottom: 1px solid #f0f0f0;">
                <span style="color: #8c8c8c; min-width: 100px; display: inline-block;">{{ key }}：</span>
                <span>{{ val }}</span>
              </div>
            </div>
            <div v-else style="font-size: 13px; color: #333; white-space: pre-wrap;">{{ field.value }}</div>
          </div>
        </div>

        <p style="font-size: 18px; font-weight: 500; margin-bottom: 20px; color: #1890ff; white-space: pre-wrap;">
          {{ request.question }}
        </p>

        <!-- suggestions_text mode: text input + skip button -->
        <template v-if="request.context?.suggestions_text">
          <ATextarea v-model:value="answer" :rows="4" placeholder="描述改进方案，如：增大截面尺寸、更换材料等" />
          <div style="margin-top: 24px; display: flex; justify-content: flex-end; gap: 12px;">
            <AButton size="large" @click="handleSkip">跳过，使用当前方案</AButton>
            <AButton type="primary" size="large" :disabled="!answer.trim()" @click="handleSubmit">提交改进方案</AButton>
          </div>
        </template>

        <!-- Options mode: show radio -->
        <template v-else-if="request.options?.length">
          <ARadioGroup v-model:value="radioAnswer" style="display: flex; flex-direction: column; gap: 12px;" @change="onRadioChange">
            <ARadio v-for="opt in request.options" :key="opt" :value="opt" style="font-size: 15px;">
              {{ opt }}
            </ARadio>
          </ARadioGroup>
          <div v-if="isManualMode" style="margin-top: 16px;">
            <div style="font-size: 13px; color: #666; margin-bottom: 8px;">请输入改进方案（如：增加截面高度到0.5m，改用C40混凝土）：</div>
            <ATextarea v-model:value="manualInput" :rows="4" placeholder="描述改进方案，或直接输入JSON格式的设计参数" />
          </div>
          <div style="margin-top: 24px; text-align: right;">
            <AButton type="primary" size="large" :disabled="isManualMode ? !manualInput.trim() : !radioAnswer" @click="handleSubmit">
              确认提交
            </AButton>
          </div>
        </template>

        <!-- Free text mode -->
        <template v-else>
          <ATextarea v-model:value="answer" :rows="4" placeholder="请输入您的回答" size="large" />
          <div style="margin-top: 24px; text-align: right;">
            <AButton type="primary" size="large" :disabled="!answer" @click="handleSubmit">确认提交</AButton>
          </div>
        </template>
      </div>
    </template>
  </AModal>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue';

import { Button as AButton, Input as AInput, Modal as AModal, Radio as ARadio, RadioGroup as ARadioGroup, Alert as AAlert, Tag as ATag, Table as ATable, Textarea as ATextarea } from 'ant-design-vue';

const props = defineProps<{ request: any | null }>();
const emit = defineEmits<{ submit: [answer: string] }>();

const answer = ref('');
const radioAnswer = ref('');
const manualInput = ref('');

const isManualMode = computed(() => radioAnswer.value.startsWith('manual'));

// Extract context fields that are not handled by specific UI sections
const otherContextFields = computed(() => {
  if (!props.request?.context) return [];

  const handledKeys = new Set([
    'warnings', 'score', 'grade', 'proposals', 'recommendation', 'image_path',
    'violations', 'max_stress', 'max_displacement', 'max_moment',
    'current_span', 'current_section', 'current_material', 'suggestions',
    'suggestions_text', 'summary', 'description'
  ]);

  const fields = [];
  for (const [key, value] of Object.entries(props.request.context)) {
    if (!handledKeys.has(key) && value !== null && value !== undefined) {
      fields.push({ key, value });
    }
  }
  return fields;
});

const formatContextKey = (key: string) => {
  // Convert snake_case or camelCase to readable format
  const formatted = key.replace(/_/g, ' ').replace(/([A-Z])/g, ' $1');
  return formatted.charAt(0).toUpperCase() + formatted.slice(1);
};

const onRadioChange = () => {
  if (!isManualMode.value) {
    manualInput.value = '';
  }
};

const proposalColumns = computed(() => {
  if (!props.request?.context?.proposals?.length) return [];

  const firstProposal = props.request.context.proposals[0];
  const metrics = firstProposal.metrics || {};

  const columns = [
    { title: '方案', key: 'name', dataIndex: 'name', width: 100, fixed: 'left' }
  ];

  const metricLabels: Record<string, string> = {
    section: '截面(m)',
    material: '材料',
    stress: '应力(MPa)',
    displacement: '位移(mm)',
    economy: '经济性',
    efficiency: '结构效率',
    safety: '安全性',
    sustainability: '可持续性',
    total_score: '综合得分',
    grade: '等级',
  };

  for (const key in metrics) {
    columns.push({
      title: metricLabels[key] || key,
      key: key,
      dataIndex: ['metrics', key],
      width: 100,
    });
  }

  return columns;
});

const getGradeColor = (grade: string) => {
  if (!grade) return 'default';
  if (grade.startsWith('A')) return 'green';
  if (grade.startsWith('B')) return 'blue';
  if (grade.startsWith('C')) return 'orange';
  return 'red';
};

watch(() => props.request, (req) => {
  answer.value = req?.default || (req?.options?.[0] ?? '');
  radioAnswer.value = req?.default || (req?.options?.[0] ?? '');
  manualInput.value = '';
  if (req) {
    console.log('[AskHumanModal] Received request:', req);
    console.log('[AskHumanModal] Context:', req.context);
  }
});

const handleSkip = () => {
  emit('submit', 'skip');
  answer.value = '';
  radioAnswer.value = '';
  manualInput.value = '';
};

const handleSubmit = () => {
  let finalAnswer: string;
  if (props.request?.options?.length) {
    if (isManualMode.value) {
      // manual mode: submit the text input content
      finalAnswer = manualInput.value.trim();
      if (!finalAnswer) return;
    } else {
      finalAnswer = radioAnswer.value.split(' - ')[0].trim();
    }
  } else {
    finalAnswer = answer.value;
  }
  if (finalAnswer) {
    emit('submit', finalAnswer);
    answer.value = '';
    radioAnswer.value = '';
    manualInput.value = '';
  }
};
</script>
