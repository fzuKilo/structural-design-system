"""
Truss evaluator for design quality assessment
Implements 4-dimensional evaluation system for truss structures
"""

from typing import Dict, Any
import numpy as np

try:
    from .base_evaluator import DesignEvaluator
    from .evaluator_config import WEIGHTS_CONFIG, SCORING_CURVES, get_deflection_limit
    from .rag_enhanced_mixin import RAGEnhancedEvaluatorMixin
except ImportError:
    from base_evaluator import DesignEvaluator
    from evaluator_config import WEIGHTS_CONFIG, SCORING_CURVES, get_deflection_limit
    from rag_enhanced_mixin import RAGEnhancedEvaluatorMixin


class TrussEvaluator(DesignEvaluator, RAGEnhancedEvaluatorMixin):
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

        # Calculate total material volume (member length × area)
        panel_length = span / n_panels
        diagonal_length = np.sqrt(panel_length**2 + height**2)
        total_length = span + span + height * (n_panels + 1) + diagonal_length * n_panels
        volume = total_length * A

        # Theoretical minimum volume based on min height-span ratio (truss: 1/10)
        h_min = max(0.3, span / 10)
        v_min = span * 0.2 * h_min
        material_usage_index = volume / v_min if v_min > 0 else 1.0

        # Calculate comprehensive utilization
        stress_utilization = self._get_stress_utilization(design, results)
        deflection_utilization = self._get_deflection_utilization(design, results)
        avg_utilization = (stress_utilization + deflection_utilization) / 2

        # Use truss-specific scoring curve
        curve = SCORING_CURVES[self.structure_type]['stress']
        utilization_score = curve.calculate_score(avg_utilization, max_score=100)

        # Material usage score (slope=30 per DES v2.0)
        material_score = max(0, 100 - (material_usage_index - 1) * 30)

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
        deflection_utilization = self._get_deflection_utilization(design, results)
        avg_utilization = (stress_utilization + deflection_utilization) / 2

        # Calculate utilization uniformity using element stresses (u_i = σ_i / allowable)
        stresses = analysis_results.get('stresses', [])
        material = design.get('material', {})
        fy = material.get('fy', 235e6)
        fy_Pa = fy if fy > 1000 else fy * 1e6
        allowable = fy_Pa / 1.5

        if len(stresses) > 0 and allowable > 0:
            member_utilizations = [abs(s) / allowable for s in stresses]
            mean_util = np.mean(member_utilizations)
            std_util = np.std(member_utilizations)
            cv = std_util / mean_util if mean_util > 0 else 0
            uniformity_score = max(0.0, min(100.0, (1 - cv) * 100))
        else:
            uniformity_score = 50.0
            cv = 0

        # Use truss-specific scoring curve for average utilization
        curve = SCORING_CURVES[self.structure_type]['stress']
        utilization_score = curve.calculate_score(avg_utilization, max_score=100)

        # Weighted efficiency score (50% + 50%, per DES v2.0)
        efficiency_score = utilization_score * 0.5 + uniformity_score * 0.5

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
        # 1. Strength safety: score = max(0, 100 - 40*x), per DES v2.0
        stress_utilization = self._get_stress_utilization(design, results)
        if stress_utilization > 1.0:
            strength_score = 0.0
        else:
            strength_score = max(0.0, 100 - 40 * stress_utilization)

        # 2. Stiffness safety: score = max(0, 100 - 40*x), per DES v2.0
        deflection_utilization = self._get_deflection_utilization(design, results)
        if deflection_utilization > 1.0:
            stiffness_score = 0.0
        else:
            stiffness_score = max(0.0, 100 - 40 * deflection_utilization)

        # 3. Construction safety
        construction_result = self.evaluate_construction(design, results)
        construction_score = construction_result['score'] * 20  # scale 0-5 to 0-100

        # Weighted safety score (50% strength + 37.5% stiffness + 12.5% construction)
        safety_score = (
            strength_score * 0.50 +
            stiffness_score * 0.375 +
            construction_score * 0.125
        )

        return {
            'score': round(safety_score, 1),
            'indicators': {
                'strength_score': round(strength_score, 1),
                'stiffness_score': round(stiffness_score, 1),
                'construction_score': round(construction_score, 1),
                'stress_utilization': round(stress_utilization, 4),
                'deflection_utilization': round(deflection_utilization, 4),
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
        span = geometry.get('span', 10.0)
        height = geometry.get('height', 2.0)
        n_panels = geometry.get('n_panels', 5)
        A = material.get('A', 0.01)

        # Calculate total material volume
        panel_length = span / n_panels
        diagonal_length = np.sqrt(panel_length**2 + height**2)
        total_length = span + span + height * (n_panels + 1) + diagonal_length * n_panels
        volume = total_length * A

        # Steel properties
        steel_density = 7850.0
        carbon_factor = 1.85
        recyclability = 0.90

        mass = volume * steel_density
        total_carbon = mass * carbon_factor

        # Bearing capacity: N_u = Σ(fy_i * A_i) for tension members
        # Use actual axial forces from analysis to identify tension members
        fy = material.get('fy', 235e6)
        fy_Pa = fy if fy > 1000 else fy * 1e6
        fy_kN_m2 = fy_Pa / 1e3  # Pa → kN/m²
        A_m2 = A  # m²

        # Try to get actual axial forces from analysis results
        detailed_results = results.get('results', {}).get('detailed_results', {})
        axial_forces = detailed_results.get('extra', {}).get('axial_forces', [])

        if axial_forces:
            # Count actual tension members (positive axial force)
            n_tension = sum(1 for f in axial_forces if f > 0)
            N_u = max(fy_kN_m2 * A_m2 * n_tension, 1.0)  # Precise calculation, kN
        else:
            # Fallback: approximate as half members in tension
            n_members = int(2 * n_panels + (n_panels + 1) + n_panels)  # top+bottom+vertical+diagonal
            N_u = max(fy_kN_m2 * A_m2 * n_members / 2, 1.0)  # Approximate, kN

        # Carbon intensity score (k=15 for truss, per DES v2.0)
        carbon_intensity = total_carbon / N_u  # kg CO2 / kN
        carbon_score = max(0.0, 100 - carbon_intensity * 15)

        recyclability_score = recyclability * 100
        sustainability_score = (carbon_score + recyclability_score) / 2

        return {
            'score': round(sustainability_score, 1),
            'indicators': {
                'carbon_emission_kg': round(total_carbon, 2),
                'carbon_intensity': round(carbon_intensity, 4),
                'N_u_kN': round(N_u, 1),
                'mass_kg': round(mass, 2),
                'recyclability_ratio': round(recyclability, 2)
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

        # 1. Check slenderness ratio (λ ≤ 150 for compression, λ ≤ 250 for tension per GB 50017)
        checks = code_check.get('checks', {})
        max_slenderness = checks.get('max_slenderness', 0)

        # Try to get axial forces and member lengths for precise check
        detailed_results = results.get('results', {}).get('detailed_results', {})
        axial_forces = detailed_results.get('extra', {}).get('axial_forces', [])
        member_lengths = detailed_results.get('extra', {}).get('member_lengths', [])

        if axial_forces and member_lengths and A > 0:
            # Calculate radius of gyration (simplified: assume circular or square section)
            r = np.sqrt(A / np.pi)  # For circular section: r = sqrt(A/π)

            # Check each member individually
            compression_violations = []
            tension_violations = []

            for i, (force, length) in enumerate(zip(axial_forces, member_lengths)):
                slenderness = length / r if r > 0 else 0

                if force < 0:  # Compression member
                    if slenderness > 150:
                        compression_violations.append((i, slenderness))
                else:  # Tension member
                    if slenderness > 250:
                        tension_violations.append((i, slenderness))

            # Report violations
            if compression_violations:
                max_comp_slenderness = max(s for _, s in compression_violations)
                issues.append({
                    'type': 'compression_slenderness_high',
                    'severity': 'severe',
                    'message': f'Compression member slenderness too high: λ={max_comp_slenderness:.1f} > 150 (GB 50017)',
                    'recommendation': 'Increase cross-sectional area or reduce member length for compression members'
                })

            if tension_violations:
                max_tens_slenderness = max(s for _, s in tension_violations)
                issues.append({
                    'type': 'tension_slenderness_high',
                    'severity': 'moderate',
                    'message': f'Tension member slenderness too high: λ={max_tens_slenderness:.1f} > 250 (GB 50017)',
                    'recommendation': 'Consider increasing cross-sectional area for tension members to reduce vibration'
                })
        else:
            # Fallback: use overall max_slenderness (conservative, assume compression)
            if max_slenderness > 150:
                issues.append({
                    'type': 'slenderness_high',
                    'severity': 'severe',
                    'message': f'Slenderness ratio too high: λ={max_slenderness:.1f} > 150 (compression limit)',
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
        fy_Pa = fy if fy > 1000 else fy * 1e6
        allowable = fy_Pa / 1.5  # per DES v2.0

        return max_stress / allowable if allowable > 0 else 0.0
