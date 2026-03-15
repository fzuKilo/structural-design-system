"""
Continuous beam evaluator for structural design assessment
Implements 4-dimensional evaluation with multi-level scoring curves
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


class ContinuousBeamEvaluator(DesignEvaluator, RAGEnhancedEvaluatorMixin):
    """
    Concrete evaluator for continuous beam structures

    Key differences from simply supported beam:
    - Stricter deflection limit (L/300 vs L/250)
    - More slender height-span ratio allowed (0.04-0.12)
    - Multiple span considerations
    """

    def __init__(self):
        """Initialize continuous beam evaluator"""
        super().__init__()
        self.scoring_curves = get_scoring_curves('continuous_beam')
        self.construction_reqs = get_construction_requirements('continuous_beam')

    def _get_structure_type(self) -> str:
        """Return structure type identifier"""
        return "continuous_beam"

    def evaluate_economy(self, design: Dict[str, Any], results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate economic aspects of continuous beam design

        Components:
        - Comprehensive utilization score (60%)
        - Material usage score (40%)
        """
        # Calculate material volume
        geometry = design.get('geometry', {})
        length = geometry.get('length', 1.0)
        width = geometry.get('width', 0.3)
        height = geometry.get('height', 0.5)
        volume = length * width * height

        # Theoretical minimum volume based on min height-span ratio (continuous beam: 1/15)
        h_min = max(0.3, length / 15)
        v_min = length * 0.2 * h_min
        material_usage_index = volume / v_min if v_min > 0 else 1.0

        # Comprehensive utilization
        comprehensive_util = self._get_comprehensive_utilization(design, results)

        # Use multi-level scoring curve
        utilization_score = self.scoring_curves['stress'].calculate_score(comprehensive_util)

        # Material usage score (slope=30 per DES v2.0)
        material_score = max(0, 100 - (material_usage_index - 1) * 30)

        # Weighted economy score
        economy_score = utilization_score * 0.6 + material_score * 0.4

        return {
            'score': round(economy_score, 1),
            'indicators': {
                'comprehensive_utilization': round(comprehensive_util, 4),
                'stress_utilization': round(self._get_stress_utilization(design, results), 4),
                'deflection_utilization': round(self._get_deflection_utilization(design, results), 4),
                'material_usage_index': round(material_usage_index, 3),
                'volume_m3': round(volume, 4),
                'construction_complexity': self._evaluate_construction_complexity(geometry)
            }
        }

    def evaluate_efficiency(self, design: Dict[str, Any], results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate structural efficiency of continuous beam design

        Components:
        - Stress utilization score (50%)
        - Utilization uniformity (30%)
        - Redundancy index (20%)
        """
        # Get stress utilization
        stress_utilization = self._get_stress_utilization(design, results)

        # Use multi-level scoring curve
        utilization_score = self.scoring_curves['stress'].calculate_score(stress_utilization)

        # Calculate utilization uniformity using element stresses
        utilization_uniformity = self._calculate_utilization_uniformity(design, results)
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

    def evaluate_safety(self, design: Dict[str, Any], results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate safety aspects of continuous beam design

        Components:
        - Strength score (50%): Based on stress utilization
        - Stiffness score (37.5%): Based on deflection utilization
        - Construction score (12.5%): Deduction-based construction checks
        """
        # 1. Strength evaluation: score = max(0, 100 - 40*x), per DES v2.0
        stress_util = self._get_stress_utilization(design, results)
        if stress_util > 1.0:
            strength_score = 0.0
        else:
            strength_score = max(0.0, 100 - 40 * stress_util)

        # 2. Stiffness evaluation: score = max(0, 100 - 40*x), per DES v2.0
        deflection_util = self._get_deflection_utilization(design, results)
        if deflection_util > 1.0:
            stiffness_score = 0.0
        else:
            stiffness_score = max(0.0, 100 - 40 * deflection_util)

        # 3. Construction evaluation (deduction-based)
        construction_eval = self.evaluate_construction(design, results)
        construction_score = construction_eval['score'] * 20  # Scale 0-5 to 0-100

        # Weighted safety score
        safety_score = (
            strength_score * 0.50 +
            stiffness_score * 0.375 +
            construction_score * 0.125
        )

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
                'construction_issues': construction_eval['issues']
            }
        }

    def evaluate_sustainability(self, design: Dict[str, Any], results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate sustainability aspects of continuous beam design

        Components:
        - Carbon emission score (50%)
        - Recyclability score (50%)
        """
        # Calculate carbon emissions
        geometry = design.get('geometry', {})
        length = geometry.get('length', 1.0)
        width = geometry.get('width', 0.3)
        height = geometry.get('height', 0.5)
        volume = length * width * height

        material = design.get('material', {})
        material_name = material.get('material_name', 'concrete').lower()
        is_steel = 'steel' in material_name or material_name.startswith('q')

        if is_steel:
            density, carbon_factor, recyclability = 7850.0, 1.85, 0.90
        else:
            density, carbon_factor, recyclability = 2400.0, 0.11, 0.15

        total_carbon = volume * density * carbon_factor

        fy = material.get('fy', 235e6)
        fy_MPa = fy / 1e6 if fy > 1000 else fy
        W = width * height ** 2 / 6
        M_u = max(fy_MPa * 1e3 * W, 1.0)

        carbon_intensity = total_carbon / M_u
        carbon_score = max(0.0, 100 - carbon_intensity * 20)
        recyclability_score = recyclability * 100
        sustainability_score = (carbon_score + recyclability_score) / 2

        return {
            'score': round(sustainability_score, 1),
            'indicators': {
                'carbon_emission_kg': round(total_carbon, 1),
                'carbon_intensity': round(carbon_intensity, 4),
                'M_u_kNm': round(M_u, 1),
                'recyclability_ratio': round(recyclability, 2)
            }
        }

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

    def _calculate_utilization_uniformity(self, design: Dict[str, Any], results: Dict[str, Any]) -> float:
        """Calculate uniformity of stress utilization across elements"""
        try:
            stresses = results.get('results', {}).get('stresses', [])
            if not stresses or len(stresses) < 2:
                return 0.7

            material = design.get('material', {})
            fy = material.get('fy', 235e6)
            fy_Pa = fy if fy > 1000 else fy * 1e6
            allowable = fy_Pa / 1.5

            utilizations = [abs(s) / allowable for s in stresses if allowable > 0]
            if not utilizations:
                return 0.7

            u_avg = sum(utilizations) / len(utilizations)
            if u_avg == 0:
                return 1.0

            variance = sum((u - u_avg) ** 2 for u in utilizations) / len(utilizations)
            cv = variance ** 0.5 / u_avg

            return max(0.0, min(1.0, 1 - cv))
        except:
            return 0.7

    def _evaluate_construction_complexity(self, geometry: Dict[str, Any]) -> str:
        """
        Evaluate construction complexity for continuous beam

        Factors:
        - Number of spans
        - Section dimensions
        """
        n_spans = geometry.get('n_spans', 2)
        length = geometry.get('length', 1.0)
        height = geometry.get('height', 0.5)

        # More spans = higher complexity
        if n_spans >= 4:
            return "high"
        elif n_spans == 3:
            return "medium"
        elif length > 20 or height > 1.5:
            return "medium"
        else:
            return "low"

    def _check_structure_specific_construction(
        self,
        design: Dict[str, Any],
        results: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Check continuous beam-specific construction requirements

        Checks:
        - Height-span ratio (0.04-0.12, more slender than simple beam)
        - Width-height ratio (0.33-0.67)
        - Minimum section dimensions
        - Number of spans (2-5)
        """
        issues = []
        geometry = design.get('geometry', {})

        length = geometry.get('length', 1.0)
        width = geometry.get('width', 0.3)
        height = geometry.get('height', 0.5)
        n_spans = geometry.get('n_spans', 2)

        # Check number of spans
        if n_spans < 2:
            issues.append({
                'type': 'span_count_low',
                'severity': 'severe',
                'message': f'跨数过少 ({n_spans} < 2)',
                'recommendation': '连续梁至少需要2跨'
            })
        elif n_spans > 5:
            issues.append({
                'type': 'span_count_high',
                'severity': 'moderate',
                'message': f'跨数过多 ({n_spans} > 5)',
                'recommendation': '建议减少跨数或分段设计'
            })

        # Height-span ratio check (continuous beam: 0.04-0.12)
        height_span_ratio = height / length
        min_ratio, max_ratio = self.construction_reqs['height_span_ratio']

        if height_span_ratio < min_ratio:
            issues.append({
                'type': 'height_span_ratio_low',
                'severity': 'moderate',
                'message': f'高跨比过小 ({height_span_ratio:.3f} < {min_ratio})',
                'recommendation': '增加梁高或减小跨度'
            })
        elif height_span_ratio > max_ratio:
            issues.append({
                'type': 'height_span_ratio_high',
                'severity': 'minor',
                'message': f'高跨比过大 ({height_span_ratio:.3f} > {max_ratio})',
                'recommendation': '减小梁高以提高经济性'
            })

        # Width-height ratio check
        width_height_ratio = width / height
        min_wh, max_wh = self.construction_reqs['width_height_ratio']

        if width_height_ratio < min_wh:
            issues.append({
                'type': 'width_height_ratio_low',
                'severity': 'moderate',
                'message': f'宽高比过小 ({width_height_ratio:.3f} < {min_wh})',
                'recommendation': '增加梁宽以提高稳定性'
            })
        elif width_height_ratio > max_wh:
            issues.append({
                'type': 'width_height_ratio_high',
                'severity': 'minor',
                'message': f'宽高比过大 ({width_height_ratio:.3f} > {max_wh})',
                'recommendation': '减小梁宽或增加梁高'
            })

        # Minimum dimensions check
        min_width = self.construction_reqs['min_width']
        min_height = self.construction_reqs['min_height']

        if width < min_width:
            issues.append({
                'type': 'width_too_small',
                'severity': 'severe',
                'message': f'梁宽过小 ({width}m < {min_width}m)',
                'recommendation': f'增加梁宽至至少{min_width}m'
            })

        if height < min_height:
            issues.append({
                'type': 'height_too_small',
                'severity': 'severe',
                'message': f'梁高过小 ({height}m < {min_height}m)',
                'recommendation': f'增加梁高至至少{min_height}m'
            })

        return issues
