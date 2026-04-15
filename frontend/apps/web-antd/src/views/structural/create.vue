<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue';

import { Alert as AAlert, Button as AButton, Card as ACard, Form as AForm, FormItem as AFormItem, message, Textarea as ATextarea } from 'ant-design-vue';
import { useRouter } from 'vue-router';

import { baseRequestClient } from '#/api/request';
import { createDesignApi } from '#/api/design';

const router = useRouter();
const submitting = ref(false);
const hasApiKey = ref<boolean | null>(null);

const form = reactive({ request_text: '' });

onMounted(async () => {
  const res = await baseRequestClient.get('/auth/profile');
  const profile = (res as any)?.data ?? res;
  hasApiKey.value = !!profile?.has_api_key;
});

const handleSubmit = async () => {
  if (!form.request_text) { message.warning('请填写设计描述'); return; }
  submitting.value = true;
  try {
    const result = await createDesignApi(form);
    message.success('设计任务提交成功');
    router.push(`/structural/detail/${result.id}`);
  } catch (err: any) {
    const detail = err?.response?.data?.detail;
    message.error(detail || '提交失败，请重试');
  } finally {
    submitting.value = false;
  }
};
</script>

<template>
  <div class="p-4">
    <div class="mb-4 flex items-center gap-2">
      <AButton @click="router.push('/structural')">← 返回</AButton>
      <h2 class="m-0 text-lg font-semibold">新建设计任务</h2>
    </div>

    <AAlert
      v-if="hasApiKey === false"
      type="warning"
      class="mb-4"
      show-icon
      message="您尚未配置 API Key，无法提交设计任务"
      description="请前往个人中心 → API Key 标签页配置您的 DeepSeek API Key"
    >
      <template #action>
        <AButton size="small" type="primary" @click="router.push('/profile')">
          去配置
        </AButton>
      </template>
    </AAlert>

    <ACard>
      <AForm :model="form" layout="vertical">
        <AFormItem label="设计描述" required>
          <ATextarea v-model:value="form.request_text" :rows="6" placeholder="请详细描述您的结构设计需求..." />
        </AFormItem>
        <AFormItem>
          <AButton type="primary" :loading="submitting" :disabled="hasApiKey === false" @click="handleSubmit">
            提交设计
          </AButton>
        </AFormItem>
      </AForm>
    </ACard>
  </div>
</template>
