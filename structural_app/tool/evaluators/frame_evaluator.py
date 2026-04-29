"""
Frame evaluator for structural design assessment
Implements frame-specific evaluation with strong column weak beam checks
"""

from typing import Dict, Any, List

try:
    from .base_evaluator import DesignEvaluator
    from .evaluator_config import get_scoring_curves, get_construction_requirements
    from .rag_enhanced_mixin import RAGEnhancedEvaluatorMixin
except ImportError:
    from base_evaluator import DesignEvaluator
    from evaluator_config import get_scoring_curves, get_construction_requirements
    from rag_enhanced_mixin import RAGEnhancedEvaluatorMixin


class FrameEvaluator(DesignEvaluator, RAGEnhancedEvaluatorMixin):
    """
    Concrete evaluator for frame structures

    Frame-specific features:
    - Strong column weak beam checks (强柱弱梁)
    - Column axial ratio checks (柱轴压比)
    - Story drift ratio checks (层间位移角)
    - Safety weight: 45% (most conservative)
    """

    def __init__(self):
        """Initialize frame evaluator"""
        super().__init__()
        self.scoring_curves = get_scoring_curves('frame')
        self.construction_reqs = get_construction_requirements('frame')

    def _get_structure_type(self) -> str:
        """Return structure type identifier"""
        return "frame"

    # ========================================================================
    # Economy Evaluation (20%)
    # ========================================================================

    def evaluate_economy(self, design: Dict[str, Any], results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate economic aspects of frame design

        Components:
        - Comprehensive utilization score (60%): Uses multi-level curve
        - Material usage score (40%): Based on material usage index

        Args:
            design: Design parameters
            results: Analysis results

        Returns:
            Dictionary with score and economic indicators
        """
        # Calculate total material volume
        geometry = design.get('geometry', {})
        num_bays = geometry.get('num_bays', 1)
        num_stories = geometry.get('num_stories', 1)
        bay_widths = geometry.get('bay_widths', [6.0])
        story_heights = geometry.get('story_heights', [4.0])

        columns = geometry.get('columns', {})
        beams = geometry.get('beams', {})
        col_width = columns.get('width', 0.4)
        col_depth = columns.get('depth', 0.4)
        beam_width = beams.get('width', 0.3)
        beam_depth = beams.get('depth', 0.6)

        total_column_length = sum(story_heights) * (num_bays + 1)
        total_beam_length = sum(bay_widths) * num_stories

        column_volume = total_column_length * col_width * col_depth
        beam_volume = total_beam_length * beam_width * beam_depth
        total_volume = column_volume + beam_volume

        # Theoretical minimum volume per DES v2.0
        # Beam: h_min = max(0.3, span/18), V_min = span * 0.2 * h_min
        span = sum(bay_widths) / max(num_bays, 1)
        h_min_beam = max(0.3, span / 18)
        v_min_beam = total_beam_length * 0.2 * h_min_beam
        # Column: use fixed reference 0.3×0.3
        v_min_col = total_column_length * 0.3 * 0.3
        v_min = v_min_beam + v_min_col
        material_usage_index = total_volume / v_min if v_min > 0 else 1.0

        # Comprehensive utilization
        comprehensive_util = self._get_comprehensive_utilization(design, results)
        utilization_score = self.scoring_curves['stress'].calculate_score(comprehensive_util)

        # Material usage score (slope=30 per DES v2.0)
        material_score = min(100, max(0, 100 - (material_usage_index - 1) * 30))

        # Weighted economy score
        economy_score = min(100, utilization_score * 0.6 + material_score * 0.4)

        return {
            'score': round(economy_score, 1),
            'indicators': {
                'comprehensive_utilization': round(comprehensive_util, 4),
                'stress_utilization': round(self._get_stress_utilization(design, results), 4),
                'deflection_utilization': round(self._get_deflection_utilization(design, results), 4),
                'drift_utilization': round(self._get_drift_utilization(design, results), 4),
                'material_usage_index': round(material_usage_index, 3),
                'total_volume_m3': round(total_volume, 4),
                'column_volume_m3': round(column_volume, 4),
                'beam_volume_m3': round(beam_volume, 4),
                'construction_complexity': self._evaluate_construction_complexity(geometry)
            }
        }

    # ========================================================================
    # Structural Efficiency Evaluation (15%)
    # ========================================================================

    def evaluate_efficiency(self, design: Dict[str, Any], results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate structural efficiency of frame design

        Components:
        - Stress utilization score (50%): Uses multi-level curve
        - Utilization uniformity (30%): Coefficient of variation
        - Redundancy index (20%): Based on frame configuration

        Args:
            design: Design parameters
            results: Analysis results

        Returns:
            Dictionary with score and efficiency indicators
        """
        # Get stress utilization
        stress_utilization = self._get_stress_utilization(design, results)
        utilization_score = self.scoring_curves['stress'].calculate_score(stress_utilization)

        # Calculate utilization uniformity using element stresses
        utilization_uniformity = self._calculate_utilization_uniformity(results)
        uniformity_score = utilization_uniformity * 100

        # Weighted efficiency score (50% + 50%, per DES v2.0)
        efficiency_score = (
            utilization_score * 0.5 +
            uniformity_score * 0.5
        )

        return {
            'score': round(efficiency_score, 1),
            'indicators': {
                'average_utilization': round(stress_utilization, 4),
                'utilization_uniformity': round(utilization_uniformity, 4)
            }
        }

    # ========================================================================
    # Safety Evaluation (45% = Strength 20% + Stiffness 15% + Construction 10%)
    # ========================================================================

    def evaluate_safety(self, design: Dict[str, Any], results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate safety aspects of frame design

        Components:
        - Strength score (44.4%): Based on stress utilization
        - Stiffness score (33.3%): Based on deflection and drift utilization
        - Construction score (22.2%): Frame-specific checks (strong column weak beam, axial ratio)

        Args:
            design: Design parameters
            results: Analysis results

        Returns:
            Dictionary with score and safety indicators
        """
        # 1. Strength evaluation: score = max(0, 100 - 40*x), per DES v2.0
        stress_util = self._get_stress_utilization(design, results)
        if stress_util > 1.0:
            strength_score = 0.0
        else:
            strength_score = max(0.0, 100 - 40 * stress_util)

        # 2. Stiffness evaluation: take the more critical of deflection and drift
        deflection_util = self._get_deflection_utilization(design, results)
        drift_util = self._get_drift_utilization(design, results)
        stiffness_util = max(deflection_util, drift_util)
        if stiffness_util > 1.0:
            stiffness_score = 0.0
        else:
            stiffness_score = max(0.0, 100 - 40 * stiffness_util)

        # 3. Construction evaluation
        construction_eval = self.evaluate_construction(design, results)
        construction_score = construction_eval['score'] * 20  # scale 0-5 to 0-100

        # Weighted safety score (50% + 37.5% + 12.5%, per DES v2.0)
        safety_score = (
            strength_score * 0.50 +
            stiffness_score * 0.375 +
            construction_score * 0.125
        )

        # 不合规时安全分上限 60
        code_check = results.get('code_check', {})
        if not code_check.get('compliant', True):
            safety_score = min(safety_score, 60.0)

        # Get code check results
        code_check = results.get('code_check', {})
        safety_factors = code_check.get('safety_factors', {})
        min_safety_factor = min(safety_factors.values()) if safety_factors else 0

        return {
            'score': round(safety_score, 1),
            'indicators': {
                'strength_score': round(strength_score, 1),
                'stiffness_score': round(stiffness_score, 1),
                'construction_score': round(construction_score, 1),
                'min_safety_factor': round(min_safety_factor, 2),
                'stress_utilization': round(stress_util, 4),
                'deflection_utilization': round(deflection_util, 4),
                'drift_utilization': round(drift_util, 4),
                'construction_issues': construction_eval['issues']
            }
        }

    # ========================================================================
    # Sustainability Evaluation (20%)
    # ========================================================================

    def evaluate_sustainability(self, design: Dict[str, Any], results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate sustainability aspects of frame design

        Components:
        - Carbon emission score (50%)
        - Recyclability score (50%)

        Args:
            design: Design parameters
            results: Analysis results

        Returns:
            Dictionary with score and sustainability indicators
        """
        # Calculate total volume
        economy_eval = self.evaluate_economy(design, results)
        total_volume = economy_eval['indicators']['total_volume_m3']

        material = design.get('material', {})
        material_name = material.get('material_name', 'concrete').lower()
        is_steel = 'steel' in material_name or material_name.startswith('q')

        if is_steel:
            density, carbon_factor, recyclability = 7850.0, 1.85, 0.90
        else:
            density, carbon_factor, recyclability = 2400.0, 0.11, 0.15

        total_carbon = total_volume * density * carbon_factor

        # Bearing capacity: use max_shear as base shear (N → kN)
        analysis_results = results.get('results', {})
        max_shear_N = analysis_results.get('max_shear', 0.0)
        base_shear_kN = max(abs(max_shear_N) / 1000.0, 1.0)

        # Carbon intensity score (k=25 for frame, per DES v2.0)
        carbon_intensity = total_carbon / base_shear_kN
        carbon_score = max(0.0, 100 - carbon_intensity * 25)

        recyclability_score = recyclability * 100
        sustainability_score = (carbon_score + recyclability_score) / 2

        return {
            'score': round(sustainability_score, 1),
            'indicators': {
                'carbon_emission_kg': round(total_carbon, 1),
                'carbon_intensity': round(carbon_intensity, 4),
                'base_shear_kN': round(base_shear_kN, 1),
                'recyclability_ratio': round(recyclability, 2)
            }
        }

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _get_stress_utilization(self, design: Dict[str, Any], results: Dict[str, Any]) -> float:
        """Calculate stress utilization ratio"""
        try:
            max_stress = results.get('results', {}).get('max_stress_MPa', 0)
            if max_stress <= 0:
                return 0.5

            material = design.get('material', {})
            fy = material.get('fy', 235e6)
            fy_MPa = fy / 1e6

            allowable_stress = fy_MPa / 1.5
            utilization = max_stress / allowable_stress

            return min(1.0, max(0.0, utilization))
        except:
            return 0.5

    def _get_drift_utilization(self, design: Dict[str, Any], results: Dict[str, Any]) -> float:
        """Calculate story drift utilization ratio (frame-specific)"""
        try:
            max_drift_ratio = results.get('results', {}).get('max_drift_ratio', 0)
            if max_drift_ratio <= 0:
                return 0.3

            # Limit: 1/500
            limit = 1.0 / 500
            utilization = max_drift_ratio / limit

            return min(1.0, max(0.0, utilization))
        except:
            return 0.3

    def _check_structure_specific_construction(
        self, design: Dict[str, Any], results: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Check frame-specific construction requirements

        Checks:
        1. Strong column weak beam (强柱弱梁)
        2. Column axial ratio (柱轴压比)
        3. Story drift ratio (层间位移角)
        4. Beam-column section compatibility

        Args:
            design: Design parameters
            results: Analysis results

        Returns:
            List of construction issues
        """
        issues = []
        geometry = design.get('geometry', {})

        # Get section properties
        columns = geometry.get('columns', {})
        beams = geometry.get('beams', {})
        col_width = columns.get('width', 0.4)
        col_depth = columns.get('depth', 0.4)
        beam_width = beams.get('width', 0.3)
        beam_depth = beams.get('depth', 0.6)

        # Check 1: Strong column weak beam
        # Column moment capacity should be > beam moment capacity
        col_section_modulus = col_width * col_depth ** 2 / 6
        beam_section_modulus = beam_width * beam_depth ** 2 / 6

        if col_section_modulus < beam_section_modulus * 1.2:
            issues.append({
                'type': 'weak_column',
                'severity': 'severe',
                'message': f'柱截面可能不满足强柱弱梁要求',
                'recommendation': '增大柱截面或减小梁截面'
            })

        # Check 2: Column axial ratio
        # Get max axial force from results
        detailed_results = results.get('results', {}).get('detailed_results', {})
        axial_forces = detailed_results.get('axial_forces', [])

        if axial_forces:
            max_axial = max([abs(af.get('N_i', 0)) for af in axial_forces] +
                          [abs(af.get('N_j', 0)) for af in axial_forces])

            # Calculate column area and allowable axial force
            col_area = col_width * col_depth
            material = design.get('material', {})
            fy = material.get('fy', 235e6)
            allowable_axial = col_area * fy * 0.9  # 0.9 reduction factor

            axial_ratio = max_axial / allowable_axial if allowable_axial > 0 else 0

            if axial_ratio > 0.9:
                issues.append({
                    'type': 'high_axial_ratio',
                    'severity': 'severe',
                    'message': f'柱轴压比过高（{axial_ratio:.2f} > 0.9）',
                    'recommendation': '增大柱截面'
                })
            elif axial_ratio > 0.75:
                issues.append({
                    'type': 'moderate_axial_ratio',
                    'severity': 'moderate',
                    'message': f'柱轴压比偏高（{axial_ratio:.2f} > 0.75）',
                    'recommendation': '建议增大柱截面以提高安全裕度'
                })

        # Check 3: Story drift ratio
        max_drift_ratio = results.get('results', {}).get('max_drift_ratio', 0)
        limit = 1.0 / 500

        if max_drift_ratio > limit:
            issues.append({
                'type': 'excessive_drift',
                'severity': 'severe',
                'message': f'层间位移角超限（{max_drift_ratio:.6f} > {limit:.6f}）',
                'recommendation': '增大柱/梁刚度或减小水平荷载'
            })
        elif max_drift_ratio > limit * 0.8:
            issues.append({
                'type': 'high_drift',
                'severity': 'moderate',
                'message': f'层间位移角接近限值（{max_drift_ratio:.6f} > {limit*0.8:.6f}）',
                'recommendation': '建议适当增大刚度以提高使用性能'
            })

        # Check 4: Beam-column section compatibility
        if beam_depth > col_depth * 0.8:
            issues.append({
                'type': 'beam_column_incompatible',
                'severity': 'minor',
                'message': f'梁高（{beam_depth}m）与柱高（{col_depth}m）过于接近',
                'recommendation': '注意节点连接构造处理'
            })

        # Check 5: Beam height-span ratio (1/18 ~ 1/10, per DES v2.0)
        geometry = design.get('geometry', {})
        bay_widths = geometry.get('bay_widths', [6.0])
        span = sum(bay_widths) / max(len(bay_widths), 1)
        beam_height_span = beam_depth / span if span > 0 else 0
        if beam_height_span < 1 / 18:
            issues.append({
                'type': 'beam_height_span_low',
                'severity': 'moderate',
                'message': f'框架梁高跨比过小 ({beam_height_span:.3f} < {1/18:.3f})',
                'recommendation': '增加梁高或减小跨度'
            })
        elif beam_height_span > 1 / 10:
            issues.append({
                'type': 'beam_height_span_high',
                'severity': 'minor',
                'message': f'框架梁高跨比偏大 ({beam_height_span:.3f} > {1/10:.3f})',
                'recommendation': '可适当减小梁高以提高经济性'
            })

        # Check 6: Column height-thickness ratio (1/25 ~ 1/15, per DES v2.0)
        story_heights = geometry.get('story_heights', [4.0])
        story_h = sum(story_heights) / max(len(story_heights), 1)
        col_height_thickness = col_depth / story_h if story_h > 0 else 0
        if col_height_thickness < 1 / 25:
            issues.append({
                'type': 'col_height_thickness_low',
                'severity': 'moderate',
                'message': f'柱截面高厚比过小 ({col_height_thickness:.3f} < {1/25:.3f})',
                'recommendation': '增加柱截面尺寸'
            })

        # Check 7: Beam width should not exceed column width (per DES v2.0)
        if beam_width > col_width:
            issues.append({
                'type': 'beam_wider_than_column',
                'severity': 'moderate',
                'message': f'梁宽 ({beam_width}m) 大于柱宽 ({col_width}m)',
                'recommendation': '梁宽不宜大于柱宽，建议减小梁宽或增大柱宽'
            })

        return issues

    def _calculate_utilization_uniformity(self, results: Dict[str, Any]) -> float:
        """
        Calculate how uniform the stress utilization is across all elements

        Uses element stresses from analyzer if available, otherwise falls back to moment distribution.
        Calculates utilization ratio u_i = σ_i / (fy/1.5) for each element, then computes
        coefficient of variation (CV) to measure uniformity.
        """
        try:
            detailed_results = results.get('results', {}).get('detailed_results', {})

            # Try to get element stresses from analyzer (preferred method)
            element_stresses = detailed_results.get('extra', {}).get('element_stresses', [])

            if element_stresses and len(element_stresses) >= 2:
                # Get material yield strength
                material = results.get('results', {}).get('detailed_results', {}).get('material', {})
                fy = material.get('fy', 235e6)  # Default Q235 steel
                fy_Pa = fy if fy > 1000 else fy * 1e6
                allowable_stress = fy_Pa / 1.5  # Allowable stress

                # Calculate utilization ratio for each element
                utilizations = [sigma / allowable_stress for sigma in element_stresses if allowable_stress > 0]

                if not utilizations:
                    return 0.7

                # Calculate coefficient of variation (CV)
                avg_util = sum(utilizations) / len(utilizations)
                if avg_util == 0:
                    return 1.0

                variance = sum((u - avg_util) ** 2 for u in utilizations) / len(utilizations)
                std_dev = variance ** 0.5
                cv = std_dev / avg_util

                # Uniformity score: CV=0 → 1.0, CV≥1 → 0
                uniformity = max(0, min(1, 1 - cv))
                return uniformity

            else:
                # Fallback: use moment distribution (original method)
                moments = detailed_results.get('moments', [])

                if not moments or len(moments) < 2:
                    return 0.7

                # Extract moment values
                moment_values = []
                for m in moments:
                    if isinstance(m, dict):
                        moment_values.append(abs(m.get('M_i', 0)))
                        moment_values.append(abs(m.get('M_j', 0)))
                    else:
                        moment_values.append(abs(m))

                if not moment_values:
                    return 0.7

                avg_moment = sum(moment_values) / len(moment_values)
                if avg_moment == 0:
                    return 1.0

                variance = sum((m - avg_moment) ** 2 for m in moment_values) / len(moment_values)
                std_dev = variance ** 0.5
                cv = std_dev / avg_moment

                uniformity = max(0, min(1, 1 - cv / 2))
                return uniformity

        except Exception as e:
            return 0.7

    def _evaluate_construction_complexity(self, geometry: Dict[str, Any]) -> str:
        """Evaluate construction complexity based on frame configuration"""
        num_bays = geometry.get('num_bays', 1)
        num_stories = geometry.get('num_stories', 1)

        total_elements = num_bays * num_stories + (num_bays + 1) * num_stories

        if num_stories > 5 or num_bays > 4 or total_elements > 30:
            return "high"
        elif num_stories > 3 or num_bays > 2 or total_elements > 15:
            return "medium"
        else:
            return "low"

