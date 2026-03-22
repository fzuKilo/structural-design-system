/**
 * Stage Message Localization
 */
export const stageMessages: Record<string, Record<string, string>> = {
  design_proposal: {
    started: '正在生成设计方案...',
    completed: '设计方案生成完成',
    failed: '设计方案生成失败'
  },
  fe_analysis: {
    started: '正在进行有限元分析...',
    completed: '有限元分析完成',
    failed: '有限元分析失败'
  },
  evaluation: {
    started: '正在评估设计质量...',
    completed: '设计评估完成',
    failed: '设计评估失败'
  },
  cad_drawing: {
    started: '正在生成CAD图纸...',
    completed: 'CAD图纸生成完成',
    failed: 'CAD图纸生成失败'
  },
  report_generation: {
    started: '正在生成设计报告...',
    completed: '设计报告生成完成',
    failed: '设计报告生成失败'
  }
}

export const getStageLabel = (stage: string) => {
  const labels: Record<string, string> = {
    design_proposal: '设计方案',
    fe_analysis: '有限元分析',
    evaluation: '设计评估',
    cad_drawing: 'CAD绘图',
    report_generation: '报告生成'
  }
  return labels[stage] || stage
}

export const getStageMessage = (stage: string, status: string) =>
  stageMessages[stage]?.[status] || `${getStageLabel(stage)} ${status}`
