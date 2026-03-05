"""
Beam visualizer for structural design results
Generates static and interactive plots for beam analysis results with cloud plot effects
"""

import os
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.colors import Normalize
import matplotlib.patches as patches
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
    Generates cloud plots with support visualization and deformation display
    """

    def __init__(self):
        """Initialize the beam visualizer"""
        super().__init__()
        self.structure_type = "beam"

    def generate_static_visualizations(self, design: Dict[str, Any], results: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate static visualizations using matplotlib with cloud plot effects

        Args:
            design: Design parameters
            results: Analysis results

        Returns:
            Dictionary mapping visualization type to file path
        """
        print(f"[BeamVisualizer] Starting static visualization generation...")
        print(f"[BeamVisualizer] Output directory: {self.output_dir}")

        try:
            os.makedirs(self.output_dir, exist_ok=True)
            print(f"[BeamVisualizer] Output directory created/verified")
        except Exception as e:
            print(f"[BeamVisualizer] ERROR: Failed to create output directory: {e}")
            import traceback
            traceback.print_exc()
            return {}

        # Extract data from results
        if 'results' in results:
            actual_results = results['results']
        else:
            actual_results = results

        detailed_results = actual_results.get('detailed_results', {})

        # Extract all required data
        nodes_data = detailed_results.get('nodes', [])
        displacements = detailed_results.get('displacements', [])
        moments = detailed_results.get('moments', [])
        shears = detailed_results.get('shears', [])
        stresses = detailed_results.get('stresses', [])

        length = design.get('geometry', {}).get('length', 1.0)
        height = design.get('geometry', {}).get('height', 0.6)
        n_elements = design.get('geometry', {}).get('n_elements', 10)

        print(f"[BeamVisualizer] Data extracted:")
        print(f"  - Nodes: {len(nodes_data)} points")
        print(f"  - Displacements: {len(displacements)} points")
        print(f"  - Moments: {len(moments)} points")
        print(f"  - Shears: {len(shears)} points")
        print(f"  - Stresses: {len(stresses)} points")
        print(f"  - Length: {length} m")
        print(f"  - Height: {height} m")

        # Convert nodes to numpy array
        if nodes_data:
            nodes = np.array(nodes_data)
        else:
            # Fallback: generate nodes if not available
            nodes = np.array([[i * length / n_elements, 0.0] for i in range(n_elements + 1)])

        # File paths
        base_path = os.path.join(self.output_dir, "beam")
        timestamp = self._get_timestamp()
        print(f"[BeamVisualizer] Timestamp: {timestamp}")

        files = {}

        # Generate displacement cloud plot
        if displacements and len(displacements) > 0:
            files['displacement_cloud'] = f"{base_path}_displacement_cloud_{timestamp}.png"
            print(f"[BeamVisualizer] Generating displacement cloud plot: {files['displacement_cloud']}")
            try:
                self._plot_displacement_cloud(nodes, displacements, files['displacement_cloud'], length)
                if os.path.exists(files['displacement_cloud']):
                    print(f"[BeamVisualizer] SUCCESS: Displacement cloud plot created")
                else:
                    print(f"[BeamVisualizer] WARNING: Displacement cloud plot file not found after plotting")
            except Exception as e:
                print(f"[BeamVisualizer] ERROR: Failed to generate displacement cloud plot: {e}")
                import traceback
                traceback.print_exc()
                del files['displacement_cloud']
        else:
            print(f"[BeamVisualizer] SKIP: No displacement data available")

        # Generate moment cloud plot
        if moments and len(moments) > 0:
            files['moment_cloud'] = f"{base_path}_moment_cloud_{timestamp}.png"
            print(f"[BeamVisualizer] Generating moment cloud plot: {files['moment_cloud']}")
            try:
                self._plot_moment_cloud(nodes, moments, files['moment_cloud'], length, n_elements)
                if os.path.exists(files['moment_cloud']):
                    print(f"[BeamVisualizer] SUCCESS: Moment cloud plot created")
                else:
                    print(f"[BeamVisualizer] WARNING: Moment cloud plot file not found after plotting")
            except Exception as e:
                print(f"[BeamVisualizer] ERROR: Failed to generate moment cloud plot: {e}")
                import traceback
                traceback.print_exc()
                del files['moment_cloud']
        else:
            print(f"[BeamVisualizer] SKIP: No moment data available")

        # Generate stress cloud plot
        if stresses and len(stresses) > 0:
            files['stress_cloud'] = f"{base_path}_stress_cloud_{timestamp}.png"
            print(f"[BeamVisualizer] Generating stress cloud plot: {files['stress_cloud']}")
            try:
                self._plot_stress_cloud(nodes, stresses, files['stress_cloud'], length, n_elements)
                if os.path.exists(files['stress_cloud']):
                    print(f"[BeamVisualizer] SUCCESS: Stress cloud plot created")
                else:
                    print(f"[BeamVisualizer] WARNING: Stress cloud plot file not found after plotting")
            except Exception as e:
                print(f"[BeamVisualizer] ERROR: Failed to generate stress cloud plot: {e}")
                import traceback
                traceback.print_exc()
                del files['stress_cloud']
        else:
            print(f"[BeamVisualizer] SKIP: No stress data available")

        # Generate moment diagram (traditional style with annotation)
        if moments and len(moments) > 0:
            files['moment_diagram'] = f"{base_path}_moment_diagram_{timestamp}.png"
            print(f"[BeamVisualizer] Generating moment diagram: {files['moment_diagram']}")
            try:
                self._plot_moment_diagram(nodes, moments, files['moment_diagram'], length, n_elements)
                if os.path.exists(files['moment_diagram']):
                    print(f"[BeamVisualizer] SUCCESS: Moment diagram created")
                else:
                    print(f"[BeamVisualizer] WARNING: Moment diagram file not found after plotting")
            except Exception as e:
                print(f"[BeamVisualizer] ERROR: Failed to generate moment diagram: {e}")
                import traceback
                traceback.print_exc()
                del files['moment_diagram']

        print(f"[BeamVisualizer] Static visualization complete. Generated {len(files)} files")
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
            print(f"[BeamVisualizer] WARNING: Plotly not available, skipping interactive visualizations")
            return {}

        print(f"[BeamVisualizer] Starting interactive visualization generation...")

        try:
            os.makedirs(self.output_dir, exist_ok=True)
        except Exception as e:
            print(f"[BeamVisualizer] ERROR: Failed to create output directory: {e}")
            import traceback
            traceback.print_exc()
            return {}

        # Extract data from results
        if 'results' in results:
            actual_results = results['results']
        else:
            actual_results = results

        detailed_results = actual_results.get('detailed_results', {})

        # Extract all required data
        nodes_data = detailed_results.get('nodes', [])
        displacements = detailed_results.get('displacements', [])
        moments = detailed_results.get('moments', [])
        shears = detailed_results.get('shears', [])
        stresses = detailed_results.get('stresses', [])

        length = design.get('geometry', {}).get('length', 1.0)
        n_elements = design.get('geometry', {}).get('n_elements', 10)

        # Convert nodes to numpy array
        if nodes_data:
            nodes = np.array(nodes_data)
        else:
            nodes = np.array([[i * length / n_elements, 0.0] for i in range(n_elements + 1)])

        # File paths
        base_path = os.path.join(self.output_dir, "beam")
        timestamp = self._get_timestamp()

        files = {}

        # Generate interactive displacement plot
        if displacements and len(displacements) > 0:
            files['displacement_html'] = f"{base_path}_displacement_{timestamp}.html"
            print(f"[BeamVisualizer] Generating interactive displacement plot: {files['displacement_html']}")
            try:
                self._plot_interactive_displacement(nodes, displacements, files['displacement_html'], n_elements)
                if os.path.exists(files['displacement_html']):
                    print(f"[BeamVisualizer] SUCCESS: Interactive displacement plot created")
                else:
                    print(f"[BeamVisualizer] WARNING: Interactive displacement plot file not found after plotting")
            except Exception as e:
                print(f"[BeamVisualizer] ERROR: Failed to generate interactive displacement plot: {e}")
                import traceback
                traceback.print_exc()
                del files['displacement_html']

        # Generate interactive moment plot
        if moments and len(moments) > 0:
            files['moment_html'] = f"{base_path}_moment_{timestamp}.html"
            print(f"[BeamVisualizer] Generating interactive moment plot: {files['moment_html']}")
            try:
                self._plot_interactive_moment(nodes, moments, files['moment_html'], n_elements)
                if os.path.exists(files['moment_html']):
                    print(f"[BeamVisualizer] SUCCESS: Interactive moment plot created")
                else:
                    print(f"[BeamVisualizer] WARNING: Interactive moment plot file not found after plotting")
            except Exception as e:
                print(f"[BeamVisualizer] ERROR: Failed to generate interactive moment plot: {e}")
                import traceback
                traceback.print_exc()
                del files['moment_html']

        # Generate interactive stress plot
        if stresses and len(stresses) > 0:
            files['stress_html'] = f"{base_path}_stress_{timestamp}.html"
            print(f"[BeamVisualizer] Generating interactive stress plot: {files['stress_html']}")
            try:
                self._plot_interactive_stress(nodes, stresses, files['stress_html'], n_elements)
                if os.path.exists(files['stress_html']):
                    print(f"[BeamVisualizer] SUCCESS: Interactive stress plot created")
                else:
                    print(f"[BeamVisualizer] WARNING: Interactive stress plot file not found after plotting")
            except Exception as e:
                print(f"[BeamVisualizer] ERROR: Failed to generate interactive stress plot: {e}")
                import traceback
                traceback.print_exc()
                del files['stress_html']

        print(f"[BeamVisualizer] Interactive visualization complete. Generated {len(files)} files")
        return files

    def _get_timestamp(self) -> str:
        """Get timestamp for filenames"""
        from datetime import datetime
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def _plot_displacement_cloud(self, nodes: np.ndarray, displacements: list, filepath: str, length: float):
        """
        Plot displacement cloud with deformation visualization
        """
        displacements = np.array(displacements)
        n_elem = len(nodes) - 1

        # Create deformed nodes (scale deformation for visibility)
        scale = 1000  # Deformation scale factor
        deformed_nodes = nodes.copy()
        deformed_nodes[:, 1] += displacements * scale

        # Create line segments and colors
        segments = []
        colors = []

        for i in range(n_elem):
            segment = [deformed_nodes[i], deformed_nodes[i+1]]
            segments.append(segment)
            # Color based on displacement magnitude
            color_value = abs(displacements[i])
            colors.append(color_value)

        # Create figure
        fig, ax = plt.subplots(figsize=(14, 6))

        # Draw original shape (gray dashed line)
        ax.plot(nodes[:, 0], nodes[:, 1], 'k--', linewidth=1, alpha=0.3, label='Original Shape')

        # Draw deformed shape with color cloud
        lc = LineCollection(segments, cmap='jet',
                            norm=Normalize(vmin=0, vmax=max(colors) if colors else 1),
                            linewidths=8)
        lc.set_array(np.array(colors))

        ax.add_collection(lc)

        # Add colorbar
        cbar = plt.colorbar(lc, ax=ax, label='Displacement (m)')
        cbar.ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x*1000:.2f} mm'))

        # Draw supports
        support_size = 0.2
        # Left support (fixed hinge)
        triangle1 = patches.Polygon([[nodes[0, 0]-support_size/2, 0],
                                      [nodes[0, 0]+support_size/2, 0],
                                      [nodes[0, 0], -support_size]],
                                     closed=True, facecolor='gray', edgecolor='black')
        ax.add_patch(triangle1)

        # Right support (roller hinge)
        triangle2 = patches.Polygon([[nodes[-1, 0]-support_size/2, 0],
                                      [nodes[-1, 0]+support_size/2, 0],
                                      [nodes[-1, 0], -support_size]],
                                     closed=True, facecolor='gray', edgecolor='black')
        ax.add_patch(triangle2)
        circle = patches.Circle((nodes[-1, 0], -support_size), support_size/3,
                                facecolor='white', edgecolor='black')
        ax.add_patch(circle)

        # Calculate display range
        y_min = min(deformed_nodes[:, 1].min(), -support_size - 0.1)
        y_max = max(deformed_nodes[:, 1].max(), 0.5)
        y_range = y_max - y_min

        ax.set_xlim(-0.5, length + 0.5)
        ax.set_ylim(y_min - y_range*0.1, y_max + y_range*0.1)
        ax.set_aspect('equal')
        ax.grid(True, alpha=0.3)
        ax.set_xlabel('Length (m)', fontsize=12)
        ax.set_ylabel('Height (m)', fontsize=12)
        ax.set_title(f'Displacement Cloud Plot (Deformation Scale: {scale}x)', fontsize=14, fontweight='bold')
        ax.legend()

        plt.tight_layout()
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()

    def _plot_moment_cloud(self, nodes: np.ndarray, moments: list, filepath: str, length: float, n_elem: int):
        """
        Plot bending moment cloud
        """
        moments = np.array(moments)

        # Calculate element centers
        elem_centers = []
        for i in range(n_elem):
            center_x = (nodes[i, 0] + nodes[i+1, 0]) / 2
            center_y = (nodes[i, 1] + nodes[i+1, 1]) / 2
            elem_centers.append([center_x, center_y])
        elem_centers = np.array(elem_centers)

        # Create line segments
        segments = []
        for i in range(n_elem):
            segment = [nodes[i], nodes[i+1]]
            segments.append(segment)

        # Create figure
        fig, ax = plt.subplots(figsize=(14, 6))

        # Draw color cloud
        lc = LineCollection(segments, cmap='RdYlBu_r',
                            norm=Normalize(vmin=0, vmax=max(moments) if len(moments) > 0 else 1),
                            linewidths=10)
        lc.set_array(moments)

        ax.add_collection(lc)

        # Add colorbar
        cbar = plt.colorbar(lc, ax=ax, label='Bending Moment (N·m)')
        cbar.ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1000:.1f} kN·m'))

        # Draw supports
        support_size = 0.2
        triangle1 = patches.Polygon([[nodes[0, 0]-support_size/2, 0],
                                      [nodes[0, 0]+support_size/2, 0],
                                      [nodes[0, 0], -support_size]],
                                     closed=True, facecolor='gray', edgecolor='black')
        ax.add_patch(triangle1)

        triangle2 = patches.Polygon([[nodes[-1, 0]-support_size/2, 0],
                                      [nodes[-1, 0]+support_size/2, 0],
                                      [nodes[-1, 0], -support_size]],
                                     closed=True, facecolor='gray', edgecolor='black')
        ax.add_patch(triangle2)
        circle = patches.Circle((nodes[-1, 0], -support_size), support_size/3,
                                facecolor='white', edgecolor='black')
        ax.add_patch(circle)

        ax.set_xlim(-0.5, length + 0.5)
        ax.set_ylim(-0.5, 0.5)
        ax.set_aspect('equal')
        ax.grid(True, alpha=0.3)
        ax.set_xlabel('Length (m)', fontsize=12)
        ax.set_ylabel('Height (m)', fontsize=12)
        ax.set_title('Bending Moment Cloud Plot', fontsize=14, fontweight='bold')

        plt.tight_layout()
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()

    def _plot_stress_cloud(self, nodes: np.ndarray, stresses: list, filepath: str, length: float, n_elem: int):
        """
        Plot stress cloud
        """
        stresses = np.array(stresses)

        # Create line segments
        segments = []
        for i in range(n_elem):
            segment = [nodes[i], nodes[i+1]]
            segments.append(segment)

        # Create figure
        fig, ax = plt.subplots(figsize=(14, 6))

        # Draw color cloud
        lc = LineCollection(segments, cmap='coolwarm',
                            norm=Normalize(vmin=0, vmax=max(stresses) if len(stresses) > 0 else 1),
                            linewidths=10)
        lc.set_array(stresses)

        ax.add_collection(lc)

        # Add colorbar
        cbar = plt.colorbar(lc, ax=ax, label='Bending Stress (Pa)')
        cbar.ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1e6:.2f} MPa'))

        # Draw supports
        support_size = 0.2
        triangle1 = patches.Polygon([[nodes[0, 0]-support_size/2, 0],
                                      [nodes[0, 0]+support_size/2, 0],
                                      [nodes[0, 0], -support_size]],
                                     closed=True, facecolor='gray', edgecolor='black')
        ax.add_patch(triangle1)

        triangle2 = patches.Polygon([[nodes[-1, 0]-support_size/2, 0],
                                      [nodes[-1, 0]+support_size/2, 0],
                                      [nodes[-1, 0], -support_size]],
                                     closed=True, facecolor='gray', edgecolor='black')
        ax.add_patch(triangle2)
        circle = patches.Circle((nodes[-1, 0], -support_size), support_size/3,
                                facecolor='white', edgecolor='black')
        ax.add_patch(circle)

        ax.set_xlim(-0.5, length + 0.5)
        ax.set_ylim(-0.5, 0.5)
        ax.set_aspect('equal')
        ax.grid(True, alpha=0.3)
        ax.set_xlabel('Length (m)', fontsize=12)
        ax.set_ylabel('Height (m)', fontsize=12)
        ax.set_title('Bending Stress Cloud Plot', fontsize=14, fontweight='bold')

        plt.tight_layout()
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()

    def _plot_moment_diagram(self, nodes: np.ndarray, moments: list, filepath: str, length: float, n_elem: int):
        """
        Plot traditional moment diagram with fill and annotation
        """
        moments = np.array(moments)

        # Calculate element centers
        elem_centers_x = []
        for i in range(n_elem):
            center_x = (nodes[i, 0] + nodes[i+1, 0]) / 2
            elem_centers_x.append(center_x)

        fig, ax = plt.subplots(figsize=(14, 6))

        # Draw beam outline
        ax.plot([0, length], [0, 0], 'k-', linewidth=3, label='Beam')

        # Draw moment diagram (downward is positive)
        moment_scale = 0.00005  # Scale factor
        moment_y = -moments * moment_scale

        # Fill moment diagram
        ax.fill_between(elem_centers_x, 0, moment_y, alpha=0.6, color='red', label='Bending Moment')
        ax.plot(elem_centers_x, moment_y, 'r-', linewidth=2)

        # Draw supports
        support_size = 0.3
        triangle1 = patches.Polygon([[nodes[0, 0]-support_size/2, 0],
                                      [nodes[0, 0]+support_size/2, 0],
                                      [nodes[0, 0], -support_size]],
                                     closed=True, facecolor='gray', edgecolor='black')
        ax.add_patch(triangle1)

        triangle2 = patches.Polygon([[nodes[-1, 0]-support_size/2, 0],
                                      [nodes[-1, 0]+support_size/2, 0],
                                      [nodes[-1, 0], -support_size]],
                                     closed=True, facecolor='gray', edgecolor='black')
        ax.add_patch(triangle2)
        circle = patches.Circle((nodes[-1, 0], -support_size), support_size/3,
                                facecolor='white', edgecolor='black')
        ax.add_patch(circle)

        # Annotate maximum moment
        max_moment_idx = np.argmax(moments)
        max_moment = moments[max_moment_idx]
        max_moment_x = elem_centers_x[max_moment_idx]
        max_moment_y = moment_y[max_moment_idx]
        ax.annotate(f'Max M = {max_moment/1000:.2f} kN·m',
                    xy=(max_moment_x, max_moment_y),
                    xytext=(max_moment_x, max_moment_y - 0.5),
                    fontsize=12, fontweight='bold',
                    ha='center',
                    bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.7),
                    arrowprops=dict(arrowstyle='->', lw=2))

        ax.set_xlim(-0.5, length + 0.5)
        ax.set_ylim(-3, 0.5)
        ax.grid(True, alpha=0.3)
        ax.set_xlabel('Length (m)', fontsize=12)
        ax.set_ylabel('Bending Moment', fontsize=12)
        ax.set_title('Bending Moment Diagram', fontsize=14, fontweight='bold')
        ax.legend(fontsize=11)

        plt.tight_layout()
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()

    def _plot_interactive_displacement(self, nodes: np.ndarray, displacements: list, filepath: str, n_elem: int):
        """
        Plot interactive displacement cloud using Plotly
        """
        if not PLOTLY_AVAILABLE:
            return

        displacements = np.array(displacements)

        # Create deformed coordinates (scale deformation)
        scale = 1000
        deformed_y = displacements * scale

        fig = go.Figure()

        # Add original shape (gray dashed line)
        fig.add_trace(go.Scatter(
            x=nodes[:, 0],
            y=nodes[:, 1],
            mode='lines',
            line=dict(color='gray', width=2, dash='dash'),
            name='Original Shape',
            hoverinfo='skip'
        ))

        # Add deformed colored segments
        for i in range(n_elem):
            # Calculate color (based on displacement magnitude)
            disp_value = abs(displacements[i])
            color_intensity = disp_value / abs(displacements).max() if abs(displacements).max() > 0 else 0

            fig.add_trace(go.Scatter(
                x=[nodes[i, 0], nodes[i+1, 0]],
                y=[deformed_y[i], deformed_y[i+1]],
                mode='lines',
                line=dict(
                    color=f'rgb({int(255*color_intensity)}, {int(100*(1-color_intensity))}, {int(255*(1-color_intensity))})',
                    width=8
                ),
                name=f'Element {i+1}',
                hovertemplate=(
                    f'<b>Element {i+1}</b><br>' +
                    f'Position: %{{x:.2f}} m<br>' +
                    f'Displacement: {abs(displacements[i])*1000:.3f} mm<br>' +
                    '<extra></extra>'
                ),
                showlegend=False
            ))

        # Add support markers
        fig.add_trace(go.Scatter(
            x=[nodes[0, 0], nodes[-1, 0]],
            y=[0, 0],
            mode='markers',
            marker=dict(size=15, color='black', symbol='triangle-down'),
            name='Supports',
            hovertemplate='<b>Support</b><extra></extra>'
        ))

        # Layout settings
        fig.update_layout(
            title=dict(
                text=f'Interactive Displacement Cloud Plot (Deformation Scale: {scale}x)',
                font=dict(size=18, family='Arial', color='black')
            ),
            xaxis=dict(
                title='Length (m)',
                gridcolor='lightgray',
                showgrid=True
            ),
            yaxis=dict(
                title='Height (m)',
                gridcolor='lightgray',
                showgrid=True,
                scaleanchor='x',
                scaleratio=1
            ),
            hovermode='closest',
            plot_bgcolor='white',
            width=1200,
            height=500,
            showlegend=True
        )

        fig.write_html(filepath)

    def _plot_interactive_moment(self, nodes: np.ndarray, moments: list, filepath: str, n_elem: int):
        """
        Plot interactive moment cloud using Plotly
        """
        if not PLOTLY_AVAILABLE:
            return

        moments = np.array(moments)

        # Calculate element centers
        elem_centers_x = []
        for i in range(n_elem):
            center_x = (nodes[i, 0] + nodes[i+1, 0]) / 2
            elem_centers_x.append(center_x)

        fig = go.Figure()

        # Add colored segments (based on moment magnitude)
        for i in range(n_elem):
            # Calculate color (based on moment magnitude)
            moment_ratio = moments[i] / moments.max() if moments.max() > 0 else 0

            fig.add_trace(go.Scatter(
                x=[nodes[i, 0], nodes[i+1, 0]],
                y=[0, 0],
                mode='lines',
                line=dict(
                    color=f'rgb({int(255*moment_ratio)}, {int(255*(1-moment_ratio)*0.5)}, {int(255*(1-moment_ratio))})',
                    width=12
                ),
                name=f'Element {i+1}',
                hovertemplate=(
                    f'<b>Element {i+1}</b><br>' +
                    f'Position: {elem_centers_x[i]:.2f} m<br>' +
                    f'Moment: {moments[i]/1000:.2f} kN·m<br>' +
                    '<extra></extra>'
                ),
                showlegend=False
            ))

        # Add support markers
        fig.add_trace(go.Scatter(
            x=[nodes[0, 0], nodes[-1, 0]],
            y=[0, 0],
            mode='markers',
            marker=dict(size=15, color='black', symbol='triangle-down'),
            name='Supports',
            hovertemplate='<b>Support</b><extra></extra>'
        ))

        # Annotate maximum moment
        max_moment_idx = np.argmax(moments)
        max_moment = moments[max_moment_idx]
        max_moment_x = elem_centers_x[max_moment_idx]

        fig.add_annotation(
            x=max_moment_x,
            y=0.1,
            text=f'Max Moment: {max_moment/1000:.2f} kN·m',
            showarrow=True,
            arrowhead=2,
            arrowsize=1,
            arrowwidth=2,
            arrowcolor='red',
            ax=0,
            ay=-40,
            bgcolor='yellow',
            bordercolor='red',
            borderwidth=2,
            font=dict(size=12, color='black')
        )

        # Layout settings
        fig.update_layout(
            title=dict(
                text='Interactive Bending Moment Cloud Plot',
                font=dict(size=18, family='Arial', color='black')
            ),
            xaxis=dict(
                title='Length (m)',
                gridcolor='lightgray',
                showgrid=True
            ),
            yaxis=dict(
                title='',
                gridcolor='lightgray',
                showgrid=True,
                range=[-0.3, 0.3]
            ),
            hovermode='closest',
            plot_bgcolor='white',
            width=1200,
            height=400,
            showlegend=True
        )

        fig.write_html(filepath)

    def _plot_interactive_stress(self, nodes: np.ndarray, stresses: list, filepath: str, n_elem: int):
        """
        Plot interactive stress cloud using Plotly
        """
        if not PLOTLY_AVAILABLE:
            return

        stresses = np.array(stresses)

        # Calculate element centers
        elem_centers_x = []
        for i in range(n_elem):
            center_x = (nodes[i, 0] + nodes[i+1, 0]) / 2
            elem_centers_x.append(center_x)

        fig = go.Figure()

        # Add colored segments (based on stress magnitude)
        for i in range(n_elem):
            # Calculate color (based on stress magnitude)
            stress_ratio = stresses[i] / stresses.max() if stresses.max() > 0 else 0

            fig.add_trace(go.Scatter(
                x=[nodes[i, 0], nodes[i+1, 0]],
                y=[0, 0],
                mode='lines',
                line=dict(
                    color=f'rgb({int(255*stress_ratio)}, {int(100*(1-stress_ratio))}, {int(255*(1-stress_ratio))})',
                    width=12
                ),
                name=f'Element {i+1}',
                hovertemplate=(
                    f'<b>Element {i+1}</b><br>' +
                    f'Position: {elem_centers_x[i]:.2f} m<br>' +
                    f'Stress: {stresses[i]/1e6:.2f} MPa<br>' +
                    '<extra></extra>'
                ),
                showlegend=False
            ))

        # Add support markers
        fig.add_trace(go.Scatter(
            x=[nodes[0, 0], nodes[-1, 0]],
            y=[0, 0],
            mode='markers',
            marker=dict(size=15, color='black', symbol='triangle-down'),
            name='Supports',
            hovertemplate='<b>Support</b><extra></extra>'
        ))

        # Annotate maximum stress
        max_stress_idx = np.argmax(stresses)
        max_stress = stresses[max_stress_idx]
        max_stress_x = elem_centers_x[max_stress_idx]

        fig.add_annotation(
            x=max_stress_x,
            y=0.1,
            text=f'Max Stress: {max_stress/1e6:.2f} MPa',
            showarrow=True,
            arrowhead=2,
            arrowsize=1,
            arrowwidth=2,
            arrowcolor='red',
            ax=0,
            ay=-40,
            bgcolor='yellow',
            bordercolor='red',
            borderwidth=2,
            font=dict(size=12, color='black')
        )

        # Layout settings
        fig.update_layout(
            title=dict(
                text='Interactive Bending Stress Cloud Plot',
                font=dict(size=18, family='Arial', color='black')
            ),
            xaxis=dict(
                title='Length (m)',
                gridcolor='lightgray',
                showgrid=True
            ),
            yaxis=dict(
                title='',
                gridcolor='lightgray',
                showgrid=True,
                range=[-0.3, 0.3]
            ),
            hovermode='closest',
            plot_bgcolor='white',
            width=1200,
            height=400,
            showlegend=True
        )

        fig.write_html(filepath)
