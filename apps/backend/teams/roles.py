"""
Agent Role Definitions
======================

Defines specialized agent roles with distinct personalities,
expertise areas, and decision-making weights.
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class AgentRole(str, Enum):
    """Available agent roles in Claude Teams."""

    ARCHITECT = "architect"
    DEVELOPER = "developer"
    SECURITY = "security"
    QA_ENGINEER = "qa_engineer"
    DEVOPS = "devops"
    PERFORMANCE = "performance"
    UX = "ux"


@dataclass
class RoleDefinition:
    """Definition of an agent role with personality and capabilities."""

    role: AgentRole
    name: str
    description: str
    prompt_file: str
    personality: str
    expertise_areas: list[str]
    decision_weight: int  # 1-5, higher = more influence in votes
    can_veto: bool
    tools: list[str]

    def get_full_prompt(self, base_prompt_dir: Path) -> str:
        """Load the full prompt for this role."""
        prompt_path = base_prompt_dir / "teams" / self.prompt_file
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
        return prompt_path.read_text(encoding="utf-8")


# Role Definitions with Personalities
ROLE_DEFINITIONS: dict[AgentRole, RoleDefinition] = {
    AgentRole.ARCHITECT: RoleDefinition(
        role=AgentRole.ARCHITECT,
        name="System Architect",
        description="Designs system architecture and makes high-level technical decisions",
        prompt_file="architect_agent.md",
        personality=(
            "Visionary but pragmatic. Thinks long-term but considers "
            "implementation constraints. Balances elegance with practicality."
        ),
        expertise_areas=[
            "System design",
            "Design patterns",
            "Scalability",
            "Technology selection",
            "API design",
            "Database schema",
        ],
        decision_weight=5,
        can_veto=True,  # Can block bad architectural decisions
        tools=["Read", "Grep", "Glob", "Bash"],
    ),
    AgentRole.DEVELOPER: RoleDefinition(
        role=AgentRole.DEVELOPER,
        name="Senior Developer",
        description="Implements features and provides implementation perspective",
        prompt_file="developer_agent.md",
        personality=(
            "Pragmatic and efficiency-focused. Prefers simple solutions. "
            "Questions over-engineering. Optimizes for maintainability and speed."
        ),
        expertise_areas=[
            "Implementation details",
            "Code quality",
            "Refactoring",
            "Debugging",
            "Testing",
            "Performance optimization",
        ],
        decision_weight=3,
        can_veto=False,
        tools=["Read", "Write", "Grep", "Glob", "Bash"],
    ),
    AgentRole.SECURITY: RoleDefinition(
        role=AgentRole.SECURITY,
        name="Security Engineer",
        description="Ensures security best practices and identifies vulnerabilities",
        prompt_file="security_agent.md",
        personality=(
            "Paranoid by design (it's the job). Zero-trust mindset. "
            "Always asks 'what could go wrong?'. Non-negotiable on critical issues."
        ),
        expertise_areas=[
            "OWASP Top 10",
            "Authentication/Authorization",
            "Input validation",
            "Encryption",
            "Secret management",
            "Compliance",
        ],
        decision_weight=5,
        can_veto=True,  # Can block security vulnerabilities
        tools=["Read", "Grep", "Glob", "Bash"],
    ),
    AgentRole.QA_ENGINEER: RoleDefinition(
        role=AgentRole.QA_ENGINEER,
        name="QA Engineer",
        description="Ensures quality, testability, and catches edge cases",
        prompt_file="qa_engineer_agent.md",
        personality=(
            "Perfectionist and detail-oriented. Thinks in edge cases. "
            "Always asks 'what if...?'. Champions testability and observability."
        ),
        expertise_areas=[
            "Test coverage",
            "Edge cases",
            "Error handling",
            "Integration testing",
            "Test automation",
            "Quality metrics",
        ],
        decision_weight=3,
        can_veto=False,
        tools=["Read", "Grep", "Glob", "Bash"],
    ),
    AgentRole.DEVOPS: RoleDefinition(
        role=AgentRole.DEVOPS,
        name="DevOps Engineer",
        description="Handles deployment, infrastructure, and operational concerns",
        prompt_file="devops_agent.md",
        personality=(
            "Operations-focused. Thinks about production implications. "
            "Champions observability, monitoring, and disaster recovery."
        ),
        expertise_areas=[
            "CI/CD",
            "Infrastructure as Code",
            "Monitoring/Logging",
            "Deployment strategies",
            "Containerization",
            "Cloud platforms",
        ],
        decision_weight=2,
        can_veto=False,
        tools=["Read", "Grep", "Glob", "Bash"],
    ),
    AgentRole.PERFORMANCE: RoleDefinition(
        role=AgentRole.PERFORMANCE,
        name="Performance Engineer",
        description="Optimizes for speed, efficiency, and resource usage",
        prompt_file="performance_agent.md",
        personality=(
            "Data-driven and metrics-obsessed. Always benchmarking. "
            "Questions premature optimization but catches real bottlenecks."
        ),
        expertise_areas=[
            "Profiling",
            "Caching strategies",
            "Database optimization",
            "Load testing",
            "Resource management",
            "Scalability",
        ],
        decision_weight=2,
        can_veto=False,
        tools=["Read", "Grep", "Glob", "Bash"],
    ),
    AgentRole.UX: RoleDefinition(
        role=AgentRole.UX,
        name="UX Specialist",
        description="Ensures user experience and accessibility",
        prompt_file="ux_agent.md",
        personality=(
            "User-centric and empathetic. Thinks about user journeys. "
            "Champions accessibility and simplicity."
        ),
        expertise_areas=[
            "User flows",
            "Accessibility (WCAG)",
            "Error messages",
            "API usability",
            "Documentation",
            "Design consistency",
        ],
        decision_weight=2,
        can_veto=False,
        tools=["Read", "Grep", "Glob"],
    ),
}


def get_role_definition(role: AgentRole) -> RoleDefinition:
    """Get the definition for a specific role."""
    return ROLE_DEFINITIONS[role]


def get_active_roles(role_names: list[str]) -> list[RoleDefinition]:
    """Get role definitions for a list of role names."""
    return [
        ROLE_DEFINITIONS[AgentRole(name)]
        for name in role_names
        if name in [r.value for r in AgentRole]
    ]

