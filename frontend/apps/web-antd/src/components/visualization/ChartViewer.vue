<template>
  <div>
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

    <a-table
      :columns="columns"
      :data-source="dimensions"
      :pagination="false"
      size="small"
      row-key="name"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'score'">
          <a-progress :percent="record.score" :stroke-color="getColor(record.score)" size="small" />
        </template>
      </template>
    </a-table>

    <div v-if="evaluation.suggestions?.length" style="margin-top: 16px;">
      <h4>改进建议</h4>
      <a-list :data-source="evaluation.suggestions" size="small">
        <template #renderItem="{ item }">
          <a-list-item>{{ item }}</a-list-item>
        </template>
      </a-list>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';

const props = defineProps<{ evaluation: any }>();

const columns = [
  { title: '评估维度', dataIndex: 'name', key: 'name' },
  { title: '得分', key: 'score' },
];

const dimensions = computed(() => {
  const scores = props.evaluation?.dimension_scores || {};
  const labelMap: Record<string, string> = {
    structural_safety: '结构安全',
    economic_efficiency: '经济效率',
    constructability: '施工可行性',
    code_compliance: '规范符合性',
  };
  return Object.entries(scores).map(([key, val]) => ({
    name: labelMap[key] || key,
    score: Number(val),
  }));
});

const gradeColor = computed(() => {
  const g = props.evaluation?.grade;
  return g === 'A' ? 'green' : g === 'B' ? 'blue' : g === 'C' ? 'orange' : 'red';
});

const getColor = (score: number) => score >= 80 ? '#52c41a' : score >= 60 ? '#1890ff' : '#ff4d4f';
</script>
