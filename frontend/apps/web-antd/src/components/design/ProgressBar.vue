<template>
  <ACard size="small" class="progress-panel">
    <!-- 顶部步骤导航 -->
    <div class="steps-nav">
      <div
        v-for="(step, i) in steps"
        :key="step.key"
        class="step-item"
        :class="getStepClass(step.key)"
        @click="onStepClick(step.key)"
      >
        <div class="step-icon">
          <span v-if="getStageStatus(step.key) === 'completed'">✅</span>
          <span v-else-if="getStageStatus(step.key) === 'failed'">❌</span>
          <span v-else-if="getStageStatus(step.key) === 'skipped'">⏭</span>
          <span v-else>{{ step.icon }}</span>
        </div>
        <div class="step-title">{{ step.label }}</div>
        <div class="step-status">{{ getStepStatusText(step.key) }}</div>
        <div v-if="i < steps.length - 1" class="step-connector" />
      </div>
    </div>

    <!-- 主体两栏 -->
    <div class="main-body">
      <!-- 左侧：交互面板 -->
      <div class="left-panel">
        <!-- 查看历史阶段时：显示该阶段的交互记录 -->
        <template v-if="viewingStage">
          <div class="history-stage-header">
            📜 {{ getStageLabel(viewingStage) }} — 历史记录
            <span class="snapshot-time" style="margin-left:8px;">{{ snapshots[viewingStage]?.timestamp }}</span>
          </div>
          <div v-if="interactionHistoryByStage[viewingStage]?.length" class="interaction-history">
            <div v-for="(item, i) in interactionHistoryByStage[viewingStage]" :key="i" class="history-item-full">

              <!-- 问题标题 -->
              <div class="history-q-title">🔔 {{ item.question }}</div>

              <!-- 图片预览（如果有） -->
              <div v-if="item.image_path" class="history-preview-box">
                <img
                  :src="`/api/file/view?path=${encodeURIComponent(item.image_path)}`"
                  style="width:100%; max-height:600px; object-fit:contain; border-radius:8px; border:1px solid #d9d9d9; cursor:zoom-in;"
                  alt="历史交互图片"
                  @click="previewImageUrl = `/api/file/view?path=${encodeURIComponent(item.image_path)}`; previewImageVisible = true"
                />
              </div>

              <!-- 预警信息（如果有） -->
              <div v-if="item.context?.warnings?.length" class="history-warnings">
                <div v-for="(w, wi) in item.context.warnings" :key="wi" class="violation-item">
                  ⚠️ {{ w }}
                </div>
              </div>

              <!-- 评估得分（如果有） -->
              <div v-if="item.context?.score !== undefined" class="history-score">
                <span>综合得分：<strong style="font-size:18px;color:#1890ff;">{{ item.context.score }}</strong></span>
                <ATag :color="getGradeColor(item.context.grade)" style="margin-left:12px;">{{ item.context.grade }}</ATag>
              </div>

              <!-- 多方案卡片（如果有） -->
              <div v-if="item.context?.proposals?.length" class="history-schemes">
                <h4 style="font-size:14px;font-weight:600;margin-bottom:12px;">🔄 多方案优化（历史）</h4>
                <div class="schemes-container">
                  <div
                    v-for="(scheme, si) in item.context.proposals"
                    :key="si"
                    class="scheme-card"
                    :class="{ selected: isSelectedScheme(item.answer, si), recommended: scheme.recommended }"
                  >
                    <div class="scheme-header-card">
                      <span class="scheme-name">{{ scheme.name }}</span>
                      <span v-if="scheme.recommended">⭐</span>
                      <span v-else-if="isSelectedScheme(item.answer, si)">✅</span>
                    </div>
                    <div class="scheme-body">
                      <div v-for="(val, key) in scheme.metrics" :key="key" class="scheme-metric">
                        <div class="scheme-metric-label">{{ metricLabels[key] || key }}</div>
                        <div class="scheme-metric-value">{{ val }}</div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 推荐说明（如果有） -->
              <div v-if="item.context?.recommendation" class="history-recommendation">
                ★ 推荐方案：{{ item.context.recommendation }}
              </div>

              <!-- 选项列表（如果有） -->
              <div v-if="item.options?.length" class="history-options">
                <div v-for="(opt, oi) in item.options" :key="oi" class="history-option-item" :class="{ selected: opt === item.answer || opt.startsWith(item.answer) }">
                  {{ opt }}
                </div>
              </div>

              <!-- 用户的回答 -->
              <div class="history-a">
                ✅ 您的回答：<strong>{{ item.answer }}</strong>
                <span class="history-time">{{ item.time }}</span>
              </div>

            </div>
          </div>
          <div v-else style="padding:16px 0;">
            <div style="color:#999; font-size:13px; text-align:center; margin-bottom:16px;">
              该阶段无需用户交互（自动完成）
            </div>
            <!-- 显示该阶段的关键信息摘要 -->
            <div v-if="snapshots[viewingStage]?.data" class="auto-stage-summary">
              <div class="summary-title">📋 阶段摘要</div>

              <!-- 设计方案阶段摘要 -->
              <template v-if="viewingStage === 'design_proposal'">
                <div class="summary-item">
                  <span class="summary-label">结构类型：</span>
                  <span class="summary-value">{{ snapshots[viewingStage].data.type || '—' }}</span>
                </div>
                <div class="summary-item">
                  <span class="summary-label">设计描述：</span>
                  <span class="summary-value">{{ snapshots[viewingStage].data.description || '—' }}</span>
                </div>
              </template>

              <!-- 有限元分析阶段摘要 -->
              <template v-else-if="viewingStage === 'fe_analysis'">
                <div class="summary-item">
                  <span class="summary-label">最大应力：</span>
                  <span class="summary-value">{{ snapshots[viewingStage].data.max_stress_MPa || '—' }} MPa</span>
                </div>
                <div class="summary-item">
                  <span class="summary-label">最大位移：</span>
                  <span class="summary-value">{{ snapshots[viewingStage].data.max_displacement_mm || '—' }} mm</span>
                </div>
                <div class="summary-item">
                  <span class="summary-label">合规状态：</span>
                  <span class="summary-value" :class="snapshots[viewingStage].data.compliant ? 'success' : 'warning'">
                    {{ snapshots[viewingStage].data.compliant ? '✅ 合规' : '⚠️ 不合规' }}
                  </span>
                </div>
              </template>

              <!-- CAD绘图阶段摘要 -->
              <template v-else-if="viewingStage === 'cad_drawing'">
                <div class="summary-item">
                  <span class="summary-label">绘图状态：</span>
                  <span class="summary-value success">✅ DXF文件已生成</span>
                </div>
              </template>

              <!-- 报告生成阶段摘要 -->
              <template v-else-if="viewingStage === 'report_generation'">
                <div class="summary-item">
                  <span class="summary-label">报告状态：</span>
                  <span class="summary-value success">✅ 设计报告已生成</span>
                </div>
              </template>
            </div>
          </div>
          <div class="back-btn-wrap" style="margin-top:12px;">
            <AButton size="small" @click="viewingStage = null">← 返回当前进度</AButton>
          </div>
        </template>

        <!-- 当前进度：有 ask_human 时显示交互 UI -->
        <template v-else-if="askHumanRequest">
          <div class="ask-human-banner">🔔 需要您的确认，请查看并回复</div>
          <!-- 图片预览（可视化确认） -->
          <div v-if="askHumanRequest.image_path" class="preview-box">
            <img
              :src="`/api/file/view?path=${encodeURIComponent(askHumanRequest.image_path)}`"
              style="width:100%; max-height:600px; object-fit:contain; border-radius:8px; border:1px solid #d9d9d9; cursor:zoom-in;"
              alt="模型预览图"
              @click="previewImageUrl = `/api/file/view?path=${encodeURIComponent(askHumanRequest.image_path)}`; previewImageVisible = true"
            />
          </div>

          <!-- warnings 列表 -->
          <div v-if="askHumanRequest.context?.warnings?.length" class="warnings-list">
            <div v-for="(w, i) in askHumanRequest.context.warnings" :key="i" class="violation-item">
              ⚠️ {{ w }}
            </div>
          </div>

          <!-- 评估得分 -->
          <div v-if="askHumanRequest.context?.score !== undefined" class="score-summary">
            <span>综合得分：<strong style="font-size:20px;color:#1890ff;">{{ askHumanRequest.context.score }}</strong></span>
            <ATag :color="getGradeColor(askHumanRequest.context.grade)" style="margin-left:12px;">{{ askHumanRequest.context.grade }}</ATag>
          </div>

          <!-- 多方案卡片（实时显示） -->
          <div v-if="(realTimeSchemes.length > 0 || schemeTotal > 0) || askHumanRequest.context?.proposals?.length" style="margin-bottom:16px;">
            <h3 style="font-size:16px;font-weight:600;margin-bottom:16px;">🔄 多方案并行优化</h3>
            <div class="schemes-container-new">
              <!-- 使用 context.proposals（包含原方案）或 realTimeSchemes -->
              <template v-if="askHumanRequest.context?.proposals?.length">
                <div
                  v-for="(proposal, pi) in askHumanRequest.context.proposals"
                  :key="pi"
                  class="scheme-card-new"
                  :class="{
                    selected: isProposalSelected(pi),
                    recommended: proposal.recommended,
                    original: proposal.name === '原方案',
                    'history-mode': isReadonlyMode()
                  }"
                >
                  <div class="scheme-header-new">
                    <div class="scheme-title">
                      <span class="scheme-name-new">{{ proposal.name }}</span>
                      <span v-if="proposal.name === '原方案'" class="scheme-badge original-badge">原案</span>
                      <span v-else-if="proposal.recommended" class="scheme-badge recommended-badge">推荐</span>
                      <span v-if="isReadonlyMode() && isProposalSelected(pi)" class="badge-selected">✓ 用户选择</span>
                    </div>
                    <div v-if="!isReadonlyMode()" class="scheme-status">
                      <span v-if="selectedSchemeIdx === pi" class="status-icon selected-icon">✓已选</span>
                      <span v-else class="status-icon">✅</span>
                    </div>
                  </div>
                  <div class="scheme-metrics-grid">
                    <div class="metric-row">
                      <span class="metric-label">截面</span>
                      <span class="metric-value">{{ proposal.metrics.section }}</span>
                    </div>
                    <div class="metric-row">
                      <span class="metric-label">材料</span>
                      <span class="metric-value">{{ proposal.metrics.material }}</span>
                    </div>
                    <div class="metric-row">
                      <span class="metric-label">应力</span>
                      <span class="metric-value">{{ proposal.metrics.stress }}MPa</span>
                    </div>
                    <div class="metric-row">
                      <span class="metric-label">位移</span>
                      <span class="metric-value">{{ proposal.metrics.displacement }}mm</span>
                    </div>
                    <div class="metric-row">
                      <span class="metric-label">安全/经济/综合</span>
                      <span class="metric-value">{{ proposal.metrics.safety }}/{{ proposal.metrics.economy }}/{{ proposal.metrics.total_score }}</span>
                    </div>
                    <div class="metric-row">
                      <span class="metric-label">等级</span>
                      <span class="metric-value">{{ proposal.metrics.grade }}</span>
                    </div>
                  </div>
                  <!-- 只在非只读模式下显示选择按钮 -->
                  <button
                    v-if="!isReadonlyMode()"
                    class="select-btn-new"
                    :class="{ selected: selectedSchemeIdx === pi }"
                    @click="selectedSchemeIdx = pi"
                  >
                    {{ selectedSchemeIdx === pi ? '✓ 已选' : '选择' }}
                  </button>
                </div>
              </template>

              <!-- 实时推送模式（分析进行中） -->
              <template v-else>
                <div
                  v-for="scheme in realTimeSchemes"
                  :key="scheme.index"
                  class="scheme-card-new completed"
                  :class="{ selected: selectedSchemeIdx === scheme.index - 1 }"
                >
                  <div class="scheme-header-new">
                    <span class="scheme-name-new">方案 {{ scheme.index }}</span>
                    <span class="status-icon">✅</span>
                  </div>
                  <div class="scheme-metrics-grid">
                    <div v-for="(val, key) in scheme.metrics" :key="key" class="metric-row">
                      <span class="metric-label">{{ metricLabels[key] || key }}</span>
                      <span class="metric-value">{{ val }}</span>
                    </div>
                  </div>
                  <button class="select-btn-new" :disabled="selectedSchemeIdx === scheme.index - 1" @click="selectedSchemeIdx = scheme.index - 1">
                    {{ selectedSchemeIdx === scheme.index - 1 ? '✓ 已选' : '选择' }}
                  </button>
                </div>

                <!-- 还未完成的方案（分析中占位） -->
                <div
                  v-for="i in Math.max(0, schemeTotal - realTimeSchemes.length)"
                  :key="'pending-' + i"
                  class="scheme-card-new pending"
                >
                  <div class="scheme-header-new">
                    <span class="scheme-name-new">方案 {{ realTimeSchemes.length + i }}</span>
                    <span class="status-icon">⏳</span>
                  </div>
                  <div style="text-align:center;padding:40px 20px;color:#999;">
                    <div class="spinner-small" style="margin:0 auto 8px;"></div>
                    <div style="font-size:13px;">分析中...</div>
                  </div>
                </div>
              </template>
            </div>
          </div>

          <!-- 推荐方案说明 -->
          <div v-if="askHumanRequest.context?.recommendation" class="recommendation">
            ★ 推荐方案：{{ askHumanRequest.context.recommendation }}
          </div>

          <!-- LLM 改进建议 -->
          <div v-if="askHumanRequest.context?.suggestions_text" style="margin-bottom:14px; padding:12px; background:#f6ffed; border-left:4px solid #52c41a; border-radius:4px; max-height:300px; overflow-y:auto;">
            <div style="font-weight:500; color:#389e0d; margin-bottom:6px;">💡 LLM 改进建议</div>
            <pre style="margin:0; font-size:12px; color:#333; white-space:pre-wrap; font-family:inherit;">{{ askHumanRequest.context.suggestions_text }}</pre>
          </div>

          <!-- 问题文字 -->
          <p class="question-text">{{ askHumanRequest.question }}</p>

          <!-- context.description：推荐参数说明等补充信息 -->
          <div v-if="askHumanRequest.context?.description || askHumanRequest.context?.parameters" style="margin-bottom:14px; padding:10px 12px; background:#f0f5ff; border-left:4px solid #597ef7; border-radius:4px;">
            <div v-if="askHumanRequest.context?.description" style="font-weight:500; color:#2f54eb; margin-bottom:8px; font-size:13px;">{{ askHumanRequest.context.description }}</div>
            <table v-if="askHumanRequest.context?.parameters" style="width:100%; border-collapse:collapse; font-size:13px;">
              <tr v-for="(val, key) in askHumanRequest.context.parameters" :key="key" style="border-bottom:1px solid #d6e4ff;">
                <td style="padding:4px 8px; color:#555; white-space:nowrap; width:40%;">{{ key }}</td>
                <td style="padding:4px 8px; color:#222; font-weight:500;">{{ val }}</td>
              </tr>
            </table>
          </div>

          <!-- 选项模式：只在没有 proposals 时显示单选按钮 -->
          <template v-if="askHumanRequest.options?.length && !askHumanRequest.context?.proposals?.length">
            <ARadioGroup v-model:value="answer" style="display:flex; flex-direction:column; gap:10px; margin-bottom:16px;">
              <ARadio v-for="opt in askHumanRequest.options" :key="opt" :value="opt" style="font-size:14px;">{{ opt }}</ARadio>
              <!-- 非固定指令类询问（排除 是/否/continue 等）显示"其他"选项 -->
              <ARadio v-if="!(askHumanRequest.options || []).some((o: string) => /^(是|否|y|n|continue|optimize|report_only|terminate)\s*[-—]/.test(o))" value="__other__" style="font-size:14px;">其他（自定义输入）</ARadio>
            </ARadioGroup>
            <ATextarea
              v-if="answer === '__other__' || (askHumanRequest.stage === 'design_proposal' && /^否\s*[-—]/.test(answer))"
              v-model:value="otherInput"
              :rows="3"
              :placeholder="answer === '__other__' ? '请输入自定义内容...' : '请说明需要如何修改...'"
              style="margin-top:8px; margin-bottom:12px;"
            />
          </template>

          <!-- 自由文本模式 -->
          <template v-else-if="!askHumanRequest.context?.proposals?.length">
            <ATextarea v-model:value="answer" :rows="3" placeholder="请输入您的回答" style="margin-bottom:12px;" />
          </template>

          <AButton
            type="primary"
            :disabled="askHumanRequest.context?.proposals?.length ? selectedSchemeIdx < 0 : (answer === '__other__' ? !otherInput.trim() : !answer)"
            @click="submitAnswer"
          >
            {{ askHumanRequest.context?.proposals?.length ? '✅ 确认选择' : '确认提交' }}
          </AButton>
        </template>

        <!-- 无 ask_human 时显示子进度 -->
        <template v-else>
          <!-- 实时方案卡片：仅在分析进行中（schemeTotal > 0 且未全部完成）时显示 -->
          <div v-if="schemeTotal > 0 && realTimeSchemes.length < schemeTotal" style="margin-bottom:16px;">
            <h3 style="font-size:14px;font-weight:600;margin-bottom:12px;">🔄 多方案优化中...</h3>
            <div class="schemes-container">
              <div v-for="scheme in realTimeSchemes" :key="scheme.index" class="scheme-card completed">
                <div class="scheme-header-card">
                  <span class="scheme-name">方案 {{ scheme.index }}</span>
                  <span>✅</span>
                </div>
                <div class="scheme-body">
                  <div v-for="(val, key) in scheme.metrics" :key="key" class="scheme-metric">
                    <div class="scheme-metric-label">{{ metricLabels[key] || key }}</div>
                    <div class="scheme-metric-value">{{ val }}</div>
                  </div>
                </div>
              </div>
              <!-- 还未完成的占位 -->
              <div v-for="i in Math.max(0, schemeTotal - realTimeSchemes.length)" :key="'p-'+i" class="scheme-card">
                <div class="scheme-header-card">
                  <span class="scheme-name">方案 {{ realTimeSchemes.length + i }}</span>
                  <span>⏳</span>
                </div>
                <div style="text-align:center;padding:20px;color:#999;">
                  <div class="spinner-small" style="margin:0 auto 8px;"></div>
                  <div style="font-size:12px;">分析中...</div>
                </div>
              </div>
            </div>
          </div>
          <!-- 交互历史记录（全部） -->
          <div v-if="currentInteractionHistory.length" class="interaction-history">
            <div v-for="(item, i) in currentInteractionHistory" :key="i" class="history-item">
              <!-- 阶段标识 -->
              <div class="history-stage-label">📜 [{{ getStageLabel(item.stage) }}] {{ item.time }}</div>

              <!-- 图片（如果有） -->
              <div v-if="item.image_path" class="history-image">
                <img :src="`/api/design/${item.image_path.split('/').pop().split('_')[0]}/visualization/${item.image_path.split('/').pop()}`" alt="可视化图" style="max-width: 100%; border-radius: 4px;" />
              </div>

              <!-- 警告信息（如果有） -->
              <div v-if="item.context?.warnings?.length" class="history-warnings">
                <div v-for="(w, wi) in item.context.warnings" :key="wi" class="warning-item">⚠️ {{ w }}</div>
              </div>

              <!-- 方案卡片（如果有） - 历史记录模式：只读，无选择按钮 -->
              <div v-if="item.context?.proposals?.length" class="schemes-container-new" style="margin-bottom: 12px;">
                <div
                  v-for="(proposal, pi) in item.context.proposals"
                  :key="pi"
                  class="scheme-card-new history-mode"
                  :class="{
                    selected: isSelectedProposal(item.answer, proposal, pi),
                    recommended: proposal.recommended,
                    original: proposal.name === '原方案'
                  }"
                >
                  <div class="scheme-header-new">
                    <span class="scheme-name-new">{{ proposal.name }}</span>
                    <span v-if="proposal.recommended" class="badge-recommended">⭐ 推荐</span>
                    <span v-if="proposal.name === '原方案'" class="badge-original">原案</span>
                    <span v-if="isSelectedProposal(item.answer, proposal, pi)" class="badge-selected">✓ 用户选择</span>
                  </div>
                  <div class="scheme-metrics-grid">
                    <div v-if="proposal.metrics.section" class="metric-row">
                      <span class="metric-label">截面</span>
                      <span class="metric-value">{{ proposal.metrics.section }}</span>
                    </div>
                    <div v-if="proposal.metrics.material" class="metric-row">
                      <span class="metric-label">材料</span>
                      <span class="metric-value">{{ proposal.metrics.material }}</span>
                    </div>
                    <div v-if="proposal.metrics.stress" class="metric-row">
                      <span class="metric-label">应力</span>
                      <span class="metric-value">{{ proposal.metrics.stress }}</span>
                    </div>
                    <div v-if="proposal.metrics.displacement" class="metric-row">
                      <span class="metric-label">位移</span>
                      <span class="metric-value">{{ proposal.metrics.displacement }}</span>
                    </div>
                    <div v-if="proposal.metrics.total_score" class="metric-row">
                      <span class="metric-label">综合得分</span>
                      <span class="metric-value">{{ proposal.metrics.total_score }}</span>
                    </div>
                    <div v-if="proposal.metrics.grade" class="metric-row">
                      <span class="metric-label">等级</span>
                      <span class="metric-value">{{ proposal.metrics.grade }}</span>
                    </div>
                  </div>
                  <!-- 历史记录中不显示选择按钮 -->
                </div>
              </div>

              <!-- 问题文字 -->
              <div class="history-q">{{ item.question }}</div>

              <!-- 答案（非方案选择的情况） -->
              <div v-if="!item.context?.proposals?.length" class="history-a">
                ✅ 您的回答：{{ item.answer }}
              </div>
            </div>
          </div>
          <template v-if="progressData">
            <div class="sub-stage-title">
              {{ getStageLabel(progressData.stage) }}
              <span class="sub-pct">{{ Math.round(progressData.progress * 100) }}%</span>
            </div>
            <AProgress
              :percent="Math.round(progressData.progress * 100)"
              :stroke-color="{ '0%': '#108ee9', '100%': '#87d068' }"
              :status="progressData.progress >= 1 ? 'success' : 'active'"
            />
            <div class="sub-message">{{ progressData.message }}</div>
          </template>
          <template v-else-if="!props.stages?.length">
            <div style="color:#999; padding:20px 0;">等待任务开始...</div>
          </template>

          <!-- 自动优化日志：独立卡片，不受进度条影响 -->
          <div v-if="latestByStage['fe_analysis']?.data?.auto_improvement_plan"
               style="margin-top:16px; padding:12px; background:#f6ffed; border-left:4px solid #52c41a; border-radius:4px;">
            <div style="font-weight:500; color:#389e0d; margin-bottom:6px;">
              🔄 自动优化 {{ latestByStage['fe_analysis'].data.loop }}/{{ latestByStage['fe_analysis'].data.max_loops }} — LLM 改进方案
            </div>
            <pre style="margin:0; font-size:12px; color:#333; white-space:pre-wrap; font-family:inherit; max-height:200px; overflow-y:auto;">{{ latestByStage['fe_analysis'].data.auto_improvement_plan }}</pre>
          </div>
        </template>
      </div>

      <!-- 右侧：设计状态面板 -->
      <div class="right-panel">
        <div class="panel-header">
          <span>📊 设计状态</span>
          <span v-if="viewingStage" class="history-badge">📜 历史 - {{ getStageLabel(viewingStage) }}</span>
          <span v-else class="live-badge">📍 当前进度</span>
        </div>
        <div v-if="viewingStage && snapshots[viewingStage]" class="snapshot-time">
          ⏱️ {{ snapshots[viewingStage].timestamp }}
        </div>

        <div class="params-content">
          <!-- 设计方案阶段 -->
          <template v-if="displayStage === 'design_proposal'">
            <div class="param-card">
              <div class="param-title">📋 设计需求</div>
              <div style="font-size:12px; color:#555; line-height:1.6;">{{ displayParams?.designDescription || '—' }}</div>
            </div>
            <div v-if="displayParams?.geometry || displayParams?.material" class="param-card">
              <div class="param-title">📐 设计参数</div>
              <div class="param-grid">
                <div class="param-item"><span class="param-label">结构类型</span><span class="param-value">{{ displayParams?.designType || '—' }}</span></div>
                <template v-if="displayParams?.geometry">
                  <div v-for="(val, key) in displayParams.geometry" :key="key" class="param-item">
                    <span class="param-label">{{ getFieldLabel(key) }}</span>
                    <span class="param-value">{{ formatFieldValue(key, val) }}</span>
                  </div>
                </template>
                <template v-if="displayParams?.material">
                  <div v-for="(val, key) in displayParams.material" :key="'mat-'+key" class="param-item">
                    <span class="param-label">{{ getFieldLabel(key) }}</span>
                    <span class="param-value">{{ formatFieldValue(key, val) }}</span>
                  </div>
                </template>
              </div>
            </div>
            <div v-if="displayParams?.standards?.length" class="param-card">
              <div class="param-title">📏 设计规范</div>
              <div v-for="(s, i) in displayParams.standards" :key="i" style="font-size:12px; color:#555; padding:2px 0;">• {{ s }}</div>
            </div>
          </template>

          <!-- 有限元分析阶段 -->
          <template v-else-if="displayStage === 'fe_analysis'">
            <div v-if="snapshots['design_proposal']?.data" class="param-card">
              <div class="param-title">📋 当前设计方案</div>
              <div class="param-grid">
                <div class="param-item"><span class="param-label">类型</span><span class="param-value">{{ snapshots['design_proposal'].data.type || '—' }}</span></div>
                <template v-if="snapshots['design_proposal'].data.geometry">
                  <div v-for="(val, key) in snapshots['design_proposal'].data.geometry" :key="key" class="param-item">
                    <span class="param-label">{{ getFieldLabel(key) }}</span>
                    <span class="param-value">{{ formatFieldValue(key, val) }}</span>
                  </div>
                </template>
                <div v-if="snapshots['design_proposal'].data.material?.material_name" class="param-item">
                  <span class="param-label">材料</span>
                  <span class="param-value">{{ snapshots['design_proposal'].data.material.material_name }}</span>
                </div>
                <div v-if="snapshots['design_proposal'].data.type === 'truss' && snapshots['design_proposal'].data.material?.A != null" class="param-item">
                  <span class="param-label">杆件截面面积 (mm²)</span>
                  <span class="param-value">{{ (snapshots['design_proposal'].data.material.A * 1e6).toFixed(0) }}</span>
                </div>
              </div>
            </div>
            <div class="param-card">
              <div class="param-title">🔬 有限元分析结果</div>
              <div class="param-grid">
                <div class="param-item"><span class="param-label">最大应力</span><span class="param-value" :class="{ warning: (displayParams?.maxStress ?? 0) > 235 }">{{ displayParams?.maxStress != null ? displayParams.maxStress + ' MPa' : '—' }}</span></div>
                <div class="param-item"><span class="param-label">最大挠度</span><span class="param-value">{{ displayParams?.maxDeflection != null ? displayParams.maxDeflection + ' mm' : '—' }}</span></div>
                <div class="param-item"><span class="param-label">合规状态</span><span class="param-value" :class="snapshots['fe_analysis'] ? (displayParams?.complianceStatus === 'compliant' ? 'success' : displayParams?.complianceStatus === 'non_compliant' ? 'warning' : '') : ''">{{ snapshots['fe_analysis'] ? (displayParams?.complianceStatus === 'compliant' ? '✅ 合规' : displayParams?.complianceStatus === 'non_compliant' ? '⚠️ 不合规' : '—') : '—' }}</span></div>
              </div>
              <div v-if="snapshots['fe_analysis'] && mergedViolations.length" class="violations">
                <div v-for="(v, i) in mergedViolations" :key="i" class="violation-item">🔴 {{ v }}</div>
              </div>
            </div>
          </template>

          <!-- 设计评估阶段 -->
          <template v-else-if="displayStage === 'evaluation'">
            <div v-if="snapshots['design_proposal']?.data" class="param-card">
              <div class="param-title">📋 设计方案</div>
              <div class="param-grid">
                <div class="param-item"><span class="param-label">类型</span><span class="param-value">{{ snapshots['design_proposal'].data.type || '—' }}</span></div>
                <template v-if="snapshots['design_proposal'].data.geometry">
                  <div v-for="(val, key) in snapshots['design_proposal'].data.geometry" :key="key" class="param-item">
                    <span class="param-label">{{ getFieldLabel(key) }}</span>
                    <span class="param-value">{{ formatFieldValue(key, val) }}</span>
                  </div>
                </template>
                <div v-if="snapshots['design_proposal'].data.material?.material_name" class="param-item">
                  <span class="param-label">材料</span>
                  <span class="param-value">{{ snapshots['design_proposal'].data.material.material_name }}</span>
                </div>
                <div v-if="snapshots['design_proposal'].data.type === 'truss' && snapshots['design_proposal'].data.material?.A != null" class="param-item">
                  <span class="param-label">杆件截面面积 (mm²)</span>
                  <span class="param-value">{{ (snapshots['design_proposal'].data.material.A * 1e6).toFixed(0) }}</span>
                </div>
              </div>
            </div>
            <div class="param-card">
              <div class="param-title">📊 综合评估得分</div>
              <div class="score-grid">
                <div class="score-item"><div class="score-num" :style="{ color: getScoreColor(displayParams?.safetyScore) }">{{ displayParams?.safetyScore ?? '—' }}</div><div class="score-label">安全性</div></div>
                <div class="score-item"><div class="score-num" :style="{ color: getScoreColor(displayParams?.economyScore) }">{{ displayParams?.economyScore ?? '—' }}</div><div class="score-label">经济性</div></div>
                <div class="score-item"><div class="score-num" :style="{ color: getScoreColor(displayParams?.efficiencyScore) }">{{ displayParams?.efficiencyScore ?? '—' }}</div><div class="score-label">结构效率</div></div>
                <div class="score-item"><div class="score-num" :style="{ color: getScoreColor(displayParams?.sustainabilityScore) }">{{ displayParams?.sustainabilityScore ?? '—' }}</div><div class="score-label">可持续性</div></div>
                <div class="score-item"><div class="score-num" :style="{ color: getScoreColor(displayParams?.overallScore) }">{{ displayParams?.overallScore ?? '—' }}</div><div class="score-label">综合</div></div>
              </div>
              <div v-if="displayParams?.grade" style="text-align:center; margin-top:8px;">
                <ATag :color="getGradeColor(displayParams.grade)" style="font-size:14px; padding:2px 12px;">{{ displayParams.grade }}</ATag>
              </div>
              <div v-if="displayParams?.warnings?.length" style="margin-top:8px;">
                <div v-for="(w, i) in displayParams.warnings" :key="i" class="violation-item">⚠️ {{ w }}</div>
              </div>
            </div>
          </template>

          <!-- CAD绘图阶段 -->
          <template v-else-if="displayStage === 'cad_drawing'">
            <div v-if="snapshots['design_proposal']?.data" class="param-card">
              <div class="param-title">📋 设计方案</div>
              <div class="param-grid">
                <div class="param-item"><span class="param-label">类型</span><span class="param-value">{{ snapshots['design_proposal'].data.type || '—' }}</span></div>
                <div v-if="snapshots['design_proposal'].data.material?.material_name" class="param-item">
                  <span class="param-label">材料</span>
                  <span class="param-value">{{ snapshots['design_proposal'].data.material.material_name }}</span>
                </div>
                <div v-if="snapshots['design_proposal'].data.type === 'truss' && snapshots['design_proposal'].data.material?.A != null" class="param-item">
                  <span class="param-label">杆件截面面积 (mm²)</span>
                  <span class="param-value">{{ (snapshots['design_proposal'].data.material.A * 1e6).toFixed(0) }}</span>
                </div>
              </div>
            </div>
            <div class="param-card">
              <div class="param-title">✏️ CAD图纸</div>
              <div class="param-item" style="margin-bottom:8px;">
                <span class="param-label">状态</span>
                <span class="param-value" :class="['completed', 'success'].includes(displayParams?.drawingStatus) ? 'success' : ''">
                  {{ ['completed', 'success'].includes(displayParams?.drawingStatus) ? '✅ DXF已生成' : displayParams?.drawingStatus === 'skipped' ? '⏭ 已跳过' : '⏳ 生成中...' }}
                </span>
              </div>
              <div v-if="displayParams?.drawingFiles?.length">
                <div class="param-label" style="margin-bottom:4px;">生成文件：</div>
                <div v-for="(f, i) in displayParams.drawingFiles" :key="i" style="font-size:12px; color:#1890ff; padding:2px 0;">📄 {{ f }}</div>
              </div>
            </div>
          </template>

          <!-- BIM/报告阶段 -->
          <template v-else-if="displayStage === 'report_generation'">
            <div class="param-card">
              <div class="param-title">🏗️ BIM导出</div>
              <div class="param-grid">
                <div class="param-item"><span class="param-label">Speckle</span><span class="param-value" :class="displayParams?.speckleExported ? 'success' : ''">{{ displayParams?.speckleExported ? '✅ 已导出' : '⏸ 未导出' }}</span></div>
                <div class="param-item"><span class="param-label">IFC</span><span class="param-value" :class="displayParams?.ifcExported ? 'success' : ''">{{ displayParams?.ifcExported ? '✅ 已生成' : '⏸ 未生成' }}</span></div>
              </div>
            </div>
            <div class="param-card">
              <div class="param-title">📄 报告</div>
              <div class="param-value" :class="['completed', 'success'].includes(displayParams?.reportStatus) ? 'success' : ''">{{ ['completed', 'success'].includes(displayParams?.reportStatus) ? '✅ 已生成' : '⏳ 生成中' }}</div>
            </div>
          </template>

          <template v-else-if="!props.stages?.length">
            <div class="param-card" style="text-align:center; color:#999; padding:20px;">等待任务开始...</div>
          </template>
        </div>
      </div>
    </div>
  </ACard>

  <!-- 图片放大预览 -->
  <AModal v-model:open="previewImageVisible" :footer="null" width="90vw" style="top:20px">
    <img v-if="previewImageUrl" :src="previewImageUrl" style="width:100%; object-fit:contain;" alt="预览图" />
  </AModal>
