// 阶段标签映射
const stageLabels: Record<string, string> = {
  design_proposal: '设计方案',
  fe_analysis: '有限元分析',
  evaluation: '设计评估',
  cad_drawing: 'CAD绘图',
  report_generation: '报告生成',
};

// 阶段消息映射
const stageMessages: Record<string, Record<string, string>> = {
  design_proposal: {
    running: '正在生成设计方案...',
    completed: '设计方案生成完成',
    failed: '设计方案生成失败',
  },
  fe_analysis: {
    running: '正在进行有限元分析...',
    completed: '有限元分析完成',
    failed: '有限元分析失败',
  },
  evaluation: {
    running: '正在评估设计结果...',
    completed: '设计评估完成',
    failed: '设计评估失败',
  },
  cad_drawing: {
    running: '正在生成CAD图纸...',
    completed: 'CAD图纸生成完成',
    failed: 'CAD图纸生成失败',
  },
  report_generation: {
    running: '正在生成设计报告...',
    completed: '设计报告生成完成',
    failed: '设计报告生成失败',
  },
};

/**
 * 获取阶段的中文标签
 */
export function getStageLabel(stage: string): string {
  return stageLabels[stage] || stage;
}

/**
 * 获取阶段和状态的友好消息
 */
export function getStageMessage(stage: string, status: string): string {
  const messages = stageMessages[stage];
  if (messages && messages[status]) {
    return messages[status];
  }
  // 回退到默认格式
  return `[${getStageLabel(stage)}] ${status}`;
}

/**
 * 获取状态对应的颜色
 */
export function getStatusColor(status: string): string {
  const colorMap: Record<string, string> = {
    running: '#1890ff',
    completed: '#52c41a',
    failed: '#f5222d',
    pending: '#faad14',
  };
  return colorMap[status] || '#333';
}
