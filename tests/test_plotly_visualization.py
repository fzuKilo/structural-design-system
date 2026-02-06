"""
Plotly交互式可视化示例
演示如何使用Plotly创建交互式结构分析图表
"""

import openseespy.opensees as ops
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots


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


def plot_displacement_interactive(results, save_path='output/displacement_interactive.html'):
    """
    绘制交互式位移云图
    """
    nodes = results['nodes']
    displacements = results['displacements']
    n_elem = results['n_elem']

    # 创建变形后的节点坐标（放大变形）
    scale = 1000
    deformed_y = displacements * scale

    fig = go.Figure()

    # 添加原始形状（灰色虚线）
    fig.add_trace(go.Scatter(
        x=nodes[:, 0],
        y=nodes[:, 1],
        mode='lines',
        line=dict(color='gray', width=2, dash='dash'),
        name='原始形状',
        hoverinfo='skip'
    ))

    # 添加变形后的彩色线段
    for i in range(n_elem):
        # 计算颜色（基于位移大小）
        disp_value = abs(displacements[i])
        color_intensity = disp_value / abs(displacements).max()

        fig.add_trace(go.Scatter(
            x=[nodes[i, 0], nodes[i+1, 0]],
            y=[deformed_y[i], deformed_y[i+1]],
            mode='lines',
            line=dict(
                color=f'rgb({int(255*color_intensity)}, {int(100*(1-color_intensity))}, {int(255*(1-color_intensity))})',
                width=8
            ),
            name=f'单元 {i+1}',
            hovertemplate=(
                f'<b>单元 {i+1}</b><br>' +
                f'位置: %{{x:.2f}} m<br>' +
                f'位移: {abs(displacements[i])*1000:.3f} mm<br>' +
                '<extra></extra>'
            ),
            showlegend=False
        ))

    # 添加支座标记
    fig.add_trace(go.Scatter(
        x=[nodes[0, 0], nodes[-1, 0]],
        y=[0, 0],
        mode='markers',
        marker=dict(size=15, color='black', symbol='triangle-down'),
        name='支座',
        hovertemplate='<b>支座</b><extra></extra>'
    ))

    # 布局设置
    fig.update_layout(
        title=dict(
            text=f'交互式位移云图 (变形放大 {scale}x)',
            font=dict(size=18, family='Arial', color='black')
        ),
        xaxis=dict(
            title='长度 (m)',
            gridcolor='lightgray',
            showgrid=True
        ),
        yaxis=dict(
            title='高度 (m)',
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

    fig.write_html(save_path)
    print(f"OK Interactive displacement plot saved: {save_path}")
    return fig


def plot_moment_interactive(results, save_path='output/moment_interactive.html'):
    """
    绘制交互式弯矩云图
    """
    nodes = results['nodes']
    moments = results['moments']
    n_elem = results['n_elem']

    # 计算单元中心点
    elem_centers_x = []
    for i in range(n_elem):
        center_x = (nodes[i, 0] + nodes[i+1, 0]) / 2
        elem_centers_x.append(center_x)

    fig = go.Figure()

    # 添加彩色线段（基于弯矩大小）
    for i in range(n_elem):
        # 计算颜色（基于弯矩大小）
        moment_ratio = moments[i] / moments.max()

        fig.add_trace(go.Scatter(
            x=[nodes[i, 0], nodes[i+1, 0]],
            y=[0, 0],
            mode='lines',
            line=dict(
                color=f'rgb({int(255*moment_ratio)}, {int(255*(1-moment_ratio)*0.5)}, {int(255*(1-moment_ratio))})',
                width=12
            ),
            name=f'单元 {i+1}',
            hovertemplate=(
                f'<b>单元 {i+1}</b><br>' +
                f'位置: {elem_centers_x[i]:.2f} m<br>' +
                f'弯矩: {moments[i]/1000:.2f} kN·m<br>' +
                '<extra></extra>'
            ),
            showlegend=False
        ))

    # 添加支座标记
    fig.add_trace(go.Scatter(
        x=[nodes[0, 0], nodes[-1, 0]],
        y=[0, 0],
        mode='markers',
        marker=dict(size=15, color='black', symbol='triangle-down'),
        name='支座',
        hovertemplate='<b>支座</b><extra></extra>'
    ))

    # 标注最大弯矩
    max_moment_idx = np.argmax(moments)
    max_moment = moments[max_moment_idx]
    max_moment_x = elem_centers_x[max_moment_idx]

    fig.add_annotation(
        x=max_moment_x,
        y=0.1,
        text=f'最大弯矩: {max_moment/1000:.2f} kN·m',
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

    # 布局设置
    fig.update_layout(
        title=dict(
            text='交互式弯矩云图',
            font=dict(size=18, family='Arial', color='black')
        ),
        xaxis=dict(
            title='长度 (m)',
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

    fig.write_html(save_path)
    print(f"OK Interactive moment plot saved: {save_path}")
    return fig


def plot_stress_interactive(results, save_path='output/stress_interactive.html'):
    """
    绘制交互式应力云图
    """
    nodes = results['nodes']
    stresses = results['stresses']
    n_elem = results['n_elem']

    # 计算单元中心点
    elem_centers_x = []
    for i in range(n_elem):
        center_x = (nodes[i, 0] + nodes[i+1, 0]) / 2
        elem_centers_x.append(center_x)

    fig = go.Figure()

    # 添加彩色线段（基于应力大小）
    for i in range(n_elem):
        # 计算颜色（基于应力大小）
        stress_ratio = stresses[i] / stresses.max()

        fig.add_trace(go.Scatter(
            x=[nodes[i, 0], nodes[i+1, 0]],
            y=[0, 0],
            mode='lines',
            line=dict(
                color=f'rgb({int(255*stress_ratio)}, {int(100*(1-stress_ratio))}, {int(255*(1-stress_ratio))})',
                width=12
            ),
            name=f'单元 {i+1}',
            hovertemplate=(
                f'<b>单元 {i+1}</b><br>' +
                f'位置: {elem_centers_x[i]:.2f} m<br>' +
                f'应力: {stresses[i]/1e6:.2f} MPa<br>' +
                '<extra></extra>'
            ),
            showlegend=False
        ))

    # 添加支座标记
    fig.add_trace(go.Scatter(
        x=[nodes[0, 0], nodes[-1, 0]],
        y=[0, 0],
        mode='markers',
        marker=dict(size=15, color='black', symbol='triangle-down'),
        name='支座',
        hovertemplate='<b>支座</b><extra></extra>'
    ))

    # 标注最大应力
    max_stress_idx = np.argmax(stresses)
    max_stress = stresses[max_stress_idx]
    max_stress_x = elem_centers_x[max_stress_idx]

    fig.add_annotation(
        x=max_stress_x,
        y=0.1,
        text=f'最大应力: {max_stress/1e6:.2f} MPa',
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

    # 布局设置
    fig.update_layout(
        title=dict(
            text='交互式应力云图',
            font=dict(size=18, family='Arial', color='black')
        ),
        xaxis=dict(
            title='长度 (m)',
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

    fig.write_html(save_path)
    print(f"OK Interactive stress plot saved: {save_path}")
    return fig


def plot_all_interactive(results):
    """
    Generate all interactive visualization plots
    """
    print("\n" + "="*60)
    print("Generating Plotly Interactive Visualization Plots")
    print("="*60)

    import os
    os.makedirs('output', exist_ok=True)

    print("\n[1/3] Generating interactive displacement plot...")
    plot_displacement_interactive(results)

    print("\n[2/3] Generating interactive moment plot...")
    plot_moment_interactive(results)

    print("\n[3/3] Generating interactive stress plot...")
    plot_stress_interactive(results)

    print("\n" + "="*60)
    print("OK All interactive plots generated successfully!")
    print("="*60)
    print("\nGenerated files:")
    print("  - output/displacement_interactive.html")
    print("  - output/moment_interactive.html")
    print("  - output/stress_interactive.html")
    print("\nTips: Open HTML files in browser to view interactive plots")
    print("   - Hover to see detailed values")
    print("   - Scroll to zoom")
    print("   - Drag to pan")
    print("   - Double-click to reset view")


if __name__ == "__main__":
    print("="*60)
    print("Plotly Interactive Visualization Demo")
    print("="*60)

    print("\nRunning structural analysis...")
    results = analyze_simple_beam()
    print("OK Analysis completed")

    print(f"\nAnalysis Results Summary:")
    print(f"  Max displacement: {abs(min(results['displacements']))*1000:.2f} mm")
    print(f"  Max moment: {max(results['moments'])/1000:.2f} kN·m")
    print(f"  Max stress: {max(results['stresses'])/1e6:.2f} MPa")

    plot_all_interactive(results)
