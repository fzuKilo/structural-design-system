# 如何添加新的结构类型

## 文档信息

- **版本**: v2.0
- **创建日期**: 2026-02-07
- **最后更新**: 2026-02-21
- **适用对象**: 系统开发者、扩展开发者
- **策略**: 方案B - 循序渐进 + 友好错误提示

---

## 1. 概述

本文档详细说明如何在不修改 Agent 代码的前提下，为系统添加新的结构类型。

### ⚠️ 关键提醒：5个工厂注册缺一不可

添加新结构类型时，必须在以下**5个工厂**中注册：
1. AnalyzerFactory（有限元分析）
2. DrawerFactory（CAD绘图）
3. EvaluatorFactory（设计评估）
4. **VisualizerFactory（可视化）** ⚠️ **容易遗漏，会导致报告和可视化缺失**
5. **ReporterFactory（报告生成）** ⚠️ **容易遗漏，会导致报告生成失败**

---

### 1.1 核心原则

- **Agent 代码零修改**：所有 Agent 保持通用，不针对特定结构类型
- **类型区分在 Tool 层**：通过工厂模式实现类型路由
- **标准化接口**：遵循抽象基类定义的接口规范

### 1.3 添加新结构类型的策略

本系统采用**方案B：循序渐进 + 友好错误提示**策略：

#### 友好错误提示
当 LLM 生成未支持的结构类型时，系统不会直接报错，而是返回友好的提示：

```json
{
  "status": "error",
  "error": "当前未支持的结构类型: arch。可用类型: ['beam', 'cantilever_beam', 'continuous_beam', 'truss', 'frame']"
}
```

这样可以让：
- **LLM 知道哪些类型可用**，在后续生成中避免错误
- **用户理解当前限制**，不会困惑于神秘报错
- **开发者有清晰的扩展路径**，按需实现

#### 何时需要实现新类型
| 场景 | 是否需要实现 | 说明 |
|------|-------------|------|
| LLM 生成 `type: "plate"` 报错 | ⚠️ 可选 | 板结构较复杂，视需求 |
| LLM 生成 `type: "arch"` 报错 | ⚠️ 可选 | 拱结构特殊，视需求 |

---

### 1.4 需要实现的组件

添加新结构类型需要实现以下 4 个组件：

1. **Analyzer**：有限元分析器（OpenSeesPy 建模）
2. **Drawer**：CAD 绘图器（ezdxf 绘图）
3. **Evaluator**：设计评估器（4 维度评估）
4. **Visualizer**：可视化器（matplotlib/Plotly 可视化）⚠️ **容易遗漏**
5. **Reporter**：报告生成器（Markdown 报告）⚠️ **容易遗漏**

**注意**：对于梁类结构（简支梁、悬臂梁、连续梁），可以复用 `BeamVisualizer` 和 `BeamReporter`，无需创建新类。

---

## 2.1 新结构类型添加检查清单

在开始实现前，请先确认：

- [ ] **确认LLM确实会生成该类型**（查看LLM输出日志）
- [ ] **评估实现成本**（参考下方时间估算）
- [ ] **确定是否需要Drawer**（如果只要分析功能，可暂不实现）
- [ ] **确定是否需要Evaluator**（如果只要分析功能，可暂不实现）

---

## 2.2 实战示例：添加悬臂梁

本节以添加悬臂梁（Cantilever Beam）为例，展示完整的扩展流程。

### 2.2.1 步骤概览

```
1. 实现 CantileverBeamAnalyzer
2. 实现 CantileverBeamDrawer
3. 实现 CantileverBeamEvaluator
4. 在工厂类中注册
5. 编写单元测试
6. 端到端测试
```

**预计时间**：1-2 天（简单类型如悬臂梁）；3-5 天（中等复杂度如框架）

---

## 2.3 友好错误提示说明

**注意**：根据系统策略，如果遇到未支持的结构类型，系统会返回友好提示：

```
"Unknown structure type: 'arch'. Available types: ['beam', 'cantilever_beam', 'continuous_beam', 'truss', 'frame']"
```

这个提示会被 LLM 读取，在下一轮生成中 LLM 会知道哪些类型可用，从而避免持续错误。

## 2.2 步骤1：实现 CantileverBeamAnalyzer

### 2.2.1 创建文件

```bash
# 创建新文件
touch structural_app/tool/analyzers/cantilever_beam_analyzer.py
```

### 2.2.2 实现代码