</template>

<script setup lang="ts">
import { ref, computed, watch, reactive } from 'vue';
import { Card as ACard, Progress as AProgress, Button as AButton, Radio as ARadio, RadioGroup as ARadioGroup, Input, Tag as ATag, Table as ATable } from 'ant-design-vue';
import { getStageLabel } from '#/utils/i18n';

const ATextarea = Input.TextArea;

const props = defineProps<{
  stages: any[];
  progressData: any | null;
  taskParams: any | null;
  askHumanRequest: any | null;
  schemeUpdates: any[];
  schemeTotalHint: number;
  savedInteractionHistory: { stage: string; question: string; answer: string; time: string }[];
}>();

const emit = defineEmits<{ submit: [answer: string] }>();

const steps = [
  { key: 'design_proposal', label: '设计方案', icon: '📋' },
  { key: 'fe_analysis', label: '有限元分析', icon: '🔬' },
  { key: 'evaluation', label: '设计评估', icon: '📊' },
  { key: 'cad_drawing', label: 'CAD绘图', icon: '✏️' },
  { key: 'report_generation', label: 'BIM/报告', icon: '🏗️' },
];

const answer = ref('');
const otherInput = ref('');
const snapshots = reactive<Record<string, any>>({});
const viewingStage = ref<string | null>(null);
// 交互历史按阶段存储，key 为 stage name
const interactionHistoryByStage = reactive<Record<string, { question: string; answer: string; time: string }[]>>({});

