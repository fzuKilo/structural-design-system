"""
OpenSees结果可视化示例
演示如何使用matplotlib绘制各种"云图"效果
"""

import openseespy.opensees as ops
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.colors import Normalize
import matplotlib.patches as patches


def analyze_simple_beam():
    """
    运行简支梁分析并返回结果
    """
    # 初始化模型
    ops.wipe()
    ops.model('basic', '-ndm', 2, '-ndf', 3)

    # 材料和截面参数
    E = 30e9  # Pa
    nu = 0.2
    b = 0.3  # m
    h = 0.6  # m
    A = b * h
    I = b * h**3 / 12

    # 几何参数
    L = 6.0  # m
    n_elem = 20

    # 创建节点
    nodes = []
    for i in range(n_elem + 1):
        x = i * L / n_elem
        y = 0.0
        ops.node(i + 1, x, y)
        nodes.append([x, y])

    # 边界条件
    ops.fix(1, 1, 1, 0)
    ops.fix(n_elem + 1, 0, 1, 0)

    # 创建单元
    geom_transf_tag = 1
    ops.geomTransf('Linear', geom_transf_tag)

    for i in range(n_elem):
        ops.element('elasticBeamColumn', i + 1, i + 1, i + 2, A, E, I, geom_transf_tag)

    # 施加荷载
    ops.timeSeries('Linear', 1)
    ops.pattern('Plain', 1, 1)
    q = -10000  # N/m

    for i in range(n_elem):
        ops.eleLoad('-ele', i + 1, '-type', '-beamUniform', q, 0.0)

    # 求解
    ops.system('BandGeneral')
    ops.numberer('RCM')
    ops.constraints('Plain')
    ops.integrator('LoadControl', 1.0)
    ops.algorithm('Linear')
    ops.analysis('Static')
    ops.analyze(1)

    # 提取结果
    displacements = []
    for i in range(n_elem + 1):
        disp = ops.nodeDisp(i + 1)
        displacements.append(disp[1])  # Y方向位移

    # 提取单元内力
    moments = []
    shears = []
    for i in range(n_elem):
        forces = ops.eleForce(i + 1)
        # 取单元两端弯矩的平均值
        moment = (abs(forces[2]) + abs(forces[5])) / 2
        shear = abs(forces[1])
        moments.append(moment)
        shears.append(shear)

    # 计算应力 (σ = M*y/I)
    y_max = h / 2
    stresses = [M * y_max / I for M in moments]

    ops.wipe()

    return {
        'nodes': np.array(nodes),
        'n_elem': n_elem,
        'L': L,
        'displacements': np.array(displacements),
        'moments': np.array(moments),
        'shears': np.array(shears),
        'stresses': np.array(stresses),
        'h': h,
        'I': I
    }


