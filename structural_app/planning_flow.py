"""
PlanningFlow - Main Orchestration Class for OpenManus Structural Design System

This module orchestrates the multi-agent workflow for structural design:
1. StructuralDesignAgent - Collects parameters and creates design proposal
2. FEAnalysisAgent - Performs finite element analysis
3. EvaluationAgent - Evaluates design quality (在绘图之前)
4. CADDrawingAgent - Generates CAD drawings
5. ReportGenerationAgent - Generates comprehensive reports
"""

from typing import Dict, Any, Optional, List
import json
import os
from pathlib import Path
import toml

# Import agents directly to avoid agent module __init__ issues
# This avoids the hard-coded path issue in structural_design_agent.py
try:
    from structural_app.agent.structural_design_agent import StructuralDesignAgent
except (FileNotFoundError, ModuleNotFoundError):
    StructuralDesignAgent = None

try:
    from structural_app.agent.fe_analysis_agent import FEAnalysisAgent
except (FileNotFoundError, ModuleNotFoundError):
    FEAnalysisAgent = None

# Import AnalyzerFactory for structure type pre-check
try:
    from structural_app.tool.fe_analysis_tool import AnalyzerFactory
except (FileNotFoundError, ModuleNotFoundError, ImportError):
    AnalyzerFactory = None

try:
    from structural_app.agent.cad_drawing_agent import CADDrawingAgent
except (FileNotFoundError, ModuleNotFoundError):
    CADDrawingAgent = None

try:
    from structural_app.agent.evaluation_agent import EvaluationAgent
except (FileNotFoundError, ModuleNotFoundError):
    EvaluationAgent = None

try:
    from structural_app.agent.report_generation_agent import ReportGenerationAgent
except (FileNotFoundError, ModuleNotFoundError):
    ReportGenerationAgent = None


