# 集成测试计划

## 文档目的

明确各阶段的集成测试时间点和验收标准，避免将所有测试推迟到阶段10导致的风险。

## 当前问题

原开发规划中：
- 阶段6-9：只做单元测试（不调用LLM）
- 阶段10：第一次做端到端测试（5个Agent一起测试）

风险：
- 问题发现太晚，修复成本高
- 难以定位具体哪个Agent出错
- 可能需要大规模重构

## 改进方案：增量集成测试

采用"开发一个，测试一个"的策略，每完成一个Agent立即验证其与LLM/其他Agent的集成。

---

## 测试时间点和验收标准

### 阶段6后：StructuralDesignAgent集成测试

时间点：2026-02-11（今天）

测试内容：
1. 配置LLM（检查config.toml中的API key）
2. 编写集成测试脚本：`tests/integration/test_design_agent_integration.py`
3. 实际调用LLM生成设计方案

测试用例：
```python
# 测试1：简支梁设计
输入："设计一个6米跨度的简支梁，承受10kN/m均布荷载"
预期输出：
- 包含type字段（"beam"）
- 包含完整的geometry、material、loads、constraints
- 通过validate_design_proposal()验证

# 测试2：缺失参数交互
输入："设计一个简支梁"
预期行为：
- Agent调用AskHuman询问缺失参数（跨度、荷载等）
- 用户补充后生成完整方案
```

验收标准：
- LLM能够成功调用
- 输出JSON格式正确
- 包含所有必需字段
- 数值合理（如跨度6m，截面高度约0.4-0.6m）

预计时间：30分钟 - 1小时

---

### 阶段7后：StructuralDesignAgent → FEAnalysisAgent集成测试

时间点：阶段7完成后（预计2026-02-12）

测试内容：
1. 测试两个Agent的数据传递
2. 验证FEAnalysisAgent能否正确解析DesignProposal
3. 验证FEAnalysisTool能否正确调用

测试用例：
```python
# 端到端测试（2个Agent）
步骤1：StructuralDesignAgent生成设计方案
步骤2：FEAnalysisAgent接收方案并进行有限元分析
预期输出：
- AnalysisResults包含max_displacement、max_stress等
- code_check显示是否符合规范
```

验收标准：
- Agent间数据传递无误
- FEAnalysisTool成功调用OpenSeesPy
- 分析结果数值合理
- 规范校核逻辑正确

预计时间：30分钟

---

### 阶段8后：CADDrawingAgent集成测试

时间点：阶段8完成后（预计2026-02-13）

测试内容：
1. 测试CADDrawingAgent能否接收DesignProposal
2. 验证DXF文件生成
3. 验证图纸内容正确性

测试用例：
```python
# 端到端测试（3个Agent）
步骤1：StructuralDesignAgent生成设计方案
步骤2：FEAnalysisAgent进行分析
步骤3：CADDrawingAgent生成图纸
预期输出：
- 生成DXF文件
- 图纸包含梁的几何、支座、尺寸标注
- 可在AutoCAD/DraftSight中打开
```

验收标准：
- DXF文件生成成功
- 图纸内容与设计方案一致
- 图纸符合制图规范

预计时间：30分钟

---

### 阶段9后：EvaluationAgent集成测试

时间点：阶段9完成后（预计2026-02-14）

测试内容：
1. 测试EvaluationAgent能否接收DesignProposal和AnalysisResults
2. 验证量化评估逻辑
3. 验证评分和等级计算

测试用例：
```python
# 端到端测试（4个Agent）
步骤1-3：同上
步骤4：EvaluationAgent进行量化评估
预期输出：
- 综合得分（0-100分）
- 等级（A+/A/B+/B/C+/C/D）
- 4维度详细评分（经济性、效率、安全性、可持续性）
- 改进建议（如果评分<75）
```

验收标准：
- 评分计算逻辑正确
- 各维度指标合理
- 改进建议有针对性

预计时间：30分钟

---

### 阶段10：完整端到端测试

时间点：阶段10完成后（预计2026-02-15）

测试内容：
1. 测试完整的5个Agent工作流
2. 验证PlanningFlow编排逻辑
3. 验证智能决策机制（评分<75时询问用户）