// 字段名中英文映射表（带单位）
const fieldLabels: Record<string, string> = {
  // 几何参数 - 通用
  'length': '跨度 (m)',
  'width': '截面宽 (m)',
  'height': '截面高/桁架高 (m)',
  'span': '跨度 (m)',
  'thickness': '厚度 (m)',
  'diameter': '直径 (m)',
  'n_elements': '单元数量',
  // 几何参数 - 桁架
  'n_panels': '节间数',
  'truss_type': '桁架类型',
  'A': '截面积 (m²)',
  // 几何参数 - 框架
  'num_bays': '跨数',
  'num_stories': '层数',
  'bay_widths': '各跨宽度 (m)',
  'story_heights': '各层高度 (m)',
  'columns': '柱截面',
  'beams': '梁截面',
  // 材料参数
  'material_name': '材料名称',
  'E': '弹性模量',
  'fy': '屈服/抗压强度',
  'nu': '泊松比',
  'density': '密度 (kg/m³)',
  'fc': '混凝土强度 (MPa)',
  // 荷载参数
  'dead_load': '恒载 (kN/m)',
  'live_load': '活载 (kN/m)',
  'wind_load': '风荷载 (kN/m²)',
  'seismic_load': '地震荷载',
  // 其他
  'type': '结构类型',
  'description': '描述',
  'beam': '梁类型',
  'column': '柱类型',
};