class PlanningFlow:
    """
    Main orchestrator for structural design workflow.

    Manages the flow of information between agents and ensures
    each step completes successfully before proceeding to the next.

    Workflow:
    DesignProposal → FEAnalysis → Evaluation → Drawing → Report
    """

    def __init__(
        self,
        design_agent: Optional[StructuralDesignAgent] = None,
        analysis_agent: Optional[FEAnalysisAgent] = None,
        drawing_agent: Optional[CADDrawingAgent] = None,
        evaluation_agent: Optional[EvaluationAgent] = None,
        report_agent: Optional[ReportGenerationAgent] = None,
        output_dir: str = "output",
    ):
        """
        Initialize PlanningFlow with agents.

        Args:
            design_agent: StructuralDesignAgent instance
            analysis_agent: FEAnalysisAgent instance
            drawing_agent: CADDrawingAgent instance
            evaluation_agent: EvaluationAgent instance
            report_agent: ReportGenerationAgent instance
            output_dir: Base directory for output files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Create agents if not provided (handle None imports gracefully)
        self.design_agent = design_agent if design_agent is not None else (StructuralDesignAgent() if StructuralDesignAgent else None)
        self.analysis_agent = analysis_agent if analysis_agent is not None else (FEAnalysisAgent() if FEAnalysisAgent else None)
        self.drawing_agent = drawing_agent if drawing_agent is not None else (CADDrawingAgent() if CADDrawingAgent else None)
        self.evaluation_agent = evaluation_agent if evaluation_agent is not None else (EvaluationAgent() if EvaluationAgent else None)
        self.report_agent = report_agent if report_agent is not None else (ReportGenerationAgent() if ReportGenerationAgent else None)

        # Store results from each step
        self.results = {
            "design_proposal": None,
            "analysis_results": None,
            "drawing_results": None,
            "evaluation_report": None,
            "report_results": None,
        }

        # Load API configuration for LLM calls
        self.api_key, self.api_provider, self.api_base_url, self.api_model = self._load_api_config()

        # Test run timestamp for organizing output files
        self.test_timestamp = None

        # Evaluation alert: skip drawing flag and alert thresholds
        self.skip_drawing = False
        try:
            from structural_app.tool.evaluators.evaluator_config import ALERT_THRESHOLDS
            self.alert_config = ALERT_THRESHOLDS
        except ImportError:
            self.alert_config = {"default": {"safety_severe": 60, "safety_warning": 70, "economy_severe": 60, "economy_warning": 70}}

    def _load_api_config(self) -> tuple:
        """
        Load API configuration from project config.toml.

        Returns:
            Tuple of (api_key, provider, base_url, model)
        """
        # Read project config.toml (relative to this file's location)
        current_dir = Path(__file__).resolve().parent
        config_path = current_dir.parent / "config.toml"

        if config_path.exists():
            try:
                config = toml.load(config_path)
                llm_config = config.get('llm', {})
                api_key = llm_config.get('api_key', '')
                provider = llm_config.get('provider', 'deepseek')
                base_url = llm_config.get('base_url', '')
                model = llm_config.get('model', 'deepseek-chat')

                if api_key and api_key != 'your-api-key-here':
                    return api_key, provider, base_url, model
            except Exception as e:
                print(f"[WARNING] Failed to load {config_path}: {e}")

        # Fallback to environment variables
        api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY")
        provider = "anthropic" if os.getenv("ANTHROPIC_API_KEY") else "openai"
        base_url = ""
        model = "claude-sonnet-4-6" if provider == "anthropic" else "gpt-4"

        return api_key, provider, base_url, model

    def _get_allowed_params(self, design: dict) -> str:
        """
        根据结构类型生成允许修改的参数列表（含当前值），用于prompt约束。

        Args:
            design: 当前设计提案字典

        Returns:
            格式化字符串，每行一个参数
        """
        stype = design.get('type')
        geom = design.get('geometry', {})
        mat = design.get('material', {})
        cons = design.get('constraints', {})
        bound = design.get('boundary', {})

        if stype in ['beam', 'cantilever_beam', 'continuous_beam']:
            lines = [
                f"- geometry.width（梁宽，当前 {geom.get('width', '?')} m）",
                f"- geometry.height（梁高，当前 {geom.get('height', '?')} m）",
            ]
            if 'fy' in mat and mat['fy'] is not None:
                fy_mpa = mat['fy'] / 1e6 if mat['fy'] > 1000 else mat['fy']
                lines.append(f"- material.fy（屈服强度，当前 {fy_mpa:.1f} MPa，典型范围 200~500 MPa）")
            if 'E' in mat and mat['E'] is not None:
                e_gpa = mat['E'] / 1e9 if mat['E'] > 1000 else mat['E']
                lines.append(f"- material.E（弹性模量，当前 {e_gpa:.1f} GPa，混凝土约30GPa，钢约200GPa）")
            if 'material_name' in mat:
                lines.append(f"- material.material_name（材料名称，当前 '{mat['material_name']}'，常见：C30/C40/C50/Q235/Q345）")
                lines.append("  **注意**：修改材料时，fy和E应同步调整（C30: fy=20.1 E=30, C40: fy=26.8 E=32.5, Q235: fy=235 E=200）")
            if stype == 'continuous_beam' and 'n_spans' in geom:
                lines.append(f"- geometry.n_spans（跨数，当前 {geom['n_spans']}，范围2~5）")
            return "\n".join(lines)

        elif stype == 'frame':
            cols = geom.get('columns', {})
            beams = geom.get('beams', {})
            lines = [
                f"- geometry.columns.width（柱宽，当前 {cols.get('width', '?')} m）",
                f"- geometry.columns.depth（柱深，当前 {cols.get('depth', '?')} m）",
                f"- geometry.beams.width（梁宽，当前 {beams.get('width', '?')} m）",
                f"- geometry.beams.depth（梁深，当前 {beams.get('depth', '?')} m）",
            ]
            if 'fy' in mat and mat['fy'] is not None:
                fy_mpa = mat['fy'] / 1e6 if mat['fy'] > 1000 else mat['fy']
                lines.append(f"- material.fy（屈服强度，当前 {fy_mpa:.1f} MPa）")
            if 'E' in mat and mat['E'] is not None:
                e_gpa = mat['E'] / 1e9 if mat['E'] > 1000 else mat['E']
                lines.append(f"- material.E（弹性模量，当前 {e_gpa:.1f} GPa）")
            if 'material_name' in mat:
                lines.append(f"- material.material_name（材料名称，当前 '{mat['material_name']}'）")
            if 'column_base' in bound:
                lines.append(f"- boundary.column_base（柱底约束，当前 '{bound['column_base']}'，可选 fixed/pinned）")
            return "\n".join(lines)

        elif stype == 'truss':
            lines = [
                f"- geometry.span（跨度，当前 {geom.get('span', '?')} m）",
                f"- geometry.height（高度，当前 {geom.get('height', '?')} m）",
                f"- geometry.n_panels（节间数，当前 {geom.get('n_panels', 5)}）",
                f"- material.A（杆件截面积，当前 {mat.get('A', '?')} m²）",
            ]
            if 'fy' in mat and mat['fy'] is not None:
                fy_mpa = mat['fy'] / 1e6 if mat['fy'] > 1000 else mat['fy']
                lines.append(f"- material.fy（屈服强度，当前 {fy_mpa:.1f} MPa）")
            if 'E' in mat and mat['E'] is not None:
                e_gpa = mat['E'] / 1e9 if mat['E'] > 1000 else mat['E']
                lines.append(f"- material.E（弹性模量，当前 {e_gpa:.1f} GPa）")
            if 'material_name' in mat:
                lines.append(f"- material.material_name（材料名称，当前 '{mat['material_name']}'）")
            if 'support_type' in cons:
                lines.append(f"- constraints.support_type（支撑类型，当前 '{cons['support_type']}'，可选 simply_supported/both_pinned）")
            return "\n".join(lines)

        else:
            return "（当前结构类型无可调参数）"

    def _validate_design_params(self, design: dict) -> tuple:
        """
        验证设计参数的合理性

        Args:
            design: 设计参数字典

        Returns:
            (is_valid, error_message)
        """
        geom = design.get('geometry', {})
        mat = design.get('material', {})
        stype = design.get('type', '')

        # 几何参数检查
        if 'width' in geom:
            if geom['width'] <= 0 or geom['width'] > 2.0:
                return False, f"梁宽不合理: {geom['width']} m（应在0~2.0m之间）"

        if 'height' in geom:
            if geom['height'] <= 0 or geom['height'] > 3.0:
                return False, f"梁高不合理: {geom['height']} m（应在0~3.0m之间）"

        if 'span' in geom:
            if geom['span'] <= 0 or geom['span'] > 100.0:
                return False, f"跨度不合理: {geom['span']} m（应在0~100m之间）"

        # 框架特殊检查
        if stype == 'frame':
            cols = geom.get('columns', {})
            beams = geom.get('beams', {})
            if 'width' in cols and (cols['width'] <= 0 or cols['width'] > 2.0):
                return False, f"柱宽不合理: {cols['width']} m"
            if 'depth' in cols and (cols['depth'] <= 0 or cols['depth'] > 2.0):
                return False, f"柱深不合理: {cols['depth']} m"
            if 'width' in beams and (beams['width'] <= 0 or beams['width'] > 2.0):
                return False, f"梁宽不合理: {beams['width']} m"
            if 'depth' in beams and (beams['depth'] <= 0 or beams['depth'] > 3.0):
                return False, f"梁深不合理: {beams['depth']} m"

        # 材料参数检查
        if 'fy' in mat and mat['fy'] is not None:
            fy_mpa = mat['fy'] / 1e6 if mat['fy'] > 1000 else mat['fy']
            if fy_mpa < 10 or fy_mpa > 1000:
                return False, f"屈服强度不合理: {fy_mpa} MPa（应在10~1000 MPa之间）"
            # 自动单位转换
            if mat['fy'] < 1000:
                mat['fy'] = mat['fy'] * 1e6

        if 'E' in mat and mat['E'] is not None:
            e_gpa = mat['E'] / 1e9 if mat['E'] > 1000 else mat['E']
            if e_gpa < 10 or e_gpa > 500:
                return False, f"弹性模量不合理: {e_gpa} GPa（应在10~500 GPa之间）"
            # 自动单位转换
            if mat['E'] < 1000:
                mat['E'] = mat['E'] * 1e9

        # 桁架特殊检查
        if stype == 'truss' and 'A' in mat:
            if mat['A'] <= 0 or mat['A'] > 0.1:
                return False, f"杆件截面积不合理: {mat['A']} m²（应在0~0.1m²之间）"

        return True, ""

    def _extract_json_from_text(self, text: str) -> dict:
        """
        从文本中提取JSON，支持对象和数组，支持多种格式
        """
        import re

        # 1. 尝试提取代码块中的JSON
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1).strip()
            json_str = re.sub(r'//.*?\n', '\n', json_str)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass

        # 2. 尝试查找JSON数组
        json_match = re.search(r'(\[[\s\S]*\])', text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
            json_str = re.sub(r'//.*?\n', '\n', json_str)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass

        # 3. 尝试查找JSON对象
        json_match = re.search(r'(\{[\s\S]*\})', text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
            json_str = re.sub(r'//.*?\n', '\n', json_str)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass

        return None

    async def run_full_design(
        self,
        request: str,
        verbose: bool = True,
    ) -> Dict[str, Any]:
        """
        Run the complete structural design workflow.

        Args:
            request: User's design request
            verbose: Whether to print progress

        Returns:
            Dictionary containing all results
        """
        if verbose:
            print("=" * 60)
            print("OpenManus Structural Design System - PlanningFlow")
            print("=" * 60)
            print()

        # Generate timestamp for output directory (at the start of test run)
        from datetime import datetime
        self.test_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Step 1: Design Proposal
        if verbose:
            print("Step 1: Generating design proposal...")
            print("-" * 40)

        design_result = await self.design_agent.run(request)
        self.results["design_proposal"] = self._extract_design_proposal(design_result)

        if verbose and self.results["design_proposal"]:
            print(f"[OK] Design proposal created: {self.results['design_proposal'].get('type')}")

        # Create output directory with structure type name
        structure_type = self.results["design_proposal"].get("type", "unknown") if self.results["design_proposal"] else "unknown"
        self.main_output_dir = self.output_dir / f"{structure_type}_{self.test_timestamp}"
        self.main_output_dir.mkdir(parents=True, exist_ok=True)

        if verbose:
            print(f"[PlanningFlow] Output directory: {self.main_output_dir}")
            print()

        # Step 1.5: Pre-check - Verify structure type is supported
        if self.results["design_proposal"]:
            structure_type = self.results["design_proposal"].get('type')
            if structure_type and not AnalyzerFactory.is_registered(structure_type):
                available_types = AnalyzerFactory.get_available_types()
                if verbose:
                    print()
                    print("=" * 60)
                    print("[ERROR] 不支持的结构类型")
                    print("=" * 60)
                    print(f"当前设计类型: '{structure_type}'")
                    print(f"支持的类型: {available_types}")
                    print()
                    print("请使用已支持的结构类型，或参考 docs/how_to_add_new_structure_type.md")
                    print("添加新结构类型的支持。")
                    print("=" * 60)
                return {
                    "status": "failed",
                    "error": f"当前未支持的结构类型: '{structure_type}'。可用类型: {available_types}",
                    "design_proposal": self.results["design_proposal"]
                }

        # Step 2: FE Analysis
        if verbose:
            print()
            print("Step 2: Performing finite element analysis...")
            print("-" * 40)

        analysis_request = self._build_analysis_request(self.results["design_proposal"])
        analysis_result = await self.analysis_agent.run(analysis_request)
        self.results["analysis_results"] = self._extract_analysis_results(analysis_result)

        if verbose and self.results["analysis_results"]:
            status = self.results['analysis_results'].get('status', 'unknown')
            print(f"[OK] FE analysis completed: {status}")

        # Check if analysis failed (e.g., unsupported structure type)
        if self.results["analysis_results"]:
            status = self.results['analysis_results'].get('status')
            if status == 'error':
                error_msg = self.results['analysis_results'].get('error', 'Unknown error')
                if verbose:
                    print()
                    print("=" * 60)
                    print("[ERROR] 有限元分析失败")
                    print("=" * 60)
                    print(f"错误信息: {error_msg}")
                    print("=" * 60)
                # Return early with error
                return {
                    "status": "failed",
                    "error": error_msg,
                    "design_proposal": self.results["design_proposal"]
                }

        # Set up output directories for drawings, visualizations, and reports
        # Each test run gets its own timestamped directory
        drawings_dir = self.main_output_dir / "drawings"
        visualizations_dir = self.main_output_dir / "visualizations"
        reports_dir = self.main_output_dir / "reports"

        # Configure drawing agent output directory
        if hasattr(self.drawing_agent, 'available_tools'):
            for tool in self.drawing_agent.available_tools:
                if hasattr(tool, 'set_output_directory'):
                    tool.set_output_directory(str(drawings_dir), None)
                    if verbose:
                        print(f"[PlanningFlow] Set drawing tool output to: {drawings_dir}")

        # Configure evaluation agent output directory (for visualizations)
        if hasattr(self.evaluation_agent, 'available_tools'):
            for tool in self.evaluation_agent.available_tools:
                if hasattr(tool, 'set_output_directory'):
                    tool.set_output_directory(str(visualizations_dir), None)
                    if verbose:
                        print(f"[PlanningFlow] Set evaluation tool output to: {visualizations_dir}")

        # Configure report agent output directories
        # Note: ReportGenerationAgent has both ReportTool and VisualizationTool
        # We need to set different output directories for each
        if hasattr(self.report_agent, 'available_tools'):
            for tool in self.report_agent.available_tools:
                if hasattr(tool, 'set_output_directory'):
                    # Check tool type by name
                    tool_name = getattr(tool, 'name', '')
                    if tool_name == 'visualization':
                        # VisualizationTool should output to visualizations_dir
                        tool.set_output_directory(str(visualizations_dir), None)
                        if verbose:
                            print(f"[PlanningFlow] Set report agent's visualization tool output to: {visualizations_dir}")
                    elif tool_name == 'report':
                        # ReportTool should output to reports_dir
                        tool.set_output_directory(str(reports_dir), None)
                        if verbose:
                            print(f"[PlanningFlow] Set report agent's report tool output to: {reports_dir}")
                    else:
                        # Default: use reports_dir for unknown tools
                        tool.set_output_directory(str(reports_dir), None)
                        if verbose:
                            print(f"[PlanningFlow] Set report agent's {tool_name} tool output to: {reports_dir}")

        # Also configure analysis agent's visualization tool if it exists
        if hasattr(self.analysis_agent, 'available_tools'):
            for tool in self.analysis_agent.available_tools:
                if hasattr(tool, 'set_output_directory'):
                    tool.set_output_directory(str(visualizations_dir), None)
                    if verbose:
                        print(f"[PlanningFlow] Set analysis tool output to: {visualizations_dir}")

        # Handle code check failure (only if not compliant)
        if self.results["analysis_results"]:
            code_check = self.results["analysis_results"].get('code_check', {})
            if not code_check.get('compliant', True):
                # Code check failed - ask user for action
                user_choice = self._ask_code_check_failure_action(code_check, verbose)

                if user_choice == "manual":
                    # Option 1: Manual improvement loop with LLM suggestions
                    if verbose:
                        print()
                        print("[PlanningFlow] 启动手动改进模式...")

                    improved_results, updated_design_proposal = await self._manual_improvement_loop(
                        self.results["design_proposal"],
                        self.results["analysis_results"],
                        verbose
                    )
                    self.results["analysis_results"] = improved_results
                    self.results["design_proposal"] = updated_design_proposal

                    # Check final status
                    final_code_check = improved_results.get('code_check', {})
                    if not final_code_check.get('compliant', False):
                        if verbose:
                            print()
                            print("[WARNING] 手动改进结束，但设计仍未满足规范要求")
                            print("[PlanningFlow] 继续执行后续步骤...")

                elif user_choice == "auto":
                    # Option 2: 自动迭代优化（模仿manual模式，但无需用户交互）
                    if verbose:
                        print()
                        print("[PlanningFlow] 启动自动迭代优化模式...")

                    improved_results, updated_design_proposal = await self._auto_improvement_loop(
                        self.results["design_proposal"],
                        self.results["analysis_results"],
                        verbose
                    )
                    self.results["analysis_results"] = improved_results
                    self.results["design_proposal"] = updated_design_proposal

                    # 检查最终状态
                    final_code_check = improved_results.get('code_check', {})
                    if not final_code_check.get('compliant', False):
                        if verbose:
                            print()
                            print("[WARNING] 自动优化结束，但设计仍未满足规范要求")
                            print("[PlanningFlow] 继续执行后续步骤...")

                elif user_choice == "terminate":
                    # Option 3: Terminate workflow
                    if verbose:
                        print()
                        print("[PlanningFlow] 用户选择终止工作流")
                    return {"status": "terminated", "reason": "user_terminated"}

        # Step 3: Evaluation (在绘图之前先评估)
        if verbose:
            print()
            print("Step 3: Evaluating design quality...")
            print("-" * 40)

        evaluation_request = self._build_evaluation_request(
            self.results["design_proposal"],
            self.results["analysis_results"]
        )
        evaluation_result = await self.evaluation_agent.run(evaluation_request)
        self.results["evaluation_report"] = self._extract_evaluation_report(evaluation_result)

        if verbose and self.results["evaluation_report"]:
            status = self.results['evaluation_report'].get('status', 'unknown')
            grade = self.results['evaluation_report'].get('grade', 'N/A')
            score = self.results['evaluation_report'].get('comprehensive_score', 0)
            print(f"[OK] Evaluation completed: {status}, Grade: {grade}, Score: {score}")

        # Step 3.5: Evaluation Alert（预警与优化决策）
        self.skip_drawing = False
        if self.results["evaluation_report"]:
            action = self._handle_evaluation_alert(self.results["evaluation_report"])

            if action == "terminate":
                if verbose:
                    print("\n[PlanningFlow] 用户选择终止工作流")
                return {"status": "terminated", "reason": "user_terminated_after_evaluation"}

            elif action == "optimize":
                if verbose:
                    print("\n[PlanningFlow] 进入多方案优化...")
                opt_design, opt_analysis, opt_evaluation = await self._parallel_optimization(
                    self.results["design_proposal"],
                    self.results["analysis_results"],
                    self.results["evaluation_report"],
                    verbose,
                )
                self.results["design_proposal"] = opt_design
                self.results["analysis_results"] = opt_analysis
                self.results["evaluation_report"] = opt_evaluation
                self.skip_drawing = False

            elif action == "report_only":
                self.skip_drawing = True
                if verbose:
                    print("\n[PlanningFlow] 跳过绘图，直接生成报告")

            # "continue": skip_drawing 保持 False，直接往下走

        # Step 4: CAD Drawing
        if not self.skip_drawing:
            if verbose:
                print()
                print("Step 4: Generating CAD drawings...")
                print("-" * 40)

            drawing_request = self._build_drawing_request(
                self.results["design_proposal"],
                self.results["analysis_results"]
            )
            drawing_result = await self.drawing_agent.run(drawing_request)
            self.results["drawing_results"] = self._extract_drawing_results(drawing_result)

            if verbose:
                if self.results["drawing_results"]:
                    status = self.results['drawing_results'].get('status', 'unknown')
                    print(f"[OK] CAD drawings generated: {status}")
                else:
                    print(f"[WARNING] Failed to extract drawing results from response")
                    print(f"[DEBUG] Drawing agent response (first 500 chars): {str(drawing_result)[:500]}")
        else:
            if verbose:
                print()
                print("Step 4: 跳过绘图（report_only 模式）")
            self.results["drawing_results"] = {"status": "skipped", "files": {}}

        # Step 5: Report Generation
        if verbose:
            print()
            print("Step 5: Generating comprehensive report...")
            print("-" * 40)

        report_request = self._build_report_request(
            self.results["design_proposal"],
            self.results["analysis_results"],
            self.results["evaluation_report"],
            self.results["drawing_results"]
        )
        report_result = await self.report_agent.run(report_request)
        self.results["report_results"] = self._extract_report_results(report_result)

        if verbose and self.results["report_results"]:
            status = self.results['report_results'].get('status', 'unknown')
            print(f"[OK] Report generated: {status}")

        if verbose:
            print()
            print("=" * 60)
            print("Workflow completed!")
            print("=" * 60)

        # Add main_output_dir to results for test result saving
        self.results["main_output_dir"] = str(self.main_output_dir)

        return self.results

    def _find_balanced_json_with_status(self, response: str) -> Optional[str]:
        """
        Find balanced JSON object containing status field

        Args:
            response: LLM response text

        Returns:
            Balanced JSON string, or None if not found
        """
        i = 0
        while i < len(response):
            if response[i] == '{':
                # Found opening brace, find matching closing brace
                brace_count = 0
                start = i
                for j in range(i, len(response)):
                    if response[j] == '{':
                        brace_count += 1
                    elif response[j] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            json_str = response[start:j+1]
                            if '"status"' in json_str:
                                return json_str
                            break
                i = j + 1
            else:
                i += 1
        return None

    def _extract_design_proposal(self, response: str) -> Optional[Dict[str, Any]]:
        """Extract design proposal from response."""
        try:
            import re
            import json

            # Pattern 1: Extract from create_chat_completion tool output (preferred)
            # Match the JSON object after "create_chat_completion ... executed:"
            pattern = r'create_chat_completion.*?executed:\s*(\{[\s\S]*?\n\})\s*(?:Step|\Z)'
            matches = re.findall(pattern, response, re.DOTALL)

            if matches:
                # Get the last match (most recent execution)
                json_str = matches[-1]
                return json.loads(json_str)

            # Pattern 2: Find balanced JSON containing "type" field
            json_match = re.search(r'\{[\s\S]*?"type":[\s\S]*?\n\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())

            # Pattern 3: Fallback - find any balanced JSON with type field
            balanced_json = self._find_balanced_json_with_status_for_type(response)
            if balanced_json:
                return json.loads(balanced_json)

            return None
        except Exception:
            return None

    def _find_balanced_json_with_status_for_type(self, response: str) -> Optional[str]:
        """
        Find balanced JSON object containing type field (for design proposal)

        Args:
            response: LLM response text

        Returns:
            Balanced JSON string, or None if not found
        """
        i = 0
        while i < len(response):
            if response[i] == '{':
                brace_count = 0
                start = i
                for j in range(i, len(response)):
                    if response[j] == '{':
                        brace_count += 1
                    elif response[j] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            json_str = response[start:j+1]
                            if '"type"' in json_str:
                                return json_str
                            break
                i = j + 1
            else:
                i += 1
        return None

    def _build_analysis_request(self, design_proposal: Optional[Dict]) -> str:
        """Build request for FE analysis agent."""
        if not design_proposal:
            return "No design proposal available for analysis."
        return json.dumps(design_proposal, ensure_ascii=False)

    def _handle_evaluation_alert(self, evaluation_report: Dict) -> str:
        """
        根据评估报告生成差异化预警，询问用户后续操作。
        返回: "continue", "optimize", "report_only", "terminate"
        无预警时直接返回 "continue"（不打印任何内容）。
        """
        design_proposal = self.results.get("design_proposal", {})
        structure_type = design_proposal.get("type", "default")
        thresholds = self.alert_config.get(structure_type, self.alert_config.get("default", {}))

        score = evaluation_report.get("comprehensive_score", 0)
        dimensions = evaluation_report.get("dimensions", {})

        alerts = []
        safety_score = dimensions.get("safety", {}).get("score", 100)
        if safety_score < thresholds.get("safety_severe", 60):
            alerts.append(("严重", "安全性", "安全性得分过低，存在安全风险，建议立即修改"))
        elif safety_score < thresholds.get("safety_warning", 70):
            alerts.append(("警告", "安全性", "安全性裕度较小，可考虑适当增大截面或提高材料强度"))

        economy_score = dimensions.get("economy", {}).get("score", 100)
        if economy_score < thresholds.get("economy_severe", 60):
            alerts.append(("严重", "经济性", "经济性得分过低，材料浪费严重，建议优化截面尺寸"))
        elif economy_score < thresholds.get("economy_warning", 70):
            alerts.append(("警告", "经济性", "经济性一般，可尝试减小截面或优化配筋"))

        if score < 70:
            alerts.append(("不合格", "综合", f"综合得分 {score:.1f} 低于合格线70分，建议参考以上预警进行修改"))

        if not alerts:
            return "continue"

        print("\n" + "=" * 60)
        print("设计评估预警")
        print("=" * 60)
        for level, dim, msg in alerts:
            print(f"[{level}] {dim}：{msg}")
        print("=" * 60)
        print("请选择后续操作：")
        print("  1 - continue   : 继续生成图纸和完整报告")
        print("  2 - optimize   : 尝试自动优化（推荐）")
        print("  3 - report_only: 仅生成报告（跳过绘图）")
        print("  4 - terminate  : 终止工作流")
        print("=" * 60)

        while True:
            try:
                choice = input("请输入选项 (1/2/3/4): ").strip().lower()
                mapping = {
                    "1": "continue", "continue": "continue",
                    "2": "optimize", "optimize": "optimize",
                    "3": "report_only", "report_only": "report_only",
                    "4": "terminate", "terminate": "terminate",
                }
                if choice in mapping:
                    return mapping[choice]
                print("无效选项，请重新输入")
            except (EOFError, KeyboardInterrupt):
                print("\n用户中断，默认选择 continue")
                return "continue"

    async def _parallel_optimization(
        self,
        original_design: Dict,
        original_analysis: Dict,
        original_evaluation: Dict,
        verbose: bool = True,
    ) -> tuple:
        """
        顺序多方案优化：生成3个候选方案，依次分析评估，取最优方案。
        使用顺序执行（非 asyncio.gather）避免 agent 内部 memory 并发写入问题。
        返回 (best_design, best_analysis, best_evaluation)
        """
        candidate_designs = await self._generate_candidate_descriptions(
            original_design, original_analysis, original_evaluation
        )
        if not candidate_designs:
            if verbose:
                print("[WARNING] 无法生成候选方案，保留原设计")
            return original_design, original_analysis, original_evaluation

        candidates = []
        for i, new_design in enumerate(candidate_designs):
            if verbose:
                print(f"\n[优化] 正在评估候选方案 {i+1}/{len(candidate_designs)}...")
            if new_design == original_design:
                if verbose:
                    print(f"[优化] 方案{i+1}未产生变化，跳过")
                continue

            analysis_req = self._build_analysis_request(new_design)
            analysis_resp = await self.analysis_agent.run(analysis_req)
            new_analysis = self._extract_analysis_results(analysis_resp)
            if not new_analysis:
                if verbose:
                    print(f"[优化] 方案{i+1}分析失败，跳过")
                continue

            eval_req = self._build_evaluation_request(new_design, new_analysis)
            eval_resp = await self.evaluation_agent.run(eval_req)
            new_evaluation = self._extract_evaluation_report(eval_resp)
            if not new_evaluation:
                if verbose:
                    print(f"[优化] 方案{i+1}评估失败，跳过")
                continue

            score = new_evaluation.get("comprehensive_score", 0)
            if verbose:
                print(f"[优化] 方案{i+1}得分：{score:.1f}")
            candidates.append((new_design, new_analysis, new_evaluation))

        if not candidates:
            if verbose:
                print("[WARNING] 所有候选方案均失败，保留原设计")
            return original_design, original_analysis, original_evaluation

        candidates.sort(key=lambda x: x[2].get("comprehensive_score", 0), reverse=True)

        # Display comparison table and let user choose
        choice = self._display_optimization_comparison(
            original_design, original_analysis, original_evaluation, candidates
        )

        if choice == 0:
            print("[优化] 保留原设计")
            return original_design, original_analysis, original_evaluation
        else:
            selected_design, selected_analysis, selected_evaluation = candidates[choice - 1]
            selected_score = selected_evaluation.get("comprehensive_score", 0)
            print(f"[优化] 已选择方案 {choice}（得分 {selected_score:.1f}）")
            return selected_design, selected_analysis, selected_evaluation

    def _display_optimization_comparison(
        self,
        original_design: Dict,
        original_analysis: Dict,
        original_evaluation: Dict,
        candidates: List[tuple],
    ) -> int:
        """
        Display comparison table of original design and candidate designs.
        Returns user's choice: 0 = original, 1/2/3 = candidate index.
        """
        def get_section(design: Dict) -> str:
            """Get section display string based on structure type (single line)"""
            structure_type = design.get("type", "")
            g = design.get("geometry", {})
            m = design.get("material", {})

            if structure_type == "frame":
                # Frame: return empty, will be handled separately
                return ""

            elif structure_type == "truss":
                # Truss: show cross-sectional area
                A = m.get("A", "?")
                if A != "?" and isinstance(A, (int, float)):
                    # Convert m² to mm² for better readability
                    A_mm2 = A * 1e6
                    return f"{A_mm2:.0f}mm²"
                return "?"

            else:
                # Beam types: show width × height
                w = g.get("width", "?")
                h = g.get("height", "?")
                return f"{w}×{h}"

        def get_column_section(design: Dict) -> str:
            """Get column section for frame structures"""
            structure_type = design.get("type", "")
            if structure_type == "frame":
                g = design.get("geometry", {})
                columns = g.get("columns", {})
                col_w = columns.get("width", "?")
                col_d = columns.get("depth", "?")
                return f"{col_w}×{col_d}"
            return ""

        def get_beam_section(design: Dict) -> str:
            """Get beam section for frame structures"""
            structure_type = design.get("type", "")
            if structure_type == "frame":
                g = design.get("geometry", {})
                beams = g.get("beams", {})
                beam_w = beams.get("width", "?")
                beam_d = beams.get("depth", "?")
                return f"{beam_w}×{beam_d}"
            return ""

        def get_material(design: Dict) -> str:
            return design.get("material", {}).get("material_name", "?")

        def get_results(analysis: Dict) -> tuple:
            r = analysis.get("results", {}) if analysis else {}
            stress = r.get("max_stress_MPa", 0)
            disp = r.get("max_displacement_mm", 0)
            return stress, disp

        def get_dim_score(evaluation: Dict, dim: str) -> str:
            dims = evaluation.get("dimensions", {}) or {}
            score = dims.get(dim, {}).get("score", None)
            return f"{score:.1f}" if score is not None else "N/A"

        # Build all columns: original + candidates
        all_items = [(original_design, original_analysis, original_evaluation)] + candidates
        headers = ["原方案"] + [f"方案{i+1}" for i in range(len(candidates))]

        # Mark recommended (highest score among ALL options including original)
        original_score = original_evaluation.get("comprehensive_score", 0)
        best_overall_idx = max(range(len(all_items)), key=lambda i: all_items[i][2].get("comprehensive_score", 0))
        headers[best_overall_idx] += "★"

        col_w = 14
        sep = "=" * (10 + col_w * len(all_items))

        print("\n" + sep)
        print("多方案优化完成 - 请选择方案")
        print(sep)

        # Header row
        row = f"{'':10}" + "".join(f"{h:>{col_w}}" for h in headers)
        print(row)
        print("-" * (10 + col_w * len(all_items)))

        # Check if this is a frame structure (need separate column/beam rows)
        is_frame = all_items[0][0].get("type", "") == "frame"

        if is_frame:
            # Frame: show column and beam sections separately
            row = f"{'柱截面(m)':10}" + "".join(f"{get_column_section(d):>{col_w}}" for d, _, __ in all_items)
            print(row)
            row = f"{'梁截面(m)':10}" + "".join(f"{get_beam_section(d):>{col_w}}" for d, _, __ in all_items)
            print(row)
        else:
            # Other structures: single section row
            row = f"{'截面(m)':10}" + "".join(f"{get_section(d):>{col_w}}" for d, _, __ in all_items)
            print(row)

        # Material row
        row = f"{'材料':10}" + "".join(f"{get_material(d):>{col_w}}" for d, _, __ in all_items)
        print(row)

        print("-" * (10 + col_w * len(all_items)))

        # Stress row
        row = f"{'应力(MPa)':10}" + "".join(
            f"{get_results(a)[0]:>{col_w}.2f}" for _, a, __ in all_items
        )
        print(row)

        # Displacement row
        row = f"{'位移(mm)':10}" + "".join(
            f"{get_results(a)[1]:>{col_w}.2f}" for _, a, __ in all_items
        )
        print(row)

        print("-" * (10 + col_w * len(all_items)))

        # Dimension scores
        dim_labels = [
            ("economy", "经济性"),
            ("structural_efficiency", "结构效率"),
            ("safety", "安全性"),
            ("sustainability", "可持续性"),
        ]
        for dim_key, dim_label in dim_labels:
            row = f"{dim_label:10}" + "".join(
                f"{get_dim_score(e, dim_key):>{col_w}}" for _, __, e in all_items
            )
            print(row)

        print("-" * (10 + col_w * len(all_items)))

        # Comprehensive score row
        row = f"{'综合得分':10}" + "".join(
            f"{e.get('comprehensive_score', 0):>{col_w}.1f}" for _, __, e in all_items
        )
        print(row)

        # Grade row
        row = f"{'等级':10}" + "".join(
            f"{e.get('grade', 'N/A'):>{col_w}}" for _, __, e in all_items
        )
        print(row)

        print(sep)
        if best_overall_idx == 0:
            print("★ 推荐方案：原方案")
        else:
            print(f"★ 推荐方案：方案{best_overall_idx}")
        print(sep)

        # User choice
        valid = list(range(len(all_items)))
        while True:
            try:
                prompt = f"请选择方案 (0=原方案, {'/'.join(str(i+1) for i in range(len(candidates)))}=候选方案): "
                raw = input(prompt).strip()
                choice = int(raw)
                if choice in valid:
                    return choice
                print(f"请输入 {valid} 中的数字")
            except ValueError:
                print("请输入有效数字")
            except (EOFError, KeyboardInterrupt):
                if best_overall_idx == 0:
                    print("\n用户中断，默认选择原方案")
                else:
                    print(f"\n用户中断，默认选择推荐方案 {best_overall_idx}")
                return best_overall_idx

    async def _generate_candidate_descriptions(
        self,
        design: Dict,
        analysis: Dict,
        evaluation: Dict,
    ) -> List[Dict]:
        """基于评估建议直接生成3个候选设计JSON（每个方案针对一个主要问题）"""
        if not self.api_key or self.api_key == "your-api-key-here":
            return []

        results = analysis.get("results", {})
        recommendations = evaluation.get("recommendations", [])
        dimensions = evaluation.get("dimensions", {})
        rec_text = "\n".join(f"- {r}" for r in recommendations) if recommendations else "无具体建议"

        economy_score = dimensions.get('economy', {}).get('score', 100)
        safety_score = dimensions.get('safety', {}).get('score', 100)
        efficiency_score = dimensions.get('structural_efficiency', {}).get('score', 100)
        sustainability_score = dimensions.get('sustainability', {}).get('score', 100)

        # 根据得分动态生成约束规则
        constraint_rules = []
        if economy_score < 70:
            constraint_rules.append("- 经济性得分偏低：禁止将材料升级到更高强度等级（如C30→C50、Q235→Q345），优先通过减小截面尺寸（10%~25%）改善经济性")
        if safety_score < 75:
            constraint_rules.append("- 安全性得分偏低：禁止减小截面尺寸，禁止降级材料，必须增大截面或提升材料强度")
        if efficiency_score < 60:
            constraint_rules.append("- 结构效率偏低（利用率过低）：截面过于保守，应减小截面尺寸，禁止增大截面")
        if sustainability_score < 60:
            constraint_rules.append("- 可持续性偏低：优先减小截面降低用料量，不建议换钢材（碳排放更高），混凝土等级之间可以调整")
        if safety_score < 75 and economy_score < 70:
            constraint_rules.append("- 安全性与经济性同时偏低时：优先保证安全性，经济性让步")
        constraint_text = "\n".join(constraint_rules) if constraint_rules else "- 无特殊约束，均衡优化各维度"

        prompt = f"""你是一位结构工程专家。请根据以下评估建议，直接生成3个优化后的完整设计方案JSON。

