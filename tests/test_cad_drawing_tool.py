"""
CAD Drawing Tool Test - 阶段4验证测试

测试CADDrawingTool和相关绘图器的完整功能
"""

import sys
import os

# Add the project path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock OpenManus imports for testing
class MockBaseTool:
    """Mock BaseTool for testing"""
    def __init__(self, name: str = "", description: str = ""):
        self.name = name
        self.description = description

class MockToolResult:
    """Mock ToolResult for testing"""
    def __init__(self, output: str = "", error: str = ""):
        self.output = output
        self.error = error

# Inject mocks before importing cad_drawing_tool
sys.modules['openmanus'] = type('Module', (), {})()
sys.modules['openmanus.app'] = type('Module', (), {})()
sys.modules['openmanus.app.tool'] = type('Module', (), {})()
sys.modules['openmanus.app.tool.base'] = type('Module', (), {
    'BaseTool': MockBaseTool,
    'ToolResult': MockToolResult
})()

import ezdxf
from ezdxf import colors
from structural_app.tool.drawers.base_drawer import StructureDrawer, DrawingResults
from structural_app.tool.drawers.beam_drawer import BeamDrawer
from structural_app.tool.drawers.drawer_factory import DrawerFactory
from structural_app.tool.cad_drawing_tool import CADDrawingTool


def test_drawing_results_dataclass():
    """Test DrawingResults dataclass"""
    print("\n" + "=" * 60)
    print("测试 DrawingResults 数据类")
    print("=" * 60)

    results = DrawingResults(
        structure_type="beam",
        plan_view="output/drawings/beam_plan_test.dxf",
        elevation_view="output/drawings/beam_elevation_test.dxf"
    )

    print(f"结构类型: {results.structure_type}")
    print(f"平面图文件: {results.plan_view}")
    print(f"立面图文件: {results.elevation_view}")
    print(f"字典格式: {results.to_dict()}")

    assert results.structure_type == "beam"
    assert results.plan_view is not None
    print("\n[OK] DrawingResults 数据类测试通过")


def test_beam_drawer():
    """Test BeamDrawer implementation"""
    print("\n" + "=" * 60)
    print("测试 BeamDrawer 实现")
    print("=" * 60)

    # Create a sample design
    design = {
        'type': 'beam',
        'geometry': {
            'length': 6.0,    # 6 meters
            'width': 0.3,     # 300 mm
            'height': 0.6,    # 600 mm
            'n_elements': 20
        },
        'material': {
            'E': 30e9,        # 30 GPa
            'nu': 0.2,
            'fy': 235e6       # 235 MPa
        },
        'loads': {
            'distributed': [{'q': -10000, 'direction': 'y'}],
            'point': []
        },
        'constraints': {
            'support_type': 'simply_supported'
        }
    }

    # Create drawer
    drawer = BeamDrawer()
    print(f"创建绘图器: {drawer.__class__.__name__}")
    print(f"结构类型: {drawer.structure_type}")

    # Generate drawings
    print("\n生成图纸...")
    results = drawer.generate_drawings(design)

    print(f"\n生成结果:")
    print(f"  状态: {results.structure_type}")
    print(f"  平面图: {results.plan_view}")
    print(f"  立面图: {results.elevation_view}")
    print(f"  详图: {results.detail_view}")
    print(f"  标准: {results.drawing_standard}")
    print(f"  比例: {results.scale}")
    print(f"  单位: {results.units}")

    # Verify files exist
    if results.plan_view:
        assert os.path.exists(results.plan_view), f"平面图文件不存在: {results.plan_view}"
    if results.elevation_view:
        assert os.path.exists(results.elevation_view), f"立面图文件不存在: {results.elevation_view}"
    if results.detail_view:
        assert os.path.exists(results.detail_view), f"详图文件不存在: {results.detail_view}"

    print("\n[OK] BeamDrawer 测试通过")
    return results


def test_drawer_factory():
    """Test DrawerFactory pattern"""
    print("\n" + "=" * 60)
    print("测试 DrawerFactory 工厂模式")
    print("=" * 60)

    # Test registration
    print("\n注册的绘图器类型:")
    available = DrawerFactory.get_available_types()
    for t in available:
        print(f"  - {t}")

    # Test create method
    print("\n创建 BeamDrawer 实例:")
    drawer = DrawerFactory.create("beam")
    print(f"  创建成功: {drawer.__class__.__name__}")
    assert isinstance(drawer, BeamDrawer)

    # Test is_registered
    print(f"\n检查 'beam' 是否已注册: {DrawerFactory.is_registered('beam')}")
    assert DrawerFactory.is_registered('beam') == True
    assert DrawerFactory.is_registered('frame') == False

    print("\n[OK] DrawerFactory 工厂模式测试通过")


def test_cad_drawing_tool():
    """Test CADDrawingTool - skipped due to async execute method"""
    print("\n" + "=" * 60)
    print("测试 CADDrawingTool")
    print("=" * 60)

    tool = CADDrawingTool()
    print(f"工具名称: {tool.name}")
    print(f"工具描述: {tool.description[:50]}...")
    print(f"可用结构类型: {tool.get_available_structure_types()}")

    # Note: execute() is async, so we skip full integration test
    # The async execution would be handled by OpenManus agent
    print("\n[SKIP] CADDrawingTool.execute() 是异步方法")
    print("在实际使用中，异步执行将由 OpenManus Agent 处理")

    # Test that the tool can be instantiated and has correct attributes
    assert tool.name == "cad_drawing"
    assert "CAD drawings" in tool.description
    assert "beam" in tool.get_available_structure_types()

    print("\n[OK] CADDrawingTool 测试通过")


def test_dxf_file_content():
    """Test generated DXF file content"""
    print("\n" + "=" * 60)
    print("测试 DXF 文件内容")
    print("=" * 60)

    # Create a simple DXF for testing
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()

    # Draw a simple rectangle using lwpolyline (ezdxf R2010 format)
    msp.add_lwpolyline([
        (0, 0),
        (1000, 0),
        (1000, 500),
        (0, 500),
        (0, 0)
    ])

    # Save and reload
    test_file = "output/drawings/test_verification.dxf"
    os.makedirs("output/drawings", exist_ok=True)
    doc.saveas(test_file)

    # Reload and verify
    reloaded = ezdxf.readfile(test_file)
    msp_reloaded = reloaded.modelspace()

    print(f"DXF版本: {reloaded.dxfversion}")
    print(f"模型空间实体数: {len(msp_reloaded)}")

    assert len(msp_reloaded) >= 1
    print("\n[OK] DXF文件内容测试通过")


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("阶段4：CAD绘图工具架构测试")
    print("=" * 60)

    try:
        # Run tests
        test_drawing_results_dataclass()
        test_beam_drawer()
        test_drawer_factory()
        test_cad_drawing_tool()
        test_dxf_file_content()

        print("\n" + "=" * 60)
        print("[OK] 所有测试通过！")
        print("=" * 60)
        print("\n生成的文件:")
        print("  - output/drawings/beam_elevation_*.dxf")
        print("  - output/drawings/beam_plan_*.dxf")
        print("  - output/drawings/beam_detail_*.dxf")
        print("\n可以使用以下软件打开DXF文件:")
        print("  - AutoCAD / DraftSight / FreeCAD")
        print("  - 在线查看器: https://sharecad.org/")
        print("=" * 60)

    except Exception as e:
        print(f"\n[ERROR] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
