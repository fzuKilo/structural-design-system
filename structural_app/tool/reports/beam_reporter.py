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
                       evaluation: Dict[str, Any] = None, drawings: Dict[str, Any] = None,
                       bim: Dict[str, Any] = None, ifc: Dict[str, Any] = None) -> str:
        """
        Generate a structured Markdown report for beam design

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
        report_filename = f"beam_design_report_{timestamp}.md"
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
        structure_type = design.get('type', 'beam')
        report.append(f"| 结构类型 | {self.get_structure_display_name(structure_type)} |")
        if structure_type == 'continuous_beam':
            n_spans = geometry.get('n_spans', 2)
            total_length = geometry.get('length', 0)
            span_length = total_length / n_spans if n_spans > 0 else 0
            report.append(f"| 总跨度 | {total_length} m |")
            report.append(f"| 跨数 | {n_spans} 跨 |")
            report.append(f"| 每跨跨度 | {span_length:.2f} m（均等）|")
            support_desc = "、".join(
                [f"支座{i+1}: {'铰支座' if i == 0 else '滚动支座'}"
                 for i in range(n_spans + 1)]
            )
            report.append(f"| 支座配置 | {support_desc} |")
        else:
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
        report.append(f"**分布荷载**: {len(distributed_loads)} 个")
        report.append("")
        report.append(f"**集中荷载**: {len(point_loads)} 个")
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
        report.append(f"**支座类型**: {self.translate_support_type(constraints.get('support_type', 'N/A'))}")
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

            # Alert thresholds
            SEVERE = 60
            WARNING = 70

            alerts = []
            safety_score = dimensions.get('safety', {}).get('score', 100)
            economy_score = dimensions.get('economy', {}).get('score', 100)
            efficiency_score = dimensions.get('structural_efficiency', {}).get('score', 100)
            sustainability_score = dimensions.get('sustainability', {}).get('score', 100)

            if safety_score < SEVERE:
                alerts.append(("🔴 严重", "安全性", f"得分 {safety_score:.1f}，存在安全风险，建议立即增大截面或提高材料强度"))
            elif safety_score < WARNING:
                alerts.append(("🟡 警告", "安全性", f"得分 {safety_score:.1f}，安全裕度较小，可适当增大截面"))
            if economy_score < SEVERE:
                alerts.append(("🔴 严重", "经济性", f"得分 {economy_score:.1f}，材料浪费严重，建议优化截面尺寸"))
            elif economy_score < WARNING:
                alerts.append(("🟡 警告", "经济性", f"得分 {economy_score:.1f}，材料利用率偏低，可尝试减小截面"))
            if efficiency_score < SEVERE:
                alerts.append(("🔴 严重", "结构效率", f"得分 {efficiency_score:.1f}，应力分布不均，建议优化截面形式"))
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

            # Dimension detail analysis
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

                # Economy indicators
                econ_ind = dimensions.get('economy', {}).get('indicators', {})
                if econ_ind:
                    report.append("#### 经济性分析")
                    report.append("")
                    report.append("| 指标 | 值 | 说明 |")
                    report.append("|------|-----|------|")
                    util = econ_ind.get('comprehensive_utilization', None)
                    if util is not None:
                        report.append(f"| 综合利用率 | {util:.3f} | 应力+挠度综合利用率，越接近1越经济 |")
                    stress_util = econ_ind.get('stress_utilization', None)
                    if stress_util is not None:
                        report.append(f"| 应力利用率 | {stress_util:.3f} | 实际应力/许用应力 |")
                    defl_util = econ_ind.get('deflection_utilization', None)
                    if defl_util is not None:
                        report.append(f"| 挠度利用率 | {defl_util:.3f} | 实际挠度/限值挠度 |")
                    mat_idx = econ_ind.get('material_usage_index', None)
                    if mat_idx is not None:
                        report.append(f"| 材料用量指数 | {mat_idx:.3f} | 实际用量/理论最小用量，越接近1越省料 |")
                    vol = econ_ind.get('volume_m3', None)
                    if vol is not None:
                        report.append(f"| 材料体积 | {vol:.4f} m³ | |")
                    report.append("")

                # Efficiency indicators
                eff_ind = dimensions.get('structural_efficiency', {}).get('indicators', {})
                if eff_ind:
                    report.append("#### 结构效率分析")
                    report.append("")
                    report.append("| 指标 | 值 | 说明 |")
                    report.append("|------|-----|------|")
                    avg_util = eff_ind.get('average_utilization', None)
                    if avg_util is not None:
                        report.append(f"| 平均应力利用率 | {avg_util:.3f} | 截面平均应力/许用应力 |")
                    uniformity = eff_ind.get('utilization_uniformity', None)
                    if uniformity is not None:
                        report.append(f"| 利用率均匀性 | {uniformity:.3f} | 越接近1说明应力分布越均匀 |")
                    report.append("")

                # Safety indicators
                safe_ind = dimensions.get('safety', {}).get('indicators', {})
                if safe_ind:
                    report.append("#### 安全性分析")
                    report.append("")
                    report.append("| 指标 | 值 | 说明 |")
                    report.append("|------|-----|------|")
                    str_score = safe_ind.get('strength_score', None)
                    if str_score is not None:
                        report.append(f"| 强度得分 | {str_score:.1f} | 基于应力利用率计算 |")
                    stiff_score = safe_ind.get('stiffness_score', None)
                    if stiff_score is not None:
                        report.append(f"| 刚度得分 | {stiff_score:.1f} | 基于挠度利用率计算 |")
                    min_sf = safe_ind.get('min_safety_factor', None)
                    if min_sf is not None:
                        sf_flag = "✓" if min_sf >= 1.0 else "✗"
                        report.append(f"| 最小安全系数 | {min_sf:.2f} {sf_flag} | <1.0 表示不满足规范 |")
                    constr_score = safe_ind.get('construction_score', None)
                    if constr_score is not None:
                        report.append(f"| 构造得分 | {constr_score:.1f} | 构造措施检查得分 |")
                    constr_issues = safe_ind.get('construction_issues', [])
                    report.append("")
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

                # Sustainability indicators
                sust_ind = dimensions.get('sustainability', {}).get('indicators', {})
                if sust_ind:
                    report.append("#### 可持续性分析")
                    report.append("")
                    report.append("| 指标 | 值 | 说明 |")
                    report.append("|------|-----|------|")
                    carbon = sust_ind.get('carbon_emission_kg', None)
                    if carbon is not None:
                        report.append(f"| 碳排放量 | {carbon:.1f} kg CO₂ | |")
                    intensity = sust_ind.get('carbon_intensity', None)
                    if intensity is not None:
                        report.append(f"| 碳排放强度 | {intensity:.4f} kg/kN·m | 越低越好 |")
                    recyclability = sust_ind.get('recyclability_ratio', None)
                    if recyclability is not None:
                        report.append(f"| 可回收率 | {recyclability*100:.0f}% | |")
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
                    report.append(f"| {drawing_type} | cad/{os.path.basename(filepath)} |")
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
        report.append("*本报告由 OpenManus 结构设计系统自动生成*")
        report.append(f"*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")

        return '\n'.join(report)
