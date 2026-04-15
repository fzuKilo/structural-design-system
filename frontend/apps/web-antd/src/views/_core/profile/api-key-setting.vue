<script setup lang="ts">
import { ref } from 'vue';

import { Alert as AAlert, Button as AButton, Input as AInput, message } from 'ant-design-vue';

import { baseRequestClient } from '#/api/request';

const apiKey = ref('');
const showKey = ref(false);
const saving = ref(false);
const saved = ref(false);

const handleSave = async () => {
  if (!apiKey.value.trim()) {
    message.warning('请输入 API Key');
    return;
  }
  saving.value = true;
  saved.value = false;
  try {
    await baseRequestClient.put('/auth/profile', { api_key: apiKey.value });
    saved.value = true;
    message.success('API Key 已加密保存');
    apiKey.value = '';
  } catch {
    message.error('保存失败，请重试');
  } finally {
    saving.value = false;
  }
};
</script>

<template>
  <div class="max-w-lg p-4">
    <AAlert
      type="info"
      message="API Key 将使用 AES 加密存储，数据库中不保存明文。"
      class="mb-4"
      show-icon
    />
    <AAlert
      v-if="saved"
      type="success"
      message="API Key 已成功加密保存！"
      class="mb-4"
      show-icon
      closable
      @close="saved = false"
    />
    <div class="mb-3">
      <label class="mb-1 block text-sm font-medium">API Key</label>
      <AInput
        v-model:value="apiKey"
        :type="showKey ? 'text' : 'password'"
        placeholder="请输入您的 API Key（如 sk-...）"
        allow-clear
      />
    </div>
    <div class="flex gap-2">
      <AButton @click="showKey = !showKey">
        {{ showKey ? '隐藏' : '显示' }}
      </AButton>
      <AButton type="primary" :loading="saving" @click="handleSave">
        保存
      </AButton>
    </div>
  </div>
</template>
