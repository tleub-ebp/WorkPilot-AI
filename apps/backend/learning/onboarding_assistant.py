"""
Onboarding Assistant - Help new developers get started

This module provides an interactive onboarding experience for new team members.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime


class OnboardingStep(str, Enum):
    """Steps in the onboarding process"""
    
    WELCOME = "welcome"
    PROJECT_OVERVIEW = "project_overview"
    SETUP_ENVIRONMENT = "setup_environment"
    FIRST_TASK = "first_task"
    CODE_REVIEW = "code_review"
    DEPLOYMENT = "deployment"
    RESOURCES = "resources"


@dataclass
class OnboardingProgress:
    """Track onboarding progress"""
    
    developer_name: str
    start_date: datetime
    current_step: OnboardingStep
    completed_steps: List[OnboardingStep] = field(default_factory=list)
    notes: Dict[str, str] = field(default_factory=dict)
    estimated_completion_date: Optional[datetime] = None


@dataclass
class OnboardingResource:
    """A resource for onboarding"""
    
    title: str
    description: str
    url: Optional[str] = None
    resource_type: str = "documentation"  # "documentation", "video", "tutorial", "code"
    estimated_time_minutes: int = 30


class OnboardingAssistant:
    """Interactive onboarding assistant for new developers"""
    
    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.progress: Dict[str, OnboardingProgress] = {}
    
    async def start_onboarding(
        self,
        developer_name: str,
        experience_level: str = "intermediate"
    ) -> OnboardingProgress:
        """Start onboarding for a new developer"""
        progress = OnboardingProgress(
            developer_name=developer_name,
            start_date=datetime.now(),
            current_step=OnboardingStep.WELCOME
        )
        self.progress[developer_name] = progress
        return progress
    
    async def get_next_step(
        self,
        developer_name: str
    ) -> Optional[Dict[str, Any]]:
        """Get the next onboarding step"""
        if developer_name not in self.progress:
            return None
        
        progress = self.progress[developer_name]
        return {
            "step": progress.current_step.value,
            "completed": progress.completed_steps,
            "progress_percent": len(progress.completed_steps) / len(OnboardingStep) * 100
        }
    
    async def complete_step(
        self,
        developer_name: str,
        step: OnboardingStep,
        notes: Optional[str] = None
    ) -> bool:
        """Mark a step as completed"""
        if developer_name not in self.progress:
            return False
        
        progress = self.progress[developer_name]
        if step not in progress.completed_steps:
            progress.completed_steps.append(step)
        
        if notes:
            progress.notes[step.value] = notes
        
        return True
    
    async def generate_onboarding_checklist(
        self,
        experience_level: str = "intermediate"
    ) -> List[Dict[str, Any]]:
        """Generate a personalized onboarding checklist"""
        checklist = [
            {
                "step": OnboardingStep.WELCOME.value,
                "title": "Welcome to the Team",
                "tasks": ["Meet the team", "Get access to tools", "Read project overview"]
            },
            {
                "step": OnboardingStep.PROJECT_OVERVIEW.value,
                "title": "Understand the Project",
                "tasks": ["Read architecture docs", "Explore codebase", "Review tech stack"]
            },
            {
                "step": OnboardingStep.SETUP_ENVIRONMENT.value,
                "title": "Setup Development Environment",
                "tasks": ["Install dependencies", "Configure IDE", "Run tests"]
            }
        ]
        return checklist

