"""Domain-Specific Agent Factory.

Generates a domain-aware bundle of (prompt fragment + skills + validators)
that can be injected into the existing agents (`agents/coder.py`,
`agents/planner.py`, `qa/reviewer.py`). The base agent stays generic;
the factory is the "what does this domain require?" layer.

Example:

    factory = DomainAgentFactory()
    bundle = factory.build(domain="fintech", role="coder")
    # bundle.prompt_addendum  → industry-specific guardrails
    # bundle.required_skills  → ["audit-trail", "double-entry"]
    # bundle.guardrails       → ["never log raw card numbers", ...]
    # bundle.validation_rules → checks the QA reviewer must run
"""

from .factory import (
    AgentRole,
    DomainAgentBundle,
    DomainAgentFactory,
    DomainProfile,
    DomainTag,
)

__all__ = [
    "AgentRole",
    "DomainAgentBundle",
    "DomainAgentFactory",
    "DomainProfile",
    "DomainTag",
]
