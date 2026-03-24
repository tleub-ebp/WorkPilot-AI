"""
Token Aware Agent Base
=====================

Base class for token-aware agents that provides budget management
and optimization capabilities without affecting existing Claude Code agents.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any

from .token_tracker import TokenTracker, TokenType

logger = logging.getLogger(__name__)


class TaskComplexity(Enum):
    """Task complexity levels"""

    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"
    VERY_COMPLEX = "very_complex"


@dataclass
class Task:
    """Task definition with metadata"""

    id: str
    description: str
    complexity: TaskComplexity
    constraints: dict[str, Any] = None
    estimated_tokens: int | None = None
    priority: str = "normal"  # low, normal, high, critical


@dataclass
class TaskResult:
    """Result of task execution"""

    task_id: str
    success: bool
    result: Any = None
    error: str | None = None
    tokens_used: int = 0
    execution_time: float = 0.0


class TokenAwareAgentBase(ABC):
    """
    Base class for token-aware agents.

    This class provides:
    - Token budget management
    - Task complexity assessment
    - Automatic task decomposition
    - Performance tracking
    - Optimization recommendations
    """

    def __init__(self, agent_id: str, token_budget: int = 1000):
        self.agent_id = agent_id
        self.token_budget = token_budget
        self.token_tracker = TokenTracker()
        self.token_tracker.set_budget(agent_id, token_budget)

        # Task management
        self.active_tasks: dict[str, Task] = {}
        self.task_queue: list[Task] = []

        # Optimization settings
        self.auto_decompose = True
        self.max_tokens_per_task = token_budget // 2
        self.complexity_threshold = 0.7

        logger.info(
            f"Initialized TokenAwareAgent {agent_id} with budget {token_budget}"
        )

    @abstractmethod
    def execute_task_internal(self, task: Task) -> TaskResult:
        """
        Execute a task (to be implemented by subclasses).

        Args:
            task: Task to execute

        Returns:
            TaskResult with execution details
        """
        pass

    def execute_task(self, task: Task) -> TaskResult:
        """
        Execute a task with token awareness and optimization.

        Args:
            task: Task to execute

        Returns:
            TaskResult with execution details
        """
        logger.info(f"Executing task {task.id} for agent {self.agent_id}")

        # Check if task needs decomposition
        if self.should_decompose_task(task):
            logger.info(f"Decomposing complex task {task.id}")
            return self.execute_decomposed_task(task)

        # Check token budget
        estimated_tokens = self.estimate_tokens_for_task(task)
        if not self.token_tracker.check_budget(self.agent_id, estimated_tokens):
            logger.warning(f"Insufficient token budget for task {task.id}")
            return TaskResult(
                task_id=task.id,
                success=False,
                error="Insufficient token budget",
                tokens_used=0,
            )

        # Execute task with monitoring
        self.active_tasks[task.id] = task
        start_time = self.get_current_time()

        try:
            result = self.execute_task_internal(task)

            # Record token usage
            actual_tokens = result.tokens_used or estimated_tokens
            self.token_tracker.record_usage(
                agent_id=self.agent_id,
                task_id=task.id,
                token_type=TokenType.INPUT,
                tokens_used=actual_tokens,
                task_complexity=self.get_complexity_value(task.complexity),
                success=result.success,
            )

            # Calculate execution time
            result.execution_time = self.get_current_time() - start_time

            logger.info(
                f"Task {task.id} completed in {result.execution_time:.2f}s, "
                f"used {actual_tokens} tokens, success: {result.success}"
            )

            return result

        except Exception as e:
            logger.error(f"Task {task.id} failed: {str(e)}")
            return TaskResult(
                task_id=task.id,
                success=False,
                error=str(e),
                tokens_used=estimated_tokens,
                execution_time=self.get_current_time() - start_time,
            )

        finally:
            self.active_tasks.pop(task.id, None)

    def should_decompose_task(self, task: Task) -> bool:
        """Determine if a task should be decomposed"""
        if not self.auto_decompose:
            return False

        # Check complexity
        complexity_score = self.get_complexity_value(task.complexity)
        if complexity_score > self.complexity_threshold:
            return True

        # Check estimated tokens
        estimated_tokens = self.estimate_tokens_for_task(task)
        if estimated_tokens > self.max_tokens_per_task:
            return True

        return False

    def execute_decomposed_task(self, task: Task) -> TaskResult:
        """Execute a decomposed task by breaking it into subtasks"""
        subtasks = self.decompose_task(task)
        results = []
        total_tokens = 0

        logger.info(f"Decomposed task {task.id} into {len(subtasks)} subtasks")

        for subtask in subtasks:
            subtask_result = self.execute_task(subtask)
            results.append(subtask_result)
            total_tokens += subtask_result.tokens_used

            if not subtask_result.success:
                logger.error(f"Subtask {subtask.id} failed: {subtask_result.error}")
                return TaskResult(
                    task_id=task.id,
                    success=False,
                    error=f"Subtask {subtask.id} failed: {subtask_result.error}",
                    tokens_used=total_tokens,
                )

        # Combine results
        combined_result = self.combine_subtask_results(task, results)
        combined_result.tokens_used = total_tokens

        return combined_result

    def decompose_task(self, task: Task) -> list[Task]:
        """
        Decompose a complex task into simpler subtasks.

        This is a basic implementation that can be overridden by subclasses
        for more sophisticated decomposition strategies.
        """
        subtasks = []

        # Simple decomposition by splitting description
        description_parts = task.description.split(".")
        for i, part in enumerate(description_parts):
            if part.strip():
                subtask = Task(
                    id=f"{task.id}_sub_{i}",
                    description=part.strip(),
                    complexity=TaskComplexity.SIMPLE,
                    constraints=task.constraints,
                    priority=task.priority,
                )
                subtasks.append(subtask)

        return subtasks

    def combine_subtask_results(
        self, original_task: Task, subtask_results: list[TaskResult]
    ) -> TaskResult:
        """Combine results from subtasks into a final result"""
        # Basic implementation - can be overridden by subclasses
        all_successful = all(result.success for result in subtask_results)

        if all_successful:
            combined_result = "\n".join(
                [
                    str(result.result)
                    for result in subtask_results
                    if result.result is not None
                ]
            )
        else:
            combined_result = "Some subtasks failed"

        return TaskResult(
            task_id=original_task.id,
            success=all_successful,
            result=combined_result,
            tokens_used=sum(result.tokens_used for result in subtask_results),
        )

    def estimate_tokens_for_task(self, task: Task) -> int:
        """Estimate token usage for a task"""
        if task.estimated_tokens:
            return task.estimated_tokens

        # Use token tracker estimation
        complexity_value = self.get_complexity_value(task.complexity)
        return self.token_tracker.estimate_tokens_for_task(
            task.description, complexity_value
        )

    def get_complexity_value(self, complexity: TaskComplexity) -> float:
        """Convert complexity enum to numeric value"""
        complexity_map = {
            TaskComplexity.SIMPLE: 0.2,
            TaskComplexity.MEDIUM: 0.5,
            TaskComplexity.COMPLEX: 0.8,
            TaskComplexity.VERY_COMPLEX: 1.0,
        }
        return complexity_map.get(complexity, 0.5)

    def get_current_time(self) -> float:
        """Get current time (can be overridden for testing)"""
        import time

        return time.time()

    def get_performance_stats(self) -> dict[str, Any]:
        """Get performance statistics for this agent"""
        stats = self.token_tracker.get_agent_stats(self.agent_id)
        efficiency = self.token_tracker.get_efficiency_score(self.agent_id)
        recommendations = self.token_tracker.get_optimization_recommendations(
            self.agent_id
        )

        return {
            "agent_id": self.agent_id,
            "token_budget": self.token_budget,
            "tokens_used": stats.total_tokens,
            "success_rate": stats.successful_tasks
            / max(stats.successful_tasks + stats.failed_tasks, 1),
            "average_tokens_per_task": stats.average_tokens_per_task,
            "efficiency_score": efficiency,
            "active_tasks": len(self.active_tasks),
            "queued_tasks": len(self.task_queue),
            "recommendations": recommendations,
        }

    def adjust_token_budget(self, new_budget: int):
        """Adjust token budget for this agent"""
        self.token_budget = new_budget
        self.token_tracker.set_budget(self.agent_id, new_budget)
        self.max_tokens_per_task = new_budget // 2
        logger.info(f"Adjusted token budget for {self.agent_id} to {new_budget}")

    def queue_task(self, task: Task):
        """Queue a task for later execution"""
        self.task_queue.append(task)
        logger.info(f"Queued task {task.id} for agent {self.agent_id}")

    def get_next_queued_task(self) -> Task | None:
        """Get the next task from the queue"""
        if self.task_queue:
            return self.task_queue.pop(0)
        return None

    def clear_queue(self):
        """Clear the task queue"""
        cleared_count = len(self.task_queue)
        self.task_queue.clear()
        logger.info(f"Cleared {cleared_count} tasks from queue for {self.agent_id}")
        return cleared_count
