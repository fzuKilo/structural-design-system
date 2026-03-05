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
        self.main_output_dir = self.output_dir / f"e2e_test_{self.test_timestamp}"
        self.main_output_dir.mkdir(parents=True, exist_ok=True)

        if verbose:
            print(f"[PlanningFlow] Output directory: {self.main_output_dir}")
            print()

        # Step 1: Design Proposal
        if verbose:
            print("Step 1: Generating design proposal...")
            print("-" * 40)

        design_result = await self.design_agent.run(request)
        self.results["design_proposal"] = self._extract_design_proposal(design_result)

        if verbose and self.results["design_proposal"]:
            print(f"[OK] Design proposal created: {self.results['design_proposal'].get('type')}")

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

        # Check code_check compliance
        if self.results["analysis_results"]:
            code_check = self.results["analysis_results"].get('code_check', {})
            if not code_check.get('compliant', True):
                # Code check failed - ask user for action
                user_choice = self._ask_code_check_failure_action(code_check, verbose)

        # Set up output directories for drawings, visualizations, and reports
        # Each test run gets its own timestamped directory
        drawings_dir = self.main_output_dir / "drawings"
        visualizations_dir = self.main_output_dir / "visualizations"
        reports_dir = self.main_output_dir / "reports"

        # Configure drawing agent output directory
        if hasattr(self.drawing_agent, 'tools') and self.drawing_agent.tools:
            for tool in self.drawing_agent.tools:
                if hasattr(tool, 'set_output_directory'):
                    tool.set_output_directory(str(drawings_dir), None)

        # Configure evaluation agent output directory (for visualizations)
        if hasattr(self.evaluation_agent, 'tools') and self.evaluation_agent.tools:
            for tool in self.evaluation_agent.tools:
                if hasattr(tool, 'set_output_directory'):
                    tool.set_output_directory(str(visualizations_dir), None)

        # Configure report agent output directories
        if hasattr(self.report_agent, 'tools') and self.report_agent.tools:
            for tool in self.report_agent.tools:
                if hasattr(tool, 'set_output_directory'):
                    tool.set_output_directory(str(reports_dir), None)

        # Also configure analysis agent's visualization tool if it exists
        if hasattr(self.analysis_agent, 'tools') and self.analysis_agent.tools:
            for tool in self.analysis_agent.tools:
                if hasattr(tool, 'set_output_directory'):
                    tool.set_output_directory(str(visualizations_dir), None)

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
                    # Option 2: Enable automatic iterative optimization
                    if verbose:
                        print()
                        print("[PlanningFlow] 启动自动迭代优化模式...")

                    # Create new FEAnalysisAgent with loop enabled
                    loop_agent = FEAnalysisAgent(enable_loop=True) if FEAnalysisAgent else None
                    if loop_agent:
                        improved_result = await loop_agent.run(analysis_request)
                        self.results["analysis_results"] = self._extract_analysis_results(improved_result)

                        if verbose:
                            final_code_check = self.results["analysis_results"].get('code_check', {})
                            if final_code_check.get('compliant', False):
                                print("[OK] 自动优化完成，设计已满足规范要求")
                            else:
                                print("[WARNING] 自动优化结束，但设计仍未满足规范要求")

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

        # Step 4: CAD Drawing
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

        if verbose and self.results["drawing_results"]:
            status = self.results['drawing_results'].get('status', 'unknown')
            print(f"[OK] CAD drawings generated: {status}")

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
        prompt = f"""你是一位结构工程专家。请分析以下结构设计的规范检查违规项，并给出具体的改进建议。

设计类型：{design_proposal.get('type', 'Unknown')}

当前设计参数：
{json.dumps(design_proposal, ensure_ascii=False, indent=2)}

分析结果摘要：
{json.dumps(detailed_results, ensure_ascii=False, indent=2)}

规范检查结果：{summary}

违规项详情：
{json.dumps(violations, ensure_ascii=False, indent=2)}

请给出具体的改进建议，包括：
1. 每个违规项的原因分析
2. 应该调整哪些参数（如梁高度、宽度、配筋等）
3. 建议的参数值或调整方向
4. 调整的优先级

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
                max_tokens=2000,
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

        # Extract current design parameters for prompt
        design_type = design_proposal.get('type', 'Unknown')
        current_geometry = design_proposal.get('geometry', {})
        current_material = design_proposal.get('material', {})
        current_loads = design_proposal.get('loads', {})
        current_constraints = design_proposal.get('constraints', {})

        # Get current analysis results for reference
        results = current_results.get('results', {})
        detailed_results = results.get('detailed_results', {})
        code_check = current_results.get('code_check', {})
        violations = code_check.get('violations', [])

        prompt = f"""你是一位结构工程专家。请根据用户的改进要求，生成更新后的设计 proposal。

当前设计参数：
```json
{json.dumps(design_proposal, ensure_ascii=False, indent=2)}
```

用户改进方案：
{user_improvements}

当前分析结果（供参考）：
- 最大位移: {results.get('max_displacement_mm', 'N/A')} mm
- 最大应力: {results.get('max_stress_MPa', 'N/A')} MPa
- 最大弯矩: {results.get('max_moment_kNm', 'N/A')} kN*m

规范检查结果：
{json.dumps(code_check, ensure_ascii=False, indent=2)}

请生成更新后的完整设计 proposal，要求：
1. 保持 JSON 格式与原始设计一致
2. 只修改用户指定的参数（如截面尺寸、材料等级、配筋等）
3. 保持其他参数不变
4. 输出完整的 JSON 对象

重要：只返回 JSON 对象，不要包含其他文本。"""

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
                temperature=0.3  # 低温度确保输出稳定
            )

            content = response.choices[0].message.content

            # Try to extract JSON from response
            import re
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1).strip()
                return json.loads(json_str)

            # Try direct JSON parsing
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # Fallback to original design
                print(f"[WARNING] 无法解析改进后的设计，使用原始设计")
                return design_proposal

        except Exception as e:
            print(f"[ERROR] 调用 LLM 更新设计失败 - {str(e)}，使用原始设计")
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

    def _extract_analysis_results(self, response: str) -> Optional[Dict[str, Any]]:
        """Extract analysis results from response."""
        try:
            import re
            import json

            # Pattern 1: Extract from fe_analysis tool output
            pattern = r'fe_analysis.*?executed:\s*(\{[\s\S]*?\n\})\s*(?:Step|\Z)'
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
                return json.loads(matches[-1])

            # Pattern 2: Find balanced JSON containing "status" field
            balanced_json = self._find_balanced_json_with_status(response)
            if balanced_json:
                return json.loads(balanced_json)

            return None
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
