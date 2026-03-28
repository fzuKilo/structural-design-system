"""
Continuous beam analyzer using OpenSeesPy
Implements finite element analysis for continuous beam structures
"""

import openseespy.opensees as ops
import numpy as np
from typing import Dict, Any, List, Optional
from .base_analyzer import StructureAnalyzer, AnalysisResults


class ContinuousBeamAnalyzer(StructureAnalyzer):
    """
    Concrete analyzer for continuous beam structures using OpenSeesPy

    Key differences from simply supported beam:
    - Multiple spans with intermediate supports
    - Different deflection limits (L/300 vs L/250)
    - More complex boundary conditions
    """

    def __init__(self):
        """Initialize continuous beam analyzer"""
        super().__init__()
        self.model_built = False
        self.design_params = None

    def _get_structure_type(self) -> str:
        """Return structure type identifier"""
        return "continuous_beam"

    def validate_design(self, design: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate continuous beam-specific design parameters

        Args:
            design: Design parameters

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Call parent validation first
        is_valid, error_msg = super().validate_design(design)
        if not is_valid:
            return False, error_msg

        # Check geometry parameters
        geometry = design.get('geometry', {})
        required_geom = ['length', 'width', 'height']
        for param in required_geom:
            if param not in geometry:
                return False, f"Missing geometry parameter: {param}"
            if geometry[param] <= 0:
                return False, f"Invalid geometry parameter {param}: must be positive"

        # Check number of spans
        n_spans = geometry.get('n_spans', 2)
        if n_spans < 2:
            return False, "Continuous beam must have at least 2 spans"
        if n_spans > 5:
            return False, "Maximum 5 spans supported"

        # Check material parameters
        material = design.get('material', {})
        required_mat = ['E', 'nu']
        for param in required_mat:
            if param not in material:
                return False, f"Missing material parameter: {param}"
            if material[param] <= 0:
                return False, f"Invalid material parameter {param}: must be positive"

        # Check loads
        loads = design.get('loads', {})
        if 'distributed' not in loads and 'point' not in loads:
            return False, "No loads specified (need 'distributed' or 'point')"

        return True, None

    def build_model(self, design: Dict[str, Any]) -> None:
        """
        Build OpenSeesPy model for continuous beam

        Args:
            design: Design parameters including geometry, material, loads, constraints
        """
        try:
            # Validate design first
            is_valid, error_msg = self.validate_design(design)
            if not is_valid:
                raise ValueError(f"Invalid design: {error_msg}")

            # Store design parameters
            self.design_params = design

            # Clear any existing model
            ops.wipe()

            # Create model
            ops.model('basic', '-ndm', 2, '-ndf', 3)

            # Extract parameters
            geometry = design['geometry']
            material = design['material']
            loads = design['loads']

            length = geometry['length']
            width = geometry['width']
            height = geometry['height']
            n_elements = geometry.get('n_elements', 20)
            n_spans = geometry.get('n_spans', 2)

            E = material['E']
            nu = material.get('nu', 0.2)
            G = E / (2 * (1 + nu))

            # Calculate section properties
            A = width * height
            Iz = (width * height**3) / 12

            # Create nodes
            # For continuous beam: divide total length into spans
            span_length = length / n_spans
            import math
            elements_per_span = math.ceil(n_elements / n_spans)
            total_nodes = n_spans * elements_per_span + 1

            # Log warning if actual elements differ significantly
            actual_elements = n_spans * elements_per_span
            if abs(actual_elements - n_elements) > n_elements * 0.1:
                print(f"Warning: Actual elements ({actual_elements}) differs from requested ({n_elements})")

            for i in range(total_nodes):
                x = i * span_length / elements_per_span
                ops.node(i + 1, x, 0.0)

            # Define boundary conditions - CONTINUOUS BEAM
            # First node: Pinned support (x and y constrained, rotation free)
            ops.fix(1, 1, 1, 0)

            # Intermediate supports: Roller supports (y constrained, x and rotation free)
            for span_idx in range(1, n_spans):
                support_node = span_idx * elements_per_span + 1
                ops.fix(support_node, 0, 1, 0)

            # Last node: Roller support (y constrained, x and rotation free)
            ops.fix(total_nodes, 0, 1, 0)

            # Define geometric transformation
            ops.geomTransf('Linear', 1)

            # Create elements
            for i in range(total_nodes - 1):
                ops.element('elasticBeamColumn', i + 1, i + 1, i + 2, A, E, Iz, 1)

            # Create load pattern
            ops.timeSeries('Linear', 1)
            ops.pattern('Plain', 1, 1)

            # Apply loads
            # Distributed loads
            if 'distributed' in loads:
                for dist_load in loads['distributed']:
                    q = dist_load.get('q', 0)
                    direction = dist_load.get('direction', 'y')

                    if direction == 'y':
                        for i in range(total_nodes - 1):
                            ops.eleLoad('-ele', i + 1, '-type', '-beamUniform', q, 0.0)

            # Point loads
            if 'point' in loads:
                for point_load in loads['point']:
                    position = point_load.get('position', length / 2)
                    force = point_load.get('force', 0)
                    direction = point_load.get('direction', 'y')

                    # Find closest node
                    node_id = int(round(position / (span_length / elements_per_span))) + 1
                    node_id = max(1, min(total_nodes, node_id))

                    if direction == 'y':
                        ops.load(node_id, 0.0, force, 0.0)

            self.model_built = True
            return True

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            raise RuntimeError(
                f"Failed to build continuous beam model: {str(e)}\n"
                f"Design parameters: {design}\n"
                f"Traceback: {error_details}"
            )

    def analyze(self) -> AnalysisResults:
        """
        Run finite element analysis

        Returns:
            AnalysisResults object with all results
        """
        if not self.model_built:
            return AnalysisResults(
                max_displacement=0.0,
                max_stress=0.0,
                max_moment=0.0,
                max_shear=0.0,
                displacements=[],
                stresses=[],
                moments=[],
                shears=[],
                nodes=[],
                n_elements=0,
                structure_type=self.structure_type,
                analysis_status='failed',
                error_message='Model not built'
            )

        # Create analysis
        ops.system('BandGeneral')
        ops.numberer('RCM')
        ops.constraints('Plain')
        ops.integrator('LoadControl', 1.0)
        ops.algorithm('Linear')
        ops.analysis('Static')

        # Run analysis
        ok = ops.analyze(1)

        if ok != 0:
            return AnalysisResults(
                max_displacement=0.0,
                max_stress=0.0,
                max_moment=0.0,
                max_shear=0.0,
                displacements=[],
                stresses=[],
                moments=[],
                shears=[],
                nodes=[],
                n_elements=0,
                structure_type=self.structure_type,
                analysis_status='failed',
                error_message='Analysis failed to converge'
            )

        # Extract results
        geometry = self.design_params['geometry']
        n_elements = geometry.get('n_elements', 20)
        n_spans = geometry.get('n_spans', 2)
        import math
        elements_per_span = math.ceil(n_elements / n_spans)
        total_nodes = n_spans * elements_per_span + 1

        # Get displacements
        displacements = []
        for i in range(total_nodes):
            disp = ops.nodeDisp(i + 1)
            displacements.append(disp[1])  # y-displacement

        max_displacement = max(abs(d) for d in displacements)

        # Get element forces (moments and shears)
        moments = []
        shears = []
        for i in range(total_nodes - 1):
            forces = ops.eleForce(i + 1)
            # For 2D beam: [N1, V1, M1, N2, V2, M2]
            moment = max(abs(forces[2]), abs(forces[5]))
            shear = max(abs(forces[1]), abs(forces[4]))
            moments.append(moment)
            shears.append(shear)

        max_moment = max(moments)
        max_shear = max(shears)

        # Calculate stress
        width = geometry['width']
        height = geometry['height']
        Iz = (width * height**3) / 12
        c = height / 2
        max_stress = (max_moment * c) / Iz

        # Get node coordinates
        nodes = []
        span_length = geometry['length'] / n_spans
        elements_per_span = n_elements // n_spans
        for i in range(total_nodes):
            x = i * span_length / elements_per_span
            nodes.append([x, 0.0])

        # Calculate stresses for each element
        stresses = []
        for moment in moments:
            stress = (moment * c) / Iz
            stresses.append(stress)

        ops.wipe()
        self.model_built = False

        return AnalysisResults(
            max_displacement=max_displacement,
            max_stress=max_stress,
            max_moment=max_moment,
            max_shear=max_shear,
            displacements=displacements,
            stresses=stresses,
            moments=moments,
            shears=shears,
            nodes=nodes,
            n_elements=n_elements,
            structure_type=self.structure_type,
            analysis_status='success',
            error_message=None,
            geometry=geometry,
            material=self.design_params['material']
        )

    def check_code(self, results: AnalysisResults) -> Dict[str, Any]:
        """
        Check design against code requirements (continuous beam specific)

        Args:
            results: Analysis results from analyze()

        Returns:
            Dictionary containing code check results
        """
        if results.analysis_status != 'success':
            return {
                'compliant': False,
                'violations': ['Analysis failed'],
                'safety_factors': {}
            }

        geometry = self.design_params['geometry']
        material = self.design_params['material']

        length = geometry['length']
        max_displacement = results.max_displacement
        max_stress = results.max_stress
        max_stress_MPa = max_stress / 1e6

        # Deflection limit for continuous beam: L/300 (stricter than simply supported)
        deflection_limit = length / 300

        # Stress limit
        fy = material.get('fy', 235e6)
        fy_MPa = fy / 1e6
        allowable_stress = fy_MPa / 1.5

        # Check compliance
        violations = []
        if max_displacement > deflection_limit:
            violations.append(f"Deflection exceeds limit: {max_displacement:.4f}m > {deflection_limit:.4f}m")

        if max_stress_MPa > allowable_stress:
            violations.append(f"Stress exceeds limit: {max_stress_MPa:.2f}MPa > {allowable_stress:.2f}MPa")

        # Calculate safety factors
        deflection_sf = deflection_limit / max_displacement if max_displacement > 0 else float('inf')
        stress_sf = allowable_stress / max_stress_MPa if max_stress_MPa > 0 else float('inf')

        return {
            'compliant': len(violations) == 0,
            'violations': violations,
            'safety_factors': {
                'deflection': round(deflection_sf, 2),
                'stress': round(stress_sf, 2)
            },
            'summary': f"{'PASS' if not violations else 'FAIL'} - {len(violations)} violation(s) found"
        }
