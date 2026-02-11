"""
CAD绘图测试脚本 - 阶段2

测试ezdxf库的基本绘图功能：
1. 绘制简支梁立面图（6米跨度）
2. 添加支座符号（铰支座、滚动支座）
3. 添加尺寸标注
4. 生成DXF文件

运行方式：
    python tests/test_cad_drawing.py
"""

import ezdxf
from ezdxf import colors
import os
from datetime import datetime


def create_beam_elevation_drawing():
    """
    创建简支梁立面图

    梁参数：
    - 跨度：6000 mm (6米)
    - 截面宽度：300 mm
    - 截面高度：600 mm
    """

    # 创建新的DXF文档（R2010版本，兼容性好）
    doc = ezdxf.new('R2010', setup=True)

    # 获取模型空间（所有图形都绘制在这里）
    msp = doc.modelspace()

    # ========== 设置中文字体样式 ==========
    # ezdxf 需要使用 keyword-only 参数 'font'
    try:
        # 添加文字样式，使用Windows系统字体
        doc.styles.new(
            name='CHINESE',
            dxfattribs={
                'font': 'simhei.ttf',  # 黑体，Windows自带
            }
        )
    except Exception:
        # 如果simhei.ttf不存在，尝试其他字体
        try:
            doc.styles.new(
                name='CHINESE',
                dxfattribs={
                    'font': 'simsun.ttc',  # 宋体
                }
            )
        except Exception:
            # 如果都失败，使用标准样式
            doc.styles.new(
                name='CHINESE',
                dxfattribs={
                    'font': 'Arial.ttf',  # Arial作为备选
                }
            )

    # ========== 梁参数定义 ==========
    beam_length = 6000  # 梁长度 (mm)
    beam_width = 300    # 梁宽度 (mm)
    beam_height = 600   # 梁高度 (mm)

    # 绘图起点（左下角）
    start_x = 0
    start_y = 0

    print("=" * 60)
    print("开始绘制简支梁立面图")
    print("=" * 60)
    print(f"梁参数：")
    print(f"  跨度: {beam_length} mm")
    print(f"  宽度: {beam_width} mm")
    print(f"  高度: {beam_height} mm")
    print()

    # ========== 1. 绘制梁的矩形轮廓 ==========
    print("1. 绘制梁的矩形轮廓...")

    # 定义矩形的四个角点
    beam_corners = [
        (start_x, start_y),                          # 左下角
        (start_x + beam_length, start_y),            # 右下角
        (start_x + beam_length, start_y + beam_height),  # 右上角
        (start_x, start_y + beam_height),            # 左上角
        (start_x, start_y)                           # 闭合到左下角
    ]

    # 绘制梁轮廓（使用POLYLINE，线宽0.5mm）
    msp.add_lwpolyline(
        beam_corners,
        dxfattribs={
            'color': colors.BLACK,
            'const_width': 0.5  # 线宽
        }
    )

    # ========== 2. 绘制支座符号 ==========
    print("2. 绘制支座符号...")

    # 支座参数
    support_size = 400  # 支座符号大小

    # 左侧铰支座（三角形）
    left_support_x = start_x
    left_support_y = start_y - support_size

    # 绘制铰支座三角形
    hinge_points = [
        (left_support_x, start_y),                    # 顶点（梁底）
        (left_support_x - support_size/2, left_support_y),  # 左下角
        (left_support_x + support_size/2, left_support_y),  # 右下角
        (left_support_x, start_y)                     # 闭合
    ]

    msp.add_lwpolyline(
        hinge_points,
        dxfattribs={
            'color': colors.BLUE,
            'const_width': 0.3
        }
    )

    # 绘制铰支座底部的地面线（斜线填充）
    ground_y = left_support_y - 100
    for i in range(-3, 4):
        x_offset = i * 80
        msp.add_line(
            (left_support_x + x_offset, left_support_y),
            (left_support_x + x_offset - 100, ground_y),
            dxfattribs={'color': colors.BLUE, 'lineweight': 13}
        )

    # 右侧滚动支座（三角形 + 圆）
    right_support_x = start_x + beam_length
    right_support_y = start_y - support_size

    # 绘制滚动支座三角形
    roller_points = [
        (right_support_x, start_y),                    # 顶点（梁底）
        (right_support_x - support_size/2, right_support_y),  # 左下角
        (right_support_x + support_size/2, right_support_y),  # 右下角
        (right_support_x, start_y)                     # 闭合
    ]

    msp.add_lwpolyline(
        roller_points,
        dxfattribs={
            'color': colors.BLUE,
            'const_width': 0.3
        }
    )

    # 绘制滚动支座的圆（表示可滚动）
    roller_radius = 100
    msp.add_circle(
        (right_support_x, right_support_y - roller_radius),
        radius=roller_radius,
        dxfattribs={'color': colors.BLUE}
    )

    # 绘制滚动支座底部的地面线
    ground_y = right_support_y - 2 * roller_radius - 100
    for i in range(-3, 4):
        x_offset = i * 80
        msp.add_line(
            (right_support_x + x_offset, right_support_y - 2 * roller_radius),
            (right_support_x + x_offset - 100, ground_y),
            dxfattribs={'color': colors.BLUE, 'lineweight': 13}
        )

    # ========== 3. 添加尺寸标注 ==========
    print("3. 添加尺寸标注...")

    # 创建标注样式
    dimstyle = doc.dimstyles.get('EZDXF')
    dimstyle.dxf.dimtxt = 150  # 文字高度
    dimstyle.dxf.dimasz = 100  # 箭头大小

    # 标注梁的跨度（水平尺寸）
    dim_y_offset = -1200  # 标注线距离梁底的距离
    dim = msp.add_linear_dim(
        base=(start_x + beam_length/2, start_y + dim_y_offset),  # 标注线位置
        p1=(start_x, start_y),                                    # 起点
        p2=(start_x + beam_length, start_y),                      # 终点
        dimstyle='EZDXF',
        override={
            'dimtxt': 150,
            'dimclrt': colors.RED  # 标注颜色
        }
    )

    # 标注梁的高度（垂直尺寸）
    dim_x_offset = -800  # 标注线距离梁左侧的距离
    dim = msp.add_linear_dim(
        base=(start_x + dim_x_offset, start_y + beam_height/2),  # 标注线位置
        p1=(start_x, start_y),                                    # 起点
        p2=(start_x, start_y + beam_height),                      # 终点
        angle=90,  # 垂直标注
        dimstyle='EZDXF',
        override={
            'dimtxt': 150,
            'dimclrt': colors.RED
        }
    )

    # ========== 4. 添加文字说明 ==========
    print("4. 添加文字说明...")

    # 标题
    msp.add_text(
        "简支梁立面图",
        dxfattribs={
            'style': 'CHINESE',
            'height': 300,
            'color': colors.BLACK
        }
    ).set_placement(
        (start_x + beam_length/2, start_y + beam_height + 800),
        align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER
    )

    # 左支座标注
    msp.add_text(
        "铰支座",
        dxfattribs={
            'style': 'CHINESE',
            'height': 150,
            'color': colors.BLUE
        }
    ).set_placement(
        (left_support_x, left_support_y - 500),
        align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER
    )

    # 右支座标注
    msp.add_text(
        "滚动支座",
        dxfattribs={
            'style': 'CHINESE',
            'height': 150,
            'color': colors.BLUE
        }
    ).set_placement(
        (right_support_x, right_support_y - 800),
        align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER
    )

    # 技术参数文字
    param_x = start_x + beam_length + 1000
    param_y = start_y + beam_height
    line_spacing = 300

    params_text = [
        "技术参数:",
        f"跨度 L = {beam_length} mm",
        f"截面宽度 b = {beam_width} mm",
        f"截面高度 h = {beam_height} mm",
        "材料: C30混凝土",
        "设计荷载: 10 kN/m"
    ]

    for i, text in enumerate(params_text):
        msp.add_text(
            text,
            dxfattribs={
                'style': 'CHINESE',
                'height': 120,
                'color': colors.BLACK
            }
        ).set_placement(
            (param_x, param_y - i * line_spacing),
            align=ezdxf.enums.TextEntityAlignment.LEFT
        )

    # ========== 5. 保存DXF文件 ==========
    print("5. 保存DXF文件...")

    # 创建输出目录
    output_dir = "output/drawings"
    os.makedirs(output_dir, exist_ok=True)

    # 生成文件名（带时间戳）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{output_dir}/beam_elevation_{timestamp}.dxf"

    # 保存文件
    doc.saveas(filename)

    print()
    print("=" * 60)
    print("[OK] 绘图完成！")
    print("=" * 60)
    print(f"DXF文件已保存到: {filename}")
    print()
    print("下一步：")
    print("1. 使用CAD软件打开DXF文件验证")
    print("   - AutoCAD")
    print("   - DraftSight")
    print("   - FreeCAD")
    print("   - 在线查看器: https://sharecad.org/")
    print()
    print("2. 检查图纸内容：")
    print("   [OK] 梁的矩形轮廓")
    print("   [OK] 左侧铰支座（三角形）")
    print("   [OK] 右侧滚动支座（三角形+圆）")
    print("   [OK] 尺寸标注（跨度和高度）")
    print("   [OK] 文字说明（中文）")
    print("=" * 60)

    return filename


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("CAD绘图测试 - 阶段2")
    print("测试ezdxf库的基本绘图功能")
    print("=" * 60 + "\n")

    try:
        # 创建简支梁立面图
        filename = create_beam_elevation_drawing()

        print("\n[OK] 测试成功！")
        print(f"\n生成的文件: {filename}")

    except Exception as e:
        print(f"\n[ERROR] 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