// 获取字段的中文标签（带单位）
const getFieldLabel = (key: string): string => {
  return fieldLabels[key] || key;
};

const formatFieldValue = (key: string, val: any): string => {
  if (val === null || val === undefined) return '—';

  // Arrays: show as comma-separated values
  if (Array.isArray(val)) return val.join(' / ') + (key.includes('width') || key.includes('height') ? ' m' : '');

  // Objects: format section info (columns/beams)
  if (typeof val === 'object') {
    const parts: string[] = [];
    if (val.width != null && val.depth != null) parts.push(`${val.width * 1000}×${val.depth * 1000} mm`);
    else if (val.width != null) parts.push(`宽 ${val.width * 1000} mm`);
    else if (val.depth != null) parts.push(`高 ${val.depth * 1000} mm`);
    if (val.type) parts.push(val.type === 'rectangular' ? '矩形' : val.type);
    return parts.length ? parts.join('，') : JSON.stringify(val);
  }

  const numVal = Number(val);
  if (isNaN(numVal)) return String(val);

  // Elastic modulus E: convert Pa → GPa or MPa
  if (key === 'E') {
    if (Math.abs(numVal) >= 1e9) return (numVal / 1e9).toFixed(1) + ' GPa';
    if (Math.abs(numVal) >= 1e6) return (numVal / 1e6).toFixed(0) + ' MPa';
    return numVal.toFixed(0) + ' Pa';
  }

  // Strength fy/fc: convert Pa → MPa if large
  if (key === 'fy' || key === 'fc') {
    if (Math.abs(numVal) >= 1e6) return (numVal / 1e6).toFixed(1) + ' MPa';
    return numVal.toFixed(1) + ' MPa';
  }

  // Cross-section area A: m² with 4 decimal places
  if (key === 'A') return numVal.toFixed(4) + ' m²';

  // Normal numbers: up to 3 significant digits, no scientific notation
  if (Math.abs(numVal) >= 1000) return numVal.toLocaleString('zh-CN', { maximumFractionDigits: 0 });
  if (Math.abs(numVal) >= 1) return numVal.toFixed(2);
  if (numVal === 0) return '0';
  return numVal.toPrecision(3);
};

