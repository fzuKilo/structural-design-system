"""
Truss analyzer using OpenSeesPy
Implements finite element analysis for truss structures
"""

import openseespy.opensees as ops
import numpy as np
from typing import Dict, Any, List, Optional
from .base_analyzer import StructureAnalyzer, AnalysisResults


class TrussAnalyzer(StructureAnalyzer):
    """
    Concrete analyzer for truss structures using OpenSeesPy

    Supports:
    - Planar trusses (2D)
    - Pin-jointed members (axial force only)
    - Various support conditions

    Key features:
    - Truss elements (axial force only, no bending)
    - Slenderness ratio checks for compression members
    - Deflection limit: L/250
    """

    def __init__(self):
        """Initialize truss analyzer"""
        super().__init__()
        self.model_built = False
        self.design_params = None
        self.member_lengths = {}  # Store member lengths for slenderness check

    def _get_structure_type(self) -> str:
        """Return structure type identifier"""
        return "truss"

    def validate_design(self, design: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate truss-specific design parameters

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
        required_geom = ['span', 'height', 'n_panels']
        for param in required_geom:
            if param not in geometry:
                return False, f"Missing geometry parameter: {param}"
            if geometry[param] <= 0:
                return False, f"Invalid geometry parameter {param}: must be positive"

        # Check material parameters
        material = design.get('material', {})
        required_mat = ['E', 'A']  # Truss needs cross-sectional area
        for param in required_mat:
            if param not in material:
                return False, f"Missing material parameter: {param}"
            if material[param] <= 0:
                return False, f"Invalid material parameter {param}: must be positive"

        # Check loads
        loads = design.get('loads', {})
        if 'nodal' not in loads:
            return False, "No loads specified (need 'nodal' loads for truss)"

        return True, None

    def build_model(self, design: Dict[str, Any]) -> bool:
        """
        Build OpenSeesPy finite element model for truss

        Args:
            design: Design parameters containing:
                - geometry: {span, height, n_panels, truss_type (optional)}
                - material: {E, A, fy (optional)}
                - loads: {nodal: [{node, Fx, Fy}]}
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
            span = geometry['span']
            height = geometry['height']
            n_panels = geometry['n_panels']
            truss_type = geometry.get('truss_type', 'pratt')  # Default: Pratt truss

            # Material
            E = material['E']
            A = material['A']

            # Initialize model
            ops.model('basic', '-ndm', 2, '-ndf', 2)  # 2D, 2 DOF per node (x, y)

            # Define material (uniaxial elastic material for truss)
            mat_tag = 1
            ops.uniaxialMaterial('Elastic', mat_tag, E)

            # Create nodes for Pratt truss
            # Bottom chord nodes
            panel_length = span / n_panels
            node_id = 1
            self.nodes = []

            # Bottom chord
            for i in range(n_panels + 1):
                x = i * panel_length
                y = 0.0
                ops.node(node_id, x, y)
                self.nodes.append([x, y])
                node_id += 1

            # Top chord
            for i in range(n_panels + 1):
                x = i * panel_length
                y = height
                ops.node(node_id, x, y)
                self.nodes.append([x, y])
                node_id += 1

            # Apply boundary conditions
            support_type = constraints.get('support_type', 'simply_supported')
            if support_type == 'simply_supported':
                # Left bottom: pinned (fixed x, y)
                ops.fix(1, 1, 1)
                # Right bottom: roller (free x, fixed y)
                ops.fix(n_panels + 1, 0, 1)
            elif support_type == 'both_pinned':
                # Both ends pinned
                ops.fix(1, 1, 1)
                ops.fix(n_panels + 1, 1, 1)

            # Create truss elements
            self.elements = []
            elem_id = 1

            # Bottom chord members
            for i in range(n_panels):
                i_node = i + 1
                j_node = i + 2
                ops.element('Truss', elem_id, i_node, j_node, A, mat_tag)
                length = panel_length
                self.member_lengths[elem_id] = length
                self.elements.append(elem_id)
                elem_id += 1

            # Top chord members
            for i in range(n_panels):
                i_node = (n_panels + 1) + i + 1
                j_node = (n_panels + 1) + i + 2
                ops.element('Truss', elem_id, i_node, j_node, A, mat_tag)
                length = panel_length
                self.member_lengths[elem_id] = length
                self.elements.append(elem_id)
                elem_id += 1

            # Vertical web members
            for i in range(n_panels + 1):
                i_node = i + 1  # Bottom chord
                j_node = (n_panels + 1) + i + 1  # Top chord
                ops.element('Truss', elem_id, i_node, j_node, A, mat_tag)
                length = height
                self.member_lengths[elem_id] = length
                self.elements.append(elem_id)
                elem_id += 1

            # Diagonal web members (Pratt truss pattern)
            if truss_type == 'pratt':
                for i in range(n_panels):
                    # Diagonal from bottom left to top right
                    i_node = i + 1  # Bottom left
                    j_node = (n_panels + 1) + i + 2  # Top right
                    ops.element('Truss', elem_id, i_node, j_node, A, mat_tag)
                    length = np.sqrt(panel_length**2 + height**2)
                    self.member_lengths[elem_id] = length
                    self.elements.append(elem_id)
                    elem_id += 1

            # Create time series and load pattern
            ops.timeSeries('Linear', 1)
            ops.pattern('Plain', 1, 1)

            # Apply nodal loads
            nodal_loads = loads.get('nodal', [])
            for load in nodal_loads:
                node = load['node']
                Fx = load.get('Fx', 0.0)
                Fy = load.get('Fy', 0.0)
                ops.load(node, Fx, Fy)

            self.model_built = True
            return True

        except Exception as e:
            print(f"Error building truss model: {str(e)}")
            return False

    def analyze(self) -> AnalysisResults:
        """
        Perform finite element analysis on truss

        Returns:
            AnalysisResults object containing all analysis results
        """
        if not self.model_built:
            return AnalysisResults(
                max_displacement=0.0,
                max_stress=0.0,
                max_moment=0.0,  # Trusses have no moment
                max_shear=0.0,  # Trusses have no shear
                displacements=[],
                stresses=[],
                moments=[],
                shears=[],
                nodes=self.nodes,
                n_elements=len(self.elements),
                structure_type=self.structure_type,
                analysis_status='failed',
                error_message='Model not built',
                geometry=self.design_params.get('geometry'),
                material=self.design_params.get('material')
            )

        try:
            # Configure analysis
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
                    n_elements=len(self.elements),
                    structure_type=self.structure_type,
                    analysis_status='failed',
                    error_message='Analysis convergence failed',
                    geometry=self.design_params.get('geometry'),
                    material=self.design_params.get('material')
                )

            # Extract results
            # Get nodal displacements
            displacements = []
            max_disp = 0.0
            for i, node_coords in enumerate(self.nodes):
                node_id = i + 1
                disp = ops.nodeDisp(node_id)
                ux = disp[0]
                uy = disp[1]
                total_disp = np.sqrt(ux**2 + uy**2)
                displacements.append(total_disp)
                max_disp = max(max_disp, total_disp)

            # Get element axial forces and stresses
            axial_forces = []  # Keep sign: positive=tension, negative=compression
            stresses = []
            max_stress = 0.0
            A = self.design_params['material']['A']

            for elem_id in self.elements:
                force = ops.eleForce(elem_id)
                # For truss element: [Fx_i, Fy_i, Fx_j, Fy_j]
                # Axial force is Fx_i (tension positive, compression negative)
                axial_force = force[0]  # Keep sign for tension/compression identification
                stress = abs(axial_force) / A
                axial_forces.append(axial_force)
                stresses.append(stress)
                max_stress = max(max_stress, stress)

            return AnalysisResults(
                max_displacement=max_disp,
                max_stress=max_stress,
                max_moment=0.0,  # Trusses have no bending moment
                max_shear=0.0,  # Trusses have no shear force
                displacements=displacements,
                stresses=stresses,
                moments=[0.0] * len(self.elements),  # No moments in truss
                shears=[0.0] * len(self.elements),  # No shears in truss
                nodes=self.nodes,
                n_elements=len(self.elements),
                structure_type=self.structure_type,
                analysis_status='success',
                error_message=None,
                geometry=self.design_params.get('geometry'),
                material=self.design_params.get('material'),
                extra={
                    'axial_forces': axial_forces,  # Signed axial forces for evaluator
                    'member_lengths': list(self.member_lengths.values())  # For slenderness check
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
                nodes=self.nodes,
                n_elements=len(self.elements),
                structure_type=self.structure_type,
                analysis_status='failed',
                error_message=f'Analysis error: {str(e)}',
                geometry=self.design_params.get('geometry'),
                material=self.design_params.get('material')
            )

    def check_code(self, results: AnalysisResults) -> Dict[str, Any]:
        """
        Check truss design against code requirements

        Checks:
        1. Deflection limit: L/250
        2. Stress limit: fy (yield strength)
        3. Slenderness ratio for compression members: λ ≤ 150 (compression), λ ≤ 350 (tension)

        Args:
            results: Analysis results from analyze()

        Returns:
            Dictionary containing compliance status and safety factors
        """
        violations = []
        safety_factors = {}

        # Extract parameters
        geometry = self.design_params['geometry']
        material = self.design_params['material']
        span = geometry['span']
        A = material['A']
        fy = material.get('fy', 235e6)  # Default: Q235 steel (235 MPa)

        # 1. Deflection check (L/250)
        max_disp = results.max_displacement
        deflection_limit = span / 250
        deflection_ratio = max_disp / deflection_limit if deflection_limit > 0 else 0

        if max_disp > deflection_limit:
            violations.append({
                'type': 'deflection',
                'message': f'Deflection exceeds limit: {max_disp*1000:.2f}mm > {deflection_limit*1000:.2f}mm',
                'severity': 'high'
            })

        safety_factors['deflection'] = deflection_limit / max_disp if max_disp > 0 else float('inf')

        # 2. Stress check
        max_stress = results.max_stress
        stress_ratio = max_stress / fy if fy > 0 else 0

        if max_stress > fy:
            violations.append({
                'type': 'stress',
                'message': f'Stress exceeds yield strength: {max_stress/1e6:.2f}MPa > {fy/1e6:.2f}MPa',
                'severity': 'critical'
            })

        safety_factors['stress'] = fy / max_stress if max_stress > 0 else float('inf')

        # 3. Slenderness ratio check
        # λ = L / r, where r is radius of gyration
        # Priority: use user-provided r, else calculate from section shape
        material = self.design_params['material']

        # Check if user provided radius of gyration
        if 'r' in material:
            r = material['r']
        else:
            # Estimate based on section shape
            # For rectangular: r = depth / sqrt(12)
            # For circular: r = sqrt(A / π) / 2
            # Default to rectangular assumption if depth provided
            if 'depth' in material:
                r = material['depth'] / np.sqrt(12)
            else:
                # Fallback to circular approximation
                r = np.sqrt(A / np.pi) / 2

        max_slenderness = 0
        for elem_id, length in self.member_lengths.items():
            slenderness = length / r if r > 0 else 0
            max_slenderness = max(max_slenderness, slenderness)

            # Check compression member limit (λ ≤ 150)
            if slenderness > 150:
                violations.append({
                    'type': 'slenderness',
                    'message': f'Member {elem_id} slenderness ratio too high: λ={slenderness:.1f} > 150',
                    'severity': 'moderate'
                })

        safety_factors['slenderness'] = 150 / max_slenderness if max_slenderness > 0 else float('inf')

        return {
            'compliant': len(violations) == 0,
            'violations': violations,
            'safety_factors': safety_factors,
            'checks': {
                'deflection_ratio': round(deflection_ratio, 4),
                'stress_ratio': round(stress_ratio, 4),
                'max_slenderness': round(max_slenderness, 1)
            }
        }


    def _validate_structure_specific(self, design: Dict[str, Any]) -> None:
        """桁架特定验证"""
        import openseespy.opensees as ops
        
        nodes = ops.getNodeTags()
        elements = ops.getEleTags()
        
        # 检查节点连通性
        assert len(elements) >= len(nodes) - 3, "桁架单元数不足，可能存在孤立节点"

    def export_opensees_script(self, design: Dict[str, Any], output_path: str) -> str:
        """生成桁架OpenSees Tcl脚本"""
        from datetime import datetime
        
        geo = design['geometry']
        mat = design['material']
        
        script = f"""# OpenSees Tcl Script - 桁架
# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

wipe
model BasicBuilder -ndm 2 -ndf 2

set span {geo['span']}
set height {geo['height']}
set nPanels {geo['n_panels']}
set A {geo['bar_area']}
set E {mat['E']}

# 简化桁架模型（需根据实际几何生成）
puts "桁架脚本生成 - 需要完整几何信息"
"""
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(script)
        
        return output_path
