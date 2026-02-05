# 接口约定文档

## 数据传递格式

### 1. DesignProposal (设计方案)

```python
{
    "type": str,  # "beam", "frame", "truss", "cantilever_beam"
    "geometry": {
        "length": float,      # 长度 (m)
        "width": float,       # 宽度 (m)
        "height": float,      # 高度 (m)
        # 其他几何参数根据结构类型而定
    },
    "material": {
        "concrete_grade": str,  # "C30", "C40", "C50"
        "steel_grade": str,     # "HRB400", "HRB500"
        "elastic_modulus": float,  # 弹性模量 (MPa)
        "strength": float,      # 强度 (MPa)
    },
    "loads": [
        {
            "type": str,        # "uniform", "concentrated", "moment"
            "value": float,     # 荷载值 (kN or kN/m)
            "position": float,  # 位置 (m)
        }
    ],
    "constraints": [
        {
            "type": str,        # "fixed", "pinned", "roller"
            "position": float,  # 位置 (m)
        }
    ]
}
```

### 2. AnalysisResult (分析结果)

```python
{
    "success": bool,
    "stresses": List[float],        # 应力分布 (MPa)
    "displacements": List[float],   # 位移分布 (mm)
    "max_stress": float,            # 最大应力 (MPa)
    "max_displacement": float,      # 最大位移 (mm)
    "safety_factors": List[float],  # 安全系数分布
    "min_safety_factor": float,     # 最小安全系数
    "visualization": {
        "stress_plot": str,         # 应力云图路径
        "displacement_plot": str,   # 位移云图路径
    },
    "error_message": str,           # 错误信息（如果有）
}
```

### 3. ValidationResult (规范校核结果)

```python
{
    "compliant": bool,              # 是否符合规范
    "checks": [
        {
            "item": str,            # 校核项目
            "code_reference": str,  # 规范条文
            "required": float,      # 规范要求值
            "actual": float,        # 实际值
            "passed": bool,         # 是否通过
            "margin": float,        # 裕度
        }
    ],
    "summary": str,                 # 总结
}
```

### 4. EvaluationResult (评估结果)

```python
{
    "comprehensive_score": float,   # 综合得分 (0-100)
    "grade": str,                   # 等级 "A+", "A", "B+", "B", "C+", "C", "D"
    "economy": {
        "score": float,
        "material_efficiency": float,
        "total_cost": float,
        "details": dict,
    },
    "efficiency": {
        "score": float,
        "average_utilization": float,
        "utilization_uniformity": float,
    },
    "safety": {
        "score": float,
        "min_safety_factor": float,
        "deflection_margin": float,
    },
    "sustainability": {
        "score": float,
        "total_carbon_emission": float,
        "carbon_intensity": float,
    },
    "suggestions": List[str],       # 改进建议
}
```

## 抽象基类接口

### StructureAnalyzer

```python
from abc import ABC, abstractmethod
from typing import Dict

class StructureAnalyzer(ABC):
    """结构分析器抽象基类"""

    @abstractmethod
    def build_model(self, design: Dict) -> None:
        """构建有限元模型"""
        pass

    @abstractmethod
    def analyze(self, design: Dict) -> Dict:
        """执行分析"""
        pass

    @abstractmethod
    def check_code(self, design: Dict, analysis_result: Dict) -> Dict:
        """规范校核"""
        pass
```

### StructureDrawer

```python
from abc import ABC, abstractmethod
from typing import Dict

class StructureDrawer(ABC):
    """结构绘图器抽象基类"""

    @abstractmethod
    def draw_plan(self, design: Dict) -> str:
        """绘制平面图"""
        pass

    @abstractmethod
    def draw_elevation(self, design: Dict) -> str:
        """绘制立面图"""
        pass

    @abstractmethod
    def draw_details(self, design: Dict) -> str:
        """绘制详图"""
        pass
```

### CodeValidator

```python
from abc import ABC, abstractmethod
from typing import Dict

class CodeValidator(ABC):
    """规范验证器抽象基类"""

    @abstractmethod
    def validate(self, design: Dict, analysis_result: Dict) -> Dict:
        """验证设计是否符合规范"""
        pass
```

### DesignEvaluator

```python
from abc import ABC, abstractmethod
from typing import Dict

class DesignEvaluator(ABC):
    """设计评估器抽象基类"""

    @abstractmethod
    def evaluate_economy(self, design: Dict, analysis_result: Dict) -> Dict:
        """评估经济性"""
        pass

    @abstractmethod
    def evaluate_efficiency(self, design: Dict, analysis_result: Dict) -> Dict:
        """评估结构效率"""
        pass

    @abstractmethod
    def evaluate_safety(self, design: Dict, analysis_result: Dict) -> Dict:
        """评估安全性"""
        pass

    @abstractmethod
    def evaluate_sustainability(self, design: Dict, analysis_result: Dict) -> Dict:
        """评估可持续性"""
        pass

    def evaluate_comprehensive(self, design: Dict, analysis_result: Dict) -> Dict:
        """综合评估（通用方法）"""
        pass
```

## 工厂类接口

### AnalyzerFactory

```python
class AnalyzerFactory:
    """分析器工厂"""

    @staticmethod
    def create(structure_type: str) -> StructureAnalyzer:
        """根据结构类型创建分析器"""
        pass
```

### DrawerFactory

```python
class DrawerFactory:
    """绘图器工厂"""

    @staticmethod
    def create(structure_type: str) -> StructureDrawer:
        """根据结构类型创建绘图器"""
        pass
```

## 注意事项

1. **所有Agent必须使用这些标准格式**
2. **不要在Agent中硬编码结构类型判断**
3. **通过工厂模式动态创建实现类**
4. **保持接口稳定，实现可以灵活变化**