当前设计参数：
{json.dumps(design, ensure_ascii=False, indent=2)}

分析结果：
最大应力 {results.get('max_stress_MPa', 'N/A')} MPa
最大位移 {results.get('max_displacement_mm', 'N/A')} mm

各维度得分：
经济性 {economy_score}
结构效率 {efficiency_score}
安全性 {safety_score}
可持续性 {sustainability_score}

评估系统建议：
{rec_text}

【强制约束规则】（必须严格遵守）：
{constraint_text}
- 每个方案只修改1~2个参数，不要同时改截面+材料+跨度
- 修改幅度限制在10%~30%，不要极端值
- 三个方案之间参数不能完全相同
- 每个方案分别针对不同问题（经济性、结构效率、可持续性），不要重复
- 跨度（length）和荷载（load/distributed_load/point_load等）为用户输入的固定条件，禁止修改

要求：
1. 生成3个方案，每个方案针对建议中的一个主要问题，优化方向必须与建议一致且符合上述约束规则。
2. 每个方案输出完整的设计JSON，结构与原始设计完全一致，只修改相关参数。
3. 材料参数单位：E使用Pa（如32500000000.0），fy使用Pa（如26800000.0）。
4. 直接输出一个JSON数组，包含3个设计对象，不要包含任何其他文字。

