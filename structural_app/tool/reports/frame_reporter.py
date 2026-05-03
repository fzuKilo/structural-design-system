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
                       evaluation: Dict[str, Any] = None, drawings: Dict[str, Any] = None,
                       bim: Dict[str, Any] = None, ifc: Dict[str, Any] = None) -> str:
        """
        Generate a structured Markdown report for frame design

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
        report_filename = f"frame_design_report_{timestamp}.md"
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
        structure_type = design.get('type', 'frame')
        report.append(f"| 结构类型 | {self.get_structure_display_name(structure_type)} |")
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
        _type_map = {'rectangular': '矩形', 'circular': '圆形', 'I': 'I形', 'T': 'T形'}
        report.append(f"| 截面类型 | {_type_map.get(columns.get('type', ''), columns.get('type', 'N/A'))} |")
        report.append(f"| 宽度 | {columns.get('width', 0)} m |")
        report.append(f"| 深度 | {columns.get('depth', 0)} m |")
        report.append("")

        # Beam section
        beams = geometry.get('beams', {})
        report.append("**梁截面**")
        report.append("")
        report.append("| 项目 | 值 |")
        report.append("|------|-----|")
        report.append(f"| 截面类型 | {_type_map.get(beams.get('type', ''), beams.get('type', 'N/A'))} |")
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
                alerts.append(("🔴 严重", "安全性", f"得分 {safety_score:.1f}，存在安全风险，建议立即增大柱截面或提高材料强度"))
            elif safety_score < WARNING:
                alerts.append(("🟡 警告", "安全性", f"得分 {safety_score:.1f}，安全裕度较小，可适当增大柱截面"))
            if economy_score < SEVERE:
                alerts.append(("🔴 严重", "经济性", f"得分 {economy_score:.1f}，材料浪费严重，建议优化截面尺寸"))
            elif economy_score < WARNING:
                alerts.append(("🟡 警告", "经济性", f"得分 {economy_score:.1f}，材料利用率偏低，可尝试减小截面"))
            if efficiency_score < SEVERE:
                alerts.append(("🔴 严重", "结构效率", f"得分 {efficiency_score:.1f}，框架受力不均，建议优化结构布置"))
            elif efficiency_score < WARNING:
                alerts.append(("🟡 警告", "结构效率", f"得分 {efficiency_score:.1f}，截面利用率偏低"))
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
                report.append(f"| 经济性 | {economy_score:.1f} | 20% |")
                report.append(f"| 结构效率 | {efficiency_score:.1f} | 15% |")
                report.append(f"| 安全性 | {safety_score:.1f} | 45% |")
                report.append(f"| 可持续性 | {sustainability_score:.1f} | 20% |")
                report.append("")

                econ_ind = dimensions.get('economy', {}).get('indicators', {})
                if econ_ind:
                    report.append("#### 经济性分析")
                    report.append("")
                    report.append("| 指标 | 值 | 说明 |")
                    report.append("|------|-----|------|")
                    for key, label, desc in [
                        ('comprehensive_utilization', '综合利用率', '应力+挠度综合利用率，越接近1越经济'),
                        ('stress_utilization', '应力利用率', '实际应力/许用应力'),
                        ('material_usage_index', '材料用量指数', '实际用量/理论最小用量'),
                        ('volume_m3', '材料体积 (m³)', ''),
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
                        ('average_utilization', '平均应力利用率', '截面平均应力/许用应力'),
                        ('utilization_uniformity', '利用率均匀性', '越接近1说明应力分布越均匀'),
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
                        ('stress_utilization', '应力利用率', '实际应力/许用应力'),
                        ('deflection_utilization', '挠度利用率', '实际挠度/限值挠度'),
                        ('drift_utilization', '层间位移角利用率', '实际层间位移角/限值'),
                        ('min_safety_factor', '最小安全系数', '<1.0 表示不满足规范'),
                        ('construction_score', '构造得分', '构造措施检查得分'),
                    ]:
                        val = safe_ind.get(key)
                        if val is not None:
                            flag = " ✓" if key == 'min_safety_factor' and val >= 1.0 else (" ✗" if key == 'min_safety_factor' else "")
                            report.append(f"| {label} | {val:.4f}{flag} | {desc} |")
                    report.append("")

                    construction_issues = safe_ind.get('construction_issues', [])
                    if construction_issues:
                        report.append("**构造问题：**")
                        report.append("")
                        _severity_map = {
                            'severe': '严重', 'moderate': '中等', 'minor': '轻微',
                            'critical': '严重', 'warning': '警告', 'unknown': '未知'
                        }
                        for issue in construction_issues:
                            severity = issue.get('severity', 'unknown') if isinstance(issue, dict) else ''
                            message = issue.get('message', str(issue)) if isinstance(issue, dict) else str(issue)
                            recommendation = issue.get('recommendation', '') if isinstance(issue, dict) else ''
                            citation = issue.get('citation', '') if isinstance(issue, dict) else ''
                            severity_cn = _severity_map.get(severity.lower(), severity)
                            report.append(f"- **{severity_cn}**: {message}")
                            if citation:
                                report.append(f"  - 规范依据：{citation}")
                            if recommendation:
                                report.append(f"  - 建议: {recommendation}")
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
                for drawing_type, file_path in files.items():
                    report.append(f"| {drawing_type} | cad/{os.path.basename(file_path)} |")
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
                report.append(f"- 文件路径: `bim/{os.path.basename(ifc.get('path', ''))}`")
                report.append("")

        # Footer
        report.append("---")
        report.append("")
        report.append("*本报告由OpenManus结构设计系统自动生成*")
        report.append("")

        return "\n".join(report)
