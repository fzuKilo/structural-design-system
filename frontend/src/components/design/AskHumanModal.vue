<template>
  <a-modal
    :open="!!request"
    title="需要您的确认"
    :footer="null"
    :closable="false"
    :maskClosable="false"
  >
    <template v-if="request">
      <p style="font-size: 16px; margin-bottom: 16px;">{{ request.question }}</p>

      <!-- Options mode -->
      <template v-if="request.options?.length">
        <a-radio-group v-model:value="answer" style="display: flex; flex-direction: column; gap: 8px;">
          <a-radio v-for="opt in request.options" :key="opt" :value="opt">{{ opt }}</a-radio>
        </a-radio-group>
      </template>

      <!-- Free text mode -->
      <template v-else>
        <a-input v-model:value="answer" placeholder="请输入您的回答" size="large" />
      </template>

      <div style="margin-top: 16px; text-align: right;">
        <a-button type="primary" :disabled="!answer" @click="handleSubmit">确认</a-button>
      </div>
    </template>
  </a-modal>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import type { AskHumanRequest } from '@/types/task'

const props = defineProps<{ request: AskHumanRequest | null }>()
const emit = defineEmits<{ submit: [answer: string] }>()

const answer = ref('')

watch(() => props.request, (req) => {
  answer.value = req?.default || (req?.options?.[0] ?? '')
})

const handleSubmit = () => {
  if (answer.value) {
    emit('submit', answer.value)
    answer.value = ''
  }
}
</script>
