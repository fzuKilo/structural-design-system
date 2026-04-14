<template>
  <AModal
    :open="!!request"
    title="🔔 需要您的确认"
    :footer="null"
    :closable="false"
    :maskClosable="false"
    :width="900"
    :z-index="2000"
    centered
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

        <p style="font-size: 18px; font-weight: 500; margin-bottom: 20px; color: #1890ff; white-space: pre-wrap;">
          {{ request.question }}
        </p>

        <!-- Options mode -->
        <template v-if="request.options?.length">
          <ARadioGroup v-model:value="answer" style="display: flex; flex-direction: column; gap: 12px;">
            <ARadio v-for="opt in request.options" :key="opt" :value="opt" style="font-size: 15px;">
              {{ opt }}
            </ARadio>
          </ARadioGroup>
        </template>

        <!-- Free text mode -->
        <template v-else>
          <AInput v-model:value="answer" placeholder="请输入您的回答" size="large" />
        </template>

        <div style="margin-top: 24px; text-align: right;">
          <AButton type="primary" size="large" :disabled="!answer" @click="handleSubmit">
            确认提交
          </AButton>
        </div>
      </div>
    </template>
  </AModal>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue';

import { Button as AButton, Input as AInput, Modal as AModal, Radio as ARadio, RadioGroup as ARadioGroup, Alert as AAlert, Tag as ATag, Table as ATable } from 'ant-design-vue';

const props = defineProps<{ request: any | null }>();
const emit = defineEmits<{ submit: [answer: string] }>();

const answer = ref('');

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
  // Debug: 打印接收到的请求数据
  if (req) {
    console.log('[AskHumanModal] Received request:', req);
    console.log('[AskHumanModal] Context:', req.context);
  }
});

const handleSubmit = () => {
  if (answer.value) {
    const shortValue = answer.value.split(' - ')[0].trim();
    emit('submit', shortValue);
    answer.value = '';
  }
};
</script>
