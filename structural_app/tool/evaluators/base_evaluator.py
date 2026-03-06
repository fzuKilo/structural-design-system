"""
Base evaluator for structural design evaluation
Defines the abstract interface for all structure type evaluators
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List

try:
    from .evaluator_config import get_weights, get_scoring_curves, get_deflection_limit
except ImportError:
    from evaluator_config import get_weights, get_scoring_curves, get_deflection_limit


class DesignEvaluator(ABC):
    """
    Abstract base class for design evaluators

    All concrete evaluators (BeamEvaluator, FrameEvaluator, etc.) must inherit
    from this class and implement the abstract methods.

    Evaluation Dimensions:
    - Economy: Material usage, cost efficiency, construction complexity
    - Structural Efficiency: Stress utilization, redundancy, efficiency index
    - Safety: Safety factors, margin, reliability
    - Sustainability: Carbon emissions, recyclability, environmental impact
    """

    def __init__(self):
        """Initialize the evaluator"""
        self.structure_type = self._get_structure_type()

    def _get_structure_type(self) -> str:
        """
        Return the structure type identifier

        Returns:
            Structure type string (e.g., "beam", "frame", "truss")
        """
        return self.__class__.__name__.replace('Evaluator', '').lower()

    @abstractmethod
    def evaluate_economy(self, design: Dict[str, Any], results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate economic aspects of the design

        Args:
            design: Design parameters
            results: Analysis results

        Returns:
            Dictionary containing:
                - score: Score (0-100)
                - indicators: Dictionary of economic indicators
        """
        pass

    @abstractmethod
    def evaluate_efficiency(self, design: Dict[str, Any], results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate structural efficiency

        Args:
            design: Design parameters
            results: Analysis results

        Returns:
            Dictionary containing:
                - score: Score (0-100)
                - indicators: Dictionary of efficiency indicators
        """
        pass

    @abstractmethod
    def evaluate_safety(self, design: Dict[str, Any], results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate safety aspects

        Args:
            design: Design parameters
            results: Analysis results

        Returns:
            Dictionary containing:
                - score: Score (0-100)
                - indicators: Dictionary of safety indicators
        """
        pass

    @abstractmethod
    def evaluate_sustainability(self, design: Dict[str, Any], results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate sustainability aspects

        Args:
            design: Design parameters
            results: Analysis results

        Returns:
            Dictionary containing:
                - score: Score (0-100)
                - indicators: Dictionary of sustainability indicators
        """
        pass

    def evaluate_comprehensive(self, design: Dict[str, Any], results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform comprehensive evaluation with weighted scoring

        Args:
            design: Design parameters
            results: Analysis results

        Returns:
            Dictionary containing:
                - status: "success" or "error"
                - comprehensive_score: Weighted score (0-100)
                - grade: Letter grade (A+/A/B+/B/C+/C/D)
                - dimensions: Dictionary of all dimension scores
                - recommendations: List of improvement suggestions
        """
        try:
            # Evaluate each dimension
            economy = self.evaluate_economy(design, results)
            efficiency = self.evaluate_efficiency(design, results)
            safety = self.evaluate_safety(design, results)
            sustainability = self.evaluate_sustainability(design, results)

            # Weighted scoring (structure-specific weights from config)
            weights = get_weights(self.structure_type)

            # Calculate comprehensive score
            comprehensive_score = (
                economy['score'] * weights['economy'] +
                efficiency['score'] * weights['efficiency'] +
                safety['score'] * weights['safety'] +
                sustainability['score'] * weights['sustainability']
            )

            # Convert to letter grade
            grade = self._calculate_grade(comprehensive_score)

            # Generate recommendations if score < 75
            recommendations = []
            if comprehensive_score < 75:
                recommendations = self._generate_recommendations(
                    economy, efficiency, safety, sustainability
                )

            return {
                'status': 'success',
                'comprehensive_score': round(comprehensive_score, 1),
                'grade': grade,
                'dimensions': {
                    'economy': economy,
                    'structural_efficiency': efficiency,
                    'safety': safety,
                    'sustainability': sustainability
                },
                'recommendations': recommendations
            }

        except Exception as e:
            return {
                'status': 'error',
                'error': f"Evaluation error: {str(e)}",
                'comprehensive_score': 0,
                'grade': 'D'
            }

    def _calculate_grade(self, score: float) -> str:
        """
        Convert comprehensive score to letter grade

        Scoring Scale:
        - A+: >= 95
        - A: 90-94
        - B+: 85-89
        - B: 80-84
        - C+: 75-79
        - C: 70-74
        - D: < 70

        Args:
            score: Comprehensive score (0-100)

        Returns:
            Letter grade
        """
        if score >= 95:
            return 'A+'
        elif score >= 90:
            return 'A'
        elif score >= 85:
            return 'B+'
        elif score >= 80:
            return 'B'
        elif score >= 75:
            return 'C+'
        elif score >= 70:
            return 'C'
        else:
            return 'D'

    def _generate_recommendations(
        self,
        economy: Dict[str, Any],
        efficiency: Dict[str, Any],
        safety: Dict[str, Any],
        sustainability: Dict[str, Any]
    ) -> List[str]:
        """
        Generate improvement recommendations based on low scores

        Args:
            economy: Economy evaluation results
            efficiency: Efficiency evaluation results
            safety: Safety evaluation results
            sustainability: Sustainability evaluation results

        Returns:
            List of recommendation strings
        """
        recommendations = []

        # Economy recommendations
        if economy['score'] < 70:
            indicators = economy.get('indicators', {})
            if 'material_usage_index' in indicators:
                usage = indicators['material_usage_index']
                recommendations.append(
                    f"Material usage is high (index: {usage:.2f}). "
                    f"Consider optimizing the design to reduce material consumption."
                )

        # Efficiency recommendations
        if efficiency['score'] < 70:
            indicators = efficiency.get('indicators', {})
            if 'average_utilization' in indicators:
                util = indicators['average_utilization']
                if util < 0.5:
                    recommendations.append(
                        f"Structural utilization is low ({util:.2%}). "
                        f"The design may be over-conservative; consider reducing section sizes."
                    )
                elif util > 0.9:
                    recommendations.append(
                        f"Structural utilization is high ({util:.2%}). "
                        f"Consider adding redundancy or safety margins."
                    )

        # Safety recommendations
        if safety['score'] < 70:
            indicators = safety.get('indicators', {})
            if 'min_safety_factor' in indicators:
                sf = indicators['min_safety_factor']
                if sf < 1.5:
                    recommendations.append(
                        f"Safety factor is critical ({sf:.2f}). "
                        f"Consider increasing section sizes or using stronger materials."
                    )

        # Sustainability recommendations
        if sustainability['score'] < 70:
            indicators = sustainability.get('indicators', {})
            if 'carbon_emission_kg' in indicators:
                emissions = indicators['carbon_emission_kg']
                recommendations.append(
                    f"Carbon emissions are high ({emissions:.0f} kg). "
                    f"Consider using more sustainable materials or optimizing the design."
                )

        return recommendations

    # ========================================================================
    # New Helper Methods for Improved Scoring System
    # ========================================================================

    def _get_deflection_utilization(self, design: Dict[str, Any], results: Dict[str, Any]) -> float:
        """
        Calculate deflection utilization ratio

        Args:
            design: Design parameters
            results: Analysis results

        Returns:
            Deflection utilization ratio (0.0 to 1.0+)
        """
        try:
            max_displacement = results.get('results', {}).get('max_displacement', 0)
            geometry = design.get('geometry', {})
            length = geometry.get('length', 1.0)

            # Get structure-specific deflection limit
            deflection_limit = get_deflection_limit(self.structure_type, length)

            if deflection_limit <= 0:
                return 0.5  # Default value

            utilization = max_displacement / deflection_limit
            return min(1.0, max(0.0, utilization))
        except:
            return 0.5

    def _get_comprehensive_utilization(self, design: Dict[str, Any], results: Dict[str, Any]) -> float:
        """
        Calculate comprehensive utilization (average of stress and deflection utilization)

        This is a key indicator for economy evaluation (ref: DQS)

        Args:
            design: Design parameters
            results: Analysis results

        Returns:
            Comprehensive utilization ratio (0.0 to 1.0+)
        """
        stress_util = self._get_stress_utilization(design, results)
        deflection_util = self._get_deflection_utilization(design, results)

        return (stress_util + deflection_util) / 2

    @abstractmethod
    def _get_stress_utilization(self, design: Dict[str, Any], results: Dict[str, Any]) -> float:
        """
        Calculate stress utilization ratio (must be implemented by subclasses)

        Args:
            design: Design parameters
            results: Analysis results

        Returns:
            Stress utilization ratio (0.0 to 1.0+)
        """
        pass

    @abstractmethod
    def _check_structure_specific_construction(
        self, design: Dict[str, Any], results: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Check structure-specific construction requirements (must be implemented by subclasses)

        Args:
            design: Design parameters
            results: Analysis results

        Returns:
            List of construction issues, each containing:
                - type: Issue type identifier
                - severity: 'minor', 'moderate', or 'severe'
                - message: Human-readable description
                - recommendation: Suggested fix
        """
        pass

    def evaluate_construction(self, design: Dict[str, Any], results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate construction aspects (deduction-based scoring)

        Initial score: 5.0 points
        Deductions based on issue severity:
        - Minor: -0.5 points
        - Moderate: -1.0 points
        - Severe: -2.0 points

        Args:
            design: Design parameters
            results: Analysis results

        Returns:
            Dictionary containing:
                - score: Score (0-5)
                - issues: List of construction issues
        """
        initial_score = 5.0
        issues = []

        # Call structure-specific construction checks
        structure_issues = self._check_structure_specific_construction(design, results)

        # Deduct points based on severity
        for issue in structure_issues:
            severity = issue.get('severity', 'minor')
            if severity == 'minor':
                initial_score -= 0.5
            elif severity == 'moderate':
                initial_score -= 1.0
            elif severity == 'severe':
                initial_score -= 2.0
            issues.append(issue)

        return {
            'score': max(0, initial_score),
            'issues': issues
        }
