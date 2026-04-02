"""
Base analyzer for structural analysis
Defines the abstract interface for all structure type analyzers
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class AnalysisResults:
    """
    Standard format for analysis results
    """
    # Basic results
    max_displacement: float  # Maximum displacement (m)
    max_stress: float  # Maximum stress (Pa)
    max_moment: float  # Maximum moment (N*m)
    max_shear: float  # Maximum shear force (N)

    # Detailed results
    displacements: List[float]  # Nodal displacements
    stresses: List[float]  # Element stresses
    moments: List[float]  # Element moments
    shears: List[float]  # Element shears

    # Node and element data
    nodes: List[List[float]]  # Node coordinates
    n_elements: int  # Number of elements

    # Metadata
    structure_type: str  # Type of structure (beam, frame, etc.)
    analysis_status: str  # "success" or "failed"
    error_message: Optional[str] = None

    # Additional data for visualization
    geometry: Dict[str, Any] = None  # Geometry parameters
    material: Dict[str, Any] = None  # Material properties
    extra: Dict[str, Any] = None     # Structure-specific extra data (e.g. ux_displacements, axial_forces)

    def to_dict(self) -> Dict:
        """Convert to dictionary format"""
        return {
            'max_displacement': self.max_displacement,
            'max_stress': self.max_stress,
            'max_moment': self.max_moment,
            'max_shear': self.max_shear,
            'displacements': self.displacements,
            'stresses': self.stresses,
            'moments': self.moments,
            'shears': self.shears,
            'nodes': self.nodes,
            'n_elements': self.n_elements,
            'structure_type': self.structure_type,
            'analysis_status': self.analysis_status,
            'error_message': self.error_message,
            'geometry': self.geometry,
            'material': self.material,
            'extra': self.extra or {}
        }


class StructureAnalyzer(ABC):
    """
    Abstract base class for structure analyzers

    All concrete analyzers (BeamAnalyzer, FrameAnalyzer, etc.) must inherit from this class
    and implement the abstract methods.
    """

    def __init__(self):
        """Initialize the analyzer"""
        self.structure_type = self._get_structure_type()

    @abstractmethod
    def _get_structure_type(self) -> str:
        """
        Return the structure type identifier

        Returns:
            Structure type string (e.g., "beam", "frame", "truss")
        """
        pass

    @abstractmethod
    def build_model(self, design: Dict[str, Any]) -> bool:
        """
        Build the finite element model based on design parameters

        Args:
            design: Design parameters including:
                - geometry: Geometric parameters (length, width, height, etc.)
                - material: Material properties (E, nu, density, etc.)
                - loads: Load cases (point loads, distributed loads, etc.)
                - constraints: Boundary conditions

        Returns:
            True if model built successfully, False otherwise

        Raises:
            ValueError: If design parameters are invalid
        """
        pass

    @abstractmethod
    def analyze(self) -> AnalysisResults:
        """
        Perform finite element analysis

        Returns:
            AnalysisResults object containing all analysis results

        Raises:
            RuntimeError: If analysis fails
        """
        pass

    @abstractmethod
    def check_code(self, results: AnalysisResults) -> Dict[str, Any]:
        """
        Check design against code requirements

        Args:
            results: Analysis results from analyze()

        Returns:
            Dictionary containing:
                - compliant: bool (True if all checks pass)
                - violations: List of code violations
                - safety_factors: Dictionary of safety factors
        """
        pass

    def validate_design(self, design: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate design parameters before analysis

        Args:
            design: Design parameters

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check required fields
        required_fields = ['geometry', 'material', 'loads', 'constraints']
        for field in required_fields:
            if field not in design:
                return False, f"Missing required field: {field}"

        # Type-specific validation will be done in concrete classes
        return True, None

    def _validate_model(self, design: Dict[str, Any]) -> None:
        """
        Validate the built FE model (automatic checks)

        Args:
            design: Design parameters

        Raises:
            AssertionError: If model validation fails
        """
        import openseespy.opensees as ops

        nodes = ops.getNodeTags()
        elements = ops.getEleTags()

        assert nodes, "错误：未创建任何节点"
        assert elements, "错误：未创建任何单元"

        # Check boundary conditions
        fixed_dofs = sum(len([d for d in ops.getFixedNodes(n) if d == 1]) for n in nodes)
        assert fixed_dofs > 0, "错误：未施加边界条件"

        # Structure-specific checks
        self._validate_structure_specific(design)

        print(f"[OK] 模型验证通过：{len(nodes)}节点，{len(elements)}单元")

    @abstractmethod
    def _validate_structure_specific(self, design: Dict[str, Any]) -> None:
        """
        Structure-specific model validation (implemented by subclasses)

        Args:
            design: Design parameters

        Raises:
            AssertionError: If validation fails
        """
        pass

    @abstractmethod
    def export_opensees_script(self, design: Dict[str, Any], output_path: str) -> str:
        """
        Export OpenSees Tcl script for expert review

        Args:
            design: Design parameters
            output_path: Path to save the script

        Returns:
            Path to the generated script
        """
        pass

    def run_full_analysis(self, design: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run complete analysis workflow: validate -> build -> analyze -> check

        Args:
            design: Design parameters

        Returns:
            Dictionary containing:
                - results: AnalysisResults object
                - code_check: Code compliance results
                - status: Overall status
        """
        # Validate design
        is_valid, error_msg = self.validate_design(design)
        if not is_valid:
            return {
                'status': 'failed',
                'error': f"Design validation failed: {error_msg}",
                'results': None,
                'code_check': None
            }

        try:
            # Build model
            if not self.build_model(design):
                return {
                    'status': 'failed',
                    'error': 'Failed to build finite element model',
                    'results': None,
                    'code_check': None
                }

            # Validate model (automatic checks)
            self._validate_model(design)

            # Analyze
            results = self.analyze()

            if results.analysis_status != 'success':
                return {
                    'status': 'failed',
                    'error': f"Analysis failed: {results.error_message}",
                    'results': results,
                    'code_check': None
                }

            # Check code compliance
            code_check = self.check_code(results)

            return {
                'status': 'success',
                'results': results,
                'code_check': code_check,
                'error': None
            }

        except Exception as e:
            return {
                'status': 'failed',
                'error': f"Analysis error: {str(e)}",
                'results': None,
                'code_check': None
            }
