# 结构类型扩展计划

## 策略选择：方案B - 循序渐进

> 先完成 Agent 层闭环，再扩展结构类型

---

## 扩展时间点

- **时机**：阶段8-9完成后（Agent层完成）
- **目标**：为架构验证（阶段10.5）做准备
- **优先级**：测试常用结构类型

---

## 待实现结构类型

| 序号 | 类型 | 复杂度 | 预计时间 | 实现内容 |
|------|------|--------|----------|----------|
| 1 | CantileverBeam | ⭐ 极低 | 30分钟 | 固定端边界条件 |
| 2 | ContinuousBeam | ⭐⭐ 低 | 1小时 | 多跨边界条件 |
| 3 | Truss | ⭐⭐⭐ 中等 | 2小时 | 杆单元建模 |
| 4 | Frame | ⭐⭐⭐⭐ 高 | 3小时 | 梁柱刚性连接 |

**总计**：约 6.5 小时

---

## 实现组件（每个类型）

每个结构类型需要实现：

```
app/tool/
├── analyzers/
│   ├── {type}_analyzer.py        # 有限元分析
│   └── analyzer_factory.py       # 注册
├── drawers/
│   ├── {type}_drawer.py          # CAD绘图
│   └── drawer_factory.py         # 注册
└── evaluators/
    ├── {type}_evaluator.py       # 设计评估
    └── evaluator_factory.py      # 注册
```

---

## 验收标准

- [ ] 所有单元测试通过
- [ ] 端到端测试通过（Agent零修改）
- [ ] 友好错误提示（未注册类型）

---

## 更新日志

| 日期 | 版本 | 状态 |
|------|------|------|
| 2026-02-22 | v1.0 | 创建计划 |
| 2026-03-05 | v2.0 | 整合三大任务实施方案 |

---
---

# 三大任务整合实施方案 (v2.0)

> **更新日期**: 2026-03-05
> **核心策略**: 方案A - 保守渐进式 ⭐⭐⭐⭐⭐

---

## 📋 总体规划

本方案整合了三大核心任务:

1. **任务1**: 增加系统支持的结构类型
2. **任务2**: 改进评分系统
3. **任务3**: 集成RAG知识库

### 实施路径

```
阶段1: 改进评分系统 (3-4天)
   ↓
阶段2: 增加悬臂梁验证 (1天)
   ↓
阶段3: 集成RAG知识库 (2-3天)
   ↓
阶段4: 批量增加剩余结构 (4-5天)
```

**总时间**: 10-13天 (约2-3周)

---

## 🔗 三大任务依赖关系分析

### 任务依赖图

```
任务1: 增加结构类型
├── 依赖: Evaluator基类 (评分系统)
├── 产出: 4种新结构的 Analyzer/Drawer/Evaluator
└── 影响: 评分系统需要更多测试数据

任务2: 改进评分系统
├── 依赖: 无 (可独立进行)
├── 产出: 新的评分基类和算法
└── 影响: 任务1的Evaluator实现、任务3的规范校核

任务3: 集成RAG知识库
├── 依赖: 无 (可独立进行)
├── 产出: 规范查询能力
└── 影响: 任务2的构造评分、任务1的规范校核
```

### 关键冲突点

⚠️ **冲突1: 评分系统的重复修改**
- 如果先做任务1 (增加结构),使用旧评分系统
- 再做任务2 (改进评分),需要修改所有新增的Evaluator
- **成本**: 重复工作,浪费时间

⚠️ **冲突2: 评分系统的测试覆盖**
- 如果先做任务2 (改进评分),只有梁结构测试
- 评分曲线参数可能不够准确
- **风险**: 参数调优不充分

⚠️ **冲突3: RAG与评分系统的集成时机**
- RAG可以增强构造评分 (查询规范条文)
- 如果先做任务2,后做任务3,需要回头修改构造评分
- **成本**: 集成成本增加

---

## 🎯 方案对比

