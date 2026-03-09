"""
QA Validation Package
=====================

Modular QA validation system with:
- Acceptance criteria validation
- Issue tracking and reporting
- Recurring issue detection
- QA reviewer and fixer agents
- Main orchestration loop
- Auto-fix loops for intelligent test fixing

Usage:
    from qa import run_qa_validation_loop, should_run_qa, is_qa_approved
    from qa import run_auto_fix_loop  # For auto-fix mode

Module structure:
    - loop.py: Main QA orchestration loop
    - reviewer.py: QA reviewer agent session
    - fixer.py: QA fixer agent session
    - report.py: Issue tracking, reporting, escalation
    - criteria.py: Acceptance criteria and status management
    - auto_fix_loop.py: Intelligent auto-fix loops
"""

# Auto-fix loop
from .auto_fix_loop import (
    DEFAULT_MAX_AUTO_FIX_ATTEMPTS,
    AutoFixLoop,
    run_auto_fix_loop,
)

# Configuration constants
# Criteria & status
from .criteria import (
    get_architecture_status,
    get_qa_iteration_count,
    get_qa_signoff_status,
    is_architecture_approved,
    is_fixes_applied,
    is_qa_approved,
    is_qa_rejected,
    load_implementation_plan,
    print_qa_status,
    save_implementation_plan,
    should_run_fixes,
    should_run_qa,
)
from .fixer import (
    load_qa_fixer_prompt,
    run_qa_fixer_session,
)

# Main loop
from .loop import MAX_QA_ITERATIONS, run_qa_validation_loop

# Report & tracking
from .report import (
    ISSUE_SIMILARITY_THRESHOLD,
    RECURRING_ISSUE_THRESHOLD,
    _issue_similarity,
    # Private functions exposed for testing
    _normalize_issue_key,
    check_test_discovery,
    create_manual_test_plan,
    escalate_to_human,
    get_iteration_history,
    get_recurring_issue_summary,
    has_recurring_issues,
    is_no_test_project,
    record_iteration,
)

# Agent sessions
from .reviewer import run_qa_agent_session

# Public API
__all__ = [
    # Configuration
    "MAX_QA_ITERATIONS",
    "RECURRING_ISSUE_THRESHOLD",
    "ISSUE_SIMILARITY_THRESHOLD",
    "DEFAULT_MAX_AUTO_FIX_ATTEMPTS",
    # Main loop
    "run_qa_validation_loop",
    # Auto-fix loop
    "run_auto_fix_loop",
    "AutoFixLoop",
    # Criteria & status
    "load_implementation_plan",
    "save_implementation_plan",
    "get_qa_signoff_status",
    "is_qa_approved",
    "is_qa_rejected",
    "is_fixes_applied",
    "get_qa_iteration_count",
    "should_run_qa",
    "should_run_fixes",
    "print_qa_status",
    # Architecture enforcement
    "get_architecture_status",
    "is_architecture_approved",
    # Report & tracking
    "get_iteration_history",
    "record_iteration",
    "has_recurring_issues",
    "get_recurring_issue_summary",
    "escalate_to_human",
    "create_manual_test_plan",
    "check_test_discovery",
    "is_no_test_project",
    "_normalize_issue_key",
    "_issue_similarity",
    # Agent sessions
    "run_qa_agent_session",
    "load_qa_fixer_prompt",
    "run_qa_fixer_session",
]
