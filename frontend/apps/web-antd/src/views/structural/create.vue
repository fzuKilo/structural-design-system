<script setup lang="ts">
import { reactive, ref } from 'vue';

import { Button as AButton, Card as ACard, Form as AForm, FormItem as AFormItem, message, Select as ASelect, SelectOption as ASelectOption, Textarea as ATextarea } from 'ant-design-vue';
import { useRouter } from 'vue-router';

import { createDesignApi } from '#/api/design';

const router = useRouter();
const submitting = ref(false);

const form = reactive({
  request_text: '',
  structure_type: undefined as string | undefined,
});

const handleSubmit = async () => {
  if (!form.request_text || !form.structure_type) {
    message.warning('请填写完整的设计信息');
    return;
  }
  submitting.value = true;
  try {
    await createDesignApi(form);
    message.success('设计任务提交成功');
    router.push('/structural');
  } catch {
    message.error('提交失败，请重试');
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

    <ACard>
      <AForm :model="form" layout="vertical">
        <AFormItem label="结构类型" required>
          <ASelect v-model:value="form.structure_type" placeholder="请选择结构类型">
            <ASelectOption value="beam">梁</ASelectOption>
            <ASelectOption value="cantilever_beam">悬臂梁</ASelectOption>
            <ASelectOption value="continuous_beam">连续梁</ASelectOption>
            <ASelectOption value="truss">桁架</ASelectOption>
            <ASelectOption value="frame">框架</ASelectOption>
          </ASelect>
        </AFormItem>
        <AFormItem label="设计描述" required>
          <ATextarea
            v-model:value="form.request_text"
            :rows="6"
            placeholder="请详细描述您的结构设计需求..."
          />
        </AFormItem>
        <AFormItem>
          <AButton type="primary" :loading="submitting" @click="handleSubmit">
            提交设计
          </AButton>
        </AFormItem>
      </AForm>
    </ACard>
  </div>
</template>
