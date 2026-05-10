import base64
import json
import multiprocessing
import sys
from io import StringIO
from typing import Dict

from app.tool.base import BaseTool
from app.utils.arg_serialization import decode_args


class PythonExecute(BaseTool):
    """A tool for executing Python code with timeout and safety restrictions."""

    name: str = "python_execute"
    description: str = "Executes Python code string. Note: Only print outputs are visible, function return values are not captured. Use print statements to see results."
    parameters: dict = {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "The Python code to execute.",
            },
        },
        "required": ["code"],
    }

    def _run_code(self, code: str, result_dict: dict, safe_globals: dict) -> None:
        original_stdout = sys.stdout
        try:
            output_buffer = StringIO()
            sys.stdout = output_buffer
            exec(code, safe_globals, safe_globals)
            result_dict["observation"] = output_buffer.getvalue()
            result_dict["success"] = True
        except Exception as e:
            result_dict["observation"] = str(e)
            result_dict["success"] = False
        finally:
            sys.stdout = original_stdout

    async def execute(
        self,
        code: str | None = None,
        timeout: int = 5,
        **kwargs,
    ) -> Dict:
        """
        Executes the provided Python code with a timeout.

        Args:
            code (str): The Python code to execute.
            timeout (int): Execution timeout in seconds.

        Returns:
            Dict: Contains 'output' with execution output or error message and 'success' status.
        """

        # Handle multiple parameter passing strategies
        if code is None:
            # Strategy 1: Try raw_args as encoded JSON
            try:
                raw_args = kwargs.get("raw_args", "{}")
                if isinstance(raw_args, str):
                    decoded = decode_args(raw_args)
                    code = decoded.get("code", "")
            except Exception:
                pass
            
            # Strategy 2: Try code_b64 for base64-encoded long code
            if not code:
                try:
                    code_b64 = kwargs.get("code_b64")
                    if code_b64:
                        code = base64.b64decode(code_b64).decode("utf-8")
                except Exception:
                    pass
            
            # Strategy 3: Fallback to direct code kwarg
            if not code:
                code = kwargs.get("code", "")

        with multiprocessing.Manager() as manager:
            result = manager.dict({"observation": "", "success": False})
            if isinstance(__builtins__, dict):
                safe_globals = {"__builtins__": __builtins__}
            else:
                safe_globals = {"__builtins__": __builtins__.__dict__.copy()}
            proc = multiprocessing.Process(
                target=self._run_code, args=(code, result, safe_globals)
            )
            proc.start()
            proc.join(timeout)

            # timeout process
            if proc.is_alive():
                proc.terminate()
                proc.join(1)
                return {
                    "observation": f"Execution timeout after {timeout} seconds",
                    "success": False,
                }
            return dict(result)
