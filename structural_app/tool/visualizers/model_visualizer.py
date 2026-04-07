"""
Model visualizer for structural design verification
Generates schematic diagrams for 5 structure types using matplotlib
"""

import matplotlib
matplotlib.use("Agg")  # non-interactive backend, safe for CI
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch
from typing import Dict, Any


class ModelVisualizer:
    """
    Static methods to visualize structural models and save as PNG.
    Each method accepts a `design` dict (same format as the analyzers)
    and an `output_path` string.
    """

    # ------------------------------------------------------------------
    # 1. Simply-supported beam
    # ------------------------------------------------------------------
    @staticmethod
    def visualize_beam(design: Dict[str, Any], output_path: str) -> str:
        """
        Draw simply-supported beam with supports, loads, and section annotation.

        Args:
            design: beam design dict (geometry/material/loads/constraints)
            output_path: path to save PNG

        Returns:
            output_path
        """
        geo = design["geometry"]
        L = geo["length"]
        b = geo.get("width", 0.3)
        h = geo.get("height", 0.5)
        loads = design.get("loads", {})

        fig, ax = plt.subplots(figsize=(10, 4))
        ax.set_aspect("equal")

        # Beam body
        beam_y = 0.0
        beam_h = h * 0.5  # visual height scale
        rect = mpatches.FancyBboxPatch(
            (0, beam_y - beam_h / 2), L, beam_h,
            boxstyle="square,pad=0", linewidth=1.5,
            edgecolor="black", facecolor="#D0E8FF"
        )
        ax.add_patch(rect)

        # Supports
        _draw_pin_support(ax, 0, beam_y - beam_h / 2)
        _draw_roller_support(ax, L, beam_y - beam_h / 2)

        # Distributed loads
        for dl in loads.get("distributed", []):
            q = dl.get("q", 0)
            x0 = dl.get("start", 0)
            x1 = dl.get("end", L)
            _draw_distributed_load(ax, x0, x1, beam_y + beam_h / 2, q, L)

        # Point loads
        for pl in loads.get("point", []):
            P = pl.get("P", 0)
            x = pl.get("location", pl.get("x", L / 2))
            _draw_point_load(ax, x, beam_y + beam_h / 2, P)

        # Annotations
        ax.annotate(
            f"L = {L} m\nb×h = {b}×{h} m",
            xy=(L / 2, beam_y - beam_h / 2 - 0.3),
            ha="center", fontsize=12, color="#333333"
        )
        ax.set_title("简支梁示意图", fontsize=14, fontweight="bold")
        _finalize(ax, fig, -0.5, L + 0.5, beam_y - beam_h - 0.8, beam_y + beam_h + 1.0)
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return output_path

    # ------------------------------------------------------------------
    # 2. Cantilever beam
    # ------------------------------------------------------------------
    @staticmethod
    def visualize_cantilever_beam(design: Dict[str, Any], output_path: str) -> str:
        """
        Draw cantilever beam with fixed wall, loads, and section annotation.
        """
        geo = design["geometry"]
        L = geo["length"]
        b = geo.get("width", 0.3)
        h = geo.get("height", 0.5)
        loads = design.get("loads", {})
        cons = design.get("constraints", {})
        fixed_end = cons.get("fixed_end", "left")

        fig, ax = plt.subplots(figsize=(10, 4))
        ax.set_aspect("equal")

        beam_y = 0.0
        beam_h = h * 0.5

        # Beam body
        rect = mpatches.FancyBboxPatch(
            (0, beam_y - beam_h / 2), L, beam_h,
            boxstyle="square,pad=0", linewidth=1.5,
            edgecolor="black", facecolor="#D0E8FF"
        )
        ax.add_patch(rect)

        # Fixed wall
        wall_x = 0.0 if fixed_end == "left" else L
        _draw_fixed_wall(ax, wall_x, beam_y, beam_h, side=fixed_end)

        # Distributed loads
        for dl in loads.get("distributed", []):
            q = dl.get("q", 0)
            x0 = dl.get("start", 0)
            x1 = dl.get("end", L)
            _draw_distributed_load(ax, x0, x1, beam_y + beam_h / 2, q, L)

        # Point loads
        for pl in loads.get("point", []):
            force = pl.get("force", pl.get("P", 0))
            position = pl.get("position", pl.get("x", L))
            _draw_point_load(ax, position, beam_y + beam_h / 2, force)

        ax.annotate(
            f"L = {L} m\nb×h = {b}×{h} m",
            xy=(L / 2, beam_y - beam_h / 2 - 0.3),
            ha="center", fontsize=12, color="#333333"
        )
        ax.set_title("悬臂梁示意图", fontsize=14, fontweight="bold")
        _finalize(ax, fig, -0.8, L + 0.5, beam_y - beam_h - 0.8, beam_y + beam_h + 1.0)
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return output_path

    # ------------------------------------------------------------------
    # 3. Continuous beam
    # ------------------------------------------------------------------
    @staticmethod
    def visualize_continuous_beam(design: Dict[str, Any], output_path: str) -> str:
        """
        Draw multi-span continuous beam with intermediate roller supports.
        """
        geo = design["geometry"]
        b = geo.get("width", 0.3)
        h = geo.get("height", 0.5)
        loads = design.get("loads", {})

        # Accept either spans list or length+n_spans
        if "spans" in geo:
            spans = geo["spans"]
        else:
            n = geo.get("n_spans", 2)
            L_total = geo.get("length", 10.0)
            spans = [L_total / n] * n

        L_total = sum(spans)
        beam_y = 0.0
        beam_h = h * 0.5

        fig, ax = plt.subplots(figsize=(max(10, L_total + 2), 4))
        ax.set_aspect("equal")

        # Beam body
        rect = mpatches.FancyBboxPatch(
            (0, beam_y - beam_h / 2), L_total, beam_h,
            boxstyle="square,pad=0", linewidth=1.5,
            edgecolor="black", facecolor="#D0E8FF"
        )
        ax.add_patch(rect)

        # Support positions
        support_xs = [0.0]
        x = 0.0
        for sp in spans:
            x += sp
            support_xs.append(x)

        _draw_pin_support(ax, support_xs[0], beam_y - beam_h / 2)
        for sx in support_xs[1:-1]:
            _draw_roller_support(ax, sx, beam_y - beam_h / 2)
        _draw_roller_support(ax, support_xs[-1], beam_y - beam_h / 2)

        # Span labels
        x = 0.0
        for i, sp in enumerate(spans):
            ax.annotate(
                f"L{i+1}={sp}m",
                xy=(x + sp / 2, beam_y - beam_h / 2 - 0.25),
                ha="center", fontsize=11, color="#555555"
            )
            x += sp

        # Distributed loads
        for dl in loads.get("distributed", []):
            q = dl.get("q", 0)
            _draw_distributed_load(ax, 0, L_total, beam_y + beam_h / 2, q, L_total)

        # Point loads
        for pl in loads.get("point", []):
            force = pl.get("force", pl.get("P", 0))
            position = pl.get("position", pl.get("x", L_total / 2))
            _draw_point_load(ax, position, beam_y + beam_h / 2, force)

        ax.annotate(
            f"b×h = {b}×{h} m",
            xy=(L_total / 2, beam_y + beam_h / 2 + 0.7),
            ha="center", fontsize=12, color="#333333"
        )
        ax.set_title(f"连续梁示意图（{len(spans)}跨）", fontsize=14, fontweight="bold")
        _finalize(ax, fig, -0.5, L_total + 0.5, beam_y - beam_h - 0.8, beam_y + beam_h + 1.2)
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return output_path

    # ------------------------------------------------------------------
    # 4. Truss
    # ------------------------------------------------------------------
    @staticmethod
    def visualize_truss(design: Dict[str, Any], output_path: str) -> str:
        """
        Draw Pratt truss with nodes, members, supports, and nodal loads.
        """
        geo = design["geometry"]
        span = geo["span"]
        height = geo["height"]
        n_panels = geo["n_panels"]
        loads = design.get("loads", {})

        panel_length = span / n_panels

        # Node coordinates
        bottom_nodes = [(i * panel_length, 0.0) for i in range(n_panels + 1)]
        top_nodes = [(i * panel_length, height) for i in range(n_panels + 1)]
        all_nodes = bottom_nodes + top_nodes

        fig, ax = plt.subplots(figsize=(max(10, span + 2), 5))
        ax.set_aspect("equal")

        # Bottom chord
        for i in range(n_panels):
            x0, y0 = bottom_nodes[i]
            x1, y1 = bottom_nodes[i + 1]
            ax.plot([x0, x1], [y0, y1], "b-", linewidth=2)

        # Top chord
        for i in range(n_panels):
            x0, y0 = top_nodes[i]
            x1, y1 = top_nodes[i + 1]
            ax.plot([x0, x1], [y0, y1], "b-", linewidth=2)

        # Verticals
        for i in range(n_panels + 1):
            bx, by = bottom_nodes[i]
            tx, ty = top_nodes[i]
            ax.plot([bx, tx], [by, ty], "g-", linewidth=1.5)

        # Diagonals (Pratt: bottom-left to top-right)
        for i in range(n_panels):
            bx, by = bottom_nodes[i]
            tx, ty = top_nodes[i + 1]
            ax.plot([bx, tx], [by, ty], "r-", linewidth=1.5, alpha=0.7)

        # Nodes
        for nx, ny in all_nodes:
            ax.plot(nx, ny, "ko", markersize=5)

        # Node IDs (bottom chord 1-based, top chord starts after)
        for i, (nx, ny) in enumerate(bottom_nodes):
            ax.annotate(str(i + 1), (nx, ny - 0.15), ha="center", fontsize=9, color="navy")
        for i, (nx, ny) in enumerate(top_nodes):
            ax.annotate(str(n_panels + 1 + i + 1), (nx, ny + 0.12), ha="center", fontsize=9, color="darkgreen")

        # Supports
        _draw_pin_support(ax, 0, 0)
        _draw_roller_support(ax, span, 0)

        # Nodal loads
        for nl in loads.get("nodal", []):
            node_idx = nl["node"] - 1  # 1-based → 0-based
            if node_idx < len(all_nodes):
                nx, ny = all_nodes[node_idx]
                Fy = nl.get("Fy", 0)
                if Fy != 0:
                    _draw_point_load(ax, nx, ny, Fy, arrow_len=0.3)

        ax.annotate(
            f"span={span}m  h={height}m  n={n_panels}",
            xy=(span / 2, -0.4),
            ha="center", fontsize=12, color="#333333"
        )
        ax.set_title("桁架示意图（Pratt型）", fontsize=14, fontweight="bold")
        _finalize(ax, fig, -0.5, span + 0.5, -0.8, height + 0.6)
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return output_path

    # ------------------------------------------------------------------
    # 5. Frame
    # ------------------------------------------------------------------
    @staticmethod
    def visualize_frame(design: Dict[str, Any], output_path: str) -> str:
        """
        Draw multi-bay multi-story frame with:
        - columns / beams / fixed bases
        - beam distributed loads (per bay, labeled individually)
        - lateral loads (horizontal arrows on each story)
        - span and story-height dimension annotations
        - section sizes + material info box
        """
        geo   = design["geometry"]
        loads = design.get("loads", {})
        mat   = design.get("material", {})

        num_bays      = geo["num_bays"]
        num_stories   = geo["num_stories"]
        bay_widths    = geo["bay_widths"]
        story_heights = geo["story_heights"]
        col_sec       = geo.get("columns", {})
        beam_sec      = geo.get("beams", {})

        total_w = sum(bay_widths)
        total_h = sum(story_heights)

        # ── node coordinates ──────────────────────────────────────────────
        node = {}          # node[story][bay] = (x, y)
        y = 0.0
        for s in range(num_stories + 1):
            node[s] = {}
            x = 0.0
            for b in range(num_bays + 1):
                node[s][b] = (x, y)
                if b < num_bays:
                    x += bay_widths[b]
            if s < num_stories:
                y += story_heights[s]

        # ── figure size: give extra space left (dim) and right (info) ─────
        left_margin  = 1.8    # for story-height dims
        right_margin = 0.5
        top_margin   = 2.5    # for load arrows
        bot_margin   = 1.5    # for supports + base dims

        fig_w = total_w + left_margin + right_margin + 2
        fig_h = total_h + top_margin  + bot_margin   + 2
        fig, ax = plt.subplots(figsize=(max(12, fig_w), max(10, fig_h)))
        ax.set_aspect("equal")

        FS = 11   # base font size

        # ── columns (blue) ────────────────────────────────────────────────
        for s in range(num_stories):
            for b in range(num_bays + 1):
                x0, y0 = node[s][b]
                x1, y1 = node[s + 1][b]
                ax.plot([x0, x1], [y0, y1], "b-", linewidth=3.5)

        # ── beams (red) ───────────────────────────────────────────────────
        for s in range(1, num_stories + 1):
            for b in range(num_bays):
                x0, beam_y = node[s][b]
                x1, _      = node[s][b + 1]
                ax.plot([x0, x1], [beam_y, beam_y], "r-", linewidth=3)

        # ── nodes ─────────────────────────────────────────────────────────
        for s in range(num_stories + 1):
            for b in range(num_bays + 1):
                ax.plot(*node[s][b], "ko", markersize=6)

        # ── fixed bases ───────────────────────────────────────────────────
        for b in range(num_bays + 1):
            bx, by = node[0][b]
            _draw_fixed_base(ax, bx, by)

        # ── beam distributed loads ────────────────────────────────────────
        arrow_h = min(story_heights) * 0.28
        for dl in loads.get("beam_distributed", []):
            s  = dl.get("story", 1)
            b  = dl.get("bay",   0)
            q  = dl.get("q",     0)
            if s > num_stories or b >= num_bays:
                continue
            x0, y0 = node[s][b]
            x1, _  = node[s][b + 1]
            bw = x1 - x0
            dy = -arrow_h if q < 0 else arrow_h   # fixed: compute once, not inside loop

            # horizontal line at arrow tops
            ax.plot([x0, x1], [y0 - dy, y0 - dy], color="magenta", linewidth=1.5)

            # arrows
            n_arr = max(3, int(bw / 1.2))
            for i in range(n_arr + 1):
                xa = x0 + i * bw / n_arr
                ax.annotate("", xy=(xa, y0), xytext=(xa, y0 - dy),
                            arrowprops=dict(arrowstyle="-|>",
                                           color="magenta", lw=1.5))

            # label above the horizontal line
            ax.text((x0 + x1) / 2, y0 - dy * 1.6,
                    f"q={abs(q)/1000:.1f} kN/m",
                    ha="center", va="center",
                    fontsize=FS, color="magenta", fontweight="bold")

        # ── lateral loads ─────────────────────────────────────────────────
        lat_arrow = min(bay_widths) * 0.35
        for ll in loads.get("lateral", []):
            s = ll.get("story", 1)
            F = ll.get("F", 0)
            if s > num_stories:
                continue
            # apply at left column, mid story height
            xl, yl = node[s][0]
            ax.annotate("",
                        xy=(xl, yl), xytext=(xl - lat_arrow, yl),
                        arrowprops=dict(arrowstyle="-|>",
                                       color="darkorange", lw=2.5))
            ax.text(xl - lat_arrow - 0.1, yl,
                    f"F={abs(F)/1000:.1f} kN",
                    ha="right", va="center",
                    fontsize=FS - 1, color="darkorange", fontweight="bold")

        # ── span dimension lines (below ground) ───────────────────────────
        dim_y = -0.9
        tick  = 0.15
        cum_x = 0.0
        for b in range(num_bays):
            x0 = cum_x
            x1 = cum_x + bay_widths[b]
            cx = (x0 + x1) / 2
            ax.annotate("", xy=(x1, dim_y), xytext=(x0, dim_y),
                        arrowprops=dict(arrowstyle="<->", color="gray", lw=1.2))
            ax.text(cx, dim_y - 0.3, f"{bay_widths[b]:.1f} m",
                    ha="center", va="top", fontsize=FS, color="gray")
            cum_x = x1

        # ── story-height dimension lines (left of frame) ──────────────────
        dim_x = -1.2
        cum_y = 0.0
        for s in range(num_stories):
            y0 = cum_y
            y1 = cum_y + story_heights[s]
            cy = (y0 + y1) / 2
            ax.annotate("", xy=(dim_x, y1), xytext=(dim_x, y0),
                        arrowprops=dict(arrowstyle="<->", color="gray", lw=1.2))
            ax.text(dim_x - 0.15, cy, f"{story_heights[s]:.1f} m",
                    ha="right", va="center", fontsize=FS, color="gray")
            cum_y = y1

        # ── support label ─────────────────────────────────────────────────
        ax.text(total_w / 2, -1.6,
                "支座：柱底固定（Fixed）",
                ha="center", va="top", fontsize=FS, color="navy", fontweight="bold")

        # ── info box: section + material ──────────────────────────────────
        col_w = col_sec.get("width",  "?")
        col_d = col_sec.get("depth",  "?")
        bm_w  = beam_sec.get("width", "?")
        bm_d  = beam_sec.get("depth", "?")
        mat_name = mat.get("material_name", "—")
        E_gpa    = mat.get("E", 0) / 1e9
        fy_mpa   = mat.get("fy", 0) / 1e6
        info = (f"截面：柱 {col_w}×{col_d} m  │  梁 {bm_w}×{bm_d} m\n"
                f"材料：{mat_name}   E={E_gpa:.1f} GPa   fy={fy_mpa:.1f} MPa")
        ax.text(total_w / 2, total_h + top_margin * 0.55,
                info, ha="center", va="center", fontsize=FS,
                bbox=dict(boxstyle="round,pad=0.5",
                          facecolor="lightyellow", edgecolor="#888888", alpha=0.9))

        # ── title ─────────────────────────────────────────────────────────
        ax.set_title(
            f"框架结构模型示意图（{num_bays}跨 × {num_stories}层）\n"
            f"请确认：支座 / 荷载 / 跨度 / 层高 / 截面 / 材料",
            fontsize=FS + 2, fontweight="bold", pad=14
        )

        _finalize(ax, fig,
                  dim_x - 0.5, total_w + right_margin + 0.5,
                  -2.0,         total_h + top_margin)
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return output_path