示例输出格式：
[
  {{...方案1完整JSON...}},
  {{...方案2完整JSON...}},
  {{...方案3完整JSON...}}
]"""

        try:
            from openai import OpenAI
            client = OpenAI(
                api_key=self.api_key,
                base_url=self.api_base_url if self.api_base_url else None
            )
            response = client.chat.completions.create(
                model=self.api_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
                temperature=0.5,
            )
            content = response.choices[0].message.content.strip()
            candidates = self._extract_json_from_text(content)
            if isinstance(candidates, list) and len(candidates) > 0:
                # validate each candidate
                valid = []
                for c in candidates[:3]:
                    if isinstance(c, dict):
                        ok, _ = self._validate_design_params(c)
                        if ok:
                            orig_mat = design.get('material', {})
                            cand_mat = c.get('material', {})
                            orig_geo = design.get('geometry', {})
                            cand_geo = c.get('geometry', {})

                            # 跨度和荷载为固定条件，强制回退
                            for fixed_key in ('length', 'span'):
                                if fixed_key in orig_geo and cand_geo.get(fixed_key) != orig_geo[fixed_key]:
                                    cand_geo[fixed_key] = orig_geo[fixed_key]
                            for load_key in ('load', 'distributed_load', 'point_load', 'loads'):
                                if load_key in design and c.get(load_key) != design[load_key]:
                                    c[load_key] = design[load_key]

                            # 材料强度等级排序（越靠后越强）
                            mat_rank = ['C20','C25','C30','C35','C40','C45','C50','C55','C60',
                                        'Q235','Q345','Q390','Q420']
                            orig_rank = mat_rank.index(orig_mat.get('name','C30')) if orig_mat.get('name') in mat_rank else 0
                            cand_rank = mat_rank.index(cand_mat.get('name','C30')) if cand_mat.get('name') in mat_rank else 0

                            # 经济性差：禁止升级材料
                            if economy_score < 70 and cand_rank > orig_rank:
                                cand_mat.update({k: orig_mat[k] for k in orig_mat})

                            # 安全性差：禁止减小截面
                            if safety_score < 75:
                                for dim in ('width', 'height', 'area'):
                                    if dim in orig_geo and dim in cand_geo:
                                        if cand_geo[dim] < orig_geo[dim] * 0.99:
                                            cand_geo[dim] = orig_geo[dim]

                            # 过滤与原方案完全相同的候选
                            if c == design:
                                continue
                            valid.append(c)
                return valid
            return []
        except Exception as e:
            print(f"[ERROR] 生成候选方案失败: {e}")
            return []

    def _ask_code_check_failure_action(self, code_check: dict, verbose: bool = True) -> str:
        """
        Ask user how to handle code_check failure.

        Args:
            code_check: Code check results dictionary
            verbose: Whether to print detailed information

        Returns:
            User's choice: "manual", "auto", or "terminate"
        """
        violations = code_check.get('violations', [])
        summary = code_check.get('summary', 'Unknown')

        if verbose:
            print()
            print("=" * 60)
            print("规范检查未通过")
            print("=" * 60)
            print(f"检查结果: {summary}")
            print(f"违规项数: {len(violations)}")
            print()
            print("请选择处理方式：")
            print("  1 - manual    : 查看改进建议，手动修改后重新运行")
            print("  2 - auto      : 自动迭代优化直至满足规范")
            print("  3 - terminate : 终止工作流")
            print("=" * 60)

        while True:
            try:
                choice = input("请输入选项 (1/2/3 或 manual/auto/terminate): ").strip().lower()

                # Map numeric choices to string choices
                choice_map = {
                    "1": "manual",
                    "2": "auto",
                    "3": "terminate",
                    "manual": "manual",
                    "auto": "auto",
                    "terminate": "terminate"
                }

                if choice in choice_map:
                    return choice_map[choice]
                else:
                    print("无效选项，请重新输入")
            except (EOFError, KeyboardInterrupt):
                print("\n用户中断，默认选择 terminate")
                return "terminate"

    def _generate_improvement_suggestions(self, code_check: dict) -> str:
        """
        Generate improvement suggestions based on code_check results.

        Args:
            code_check: Code check results dictionary

        Returns:
            Formatted suggestions string
        """
        violations = code_check.get('violations', [])
        suggestions = []

        for i, v in enumerate(violations, 1):
            rule = v.get('rule', 'Unknown rule')
            actual = v.get('actual_value', 'N/A')
            limit = v.get('limit_value', 'N/A')
            location = v.get('location', 'N/A')

            suggestion = f"{i}. {rule}\n"
            suggestion += f"   位置: {location}\n"
            suggestion += f"   当前值: {actual}\n"
            suggestion += f"   限值: {limit}\n"
            suggestion += f"   建议: 调整结构参数以满足规范要求"
            suggestions.append(suggestion)

        if not suggestions:
            return "未找到具体违规项，请检查整体设计参数"

        return "\n\n".join(suggestions)

    async def _generate_llm_suggestions(
        self,
        design_proposal: Dict,
        analysis_results: Dict,
        code_check: Dict
    ) -> str:
        """
        Use LLM API to generate improvement suggestions based on code_check violations.
        Supports OpenAI-compatible APIs (DeepSeek, OpenAI, etc.) and Anthropic.

        Args:
            design_proposal: Design proposal dictionary
            analysis_results: Analysis results dictionary
            code_check: Code check results dictionary

        Returns:
            LLM-generated improvement suggestions
        """
        if not self.api_key or self.api_key == 'your-api-key-here':
            return "错误：未配置 API key，请在 OpenManus config.toml 或项目 config.toml 中配置"

        # Extract violation details
        violations = code_check.get('violations', [])
        summary = code_check.get('summary', 'Unknown')

        # Get design parameters from results
        results = analysis_results.get('results', {})
        detailed_results = results.get('detailed_results', {})

        # Build prompt for LLM
        prompt = f"""你是一位结构工程专家。请分析以下结构设计的规范检查违规项，并给出改进建议。

