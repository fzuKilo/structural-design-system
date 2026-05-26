"""
Base drawer for CAD drawings
Defines the abstract interface for all structure type drawers
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import os
from pathlib import Path
from datetime import datetime


@dataclass
class DrawingResults:
    """
    Standard format for drawing results
    """
    # Drawing files generated
    plan_view: Optional[str] = None  # Floor plan view (DXF)
    elevation_view: Optional[str] = None  # Elevation view (DXF)
    section_view: Optional[str] = None  # Section view (DXF)
    detail_view: Optional[str] = None  # Detail view (DXF)

    # Metadata
    structure_type: str = ""
    drawing_standard: str = "GB/T 50001-2017"
    scale: str = "1:50"
    units: str = "mm"

    # Timestamp
    generated_at: str = ""

    # Additional data
    metadata: Dict[str, Any] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convert to dictionary format"""
        return {
            'plan_view': self.plan_view,
            'elevation_view': self.elevation_view,
            'section_view': self.section_view,
            'detail_view': self.detail_view,
            'structure_type': self.structure_type,
            'drawing_standard': self.drawing_standard,
            'scale': self.scale,
            'units': self.units,
            'generated_at': self.generated_at,
            'metadata': self.metadata,
            'notes': self.notes
        }

    def get_files(self) -> Dict[str, str]:
        """Get dictionary of available drawing files (only includes files that were actually generated)"""
        return {k: v for k, v in {
            'plan_view': self.plan_view,
            'elevation_view': self.elevation_view,
            'section_view': self.section_view,
            'detail_view': self.detail_view,
        }.items() if v is not None}


