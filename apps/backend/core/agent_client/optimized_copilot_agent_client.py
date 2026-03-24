"""
Optimized Copilot Agent Client
==============================

Optimized version of CopilotAgentClient with token awareness and prompt optimization.
This extends the original CopilotAgentClient without affecting Claude Code agents.
"""

import logging
from pathlib import Path
from typing import Any

from ..optimization.dynamic_prompt_template import ContextInfo, DynamicPromptTemplate
from ..optimization.hierarchical_prompt import HierarchicalPrompt, PromptLevel
from ..optimization.token_aware_agent import (
    Task,
    TaskComplexity,
    TaskResult,
    TokenAwareAgentBase,
)
from .agent_client import CopilotAgentClient

logger = logging.getLogger(__name__)


class OptimizedCopilotAgentClient(TokenAwareAgentBase):
    """
    Optimized Copilot agent client with token awareness and prompt optimization.

    This class extends TokenAwareAgentBase and wraps the original CopilotAgentClient
    to provide token optimization without changing the core functionality.
    """

    def __init__(
        self,
        model: str = "gpt-4o",
        system_prompt: str | None = None,
        allowed_tools: list[str] | None = None,
        agents: dict[str, Any] | None = None,
        cwd: str | None = None,
        max_turns: int = 50,
        github_token: str | None = None,
        token_budget: int = 3000,
    ):
        """
        Initialize optimized Copilot agent client.

        Args:
            model: Model to use
            system_prompt: System prompt for the agent
            allowed_tools: List of allowed tools
            agents: Sub-agent definitions
            cwd: Current working directory
            max_turns: Maximum number of turns
            github_token: GitHub authentication token
            token_budget: Token budget for this client
        """
        super().__init__(f"copilot_client_{model}", token_budget)

        # Initialize original CopilotAgentClient
        self.original_client = CopilotAgentClient(
            model=model,
            system_prompt=system_prompt,
            allowed_tools=allowed_tools,
            agents=agents,
            cwd=cwd,
            max_turns=max_turns,
            github_token=github_token,
        )

        # Store configuration
        self.model = model
        self.system_prompt = system_prompt
        self.allowed_tools = allowed_tools or []
        self.agents = agents or {}
        self.cwd = cwd
        self.max_turns = max_turns
        self.github_token = github_token

        # Optimization components
        self.hierarchical_prompt = HierarchicalPrompt()
        self.dynamic_prompt = DynamicPromptTemplate()

        # Optimization settings
        self.auto_optimize_prompts = True
        self.context_level = PromptLevel.STANDARD
        self.optimize_subagents = True

        logger.info(
            f"Initialized OptimizedCopilotAgentClient with model {model} and budget {token_budget}"
        )

    async def execute_task_internal(self, task: Task) -> TaskResult:
        """
        Execute a task using optimized Copilot agent client.

        Args:
            task: Task to execute

        Returns:
            TaskResult with execution details
        """
        logger.info(f"Executing optimized Copilot client task: {task.id}")

        try:
            # Optimize prompts if enabled
            if self.auto_optimize_prompts:
                self._optimize_system_prompt()
                self._optimize_subagents()

            # Execute using original client
            response = await self._execute_with_original_client(task)

            # Convert to TaskResult
            return self._convert_to_task_result(task, response)

        except Exception as e:
            logger.error(f"Optimized Copilot client task failed: {str(e)}")
            return TaskResult(
                task_id=task.id,
                success=False,
                error=str(e),
                tokens_used=self._estimate_task_tokens(task),
            )

    async def _execute_with_original_client(self, task: Task):
        """Execute task using original CopilotAgentClient"""
        # Set up the query
        self.original_client.query(task.description)

        # Collect responses
        responses = []
        total_tokens = 0

        try:
            async for message in self.original_client.receive_response():
                responses.append(message)
                # Estimate tokens for this message
                total_tokens += self._estimate_message_tokens(message)
        except Exception as e:
            logger.error(f"Error receiving responses: {str(e)}")
            raise

        return {"responses": responses, "total_tokens": total_tokens, "success": True}

    def _convert_to_task_result(
        self, task: Task, response_data: dict[str, Any]
    ) -> TaskResult:
        """Convert CopilotAgentClient response to TaskResult"""
        success = response_data.get("success", True)
        responses = response_data.get("responses", [])

        # Extract the main response content
        result_content = None
        if responses:
            # Combine all text content blocks
            text_blocks = []
            for response in responses:
                for block in response.content:
                    if block.type.value == "text":
                        text_blocks.append(block.text)

            result_content = "\n".join(text_blocks) if text_blocks else str(responses)

        return TaskResult(
            task_id=task.id,
            success=success,
            result=result_content,
            error=None if success else "Execution failed",
            tokens_used=response_data.get(
                "total_tokens", self._estimate_task_tokens(task)
            ),
            execution_time=0.0,  # Could be enhanced with timing
        )

    def _optimize_system_prompt(self):
        """Optimize the system prompt using hierarchical approach"""
        if not self.system_prompt:
            return

        # Build context info
        context_info = self._build_context_info()

        # Build constraints
        constraints = self._build_constraints()

        # Determine optimal level based on budget
        available_tokens = (
            self.token_budget
            - self.token_tracker.get_agent_stats(self.agent_id).total_tokens
        )

        if available_tokens < 300:
            level = PromptLevel.MINIMAL
        elif available_tokens < 800:
            level = PromptLevel.STANDARD
        else:
            level = PromptLevel.COMPREHENSIVE

        # Generate optimized system prompt
        optimized_prompt = self.hierarchical_prompt.build_prompt(
            task_description=self.system_prompt,
            level=level,
            context=context_info,
            constraints=constraints,
        )

        # Update the original client's system prompt
        self.original_client.system_prompt = optimized_prompt

        logger.debug(f"Optimized system prompt with level {level.value}")

    def _optimize_subagents(self):
        """Optimize sub-agent prompts"""
        if not self.optimize_subagents or not self.agents:
            return

        # Build context info for subagents
        context_info = self._build_context_info()

        # Optimize each sub-agent
        for agent_name, agent_def in self.agents.items():
            if hasattr(agent_def, "prompt"):
                # Optimize the sub-agent prompt
                optimized_prompt = self.dynamic_prompt.generate(
                    task_description=agent_def.prompt,
                    context_info=context_info,
                    max_tokens=500,  # Limit sub-agent prompts
                    output_format="text",
                )

                # Update the sub-agent definition
                agent_def.prompt = optimized_prompt
                logger.debug(f"Optimized sub-agent {agent_name} prompt")

    def _build_context_info(self) -> ContextInfo:
        """Build context information for the agent"""
        context_info = ContextInfo()

        # Add working directory context
        if self.cwd:
            working_path = Path(self.cwd)
            context_info.files = [
                str(f)
                for f in working_path.iterdir()
                if f.is_file() and f.suffix in [".py", ".js", ".ts", ".json", ".md"]
            ][:5]  # Limit to 5 files

        # Add model context
        context_info.recent_history = [
            f"Model: {self.model}",
            f"Max turns: {self.max_turns}",
        ]

        # Add tools context
        if self.allowed_tools:
            context_info.dependencies = self.allowed_tools

        # Add sub-agents context
        if self.agents:
            context_info.constraints = {"available_subagents": list(self.agents.keys())}

        return context_info

    def _build_constraints(self) -> dict[str, Any]:
        """Build constraints for the agent"""
        constraints = {
            "model": self.model,
            "max_turns": self.max_turns,
            "allowed_tools": self.allowed_tools,
            "use_github_copilot_api": True,
            "token_optimization_enabled": self.auto_optimize_prompts,
        }

        # Add working directory constraint
        if self.cwd:
            constraints["working_directory"] = self.cwd

        return constraints

    def _estimate_task_tokens(self, task: Task) -> int:
        """Estimate tokens needed for a task"""
        # Base estimation from task description
        prompt_tokens = len(task.description) // 4

        # Add overhead for API interaction
        overhead = 300  # Approximate overhead for API calls

        # Add system prompt tokens
        system_prompt_tokens = (
            len(self.system_prompt or "") // 4 if self.system_prompt else 0
        )

        # Add context tokens
        context_tokens = 200  # Approximate context tokens

        return prompt_tokens + overhead + system_prompt_tokens + context_tokens

    def _estimate_message_tokens(self, message) -> int:
        """Estimate tokens in a message"""
        total_tokens = 0

        for block in message.content:
            if block.text:
                total_tokens += len(block.text) // 4
            elif block.tool_name:
                total_tokens += 50  # Approximate for tool calls
            elif block.structured_output:
                total_tokens += len(str(block.structured_output)) // 4

        return total_tokens

    async def query(self, prompt: str) -> None:
        """
        Send a prompt/query to the agent.

        This method maintains compatibility with the original interface.
        """
        # Create a task for internal tracking
        task = Task(
            id=f"query_{self.get_current_time()}",
            description=prompt,
            complexity=TaskComplexity.MEDIUM,
            priority="normal",
        )

        # Store the task for execution
        self.active_tasks[task.id] = task

        # Use original client's query method
        self.original_client.query(prompt)

    async def receive_response(self):
        """
        Receive the agent's response as a stream of messages.

        This method maintains compatibility with the original interface.
        """
        # Get the current active task
        if self.active_tasks:
            task_id = next(iter(self.active_tasks.keys()))
            task = self.active_tasks[task_id]
        else:
            # Create a default task
            task = Task(
                id=f"response_{self.get_current_time()}",
                description="Response generation",
                complexity=TaskComplexity.MEDIUM,
                priority="normal",
            )

        try:
            # Receive responses from original client
            responses = []
            total_tokens = 0

            async for message in self.original_client.receive_response():
                responses.append(message)
                total_tokens += self._estimate_message_tokens(message)

                # Yield the message immediately for streaming
                yield message

            # Record token usage
            self.token_tracker.record_usage(
                agent_id=self.agent_id,
                task_id=task.id,
                token_type="output",
                tokens_used=total_tokens,
                task_complexity=self.get_complexity_value(task.complexity),
                success=True,
            )

        except Exception as e:
            logger.error(f"Error in receive_response: {str(e)}")
            # Re-raise the exception to maintain compatibility
            raise

        finally:
            # Clean up active task
            if hasattr(self, "active_tasks") and task_id in self.active_tasks:
                self.active_tasks.pop(task_id, None)

    def supports_subagents(self) -> bool:
        """Whether this client supports native sub-agent execution"""
        return True

    def provider_name(self) -> str:
        """Return the provider identifier"""
        return "copilot"

    async def run_subagents(
        self, agents: dict[str, Any], context_prompt: str
    ) -> dict[str, str]:
        """
        Run sub-agents in parallel using the Copilot Models API.

        This method maintains compatibility with the original interface.
        """
        logger.info(f"Running {len(agents)} optimized sub-agents")

        # Create a task for sub-agent execution
        task = Task(
            id=f"subagents_{self.get_current_time()}",
            description=f"Run sub-agents: {list(agents.keys())}",
            complexity=TaskComplexity.COMPLEX,
            priority="normal",
        )

        try:
            # Execute with original client
            results = await self.original_client.run_subagents(agents, context_prompt)

            # Estimate and record token usage
            estimated_tokens = (
                len(context_prompt) // 4 + len(str(results)) // 4 + 500
            )  # Approximate

            self.token_tracker.record_usage(
                agent_id=self.agent_id,
                task_id=task.id,
                token_type="input",
                tokens_used=estimated_tokens,
                task_complexity=self.get_complexity_value(task.complexity),
                success=True,
            )

            return results

        except Exception as e:
            logger.error(f"Sub-agent execution failed: {str(e)}")

            # Record failure
            self.token_tracker.record_usage(
                agent_id=self.agent_id,
                task_id=task.id,
                token_type="input",
                tokens_used=100,  # Minimal tokens for failed attempt
                task_complexity=self.get_complexity_value(task.complexity),
                success=False,
            )

            # Return error results
            return {agent_id: f"Error: {str(e)}" for agent_id in agents.keys()}

    def get_current_time(self) -> float:
        """Get current timestamp"""
        import time

        return time.time()

    def set_optimization_level(self, level: PromptLevel):
        """Set the optimization level for prompts"""
        self.context_level = level
        logger.info(f"Set optimization level to {level.value}")

    def enable_prompt_optimization(self, enabled: bool = True):
        """Enable or disable prompt optimization"""
        self.auto_optimize_prompts = enabled
        logger.info(f"Prompt optimization {'enabled' if enabled else 'disabled'}")

    def enable_subagent_optimization(self, enabled: bool = True):
        """Enable or disable sub-agent optimization"""
        self.optimize_subagents = enabled
        logger.info(f"Sub-agent optimization {'enabled' if enabled else 'disabled'}")

    def get_optimization_stats(self) -> dict[str, Any]:
        """Get optimization statistics"""
        base_stats = self.get_performance_stats()

        optimization_stats = {
            "auto_optimize_prompts": self.auto_optimize_prompts,
            "optimize_subagents": self.optimize_subagents,
            "context_level": self.context_level.value,
            "original_client_active": True,
            "model": self.model,
            "subagents_count": len(self.agents),
        }

        base_stats.update(optimization_stats)
        return base_stats