设计类型：{design_proposal.get('type', 'Unknown')}

当前设计参数：
- 跨度: {design_proposal.get('geometry', {}).get('length', 'N/A')} m
- 截面: {design_proposal.get('geometry', {}).get('width', 'N/A')} x {design_proposal.get('geometry', {}).get('height', 'N/A')} m
- 材料: {design_proposal.get('material', {}).get('material_name', 'N/A')}

分析结果：
- 最大应力: {results.get('max_stress_MPa', 'N/A')} MPa
- 最大位移: {results.get('max_displacement_mm', 'N/A')} mm
- 应力安全系数: {code_check.get('safety_factors', {}).get('stress', 'N/A')}
- 挠度安全系数: {code_check.get('safety_factors', {}).get('deflection', 'N/A')}

违规项：
{json.dumps(violations, ensure_ascii=False, indent=2)}

**要求**：
1. 简要分析违规原因（每个违规项2-3句话）
2. 给出具体的改进建议，包括：
   - 应该调整哪些参数
   - 建议的参数值或调整方向
   - 调整的优先级
3. 保持简洁明了，总字数控制在400-500字

请用中文回答，格式清晰。"""

        try:
            # Use OpenAI-compatible API (supports DeepSeek, OpenAI, etc.)
            from openai import OpenAI

            client = OpenAI(
                api_key=self.api_key,
                base_url=self.api_base_url if self.api_base_url else None
            )

            response = client.chat.completions.create(
                model=self.api_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,
                temperature=0.7
            )

            return response.choices[0].message.content

        except Exception as e:
            return f"错误：调用 LLM API 失败 - {str(e)}"

    async def _update_design_proposal_with_improvements(
        self,
        design_proposal: Dict,
        user_improvements: str,
        current_results: Dict
    ) -> Dict:
        """
        Update design proposal based on user's improvements using LLM.

        Uses LLM to parse natural language improvements and generate
        a new design proposal JSON with updated parameters.

        Args:
            design_proposal: Current design proposal dictionary
            user_improvements: User's improvement input (natural language)
            current_results: Current analysis results for reference

        Returns:
            Updated design proposal dictionary
        """
        if not self.api_key or self.api_key == 'your-api-key-here':
            print("[WARNING] 未配置 API key，使用原始设计")
            return design_proposal

        # 获取允许修改的参数列表
        allowed_params = self._get_allowed_params(design_proposal)

        # Get current analysis results for reference
        results = current_results.get('results', {})
        code_check = current_results.get('code_check', {})

        prompt = f"""你是一位结构工程专家。请根据用户的改进要求，生成更新后的设计proposal。

