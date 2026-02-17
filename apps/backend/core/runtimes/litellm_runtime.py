"""
LiteLLMRuntime: AgentRuntime for provider-agnostic LLMs via LiteLLM
Implements agent loop with tool execution for OpenAI-compatible LLMs
"""
import asyncio
from typing import Any, Dict, Optional, List
from core.runtime import AgentRuntime, SessionResult, StreamEvent, SessionStatus, ErrorType
from core.llm_client import LLMClient, LLMResponse, LLMToolResponse, ToolCall
from core.provider_config import ProviderConfig
from core.runtimes.tool_executor import ToolExecutor, get_tool_definitions
import progress

class LiteLLMRuntime(AgentRuntime):
    def __init__(self, spec_dir: str, phase: str, project_dir: str, agent_type: str, config: ProviderConfig, cli_thinking: Optional[int] = None):
        self.spec_dir = spec_dir
        self.phase = phase
        self.project_dir = project_dir
        self.agent_type = agent_type
        self.config = config
        self.cli_thinking = cli_thinking
        self.llm_client = LLMClient.from_provider_config(config)
        self.tool_executor = ToolExecutor(project_dir)
        self.tool_definitions = get_tool_definitions(agent_type)
        self.max_turns = 10

    async def run_session(self, prompt: str, tools: Optional[List[Dict[str, Any]]] = None, **kwargs) -> SessionResult:
        turn = 0
        last_response = None
        tool_calls_count = 0
        error_info = None
        usage = None
        while turn < self.max_turns:
            try:
                llm_response: LLMToolResponse = await self.llm_client.complete_with_tools(
                    prompt,
                    tools or self.tool_definitions,
                    **kwargs
                )
                usage = llm_response.usage
                if llm_response.has_tool_calls:
                    tool_results = {}
                    for tool_call in llm_response.tool_calls:
                        tool_calls_count += 1
                        try:
                            result = await self.tool_executor.execute(tool_call.name, tool_call.arguments)
                            tool_results[tool_call.id] = result
                        except Exception as e:
                            tool_results[tool_call.id] = {"error": str(e)}
                    prompt = self._build_tool_result_prompt(prompt, tool_results)
                    turn += 1
                    continue
                else:
                    last_response = llm_response.content
                    break
            except Exception as e:
                error_info = str(e)
                break
        status = SessionStatus.COMPLETE if last_response else SessionStatus.ERROR
        return SessionResult(
            status=status,
            response=last_response,
            error_info=error_info,
            tool_calls_count=tool_calls_count,
            usage=usage
        )

    async def stream_session(self, prompt: str, tools: Optional[List[Dict[str, Any]]] = None, **kwargs):
        turn = 0
        while turn < self.max_turns:
            try:
                llm_response: LLMToolResponse = await self.llm_client.complete_with_tools(
                    prompt,
                    tools or self.tool_definitions,
                    **kwargs
                )
                if llm_response.has_tool_calls:
                    tool_results = {}
                    for tool_call in llm_response.tool_calls:
                        yield StreamEvent(StreamEvent.Type.TOOL_START, tool_call.name)
                        try:
                            result = await self.tool_executor.execute(tool_call.name, tool_call.arguments)
                            tool_results[tool_call.id] = result
                            yield StreamEvent(StreamEvent.Type.TOOL_END, result)
                        except Exception as e:
                            tool_results[tool_call.id] = {"error": str(e)}
                            yield StreamEvent(StreamEvent.Type.ERROR, str(e))
                    prompt = self._build_tool_result_prompt(prompt, tool_results)
                    turn += 1
                    continue
                else:
                    yield StreamEvent(StreamEvent.Type.TEXT, llm_response.content)
                    break
            except Exception as e:
                yield StreamEvent(StreamEvent.Type.ERROR, str(e))
                break
        yield StreamEvent(StreamEvent.Type.DONE, None)

    def _build_tool_result_prompt(self, prompt: str, tool_results: Dict[str, Any]) -> str:
        # Simple prompt augmentation for tool results
        tool_result_str = "\n".join([
            f"Tool {tid}: {res}" for tid, res in tool_results.items()
        ])
        return f"{prompt}\n{tool_result_str}"
