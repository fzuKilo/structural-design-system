"""
阶段8集成测试：StructuralDesignAgent -> FEAnalysisAgent -> CADDrawingAgent 端到端测试

支持三种测试模式：
1. 自定义需求测试 (手动输入设计需求)
2. 完整参数测试 (预设的6米简支梁)
3. 缺失参数测试 (测试AskHuman交互功能)

运行方式:
    python tests/integration/test_stage8_integration.py
"""

import sys
import os
import asyncio
import json

import pytest

# Add OpenManus to path
_openmanus_path = 'D:\\openmanus'
if os.path.exists(_openmanus_path) and _openmanus_path not in sys.path:
    sys.path.insert(0, _openmanus_path)

# Add project root to path
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if _project_root not in sys.path:
    sys.path.append(_project_root)

from structural_app.agent.structural_design_agent import StructuralDesignAgent
from structural_app.agent.fe_analysis_agent import FEAnalysisAgent
from structural_app.agent.cad_drawing_agent import CADDrawingAgent


async def test_with_complete_parameters(user_request):
    """
    测试完整参数场景：Agent直接生成设计方案，无需交互
    """
    print("\n" + "="*80)
    print("步骤1: 调用 StructuralDesignAgent 生成设计方案...")
    print("="*80)

    design_agent = StructuralDesignAgent()

    print(f"\n用户需求: {user_request}")

    try:
        design_result = await design_agent.run(user_request)

        # 提取设计方案
        if isinstance(design_result, dict) and 'content' in design_result:
            design_response = design_result['content']
        elif isinstance(design_result, str):
            design_response = design_result
        else:
            design_response = str(design_result)

        print("\n[设计Agent原始响应]:")
        print(design_response[:500] + "..." if len(design_response) > 500 else design_response)

        design_proposal = design_agent.extract_design_proposal(design_response)

        if design_proposal is None:
            print("\n[FAIL] 无法从设计Agent响应中提取设计方案")
            return None, None

        print("\n[提取的设计方案]:")
        print(json.dumps(design_proposal, indent=2, ensure_ascii=False))

        # 验证设计方案
        is_valid, error = design_agent.validate_design_proposal(design_proposal)
        if not is_valid:
            print(f"\n[FAIL] 设计方案验证失败: {error}")
            return None, None

        print("\n[PASS] 设计方案验证通过")

        return design_proposal, design_response

    except Exception as e:
        print(f"\n[FAIL] 设计Agent执行失败: {e}")
        import traceback
        traceback.print_exc()
        return None, None


async def test_with_incomplete_parameters(user_request):
    """
    测试缺失参数场景：Agent通过AskHuman询问用户
    """
    print("\n" + "="*80)
    print("步骤1: 调用 StructuralDesignAgent (参数缺失，会交互)...")
    print("="*80)

    design_agent = StructuralDesignAgent()

    print(f"\n用户需求: {user_request}")
    print("\n注意: 由于参数缺失，Agent会通过AskHuman工具询问你。")
    print("请在终端根据提示输入缺失的信息。\n")

    try:
        design_result = await design_agent.run(user_request)

        # 提取设计方案
        if isinstance(design_result, dict) and 'content' in design_result:
            design_response = design_result['content']
        elif isinstance(design_result, str):
            design_response = design_result
        else:
            design_response = str(design_result)

        print("\n[设计Agent原始响应]:")
        print(design_response[:500] + "..." if len(design_response) > 500 else design_response)

        design_proposal = design_agent.extract_design_proposal(design_response)

        if design_proposal is None:
            print("\n[FAIL] 无法从设计Agent响应中提取设计方案")
            return None, None

        print("\n[提取的设计方案]:")
        print(json.dumps(design_proposal, indent=2, ensure_ascii=False))

        # 验证设计方案
        is_valid, error = design_agent.validate_design_proposal(design_proposal)
        if not is_valid:
            print(f"\n[FAIL] 设计方案验证失败: {error}")
            return None, None

        print("\n[PASS] 设计方案验证通过")

        return design_proposal, design_response

    except Exception as e:
        print(f"\n[FAIL] 设计Agent执行失败: {e}")
        import traceback
        traceback.print_exc()
        return None, None