def plot_displacement_cloud(results, save_path='output/displacement_cloud.png'):
    """
    绘制位移云图
    """
    nodes = results['nodes']
    displacements = results['displacements']
    n_elem = results['n_elem']

    # 创建变形后的节点坐标（放大变形）
    scale = 1000  # 放大倍数
    deformed_nodes = nodes.copy()
    deformed_nodes[:, 1] += displacements * scale

    # 创建线段和颜色
    segments = []
    colors = []

    for i in range(n_elem):
        segment = [deformed_nodes[i], deformed_nodes[i+1]]
        segments.append(segment)
        # 颜色基于位移大小（取绝对值）
        color_value = abs(displacements[i])
        colors.append(color_value)

    # 创建图形
    fig, ax = plt.subplots(figsize=(14, 6))

    # 绘制原始形状（灰色虚线）
    ax.plot(nodes[:, 0], nodes[:, 1], 'k--', linewidth=1, alpha=0.3, label='Original Shape')

    # 绘制变形后的彩色云图
    lc = LineCollection(segments, cmap='jet',
                        norm=Normalize(vmin=0, vmax=max(colors)),
                        linewidths=8)
    lc.set_array(np.array(colors))

    ax.add_collection(lc)

    # 添加颜色条
    cbar = plt.colorbar(lc, ax=ax, label='Displacement (m)')
    cbar.ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x*1000:.2f} mm'))

    # 绘制支座
    support_size = 0.2
    # 左支座（固定铰）
    triangle1 = patches.Polygon([[nodes[0, 0]-support_size/2, 0],
                                  [nodes[0, 0]+support_size/2, 0],
                                  [nodes[0, 0], -support_size]],
                                 closed=True, facecolor='gray', edgecolor='black')
    ax.add_patch(triangle1)

    # 右支座（滚动铰）
    triangle2 = patches.Polygon([[nodes[-1, 0]-support_size/2, 0],
                                  [nodes[-1, 0]+support_size/2, 0],
                                  [nodes[-1, 0], -support_size]],
                                 closed=True, facecolor='gray', edgecolor='black')
    ax.add_patch(triangle2)
    circle = patches.Circle((nodes[-1, 0], -support_size), support_size/3,
                            facecolor='white', edgecolor='black')
    ax.add_patch(circle)

    # 计算合适的显示范围（确保变形后的梁完全显示）
    y_min = min(deformed_nodes[:, 1].min(), -support_size - 0.1)
    y_max = max(deformed_nodes[:, 1].max(), 0.5)
    y_range = y_max - y_min

    ax.set_xlim(-0.5, results['L'] + 0.5)
    ax.set_ylim(y_min - y_range*0.1, y_max + y_range*0.1)  # 留10%边距
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3)
    ax.set_xlabel('Length (m)', fontsize=12)
    ax.set_ylabel('Height (m)', fontsize=12)
    ax.set_title(f'Displacement Cloud Plot (Deformation Scale: {scale}x)', fontsize=14, fontweight='bold')
    ax.legend()

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    print(f"OK Displacement cloud plot saved: {save_path}")
    plt.close()


def plot_moment_cloud(results, save_path='output/moment_cloud.png'):
    """
    绘制弯矩云图
    """
    nodes = results['nodes']
    moments = results['moments']
    n_elem = results['n_elem']

    # 计算单元中心点
    elem_centers = []
    for i in range(n_elem):
        center_x = (nodes[i, 0] + nodes[i+1, 0]) / 2
        center_y = (nodes[i, 1] + nodes[i+1, 1]) / 2
        elem_centers.append([center_x, center_y])
    elem_centers = np.array(elem_centers)

    # 创建线段
    segments = []
    for i in range(n_elem):
        segment = [nodes[i], nodes[i+1]]
        segments.append(segment)

    # 创建图形
    fig, ax = plt.subplots(figsize=(14, 6))

    # 绘制彩色云图
    lc = LineCollection(segments, cmap='RdYlBu_r',
                        norm=Normalize(vmin=0, vmax=max(moments)),
                        linewidths=10)
    lc.set_array(moments)

    ax.add_collection(lc)

    # 添加颜色条
    cbar = plt.colorbar(lc, ax=ax, label='Bending Moment (N·m)')
    cbar.ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1000:.1f} kN·m'))

    # 绘制支座
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

    ax.set_xlim(-0.5, results['L'] + 0.5)
    ax.set_ylim(-0.5, 0.5)
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3)
    ax.set_xlabel('Length (m)', fontsize=12)
    ax.set_ylabel('Height (m)', fontsize=12)
    ax.set_title('Bending Moment Cloud Plot', fontsize=14, fontweight='bold')

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    print(f"OK Moment cloud plot saved: {save_path}")
    plt.close()