测试用例：
```python
# 完整端到端测试
输入："设计一个6米跨度的简支梁，承受10kN/m均布荷载"
预期流程：
1. StructuralDesignAgent：生成设计方案
2. FEAnalysisAgent：有限元分析
3. EvaluationAgent：量化评估
4. 决策点：评分>=75，继续；评分<75，询问用户
5. CADDrawingAgent：生成图纸
6. ReportGenerationAgent：生成报告

预期输出：
- 完整的设计报告（Markdown）
- DXF图纸
- 静态和交互式可视化
- 量化评估结果
```

验收标准：
- 完整流程无错误
- 所有输出文件生成
- 用户体验流畅
- 处理时间合理（<5分钟）

预计时间：1-2小时

---

## 测试环境要求

### 必需配置
1. LLM API配置（config.toml）
   - GPT-4o / Claude 3.5 Sonnet / DeepSeek
   - API key有效
   - 有足够的配额

2. OpenSeesPy环境
   - 已安装并可正常运行

3. ezdxf库
   - 已安装（阶段8前）

### 测试数据
使用标准测试用例：
- 简支梁：6m跨度，10kN/m均布荷载
- 悬臂梁：3m跨度，5kN/m均布荷载（阶段10.5架构验证）

---

## 测试记录

### 阶段6集成测试
- 日期：2026-02-11 & 2026-02-15
- 执行人：Claude Code + 用户A
- 结果：通过
- LLM：DeepSeek (deepseek-chat)
- 测试用例：6米简支梁，10kN/m均布荷载，C30混凝土
- 生成结果：
  - 结构类型: beam
  - 跨度: 6.0m
  - 截面尺寸: 0.3m × 0.5m (宽×高)
  - 跨高比: 12.0 (合理范围: 10-15)
  - 材料: C30混凝土 (E=30GPa, nu=0.2, fy=14.3MPa)
  - 荷载: -10000 N/m (均布荷载)
  - 支座类型: simply_supported
  - 单元数: 20
- 验证结果：
  - JSON格式正确
  - 包含所有必需字段 (type, geometry, material, loads, constraints)
  - 数值合理，符合工程实践
  - 跨高比在合理范围内
- 问题记录：
  1. 初始API调用参数错误 (task vs request) - 已修复
  2. JSON提取失败 (未识别OpenManus执行日志格式) - 已修复
  3. AskHuman工具未正确注册到available_tools - 已修复
  4. 外部验证循环与OpenManus内部循环冲突 - 已移除外部循环
  5. 相对导入导致ModuleNotFoundError - 已改为绝对导入
- 修复措施：
  1. 修改StructuralDesignAgent.run()参数名为request
  2. 更新extract_design_proposal()支持OpenManus日志格式
  3. FEAnalysisAgent.__init__()中添加: self.available_tools = ToolCollection(*all_tools)
  4. 简化StructuralDesignAgent.run()，移除外部验证循环
  5. fe_analysis_tool.py使用绝对导入
- AskHuman测试记录（2026-02-15）：
  - 测试方式：集成测试脚本交互式输入
  - 输入："设计一个简支梁"
  - 用户补充：跨度6m，均布荷载10kN/m，楼面梁
  - 结果：Agent正确调用AskHuman询问参数，获取后生成设计方案
  - 验证：测试通过，AskHuman工具正常工作
- Token使用：Input=2753, Completion=242, Total=2995 (基础测试)
- 执行时间：约12秒 (基础测试) / 约2分钟 (含AskHuman交互)

### 阶段7集成测试
- 日期：2026-02-21 - 2026-02-22
- 执行人：Lin-0408-Yiran
- 结果：通过
- LLM：DeepSeek (deepseek-chat)
- 测试用例：6米简支梁，10kN/m均布荷载，C30混凝土

**测试流程**：
1. StructuralDesignAgent生成设计方案
2. FEAnalysisAgent接收方案并进行有限元分析
3. 支持循环模式：code_check不通过时自动询问用户改进

