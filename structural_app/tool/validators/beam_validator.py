"""
Validator for beam design parameters.
"""
from typing import Dict, Any, Tuple, Optional

from structural_app.tool.validators.base_validator import ParameterValidator


class BeamValidator(ParameterValidator):
    """
    Validator for beam structure type.

    Beam requires these parameters:
    - length (span): MUST be provided by user (cannot guess)
    - loads: MUST be provided by user (cannot guess)
    - support_type: MUST be provided by user (cannot guess)
    - width, height, material: CAN be defaulted using engineering judgment
    """

    # Required parameters that must be asked from user
    REQUIRED_PARAMETERS = ['length', 'loads', 'support_type']

    # Parameters that can be defaulted
    DEFAULTABLE_PARAMETERS = {
        'width': {'default': 0.3, 'inquiry': '截面宽度是多少米？(默认 0.3m)'},
        'height': {'default': None, 'inquiry': '截面高度是多少米？(可按 L/15 估算)'},
        'material_name': {'default': 'C30', 'inquiry': '使用什么材料？(如 C30, Q235)'},
        'E': {'default': 30e9, 'inquiry': '弹性模量 E 是多少 Pa？(C30 混凝土: 30e9)'},
        'nu': {'default': 0.2, 'inquiry': '泊松比 nu 是多少？(混凝土: 0.2)'},
    }

    def validate_parameters(self, design: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Validate beam design parameters.
        """
        # Get geometry and constraints
        geometry = design.get('geometry', {})
        loads = design.get('loads', {})
        constraints = design.get('constraints', {})

        # Check required parameters
        missing_params = {}

        # Check length (span) - MUST be provided
        if 'length' not in geometry:
            missing_params['length'] = '跨度（长度）是多少米？'

        # Check loads - MUST be provided
        if not loads or ('distributed' not in loads and 'point' not in loads):
            missing_params['loads'] = '荷载是多少？(请说明均布荷载或点荷载的大小)'

        # Check support_type - MUST be provided
        if 'support_type' not in constraints:
            missing_params['support_type'] = '支座类型是什么？(简支梁、固定梁、悬臂梁等)'

        # If there are missing required parameters
        if missing_params:
            return False, "Missing required parameters for beam design", missing_params

        # All required parameters present
        return True, None, None

    def get_inquiry_questions(self, missing_params: Dict[str, Any]) -> str:
        """
        Generate inquiry questions for missing beam parameters.
        """
        questions = ["请补充以下必要信息："]

        for param, question in missing_params.items():
            questions.append(f"- {question}")

        return "\n".join(questions)