def plot_stress_cloud(results, save_path='output/stress_cloud.png'):
    """
    绘制应力云图
    """
    nodes = results['nodes']
    stresses = results['stresses']
    n_elem = results['n_elem']

    # 创建线段
    segments = []
    for i in range(n_elem):
        segment = [nodes[i], nodes[i+1]]
        segments.append(segment)

    # 创建图形
    fig, ax = plt.subplots(figsize=(14, 6))

    # 绘制彩色云图
    lc = LineCollection(segments, cmap='coolwarm',
                        norm=Normalize(vmin=0, vmax=max(stresses)),
                        linewidths=10)
    lc.set_array(stresses)

    ax.add_collection(lc)

    # 添加颜色条
    cbar = plt.colorbar(lc, ax=ax, label='Bending Stress (Pa)')
    cbar.ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1e6:.2f} MPa'))

    # 绘制支座
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

    ax.set_xlim(-0.5, results['L'] + 0.5)
    ax.set_ylim(-0.5, 0.5)
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3)
    ax.set_xlabel('Length (m)', fontsize=12)
    ax.set_ylabel('Height (m)', fontsize=12)
    ax.set_title('Bending Stress Cloud Plot', fontsize=14, fontweight='bold')

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    print(f"OK Stress cloud plot saved: {save_path}")
    plt.close()


def plot_moment_diagram(results, save_path='output/moment_diagram.png'):
    """
    绘制传统的弯矩图（带填充）
    """
    nodes = results['nodes']
    moments = results['moments']
    n_elem = results['n_elem']

    # 计算单元中心点
    elem_centers_x = []
    for i in range(n_elem):
        center_x = (nodes[i, 0] + nodes[i+1, 0]) / 2
        elem_centers_x.append(center_x)

    fig, ax = plt.subplots(figsize=(14, 6))

    # 绘制梁的轮廓
    ax.plot([0, results['L']], [0, 0], 'k-', linewidth=3, label='Beam')

    # 绘制弯矩图（向下为正）
    moment_scale = 0.00005  # 缩放因子
    moment_y = -np.array(moments) * moment_scale

    # 填充弯矩图
    ax.fill_between(elem_centers_x, 0, moment_y, alpha=0.6, color='red', label='Bending Moment')
    ax.plot(elem_centers_x, moment_y, 'r-', linewidth=2)

    # 绘制支座
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

    # 标注最大弯矩
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

    ax.set_xlim(-0.5, results['L'] + 0.5)
    ax.set_ylim(-3, 0.5)
    ax.grid(True, alpha=0.3)
    ax.set_xlabel('Length (m)', fontsize=12)
    ax.set_ylabel('Bending Moment', fontsize=12)
    ax.set_title('Bending Moment Diagram', fontsize=14, fontweight='bold')
    ax.legend(fontsize=11)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    print(f"OK Moment diagram saved: {save_path}")
    plt.close()


def plot_all_results(results):
    """
    生成所有可视化图形
    """
    print("\n" + "="*60)
    print("Generating Visualization Plots")
    print("="*60)

    import os
    os.makedirs('output', exist_ok=True)

    print("\n[1/4] Generating displacement cloud plot...")
    plot_displacement_cloud(results)

    print("\n[2/4] Generating moment cloud plot...")
    plot_moment_cloud(results)

    print("\n[3/4] Generating stress cloud plot...")
    plot_stress_cloud(results)

    print("\n[4/4] Generating moment diagram...")
    plot_moment_diagram(results)

    print("\n" + "="*60)
    print("OK All plots generated successfully!")
    print("="*60)
    print("\nGenerated files:")
    print("  - output/displacement_cloud.png")
    print("  - output/moment_cloud.png")
    print("  - output/stress_cloud.png")
    print("  - output/moment_diagram.png")


if __name__ == "__main__":
    print("="*60)
    print("OpenSees Visualization Demo")
    print("="*60)

    print("\nRunning structural analysis...")
    results = analyze_simple_beam()
    print("OK Analysis completed")

    print(f"\nAnalysis Results Summary:")
    print(f"  Max displacement: {abs(min(results['displacements']))*1000:.2f} mm")
    print(f"  Max moment: {max(results['moments'])/1000:.2f} kN·m")
    print(f"  Max stress: {max(results['stresses'])/1e6:.2f} MPa")

    plot_all_results(results)