### 方案A: 保守渐进式 (推荐 ⭐⭐⭐⭐⭐)

**实施路径**:
1. 阶段1: 改进评分系统 (梁结构) [3-4天]
2. 阶段2: 增加1个简单结构验证 [1天]
3. 阶段3: 集成RAG知识库 [2-3天]
4. 阶段4: 批量增加剩余结构 [4-5天]

**优点**:
- ✅ 避免重复修改 (评分系统先完善)
- ✅ 逐步验证 (每个阶段都有明确产出)
- ✅ 风险可控 (问题可以及时发现和修正)
- ✅ RAG集成时机合适 (评分系统已稳定)

**缺点**:
- ⚠️ 总时间较长 (10-13天)
- ⚠️ 阶段1评分参数可能需要在阶段2微调

### 其他方案对比

| 维度 | 方案A (推荐) | 方案B (并行) | 方案C (RAG优先) | 方案D (MVP) |
|------|-------------|-------------|----------------|-------------|
| 总时间 | 10-13天 | 10-13天 (并行) | 11-14天 | 10-12天 |
| 风险 | 低 ⭐⭐⭐⭐⭐ | 高 ⭐⭐ | 中 ⭐⭐⭐ | 中 ⭐⭐⭐ |
| 重复工作 | 无 ⭐⭐⭐⭐⭐ | 有 ⭐⭐ | 无 ⭐⭐⭐⭐⭐ | 有 ⭐⭐⭐ |
| 测试充分性 | 高 ⭐⭐⭐⭐⭐ | 低 ⭐⭐ | 高 ⭐⭐⭐⭐ | 中 ⭐⭐⭐ |
| 集成复杂度 | 低 ⭐⭐⭐⭐⭐ | 高 ⭐⭐ | 中 ⭐⭐⭐ | 中 ⭐⭐⭐ |
| 可维护性 | 高 ⭐⭐⭐⭐⭐ | 中 ⭐⭐⭐ | 高 ⭐⭐⭐⭐ | 中 ⭐⭐⭐ |

---

## 📅 详细实施计划

### 阶段1: 改进评分系统 (3-4天)

**目标**: 建立成熟的评分系统基础

**任务清单**:

**Day 1-2: 重构基类**
- 实现 `MultiLevelScoringCurve` 类
- 重构 `DesignEvaluator` 基类
- 创建配置文件 `evaluator_config.py`
- 更新 `BeamEvaluator` 使用新基类

**Day 2-3: 实现核心改进**
- 实现多级评分曲线 (应力、挠度)
- 实现综合利用率指标
- 实现构造评分 (梁特定检查)
- 调整权重配置 (安全性40%)

**Day 3-4: 测试和调优**
- 单元测试 (评分曲线、构造检查)
- 端到端测试 (梁结构)
- 参数调优 (评分曲线区间)
- 对比新旧评分结果

**产出**:
- ✅ 成熟的评分系统基类
- ✅ 完善的梁结构评分
- ✅ 充分测试的评分曲线参数

---

### 阶段2: 增加悬臂梁验证 (1天)

**目标**: 验证评分系统的通用性和可扩展性

**任务清单**:

**上午: 实现分析和绘图**
- 实现 `CantileverBeamAnalyzer` (固定端边界条件、OpenSeesPy建模)
- 实现 `CantileverBeamDrawer` (固定端符号绘制、DXF文件生成)

**下午: 实现评估和测试**
- 实现 `CantileverBeamEvaluator` (继承新基类、配置悬臂梁特定参数)
- 实现悬臂梁构造检查
- 端到端测试
- 对比梁和悬臂梁的评分差异
- 验证Agent代码零修改

**产出**:
- ✅ 验证评分系统通用性
- ✅ 发现并修复潜在问题
- ✅ 积累第二种结构的评分数据

---

### 阶段3: 集成RAG知识库 (2-3天)

**目标**: 增强规范查询和构造评分能力

**任务清单**:

