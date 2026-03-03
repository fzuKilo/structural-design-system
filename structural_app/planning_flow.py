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
            output_dir: Directory for output files
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

        # Step 1: Design Proposal
        if verbose:
            print("Step 1: Generating design proposal...")
            print("-" * 40)

        design_result = await self.design_agent.run(request)
        self.results["design_proposal"] = self._extract_design_proposal(design_result)

        if verbose and self.results["design_proposal"]:
            print(f"[OK] Design proposal created: {self.results['design_proposal'].get('type')}")

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
            pattern = r'cad_drawing.*?executed:\s*(\{[\s\S]*?\n\})\s*(?:Step|\Z)'
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

            # Pattern 1: Extract from report tool output
            pattern = r'report.*?executed:\s*(\{[\s\S]*?\n\})\s*(?:Step|\Z)'
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
