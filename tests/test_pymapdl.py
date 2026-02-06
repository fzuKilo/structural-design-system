"""
PyMAPDL集成测试脚本
测试目标：验证Ansys MAPDL能否正常启动并完成简支梁有限元分析
"""

from ansys.mapdl.core import launch_mapdl
import numpy as np


def test_simple_beam():
    """
    简支梁有限元分析测试

    结构参数：
    - 跨度：6m
    - 截面：矩形 300mm × 600mm
    - 材料：C30混凝土 (E=30GPa, ν=0.2)
    - 荷载：均布荷载 10kN/m
    - 边界条件：两端简支
    """

    print("=" * 60)
    print("PyMAPDL简支梁分析测试")
    print("=" * 60)

    # 1. 启动MAPDL
    print("\n[1/6] 启动MAPDL...")
    try:
        mapdl = launch_mapdl()
        print(f"✓ MAPDL启动成功")
        print(f"  版本: {mapdl.version}")
    except Exception as e:
        print(f"✗ MAPDL启动失败: {e}")
        return False

    try:
        # 2. 设置分析类型和单元类型
        print("\n[2/6] 设置分析参数...")
        mapdl.clear()
        mapdl.prep7()  # 进入前处理

        # 定义单元类型：BEAM188 (3D梁单元)
        mapdl.et(1, "BEAM188")

        # 定义材料属性
        E = 30e9  # 弹性模量 30GPa (Pa)
        nu = 0.2  # 泊松比
        mapdl.mp("EX", 1, E)
        mapdl.mp("PRXY", 1, nu)

        # 定义截面属性 (矩形截面 300mm × 600mm)
        b = 0.3  # 宽度 (m)
        h = 0.6  # 高度 (m)
        mapdl.sectype(1, "BEAM", "RECT")
        mapdl.secdata(b, h)

        print("✓ 分析参数设置完成")
        print(f"  单元类型: BEAM188")
        print(f"  材料: E={E/1e9}GPa, ν={nu}")
        print(f"  截面: {b*1000}mm × {h*1000}mm")

        # 3. 创建几何模型
        print("\n[3/6] 创建几何模型...")
        L = 6.0  # 跨度 6m
        n_elem = 20  # 单元数量

        # 创建节点
        for i in range(n_elem + 1):
            x = i * L / n_elem
            mapdl.n(i + 1, x, 0, 0)

        # 创建单元
        for i in range(n_elem):
            mapdl.e(i + 1, i + 2)

        print(f"✓ 几何模型创建完成")
        print(f"  跨度: {L}m")
        print(f"  节点数: {n_elem + 1}")
        print(f"  单元数: {n_elem}")

        # 4. 施加边界条件和荷载
        print("\n[4/6] 施加边界条件和荷载...")

        # 边界条件：左端简支（约束UY, UZ, ROTX, ROTZ）
        mapdl.d(1, "UY", 0)
        mapdl.d(1, "UZ", 0)
        mapdl.d(1, "ROTX", 0)
        mapdl.d(1, "ROTZ", 0)

        # 边界条件：右端简支（约束UX, UY, UZ, ROTX, ROTZ）
        mapdl.d(n_elem + 1, "UX", 0)
        mapdl.d(n_elem + 1, "UY", 0)
        mapdl.d(n_elem + 1, "UZ", 0)
        mapdl.d(n_elem + 1, "ROTX", 0)
        mapdl.d(n_elem + 1, "ROTZ", 0)

        # 施加均布荷载 10kN/m (向下，沿Y轴负方向)
        q = -10000  # N/m
        mapdl.sfbeam("ALL", 1, "PRES", q)

        print("✓ 边界条件和荷载施加完成")
        print(f"  左端: 简支 (约束UY, UZ, ROTX, ROTZ)")
        print(f"  右端: 简支 (约束UX, UY, UZ, ROTX, ROTZ)")
        print(f"  荷载: 均布荷载 {abs(q)/1000}kN/m (向下)")

        # 5. 求解
        print("\n[5/6] 开始求解...")
        mapdl.finish()
        mapdl.slashsolu()  # 进入求解器
        mapdl.antype("STATIC")  # 静力分析
        mapdl.solve()
        mapdl.finish()

        print("✓ 求解完成")

        # 6. 后处理 - 提取结果
        print("\n[6/6] 提取分析结果...")
        mapdl.post1()  # 进入后处理
        mapdl.set(1, 1)  # 读取第一个载荷步的结果

        # 获取最大位移
        max_disp = mapdl.post_processing.nodal_displacement('Y').min()

        # 获取最大应力
        mapdl.etable("STRESS", "LS", 1)  # 提取轴向应力
        max_stress = mapdl.get_value("ETAB", 0, "MAX")

        print("✓ 结果提取完成")
        print("\n" + "=" * 60)
        print("分析结果")
        print("=" * 60)
        print(f"最大竖向位移: {abs(max_disp)*1000:.2f} mm")
        print(f"最大应力: {abs(max_stress)/1e6:.2f} MPa")

        # 理论验证（简支梁跨中最大挠度）
        I = b * h**3 / 12  # 惯性矩
        w_theory = 5 * abs(q) * L**4 / (384 * E * I)
        print(f"\n理论跨中挠度: {w_theory*1000:.2f} mm")
        print(f"误差: {abs(abs(max_disp) - w_theory) / w_theory * 100:.2f}%")

        print("\n" + "=" * 60)
        print("✓ 测试成功！PyMAPDL工作正常")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\n✗ 分析过程出错: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # 关闭MAPDL
        print("\n关闭MAPDL...")
        mapdl.exit()
        print("✓ MAPDL已关闭")


if __name__ == "__main__":
    success = test_simple_beam()
    exit(0 if success else 1)
