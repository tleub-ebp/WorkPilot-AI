"""
Configuration and constants for the migration system.
"""

from enum import Enum
from typing import Dict, Set, List, Tuple

# Supported migrations configuration
SUPPORTED_MIGRATIONS: Dict[Tuple[str, str], Dict] = {
    # (source_framework, target_framework) -> config
    ("react", "vue"): {
        "complexity": "medium",
        "supported_versions": {
            "react": ["16.0", "17.0", "18.0"],
            "vue": ["2.0", "3.0"],
        },
        "transformers": ["react_to_vue"],
        "data_preservation": True,
        "estimated_effort_hours": 40,
        "breaking_changes": True,
    },
    ("react", "angular"): {
        "complexity": "high",
        "supported_versions": {
            "react": ["16.0", "17.0", "18.0"],
            "angular": ["12.0", "13.0", "14.0", "15.0"],
        },
        "transformers": ["react_to_angular"],
        "data_preservation": True,
        "estimated_effort_hours": 60,
        "breaking_changes": True,
    },
    ("mysql", "postgresql"): {
        "complexity": "medium",
        "supported_versions": {
            "mysql": ["5.7", "8.0"],
            "postgresql": ["12", "13", "14", "15"],
        },
        "transformers": ["database"],
        "data_preservation": True,
        "estimated_effort_hours": 30,
        "breaking_changes": False,
    },
    ("python2", "python3"): {
        "complexity": "medium",
        "supported_versions": {
            "python": ["2.7"],
            "python3": ["3.8", "3.9", "3.10", "3.11"],
        },
        "transformers": ["python"],
        "data_preservation": True,
        "estimated_effort_hours": 20,
        "breaking_changes": True,
    },
    ("rest", "graphql"): {
        "complexity": "high",
        "supported_versions": {
            "rest": ["1.0"],
            "graphql": ["1.0"],
        },
        "transformers": ["rest_to_graphql"],
        "data_preservation": False,
        "estimated_effort_hours": 50,
        "breaking_changes": True,
    },
    ("javascript", "typescript"): {
        "complexity": "low",
        "supported_versions": {
            "javascript": ["es6", "es2015"],
            "typescript": ["4.0", "4.5", "5.0"],
        },
        "transformers": ["js_to_ts"],
        "data_preservation": True,
        "estimated_effort_hours": 15,
        "breaking_changes": False,
    },
    ("javascript", "csharp"): {
        "complexity": "very_high",
        "supported_versions": {
            "javascript": ["es6", "es2015"],
            "csharp": ["8.0", "9.0", "10.0", "11.0"],
            "dotnet": ["5.0", "6.0", "7.0"],
        },
        "transformers": ["js_to_csharp"],
        "data_preservation": True,
        "estimated_effort_hours": 80,
        "breaking_changes": True,
    },
    ("typescript", "csharp"): {
        "complexity": "very_high",
        "supported_versions": {
            "typescript": ["4.0", "4.5", "5.0"],
            "csharp": ["8.0", "9.0", "10.0", "11.0"],
            "dotnet": ["5.0", "6.0", "7.0"],
        },
        "transformers": ["js_to_csharp"],
        "data_preservation": True,
        "estimated_effort_hours": 80,
        "breaking_changes": True,
    },
    ("csharp", "python"): {
        "complexity": "high",
        "supported_versions": {
            "csharp": ["8.0", "9.0", "10.0", "11.0"],
            "dotnet": ["5.0", "6.0", "7.0"],
            "python": ["3.8", "3.9", "3.10", "3.11"],
        },
        "transformers": ["csharp_to_python"],
        "data_preservation": True,
        "estimated_effort_hours": 70,
        "breaking_changes": True,
    },
    ("python", "csharp"): {
        "complexity": "high",
        "supported_versions": {
            "python": ["3.8", "3.9", "3.10", "3.11"],
            "csharp": ["8.0", "9.0", "10.0", "11.0"],
            "dotnet": ["5.0", "6.0", "7.0"],
        },
        "transformers": ["python_to_csharp"],
        "data_preservation": True,
        "estimated_effort_hours": 70,
        "breaking_changes": True,
    },
}

# Risk level thresholds
RISK_ASSESSMENT_THRESHOLDS = {
    "low": {
        "max_affected_files": 50,
        "max_complexity_score": 2.0,
        "breaking_changes": False,
        "data_risk": False,
    },
    "medium": {
        "max_affected_files": 200,
        "max_complexity_score": 5.0,
        "breaking_changes": False,
        "data_risk": False,
    },
    "high": {
        "max_affected_files": 500,
        "max_complexity_score": 8.0,
        "breaking_changes": True,
        "data_risk": False,
    },
    "critical": {
        "max_affected_files": float("inf"),
        "max_complexity_score": float("inf"),
        "breaking_changes": True,
        "data_risk": True,
    },
}