**Day 1: 搭建RAG系统**
- 安装 LangChain、ChromaDB
- 导入工程规范文档 (PDF转文本)
- 构建向量数据库
- 测试规范查询功能

**Day 2: 集成到评分系统**
- 增强构造评分 (查询规范条文)
- 在 `_check_structure_specific_construction` 中集成RAG
- 提供规范依据 (如 "GB 50017-2017 第5.3.8条")

**Day 2-3: 集成到DesignAgent**
- 在设计阶段查询规范
- LLM引用规范进行设计
- 测试规范引用效果

**产出**:
- ✅ 可用的RAG知识库
- ✅ 增强的构造评分 (含规范依据)
- ✅ 智能的设计Agent (规范引用)

---

### 阶段4: 批量增加剩余结构 (4-5天)

**目标**: 完成所有计划结构类型

**任务清单**:

**Day 1: ContinuousBeam (连续梁)**
- Analyzer: 多跨边界条件
- Drawer: 多跨绘图
- Evaluator: 配置参数、构造检查
- 测试

**Day 2: Truss (桁架)**
- Analyzer: 杆单元建模
- Drawer: 桁架绘图
- Evaluator: 参考DQS配置激进参数、长细比检查
- 测试

**Day 3-4: Frame (框架)**
- Analyzer: 梁柱刚性连接
- Drawer: 框架绘图
- Evaluator: 配置最保守参数、刚性连接检查
- 测试

**Day 4-5: 全面测试**
- 所有结构类型端到端测试
- 评分系统对比分析
- 文档更新

**产出**:
- ✅ 5种结构类型完整支持
- ✅ 成熟的评分系统 (多种结构验证)
- ✅ 完整的RAG集成

---

## 🏗️ 评分系统改进技术方案

### 一、架构设计原则

**通用性与特异性的平衡**:

```
评分系统架构:
├── 通用评分框架 (所有结构共享)
│   ├── 评分维度定义 (安全/经济/效率/可持续)
│   ├── 权重配置机制
│   ├── 等级划分标准
│   └── 多级评分曲线算法
│
└── 结构特定评分逻辑 (每种结构独立)
    ├── BeamEvaluator (梁)
    ├── CantileverBeamEvaluator (悬臂梁)
    ├── ContinuousBeamEvaluator (连续梁)
    ├── TrussEvaluator (桁架)
    └── FrameEvaluator (框架)
```

**核心理念**:
- ✅ 通用框架: 评分维度、权重机制、等级划分在基类中定义
- ✅ 特定实现: 每种结构的最优利用率、评分曲线参数在子类中定制
- ✅ 可配置性: 通过配置文件调整权重和参数,无需修改代码

---

### 二、改进后的评分体系

#### 新的评分维度与权重

```python
# 基类默认权重 (参考DQS,提高安全性权重)
DEFAULT_WEIGHTS = {
    'safety': 0.40,          # 安全性 40% (强度20% + 刚度15% + 构造5%)
    'economy': 0.25,         # 经济性 25%
    'efficiency': 0.20,      # 结构效率 20%
    'sustainability': 0.15   # 可持续性 15%
}

# 结构特定权重 (可在子类中覆盖)
BEAM_WEIGHTS = DEFAULT_WEIGHTS  # 梁使用默认权重

TRUSS_WEIGHTS = {
    'safety': 0.35,          # 桁架: 安全性稍低 (冗余度高)
    'economy': 0.30,         # 经济性更重要
    'efficiency': 0.20,
    'sustainability': 0.15
}

FRAME_WEIGHTS = {
    'safety': 0.45,          # 框架: 安全性最高 (关键结构)
    'economy': 0.20,
    'efficiency': 0.20,
    'sustainability': 0.15
}
```

#### 安全性评分细化 (40分)

```
安全性 = 强度评分 + 刚度评分 + 构造评分
       = 20分     + 15分     + 5分
       = 40分
```