class StructureDrawer(ABC):
    """
    Abstract base class for structure drawers

    All concrete drawers (BeamDrawer, FrameDrawer, etc.) must inherit from this class
    and implement the abstract methods.
    """

    def __init__(self):
        """Initialize the drawer"""
        self.structure_type = self._get_structure_type()
        # Find project root dynamically to avoid hardcoding
        _project_root = self._find_project_root()
        self.output_dir = _project_root / "output" / "drawings"
        self.drawing_standard = "GB/T 50001-2017"
        self.scale = "1:50"
        self.units = "mm"

    def _get_structure_type(self) -> str:
        """
        Return the structure type identifier

        Returns:
            Structure type string (e.g., "beam", "frame", "truss")
        """
        return self.__class__.__name__.replace('Drawer', '').lower()

    def _find_project_root(self) -> Path:
        """
        Find the project root directory by searching for common markers.

        Returns:
            Path to the project root directory
        """
        _current_file = Path(__file__).resolve()
        _project_root = _current_file.parent

        while _project_root.parent != _project_root:
            if (_current_file.parent.parent.parent == _project_root and
                (_project_root / "structural_app").exists()):
                return _project_root

            if (_project_root / "config.toml").exists():
                return _project_root

            if (_project_root / "README.md").exists() and (_project_root / "structural_app").exists():
                return _project_root

            _project_root = _project_root.parent

        return _current_file.parent.parent.parent

    @abstractmethod
    def draw_plan(self, design: Dict[str, Any]) -> Optional[str]:
        """
        Draw the plan view (floor plan)

        Args:
            design: Design parameters including:
                - type: Structure type identifier
                - geometry: Geometric parameters
                - material: Material properties
                - loads: Load cases
                - constraints: Boundary conditions

        Returns:
            Path to the generated DXF file, or None if not applicable
        """
        pass

    @abstractmethod
    def draw_elevation(self, design: Dict[str, Any]) -> Optional[str]:
        """
        Draw the elevation view (side view)

        Args:
            design: Design parameters

        Returns:
            Path to the generated DXF file, or None if not applicable
        """
        pass

    @abstractmethod
    def draw_details(self, design: Dict[str, Any]) -> Optional[str]:
        """
        Draw detailed views (node details, section details, etc.)

        Args:
            design: Design parameters

        Returns:
            Path to the generated DXF file, or None if not applicable
        """
        pass

    def generate_drawings(self, design: Dict[str, Any]) -> DrawingResults:
        """
        Generate all applicable drawings for the structure

        Args:
            design: Design parameters

        Returns:
            DrawingResults containing paths to all generated files
        """
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)

        # Generate timestamp for filenames
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Store design for use by drawing methods
        self.design = design

        # Generate drawings and collect results
        results = DrawingResults(
            structure_type=self.structure_type,
            generated_at=datetime.now().isoformat()
        )

        # Generate plan view if applicable
        plan_file = self.draw_plan(design)
        if plan_file:
            results.plan_view = plan_file
            self._add_timestamp_to_file(plan_file, timestamp)
            # Generate PNG preview
            png_file = self._convert_dxf_to_png(plan_file)
            if png_file:
                results.metadata['plan_preview'] = png_file

        # Generate elevation view if applicable
        elev_file = self.draw_elevation(design)
        if elev_file:
            results.elevation_view = elev_file
            self._add_timestamp_to_file(elev_file, timestamp)
            # Generate PNG preview
            png_file = self._convert_dxf_to_png(elev_file)
            if png_file:
                results.metadata['elevation_preview'] = png_file

        # Generate detail views if applicable
        detail_file = self.draw_details(design)
        if detail_file:
            results.detail_view = detail_file
            self._add_timestamp_to_file(detail_file, timestamp)
            # Generate PNG preview
            png_file = self._convert_dxf_to_png(detail_file)
            if png_file:
                results.metadata['detail_preview'] = png_file

        # Add notes
        results.notes = self._generate_notes(design)

        return results

    def _add_timestamp_to_file(self, file_path: str, timestamp: str) -> str:
        """
        Add timestamp to filename if not already present

        Args:
            file_path: Original file path
            timestamp: Timestamp string

        Returns:
            Updated file path with timestamp
        """
        if timestamp not in os.path.basename(file_path):
            base, ext = os.path.splitext(file_path)
            return f"{base}_{timestamp}{ext}"
        return file_path

    def _generate_notes(self, design: Dict[str, Any]) -> List[str]:
        """
        Generate standard notes for the drawings

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

        # Add structure-specific notes
        geometry = design.get('geometry', {})
        if 'length' in geometry:
            notes.append(f"Length: {geometry['length']} m")
        if 'width' in geometry:
            notes.append(f"Width: {geometry['width']} m")
        if 'height' in geometry:
            notes.append(f"Height: {geometry['height']} m")

        return notes

    def set_output_directory(self, directory: str, subdirectory: str = None) -> None:
        """
        Set the output directory for generated drawings

        Args:
            directory: Path to output directory
            subdirectory: Optional subdirectory to append to directory
        """
        if subdirectory:
            self.output_dir = os.path.join(directory, subdirectory)
        else:
            self.output_dir = directory
        os.makedirs(self.output_dir, exist_ok=True)

    def _convert_dxf_to_png(self, dxf_path: str) -> Optional[str]:
        """
        Convert DXF file to PNG for preview

        Args:
            dxf_path: Path to DXF file

        Returns:
            Path to generated PNG file, or None if conversion fails
        """
        try:
            import ezdxf
            from ezdxf.addons.drawing import RenderContext, Frontend
            from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
            import matplotlib
            import matplotlib.pyplot as plt
            from matplotlib import font_manager

            # Chinese font setup for DXF preview rendering
            candidates = ['WenQuanYi Micro Hei', 'WenQuanYi Zen Hei',
                          'Noto Sans CJK SC', 'Microsoft YaHei', 'SimHei', 'SimSun']
            available = {f.name for f in font_manager.fontManager.ttflist}
            for font in candidates:
                if font in available:
                    matplotlib.rcParams['font.family'] = font
                    break
            matplotlib.rcParams['axes.unicode_minus'] = False

            # Let ezdxf find system fonts (it does not scan system dirs by default)
            from pathlib import Path as _Path
            import ezdxf.fonts.fonts as _ezdxf_fonts
            _ezdxf_fonts.font_manager.scan_folder(_Path('/usr/share/fonts'))

            doc = ezdxf.readfile(dxf_path)
            msp = doc.modelspace()

            fig = plt.figure(figsize=(12, 8), dpi=150)
            ax = fig.add_axes([0, 0, 1, 1])
            ctx = RenderContext(doc)
            out = MatplotlibBackend(ax)
            Frontend(ctx, out).draw_layout(msp, finalize=True)

            png_path = dxf_path.replace('.dxf', '_preview.png')
            fig.savefig(png_path, dpi=150, bbox_inches='tight', facecolor='white')
            plt.close(fig)

            return png_path
        except Exception as e:
            print(f"[WARNING] DXF→PNG conversion failed: {e}")
            return None

