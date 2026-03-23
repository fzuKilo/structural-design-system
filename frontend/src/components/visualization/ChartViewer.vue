<template>
  <div>
    <!-- 综合评分 -->
    <div style="text-align: center; margin-bottom: 24px;">
      <a-statistic
        title="综合评分"
        :value="evaluation.comprehensive_score"
        :precision="1"
        suffix="/ 100"
        style="display: inline-block; margin-right: 32px;"
      />
      <a-tag :color="gradeColor" style="font-size: 18px; padding: 4px 16px;">
        {{ evaluation.grade }}
      </a-tag>
    </div>

    <!-- 雷达图 -->
    <div ref="chartRef" style="width: 100%; height: 320px;" />

    <!-- 维度明细 -->
    <a-row :gutter="[12, 12]" style="margin-top: 16px;">
      <a-col :span="12" v-for="(dim, key) in evaluation.dimensions" :key="key">
        <a-card size="small" :title="dimensionLabels[key] || key">
          <a-progress
            :percent="dim.score"
            :stroke-color="getProgressColor(dim.score)"
            :format="(p: number) => `${p.toFixed(1)}分`"
          />
          <div style="margin-top: 8px; font-size: 12px; color: #666;">
            <div v-for="(val, k) in dim.indicators" :key="k">
              {{ indicatorLabels[k] || k }}: {{ formatValue(val) }}
            </div>
          </div>
        </a-card>
      </a-col>
    </a-row>

    <!-- 改进建议 -->
    <template v-if="evaluation.recommendations?.length">
      <a-divider>改进建议</a-divider>
      <a-list size="small" :dataSource="evaluation.recommendations">
        <template #renderItem="{ item }">
          <a-list-item>
            <a-typography-text type="warning">⚠ {{ item }}</a-typography-text>
          </a-list-item>
        </template>
      </a-list>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps<{ evaluation: any }>()

const chartRef = ref<HTMLElement | null>(null)
let chart: echarts.ECharts | null = null

const dimensionLabels: Record<string, string> = {
  economy: '经济性',
  structural_efficiency: '结构效率',
  safety: '安全性',
  sustainability: '可持续性'
}

const indicatorLabels: Record<string, string> = {
  material_usage_index: '材料用量指数',
  cost_efficiency_ratio: '造价效率比',
  avg_utilization: '平均利用率',
  utilization_uniformity: '利用率均匀性',
  min_safety_factor: '最小安全系数',
  deflection_margin: '挠度裕度',
  carbon_intensity: '碳排放强度',
  recyclability: '可回收率'
}

const gradeColor = (() => {
  const g = props.evaluation?.grade || ''
  if (g.startsWith('A')) return 'green'
  if (g.startsWith('B')) return 'blue'
  if (g.startsWith('C')) return 'orange'
  return 'red'
})()

const getProgressColor = (score: number) => {
  if (score >= 80) return '#52c41a'
  if (score >= 60) return '#1890ff'
  if (score >= 40) return '#faad14'
  return '#f5222d'
}

const formatValue = (val: any) => {
  if (typeof val === 'number') return val.toFixed(2)
  return val
}

const initChart = () => {
  if (!chartRef.value || !props.evaluation?.dimensions) return
  chart = echarts.init(chartRef.value)

  const dims = props.evaluation.dimensions
  const indicators = Object.keys(dims).map(k => ({
    name: dimensionLabels[k] || k,
    max: 100
  }))
  const values = Object.values(dims).map((d: any) => d.score)

  chart.setOption({
    radar: {
      indicator: indicators,
      radius: '65%'
    },
    series: [{
      type: 'radar',
      data: [{
        value: values,
        name: '评估得分',
        areaStyle: { opacity: 0.2 },
        lineStyle: { color: '#1890ff' },
        itemStyle: { color: '#1890ff' }
      }]
    }],
    tooltip: { trigger: 'item' }
  })
}

onMounted(initChart)
watch(() => props.evaluation, initChart, { deep: true })
</script>