1. **强度评分 (20分)**: 基于应力利用率,使用多级评分曲线
2. **刚度评分 (15分)**: 基于挠度利用率,使用多级评分曲线
3. **构造评分 (5分)**: 初始5分,扣分制,检查几何合理性、规范符合性

---

### 三、核心改进点

#### ✅ 改进1: 引入多级评分曲线 (通用算法)

```python
class MultiLevelScoringCurve:
    """
    多级评分曲线 (参考DQS)

    适用于所有结构类型,通过参数配置实现差异化
    """

    def __init__(self,
                 excellent_range: tuple,  # 卓越区间 (min, max)
                 good_range: tuple,       # 优秀区间 (min, max)
                 acceptable_range: tuple, # 良好区间 (min, max)
                 peak_position: float = None):  # 峰值位置
        """
        初始化评分曲线

        Args:
            excellent_range: 卓越区间,如 (0.65, 0.75)
            good_range: 优秀区间,如 (0.60, 0.80)
            acceptable_range: 良好区间,如 (0.50, 0.90)
            peak_position: 峰值位置,如 0.70 (默认为卓越区间中心)
        """
        self.excellent_min, self.excellent_max = excellent_range
        self.good_min, self.good_max = good_range
        self.acceptable_min, self.acceptable_max = acceptable_range
        self.peak = peak_position or (self.excellent_min + self.excellent_max) / 2

    def calculate_score(self, utilization: float, max_score: float = 100) -> float:
        """
        计算评分

        评分区间:
        - 超限 (>1.0): 0分
        - 卓越区间: 92-100%得分
        - 优秀区间: 85-92%得分
        - 良好区间: 70-85%得分
        - 较差区间: 0-70%得分
        """
        # 超限: 0分
        if utilization > 1.0:
            return 0

        # 卓越区间: 92-100%得分
        if self.excellent_min <= utilization <= self.excellent_max:
            distance = abs(utilization - self.peak)
            max_distance = (self.excellent_max - self.excellent_min) / 2
            score_ratio = 1.0 - 0.08 * (distance / max_distance)
            return max_score * score_ratio

        # 优秀区间-低侧: 85-92%得分
        if self.good_min <= utilization < self.excellent_min:
            ratio = (utilization - self.good_min) / (self.excellent_min - self.good_min)
            score_ratio = 0.85 + 0.07 * ratio
            return max_score * score_ratio

        # 优秀区间-高侧: 85-92%得分
        if self.excellent_max < utilization <= self.good_max:
            ratio = 1 - (utilization - self.excellent_max) / (self.good_max - self.excellent_max)
            score_ratio = 0.85 + 0.07 * ratio
            return max_score * score_ratio

        # 良好区间-低侧: 70-85%得分
        if self.acceptable_min <= utilization < self.good_min:
            ratio = (utilization - self.acceptable_min) / (self.good_min - self.acceptable_min)
            score_ratio = 0.70 + 0.15 * ratio
            return max_score * score_ratio

        # 良好区间-高侧: 70-85%得分
        if self.good_max < utilization <= self.acceptable_max:
            ratio = 1 - (utilization - self.good_max) / (self.acceptable_max - self.good_max)
            score_ratio = 0.70 + 0.15 * ratio
            return max_score * score_ratio

        # 较差区间-低侧: 0-70%得分
        if utilization < self.acceptable_min:
            ratio = utilization / self.acceptable_min
            score_ratio = 0.70 * ratio
            return max_score * score_ratio

        # 较差区间-高侧: 0-70%得分
        ratio = (1.0 - utilization) / (1.0 - self.acceptable_max)
        score_ratio = 0.70 * ratio
        return max_score * score_ratio
```

---

#### ✅ 改进2: 结构特定的评分参数配置

