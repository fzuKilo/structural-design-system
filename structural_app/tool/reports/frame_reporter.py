"""
Frame reporter for structural design reports
Generates structured Markdown reports for frame design
"""

import os
from datetime import datetime
from typing import Dict, Any

from .base_reporter import BaseReporter


class FrameReporter(BaseReporter):
    """
    Reporter for frame structure design
    Generates comprehensive Markdown reports with frame-specific content
    """

    def __init__(self):
        """Initialize the frame reporter"""
        super().__init__()
        self.structure_type = "frame"

    def generate_report(self, design: Dict[str, Any], results: Dict[str, Any],
                       evaluation: Dict[str, Any] = None, drawings: Dict[str, Any] = None) -> str:
        """
        Generate a structured Markdown report for frame design

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
        report_filename = f"frame_design_report_{timestamp}.md"
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

        analysis_results = results.get('results', {})
        code_check = results.get('code_check', {})

        # Report header
        report = []
        report.append("# 框架结构设计报告")
        report.append("")
        report.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        report.append("## 1. 设计参数")
        report.append("")
        report.append("### 1.1 结构信息")
        report.append("")
        report.append("| 项目 | 值 |")
        report.append("|------|-----|")
        report.append(f"| 结构类型 | 框架 (Frame) |")
        report.append(f"| 跨数 | {geometry.get('num_bays', 0)} |")
        report.append(f"| 层数 | {geometry.get('num_stories', 0)} |")

        # Bay widths
        bay_widths = geometry.get('bay_widths', [])
        if bay_widths:
            bay_widths_str = ", ".join([f"{w:.2f}m" for w in bay_widths])
            report.append(f"| 跨度 | {bay_widths_str} |")

        # Story heights
        story_heights = geometry.get('story_heights', [])
        if story_heights:
            story_heights_str = ", ".join([f"{h:.2f}m" for h in story_heights])
            report.append(f"| 层高 | {story_heights_str} |")

        report.append("")
        report.append("### 1.2 构件截面")
        report.append("")

        # Column section
        columns = geometry.get('columns', {})
        report.append("**柱截面**")
        report.append("")
        report.append("| 项目 | 值 |")
        report.append("|------|-----|")
        report.append(f"| 截面类型 | {columns.get('type', 'N/A')} |")
        report.append(f"| 宽度 | {columns.get('width', 0)} m |")
        report.append(f"| 深度 | {columns.get('depth', 0)} m |")
        report.append("")

        # Beam section
        beams = geometry.get('beams', {})
        report.append("**梁截面**")
        report.append("")
        report.append("| 项目 | 值 |")
        report.append("|------|-----|")
        report.append(f"| 截面类型 | {beams.get('type', 'N/A')} |")
        report.append(f"| 宽度 | {beams.get('width', 0)} m |")
        report.append(f"| 深度 | {beams.get('depth', 0)} m |")
        report.append("")

        report.append("### 1.3 材料信息")
        report.append("")
        report.append("| 项目 | 值 |")
        report.append("|------|-----|")
        report.append(f"| 弹性模量 E | {material.get('E', 0) / 1e9:.2f} GPa |")
        report.append(f"| 泊松比 nu | {material.get('nu', 0):.2f} |")
        report.append(f"| 屈服强度 fy | {material.get('fy', 0) / 1e6:.2f} MPa |")
        report.append(f"| 材料名称 | {material.get('material_name', 'N/A')} |")
        report.append("")

        report.append("### 1.4 荷载信息")
        report.append("")

        # Beam distributed loads
        beam_distributed = loads.get('beam_distributed', [])
        if beam_distributed:
            report.append("**梁分布荷载**")
            report.append("")
            for i, load in enumerate(beam_distributed, 1):
                q = load.get('q', 0)
                story = load.get('story', 0)
                bay = load.get('bay', 0)
                report.append(f"- 荷载 {i}: {abs(q)} kN/m (第{story}层, 第{bay}跨)")
            report.append("")

        # Lateral loads
        lateral = loads.get('lateral', [])
        if lateral:
            report.append("**侧向荷载 (风荷载/地震作用)**")
            report.append("")
            for i, load in enumerate(lateral, 1):
                F = load.get('F', 0)
                story = load.get('story', 0)
                report.append(f"- 荷载 {i}: {abs(F)} kN (第{story}层)")
            report.append("")

        # Nodal loads
        nodal = loads.get('nodal', [])
        if nodal:
            report.append("**节点荷载**")
            report.append("")
            for i, load in enumerate(nodal, 1):
                Fx = load.get('Fx', 0)
                Fy = load.get('Fy', 0)
                node = load.get('node', 0)
                report.append(f"- 荷载 {i}: Fx={Fx} kN, Fy={Fy} kN (节点{node})")
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
        report.append(f"| 最大轴力 | {analysis_results.get('max_axial_kN', 0):.2f} kN |")

        # Frame-specific: story drift ratio
        max_drift_ratio = analysis_results.get('max_drift_ratio', 0)
        drift_limit = 1.0 / 500
        drift_status = "✓ 满足" if max_drift_ratio <= drift_limit else "✗ 超限"
        report.append(f"| 最大层间位移角 | {max_drift_ratio:.6f} ({drift_status}, 限值: {drift_limit:.6f}) |")
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
            report.append(f"| 层间位移角安全系数 | {safety_factors.get('drift', 0):.2f} |")
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
                report.append("| 维度 | 评分 | 权重 |")
                report.append("|------|------|------|")
                report.append(f"| 经济性 | {dimensions.get('economy', {}).get('score', 0):.1f} | 20% |")
                report.append(f"| 结构效率 | {dimensions.get('structural_efficiency', {}).get('score', 0):.1f} | 15% |")
                report.append(f"| 安全性 | {dimensions.get('safety', {}).get('score', 0):.1f} | 45% |")
                report.append(f"| 可持续性 | {dimensions.get('sustainability', {}).get('score', 0):.1f} | 20% |")
                report.append("")

                # Frame-specific indicators
                safety_indicators = dimensions.get('safety', {}).get('indicators', {})
                if safety_indicators:
                    report.append("### 3.2 框架特有指标")
                    report.append("")
                    report.append("| 指标 | 值 |")
                    report.append("|------|-----|")
                    report.append(f"| 应力利用率 | {safety_indicators.get('stress_utilization', 0):.4f} |")
                    report.append(f"| 挠度利用率 | {safety_indicators.get('deflection_utilization', 0):.4f} |")
                    report.append(f"| 层间位移角利用率 | {safety_indicators.get('drift_utilization', 0):.4f} |")
                    report.append("")

                    # Construction issues
                    construction_issues = safety_indicators.get('construction_issues', [])
                    if construction_issues:
                        report.append("### 3.3 构造检查")
                        report.append("")
                        for issue in construction_issues:
                            severity = issue.get('severity', 'unknown')
                            message = issue.get('message', '')
                            recommendation = issue.get('recommendation', '')
                            report.append(f"**{severity.upper()}**: {message}")
                            report.append(f"- 建议: {recommendation}")
                            report.append("")

            # Recommendations
            recommendations = evaluation.get('recommendations', [])
            if recommendations:
                report.append("### 3.4 改进建议")
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
                for drawing_type, file_path in files.items():
                    report.append(f"| {drawing_type} | `{file_path}` |")
                report.append("")

        # Footer
        report.append("---")
        report.append("")
        report.append("*本报告由OpenManus结构设计系统自动生成*")
        report.append("")

        return "\n".join(report)