# ---------------------------------------------------------------------------
# Private drawing helpers
# ---------------------------------------------------------------------------

def _draw_pin_support(ax, x, y, size=0.2):
    """Triangle pin support."""
    triangle = plt.Polygon(
        [[x, y], [x - size, y - size], [x + size, y - size]],
        closed=True, facecolor="#888888", edgecolor="black", linewidth=1
    )
    ax.add_patch(triangle)
    ax.plot([x - size * 1.2, x + size * 1.2], [y - size, y - size], "k-", linewidth=1.5)


def _draw_roller_support(ax, x, y, size=0.2):
    """Circle roller support."""
    circle = plt.Circle((x, y - size * 0.6), size * 0.5, facecolor="#AAAAAA", edgecolor="black", linewidth=1)
    ax.add_patch(circle)
    ax.plot([x - size * 1.2, x + size * 1.2], [y - size * 1.2, y - size * 1.2], "k-", linewidth=1.5)


def _draw_fixed_wall(ax, x, y, beam_h, side="left"):
    """Hatched wall for cantilever fixed end."""
    wall_w = 0.3
    wall_h = beam_h * 2.5
    x0 = x - wall_w if side == "left" else x
    rect = mpatches.FancyBboxPatch(
        (x0, y - wall_h / 2), wall_w, wall_h,
        boxstyle="square,pad=0", linewidth=1.5,
        edgecolor="black", facecolor="#AAAAAA", hatch="/////"
    )
    ax.add_patch(rect)


