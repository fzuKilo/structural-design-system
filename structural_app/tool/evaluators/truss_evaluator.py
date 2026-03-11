"""
Truss evaluator for design quality assessment
Implements 4-dimensional evaluation system for truss structures
"""

from typing import Dict, Any
import numpy as np

try:
    from .base_evaluator import DesignEvaluator
    from .evaluator_config import WEIGHTS_CONFIG, SCORING_CURVES, get_deflection_limit
except ImportError:
    from base_evaluator import DesignEvaluator
    from evaluator_config import WEIGHTS_CONFIG, SCORING_CURVES, get_deflection_limit


class TrussEvaluator(DesignEvaluator):
    """
    Evaluator for truss structures

    Key features:
    - More aggressive scoring curves (higher optimal utilization)
    - Slenderness ratio checks for compression members
    - Economy-focused weighting (30% vs 25% for beams)
    - Lower safety weighting (35% vs 40% for beams) due to redundancy

    Evaluation dimensions:
    1. Safety (35%): Strength + Stiffness + Construction
    2. Economy (30%): Material usage + Cost efficiency
    3. Efficiency (20%): Utilization uniformity
    4. Sustainability (15%): Carbon footprint + Recyclability
    """

    def __init__(self):
        """Initialize truss evaluator"""
        super().__init__()
        self.structure_type = 'truss'

    def _get_weights(self) -> Dict[str, float]:
        """
        Get dimension weights for truss

        Returns:
            Dictionary of dimension weights
        """
        return WEIGHTS_CONFIG.get(self.structure_type, WEIGHTS_CONFIG['beam'])

    def evaluate_economy(self, design: Dict[str, Any], results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate economic efficiency of truss design

        Metrics:
        - Material usage index (volume vs optimal)
        - Cost efficiency ratio
        - Comprehensive utilization (stress + deflection)

        Args:
            design: Design parameters
            results: Analysis results

        Returns:
            Dictionary with score and indicators
        """
        geometry = design.get('geometry', {})
        material = design.get('material', {})
        analysis_results = results.get('results', {})

        # Extract parameters
        span = geometry.get('span', 10.0)
        height = geometry.get('height', 2.0)
        n_panels = geometry.get('n_panels', 5)
        A = material.get('A', 0.01)  # Cross-sectional area (m²)

        # Calculate total material volume
        # Approximate: (top chord + bottom chord + web members) * area
        panel_length = span / n_panels
        diagonal_length = np.sqrt(panel_length**2 + height**2)

        # Member lengths
        top_chord_length = span
        bottom_chord_length = span
        vertical_length = height * (n_panels + 1)
        diagonal_length_total = diagonal_length * n_panels

        total_length = top_chord_length + bottom_chord_length + vertical_length + diagonal_length_total
        volume = total_length * A

        # Reference optimal volume (empirical: span * height * 0.02 for typical truss)
        optimal_volume = span * height * 0.02

        # Material usage index (closer to 1.0 is better)
        material_usage_index = volume / optimal_volume if optimal_volume > 0 else 1.0

        # Score material usage (penalize both over-design and under-design)
        if 0.8 <= material_usage_index <= 1.2:
            material_score = 100
        elif material_usage_index < 0.8:
            # Under-design (risky)
            material_score = max(0, 100 - (0.8 - material_usage_index) * 200)
        else:
            # Over-design (wasteful)
            material_score = max(0, 100 - (material_usage_index - 1.2) * 50)

        # Calculate comprehensive utilization
        stress_utilization = self._get_stress_utilization(design, results)
        deflection_utilization = self._get_deflection_utilization(design, results)
        avg_utilization = (stress_utilization + deflection_utilization) / 2

        # Use truss-specific scoring curve (more aggressive)
        curve = SCORING_CURVES[self.structure_type]['stress']
        utilization_score = curve.calculate_score(avg_utilization, max_score=100)

        # Weighted economy score
        economy_score = utilization_score * 0.6 + material_score * 0.4

        return {
            'score': round(economy_score, 1),
            'grade': self._calculate_grade(economy_score),
            'indicators': {
                'material_usage_index': round(material_usage_index, 3),
                'volume_m3': round(volume, 4),
                'total_length_m': round(total_length, 2),
                'stress_utilization': round(stress_utilization, 4),
                'deflection_utilization': round(deflection_utilization, 4),
                'avg_utilization': round(avg_utilization, 4),
                'utilization_score': round(utilization_score, 1),
                'material_score': round(material_score, 1)
            }
        }

    def evaluate_efficiency(self, design: Dict[str, Any], results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate structural efficiency of truss design

        Metrics:
        - Average utilization (stress + deflection)
        - Utilization uniformity (coefficient of variation)
        - Member efficiency

        Args:
            design: Design parameters
            results: Analysis results

        Returns:
            Dictionary with score and indicators
        """
        analysis_results = results.get('results', {})

        # Get stress utilization
        stress_utilization = self._get_stress_utilization(design, results)

        # Get deflection utilization
        deflection_utilization = self._get_deflection_utilization(design, results)

        # Average utilization
        avg_utilization = (stress_utilization + deflection_utilization) / 2

        # Calculate utilization uniformity
        # For trusses, check stress distribution across members
        stresses = analysis_results.get('stresses', [])
        material = design.get('material', {})
        fy = material.get('fy', 235e6)

        if len(stresses) > 0 and fy > 0:
            member_utilizations = [abs(s) / fy for s in stresses]
            mean_util = np.mean(member_utilizations)
            std_util = np.std(member_utilizations)
            cv = std_util / mean_util if mean_util > 0 else 0

            # Score uniformity (lower CV is better)
            # Excellent: CV < 0.3, Good: CV < 0.5, Acceptable: CV < 0.7
            if cv < 0.3:
                uniformity_score = 100
            elif cv < 0.5:
                uniformity_score = 100 - (cv - 0.3) * 200
            elif cv < 0.7:
                uniformity_score = 60 - (cv - 0.5) * 150
            else:
                uniformity_score = max(0, 30 - (cv - 0.7) * 100)
        else:
            uniformity_score = 50
            cv = 0

        # Use truss-specific scoring curve for average utilization
        curve = SCORING_CURVES[self.structure_type]['stress']
        utilization_score = curve.calculate_score(avg_utilization, max_score=100)

        # Weighted efficiency score
        efficiency_score = utilization_score * 0.6 + uniformity_score * 0.4

        return {
            'score': round(efficiency_score, 1),
            'grade': self._calculate_grade(efficiency_score),
            'indicators': {
                'avg_utilization': round(avg_utilization, 4),
                'stress_utilization': round(stress_utilization, 4),
                'deflection_utilization': round(deflection_utilization, 4),
                'utilization_cv': round(cv, 4),
                'uniformity_score': round(uniformity_score, 1),
                'utilization_score': round(utilization_score, 1)
            }
        }

    def evaluate_safety(self, design: Dict[str, Any], results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate safety of truss design

        Components:
        - Strength safety (20 points): Stress safety factor
        - Stiffness safety (15 points): Deflection safety factor
        - Construction safety (5 points): Slenderness ratio, member sizing

        Args:
            design: Design parameters
            results: Analysis results

        Returns:
            Dictionary with score and indicators
        """
        code_check = results.get('code_check', {})
        safety_factors = code_check.get('safety_factors', {})

        # 1. Strength safety (20 points)
        stress_sf = safety_factors.get('stress', 1.0)
        stress_curve = SCORING_CURVES[self.structure_type]['stress']
        stress_utilization = 1.0 / stress_sf if stress_sf > 0 else 1.0
        strength_score = stress_curve.calculate_score(stress_utilization, max_score=20)

        # 2. Stiffness safety (15 points)
        deflection_sf = safety_factors.get('deflection', 1.0)
        deflection_curve = SCORING_CURVES[self.structure_type]['deflection']
        deflection_utilization = 1.0 / deflection_sf if deflection_sf > 0 else 1.0
        stiffness_score = deflection_curve.calculate_score(deflection_utilization, max_score=15)

        # 3. Construction safety (5 points)
        construction_result = self.evaluate_construction(design, results)
        construction_score = construction_result['score']

        # Total safety score
        safety_score = strength_score + stiffness_score + construction_score

        return {
            'score': round(safety_score, 1),
            'grade': self._calculate_grade(safety_score * 2.5),  # Scale to 100
            'indicators': {
                'stress_safety_factor': round(stress_sf, 2),
                'deflection_safety_factor': round(deflection_sf, 2),
                'slenderness_safety_factor': round(safety_factors.get('slenderness', 1.0), 2),
                'strength_score': round(strength_score, 1),
                'stiffness_score': round(stiffness_score, 1),
                'construction_score': round(construction_score, 1),
                'construction_issues': construction_result.get('issues', [])
            }
        }

    def evaluate_sustainability(self, design: Dict[str, Any], results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate sustainability of truss design

        Metrics:
        - Carbon emission intensity (kg CO2 per m²)
        - Material recyclability
        - Structural efficiency (less material = more sustainable)

        Args:
            design: Design parameters
            results: Analysis results

        Returns:
            Dictionary with score and indicators
        """
        geometry = design.get('geometry', {})
        material = design.get('material', {})

        # Extract parameters
        span = geometry.get('span', 10.0)
        height = geometry.get('height', 2.0)
        n_panels = geometry.get('n_panels', 5)
        A = material.get('A', 0.01)

        # Calculate total material volume
        panel_length = span / n_panels
        diagonal_length = np.sqrt(panel_length**2 + height**2)

        top_chord_length = span
        bottom_chord_length = span
        vertical_length = height * (n_panels + 1)
        diagonal_length_total = diagonal_length * n_panels

        total_length = top_chord_length + bottom_chord_length + vertical_length + diagonal_length_total
        volume = total_length * A

        # Steel density: 7850 kg/m³
        # Steel carbon emission factor: 1.85 kg CO2/kg steel
        steel_density = 7850
        carbon_factor = 1.85

        mass = volume * steel_density
        carbon_emission = mass * carbon_factor

        # Carbon emission intensity (per m² of covered area)
        covered_area = span * 1.0  # Assume 1m width for 2D truss
        carbon_intensity = carbon_emission / covered_area if covered_area > 0 else 0

        # Score carbon intensity
        # Excellent: < 50 kg/m², Good: < 80 kg/m², Acceptable: < 120 kg/m²
        if carbon_intensity < 50:
            carbon_score = 100
        elif carbon_intensity < 80:
            carbon_score = 100 - (carbon_intensity - 50) * 1.0
        elif carbon_intensity < 120:
            carbon_score = 70 - (carbon_intensity - 80) * 1.0
        else:
            carbon_score = max(0, 30 - (carbon_intensity - 120) * 0.5)

        # Recyclability score (steel is highly recyclable)
        recyclability_score = 95  # Steel: 95% recyclable

        # Weighted sustainability score
        sustainability_score = carbon_score * 0.6 + recyclability_score * 0.4

        return {
            'score': round(sustainability_score, 1),
            'grade': self._calculate_grade(sustainability_score),
            'indicators': {
                'carbon_emission_kg': round(carbon_emission, 2),
                'carbon_intensity_kg_per_m2': round(carbon_intensity, 2),
                'mass_kg': round(mass, 2),
                'recyclability_percent': recyclability_score,
                'carbon_score': round(carbon_score, 1)
            }
        }

    def _check_structure_specific_construction(self, design: Dict[str, Any], results: Dict[str, Any]) -> list:
        """
        Check truss-specific construction requirements

        Checks:
        1. Slenderness ratio (λ ≤ 150 for compression, λ ≤ 350 for tension)
        2. Height-to-span ratio (typically 1/6 to 1/10)
        3. Panel aspect ratio (typically 1:1 to 2:1)
        4. Minimum member size

        Args:
            design: Design parameters
            results: Analysis results

        Returns:
            List of construction issues
        """
        issues = []
        geometry = design.get('geometry', {})
        material = design.get('material', {})
        code_check = results.get('code_check', {})

        span = geometry.get('span', 10.0)
        height = geometry.get('height', 2.0)
        n_panels = geometry.get('n_panels', 5)
        A = material.get('A', 0.01)

        # 1. Check slenderness ratio (from code_check)
        checks = code_check.get('checks', {})
        max_slenderness = checks.get('max_slenderness', 0)

        if max_slenderness > 150:
            issues.append({
                'type': 'slenderness_high',
                'severity': 'severe',
                'message': f'Slenderness ratio too high: λ={max_slenderness:.1f} > 150',
                'recommendation': 'Increase member cross-sectional area or reduce member length'
            })
        elif max_slenderness > 120:
            issues.append({
                'type': 'slenderness_moderate',
                'severity': 'moderate',
                'message': f'Slenderness ratio moderately high: λ={max_slenderness:.1f} > 120',
                'recommendation': 'Consider increasing member size for better stability'
            })

        # 2. Check height-to-span ratio (1/6 to 1/10 is typical)
        height_span_ratio = height / span if span > 0 else 0

        if height_span_ratio < 0.08:  # Less than 1/12.5
            issues.append({
                'type': 'height_span_ratio_low',
                'severity': 'moderate',
                'message': f'Height-to-span ratio too low: {height_span_ratio:.3f} < 1/12',
                'recommendation': 'Increase truss height for better structural efficiency'
            })
        elif height_span_ratio > 0.20:  # Greater than 1/5
            issues.append({
                'type': 'height_span_ratio_high',
                'severity': 'minor',
                'message': f'Height-to-span ratio too high: {height_span_ratio:.3f} > 1/5',
                'recommendation': 'Consider reducing truss height to improve economy'
            })

        # 3. Check panel aspect ratio
        panel_length = span / n_panels if n_panels > 0 else span
        panel_aspect = panel_length / height if height > 0 else 1.0

        if panel_aspect < 0.5:  # Too narrow
            issues.append({
                'type': 'panel_aspect_low',
                'severity': 'minor',
                'message': f'Panel aspect ratio too low: {panel_aspect:.2f} < 0.5',
                'recommendation': 'Reduce number of panels or increase truss height'
            })
        elif panel_aspect > 2.5:  # Too wide
            issues.append({
                'type': 'panel_aspect_high',
                'severity': 'moderate',
                'message': f'Panel aspect ratio too high: {panel_aspect:.2f} > 2.5',
                'recommendation': 'Increase number of panels or reduce truss height'
            })

        # 4. Check minimum member size
        # Assume circular section: diameter = sqrt(4*A/π)
        diameter = np.sqrt(4 * A / np.pi) * 1000  # Convert to mm

        if diameter < 20:  # Less than 20mm
            issues.append({
                'type': 'member_size_small',
                'severity': 'severe',
                'message': f'Member size too small: Ø={diameter:.1f}mm < 20mm',
                'recommendation': 'Increase member cross-sectional area'
            })
        elif diameter < 30:  # Less than 30mm
            issues.append({
                'type': 'member_size_moderate',
                'severity': 'minor',
                'message': f'Member size relatively small: Ø={diameter:.1f}mm < 30mm',
                'recommendation': 'Consider increasing member size for better durability'
            })

        return issues

    def _get_deflection_limit(self, design: Dict[str, Any]) -> float:
        """
        Get deflection limit for truss

        Args:
            design: Design parameters

        Returns:
            Deflection limit in meters
        """
        geometry = design.get('geometry', {})
        span = geometry.get('span', 10.0)
        return get_deflection_limit(self.structure_type, span)

    def _get_stress_utilization(self, design: Dict[str, Any], results: Dict[str, Any]) -> float:
        """
        Calculate stress utilization ratio for truss

        Args:
            design: Design parameters
            results: Analysis results

        Returns:
            Stress utilization ratio (0.0 to 1.0+)
        """
        analysis_results = results.get('results', {})
        material = design.get('material', {})

        max_stress = analysis_results.get('max_stress', 0.0)
        fy = material.get('fy', 235e6)

        return max_stress / fy if fy > 0 else 0.0
