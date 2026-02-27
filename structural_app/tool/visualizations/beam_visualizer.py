"""
Beam visualizer for structural design results
Generates static and interactive plots for beam analysis results
"""

import os
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
from typing import Dict, Any

try:
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

from .base_visualizer import BaseVisualizer


class BeamVisualizer(BaseVisualizer):
    """
    Visualizer for beam structure analysis results
    """

    def __init__(self):
        """Initialize the beam visualizer"""
        super().__init__()
        self.structure_type = "beam"

    def generate_static_visualizations(self, design: Dict[str, Any], results: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate static visualizations using matplotlib

        Args:
            design: Design parameters
            results: Analysis results

        Returns:
            Dictionary mapping visualization type to file path
        """
        os.makedirs(self.output_dir, exist_ok=True)

        # Extract data from results
        detailed_results = results.get('detailed_results', {})
        moments = detailed_results.get('moments', [])
        shears = detailed_results.get('shears', [])
        length = design.get('geometry', {}).get('length', 1.0)
        n_elements = design.get('geometry', {}).get('n_elements', 10)

        # Generate x-axis positions
        x = np.linspace(0, length, len(moments) if moments else n_elements + 1)

        # File paths
        base_path = os.path.join(self.output_dir, "beam")
        timestamp = self._get_timestamp()

        files = {}

        # Generate moment diagram
        if moments:
            files['moment_diagram'] = f"{base_path}_moment_{timestamp}.png"
            self._plot_moment_diagram(x, moments, files['moment_diagram'])

        # Generate shear diagram
        if shears:
            files['shear_diagram'] = f"{base_path}_shear_{timestamp}.png"
            self._plot_shear_diagram(x, shears, files['shear_diagram'])

        # Generate deflection curve if available
        max_displacement = results.get('max_displacement_mm', 0)
        if max_displacement > 0:
            files['deflection_curve'] = f"{base_path}_deflection_{timestamp}.png"
            self._plot_deflection_curve(x, moments, files['deflection_curve'], length)

        return files

    def generate_interactive_visualizations(self, design: Dict[str, Any], results: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate interactive visualizations using Plotly

        Args:
            design: Design parameters
            results: Analysis results

        Returns:
            Dictionary mapping visualization type to file path
        """
        if not PLOTLY_AVAILABLE:
            return {}

        os.makedirs(self.output_dir, exist_ok=True)

        # Extract data from results
        detailed_results = results.get('detailed_results', {})
        moments = detailed_results.get('moments', [])
        shears = detailed_results.get('shears', [])
        length = design.get('geometry', {}).get('length', 1.0)
        n_elements = design.get('geometry', {}).get('n_elements', 10)

        # Generate x-axis positions
        x = np.linspace(0, length, len(moments) if moments else n_elements + 1)

        # File paths
        base_path = os.path.join(self.output_dir, "beam")
        timestamp = self._get_timestamp()

        files = {}

        # Generate interactive moment diagram
        if moments:
            files['moment_html'] = f"{base_path}_moment_{timestamp}.html"
            self._plot_interactive_moment(x, moments, files['moment_html'])

        # Generate interactive shear diagram
        if shears:
            files['shear_html'] = f"{base_path}_shear_{timestamp}.html"
            self._plot_interactive_shear(x, shears, files['shear_html'])

        # Generate interactive deflection curve
        max_displacement = results.get('max_displacement_mm', 0)
        if max_displacement > 0:
            files['deflection_html'] = f"{base_path}_deflection_{timestamp}.html"
            self._plot_interactive_deflection(x, moments, files['deflection_html'], length)

        return files

    def _get_timestamp(self) -> str:
        """Get timestamp for filenames"""
        from datetime import datetime
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def _plot_moment_diagram(self, x: np.ndarray, moments: list, filepath: str):
        """Plot bending moment diagram"""
        fig, ax = plt.subplots(figsize=(10, 6))

        ax.plot(x, moments, 'b-', linewidth=2, label='Bending Moment (kN·m)')
        ax.fill_between(x, moments, alpha=0.3, color='blue')

        ax.set_xlabel('Length (m)', fontsize=12)
        ax.set_ylabel('Moment (kN·m)', fontsize=12)
        ax.set_title('Beam Bending Moment Diagram', fontsize=14, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)

        # Zero line
        ax.axhline(y=0, color='k', linestyle='-', linewidth=0.5)

        plt.tight_layout()
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()

    def _plot_shear_diagram(self, x: np.ndarray, shears: list, filepath: str):
        """Plot shear force diagram"""
        fig, ax = plt.subplots(figsize=(10, 6))

        ax.plot(x, shears, 'r-', linewidth=2, label='Shear Force (kN)')
        ax.fill_between(x, shears, alpha=0.3, color='red')

        ax.set_xlabel('Length (m)', fontsize=12)
        ax.set_ylabel('Shear (kN)', fontsize=12)
        ax.set_title('Beam Shear Force Diagram', fontsize=14, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)

        ax.axhline(y=0, color='k', linestyle='-', linewidth=0.5)

        plt.tight_layout()
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()

    def _plot_deflection_curve(self, x: np.ndarray, moments: list, filepath: str, length: float):
        """Plot deflection curve"""
        fig, ax = plt.subplots(figsize=(10, 6))

        # Simple deflection curve approximation (simplified)
        # In real implementation, this would use actual deflection data
        n_points = len(x)
        deflection = np.sin(np.pi * x / length) * 0.001  # Approximate sinusoidal shape

        ax.plot(x, deflection * 1000, 'g-', linewidth=2, label='Deflection (mm)')
        ax.fill_between(x, deflection * 1000, alpha=0.3, color='green')

        ax.set_xlabel('Length (m)', fontsize=12)
        ax.set_ylabel('Deflection (mm)', fontsize=12)
        ax.set_title('Beam Deflection Curve', fontsize=14, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)

        ax.axhline(y=0, color='k', linestyle='-', linewidth=0.5)

        plt.tight_layout()
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()

    def _plot_interactive_moment(self, x: np.ndarray, moments: list, filepath: str):
        """Plot interactive bending moment diagram using Plotly"""
        if not PLOTLY_AVAILABLE:
            return

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=x, y=moments,
            mode='lines+markers',
            name='Bending Moment',
            line=dict(color='blue', width=2)
        ))

        fig.update_layout(
            title='Beam Bending Moment Diagram',
            xaxis_title='Length (m)',
            yaxis_title='Moment (kN·m)',
            hovermode='closest'
        )

        fig.write_html(filepath)

    def _plot_interactive_shear(self, x: np.ndarray, shears: list, filepath: str):
        """Plot interactive shear force diagram using Plotly"""
        if not PLOTLY_AVAILABLE:
            return

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=x, y=shears,
            mode='lines+markers',
            name='Shear Force',
            line=dict(color='red', width=2)
        ))

        fig.update_layout(
            title='Beam Shear Force Diagram',
            xaxis_title='Length (m)',
            yaxis_title='Shear (kN)',
            hovermode='closest'
        )

        fig.write_html(filepath)

    def _plot_interactive_deflection(self, x: np.ndarray, moments: list, filepath: str, length: float):
        """Plot interactive deflection curve using Plotly"""
        if not PLOTLY_AVAILABLE:
            return

        # Simple deflection approximation
        n_points = len(x)
        deflection = np.sin(np.pi * x / length) * 0.001

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=x, y=deflection * 1000,
            mode='lines+markers',
            name='Deflection',
            line=dict(color='green', width=2)
        ))

        fig.update_layout(
            title='Beam Deflection Curve',
            xaxis_title='Length (m)',
            yaxis_title='Deflection (mm)',
            hovermode='closest'
        )

        fig.write_html(filepath)