```python
# structural_app/tool/analyzers/cantilever_beam_analyzer.py
from typing import Dict
import openseespy.opensees as ops
from structural_app.tool.analyzers.base_analyzer import StructureAnalyzer, AnalysisResults

class CantileverBeamAnalyzer(StructureAnalyzer):
    """悬臂梁分析器"""
    
    def __init__(self):
        super().__init__()
        self.nodes = []
        self.elements = []
    
    def build_model(self, design: Dict) -> bool:
        """构建悬臂梁有限元模型"""
        # 提取参数
        length = design["geometry"]["length"]
        width = design["geometry"]["width"]
        height = design["geometry"]["height"]
        n_elements = design["geometry"].get("n_elements", 20)
        
        E = design["material"]["E"]
        nu = design["material"]["nu"]
        
        # 计算截面属性
        A = width * height
        I = (width * height**3) / 12
        
        # 初始化模型
        ops.wipe()
        ops.model('basic', '-ndm', 2, '-ndf', 3)
        
        # 创建节点
        dx = length / n_elements
        for i in range(n_elements + 1):
            x = i * dx
            ops.node(i + 1, x, 0.0)
            self.nodes.append(i + 1)
        
        # 边界条件：左端固定（悬臂梁特征）
        ops.fix(1, 1, 1, 1)  # 固定端：x、y、转角全约束
        
        # 创建单元
        for i in range(n_elements):
            ops.element('elasticBeamColumn', i + 1, i + 1, i + 2, A, E, I, 1)
            self.elements.append(i + 1)
        
        # 施加荷载
        ops.timeSeries('Linear', 1)
        ops.pattern('Plain', 1, 1)
        
        # 均布荷载
        if "distributed" in design["loads"]:
            for load in design["loads"]["distributed"]:
                q = load["q"]
                for i in range(n_elements):
                    ops.eleLoad('-ele', i + 1, '-type', '-beamUniform', q, 0.0)
        
        # 集中荷载
        if "point" in design["loads"]:
            for load in design["loads"]["point"]:
                node_id = load["node"]
                Fy = load["Fy"]
                ops.load(node_id, 0.0, Fy, 0.0)
```

    
    def analyze(self) -> AnalysisResults:
        """运行有限元分析"""
        # 配置求解器
        ops.system('BandGeneral')
        ops.numberer('RCM')
        ops.constraints('Plain')
        ops.integrator('LoadControl', 1.0)
        ops.algorithm('Linear')
        ops.analysis('Static')
        
        # 求解
        ops.analyze(1)
        
        # 提取结果
        displacements = []
        moments = []
        shears = []
        
        for node_id in self.nodes:
            disp = ops.nodeDisp(node_id)
            displacements.append({
                "node": node_id,
                "ux": disp[0],
                "uy": disp[1],
                "rotation": disp[2]
            })
        
        for elem_id in self.elements:
            forces = ops.eleForce(elem_id)
            moments.append({
                "element": elem_id,
                "M_i": forces[2],
                "M_j": forces[5]
            })
            shears.append({
                "element": elem_id,
                "V_i": forces[1],
                "V_j": forces[4]
            })
        
        return {
            "displacements": displacements,
            "moments": moments,
            "shears": shears
        }
    
    def check_code(self, results: AnalysisResults) -> Dict:
        """规范校核（悬臂梁特定）"""
        # 提取最大值
        max_disp = max([abs(d["uy"]) for d in results["displacements"]])
        max_moment = max([abs(m["M_i"]) for m in results["moments"]] + 
                        [abs(m["M_j"]) for m in results["moments"]])
        
        # 悬臂梁挠度限值：L/250
        length = self.design["geometry"]["length"]
        deflection_limit = length / 250
        
        violations = []
        if max_disp > deflection_limit:
            violations.append(f"挠度超限：{max_disp*1000:.2f}mm > {deflection_limit*1000:.2f}mm")
        
        return {
            "compliant": len(violations) == 0,
            "violations": violations,
            "safety_factors": {
                "deflection": deflection_limit / max_disp if max_disp > 0 else float('inf')
            }
        }
