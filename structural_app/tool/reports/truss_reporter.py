"""
Truss reporter for structural design reports
Generates structured Markdown reports for truss design
"""

import os
from datetime import datetime
from typing import Dict, Any

from .base_reporter import BaseReporter


class TrussReporter(BaseReporter):
    """
    Reporter for truss structure design
    Generates comprehensive Markdown reports
    """

    def __init__(self):
        """Initialize the truss reporter"""
        super().__init__()
        self.structure_type = "truss"

    def generate_report(self, design: Dict[str, Any], results: Dict[str, Any],
                       evaluation: Dict[str, Any] = None, drawings: Dict[str, Any] = None,
                       bim: Dict[str, Any] = None, ifc: Dict[str, Any] = None) -> str:
        """
        Generate a structured Markdown report for truss design

        Args:
            design: Design proposal
            results: Analysis results
            evaluation: Evaluation report (optional)
            drawings: Drawing results (optional)
            bim: BIM export results (optional)
            ifc: IFC export results (optional)

        Returns:
            Path to the generated report file
        """
        os.makedirs(self.output_dir, exist_ok=True)

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"truss_design_report_{timestamp}.md"
        report_path = os.path.join(self.output_dir, report_filename)

        # Build report content
        report_content = self._build_report_content(design, results, evaluation, drawings, bim, ifc)

        # Write report file
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)

        return report_path

    def _build_report_content(self, design: Dict[str, Any], results: Dict[str, Any],
                             evaluation: Dict[str, Any] = None, drawings: Dict[str, Any] = None,
                             bim: Dict[str, Any] = None, ifc: Dict[str, Any] = None) -> str:
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
        report.append("# 桁架结构设计报告")
        report.append("")
        report.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        report.append("## 1. 设计参数")
        report.append("")
        report.append("### 1.1 结构信息")
        report.append("")
        report.append("| 项目 | 值 |")
        report.append("|------|-----|")
        structure_type = design.get('type', 'truss')
        report.append(f"| 结构类型 | {self.get_structure_display_name(structure_type)} |")
        report.append(f"| 跨度 | {geometry.get('span', 0)} m |")
        report.append(f"| 高度 | {geometry.get('height', 0)} m |")
        report.append(f"| 节间数 | {geometry.get('n_panels', 0)} |")

        # Get n_elements from analysis results if available
        detailed_results = analysis_results.get('detailed_results', {})
        n_elements = detailed_results.get('n_elements', geometry.get('n_elements', 0))
        report.append(f"| 单元总数 | {n_elements} |")
        report.append("")

        report.append("### 1.2 材料信息")
        report.append("")
        report.append("| 项目 | 值 |")
        report.append("|------|-----|")
        report.append(f"| 弹性模量 E | {material.get('E', 0) / 1e9:.2f} GPa |")
        report.append(f"| 截面积 A | {material.get('A', 0):.4f} m² |")
        report.append(f"| 屈服强度 fy | {material.get('fy', 0) / 1e6:.2f} MPa |")
        report.append(f"| 材料名称 | {material.get('material_name', 'N/A')} |")
        report.append("")

        report.append("### 1.3 荷载信息")
        report.append("")
        nodal_loads = loads.get('nodal', [])
        report.append(f"**节点荷载**: {len(nodal_loads)} 个")
        report.append("")

        # Add nodal load details
        if nodal_loads:
            report.append("**节点荷载详情：**")
            report.append("")
            for i, load in enumerate(nodal_loads, 1):
                node = load.get('node', 0)
                Fx = load.get('Fx', 0)
                Fy = load.get('Fy', 0)
                load_desc = []
                if Fx != 0:
                    load_desc.append(f"Fx={Fx/1000:.2f} kN")
                if Fy != 0:
                    load_desc.append(f"Fy={Fy/1000:.2f} kN")
                report.append(f"- 节点 {node}: {', '.join(load_desc)}")
            report.append("")

        report.append("### 1.4 支座信息")
        report.append("")
        report.append(f"**支座类型**: {constraints.get('support_type', 'N/A')}")
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
        report.append("")

        # Code check
        report.append("### 2.2 规范校核")
        report.append("")
        compliant = code_check.get('compliant', False)
        violations = code_check.get('violations', [])
        safety_factors = code_check.get('safety_factors', {})

        status_text = "✅ 符合规范" if compliant else "❌ 不符合规范"
        report.append(f"**校核状态**: {status_text}")
        report.append("")

        if safety_factors:
            report.append("### 2.3 安全系数")
            report.append("")
            report.append("| 指标 | 安全系数 |")
            report.append("|------|----------|")
            report.append(f"| 应力安全系数 | {safety_factors.get('stress', 0):.2f} |")
            report.append(f"| 挠度安全系数 | {safety_factors.get('deflection', 0):.2f} |")

            # Add slenderness safety factor for truss
            if 'slenderness' in safety_factors:
                report.append(f"| 长细比安全系数 | {safety_factors.get('slenderness', 0):.2f} |")
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
            dimensions = evaluation.get('dimensions', {}) or {}

            report.append("| 项目 | 值 |")
            report.append("|------|-----|")
            report.append(f"| 综合评分 | **{comprehensive_score:.1f} / 100** |")
            report.append(f"| 评估等级 | **{grade}** |")
            report.append("")

            SEVERE = 60
            WARNING = 70

            alerts = []
            safety_score = dimensions.get('safety', {}).get('score', 100)
            economy_score = dimensions.get('economy', {}).get('score', 100)
            efficiency_score = dimensions.get('structural_efficiency', {}).get('score', 100)
            sustainability_score = dimensions.get('sustainability', {}).get('score', 100)

            if safety_score < SEVERE:
                alerts.append(("🔴 严重", "安全性", f"得分 {safety_score:.1f}，存在安全风险，建议立即增大杆件截面或提高材料强度"))
            elif safety_score < WARNING:
                alerts.append(("🟡 警告", "安全性", f"得分 {safety_score:.1f}，安全裕度较小，可适当增大杆件截面"))
            if economy_score < SEVERE:
                alerts.append(("🔴 严重", "经济性", f"得分 {economy_score:.1f}，材料浪费严重，建议优化杆件截面"))
            elif economy_score < WARNING:
                alerts.append(("🟡 警告", "经济性", f"得分 {economy_score:.1f}，材料利用率偏低，可尝试减小杆件截面"))
            if efficiency_score < SEVERE:
                alerts.append(("🔴 严重", "结构效率", f"得分 {efficiency_score:.1f}，杆件受力不均，建议优化桁架布置"))
            elif efficiency_score < WARNING:
                alerts.append(("🟡 警告", "结构效率", f"得分 {efficiency_score:.1f}，杆件利用率偏低"))
            if sustainability_score < SEVERE:
                alerts.append(("🔴 严重", "可持续性", f"得分 {sustainability_score:.1f}，碳排放强度过高，建议优化材料选型"))
            elif sustainability_score < WARNING:
                alerts.append(("🟡 警告", "可持续性", f"得分 {sustainability_score:.1f}，可考虑使用更环保的材料"))
            if comprehensive_score < WARNING:
                alerts.append(("❌ 不合格", "综合", f"综合得分 {comprehensive_score:.1f} 低于合格线 70 分，建议优化设计"))

            if alerts:
                report.append("### ⚠️ 预警信息")
                report.append("")
                report.append("| 级别 | 维度 | 说明 |")
                report.append("|------|------|------|")
                for level, dim, msg in alerts:
                    report.append(f"| {level} | {dim} | {msg} |")
                report.append("")

            if dimensions:
                report.append("### 3.1 评估维度")
                report.append("")
                report.append("| 维度 | 评分 | 权重 |")
                report.append("|------|------|------|")
                report.append(f"| 经济性 | {economy_score:.1f} | 25% |")
                report.append(f"| 结构效率 | {efficiency_score:.1f} | 20% |")
                report.append(f"| 安全性 | {safety_score:.1f} | 40% |")
                report.append(f"| 可持续性 | {sustainability_score:.1f} | 15% |")
                report.append("")

                econ_ind = dimensions.get('economy', {}).get('indicators', {})
                if econ_ind:
                    report.append("#### 经济性分析")
                    report.append("")
                    report.append("| 指标 | 值 | 说明 |")
                    report.append("|------|-----|------|")
                    for key, label, desc in [
                        ('average_utilization', '平均轴力利用率', '杆件平均轴力/许用轴力'),
                        ('material_usage_index', '材料用量指数', '实际用量/理论最小用量'),
                        ('volume_m3', '总体积 (m³)', ''),
                    ]:
                        val = econ_ind.get(key)
                        if val is not None:
                            report.append(f"| {label} | {val:.4f} | {desc} |")
                    report.append("")

                eff_ind = dimensions.get('structural_efficiency', {}).get('indicators', {})
                if eff_ind:
                    report.append("#### 结构效率分析")
                    report.append("")
                    report.append("| 指标 | 值 | 说明 |")
                    report.append("|------|-----|------|")
                    for key, label, desc in [
                        ('average_utilization', '平均利用率', '杆件平均受力利用率'),
                        ('utilization_uniformity', '利用率均匀性', '越接近1说明受力越均匀'),
                        ('max_utilization', '最大利用率', '最大受力杆件利用率'),
                    ]:
                        val = eff_ind.get(key)
                        if val is not None:
                            report.append(f"| {label} | {val:.4f} | {desc} |")
                    report.append("")

                safe_ind = dimensions.get('safety', {}).get('indicators', {})
                if safe_ind:
                    report.append("#### 安全性分析")
                    report.append("")
                    report.append("| 指标 | 值 | 说明 |")
                    report.append("|------|-----|------|")
                    for key, label, desc in [
                        ('min_safety_factor', '最小安全系数', '<1.0 表示不满足规范'),
                        ('stress_utilization', '应力利用率', '实际应力/许用应力'),
                        ('deflection_utilization', '挠度利用率', '实际挠度/限值挠度'),
                        ('construction_score', '构造得分', '构造措施检查得分'),
                    ]:
                        val = safe_ind.get(key)
                        if val is not None:
                            flag = " ✓" if key == 'min_safety_factor' and val >= 1.0 else (" ✗" if key == 'min_safety_factor' else "")
                            report.append(f"| {label} | {val:.4f}{flag} | {desc} |")
                    report.append("")

                    constr_issues = safe_ind.get('construction_issues', [])
                    if constr_issues:
                        report.append("**构造问题：**")
                        report.append("")
                        for issue in constr_issues:
                            msg = issue.get('message', str(issue)) if isinstance(issue, dict) else str(issue)
                            citation = issue.get('citation', '') if isinstance(issue, dict) else ''
                            line = f"- {msg}"
                            if citation:
                                line += f"（依据：{citation}）"
                            report.append(line)
                        report.append("")

                sust_ind = dimensions.get('sustainability', {}).get('indicators', {})
                if sust_ind:
                    report.append("#### 可持续性分析")
                    report.append("")
                    report.append("| 指标 | 值 | 说明 |")
                    report.append("|------|-----|------|")
                    for key, label, desc in [
                        ('carbon_emission_kg', '碳排放量 (kg CO₂)', ''),
                        ('carbon_intensity', '碳排放强度 (kg/kN·m)', '越低越好'),
                        ('recyclability_ratio', '可回收率', ''),
                    ]:
                        val = sust_ind.get(key)
                        if val is not None:
                            fmt = f"{val*100:.0f}%" if key == 'recyclability_ratio' else f"{val:.4f}"
                            report.append(f"| {label} | {fmt} | {desc} |")
                    report.append("")

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

        # BIM/IFC Export Results
        if bim or ifc:
            report.append("## 5. BIM模型")
            report.append("")

            if bim and bim.get('status') == 'success':
                report.append("### Speckle 3D模型")
                report.append(f"- 查看链接: [{bim.get('url')}]({bim.get('url')})")
                report.append(f"- Model ID: `{bim.get('model_id')}`")
                report.append("")

            if ifc and ifc.get('status') == 'success':
                report.append("### IFC文件")
                report.append(f"- 文件路径: `{ifc.get('path')}`")
                report.append("")

        # Footer
        report.append("---")
        report.append("")
        report.append("*本报告由 OpenManus 结构设计系统自动生成*")
        report.append(f"*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")

        return '\n'.join(report)
