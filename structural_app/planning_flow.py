"""
PlanningFlow - Main Orchestration Class for OpenManus Structural Design System

This module orchestrates the multi-agent workflow for structural design:
1. StructuralDesignAgent - Collects parameters and creates design proposal
2. FEAnalysisAgent - Performs finite element analysis
3. EvaluationAgent - Evaluates design quality (在绘图之前)
4. CADDrawingAgent - Generates CAD drawings
5. ReportGenerationAgent - Generates comprehensive reports
"""

from typing import Dict, Any, Optional, List, Tuple
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
    from structural_app.tool.evaluation_tool import EvaluationTool
    _evaluation_tool_instance = EvaluationTool()
except Exception:
    _evaluation_tool_instance = None

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
        websocket_callback=None,
        task_id: Optional[str] = None,
        redis_url: str = "redis://localhost:6379/0",
        api_config: Optional[Dict[str, Any]] = None,
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
            websocket_callback: Async callback function for WebSocket updates
            task_id: Task UUID (enables WebAskHuman mode when provided)
            redis_url: Redis URL for WebAskHuman answer polling
            api_config: API configuration dict for creating agents
        """
        self.websocket_callback = websocket_callback
        self.task_id = task_id
        self.redis_url = redis_url
        self._current_stage = "unknown"  # 追踪当前阶段
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Create agents if not provided
        if api_config is None:
            api_config = {}

        try:
            self.design_agent = design_agent if design_agent is not None else (StructuralDesignAgent(**api_config) if StructuralDesignAgent else None)
        except Exception as e:
            print(f"[PlanningFlow] Failed to create StructuralDesignAgent: {e}")
            self.design_agent = None

        try:
            self.analysis_agent = analysis_agent if analysis_agent is not None else (FEAnalysisAgent(**api_config) if FEAnalysisAgent else None)
        except Exception as e:
            print(f"[PlanningFlow] Failed to create FEAnalysisAgent: {e}")
            self.analysis_agent = None

        try:
            self.drawing_agent = drawing_agent if drawing_agent is not None else (CADDrawingAgent(**api_config) if CADDrawingAgent else None)
        except Exception as e:
            print(f"[PlanningFlow] Failed to create CADDrawingAgent: {e}")
            self.drawing_agent = None

        try:
            self.evaluation_agent = evaluation_agent if evaluation_agent is not None else (EvaluationAgent(**api_config) if EvaluationAgent else None)
        except Exception as e:
            print(f"[PlanningFlow] Failed to create EvaluationAgent: {e}")
            self.evaluation_agent = None

        try:
            self.report_agent = report_agent if report_agent is not None else (ReportGenerationAgent(**api_config) if ReportGenerationAgent else None)
        except Exception as e:
            print(f"[PlanningFlow] Failed to create ReportGenerationAgent: {e}")
            self.report_agent = None

        # In web mode, replace AskHuman with WebAskHuman in all agents
        if task_id and websocket_callback:
            self._inject_web_ask_human()

        # Store results from each step
        self.results = {
            "design_proposal": None,
            "analysis_results": None,
            "drawing_results": None,
            "evaluation_report": None,
            "report_results": None,
            "bim_results": None,
            "ifc_results": None,
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

    def _inject_web_ask_human(self):
        """Replace AskHuman with WebAskHuman in all agents' tool collections."""
        try:
            from structural_app.tool.web_ask_human import WebAskHuman
        except ImportError:
            return

        web_ask_human = WebAskHuman(
            task_id=self.task_id,
            websocket_callback=self.websocket_callback,
            redis_url=self.redis_url,
        )

        agents = [
            self.design_agent,
            self.analysis_agent,
            self.drawing_agent,
            self.evaluation_agent,
            self.report_agent,
        ]

        for agent in agents:
            if agent is None:
                continue
            # ToolCollection stores tools in .tools (list) and .__tools_map__ (dict)
            tool_collection = getattr(agent, 'available_tools', None)
            if tool_collection is None:
                continue
            tools = getattr(tool_collection, 'tools', [])
            new_tools = [web_ask_human if getattr(t, 'name', '') == 'ask_human' else t for t in tools]
            # If ask_human wasn't in the list, no replacement needed
            if new_tools != tools:
                tool_collection.tools = new_tools
                # Rebuild the name→tool map if it exists
                if hasattr(tool_collection, '__tools_map__'):
                    tool_collection.__tools_map__['ask_human'] = web_ask_human

    async def _broadcast_stage(self, stage: str, status: str, message: str = "", data: dict = None):
        """Broadcast stage update via WebSocket"""
        self._current_stage = stage  # 追踪当前阶段，供 _ask_web_or_cli 使用
        # 同步写入 Redis，供 WebAskHuman 读取当前阶段
        if self.task_id and self.redis_url:
            try:
                import redis as _redis_lib
                _rc = _redis_lib.from_url(self.redis_url, decode_responses=True)
                _rc.set(f"current_stage:{self.task_id}", stage, ex=86400)
                _rc.close()
            except Exception:
                pass
        if self.websocket_callback:
            from datetime import datetime
            payload = {
                "type": "stage",
                "stage": stage,
                "status": status,
                "message": message,
                "timestamp": datetime.now().isoformat()
            }
            if data:
                payload["data"] = data
            await self.websocket_callback(payload)

    async def _broadcast_progress(self, stage: str, current: int, total: int, sub_stage: str, message: str):
        """
        Broadcast detailed progress update via WebSocket

        Args:
            stage: Stage name (design_proposal, fe_analysis, etc.)
            current: Current step number
            total: Total steps in this stage
            sub_stage: Sub-stage identifier
            message: Progress message
        """
        if self.websocket_callback:
            from datetime import datetime
            await self.websocket_callback({
                "type": "progress",
                "stage": stage,
                "current": current,
                "total": total,
                "sub_stage": sub_stage,
                "progress": current / total if total > 0 else 0,
                "message": message,
                "timestamp": datetime.now().isoformat()
            })

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

    def _load_ifc_config(self) -> Optional[Dict]:
        """从config.toml读取IFC配置，enabled=false或无配置时返回None。"""
        current_dir = Path(__file__).resolve().parent
        config_path = current_dir.parent / "config.toml"
        if config_path.exists():
            try:
                config = toml.load(config_path)
                ifc = config.get('ifc', {})
                if ifc.get('enabled', False):
                    return ifc
            except Exception:
                pass
        return None

    async def _run_ifc_export(self, verbose: bool = True) -> Optional[Dict]:
        """可选的IFC导出步骤，询问用户是否导出。"""
        ifc_cfg = self._load_ifc_config()
        if not ifc_cfg:
            return None

        if verbose:
            print()
            print("Step 7: IFC Export (可选)")
            print("-" * 40)
            # 构建 context，只传递选择的索引，不传递完整的方案列表
            context = {}
            if "selected_proposal_index" in self.results:
                context["selected_proposal_index"] = self.results["selected_proposal_index"]
            # 注释掉：不传递完整的方案列表
            # if "selected_proposals_context" in self.results:
            #     context.update(self.results["selected_proposals_context"])

            choice = await self._ask_web_or_cli(
                question="是否导出为IFC文件（BIM）？",
                options=["y - 是，导出IFC", "n - 否，跳过"],
                default="n",
                mapping={"y": "y", "yes": "y", "n": "n", "no": "n"},
                cli_prompt="是否导出为IFC文件（BIM）？(y/n): ",
                context=context if context else None,
            )

            if choice != 'y':
                print("[跳过] IFC导出已跳过")
                return None

            print("[IFC] 正在生成IFC文件...")

        # 将输出目录放到本次运行的 main_output_dir 下
        if hasattr(self, 'main_output_dir'):
            ifc_cfg = dict(ifc_cfg)
            ifc_cfg['output_dir'] = str(self.main_output_dir / "ifc")

        try:
            from structural_app.tool.exporters.ifc_exporter import IfcExporter
            exporter = IfcExporter(ifc_cfg)
            result = exporter.export(
                self.results["design_proposal"],
                self.results["analysis_results"],
                self.results["evaluation_report"],
            )
            if result.get('status') == 'success' and verbose:
                print(f"[OK] IFC导出成功")
                print(f"[IFC] 文件路径: {result['path']}")
            elif result.get('status') == 'error' and verbose:
                print(f"[ERROR] IFC导出失败: {result.get('error')}")
            return result
        except Exception as e:
            if verbose:
                print(f"[ERROR] IFC导出异常: {e}")
            return {'status': 'error', 'error': str(e)}

    def _load_speckle_config(self) -> Optional[Dict]:
        """从config.toml读取Speckle配置，enabled=false时返回None。"""
        current_dir = Path(__file__).resolve().parent
        config_path = current_dir.parent / "config.toml"
        if config_path.exists():
            try:
                config = toml.load(config_path)
                speckle = config.get('speckle', {})
                if speckle.get('token') and speckle.get('project_id'):
                    return speckle
            except Exception:
                pass
        return None

    async def _run_visualization(self, verbose: bool = True) -> Dict:
        """运行可视化工具生成静态和交互式图表。"""
        if verbose:
            print("Step 5.1: Generating visualizations...")

        try:
            structure_type = self.results["design_proposal"].get("type", "beam")

            if structure_type == "truss":
                from structural_app.tool.visualizations.truss_visualizer import TrussVisualizer
                visualizer = TrussVisualizer()
            elif structure_type == "frame":
                from structural_app.tool.visualizations.frame_visualizer import FrameVisualizer
                visualizer = FrameVisualizer()
            else:
                from structural_app.tool.visualizations.beam_visualizer import BeamVisualizer
                visualizer = BeamVisualizer()

            visualizer.set_output_directory(str(self.main_output_dir / "visualizations"))

            static_files = visualizer.generate_static_visualizations(
                self.results["design_proposal"],
                self.results["analysis_results"]
            )
            interactive_files = visualizer.generate_interactive_visualizations(
                self.results["design_proposal"],
                self.results["analysis_results"]
            )

            if verbose:
                print(f"[OK] Visualizations generated: {len(static_files)} static, {len(interactive_files)} interactive")

            return {
                "status": "success",
                "static": static_files,
                "interactive": interactive_files
            }
        except Exception as e:
            if verbose:
                print(f"[ERROR] Visualization failed: {e}")
            return {"status": "error", "error": str(e)}

    async def _run_bim_and_ifc_export(self, verbose: bool = True) -> Tuple[Optional[Dict], Optional[Dict]]:
        """合并询问BIM和IFC导出。"""
        speckle_cfg = self._load_speckle_config()
        ifc_cfg = self._load_ifc_config()

        if not speckle_cfg and not ifc_cfg:
            return None, None

        if verbose:
            print()
            print("Step 5.2: BIM/IFC Export (可选)")
            print("-" * 40)
            # 构建 context，只传递选择的索引，不传递完整的方案列表
            # 避免在BIM导出阶段重复显示方案卡片
            context = {}
            if "selected_proposal_index" in self.results:
                context["selected_proposal_index"] = self.results["selected_proposal_index"]
            # 注释掉：不传递完整的方案列表
            # if "selected_proposals_context" in self.results:
            #     context.update(self.results["selected_proposals_context"])

            choice = await self._ask_web_or_cli(
                question="是否导出BIM模型（Speckle + IFC）？",
                options=["y - 是，导出BIM/IFC", "n - 否，跳过"],
                default="n",
                mapping={"y": "y", "yes": "y", "n": "n", "no": "n"},
                cli_prompt="是否导出BIM模型（Speckle + IFC）？(y/n): ",
                context=context if context else None,
            )

            if choice != 'y':
                print("[跳过] BIM/IFC导出已跳过")
                return None, None

        bim_result = None
        ifc_result = None

        # Speckle导出
        if speckle_cfg:
            if verbose:
                print("[Speckle] 正在推送模型...")
            try:
                from structural_app.tool.exporters.speckle_exporter import SpeckleExporter
                exporter = SpeckleExporter(speckle_cfg)
                bim_result = exporter.export(
                    self.results["design_proposal"],
                    self.results["analysis_results"],
                    self.results["evaluation_report"],
                )
                if bim_result.get('status') == 'success' and verbose:
                    print(f"[OK] Speckle导出成功: {bim_result['url']}")
            except Exception as e:
                if verbose:
                    print(f"[ERROR] Speckle导出失败: {e}")
                bim_result = {'status': 'error', 'error': str(e)}

        # IFC导出
        if ifc_cfg:
            if verbose:
                print("[IFC] 正在生成IFC文件...")
            ifc_cfg = dict(ifc_cfg)
            if hasattr(self, 'main_output_dir'):
                ifc_cfg['output_dir'] = str(self.main_output_dir / "ifc")
            try:
                from structural_app.tool.exporters.ifc_exporter import IfcExporter
                exporter = IfcExporter(ifc_cfg)
                ifc_result = exporter.export(
                    self.results["design_proposal"],
                    self.results["analysis_results"],
                )
                if ifc_result.get('status') == 'success' and verbose:
                    print(f"[OK] IFC导出成功: {ifc_result['path']}")
            except Exception as e:
                if verbose:
                    print(f"[ERROR] IFC导出失败: {e}")
                ifc_result = {'status': 'error', 'error': str(e)}

        return bim_result, ifc_result

    async def _run_bim_export(self, verbose: bool = True) -> Optional[Dict]:
        """可选的Speckle BIM导出步骤，询问用户是否导出。"""
        speckle_cfg = self._load_speckle_config()
        if not speckle_cfg:
            return None

        if verbose:
            print()
            print("Step 6: BIM Export (可选)")
            print("-" * 40)
            # 构建 context，只传递选择的索引，不传递完整的方案列表
            context = {}
            if "selected_proposal_index" in self.results:
                context["selected_proposal_index"] = self.results["selected_proposal_index"]
            # 注释掉：不传递完整的方案列表
            # if "selected_proposals_context" in self.results:
            #     context.update(self.results["selected_proposals_context"])

            choice = await self._ask_web_or_cli(
                question="是否导出到Speckle BIM查看器？",
                options=["y - 是，导出BIM", "n - 否，跳过"],
                default="n",
                mapping={"y": "y", "yes": "y", "n": "n", "no": "n"},
                cli_prompt="是否导出到Speckle BIM查看器？(y/n): ",
                context=context if context else None,
            )

            if choice != 'y':
                print("[跳过] BIM导出已跳过")
                return None

            print("[Speckle] 正在推送模型...")

        try:
            from structural_app.tool.exporters.speckle_exporter import SpeckleExporter
            exporter = SpeckleExporter(speckle_cfg)
            result = exporter.export(
                self.results["design_proposal"],
                self.results["analysis_results"],
                self.results["evaluation_report"],
            )
            if result.get('status') == 'success' and verbose:
                print(f"[OK] BIM导出成功")
                print(f"[Speckle] 查看链接: {result['url']}")
            elif result.get('status') == 'error' and verbose:
                print(f"[ERROR] BIM导出失败: {result.get('error')}")
            return result
        except Exception as e:
            if verbose:
                print(f"[ERROR] BIM导出异常: {e}")
            return {'status': 'error', 'error': str(e)}

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

        await self._broadcast_stage("design_proposal", "started", "开始生成设计方案")
        await self._broadcast_progress("design_proposal", 0, 3, "initializing", "正在初始化设计参数...")
        design_result = await self.design_agent.run(request)
        await self._broadcast_progress("design_proposal", 2, 3, "generating", "正在生成设计方案...")

        # 检测用户取消：Agent 调用 terminate 后返回的字符串中包含终止信号
        if self._is_agent_cancelled(design_result):
            if verbose:
                print()
                print("[PlanningFlow] 用户取消了设计任务，终止整个工作流")
            await self._broadcast_stage("design_proposal", "cancelled", "用户取消了设计任务")
            return {"status": "cancelled", "reason": "user_cancelled"}

        self.results["design_proposal"] = self._extract_design_proposal(design_result)

        # 检测设计方案为空（Agent 未能生成有效 JSON）
        if not self.results["design_proposal"]:
            if verbose:
                print()
                print("[PlanningFlow] 未能获取有效设计方案，终止工作流")
            await self._broadcast_stage("design_proposal", "failed", "未能获取有效设计方案")
            return {"status": "failed", "reason": "no_design_proposal"}

        if verbose and self.results["design_proposal"]:
            print(f"[OK] Design proposal created: {self.results['design_proposal'].get('type')}")

        await self._broadcast_stage("design_proposal", "completed", "设计方案生成完成", data={
            "type": self.results["design_proposal"].get("type"),
            "description": self.results["design_proposal"].get("description", ""),
            "geometry": self.results["design_proposal"].get("geometry", {}),
            "material": self.results["design_proposal"].get("material", {}),
        })

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

        await self._broadcast_stage("fe_analysis", "started", "开始有限元分析")
        await self._broadcast_progress("fe_analysis", 0, 4, "building_model", "正在构建有限元模型...")
        analysis_request = self._build_analysis_request(self.results["design_proposal"])
        self.analysis_agent.output_dir = str(self.main_output_dir)
        await self._broadcast_progress("fe_analysis", 1, 4, "analyzing", "正在进行结构分析...")
        analysis_result = await self.analysis_agent.run(analysis_request)
        await self._broadcast_progress("fe_analysis", 3, 4, "solving", "正在求解位移和内力...")

        if analysis_result == "__CANCELLED__":
            print("\n[PlanningFlow] 用户取消了模型确认，工作流终止。")
            return {"status": "cancelled", "reason": "用户取消可视化确认"}

        self.results["analysis_results"] = self._extract_analysis_results(analysis_result)

        if verbose and self.results["analysis_results"]:
            status = self.results['analysis_results'].get('status', 'unknown')
            print(f"[OK] FE analysis completed: {status}")

        await self._broadcast_stage("fe_analysis", "completed", "有限元分析完成", data={
            "max_stress_MPa": self.results["analysis_results"].get("results", {}).get("max_stress_MPa"),
            "max_displacement_mm": self.results["analysis_results"].get("results", {}).get("max_displacement_mm"),
            "safety_factor": self.results["analysis_results"].get("results", {}).get("safety_factor"),
            "compliant": self.results["analysis_results"].get("code_check", {}).get("compliant"),
            "violations": self.results["analysis_results"].get("code_check", {}).get("violations", []),
        })

        # Export OpenSees script for expert review
        if self.results.get("analysis_results") and self.results["analysis_results"].get("status") == "success":
            await self._export_opensees_script()

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
                user_choice = await self._ask_code_check_failure_action(code_check, verbose)

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

                    await self._broadcast_stage("fe_analysis", "completed", "有限元分析完成（手动改进）", data={
                        "compliant": final_code_check.get('compliant', False),
                        "violations": final_code_check.get('violations', []),
                    })

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

                    await self._broadcast_stage("fe_analysis", "completed", "有限元分析完成（自动优化）", data={
                        "compliant": final_code_check.get('compliant', False),
                        "violations": final_code_check.get('violations', []),
                    })

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

        await self._broadcast_stage("evaluation", "started", "开始设计评估")
        await self._broadcast_progress("evaluation", 0, 2, "analyzing", "正在分析设计质量...")
        self.results["evaluation_report"] = await self._run_evaluation(
            self.results["design_proposal"],
            self.results["analysis_results"]
        )
        await self._broadcast_progress("evaluation", 1, 2, "grading", "正在计算综合评分...")

        if verbose and self.results["evaluation_report"]:
            status = self.results['evaluation_report'].get('status', 'unknown')
            grade = self.results['evaluation_report'].get('grade', 'N/A')
            score = self.results['evaluation_report'].get('comprehensive_score', 0)
            print(f"[OK] Evaluation completed: {status}, Grade: {grade}, Score: {score}")

        await self._broadcast_stage("evaluation", "completed", "设计评估完成", data={
            "comprehensive_score": self.results["evaluation_report"].get("comprehensive_score"),
            "grade": self.results["evaluation_report"].get("grade"),
            "safety_score": self.results["evaluation_report"].get("dimensions", {}).get("safety", {}).get("score"),
            "economy_score": self.results["evaluation_report"].get("dimensions", {}).get("economy", {}).get("score"),
            "efficiency_score": self.results["evaluation_report"].get("dimensions", {}).get("structural_efficiency", {}).get("score"),
            "sustainability_score": self.results["evaluation_report"].get("dimensions", {}).get("sustainability", {}).get("score"),
            "warnings": self.results["evaluation_report"].get("warnings", []),
            "design_type": self.results["design_proposal"].get("type"),
            "geometry": self.results["design_proposal"].get("geometry", {}),
            "material": self.results["design_proposal"].get("material", {}),
        })

        # Step 3.5: Evaluation Alert（预警与优化决策）
        self.skip_drawing = False
        if self.results["evaluation_report"]:
            action = await self._handle_evaluation_alert(self.results["evaluation_report"])

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
                # 广播更新后的设计方案，前端右侧状态栏同步
                await self._broadcast_stage("design_proposal", "completed", "设计方案已更新（优化后）", data={
                    "type": self.results["design_proposal"].get("type"),
                    "description": self.results["design_proposal"].get("description", ""),
                    "geometry": self.results["design_proposal"].get("geometry", {}),
                    "material": self.results["design_proposal"].get("material", {}),
                })

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

            await self._broadcast_stage("cad_drawing", "started", "开始生成CAD图纸")
            await self._broadcast_progress("cad_drawing", 0, 3, "preparing", "正在准备绘图数据...")
            drawing_request = self._build_drawing_request(
                self.results["design_proposal"],
                self.results["analysis_results"]
            )
            await self._broadcast_progress("cad_drawing", 1, 3, "drawing", "正在绘制CAD图纸...")
            # 直接调用 CADDrawingTool，绕过 LLM 避免 metadata（PNG路径）被丢弃
            cad_tool = None
            if hasattr(self.drawing_agent, 'available_tools'):
                for tool in self.drawing_agent.available_tools:
                    if hasattr(tool, 'execute') and 'cad' in type(tool).__name__.lower():
                        cad_tool = tool
                        break
            if cad_tool is not None:
                try:
                    dp = self.results["design_proposal"] or {}
                    tool_result = await cad_tool.execute(
                        structure_type=dp.get('type') or dp.get('structure_type'),
                        geometry=dp.get('geometry'),
                        material=dp.get('material'),
                        loads=dp.get('loads'),
                        constraints=dp.get('constraints'),
                        units=dp.get('units'),
                    )
                    raw = tool_result.output if hasattr(tool_result, 'output') else str(tool_result)
                    self.results["drawing_results"] = json.loads(raw)
                except Exception as e:
                    if verbose:
                        print(f"[WARNING] Direct CADDrawingTool call failed: {e}, falling back to agent")
                    drawing_result = await self.drawing_agent.run(drawing_request)
                    self.results["drawing_results"] = self._extract_drawing_results(drawing_result)
            else:
                drawing_result = await self.drawing_agent.run(drawing_request)
                self.results["drawing_results"] = self._extract_drawing_results(drawing_result)
            await self._broadcast_progress("cad_drawing", 2, 3, "generating", "正在生成DXF文件...")

            if verbose:
                if self.results["drawing_results"]:
                    status = self.results['drawing_results'].get('status', 'unknown')
                    print(f"[OK] CAD drawings generated: {status}")
                else:
                    print(f"[WARNING] Failed to extract drawing results from response")
                    print(f"[DEBUG] Drawing agent response (first 500 chars): {str(drawing_result)[:500]}")

            await self._broadcast_stage("cad_drawing", "completed", "CAD图纸生成完成", data={
                "status": self.results["drawing_results"].get("status"),
                "files": list(self.results["drawing_results"].get("files", {}).keys()),
            })
        else:
            if verbose:
                print()
                print("Step 4: 跳过绘图（report_only 模式）")
            await self._broadcast_stage("cad_drawing", "skipped", "CAD绘图已跳过（仅生成报告模式）")
            self.results["drawing_results"] = {"status": "skipped", "files": {}}

        # Step 5: BIM/IFC Export + Report Generation
        if verbose:
            print()
            print("Step 5: BIM/IFC Export and Report Generation...")
            print("-" * 40)

        await self._broadcast_stage("report_generation", "started", "开始生成报告")
        await self._broadcast_progress("report_generation", 0, 3, "collecting", "正在收集设计数据...")

        # 5.1: BIM/IFC Export (unless report_only mode)
        if not self.skip_drawing:
            await self._broadcast_progress("report_generation", 1, 3, "exporting", "正在导出BIM/IFC模型...")
            bim_result, ifc_result = await self._run_bim_and_ifc_export(verbose)
            self.results["bim_results"] = bim_result
            self.results["ifc_results"] = ifc_result
        else:
            if verbose:
                print("Step 5.1: 跳过BIM/IFC导出（report_only 模式）")
            self.results["bim_results"] = None
            self.results["ifc_results"] = None

        # 5.2: Report Generation (always, report agent handles visualization)
        if verbose:
            print("Step 5.2: Generating comprehensive report...")

        await self._broadcast_progress("report_generation", 2, 3, "writing", "正在编写报告文档...")
        report_request = self._build_report_request(
            self.results["design_proposal"],
            self.results["analysis_results"],
            self.results["evaluation_report"],
            self.results["drawing_results"],
            self.results.get("bim_results"),
            self.results.get("ifc_results"),
            skip_visualization=self.skip_drawing
        )
        report_result = await self.report_agent.run(report_request)
        self.results["report_results"] = self._extract_report_results(report_result)

        if verbose and self.results["report_results"]:
            status = self.results['report_results'].get('status', 'unknown')
            print(f"[OK] Report generated: {status}")

        # 广播100%进度
        await self._broadcast_progress("report_generation", 3, 3, "completed", "报告生成完成")

        await self._broadcast_stage("report_generation", "completed", "报告生成完成", data={
            "report_status": self.results["report_results"].get("status") if self.results.get("report_results") else None,
            "speckle_exported": self.results.get("bim_results", {}).get("status") == "success" if self.results.get("bim_results") else False,
            "ifc_exported": self.results.get("ifc_results", {}).get("status") == "success" if self.results.get("ifc_results") else False,
        })

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

    def _is_agent_cancelled(self, result: str) -> bool:
        """
        检测 Agent 是否因用户取消而终止。

        当 Agent 调用 terminate 工具时，返回字符串中会包含：
        "The interaction has been completed with status: failure"
        """
        if not result or not isinstance(result, str):
            return False
        return "completed with status: failure" in result or "completed with status: cancelled" in result

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
        # 确保 type 字段存在，防止 fe_analysis 报 structure type is None
        if not design_proposal.get("type"):
            fallback_type = (self.results.get("design_proposal") or {}).get("type")
            if fallback_type:
                design_proposal = {**design_proposal, "type": fallback_type}
        return json.dumps(design_proposal, ensure_ascii=False)

    async def _export_opensees_script(self):
        """自动导出OpenSees脚本供专家复核"""
        try:
            design = self.results["design_proposal"]
            stype = design.get('type')

            from structural_app.tool.analyzers.analyzer_factory import AnalyzerFactory
            analyzer = AnalyzerFactory.create(stype)

            script_path = self.main_output_dir / "opensees_script.tcl"
            analyzer.export_opensees_script(design, str(script_path))

            print(f"[OpenSees] 脚本已导出: {script_path}")
            self.results["opensees_script"] = str(script_path)
        except Exception as e:
            print(f"[警告] OpenSees脚本导出失败: {e}")

    async def _handle_evaluation_alert(self, evaluation_report: Dict) -> str:
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

        # Use WebSocket callback if available (Web mode)
        if self.websocket_callback and self.task_id:
            # Build context for frontend display
            context = {
                "warnings": [msg for level, dim, msg in alerts],
                "score": score,
                "grade": evaluation_report.get("grade", "")
            }
            # 预警交互属于 evaluation 阶段
            self._current_stage = "evaluation"
            return await self._ask_user_choice_web(context=context)

        # Fallback to CLI input
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

    async def _ask_web_or_cli(
        self,
        question: str,
        options: list,
        default: str,
        mapping: dict = None,
        cli_prompt: str = "请输入选项: ",
        context: dict = None,
    ) -> str:
        """通用询问方法：Web模式走WebSocket+Redis，CLI模式走input()"""
        import asyncio

        if self.websocket_callback and self.task_id:
            import redis as redis_lib
            from datetime import datetime
            def _strip_heavy_context(record: dict) -> dict:
                """历史记录里精简大字段：proposals 只保留展示所需的字段，去掉 image_path"""
                ctx = record.get("context") or {}
                stripped_ctx = {k: v for k, v in ctx.items() if k not in ("proposals", "image_path")}
                if "proposals" in ctx:
                    # 保留精简版 proposals（name/metrics/recommended），供历史卡片展示
                    stripped_ctx["proposals"] = [
                        {k: v for k, v in p.items() if k in ("name", "metrics", "recommended")}
                        for p in ctx["proposals"]
                    ]
                return {**record, "context": stripped_ctx}

            message = {
                "type": "ask_human",
                "question": question,
                "options": options,
                "default": default,
                "stage": self._current_stage or "unknown",
                "interaction_history": [_strip_heavy_context(r) for r in self.results.get("interaction_history", [])],
            }
            if context:
                message["context"] = context

            await self.websocket_callback(message)
            redis_key = f"ask_human:{self.task_id}"
            client = redis_lib.from_url(self.redis_url, decode_responses=True)
            try:
                timeout = 1800
                elapsed = 0
                while elapsed < timeout:
                    answer = client.get(redis_key)
                    if answer is not None:
                        client.delete(redis_key)
                        answer = answer.strip().lower()
                        final = mapping.get(answer, default) if mapping else answer
                        # 记录交互历史（保存完整信息）
                        if "interaction_history" not in self.results:
                            self.results["interaction_history"] = []
                        self.results["interaction_history"].append({
                            "stage": self._current_stage or "unknown",
                            "question": question,
                            "answer": final,
                            "time": datetime.now().strftime("%H:%M:%S"),
                            "options": options,
                            "context": {k: v for k, v in (context or {}).items() if k != 'image_path'},
                        })
                        return final
                    await asyncio.sleep(1)
                    elapsed += 1
            finally:
                client.close()
            return default
        else:
            while True:
                try:
                    answer = input(cli_prompt).strip().lower()
                    if mapping:
                        if answer in mapping:
                            return mapping[answer]
                        print("无效选项，请重新输入")
                    else:
                        return answer
                except (EOFError, KeyboardInterrupt):
                    return default

    async def _ask_user_choice_web(self, context: dict = None) -> str:
        """Ask user for choice via WebSocket + Redis (kept for compatibility)"""
        return await self._ask_web_or_cli(
            question="请选择后续操作",
            options=[
                "continue - 继续生成图纸和完整报告",
                "optimize - 尝试自动优化（推荐）",
                "report_only - 仅生成报告（跳过绘图）",
                "terminate - 终止工作流",
            ],
            default="optimize",
            mapping={
                "1": "continue", "continue": "continue",
                "2": "optimize", "optimize": "optimize",
                "3": "report_only", "report_only": "report_only",
                "4": "terminate", "terminate": "terminate",
            },
            cli_prompt="请输入选项 (1/2/3/4): ",
            context=context,
        )

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
        target_count = 3
        max_retry_rounds = 3  # 最多重试3轮
        retry_round = 0
        tried_designs = []  # 记录已尝试过的设计，避免重复

        # 先告知前端总方案数
        if self.websocket_callback:
            from datetime import datetime
            await self.websocket_callback({
                "type": "scheme_start",
                "total": target_count,
                "timestamp": datetime.now().isoformat(),
            })

        current_designs = candidate_designs

        while len(candidates) < target_count and retry_round < max_retry_rounds:
            retry_round += 1
            need = target_count - len(candidates)

            if retry_round > 1:
                if verbose:
                    print(f"\n[优化] 第{retry_round}轮重试，还需 {need} 个合规方案...")
                await self._broadcast_progress("evaluation", len(candidates), target_count,
                    "retrying", f"部分方案不合规，正在重新生成 {need} 个合规方案（第{retry_round}轮）...")
                # 把已失败的设计传入，让 LLM 知道哪些截面不合规
                current_designs = await self._generate_candidate_descriptions(
                    original_design, original_analysis, original_evaluation,
                    failed_designs=tried_designs
                )
                if not current_designs:
                    break

            for i, new_design in enumerate(current_designs):
                if len(candidates) >= target_count:
                    break

                # 跳过已尝试过的设计
                if new_design in tried_designs:
                    continue
                tried_designs.append(new_design)

                if new_design == original_design:
                    if verbose:
                        print(f"[优化] 方案未产生变化，跳过")
                    continue

                slot = len(candidates) + 1
                await self._broadcast_progress("evaluation", len(candidates), target_count,
                    f"scheme_{slot}_analyzing", f"正在分析候选方案 {slot}/{target_count}...")

                analysis_req = self._build_analysis_request(new_design)
                analysis_resp = await self.analysis_agent.run(
                    analysis_req,
                    skip_visual_validation=True
                )
                new_analysis = self._extract_analysis_results(analysis_resp)
                if not new_analysis:
                    if verbose:
                        print(f"[优化] 方案分析失败，跳过")
                    continue

                new_evaluation = await self._run_evaluation(new_design, new_analysis)
                if not new_evaluation:
                    if verbose:
                        print(f"[优化] 方案评估失败，跳过")
                    continue

                # 过滤不合规方案
                new_code_check = new_analysis.get('code_check', {})
                if not new_code_check.get('compliant', True):
                    violations = new_code_check.get('violations', [])
                    if verbose:
                        print(f"[优化] 方案未通过规范检查（{len(violations)}条违规），跳过")
                    continue

                score = new_evaluation.get("comprehensive_score", 0)
                if verbose:
                    print(f"[优化] 方案{slot}合规，得分：{score:.1f}")
                await self._broadcast_progress("evaluation", slot, target_count,
                    f"scheme_{slot}_done", f"方案 {slot}/{target_count} 分析完成，得分：{score:.1f}")

                if self.websocket_callback:
                    from datetime import datetime
                    metrics = self._build_scheme_metrics(new_design, new_analysis, new_evaluation)
                    await self.websocket_callback({
                        "type": "scheme_ready",
                        "index": slot,
                        "total": target_count,
                        "metrics": metrics,
                        "timestamp": datetime.now().isoformat(),
                    })
                candidates.append((new_design, new_analysis, new_evaluation))

        if not candidates:
            if verbose:
                print("[WARNING] 所有轮次均未能生成合规候选方案，保留原设计")
            return original_design, original_analysis, original_evaluation

        if len(candidates) < target_count and verbose:
            print(f"[WARNING] 仅生成了 {len(candidates)}/{target_count} 个合规方案")

        candidates.sort(key=lambda x: x[2].get("comprehensive_score", 0), reverse=True)

        # Display comparison table and let user choose
        choice = await self._display_optimization_comparison(
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

    def _build_scheme_metrics(self, design: Dict, analysis: Dict, evaluation: Dict) -> Dict:
        """构建方案 metrics，与 _display_optimization_comparison 里的格式完全一致。"""
        geo = design.get("geometry", {})
        mat = design.get("material", {})
        structure_type = design.get("type") or (self.results.get("design_proposal") or {}).get("type", "")
        is_frame = structure_type == "frame"

        def get_column_section(d: Dict) -> str:
            g = d.get("geometry", {})
            cols = g.get("columns", {})
            w = cols.get("width", g.get("column_width", "?"))
            h = cols.get("depth", cols.get("height", g.get("column_depth", "?")))
            return f"{w}×{h}"

        def get_beam_section(d: Dict) -> str:
            g = d.get("geometry", {})
            beams = g.get("beams", {})
            w = beams.get("width", g.get("beam_width", "?"))
            h = beams.get("depth", beams.get("height", g.get("beam_depth", "?")))
            return f"{w}×{h}"

        def get_section(d: Dict) -> str:
            g = d.get("geometry", {})
            m = d.get("material", {})
            if structure_type == "truss":
                A = m.get("A", None)
                return f"{A*1e6:.0f}mm²" if A and isinstance(A, (int, float)) else "?"
            return (
                g.get("section_name") or g.get("section")
                or (f"H{g.get('height_mm','')}×{g.get('flange_width_mm','')}" if g.get("height_mm") else None)
                or (f"{g.get('width','')}×{g.get('height','')}" if g.get("width") and g.get("height") else "—")
            )

        def get_dim_score(ev: Dict, dim: str) -> str:
            dims = ev.get("dimensions", {}) or {}
            score = dims.get(dim, {}).get("score", None)
            return f"{score:.1f}" if score is not None else "N/A"

        results = analysis.get("results", {})
        stress = results.get("max_stress_MPa", 0)
        disp = results.get("max_displacement_mm", 0)

        metrics: Dict = {}
        if is_frame:
            metrics["col_section"] = get_column_section(design) + "m"
            metrics["beam_section"] = get_beam_section(design) + "m"
        elif structure_type == "truss":
            metrics["section"] = get_section(design)
            span = geo.get("span", geo.get("length", None))
            height = geo.get("height", None)
            n_panels = geo.get("n_panels", geo.get("num_panels", None))
            if span is not None:
                metrics["跨度"] = f"{span}m"
            if height is not None:
                metrics["桁架高度"] = f"{height}m"
            if n_panels is not None:
                metrics["节间数"] = str(n_panels)
        else:
            metrics["section"] = get_section(design)

        metrics["material"] = mat.get("material_name") or mat.get("grade") or "—"
        metrics["stress"] = f"{stress:.2f}"
        metrics["displacement"] = f"{disp:.2f}"
        metrics["economy"] = get_dim_score(evaluation, "economy")
        metrics["efficiency"] = get_dim_score(evaluation, "structural_efficiency")
        metrics["safety"] = get_dim_score(evaluation, "safety")
        metrics["sustainability"] = get_dim_score(evaluation, "sustainability")
        metrics["total_score"] = f"{evaluation.get('comprehensive_score', 0):.1f}"
        metrics["grade"] = evaluation.get("grade", "N/A")
        return metrics

    async def _display_optimization_comparison(
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
        options = ["0 - 原方案"] + [f"{i+1} - 候选方案{i+1}" for i in range(len(candidates))]

        # Build context with proposal comparison data
        proposals = []
        for idx, (design, analysis, evaluation) in enumerate(all_items):
            proposal_name = "原方案" if idx == 0 else f"方案{idx}"
            is_recommended = (idx == best_overall_idx)

            # Extract metrics
            results = analysis.get("results", {})
            dimensions = evaluation.get("dimensions", {})

            metrics = {}
            # Section
            if is_frame:
                metrics["col_section"] = get_column_section(design) + "m"
                metrics["beam_section"] = get_beam_section(design) + "m"
            elif design.get("type") == "truss":
                g = design.get("geometry", {})
                m_d = design.get("material", {})
                A = m_d.get("A", None)
                A_str = f"{A*1e6:.0f}mm²" if A and isinstance(A, (int, float)) else "?"
                metrics["section"] = A_str
                span = g.get("span", g.get("length", None))
                height = g.get("height", None)
                n_panels = g.get("n_panels", g.get("num_panels", None))
                if span is not None:
                    metrics["跨度"] = f"{span}m"
                if height is not None:
                    metrics["桁架高度"] = f"{height}m"
                if n_panels is not None:
                    metrics["节间数"] = str(n_panels)
            else:
                metrics["section"] = get_section(design)

            # Material
            metrics["material"] = get_material(design)

            # Stress and displacement
            stress, disp = get_results(analysis)
            metrics["stress"] = f"{stress:.2f}"
            metrics["displacement"] = f"{disp:.2f}"

            # Dimension scores
            metrics["economy"] = f"{get_dim_score(evaluation, 'economy')}"
            metrics["efficiency"] = f"{get_dim_score(evaluation, 'structural_efficiency')}"
            metrics["safety"] = f"{get_dim_score(evaluation, 'safety')}"
            metrics["sustainability"] = f"{get_dim_score(evaluation, 'sustainability')}"

            # Total score and grade
            metrics["total_score"] = f"{evaluation.get('comprehensive_score', 0):.1f}"
            metrics["grade"] = evaluation.get('grade', 'N/A')

            proposals.append({
                "name": proposal_name,
                "recommended": is_recommended,
                "metrics": metrics
            })

        recommendation = "原方案" if best_overall_idx == 0 else f"方案{best_overall_idx}"

        context = {
            "proposals": proposals,
            "recommendation": recommendation
        }

        # 方案选择属于 evaluation 阶段，强制设置 stage，避免被优化过程中的广播覆盖
        self._current_stage = "evaluation"
        raw = await self._ask_web_or_cli(
            question=f"请选择方案 (0=原方案, {'/'.join(str(i+1) for i in range(len(candidates)))}=候选方案)",
            options=options,
            default=str(best_overall_idx),
            mapping=None,
            cli_prompt=f"请选择方案 (0=原方案, {'/'.join(str(i+1) for i in range(len(candidates)))}=候选方案): ",
            context=context,
        )
        try:
            choice = int(raw.strip())
            if choice in valid:
                # 保存用户选择的方案索引和方案信息，供后续阶段使用
                self.results["selected_proposal_index"] = choice
                self.results["selected_proposals_context"] = context
                return choice
        except (ValueError, AttributeError):
            pass
        # 保存默认选择
        self.results["selected_proposal_index"] = best_overall_idx
        self.results["selected_proposals_context"] = context
        return best_overall_idx

    async def _generate_candidate_descriptions(
        self,
        design: Dict,
        analysis: Dict,
        evaluation: Dict,
        failed_designs: List[Dict] = None,
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

        # 提取 code_check 违规信息，用于提示词约束
        code_check = analysis.get('code_check', {})
        violations = code_check.get('violations', [])
        is_compliant = code_check.get('compliant', True)

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

        # 长细比违规时，强制要求候选方案截面不得减小
        if not is_compliant and violations:
            slenderness_violations = [v for v in violations if 'slenderness' in v.get('type', '').lower() or 'slenderness' in v.get('message', '').lower()]
            if slenderness_violations:
                # 计算当前截面对应的最小合规截面（λ=L/r≤150，r=sqrt(A/π)，A≥(L/150)²*π）
                detailed = analysis.get('results', {}).get('detailed_results', {})
                member_lengths = detailed.get('extra', {}).get('member_lengths', [])
                max_len = max(member_lengths) if member_lengths else 0
                if max_len > 0:
                    import math
                    min_r = max_len / 150.0
                    min_A_m2 = min_r ** 2 * math.pi
                    min_A_mm2 = int(min_A_m2 * 1e6) + 1
                    constraint_rules.append(
                        f"- 【严重违规】当前设计存在长细比超限（λ>{150}），所有候选方案截面积 A 必须 ≥ {min_A_mm2} mm²，"
                        f"禁止减小截面，否则方案将被自动丢弃"
                    )
                else:
                    constraint_rules.append("- 【严重违规】当前设计存在长细比超限，所有候选方案截面积必须大于当前值，禁止减小截面")

        constraint_text = "\n".join(constraint_rules) if constraint_rules else "- 无特殊约束，均衡优化各维度"

        # 违规信息文本
        violation_text = ""
        if not is_compliant and violations:
            violation_text = f"\n规范检查违规项（必须在候选方案中解决）：\n" + "\n".join(f"- {v.get('message', v)}" for v in violations)

        # 方案C：计算合规下限 + 方案A：反馈已失败截面
        compliance_hint = ""
        if not is_compliant and violations:
            slenderness_violations = [v for v in violations if 'slenderness' in v.get('type', '').lower() or 'slenderness' in v.get('message', '').lower()]
            if slenderness_violations:
                import math
                detailed = analysis.get('results', {}).get('detailed_results', {})
                member_lengths = detailed.get('extra', {}).get('member_lengths', [])
                if member_lengths:
                    max_len = max(member_lengths)
                    # 圆形截面：r = sqrt(A/π)/2，λ = L/r ≤ 150 → A ≥ (2L*sqrt(π)/150)²
                    import math
                    min_A_m2 = (2 * max_len * math.sqrt(math.pi) / 150) ** 2
                    min_A_mm2 = math.ceil(min_A_m2 * 1e6)
                    compliance_hint += f"\n【长细比合规下限（精确计算）】\n最长杆件 L={max_len:.4f}m，圆形截面 r=sqrt(A/π)/2，λ≤150 要求 A≥{min_A_mm2} mm²（{min_A_m2:.6f} m²）\n所有候选方案的截面积 A 必须 ≥ {min_A_mm2} mm²，否则必然不合规。\n"

        if failed_designs:
            failed_summary = []
            for fd in failed_designs:
                mat = fd.get('material', {})
                A = mat.get('A')
                if A:
                    failed_summary.append(f"A={A*1e6:.0f}mm²（{A:.4f}m²）")
            if failed_summary:
                compliance_hint += f"\n【已验证不合规的截面（禁止重复使用）】\n" + "、".join(failed_summary) + "\n请生成与上述截面不同且 ≥ 合规下限的方案。\n"

        prompt = f"""你是一位结构工程专家。请根据以下评估建议，直接生成3个优化后的完整设计方案JSON。

当前设计参数：
{json.dumps(design, ensure_ascii=False, indent=2)}

分析结果：
最大应力 {results.get('max_stress_MPa', 'N/A')} MPa
最大位移 {results.get('max_displacement_mm', 'N/A')} mm
{violation_text}{compliance_hint}
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
- 【规范合规强制要求】所有候选方案必须通过规范检查（code_check），不合规方案会被自动丢弃

【长细比合规截面计算方法（必须掌握）】
本系统桁架截面为实心圆形截面，惯性半径公式为：
  r = sqrt(A / π) / 2
长细比 λ = L / r = 2 * L * sqrt(π) / sqrt(A) ≤ 150
因此合规截面下限：A ≥ (2 * L_max * sqrt(π) / 150)²
其中 L_max 为最长杆件长度（斜腹杆，通常是 sqrt(节间长² + 桁架高²)）。
请用此公式自行计算合规下限，生成的所有方案截面积 A 必须 ≥ 该下限，并在此基础上做差异化优化（如 A_min、A_min×1.1、A_min×1.2 等不同截面，或调整桁架高度、节间数等几何参数）。

要求：
1. 生成3个方案，每个方案针对建议中的一个主要问题，优化方向必须与建议一致且符合上述约束规则。
2. 3个方案之间不能完全相同（至少有一个参数不同）。
3. 每个方案输出完整的设计JSON，结构与原始设计完全一致，只修改相关参数。
4. 材料参数单位：E使用Pa（如32500000000.0），fy使用Pa（如26800000.0）。
5. 直接输出一个JSON数组，包含3个设计对象，不要包含任何其他文字。

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
                max_tokens=4000,
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
                            orig_mat_name = orig_mat.get('material_name') or orig_mat.get('name', 'C30')
                            cand_mat_name = cand_mat.get('material_name') or cand_mat.get('name', 'C30')
                            orig_rank = mat_rank.index(orig_mat_name) if orig_mat_name in mat_rank else 0
                            cand_rank = mat_rank.index(cand_mat_name) if cand_mat_name in mat_rank else 0

                            # 经济性差：禁止升级材料
                            if economy_score < 70 and cand_rank > orig_rank:
                                cand_mat.update({k: orig_mat[k] for k in orig_mat})

                            # 安全性差：禁止减小截面
                            if safety_score < 75:
                                for dim in ('width', 'height', 'area'):
                                    if dim in orig_geo and dim in cand_geo:
                                        if cand_geo[dim] < orig_geo[dim] * 0.99:
                                            cand_geo[dim] = orig_geo[dim]

                            # 桁架：n_panels变化时自动重算荷载节点编号
                            if c.get('type') == 'truss':
                                orig_n = orig_geo.get('n_panels')
                                cand_n = cand_geo.get('n_panels')
                                if orig_n and cand_n and orig_n != cand_n:
                                    cand_loads = c.get('loads', {})
                                    nodal = cand_loads.get('nodal', [])
                                    if nodal:
                                        # 节点编号规则：底弦 1~(n+1)，顶弦 (n+2)~(2n+2)
                                        # 将原节点按位置比例映射到新节点编号
                                        new_nodal = []
                                        for nl in nodal:
                                            old_node = nl['node']
                                            # 判断是底弦还是顶弦
                                            if old_node <= orig_n + 1:
                                                # 底弦节点：保持相对位置（第i个底弦节点）
                                                idx = old_node - 1  # 0-based index
                                                ratio = idx / orig_n if orig_n > 0 else 0
                                                new_node = max(1, min(cand_n + 1, round(ratio * cand_n) + 1))
                                            else:
                                                # 顶弦节点：偏移量 = old_node - (orig_n+2)
                                                top_idx = old_node - (orig_n + 2)  # 0-based top chord index
                                                ratio = top_idx / orig_n if orig_n > 0 else 0
                                                new_node = (cand_n + 2) + round(ratio * cand_n)
                                                new_node = max(cand_n + 2, min(2 * cand_n + 2, new_node))
                                            new_nodal.append({**nl, 'node': new_node})
                                        cand_loads['nodal'] = new_nodal
                                        c['loads'] = cand_loads

                            # 过滤与原方案完全相同的候选
                            if c == design:
                                print(f"[DEBUG] 方案被过滤（与原方案完全相同）: {json.dumps(c.get('geometry'), ensure_ascii=False)} / {c.get('material', {}).get('material_name')}")
                                continue
                            valid.append(c)

                # 兜底：不足3个时按短板维度自动补充
                if len(valid) < 3:
                    valid = self._supplement_candidates(design, valid, economy_score, safety_score, efficiency_score, sustainability_score)

                return valid
            return []
        except Exception as e:
            print(f"[ERROR] 生成候选方案失败: {e}")
            return []

    def _supplement_candidates(
        self,
        design: Dict,
        valid: List[Dict],
        economy_score: float,
        safety_score: float,
        efficiency_score: float,
        sustainability_score: float,
    ) -> List[Dict]:
        """当LLM生成的有效方案不足3个时，按短板维度自动补充。"""
        import copy

        mat_rank = ['C20','C25','C30','C35','C40','C45','C50','C55','C60',
                    'Q235','Q345','Q390','Q420']

        def is_duplicate(c):
            if c == design:
                return True
            for v in valid:
                if c == v:
                    return True
            return False

        def make_candidate(geo_overrides=None, mat_overrides=None):
            c = copy.deepcopy(design)
            if geo_overrides:
                c['geometry'].update(geo_overrides)
            if mat_overrides:
                c['material'].update(mat_overrides)
            return c

        # 按短板优先级确定补充规则列表
        rules = []

        if safety_score < 75:
            # 安全性差：增大截面或升级材料
            orig_h = design.get('geometry', {}).get('height', 0.3)
            orig_w = design.get('geometry', {}).get('width', 0.2)
            orig_mat_name = design.get('material', {}).get('material_name', 'C30')
            rules.append(('增大梁宽20%', make_candidate(geo_overrides={'width': round(orig_w * 1.2, 4)})))
            rules.append(('增大梁高和梁宽各15%', make_candidate(geo_overrides={'height': round(orig_h * 1.15, 4), 'width': round(orig_w * 1.15, 4)})))
            if orig_mat_name in mat_rank and mat_rank.index(orig_mat_name) + 1 < len(mat_rank):
                next_mat = mat_rank[mat_rank.index(orig_mat_name) + 1]
                rules.append(('升级一级材料', make_candidate(mat_overrides={'material_name': next_mat})))

        elif economy_score < 70:
            # 经济性差：减小截面（安全允许范围内）
            orig_h = design.get('geometry', {}).get('height', 0.3)
            orig_w = design.get('geometry', {}).get('width', 0.2)
            rules.append(('减小梁高10%', make_candidate(geo_overrides={'height': round(orig_h * 0.9, 4)})))
            rules.append(('减小梁宽10%', make_candidate(geo_overrides={'width': round(orig_w * 0.9, 4)})))
            rules.append(('同时减小梁高梁宽各10%', make_candidate(geo_overrides={'height': round(orig_h * 0.9, 4), 'width': round(orig_w * 0.9, 4)})))

        elif efficiency_score < 60:
            # 结构效率差：截面过于保守，减小截面
            orig_h = design.get('geometry', {}).get('height', 0.3)
            orig_w = design.get('geometry', {}).get('width', 0.2)
            rules.append(('减小梁高15%', make_candidate(geo_overrides={'height': round(orig_h * 0.85, 4)})))
            rules.append(('增大梁高减小梁宽提高截面效率', make_candidate(geo_overrides={'height': round(orig_h * 1.15, 4), 'width': round(orig_w * 0.9, 4)})))
            rules.append(('减小梁宽15%', make_candidate(geo_overrides={'width': round(orig_w * 0.85, 4)})))

        elif sustainability_score < 60:
            # 可持续性差：减小截面降低用料
            orig_h = design.get('geometry', {}).get('height', 0.3)
            orig_w = design.get('geometry', {}).get('width', 0.2)
            rules.append(('减小梁高10%', make_candidate(geo_overrides={'height': round(orig_h * 0.9, 4)})))
            rules.append(('减小梁宽10%', make_candidate(geo_overrides={'width': round(orig_w * 0.9, 4)})))
            rules.append(('同时减小梁高梁宽各10%', make_candidate(geo_overrides={'height': round(orig_h * 0.9, 4), 'width': round(orig_w * 0.9, 4)})))

        else:
            # 综合得分偏低但无明显短板：增大梁宽
            orig_h = design.get('geometry', {}).get('height', 0.3)
            orig_w = design.get('geometry', {}).get('width', 0.2)
            orig_mat_name = design.get('material', {}).get('material_name', 'C30')
            rules.append(('增大梁宽20%', make_candidate(geo_overrides={'width': round(orig_w * 1.2, 4)})))
            rules.append(('增大梁高和梁宽各15%', make_candidate(geo_overrides={'height': round(orig_h * 1.15, 4), 'width': round(orig_w * 1.15, 4)})))
            if orig_mat_name in mat_rank and mat_rank.index(orig_mat_name) + 1 < len(mat_rank):
                next_mat = mat_rank[mat_rank.index(orig_mat_name) + 1]
                rules.append(('升级一级材料', make_candidate(mat_overrides={'material_name': next_mat})))

        for label, candidate in rules:
            if len(valid) >= 3:
                break
            if not is_duplicate(candidate):
                print(f"[优化] 自动补充方案（{label}）")
                valid.append(candidate)

        return valid

    async def _ask_code_check_failure_action(self, code_check: dict, verbose: bool = True) -> str:
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

        # Format violations for frontend display, merging duplicates by type
        type_groups: dict = {}
        for v in violations:
            if isinstance(v, dict):
                description = v.get('description', v.get('message', v.get('rule', '未知违规')))
                vtype = v.get('type', 'unknown')
            elif isinstance(v, str):
                description = v
                vtype = 'unknown'
            else:
                description = str(v)
                vtype = 'unknown'
            translated = self._translate_violation(description)
            if vtype not in type_groups:
                type_groups[vtype] = {'msg': translated, 'count': 0}
            type_groups[vtype]['count'] += 1

        violation_messages = []
        for vtype, info in type_groups.items():
            if info['count'] > 1:
                violation_messages.append(f"{info['msg']}（共 {info['count']} 处）")
            else:
                violation_messages.append(info['msg'])

        # Build context for WebSocket (use 'warnings' key to match frontend)
        context = {
            "warnings": violation_messages,
            "summary": summary
        }

        return await self._ask_web_or_cli(
            question="规范检查未通过，请选择处理方式",
            options=[
                "manual - 查看改进建议，手动修改后重新运行",
                "auto - 自动迭代优化直至满足规范",
                "terminate - 终止工作流",
            ],
            default="terminate",
            mapping={
                "1": "manual", "manual": "manual",
                "2": "auto", "auto": "auto",
                "3": "terminate", "terminate": "terminate",
            },
            cli_prompt="请输入选项 (1/2/3 或 manual/auto/terminate): ",
            context=context,
        )

    def _translate_violation(self, text: str) -> str:
        """
        Translate English violation messages to Chinese.

        Args:
            text: English violation message

        Returns:
            Chinese violation message
        """
        import re

        # Pattern 1: "Max stress X MPa exceeds allowable Y MPa"
        match = re.search(r'Max stress ([\d.]+) MPa exceeds allowable ([\d.]+) MPa', text)
        if match:
            actual, limit = match.groups()
            return f"应力超限：实际值 {actual} MPa > 限值 {limit} MPa"

        # Pattern 2: "Max deflection X mm exceeds limit Y mm (L/250)"
        match = re.search(r'Max deflection ([\d.]+) mm exceeds limit ([\d.]+) mm \(L/(\d+)\)', text)
        if match:
            actual, limit, ratio = match.groups()
            return f"挠度超限：实际值 {actual} mm > 限值 {limit} mm（L/{ratio}）"

        # Pattern 3: "Deflection exceeds limit: Xm > Ym"
        match = re.search(r'Deflection exceeds limit: ([\d.]+)m > ([\d.]+)m', text)
        if match:
            actual, limit = match.groups()
            actual_mm = float(actual) * 1000
            limit_mm = float(limit) * 1000
            return f"挠度超限：实际值 {actual_mm:.2f} mm > 限值 {limit_mm:.2f} mm"

        # Pattern 4: "Stress exceeds limit: X MPa > Y MPa"
        match = re.search(r'Stress exceeds limit: ([\d.]+)MPa > ([\d.]+)MPa', text)
        if match:
            actual, limit = match.groups()
            return f"应力超限：实际值 {actual} MPa > 限值 {limit} MPa"

        # Pattern 5: "Member X slenderness ratio too high: λ=Y > Z"
        match = re.search(r'slenderness ratio too high: λ=([\d.]+) > (\d+)', text)
        if match:
            actual, limit = match.groups()
            return f"杆件长细比超限：λ={actual} > 限值 {limit}"

        # Pattern 6: "Member X slenderness ratio Y > Z"
        match = re.search(r'slenderness ratio ([\d.]+) > (\d+)', text)
        if match:
            actual, limit = match.groups()
            return f"杆件长细比超限：λ={actual} > 限值 {limit}"

        # Fallback: return original text if no pattern matches
        return text

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

        # Build design type specific parameter description and supported params hint
        design_type = design_proposal.get('type', 'unknown')
        geometry = design_proposal.get('geometry', {})
        material = design_proposal.get('material', {})

        if design_type == 'truss':
            current_params_text = f"""- 跨度 (geometry.span): {geometry.get('span', 'N/A')} m
- 桁架高度 (geometry.height): {geometry.get('height', 'N/A')} m
- 节间数 (geometry.n_panels): {geometry.get('n_panels', 'N/A')}
- 桁架类型 (geometry.truss_type): {geometry.get('truss_type', 'pratt')}
- 弹性模量 (material.E): {material.get('E', 'N/A')} Pa
- 截面积 (material.A): {material.get('A', 'N/A')} m²
- 屈服强度 (material.fy): {material.get('fy', 'N/A')} Pa
- 材料名称 (material.material_name): {material.get('material_name', 'N/A')}"""
            supported_params_text = """系统支持修改的参数（请在建议中直接使用这些字段名）：
- geometry.span：桁架跨度（m）
- geometry.height：桁架高度（m），增大可降低长细比
- geometry.n_panels：节间数，增大可缩短杆件计算长度
- geometry.truss_type：桁架类型（pratt/howe/warren）
- material.A：杆件截面积（m²），增大可直接降低长细比
- material.E：弹性模量（Pa），如Q235=200GPa，Q355=206GPa
- material.fy：屈服强度（Pa），如Q235=235MPa，Q355=355MPa
- material.material_name：材料名称（如Q235、Q355）"""

        elif design_type == 'frame':
            current_params_text = f"""- 跨数 (geometry.num_bays): {geometry.get('num_bays', 'N/A')}
- 层数 (geometry.num_stories): {geometry.get('num_stories', 'N/A')}
- 各跨宽度 (geometry.bay_widths): {geometry.get('bay_widths', 'N/A')} m
- 各层高度 (geometry.story_heights): {geometry.get('story_heights', 'N/A')} m
- 柱截面宽 (geometry.columns.width): {geometry.get('columns', {}).get('width', 'N/A')} m
- 柱截面高 (geometry.columns.depth): {geometry.get('columns', {}).get('depth', 'N/A')} m
- 梁截面宽 (geometry.beams.width): {geometry.get('beams', {}).get('width', 'N/A')} m
- 梁截面高 (geometry.beams.depth): {geometry.get('beams', {}).get('depth', 'N/A')} m
- 弹性模量 (material.E): {material.get('E', 'N/A')} Pa
- 屈服强度 (material.fy): {material.get('fy', 'N/A')} Pa"""
            supported_params_text = """系统支持修改的参数（请在建议中直接使用这些字段名）：
- geometry.bay_widths：各跨宽度列表（m），如[3.0, 3.0]
- geometry.story_heights：各层高度列表（m），如[4.0, 3.5, 3.5]
- geometry.columns.width / depth：柱截面宽/高（m）
- geometry.beams.width / depth：梁截面宽/高（m）
- material.E：弹性模量（Pa），如C30混凝土=30GPa
- material.fy：屈服强度/抗压强度（Pa），如C30=14.3MPa"""

        else:  # beam
            current_params_text = f"""- 跨度 (geometry.length): {geometry.get('length', 'N/A')} m
- 截面宽 (geometry.width): {geometry.get('width', 'N/A')} m
- 截面高 (geometry.height): {geometry.get('height', 'N/A')} m
- 弹性模量 (material.E): {material.get('E', 'N/A')} Pa
- 泊松比 (material.nu): {material.get('nu', 'N/A')}
- 屈服强度 (material.fy): {material.get('fy', 'N/A')} Pa"""
            supported_params_text = """系统支持修改的参数（请在建议中直接使用这些字段名）：
- geometry.length：梁跨度（m）
- geometry.width：截面宽度（m）
- geometry.height：截面高度（m），增大可提高抗弯刚度
- material.E：弹性模量（Pa），如C30=30GPa，C40=32.5GPa
- material.nu：泊松比（如混凝土取0.2）
- material.fy：屈服强度（Pa）"""

        # Build prompt for LLM
        prompt = f"""你是一位结构工程专家。请分析以下结构设计的规范检查违规项，并给出改进建议。

设计类型：{design_type}

当前设计参数：
{current_params_text}

分析结果：
- 最大应力: {results.get('max_stress_MPa', 'N/A')} MPa
- 最大位移: {results.get('max_displacement_mm', 'N/A')} mm
- 应力安全系数: {code_check.get('safety_factors', {}).get('stress', 'N/A')}
- 挠度安全系数: {code_check.get('safety_factors', {}).get('deflection', 'N/A')}

违规项：
{json.dumps(violations, ensure_ascii=False, indent=2)}

**要求**：
1. 简要分析违规原因（2-3句话）
2. 给出具体的改进建议，直接对应系统支持的参数字段，给出建议值
3. 调整优先级排序
4. 末尾单独列出"建议修改的参数"，格式为：参数字段名 → 建议值（原因）

{supported_params_text}

请用中文回答，格式清晰，总字数控制在500字以内。"""

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

            # Ask user for improvements - show LLM suggestions and text input in one step
            print()
            user_input = await self._ask_web_or_cli(
                question="请根据以下改进建议，输入您的改进方案（输入 skip 可跳过）",
                options=[],
                default="",
                mapping=None,
                cli_prompt="请输入改进方案（或输入 'skip' 跳过）: ",
                context={"suggestions_text": suggestions or "（LLM建议生成失败，请直接输入改进方案）"},
            )

            if user_input.lower().startswith('skip') or user_input.strip() == '':
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
            analysis_result = await self.analysis_agent.run(
                analysis_request,
                skip_visual_validation=True  # 手动优化循环不需要预览图
            )
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

            await self._broadcast_progress("fe_analysis", 1, 4, "auto_optimizing",
                f"[自动优化 {loop_count}/{max_loops}] 正在生成改进方案...")

            # Step 1: 使用LLM自动生成改进方案（不需要用户输入）
            improvement_plan = await self._generate_auto_improvement_plan(
                current_design_proposal,
                current_results,
                code_check
            )

            if verbose:
                print(f"[改进方案] {improvement_plan}")

            # 提取改进说明文字（JSON之前的部分）推送给前端
            plan_description = improvement_plan.split("```")[0].strip() if "```" in improvement_plan else improvement_plan[:800]
            await self._broadcast_stage("fe_analysis", "running",
                f"[自动优化 {loop_count}/{max_loops}] 改进方案已生成",
                data={"auto_improvement_plan": plan_description, "loop": loop_count, "max_loops": max_loops})

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

            await self._broadcast_progress("fe_analysis", 3, 4, "auto_optimizing",
                f"[自动优化 {loop_count}/{max_loops}] 正在重新分析...")

            analysis_request = json.dumps(current_design_proposal, ensure_ascii=False)
            analysis_result = await self.analysis_agent.run(
                analysis_request,
                skip_visual_validation=True  # 自动优化循环不需要预览图
            )
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
                await self._broadcast_progress("fe_analysis", 4, 4, "auto_optimizing",
                    f"[自动优化] 优化成功！共 {loop_count} 轮，设计已满足规范要求")
                return (current_results, current_design_proposal)
            else:
                violations_count = len(new_code_check.get('violations', []))
                if verbose:
                    print()
                    print(f"[INFO] 仍有 {violations_count} 个违规项，继续优化...")
                await self._broadcast_progress("fe_analysis", 2, 4, "auto_optimizing",
                    f"[自动优化 {loop_count}/{max_loops}] 仍有 {violations_count} 个违规项，继续优化...")

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

    async def _run_evaluation(
        self,
        design_proposal: Optional[Dict],
        analysis_results: Optional[Dict]
    ) -> Optional[Dict[str, Any]]:
        """直接调用 EvaluationTool，绕过 LLM。"""
        if _evaluation_tool_instance is None:
            return None
        result = await _evaluation_tool_instance.execute(
            design_proposal=design_proposal,
            analysis_results=analysis_results
        )
        if hasattr(result, 'output'):
            raw = result.output
        else:
            raw = str(result)
        try:
            return json.loads(raw)
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
        drawing_results: Optional[Dict],
        bim_results: Optional[Dict] = None,
        ifc_results: Optional[Dict] = None,
        skip_visualization: bool = False
    ) -> str:
        """Build request for report generation agent."""
        import copy
        # 裁剪 detailed_results 中的大数组，避免超出 LLM 工具参数长度限制
        analysis_for_report = copy.deepcopy(analysis_results) if analysis_results else None
        # 保留完整数组供 Visualizer 使用（裁剪前深拷贝）
        analysis_results_full = copy.deepcopy(analysis_results) if analysis_results else None
        if analysis_for_report:
            detailed = analysis_for_report.get('results', {}).get('detailed_results', {})
            for key in ('displacements', 'stresses', 'moments', 'shears', 'nodes'):
                detailed.pop(key, None)
        request = {
            "design_proposal": design_proposal,
            "analysis_results": analysis_for_report,
            "analysis_results_full": analysis_results_full,
            "evaluation_report": evaluation_report,
            "drawing_results": drawing_results,
            "bim_results": bim_results,
            "ifc_results": ifc_results,
            "skip_visualization": skip_visualization,
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