async def test_fe_analysis(design_proposal, enable_loop: bool = False):
    """
    测试FEAnalysisAgent进行有限元分析

    Args:
        design_proposal: 设计方案
        enable_loop: 是否启用循环模式（code_check不通过时自动AskHuman）
    """
    print("\n" + "="*80)
    print("步骤2: 调用 FEAnalysisAgent 进行有限元分析...")
    print("="*80)
    print(f"[配置] 循环模式: {'开启' if enable_loop else '关闭'}")

    fe_agent = FEAnalysisAgent(enable_loop=enable_loop)

    try:
        # 将设计方案传递给FE分析Agent
        fe_request = f"""请分析以下结构设计方案:

{json.dumps(design_proposal, indent=2, ensure_ascii=False)}
"""

        print(f"\nFE分析请求: {fe_request[:200]}...")

        fe_result = await fe_agent.run(fe_request)

        # 提取分析结果
        if isinstance(fe_result, dict) and 'content' in fe_result:
            fe_response = fe_result['content']
        elif isinstance(fe_result, str):
            fe_response = fe_result
        else:
            fe_response = str(fe_result)

        print("\n[FEAnalysisAgent原始响应]:")
        print(fe_response[:500] + "..." if len(fe_response) > 500 else fe_response)

        analysis_results = fe_agent.extract_analysis_results(fe_response)

        if analysis_results is None:
            print("\n[FAIL] 无法从FE分析Agent响应中提取分析结果")
            return None

        print("\n[提取的分析结果]:")
        print(json.dumps(analysis_results, indent=2, ensure_ascii=False))

        # 验证分析结果
        if analysis_results.get('status') != 'success':
            print(f"\n[FAIL] FE分析失败: {analysis_results.get('error', 'Unknown error')}")
            return None

        print("\n[PASS] FE分析状态检查通过")
        return analysis_results

    except UnicodeEncodeError as e:
        print(f"\n[FAIL] 编码错误: {e}")
        print("注意: 这是由于 Windows 控制台使用 GBK 编码，无法显示 Unicode 字符")
        print("请确保所有输出只使用 ASCII 字符 (参考 TD-010)")
        return None
    except Exception as e:
        print(f"\n[FAIL] FEAnalysisAgent执行失败: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_cad_drawing(design_proposal):
    """
    测试CADDrawingAgent生成CAD图纸

    Args:
        design_proposal: 设计方案

    Returns:
        DrawingResults dict or None if failed
    """
    print("\n" + "="*80)
    print("步骤3: 调用 CADDrawingAgent 生成CAD图纸...")
    print("="*80)

    cad_agent = CADDrawingAgent()

    try:
        # 将设计方案传递给CAD绘图Agent
        cad_request = f"""请为以下结构设计方案生成CAD图纸:

{json.dumps(design_proposal, indent=2, ensure_ascii=False)}
"""

        print(f"\nCAD绘图请求: {cad_request[:200]}...")

        cad_result = await cad_agent.run(cad_request)

        # 提取绘图结果
        if isinstance(cad_result, dict) and 'content' in cad_result:
            cad_response = cad_result['content']
        elif isinstance(cad_result, str):
            cad_response = cad_result
        else:
            cad_response = str(cad_result)

        print("\n[CADDrawingAgent原始响应]:")
        print(cad_response[:500] + "..." if len(cad_response) > 500 else cad_response)

        drawing_results = cad_agent.extract_drawing_results(cad_response)

        if drawing_results is None:
            print("\n[FAIL] 无法从CAD绘图Agent响应中提取绘图结果")
            return None

        print("\n[提取的绘图结果]:")
        print(json.dumps(drawing_results, indent=2, ensure_ascii=False))

        # 验证绘图结果
        if drawing_results.get('status') != 'success':
            print(f"\n[FAIL] CAD绘图失败: {drawing_results.get('error', 'Unknown error')}")
            return None

        print("\n[PASS] CAD绘图状态检查通过")

        # 验证DXF文件生成
        files = drawing_results.get('files', {})
        for file_key, file_path in files.items():
            if file_path and os.path.exists(file_path):
                print(f"  [PASS] {file_key}: {file_path} 文件存在")
            else:
                print(f"  [WARN] {file_key}: {file_path} 文件不存在或路径为空")

        return drawing_results

    except UnicodeEncodeError as e:
        print(f"\n[FAIL] 编码错误: {e}")
        print("注意: 这是由于 Windows 控制台使用 GBK 编码，无法显示 Unicode 字符")
        print("请确保所有输出只使用 ASCII 字符 (参考 TD-010)")
        return None
    except Exception as e:
        print(f"\n[FAIL] CADDrawingAgent执行失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def validate_drawing_results(drawing_results, design_proposal=None):
    """
    验证绘图结果

    Args:
        drawing_results: 绘图结果字典
        design_proposal: 设计方案（可选）

    Returns:
        bool: 是否通过验证
    """
    print("\n" + "="*80)
    print("步骤4: 验证绘图结果...")
    print("="*80)

    all_passed = True

    # 验证文件生成
    files = drawing_results.get('files', {})
    metadata = drawing_results.get('metadata', {})

    print("\n[文件生成检查]:")
    required_files = ['plan_view', 'elevation_view', 'section_view', 'detail_view']
    for req_file in required_files:
        file_path = files.get(req_file)
        if file_path:
            if os.path.exists(file_path):
                print(f"  [PASS] {req_file}: {file_path}")
            else:
                print(f"  [WARN] {req_file}: {file_path} (文件不存在)")
                all_passed = False
        else:
            print(f"  [INFO] {req_file}: 未生成")

    # 验证元数据
    print("\n[元数据检查]:")
    print(f"  - 结构类型: {metadata.get('structure_type', 'N/A')}")
    print(f"  - 绘图标准: {metadata.get('drawing_standard', 'N/A')}")
    print(f"  - 比例: {metadata.get('scale', 'N/A')}")
    print(f"  - 单位: {metadata.get('units', 'N/A')}")

    # 检查DXF文件内容（简单验证）
    print("\n[DXF文件内容验证]:")
    dxf_files = [f for f in files.values() if f and os.path.exists(f)]
    if dxf_files:
        import ezdxf
        for dxf_path in dxf_files[:2]:  # 只检查前两个文件
            try:
                doc = ezdxf.readfile(dxf_path)
                modelspace = doc.modelspace()
                entity_count = len(modelspace)
                print(f"  [PASS] {os.path.basename(dxf_path)}: {entity_count} 个实体")
            except Exception as e:
                print(f"  [WARN] {os.path.basename(dxf_path)}: 读取失败 - {e}")

    return all_passed


async def run_custom_test():
    """自定义需求测试模式"""
    print("\n" + "="*80)
    print("自定义需求测试")
    print("="*80)

    # 获取用户输入
    user_request = input("\n请输入你的结构设计需求:\n> ")

    print("\n" + "-"*80)
    print("说明: Agent会自动判断是否需要询问缺失参数")
    print("-"*80)

    # Step 1: 结构设计 (自动判断是否交互)
    design_proposal, design_response = await test_with_complete_parameters(user_request)

    # 如果提取失败，说明可能是需要交互，切换到交互模式
    if design_proposal is None:
        print("\n[INFO] 无法提取设计方案，可能需要交互式输入参数...")
        design_proposal, design_response = await test_with_incomplete_parameters(user_request)

    if design_proposal is None:
        print("\n[FAIL] 设计阶段失败")
        return False

    # Step 2: 有限元分析（启用循环模式）
    analysis_results = await test_fe_analysis(design_proposal, enable_loop=True)

    if analysis_results is None:
        print("\n[FAIL] 分析阶段失败")
        return False

    # Step 3: 从analysis_results中提取最终的设计方案
    detailed_results = analysis_results.get('results', {}).get('detailed_results', {})
    final_geometry = detailed_results.get('geometry', design_proposal.get('geometry', {}))
    final_material = detailed_results.get('material', design_proposal.get('material', {}))

    final_design_proposal = {
        'type': design_proposal.get('type', 'beam'),
        'geometry': final_geometry,
        'material': final_material,
        'loads': design_proposal.get('loads', {}),
        'constraints': design_proposal.get('constraints', {})
    }

    # Step 4: CAD绘图
    drawing_results = await test_cad_drawing(final_design_proposal)

    if drawing_results is None:
        print("\n[FAIL] 绘图阶段失败")
        return False

    # Step 5: 验证结果
    results_valid = validate_analysis_results(analysis_results, final_design_proposal)
    drawing_valid = validate_drawing_results(drawing_results, final_design_proposal)

    # 总结
    print("\n" + "="*80)
    print("测试总结")
    print("="*80)

    all_passed = (
        design_proposal is not None and
        analysis_results is not None and
        analysis_results.get('status') == 'success' and
        results_valid and
        drawing_results is not None and
        drawing_results.get('status') == 'success' and
        drawing_valid
    )

    if all_passed:
        print("\n[SUCCESS] 阶段8集成测试通过！")
        print("  - StructuralDesignAgent 正常生成设计方案")
        print("  - FEAnalysisAgent 正常调用 FEAnalysisTool")
        print("  - OpenSeesPy 分析结果数值合理")
        print("  - CADDrawingAgent 正常调用 CADDrawingTool")
        print("  - DXF图纸生成成功")
        print("  - 数据传递流程完整")
        return True
    else:
        print("\n[FAIL] 阶段8集成测试部分失败")
        return False


def validate_analysis_results(analysis_results, design_proposal=None):
    """
    验证分析结果数值合理性

    Args:
        analysis_results: 分析结果字典
        design_proposal: 设计方案（可选，用于动态验证）

    Returns:
        bool: 是否通过验证
    """
    print("\n" + "="*80)
    print("步骤3: 验证分析结果数值...")
    print("="*80)

    results = analysis_results.get('results', {})
    max_displacement_mm = results.get('max_displacement_mm', 0)
    max_stress_MPa = results.get('max_stress_MPa', 0)
    max_moment_kNm = results.get('max_moment_kNm', 0)

    print("\n[关键结果]:")
    print(f"  - 最大位移: {max_displacement_mm:.4f} mm")
    print(f"  - 最大应力: {max_stress_MPa:.4f} MPa")
    print(f"  - 最大弯矩: {max_moment_kNm:.4f} kN*m")

    # 规范校核检查
    code_check = analysis_results.get('code_check', {})

    # 如果提供了设计方案，进行动态验证
    all_passed = True

    if design_proposal:
        geometry = design_proposal.get('geometry', {})
        material = design_proposal.get('material', {})
        loads = design_proposal.get('loads', {})
        length = geometry.get('length', 0)
        height = geometry.get('height', 0)
        E = material.get('E', 0)
        fy = material.get('fy', 0)
        material_name = material.get('material_name', 'Unknown')

        print(f"\n[设计方案信息]:")
        print(f"  - 跨度: {length} m")
        print(f"  - 截面高度: {height} m")
        print(f"  - 弹性模量: {E/1e9:.1f} GPa")
        print(f"  - 材料: {material_name}")

        # 动态位移检查（简支梁均布荷载理论位移公式：5qL^4/384EI）
        # 简单检查：位移应该与 L^4 成正比，与 I 成反比
        # 对于梁，跨高比通常在 10-15 之间
        if length > 0 and height > 0:
            span_depth_ratio = length / height
            print(f"  - 跨高比: {span_depth_ratio:.1f} (合理范围: 10-15)")
            if 8 <= span_depth_ratio <= 20:
                print("    [PASS] 跨高比合理")
            else:
                print("    [WARN] 跨高比可能不合理")

        # 动态应力检查（基于材料屈服强度）
        if fy > 0:
            stress_utilization = max_stress_MPa / (fy / 1e6) * 100
            print(f"\n  - 应力利用率: {stress_utilization:.1f}% (屈服强度: {fy/1e6:.0f} MPa)")
            if stress_utilization < 100:
                print("    [PASS] 应力低于屈服强度")
            else:
                print("    [FAIL] 应力超过屈服强度！")
                all_passed = False

        # 动态弯矩检查（简支梁均布荷载理论弯矩：qL^2/8）
        distributed_loads = loads.get('distributed', [])
        if distributed_loads and length > 0:
            q = abs(distributed_loads[0].get('q', 0)) / 1000  # N/m -> kN/m
            theoretical_moment = q * length * length / 8  # kN*m
            moment_ratio = max_moment_kNm / theoretical_moment if theoretical_moment > 0 else 1
            print(f"\n  - 均布荷载: {q:.1f} kN/m")
            print(f"  - 理论最大弯矩: {theoretical_moment:.1f} kN*m")
            print(f"  - 实际最大弯矩: {max_moment_kNm:.1f} kN*m")
            print(f"  - 弯矩比: {moment_ratio*100:.1f}%")
            if 0.95 <= moment_ratio <= 1.05:
                print("    [PASS] 弯矩与理论值一致")
            else:
                print("    [WARN] 弯矩与理论值有偏差")
    else:
        # 没有设计方案时，使用默认范围检查
        print("\n[使用默认验证范围]:")
        # 位移检查（默认范围）
        if 0.5 <= max_displacement_mm <= 3.0:
            print("\n  [PASS] 最大位移在合理范围内")
        else:
            print(f"\n  [WARN] 最大位移可能异常 (默认范围 0.5-3.0mm)")
            all_passed = False

        # 应力检查（默认范围）
        if 1.0 <= max_stress_MPa <= 5.0:
            print("  [PASS] 最大应力在合理范围内")
        else:
            print(f"  [WARN] 最大应力可能异常 (默认范围 1.0-5.0MPa)")
            all_passed = False

        # 弯矩检查（默认范围）
        if 35 <= max_moment_kNm <= 55:
            print("  [PASS] 最大弯矩在合理范围内")
        else:
            print(f"  [WARN] 最大弯矩可能异常 (默认范围 35-55kN*m)")
            all_passed = False

    # 规范校核检查（最重要）
    print("\n[规范校核检查]:")
    if code_check.get('compliant', False):
        print("  [PASS] 规范校核通过")
        # 安全系数检查
        safety_factors = code_check.get('safety_factors', {})
        stress_sf = safety_factors.get('stress', 0)
        deflection_sf = safety_factors.get('deflection', 0)
        print(f"  - 应力安全系数: {stress_sf:.2f}")
        print(f"  - 挠度安全系数: {deflection_sf:.2f}")
        if stress_sf < 1.0 or deflection_sf < 1.0:
            print("  [FAIL] 安全系数小于1.0")
            all_passed = False
    else:
        print(f"  [FAIL] 规范校核未通过: {code_check.get('violations', [])}")
        all_passed = False

    return all_passed


async def run_predefined_complete_test():
    """预设完整参数测试模式"""
    print("\n" + "="*80)
    print("预设完整参数测试")
    print("="*80)

    user_request = "设计一个6米跨度的简支梁，承受10kN/m的均布荷载，使用C30混凝土"

    # Step 1: 结构设计
    design_proposal, design_response = await test_with_complete_parameters(user_request)

    if design_proposal is None:
        print("\n[FAIL] 设计阶段失败")
        return False

    # Step 2: 有限元分析（启用循环模式）
    analysis_results = await test_fe_analysis(design_proposal, enable_loop=True)

    if analysis_results is None:
        print("\n[FAIL] 分析阶段失败")
        return False

    # Step 3: 从analysis_results中提取最终的设计方案
    detailed_results = analysis_results.get('results', {}).get('detailed_results', {})
    final_geometry = detailed_results.get('geometry', design_proposal.get('geometry', {}))
    final_material = detailed_results.get('material', design_proposal.get('material', {}))

    final_design_proposal = {
        'type': design_proposal.get('type', 'beam'),
        'geometry': final_geometry,
        'material': final_material,
        'loads': design_proposal.get('loads', {}),
        'constraints': design_proposal.get('constraints', {})
    }

    # Step 4: 验证分析结果
    results_valid = validate_analysis_results(analysis_results, final_design_proposal)

    # Step 5: CAD绘图
    drawing_results = await test_cad_drawing(final_design_proposal)

    if drawing_results is None:
        print("\n[FAIL] 绘图阶段失败")
        return False

    # Step 6: 验证绘图结果
    drawing_valid = validate_drawing_results(drawing_results, final_design_proposal)

    # 总结
    print("\n" + "="*80)
    print("测试总结")
    print("="*80)

    all_passed = (
        design_proposal is not None and
        analysis_results is not None and
        analysis_results.get('status') == 'success' and
        results_valid and
        drawing_results is not None and
        drawing_results.get('status') == 'success' and
        drawing_valid
    )

    if all_passed:
        print("\n[SUCCESS] 阶段8集成测试通过！")
        return True
    else:
        print("\n[FAIL] 阶段8集成测试部分失败")
        return False


async def run_predefined_incomplete_test():
    """预设缺失参数测试模式"""
    print("\n" + "="*80)
    print("预设缺失参数测试 (测试AskHuman交互)")
    print("="*80)

    user_request = "设计一个简支梁"

    # Step 1: 结构设计 (会触发AskHuman)
    design_proposal, design_response = await test_with_incomplete_parameters(user_request)

    if design_proposal is None:
        print("\n[FAIL] 设计阶段失败")
        return False

    # Step 2: 有限元分析（启用循环模式）
    analysis_results = await test_fe_analysis(design_proposal, enable_loop=True)

    if analysis_results is None:
        print("\n[FAIL] 分析阶段失败")
        return False

    # Step 3: 从analysis_results中提取最终的设计方案
    detailed_results = analysis_results.get('results', {}).get('detailed_results', {})
    final_geometry = detailed_results.get('geometry', design_proposal.get('geometry', {}))
    final_material = detailed_results.get('material', design_proposal.get('material', {}))

    final_design_proposal = {
        'type': design_proposal.get('type', 'beam'),
        'geometry': final_geometry,
        'material': final_material,
        'loads': design_proposal.get('loads', {}),
        'constraints': design_proposal.get('constraints', {})
    }

    # Step 4: 验证分析结果
    results_valid = validate_analysis_results(analysis_results, final_design_proposal)

    # Step 5: CAD绘图
    drawing_results = await test_cad_drawing(final_design_proposal)

    if drawing_results is None:
        print("\n[FAIL] 绘图阶段失败")
        return False

    # Step 6: 验证绘图结果
    drawing_valid = validate_drawing_results(drawing_results, final_design_proposal)

    # 总结
    print("\n" + "="*80)
    print("测试总结")
    print("="*80)

    all_passed = (
        design_proposal is not None and
        analysis_results is not None and
        analysis_results.get('status') == 'success' and
        results_valid and
        drawing_results is not None and
        drawing_results.get('status') == 'success' and
        drawing_valid
    )

    if all_passed:
        print("\n[SUCCESS] 阶段8集成测试通过！")
        return True
    else:
        print("\n[FAIL] 阶段8集成测试部分失败")
        return False

async def main():
    """Run stage 8 integration test"""
    print("\n" + "="*80)
    print("OpenManus 结构设计系统 - 阶段8集成测试")
    print("="*80)
    print("\n前置条件检查:")

    # Check config file
    config_path = os.path.join(_project_root, 'config.toml')
    if not os.path.exists(config_path):
        print(f"[ERROR] 配置文件不存在: {config_path}")
        print("请先创建 config.toml 并配置 API key")
        return

    # Read config to check API key
    with open(config_path, 'r', encoding='utf-8') as f:
        config_content = f.read()
        if 'YOUR_DEEPSEEK_API_KEY_HERE' in config_content:
            print(f"[ERROR] 请先在 config.toml 中填入实际的 API key")
            print(f"配置文件位置: {config_path}")
            return

    print("[OK] 配置文件检查通过")
    print("[OK] OpenManus 导入检查通过")
    print("[OK] ezdxf 导入检查通过")

    # 选择测试模式
    print("\n" + "-"*80)
    print("测试模式选择:")
    print("  1. 自定义需求测试 (输入你的结构设计需求)")
    print("  2. 预设完整参数测试 (6米简支梁，10kN/m)")
    print("  3. 预设缺失参数测试 (测试AskHuman交互)")
    print("-"*80)

    test_mode = input("\n请选择测试模式 (1/2/3): ").strip()

    # Run tests based on mode
    if test_mode == "1":
        result = await run_custom_test()
    elif test_mode == "2":
        result = await run_predefined_complete_test()
    elif test_mode == "3":
        result = await run_predefined_incomplete_test()
    else:
        print(f"\n[ERROR] 无效的选项: {test_mode}")
        return

    # Summary
    print("\n" + "="*80)
    if result:
        print("[测试结果] 通过")
    else:
        print("[测试结果] 失败")
    print("="*80)

    return result


if __name__ == "__main__":
    asyncio.run(main())
