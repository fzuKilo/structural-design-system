"""
Base drawer for CAD drawings
Defines the abstract interface for all structure type drawers
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import os
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
        """Get dictionary of available drawing files"""
        return {
            'plan_view': self.plan_view,
            'elevation_view': self.elevation_view,
            'section_view': self.section_view,
            'detail_view': self.detail_view
        }


class StructureDrawer(ABC):
    """
    Abstract base class for structure drawers

    All concrete drawers (BeamDrawer, FrameDrawer, etc.) must inherit from this class
    and implement the abstract methods.
    """

    def __init__(self):
        """Initialize the drawer"""
        self.structure_type = self._get_structure_type()
        self.output_dir = "output/drawings"
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

        # Generate elevation view if applicable
        elev_file = self.draw_elevation(design)
        if elev_file:
            results.elevation_view = elev_file
            self._add_timestamp_to_file(elev_file, timestamp)

        # Generate detail views if applicable
        detail_file = self.draw_details(design)
        if detail_file:
            results.detail_view = detail_file
            self._add_timestamp_to_file(detail_file, timestamp)

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

    def set_output_directory(self, directory: str) -> None:
        """
        Set the output directory for generated drawings

        Args:
            directory: Path to output directory
        """
        self.output_dir = directory
        os.makedirs(self.output_dir, exist_ok=True)
