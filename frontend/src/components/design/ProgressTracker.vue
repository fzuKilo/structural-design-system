<template>
  <a-card title="设计进度">
    <a-steps :current="currentStep" :status="stepStatus">
      <a-step
        v-for="(step, index) in steps"
        :key="step.key"
        :title="step.label"
        :description="getStepDescription(step.key)"
      />
    </a-steps>
  </a-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { StageUpdate } from '@/types/task'
import { getStageLabel, getStageMessage } from '@/utils/i18n'

const props = defineProps<{ stages: StageUpdate[] }>()

const steps = [
  { key: 'design_proposal', label: '设计方案' },
  { key: 'fe_analysis', label: '有限元分析' },
  { key: 'evaluation', label: '设计评估' },
  { key: 'cad_drawing', label: 'CAD绘图' },
  { key: 'report_generation', label: '报告生成' }
]

const latestByStage = computed(() => {
  const map: Record<string, StageUpdate> = {}
  for (const s of props.stages) {
    map[s.stage] = s
  }
  return map
})

const currentStep = computed(() => {
  let last = -1
  steps.forEach((step, i) => {
    if (latestByStage.value[step.key]) last = i
  })
  return last
})

const stepStatus = computed(() => {
  const last = steps[currentStep.value]
  if (!last) return 'process'
  const s = latestByStage.value[last.key]
  if (s?.status === 'failed') return 'error'
  if (s?.status === 'completed' && currentStep.value === steps.length - 1) return 'finish'
  return 'process'
})

const getStepDescription = (key: string) => {
  const s = latestByStage.value[key]
  if (!s) return ''
  return getStageMessage(s.stage, s.status)
}
</script>