// 从持久化历史初始化（任务完成后刷新页面时恢复）
watch(() => props.savedInteractionHistory, (history) => {
  if (!history?.length) return;
  // 清空再重建，避免重复
  for (const key of Object.keys(interactionHistoryByStage)) {
    delete interactionHistoryByStage[key];
  }
  for (const item of history) {
    const s = item.stage || 'unknown';
    if (!interactionHistoryByStage[s]) interactionHistoryByStage[s] = [];
    interactionHistoryByStage[s].push({
      question: item.question,
      answer: item.answer,
      time: item.time,
      options: item.options || [],
      context: item.context || {},
      image_path: item.image_path || null,
    });
  }
}, { immediate: true, deep: true });

// 当前阶段的交互历史（用于实时显示）
const currentInteractionHistory = computed(() => {
  const all: { question: string; answer: string; time: string; stage: string }[] = [];
  for (const [stage, items] of Object.entries(interactionHistoryByStage)) {
    for (const item of items) all.push({ ...item, stage });
  }
  return all.sort((a, b) => a.time.localeCompare(b.time));
});

// 多方案实时数据
const realTimeSchemes = ref<any[]>([]);  // 实时接收的方案数据
const selectedSchemeIdx = ref<number>(-1);

const metricLabels: Record<string, string> = {
  section: '截面', material: '材料',
  stress: '最大应力', displacement: '最大挠度',
  safety: '安全性', economy: '经济性',
  total_score: '综合得分', grade: '等级',
};

