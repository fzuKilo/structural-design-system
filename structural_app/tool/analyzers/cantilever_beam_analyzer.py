"""
Cantilever beam analyzer using OpenSeesPy
Implements finite element analysis for cantilever beam structures
"""

import openseespy.opensees as ops
import numpy as np
from typing import Dict, Any, List, Optional
from .base_analyzer import StructureAnalyzer, AnalysisResults


class CantileverBeamAnalyzer(StructureAnalyzer):
    """
    Concrete analyzer for cantilever beam structures using OpenSeesPy

    Key differences from simply supported beam:
    - Fixed support at one end (all DOFs constrained)
    - Free end at the other end
    - Different deflection limits (L/200 vs L/250)
    """

    def __init__(self):
        """Initialize cantilever beam analyzer"""
        super().__init__()
        self.model_built = False
        self.design_params = None

    def _get_structure_type(self) -> str:
        """Return structure type identifier"""
        return "cantilever_beam"

    def validate_design(self, design: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate cantilever beam-specific design parameters

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

        return True, None

    def build_model(self, design: Dict[str, Any]) -> None:
        """
        Build OpenSeesPy model for cantilever beam

        Args:
            design: Design parameters including geometry, material, loads, constraints
        """
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

        E = material['E']
        nu = material.get('nu', 0.2)
        G = E / (2 * (1 + nu))

        # Calculate section properties
        A = width * height
        Iz = (width * height**3) / 12

        # Create nodes
        n_nodes = n_elements + 1
        for i in range(n_nodes):
            x = i * length / n_elements
            ops.node(i + 1, x, 0.0)

        # Define boundary conditions - CANTILEVER
        # Node 1 (left end): Fixed support (all DOFs constrained)
        ops.fix(1, 1, 1, 1)
        # All other nodes: Free (no constraints)

        # Define geometric transformation
        ops.geomTransf('Linear', 1)

        # Create elements
        for i in range(n_elements):
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
                    for i in range(n_elements):
                        ops.eleLoad('-ele', i + 1, '-type', '-beamUniform', q, 0.0)

        # Point loads
        if 'point' in loads:
            for point_load in loads['point']:
                position = point_load.get('position', length)
                force = point_load.get('force', 0)
                direction = point_load.get('direction', 'y')

                # Find closest node
                node_id = int(round(position / length * n_elements)) + 1
                node_id = max(1, min(n_nodes, node_id))

                if direction == 'y':
                    ops.load(node_id, 0.0, force, 0.0)

        self.model_built = True
        return True

    def analyze(self) -> AnalysisResults:
        """
        Run finite element analysis

        Returns:
            AnalysisResults object with all results
        """
        if not self.model_built:
            return AnalysisResults(
                max_displacement=0.0, max_stress=0.0, max_moment=0.0, max_shear=0.0,
                displacements=[], stresses=[], moments=[], shears=[],
                nodes=[], n_elements=0, structure_type=self.structure_type,
                analysis_status='failed', error_message='Model not built'
            )

        try:
            ops.system('BandGeneral')
            ops.numberer('RCM')
            ops.constraints('Plain')
            ops.integrator('LoadControl', 1.0)
            ops.algorithm('Linear')
            ops.analysis('Static')

            ok = ops.analyze(1)

            if ok != 0:
                ops.wipe()
                self.model_built = False
                return AnalysisResults(
                    max_displacement=0.0, max_stress=0.0, max_moment=0.0, max_shear=0.0,
                    displacements=[], stresses=[], moments=[], shears=[],
                    nodes=[], n_elements=0, structure_type=self.structure_type,
                    analysis_status='failed', error_message='Analysis failed to converge'
                )

            geometry = self.design_params['geometry']
            n_elements = geometry.get('n_elements', 20)
            n_nodes = n_elements + 1
            length = geometry['length']
            width = geometry['width']
            height = geometry['height']

            # Node coordinates
            nodes = [[i * length / n_elements, 0.0] for i in range(n_nodes)]

            # Displacements
            displacements = [ops.nodeDisp(i + 1)[1] for i in range(n_nodes)]
            max_displacement = max(abs(d) for d in displacements)

            # Element forces
            moments = []
            shears = []
            for i in range(n_elements):
                forces = ops.eleForce(i + 1)
                moments.append(max(abs(forces[2]), abs(forces[5])))
                shears.append(max(abs(forces[1]), abs(forces[4])))

            max_moment = max(moments)
            max_shear = max(shears)

            # Stresses
            Iz = (width * height**3) / 12
            c = height / 2
            stresses = [m * c / Iz for m in moments]
            max_stress = max(stresses)

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
                geometry=self.design_params.get('geometry'),
                material=self.design_params.get('material')
            )

        except Exception as e:
            ops.wipe()
            self.model_built = False
            return AnalysisResults(
                max_displacement=0.0, max_stress=0.0, max_moment=0.0, max_shear=0.0,
                displacements=[], stresses=[], moments=[], shears=[],
                nodes=[], n_elements=0, structure_type=self.structure_type,
                analysis_status='failed', error_message=str(e)
            )

    def check_code(self, results: AnalysisResults) -> Dict[str, Any]:
        """
        Check design against code requirements (cantilever beam specific)

        Args:
            results: AnalysisResults from analyze()

        Returns:
            Dictionary containing code check results
        """
        if results.analysis_status != 'success':
            return {
                'compliant': False,
                'violations': ['Analysis failed'],
                'safety_factors': {},
                'summary': 'FAIL - Analysis failed'
            }

        geometry = self.design_params['geometry']
        material = self.design_params['material']

        length = geometry['length']
        max_displacement = results.max_displacement
        max_stress = results.max_stress

        # Deflection limit for cantilever: L/200
        deflection_limit = length / 200

        # Stress limit
        fy = material.get('fy', 235e6)
        allowable_stress = fy / 1.5

        violations = []
        if max_displacement > deflection_limit:
            violations.append(f"Deflection exceeds limit: {max_displacement:.4f}m > {deflection_limit:.4f}m")
        if max_stress > allowable_stress:
            violations.append(f"Stress exceeds limit: {max_stress/1e6:.2f}MPa > {allowable_stress/1e6:.2f}MPa")

        deflection_sf = deflection_limit / max_displacement if max_displacement > 0 else float('inf')
        stress_sf = allowable_stress / max_stress if max_stress > 0 else float('inf')

        return {
            'compliant': len(violations) == 0,
            'violations': violations,
            'safety_factors': {
                'deflection': round(deflection_sf, 2),
                'stress': round(stress_sf, 2)
            },
            'summary': f"{'PASS' if not violations else 'FAIL'} - {len(violations)} violation(s) found"
        }