```


### 2.2.3 关键点说明

**与简支梁的区别**：
- 边界条件：`ops.fix(1, 1, 1, 1)` 固定端全约束
- 挠度限值：悬臂梁为 L/250，简支梁为 L/400
- 最大弯矩位置：悬臂梁在固定端，简支梁在跨中

---

## 2.3 步骤2：实现 CantileverBeamDrawer

### 2.3.1 创建文件

```bash
touch structural_app/tool/drawers/cantilever_beam_drawer.py
```

### 2.3.2 实现代码

```python
# structural_app/tool/drawers/cantilever_beam_drawer.py
from typing import Dict
import ezdxf
from datetime import datetime
from structural_app.tool.drawers.base_drawer import StructureDrawer

class CantileverBeamDrawer(StructureDrawer):
    """悬臂梁绘图器"""
    
    def draw_elevation(self, design: Dict) -> str:
        """绘制悬臂梁立面图"""
        # 创建 DXF 文档
        doc = ezdxf.new('R2010')
        msp = doc.modelspace()
        
        # 提取参数
        length = design["geometry"]["length"]
        height = design["geometry"]["height"]
        
        # 绘制梁轮廓
        msp.add_line((0, 0), (length, 0))  # 底边
        msp.add_line((length, 0), (length, height))  # 右边
        msp.add_line((length, height), (0, height))  # 顶边
        msp.add_line((0, height), (0, 0))  # 左边
        
        # 绘制固定端支座符号（左端）
        self._draw_fixed_support(msp, 0, 0)
        
        # 添加尺寸标注
        msp.add_text(
            f'L={length}m',
            dxfattribs={'height': 0.1}
        ).set_pos((length/2, -0.3), align='CENTER')
        
        # 保存文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"output/drawings/cantilever_beam_elevation_{timestamp}.dxf"
        doc.saveas(filename)
        
        return filename
    
    def _draw_fixed_support(self, msp, x, y):
        """绘制固定端支座符号"""
        # 绘制三角形
        msp.add_line((x, y), (x-0.2, y-0.2))
        msp.add_line((x, y+0.6), (x-0.2, y+0.8))
        # 绘制斜线填充
        for i in range(5):
            msp.add_line((x-0.2, y-0.2+i*0.25), (x-0.3, y-0.3+i*0.25))
```


---

## 2.4 步骤3：实现 CantileverBeamEvaluator

### 2.4.1 创建文件

```bash
touch structural_app/tool/evaluators/cantilever_beam_evaluator.py
```

### 2.4.2 实现代码

```python
# structural_app/tool/evaluators/cantilever_beam_evaluator.py
from typing import Dict
from structural_app.tool.evaluators.base_evaluator import DesignEvaluator

class CantileverBeamEvaluator(DesignEvaluator):
    """悬臂梁评估器"""
    
    def evaluate_economy(self, design: Dict, results: Dict) -> Dict:
        """经济性评估"""
        # 计算材料用量
        length = design["geometry"]["length"]
        width = design["geometry"]["width"]
        height = design["geometry"]["height"]
        volume = length * width * height
        
        # 材料用量指数（相对于理论最优值）
        material_usage_index = volume / (length * 0.2 * 0.4)  # 假设理论最优截面
        
        # 评分：材料用量越少越好
        score = max(0, 100 - (material_usage_index - 1) * 50)
        
        return {
            "score": score,
            "indicators": {
                "material_usage_index": material_usage_index,
                "volume_m3": volume
            }
        }
```

    
    def evaluate_efficiency(self, design: Dict, results: Dict) -> Dict:
        """结构效率评估"""
        # 计算平均应力利用率
        max_stress = results["results"]["max_stress_MPa"]
        fy = design["material"]["fy"] / 1e6  # 转换为 MPa
        utilization = max_stress / fy
        
        # 评分：利用率在 0.6-0.8 之间最优
        if 0.6 <= utilization <= 0.8:
            score = 100
        elif utilization < 0.6:
            score = 100 - (0.6 - utilization) * 100
        else:
            score = 100 - (utilization - 0.8) * 200
        
        return {
            "score": max(0, score),
            "indicators": {
                "average_utilization": utilization
            }
        }
    
    def evaluate_safety(self, design: Dict, results: Dict) -> Dict:
        """安全性评估"""
        safety_factors = results["code_check"]["safety_factors"]
        deflection_sf = safety_factors["deflection"]
        
        # 评分：安全系数越大越好，但过大浪费
        if deflection_sf >= 2.0:
            score = 100
        else:
            score = deflection_sf * 50
        
        return {
            "score": min(100, score),
            "indicators": {
                "deflection_safety_factor": deflection_sf
            }
        }
    
    def evaluate_sustainability(self, design: Dict, results: Dict) -> Dict:
        """可持续性评估"""
        # 简化评估：基于材料用量
        volume = design["geometry"]["length"] * design["geometry"]["width"] * design["geometry"]["height"]
        carbon_emission = volume * 2400 * 0.11  # 混凝土碳排放系数
        
        score = max(0, 100 - carbon_emission / 10)
        
        return {
            "score": score,
            "indicators": {
                "carbon_emission_kg": carbon_emission
            }
        }
```