// 监听实时方案推送 —— 直接 watch 数组长度，push 时可靠触发
watch(() => props.schemeUpdates.length, () => {
  const updates = props.schemeUpdates;
  if (!updates || updates.length === 0) return;

  // 按 index 排序，逐个追加（不重复）
  const sorted = [...updates].sort((a, b) => a.index - b.index);
  realTimeSchemes.value = sorted.map(u => ({
    name: `方案 ${u.index}`,
    metrics: u.metrics,
    index: u.index,
  }));
});

// 从 scheme_ready 消息获取总方案数，优先用 scheme_start 提前告知的总数
const schemeTotal = computed(() => {
  if (props.schemeTotalHint > 0) return props.schemeTotalHint;
  if (props.schemeUpdates.length > 0) return props.schemeUpdates[0].total;
  return 0;
});

// 当 ask_human 包含 proposals 时，初始化选择状态
watch(() => props.askHumanRequest, (req) => {
  answer.value = req?.default || (req?.options?.[0] ?? '');
  if (req?.context?.proposals?.length) {
    // 找推荐方案作为默认选中（proposals 包含原方案，索引从0开始）
    const recIdx = req.context.proposals.findIndex((p: any) => p.recommended);
    selectedSchemeIdx.value = recIdx >= 0 ? recIdx : 0;
  } else {
    selectedSchemeIdx.value = -1;
  }
});

watch(() => props.stages, (newStages) => {
  for (const s of newStages) {
    if ((s.status === 'completed' || s.status === 'skipped') && s.data) {
      snapshots[s.stage] = {
        timestamp: s.timestamp || new Date().toLocaleTimeString(),
        data: s.data,
      };
    } else if ((s.status === 'completed' || s.status === 'skipped') && !snapshots[s.stage]) {
      snapshots[s.stage] = {
        timestamp: s.timestamp || new Date().toLocaleTimeString(),
        data: null,
      };
    }
  }
}, { deep: true, immediate: true });

const latestByStage = computed(() => {
  const map: Record<string, any> = {};
  for (const s of props.stages) map[s.stage] = s;
  return map;
});

const activeStage = computed(() => {
  let last = '';
  for (const step of steps) { if (latestByStage.value[step.key]) last = step.key; }
  return last;
});

const displayStage = computed(() => viewingStage.value || activeStage.value);

// 从 snapshot data 映射为面板字段
function mapSnapshotData(d: any) {
  if (!d) return null;
  return {
    designDescription: d.description,
    designType: d.type,
    geometry: d.geometry,
    material: d.material,
    standards: d.standards,
    // fe_analysis
    maxStress: d.max_stress_MPa,
    maxDeflection: d.max_displacement_mm,
    safetyFactor: d.safety_factor,
    complianceStatus: d.compliant === true ? 'compliant' : d.compliant === false ? 'non_compliant' : null,
    violations: d.violations,
    // evaluation
    overallScore: d.comprehensive_score,
    safetyScore: d.safety_score,
    economyScore: d.economy_score,
    efficiencyScore: d.efficiency_score,
    sustainabilityScore: d.sustainability_score,
    grade: d.grade,
    warnings: d.warnings,
    // cad_drawing
    drawingStatus: d.status,
    drawingFiles: d.files,
    // report_generation
    reportStatus: d.report_status,
    speckleExported: d.speckle_exported,
    ifcExported: d.ifc_exported,
  };
}

const previewImageUrl = ref('');
const previewImageVisible = ref(false);

const translateViolation = (text: string): string => {
  let m;
  m = text.match(/slenderness ratio too high: λ=([\d.]+) > (\d+)/);
  if (m) return `杆件长细比超限：λ=${m[1]} > 限值 ${m[2]}`;
  m = text.match(/Max stress ([\d.]+) MPa exceeds allowable ([\d.]+) MPa/);
  if (m) return `应力超限：实际值 ${m[1]} MPa > 限值 ${m[2]} MPa`;
  m = text.match(/Max deflection ([\d.]+) mm exceeds limit ([\d.]+) mm/);
  if (m) return `挠度超限：实际值 ${m[1]} mm > 限值 ${m[2]} mm`;
  m = text.match(/Deflection exceeds limit: ([\d.]+)m > ([\d.]+)m/);
  if (m) return `挠度超限：实际值 ${(parseFloat(m[1])*1000).toFixed(2)} mm > 限值 ${(parseFloat(m[2])*1000).toFixed(2)} mm`;
  return text;
};

const mergedViolations = computed(() => {
  const raw = displayParams.value?.violations;
  if (!raw?.length) return [];
  // Group by type, merge duplicates
  const groups: Record<string, { msg: string; count: number }> = {};
  for (const v of raw) {
    const text = typeof v === 'string' ? v : (v.message || v.description || '未知违规');
    const type = typeof v === 'object' ? (v.type || 'unknown') : 'unknown';
    if (!groups[type]) groups[type] = { msg: translateViolation(text), count: 0 };
    groups[type].count++;
  }
  return Object.values(groups).map(g => g.count > 1 ? `${g.msg}（共 ${g.count} 处）` : g.msg);
});

const displayParams = computed(() => {
  const stage = displayStage.value;
  if (!stage) return props.taskParams;

  // 优先用 snapshot（已完成阶段的数据）
  if (snapshots[stage]?.data) return mapSnapshotData(snapshots[stage].data);

  // 运行中阶段：用 taskParams（任务完成后有数据）或 null
  return props.taskParams;
});

const getStageStatus = (key: string) => latestByStage.value[key]?.status || 'pending';

const getStepClass = (key: string) => ({
  completed: getStageStatus(key) === 'completed',
  active: getStageStatus(key) === 'started' || getStageStatus(key) === 'running',
  failed: getStageStatus(key) === 'failed',
  skipped: getStageStatus(key) === 'skipped',
  viewing: viewingStage.value === key,
  clickable: !!snapshots[key] || !!latestByStage.value[key],
});

const statusTextMap: Record<string, string> = { completed: '✅ 完成', started: '⏳ 进行中', running: '⏳ 进行中', failed: '❌ 失败', skipped: '⏭ 跳过' };
const getStepStatusText = (key: string) => statusTextMap[getStageStatus(key)] || '⏸ 等待';

const onStepClick = (key: string) => {
  // 有 snapshot 或有 stage 记录都可以点击查看历史
  if (snapshots[key] || latestByStage.value[key]) {
    viewingStage.value = viewingStage.value === key ? null : key;
  }
};

const getScoreColor = (score: number | null) => {
  if (score == null) return '#999';
  return score >= 80 ? '#52c41a' : score >= 70 ? '#faad14' : '#f5222d';
};

const getGradeColor = (grade: string) => {
  if (!grade) return 'default';
  if (grade.startsWith('A')) return 'green';
  if (grade.startsWith('B')) return 'blue';
  if (grade.startsWith('C')) return 'orange';
  return 'red';
};

const isSelectedScheme = (answer: string, schemeIndex: number) => {
  // answer 可能是 "0", "1", "2" 或 "optimize" 等
  // schemeIndex 是数组索引 0, 1, 2
  const answerNum = parseInt(answer);
  if (!isNaN(answerNum)) {
    return answerNum === schemeIndex;
  }
  return false;
};

