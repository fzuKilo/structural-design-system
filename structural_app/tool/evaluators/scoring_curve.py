"""
Multi-level scoring curve for structural design evaluation
Implements DQS-inspired scoring algorithm with configurable parameters
"""

from typing import Tuple


class MultiLevelScoringCurve:
    """
    Multi-level scoring curve (inspired by DQS)

    Applicable to all structure types through parameter configuration.
    Implements a bell-shaped scoring curve with optimal utilization range.

    Scoring Zones:
    - Excellent zone: 92-100% score (near optimal utilization)
    - Good zone: 85-92% score (acceptable utilization)
    - Acceptable zone: 70-85% score (marginal utilization)
    - Poor zone: 0-70% score (too low or too high utilization)
    - Over-limit: 0% score (exceeds capacity)
    """

    def __init__(
        self,
        excellent_range: Tuple[float, float],
        good_range: Tuple[float, float],
        acceptable_range: Tuple[float, float],
        peak_position: float = None
    ):
        """
        Initialize scoring curve

        Args:
            excellent_range: Excellent zone range, e.g., (0.65, 0.75)
            good_range: Good zone range, e.g., (0.60, 0.80)
            acceptable_range: Acceptable zone range, e.g., (0.50, 0.90)
            peak_position: Peak score position, e.g., 0.70 (defaults to center of excellent range)
        """
        self.excellent_min, self.excellent_max = excellent_range
        self.good_min, self.good_max = good_range
        self.acceptable_min, self.acceptable_max = acceptable_range
        self.peak = peak_position or (self.excellent_min + self.excellent_max) / 2

        # Validate ranges
        self._validate_ranges()

    def _validate_ranges(self):
        """Validate that ranges are properly nested"""
        if not (self.acceptable_min <= self.good_min <= self.excellent_min):
            raise ValueError("Ranges must be properly nested: acceptable <= good <= excellent")
        if not (self.excellent_max <= self.good_max <= self.acceptable_max):
            raise ValueError("Ranges must be properly nested: excellent <= good <= acceptable")

    def calculate_score(self, utilization: float, max_score: float = 100) -> float:
        """
        Calculate score based on utilization ratio

        Scoring zones:
        - Over-limit (>1.0): 0 score
        - Excellent zone: 92-100% score
        - Good zone: 85-92% score
        - Acceptable zone: 70-85% score
        - Poor zone: 0-70% score

        Args:
            utilization: Utilization ratio (0.0 to 1.0+)
            max_score: Maximum possible score (default: 100)

        Returns:
            Score value (0 to max_score)
        """
        # Over-limit: 0 score
        if utilization > 1.0:
            return 0.0

        # Excellent zone: 92-100% score
        if self.excellent_min <= utilization <= self.excellent_max:
            distance = abs(utilization - self.peak)
            max_distance = (self.excellent_max - self.excellent_min) / 2
            score_ratio = 1.0 - 0.08 * (distance / max_distance)
            return max_score * score_ratio

        # Good zone - low side: 85-92% score
        if self.good_min <= utilization < self.excellent_min:
            ratio = (utilization - self.good_min) / (self.excellent_min - self.good_min)
            score_ratio = 0.85 + 0.07 * ratio
            return max_score * score_ratio

        # Good zone - high side: 85-92% score
        if self.excellent_max < utilization <= self.good_max:
            ratio = 1 - (utilization - self.excellent_max) / (self.good_max - self.excellent_max)
            score_ratio = 0.85 + 0.07 * ratio
            return max_score * score_ratio

        # Acceptable zone - low side: 70-85% score
        if self.acceptable_min <= utilization < self.good_min:
            ratio = (utilization - self.acceptable_min) / (self.good_min - self.acceptable_min)
            score_ratio = 0.70 + 0.15 * ratio
            return max_score * score_ratio

        # Acceptable zone - high side: 70-85% score
        if self.good_max < utilization <= self.acceptable_max:
            ratio = 1 - (utilization - self.good_max) / (self.acceptable_max - self.good_max)
            score_ratio = 0.70 + 0.15 * ratio
            return max_score * score_ratio

        # Poor zone - low side: 0-70% score
        if utilization < self.acceptable_min:
            ratio = utilization / self.acceptable_min
            score_ratio = 0.70 * ratio
            return max_score * score_ratio

        # Poor zone - high side: 0-70% score
        ratio = (1.0 - utilization) / (1.0 - self.acceptable_max)
        score_ratio = 0.70 * ratio
        return max_score * score_ratio
