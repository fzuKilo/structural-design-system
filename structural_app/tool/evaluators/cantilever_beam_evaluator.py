"""
Cantilever beam evaluator for structural design assessment
Implements 4-dimensional evaluation with cantilever-specific parameters
"""

from typing import Dict, Any, List

try:
    from .base_evaluator import DesignEvaluator
    from .evaluator_config import get_scoring_curves, get_construction_requirements
except ImportError:
    from base_evaluator import DesignEvaluator
    from evaluator_config import get_scoring_curves, get_construction_requirements


class CantileverBeamEvaluator(DesignEvaluator):
    """
    Concrete evaluator for cantilever beam structures

    Key differences from simply supported beam:
    - More conservative scoring curves (lower optimal utilization)
    - Stricter deflection limits (L/200 vs L/250)
    - Different construction requirements (larger height-span ratio)
    - Higher safety weight (45% vs 40%)
    """

    def __init__(self):
        """Initialize cantilever beam evaluator"""
        super().__init__()
        self.scoring_curves = get_scoring_curves('cantilever_beam')
        self.construction_reqs = get_construction_requirements('cantilever_beam')

    def _get_structure_type(self) -> str:
        """Return structure type identifier"""
        return "cantilever_beam"

    # ========================================================================
    # Economy Evaluation (20%)
    # ========================================================================

    def evaluate_economy(self, design: Dict[str, Any], results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate economic aspects of cantilever beam design

        Components:
        - Comprehensive utilization score (60%): Uses multi-level curve
        - Material usage score (40%): Based on material usage index

        Args:
            design: Design parameters
            results: Analysis results

        Returns:
            Dictionary with score and economic indicators
        """
        # Calculate material volume
        geometry = design.get('geometry', {})
        length = geometry.get('length', 1.0)
        width = geometry.get('width', 0.3)
        height = geometry.get('height', 0.5)
        volume = length * width * height

        # Material usage index (cantilever typically needs more material)
        theoretical_min = length * 0.25 * 0.5  # Cantilever needs larger sections
        material_usage_index = volume / theoretical_min if theoretical_min > 0 else 1.0

        # Comprehensive utilization
        comprehensive_util = self._get_comprehensive_utilization(design, results)

        # Use multi-level scoring curve for utilization
        utilization_score = self.scoring_curves['stress'].calculate_score(comprehensive_util)

        # Material usage score
        material_score = max(0, 100 - (material_usage_index - 1) * 50)

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

    # ========================================================================
    # Structural Efficiency Evaluation (20%)
    # ========================================================================

    def evaluate_efficiency(self, design: Dict[str, Any], results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate structural efficiency of cantilever beam design

        Components:
        - Stress utilization score (50%): Uses multi-level curve
        - Utilization uniformity (30%): Coefficient of variation
        - Redundancy index (20%): Element count proxy

        Args:
            design: Design parameters
            results: Analysis results

        Returns:
            Dictionary with score and efficiency indicators
        """
        # Get stress utilization
        stress_utilization = self._get_stress_utilization(design, results)

        # Use multi-level scoring curve
        utilization_score = self.scoring_curves['stress'].calculate_score(stress_utilization)

        # Calculate utilization uniformity
        utilization_uniformity = self._calculate_utilization_uniformity(results)
        uniformity_score = utilization_uniformity * 100

        # Redundancy index
        geometry = design.get('geometry', {})
        n_elements = geometry.get('n_elements', 20)
        redundancy_index = min(1.5, n_elements / 20)
        redundancy_score = min(100, redundancy_index * 50)

        # Weighted efficiency score
        efficiency_score = (
            utilization_score * 0.5 +
            uniformity_score * 0.3 +
            redundancy_score * 0.2
        )

        return {
            'score': round(efficiency_score, 1),
            'indicators': {
                'average_utilization': round(stress_utilization, 4),
                'utilization_uniformity': round(utilization_uniformity, 4),
                'redundancy_index': round(redundancy_index, 2)
            }
        }

    # ========================================================================
    # Safety Evaluation (45% - Higher than beam due to cantilever nature)
    # ========================================================================

    def evaluate_safety(self, design: Dict[str, Any], results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate safety aspects of cantilever beam design

        Components:
        - Strength score (50%): Based on stress utilization
        - Stiffness score (37.5%): Based on deflection utilization
        - Construction score (12.5%): Deduction-based construction checks

        Args:
            design: Design parameters
            results: Analysis results

        Returns:
            Dictionary with score and safety indicators
        """
        # 1. Strength evaluation
        stress_util = self._get_stress_utilization(design, results)
        strength_score = max(0, 100 - stress_util * 100)

        # 2. Stiffness evaluation
        deflection_util = self._get_deflection_utilization(design, results)
        stiffness_score = max(0, 100 - deflection_util * 100)

        # 3. Construction evaluation
        construction_eval = self.evaluate_construction(design, results)
        construction_score = construction_eval['score'] * 20

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

    # ========================================================================
    # Sustainability Evaluation (15%)
    # ========================================================================

    def evaluate_sustainability(self, design: Dict[str, Any], results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate sustainability aspects of cantilever beam design

        Components:
        - Carbon emission score (50%)
        - Recyclability score (50%)

        Args:
            design: Design parameters
            results: Analysis results

        Returns:
            Dictionary with score and sustainability indicators
        """
        # Calculate carbon emissions
        geometry = design.get('geometry', {})
        volume = geometry.get('length', 1.0) * geometry.get('width', 0.3) * geometry.get('height', 0.5)

        # Concrete: ~2400 kg/m^3, ~0.11 kg CO2/kg
        carbon_emission = volume * 2400 * 0.11

        # Recyclability
        material = design.get('material', {})
        material_name = material.get('material_name', 'concrete').lower()
        recyclability = 0.9 if 'steel' in material_name or 'q' in material_name else 0.15

        # Scoring
        carbon_score = max(0, 100 - carbon_emission / 5)
        recyclability_score = recyclability * 100

        sustainability_score = (carbon_score + recyclability_score) / 2

        return {
            'score': round(sustainability_score, 1),
            'indicators': {
                'carbon_emission_kg': round(carbon_emission, 1),
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

    def _check_structure_specific_construction(
        self, design: Dict[str, Any], results: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Check cantilever beam-specific construction requirements

        Checks:
        1. Height-span ratio (1/12.5 to 1/5 for cantilever)
        2. Width-height ratio (1/3 to 1/1.5)
        3. Minimum section dimensions

        Args:
            design: Design parameters
            results: Analysis results

        Returns:
            List of construction issues
        """
        issues = []
        geometry = design.get('geometry', {})

        length = geometry.get('length', 1.0)
        height = geometry.get('height', 0.5)
        width = geometry.get('width', 0.3)

        # Check 1: Height-span ratio (cantilever needs larger ratio)
        height_span_ratio = height / length
        min_ratio, max_ratio = self.construction_reqs['height_span_ratio']

        if height_span_ratio < min_ratio:
            issues.append({
                'type': 'height_span_ratio_low',
                'severity': 'severe',  # More severe for cantilever
                'message': f'Height-span ratio too small for cantilever ({height_span_ratio:.3f} < {min_ratio:.3f})',
                'recommendation': 'Increase beam height significantly or reduce span'
            })
        elif height_span_ratio > max_ratio:
            issues.append({
                'type': 'height_span_ratio_high',
                'severity': 'minor',
                'message': f'Height-span ratio too large ({height_span_ratio:.3f} > {max_ratio:.3f})',
                'recommendation': 'Consider reducing beam height for economy'
            })

        # Check 2: Width-height ratio
        width_height_ratio = width / height
        min_wh, max_wh = self.construction_reqs['width_height_ratio']

        if width_height_ratio < min_wh:
            issues.append({
                'type': 'width_height_ratio_low',
                'severity': 'moderate',  # More important for cantilever stability
                'message': f'Width-height ratio too small ({width_height_ratio:.2f} < {min_wh:.2f})',
                'recommendation': 'Increase beam width for lateral stability'
            })
        elif width_height_ratio > max_wh:
            issues.append({
                'type': 'width_height_ratio_high',
                'severity': 'minor',
                'message': f'Width-height ratio too large ({width_height_ratio:.2f} > {max_wh:.2f})',
                'recommendation': 'Reduce beam width or increase height'
            })

        # Check 3: Minimum dimensions
        min_width = self.construction_reqs['min_width']
        min_height = self.construction_reqs['min_height']

        if width < min_width or height < min_height:
            issues.append({
                'type': 'section_too_small',
                'severity': 'severe',
                'message': f'Section dimensions too small for cantilever ({width}m × {height}m)',
                'recommendation': 'Increase section dimensions to meet minimum construction requirements'
            })

        return issues

    def _calculate_utilization_uniformity(self, results: Dict[str, Any]) -> float:
        """Calculate how uniform the stress distribution is"""
        try:
            moments = results.get('results', {}).get('detailed_results', {}).get('moments', [])
            if not moments or len(moments) < 2:
                return 0.7

            avg_moment = sum(moments) / len(moments)
            if avg_moment == 0:
                return 1.0

            variance = sum((m - avg_moment) ** 2 for m in moments) / len(moments)
            std_dev = variance ** 0.5
            cv = std_dev / avg_moment

            uniformity = max(0, min(1, 1 - cv))
            return uniformity
        except:
            return 0.7

    def _evaluate_construction_complexity(self, geometry: Dict[str, Any]) -> str:
        """Evaluate construction complexity based on geometry"""
        length = geometry.get('length', 0)
        height = geometry.get('height', 0)

        # Cantilever is generally more complex than simply supported
        if length > 10 or height > 0.8:
            return "high"
        elif length > 5 or height > 0.5:
            return "medium"
        else:
            return "low"