// 判断历史记录中某个方案是否是用户选择的方案
const isSelectedProposal = (answer: string, proposal: any, proposalIndex: number) => {
  // answer 是用户提交的答案，可能是 "0", "1", "2" 等索引
  const answerNum = parseInt(answer);
  if (!isNaN(answerNum)) {
    return answerNum === proposalIndex;
  }
  // 也可能通过方案名称匹配
  if (answer.includes(proposal.name)) {
    return true;
  }
  return false;
};

// 判断当前 askHumanRequest 是否是只读模式（已经选择过方案，仅展示）
const isReadonlyMode = () => {
  // 如果 context 中有 selected_proposal_index，说明已经选择过方案，现在是只读展示
  if (props.askHumanRequest?.context?.selected_proposal_index !== undefined) {
    return true;
  }
  // 如果 context 中有 readonly 标识
  if (props.askHumanRequest?.context?.readonly === true) {
    return true;
  }
  // 如果问题不是关于选择方案的（比如"是否导出BIM"），但包含了 proposals，说明是只读展示
  const question = props.askHumanRequest?.question || '';
  if (props.askHumanRequest?.context?.proposals?.length &&
      !question.includes('选择') &&
      !question.includes('方案') &&
      (question.includes('是否') || question.includes('导出'))) {
    return true;
  }
  return false;
};

// 判断某个方案是否被选中（在只读模式下）
const isProposalSelected = (proposalIndex: number) => {
  // 只读模式：使用 context.selected_proposal_index
  if (isReadonlyMode()) {
    const selectedIdx = props.askHumanRequest?.context?.selected_proposal_index;
    if (selectedIdx !== undefined) {
      return selectedIdx === proposalIndex;
    }
  }
  // 正常选择模式：使用 selectedSchemeIdx
  return selectedSchemeIdx.value === proposalIndex;
};

const proposalColumns = computed(() => {
  if (!props.askHumanRequest?.context?.proposals?.length) return [];
  const metrics = props.askHumanRequest.context.proposals[0]?.metrics || {};
  const metricLabels: Record<string, string> = {
    section: '截面', material: '材料',
    stress: '最大应力', displacement: '最大挠度',
    safety: '安全性', economy: '经济性',
    total_score: '综合得分', grade: '等级',
  };
  return [
    { title: '方案', key: 'name', dataIndex: 'name', width: 100 },
    ...Object.keys(metrics).map(k => ({ title: metricLabels[k] || k, key: k, dataIndex: ['metrics', k], width: 100 })),
  ];
});

const submitAnswer = () => {
  let submitted = '';
  if (props.askHumanRequest?.context?.proposals?.length) {
    submitted = String(selectedSchemeIdx.value);
  } else {
    // "其他"模式：提交文本输入内容
    if (answer.value === '__other__') {
      if (!otherInput.value.trim()) return;
      submitted = otherInput.value.trim();
    } else if (props.askHumanRequest?.stage === 'design_proposal' && /^否\s*[-—]/.test(answer.value) && otherInput.value.trim()) {
      // design_proposal 阶段选"否"且有补充说明，拼接提交
      submitted = answer.value.split(' - ')[0].trim() + '：' + otherInput.value.trim();
    } else {
      if (!answer.value) return;
      submitted = answer.value.split(' - ')[0].trim();
    }
  }
  const stage = props.askHumanRequest?.stage || activeStage.value || 'unknown';
  if (!interactionHistoryByStage[stage]) interactionHistoryByStage[stage] = [];
  interactionHistoryByStage[stage].push({
    question: props.askHumanRequest?.question || '',
    answer: submitted,
    time: new Date().toLocaleTimeString(),
  });
  emit('submit', submitted);
  answer.value = '';
  otherInput.value = '';
};
</script>

<style scoped>
.progress-panel { margin-bottom: 12px; }

/* 去掉 ACard body 的默认 padding，让 grid 撑满 */
:deep(.ant-card-body) { padding: 0; }

.steps-nav {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 16px 16px 20px;
  overflow-x: auto;
  border-bottom: 1px solid #f0f0f0;
}

.step-item {
  flex: 1;
  text-align: center;
  position: relative;
  cursor: default;
  min-width: 80px;
}
.step-item.clickable { cursor: pointer; }
.step-item.clickable:hover .step-icon { transform: scale(1.08); }

