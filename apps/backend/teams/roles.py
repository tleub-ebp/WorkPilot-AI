"""
Claude Teams - Agent Roles
============================

Role definitions, weights, and veto rights for team agents.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List


class AgentRole(str, Enum):
    ARCHITECT = "architect"
    DEVELOPER = "developer"
    SECURITY = "security"
    QA = "qa"
    PRODUCT = "product"
    DATA = "data"


@dataclass
class RoleDefinition:
    role: AgentRole
    name: str
    description: str
    decision_weight: int
    can_veto: bool
    focus_areas: List[str]


_ROLE_DEFINITIONS: dict[AgentRole, RoleDefinition] = {
    AgentRole.ARCHITECT: RoleDefinition(
        role=AgentRole.ARCHITECT,
        name="System Architect",
        description="Designs system architecture and ensures technical coherence",
        decision_weight=5,
        can_veto=True,
        focus_areas=["architecture", "scalability", "patterns", "integration"],
    ),
    AgentRole.DEVELOPER: RoleDefinition(
        role=AgentRole.DEVELOPER,
        name="Senior Developer",
        description="Implements features with focus on code quality",
        decision_weight=3,
        can_veto=False,
        focus_areas=["implementation", "code_quality", "maintainability"],
    ),
    AgentRole.SECURITY: RoleDefinition(
        role=AgentRole.SECURITY,
        name="Security Engineer",
        description="Ensures security best practices and identifies vulnerabilities",
        decision_weight=5,
        can_veto=True,
        focus_areas=["security", "vulnerabilities", "auth", "data_protection"],
    ),
    AgentRole.QA: RoleDefinition(
        role=AgentRole.QA,
        name="QA Engineer",
        description="Validates quality, testability, and edge cases",
        decision_weight=3,
        can_veto=False,
        focus_areas=["testing", "edge_cases", "reliability", "coverage"],
    ),
    AgentRole.PRODUCT: RoleDefinition(
        role=AgentRole.PRODUCT,
        name="Product Manager",
        description="Ensures alignment with product vision and user needs",
        decision_weight=4,
        can_veto=False,
        focus_areas=["requirements", "user_experience", "priorities"],
    ),
    AgentRole.DATA: RoleDefinition(
        role=AgentRole.DATA,
        name="Data Engineer",
        description="Designs data models and ensures data integrity",
        decision_weight=3,
        can_veto=False,
        focus_areas=["data_models", "migrations", "performance", "integrity"],
    ),
}


def get_role_definition(role: AgentRole) -> RoleDefinition:
    return _ROLE_DEFINITIONS[role]


def get_active_roles(role_names: List[str]) -> List[RoleDefinition]:
    result = []
    for name in role_names:
        try:
            role = AgentRole(name)
            result.append(_ROLE_DEFINITIONS[role])
        except ValueError:
            pass
    return result
