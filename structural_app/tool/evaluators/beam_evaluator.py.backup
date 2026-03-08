"""
Beam evaluator for structural design assessment
Implements 4-dimensional evaluation for beam structures
"""

from typing import Dict, Any
from .base_evaluator import DesignEvaluator


class BeamEvaluator(DesignEvaluator):
    """
    Concrete evaluator for beam structures

    Implements 4-dimensional evaluation:
    - Economy: Material usage, cost efficiency
    - Structural Efficiency: Stress utilization, redundancy
    - Safety: Safety factors, deflection margins
    - Sustainability: Carbon emissions, recyclability
    """

    def __init__(self):
        """Initialize beam evaluator"""
        super().__init__()

    def _get_structure_type(self) -> str:
        """Return structure type identifier"""
        return "beam"

    def evaluate_economy(self, design: Dict[str, Any], results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate economic aspects of beam design

        Args:
            design: Design parameters
            results: Analysis results

        Returns:
            Dictionary with score and economic indicators
        """
        # Calculate material volume
        geometry = design.get('geometry', {})
        length = geometry.get('length', 1.0)  # meters
        width = geometry.get('width', 0.3)    # meters
        height = geometry.get('height', 0.5)  # meters
        volume = length * width * height      # m^3

        # Material usage index: ratio to theoretical minimum
        # Theoretical minimum for a beam: L * 0.2 * 0.4 = 0.08 m^3 for 6m span
        theoretical_min = length * 0.2 * 0.4
        material_usage_index = volume / theoretical_min if theoretical_min > 0 else 1.0

        # Cost efficiency: based on material usage and stress utilization
        stress_utilization = self._get_stress_utilization(design, results)

        # Score calculation:
        # - Low material usage is good (< 1.2 is excellent, 1.5 is acceptable)
        # - High stress utilization is good (0.6-0.8 is optimal)
        material_score = max(0, 100 - (material_usage_index - 1) * 50)
        efficiency_score = self._calculate_utilization_score(stress_utilization)

        economy_score = material_score * 0.6 + efficiency_score * 0.4

        return {
            'score': round(economy_score, 1),
            'indicators': {
                'material_usage_index': round(material_usage_index, 3),
                'volume_m3': round(volume, 4),
                'cost_efficiency_ratio': round(stress_utilization / 0.7 if stress_utilization > 0 else 0, 2),
                'construction_complexity': self._evaluate_construction_complexity(geometry)
            }
        }

    def evaluate_efficiency(self, design: Dict[str, Any], results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate structural efficiency of beam design

        Args:
            design: Design parameters
            results: Analysis results

        Returns:
            Dictionary with score and efficiency indicators
        """
        # Get stress utilization
        stress_utilization = self._get_stress_utilization(design, results)

        # Calculate utilization uniformity
        utilization_uniformity = self._calculate_utilization_uniformity(results)

        # Check redundancy (number of elements - simple proxy)
        geometry = design.get('geometry', {})
        n_elements = geometry.get('n_elements', 20)
        redundancy_index = min(1.5, n_elements / 20)  # More elements = more redundancy

        # Score calculation
        utilization_score = self._calculate_utilization_score(stress_utilization)

        # Uniformity score: more uniform = better (less local stress concentrations)
        uniformity_score = utilization_uniformity * 100

        # Redundancy score: some redundancy is good for safety
        redundancy_score = min(100, redundancy_index * 50)

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

    def evaluate_safety(self, design: Dict[str, Any], results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate safety aspects of beam design

        Args:
            design: Design parameters
            results: Analysis results

        Returns:
            Dictionary with score and safety indicators
        """
        code_check = results.get('code_check', {})
        safety_factors = code_check.get('safety_factors', {})

        # Get minimum safety factor
        min_safety_factor = min(safety_factors.values()) if safety_factors else 0

        # Check deflection margin
        max_displacement = results.get('results', {}).get('max_displacement', 0)
        geometry = design.get('geometry', {})
        length = geometry.get('length', 1.0)
        deflection_limit = length / 250  # Standard deflection limit
        deflection_margin = deflection_limit / max_displacement if max_displacement > 0 else float('inf')

        # Score calculation
        # Safety factor scoring: > 2.0 is excellent, 1.5 is minimum acceptable
        sf_score = min(100, max(0, min_safety_factor * 50))

        # Deflection margin scoring: > 1.5 is good
        deflection_score = min(100, max(0, 150 - deflection_margin * 50))

        # Code compliance score
        compliant = code_check.get('compliant', False)
        compliance_score = 100 if compliant else 40

        safety_score = (
            sf_score * 0.4 +
            deflection_score * 0.3 +
            compliance_score * 0.3
        )

        return {
            'score': round(safety_score, 1),
            'indicators': {
                'min_safety_factor': round(min_safety_factor, 2),
                'safety_factor_distribution': self._evaluate_sf_distribution(safety_factors),
                'deflection_margin': round(min(deflection_margin, 3.0), 2)
            }
        }

    def evaluate_sustainability(self, design: Dict[str, Any], results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate sustainability aspects of beam design

        Args:
            design: Design parameters
            results: Analysis results

        Returns:
            Dictionary with score and sustainability indicators
        """
        # Calculate carbon emissions (approximate)
        # Concrete: ~2400 kg/m^3, ~0.11 kg CO2/kg
        # Steel: ~7850 kg/m^3, ~1.8 kg CO2/kg
        geometry = design.get('geometry', {})
        volume = geometry.get('length', 1.0) * geometry.get('width', 0.3) * geometry.get('height', 0.5)

        # Assume concrete (conservative estimate)
        carbon_emission = volume * 2400 * 0.11  # kg CO2

        # Recyclability ratio (concrete = 0, steel = 0.9+)
        material = design.get('material', {})
        material_name = material.get('material_name', 'concrete').lower()
        recyclability = 0.9 if 'steel' in material_name or 'q' in material_name else 0.15

        # Score calculation
        # Lower carbon = better
        carbon_score = max(0, 100 - carbon_emission / 5)

        # Recyclability score
        recyclability_score = recyclability * 100

        sustainability_score = (carbon_score + recyclability_score) / 2

        return {
            'score': round(sustainability_score, 1),
            'indicators': {
                'carbon_emission_kg': round(carbon_emission, 1),
                'recyclability_ratio': round(recyclability, 2)
            }
        }

    # Helper methods

    def _get_stress_utilization(self, design: Dict[str, Any], results: Dict[str, Any]) -> float:
        """Calculate stress utilization ratio"""
        try:
            max_stress = results.get('results', {}).get('max_stress_MPa', 0)
            if max_stress <= 0:
                return 0.5  # Default if no results

            material = design.get('material', {})
            fy = material.get('fy', 235e6)  # Default: Q235 steel
            fy_MPa = fy / 1e6

            allowable_stress = fy_MPa / 1.5  # Allowable stress design
            utilization = max_stress / allowable_stress

            return min(1.0, max(0.0, utilization))
        except:
            return 0.5

    def _calculate_utilization_score(self, utilization: float) -> float:
        """Calculate score based on stress utilization (optimal: 0.6-0.8)"""
        if utilization <= 0:
            return 50

        # Optimal range: 0.6-0.8
        if 0.6 <= utilization <= 0.8:
            return 100

        # Below optimal (under-designed)
        if utilization < 0.6:
            return 100 - (0.6 - utilization) * 100

        # Above optimal (over-designed)
        if utilization <= 1.0:
            return 100 - (utilization - 0.8) * 200

        # Way over (100+ score clamped)
        return max(0, 100 - (utilization - 0.8) * 200)

    def _calculate_utilization_uniformity(self, results: Dict[str, Any]) -> float:
        """Calculate how uniform the stress distribution is"""
        try:
            moments = results.get('results', {}).get('detailed_results', {}).get('moments', [])
            if not moments or len(moments) < 2:
                return 0.7  # Default for insufficient data

            avg_moment = sum(moments) / len(moments)
            if avg_moment == 0:
                return 1.0

            # Calculate coefficient of variation
            variance = sum((m - avg_moment) ** 2 for m in moments) / len(moments)
            std_dev = variance ** 0.5
            cv = std_dev / avg_moment

            # Lower CV = more uniform = better
            # CV < 0.3 is excellent, CV > 1.0 is poor
            uniformity = max(0, min(1, 1 - cv))
            return uniformity
        except:
            return 0.7

    def _evaluate_construction_complexity(self, geometry: Dict[str, Any]) -> str:
        """Evaluate construction complexity based on geometry"""
        length = geometry.get('length', 0)
        height = geometry.get('height', 0)

        # Simple heuristic
        if length > 15 or height > 1.0:
            return "high"
        elif length > 8 or height > 0.7:
            return "medium"
        else:
            return "low"

    def _evaluate_sf_distribution(self, safety_factors: Dict[str, float]) -> str:
        """Evaluate safety factor distribution"""
        if not safety_factors:
            return "unknown"

        values = list(safety_factors.values())
        min_sf = min(values)
        max_sf = max(values)

        ratio = max_sf / min_sf if min_sf > 0 else 1

        if ratio > 2:
            return "uneven"
        elif ratio > 1.5:
            return "moderate"
        else:
            return "uniform"