```python
# 评分曲线配置 (每种结构不同)
SCORING_CURVES = {
    'beam': {
        'stress': MultiLevelScoringCurve(
            excellent_range=(0.65, 0.75),  # 梁: 保守
            good_range=(0.60, 0.80),
            acceptable_range=(0.50, 0.90),
            peak_position=0.70
        ),
        'deflection': MultiLevelScoringCurve(
            excellent_range=(0.70, 0.80),
            good_range=(0.65, 0.85),
            acceptable_range=(0.55, 0.95),
            peak_position=0.75
        )
    },

    'cantilever_beam': {
        'stress': MultiLevelScoringCurve(
            excellent_range=(0.60, 0.70),  # 悬臂梁: 更保守
            good_range=(0.55, 0.75),
            acceptable_range=(0.45, 0.85),
            peak_position=0.65
        ),
        'deflection': MultiLevelScoringCurve(
            excellent_range=(0.65, 0.75),  # 挠度控制更严格
            good_range=(0.60, 0.80),
            acceptable_range=(0.50, 0.90),
            peak_position=0.70
        )
    },

    'truss': {
        'stress': MultiLevelScoringCurve(
            excellent_range=(0.75, 0.85),  # 桁架: 可以更激进 (参考DQS)
            good_range=(0.70, 0.90),
            acceptable_range=(0.60, 0.95),
            peak_position=0.80
        ),
        'deflection': MultiLevelScoringCurve(
            excellent_range=(0.80, 0.90),
            good_range=(0.75, 0.95),
            acceptable_range=(0.65, 1.00),
            peak_position=0.85
        )
    },

    'frame': {
        'stress': MultiLevelScoringCurve(
            excellent_range=(0.60, 0.70),  # 框架: 最保守
            good_range=(0.55, 0.75),
            acceptable_range=(0.45, 0.85),
            peak_position=0.65
        ),
        'deflection': MultiLevelScoringCurve(
            excellent_range=(0.65, 0.75),
            good_range=(0.60, 0.80),
            acceptable_range=(0.50, 0.90),
            peak_position=0.70
        )
    }
}
```

---

#### ✅ 改进3: 增加构造评分 (通用框架+特定检查)

```python
class DesignEvaluator(ABC):
    """基类: 定义构造评分框架"""

    def evaluate_construction(self, design: Dict, results: Dict) -> Dict:
        """
        构造评分 (扣分制)

        Returns:
            {
                'score': float,  # 0-5分
                'issues': List[Dict]  # 问题列表
            }
        """
        initial_score = 5.0
        issues = []

        # 调用结构特定的检查方法
        structure_issues = self._check_structure_specific_construction(design, results)

        # 根据问题严重性扣分
        for issue in structure_issues:
            severity = issue['severity']  # 'minor', 'moderate', 'severe'
            if severity == 'minor':
                initial_score -= 0.5
            elif severity == 'moderate':
                initial_score -= 1.0
            elif severity == 'severe':
                initial_score -= 2.0
            issues.append(issue)

        return {
            'score': max(0, initial_score),
            'issues': issues
        }

    @abstractmethod
    def _check_structure_specific_construction(self, design: Dict, results: Dict) -> List[Dict]:
        """结构特定的构造检查 (子类实现)"""
        pass


class BeamEvaluator(DesignEvaluator):
    """梁评估器: 实现梁特定的构造检查"""

    def _check_structure_specific_construction(self, design: Dict, results: Dict) -> List[Dict]:
        issues = []
        geometry = design.get('geometry', {})

        length = geometry.get('length', 1.0)
        height = geometry.get('height', 0.5)
        width = geometry.get('width', 0.3)

        # 检查1: 高跨比 (梁: 1/10 ~ 1/20)
        height_span_ratio = height / length
        if height_span_ratio < 0.05:
            issues.append({
                'type': 'height_span_ratio_low',
                'severity': 'moderate',
                'message': f'高跨比过小 ({height_span_ratio:.3f} < 1/20)',
                'recommendation': '增加梁高或减小跨度'
            })
        elif height_span_ratio > 0.15:
            issues.append({
                'type': 'height_span_ratio_high',
                'severity': 'minor',
                'message': f'高跨比偏大 ({height_span_ratio:.3f} > 1/10)',
                'recommendation': '考虑减小梁高以提高经济性'
            })

        # 检查2: 宽高比 (梁: 1/1.5 ~ 1/3)
        width_height_ratio = width / height
        if width_height_ratio < 0.33:
            issues.append({
                'type': 'width_height_ratio_low',
                'severity': 'minor',
                'message': f'宽高比过小 ({width_height_ratio:.2f} < 1/3)',
                'recommendation': '增加梁宽以提高稳定性'
            })
        elif width_height_ratio > 0.67:
            issues.append({
                'type': 'width_height_ratio_high',
                'severity': 'minor',
                'message': f'宽高比过大 ({width_height_ratio:.2f} > 1/1.5)',
                'recommendation': '减小梁宽或增加梁高'
            })

        # 检查3: 最小截面尺寸
        if width < 0.2 or height < 0.3:
            issues.append({
                'type': 'section_too_small',
                'severity': 'severe',
                'message': f'截面尺寸过小 ({width}m × {height}m)',
                'recommendation': '增大截面尺寸以满足最小构造要求'
            })

        return issues
```