---

## 2.5 步骤4：在工厂类中注册 ⚠️ 关键步骤

### 2.5.1 注册 Analyzer

```python
# structural_app/tool/analyzers/analyzer_factory.py
from structural_app.tool.analyzers.cantilever_beam_analyzer import CantileverBeamAnalyzer

# 在文件末尾添加注册
AnalyzerFactory.register("cantilever_beam", CantileverBeamAnalyzer)
```

### 2.5.2 注册 Drawer

```python
# structural_app/tool/drawers/drawer_factory.py
from structural_app.tool.drawers.cantilever_beam_drawer import CantileverBeamDrawer

# 在文件末尾添加注册
DrawerFactory.register("cantilever_beam", CantileverBeamDrawer)
```

### 2.5.3 注册 Evaluator

```python
# structural_app/tool/evaluators/evaluator_factory.py
from structural_app.tool.evaluators.cantilever_beam_evaluator import CantileverBeamEvaluator

# 在文件末尾添加注册
EvaluatorFactory.register("cantilever_beam", CantileverBeamEvaluator)
```

### 2.5.4 注册 Visualizer ⚠️ **容易遗漏**

```python
# structural_app/tool/visualizations/visualizer_factory.py

# 方案A：复用 BeamVisualizer（推荐，适用于梁类结构）
VisualizerFactory.register("cantilever_beam", BeamVisualizer)

# 方案B：创建独立 Visualizer（如果需要定制可视化样式）
# from structural_app.tool.visualizations.cantilever_beam_visualizer import CantileverBeamVisualizer
# VisualizerFactory.register("cantilever_beam", CantileverBeamVisualizer)
```

### 2.5.5 注册 Reporter ⚠️ **容易遗漏**

```python
# structural_app/tool/reports/reporter_factory.py

# 方案A：复用 BeamReporter（推荐，适用于梁类结构）
ReporterFactory.register("cantilever_beam", BeamReporter)

# 方案B：创建独立 Reporter（如果需要定制报告格式）
# from structural_app.tool.reports.cantilever_beam_reporter import CantileverBeamReporter
# ReporterFactory.register("cantilever_beam", CantileverBeamReporter)
```

**重要提示**：
- ✅ 注册的 key（"cantilever_beam"）必须与 LLM 输出的 `type` 字段一致
- ✅ 确保在系统启动时执行注册代码
- ⚠️ **VisualizerFactory 和 ReporterFactory 注册最容易遗漏**，会导致报告生成失败

---


## 2.6 步骤5：编写单元测试

### 2.6.1 创建测试文件

```bash
touch tests/test_cantilever_beam_analyzer.py
```

### 2.6.2 测试代码示例

```python
# tests/test_cantilever_beam_analyzer.py
import pytest
from structural_app.tool.analyzers.cantilever_beam_analyzer import CantileverBeamAnalyzer

def test_cantilever_beam_analysis():
    """测试悬臂梁分析"""
    design = {
        "type": "cantilever_beam",
        "geometry": {
            "length": 3.0,
            "width": 0.3,
            "height": 0.5,
            "n_elements": 10
        },
        "material": {
            "E": 30e9,
            "nu": 0.2,
            "fy": 235e6
        },
        "loads": {
            "distributed": [{"q": -5000, "direction": "y"}]
        }
    }
    
    analyzer = CantileverBeamAnalyzer()
    results = analyzer.run_full_analysis(design)
    
    # 验证结果
    assert results.status == "success"
    assert results.max_displacement_mm > 0
    assert results.max_moment_kNm > 0
```


### 2.6.3 运行测试

```bash
# 运行单元测试
pytest tests/test_cantilever_beam_analyzer.py -v

# 运行所有测试
pytest tests/ -v
```

---

## 2.7 步骤6：端到端测试

### 2.7.1 测试用例