def _draw_fixed_base(ax, x, y, size=0.25):
    """Fixed base symbol (hatched rectangle)."""
    rect = mpatches.FancyBboxPatch(
        (x - size, y - size * 0.6), size * 2, size * 0.6,
        boxstyle="square,pad=0", linewidth=1,
        edgecolor="black", facecolor="#AAAAAA", hatch="////"
    )
    ax.add_patch(rect)


def _draw_distributed_load(ax, x0, x1, y_top, q, ref_len, n_arrows=8, arrow_len=0.4):
    """Draw distributed load arrows and load line above beam."""
    if q == 0:
        return
    direction = -1 if q < 0 else 1  # negative = downward
    tip_y = y_top
    tail_y = tip_y + direction * (-arrow_len)  # arrow from tail to tip

    # Load line
    ax.plot([x0, x1], [tail_y, tail_y], "m-", linewidth=1.5)

    # Arrows
    xs = [x0 + i * (x1 - x0) / (n_arrows - 1) for i in range(n_arrows)]
    for ax_x in xs:
        ax.annotate(
            "", xy=(ax_x, tip_y), xytext=(ax_x, tail_y),
            arrowprops=dict(arrowstyle="-|>", color="magenta", lw=1.2)
        )

    # Label
    q_kn = abs(q) / 1000
    ax.annotate(
        f"q={q_kn:.1f} kN/m",
        xy=((x0 + x1) / 2, tail_y + direction * 0.05),
        ha="center", fontsize=11, color="purple"
    )


def _draw_point_load(ax, x, y, P, arrow_len=0.5):
    """Draw single point load arrow."""
    if P == 0:
        return
    direction = -1 if P < 0 else 1
    tip_y = y
    tail_y = tip_y + direction * (-arrow_len)
    ax.annotate(
        "", xy=(x, tip_y), xytext=(x, tail_y),
        arrowprops=dict(arrowstyle="-|>", color="red", lw=2)
    )
    P_kn = abs(P) / 1000
    ax.annotate(
        f"P={P_kn:.1f}kN",
        xy=(x, tail_y + direction * 0.05),
        ha="center", fontsize=11, color="darkred"
    )


def _finalize(ax, fig, xmin, xmax, ymin, ymax):
    """Set axes limits, remove ticks, add grid."""
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.axis("off")
    fig.tight_layout()
