"""
Prompt Injection for the Autonomous Agent Learning Loop.

Provides a simple function to get learning context for agent prompts.
Called from agent system prompt construction in planner/coder/QA agents.

Always fails gracefully — returns empty string on any error.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def get_learning_context(
    project_dir: str | Path,
    phase: str,
    task_context: dict | None = None,
) -> str:
    """Get learning-based prompt augmentation for the given agent phase.

    This function is designed to be called from agent prompt builders.
    It always returns a string (empty on error) and never raises.

    Args:
        project_dir: Path to the project directory
        phase: Agent phase (planning, coding, qa_review, qa_fixing)
        task_context: Optional task context with tags for relevance filtering

    Returns:
        Formatted markdown string to append to agent prompts, or empty string.
    """
    try:
        from .service import LearningLoopService

        service = LearningLoopService(Path(project_dir))
        return service.get_prompt_augmentation(phase, task_context=task_context)
    except Exception as e:
        logger.debug(f"Learning context unavailable: {e}")
        return ""
