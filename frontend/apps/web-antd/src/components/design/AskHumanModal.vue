<template>
  <AModal
    :open="!!request"
    title="🔔 需要您的确认"
    :footer="null"
    :closable="false"
    :maskClosable="false"
    :width="600"
    :z-index="2000"
    centered
  >
    <template v-if="request">
      <div style="padding: 16px 0;">
        <p style="font-size: 18px; font-weight: 500; margin-bottom: 20px; color: #1890ff;">
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
import { ref, watch } from 'vue';

import { Button as AButton, Input as AInput, Modal as AModal, Radio as ARadio, RadioGroup as ARadioGroup } from 'ant-design-vue';

const props = defineProps<{ request: any | null }>();
const emit = defineEmits<{ submit: [answer: string] }>();

const answer = ref('');

watch(() => props.request, (req) => {
  answer.value = req?.default || (req?.options?.[0] ?? '');
});

const handleSubmit = () => {
  if (answer.value) {
    const shortValue = answer.value.split(' - ')[0].trim();
    emit('submit', shortValue);
    answer.value = '';
  }
};
</script>