当前设计参数：
```json
{json.dumps(design_proposal, ensure_ascii=False, indent=2)}
```

用户改进方案：
{user_improvements}

**允许修改的参数**（只能修改以下参数，其他参数必须保持原值）：
{allowed_params}

当前分析结果（供参考）：
- 最大位移: {results.get('max_displacement_mm', 'N/A')} mm
- 最大应力: {results.get('max_stress_MPa', 'N/A')} MPa
- 最大弯矩: {results.get('max_moment_kNm', 'N/A')} kN*m

请生成更新后的完整设计proposal，要求：
1. 保持JSON格式与原始设计一致
2. 只修改用户指定的参数（且必须在允许范围内）
3. 保持其他参数不变
4. 输出完整的JSON对象
5. 材料参数使用常用单位：fy使用MPa，E使用GPa

重要：只返回JSON对象，不要包含其他文本。"""

        try:
            from openai import OpenAI

            client = OpenAI(
                api_key=self.api_key,
                base_url=self.api_base_url if self.api_base_url else None
            )

            response = client.chat.completions.create(
                model=self.api_model,
                messages=[
                    {"role": "system", "content": "你是一个结构工程专家，负责根据用户改进要求更新设计参数。请只返回JSON格式的设计proposal。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                temperature=0.3
            )

            content = response.choices[0].message.content

            # 提取JSON
            new_design = self._extract_json_from_text(content)

            if new_design:
                # 验证参数合理性并自动转换单位
                is_valid, error_msg = self._validate_design_params(new_design)
                if not is_valid:
                    print(f"[WARNING] 设计参数验证失败: {error_msg}，使用原始设计")
                    return design_proposal
                return new_design
            else:
                print(f"[WARNING] 无法解析改进后的设计，使用原始设计")
                return design_proposal

        except Exception as e:
            print(f"[ERROR] 调用LLM更新设计失败 - {str(e)}，使用原始设计")
            return design_proposal

    async def _manual_improvement_loop(
        self,
        design_proposal: Dict,
        initial_analysis_results: Dict,
        verbose: bool = True
    ) -> tuple:
        """
        Manual improvement loop with LLM-generated suggestions.

        Workflow:
        1. LLM analyzes code_check violations and generates suggestions
        2. User inputs improvements
        3. Use LLM to update design proposal based on improvements
        4. Re-run FEAnalysisAgent with updated design proposal
        5. Loop until compliant or user types "skip"

        Args:
            design_proposal: Design proposal dictionary
            initial_analysis_results: Initial analysis results
            verbose: Whether to print progress

        Returns:
            Tuple of (final_analysis_results, updated_design_proposal)
        """
        loop_count = 0
        current_results = initial_analysis_results
        current_design_proposal = design_proposal.copy()  # Create a copy to update

        while True:
            loop_count += 1
            code_check = current_results.get('code_check', {})

            if verbose:
                print()
                print("=" * 60)
                print(f"[循环 {loop_count}] 正在生成 LLM 改进建议...")
                print("=" * 60)

            # Generate LLM-based improvement suggestions
            suggestions = await self._generate_llm_suggestions(
                current_design_proposal,
                current_results,
                code_check
            )

            if verbose:
                print(suggestions)
                print("=" * 60)

            # Ask user for improvements
            print()
            user_input = input("请输入改进方案（或输入 'skip' 跳过）: ").strip()

            if user_input.lower() == 'skip':
                if verbose:
                    print("[PlanningFlow] 用户跳过改进，使用当前结果")
                return (current_results, current_design_proposal)

            # Update design proposal based on user improvements
            if verbose:
                print()
                print(f"[PlanningFlow] 根据用户改进更新设计提案...")

            updated_design_proposal = await self._update_design_proposal_with_improvements(
                current_design_proposal,
                user_input,
                current_results
            )

            # Check if design actually changed
            if updated_design_proposal == current_design_proposal:
                if verbose:
                    print("[WARNING] 设计未发生变化，继续使用当前设计")

            current_design_proposal = updated_design_proposal

            # Re-run analysis with updated design proposal
            if verbose:
                print(f"[PlanningFlow] 使用更新后的设计重新分析...")

            analysis_request = json.dumps(current_design_proposal, ensure_ascii=False)
            analysis_result = await self.analysis_agent.run(analysis_request)
            current_results = self._extract_analysis_results(analysis_result)

            if not current_results:
                if verbose:
                    print("[ERROR] 无法提取分析结果，终止循环")
                return (initial_analysis_results, design_proposal)

            # Check if now compliant
            new_code_check = current_results.get('code_check', {})
            if new_code_check.get('compliant', False):
                if verbose:
                    print()
                    print("[OK] 设计已满足规范要求！")
                return (current_results, current_design_proposal)
            else:
                violations_count = len(new_code_check.get('violations', []))
                if verbose:
                    print()
                    print(f"[WARNING] 仍有 {violations_count} 个违规项，继续改进...")

    async def _auto_improvement_loop(
        self,
        design_proposal: Dict,
        initial_analysis_results: Dict,
        verbose: bool = True
    ) -> tuple:
        """
        自动改进循环（模仿manual模式，但无需用户交互）

        Workflow:
        1. LLM分析code_check违规并自动生成改进方案
        2. LLM自动更新设计提案
        3. 重新运行FEAnalysisAgent
        4. 循环直到通过或达到最大次数

        Args:
            design_proposal: 设计提案字典
            initial_analysis_results: 初始分析结果
            verbose: 是否打印进度

        Returns:
            Tuple of (final_analysis_results, updated_design_proposal)
        """
        loop_count = 0
        max_loops = 10  # 最大迭代次数
        current_results = initial_analysis_results
        current_design_proposal = design_proposal.copy()

        while loop_count < max_loops:
            loop_count += 1
            code_check = current_results.get('code_check', {})

            if verbose:
                print()
                print("=" * 60)
                print(f"[自动优化 {loop_count}/{max_loops}] 正在生成改进方案...")
                print("=" * 60)

            # Step 1: 使用LLM自动生成改进方案（不需要用户输入）
            improvement_plan = await self._generate_auto_improvement_plan(
                current_design_proposal,
                current_results,
                code_check
            )

            if verbose:
                print(f"[改进方案] {improvement_plan}")

            # 检查是否生成失败
            if improvement_plan.startswith("错误："):
                if verbose:
                    print(f"[ERROR] {improvement_plan}")
                return (current_results, current_design_proposal)

            # Step 2: 从改进方案中提取JSON
            new_design = self._extract_json_from_text(improvement_plan)

            if new_design:
                # 验证参数合理性并自动转换单位
                is_valid, error_msg = self._validate_design_params(new_design)
                if not is_valid:
                    if verbose:
                        print(f"[WARNING] 设计参数验证失败: {error_msg}，保留原设计")
                    # 继续使用原设计，但不终止循环
                    continue

                # 检查设计是否真的变化了
                if new_design != current_design_proposal:
                    current_design_proposal = new_design
                    if verbose:
                        print(f"[PlanningFlow] 设计已更新")
                else:
                    if verbose:
                        print("[WARNING] 设计未发生变化，终止自动优化")
                    return (current_results, current_design_proposal)
            else:
                if verbose:
                    print("[WARNING] 未找到JSON输出，保留原设计")
                # 继续循环，尝试下一轮
                continue

            # Step 3: 重新运行分析
            if verbose:
                print(f"[PlanningFlow] 使用更新后的设计重新分析...")

            analysis_request = json.dumps(current_design_proposal, ensure_ascii=False)
            analysis_result = await self.analysis_agent.run(analysis_request)
            current_results = self._extract_analysis_results(analysis_result)

            if not current_results:
                if verbose:
                    print("[ERROR] 无法提取分析结果，终止循环")
                return (initial_analysis_results, design_proposal)

            # Step 4: 检查是否通过
            new_code_check = current_results.get('code_check', {})
            if new_code_check.get('compliant', False):
                if verbose:
                    print()
                    print(f"[OK] 自动优化成功！设计已满足规范要求（共 {loop_count} 轮）")
                return (current_results, current_design_proposal)
            else:
                violations_count = len(new_code_check.get('violations', []))
                if verbose:
                    print()
                    print(f"[INFO] 仍有 {violations_count} 个违规项，继续优化...")

        # 达到最大次数
        if verbose:
            print()
            print(f"[WARNING] 已达到最大迭代次数（{max_loops}），设计仍未满足规范要求")
        return (current_results, current_design_proposal)

    async def _generate_auto_improvement_plan(
        self,
        design_proposal: Dict,
        analysis_results: Dict,
        code_check: Dict
    ) -> str:
        """
        使用LLM自动生成改进方案（包含改进说明和完整JSON）

        Args:
            design_proposal: 设计提案字典
            analysis_results: 分析结果字典
            code_check: 规范检查结果字典

        Returns:
            LLM生成的改进方案（改进说明 + JSON代码块）
        """
        if not self.api_key or self.api_key == 'your-api-key-here':
            return "错误：未配置 API key，请在 OpenManus config.toml 或项目 config.toml 中配置"

        # 提取违规详情
        violations = code_check.get('violations', [])
        safety_factors = code_check.get('safety_factors', {})

        # 获取设计参数
        results = analysis_results.get('results', {})

        # 获取允许修改的参数列表
        allowed_params = self._get_allowed_params(design_proposal)

        # 构建LLM提示词
        prompt = f"""你是一位结构工程专家。请分析以下结构设计的规范检查违规项，并给出**包含改进说明和更新后的完整设计JSON**。

