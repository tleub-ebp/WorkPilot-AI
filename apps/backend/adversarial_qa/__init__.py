"""
Adversarial QA Agent — Red team automatique.

A dedicated agent to "break" what other agents produce by generating
malformed inputs, edge cases, prompt injection attacks, and concurrency
stress tests.

Modules:
    - fuzzer: generate malformed/boundary inputs
    - edge_case_generator: systematic edge case enumeration
    - injection_tester: prompt injection and XSS attack vectors
    - concurrency_analyzer: detect race conditions and deadlocks
    - adversarial_agent: orchestrate all attack modes and produce reports
"""

from .adversarial_agent import (
    AdversarialAgent,
    AdversarialConfig,
    AdversarialReport,
    AttackMode,
    Finding,
    FindingSeverity,
)
from .concurrency_analyzer import ConcurrencyAnalyzer, ConcurrencyFinding, RaceCondition
from .edge_case_generator import EdgeCase, EdgeCaseGenerator, EdgeCaseCategory
from .fuzzer import FuzzResult, Fuzzer, FuzzStrategy
from .injection_tester import InjectionResult, InjectionTester, InjectionType

__all__ = [
    "AdversarialAgent",
    "AdversarialConfig",
    "AdversarialReport",
    "AttackMode",
    "Finding",
    "FindingSeverity",
    "Fuzzer",
    "FuzzResult",
    "FuzzStrategy",
    "EdgeCaseGenerator",
    "EdgeCase",
    "EdgeCaseCategory",
    "InjectionTester",
    "InjectionResult",
    "InjectionType",
    "ConcurrencyAnalyzer",
    "ConcurrencyFinding",
    "RaceCondition",
]
