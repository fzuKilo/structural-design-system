<script lang="ts" setup>
import { Page } from '@vben/common-ui';

defineOptions({ name: 'About' });

const backendTechs = ['Python 3.12', 'OpenManus', 'OpenSeesPy', 'ezdxf', 'FastAPI', 'Celery', 'Redis', 'PostgreSQL'];
const frontendTechs = ['Vue 3', 'TypeScript', 'Ant Design Vue', 'Vite', 'TailwindCSS', 'Pinia', 'Vue Router', 'marked', 'ECharts', 'VueUse', 'Day.js'];
</script>

<template>
  <Page title="关于系统">
    <template #description>
      <p class="mt-3 text-sm/6 text-foreground">
        <strong>OpenManus 结构设计系统</strong>
        是一个基于 OpenManus 框架构建的 AI 驱动土木工程结构设计平台。
      </p>
      <p class="mt-2 text-sm/6 text-foreground">
        传统结构设计需要工程师手动建模、反复调参、逐条查阅规范——本系统将这一流程全面自动化。用户只需用自然语言描述设计需求（如"设计一个跨度12米、承受均布荷载的简支梁"），系统便会通过多轮智能交互收集完整参数，自动完成结构方案生成、有限元建模与分析、规范合规性校核、多维度质量评估、CAD 图纸绘制，直至输出完整设计报告，全程无需手动建模。
      </p>
      <p class="mt-2 text-sm/6 text-foreground">
        系统内置自动迭代优化机制：当结构不满足规范要求时，LLM 可自动生成改进方案并重新分析，最多迭代10轮直至合规；评估阶段支持多方案并行生成，自动择优。每个关键节点均提供人机交互确认，工程师可随时介入调整，兼顾自动化效率与专业判断。
      </p>
    </template>

    <!-- 核心功能 -->
    <div class="card-box p-5">
      <h5 class="text-lg font-medium text-foreground">核心功能</h5>
      <div class="mt-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div class="border border-border rounded-lg p-4">
          <dt class="text-sm font-medium text-foreground flex items-center gap-2">
            <span class="text-blue-500">①</span> 设计方案生成
          </dt>
          <dd class="mt-2 text-sm text-foreground/70">
            LLM 理解自然语言需求，通过多轮交互收集完整参数，自动生成结构方案，支持桁架、框架、梁等多种结构类型。
          </dd>
        </div>
        <div class="border border-border rounded-lg p-4">
          <dt class="text-sm font-medium text-foreground flex items-center gap-2">
            <span class="text-blue-500">②</span> 有限元分析
          </dt>
          <dd class="mt-2 text-sm text-foreground/70">
            OpenSeesPy 自动建模计算，输出应力、位移等关键指标，规范合规性校核，不合规时自动迭代优化，最多10轮直至合规。
          </dd>
        </div>
        <div class="border border-border rounded-lg p-4">
          <dt class="text-sm font-medium text-foreground flex items-center gap-2">
            <span class="text-blue-500">③</span> 设计评估
          </dt>
          <dd class="mt-2 text-sm text-foreground/70">
            安全性、经济性、适用性、综合性四维度量化评分，预警提示，支持多方案并行生成自动择优。
          </dd>
        </div>
        <div class="border border-border rounded-lg p-4">
          <dt class="text-sm font-medium text-foreground flex items-center gap-2">
            <span class="text-blue-500">④</span> CAD 出图
          </dt>
          <dd class="mt-2 text-sm text-foreground/70">
            基于 ezdxf 自动生成标准 CAD 图纸，支持直接下载，无需手动绘图。
          </dd>
        </div>
        <div class="border border-border rounded-lg p-4">
          <dt class="text-sm font-medium text-foreground flex items-center gap-2">
            <span class="text-blue-500">⑤</span> 报告生成
          </dt>
          <dd class="mt-2 text-sm text-foreground/70">
            汇总设计参数、分析结果、评估得分，自动生成完整设计报告，一键导出。
          </dd>
        </div>
        <div class="border border-border rounded-lg p-4">
          <dt class="text-sm font-medium text-foreground flex items-center gap-2">
            <span class="text-blue-500">⑥</span> 人机协同
          </dt>
          <dd class="mt-2 text-sm text-foreground/70">
            每个关键节点均支持工程师介入确认，可随时调整方案或终止流程，兼顾自动化效率与专业判断。
          </dd>
        </div>
      </div>
    </div>

    <!-- 支持的结构类型 -->
    <div class="card-box mt-6 p-5">
      <h5 class="text-lg font-medium text-foreground">支持的结构类型</h5>
      <div class="mt-4 flex flex-wrap gap-3">
        <span v-for="s in ['桁架', '框架', '简支梁', '悬臂梁', '连续梁']" :key="s"
          class="px-4 py-2 bg-blue-50 text-blue-700 rounded-full text-sm border border-blue-200">
          {{ s }}
        </span>
      </div>
    </div>

    <!-- 技术栈 -->
    <div class="card-box mt-6 p-5">
      <h5 class="text-lg font-medium text-foreground">技术栈</h5>
      <div class="mt-4 grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <p class="text-sm font-medium text-foreground mb-3">后端</p>
          <div class="flex flex-wrap gap-2">
            <span v-for="tech in backendTechs" :key="tech"
              class="px-3 py-1 bg-gray-100 text-gray-700 rounded text-xs">{{ tech }}</span>
          </div>
        </div>
        <div>
          <p class="text-sm font-medium text-foreground mb-3">前端</p>
          <div class="flex flex-wrap gap-2">
            <span v-for="tech in frontendTechs" :key="tech"
              class="px-3 py-1 bg-gray-100 text-gray-700 rounded text-xs">{{ tech }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- GitHub -->
    <div class="card-box mt-6 p-5">
      <h5 class="text-lg font-medium text-foreground">开源地址</h5>
      <div class="mt-4">
        <a
          href="https://github.com/Lin-0408-Yiran/structural-design-system"
          target="_blank"
          class="vben-link text-sm"
        >
          https://github.com/Lin-0408-Yiran/structural-design-system
        </a>
      </div>
    </div>
  </Page>
</template>
