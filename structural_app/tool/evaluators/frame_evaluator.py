"""
Frame evaluator for structural design assessment
Implements frame-specific evaluation with strong column weak beam checks
"""

from typing import Dict, Any, List

try:
    from .base_evaluator import DesignEvaluator
    from .evaluator_config import get_scoring_curves, get_construction_requirements
except ImportError:
    from base_evaluator import DesignEvaluator
    from evaluator_config import get_scoring_curves, get_construction_requirements


class FrameEvaluator(DesignEvaluator):
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

        # Calculate volumes
        total_column_length = sum(story_heights) * (num_bays + 1)
        total_beam_length = sum(bay_widths) * num_stories

        column_volume = total_column_length * col_width * col_depth
        beam_volume = total_beam_length * beam_width * beam_depth
        total_volume = column_volume + beam_volume

        # Material usage index (compared to theoretical minimum)
        theoretical_min = total_column_length * 0.3 * 0.3 + total_beam_length * 0.25 * 0.5
        material_usage_index = total_volume / theoretical_min if theoretical_min > 0 else 1.0

        # Comprehensive utilization (stress + deflection + drift) / 3
        comprehensive_util = self._get_comprehensive_utilization(design, results)

        # Use multi-level scoring curve for utilization
        utilization_score = self.scoring_curves['stress'].calculate_score(comprehensive_util)

        # Material usage score (linear: lower is better)
        material_score = max(0, 100 - (material_usage_index - 1) * 50)

        # Weighted economy score
        economy_score = utilization_score * 0.6 + material_score * 0.4

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

        # Use multi-level scoring curve
        utilization_score = self.scoring_curves['stress'].calculate_score(stress_utilization)

        # Calculate utilization uniformity
        utilization_uniformity = self._calculate_utilization_uniformity(results)
        uniformity_score = utilization_uniformity * 100

        # Redundancy index (frames have high redundancy)
        geometry = design.get('geometry', {})
        num_bays = geometry.get('num_bays', 1)
        num_stories = geometry.get('num_stories', 1)
        redundancy_index = min(2.0, (num_bays + num_stories) / 4)
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
        # 1. Strength evaluation (inverted logic: lower utilization = higher safety)
        stress_util = self._get_stress_utilization(design, results)
        strength_score = max(0, 100 - stress_util * 100)

        # 2. Stiffness evaluation (deflection + drift)
        deflection_util = self._get_deflection_utilization(design, results)
        drift_util = self._get_drift_utilization(design, results)
        stiffness_util = (deflection_util + drift_util) / 2
        stiffness_score = max(0, 100 - stiffness_util * 100)

        # 3. Construction evaluation (frame-specific checks)
        construction_eval = self.evaluate_construction(design, results)
        construction_score = construction_eval['score'] * 20  # Scale 0-5 to 0-100

        # Weighted safety score (45% total weight)
        safety_score = (
            strength_score * 0.444 +
            stiffness_score * 0.333 +
            construction_score * 0.222
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

        # Concrete: ~2400 kg/m^3, ~0.11 kg CO2/kg
        carbon_emission = total_volume * 2400 * 0.11

        # Recyclability
        material = design.get('material', {})
        material_name = material.get('material_name', 'concrete').lower()
        recyclability = 0.9 if 'steel' in material_name or 'q' in material_name else 0.15

        # Scoring
        carbon_score = max(0, 100 - carbon_emission / 50)
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
                'message': f'Column section may not satisfy strong column weak beam requirement',
                'recommendation': 'Increase column section or reduce beam section'
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
                    'message': f'Column axial ratio too high ({axial_ratio:.2f} > 0.9)',
                    'recommendation': 'Increase column section'
                })
            elif axial_ratio > 0.75:
                issues.append({
                    'type': 'moderate_axial_ratio',
                    'severity': 'moderate',
                    'message': f'Column axial ratio moderate ({axial_ratio:.2f} > 0.75)',
                    'recommendation': 'Consider increasing column section for better safety margin'
                })

        # Check 3: Story drift ratio
        max_drift_ratio = results.get('results', {}).get('max_drift_ratio', 0)
        limit = 1.0 / 500

        if max_drift_ratio > limit:
            issues.append({
                'type': 'excessive_drift',
                'severity': 'severe',
                'message': f'Story drift ratio exceeds limit ({max_drift_ratio:.6f} > {limit:.6f})',
                'recommendation': 'Increase column/beam stiffness or reduce lateral loads'
            })
        elif max_drift_ratio > limit * 0.8:
            issues.append({
                'type': 'high_drift',
                'severity': 'moderate',
                'message': f'Story drift ratio approaching limit ({max_drift_ratio:.6f} > {limit*0.8:.6f})',
                'recommendation': 'Consider increasing stiffness for better serviceability'
            })

        # Check 4: Beam-column section compatibility
        if beam_depth > col_depth * 0.8:
            issues.append({
                'type': 'beam_column_incompatible',
                'severity': 'minor',
                'message': f'Beam depth ({beam_depth}m) too close to column depth ({col_depth}m)',
                'recommendation': 'Ensure proper connection detailing'
            })

        return issues

    def _calculate_utilization_uniformity(self, results: Dict[str, Any]) -> float:
        """Calculate how uniform the stress distribution is"""
        try:
            detailed_results = results.get('results', {}).get('detailed_results', {})
            moments = detailed_results.get('moments', [])

            if not moments or len(moments) < 2:
                return 0.7

            # Extract moment values
            moment_values = []
            for m in moments:
                moment_values.append(abs(m.get('M_i', 0)))
                moment_values.append(abs(m.get('M_j', 0)))

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
        except:
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

