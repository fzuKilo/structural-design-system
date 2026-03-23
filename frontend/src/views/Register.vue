<template>
  <div style="display: flex; justify-content: center; align-items: center; min-height: 100vh; background: #f0f2f5; padding: 16px;">
    <a-card title="用户注册" style="width: 100%; max-width: 400px;">
      <a-form :model="form" @finish="handleRegister">
        <a-form-item name="username" :rules="[{ required: true, message: '请输入用户名' }, { min: 3, message: '用户名至少3位' }]">
          <a-input v-model:value="form.username" placeholder="用户名（至少3位）" size="large" />
        </a-form-item>
        <a-form-item name="email" :rules="[{ required: true, type: 'email', message: '请输入有效邮箱' }]">
          <a-input v-model:value="form.email" placeholder="邮箱" size="large" />
        </a-form-item>
        <a-form-item name="password" :rules="[{ required: true, min: 6, message: '密码至少6位' }]">
          <a-input-password v-model:value="form.password" placeholder="密码" size="large" />
        </a-form-item>
        <a-form-item>
          <a-button type="primary" html-type="submit" block size="large" :loading="loading">
            注册
          </a-button>
        </a-form-item>
        <a-form-item>
          <router-link to="/login">已有账号？立即登录</router-link>
        </a-form-item>
      </a-form>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { authApi } from '@/api/auth'

const router = useRouter()
const loading = ref(false)
const form = ref({ username: '', email: '', password: '' })

const handleRegister = async () => {
  loading.value = true
  try {
    await authApi.register(form.value)
    message.success('注册成功，请登录')
    router.push('/login')
  } catch (error: any) {
    const detail = error.response?.data?.detail
    if (Array.isArray(detail)) {
      message.error(detail[0]?.msg || '注册失败')
    } else if (typeof detail === 'string') {
      message.error(detail)
    } else {
      message.error('注册失败')
    }
  } finally {
    loading.value = false
  }
}
</script>
