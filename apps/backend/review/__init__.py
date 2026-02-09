"""
Human Review Checkpoint System
==============================

Provides a mandatory human review checkpoint between spec creation (spec_runner.py)
and build execution (run.py). Users can review the spec.md and implementation_plan.json,
provide feedback, request changes, or explicitly approve before any code is written.

Public API:
    - ReviewState: State management class
    - run_review_checkpoint: Main interactive review function
    - get_review_status_summary: Get review status summary
    - display_spec_summary: Display spec overview
    - display_plan_summary: Display implementation plan
    - display_review_status: Display current review status
    - open_file_in_editor: Open file in user's editor
    - ReviewChoice: Enum of review actions

Usage:
    from review import ReviewState, run_review_checkpoint

    state = ReviewState.load(spec_dir)
    if not state.is_approved():
        state = run_review_checkpoint(spec_dir)
"""

from .diff_analyzer import (
    extract_checkboxes,
    extract_section,
    extract_table_rows,
    extract_title,
    truncate_text,
)
from .formatters import (
    display_plan_summary,
    display_review_status,
    display_spec_summary,
)
from .reviewer import (
    ReviewChoice,
    get_review_menu_options,
    open_file_in_editor,
    prompt_feedback,
    run_review_checkpoint,
)
from .state import (
    REVIEW_STATE_FILE,
    ReviewState,
    _compute_file_hash,
    _compute_spec_hash,
    get_review_status_summary,
)

try:
    from .quality_autofix import AutoFixEngine, AutoFix
    from .quality_badge import QualityBadgeFormatter
    from .quality_coverage import TestCoverageAnalyzer, analyze_project_coverage
    from .quality_custom_rules import CustomRuleEngine, CustomRule, load_project_rules
    from .quality_extended import ExtendedQualityScorer, create_extended_scorer
    from .quality_integration import (
        QualityReviewIntegration,
        display_quality_report,
        review_current_pr,
    )
    from .quality_ml import MLPatternDetector, LearnedPattern, learn_and_detect
    from .quality_multilang import (
        CSharpAnalyzer,
        GoAnalyzer,
        JavaAnalyzer,
        KotlinAnalyzer,
        RustAnalyzer,
        get_analyzer,
    )
    from .quality_performance import PerformanceAnalyzer, analyze_project_performance
    from .quality_similarity import CodeClone, CodeSimilarityDetector, detect_clones_in_project
except ImportError:
    # Quality scoring module not yet available
    QualityScorer = None
    QualityScore = None
    QualityIssue = None
    QualityCategory = None
    IssueSeverity = None
    QualityBadgeFormatter = None
    QualityReviewIntegration = None
    review_current_pr = None
    display_quality_report = None
    ExtendedQualityScorer = None
    create_extended_scorer = None
    AutoFixEngine = None
    AutoFix = None
    JavaAnalyzer = None
    KotlinAnalyzer = None
    CSharpAnalyzer = None
    GoAnalyzer = None
    RustAnalyzer = None
    get_analyzer = None
    CodeSimilarityDetector = None
    CodeClone = None
    detect_clones_in_project = None
    CustomRuleEngine = None
    CustomRule = None
    load_project_rules = None
    PerformanceAnalyzer = None
    analyze_project_performance = None

# Aliases for underscore-prefixed names used in tests
_extract_section = extract_section
_truncate_text = truncate_text

__all__ = [
    # State
    "ReviewState",
    "get_review_status_summary",
    "REVIEW_STATE_FILE",
    "_compute_file_hash",
    "_compute_spec_hash",
    # Formatters
    "display_spec_summary",
    "display_plan_summary",
    "display_review_status",
    # Reviewer
    "ReviewChoice",
    "run_review_checkpoint",
    "open_file_in_editor",
    "get_review_menu_options",
    "prompt_feedback",
    # Diff analyzer (utility)
    "extract_section",
    "extract_table_rows",
    "truncate_text",
    "extract_title",
    "extract_checkboxes",
    # Aliases for tests
    "_extract_section",
    "_truncate_text",
    # Quality scoring exports
    "QualityScorer",
    "QualityScore",
    "QualityIssue",
    "QualityCategory",
    "IssueSeverity",
    "QualityBadgeFormatter",
    "QualityReviewIntegration",
    "review_current_pr",
    "display_quality_report",
    "ExtendedQualityScorer",
    "create_extended_scorer",
    "AutoFixEngine",
    "AutoFix",
    "JavaAnalyzer",
    "KotlinAnalyzer",
    "CSharpAnalyzer",
    "GoAnalyzer",
    "RustAnalyzer",
    # Phase 4 - Future Features
    "CodeSimilarityDetector",
    "CodeClone",
    "detect_clones_in_project",
    "CustomRuleEngine",
    "CustomRule",
    "load_project_rules",
    "PerformanceAnalyzer",
    "analyze_project_performance",
    # Phase 5 - Advanced ML & Coverage
    "MLPatternDetector",
    "LearnedPattern",
    "learn_and_detect",
    "TestCoverageAnalyzer",
    "analyze_project_coverage",
]