设计类型：{design_proposal.get('type', 'Unknown')}

当前设计参数：
```json
{json.dumps(design_proposal, ensure_ascii=False, indent=2)}
```

分析结果摘要：
- 最大应力: {results.get('max_stress_MPa', 'N/A')} MPa
- 最大位移: {results.get('max_displacement_mm', 'N/A')} mm
- 应力安全系数: {safety_factors.get('stress', 'N/A')}
- 挠度安全系数: {safety_factors.get('deflection', 'N/A')}

违规项详情：
{json.dumps(violations, ensure_ascii=False, indent=2)}

**允许修改的参数**（只能修改以下参数，其他参数必须保持原值）：
{allowed_params}

**要求**：
1. 第一行输出"改进说明："后跟自然语言描述（供用户理解，例如"增大截面高度以降低应力"）。
2. 空一行。
3. 然后输出一个代码块，包含**更新后的完整设计JSON**，格式必须与输入的JSON完全一致（只修改允许的参数，且必须包含所有原有字段）。
4. 不得引入系统不支持的参数（如"惯性矩"、"圆钢管"等）。
5. 参数值必须在合理范围内（例如截面积不能为负）。
6. 材料参数使用常用单位：fy使用MPa，E使用GPa（例如：fy=235表示235 MPa，E=200表示200 GPa）。

