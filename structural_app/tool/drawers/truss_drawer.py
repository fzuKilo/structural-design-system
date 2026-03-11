"""
Truss drawer using ezdxf
Implements CAD drawing generation for truss structures
"""

import ezdxf
from ezdxf import colors
from ezdxf.enums import TextEntityAlignment
import numpy as np
from typing import Dict, Any, Optional
from datetime import datetime
from .base_drawer import StructureDrawer


class TrussDrawer(StructureDrawer):
    """
    Concrete drawer for truss structures using ezdxf

    Generates:
    - Elevation view (side view showing truss geometry)
    - Plan view (top view, optional)
    - Detail views (node details, member connections)

    Drawing conventions:
    - Top chord: solid line
    - Bottom chord: solid line
    - Web members: solid line
    - Compression members: thicker line
    - Tension members: normal line
    - Supports: standard symbols (pinned, roller)
    """

    def __init__(self):
        """Initialize truss drawer"""
        super().__init__()

    def _get_structure_type(self) -> str:
        """Return structure type identifier"""
        return "truss"

    def draw_plan(self, design: Dict[str, Any]) -> Optional[str]:
        """
        Draw plan view (top view) of truss

        For planar trusses, plan view is optional
        Shows the width of the truss if 3D

        Args:
            design: Design parameters

        Returns:
            Path to DXF file or None
        """
        # For 2D planar truss, plan view is not typically needed
        # Return None to skip
        return None

    def draw_elevation(self, design: Dict[str, Any]) -> Optional[str]:
        """
        Draw elevation view (side view) of truss

        Shows:
        - Top chord
        - Bottom chord
        - Web members (verticals and diagonals)
        - Support symbols
        - Member labels
        - Dimensions

        Args:
            design: Design parameters

        Returns:
            Path to generated DXF file
        """
        try:
            # Create new DXF document
            doc = ezdxf.new('R2010')
            msp = doc.modelspace()

            # Extract parameters (support both 'span'/'length' for compatibility)
            geometry = design.get('geometry', {})
            span = geometry.get('span') or geometry.get('length', 10.0)
            height = geometry.get('height', 2.0)
            n_panels = geometry.get('n_panels') or geometry.get('n_elements', 5)
            truss_type = geometry.get('truss_type', 'pratt')

            panel_length = span / n_panels

            # Calculate node positions
            # Bottom chord nodes
            bottom_nodes = []
            for i in range(n_panels + 1):
                x = i * panel_length
                y = 0.0
                bottom_nodes.append((x, y))

            # Top chord nodes
            top_nodes = []
            for i in range(n_panels + 1):
                x = i * panel_length
                y = height
                top_nodes.append((x, y))

            # Draw bottom chord
            for i in range(n_panels):
                start = bottom_nodes[i]
                end = bottom_nodes[i + 1]
                msp.add_line(start, end, dxfattribs={'color': colors.BLACK, 'lineweight': 35})

            # Draw top chord
            for i in range(n_panels):
                start = top_nodes[i]
                end = top_nodes[i + 1]
                msp.add_line(start, end, dxfattribs={'color': colors.BLACK, 'lineweight': 35})

            # Draw vertical web members
            for i in range(n_panels + 1):
                start = bottom_nodes[i]
                end = top_nodes[i]
                msp.add_line(start, end, dxfattribs={'color': colors.BLUE, 'lineweight': 25})

            # Draw diagonal web members (Pratt truss pattern)
            if truss_type == 'pratt':
                for i in range(n_panels):
                    # Diagonal from bottom left to top right
                    start = bottom_nodes[i]
                    end = top_nodes[i + 1]
                    msp.add_line(start, end, dxfattribs={'color': colors.RED, 'lineweight': 25})

            # Draw support symbols
            self._draw_pinned_support(msp, bottom_nodes[0][0], bottom_nodes[0][1])
            self._draw_roller_support(msp, bottom_nodes[-1][0], bottom_nodes[-1][1])

            # Add dimensions
            # Span dimension
            y_dim = -0.8
            msp.add_text(
                f'Span = {span:.1f}m',
                dxfattribs={
                    'height': 0.15,
                    'color': colors.BLACK
                }
            ).set_placement((span / 2, y_dim), align=TextEntityAlignment.CENTER)

            # Height dimension
            x_dim = -0.8
            msp.add_text(
                f'H = {height:.1f}m',
                dxfattribs={
                    'height': 0.15,
                    'color': colors.BLACK,
                    'rotation': 90
                }
            ).set_placement((x_dim, height / 2), align=TextEntityAlignment.CENTER)

            # Add title block
            self._add_title_block(msp, design, span, height)

            # Add node labels
            for i, node in enumerate(bottom_nodes):
                msp.add_circle(node, radius=0.08, dxfattribs={'color': colors.BLACK})
                msp.add_text(
                    f'N{i+1}',
                    dxfattribs={'height': 0.12, 'color': colors.BLUE}
                ).set_placement((node[0], node[1] - 0.3), align=TextEntityAlignment.CENTER)

            for i, node in enumerate(top_nodes):
                msp.add_circle(node, radius=0.08, dxfattribs={'color': colors.BLACK})
                msp.add_text(
                    f'N{n_panels+2+i}',
                    dxfattribs={'height': 0.12, 'color': colors.BLUE}
                ).set_placement((node[0], node[1] + 0.3), align=TextEntityAlignment.CENTER)

            # Save file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = self.output_dir / f"truss_elevation_{timestamp}.dxf"
            doc.saveas(filename)

            return str(filename)

        except Exception as e:
            print(f"Error drawing truss elevation: {str(e)}")
            return None

    def draw_details(self, design: Dict[str, Any]) -> Optional[str]:
        """
        Draw detail views (node connections, member details)

        Args:
            design: Design parameters

        Returns:
            Path to DXF file or None
        """
        try:
            # Create new DXF document
            doc = ezdxf.new('R2010')
            msp = doc.modelspace()

            # Extract parameters
            material = design.get('material', {})
            A = material.get('A', 0.01)  # Cross-sectional area in m²

            # Convert to mm² for display
            A_mm2 = A * 1e6

            # Draw typical member cross-section detail
            # Assume circular hollow section
            diameter = np.sqrt(4 * A / np.pi) * 1000  # Convert to mm

            # Detail 1: Typical member section
            center_x = 2.0
            center_y = 2.0
            msp.add_circle((center_x, center_y), radius=diameter/2000, dxfattribs={'color': colors.BLACK})

            # Add dimension
            msp.add_text(
                f'Typical Member',
                dxfattribs={'height': 0.15, 'color': colors.BLACK}
            ).set_placement((center_x, center_y + 0.5), align=TextEntityAlignment.CENTER)

            msp.add_text(
                f'Area = {A_mm2:.0f} mm²',
                dxfattribs={'height': 0.12, 'color': colors.BLACK}
            ).set_placement((center_x, center_y - 0.5), align=TextEntityAlignment.CENTER)

            msp.add_text(
                f'Ø = {diameter:.1f} mm',
                dxfattribs={'height': 0.12, 'color': colors.BLACK}
            ).set_placement((center_x, center_y - 0.7), align=TextEntityAlignment.CENTER)

            # Detail 2: Node connection detail (simplified)
            node_x = 5.0
            node_y = 2.0

            # Draw gusset plate (simplified)
            gusset_points = [
                (node_x - 0.3, node_y - 0.3),
                (node_x + 0.3, node_y - 0.3),
                (node_x + 0.3, node_y + 0.3),
                (node_x - 0.3, node_y + 0.3),
                (node_x - 0.3, node_y - 0.3)
            ]
            msp.add_lwpolyline(gusset_points, dxfattribs={'color': colors.YELLOW})

            # Draw members connecting to node
            msp.add_line((node_x - 0.5, node_y), (node_x - 0.3, node_y), dxfattribs={'color': colors.BLACK, 'lineweight': 25})
            msp.add_line((node_x + 0.3, node_y), (node_x + 0.5, node_y), dxfattribs={'color': colors.BLACK, 'lineweight': 25})
            msp.add_line((node_x, node_y - 0.3), (node_x, node_y - 0.5), dxfattribs={'color': colors.BLACK, 'lineweight': 25})

            msp.add_text(
                'Typical Node Connection',
                dxfattribs={'height': 0.15, 'color': colors.BLACK}
            ).set_placement((node_x, node_y + 0.5), align=TextEntityAlignment.CENTER)

            msp.add_text(
                'Gusset Plate',
                dxfattribs={'height': 0.10, 'color': colors.BLACK}
            ).set_placement((node_x, node_y - 0.7), align=TextEntityAlignment.CENTER)

            # Save file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = self.output_dir / f"truss_details_{timestamp}.dxf"
            doc.saveas(filename)

            return str(filename)

        except Exception as e:
            print(f"Error drawing truss details: {str(e)}")
            return None

    def _draw_pinned_support(self, msp, x: float, y: float):
        """
        Draw pinned support symbol

        Args:
            msp: Model space
            x, y: Support location
        """
        # Draw triangle
        size = 0.3
        points = [
            (x, y),
            (x - size/2, y - size),
            (x + size/2, y - size),
            (x, y)
        ]
        msp.add_lwpolyline(points, dxfattribs={'color': colors.BLACK})

        # Draw hatch lines
        for i in range(5):
            x_offset = -size/2 + i * size/4
            msp.add_line(
                (x + x_offset, y - size),
                (x + x_offset - 0.1, y - size - 0.15),
                dxfattribs={'color': colors.BLACK}
            )

    def _draw_roller_support(self, msp, x: float, y: float):
        """
        Draw roller support symbol

        Args:
            msp: Model space
            x, y: Support location
        """
        # Draw triangle
        size = 0.3
        points = [
            (x, y),
            (x - size/2, y - size),
            (x + size/2, y - size),
            (x, y)
        ]
        msp.add_lwpolyline(points, dxfattribs={'color': colors.BLACK})

        # Draw rollers (circles)
        roller_radius = 0.08
        msp.add_circle((x - size/4, y - size - roller_radius), radius=roller_radius, dxfattribs={'color': colors.BLACK})
        msp.add_circle((x + size/4, y - size - roller_radius), radius=roller_radius, dxfattribs={'color': colors.BLACK})

        # Draw base line
        msp.add_line(
            (x - size/2, y - size - 2*roller_radius),
            (x + size/2, y - size - 2*roller_radius),
            dxfattribs={'color': colors.BLACK}
        )

    def _add_title_block(self, msp, design: Dict, span: float, height: float):
        """
        Add title block to drawing

        Args:
            msp: Model space
            design: Design parameters
            span: Truss span
            height: Truss height
        """
        # Title block position (bottom right)
        x_title = span - 3.0
        y_title = -2.0

        # Draw title block border
        msp.add_line((x_title, y_title), (x_title + 2.5, y_title), dxfattribs={'color': colors.BLACK})
        msp.add_line((x_title + 2.5, y_title), (x_title + 2.5, y_title + 1.0), dxfattribs={'color': colors.BLACK})
        msp.add_line((x_title + 2.5, y_title + 1.0), (x_title, y_title + 1.0), dxfattribs={'color': colors.BLACK})
        msp.add_line((x_title, y_title + 1.0), (x_title, y_title), dxfattribs={'color': colors.BLACK})

        # Add title text
        msp.add_text(
            'TRUSS STRUCTURE',
            dxfattribs={'height': 0.15, 'color': colors.BLACK}
        ).set_placement((x_title + 1.25, y_title + 0.75), align=TextEntityAlignment.CENTER)

        # Add design info
        geometry = design.get('geometry', {})
        n_panels = geometry.get('n_panels', 5)

        msp.add_text(
            f'Span: {span:.1f}m',
            dxfattribs={'height': 0.10, 'color': colors.BLACK}
        ).set_placement((x_title + 0.1, y_title + 0.50), align=TextEntityAlignment.LEFT)

        msp.add_text(
            f'Height: {height:.1f}m',
            dxfattribs={'height': 0.10, 'color': colors.BLACK}
        ).set_placement((x_title + 0.1, y_title + 0.35), align=TextEntityAlignment.LEFT)

        msp.add_text(
            f'Panels: {n_panels}',
            dxfattribs={'height': 0.10, 'color': colors.BLACK}
        ).set_placement((x_title + 0.1, y_title + 0.20), align=TextEntityAlignment.LEFT)

        # Add date
        date_str = datetime.now().strftime("%Y-%m-%d")
        msp.add_text(
            f'Date: {date_str}',
            dxfattribs={'height': 0.08, 'color': colors.BLACK}
        ).set_placement((x_title + 0.1, y_title + 0.05), align=TextEntityAlignment.LEFT)

    def _generate_notes(self, design: Dict[str, Any]) -> list:
        """
        Generate truss-specific notes for the drawings

        Args:
            design: Design parameters

        Returns:
            List of note strings
        """
        notes = [
            f"Generated by OpenManus Structure Designer",
            f"Design standard: {self.drawing_standard}",
            f"Scale: {self.scale}",
            f"Units: {self.units}",
        ]

        # Add truss-specific notes
        geometry = design.get('geometry', {})
        if 'span' in geometry:
            notes.append(f"Span: {geometry['span']} m")
        if 'height' in geometry:
            notes.append(f"Height: {geometry['height']} m")
        if 'n_panels' in geometry:
            notes.append(f"Number of panels: {geometry['n_panels']}")

        material = design.get('material', {})
        if 'material_name' in material:
            notes.append(f"Material: {material['material_name']}")

        return notes