```python
# 用户输入
user_input = "我需要设计一根3米长的悬臂梁，承受5kN/m的均布荷载"

# 运行完整流程
result = await planning_flow.execute(user_input)

# 验证输出
assert "cantilever_beam" in result
assert "design_report" in result
assert "drawings" in result
```

### 2.7.2 预期结果

- ✅ StructuralDesignAgent 自动识别为悬臂梁（type: "cantilever_beam"）
- ✅ FEAnalysisAgent 成功调用 CantileverBeamAnalyzer
- ✅ CADDrawingAgent 成功调用 CantileverBeamDrawer
- ✅ EvaluationAgent 成功调用 CantileverBeamEvaluator
- ✅ 生成完整的设计报告和图纸

---


## 3. 验证清单

### 3.1 代码验证

- [ ] **Analyzer 实现**
  - [ ] 继承自 `StructureAnalyzer`
  - [ ] 实现 `build_model()` 方法
  - [ ] 实现 `analyze()` 方法
  - [ ] 实现 `check_code()` 方法
  - [ ] 边界条件正确

- [ ] **Drawer 实现**
  - [ ] 继承自 `StructureDrawer`
  - [ ] 实现 `draw_elevation()` 方法
  - [ ] 生成有效的 DXF 文件
  - [ ] 支座符号正确

- [ ] **Evaluator 实现**
  - [ ] 继承自 `DesignEvaluator`
  - [ ] 实现 4 个评估方法
  - [ ] 评分逻辑合理

- [ ] **工厂注册** ⚠️ **最容易出错的环节**
  - [ ] 在 AnalyzerFactory 中注册
  - [ ] 在 DrawerFactory 中注册
  - [ ] 在 EvaluatorFactory 中注册
  - [ ] **在 VisualizerFactory 中注册** ⚠️ **容易遗漏**
  - [ ] **在 ReporterFactory 中注册** ⚠️ **容易遗漏**
  - [ ] 注册 key 与 type 字段一致
  - [ ] 验证注册成功：`VisualizerFactory.get_available_types()` 和 `ReporterFactory.get_available_types()`


### 3.2 架构验证

- [ ] **Agent 代码零修改**
  - [ ] StructuralDesignAgent 代码未修改
  - [ ] FEAnalysisAgent 代码未修改
  - [ ] EvaluationAgent 代码未修改
  - [ ] CADDrawingAgent 代码未修改
  - [ ] ReportGenerationAgent 代码未修改

- [ ] **类型路由正常**
  - [ ] LLM 能够识别新结构类型
  - [ ] 工厂类能够正确路由
  - [ ] Tool 层调用正确的实现类

### 3.3 功能验证

- [ ] **单元测试**
  - [ ] Analyzer 测试通过
  - [ ] Drawer 测试通过
  - [ ] Evaluator 测试通过
  - [ ] 测试覆盖率 > 80%

- [ ] **端到端测试**
  - [ ] 完整流程运行成功
  - [ ] 生成正确的分析结果
  - [ ] 生成有效的图纸文件
  - [ ] 生成完整的报告

---


## 4. 常见问题

### 4.1 LLM 无法识别新结构类型

**问题**：用户输入后，LLM 输出的 `type` 字段不是预期的值。

**解决方案**：
1. 在 StructuralDesignAgent 的 system prompt 中添加新类型的描述
2. 提供示例输出格式
3. 使用更明确的用户输入（如"悬臂梁"而非"梁"）

### 4.2 工厂类找不到注册的类型

**问题**：运行时报错 `Unknown structure type: cantilever_beam`

**常见原因**：
1. ❌ 忘记在某个工厂中注册（最常见：VisualizerFactory）
2. ❌ 注册的 key 与 type 字段不一致（大小写敏感）
3. ❌ 导入路径错误
4. ❌ 注册代码未执行

**解决方案**：
1. **检查所有4个工厂的注册**：
   ```python
   # 验证注册状态
   from structural_app.tool.analyzers.analyzer_factory import AnalyzerFactory
   from structural_app.tool.drawers.drawer_factory import DrawerFactory
   from structural_app.tool.evaluators.evaluator_factory import EvaluatorFactory
   from structural_app.tool.visualizations.visualizer_factory import VisualizerFactory

   print("Analyzer:", AnalyzerFactory.get_available_types())
   print("Drawer:", DrawerFactory.get_available_types())
   print("Evaluator:", EvaluatorFactory.get_available_types())
   print("Visualizer:", VisualizerFactory.get_available_types())  # ⚠️ 最容易遗漏
   ```