---

#### ✅ 改进4: 综合利用率指标 (参考DQS)

```python
def evaluate_economy(self, design: Dict, results: Dict) -> Dict:
    """
    经济性评分 (引入综合利用率)

    综合利用率 = (应力利用率 + 挠度利用率) / 2
    """
    # 1. 计算应力利用率
    stress_utilization = self._get_stress_utilization(design, results)

    # 2. 计算挠度利用率
    deflection_utilization = self._get_deflection_utilization(design, results)

    # 3. 综合利用率
    avg_utilization = (stress_utilization + deflection_utilization) / 2

    # 4. 使用多级评分曲线计算综合利用率得分
    structure_type = design.get('type', 'beam')
    curve = SCORING_CURVES[structure_type]['stress']
    utilization_score = curve.calculate_score(avg_utilization, max_score=100)

    # 5. 材料用量评分 (保持原有逻辑)
    material_score = self._evaluate_material_usage(design, results)

    # 6. 加权计算经济性得分
    economy_score = utilization_score * 0.6 + material_score * 0.4

    return {
        'score': round(economy_score, 1),
        'indicators': {
            'stress_utilization': round(stress_utilization, 4),
            'deflection_utilization': round(deflection_utilization, 4),
            'avg_utilization': round(avg_utilization, 4),
            'material_usage_index': ...,
            'volume_m3': ...,
        }
    }

def _get_deflection_utilization(self, design: Dict, results: Dict) -> float:
    """计算挠度利用率"""
    max_displacement = results.get('results', {}).get('max_displacement', 0)
    deflection_limit = self._get_deflection_limit(design)

    if deflection_limit <= 0:
        return 0.5  # 默认值

    utilization = max_displacement / deflection_limit
    return min(1.0, max(0.0, utilization))

def _get_deflection_limit(self, design: Dict) -> float:
    """获取挠度限值 (结构特定)"""
    structure_type = design.get('type', 'beam')
    geometry = design.get('geometry', {})
    length = geometry.get('length', 1.0)

    # 不同结构类型的挠度限值
    DEFLECTION_LIMITS = {
        'beam': length / 250,           # 简支梁: L/250
        'cantilever_beam': length / 200, # 悬臂梁: L/200 (更严格)
        'continuous_beam': length / 300, # 连续梁: L/300 (更严格)
        'truss': length / 250,          # 桁架: L/250
        'frame': length / 300,          # 框架: L/300 (更严格)
    }

    return DEFLECTION_LIMITS.get(structure_type, length / 250)
```

---

### 四、配置文件示例

