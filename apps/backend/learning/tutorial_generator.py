"""
Tutorial Generator - Create personalized tutorials

This module generates step-by-step tutorials based on the code being created.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class TutorialTopic(str, Enum):
    """Tutorial topic categories"""

    GETTING_STARTED = "getting_started"
    API_USAGE = "api_usage"
    BEST_PRACTICES = "best_practices"
    ARCHITECTURE = "architecture"
    DEBUGGING = "debugging"
    TESTING = "testing"
    DEPLOYMENT = "deployment"


@dataclass
class TutorialStep:
    """A single step in a tutorial"""

    step_number: int
    title: str
    description: str
    code_example: str | None = None
    explanation: str = ""
    tips: list[str] = field(default_factory=list)
    common_mistakes: list[str] = field(default_factory=list)


@dataclass
class Tutorial:
    """A complete tutorial"""

    topic: TutorialTopic
    title: str
    description: str
    difficulty: str  # "beginner", "intermediate", "advanced"
    estimated_time_minutes: int
    prerequisites: list[str] = field(default_factory=list)
    steps: list[TutorialStep] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)


class TutorialGenerator:
    """Generate personalized tutorials from code"""

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.generated_tutorials: list[Tutorial] = []

    async def generate_tutorial(
        self,
        topic: TutorialTopic,
        code_context: dict[str, Any],
        target_audience: str = "intermediate",
    ) -> Tutorial:
        """Generate a tutorial for a specific topic"""
        tutorial = Tutorial(
            topic=topic,
            title=f"{topic.value.replace('_', ' ').title()} Tutorial",
            description="Learn how to use this feature",
            difficulty=target_audience,
            estimated_time_minutes=30,
        )
        return tutorial

    def add_step(self, tutorial: Tutorial, step: TutorialStep) -> None:
        """Add a step to a tutorial"""
        tutorial.steps.append(step)
