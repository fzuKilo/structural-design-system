"""
Abstract base class for structural parameter validation.
"""
from typing import Dict, Any, Tuple, Optional


class ParameterValidator:
    """
    Abstract base class for validating structural design parameters.

    Different structure types (beam, frame, truss, etc.) should implement
    their own validators by inheriting from this class.
    """

    def validate_parameters(self, design: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Validate that the design has all required parameters.

        Args:
            design: Design proposal dictionary

        Returns:
            Tuple of (is_valid, error_message, missing_parameters)
            - is_valid: True if all required parameters are present
            - error_message: Description of validation failure (if not valid)
            - missing_parameters: Dict of missing parameters with inquiry questions
        """
        raise NotImplementedError("Subclasses must implement validate_parameters")

    def get_inquiry_questions(self, missing_params: Dict[str, Any]) -> str:
        """
        Generate inquiry questions for missing parameters.

        Args:
            missing_params: Dictionary of missing parameters

        Returns:
            Formatted string asking for the missing information
        """
        raise NotImplementedError("Subclasses must implement get_inquiry_questions")
