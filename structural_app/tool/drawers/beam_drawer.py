"""
Beam drawer using ezdxf
Implements CAD drawing for beam structures
"""

import ezdxf
from ezdxf import colors
import os
from datetime import datetime
from typing import Dict, Any, Optional
from .base_drawer import StructureDrawer, DrawingResults


class BeamDrawer(StructureDrawer):
    """
    Concrete drawer for beam structures using ezdxf

    Generates standard CAD drawings for beams including:
    - Elevation view (side view)
    - Plan view (top view, simplified)
    - Detail views (cross-section details)
    """

    def __init__(self):
        """Initialize beam drawer"""
        super().__init__()

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
            # Default to meters if unknown unit, then convert to mm
            return value * 1000.0

    def _get_structure_type(self) -> str:
        """Return structure type identifier"""
        return "beam"

    def _detect_units(self, geometry: Dict[str, Any], explicit_units: str) -> str:
        """
        Detect units from geometry values if not explicitly specified

        Args:
            geometry: Geometry parameters
            explicit_units: Explicitly specified units from design["units"]

        Returns:
            Detected units ("m" or "mm")
        """
        # If explicitly specified as "mm", return "mm"
        if explicit_units == "mm":
            return "mm"

        # If explicitly specified as "m", use "m"
        if explicit_units == "m":
            # Smart detection: override "m" if values are clearly in mm
            length = geometry.get('length', 0)
            width = geometry.get('width', 0)
            height = geometry.get('height', 0)

            # If any dimension is >= 1000, likely already in mm
            if length >= 1000 or width >= 1000 or height >= 1000:
                return "mm"

            # If any dimension is between 100-1000 and looks like mm (round number)
            if (length > 100 and length < 1000 and length % 100 == 0) or \
               (width > 100 and width < 1000 and width % 100 == 0) or \
               (height > 100 and height < 1000 and height % 100 == 0):
                return "mm"

            return "m"

        # Default to "m" for unknown explicit_units
        return "m"

    def draw_elevation(self, design: Dict[str, Any]) -> Optional[str]:
        """
        Draw the elevation view (side view) of the beam

        Args:
            design: Design parameters including:
                - geometry: {length, width, height, n_elements}
                - material: {E, nu, fy}
                - loads: {distributed, point}
                - constraints: {support_type}
                - units: "m" or "mm" (optional, default "m")

        Returns:
            Path to the generated DXF file
        """
        try:
            # Extract beam parameters
            geometry = design.get('geometry', {})
            explicit_units = design.get('units', 'm')  # Get units, default to "m"
            units = self._detect_units(geometry, explicit_units)  # Smart detection

            # Convert to mm for CAD drawing
            length_mm = self._convert_to_mm(geometry.get('length', 6), units)
            width_mm = self._convert_to_mm(geometry.get('width', 0.3), units)
            height_mm = self._convert_to_mm(geometry.get('height', 0.6), units)

            constraints = design.get('constraints', {})
            support_type = constraints.get('support_type', 'simply_supported')

            # Extract material information
            material = design.get('material', {})
            material_name = material.get('material_name', 'Unknown')

            # Create new DXF document
            doc = ezdxf.new('R2010', setup=True)
            msp = doc.modelspace()

            # Ensure STANDARD text style exists (required for dimensions)
            if 'STANDARD' not in doc.styles:
                doc.styles.new('STANDARD', dxfattribs={'font': 'txt.shx'})

            # Setup Chinese font style
            self._setup_chinese_style(doc)

            # Fix EZDXF dimstyle: change dimlfac from 100 to 1 for correct mm units
            # This fixes the issue where AutoCAD displays 600000 instead of 6000
            # Reference: TD-023 标注显示 100 倍问题修复
            try:
                dimstyle = doc.dimstyles.get('EZDXF')
                if dimstyle:
                    dimstyle.dxf.dimlfac = 1.0
                    dimstyle.dxf.dimtxsty = 'STANDARD'  # Set text style
            except Exception:
                pass  # EZDXF dimstyle not found, skip

            # Create MM_UNITS dimstyle if it doesn't exist (required for dimensions)
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
                dimstyle.dxf.dimtxsty = 'STANDARD'  # Set text style for dimension text

            # Draw beam elevation
            self._draw_beam_elevation(
                msp=msp,
                length_mm=length_mm,
                width_mm=width_mm,
                height_mm=height_mm,
                support_type=support_type,
                material_name=material_name
            )

            # Save file
            os.makedirs(self.output_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.output_dir}/beam_elevation_{timestamp}.dxf"
            doc.saveas(filename)

            return filename

        except Exception as e:
            print(f"Error drawing elevation: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    def draw_plan(self, design: Dict[str, Any]) -> Optional[str]:
        """
        Draw the plan view (top view) of the beam

        Args:
            design: Design parameters including units field

        Returns:
            Path to the generated DXF file
        """
        try:
            # Extract beam parameters
            geometry = design.get('geometry', {})
            explicit_units = design.get('units', 'm')  # Get units, default to "m"
            units = self._detect_units(geometry, explicit_units)  # Smart detection

            # Convert to mm for CAD drawing
            length_mm = self._convert_to_mm(geometry.get('length', 6), units)
            width_mm = self._convert_to_mm(geometry.get('width', 0.3), units)

            # Create new DXF document
            doc = ezdxf.new('R2010')
            msp = doc.modelspace()

            # Ensure STANDARD text style exists (required for dimensions)
            if 'STANDARD' not in doc.styles:
                doc.styles.new('STANDARD', dxfattribs={'font': 'txt.shx'})

            # Setup Chinese font style
            self._setup_chinese_style(doc)

            # Fix EZDXF dimstyle: change dimlfac from 100 to 1 for correct mm units
            # This fixes the issue where AutoCAD displays 600000 instead of 6000
            try:
                dimstyle = doc.dimstyles.get('EZDXF')
                if dimstyle:
                    dimstyle.dxf.dimlfac = 1.0
                    dimstyle.dxf.dimtxsty = 'STANDARD'  # Set text style
            except Exception:
                pass  # EZDXF dimstyle not found, skip

            # Create MM_UNITS dimstyle if it doesn't exist (required for dimensions)
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
                dimstyle.dxf.dimtxsty = 'STANDARD'  # Set text style for dimension text

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
            filename = f"{self.output_dir}/beam_plan_{timestamp}.dxf"
            doc.saveas(filename)

            return filename

        except Exception as e:
            print(f"Error drawing plan: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    def draw_details(self, design: Dict[str, Any]) -> Optional[str]:
        """
        Draw detailed views (cross-section details) of the beam

        Args:
            design: Design parameters including units field

        Returns:
            Path to the generated DXF file
        """
        try:
            # Extract beam parameters
            geometry = design.get('geometry', {})
            explicit_units = design.get('units', 'm')  # Get units, default to "m"
            units = self._detect_units(geometry, explicit_units)  # Smart detection

            # Convert to mm for CAD drawing
            width_mm = self._convert_to_mm(geometry.get('width', 0.3), units)
            height_mm = self._convert_to_mm(geometry.get('height', 0.6), units)

            # Create new DXF document
            doc = ezdxf.new('R2010')
            msp = doc.modelspace()

            # Ensure STANDARD text style exists (required for dimensions)
            if 'STANDARD' not in doc.styles:
                doc.styles.new('STANDARD', dxfattribs={'font': 'txt.shx'})

            # Setup Chinese font style
            self._setup_chinese_style(doc)

            # Fix EZDXF dimstyle: change dimlfac from 100 to 1 for correct mm units
            # This fixes the issue where AutoCAD displays 600000 instead of 6000
            try:
                dimstyle = doc.dimstyles.get('EZDXF')
                if dimstyle:
                    dimstyle.dxf.dimlfac = 1.0
                    dimstyle.dxf.dimtxsty = 'STANDARD'  # Set text style
            except Exception:
                pass  # EZDXF dimstyle not found, skip

            # Create MM_UNITS dimstyle if it doesn't exist (required for dimensions)
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
                dimstyle.dxf.dimtxsty = 'STANDARD'  # Set text style for dimension text

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
            filename = f"{self.output_dir}/beam_detail_{timestamp}.dxf"
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

    def _draw_beam_elevation(
        self,
        msp,
        length_mm: float,
        width_mm: float,
        height_mm: float,
        support_type: str,
        material_name: str
    ):
        """
        Draw beam elevation view

        Args:
            msp: Model space to draw in
            length_mm: Beam length in mm
            width_mm: Beam width in mm
            height_mm: Beam height in mm
            support_type: Type of support (simply_supported, cantilever, fixed_fixed)
            material_name: Material name (e.g., C30, C40)
        """
        # Setup drawing parameters
        beam_start_x = 0
        beam_start_y = 0
        support_size = 400

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
            dxfattribs={'color': colors.WHITE, 'const_width': 15}
        )

        # 2. Draw supports based on type
        if support_type == 'simply_supported':
            # Left: hinge support (triangle)
            self._draw_hinge_support(msp, beam_start_x, beam_start_y, support_size)
            # Right: roller support (triangle + circle)
            self._draw_roller_support(msp, beam_start_x + length_mm, beam_start_y, support_size)
        elif support_type == 'cantilever':
            # Left: fixed support
            self._draw_fixed_support(msp, beam_start_x, beam_start_y, support_size)
        elif support_type == 'fixed_fixed':
            # Both ends fixed
            self._draw_fixed_support(msp, beam_start_x, beam_start_y, support_size)
            self._draw_fixed_support(msp, beam_start_x + length_mm, beam_start_y, support_size)

        # 3. Add dimensions
        self._add_dimensions(msp, length_mm, height_mm)

        # 4. Add text annotations
        self._add_annotations(msp, length_mm, width_mm, height_mm, support_type, material_name)

    def _draw_beam_plan(self, msp, doc, length_mm: float, width_mm: float):
        """
        Draw beam plan view (top view)

        Args:
            msp: Model space to draw in
            doc: DXF document for accessing dimstyle
            length_mm: Beam length in mm
            width_mm: Beam width in mm
        """
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
            dxfattribs={'color': colors.WHITE, 'const_width': 15}
        )

        # Add dimensions using MM_UNITS dimstyle
        try:
            dim = msp.add_linear_dim(
                base=(length_mm / 2, -200),
                p1=(0, 0),
                p2=(length_mm, 0),
                dimstyle='MM_UNITS',
                override={'dimtxt': 150, 'dimclrt': colors.WHITE}
            )
            dim.render()
            # Set explicit text (overwrite the dynamic <>)
            for entity in msp:
                if entity.dxftype() == 'DIMENSION' and entity.dxf.text == '<>':
                    entity.dxf.text = f"{int(length_mm)}"
        except Exception as e:
            print(f"Warning: Could not add plan dimensions: {e}")

        # Add annotations
        msp.add_text(
            "梁平面图",
            dxfattribs={'style': 'CHINESE', 'height': 300, 'color': colors.BLACK}
        ).set_placement(
            (length_mm / 2, width_mm + 500),
            align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER
        )

    def _draw_beam_detail(self, msp, doc, width_mm: float, height_mm: float):
        """
        Draw beam cross-section detail

        Args:
            msp: Model space to draw in
            doc: DXF document for accessing dimstyle
            width_mm: Beam width in mm
            height_mm: Beam height in mm
        """
        # Draw cross-section rectangle with actual width, scaled height
        # This ensures dimensions match the drawn geometry
        section_width = width_mm
        section_height = height_mm  # Use actual height for correct proportions

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
            dxfattribs={'color': colors.WHITE, 'const_width': 15}
        )

        # Add section dimensions
        self._add_section_dimensions(msp, doc, section_width, section_height)

        # Add title
        msp.add_text(
            "梁截面详图",
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
            dxfattribs={'color': colors.WHITE, 'const_width': 0.3}
        )

        # Ground line
        ground_y = y - size - 100
        for i in range(-3, 4):
            msp.add_line(
                (x + i * 80, y - size),
                (x + i * 80 - 100, ground_y),
                dxfattribs={'color': colors.WHITE, 'lineweight': 13}
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
            dxfattribs={'color': colors.WHITE, 'const_width': 0.3}
        )

        # Circle for roller
        roller_radius = size / 2
        msp.add_circle(
            (x, y - size - roller_radius),
            radius=roller_radius,
            dxfattribs={'color': colors.WHITE}
        )

        # Ground line
        ground_y = y - size - 2 * roller_radius - 100
        for i in range(-3, 4):
            msp.add_line(
                (x + i * 80, y - size - 2 * roller_radius),
                (x + i * 80 - 100, ground_y),
                dxfattribs={'color': colors.WHITE, 'lineweight': 13}
            )

    def _draw_fixed_support(self, msp, x: float, y: float, size: float):
        """Draw fixed support (zigzag pattern)"""
        # Zigzag line
        num_lines = 6
        step_y = size / num_lines
        for i in range(num_lines):
            offset = (i % 2) * 30
            msp.add_line(
                (x - 50 + offset, y - i * step_y),
                (x + 50 + offset, y - (i + 1) * step_y),
                dxfattribs={'color': colors.WHITE, 'lineweight': 13}
            )

        # Ground line
        ground_y = y - size - 100
        for i in range(-3, 4):
            msp.add_line(
                (x + i * 80, y - size),
                (x + i * 80 - 100, ground_y),
                dxfattribs={'color': colors.WHITE, 'lineweight': 13}
            )

    def _add_dimensions(self, msp, length_mm: float, height_mm: float):
        """Add dimensions to elevation view"""
        try:
            # Get or create MM_UNITS dimstyle (created in draw methods)
            try:
                dimstyle = msp.doc.dimstyles.get('MM_UNITS')
                if dimstyle:
                    dimstyle.dxf.dimasz = 100
                    dimstyle.dxf.dimtxt = 150
            except Exception:
                pass  # MM_UNITS dimstyle not found, skip

            # Length dimension
            dim = msp.add_linear_dim(
                base=(length_mm / 2, -1200),
                p1=(0, 0),
                p2=(length_mm, 0),
                dimstyle='MM_UNITS',
                override={'dimtxt': 150, 'dimclrt': colors.WHITE}
            )
            dim.render()

            # Height dimension
            dim = msp.add_linear_dim(
                base=(-800, height_mm / 2),
                p1=(0, 0),
                p2=(0, height_mm),
                angle=90,
                dimstyle='MM_UNITS',
                override={'dimtxt': 150, 'dimclrt': colors.WHITE}
            )
            dim.render()
        except Exception as e:
            print(f"Warning: Could not add dimensions: {e}")

    def _add_section_dimensions(self, msp, doc, width_mm: float, height_mm: float):
        """Add dimensions to section view"""
        try:
            # Get or create MM_UNITS dimstyle (created in draw methods)
            try:
                dimstyle = doc.dimstyles.get('MM_UNITS')
                if dimstyle:
                    dimstyle.dxf.dimtxt = 150
            except Exception:
                pass  # MM_UNITS dimstyle not found, skip

            # Calculate actual coordinates (centered)
            start_x = -width_mm / 2
            start_y = 0

            # Width dimension (below the section)
            dim = msp.add_linear_dim(
                base=(start_x + width_mm / 2, start_y - 200),
                p1=(start_x, start_y),
                p2=(start_x + width_mm, start_y),
                dimstyle='MM_UNITS',
                override={'dimtxt': 150, 'dimclrt': colors.WHITE}
            )
            dim.render()
            # Set explicit text (overwrite the dynamic <>)
            for entity in msp:
                if entity.dxftype() == 'DIMENSION' and entity.dxf.text == '<>':
                    entity.dxf.text = f"{int(width_mm)}"

            # Height dimension (to the right of the section)
            dim = msp.add_linear_dim(
                base=(start_x + width_mm + 200, start_y + height_mm / 2),
                p1=(start_x + width_mm, start_y),
                p2=(start_x + width_mm, start_y + height_mm),
                angle=90,
                dimstyle='MM_UNITS',
                override={'dimtxt': 150, 'dimclrt': colors.WHITE}
            )
            dim.render()
            # Set explicit text (overwrite the dynamic <>)
            for entity in msp:
                if entity.dxftype() == 'DIMENSION' and entity.dxf.text == '<>':
                    entity.dxf.text = f"{int(height_mm)}"
        except Exception as e:
            print(f"Warning: Could not add section dimensions: {e}")

    def _add_annotations(self, msp, length_mm: float, width_mm: float, height_mm: float, support_type: str, material_name: str):
        """Add text annotations to drawing"""
        # Title
        msp.add_text(
            "简支梁立面图",
            dxfattribs={'style': 'CHINESE', 'height': 300, 'color': colors.BLACK}
        ).set_placement(
            (length_mm / 2, height_mm + 800),
            align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER
        )

        # Support annotations
        if support_type == 'simply_supported':
            msp.add_text(
                "铰支座",
                dxfattribs={'style': 'CHINESE', 'height': 150, 'color': colors.WHITE}
            ).set_placement(
                (0, -500),
                align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER
            )
            msp.add_text(
                "滚动支座",
                dxfattribs={'style': 'CHINESE', 'height': 150, 'color': colors.WHITE}
            ).set_placement(
                (length_mm, -500),
                align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER
            )

        # Technical parameters
        param_x = length_mm + 1000
        param_y = height_mm
        line_spacing = 300

        params = [
            "技术参数:",
            f"跨度 L = {length_mm} mm",
            f"截面宽度 b = {width_mm} mm",
            f"截面高度 h = {height_mm} mm",
            f"材料: {material_name}",
            f"支座类型: {support_type}"
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
            subdirectory: Optional subdirectory (ignored for compatibility with base class)
        """
        self.output_dir = directory
        os.makedirs(self.output_dir, exist_ok=True)
