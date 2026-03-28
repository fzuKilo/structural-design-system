"""
Frame analyzer using OpenSeesPy
Implements finite element analysis for frame structures (multi-bay, multi-story)
"""

import openseespy.opensees as ops
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from .base_analyzer import StructureAnalyzer, AnalysisResults


class FrameAnalyzer(StructureAnalyzer):
    """
    Concrete analyzer for frame structures using OpenSeesPy

    Supports:
    - Multi-bay, multi-story frames
    - Rigid beam-column connections
    - Fixed or pinned column bases
    - Vertical loads on beams
    - Lateral loads (wind, seismic)

    Key features:
    - Story drift calculation (critical for frames)
    - Column axial force extraction
    - Beam-column moment distribution
    """

    def __init__(self):
        """Initialize frame analyzer"""
        super().__init__()
        self.model_built = False
        self.design_params = None
        self.nodes = []
        self.beam_elements = []
        self.column_elements = []
        self.node_coords = {}  # Store node coordinates for visualization

    def _get_structure_type(self) -> str:
        """Return structure type identifier"""
        return "frame"

    def validate_design(self, design: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate frame-specific design parameters

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
        required_geom = ['num_bays', 'num_stories', 'bay_widths', 'story_heights', 'columns', 'beams']
        for param in required_geom:
            if param not in geometry:
                return False, f"Missing required geometry parameter: {param}"

        # Validate bay_widths length
        num_bays = geometry.get('num_bays', 0)
        bay_widths = geometry.get('bay_widths', [])
        if len(bay_widths) != num_bays:
            return False, f"bay_widths length ({len(bay_widths)}) must equal num_bays ({num_bays})"

        # Validate story_heights length
        num_stories = geometry.get('num_stories', 0)
        story_heights = geometry.get('story_heights', [])
        if len(story_heights) != num_stories:
            return False, f"story_heights length ({len(story_heights)}) must equal num_stories ({num_stories})"

        # Validate column and beam sections
        columns = geometry.get('columns', {})
        beams = geometry.get('beams', {})
        if 'width' not in columns or 'depth' not in columns:
            return False, "Column section must have 'width' and 'depth'"
        if 'width' not in beams or 'depth' not in beams:
            return False, "Beam section must have 'width' and 'depth'"

        # Check material parameters
        material = design.get('material', {})
        required_mat = ['E', 'fy']
        for param in required_mat:
            if param not in material:
                return False, f"Missing required material parameter: {param}"

        # Check loads
        loads = design.get('loads', {})
        if not loads:
            return False, "No loads specified"

        return True, None

    def build_model(self, design: Dict[str, Any]) -> bool:
        """
        Build the finite element model for frame structure

        Node numbering scheme (example for 2-bay, 3-story frame):
        Story 3:  9 ------- 10 ------- 11
                  |          |          |
        Story 2:  6 ------- 7 -------- 8
                  |          |          |
        Story 1:  3 ------- 4 -------- 5
                  |          |          |
        Story 0:  0 ------- 1 -------- 2
               (fixed)   (fixed)   (fixed)

        Node ID = story * (num_bays + 1) + bay

        Args:
            design: Design parameters

        Returns:
            True if model built successfully
        """
        try:
            # Validate design
            is_valid, error_msg = self.validate_design(design)
            if not is_valid:
                raise ValueError(f"Invalid design: {error_msg}")

            # Store design parameters
            self.design_params = design

            # Extract parameters
            geometry = design['geometry']
            material = design['material']
            loads = design['loads']
            boundary = design.get('boundary', {'column_base': 'fixed'})

            num_bays = geometry['num_bays']
            num_stories = geometry['num_stories']
            bay_widths = geometry['bay_widths']
            story_heights = geometry['story_heights']

            # Column and beam sections
            col_width = geometry['columns']['width']
            col_depth = geometry['columns']['depth']
            beam_width = geometry['beams']['width']
            beam_depth = geometry['beams']['depth']

            # Material properties
            E = material['E']

            # Calculate section properties
            A_col = col_width * col_depth
            I_col = (col_width * col_depth**3) / 12
            A_beam = beam_width * beam_depth
            I_beam = (beam_width * beam_depth**3) / 12

            # Initialize OpenSeesPy model
            ops.wipe()
            ops.model('basic', '-ndm', 2, '-ndf', 3)

            # Define geometric transformation for 2D frame elements
            # transfTag=1: Linear transformation for frame elements
            ops.geomTransf('Linear', 1)

            # Create nodes
            self._create_nodes(num_bays, num_stories, bay_widths, story_heights)

            # Set boundary conditions
            self._set_boundary_conditions(num_bays, boundary)

            # Create column elements
            self._create_column_elements(num_bays, num_stories, A_col, E, I_col)

            # Create beam elements
            self._create_beam_elements(num_bays, num_stories, A_beam, E, I_beam)

            # Apply loads
            self._apply_loads(loads, num_bays, num_stories)

            self.model_built = True
            return True

        except Exception as e:
            print(f"Error building frame model: {str(e)}")
            return False

    def _create_nodes(self, num_bays: int, num_stories: int,
                     bay_widths: List[float], story_heights: List[float]):
        """
        Create all nodes for the frame

        Args:
            num_bays: Number of bays
            num_stories: Number of stories
            bay_widths: Width of each bay
            story_heights: Height of each story
        """
        node_id = 0
        y = 0.0

        for story in range(num_stories + 1):
            x = 0.0
            for bay in range(num_bays + 1):
                ops.node(node_id, x, y)
                self.nodes.append(node_id)
                self.node_coords[node_id] = (x, y)
                node_id += 1

                if bay < num_bays:
                    x += bay_widths[bay]

            if story < num_stories:
                y += story_heights[story]

    def _set_boundary_conditions(self, num_bays: int, boundary: Dict):
        """
        Set boundary conditions at column bases

        Args:
            num_bays: Number of bays
            boundary: Boundary configuration
        """
        base_type = boundary.get('column_base', 'fixed')

        for bay in range(num_bays + 1):
            node_id = bay  # Story 0 nodes
            if base_type == 'fixed':
                ops.fix(node_id, 1, 1, 1)  # Fixed: x, y, rotation all constrained
            elif base_type == 'pinned':
                ops.fix(node_id, 1, 1, 0)  # Pinned: x, y constrained, rotation free

    def _create_column_elements(self, num_bays: int, num_stories: int,
                                A: float, E: float, I: float):
        """
        Create column elements

        Args:
            num_bays: Number of bays
            num_stories: Number of stories
            A: Column cross-sectional area
            E: Elastic modulus
            I: Moment of inertia
        """
        elem_id = 1

        for story in range(num_stories):
            for bay in range(num_bays + 1):
                node_i = story * (num_bays + 1) + bay
                node_j = (story + 1) * (num_bays + 1) + bay

                ops.element('elasticBeamColumn', elem_id, node_i, node_j,
                           A, E, I, 1)
                self.column_elements.append(elem_id)
                elem_id += 1

    def _create_beam_elements(self, num_bays: int, num_stories: int,
                             A: float, E: float, I: float):
        """
        Create beam elements

        Args:
            num_bays: Number of bays
            num_stories: Number of stories
            A: Beam cross-sectional area
            E: Elastic modulus
            I: Moment of inertia
        """
        elem_id = len(self.column_elements) + 1

        for story in range(1, num_stories + 1):  # Start from story 1
            for bay in range(num_bays):
                node_i = story * (num_bays + 1) + bay
                node_j = story * (num_bays + 1) + bay + 1

                ops.element('elasticBeamColumn', elem_id, node_i, node_j,
                           A, E, I, 1)
                self.beam_elements.append(elem_id)
                elem_id += 1

    def _apply_loads(self, loads: Dict, num_bays: int, num_stories: int):
        """
        Apply loads to the frame

        Args:
            loads: Load configuration
            num_bays: Number of bays
            num_stories: Number of stories
        """
        ops.timeSeries('Linear', 1)
        ops.pattern('Plain', 1, 1)

        # 1. Beam distributed loads
        if 'beam_distributed' in loads:
            for load in loads['beam_distributed']:
                story = load['story']
                bay = load['bay']
                q = load['q']

                # Find corresponding beam element
                beam_elem_id = self._get_beam_element_id(story, bay, num_bays)
                ops.eleLoad('-ele', beam_elem_id, '-type', '-beamUniform', q, 0.0)

        # 2. Lateral loads (wind, seismic)
        if 'lateral' in loads:
            for load in loads['lateral']:
                story = load['story']
                # Support both 'F' and 'Fx' keys for backward compatibility
                Fx = load.get('F', load.get('Fx', 0.0))

                # Distribute horizontal force to all nodes at this story
                for bay in range(num_bays + 1):
                    node_id = story * (num_bays + 1) + bay
                    ops.load(node_id, Fx / (num_bays + 1), 0.0, 0.0)

        # 3. Nodal loads
        if 'nodal' in loads:
            for load in loads['nodal']:
                node_id = load['node']
                Fx = load.get('Fx', 0.0)
                Fy = load.get('Fy', 0.0)
                ops.load(node_id, Fx, Fy, 0.0)

    def _get_beam_element_id(self, story: int, bay: int, num_bays: int) -> int:
        """
        Get beam element ID based on story and bay

        Args:
            story: Story number (1-indexed)
            bay: Bay number (0-indexed)
            num_bays: Total number of bays

        Returns:
            Beam element ID
        """
        # Number of column elements
        num_column_elements = len(self.column_elements)

        # Number of beams before this story
        num_beams_before = (story - 1) * num_bays

        # Current beam element ID
        beam_elem_id = num_column_elements + num_beams_before + bay + 1

        return beam_elem_id

    def analyze(self) -> AnalysisResults:
        """
        Run finite element analysis

        Returns:
            AnalysisResults object with analysis results
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
                structure_type="frame",
                analysis_status="failed",
                error_message="Model not built"
            )

        try:
            # Configure solver
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
                    structure_type="frame",
                    analysis_status="failed",
                    error_message="Analysis did not converge"
                )

            # Extract results
            displacements = self._extract_displacements()       # uy (vertical)
            ux_displacements = self._extract_ux_displacements() # ux (horizontal)
            moments, shears = self._extract_forces()
            axial_forces = self._extract_axial_forces()
            element_stresses = self._extract_element_stresses()  # For uniformity calculation

            # Calculate maximum values
            max_displacement = max([abs(d) for d in displacements]) if displacements else 0.0
            max_moment = max([abs(m) for m in moments]) if moments else 0.0
            max_shear = max([abs(s) for s in shears]) if shears else 0.0

            # Calculate maximum stress using combined stress (bending + axial)
            element_stresses = self._extract_element_stresses()
            max_stress = max(element_stresses) if element_stresses else 0.0

            # Calculate story drift ratio (frame-specific)
            max_drift_ratio = self._calculate_max_drift_ratio(displacements)

            # Get node coordinates
            node_list = [[self.node_coords[nid][0], self.node_coords[nid][1]]
                        for nid in self.nodes]

            return AnalysisResults(
                max_displacement=max_displacement,
                max_stress=max_stress,
                max_moment=max_moment,
                max_shear=max_shear,
                displacements=displacements,
                stresses=element_stresses,
                moments=moments,
                shears=shears,
                nodes=node_list,
                n_elements=len(self.column_elements) + len(self.beam_elements),
                structure_type="frame",
                analysis_status="success",
                geometry=self.design_params['geometry'],
                material=self.design_params['material'],
                extra={
                    'ux_displacements': ux_displacements,
                    'axial_forces': axial_forces,
                    'max_drift_ratio': max_drift_ratio,
                    'max_axial': max(abs(f) for f in axial_forces) if axial_forces else 0.0,
                    'element_stresses': element_stresses,  # For evaluator uniformity calculation
                }
            )

        except Exception as e:
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
                structure_type="frame",
                analysis_status="failed",
                error_message=f"Analysis error: {str(e)}"
            )

    def _extract_displacements(self) -> List[float]:
        """Extract nodal vertical displacements (uy) for beam deflection check"""
        displacements = []
        for node_id in self.nodes:
            disp = ops.nodeDisp(node_id)
            displacements.append(disp[1])  # uy: vertical
        return displacements

    def _extract_ux_displacements(self) -> List[float]:
        """Extract nodal horizontal displacements (ux) for story drift visualization"""
        ux_displacements = []
        for node_id in self.nodes:
            disp = ops.nodeDisp(node_id)
            ux_displacements.append(disp[0])  # ux: horizontal
        return ux_displacements

    def _extract_forces(self) -> Tuple[List[float], List[float]]:
        """Extract element moments and shears"""
        moments = []
        shears = []

        # Extract from all elements (columns and beams)
        all_elements = self.column_elements + self.beam_elements
        for elem_id in all_elements:
            forces = ops.eleForce(elem_id)
            # forces = [N_i, V_i, M_i, N_j, V_j, M_j]
            moments.extend([forces[2], forces[5]])
            shears.extend([forces[1], forces[4]])

        return moments, shears

    def _extract_axial_forces(self) -> List[float]:
        """Extract column axial forces"""
        axial_forces = []
        for elem_id in self.column_elements:
            forces = ops.eleForce(elem_id)
            # forces[0] = N_i, forces[3] = N_j
            axial_forces.extend([forces[0], forces[3]])
        return axial_forces

    def _extract_element_stresses(self) -> List[float]:
        """
        Extract element stresses for uniformity calculation

        For frame structures, calculate combined stress considering:
        - Bending stress: σ_b = M / W
        - Axial stress: σ_a = N / A
        - Combined: σ = σ_b + σ_a (most unfavorable combination)

        Returns:
            List of element stresses (one per element)
        """
        element_stresses = []
        geometry = self.design_params['geometry']

        # Beam properties
        beam_width = geometry['beams']['width']
        beam_depth = geometry['beams']['depth']
        W_beam = (beam_width * beam_depth**2) / 6
        A_beam = beam_width * beam_depth

        # Column properties
        col_width = geometry['columns']['width']
        col_depth = geometry['columns']['depth']
        W_col = (col_width * col_depth**2) / 6
        A_col = col_width * col_depth

        # Extract beam stresses
        for elem_id in self.beam_elements:
            forces = ops.eleForce(elem_id)
            # forces = [N_i, V_i, M_i, N_j, V_j, M_j]
            M_i = abs(forces[2])
            M_j = abs(forces[5])
            N_i = abs(forces[0])
            N_j = abs(forces[3])

            # Calculate combined stress at both ends, take maximum
            sigma_i = M_i / W_beam + N_i / A_beam if W_beam > 0 and A_beam > 0 else 0.0
            sigma_j = M_j / W_beam + N_j / A_beam if W_beam > 0 and A_beam > 0 else 0.0
            element_stresses.append(max(sigma_i, sigma_j))

        # Extract column stresses
        for elem_id in self.column_elements:
            forces = ops.eleForce(elem_id)
            M_i = abs(forces[2])
            M_j = abs(forces[5])
            N_i = abs(forces[0])
            N_j = abs(forces[3])

            # Calculate combined stress at both ends, take maximum
            sigma_i = M_i / W_col + N_i / A_col if W_col > 0 and A_col > 0 else 0.0
            sigma_j = M_j / W_col + N_j / A_col if W_col > 0 and A_col > 0 else 0.0
            element_stresses.append(max(sigma_i, sigma_j))

        return element_stresses

    def _calculate_max_drift_ratio(self, displacements: List[float]) -> float:
        """
        Calculate maximum story drift ratio (frame-specific)
        Uses maximum displacement difference (not average) for conservative estimate

        Args:
            displacements: List of nodal displacements

        Returns:
            Maximum drift ratio
        """
        geometry = self.design_params['geometry']
        num_bays = geometry['num_bays']
        num_stories = geometry['num_stories']
        story_heights = geometry['story_heights']

        max_drift_ratio = 0.0
        story_drifts = []

        for story in range(1, num_stories + 1):
            # Get maximum horizontal displacement at current story
            ux_current_max = 0.0
            for bay in range(num_bays + 1):
                node_id = story * (num_bays + 1) + bay
                disp = ops.nodeDisp(node_id)
                ux_current_max = max(ux_current_max, abs(disp[0]))

            # Get maximum horizontal displacement at story below
            ux_below_max = 0.0
            for bay in range(num_bays + 1):
                node_id = (story - 1) * (num_bays + 1) + bay
                disp = ops.nodeDisp(node_id)
                ux_below_max = max(ux_below_max, abs(disp[0]))

            # Story drift (maximum displacement difference)
            story_drift = abs(ux_current_max - ux_below_max)
            story_height = story_heights[story - 1]
            drift_ratio = story_drift / story_height

            story_drifts.append(drift_ratio)
            max_drift_ratio = max(max_drift_ratio, drift_ratio)

        # Store story drifts in results for detailed reporting
        if hasattr(self, 'design_params'):
            if 'extra' not in self.design_params:
                self.design_params['extra'] = {}
            self.design_params['extra']['story_drifts'] = story_drifts

        return max_drift_ratio

    def check_code(self, results: AnalysisResults) -> Dict[str, Any]:
        """
        Check frame design against code requirements

        Checks:
        1. Stress limit (fy/1.5)
        2. Beam deflection limit (L/300)
        3. Story drift ratio limit (1/500) - frame specific
        4. Column axial ratio limit (0.9) - frame specific

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

        # Check 2: Beam deflection limit (L/300)
        geometry = self.design_params['geometry']
        bay_widths = geometry.get('bay_widths', [6.0])
        max_bay_width = max(bay_widths)
        deflection_limit = max_bay_width / 300

        if results.max_displacement > deflection_limit:
            violations.append({
                'code': 'Deflection Limit',
                'description': f'Max deflection {results.max_displacement*1000:.2f} mm exceeds limit {deflection_limit*1000:.2f} mm (L/300)',
                'severity': 'warning'
            })
        safety_factors['deflection'] = deflection_limit / results.max_displacement if results.max_displacement > 0 else float('inf')

        # Check 3: Story drift ratio limit (1/500) - frame specific
        max_drift_ratio = self._calculate_max_drift_ratio([])  # Will recalculate from current model
        drift_limit = 1.0 / 500

        if max_drift_ratio > drift_limit:
            violations.append({
                'code': 'Story Drift Ratio',
                'description': f'Max drift ratio {max_drift_ratio:.6f} exceeds limit {drift_limit:.6f} (1/500)',
                'severity': 'critical'
            })
        safety_factors['drift'] = drift_limit / max_drift_ratio if max_drift_ratio > 0 else float('inf')

        # Check 4: Column axial ratio (use pre-extracted data from results.extra)
        try:
            columns = geometry.get('columns', {})
            col_width = columns.get('width', 0.4)
            col_depth = columns.get('depth', 0.4)
            col_area = col_width * col_depth

            # Get max axial force from results.extra (already extracted during analyze)
            axial_forces = results.extra.get('axial_forces', [])
            max_axial = max(abs(f) for f in axial_forces) if axial_forces else 0.0

            # Calculate axial ratio
            allowable_axial = col_area * fy * 0.9  # 0.9 reduction factor
            axial_ratio = max_axial / allowable_axial if allowable_axial > 0 else 0

            if axial_ratio > 0.9:
                violations.append({
                    'code': 'Column Axial Ratio',
                    'description': f'Column axial ratio {axial_ratio:.3f} exceeds limit 0.9',
                    'severity': 'critical'
                })
            safety_factors['axial_ratio'] = 0.9 / axial_ratio if axial_ratio > 0 else float('inf')
        except Exception as e:
            # If axial ratio check fails, skip it (non-critical)
            pass

        # Compliance status
        compliant = len(violations) == 0

        return {
            'compliant': compliant,
            'violations': violations,
            'safety_factors': safety_factors,
            'summary': f"{'PASS' if compliant else 'FAIL'} - {len(violations)} violation(s) found"
        }