# Phase configuration
MIGRATION_PHASES = [
    {
        "id": "analysis",
        "name": "Analysis",
        "description": "Analyze source code and create migration plan",
        "requires_approval": False,
        "auto_proceed_on_low_risk": True,
    },
    {
        "id": "planning",
        "name": "Planning",
        "description": "Generate detailed step-by-step migration plan",
        "requires_approval": False,
        "auto_proceed_on_low_risk": True,
    },
    {
        "id": "backup",
        "name": "Backup & Checkpoint",
        "description": "Create backup and checkpoint for rollback",
        "requires_approval": False,
        "auto_proceed_on_low_risk": True,
    },
    {
        "id": "transformation",
        "name": "Code Transformation",
        "description": "Apply code transformations",
        "requires_approval": False,
        "auto_proceed_on_low_risk": False,
    },
    {
        "id": "validation",
        "name": "Validation & Testing",
        "description": "Validate transformations and run tests",
        "requires_approval": False,
        "auto_proceed_on_low_risk": False,
    },
    {
        "id": "fixup",
        "name": "Auto-Fix Issues",
        "description": "Automatically fix validation failures",
        "requires_approval": False,
        "auto_proceed_on_low_risk": False,
    },
    {
        "id": "reporting",
        "name": "Report Generation",
        "description": "Generate migration report and documentation",
        "requires_approval": False,
        "auto_proceed_on_low_risk": True,
    },
]

# Timeout configurations (seconds)
TIMEOUTS = {
    "analysis": 300,  # 5 minutes
    "planning": 300,
    "transformation": 1800,  # 30 minutes
    "test_execution": 1200,  # 20 minutes
    "validation": 600,
    "reporting": 300,
}

# Auto-fix configuration
AUTO_FIX_CONFIG = {
    "enabled": True,
    "max_attempts": 3,
    "timeout_per_attempt": 300,
    "escalate_on_failure": True,
    "run_before_validation": True,
}

# Validation configuration
VALIDATION_CONFIG = {
    "run_unit_tests": True,
    "run_integration_tests": True,
    "check_build": True,
    "check_linting": True,
    "check_types": True,  # For TypeScript projects
    "coverage_threshold": 70,  # Percentage
    "regression_threshold": 0.95,  # Allow 5% regression
}

# Transformer selection rules
TRANSFORMER_RULES = {
    "react_to_vue": {
        "file_patterns": [
            "**/*.jsx",
            "**/*.tsx",
        ],
        "transformations": [
            "jsx_to_template",
            "hooks_to_composition_api",
            "state_management",
            "routing",
            "styling",
        ],
    },
    "database": {
        "file_patterns": [
            "**/migrations/**/*.sql",
            "**/schema.sql",
            "**/db/**/*.sql",
        ],
        "transformations": [
            "syntax_conversion",
            "type_mapping",
            "function_mapping",
            "data_types",
        ],
    },
    "python": {
        "file_patterns": [
            "**/*.py",
        ],
        "transformations": [
            "print_function",
            "string_types",
            "imports",
            "division",
            "unicode",
        ],
    },
    "rest_to_graphql": {
        "file_patterns": [
            "**/*.ts",
            "**/*.js",
        ],
        "transformations": [
            "endpoint_to_schema",
            "routes_to_resolvers",
            "query_generation",
        ],
    },
    "js_to_ts": {
        "file_patterns": [
            "**/*.js",
            "**/*.jsx",
        ],
        "transformations": [
            "type_annotations",
            "interface_generation",
            "strict_mode",
        ],
    },
}

# Confidence score thresholds
CONFIDENCE_THRESHOLDS = {
    "very_high": 0.9,
    "high": 0.75,
    "medium": 0.6,
    "low": 0.4,
    "very_low": 0.0,
}

# Approval requirements based on risk
APPROVAL_REQUIREMENTS = {
    "low": [],
    "medium": ["migration_type"],
    "high": ["migration_type", "data_impact"],
    "critical": ["migration_type", "data_impact", "security", "performance"],
}

# CLI Configuration
CLI_CONFIG = {
    "interactive_mode": True,
    "show_diffs": True,
    "auto_confirm_low_risk": False,
    "save_state": True,
    "state_dir": ".auto-claude/migration",
    "enable_rollback": True,
}

# Prompts configuration
PROMPTS_DIR = "apps/backend/migration/prompts"
PROMPT_TEMPLATES = {
    "analyzer": "analyzer.md",
    "planner": "planner.md",
    "transformer": "transformer.md",
    "validator": "validator.md",
}

# Feature flags
FEATURE_FLAGS = {
    "enable_parallel_transformation": False,  # Enable in later phase
    "enable_data_migration": False,  # Enable in later phase
    "enable_custom_transformers": False,
    "enable_teams_collaboration": True,
    "enable_auto_fix": True,
    "enable_incremental_rollback": True,
}
