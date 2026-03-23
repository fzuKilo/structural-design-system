<template>
  <a-layout style="min-height: 100vh;">
    <a-layout-header style="background: #fff; padding: 0 16px; display: flex; align-items: center; gap: 8px;">
      <a-button size="small" @click="$router.push('/')">← 返回</a-button>
      <h2 style="margin: 0; font-size: clamp(14px, 3.5vw, 18px);">用户设置</h2>
    </a-layout-header>

    <a-layout-content style="padding: 12px; max-width: 700px; margin: 0 auto; width: 100%;">
      <a-row :gutter="[0, 16]">

        <!-- 账户信息 -->
        <a-col :span="24">
          <a-card title="账户信息">
            <a-descriptions :column="1" bordered size="small">
              <a-descriptions-item label="用户名">{{ user?.username }}</a-descriptions-item>
              <a-descriptions-item label="邮箱">{{ user?.email }}</a-descriptions-item>
              <a-descriptions-item label="每日配额">{{ user?.quota_daily }} 次</a-descriptions-item>
              <a-descriptions-item label="每月配额">{{ user?.quota_monthly }} 次</a-descriptions-item>
              <a-descriptions-item label="注册时间">{{ formatDate(user?.created_at) }}</a-descriptions-item>
            </a-descriptions>
          </a-card>
        </a-col>

        <!-- API Key 管理 -->
        <a-col :span="24">
          <a-card title="LLM API Key">
            <a-alert
              type="info"
              show-icon
              style="margin-bottom: 16px;"
              message="API Key 用于调用 LLM 服务（DeepSeek/OpenAI/Claude），加密存储在服务器端。"
            />
            <a-form :model="apiKeyForm" @finish="handleSaveApiKey">
              <a-form-item
                name="api_key"
                label="API Key"
                :rules="[{ required: true, message: '请输入 API Key' }]"
              >
                <a-input-password
                  v-model:value="apiKeyForm.api_key"
                  placeholder="sk-... 或 your-api-key"
                  size="large"
                />
              </a-form-item>
              <a-form-item>
                <a-button type="primary" html-type="submit" :loading="savingKey">
                  保存 API Key
                </a-button>
              </a-form-item>
            </a-form>
          </a-card>
        </a-col>

        <!-- 危险操作 -->
        <a-col :span="24">
          <a-card title="账户操作">
            <a-space>
              <a-button danger @click="handleLogout">退出登录</a-button>
            </a-space>
          </a-card>
        </a-col>

      </a-row>
    </a-layout-content>
  </a-layout>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { useAuthStore } from '@/stores/auth'
import { authApi } from '@/api/auth'

const router = useRouter()
const authStore = useAuthStore()
const user = ref(authStore.user)
const savingKey = ref(false)
const apiKeyForm = ref({ api_key: '' })

const formatDate = (dateStr?: string) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString('zh-CN', {
    year: 'numeric', month: 'long', day: 'numeric'
  })
}

const handleSaveApiKey = async () => {
  savingKey.value = true
  try {
    await authApi.updateProfile({ api_key: apiKeyForm.value.api_key })
    message.success('API Key 已保存')
    apiKeyForm.value.api_key = ''
  } catch {
    message.error('保存失败，请重试')
  } finally {
    savingKey.value = false
  }
}

const handleLogout = () => {
  authStore.logout()
  router.push('/login')
}

onMounted(async () => {
  if (!authStore.user) {
    await authStore.fetchProfile()
    user.value = authStore.user
  }
})
</script>
