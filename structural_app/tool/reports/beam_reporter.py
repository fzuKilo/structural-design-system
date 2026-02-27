"""
Beam reporter for structural design reports
Generates structured Markdown reports for beam design
"""

import os
from datetime import datetime
from typing import Dict, Any

from .base_reporter import BaseReporter


class BeamReporter(BaseReporter):
    """
    Reporter for beam structure design
    Generates comprehensive Markdown reports
    """

    def __init__(self):
        """Initialize the beam reporter"""
        super().__init__()
        self.structure_type = "beam"

    def generate_report(self, design: Dict[str, Any], results: Dict[str, Any],
                       evaluation: Dict[str, Any] = None, drawings: Dict[str, Any] = None) -> str:
        """
        Generate a structured Markdown report for beam design

        Args:
            design: Design proposal
            results: Analysis results
            evaluation: Evaluation report (optional)
            drawings: Drawing results (optional)

        Returns:
            Path to the generated report file
        """
        os.makedirs(self.output_dir, exist_ok=True)

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"beam_design_report_{timestamp}.md"
        report_path = os.path.join(self.output_dir, report_filename)

        # Build report content
        report_content = self._build_report_content(design, results, evaluation, drawings)

        # Write report file
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)

        return report_path

    def _build_report_content(self, design: Dict[str, Any], results: Dict[str, Any],
                             evaluation: Dict[str, Any] = None, drawings: Dict[str, Any] = None) -> str:
        """Build the Markdown report content"""

        # Extract data
        geometry = design.get('geometry', {})
        material = design.get('material', {})
        loads = design.get('loads', {})
        constraints = design.get('constraints', {})

        analysis_results = results.get('results', {})
        code_check = results.get('code_check', {})

        # Report header
        report = []
        report.append("# 结构设计报告")
        report.append("")
        report.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        report.append("## 1. 设计参数")
        report.append("")
        report.append("### 1.1 结构信息")
        report.append("")
        report.append("| 项目 | 值 |")
        report.append("|------|-----|")
        report.append(f"| 结构类型 | 梁 (Beam) |")
        report.append(f"| 跨度 | {geometry.get('length', 0)} m |")
        report.append(f"| 宽度 | {geometry.get('width', 0)} m |")
        report.append(f"| 高度 | {geometry.get('height', 0)} m |")
        report.append(f"| 单元数 | {geometry.get('n_elements', 0)} |")
        report.append("")
        report.append("### 1.2 材料信息")
        report.append("")
        report.append("| 项目 | 值 |")
        report.append("|------|-----|")
        report.append(f"| 弹性模量 E | {material.get('E', 0) / 1e9:.2f} GPa |")
        report.append(f"| 泊松比 nu | {material.get('nu', 0):.2f} |")
        report.append(f"| 屈服强度 fy | {material.get('fy', 0) / 1e6:.2f} MPa |")
        report.append(f"| 材料名称 | {material.get('material_name', 'N/A')} |")
        report.append("")
        report.append("### 1.3 荷载信息")
        report.append("")
        distributed_loads = loads.get('distributed', [])
        point_loads = loads.get('point', [])
        report.append(f"| 分布荷载 | {len(distributed_loads)} 个 |")
        report.append(f"| 集中荷载 | {len(point_loads)} 个 |")
        report.append("")

        # Add load details
        for i, load in enumerate(distributed_loads, 1):
            q = load.get('q', 0)
            direction = load.get('direction', 'y')
            report.append(f"- 分布荷载 {i}: {abs(q)} kN/m (方向: {direction})")

        for i, load in enumerate(point_loads, 1):
            P = load.get('P', 0)
            location = load.get('location', 0)
            direction = load.get('direction', 'y')
            report.append(f"- 集中荷载 {i}: {abs(P)} kN (位置: {location} m, 方向: {direction})")

        report.append("")
        report.append("### 1.4 支座信息")
        report.append("")
        report.append(f"| 支座类型 | {constraints.get('support_type', 'N/A')} |")
        report.append("")

        # Analysis results
        report.append("## 2. 有限元分析结果")
        report.append("")
        report.append("### 2.1 关键指标")
        report.append("")
        report.append("| 指标 | 值 |")
        report.append("|------|-----|")
        report.append(f"| 最大位移 | {analysis_results.get('max_displacement_mm', 0):.3f} mm |")
        report.append(f"| 最大应力 | {analysis_results.get('max_stress_MPa', 0):.2f} MPa |")
        report.append(f"| 最大弯矩 | {analysis_results.get('max_moment_kNm', 0):.2f} kN·m |")
        report.append(f"| 最大剪力 | {analysis_results.get('max_shear_kN', 0):.2f} kN |")
        report.append("")

        # Code check
        report.append("### 2.2 规范校核")
        report.append("")
        compliant = code_check.get('compliant', False)
        violations = code_check.get('violations', [])
        safety_factors = code_check.get('safety_factors', {})

        report.append(f"| 校核状态 | **{'符合规范' if compliant else '不符合规范'}** |")
        report.append("")

        if safety_factors:
            report.append("### 2.3 安全系数")
            report.append("")
            report.append("| 指标 | 安全系数 |")
            report.append("|------|----------|")
            report.append(f"| 应力安全系数 | {safety_factors.get('stress', 0):.2f} |")
            report.append(f"| 挠度安全系数 | {safety_factors.get('deflection', 0):.2f} |")
            report.append("")

        if violations:
            report.append("### 2.4 违规项")
            report.append("")
            for violation in violations:
                report.append(f"- {violation}")
            report.append("")

        # Evaluation results
        if evaluation:
            report.append("## 3. 设计评估")
            report.append("")

            comprehensive_score = evaluation.get('comprehensive_score', 0)
            grade = evaluation.get('grade', 'N/A')

            report.append(f"| 综合评分 | **{comprehensive_score:.1f} / 100** |")
            report.append(f"| 评估等级 | **{grade}** |")
            report.append("")

            # Dimension scores
            dimensions = evaluation.get('dimensions', {})
            if dimensions:
                report.append("### 3.1 评估维度")
                report.append("")
                report.append("| 维度 | 评分 |")
                report.append("|------|------|")
                report.append(f"| 经济性 | {dimensions.get('economy', {}).get('score', 0):.1f} |")
                report.append(f"| 结构效率 | {dimensions.get('structural_efficiency', {}).get('score', 0):.1f} |")
                report.append(f"| 安全性 | {dimensions.get('safety', {}).get('score', 0):.1f} |")
                report.append(f"| 可持续性 | {dimensions.get('sustainability', {}).get('score', 0):.1f} |")
                report.append("")

            # Recommendations
            recommendations = evaluation.get('recommendations', [])
            if recommendations:
                report.append("### 3.2 改进建议")
                report.append("")
                for i, rec in enumerate(recommendations, 1):
                    report.append(f"{i}. {rec}")
                report.append("")

        # Drawings
        if drawings:
            report.append("## 4. CAD图纸")
            report.append("")

            files = drawings.get('files', {})
            if files:
                report.append("| 图纸类型 | 文件路径 |")
                report.append("|----------|----------|")
                for drawing_type, filepath in files.items():
                    report.append(f"| {drawing_type} | {filepath} |")
                report.append("")

        # Footer
        report.append("---")
        report.append("")
        report.append("*本报告由 OpenManus 结构设计系统自动生成*")
        report.append(f"*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")

        return '\n'.join(report)
