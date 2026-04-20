"""
Frame visualizer for structural design results
Outputs 3 visualization types, each as PNG + HTML:
  1. Displacement contour (整体刚度 - 位移云图)
  2. Moment diagram       (构件受力 - 弯矩图)
  3. Story drift          (抗震性能 - 层间位移角)
"""

import os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.colors import Normalize
from matplotlib import font_manager, cm
from typing import Dict, Any, List, Tuple
from datetime import datetime

try:
    import plotly.graph_objects as go
    import plotly.offline as pyo
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

from .base_visualizer import BaseVisualizer


# ── Chinese font setup ────────────────────────────────────────────────────────
def _setup_chinese_font():
    candidates = ['Microsoft YaHei', 'SimHei', 'SimSun', 'WenQuanYi Micro Hei',
                  'Noto Sans CJK SC', 'Arial Unicode MS']
    available = {f.name for f in font_manager.fontManager.ttflist}
    for font in candidates:
        if font in available:
            matplotlib.rcParams['font.family'] = font
            break
    matplotlib.rcParams['axes.unicode_minus'] = False

_setup_chinese_font()


class FrameVisualizer(BaseVisualizer):
    """
    Visualizer for frame structures.
    Produces 3 visualization types × 2 formats (PNG + HTML) = 6 files.
    """

    def __init__(self):
        super().__init__()
        self.structure_type = "frame"

    # ── public entry points ───────────────────────────────────────────────────

    def generate_static_visualizations(self, design: Dict[str, Any],
                                        results: Dict[str, Any]) -> Dict[str, str]:
        print("[FrameVisualizer] Starting static visualization generation...")
        print(f"[FrameVisualizer] Output directory: {self.output_dir}")
        os.makedirs(self.output_dir, exist_ok=True)
        print("[FrameVisualizer] Output directory created/verified")

        actual = results.get('results', results)
        geo = design.get('geometry', {})
        node_coords = self._node_coords(geo)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        files = {}

        for name, fn in [
            ('displacement', self._png_displacement),
            ('moment',       self._png_moment),
            ('story_drift',  self._png_story_drift),
        ]:
            try:
                path = fn(design, actual, node_coords, ts)
                if path:
                    files[name] = path
                    print(f"[FrameVisualizer] OK {name} PNG generated")
            except Exception as e:
                print(f"[FrameVisualizer] ERROR {name} PNG: {e}")

        print(f"[FrameVisualizer] Generated {len(files)} visualizations")
        return files

    def generate_interactive_visualizations(self, design: Dict[str, Any],
                                             results: Dict[str, Any]) -> Dict[str, str]:
        if not PLOTLY_AVAILABLE:
            print("[FrameVisualizer] Plotly not available, skipping interactive visualizations")
            return {}
        print("[FrameVisualizer] Generating interactive visualizations...")

        actual = results.get('results', results)
        geo = design.get('geometry', {})
        node_coords = self._node_coords(geo)
        files = {}

        for name, fn in [
            ('displacement_interactive', self._html_displacement),
            ('moment_interactive',       self._html_moment),
            ('story_drift_interactive',  self._html_story_drift),
        ]:
            try:
                path = fn(design, actual, node_coords)
                if path:
                    files[name] = path
                    print(f"[FrameVisualizer] OK {name} HTML generated")
            except Exception as e:
                print(f"[FrameVisualizer] ERROR {name} HTML: {e}")

        return files

    # ── helpers ───────────────────────────────────────────────────────────────

    def _node_coords(self, geo: Dict) -> Dict[int, Tuple[float, float]]:
        num_bays      = geo.get('num_bays', 1)
        num_stories   = geo.get('num_stories', 1)
        bay_widths    = geo.get('bay_widths', [6.0])
        story_heights = geo.get('story_heights', [4.0])
        coords = {}
        nid = 0
        y = 0.0
        for s in range(num_stories + 1):
            x = 0.0
            for b in range(num_bays + 1):
                coords[nid] = (x, y)
                nid += 1
                if b < num_bays:
                    x += bay_widths[b]
            if s < num_stories:
                y += story_heights[s]
        return coords

    def _draw_frame(self, ax, node_coords, num_bays, num_stories, **kw):
        """Draw frame outline; only first segment gets the label."""
        first = True
        for s in range(num_stories):
            for b in range(num_bays + 1):
                ni = s * (num_bays + 1) + b
                nj = (s + 1) * (num_bays + 1) + b
                if ni in node_coords and nj in node_coords:
                    xs = [node_coords[ni][0], node_coords[nj][0]]
                    ys = [node_coords[ni][1], node_coords[nj][1]]
                    ax.plot(xs, ys, **(kw if first else {k: v for k, v in kw.items() if k != 'label'}))
                    first = False
        for s in range(1, num_stories + 1):
            for b in range(num_bays):
                ni = s * (num_bays + 1) + b
                nj = s * (num_bays + 1) + b + 1
                if ni in node_coords and nj in node_coords:
                    xs = [node_coords[ni][0], node_coords[nj][0]]
                    ys = [node_coords[ni][1], node_coords[nj][1]]
                    ax.plot(xs, ys, **{k: v for k, v in kw.items() if k != 'label'})

    def _get_extra(self, results: Dict) -> Dict:
        return results.get('detailed_results', {}).get('extra', {})

    def _save_png(self, fig, name: str, ts: str) -> str:
        path = os.path.join(self.output_dir, f"frame_{name}_{ts}.png")
        fig.savefig(path, dpi=200, bbox_inches='tight')
        plt.close(fig)
        return path

    def _save_html(self, fig, name: str) -> str:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(self.output_dir, f"frame_{name}_{ts}.html")
        fig.write_html(path)
        return path

    # ── 1. Displacement contour (位移云图) ────────────────────────────────────

    def _png_displacement(self, design, results, node_coords, ts) -> str:
        geo = design.get('geometry', {})
        num_bays    = geo.get('num_bays', 1)
        num_stories = geo.get('num_stories', 1)

        uy_list = results.get('detailed_results', {}).get('displacements', [])
        ux_list = self._get_extra(results).get('ux_displacements', [])

        n_nodes = (num_bays + 1) * (num_stories + 1)
        disp_mag = []
        for i in range(n_nodes):
            ux = ux_list[i] if i < len(ux_list) else 0.0
            uy = uy_list[i] if i < len(uy_list) else 0.0
            disp_mag.append((ux**2 + uy**2) ** 0.5)

        max_disp = max(disp_mag) if disp_mag else 1e-9
        scale = 200

        fig, ax = plt.subplots(figsize=(12, 9))
        cmap = cm.jet
        norm = Normalize(vmin=0, vmax=max_disp * 1000)

        def draw_elem_colored(ni, nj):
            if ni not in node_coords or nj not in node_coords:
                return
            mag = (disp_mag[ni] + disp_mag[nj]) / 2 * 1000
            color = cmap(norm(mag))
            ux_i = ux_list[ni] if ni < len(ux_list) else 0.0
            uy_i = uy_list[ni] if ni < len(uy_list) else 0.0
            ux_j = ux_list[nj] if nj < len(ux_list) else 0.0
            uy_j = uy_list[nj] if nj < len(uy_list) else 0.0
            xi = node_coords[ni][0] + ux_i * scale
            yi = node_coords[ni][1] + uy_i * scale
            xj = node_coords[nj][0] + ux_j * scale
            yj = node_coords[nj][1] + uy_j * scale
            ax.plot([xi, xj], [yi, yj], color=color, linewidth=5, solid_capstyle='round')

        for s in range(num_stories):
            for b in range(num_bays + 1):
                draw_elem_colored(s*(num_bays+1)+b, (s+1)*(num_bays+1)+b)
        for s in range(1, num_stories + 1):
            for b in range(num_bays):
                draw_elem_colored(s*(num_bays+1)+b, s*(num_bays+1)+b+1)

        self._draw_frame(ax, node_coords, num_bays, num_stories,
                         color='gray', linestyle='--', linewidth=0.8,
                         alpha=0.4, label='Original')

        sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])
        plt.colorbar(sm, ax=ax, label='Displacement (mm)')
        ax.set_xlabel('X (m)')
        ax.set_ylabel('Y (m)')
        ax.set_title(f'Frame Displacement Contour  (scale x{scale})')
        ax.legend(fontsize=9)
        ax.set_aspect('equal')
        ax.grid(True, alpha=0.3)
        return self._save_png(fig, 'displacement', ts)

    def _html_displacement(self, design, results, node_coords) -> str:
        import colorsys
        geo = design.get('geometry', {})
        num_bays    = geo.get('num_bays', 1)
        num_stories = geo.get('num_stories', 1)

        uy_list = results.get('detailed_results', {}).get('displacements', [])
        ux_list = self._get_extra(results).get('ux_displacements', [])
        n_nodes = (num_bays + 1) * (num_stories + 1)
        disp_mag = []
        for i in range(n_nodes):
            ux = ux_list[i] if i < len(ux_list) else 0.0
            uy = uy_list[i] if i < len(uy_list) else 0.0
            disp_mag.append((ux**2 + uy**2) ** 0.5 * 1000)

        max_d = max(disp_mag) if disp_mag else 1
        scale = 200

        def mag_color(ni, nj):
            mag = (disp_mag[ni] + disp_mag[nj]) / 2
            ratio = mag / max_d if max_d > 0 else 0
            r, g, b = colorsys.hsv_to_rgb(0.67 * (1 - ratio), 1, 1)
            return f'rgb({int(r*255)},{int(g*255)},{int(b*255)})'

        fig = go.Figure()

        def add_elem(ni, nj, etype):
            if ni not in node_coords or nj not in node_coords:
                return
            ux_i = ux_list[ni] if ni < len(ux_list) else 0.0
            uy_i = uy_list[ni] if ni < len(uy_list) else 0.0
            ux_j = ux_list[nj] if nj < len(ux_list) else 0.0
            uy_j = uy_list[nj] if nj < len(uy_list) else 0.0
            xi = node_coords[ni][0] + ux_i * scale
            yi = node_coords[ni][1] + uy_i * scale
            xj = node_coords[nj][0] + ux_j * scale
            yj = node_coords[nj][1] + uy_j * scale
            avg = (disp_mag[ni] + disp_mag[nj]) / 2
            fig.add_trace(go.Scatter(
                x=[xi, xj], y=[yi, yj], mode='lines',
                line=dict(color=mag_color(ni, nj), width=4),
                hovertemplate=f'{etype}<br>Disp: {avg:.3f} mm<extra></extra>',
                showlegend=False
            ))

        for s in range(num_stories):
            for b in range(num_bays + 1):
                add_elem(s*(num_bays+1)+b, (s+1)*(num_bays+1)+b, 'Column')
        for s in range(1, num_stories + 1):
            for b in range(num_bays):
                add_elem(s*(num_bays+1)+b, s*(num_bays+1)+b+1, 'Beam')

        fig.update_layout(
            title=f'Frame Displacement Contour (scale x{scale})',
            xaxis_title='X (m)', yaxis_title='Y (m)',
            yaxis=dict(scaleanchor='x'), showlegend=False, hovermode='closest'
        )
        return self._save_html(fig, 'displacement_interactive')

    # ── 2. Moment diagram (弯矩图) ────────────────────────────────────────────

    def _png_moment(self, design, results, node_coords, ts) -> str:
        geo = design.get('geometry', {})
        num_bays    = geo.get('num_bays', 1)
        num_stories = geo.get('num_stories', 1)

        moments = results.get('detailed_results', {}).get('moments', [])
        moment_vals = [float(m) for m in moments]
        max_m = max(abs(v) for v in moment_vals) if moment_vals else 1

        fig, ax = plt.subplots(figsize=(12, 9))
        cmap = cm.RdYlBu_r
        norm = Normalize(vmin=-max_m, vmax=max_m)
        num_col_elems = num_stories * (num_bays + 1)

        for i in range(len(moment_vals) // 2):
            Mi = moment_vals[i * 2]
            Mj = moment_vals[i * 2 + 1]
            color = cmap(norm((Mi + Mj) / 2))
            if i < num_col_elems:
                s = i // (num_bays + 1); b = i % (num_bays + 1)
                ni = s*(num_bays+1)+b; nj = (s+1)*(num_bays+1)+b
            else:
                idx = i - num_col_elems; s = idx//num_bays+1; b = idx%num_bays
                ni = s*(num_bays+1)+b; nj = s*(num_bays+1)+b+1
            if ni in node_coords and nj in node_coords:
                x1, y1 = node_coords[ni]; x2, y2 = node_coords[nj]
                ax.plot([x1, x2], [y1, y2], color=color, linewidth=5, solid_capstyle='round')
                mx, my = (x1+x2)/2, (y1+y2)/2
                ax.text(mx+0.15, my, f'{(Mi+Mj)/2/1000:.1f}kNm',
                        fontsize=7, va='center', color='black')

        self._draw_frame(ax, node_coords, num_bays, num_stories,
                         color='black', linestyle='-', linewidth=0.6, alpha=0.3)
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])
        plt.colorbar(sm, ax=ax, label='Moment (N·m)')
        ax.set_xlabel('X (m)'); ax.set_ylabel('Y (m)')
        ax.set_title('Frame Moment Diagram')
        ax.set_aspect('equal'); ax.grid(True, alpha=0.3)
        return self._save_png(fig, 'moment', ts)

    def _html_moment(self, design, results, node_coords) -> str:
        import colorsys
        geo = design.get('geometry', {})
        num_bays    = geo.get('num_bays', 1)
        num_stories = geo.get('num_stories', 1)

        moments = results.get('detailed_results', {}).get('moments', [])
        moment_vals = [float(m) for m in moments]
        max_m = max(abs(v) for v in moment_vals) if moment_vals else 1
        num_col_elems = num_stories * (num_bays + 1)

        def m_color(m_avg):
            ratio = (m_avg / max_m + 1) / 2
            r, g, b = colorsys.hsv_to_rgb(0.67 * (1 - ratio), 1, 1)
            return f'rgb({int(r*255)},{int(g*255)},{int(b*255)})'

        fig = go.Figure()
        for i in range(len(moment_vals) // 2):
            Mi = moment_vals[i*2]; Mj = moment_vals[i*2+1]
            if i < num_col_elems:
                s = i//(num_bays+1); b = i%(num_bays+1)
                ni = s*(num_bays+1)+b; nj = (s+1)*(num_bays+1)+b; etype = 'Column'
            else:
                idx = i-num_col_elems; s = idx//num_bays+1; b = idx%num_bays
                ni = s*(num_bays+1)+b; nj = s*(num_bays+1)+b+1; etype = 'Beam'
            if ni in node_coords and nj in node_coords:
                x1, y1 = node_coords[ni]; x2, y2 = node_coords[nj]
                avg = (Mi+Mj)/2
                fig.add_trace(go.Scatter(
                    x=[x1, x2], y=[y1, y2], mode='lines',
                    line=dict(color=m_color(avg), width=5),
                    hovertemplate=f'{etype}<br>Mi={Mi/1000:.2f} kNm<br>Mj={Mj/1000:.2f} kNm<extra></extra>',
                    showlegend=False
                ))
        fig.update_layout(
            title='Frame Moment Diagram',
            xaxis_title='X (m)', yaxis_title='Y (m)',
            yaxis=dict(scaleanchor='x'), hovermode='closest'
        )
        return self._save_html(fig, 'moment_interactive')

    # ── 3. Story drift (层间位移角) ───────────────────────────────────────────

    def _compute_drift(self, design, results) -> Tuple[List[str], List[float], bool]:
        """Returns (labels, ratios, has_lateral). Numerical noise < 1e-9 is zeroed."""
        geo = design.get('geometry', {})
        num_bays      = geo.get('num_bays', 1)
        num_stories   = geo.get('num_stories', 1)
        story_heights = geo.get('story_heights', [4.0])
        ux_list = self._get_extra(results).get('ux_displacements', [])

        loads = design.get('loads', {})
        has_lateral = bool(loads.get('lateral', []))

        labels, ratios = [], []
        for s in range(1, num_stories + 1):
            ux_cur  = sum(ux_list[s*(num_bays+1)+b]
                          for b in range(num_bays+1)
                          if s*(num_bays+1)+b < len(ux_list)) / (num_bays+1)
            ux_prev = sum(ux_list[(s-1)*(num_bays+1)+b]
                          for b in range(num_bays+1)
                          if (s-1)*(num_bays+1)+b < len(ux_list)) / (num_bays+1)
            h = story_heights[s-1] if s-1 < len(story_heights) else 4.0
            ratio = abs(ux_cur - ux_prev) / h if h > 0 else 0.0
            ratios.append(ratio if ratio >= 1e-9 else 0.0)
            labels.append(f'Story {s}')
        return labels, ratios, has_lateral

    def _png_story_drift(self, design, results, node_coords, ts) -> str:
        labels, ratios, has_lateral = self._compute_drift(design, results)
        limit = 1.0 / 500

        # 无水平荷载时层间位移角全为0，显示说明文字
        has_lateral = any(r > 1e-9 for r in ratios)
        fig, ax = plt.subplots(figsize=(8, 6))
        if not has_lateral:
            ax.text(0.5, 0.5, 'No lateral load applied\nStory drift = 0',
                    ha='center', va='center', fontsize=14, color='gray',
                    transform=ax.transAxes)
            ax.set_title('Story Drift Ratio Distribution')
            return self._save_png(fig, 'story_drift', ts)

        colors = ['red' if r > limit else 'steelblue' for r in ratios]
        bars = ax.bar(labels, ratios, color=colors, alpha=0.75,
                      edgecolor='black', linewidth=0.5)
        for bar, val in zip(bars, ratios):
            ax.text(bar.get_x() + bar.get_width()/2,
                    bar.get_height() + limit*0.02,
                    f'{val:.5f}', ha='center', va='bottom', fontsize=9)
        ax.axhline(limit, color='red', linestyle='--', linewidth=1.5,
                   label=f'Limit 1/500 = {limit:.4f}')
        ax.set_xlabel('Story'); ax.set_ylabel('Story Drift Ratio')
        ax.set_title('Story Drift Ratio Distribution')
        ax.legend(fontsize=9); ax.grid(True, axis='y', alpha=0.3)
        return self._save_png(fig, 'story_drift', ts)

    def _html_story_drift(self, design, results, node_coords) -> str:
        labels, ratios, has_lateral = self._compute_drift(design, results)
        limit = 1.0 / 500

        # 无水平荷载时显示说明
        has_lateral = any(r > 1e-9 for r in ratios)
        if not has_lateral:
            fig = go.Figure()
            fig.add_annotation(text='No lateral load applied — Story drift = 0',
                               xref='paper', yref='paper', x=0.5, y=0.5,
                               showarrow=False, font=dict(size=16, color='gray'))
            fig.update_layout(title='Story Drift Ratio Distribution')
            return self._save_html(fig, 'story_drift_interactive')

        colors = ['red' if r > limit else 'steelblue' for r in ratios]

        fig = go.Figure()

        if not has_lateral:
            fig.add_annotation(
                text='无水平荷载工况<br>层间位移角接近零<br>(仅竖向荷载)',
                xref='paper', yref='paper', x=0.5, y=0.5,
                showarrow=False, font=dict(size=16, color='gray')
            )
            fig.update_layout(title='Story Drift Ratio Distribution',
                              xaxis_title='Story', yaxis_title='Story Drift Ratio')
            return self._save_html(fig, 'story_drift_interactive')

        colors = ['red' if r > limit else 'steelblue' for r in ratios]
        fig.add_trace(go.Bar(
            x=labels, y=ratios, marker_color=colors,
            text=[f'{r:.5f}' for r in ratios], textposition='outside',
            hovertemplate='%{x}<br>Drift: %{y:.6f}<extra></extra>',
            name='Story Drift'
        ))
        fig.add_hline(y=limit, line_dash='dash', line_color='red',
                      annotation_text=f'Limit 1/500={limit:.4f}',
                      annotation_position='top right')
        fig.update_layout(
            title='Story Drift Ratio Distribution',
            xaxis_title='Story', yaxis_title='Story Drift Ratio',
            hovermode='x unified'
        )
        return self._save_html(fig, 'story_drift_interactive')
