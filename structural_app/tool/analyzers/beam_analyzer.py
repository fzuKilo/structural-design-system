"""
Beam analyzer using OpenSeesPy
Implements finite element analysis for beam structures
"""

import openseespy.opensees as ops
import numpy as np
from typing import Dict, Any, List, Optional
from .base_analyzer import StructureAnalyzer, AnalysisResults


class BeamAnalyzer(StructureAnalyzer):
    """
    Concrete analyzer for beam structures using OpenSeesPy

    Supports:
    - Simply supported beams
    - Cantilever beams (future)
    - Continuous beams (future)
    """

    def __init__(self):
        """Initialize beam analyzer"""
        super().__init__()
        self.model_built = False
        self.design_params = None

    def _get_structure_type(self) -> str:
        """Return structure type identifier"""
        return "beam"

    def validate_design(self, design: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate beam-specific design parameters

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

        # Check constraints
        constraints = design.get('constraints', {})
        if 'support_type' not in constraints:
            return False, "Missing constraint parameter: support_type"

        support_type = constraints['support_type']
        valid_types = ['simply_supported', 'cantilever', 'fixed_fixed']
        if support_type not in valid_types:
            return False, f"Invalid support_type: {support_type}. Must be one of {valid_types}"

        return True, None

    def build_model(self, design: Dict[str, Any]) -> bool:
        """
        Build OpenSeesPy finite element model for beam

        Args:
            design: Design parameters containing:
                - geometry: {length, width, height, n_elements (optional)}
                - material: {E, nu, fy (optional)}
                - loads: {distributed: [{q, direction}], point: [{P, location, direction}]}
                - constraints: {support_type}

        Returns:
            True if model built successfully
        """
        try:
            # Clear any existing model
            ops.wipe()

            # Store design parameters
            self.design_params = design

            # Extract parameters
            geometry = design['geometry']
            material = design['material']
            loads = design['loads']
            constraints = design['constraints']

            # Geometry
            L = geometry['length']
            b = geometry['width']
            h = geometry['height']
            n_elem = geometry.get('n_elements', 20)  # Default 20 elements

            # Material
            E = material['E']
            nu = material.get('nu', 0.2)

            # Section properties
            A = b * h
            I = b * h**3 / 12

            # Initialize model
            ops.model('basic', '-ndm', 2, '-ndf', 3)

            # Create nodes
            self.nodes = []
            for i in range(n_elem + 1):
                x = i * L / n_elem
                y = 0.0
                ops.node(i + 1, x, y)
                self.nodes.append([x, y])

            # Apply boundary conditions based on support type
            support_type = constraints['support_type']
            if support_type == 'simply_supported':
                # Left: pinned (fixed x, y; free rotation)
                ops.fix(1, 1, 1, 0)
                # Right: roller (free x, fixed y; free rotation)
                ops.fix(n_elem + 1, 0, 1, 0)
            elif support_type == 'cantilever':
                # Left: fixed (fixed x, y, rotation)
                ops.fix(1, 1, 1, 1)
                # Right: free
            elif support_type == 'fixed_fixed':
                # Both ends fixed
                ops.fix(1, 1, 1, 1)
                ops.fix(n_elem + 1, 1, 1, 1)

            # Create geometric transformation
            geom_transf_tag = 1
            ops.geomTransf('Linear', geom_transf_tag)

            # Create elements
            for i in range(n_elem):
                ops.element('elasticBeamColumn', i + 1, i + 1, i + 2, A, E, I, geom_transf_tag)

            # Apply loads
            ops.timeSeries('Linear', 1)
            ops.pattern('Plain', 1, 1)

            # Distributed loads
            if 'distributed' in loads:
                for load in loads['distributed']:
                    q = load['q']  # Load intensity (N/m)
                    direction = load.get('direction', 'y')  # Default vertical

                    if direction == 'y':
                        for i in range(n_elem):
                            ops.eleLoad('-ele', i + 1, '-type', '-beamUniform', q, 0.0)
                    elif direction == 'x':
                        for i in range(n_elem):
                            ops.eleLoad('-ele', i + 1, '-type', '-beamUniform', 0.0, q)

            # Point loads - use eleLoad for precise positioning
            if 'point' in loads:
                for load in loads['point']:
                    P = load['P']  # Load magnitude (N)
                    location = load['location']  # Position along beam (m)
                    direction = load.get('direction', 'y')  # Default vertical

                    # Find element and local position
                    elem_length = L / n_elem
                    elem_id = int(location / elem_length) + 1
                    elem_id = max(1, min(elem_id, n_elem))

                    # Calculate local position within element (0 to 1)
                    elem_start = (elem_id - 1) * elem_length
                    local_pos = (location - elem_start) / elem_length
                    local_pos = max(0.0, min(1.0, local_pos))

                    if direction == 'y':
                        ops.eleLoad('-ele', elem_id, '-type', '-beamPoint', P, local_pos)
                    elif direction == 'x':
                        # For axial loads, still use nodal load
                        node_id = int(round(location / L * n_elem)) + 1
                        node_id = max(1, min(node_id, n_elem + 1))
                        ops.load(node_id, P, 0.0, 0.0)

            # Store model parameters
            self.n_elem = n_elem
            self.L = L
            self.b = b
            self.h = h
            self.I = I
            self.E = E

            self.model_built = True
            return True

        except Exception as e:
            print(f"Error building model: {str(e)}")
            self.model_built = False
            return False

    def analyze(self) -> AnalysisResults:
        """
        Perform finite element analysis using OpenSeesPy

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

        try:
            # Set up analysis
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
                    nodes=self.nodes,
                    n_elements=self.n_elem,
                    structure_type=self.structure_type,
                    analysis_status='failed',
                    error_message='Analysis convergence failed'
                )

            # Extract results
            displacements = []
            for i in range(self.n_elem + 1):
                disp = ops.nodeDisp(i + 1)
                displacements.append(disp[1])  # Y-direction displacement

            # Extract element forces
            moments = []
            shears = []
            for i in range(self.n_elem):
                forces = ops.eleForce(i + 1)
                # Average moment at element ends
                moment = (abs(forces[2]) + abs(forces[5])) / 2
                shear = abs(forces[1])
                moments.append(moment)
                shears.append(shear)

            # Calculate stresses (σ = M*y/I)
            y_max = self.h / 2
            stresses = [M * y_max / self.I for M in moments]

            # Find maximum values
            max_displacement = max(abs(d) for d in displacements)
            max_stress = max(stresses) if stresses else 0.0
            max_moment = max(moments) if moments else 0.0
            max_shear = max(shears) if shears else 0.0

            # Clean up
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
                nodes=self.nodes,
                n_elements=self.n_elem,
                structure_type=self.structure_type,
                analysis_status='success',
                geometry=self.design_params.get('geometry'),
                material=self.design_params.get('material')
            )

        except Exception as e:
            ops.wipe()
            self.model_built = False
            return AnalysisResults(
                max_displacement=0.0,
                max_stress=0.0,
                max_moment=0.0,
                max_shear=0.0,
                displacements=[],
                stresses=[],
                moments=[],
                shears=[],
                nodes=self.nodes if hasattr(self, 'nodes') else [],
                n_elements=self.n_elem if hasattr(self, 'n_elem') else 0,
                structure_type=self.structure_type,
                analysis_status='failed',
                error_message=f'Analysis error: {str(e)}'
            )

    def check_code(self, results: AnalysisResults) -> Dict[str, Any]:
        """
        Check beam design against code requirements (simplified)

        Args:
            results: Analysis results

        Returns:
            Dictionary with compliance status
        """
        violations = []
        safety_factors = {}

        # Get material properties
        material = self.design_params.get('material', {})
        fy = material.get('fy', 235e6)  # Default: Q235 steel (235 MPa)

        # Check 1: Stress limit (allowable stress = fy / 1.5)
        allowable_stress = fy / 1.5
        if results.max_stress > allowable_stress:
            violations.append({
                'code': 'Stress Limit',
                'description': f'Max stress {results.max_stress/1e6:.2f} MPa exceeds allowable {allowable_stress/1e6:.2f} MPa',
                'severity': 'critical'
            })
        safety_factors['stress'] = allowable_stress / results.max_stress if results.max_stress > 0 else float('inf')

        # Check 2: Deflection limit (L/250 for general structures)
        L = self.design_params['geometry']['length']
        deflection_limit = L / 250
        if results.max_displacement > deflection_limit:
            violations.append({
                'code': 'Deflection Limit',
                'description': f'Max deflection {results.max_displacement*1000:.2f} mm exceeds limit {deflection_limit*1000:.2f} mm (L/250)',
                'severity': 'warning'
            })
        safety_factors['deflection'] = deflection_limit / results.max_displacement if results.max_displacement > 0 else float('inf')

        # Overall compliance
        compliant = len(violations) == 0

        return {
            'compliant': compliant,
            'violations': violations,
            'safety_factors': safety_factors,
            'summary': f"{'PASS' if compliant else 'FAIL'} - {len(violations)} violation(s) found"
        }
