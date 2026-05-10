<template>
  <div>
    <div v-if="!src" style="text-align: center; padding: 40px; color: #999;">
      暂无图纸文件
    </div>
    <template v-else>
      <!-- 工具栏 -->
      <div style="margin-bottom: 12px; display: flex; gap: 8px; align-items: center;">
        <a-button size="small" @click="zoom(1.2)">放大</a-button>
        <a-button size="small" @click="zoom(0.8)">缩小</a-button>
        <a-button size="small" @click="resetView">重置</a-button>
        <a-button size="small" type="link" :href="downloadUrl" target="_blank">下载 DXF</a-button>
      </div>

      <!-- SVG/PNG 渲染区 -->
      <div
        ref="containerRef"
        style="border: 1px solid #d9d9d9; border-radius: 4px; overflow: hidden; background: #1a1a2e; cursor: grab; position: relative;"
        :style="{ height: height + 'px' }"
        @mousedown="onMouseDown"
        @mousemove="onMouseMove"
        @mouseup="onMouseUp"
        @wheel.prevent="onWheel"
      >
        <div
          :style="{
            transform: `translate(${pan.x}px, ${pan.y}px) scale(${scale})`,
            transformOrigin: '0 0',
            position: 'absolute',
            width: '100%',
            height: '100%'
          }"
        >
          <div v-if="loading" style="display: flex; justify-content: center; align-items: center; height: 100%; color: #fff;">
            <a-spin tip="加载图纸中..." />
          </div>
          <img
            v-else-if="props.preview"
            :src="`/api/file/view?path=${encodeURIComponent(props.preview)}`"
            style="width: 100%; height: 100%; object-fit: contain; mix-blend-mode: lighten;"
            alt="CAD预览图"
          />
          <div v-else style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 100%; color: #999;">
            <div style="font-size: 48px; margin-bottom: 16px;">📐</div>
            <div style="font-size: 16px; margin-bottom: 8px;">CAD 图纸已生成</div>
            <div style="font-size: 14px;">请点击上方"下载 DXF"按钮下载后在 AutoCAD 中查看</div>
          </div>
        </div>
      </div>

      <!-- 提示 -->
      <div style="margin-top: 4px; font-size: 12px; color: #999;">
        滚轮缩放 · 拖拽平移
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { Button as AButton, Spin as ASpin } from 'ant-design-vue'
import { useAccessStore } from '@vben/stores'
import axios from 'axios'

const props = defineProps<{
  src: string        // 后端文件路径
  preview?: string   // PNG预览图路径
  height?: number
}>()

const height = props.height ?? 400
const accessStore = useAccessStore()
const svgContent = ref('')
const loading = ref(false)
const error = ref('')
const scale = ref(1)
const pan = ref({ x: 0, y: 0 })
const dragging = ref(false)
const dragStart = ref({ x: 0, y: 0 })
const containerRef = ref<HTMLElement | null>(null)

const downloadUrl = computed(() => {
  const token = accessStore.accessToken
  return `/api/file/download?path=${encodeURIComponent(props.src)}&token=${token}`
})

const loadDxf = async () => {
  if (!props.src) return

  // 如果有 PNG 预览，跳过 SVG 加载
  if (props.preview) {
    loading.value = false
    return
  }

  loading.value = true
  error.value = ''
  svgContent.value = ''
  try {
    const token = accessStore.accessToken
    const res = await axios.get('/api/file/preview', {
      params: { path: props.src },
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      responseType: 'text'
    })
    svgContent.value = res.data
  } catch {
    error.value = '图纸加载失败，请下载后在本地查看'
  } finally {
    loading.value = false
  }
}

const zoom = (factor: number) => {
  scale.value = Math.min(Math.max(scale.value * factor, 0.1), 10)
}

const resetView = () => {
  scale.value = 1
  pan.value = { x: 0, y: 0 }
}

const onWheel = (e: WheelEvent) => {
  zoom(e.deltaY < 0 ? 1.1 : 0.9)
}

const onMouseDown = (e: MouseEvent) => {
  dragging.value = true
  dragStart.value = { x: e.clientX - pan.value.x, y: e.clientY - pan.value.y }
}

const onMouseMove = (e: MouseEvent) => {
  if (!dragging.value) return
  pan.value = { x: e.clientX - dragStart.value.x, y: e.clientY - dragStart.value.y }
}

const onMouseUp = () => { dragging.value = false }

watch(() => props.src, loadDxf, { immediate: true })
</script>
