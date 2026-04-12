<template>
  <div>
    <!-- 顶部：综合评分和雷达图 -->
    <ARow :gutter="24" style="margin-bottom: 24px;">
      <!-- 左侧：雷达图 -->
      <ACol :xs="24" :lg="14">
        <ACard size="small" title="四维评估雷达图">
          <div ref="chartRef" style="width: 100%; height: 400px;"></div>
        </ACard>
      </ACol>

      <!-- 右侧：综合评分 -->
      <ACol :xs="24" :lg="10">
        <ACard size="small" title="综合评估">
          <div style="text-align: center; padding: 40px 0;">
            <AStatistic
              title="综合评分"
              :value="evaluation.comprehensive_score"
              :precision="1"
              suffix="/ 100"
              :value-style="{ color: getScoreColor(evaluation.comprehensive_score), fontSize: '48px' }"
            />
            <div style="margin-top: 24px;">
              <ATag :color="gradeColor" style="font-size: 24px; padding: 8px 24px;">
                等级: {{ evaluation.grade }}
              </ATag>
            </div>
          </div>
        </ACard>
      </ACol>
    </ARow>

    <!-- 中部：详细指标手风琴 -->
    <ACard size="small" title="详细指标" style="margin-bottom: 24px;">
      <ACollapse v-model:activeKey="activeKeys" :bordered="false">
        <ACollapsePanel
          v-for="dim in dimensionDetails"
          :key="dim.key"
          :header="dim.header"
        >
          <template #extra>
            <ATag :color="getScoreTagColor(dim.score)">{{ dim.score.toFixed(1) }} 分</ATag>
          </template>
          <ADescriptions :column="2" size="small" bordered>
            <ADescriptionsItem
              v-for="indicator in dim.indicators"
              :key="indicator.key"
              :label="indicator.label"
            >
              {{ indicator.value }}
            </ADescriptionsItem>
          </ADescriptions>
        </ACollapsePanel>
      </ACollapse>
    </ACard>

    <!-- 底部：改进建议 -->
    <ACard v-if="recommendations.length" size="small" title="改进建议">
      <AList :data-source="recommendations" size="small">
        <template #renderItem="{ item, index }">
          <AListItem>
            <AListItemMeta>
              <template #avatar>
                <AAvatar :style="{ backgroundColor: '#1890ff' }">{{ index + 1 }}</AAvatar>
              </template>
              <template #title>
                <span style="font-size: 14px;">{{ item }}</span>
              </template>
            </AListItemMeta>
          </AListItem>
        </template>
      </AList>
    </ACard>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue';

import {
  Avatar as AAvatar,
  Card as ACard,
  Col as ACol,
  Collapse as ACollapse,
  CollapsePanel as ACollapsePanel,
  Descriptions as ADescriptions,
  DescriptionsItem as ADescriptionsItem,
  List as AList,
  ListItem as AListItem,
  ListItemMeta as AListItemMeta,
  Row as ARow,
  Statistic as AStatistic,
  Tag as ATag,
} from 'ant-design-vue';
import * as echarts from 'echarts';

const props = defineProps<{ evaluation: any }>();

const chartRef = ref<HTMLElement | null>(null);
const activeKeys = ref<string[]>(['economy']); // 默认展开第一个
let chartInstance: echarts.ECharts | null = null;

// 维度标签映射
const dimensionLabels: Record<string, string> = {
  economy: '经济性',
  structural_efficiency: '结构效率',
  safety: '安全性',
  sustainability: '可持续性',
};

// 雷达图数据
const radarData = computed(() => {
  const dims = props.evaluation?.dimensions || {};
  return [
    { name: '经济性', value: dims.economy?.score || 0 },
    { name: '结构效率', value: dims.structural_efficiency?.score || 0 },
    { name: '安全性', value: dims.safety?.score || 0 },
    { name: '可持续性', value: dims.sustainability?.score || 0 },
  ];
});

