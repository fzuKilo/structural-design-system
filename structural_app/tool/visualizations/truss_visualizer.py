"""
Truss visualizer for structural design results
Generates static and interactive plots for truss analysis results
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


class TrussVisualizer(BaseVisualizer):
    """
    Visualizer for truss structure analysis results
    Generates topology plots, displacement clouds, and stress distributions
    """

    def __init__(self):
        """Initialize the truss visualizer"""
        super().__init__()
        self.structure_type = "truss"

    def generate_static_visualizations(self, design: Dict[str, Any], results: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate static visualizations using matplotlib

        Args:
            design: Design parameters
            results: Analysis results

        Returns:
            Dictionary mapping visualization type to file path
        """
        print(f"[TrussVisualizer] Starting static visualization generation...")
        print(f"[TrussVisualizer] Output directory: {self.output_dir}")

        try:
            os.makedirs(self.output_dir, exist_ok=True)
            print(f"[TrussVisualizer] Output directory created/verified")
        except Exception as e:
            print(f"[TrussVisualizer] ERROR: Failed to create output directory: {e}")
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
        stresses = detailed_results.get('stresses', [])

        geometry = design.get('geometry', {})
        span = geometry.get('span') or geometry.get('length', 10.0)
        height = geometry.get('height', 2.0)
        # Infer n_panels from nodes array (bottom + top rows, each n_panels+1 nodes)
        if nodes_data:
            n_panels = len(nodes_data) // 2 - 1
        else:
            n_panels = geometry.get('n_panels') or geometry.get('n_elements', 5)

        print(f"[TrussVisualizer] Data extracted:")
        print(f"  - Nodes: {len(nodes_data)} points")
        print(f"  - Displacements: {len(displacements)} points")
        print(f"  - Stresses: {len(stresses)} points")
        print(f"  - Span: {span} m")
        print(f"  - Height: {height} m")
        print(f"  - Panels: {n_panels}")

        # Convert nodes to numpy array
        nodes = np.array(nodes_data) if nodes_data else np.array([])

        # File paths
        base_path = os.path.join(self.output_dir, "truss")
        timestamp = self._get_timestamp()
        print(f"[TrussVisualizer] Timestamp: {timestamp}")

        files = {}

        # 1. Displacement cloud plot
        disp_file = f"{base_path}_displacement_cloud_{timestamp}.png"
        files['displacement_cloud'] = disp_file
        print(f"[TrussVisualizer] Generating displacement cloud plot: {disp_file}")
        try:
            self._plot_displacement_cloud(nodes, displacements, disp_file, span, height, n_panels)
            print(f"[TrussVisualizer] SUCCESS: Displacement cloud plot created")
        except Exception as e:
            print(f"[TrussVisualizer] ERROR: Failed to generate displacement cloud: {e}")
            import traceback
            traceback.print_exc()

        # 2. Stress cloud plot
        stress_file = f"{base_path}_stress_cloud_{timestamp}.png"
        files['stress_cloud'] = stress_file
        print(f"[TrussVisualizer] Generating stress cloud plot: {stress_file}")
        try:
            self._plot_stress_cloud(nodes, stresses, stress_file, span, height, n_panels)
            print(f"[TrussVisualizer] SUCCESS: Stress cloud plot created")
        except Exception as e:
            print(f"[TrussVisualizer] ERROR: Failed to generate stress cloud: {e}")
            import traceback
            traceback.print_exc()

        # 3. Truss topology with deformation
        topo_file = f"{base_path}_topology_{timestamp}.png"
        files['topology'] = topo_file
        print(f"[TrussVisualizer] Generating topology plot: {topo_file}")
        try:
            self._plot_topology(nodes, displacements, topo_file, span, height, n_panels)
            print(f"[TrussVisualizer] SUCCESS: Topology plot created")
        except Exception as e:
            print(f"[TrussVisualizer] ERROR: Failed to generate topology: {e}")
            import traceback
            traceback.print_exc()

        print(f"[TrussVisualizer] Static visualization complete. Generated {len(files)} files")
        return files

    def generate_interactive_visualizations(self, design: Dict[str, Any], results: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate interactive visualizations using plotly

        Args:
            design: Design parameters
            results: Analysis results

        Returns:
            Dictionary mapping visualization type to file path
        """
        if not PLOTLY_AVAILABLE:
            print("[TrussVisualizer] Plotly not available, skipping interactive visualizations")
            return {}

        print(f"[TrussVisualizer] Starting interactive visualization generation...")

        # Extract data
        if 'results' in results:
            actual_results = results['results']
        else:
            actual_results = results

        detailed_results = actual_results.get('detailed_results', {})
        nodes_data = detailed_results.get('nodes', [])
        displacements = detailed_results.get('displacements', [])
        stresses = detailed_results.get('stresses', [])

        geometry = design.get('geometry', {})
        span = geometry.get('span') or geometry.get('length', 10.0)
        height = geometry.get('height', 2.0)
        # Infer n_panels from nodes array
        if nodes_data:
            n_panels = len(nodes_data) // 2 - 1
        else:
            n_panels = geometry.get('n_panels') or geometry.get('n_elements', 5)

        nodes = np.array(nodes_data) if nodes_data else np.array([])

        base_path = os.path.join(self.output_dir, "truss")
        timestamp = self._get_timestamp()

        files = {}

        # 1. Interactive displacement plot
        disp_file = f"{base_path}_displacement_{timestamp}.html"
        files['displacement_interactive'] = disp_file
        print(f"[TrussVisualizer] Generating interactive displacement plot: {disp_file}")
        try:
            self._plot_interactive_displacement(nodes, displacements, disp_file, span, height, n_panels)
            print(f"[TrussVisualizer] SUCCESS: Interactive displacement plot created")
        except Exception as e:
            print(f"[TrussVisualizer] ERROR: Failed to generate interactive displacement: {e}")
            import traceback
            traceback.print_exc()

        # 2. Interactive stress plot
        stress_file = f"{base_path}_stress_{timestamp}.html"
        files['stress_interactive'] = stress_file
        print(f"[TrussVisualizer] Generating interactive stress plot: {stress_file}")
        try:
            self._plot_interactive_stress(nodes, stresses, stress_file, span, height, n_panels)
            print(f"[TrussVisualizer] SUCCESS: Interactive stress plot created")
        except Exception as e:
            print(f"[TrussVisualizer] ERROR: Failed to generate interactive stress: {e}")
            import traceback
            traceback.print_exc()

        print(f"[TrussVisualizer] Interactive visualization complete. Generated {len(files)} files")
        return files

    def _get_timestamp(self) -> str:
        """Get timestamp for filenames"""
        from datetime import datetime
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def _plot_displacement_cloud(self, nodes, displacements, filename, span, height, n_panels):
        """Plot displacement cloud for truss nodes"""
        fig, ax = plt.subplots(figsize=(12, 6))

        if len(nodes) == 0 or len(displacements) == 0:
            ax.text(0.5, 0.5, 'No data available', ha='center', va='center')
            plt.savefig(filename, dpi=150, bbox_inches='tight')
            plt.close()
            return

        # Extract node coordinates
        x_coords = nodes[:, 0]
        y_coords = nodes[:, 1]

        # Create scatter plot with displacement as color
        scatter = ax.scatter(x_coords, y_coords, c=displacements, cmap='jet',
                           s=200, edgecolors='black', linewidths=1.5, zorder=5)

        # Draw truss members
        self._draw_truss_members(ax, nodes, n_panels, alpha=0.3)

        # Colorbar
        cbar = plt.colorbar(scatter, ax=ax)
        cbar.set_label('Displacement (m)', fontsize=12)

        ax.set_xlabel('X (m)', fontsize=12)
        ax.set_ylabel('Y (m)', fontsize=12)
        ax.set_title('Truss Displacement Cloud', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.set_aspect('equal')

        plt.savefig(filename, dpi=150, bbox_inches='tight')
        plt.close()

    def _plot_stress_cloud(self, nodes, stresses, filename, span, height, n_panels):
        """Plot stress cloud for truss members"""
        fig, ax = plt.subplots(figsize=(12, 6))

        if len(nodes) == 0 or len(stresses) == 0:
            ax.text(0.5, 0.5, 'No data available', ha='center', va='center')
            plt.savefig(filename, dpi=150, bbox_inches='tight')
            plt.close()
            return

        # Draw truss members with stress coloring
        member_lines, member_stresses = self._get_member_lines(nodes, stresses, n_panels)

        if len(member_lines) > 0:
            # Normalize stresses for coloring
            norm = Normalize(vmin=min(member_stresses), vmax=max(member_stresses))
            lc = LineCollection(member_lines, cmap='coolwarm', norm=norm, linewidths=3)
            lc.set_array(np.array(member_stresses))
            ax.add_collection(lc)

            # Colorbar
            cbar = plt.colorbar(lc, ax=ax)
            cbar.set_label('Stress (Pa)', fontsize=12)

        # Draw nodes
        x_coords = nodes[:, 0]
        y_coords = nodes[:, 1]
        ax.scatter(x_coords, y_coords, c='black', s=50, zorder=5)

        ax.set_xlabel('X (m)', fontsize=12)
        ax.set_ylabel('Y (m)', fontsize=12)
        ax.set_title('Truss Stress Distribution', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.set_aspect('equal')
        ax.autoscale()

        plt.savefig(filename, dpi=150, bbox_inches='tight')
        plt.close()

    def _plot_topology(self, nodes, displacements, filename, span, height, n_panels):
        """Plot truss topology with deformed shape"""
        fig, ax = plt.subplots(figsize=(14, 7))

        if len(nodes) == 0:
            ax.text(0.5, 0.5, 'No data available', ha='center', va='center')
            plt.savefig(filename, dpi=150, bbox_inches='tight')
            plt.close()
            return

        # Original shape
        x_coords = nodes[:, 0]
        y_coords = nodes[:, 1]

        # Draw original truss (gray, dashed)
        self._draw_truss_members(ax, nodes, n_panels, color='gray', linestyle='--', alpha=0.5, label='Original')

        # Draw deformed shape if displacements available
        if len(displacements) > 0 and len(displacements) == len(nodes):
            # Scale factor for visibility
            max_disp = max(displacements) if max(displacements) > 0 else 1.0
            scale_factor = span * 0.1 / max_disp  # Scale to 10% of span

            # Calculate deformed positions (simplified: assume vertical displacement)
            deformed_nodes = nodes.copy()
            for i in range(len(nodes)):
                # Approximate deformation direction (mostly vertical for truss)
                deformed_nodes[i, 1] -= displacements[i] * scale_factor

            # Draw deformed truss (red, solid)
            self._draw_truss_members(ax, deformed_nodes, n_panels, color='red', linestyle='-', alpha=0.8, label='Deformed (scaled)')

        # Draw nodes
        ax.scatter(x_coords, y_coords, c='blue', s=100, zorder=5, label='Nodes')

        ax.set_xlabel('X (m)', fontsize=12)
        ax.set_ylabel('Y (m)', fontsize=12)
        ax.set_title('Truss Topology and Deformation', fontsize=14, fontweight='bold')
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)
        ax.set_aspect('equal')

        plt.savefig(filename, dpi=150, bbox_inches='tight')
        plt.close()

    def _draw_truss_members(self, ax, nodes, n_panels, **kwargs):
        """Draw truss member lines"""
        if len(nodes) < n_panels + 1:
            return

        # Extract label if present (only use it once)
        label = kwargs.pop('label', None)
        first_line = True

        # Bottom chord
        for i in range(n_panels):
            line_kwargs = kwargs.copy()
            if first_line and label:
                line_kwargs['label'] = label
                first_line = False
            ax.plot([nodes[i, 0], nodes[i+1, 0]],
                   [nodes[i, 1], nodes[i+1, 1]], **line_kwargs)

        # Top chord
        offset = n_panels + 1
        for i in range(n_panels):
            if offset + i + 1 < len(nodes):
                ax.plot([nodes[offset+i, 0], nodes[offset+i+1, 0]],
                       [nodes[offset+i, 1], nodes[offset+i+1, 1]], **kwargs)

        # Vertical members
        for i in range(n_panels + 1):
            if offset + i < len(nodes):
                ax.plot([nodes[i, 0], nodes[offset+i, 0]],
                       [nodes[i, 1], nodes[offset+i, 1]], **kwargs)

        # Diagonal members (alternating V-pattern)
        for i in range(n_panels):
            if offset + i + 1 < len(nodes):
                if i % 2 == 0:
                    # Even: bottom-left to top-right
                    ax.plot([nodes[i, 0], nodes[offset+i+1, 0]],
                           [nodes[i, 1], nodes[offset+i+1, 1]], **kwargs)
                else:
                    # Odd: top-left to bottom-right
                    ax.plot([nodes[offset+i, 0], nodes[i+1, 0]],
                           [nodes[offset+i, 1], nodes[i+1, 1]], **kwargs)

    def _get_member_lines(self, nodes, stresses, n_panels):
        """Get member line segments and corresponding stresses"""
        member_lines = []
        member_stresses = []
        stress_idx = 0

        if len(nodes) < n_panels + 1:
            return member_lines, member_stresses

        # Bottom chord
        for i in range(n_panels):
            if stress_idx < len(stresses):
                member_lines.append([nodes[i], nodes[i+1]])
                member_stresses.append(abs(stresses[stress_idx]))
                stress_idx += 1

        # Top chord
        offset = n_panels + 1
        for i in range(n_panels):
            if offset + i + 1 < len(nodes) and stress_idx < len(stresses):
                member_lines.append([nodes[offset+i], nodes[offset+i+1]])
                member_stresses.append(abs(stresses[stress_idx]))
                stress_idx += 1

        # Vertical members
        for i in range(n_panels + 1):
            if offset + i < len(nodes) and stress_idx < len(stresses):
                member_lines.append([nodes[i], nodes[offset+i]])
                member_stresses.append(abs(stresses[stress_idx]))
                stress_idx += 1

        # Diagonal members (alternating V-pattern)
        for i in range(n_panels):
            if stress_idx < len(stresses):
                if i % 2 == 0:
                    # Even: bottom-left to top-right
                    if offset + i + 1 < len(nodes):
                        member_lines.append([nodes[i], nodes[offset+i+1]])
                        member_stresses.append(abs(stresses[stress_idx]))
                else:
                    # Odd: top-left to bottom-right
                    if offset + i < len(nodes) and i + 1 < len(nodes):
                        member_lines.append([nodes[offset+i], nodes[i+1]])
                        member_stresses.append(abs(stresses[stress_idx]))
                stress_idx += 1

        return member_lines, member_stresses

    def _plot_interactive_displacement(self, nodes, displacements, filename, span, height, n_panels):
        """Generate interactive displacement plot using plotly"""
        if len(nodes) == 0 or len(displacements) == 0:
            return

        x_coords = nodes[:, 0]
        y_coords = nodes[:, 1]

        fig = go.Figure()

        # Add nodes with displacement coloring
        fig.add_trace(go.Scatter(
            x=x_coords, y=y_coords,
            mode='markers',
            marker=dict(
                size=15,
                color=displacements,
                colorscale='Jet',
                showscale=True,
                colorbar=dict(title="Displacement (m)"),
                line=dict(width=1, color='black')
            ),
            text=[f'Node {i}<br>Disp: {d:.6f} m' for i, d in enumerate(displacements)],
            hoverinfo='text',
            name='Nodes'
        ))

        # Add truss members
        member_lines = self._get_member_line_traces(nodes, n_panels)
        for line in member_lines:
            fig.add_trace(line)

        fig.update_layout(
            title='Interactive Truss Displacement',
            xaxis_title='X (m)',
            yaxis_title='Y (m)',
            hovermode='closest',
            showlegend=False,
            yaxis=dict(scaleanchor="x", scaleratio=1)
        )

        fig.write_html(filename)

    def _plot_interactive_stress(self, nodes, stresses, filename, span, height, n_panels):
        """Generate interactive stress plot using plotly"""
        if len(nodes) == 0 or len(stresses) == 0:
            return

        x_coords = nodes[:, 0]
        y_coords = nodes[:, 1]

        fig = go.Figure()

        # Add nodes
        fig.add_trace(go.Scatter(
            x=x_coords, y=y_coords,
            mode='markers',
            marker=dict(size=10, color='black'),
            name='Nodes',
            hoverinfo='skip'
        ))

        # Add members with stress coloring
        member_lines, member_stresses = self._get_member_lines(nodes, stresses, n_panels)

        # Normalize stresses for color mapping
        if len(member_stresses) > 0:
            min_stress = min(member_stresses)
            max_stress = max(member_stresses)
            stress_range = max_stress - min_stress if max_stress > min_stress else 1.0

            # Create colorscale mapping
            import matplotlib.cm as cm
            import matplotlib.colors as mcolors
            cmap = cm.get_cmap('coolwarm')

            for i, (line, stress) in enumerate(zip(member_lines, member_stresses)):
                # Normalize stress to [0, 1]
                normalized_stress = (stress - min_stress) / stress_range if stress_range > 0 else 0.5
                # Get color from colormap
                rgba = cmap(normalized_stress)
                color_str = mcolors.rgb2hex(rgba[:3])

                fig.add_trace(go.Scatter(
                    x=[line[0][0], line[1][0]],
                    y=[line[0][1], line[1][1]],
                    mode='lines',
                    line=dict(width=4, color=color_str),
                    text=f'Member {i}<br>Stress: {stress/1e6:.2f} MPa',
                    hoverinfo='text',
                    showlegend=False
                ))

        fig.update_layout(
            title='Interactive Truss Stress Distribution',
            xaxis_title='X (m)',
            yaxis_title='Y (m)',
            hovermode='closest',
            yaxis=dict(scaleanchor="x", scaleratio=1)
        )

        fig.write_html(filename)

    def _get_member_line_traces(self, nodes, n_panels):
        """Get plotly line traces for truss members"""
        traces = []
        offset = n_panels + 1

        # Bottom chord
        for i in range(n_panels):
            traces.append(go.Scatter(
                x=[nodes[i, 0], nodes[i+1, 0]],
                y=[nodes[i, 1], nodes[i+1, 1]],
                mode='lines',
                line=dict(width=2, color='gray'),
                showlegend=False,
                hoverinfo='skip'
            ))

        # Top chord
        for i in range(n_panels):
            if offset + i + 1 < len(nodes):
                traces.append(go.Scatter(
                    x=[nodes[offset+i, 0], nodes[offset+i+1, 0]],
                    y=[nodes[offset+i, 1], nodes[offset+i+1, 1]],
                    mode='lines',
                    line=dict(width=2, color='gray'),
                    showlegend=False,
                    hoverinfo='skip'
                ))

        # Vertical members
        for i in range(n_panels + 1):
            if offset + i < len(nodes):
                traces.append(go.Scatter(
                    x=[nodes[i, 0], nodes[offset+i, 0]],
                    y=[nodes[i, 1], nodes[offset+i, 1]],
                    mode='lines',
                    line=dict(width=2, color='gray'),
                    showlegend=False,
                    hoverinfo='skip'
                ))

        # Diagonal members (alternating V-pattern)
        for i in range(n_panels):
            if offset + i + 1 < len(nodes):
                if i % 2 == 0:
                    # Even: bottom-left to top-right
                    traces.append(go.Scatter(
                        x=[nodes[i, 0], nodes[offset+i+1, 0]],
                        y=[nodes[i, 1], nodes[offset+i+1, 1]],
                        mode='lines',
                        line=dict(width=2, color='gray'),
                        showlegend=False,
                        hoverinfo='skip'
                    ))
                else:
                    # Odd: top-left to bottom-right
                    traces.append(go.Scatter(
                        x=[nodes[offset+i, 0], nodes[i+1, 0]],
                        y=[nodes[offset+i, 1], nodes[i+1, 1]],
                        mode='lines',
                        line=dict(width=2, color='gray'),
                        showlegend=False,
                        hoverinfo='skip'
                    ))

        return traces

