<template>
  <a-card title="设计结果">
    <a-tabs v-model:activeKey="activeTab">

      <!-- 设计报告 -->
      <a-tab-pane key="report" tab="设计报告">
        <div v-if="reportContent">
          <MarkdownViewer :content="reportContent" />
        </div>
        <div v-else-if="loadingReport" style="text-align: center; padding: 40px;">
          <a-spin tip="加载报告中..." />
        </div>
        <a-empty v-else description="暂无报告" />
      </a-tab-pane>

      <!-- CAD 图纸 -->
      <a-tab-pane key="drawings" tab="CAD 图纸">
        <template v-if="drawings.length">
          <a-tabs type="card" size="small">
            <a-tab-pane
              v-for="d in drawings"
              :key="d.key"
              :tab="d.label"
            >
              <DXFViewer :src="d.path" :height="420" />
            </a-tab-pane>
          </a-tabs>
        </template>
        <a-empty v-else description="暂无图纸" />
      </a-tab-pane>

      <!-- 可视化图表 -->
      <a-tab-pane key="visualizations" tab="可视化">
        <template v-if="visualizations.length">
          <a-row :gutter="[16, 16]">
            <a-col
              v-for="v in visualizations"
              :key="v.key"
              :span="v.type === 'html' ? 24 : 12"
            >
              <a-card size="small" :title="v.label">
                <!-- 交互式 HTML (Plotly) -->
                <iframe
                  v-if="v.type === 'html'"
                  :src="`/api/file/download?path=${encodeURIComponent(v.path)}`"
                  style="width: 100%; height: 400px; border: none;"
                />
                <!-- 静态图片 -->
                <img
                  v-else
                  :src="`/api/file/download?path=${encodeURIComponent(v.path)}`"
                  style="width: 100%; border-radius: 4px;"
                  :alt="v.label"
                />
              </a-card>
            </a-col>
          </a-row>
        </template>
        <a-empty v-else description="暂无可视化图表" />
      </a-tab-pane>

      <!-- 设计评估 -->
      <a-tab-pane key="evaluation" tab="设计评估">
        <ChartViewer v-if="result?.evaluation" :evaluation="result.evaluation" />
        <a-empty v-else description="暂无评估数据" />
      </a-tab-pane>

      <!-- 下载 -->
      <a-tab-pane key="download" tab="下载文件">
        <a-list :dataSource="allFiles" :bordered="true">
          <template #renderItem="{ item }">
            <a-list-item>
              <a-list-item-meta
                :title="item.label"
                :description="item.path"
              >
                <template #avatar>
                  <a-avatar :style="{ background: item.color }">{{ item.icon }}</a-avatar>
                </template>
              </a-list-item-meta>
              <template #actions>
                <a
                  :href="`/api/file/download?path=${encodeURIComponent(item.path)}`"
                  target="_blank"
                >
                  下载
                </a>
              </template>
            </a-list-item>
          </template>
        </a-list>

        <div v-if="allFiles.length" style="margin-top: 16px; text-align: right;">
          <a-button
            type="primary"
            :href="`/api/file/package/${taskId}`"
            target="_blank"
          >
            打包下载全部 (ZIP)
          </a-button>
        </div>
        <a-empty v-if="!allFiles.length" description="暂无可下载文件" />
      </a-tab-pane>

      <!-- 原始数据 -->
      <a-tab-pane key="raw" tab="原始数据">
        <pre style="font-size: 12px; overflow: auto; max-height: 500px; background: #f5f5f5; padding: 12px; border-radius: 4px;">{{ JSON.stringify(result, null, 2) }}</pre>
      </a-tab-pane>

    </a-tabs>
  </a-card>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import axios from 'axios'
import MarkdownViewer from '@/components/visualization/MarkdownViewer.vue'
import DXFViewer from '@/components/visualization/DXFViewer.vue'
import ChartViewer from '@/components/visualization/ChartViewer.vue'

const props = defineProps<{
  result: any       // task.result_json
  taskId: string
}>()

const activeTab = ref('report')
const reportContent = ref('')
const loadingReport = ref(false)

// 图纸列表
const drawings = computed(() => {
  const files = props.result?.files || {}
  const labelMap: Record<string, string> = {
    plan_view: '平面图',
    elevation_view: '立面图',
    details: '详图'
  }
  return Object.entries(files)
    .filter(([, path]) => typeof path === 'string' && (path as string).endsWith('.dxf'))
    .map(([key, path]) => ({ key, label: labelMap[key] || key, path: path as string }))
})

// 可视化列表
const visualizations = computed(() => {
  const vis = props.result?.visualizations || {}
  const result: { key: string; label: string; path: string; type: 'html' | 'img' }[] = []

  const staticVis = vis.static || {}
  const labelMap: Record<string, string> = {
    displacement_contour: '位移云图',
    moment_contour: '弯矩云图',
    stress_contour: '应力云图',
    moment_diagram: '弯矩图'
  }
  for (const [key, path] of Object.entries(staticVis)) {
    if (typeof path === 'string') {
      result.push({ key, label: labelMap[key] || key, path, type: 'img' })
    }
  }

  const interactiveVis = vis.interactive || {}
  const iLabelMap: Record<string, string> = {
    displacement_html: '位移（交互式）',
    moment_html: '弯矩（交互式）',
    stress_html: '应力（交互式）'
  }
  for (const [key, path] of Object.entries(interactiveVis)) {
    if (typeof path === 'string') {
      result.push({ key, label: iLabelMap[key] || key, path, type: 'html' })
    }
  }

  return result
})

// 所有可下载文件
const allFiles = computed(() => {
  const files: { key: string; label: string; path: string; icon: string; color: string }[] = []

  if (props.result?.report_file) {
    files.push({ key: 'report', label: '设计报告 (Markdown)', path: props.result.report_file, icon: '报', color: '#1890ff' })
  }

  for (const d of drawings.value) {
    files.push({ key: d.key, label: `图纸 - ${d.label} (DXF)`, path: d.path, icon: '图', color: '#52c41a' })
  }

  for (const v of visualizations.value) {
    const ext = v.type === 'html' ? 'HTML' : 'PNG'
    files.push({ key: v.key, label: `${v.label} (${ext})`, path: v.path, icon: '图', color: '#722ed1' })
  }

  return files
})

// 加载报告内容
const loadReport = async () => {
  const path = props.result?.report_file
  if (!path) return
  loadingReport.value = true
  try {
    const token = localStorage.getItem('token')
    const res = await axios.get('/api/file/download', {
      params: { path },
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      responseType: 'text'
    })
    reportContent.value = res.data
  } catch {
    reportContent.value = ''
  } finally {
    loadingReport.value = false
  }
}

watch(() => props.result, (val) => {
  if (val?.report_file) loadReport()
}, { immediate: true })
</script>