// 详细指标数据
const dimensionDetails = computed(() => {
  const dims = props.evaluation?.dimensions || {};
  const result: any[] = [];

  // 经济性
  if (dims.economy) {
    result.push({
      key: 'economy',
      header: '💰 经济性',
      score: dims.economy.score,
      indicators: [
        { key: 'comprehensive_utilization', label: '综合利用率', value: `${(dims.economy.indicators.comprehensive_utilization * 100).toFixed(2)}%` },
        { key: 'stress_utilization', label: '应力利用率', value: `${(dims.economy.indicators.stress_utilization * 100).toFixed(2)}%` },
        { key: 'deflection_utilization', label: '挠度利用率', value: `${(dims.economy.indicators.deflection_utilization * 100).toFixed(2)}%` },
        { key: 'material_usage_index', label: '材料用量指数', value: dims.economy.indicators.material_usage_index.toFixed(2) },
        { key: 'volume_m3', label: '材料体积', value: `${dims.economy.indicators.volume_m3.toFixed(2)} m³` },
        { key: 'construction_complexity', label: '施工复杂度', value: dims.economy.indicators.construction_complexity },
      ],
    });
  }

  // 结构效率
  if (dims.structural_efficiency) {
    result.push({
      key: 'structural_efficiency',
      header: '⚙️ 结构效率',
      score: dims.structural_efficiency.score,
      indicators: [
        { key: 'average_utilization', label: '平均利用率', value: `${(dims.structural_efficiency.indicators.average_utilization * 100).toFixed(2)}%` },
        { key: 'utilization_uniformity', label: '利用率均匀性', value: dims.structural_efficiency.indicators.utilization_uniformity.toFixed(2) },
      ],
    });
  }

  // 安全性
  if (dims.safety) {
    result.push({
      key: 'safety',
      header: '🛡️ 安全性',
      score: dims.safety.score,
      indicators: [
        { key: 'strength_score', label: '强度得分', value: dims.safety.indicators.strength_score.toFixed(1) },
        { key: 'stiffness_score', label: '刚度得分', value: dims.safety.indicators.stiffness_score.toFixed(1) },
        { key: 'construction_score', label: '施工得分', value: dims.safety.indicators.construction_score.toFixed(1) },
        { key: 'min_safety_factor', label: '最小安全系数', value: dims.safety.indicators.min_safety_factor.toFixed(2) },
        { key: 'stress_utilization', label: '应力利用率', value: `${(dims.safety.indicators.stress_utilization * 100).toFixed(2)}%` },
        { key: 'deflection_utilization', label: '挠度利用率', value: `${(dims.safety.indicators.deflection_utilization * 100).toFixed(2)}%` },
      ],
    });
  }

  // 可持续性
  if (dims.sustainability) {
    result.push({
      key: 'sustainability',
      header: '🌱 可持续性',
      score: dims.sustainability.score,
      indicators: [
        { key: 'carbon_emission_kg', label: '碳排放量', value: `${dims.sustainability.indicators.carbon_emission_kg.toFixed(1)} kg` },
        { key: 'carbon_intensity', label: '碳排放强度', value: dims.sustainability.indicators.carbon_intensity.toFixed(2) },
        { key: 'M_u_kNm', label: '抗弯承载力', value: `${dims.sustainability.indicators.M_u_kNm.toFixed(1)} kN·m` },
        { key: 'recyclability_ratio', label: '可回收率', value: `${(dims.sustainability.indicators.recyclability_ratio * 100).toFixed(0)}%` },
      ],
    });
  }

  return result;
});

// 改进建议
const recommendations = computed(() => {
  return props.evaluation?.recommendations || [];
});

// 等级颜色
const gradeColor = computed(() => {
  const g = props.evaluation?.grade;
  if (g?.startsWith('A')) return 'green';
  if (g?.startsWith('B')) return 'blue';
  if (g?.startsWith('C')) return 'orange';
  return 'red';
});

// 分数颜色
const getScoreColor = (score: number) => {
  if (score >= 80) return '#52c41a';
  if (score >= 60) return '#1890ff';
  if (score >= 40) return '#faad14';
  return '#ff4d4f';
};

const getScoreTagColor = (score: number) => {
  if (score >= 80) return 'green';
  if (score >= 60) return 'blue';
  if (score >= 40) return 'orange';
  return 'red';
};

// 初始化雷达图
const initChart = () => {
  if (!chartRef.value) {
    console.warn('ChartViewer: chartRef is null, skipping initialization');
    return;
  }

  if (chartInstance) {
    chartInstance.dispose();
  }

  try {
    chartInstance = echarts.init(chartRef.value);

    const option = {
      tooltip: {
        trigger: 'item',
      },
      radar: {
        indicator: [
          { name: '经济性', max: 100 },
          { name: '结构效率', max: 100 },
          { name: '安全性', max: 100 },
          { name: '可持续性', max: 100 },
        ],
        radius: '65%',
        splitNumber: 4,
        name: {
          textStyle: {
            fontSize: 14,
            color: '#333',
          },
        },
        splitArea: {
          areaStyle: {
            color: ['rgba(24, 144, 255, 0.05)', 'rgba(24, 144, 255, 0.1)', 'rgba(24, 144, 255, 0.15)', 'rgba(24, 144, 255, 0.2)'],
          },
        },
        axisLine: {
          lineStyle: {
            color: 'rgba(24, 144, 255, 0.3)',
          },
        },
        splitLine: {
          lineStyle: {
            color: 'rgba(24, 144, 255, 0.3)',
          },
        },
      },
      series: [
        {
          type: 'radar',
          data: [
            {
              value: radarData.value.map(d => d.value),
              name: '评估结果',
              areaStyle: {
                color: 'rgba(24, 144, 255, 0.3)',
              },
              lineStyle: {
                color: '#1890ff',
                width: 2,
              },
              itemStyle: {
                color: '#1890ff',
              },
            },
          ],
        },
      ],
    };

    chartInstance.setOption(option);
  } catch (error) {
    console.error('ChartViewer: Failed to initialize chart', error);
  }
};

// 更新图表
const updateChart = () => {
  if (!chartInstance) return;

  chartInstance.setOption({
    series: [
      {
        data: [
          {
            value: radarData.value.map(d => d.value),
          },
        ],
      },
    ],
  });
};

onMounted(async () => {
  await nextTick();
  initChart();

  const handleResize = () => chartInstance?.resize();
  window.addEventListener('resize', handleResize);

  // Cleanup on unmount
  onUnmounted(() => {
    window.removeEventListener('resize', handleResize);
    chartInstance?.dispose();
  });
});

watch(() => props.evaluation, async () => {
  await nextTick();
  if (!chartInstance) {
    initChart();
  } else {
    updateChart();
  }
}, { deep: true });
</script>