```python
# config/evaluator_config.py
"""
评分系统配置文件
"""

# 权重配置
WEIGHTS_CONFIG = {
    'beam': {
        'safety': 0.40,
        'economy': 0.25,
        'efficiency': 0.20,
        'sustainability': 0.15
    },
    'cantilever_beam': {
        'safety': 0.45,  # 悬臂梁: 安全性更重要
        'economy': 0.20,
        'efficiency': 0.20,
        'sustainability': 0.15
    },
    'truss': {
        'safety': 0.35,  # 桁架: 经济性更重要
        'economy': 0.30,
        'efficiency': 0.20,
        'sustainability': 0.15
    },
    'frame': {
        'safety': 0.45,  # 框架: 安全性最重要
        'economy': 0.20,
        'efficiency': 0.20,
        'sustainability': 0.15
    }
}

# 挠度限值配置
DEFLECTION_LIMITS = {
    'beam': lambda L: L / 250,
    'cantilever_beam': lambda L: L / 200,
    'continuous_beam': lambda L: L / 300,
    'truss': lambda L: L / 250,
    'frame': lambda L: L / 300,
}

# 构造要求配置
CONSTRUCTION_REQUIREMENTS = {
    'beam': {
        'height_span_ratio': (0.05, 0.15),  # (min, max)
        'width_height_ratio': (0.33, 0.67),
        'min_width': 0.2,
        'min_height': 0.3
    },
    'truss': {
        'height_span_ratio': (0.05, 0.20),
        'slenderness_ratio_compression': 150,
        'slenderness_ratio_tension': 350,
        'min_section_area': 500  # mm²
    },
    # ... 其他结构类型
}
```

---

## ✅ 改进优势总结

### 学习DQS的优点

1. ✅ **多级评分曲线** → 提升区分度
2. ✅ **提高安全性权重** → 符合工程实践
3. ✅ **构造评分 (扣分制)** → 全面评估
4. ✅ **综合利用率指标** → 更科学

### 适应多结构类型

1. ✅ **通用框架 + 特定实现** → 可扩展
2. ✅ **配置文件驱动** → 易于调整
3. ✅ **结构特定参数** → 精准评估

---

## 🎯 关键成功因素

- ✅ 阶段1必须充分测试评分系统 (这是基础)
- ✅ 阶段2的悬臂梁是关键验证点 (发现问题的最佳时机)
- ✅ 阶段3的RAG集成要保持简单 (不要过度设计)
- ✅ 阶段4可以并行开发多个结构 (此时系统已成熟)

---

## 📊 预期时间线

- **第1周**: 阶段1 + 阶段2 (评分系统 + 悬臂梁验证)
- **第2周**: 阶段3 (RAG集成)
- **第3周**: 阶段4 (剩余结构批量实现)

**总计**: 10-13天 (约2-3周)

---

## 📝 验收标准

### 阶段1验收
- [ ] `MultiLevelScoringCurve` 类单元测试通过
- [ ] `BeamEvaluator` 使用新评分系统
- [ ] 构造评分功能正常
- [ ] 新旧评分对比文档

### 阶段2验收
- [ ] `CantileverBeamAnalyzer/Drawer/Evaluator` 实现完成
- [ ] 端到端测试通过
- [ ] Agent代码零修改
- [ ] 评分系统通用性验证

### 阶段3验收
- [ ] RAG知识库可用
- [ ] 构造评分集成RAG
- [ ] DesignAgent规范引用功能
- [ ] 规范查询准确率 >80%

### 阶段4验收
- [ ] 所有结构类型单元测试通过
- [ ] 所有结构类型端到端测试通过
- [ ] 评分系统对比分析报告
- [ ] 文档更新完成

---

## 📚 相关文档

- [如何添加新结构类型](./how_to_add_new_structure_type.md)
- [评分系统设计文档](./evaluation_system.md)
- [RAG集成指南](./rag_integration.md)

---

## 📅 更新日志 (v2.0)

| 日期 | 版本 | 更新内容 |
|------|------|----------|
| 2026-02-22 | v1.0 | 创建初始计划 |
| 2026-03-05 | v2.0 | 整合三大任务实施方案,添加评分系统改进技术细节 |

