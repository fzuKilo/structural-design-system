"""
Cantilever beam drawer using ezdxf
Implements CAD drawing for cantilever beam structures
"""

import ezdxf
from ezdxf import colors
import os
import traceback
from datetime import datetime
from typing import Dict, Any, Optional
from .base_drawer import StructureDrawer, DrawingResults


class CantileverBeamDrawer(StructureDrawer):
    """
    Concrete drawer for cantilever beam structures using ezdxf

    Key differences from simply supported beam:
    - Fixed support symbol at one end
    - Free end at the other end
    - Different annotation for support conditions
    """

    def __init__(self):
        """Initialize cantilever beam drawer"""
        super().__init__()

    def _convert_to_mm(self, value: float, units: str) -> float:
        """Convert value from specified units to millimeters"""
        if units == "m":
            return value * 1000.0
        elif units == "mm":
            return value
        else:
            return value * 1000.0

    def _get_structure_type(self) -> str:
        """Return structure type identifier"""
        return "cantilever_beam"

    def _detect_units(self, geometry: Dict[str, Any], explicit_units: str) -> str:
        """Detect units from geometry values"""
        if explicit_units != "m":
            return explicit_units

        length = geometry.get('length', 0)
        width = geometry.get('width', 0)
        height = geometry.get('height', 0)

        if length > 100 or width > 100 or height > 100:
            if length >= 1000 or (length > 100 and length % 100 == 0):
                return "mm"

        return explicit_units

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
        """配置 MM_UNITS 标注样式"""
        # Ensure STANDARD text style exists
        if 'STANDARD' not in doc.styles:
            doc.styles.new('STANDARD', dxfattribs={'font': 'txt.shx'})

        # Fix EZDXF default dimstyle
        try:
            dimstyle = doc.dimstyles.get('EZDXF')
            if dimstyle:
                dimstyle.dxf.dimlfac = 1.0
                dimstyle.dxf.dimtxsty = 'STANDARD'
        except Exception:
            pass

        # Create MM_UNITS dimstyle
        if 'MM_UNITS' not in doc.dimstyles:
            dimstyle = doc.dimstyles.new('MM_UNITS')
            dimstyle.dxf.dimtxt = 150
            dimstyle.dxf.dimasz = 100
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
        Draw the elevation view (side view) of the cantilever beam

        Args:
            design: Design parameters

        Returns:
            Path to generated DXF file or None if failed
        """
        try:
            # Extract parameters
            geometry = design.get('geometry', {})
            material = design.get('material', {})
            units = design.get('units', 'm')

            # Detect actual units
            detected_units = self._detect_units(geometry, units)

            # Convert to mm for drawing
            length_mm = self._convert_to_mm(geometry.get('length', 6.0), detected_units)
            width_mm = self._convert_to_mm(geometry.get('width', 0.3), detected_units)
            height_mm = self._convert_to_mm(geometry.get('height', 0.6), detected_units)
            material_name = material.get('material_name', 'Unknown')

            # Create DXF document
            doc = ezdxf.new('R2010', setup=True)
            msp = doc.modelspace()

            # Setup styles
            self._setup_chinese_style(doc)
            self._setup_dimstyle(doc)

            # Draw elevation
            self._draw_cantilever_elevation(
                msp=msp,
                length_mm=length_mm,
                width_mm=width_mm,
                height_mm=height_mm,
                material_name=material_name
            )

            # Save file
            os.makedirs(self.output_dir, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{self.output_dir}/cantilever_beam_elevation_{timestamp}.dxf"
            doc.saveas(filename)
            return filename

        except Exception as e:
            print(f"Error drawing cantilever beam elevation: {e}")
            traceback.print_exc()
            return None

    def draw_plan(self, design: Dict[str, Any]) -> Optional[str]:
        """
        Draw the plan view (top view) of the cantilever beam

        Args:
            design: Design parameters

        Returns:
            Path to generated DXF file or None if failed
        """
        try:
            geometry = design.get('geometry', {})
            units = design.get('units', 'm')

            detected_units = self._detect_units(geometry, units)

            length_mm = self._convert_to_mm(geometry.get('length', 6.0), detected_units)
            width_mm = self._convert_to_mm(geometry.get('width', 0.3), detected_units)

            doc = ezdxf.new('R2010')
            msp = doc.modelspace()

            # Setup styles
            self._setup_chinese_style(doc)
            self._setup_dimstyle(doc)

            # Draw plan
            self._draw_beam_plan(msp=msp, doc=doc, length_mm=length_mm, width_mm=width_mm)

            # Save file
            os.makedirs(self.output_dir, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{self.output_dir}/cantilever_beam_plan_{timestamp}.dxf"
            doc.saveas(filename)
            return filename

        except Exception as e:
            print(f"Error drawing cantilever beam plan: {e}")
            traceback.print_exc()
            return None

    def draw_details(self, design: Dict[str, Any]) -> Optional[str]:
        """
        Draw detail views (cross-section) of the cantilever beam

        Args:
            design: Design parameters

        Returns:
            Path to generated DXF file or None if failed
        """
        try:
            geometry = design.get('geometry', {})
            units = design.get('units', 'm')

            detected_units = self._detect_units(geometry, units)

            width_mm = self._convert_to_mm(geometry.get('width', 0.3), detected_units)
            height_mm = self._convert_to_mm(geometry.get('height', 0.6), detected_units)

            doc = ezdxf.new('R2010')
            msp = doc.modelspace()

            # Setup styles
            self._setup_chinese_style(doc)
            self._setup_dimstyle(doc)

            # Draw cross-section detail
            self._draw_beam_detail(msp=msp, doc=doc, width_mm=width_mm, height_mm=height_mm)

            # Save file
            os.makedirs(self.output_dir, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{self.output_dir}/cantilever_beam_details_{timestamp}.dxf"
            doc.saveas(filename)
            return filename

        except Exception as e:
            print(f"Error drawing cantilever beam details: {e}")
            traceback.print_exc()
            return None

    def _draw_cantilever_elevation(
        self,
        msp,
        length_mm: float,
        width_mm: float,
        height_mm: float,
        material_name: str
    ):
        """Draw cantilever beam elevation view"""
        beam_start_x = 0
        beam_start_y = 0

        # 1. Draw beam rectangle outline
        beam_corners = [
            (beam_start_x, beam_start_y),
            (beam_start_x + length_mm, beam_start_y),
            (beam_start_x + length_mm, beam_start_y + height_mm),
            (beam_start_x, beam_start_y + height_mm),
            (beam_start_x, beam_start_y)
        ]
        msp.add_lwpolyline(
            beam_corners,
            dxfattribs={'color': colors.WHITE, 'const_width': 15}
        )

        # 2. Draw fixed support at left end
        self._draw_fixed_support(msp, beam_start_x, beam_start_y, height_mm)

        # 3. Add dimensions
        self._add_cantilever_dimensions(msp, length_mm, height_mm)

        # 4. Add text annotations
        self._add_cantilever_annotations(
            msp, length_mm, width_mm, height_mm, material_name
        )

    def _draw_fixed_support(self, msp, x: float, y: float, height: float):
        """
        Draw fixed support symbol (standard engineering drawing convention):
        - Thick vertical wall-face line spanning full beam height
        - 5 diagonal hatch lines angled 45° to upper-left (embedded in wall)
        - Filled rectangle outline on the left representing wall body
        """
        wall_line_x = x
        wall_thickness = height * 0.4
        hatch_length = height * 0.2

        # Wall face line (thick vertical line at beam left end)
        msp.add_line(
            (wall_line_x, y - height * 0.1),
            (wall_line_x, y + height * 1.1),
            dxfattribs={'color': colors.WHITE, 'lineweight': 70}
        )

        # Wall body outline (rectangle to the left of wall face line)
        wall_corners = [
            (wall_line_x - wall_thickness, y - height * 0.1),
            (wall_line_x, y - height * 0.1),
            (wall_line_x, y + height * 1.1),
            (wall_line_x - wall_thickness, y + height * 1.1),
            (wall_line_x - wall_thickness, y - height * 0.1)
        ]
        msp.add_lwpolyline(
            wall_corners,
            dxfattribs={'color': colors.WHITE, 'lineweight': 25}
        )

        # 5 diagonal hatch lines inside the wall body (45° upper-left)
        num_hatch = 5
        for i in range(num_hatch):
            frac = (i + 1) / (num_hatch + 1)
            hatch_y = y + height * frac
            msp.add_line(
                (wall_line_x - wall_thickness * 0.1, hatch_y),
                (wall_line_x - wall_thickness * 0.1 - hatch_length,
                 hatch_y + hatch_length),
                dxfattribs={'color': colors.WHITE, 'lineweight': 13}
            )

    def _add_cantilever_dimensions(self, msp, length_mm: float, height_mm: float):
        """Add linear dimensions to cantilever elevation view"""
        try:
            # Total length dimension below the beam
            dim = msp.add_linear_dim(
                base=(length_mm / 2, -1200),
                p1=(0, 0),
                p2=(length_mm, 0),
                dimstyle='MM_UNITS',
                override={'dimtxt': 150, 'dimclrt': colors.WHITE}
            )
            dim.render()
        except Exception as e:
            print(f"Warning: Could not add length dimension: {e}")

        try:
            # Height dimension on the LEFT side (consistent with continuous beam style)
            # Place it clear of the wall symbol (wall extends to -height*0.4)
            left_offset = height_mm * 0.4 + 600
            dim = msp.add_linear_dim(
                base=(-left_offset, height_mm / 2),
                p1=(0, 0),
                p2=(0, height_mm),
                angle=90,
                dimstyle='MM_UNITS',
                override={'dimtxt': 150, 'dimclrt': colors.WHITE}
            )
            dim.render()
        except Exception as e:
            print(f"Warning: Could not add height dimension: {e}")

    def _add_cantilever_annotations(
        self,
        msp,
        length_mm: float,
        width_mm: float,
        height_mm: float,
        material_name: str
    ):
        """Add Chinese text annotations and technical parameter table"""
        # Title: 悬臂梁立面图 (centered above beam)
        msp.add_text(
            "悬臂梁立面图",
            dxfattribs={'style': 'CHINESE', 'height': 300, 'color': colors.WHITE}
        ).set_placement(
            (length_mm / 2, height_mm + 800),
            align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER
        )

        # Fixed end annotation (left side, below beam, same level as dim line)
        msp.add_text(
            "固定端",
            dxfattribs={'style': 'CHINESE', 'height': 150, 'color': colors.WHITE}
        ).set_placement(
            (0, -1600),
            align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER
        )

        # Free end annotation (right side, below beam, same level as dim line)
        msp.add_text(
            "自由端",
            dxfattribs={'style': 'CHINESE', 'height': 150, 'color': colors.WHITE}
        ).set_placement(
            (length_mm, -1600),
            align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER
        )

        # Technical parameter table (to the right of the drawing)
        param_x = length_mm + 1200
        param_y = height_mm
        line_spacing = 300

        params = [
            "技术参数:",
            f"悬臂长度 L = {length_mm:.0f} mm",
            f"截面宽度 b = {width_mm:.0f} mm",
            f"截面高度 h = {height_mm:.0f} mm",
            f"材料: {material_name}",
            "支座: 固定端（左端嵌固）",
        ]

        for i, text in enumerate(params):
            msp.add_text(
                text,
                dxfattribs={'style': 'CHINESE', 'height': 120, 'color': colors.WHITE}
            ).set_placement(
                (param_x, param_y - i * line_spacing),
                align=ezdxf.enums.TextEntityAlignment.LEFT
            )

    def _draw_beam_plan(self, msp, doc, length_mm: float, width_mm: float):
        """Draw beam plan view (top view)"""
        # Draw beam rectangle
        beam_corners = [
            (0, 0),
            (length_mm, 0),
            (length_mm, width_mm),
            (0, width_mm),
            (0, 0)
        ]
        msp.add_lwpolyline(
            beam_corners,
            dxfattribs={'color': colors.WHITE, 'const_width': 15}
        )

        # Add length dimension below the beam
        try:
            dim = msp.add_linear_dim(
                base=(length_mm / 2, -200),
                p1=(0, 0),
                p2=(length_mm, 0),
                dimstyle='MM_UNITS',
                override={'dimtxt': 150, 'dimclrt': colors.WHITE}
            )
            dim.render()
        except Exception as e:
            print(f"Warning: Could not add plan dimensions: {e}")

        # Title
        msp.add_text(
            "悬臂梁平面图",
            dxfattribs={'style': 'CHINESE', 'height': 300, 'color': colors.WHITE}
        ).set_placement(
            (length_mm / 2, width_mm + 500),
            align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER
        )

    def _draw_beam_detail(self, msp, doc, width_mm: float, height_mm: float):
        """Draw beam cross-section detail (horizontally centered)"""
        start_x = -width_mm / 2
        start_y = 0

        corners = [
            (start_x, start_y),
            (start_x + width_mm, start_y),
            (start_x + width_mm, start_y + height_mm),
            (start_x, start_y + height_mm),
            (start_x, start_y)
        ]
        msp.add_lwpolyline(
            corners,
            dxfattribs={'color': colors.WHITE, 'const_width': 15}
        )

        # Add section dimensions
        self._add_section_dimensions(msp, doc, width_mm, height_mm)

        # Title
        msp.add_text(
            "悬臂梁截面详图",
            dxfattribs={'style': 'CHINESE', 'height': 300, 'color': colors.WHITE}
        ).set_placement(
            (0, start_y + height_mm + 500),
            align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER
        )

    def _add_section_dimensions(self, msp, doc, width_mm: float, height_mm: float):
        """Add dimensions to section view"""
        start_x = -width_mm / 2
        start_y = 0

        try:
            # Width dimension below the section
            dim = msp.add_linear_dim(
                base=(start_x + width_mm / 2, start_y - 200),
                p1=(start_x, start_y),
                p2=(start_x + width_mm, start_y),
                dimstyle='MM_UNITS',
                override={'dimtxt': 150, 'dimclrt': colors.WHITE}
            )
            dim.render()
        except Exception as e:
            print(f"Warning: Could not add section width dimension: {e}")

        try:
            # Height dimension to the right of the section
            dim = msp.add_linear_dim(
                base=(start_x + width_mm + 200, start_y + height_mm / 2),
                p1=(start_x + width_mm, start_y),
                p2=(start_x + width_mm, start_y + height_mm),
                angle=90,
                dimstyle='MM_UNITS',
                override={'dimtxt': 150, 'dimclrt': colors.WHITE}
            )
            dim.render()
        except Exception as e:
            print(f"Warning: Could not add section height dimension: {e}")

    def set_output_directory(self, directory: str, subdirectory: str = None) -> None:
        """
        Set output directory for generated drawings

        Args:
            directory: Path to output directory
            subdirectory: Optional subdirectory (ignored for compatibility)
        """
        self.output_dir = directory
        os.makedirs(self.output_dir, exist_ok=True)
