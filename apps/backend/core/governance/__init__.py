"""
Policy-as-Code Governance Engine
=================================

Provides enforceable policy rules for AI agents via a `workpilot.policy.yaml`
file placed at the project root.

Modules:
    - policy_loader: load & validate YAML policy files
    - policy_engine: evaluate agent actions against loaded rules
    - semantic_analyzer: AST-level diff analysis for semantic violations
    - approval_gate: suspend actions pending human approval
"""

from .approval_gate import ApprovalGate, ApprovalRequest, ApprovalStatus
from .policy_engine import PolicyEngine, PolicyEvaluation, PolicyVerdict
from .policy_loader import PolicyFile, PolicyLoader, PolicyRule, PolicyValidationError
from .semantic_analyzer import SemanticAnalyzer, SemanticViolation

__all__ = [
    # Engine
    "PolicyEngine",
    "PolicyEvaluation",
    "PolicyVerdict",
    # Loader
    "PolicyLoader",
    "PolicyRule",
    "PolicyFile",
    "PolicyValidationError",
    # Semantic
    "SemanticAnalyzer",
    "SemanticViolation",
    # Approval
    "ApprovalGate",
    "ApprovalRequest",
    "ApprovalStatus",
]
