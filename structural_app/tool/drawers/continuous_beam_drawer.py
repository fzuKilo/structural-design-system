"""
Continuous beam drawer using ezdxf
Implements CAD drawing for continuous beam structures
"""

import ezdxf
from ezdxf import colors
import os
from datetime import datetime
from typing import Dict, Any, Optional
from .base_drawer import StructureDrawer, DrawingResults


class ContinuousBeamDrawer(StructureDrawer):
    """
    Concrete drawer for continuous beam structures using ezdxf

    Key differences from simply supported beam:
    - Multiple spans with intermediate supports
    - Intermediate roller supports visualization
    - Span length annotations
    """

    def __init__(self):
        """Initialize continuous beam drawer"""
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
        return "continuous_beam"

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
        Draw the elevation view (side view) of the continuous beam

        Args:
            design: Design parameters including:
                - geometry: {length, width, height, n_spans}
                - material: {E, nu, fy}
                - loads: {distributed, point}
                - units: "m" or "mm" (optional, default "m")

        Returns:
            Path to the generated DXF file
        """
        try:
            # Extract parameters
            geometry = design.get('geometry', {})
            explicit_units = design.get('units', 'm')
            units = self._detect_units(geometry, explicit_units)

            # Convert to mm for CAD drawing
            length_mm = self._convert_to_mm(geometry.get('length', 12), units)
            width_mm = self._convert_to_mm(geometry.get('width', 0.3), units)
            height_mm = self._convert_to_mm(geometry.get('height', 0.6), units)
            n_spans = geometry.get('n_spans', 2)

            # Extract material information
            material = design.get('material', {})
            material_name = material.get('material_name', 'Unknown')

            # Create new DXF document
            doc = ezdxf.new('R2010', setup=True)
            msp = doc.modelspace()

            # Ensure STANDARD text style exists
            if 'STANDARD' not in doc.styles:
                doc.styles.new('STANDARD', dxfattribs={'font': 'txt.shx'})

            # Setup Chinese font style
            self._setup_chinese_style(doc)

            # Fix EZDXF dimstyle
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
                dimstyle.dxf.dimclrt = colors.RED
                dimstyle.dxf.dimtxsty = 'STANDARD'

            # Draw continuous beam elevation
            self._draw_continuous_beam_elevation(
                msp=msp,
                length_mm=length_mm,
                width_mm=width_mm,
                height_mm=height_mm,
                n_spans=n_spans,
                material_name=material_name
            )

            # Save file
            os.makedirs(self.output_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.output_dir}/continuous_beam_elevation_{timestamp}.dxf"
            doc.saveas(filename)

            return filename

        except Exception as e:
            print(f"Error drawing elevation: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    def draw_plan(self, design: Dict[str, Any]) -> Optional[str]:
        """
        Draw the plan view (top view) of the continuous beam

        Args:
            design: Design parameters including units field

        Returns:
            Path to the generated DXF file
        """
        try:
            # Extract parameters
            geometry = design.get('geometry', {})
            explicit_units = design.get('units', 'm')
            units = self._detect_units(geometry, explicit_units)

            # Convert to mm for CAD drawing
            length_mm = self._convert_to_mm(geometry.get('length', 12), units)
            width_mm = self._convert_to_mm(geometry.get('width', 0.3), units)

            # Create new DXF document
            doc = ezdxf.new('R2010')
            msp = doc.modelspace()

            # Ensure STANDARD text style exists
            if 'STANDARD' not in doc.styles:
                doc.styles.new('STANDARD', dxfattribs={'font': 'txt.shx'})

            # Setup Chinese font style
            self._setup_chinese_style(doc)

            # Fix EZDXF dimstyle
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
                dimstyle.dxf.dimclrt = colors.RED
                dimstyle.dxf.dimtxsty = 'STANDARD'

            # Draw beam plan
            self._draw_beam_plan(
                msp=msp,
                doc=doc,
                length_mm=length_mm,
                width_mm=width_mm
            )

            # Save file
            os.makedirs(self.output_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.output_dir}/continuous_beam_plan_{timestamp}.dxf"
            doc.saveas(filename)

            return filename

        except Exception as e:
            print(f"Error drawing plan: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    def draw_details(self, design: Dict[str, Any]) -> Optional[str]:
        """
        Draw detailed views (cross-section details) of the continuous beam

        Args:
            design: Design parameters including units field

        Returns:
            Path to the generated DXF file
        """
        try:
            # Extract parameters
            geometry = design.get('geometry', {})
            explicit_units = design.get('units', 'm')
            units = self._detect_units(geometry, explicit_units)

            # Convert to mm for CAD drawing
            width_mm = self._convert_to_mm(geometry.get('width', 0.3), units)
            height_mm = self._convert_to_mm(geometry.get('height', 0.6), units)

            # Create new DXF document
            doc = ezdxf.new('R2010')
            msp = doc.modelspace()

            # Ensure STANDARD text style exists
            if 'STANDARD' not in doc.styles:
                doc.styles.new('STANDARD', dxfattribs={'font': 'txt.shx'})

            # Setup Chinese font style
            self._setup_chinese_style(doc)

            # Fix EZDXF dimstyle
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
                dimstyle.dxf.dimclrt = colors.RED
                dimstyle.dxf.dimtxsty = 'STANDARD'

            # Draw beam detail (cross-section)
            self._draw_beam_detail(
                msp=msp,
                doc=doc,
                width_mm=width_mm,
                height_mm=height_mm
            )

            # Save file
            os.makedirs(self.output_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.output_dir}/continuous_beam_detail_{timestamp}.dxf"
            doc.saveas(filename)

            return filename

        except Exception as e:
            print(f"Error drawing detail: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    def _setup_chinese_style(self, doc):
        """Setup Chinese font style for the DXF document"""
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

    def _draw_continuous_beam_elevation(
        self,
        msp,
        length_mm: float,
        width_mm: float,
        height_mm: float,
        n_spans: int,
        material_name: str
    ):
        """
        Draw continuous beam elevation view with multiple spans

        Args:
            msp: Model space to draw in
            length_mm: Total beam length in mm
            width_mm: Beam width in mm
            height_mm: Beam height in mm
            n_spans: Number of spans
            material_name: Material name
        """
        # Setup drawing parameters
        beam_start_x = 0
        beam_start_y = 0
        support_size = 400
        span_length = length_mm / n_spans

        # 1. Draw beam rectangle
        beam_corners = [
            (beam_start_x, beam_start_y),
            (beam_start_x + length_mm, beam_start_y),
            (beam_start_x + length_mm, beam_start_y + height_mm),
            (beam_start_x, beam_start_y + height_mm),
            (beam_start_x, beam_start_y)
        ]
        msp.add_lwpolyline(
            beam_corners,
            dxfattribs={'color': colors.BLACK, 'const_width': 0.5}
        )

        # 2. Draw supports
        # First support: hinge (pinned)
        self._draw_hinge_support(msp, beam_start_x, beam_start_y, support_size)

        # Intermediate supports: rollers
        for i in range(1, n_spans):
            support_x = beam_start_x + i * span_length
            self._draw_roller_support(msp, support_x, beam_start_y, support_size)

        # Last support: roller
        self._draw_roller_support(msp, beam_start_x + length_mm, beam_start_y, support_size)

        # 3. Add dimensions
        self._add_continuous_beam_dimensions(msp, length_mm, height_mm, n_spans, span_length)

        # 4. Add text annotations
        self._add_continuous_beam_annotations(
            msp, length_mm, width_mm, height_mm, n_spans, material_name
        )

    def _draw_beam_plan(self, msp, doc, length_mm: float, width_mm: float):
        """Draw beam plan view (top view)"""
        # Draw beam top view (simplified rectangle)
        beam_corners = [
            (0, 0),
            (length_mm, 0),
            (length_mm, width_mm),
            (0, width_mm),
            (0, 0)
        ]
        msp.add_lwpolyline(
            beam_corners,
            dxfattribs={'color': colors.BLACK, 'const_width': 0.5}
        )

        # Add dimensions
        try:
            dim = msp.add_linear_dim(
                base=(length_mm / 2, -200),
                p1=(0, 0),
                p2=(length_mm, 0),
                dimstyle='MM_UNITS',
                override={'dimtxt': 150, 'dimclrt': colors.RED}
            )
            dim.render()
        except Exception as e:
            print(f"Warning: Could not add plan dimensions: {e}")

        # Add annotations
        msp.add_text(
            "连续梁平面图",
            dxfattribs={'style': 'CHINESE', 'height': 300, 'color': colors.BLACK}
        ).set_placement(
            (length_mm / 2, width_mm + 500),
            align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER
        )

    def _draw_beam_detail(self, msp, doc, width_mm: float, height_mm: float):
        """Draw beam cross-section detail"""
        # Draw cross-section rectangle
        section_width = width_mm
        section_height = height_mm

        # Center the section
        start_x = -section_width / 2
        start_y = 0

        corners = [
            (start_x, start_y),
            (start_x + section_width, start_y),
            (start_x + section_width, start_y + section_height),
            (start_x, start_y + section_height),
            (start_x, start_y)
        ]
        msp.add_lwpolyline(
            corners,
            dxfattribs={'color': colors.BLACK, 'const_width': 0.5}
        )

        # Add section dimensions
        self._add_section_dimensions(msp, doc, section_width, section_height)

        # Add title
        msp.add_text(
            "连续梁截面详图",
            dxfattribs={'style': 'CHINESE', 'height': 300, 'color': colors.BLACK}
        ).set_placement(
            (0, start_y + section_height + 500),
            align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER
        )

    def _draw_hinge_support(self, msp, x: float, y: float, size: float):
        """Draw hinge (pinned) support"""
        points = [
            (x, y),
            (x - size / 2, y - size),
            (x + size / 2, y - size),
            (x, y)
        ]
        msp.add_lwpolyline(
            points,
            dxfattribs={'color': colors.BLUE, 'const_width': 0.3}
        )

        # Ground line
        ground_y = y - size - 100
        for i in range(-3, 4):
            msp.add_line(
                (x + i * 80, y - size),
                (x + i * 80 - 100, ground_y),
                dxfattribs={'color': colors.BLUE, 'lineweight': 13}
            )

    def _draw_roller_support(self, msp, x: float, y: float, size: float):
        """Draw roller (movable) support"""
        # Triangle
        points = [
            (x, y),
            (x - size / 2, y - size),
            (x + size / 2, y - size),
            (x, y)
        ]
        msp.add_lwpolyline(
            points,
            dxfattribs={'color': colors.BLUE, 'const_width': 0.3}
        )

        # Circle for roller
        roller_radius = size / 2
        msp.add_circle(
            (x, y - size - roller_radius),
            radius=roller_radius,
            dxfattribs={'color': colors.BLUE}
        )

        # Ground line
        ground_y = y - size - 2 * roller_radius - 100
        for i in range(-3, 4):
            msp.add_line(
                (x + i * 80, y - size - 2 * roller_radius),
                (x + i * 80 - 100, ground_y),
                dxfattribs={'color': colors.BLUE, 'lineweight': 13}
            )

    def _add_continuous_beam_dimensions(
        self,
        msp,
        length_mm: float,
        height_mm: float,
        n_spans: int,
        span_length: float
    ):
        """Add dimensions to continuous beam elevation view"""
        try:
            # Total length dimension
            dim = msp.add_linear_dim(
                base=(length_mm / 2, -1200),
                p1=(0, 0),
                p2=(length_mm, 0),
                dimstyle='MM_UNITS',
                override={'dimtxt': 150, 'dimclrt': colors.RED}
            )
            dim.render()

            # Individual span dimensions
            for i in range(n_spans):
                span_start_x = i * span_length
                span_end_x = (i + 1) * span_length
                dim = msp.add_linear_dim(
                    base=(span_start_x + span_length / 2, -600),
                    p1=(span_start_x, 0),
                    p2=(span_end_x, 0),
                    dimstyle='MM_UNITS',
                    override={'dimtxt': 120, 'dimclrt': colors.GREEN}
                )
                dim.render()

            # Height dimension
            dim = msp.add_linear_dim(
                base=(-800, height_mm / 2),
                p1=(0, 0),
                p2=(0, height_mm),
                angle=90,
                dimstyle='MM_UNITS',
                override={'dimtxt': 150, 'dimclrt': colors.RED}
            )
            dim.render()
        except Exception as e:
            print(f"Warning: Could not add dimensions: {e}")

    def _add_section_dimensions(self, msp, doc, width_mm: float, height_mm: float):
        """Add dimensions to section view"""
        try:
            # Calculate actual coordinates (centered)
            start_x = -width_mm / 2
            start_y = 0

            # Width dimension
            dim = msp.add_linear_dim(
                base=(start_x + width_mm / 2, start_y - 200),
                p1=(start_x, start_y),
                p2=(start_x + width_mm, start_y),
                dimstyle='MM_UNITS',
                override={'dimtxt': 150, 'dimclrt': colors.RED}
            )
            dim.render()

            # Height dimension
            dim = msp.add_linear_dim(
                base=(start_x + width_mm + 200, start_y + height_mm / 2),
                p1=(start_x + width_mm, start_y),
                p2=(start_x + width_mm, start_y + height_mm),
                angle=90,
                dimstyle='MM_UNITS',
                override={'dimtxt': 150, 'dimclrt': colors.RED}
            )
            dim.render()
        except Exception as e:
            print(f"Warning: Could not add section dimensions: {e}")

    def _add_continuous_beam_annotations(
        self,
        msp,
        length_mm: float,
        width_mm: float,
        height_mm: float,
        n_spans: int,
        material_name: str
    ):
        """Add text annotations to continuous beam drawing"""
        # Title
        msp.add_text(
            "连续梁立面图",
            dxfattribs={'style': 'CHINESE', 'height': 300, 'color': colors.BLACK}
        ).set_placement(
            (length_mm / 2, height_mm + 800),
            align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER
        )

        # Support annotations
        msp.add_text(
            "铰支座",
            dxfattribs={'style': 'CHINESE', 'height': 150, 'color': colors.BLUE}
        ).set_placement(
            (0, -500),
            align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER
        )

        span_length = length_mm / n_spans
        for i in range(1, n_spans + 1):
            support_x = i * span_length
            msp.add_text(
                "滚动支座",
                dxfattribs={'style': 'CHINESE', 'height': 150, 'color': colors.BLUE}
            ).set_placement(
                (support_x, -500),
                align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER
            )

        # Technical parameters
        param_x = length_mm + 1000
        param_y = height_mm
        line_spacing = 300

        params = [
            "技术参数:",
            f"总跨度 L = {length_mm} mm",
            f"跨数 = {n_spans}",
            f"单跨长度 = {span_length:.0f} mm",
            f"截面宽度 b = {width_mm} mm",
            f"截面高度 h = {height_mm} mm",
            f"材料: {material_name}",
            "支座: " + "支座1: 铰支座" + "".join(
                f"，支座{i+1}: 滚动支座" for i in range(1, n_spans + 1)
            )
        ]

        for i, text in enumerate(params):
            msp.add_text(
                text,
                dxfattribs={'style': 'CHINESE', 'height': 120, 'color': colors.BLACK}
            ).set_placement(
                (param_x, param_y - i * line_spacing),
                align=ezdxf.enums.TextEntityAlignment.LEFT
            )

    def set_output_directory(self, directory: str, subdirectory: str = None) -> None:
        """
        Set output directory for generated drawings

        Args:
            directory: Path to output directory
            subdirectory: Optional subdirectory (ignored for compatibility)
        """
        self.output_dir = directory
        os.makedirs(self.output_dir, exist_ok=True)

