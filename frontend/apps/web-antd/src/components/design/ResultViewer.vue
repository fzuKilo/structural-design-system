<template>
  <ACard title="设计结果">
    <ATabs v-model:activeKey="activeTab">

      <ATabPane key="report" tab="设计报告">
        <div v-if="loadingReport" style="text-align: center; padding: 40px;">
          <ASpin tip="加载报告中..." />
        </div>
        <MarkdownViewer v-else-if="reportContent" :content="reportContent" />
        <AEmpty v-else description="暂无报告" />
      </ATabPane>

      <ATabPane key="drawings" tab="CAD 图纸">
        <template v-if="drawings.length">
          <ATabs type="card" size="small">
            <ATabPane v-for="d in drawings" :key="d.key" :tab="d.label">
              <DXFViewer :src="d.path" :height="420" />
            </ATabPane>
          </ATabs>
        </template>
        <AEmpty v-else description="暂无图纸" />
      </ATabPane>

      <ATabPane key="visualizations" tab="可视化">
        <template v-if="visualizations.length">
          <ARow :gutter="[16, 16]">
            <ACol v-for="v in visualizations" :key="v.key" :span="v.type === 'html' ? 24 : 12">
              <ACard size="small" :title="v.label">
                <iframe
                  v-if="v.type === 'html'"
                  :src="`/api/file/view?path=${encodeURIComponent(v.path)}`"
                  style="width: 100%; height: 400px; border: none;"
                />
                <img
                  v-else
                  :src="`/api/file/view?path=${encodeURIComponent(v.path)}`"
                  style="width: 100%; border-radius: 4px;"
                  :alt="v.label"
                />
              </ACard>
            </ACol>
          </ARow>
        </template>
        <AEmpty v-else description="暂无可视化图表" />
      </ATabPane>

      <ATabPane key="evaluation" tab="设计评估">
        <ChartViewer v-if="result?.evaluation" :evaluation="result.evaluation" />
        <AEmpty v-else description="暂无评估数据" />
      </ATabPane>

      <ATabPane key="3d-model" tab="3D模型">
        <div v-if="result?.bim_url && result.bim_url.startsWith('http')">
          <AResult status="success" title="3D 模型已生成" sub-title="点击下方按钮在新窗口中查看 Speckle 3D 模型">
            <template #extra>
              <AButton type="primary" size="large" :href="result.bim_url" target="_blank">
                在新窗口查看 3D 模型
              </AButton>
            </template>
          </AResult>
        </div>
        <AEmpty v-else description="暂无3D模型" />
      </ATabPane>

      <ATabPane key="download" tab="下载文件">
        <AList :data-source="allFiles" :bordered="true">
          <template #renderItem="{ item }">
            <AListItem>
              <AListItemMeta :title="item.label" :description="item.path">
                <template #avatar>
                  <AAvatar :style="{ background: item.color }">{{ item.icon }}</AAvatar>
                </template>
              </AListItemMeta>
              <template #actions>
                <a :href="`/api/file/download?path=${encodeURIComponent(item.path)}`" target="_blank">下载</a>
              </template>
            </AListItem>
          </template>
        </AList>
        <div v-if="allFiles.length" style="margin-top: 16px; text-align: right;">
          <AButton type="primary" @click="downloadPackage">打包下载全部 (ZIP)</AButton>
        </div>
        <AEmpty v-if="!allFiles.length" description="暂无可下载文件" />
      </ATabPane>

      <ATabPane key="raw" tab="原始数据">
        <pre style="font-size: 12px; overflow: auto; max-height: 500px; background: #f5f5f5; padding: 12px; border-radius: 4px;">{{ JSON.stringify(result, null, 2) }}</pre>
      </ATabPane>

    </ATabs>
  </ACard>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue';

import {
  Avatar as AAvatar,
  Button as AButton,
  Card as ACard,
  Col as ACol,
  Empty as AEmpty,
  List as AList,
  ListItem as AListItem,
  ListItemMeta as AListItemMeta,
  Result as AResult,
  Row as ARow,
  Spin as ASpin,
  Tabs as ATabs,
  TabPane as ATabPane,
} from 'ant-design-vue';
import axios from 'axios';

import { useAccessStore } from '@vben/stores';

import ChartViewer from '#/components/visualization/ChartViewer.vue';
import DXFViewer from '#/components/visualization/DXFViewer.vue';
import MarkdownViewer from '#/components/visualization/MarkdownViewer.vue';

const props = defineProps<{ result: any; taskId: string }>();

const accessStore = useAccessStore();
const activeTab = ref('report');
const reportContent = ref('');
const loadingReport = ref(false);

const drawings = computed(() => {
  const files = props.result?.files || {};
  const labelMap: Record<string, string> = {
    plan_view: '平面图', elevation_view: '立面图', details: '详图',
  };
  return Object.entries(files)
    .filter(([, path]) => typeof path === 'string' && (path as string).endsWith('.dxf'))
    .map(([key, path]) => ({ key, label: labelMap[key] || key, path: path as string }));
});

const visualizations = computed(() => {
  const vis = props.result?.visualizations || {};
  const result: { key: string; label: string; path: string; type: 'html' | 'img' }[] = [];
  const labelMap: Record<string, string> = {
    displacement_contour: '位移云图', moment_contour: '弯矩云图',
    stress_contour: '应力云图', moment_diagram: '弯矩图',
  };
  for (const [key, path] of Object.entries(vis.static || {})) {
    if (typeof path === 'string') result.push({ key, label: labelMap[key] || key, path, type: 'img' });
  }
  const iLabelMap: Record<string, string> = {
    displacement_html: '位移（交互式）', moment_html: '弯矩（交互式）', stress_html: '应力（交互式）',
  };
  for (const [key, path] of Object.entries(vis.interactive || {})) {
    if (typeof path === 'string') result.push({ key, label: iLabelMap[key] || key, path, type: 'html' });
  }
  return result;
});

const allFiles = computed(() => {
  const files: any[] = [];
  if (props.result?.report_file) {
    files.push({ key: 'report', label: '设计报告 (Markdown)', path: props.result.report_file, icon: '报', color: '#1890ff' });
  }
  for (const d of drawings.value) {
    files.push({ key: d.key, label: `图纸 - ${d.label} (DXF)`, path: d.path, icon: '图', color: '#52c41a' });
  }
  for (const v of visualizations.value) {
    files.push({ key: v.key, label: v.label, path: v.path, icon: '图', color: '#722ed1' });
  }
  if (props.result?.ifc_path) {
    files.push({ key: 'ifc', label: 'BIM模型 (IFC)', path: props.result.ifc_path, icon: 'B', color: '#fa8c16' });
  }
  return files;
});

const loadReport = async () => {
  const path = props.result?.report_file;
  if (!path) return;
  loadingReport.value = true;
  try {
    const res = await axios.get('/api/file/download', {
      params: { path },
      headers: { Authorization: `Bearer ${accessStore.accessToken}` },
      responseType: 'text',
    });
    reportContent.value = res.data;
  } catch {
    reportContent.value = '';
  } finally {
    loadingReport.value = false;
  }
};

const downloadPackage = () => {
  window.open(`/api/file/package/${props.taskId}?token=${accessStore.accessToken}`, '_blank');
};

watch(() => props.result, (val) => { if (val?.report_file) loadReport(); }, { immediate: true });
</script>
