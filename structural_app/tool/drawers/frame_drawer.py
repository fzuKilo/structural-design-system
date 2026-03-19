"""
Frame drawer using ezdxf
Implements CAD drawing for frame structures (multi-bay, multi-story)
"""

import ezdxf
from ezdxf import colors
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
from .base_drawer import StructureDrawer, DrawingResults


class FrameDrawer(StructureDrawer):
    """
    Concrete drawer for frame structures using ezdxf

    Generates standard CAD drawings for frames including:
    - Elevation view (frame layout with all beams and columns)
    - Detail views (beam-column connection details)
    """

    def __init__(self):
        """Initialize frame drawer"""
        super().__init__()

    def _get_structure_type(self) -> str:
        """Return structure type identifier"""
        return "frame"

    def _convert_to_mm(self, value: float, units: str) -> float:
        """
        Convert value from specified units to millimeters

        Args:
            value: Value to convert
            units: Source units ("m" or "mm")

        Returns:
            Value in millimeters
        """
        if units == "m":
            return value * 1000.0
        elif units == "mm":
            return value
        else:
            # Default to meters if unknown unit
            return value * 1000.0

    def _detect_units(self, geometry: Dict[str, Any], explicit_units: str) -> str:
        """
        Detect units from geometry values

        Args:
            geometry: Geometry parameters
            explicit_units: Explicitly specified units

        Returns:
            Detected units ("m" or "mm")
        """
        if explicit_units != "m":
            return explicit_units

        # Check bay widths
        bay_widths = geometry.get('bay_widths', [6.0])
        if bay_widths and bay_widths[0] > 100:
            return "mm"

        return explicit_units

    def draw_elevation(self, design: Dict[str, Any]) -> Optional[str]:
        """
        Draw the elevation view of the frame

        Args:
            design: Design parameters including:
                - geometry: {num_bays, num_stories, bay_widths, story_heights, columns, beams}
                - material: {E, nu, fy}
                - loads: {beam_distributed, lateral, nodal}
                - boundary: {column_base}
                - units: "m" or "mm" (optional, default "m")

        Returns:
            Path to the generated DXF file
        """
        try:
            # Extract parameters
            geometry = design.get('geometry', {})
            explicit_units = design.get('units', 'm')
            units = self._detect_units(geometry, explicit_units)

            num_bays = geometry.get('num_bays', 1)
            num_stories = geometry.get('num_stories', 1)
            bay_widths = geometry.get('bay_widths', [6.0])
            story_heights = geometry.get('story_heights', [4.0])

            # Column and beam sections
            columns = geometry.get('columns', {})
            beams = geometry.get('beams', {})
            col_width_mm = self._convert_to_mm(columns.get('width', 0.4), units)
            col_depth_mm = self._convert_to_mm(columns.get('depth', 0.4), units)
            beam_width_mm = self._convert_to_mm(beams.get('width', 0.3), units)
            beam_depth_mm = self._convert_to_mm(beams.get('depth', 0.6), units)

            # Convert to mm
            bay_widths_mm = [self._convert_to_mm(w, units) for w in bay_widths]
            story_heights_mm = [self._convert_to_mm(h, units) for h in story_heights]

            # Create DXF document
            doc = ezdxf.new('R2010')
            msp = doc.modelspace()
            self._setup_chinese_style(doc)

            # 1. Draw columns
            self._draw_all_columns(msp, num_bays, num_stories, bay_widths_mm,
                                  story_heights_mm, col_width_mm, col_depth_mm)

            # 2. Draw beams
            self._draw_all_beams(msp, num_bays, num_stories, bay_widths_mm,
                                story_heights_mm, beam_width_mm, beam_depth_mm)

            # 3. Draw support symbols
            self._draw_support_symbols(msp, num_bays, bay_widths_mm)

            # 4. Add dimensions
            self._add_dimensions(msp, num_bays, num_stories, bay_widths_mm, story_heights_mm)

            # 5. Add axis labels
            self._add_axis_labels(msp, num_bays, bay_widths_mm)

            # 6. Add title block
            total_width = sum(bay_widths_mm)
            total_height = sum(story_heights_mm)
            self._add_title_block(msp, total_width, total_height, num_bays, num_stories)

            # Save file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(str(self.output_dir), f"frame_elevation_{timestamp}.dxf")
            doc.saveas(filename)

            return filename

        except Exception as e:
            print(f"Error drawing frame elevation: {str(e)}")
            return None

    def _draw_all_columns(self, msp, num_bays: int, num_stories: int,
                         bay_widths_mm: List[float], story_heights_mm: List[float],
                         col_width_mm: float, col_depth_mm: float):
        """Draw all columns"""
        x = 0.0
        for bay in range(num_bays + 1):
            y = 0.0
            for story in range(num_stories):
                self._draw_column(msp, x, y, col_width_mm, story_heights_mm[story])
                y += story_heights_mm[story]

            if bay < num_bays:
                x += bay_widths_mm[bay]

    def _draw_column(self, msp, x: float, y: float, width: float, height: float):
        """
        Draw a single column

        Args:
            msp: Model space
            x: X coordinate of column centerline
            y: Y coordinate of column base
            width: Column width (mm)
            height: Column height (mm)
        """
        # Column centerline at x, draw rectangle
        x_left = x - width / 2
        x_right = x + width / 2

        # Draw column outline
        msp.add_line((x_left, y), (x_right, y), dxfattribs={'color': colors.BLACK})
        msp.add_line((x_right, y), (x_right, y + height), dxfattribs={'color': colors.BLACK})
        msp.add_line((x_right, y + height), (x_left, y + height), dxfattribs={'color': colors.BLACK})
        msp.add_line((x_left, y + height), (x_left, y), dxfattribs={'color': colors.BLACK})

    def _draw_all_beams(self, msp, num_bays: int, num_stories: int,
                       bay_widths_mm: List[float], story_heights_mm: List[float],
                       beam_width_mm: float, beam_depth_mm: float):
        """Draw all beams"""
        y = 0.0
        for story in range(num_stories):
            y += story_heights_mm[story]
            x = 0.0
            for bay in range(num_bays):
                self._draw_beam(msp, x, y, bay_widths_mm[bay], beam_width_mm, beam_depth_mm)
                x += bay_widths_mm[bay]

    def _draw_beam(self, msp, x_start: float, y: float, length: float,
                   width: float, depth: float):
        """
        Draw a single beam

        Args:
            msp: Model space
            x_start: X coordinate of beam start
            y: Y coordinate of beam centerline
            length: Beam length (mm)
            width: Beam width (mm)
            depth: Beam depth (mm)
        """
        # Beam centerline at y, draw rectangle
        y_bottom = y - depth / 2
        y_top = y + depth / 2

        # Draw beam outline
        msp.add_line((x_start, y_bottom), (x_start + length, y_bottom), dxfattribs={'color': colors.BLACK})
        msp.add_line((x_start + length, y_bottom), (x_start + length, y_top), dxfattribs={'color': colors.BLACK})
        msp.add_line((x_start + length, y_top), (x_start, y_top), dxfattribs={'color': colors.BLACK})
        msp.add_line((x_start, y_top), (x_start, y_bottom), dxfattribs={'color': colors.BLACK})

    def _draw_support_symbols(self, msp, num_bays: int, bay_widths_mm: List[float]):
        """Draw fixed support symbols at column bases"""
        x = 0.0
        for bay in range(num_bays + 1):
            self._draw_fixed_support(msp, x, 0)
            if bay < num_bays:
                x += bay_widths_mm[bay]

    def _draw_fixed_support(self, msp, x: float, y: float):
        """
        Draw fixed support symbol

        Args:
            msp: Model space
            x: X coordinate
            y: Y coordinate
        """
        support_width = 300  # mm
        support_height = 200  # mm

        # Draw triangle
        msp.add_line((x, y), (x - support_width/2, y - support_height), dxfattribs={'color': colors.BLACK})
        msp.add_line((x, y), (x + support_width/2, y - support_height), dxfattribs={'color': colors.BLACK})
        msp.add_line((x - support_width/2, y - support_height),
                    (x + support_width/2, y - support_height), dxfattribs={'color': colors.BLACK})

        # Draw hatch lines
        for i in range(5):
            offset = -support_width/2 + i * support_width/4
            msp.add_line((x + offset, y - support_height),
                        (x + offset - 100, y - support_height - 100),
                        dxfattribs={'color': colors.BLACK})

    def _setup_chinese_style(self, doc):
        """Setup Chinese font style for the DXF document"""
        try:
            doc.styles.new('CHINESE', dxfattribs={'font': 'simhei.ttf'})
        except Exception:
            try:
                doc.styles.new('CHINESE', dxfattribs={'font': 'simsun.ttc'})
            except Exception:
                doc.styles.new('CHINESE', dxfattribs={'font': 'Arial.ttf'})

    def _add_dimensions(self, msp, num_bays: int, num_stories: int,
                       bay_widths_mm: List[float], story_heights_mm: List[float]):
        """Add dimension annotations with proper spacing to avoid overlap.

        Layout (from y=0 downward):
          y=0       structure base (supports)
          y=-400    horizontal dimension line
          y=-620    bay width text (L1=6.0m)
          y=-1200   axis label circles (A, B, C...)
        """
        text_height = 150  # mm
        dim_line_y = -400
        dim_text_y = -620

        # Dimension bay widths
        x = 0.0
        for i, width in enumerate(bay_widths_mm):
            x_mid = x + width / 2

            # Left tick
            msp.add_line((x, dim_line_y + 100), (x, dim_line_y - 100),
                         dxfattribs={'color': colors.BLUE})
            # Horizontal dimension line
            msp.add_line((x, dim_line_y), (x + width, dim_line_y),
                         dxfattribs={'color': colors.BLUE})
            # Bay width text
            t = msp.add_text(f'L{i+1}={width/1000:.1f}m',
                             dxfattribs={'height': text_height, 'color': colors.BLUE,
                                         'style': 'CHINESE'})
            t.set_placement((x_mid, dim_text_y), align=ezdxf.enums.TextEntityAlignment.CENTER)
            x += width

        # Right tick for last bay
        msp.add_line((x, dim_line_y + 100), (x, dim_line_y - 100),
                     dxfattribs={'color': colors.BLUE})

        # Dimension story heights (right side)
        y = 0.0
        total_width = sum(bay_widths_mm)
        for i, height in enumerate(story_heights_mm):
            t = msp.add_text(f'H{i+1}={height/1000:.1f}m',
                             dxfattribs={'height': text_height, 'color': colors.BLUE,
                                         'style': 'CHINESE'})
            t.set_placement((total_width + 500, y + height / 2),
                            align=ezdxf.enums.TextEntityAlignment.LEFT)
            y += height

    def _add_axis_labels(self, msp, num_bays: int, bay_widths_mm: List[float]):
        """Add axis labels (A, B, C, ...) below dimension lines"""
        axis_labels = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']
        circle_radius = 200  # mm
        text_height = 150    # mm
        circle_y = -1200

        x = 0.0
        for i in range(num_bays + 1):
            msp.add_circle((x, circle_y), radius=circle_radius,
                           dxfattribs={'color': colors.BLACK})
            label = axis_labels[i] if i < len(axis_labels) else str(i + 1)
            t = msp.add_text(label, dxfattribs={'height': text_height, 'color': colors.BLACK,
                                                 'style': 'CHINESE'})
            t.set_placement((x, circle_y), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)
            if i < num_bays:
                x += bay_widths_mm[i]

    def _add_title_block(self, msp, total_width: float, total_height: float,
                        num_bays: int, num_stories: int):
        """Add title block above the frame"""
        text_height = 200  # mm
        y_pos = total_height + 1500  # enough clearance above frame

        t = msp.add_text('框架结构立面图',
                         dxfattribs={'height': text_height * 1.5, 'color': colors.BLACK,
                                     'style': 'CHINESE'})
        t.set_placement((total_width / 2, y_pos),
                        align=ezdxf.enums.TextEntityAlignment.CENTER)

        t2 = msp.add_text(f'{num_bays}x{num_stories} Frame',
                          dxfattribs={'height': text_height, 'color': colors.BLUE,
                                      'style': 'CHINESE'})
        t2.set_placement((total_width / 2, y_pos - 500),
                         align=ezdxf.enums.TextEntityAlignment.CENTER)

    def draw_plan(self, design: Dict[str, Any]) -> Optional[str]:
        """
        Draw plan view (optional, can be implemented later)

        Args:
            design: Design parameters

        Returns:
            Path to the generated DXF file, or None
        """
        # Simplified implementation - can be expanded later
        return None

    def draw_section(self, design: Dict[str, Any]) -> Optional[str]:
        """
        Draw section view (optional)

        Args:
            design: Design parameters

        Returns:
            Path to the generated DXF file, or None
        """
        return None

    def draw_detail(self, design: Dict[str, Any]) -> Optional[str]:
        """
        Draw detail view: beam and column cross-sections with dimension annotations.

        Args:
            design: Design parameters

        Returns:
            Path to the generated DXF file
        """
        try:
            geometry = design.get('geometry', {})
            explicit_units = design.get('units', 'm')
            units = self._detect_units(geometry, explicit_units)

            columns = geometry.get('columns', {})
            beams = geometry.get('beams', {})
            col_w = self._convert_to_mm(columns.get('width', 0.4), units)
            col_d = self._convert_to_mm(columns.get('depth', 0.4), units)
            beam_w = self._convert_to_mm(beams.get('width', 0.3), units)
            beam_d = self._convert_to_mm(beams.get('depth', 0.6), units)

            doc = ezdxf.new('R2010')
            msp = doc.modelspace()
            self._setup_chinese_style(doc)

            # 两截面间距 = 较大截面宽度的 3 倍，确保尺寸线和文字不重叠
            gap = max(col_w, beam_w) * 3
            total_w = col_w + gap + beam_w
            # 内容整体居中于原点，让默认视口能看到
            col_cx = -total_w / 2 + col_w / 2
            beam_cx = col_cx + col_w / 2 + gap + beam_w / 2

            self._draw_section(msp, col_cx, 0, col_w, col_d, '柱截面')
            self._draw_section(msp, beam_cx, 0, beam_w, beam_d, '梁截面')

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(str(self.output_dir), f"frame_details_{timestamp}.dxf")
            doc.saveas(filename)
            return filename

        except Exception as e:
            print(f"Error drawing frame details: {str(e)}")
            return None

    def draw_details(self, design: Dict[str, Any]) -> Optional[str]:
        """Alias for draw_detail() to satisfy abstract base class requirement"""
        return self.draw_detail(design)

    def _draw_section(self, msp, cx: float, cy: float,
                      width: float, depth: float, title: str):
        """
        Draw a rectangular cross-section with dimension annotations.

        Args:
            msp: Model space
            cx: Center X of the section
            cy: Center Y of the section
            width: Section width (mm)
            depth: Section depth (mm)
            title: Title text above the section
        """
        x0, x1 = cx - width / 2, cx + width / 2
        y0, y1 = cy - depth / 2, cy + depth / 2
        text_h = max(width, depth) * 0.08

        # Rectangle outline
        msp.add_line((x0, y0), (x1, y0), dxfattribs={'color': colors.BLACK})
        msp.add_line((x1, y0), (x1, y1), dxfattribs={'color': colors.BLACK})
        msp.add_line((x1, y1), (x0, y1), dxfattribs={'color': colors.BLACK})
        msp.add_line((x0, y1), (x0, y0), dxfattribs={'color': colors.BLACK})

        # Diagonal hatch lines
        msp.add_line((x0, y0), (x1, y1), dxfattribs={'color': 8})
        msp.add_line((x1, y0), (x0, y1), dxfattribs={'color': 8})

        # Width dimension line (below)
        dim_y = y0 - depth * 0.5
        msp.add_line((x0, dim_y), (x1, dim_y), dxfattribs={'color': colors.BLUE})
        msp.add_line((x0, y0), (x0, dim_y), dxfattribs={'color': colors.BLUE})
        msp.add_line((x1, y0), (x1, dim_y), dxfattribs={'color': colors.BLUE})
        t_w = msp.add_text(f'宽={width/1000:.3f}m',
                           dxfattribs={'height': text_h, 'color': colors.BLUE, 'style': 'CHINESE'})
        t_w.set_placement((cx, dim_y - text_h * 2.5),
                          align=ezdxf.enums.TextEntityAlignment.CENTER)

        # Depth dimension line (right side)
        dim_x = x1 + width * 0.5
        msp.add_line((dim_x, y0), (dim_x, y1), dxfattribs={'color': colors.BLUE})
        msp.add_line((x1, y0), (dim_x, y0), dxfattribs={'color': colors.BLUE})
        msp.add_line((x1, y1), (dim_x, y1), dxfattribs={'color': colors.BLUE})
        t_d = msp.add_text(f'高={depth/1000:.3f}m',
                           dxfattribs={'height': text_h, 'color': colors.BLUE, 'style': 'CHINESE'})
        t_d.set_placement((dim_x + text_h * 1.5, cy),
                          align=ezdxf.enums.TextEntityAlignment.LEFT)

        # Title above
        t_title = msp.add_text(title,
                               dxfattribs={'height': text_h * 1.2, 'color': colors.BLACK,
                                           'style': 'CHINESE'})
        t_title.set_placement((cx, y1 + text_h * 2.5),
                              align=ezdxf.enums.TextEntityAlignment.CENTER)