2. **确认注册的 key 与 type 字段完全一致**（大小写敏感）
3. **检查导入路径是否正确**
4. **确保注册代码在工厂文件末尾执行**

**症状对照表**：

| 症状 | 缺失的工厂注册 | 影响 |
|------|--------------|------|
| 有限元分析失败 | AnalyzerFactory | 无法进行结构分析 |
| CAD图纸生成失败 | DrawerFactory | 无法生成DXF文件 |
| 设计评估失败 | EvaluatorFactory | 无法生成评分报告 |
| **可视化缺失** | **VisualizerFactory** ⚠️ | **无可视化图表** |
| **报告生成失败或降级** | **ReporterFactory** ⚠️ | **报告生成失败，LLM可能自动降级为beam** |

### 4.3 OpenSeesPy 建模失败

**问题**：有限元分析时报错或结果异常。

**解决方案**：
1. 检查边界条件是否正确
2. 验证单元类型和参数
3. 确认荷载施加方式
4. 参考 BeamAnalyzer 的实现


### 4.4 DXF 文件无法打开

**问题**：生成的 DXF 文件在 CAD 软件中无法打开。

**解决方案**：
1. 检查 ezdxf 版本兼容性
2. 使用 `doc.saveas()` 而非手动写入
3. 确认文件路径存在
4. 参考 BeamDrawer 的实现

---

## 5. 最佳实践

### 5.1 代码组织

```
structural_app/tool/
├── analyzers/
│   ├── base_analyzer.py              # 抽象基类
│   ├── beam_analyzer.py              # 简支梁
│   ├── cantilever_beam_analyzer.py   # 悬臂梁
│   ├── continuous_beam_analyzer.py   # 连续梁
│   ├── truss_analyzer.py             # 桁架
│   ├── frame_analyzer.py             # 框架
│   └── analyzer_factory.py           # 工厂类
├── drawers/
│   ├── base_drawer.py
│   ├── beam_drawer.py
│   ├── cantilever_beam_drawer.py
│   ├── continuous_beam_drawer.py
│   ├── truss_drawer.py
│   ├── frame_drawer.py
│   └── drawer_factory.py
├── evaluators/
│   ├── base_evaluator.py
│   ├── beam_evaluator.py
│   ├── cantilever_beam_evaluator.py
│   ├── continuous_beam_evaluator.py
│   ├── truss_evaluator.py
│   ├── frame_evaluator.py
│   └── evaluator_factory.py
├── visualizations/
│   ├── base_visualizer.py
│   ├── beam_visualizer.py            # 复用于 beam/cantilever_beam/continuous_beam
│   ├── truss_visualizer.py
│   ├── frame_visualizer.py
│   └── visualizer_factory.py
└── reports/
    ├── base_reporter.py
    ├── beam_reporter.py              # 复用于 beam/cantilever_beam/continuous_beam
    ├── truss_reporter.py
    ├── frame_reporter.py
    └── reporter_factory.py
```


### 5.2 命名规范

- **类名**：使用 PascalCase，如 `CantileverBeamAnalyzer`
- **文件名**：使用 snake_case，如 `cantilever_beam_analyzer.py`
- **注册 key**：使用 snake_case，如 `"cantilever_beam"`
- **保持一致性**：同一结构类型的命名前缀保持一致

### 5.3 测试策略

1. **单元测试优先**：先确保每个组件独立工作
2. **使用真实数据**：测试用例应基于实际工程案例
3. **边界条件测试**：测试极端情况（如超长跨度、超大荷载）
4. **对比验证**：与手算或其他软件结果对比

### 5.4 文档要求

- 在类的 docstring 中说明结构类型特点
- 注释关键的建模逻辑（如边界条件）
- 提供使用示例
- 说明与其他类型的区别

---


## 6. 参考资料

### 6.1 相关文档

- **架构设计文档**：`docs/agent_architecture.md`
- **开发规划**：`docs/OpenManus开发规划2.3.md`
- **协作指南**：`docs/COLLABORATION.md`

### 6.2 代码参考

- **BeamAnalyzer**：`structural_app/tool/analyzers/beam_analyzer.py`
- **BeamDrawer**：`structural_app/tool/drawers/beam_drawer.py`
- **BeamEvaluator**：`structural_app/tool/evaluators/beam_evaluator.py`

### 6.3 技术文档