.step-icon {
  width: 48px; height: 48px;
  border-radius: 50%;
  border: 3px solid #dee2e6;
  background: white;
  margin: 0 auto 8px;
  display: flex; align-items: center; justify-content: center;
  font-size: 20px;
  transition: all 0.3s;
}
.step-item.completed .step-icon { border-color: #52c41a; background: #f6ffed; }
.step-item.active .step-icon { border-color: #1890ff; animation: pulse 2s infinite; }
.step-item.failed .step-icon { border-color: #f5222d; background: #fff1f0; }
.step-item.skipped .step-icon { border-color: #d9d9d9; background: #f5f5f5; opacity: 0.6; }
.step-item.viewing .step-icon { box-shadow: 0 0 0 3px rgba(23,162,184,0.4); }

@keyframes pulse {
  0% { box-shadow: 0 0 0 0 rgba(24,144,255,0.4); }
  70% { box-shadow: 0 0 0 8px rgba(24,144,255,0); }
  100% { box-shadow: 0 0 0 0 rgba(24,144,255,0); }
}

.step-title { font-size: 12px; font-weight: 600; color: #495057; margin-bottom: 2px; }
.step-status { font-size: 11px; color: #6c757d; }

.step-connector {
  position: absolute; top: 24px; right: -50%;
  width: 100%; height: 2px; background: #dee2e6; z-index: 0;
}

.main-body {
  display: grid;
  grid-template-columns: 1fr 380px;
  gap: 0;
  border-top: 1px solid #f0f0f0;
  min-height: 220px;
  width: 100%;
  overflow: visible;
}

.left-panel { padding: 16px; border-right: 1px solid #f0f0f0; min-width: 0; overflow-y: auto; }

.right-panel { width: 380px; min-width: 380px; box-sizing: border-box; padding: 12px 16px; background: #fafafa; overflow-y: auto; }

.preview-box { margin-bottom: 16px; text-align: center; background: #f0f7ff; padding: 16px; border-radius: 8px; }

.warnings-list { margin-bottom: 12px; }
.violation-item { font-size: 13px; color: #fa8c16; padding: 3px 0; }

.score-summary { margin-bottom: 12px; padding: 12px; background: #f5f5f5; border-radius: 6px; }

.recommendation { margin-bottom: 12px; padding: 10px 12px; background: #e6f7ff; border-left: 4px solid #1890ff; border-radius: 4px; font-size: 13px; color: #333; }

.question-text { font-size: 16px; font-weight: 500; color: #1890ff; margin-bottom: 16px; white-space: pre-wrap; }

.sub-stage-title { font-size: 14px; font-weight: 600; color: #333; margin-bottom: 10px; display: flex; justify-content: space-between; }
.sub-pct { color: #1890ff; }
.sub-message { margin-top: 8px; font-size: 13px; color: #666; }

.panel-header { font-size: 13px; font-weight: 600; color: #333; margin-bottom: 4px; display: flex; align-items: center; justify-content: space-between; }
.history-badge { font-size: 11px; background: #17a2b8; color: white; padding: 2px 8px; border-radius: 10px; }
.live-badge { font-size: 11px; background: #e9ecef; color: #6c757d; padding: 2px 8px; border-radius: 10px; }
.snapshot-time { font-size: 11px; color: #6c757d; margin-bottom: 8px; }

.params-content { margin-top: 8px; }
.param-card { background: white; border-radius: 8px; padding: 12px; margin-bottom: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
.param-title { font-size: 12px; font-weight: 600; color: #495057; margin-bottom: 8px; padding-bottom: 6px; border-bottom: 1px solid #f0f0f0; }
.param-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
.param-item { display: flex; flex-direction: column; gap: 2px; }
.param-label { font-size: 11px; color: #999; }
.param-value { font-size: 13px; color: #333; font-weight: 500; }
.param-value.success { color: #52c41a; }
.param-value.warning { color: #faad14; }
.score-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; text-align: center; }
.score-num { font-size: 26px; font-weight: bold; }
.score-label { font-size: 12px; color: #666; }
.violations { margin-top: 8px; }
.back-btn-wrap { margin-top: 8px; text-align: center; }

@media (max-width: 768px) {
  .main-body { grid-template-columns: 1fr; }
  .left-panel { border-right: none; border-bottom: 1px solid #f0f0f0; }
}

.interaction-history { margin-bottom: 12px; }
.history-item { background: #f6ffed; border: 1px solid #b7eb8f; border-radius: 6px; padding: 12px; margin-bottom: 12px; }
.history-stage-label { font-size: 12px; font-weight: 600; color: #17a2b8; margin-bottom: 8px; }
.history-image { margin-bottom: 12px; text-align: center; }
.history-warnings { margin-bottom: 12px; }
.history-warnings .warning-item { font-size: 13px; color: #fa8c16; padding: 4px 0; }
.history-q { font-size: 14px; color: #333; margin-bottom: 8px; font-weight: 500; }
.history-a { font-size: 13px; color: #389e0d; font-weight: 500; }
.history-time { font-size: 11px; color: #999; margin-left: 8px; }

/* 历史记录中的方案卡片：只读模式，无选择按钮 */
.scheme-card-new.history-mode {
  opacity: 0.95;
  cursor: default;
}

.scheme-card-new.history-mode.selected {
  border-color: #52c41a;
  background: #f6ffed;
  box-shadow: 0 4px 12px rgba(82, 196, 26, 0.3);
}

/* 历史记录中的徽章样式 */
.badge-recommended {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  background: #faad14;
  color: white;
  font-weight: 600;
}

.badge-original {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  background: #52c41a;
  color: white;
  font-weight: 600;
}

.badge-selected {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  background: #1890ff;
  color: white;
  font-weight: 600;
}

/* 历史交互完整显示样式 */
.history-item-full { background: #f6ffed; border: 1px solid #b7eb8f; border-radius: 8px; padding: 12px; margin-bottom: 16px; }
.history-q-title { font-size: 14px; font-weight: 600; color: #1890ff; margin-bottom: 12px; }
.history-preview-box { margin-bottom: 12px; text-align: center; background: #f0f7ff; padding: 12px; border-radius: 6px; }
.history-warnings { margin-bottom: 12px; }
.history-score { margin-bottom: 12px; padding: 10px; background: #f5f5f5; border-radius: 6px; }
.history-schemes { margin-bottom: 12px; }
.history-schemes h4 { margin: 0 0 12px 0; }
.history-recommendation { margin-bottom: 12px; padding: 8px 12px; background: #e6f7ff; border-left: 4px solid #1890ff; border-radius: 4px; font-size: 13px; }
.history-options { margin-bottom: 12px; }
.history-option-item { padding: 6px 10px; margin-bottom: 4px; border: 1px solid #d9d9d9; border-radius: 4px; font-size: 13px; background: white; }
.history-option-item.selected { border-color: #52c41a; background: #f6ffed; font-weight: 600; }
.history-a { font-size: 14px; color: #389e0d; font-weight: 600; padding-top: 8px; border-top: 1px solid #d9f7be; }
.scheme-card.recommended { border-color: #faad14; background: #fffbe6; }

.history-stage-header {
  font-size: 13px;
  font-weight: 600;
  color: #17a2b8;
  padding: 8px 0 12px;
  border-bottom: 1px solid #e9ecef;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
}

.ask-human-banner {  background: #fff7e6;
  border: 1px solid #ffd591;
  border-radius: 6px;
  padding: 8px 12px;
  font-size: 13px;
  color: #d46b08;
  font-weight: 600;
  margin-bottom: 12px;
  animation: pulse-banner 1.5s ease-in-out infinite;
}
@keyframes pulse-banner {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

/* 自动完成阶段摘要样式 */
.auto-stage-summary {
  background: #f0f7ff;
  border: 1px solid #91d5ff;
  border-radius: 8px;
  padding: 16px;
}

.summary-title {
  font-size: 14px;
  font-weight: 600;
  color: #1890ff;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #d6e4ff;
}

.summary-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid #e6f7ff;
}

.summary-item:last-child {
  border-bottom: none;
}

.summary-label {
  font-size: 13px;
  color: #666;
  font-weight: 500;
}

.summary-value {
  font-size: 13px;
  color: #262626;
  font-weight: 600;
}

.summary-value.success {
  color: #52c41a;
}

.summary-value.warning {
  color: #faad14;
}

.schemes-container { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 12px; align-items: start; }

/* 新版方案卡片样式（参考图片） */
.schemes-container-new { display: flex; flex-direction: column; gap: 16px; }

.scheme-card-new {
  border: 3px solid #d9d9d9;
  border-radius: 12px;
  padding: 16px;
  background: white;
  transition: all 0.3s;
  position: relative;
}

.scheme-card-new.original { border-color: #52c41a; background: #f6ffed; }
.scheme-card-new.recommended { border-color: #1890ff; background: #e6f7ff; }
.scheme-card-new.selected { border-color: #1890ff; background: #e6f7ff; box-shadow: 0 4px 12px rgba(24, 144, 255, 0.3); }
.scheme-card-new.pending { border-color: #d9d9d9; background: #fafafa; }

.scheme-header-new {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 2px solid #f0f0f0;
}

.scheme-title { display: flex; align-items: center; gap: 8px; }

.scheme-name-new {
  font-size: 16px;
  font-weight: 700;
  color: #262626;
}

.scheme-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 600;
}

.scheme-badge.original-badge { background: #52c41a; color: white; }
.scheme-badge.recommended-badge { background: #faad14; color: white; }

.status-icon {
  font-size: 18px;
}

.status-icon.selected-icon {
  color: #1890ff;
  font-weight: 600;
  font-size: 14px;
}

.scheme-metrics-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-bottom: 16px;
}

.metric-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: #fafafa;
  border-radius: 6px;
}

.metric-label {
  font-size: 13px;
  color: #8c8c8c;
  font-weight: 500;
}

.metric-value {
  font-size: 14px;
  color: #262626;
  font-weight: 600;
}

.select-btn-new {
  width: 100%;
  padding: 10px;
  border-radius: 8px;
  border: 2px solid #1890ff;
  background: white;
  color: #1890ff;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}

.select-btn-new:hover { background: #e6f7ff; }
.select-btn-new.selected { background: #1890ff; color: white; border-color: #1890ff; }
.select-btn-new:disabled { opacity: 0.6; cursor: not-allowed; }

.scheme-card {
  border: 2px solid #dee2e6;
  border-radius: 8px;
  padding: 10px 12px;
  transition: all 0.3s;
}
.scheme-card.optimizing { border-color: #1890ff; background: #f0f7ff; }
.scheme-card.completed { border-color: #d9d9d9; }
.scheme-card.selected { border-color: #52c41a; background: #f6ffed; }

.scheme-header-card { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.scheme-name { font-size: 13px; font-weight: 600; }
.scheme-badge { font-size: 11px; background: #faad14; color: white; padding: 1px 6px; border-radius: 8px; margin-left: 6px; }

.optimizing-text { display: flex; align-items: center; gap: 8px; font-size: 13px; color: #1890ff; margin-bottom: 6px; }
.spinner-small {
  width: 14px; height: 14px;
  border: 2px solid #d9d9d9;
  border-top-color: #1890ff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.progress-bar-container { height: 6px; background: #e9ecef; border-radius: 3px; overflow: hidden; }
.progress-bar-fill { height: 100%; background: linear-gradient(90deg, #108ee9, #87d068); transition: width 0.05s linear; }

.scheme-body { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 8px; }
.scheme-metric { display: flex; flex-direction: column; gap: 2px; }
.scheme-metric-label { font-size: 11px; color: #999; }
.scheme-metric-value { font-size: 13px; font-weight: 600; color: #333; }

.select-btn {
  padding: 3px 10px; border-radius: 4px; border: 1px solid #1890ff;
  background: white; color: #1890ff; cursor: pointer; font-size: 12px;
}
.select-btn:disabled { border-color: #52c41a; color: #52c41a; cursor: default; }
</style>
