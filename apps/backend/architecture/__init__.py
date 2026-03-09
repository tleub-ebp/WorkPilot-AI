"""
Architecture Enforcement Package
==================================

Automatic architecture guardian that detects and blocks architectural
violations before they reach the codebase. Integrates into the QA
pipeline as a pre-merge validation gate.

Two modes:
  1. Deterministic rules engine (fast) — static import analysis,
     cycle detection, layer violations, forbidden imports
  2. AI-powered review (optional) — Claude reviews git diff for
     subtle violations (bounded context leaks, pattern violations)

Usage:
    from architecture import run_architecture_validation
    passed, report = await run_architecture_validation(project_dir, spec_dir, model)

    # Or use the rules engine directly:
    from architecture import ArchitectureRulesEngine, load_architecture_config
    config = load_architecture_config(project_dir)
    engine = ArchitectureRulesEngine(project_dir, config)
    report = engine.validate(changed_files=["src/foo.py"])
"""

from .config import (
    ArchitectureConfig,
    infer_architecture_config,
    load_architecture_config,
)
from .models import (
    ArchitectureReport,
    ArchitectureViolation,
    ImportGraph,
)
from .rules_engine import ArchitectureRulesEngine
from .validator import run_architecture_validation

__all__ = [
    # Main entry point
    "run_architecture_validation",
    # Rules engine
    "ArchitectureRulesEngine",
    # Configuration
    "ArchitectureConfig",
    "load_architecture_config",
    "infer_architecture_config",
    # Models
    "ArchitectureReport",
    "ArchitectureViolation",
    "ImportGraph",
]
