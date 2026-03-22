<template>
  <a-layout style="min-height: 100vh;">
    <a-layout-header style="background: #fff; padding: 0 24px; display: flex; align-items: center; gap: 16px;">
      <a-button @click="$router.push('/')">← 返回</a-button>
      <h2 style="margin: 0;">新建结构设计</h2>
    </a-layout-header>
    <a-layout-content style="padding: 24px; max-width: 800px; margin: 0 auto; width: 100%;">
      <a-card title="输入设计需求">
        <a-form :model="form" @finish="handleSubmit">
          <a-form-item
            name="request_text"
            :rules="[{ required: true, min: 10, message: '请输入至少10个字符的设计需求' }]"
          >
            <a-textarea
              v-model:value="form.request_text"
              :rows="6"
              placeholder="请用自然语言描述您的结构设计需求，例如：设计一个跨度6米的简支梁，承受均布荷载10kN/m，使用Q345钢材..."
              show-count
              :maxlength="5000"
            />
          </a-form-item>
          <a-form-item>
            <a-space>
              <a-button type="primary" html-type="submit" size="large" :loading="loading">
                开始设计
              </a-button>
              <a-button @click="$router.push('/')">取消</a-button>
            </a-space>
          </a-form-item>
        </a-form>

        <a-divider>示例需求</a-divider>
        <a-space wrap>
          <a-tag
            v-for="example in examples"
            :key="example"
            style="cursor: pointer; padding: 4px 8px;"
            @click="form.request_text = example"
          >
            {{ example }}
          </a-tag>
        </a-space>
      </a-card>
    </a-layout-content>
  </a-layout>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { designApi } from '@/api/design'

const router = useRouter()
const loading = ref(false)
const form = ref({ request_text: '' })

const examples = [
  '设计一个跨度6米的简支梁，均布荷载10kN/m，Q345钢材',
  '设计一个两跨连续梁，每跨8米，集中荷载50kN',
  '设计一个三层两跨钢框架，层高3.5米，跨度6米',
  '设计一个跨度12米的普拉特桁架，节点荷载20kN'
]

const handleSubmit = async () => {
  loading.value = true
  try {
    const task = await designApi.create({ request_text: form.value.request_text })
    message.success('任务创建成功，正在跳转...')
    router.push(`/design/${task.id}`)
  } catch (error: any) {
    message.error(error.response?.data?.detail || '创建失败')
  } finally {
    loading.value = false
  }
}
</script>
