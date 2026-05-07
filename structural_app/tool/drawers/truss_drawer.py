"""
Truss drawer using ezdxf
Implements CAD drawing generation for truss structures
"""

import os
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

    def _setup_chinese_style(self, doc):
        """配置中文字体样式 CHINESE"""
        try:
            doc.styles.new(
                name='CHINESE',
                dxfattribs={'font': 'simhei.ttf'}
            )
        except Exception:
            try:
                doc.styles.new(
                    name='CHINESE',
                    dxfattribs={'font': 'simsun.ttc'}
                )
            except Exception:
                doc.styles.new(
                    name='CHINESE',
                    dxfattribs={'font': 'Arial.ttf'}
                )

    def _setup_dimstyle(self, doc):
        """配置 MM_UNITS 标注样式（坐标系为米，dimlfac=1.0）"""
        if 'STANDARD' not in doc.styles:
            doc.styles.new('STANDARD', dxfattribs={'font': 'txt.shx'})

        try:
            dimstyle = doc.dimstyles.get('EZDXF')
            if dimstyle:
                dimstyle.dxf.dimlfac = 1.0
                dimstyle.dxf.dimtxsty = 'STANDARD'
        except Exception:
            pass

        if 'TRUSS_DIM' not in doc.dimstyles:
            dimstyle = doc.dimstyles.new('TRUSS_DIM')
            dimstyle.dxf.dimtxt = 0.15
            dimstyle.dxf.dimasz = 0.1
            dimstyle.dxf.dimcen = 0
            dimstyle.dxf.dimtsz = 0
            dimstyle.dxf.dimaltf = 1.0
            dimstyle.dxf.dimlfac = 1.0
            dimstyle.dxf.dimtp = 0
            dimstyle.dxf.dimtm = 0
            dimstyle.dxf.dimtol = 0
            dimstyle.dxf.dimlim = 0
            dimstyle.dxf.dimclrt = colors.WHITE
            dimstyle.dxf.dimtxsty = 'STANDARD'

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
            doc = ezdxf.new('R2010', setup=True)
            msp = doc.modelspace()

            # Setup styles
            self._setup_chinese_style(doc)
            self._setup_dimstyle(doc)

            # Extract parameters (support both 'span'/'length' for compatibility)
            geometry = design.get('geometry', {})
            material = design.get('material', {})
            material_name = material.get('material_name', 'Q235')

            # Get span with fallback to length, ensure numeric type
            span = geometry.get('span')
            if not isinstance(span, (int, float)) or span is None:
                span = geometry.get('length')
            if not isinstance(span, (int, float)) or span is None:
                span = 10.0
            span = float(span)

            # Get height, ensure numeric type
            height = geometry.get('height')
            if not isinstance(height, (int, float)) or height is None:
                height = 2.0
            height = float(height)

            # Get n_panels (do NOT use n_elements as fallback - they are different!)
            # n_panels = number of panel divisions (节间数)
            # n_elements = total number of structural elements (单元总数)
            n_panels = geometry.get('n_panels')
            if not isinstance(n_panels, (int, float)) or n_panels is None:
                # Default to 5 panels if not specified
                n_panels = 5
            n_panels = int(n_panels)

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
                msp.add_line(start, end, dxfattribs={'color': colors.WHITE, 'lineweight': 35})

            # Draw top chord
            for i in range(n_panels):
                start = top_nodes[i]
                end = top_nodes[i + 1]
                msp.add_line(start, end, dxfattribs={'color': colors.WHITE, 'lineweight': 35})

            # Draw vertical web members
            for i in range(n_panels + 1):
                start = bottom_nodes[i]
                end = top_nodes[i]
                msp.add_line(start, end, dxfattribs={'color': colors.WHITE, 'lineweight': 25})

            # Draw diagonal web members (交替方向的V字形斜杆)
            if truss_type == 'pratt':
                for i in range(n_panels):
                    if i % 2 == 0:
                        # 偶数：从下左到上右
                        start = bottom_nodes[i]
                        end = top_nodes[i + 1]
                    else:
                        # 奇数：从上左到下右
                        start = top_nodes[i]
                        end = bottom_nodes[i + 1]
                    msp.add_line(start, end, dxfattribs={'color': colors.WHITE, 'lineweight': 25})

            # Draw support symbols
            self._draw_pinned_support(msp, bottom_nodes[0][0], bottom_nodes[0][1])
            self._draw_roller_support(msp, bottom_nodes[-1][0], bottom_nodes[-1][1])

            # Add dimensions (native DXF DIMENSION entities)
            try:
                # Span dimension
                dim = msp.add_linear_dim(
                    base=(span / 2, -0.8),
                    p1=(0, 0),
                    p2=(span, 0),
                    dimstyle='TRUSS_DIM',
                    override={'dimtxt': 0.15, 'dimclrt': colors.WHITE, 'dimpost': '<>m'}
                )
                dim.render()

                # Height dimension
                dim = msp.add_linear_dim(
                    base=(-0.8, height / 2),
                    p1=(0, 0),
                    p2=(0, height),
                    angle=90,
                    dimstyle='TRUSS_DIM',
                    override={'dimtxt': 0.15, 'dimclrt': colors.WHITE, 'dimpost': '<>m'}
                )
                dim.render()
            except Exception as e:
                print(f"Warning: Could not add dimensions: {e}")

            # Add title block
            self._add_title_block(msp, design, span, height, material_name)

            # Add node labels
            for i, node in enumerate(bottom_nodes):
                msp.add_circle(node, radius=0.08, dxfattribs={'color': colors.WHITE})
                msp.add_text(
                    f'N{i+1}',
                    dxfattribs={'height': 0.12, 'color': colors.WHITE, 'style': 'CHINESE'}
                ).set_placement((node[0], node[1] - 0.3), align=TextEntityAlignment.CENTER)

            for i, node in enumerate(top_nodes):
                msp.add_circle(node, radius=0.08, dxfattribs={'color': colors.WHITE})
                msp.add_text(
                    f'N{n_panels+2+i}',
                    dxfattribs={'height': 0.12, 'color': colors.WHITE, 'style': 'CHINESE'}
                ).set_placement((node[0], node[1] + 0.3), align=TextEntityAlignment.CENTER)

            # Save file
            os.makedirs(self.output_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(self.output_dir, f"truss_elevation_{timestamp}.dxf")
            doc.saveas(filename)

            return str(filename)

        except Exception as e:
            print(f"Error drawing truss elevation: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    def draw_details(self, design: Dict[str, Any]) -> Optional[str]:
        """
        Draw detail views (node connections, member details)

        Layout (2 rows × 3 columns):
        Row 1: 上弦杆 | 下弦杆 | 竖杆
        Row 2: 斜杆   | 节点   | 材料表

        Args:
            design: Design parameters

        Returns:
            Path to DXF file or None
        """
        try:
            # Create new DXF document
            doc = ezdxf.new('R2010')
            doc.styles.new('chinese', dxfattribs={'font': 'simsun.ttf'})
            msp = doc.modelspace()

            # Extract parameters
            material = design.get('material', {})
            geometry = design.get('geometry', {})
            A = material.get('A', 0.01)  # Cross-sectional area in m²（所有杆件统一截面积）
            A_mm2 = A * 1e6
            diameter = np.sqrt(4 * A / np.pi) * 1000  # Convert to mm

            # Layout positions (2 rows × 3 columns)
            row1_y = 5.0
            row2_y = 2.0
            col_spacing = 3.5
            col1_x = 2.0
            col2_x = col1_x + col_spacing
            col3_x = col2_x + col_spacing

            # Row 1, Col 1: 上弦杆截面
            self._draw_member_section(msp, col1_x, row1_y, '上弦杆', diameter, A_mm2)

            # Row 1, Col 2: 下弦杆截面
            self._draw_member_section(msp, col2_x, row1_y, '下弦杆', diameter, A_mm2)

            # Row 1, Col 3: 竖杆截面
            self._draw_member_section(msp, col3_x, row1_y, '竖杆', diameter, A_mm2)

            # Row 2, Col 1: 斜杆截面
            self._draw_member_section(msp, col1_x, row2_y, '斜杆', diameter, A_mm2)

            # Row 2, Col 2: 节点连接详图
            self._draw_node_detail(msp, col2_x, row2_y)

            # Row 2, Col 3: 材料表
            self._draw_material_table(msp, col3_x, row2_y, design, diameter, A_mm2)

            # Add title
            msp.add_text(
                '桁架杆件详图',
                dxfattribs={'height': 0.25, 'color': colors.BLACK, 'style': 'chinese'}
            ).set_placement((col2_x, 7.0), align=TextEntityAlignment.CENTER)

            # Save file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(self.output_dir, f"truss_details_{timestamp}.dxf")
            doc.saveas(filename)

            return str(filename)

        except Exception as e:
            print(f"Error drawing truss details: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    def _draw_member_section(self, msp, center_x: float, center_y: float,
                            member_name: str, diameter: float, area_mm2: float):
        """
        Draw a single member cross-section detail

        Args:
            msp: Model space
            center_x, center_y: Center position
            member_name: Member name (e.g., '上弦杆')
            diameter: Diameter in mm
            area_mm2: Area in mm²
        """
        # Draw circle (section)
        radius_m = diameter / 2000  # Convert mm to m for drawing
        msp.add_circle((center_x, center_y), radius=radius_m, dxfattribs={'color': colors.BLACK, 'lineweight': 25})

        # Title
        msp.add_text(
            member_name,
            dxfattribs={'height': 0.15, 'color': colors.BLACK, 'style': 'chinese'}
        ).set_placement((center_x, center_y + 0.6), align=TextEntityAlignment.CENTER)

        # Diameter
        msp.add_text(
            f'Ø{diameter:.1f}',
            dxfattribs={'height': 0.12, 'color': colors.BLACK, 'style': 'chinese'}
        ).set_placement((center_x, center_y - 0.4), align=TextEntityAlignment.CENTER)

        # Area
        msp.add_text(
            f'A={area_mm2:.0f}mm²',
            dxfattribs={'height': 0.10, 'color': colors.BLACK, 'style': 'chinese'}
        ).set_placement((center_x, center_y - 0.6), align=TextEntityAlignment.CENTER)

    def _draw_node_detail(self, msp, center_x: float, center_y: float):
        """
        Draw node connection detail

        Args:
            msp: Model space
            center_x, center_y: Center position
        """
        # Draw gusset plate
        gusset_points = [
            (center_x - 0.3, center_y - 0.3),
            (center_x + 0.3, center_y - 0.3),
            (center_x + 0.3, center_y + 0.3),
            (center_x - 0.3, center_y + 0.3),
            (center_x - 0.3, center_y - 0.3)
        ]
        msp.add_lwpolyline(gusset_points, dxfattribs={'color': colors.YELLOW})

        # Draw members
        msp.add_line((center_x - 0.5, center_y), (center_x - 0.3, center_y),
                    dxfattribs={'color': colors.BLACK, 'lineweight': 25})
        msp.add_line((center_x + 0.3, center_y), (center_x + 0.5, center_y),
                    dxfattribs={'color': colors.BLACK, 'lineweight': 25})
        msp.add_line((center_x, center_y - 0.3), (center_x, center_y - 0.5),
                    dxfattribs={'color': colors.BLACK, 'lineweight': 25})

        # Title
        msp.add_text(
            '节点连接',
            dxfattribs={'height': 0.15, 'color': colors.BLACK, 'style': 'chinese'}
        ).set_placement((center_x, center_y + 0.6), align=TextEntityAlignment.CENTER)

        # Label
        msp.add_text(
            '节点板',
            dxfattribs={'height': 0.10, 'color': colors.BLACK, 'style': 'chinese'}
        ).set_placement((center_x, center_y - 0.6), align=TextEntityAlignment.CENTER)

    def _draw_material_table(self, msp, center_x: float, center_y: float,
                            design: Dict[str, Any], diameter: float, area: float):
        """
        Draw material specification table

        Args:
            msp: Model space
            center_x, center_y: Center position
            design: Design parameters
            diameter: Member diameter in mm（所有杆件统一）
            area: Member area in mm²（所有杆件统一）
        """
        # Table border
        width = 1.2
        height = 1.2
        x0 = center_x - width/2
        y0 = center_y - height/2

        # Draw border
        border_points = [
            (x0, y0),
            (x0 + width, y0),
            (x0 + width, y0 + height),
            (x0, y0 + height),
            (x0, y0)
        ]
        msp.add_lwpolyline(border_points, dxfattribs={'color': colors.BLACK})

        # Title
        msp.add_text(
            '材料规格',
            dxfattribs={'height': 0.12, 'color': colors.BLACK, 'style': 'chinese'}
        ).set_placement((center_x, y0 + height - 0.15), align=TextEntityAlignment.CENTER)

        # Content
        geometry = design.get('geometry', {})
        material = design.get('material', {})
        n_panels = geometry.get('n_panels', 5)
        span = geometry.get('span', 10.0)
        material_name = material.get('material_name', 'Q235')

        y_line = y0 + height - 0.35
        line_height = 0.15

        # All members (unified section)
        msp.add_text(
            f'杆件: Ø{diameter:.0f}',
            dxfattribs={'height': 0.09, 'color': colors.BLACK, 'style': 'chinese'}
        ).set_placement((x0 + 0.1, y_line), align=TextEntityAlignment.LEFT)
        y_line -= line_height

        # Material
        msp.add_text(
            f'材料: {material_name}',
            dxfattribs={'height': 0.09, 'color': colors.BLACK, 'style': 'chinese'}
        ).set_placement((x0 + 0.1, y_line), align=TextEntityAlignment.LEFT)
        y_line -= line_height

        # Span
        msp.add_text(
            f'跨度: {span:.1f}m',
            dxfattribs={'height': 0.09, 'color': colors.BLACK, 'style': 'chinese'}
        ).set_placement((x0 + 0.1, y_line), align=TextEntityAlignment.LEFT)

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
        msp.add_lwpolyline(points, dxfattribs={'color': colors.WHITE})

        # Draw hatch lines
        for i in range(5):
            x_offset = -size/2 + i * size/4
            msp.add_line(
                (x + x_offset, y - size),
                (x + x_offset - 0.1, y - size - 0.15),
                dxfattribs={'color': colors.WHITE}
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
        msp.add_lwpolyline(points, dxfattribs={'color': colors.WHITE})

        # Draw rollers (circles)
        roller_radius = 0.08
        msp.add_circle((x - size/4, y - size - roller_radius), radius=roller_radius, dxfattribs={'color': colors.WHITE})
        msp.add_circle((x + size/4, y - size - roller_radius), radius=roller_radius, dxfattribs={'color': colors.WHITE})

        # Draw base line
        msp.add_line(
            (x - size/2, y - size - 2*roller_radius),
            (x + size/2, y - size - 2*roller_radius),
            dxfattribs={'color': colors.WHITE}
        )

    def _add_title_block(self, msp, design: Dict, span: float, height: float, material_name: str = 'Q235'):
        """
        Add title block to drawing

        Args:
            msp: Model space
            design: Design parameters
            span: Truss span
            height: Truss height
            material_name: Material name
        """
        # Title block position (bottom right)
        x_title = span - 3.0
        y_title = -2.0

        # Draw title block border
        msp.add_line((x_title, y_title), (x_title + 2.5, y_title), dxfattribs={'color': colors.WHITE})
        msp.add_line((x_title + 2.5, y_title), (x_title + 2.5, y_title + 1.0), dxfattribs={'color': colors.WHITE})
        msp.add_line((x_title + 2.5, y_title + 1.0), (x_title, y_title + 1.0), dxfattribs={'color': colors.WHITE})
        msp.add_line((x_title, y_title + 1.0), (x_title, y_title), dxfattribs={'color': colors.WHITE})

        # Add title text
        msp.add_text(
            '桁架立面图',
            dxfattribs={'height': 0.15, 'color': colors.WHITE, 'style': 'CHINESE'}
        ).set_placement((x_title + 1.25, y_title + 0.75), align=TextEntityAlignment.CENTER)

        # Add design info
        geometry = design.get('geometry', {})
        n_panels = geometry.get('n_panels', 5)
        date_str = datetime.now().strftime("%Y-%m-%d")

        params = [
            (f'跨度: {span:.1f}m', y_title + 0.55),
            (f'高度: {height:.1f}m', y_title + 0.40),
            (f'节间数: {n_panels}', y_title + 0.25),
            (f'材料: {material_name}', y_title + 0.10),
        ]
        for text, y_pos in params:
            msp.add_text(
                text,
                dxfattribs={'height': 0.10, 'color': colors.WHITE, 'style': 'CHINESE'}
            ).set_placement((x_title + 0.1, y_pos), align=TextEntityAlignment.LEFT)

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
