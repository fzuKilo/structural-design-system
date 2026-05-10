import asyncio
import json
from typing import Any, List, Optional, Union
from app.utils.arg_serialization import decode_args

from pydantic import Field

from app.agent.react import ReActAgent
from app.exceptions import TokenLimitExceeded
from app.logger import logger
from app.prompt.toolcall import NEXT_STEP_PROMPT, SYSTEM_PROMPT
from app.schema import TOOL_CHOICE_TYPE, AgentState, Message, ToolCall, ToolChoice
from app.tool import CreateChatCompletion, Terminate, ToolCollection


TOOL_CALL_REQUIRED = "Tool calls required but none provided"


class ToolCallAgent(ReActAgent):
    """Base agent class for handling tool/function calls with enhanced abstraction"""

    name: str = "toolcall"
    description: str = "an agent that can execute tool calls."

    system_prompt: str = SYSTEM_PROMPT
    next_step_prompt: str = NEXT_STEP_PROMPT

    available_tools: ToolCollection = ToolCollection(
        CreateChatCompletion(), Terminate()
    )
    tool_choices: TOOL_CHOICE_TYPE = ToolChoice.AUTO  # type: ignore
    special_tool_names: List[str] = Field(default_factory=lambda: [Terminate().name])

    tool_calls: List[ToolCall] = Field(default_factory=list)
    _current_base64_image: Optional[str] = None

    max_steps: int = 30
    max_observe: Optional[Union[int, bool]] = None

    async def think(self) -> bool:
        """Process current state and decide next actions using tools"""
        if self.next_step_prompt:
            user_msg = Message.user_message(self.next_step_prompt)
            self.messages += [user_msg]

        try:
            # Get response with tool options
            response = await self.llm.ask_tool(
                messages=self.messages,
                system_msgs=(
                    [Message.system_message(self.system_prompt)]
                    if self.system_prompt
                    else None
                ),
                tools=self.available_tools.to_params(),
                tool_choice=self.tool_choices,
            )
        except ValueError:
            raise
        except Exception as e:
            # Check if this is a RetryError containing TokenLimitExceeded
            if hasattr(e, "__cause__") and isinstance(e.__cause__, TokenLimitExceeded):
                token_limit_error = e.__cause__
                logger.error(
                    f"🚨 Token limit error (from RetryError): {token_limit_error}"
                )
                self.memory.add_message(
                    Message.assistant_message(
                        f"Maximum token limit reached, cannot continue execution: {str(token_limit_error)}"
                    )
                )
                self.state = AgentState.FINISHED
                return False
            raise

        self.tool_calls = tool_calls = (
            response.tool_calls if response and response.tool_calls else []
        )
        content = response.content if response and response.content else ""

        # Log response info
        logger.info(f"✨ {self.name}'s thoughts: {content}")
        logger.info(
            f"🛠️ {self.name} selected {len(tool_calls) if tool_calls else 0} tools to use"
        )
        if tool_calls:
            logger.info(
                f"🧰 Tools being prepared: {[call.function.name for call in tool_calls]}"
            )
            logger.info(f"🔧 Tool arguments: {tool_calls[0].function.arguments}")

        try:
            if response is None:
                raise RuntimeError("No response received from the LLM")

            # Handle different tool_choices modes
            if self.tool_choices == ToolChoice.NONE:
                if tool_calls:
                    logger.warning(
                        f"🤔 Hmm, {self.name} tried to use tools when they weren't available!"
                    )
                if content:
                    self.memory.add_message(Message.assistant_message(content))
                    return True
                return False

            # Create and add assistant message
            assistant_msg = (
                Message.from_tool_calls(content=content, tool_calls=self.tool_calls)
                if self.tool_calls
                else Message.assistant_message(content)
            )
            self.memory.add_message(assistant_msg)

            if self.tool_choices == ToolChoice.REQUIRED and not self.tool_calls:
                return True  # Will be handled in act()

            # For 'auto' mode, continue with content if no commands but content exists
            if self.tool_choices == ToolChoice.AUTO and not self.tool_calls:
                return bool(content)

            return bool(self.tool_calls)
        except Exception as e:
            logger.error(f"🚨 Oops! The {self.name}'s thinking process hit a snag: {e}")
            self.memory.add_message(
                Message.assistant_message(
                    f"Error encountered while processing: {str(e)}"
                )
            )
            return False

    async def act(self) -> str:
        """Execute tool calls and handle their results"""
        if not self.tool_calls:
            if self.tool_choices == ToolChoice.REQUIRED:
                raise ValueError(TOOL_CALL_REQUIRED)

            # Return last message content if no tool calls
            return self.messages[-1].content or "No content or commands to execute"

        results = []
        for command in self.tool_calls:
            # Reset base64_image for each tool call
            self._current_base64_image = None

            result = await self.execute_tool(command)

            if self.max_observe:
                result = result[: self.max_observe]

            logger.info(
                f"🎯 Tool '{command.function.name}' completed its mission! Result: {result}"
            )

            # Add tool response to memory
            tool_msg = Message.tool_message(
                content=result,
                tool_call_id=command.id,
                name=command.function.name,
                base64_image=self._current_base64_image,
            )
            self.memory.add_message(tool_msg)
            results.append(result)

        return "\n\n".join(results)

    async def execute_tool(self, command: ToolCall) -> str:
        """Execute a single tool call with robust error handling"""
        if not command or not command.function or not command.function.name:
            return "Error: Invalid command format"

        name = command.function.name
        if name not in self.available_tools.tool_map:
            return f"Error: Unknown tool '{name}'"

        try:
            # Parse arguments with robust fallback for malformed JSON
            raw_args = command.function.arguments or "{}"
            try:
                args = json.loads(raw_args)
            except json.JSONDecodeError:
                # Attempt to recover by extracting the first JSON object-like substring
                try:
                    first = raw_args.index("{")
                    last = raw_args.rindex("}")
                    candidate = raw_args[first : last + 1]
                    args = json.loads(candidate)
                    logger.warning("Recovered JSON arguments by extracting JSON substring")
                except Exception:
                        # As a last resort, try to evaluate as a Python literal
                        try:
                            import ast

                            args = ast.literal_eval(raw_args)
                            logger.warning("Recovered arguments using ast.literal_eval")
                        except Exception:
                            # Try to recover triple-quoted or large raw string fields (common when LLM emits
                            # Python-style triple-quoted strings inside a JSON-like payload).
                            try:
                                import re

                                recovered = None
                                # Keys which often carry large unescaped text
                                keys = ["code", "html_content", "file_text", "content"]
                                for k in keys:
                                    # Match patterns like "code": '''...''' or "code": """..."""
                                    m = re.search(rf'["\']{k}["\']\s*:\s*(?P<quote>"""|\'\'\'|\")', raw_args, flags=re.S)
                                    if not m:
                                        continue
                                    quote = m.group("quote")
                                    # Position after the opening quote
                                    start = m.end()
                                    if quote in ('"""', "'''"):
                                        end_idx = raw_args.find(quote, start)
                                        if end_idx == -1:
                                            continue
                                        extracted = raw_args[start:end_idx]
                                    else:
                                        # For single/double quotes, find the next unescaped matching quote
                                        esc_pattern = re.compile(rf'(?<!\\){quote}')
                                        search_span = raw_args[start:]
                                        m2 = esc_pattern.search(search_span)
                                        if not m2:
                                            continue
                                        extracted = search_span[: m2.start()]

                                    # Build a recovered args dict using extracted value and any obvious simple keys
                                    recovered = {k: extracted}
                                    path_m = re.search(r'"path"\s*:\s*"(?P<p>[^"\n]+)"', raw_args)
                                    cmd_m = re.search(r'"command"\s*:\s*"(?P<c>[^"\n]+)"', raw_args)
                                    if path_m:
                                        recovered["path"] = path_m.group("p")
                                    if cmd_m:
                                        recovered["command"] = cmd_m.group("c")
                                    logger.warning(f"Recovered arguments by extracting raw {k} substring")
                                    break

                                if recovered is not None:
                                    args = recovered
                                else:
                                    # Attempt heuristic extraction for common cases like large raw `file_text`
                                    cmd_match = re.search(r'"command"\s*:\s*"(?P<c>[^\"]+)"', raw_args)
                                    path_match = re.search(r'"path"\s*:\s*"(?P<p>[^\"]+)"', raw_args)
                                    ft_index = raw_args.find('"file_text"')
                                    if cmd_match and path_match and ft_index != -1:
                                        # start of file_text value (after the colon and optional space)
                                        colon = raw_args.find(':', ft_index)
                                        # find first quote after colon
                                        first_quote = raw_args.find('"', colon)
                                        if first_quote != -1:
                                            # Assume file_text runs until the last '}' of the whole string
                                            last_brace = raw_args.rfind('}')
                                            file_text_raw = raw_args[first_quote + 1 : last_brace]
                                            # Trim any trailing '"' or commas
                                            file_text_raw = file_text_raw.rstrip('\",')
                                            args = {
                                                "command": cmd_match.group('c'),
                                                "path": path_match.group('p'),
                                                "file_text": file_text_raw,
                                            }
                                            logger.warning(
                                                "Recovered arguments heuristically by extracting `file_text` substring"
                                            )
                                        else:
                                            raise json.JSONDecodeError("Invalid JSON", raw_args, 0)
                                    else:
                                        raise json.JSONDecodeError("Invalid JSON", raw_args, 0)
                            except Exception:
                                # Re-raise to be handled by outer JSONDecodeError handler
                                raise json.JSONDecodeError("Invalid JSON", raw_args, 0)

            # Decode any encoded fields (e.g., *_b64) so tools receive original names
            try:
                if isinstance(args, dict):
                    args = decode_args(json.dumps(args))
                else:
                    args = decode_args(args)
            except Exception:
                # If decoding fails, proceed with original args
                pass

            # Execute the tool
            logger.info(f"🔧 Activating tool: '{name}'...")
            result = await self.available_tools.execute(name=name, tool_input=args)

            # Handle special tools
            await self._handle_special_tool(name=name, result=result)

            # Check if result is a ToolResult with base64_image
            if hasattr(result, "base64_image") and result.base64_image:
                # Store the base64_image for later use in tool_message
                self._current_base64_image = result.base64_image

            # Format result for display (standard case)
            observation = (
                f"Observed output of cmd `{name}` executed:\n{str(result)}"
                if result
                else f"Cmd `{name}` completed with no output"
            )

            return observation
        except json.JSONDecodeError:
            error_msg = f"Error parsing arguments for {name}: Invalid JSON format"
            logger.error(
                f"📝 Oops! The arguments for '{name}' don't make sense - invalid JSON, arguments:{command.function.arguments}"
            )
            return f"Error: {error_msg}"
        except Exception as e:
            error_msg = f"⚠️ Tool '{name}' encountered a problem: {str(e)}"
            logger.exception(error_msg)
            return f"Error: {error_msg}"

    async def _handle_special_tool(self, name: str, result: Any, **kwargs):
        """Handle special tool execution and state changes"""
        if not self._is_special_tool(name):
            return

        if self._should_finish_execution(name=name, result=result, **kwargs):
            # Set agent state to finished
            logger.info(f"🏁 Special tool '{name}' has completed the task!")
            self.state = AgentState.FINISHED

    @staticmethod
    def _should_finish_execution(**kwargs) -> bool:
        """Determine if tool execution should finish the agent"""
        return True

    def _is_special_tool(self, name: str) -> bool:
        """Check if tool name is in special tools list"""
        return name.lower() in [n.lower() for n in self.special_tool_names]

    async def cleanup(self):
        """Clean up resources used by the agent's tools."""
        logger.info(f"🧹 Cleaning up resources for agent '{self.name}'...")
        for tool_name, tool_instance in self.available_tools.tool_map.items():
            if hasattr(tool_instance, "cleanup") and asyncio.iscoroutinefunction(
                tool_instance.cleanup
            ):
                try:
                    logger.debug(f"🧼 Cleaning up tool: {tool_name}")
                    await tool_instance.cleanup()
                except Exception as e:
                    logger.error(
                        f"🚨 Error cleaning up tool '{tool_name}': {e}", exc_info=True
                    )
        logger.info(f"✨ Cleanup complete for agent '{self.name}'.")

    async def run(self, request: Optional[str] = None) -> str:
        """Run the agent with cleanup when done."""
        try:
            return await super().run(request)
        finally:
            await self.cleanup()
