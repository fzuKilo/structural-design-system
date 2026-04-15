<script setup lang="ts">
import { onMounted, ref } from 'vue';

import { Alert as AAlert, Card as ACard, Progress as AProgress, Statistic as AStatistic } from 'ant-design-vue';

import { baseRequestClient } from '#/api/request';

const profile = ref<any>(null);
const loading = ref(true);

onMounted(async () => {
  try {
    const res = await baseRequestClient.get('/auth/profile');
    profile.value = (res as any)?.data ?? res;
  } finally {
    loading.value = false;
  }
});

const dailyPercent = (v: number) => Math.round((v / 100) * 100);
const monthlyPercent = (v: number) => Math.round((v / 1000) * 100);
</script>

<template>
  <div class="max-w-lg p-4">
    <template v-if="profile">
      <AAlert
        v-if="profile.quota_daily <= 10"
        type="warning"
        message="今日配额即将耗尽，请联系管理员增加配额"
        class="mb-4"
        show-icon
      />
      <ACard size="small" class="mb-3" title="今日配额">
        <AStatistic :value="profile.quota_daily" suffix="/ 100" />
        <AProgress :percent="dailyPercent(profile.quota_daily)" :status="profile.quota_daily <= 10 ? 'exception' : 'normal'" />
      </ACard>
      <ACard size="small" title="本月配额">
        <AStatistic :value="profile.quota_monthly" suffix="/ 1000" />
        <AProgress :percent="monthlyPercent(profile.quota_monthly)" :status="profile.quota_monthly <= 50 ? 'exception' : 'normal'" />
      </ACard>
    </template>
    <div v-else-if="loading" class="text-gray-400">加载中...</div>
  </div>
</template>
