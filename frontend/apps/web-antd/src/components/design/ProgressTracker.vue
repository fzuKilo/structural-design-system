<template>
  <a-card title="设计进度">
    <a-steps :current="currentStep" :status="stepStatus">
      <a-step
        v-for="step in steps"
        :key="step.key"
        :title="step.label"
        :description="getStepDescription(step.key)"
      />
    </a-steps>
  </a-card>
</template>

<script setup lang="ts">
import { computed } from 'vue';

import { getStageLabel } from '#/utils/i18n';

const props = defineProps<{ stages: any[] }>();

const steps = [
  { key: 'design_proposal', label: getStageLabel('design_proposal') },
  { key: 'fe_analysis', label: getStageLabel('fe_analysis') },
  { key: 'evaluation', label: getStageLabel('evaluation') },
  { key: 'cad_drawing', label: getStageLabel('cad_drawing') },
  { key: 'report_generation', label: getStageLabel('report_generation') },
];

const latestByStage = computed(() => {
  const map: Record<string, any> = {};
  for (const s of props.stages) map[s.stage] = s;
  return map;
});

const currentStep = computed(() => {
  let last = -1;
  steps.forEach((step, i) => { if (latestByStage.value[step.key]) last = i; });
  return last;
});

const stepStatus = computed(() => {
  const last = steps[currentStep.value];
  if (!last) return 'process';
  const s = latestByStage.value[last.key];
  if (s?.status === 'failed') return 'error';
  if (s?.status === 'completed' && currentStep.value === steps.length - 1) return 'finish';
  return 'process';
});

const statusText: Record<string, string> = {
  running: '进行中', completed: '已完成', failed: '失败',
};

const getStepDescription = (key: string) => {
  const s = latestByStage.value[key];
  if (!s) return '';
  return statusText[s.status] || s.status;
};
</script>
