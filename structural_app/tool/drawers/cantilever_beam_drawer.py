"""
Cantilever beam drawer using ezdxf
Implements CAD drawing for cantilever beam structures
"""

import ezdxf
from ezdxf import colors
import os
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

            # Create DXF document
            doc = ezdxf.new('R2010')
            msp = doc.modelspace()

            # Drawing parameters
            scale = 1.0
            if length_mm > 10000:
                scale = 0.5

            # Beam outline (rectangle in elevation view)
            beam_start_x = 0
            beam_start_y = 0
            beam_end_x = length_mm * scale
            beam_end_y = height_mm * scale

            # Draw beam rectangle
            msp.add_lwpolyline([
                (beam_start_x, beam_start_y),
                (beam_end_x, beam_start_y),
                (beam_end_x, beam_end_y),
                (beam_start_x, beam_end_y),
                (beam_start_x, beam_start_y)
            ], dxfattribs={'color': colors.WHITE, 'lineweight': 50})

            # Draw fixed support at left end (cantilever)
            support_height = height_mm * scale * 1.5
            support_width = height_mm * scale * 0.3

            # Fixed support symbol: vertical line with hatching
            msp.add_line(
                (beam_start_x, beam_start_y - support_height * 0.2),
                (beam_start_x, beam_end_y + support_height * 0.2),
                dxfattribs={'color': colors.WHITE, 'lineweight': 70}
            )

            # Hatching lines for fixed support
            num_hatch_lines = 5
            for i in range(num_hatch_lines):
                y_pos = beam_start_y + (beam_end_y - beam_start_y) * i / (num_hatch_lines - 1)
                msp.add_line(
                    (beam_start_x, y_pos),
                    (beam_start_x - support_width, y_pos - support_width * 0.5),
                    dxfattribs={'color': colors.WHITE, 'lineweight': 25}
                )

            # Add dimensions
            # Length dimension
            dim_offset_y = -height_mm * scale * 0.8
            msp.add_line(
                (beam_start_x, dim_offset_y),
                (beam_end_x, dim_offset_y),
                dxfattribs={'color': colors.GREEN}
            )
            msp.add_text(
                f'L = {length_mm:.0f} mm',
                dxfattribs={'height': height_mm * scale * 0.15, 'color': colors.GREEN}
            ).set_placement((beam_end_x / 2, dim_offset_y - height_mm * scale * 0.2))

            # Height dimension
            dim_offset_x = beam_end_x + height_mm * scale * 0.5
            msp.add_line(
                (dim_offset_x, beam_start_y),
                (dim_offset_x, beam_end_y),
                dxfattribs={'color': colors.GREEN}
            )
            msp.add_text(
                f'H = {height_mm:.0f} mm',
                dxfattribs={'height': height_mm * scale * 0.15, 'color': colors.GREEN}
            ).set_placement((dim_offset_x + height_mm * scale * 0.2, beam_end_y / 2))

            # Add title and material info
            title_y = beam_end_y + height_mm * scale * 1.0
            msp.add_text(
                'CANTILEVER BEAM - ELEVATION VIEW',
                dxfattribs={'height': height_mm * scale * 0.25, 'color': colors.CYAN}
            ).set_placement((beam_start_x, title_y))

            material_name = material.get('material_name', 'Unknown')
            msp.add_text(
                f'Material: {material_name}',
                dxfattribs={'height': height_mm * scale * 0.15, 'color': colors.CYAN}
            ).set_placement((beam_start_x, title_y - height_mm * scale * 0.4))

            # Add support type annotation
            msp.add_text(
                'FIXED SUPPORT',
                dxfattribs={'height': height_mm * scale * 0.12, 'color': colors.WHITE}
            ).set_placement((beam_start_x - support_width * 2, beam_start_y - height_mm * scale * 0.6))

            msp.add_text(
                'FREE END',
                dxfattribs={'height': height_mm * scale * 0.12, 'color': colors.MAGENTA}
            ).set_placement((beam_end_x - height_mm * scale * 0.8, beam_start_y - height_mm * scale * 0.6))

            # Save file
            os.makedirs(self.output_dir, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{self.output_dir}/cantilever_beam_elevation_{timestamp}.dxf"
            doc.saveas(filename)
            return filename

        except Exception as e:
            print(f"Error drawing cantilever beam elevation: {e}")
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

            scale = 1.0
            if length_mm > 10000:
                scale = 0.5

            # Draw beam rectangle (plan view)
            msp.add_lwpolyline([
                (0, 0),
                (length_mm * scale, 0),
                (length_mm * scale, width_mm * scale),
                (0, width_mm * scale),
                (0, 0)
            ], dxfattribs={'color': colors.WHITE, 'lineweight': 50})

            # Add title
            msp.add_text(
                'CANTILEVER BEAM - PLAN VIEW',
                dxfattribs={'height': width_mm * scale * 0.5, 'color': colors.CYAN}
            ).set_placement((0, width_mm * scale * 1.5))

            # Save file
            os.makedirs(self.output_dir, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{self.output_dir}/cantilever_beam_plan_{timestamp}.dxf"
            doc.saveas(filename)
            return filename

        except Exception as e:
            print(f"Error drawing cantilever beam plan: {e}")
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

            # Draw cross-section rectangle
            msp.add_lwpolyline([
                (0, 0),
                (width_mm, 0),
                (width_mm, height_mm),
                (0, height_mm),
                (0, 0)
            ], dxfattribs={'color': colors.WHITE, 'lineweight': 50})

            # Add dimensions
            msp.add_text(
                f'W = {width_mm:.0f} mm',
                dxfattribs={'height': height_mm * 0.1, 'color': colors.GREEN}
            ).set_placement((width_mm / 2 - width_mm * 0.2, -height_mm * 0.3))

            msp.add_text(
                f'H = {height_mm:.0f} mm',
                dxfattribs={'height': height_mm * 0.1, 'color': colors.GREEN}
            ).set_placement((width_mm + width_mm * 0.2, height_mm / 2))

            # Add title
            msp.add_text(
                'CANTILEVER BEAM - CROSS SECTION',
                dxfattribs={'height': height_mm * 0.15, 'color': colors.CYAN}
            ).set_placement((0, height_mm * 1.3))

            # Save file
            os.makedirs(self.output_dir, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{self.output_dir}/cantilever_beam_details_{timestamp}.dxf"
            doc.saveas(filename)
            return filename

        except Exception as e:
            print(f"Error drawing cantilever beam details: {e}")
            return None