请直接输出结果："""

        try:
            # Use OpenAI-compatible API (supports DeepSeek, OpenAI, etc.)
            from openai import OpenAI

            client = OpenAI(
                api_key=self.api_key,
                base_url=self.api_base_url if self.api_base_url else None
            )

            response = client.chat.completions.create(
                model=self.api_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,
                temperature=0.3
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            return f"错误：调用 LLM API 失败 - {str(e)}"

    def _extract_analysis_results(self, response: str) -> Optional[Dict[str, Any]]:
        """Extract analysis results from response."""
        try:
            import re
            import json

            # Pattern 1: Extract from fe_analysis tool output
            # Match JSON with flexible whitespace handling
            pattern = r'fe_analysis.*?executed:\s*(\{[\s\S]*?\})\s*(?:Step|\Z|$)'
            matches = re.findall(pattern, response, re.DOTALL)

            if matches:
                # Try to parse all matches and prefer success results over error results
                parsed_results = []
                for match in matches:
                    try:
                        result = json.loads(match)
                        parsed_results.append(result)
                    except json.JSONDecodeError:
                        continue

                # Prefer success results
                for result in reversed(parsed_results):
                    if result.get('status') == 'success':
                        return result

                # If no success, return the last parsed result
                if parsed_results:
                    return parsed_results[-1]

            # Pattern 2: Find balanced JSON containing "status" field
            balanced_json = self._find_balanced_json_with_status(response)
            if balanced_json:
                return json.loads(balanced_json)

            return None
        except Exception:
            return None

    def _build_drawing_request(
        self,
        design_proposal: Optional[Dict],
        analysis_results: Optional[Dict]
    ) -> str:
        """Build request for CAD drawing agent."""
        request = {
            "design_proposal": design_proposal,
            "analysis_results": analysis_results,
        }
        return json.dumps(request, ensure_ascii=False)

    def _extract_drawing_results(self, response: str) -> Optional[Dict[str, Any]]:
        """Extract drawing results from response."""
        try:
            import re
            import json

            # Pattern 1: Extract from cad_drawing tool output
            # Modified to handle JSON that may or may not have trailing newline
            pattern = r'cad_drawing.*?executed:\s*(\{[\s\S]*?\})\s*(?:Step|\Z)'
            matches = re.findall(pattern, response, re.DOTALL)
            if matches:
                return json.loads(matches[-1])

            # Pattern 2: Find balanced JSON containing "status" field
            balanced_json = self._find_balanced_json_with_status(response)
            if balanced_json:
                return json.loads(balanced_json)

            return None
        except Exception:
            return None

    def _build_evaluation_request(
        self,
        design_proposal: Optional[Dict],
        analysis_results: Optional[Dict]
    ) -> str:
        """Build request for evaluation agent."""
        request = {
            "design_proposal": design_proposal,
            "analysis_results": analysis_results,
        }
        return json.dumps(request, ensure_ascii=False)

    def _extract_evaluation_report(self, response: str) -> Optional[Dict[str, Any]]:
        """Extract evaluation report from response."""
        try:
            import re
            import json

            # Pattern 1: Extract from evaluation tool output
            pattern = r'evaluation.*?executed:\s*(\{[\s\S]*?\n\})\s*(?:Step|\Z)'
            matches = re.findall(pattern, response, re.DOTALL)
            if matches:
                result = json.loads(matches[-1])
                # If tool returned error, fallback to manual evaluation
                if result.get('status') == 'error':
                    manual_eval = self._extract_manual_evaluation(response)
                    if manual_eval:
                        return manual_eval
                return result

            # Pattern 2: Find balanced JSON containing "status" field
            balanced_json = self._find_balanced_json_with_status(response)
            if balanced_json:
                result = json.loads(balanced_json)
                if result.get('status') == 'error':
                    manual_eval = self._extract_manual_evaluation(response)
                    if manual_eval:
                        return manual_eval
                return result

            # Pattern 3: Fallback to manual evaluation (Markdown)
            return self._extract_manual_evaluation(response)

        except Exception:
            return None

    def _extract_manual_evaluation(self, response: str) -> Optional[Dict[str, Any]]:
        """Extract evaluation from Agent's Markdown manual evaluation output."""
        try:
            import re

            # Extract comprehensive score
            score_pattern = r'(?:Comprehensive Score|综合得分)[:\s]*([0-9.]+)(?:/100)?'
            score_match = re.search(score_pattern, response, re.IGNORECASE)

            # Extract grade
            grade_pattern = r'\*\*Grade[:\s]*([A-F][+\-]?)\*\*'
            grade_match = re.search(grade_pattern, response, re.IGNORECASE)

            if not score_match or not grade_match:
                return None

            score = float(score_match.group(1))
            grade = grade_match.group(1)

            # Extract dimension scores
            dimensions = {}
            dim_patterns = {
                'economy': r'Economy.*?(?:Estimated )?Score[:\s]*([0-9.]+)',
                'structural_efficiency': r'Structural Efficiency.*?(?:Estimated )?Score[:\s]*([0-9.]+)',
                'safety': r'Safety.*?(?:Estimated )?Score[:\s]*([0-9.]+)',
                'sustainability': r'Sustainability.*?(?:Estimated )?Score[:\s]*([0-9.]+)',
            }
            for dim_name, pattern in dim_patterns.items():
                match = re.search(pattern, response, re.IGNORECASE | re.DOTALL)
                if match:
                    dimensions[dim_name] = {'score': float(match.group(1))}

            return {
                'status': 'success',
                'comprehensive_score': score,
                'grade': grade,
                'dimensions': dimensions if dimensions else None,
                'source': 'manual_evaluation',
            }

        except Exception:
            return None

    def _build_report_request(
        self,
        design_proposal: Optional[Dict],
        analysis_results: Optional[Dict],
        evaluation_report: Optional[Dict],
        drawing_results: Optional[Dict]
    ) -> str:
        """Build request for report generation agent."""
        request = {
            "design_proposal": design_proposal,
            "analysis_results": analysis_results,
            "evaluation_report": evaluation_report,
            "drawing_results": drawing_results,
        }
        return json.dumps(request, ensure_ascii=False)

    def _extract_report_results(self, response: str) -> Optional[Dict[str, Any]]:
        """Extract report results from response."""
        try:
            import re
            import json

            # Extract visualization results
            visualization_results = self._extract_visualization_results(response)

            # Extract report file results
            report_results = self._extract_report_file_results(response)

            # If no results found, return None
            if not report_results and not visualization_results:
                return None

            # Build combined ReportResults
            # visualization_results is already the visualizations object (static/interactive)
            combined_results = {
                'status': 'success',
                'report_file': report_results.get('report_file') if report_results else None,
                'visualizations': visualization_results if visualization_results else {},
                'summary': {}
            }

            return combined_results

        except json.JSONDecodeError as e:
            print(f"Failed to parse report results JSON: {e}")
            return None

    def _extract_visualization_results(self, response: str) -> Optional[Dict[str, Any]]:
        """Extract visualization results from response or from output directory."""
        try:
            import re
            import json
            import os

            # Pattern 1: Extract from visualization tool output
            pattern = r'visualization.*?executed:\s*(\{[\s\S]*?\})\s*(?:Step|\Z)'
            matches = re.findall(pattern, response, re.DOTALL)
            if matches:
                json_str = matches[-1]
                result = json.loads(json_str)
                return result.get('visualizations', result)

            # Pattern 2: Extract from code block
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                result = json.loads(json_str)
                return result.get('visualizations', result)

            # Pattern 3: If no visualization output found in response,
            # try to find the latest visualization files in the output directory
            viz_dir = self.output_dir / "visualizations"

            if viz_dir.exists():
                # Find latest PNG and HTML files
                static_files = {}
                interactive_files = {}

                # Get all visualization files and convert to relative paths
                for f in viz_dir.glob('*'):
                    f_rel = f.relative_to(viz_dir.parent)  # Get path relative to output directory
                    f_str = str(f_rel).replace('\\', '/')  # Use forward slashes
                    if f_str.endswith('.png'):
                        if 'moment' in f_str.lower():
                            static_files['moment_diagram'] = f_str
                        elif 'shear' in f_str.lower():
                            static_files['shear_diagram'] = f_str
                        elif 'deflection' in f_str.lower():
                            static_files['deflection_curve'] = f_str
                    elif f_str.endswith('.html'):
                        if 'moment' in f_str.lower():
                            interactive_files['moment_html'] = f_str
                        elif 'shear' in f_str.lower():
                            interactive_files['shear_html'] = f_str
                        elif 'deflection' in f_str.lower():
                            interactive_files['deflection_html'] = f_str

                if static_files or interactive_files:
                    return {
                        'static': static_files,
                        'interactive': interactive_files
                    }

            return None
        except Exception:
            return None

    def _extract_report_file_results(self, response: str) -> Optional[Dict[str, Any]]:
        """Extract report file results from response."""
        try:
            import re
            import json

            # Pattern 1: Extract from report tool output
            pattern = r'report.*?executed:\s*(\{[\s\S]*?\})\s*(?:Step|\Z)'
            matches = re.findall(pattern, response, re.DOTALL)
            if matches:
                return json.loads(matches[-1])

            # Pattern 2: Extract from code block
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                return json.loads(json_str)

            return None
        except Exception:
            return None

    def get_results(self) -> Dict[str, Any]:
        """Get all results from the workflow."""
        return self.results

    def save_results(self, filename: str = "workflow_results.json") -> str:
        """Save results to a JSON file."""
        filepath = self.output_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        return str(filepath)


def create_planning_flow(**kwargs) -> PlanningFlow:
    """
    Factory function to create PlanningFlow instance.

    Args:
        **kwargs: Arguments passed to PlanningFlow constructor

    Returns:
        PlanningFlow instance
    """
    return PlanningFlow(**kwargs)
