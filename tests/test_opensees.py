"""
OpenSees集成测试脚本
测试目标：验证OpenSees能否正常工作并完成简支梁有限元分析
"""

import openseespy.opensees as ops
import numpy as np


def test_simple_beam():
    """
    简支梁有限元分析测试 (使用OpenSees)

    结构参数：
    - 跨度：6m
    - 截面：矩形 300mm × 600mm
    - 材料：C30混凝土 (E=30GPa, ν=0.2)
    - 荷载：均布荷载 10kN/m
    - 边界条件：两端简支
    """

    print("=" * 60)
    print("OpenSees简支梁分析测试")
    print("=" * 60)

    try:
        # 1. 初始化模型
        print("\n[1/6] 初始化OpenSees模型...")
        ops.wipe()  # 清除之前的模型
        ops.model('basic', '-ndm', 2, '-ndf', 3)  # 2D模型，每个节点3个自由度(UX, UY, ROTZ)
        print("OK 模型初始化完成")
        print("  维度: 2D")
        print("  自由度: 3 (UX, UY, ROTZ)")

        # 2. 定义材料和截面
        print("\n[2/6] 定义材料和截面...")

        # 材料参数
        E = 30e9  # 弹性模量 30GPa (Pa)
        nu = 0.2  # 泊松比
        G = E / (2 * (1 + nu))  # 剪切模量

        # 截面参数
        b = 0.3  # 宽度 (m)
        h = 0.6  # 高度 (m)
        A = b * h  # 截面积
        I = b * h**3 / 12  # 惯性矩

        # 定义弹性截面
        sec_tag = 1
        ops.section('Elastic', sec_tag, E, A, I)

        print("OK 材料和截面定义完成")
        print(f"  弹性模量: E={E/1e9}GPa")
        print(f"  泊松比: nu={nu}")
        print(f"  截面: {b*1000}mm x {h*1000}mm")
        print(f"  截面积: A={A:.4f}m^2")
        print(f"  惯性矩: I={I:.6f}m^4")

        # 3. 创建几何模型
        print("\n[3/6] 创建几何模型...")
        L = 6.0  # 跨度 6m
        n_elem = 20  # 单元数量

        # 创建节点
        for i in range(n_elem + 1):
            x = i * L / n_elem
            y = 0.0
            ops.node(i + 1, x, y)

        # 定义边界条件
        # 左端简支：约束UX=0, UY=0, ROTZ自由
        ops.fix(1, 1, 1, 0)
        # 右端简支：约束UY=0, UX和ROTZ自由
        ops.fix(n_elem + 1, 0, 1, 0)

        # 定义几何变换（用于梁单元）
        geom_transf_tag = 1
        ops.geomTransf('Linear', geom_transf_tag)

        # 创建梁单元 (forceBeamColumn单元，基于柔度法)
        for i in range(n_elem):
            ops.element('elasticBeamColumn', i + 1, i + 1, i + 2, A, E, I, geom_transf_tag)

        print("OK 几何模型创建完成")
        print(f"  跨度: {L}m")
        print(f"  节点数: {n_elem + 1}")
        print(f"  单元数: {n_elem}")
        print(f"  单元类型: elasticBeamColumn")

        # 4. 施加荷载
        print("\n[4/6] 施加荷载...")

        # 创建时间序列和荷载模式
        ops.timeSeries('Linear', 1)
        ops.pattern('Plain', 1, 1)

        # 施加均布荷载 10kN/m (向下，沿Y轴负方向)
        q = -10000  # N/m

        # 对每个单元施加均布荷载
        for i in range(n_elem):
            ops.eleLoad('-ele', i + 1, '-type', '-beamUniform', q, 0.0)

        print("OK 荷载施加完成")
        print(f"  荷载类型: 均布荷载")
        print(f"  荷载大小: {abs(q)/1000}kN/m (向下)")

        # 5. 求解
        print("\n[5/6] 开始求解...")

        # 创建分析对象
        ops.system('BandGeneral')  # 求解器
        ops.numberer('RCM')  # 节点编号优化
        ops.constraints('Plain')  # 约束处理
        ops.integrator('LoadControl', 1.0)  # 荷载控制，一步加载
        ops.algorithm('Linear')  # 线性算法
        ops.analysis('Static')  # 静力分析

        # 执行分析
        ok = ops.analyze(1)

        if ok == 0:
            print("OK 求解成功")
        else:
            print("ERROR 求解失败")
            return False

        # 6. 后处理 - 提取结果
        print("\n[6/6] 提取分析结果...")

        # 提取所有节点的位移
        displacements = []
        for i in range(n_elem + 1):
            disp = ops.nodeDisp(i + 1)
            displacements.append(disp[1])  # Y方向位移

        # 找到最大位移（绝对值）
        max_disp = min(displacements)  # 负值最大（向下）
        max_disp_node = displacements.index(max_disp) + 1
        max_disp_location = (max_disp_node - 1) * L / n_elem

        # 提取跨中单元的内力
        mid_elem = n_elem // 2
        forces = ops.eleForce(mid_elem)
        # forces格式: [N1, V1, M1, N2, V2, M2]
        # N=轴力, V=剪力, M=弯矩
        max_moment = max(abs(forces[2]), abs(forces[5]))
        max_shear = max(abs(forces[1]), abs(forces[4]))

        # 计算最大应力（简化：σ = M*y/I，取截面边缘）
        y_max = h / 2  # 距中性轴最远距离
        max_stress = max_moment * y_max / I

        print("OK 结果提取完成")
        print("\n" + "=" * 60)
        print("分析结果")
        print("=" * 60)
        print(f"最大竖向位移: {abs(max_disp)*1000:.2f} mm")
        print(f"  位置: x={max_disp_location:.2f}m (节点{max_disp_node})")
        print(f"最大弯矩: {max_moment/1000:.2f} kN·m")
        print(f"最大剪力: {max_shear/1000:.2f} kN")
        print(f"最大弯曲应力: {max_stress/1e6:.2f} MPa")

        # 理论验证
        print("\n" + "=" * 60)
        print("理论验证")
        print("=" * 60)

        # 简支梁跨中最大挠度: w_max = 5*q*L^4 / (384*E*I)
        w_theory = 5 * abs(q) * L**4 / (384 * E * I)
        print(f"理论跨中挠度: {w_theory*1000:.2f} mm")
        print(f"有限元结果: {abs(max_disp)*1000:.2f} mm")
        print(f"误差: {abs(abs(max_disp) - w_theory) / w_theory * 100:.2f}%")

        # 简支梁跨中最大弯矩: M_max = q*L^2 / 8
        M_theory = abs(q) * L**2 / 8
        print(f"\n理论跨中弯矩: {M_theory/1000:.2f} kN·m")
        print(f"有限元结果: {max_moment/1000:.2f} kN·m")
        print(f"误差: {abs(max_moment - M_theory) / M_theory * 100:.2f}%")

        # 简支梁支座最大剪力: V_max = q*L / 2
        V_theory = abs(q) * L / 2
        print(f"\n理论支座剪力: {V_theory/1000:.2f} kN")
        print(f"有限元结果: {max_shear/1000:.2f} kN")
        print(f"误差: {abs(max_shear - V_theory) / V_theory * 100:.2f}%")

        # 最大弯曲应力
        stress_theory = M_theory * y_max / I
        print(f"\n理论最大应力: {stress_theory/1e6:.2f} MPa")
        print(f"有限元结果: {max_stress/1e6:.2f} MPa")
        print(f"误差: {abs(max_stress - stress_theory) / stress_theory * 100:.2f}%")

        print("\n" + "=" * 60)
        print("OK 测试成功！OpenSees工作正常")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\nERROR 分析过程出错: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # 清理模型
        print("\n清理OpenSees模型...")
        ops.wipe()
        print("OK OpenSees模型已清理")


if __name__ == "__main__":
    success = test_simple_beam()
    exit(0 if success else 1)