- **OpenSeesPy 官方文档**：https://openseespydoc.readthedocs.io/
- **ezdxf 官方文档**：https://ezdxf.readthedocs.io/
- **OpenManus 框架文档**：项目内部文档

---


## 7. 总结

### 7.1 关键要点

1. **Agent 代码零修改**：这是架构设计的核心目标
2. **遵循抽象基类**：确保接口一致性
3. **工厂模式注册**：实现类型动态路由
4. **充分测试**：单元测试 + 端到端测试
5. **⚠️ 检查所有5个工厂注册**：Analyzer、Drawer、Evaluator、**Visualizer**、**Reporter**（后两个最容易遗漏）

### 7.2 开发时间估算

以下为新增结构类型的参考时间（已有 5 种类型可参考实现）：

- **梁类扩展**（边界条件、荷载形式与已有梁类相近）：1-2 天
- **中等复杂度**（如壳体、板结构）：3-5 天
- **复杂结构类型**（如拱、索结构）：5-7 天

### 7.3 成功标准

- ✅ Agent 代码未修改
- ✅ 所有单元测试通过
- ✅ 端到端测试通过
- ✅ 生成正确的分析结果和图纸
- ✅ **生成完整的可视化和报告**（验证 VisualizerFactory 注册）

### 7.4 常见错误排查

**如果端到端测试只生成了CAD图纸，但缺少可视化和报告**：
1. 检查 `VisualizerFactory.get_available_types()` 是否包含新类型
2. 检查 `ReporterFactory.get_available_types()` 是否包含新类型
3. 在 `visualizer_factory.py` 和 `reporter_factory.py` 末尾添加注册代码
4. 对于梁类结构，可以直接复用 `BeamVisualizer` 和 `BeamReporter`

---

**文档版本**：v2.1
**创建日期**：2026-02-07
**最后更新**：2026-05-01
**维护者**：开发团队

---

## 8. 友好错误提示实现指南

### 8.1 错误提示设计原则

当遇到未注册的结构类型时，系统采用**友好错误提示**而非直接崩溃：

| 场景 | 错误提示 | LLM 行为 | 用户体验 |
|------|---------|---------|---------|
| 未知结构类型 | "Unknown structure type: 'arch'. Available types: ['beam', 'cantilever_beam', 'continuous_beam', 'truss', 'frame']" | 下轮避免该类型 | 知道当前限制 |
| 分析失败 | "Analysis failed: convergence error" | 可能尝试调整参数 | 清晰的失败原因 |
| 参数缺失 | "Missing geometry parameter: length" | 补充缺失参数 | 明确需要什么 |

### 8.2 可用类型提示格式

**AnalyzerFactory** 和 **DrawerFactory** 的 `get_available_types()` 方法会返回当前注册的类型列表：

```python
# AnalyzerFactory
>>> AnalyzerFactory.get_available_types()
['beam', 'cantilever_beam', 'continuous_beam', 'truss', 'frame']

# DrawerFactory
>>> DrawerFactory.get_available_types()
['beam', 'cantilever_beam', 'continuous_beam', 'truss', 'frame']
```

### 8.3 LLM 引导策略

当 LLM 生成未支持的类型时，系统通过错误提示引导：

1. **第一轮**：LLM 生成 `type: "arch"` → 错误提示可用类型
2. **第二轮**：LLM 看到提示 → 改为已支持的类型或询问用户
3. **第三轮**：用户确认使用合适类型 → 正常执行

### 8.4 扩展建议

目前已支持 5 种结构类型：`beam`、`cantilever_beam`、`continuous_beam`、`truss`、`frame`。

如需添加新类型（如 `plate`、`arch`），按照本文档步骤实现并在 5 个工厂中注册即可，无需修改任何 Agent 代码。

### 8.5 测试友好错误提示

**测试用例**：

```python
def test_unknown_structure_type_error():
    """测试未知结构类型的友好错误提示"""
    from structural_app.tool.analyzers.analyzer_factory import AnalyzerFactory

    # 验证未注册类型
    assert not AnalyzerFactory.is_registered("arch")

    # 验证可用类型提示
    available = AnalyzerFactory.get_available_types()
    assert set(available) == {"beam", "cantilever_beam", "continuous_beam", "truss", "frame"}

    # 验证错误信息格式
    try:
        AnalyzerFactory.create("arch")
    except ValueError as e:
        error_msg = str(e)
        assert "arch" in error_msg
        assert "beam" in error_msg  # 提示可用类型
```