**测试结果**：
- AnalysisResults包含：max_displacement, max_stress, max_moment, max_shear
- code_check显示：compliant = True/False
- 12m跨度简支梁测试：3轮改进后通过规范校核

**问题记录**：
1. extract_analysis_results正则无法匹配多行JSON - 已修复（Pattern 4）
2. LLM调用fe_analysis工具时参数传递格式不匹配 - 已修复（添加design_proposal参数）
3. 循环模式轮次显示错误（第2轮显示第1/3轮）- 已修复（添加start_loop_count参数）
4. analysis_prompt双重嵌套 - 已修复（简化prompt）
5. validate_analysis_results显示原始方案 - 已修复（从detailed_results提取最终方案）

**修复措施**：
1. fe_analysis_agent.py：添加Pattern 4处理错误JSON，增强JSON完整性检查
2. fe_analysis_tool.py：添加design_proposal参数支持，统一使用json.dumps输出
3. fe_analysis_agent.py：添加start_loop_count参数传递轮次信息
4. fe_analysis_agent.py：简化analysis_prompt
5. fe_analysis_agent.py：从analysis_results.detailed_results提取最终设计方案

**Token使用**：约2000-4000 tokens/测试（含循环改进）
**执行时间**：约15-30秒（单次分析）/ 纳秒-2分钟（含循环改进）

---

### 阶段8集成测试
- 日期：2026-02-23
- 执行人：Lin-0408-Yiran
- 结果：通过
- LLM：DeepSeek (deepseek-chat)
- 测试用例：6米简支梁，10kN/m均布荷载，C30混凝土

**测试流程**：
1. StructuralDesignAgent生成设计方案
2. FEAnalysisAgent进行有限元分析
3. CADDrawingAgent生成CAD图纸（立面图、平面图、详图）

**测试结果**：
- 生成DXF文件成功
- 图纸包含：梁几何、支座符号、尺寸标注、中文标注
- 可在AutoCAD/DraftSight中正常打开

**问题记录**：
1. StructuralDesignAgent无法提取JSON - 已修复（修改系统提示词）
2. CADDrawingTool缺少to_param()方法 - 已修复（创建base.py统一BaseTool导入）
3. CADDrawingTool返回格式错误 - 已修复（使用json.dumps替代str()）
4. 相对导入导致ModuleNotFoundError - 已修复（改用绝对导入）
5. 标注显示值100倍放大（6000显示600000）- 已修复（修改EZDXF dimlfac=1.0）

**修复措施**：
1. structural_design_agent.py：修改系统提示词强制LLM使用create_chat_completion
2. structural_app/tool/base.py：创建统一BaseTool基类
3. cad_drawing_tool.py：使用json.dumps输出标准JSON格式
4. cad_drawing_tool.py：改用绝对导入
5. beam_drawer.py：在三个draw方法中修改EZDXF dimlfac从100改为1.0

**Git提交**：53f622f (阶段8集成测试修复), f3bace6 (标注显示修复)
**输出文件**：
- beam_plan_*.dxf
- beam_elevation_*.dxf
- beam_detail_*.dxf

---

### 阶段9集成测试
- 日期：____
- 执行人：____
- 结果：通过 / 失败
- 问题记录：____
- 修复措施：____

### 阶段10端到端测试
- 日期：____
- 执行人：____
- 结果：通过 / 失败
- 问题记录：____
- 修复措施：____

---

## 成本估算

### 时间成本
- 阶段6-9集成测试：每次30分钟，共2小时
- 阶段10端到端测试：1-2小时
- 总计：3-4小时

### API成本
- 每次集成测试：1-3次LLM调用
- 阶段6-10：约20-30次LLM调用
- 预计成本：$0.5 - $2（使用GPT-4o）

### 收益
- 早期发现问题，避免大规模重构
- 降低阶段10的调试时间（从预计2-3天降至半天）
- 提高开发信心和代码质量

---

## 总结

采用增量集成测试策略：
- 每完成一个Agent立即测试
- 逐步验证Agent间协作
- 降低阶段10的风险
- 总时间成本增加3-4小时，但大幅降低返工风险

建议：从阶段6集成测试开始执行此计划。

---

最后更新：2026-02-25
更新人：Claude Code
