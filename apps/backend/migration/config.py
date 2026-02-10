"""
Configuration and constants for the migration system.
"""

from typing import Dict, Tuple

# Supported migrations configuration
SUPPORTED_MIGRATIONS: Dict[Tuple[str, str], Dict] = {

    # =========================
    # Frontend Frameworks
    # =========================
    ("react", "vue"): {
        "complexity": "medium",
        "supported_versions": {
            "react": ["17.0", "18.2"],
            "vue": ["3.3", "3.4"],
        },
        "transformers": ["react_to_vue"],
        "data_preservation": True,
        "estimated_effort_hours": 40,
        "breaking_changes": True,
    },
    ("vue", "react"): {
        "complexity": "medium",
        "supported_versions": {
            "vue": ["3.3", "3.4"],
            "react": ["17.0", "18.2"],
        },
        "transformers": ["vue_to_react"],
        "data_preservation": True,
        "estimated_effort_hours": 40,
        "breaking_changes": True,
    },
    ("react", "angular"): {
        "complexity": "high",
        "supported_versions": {
            "react": ["17.0", "18.2"],
            "angular": ["16", "17"],
        },
        "transformers": ["react_to_angular"],
        "data_preservation": True,
        "estimated_effort_hours": 60,
        "breaking_changes": True,
    },
    ("angular", "react"): {
        "complexity": "high",
        "supported_versions": {
            "angular": ["16", "17"],
            "react": ["17.0", "18.2"],
        },
        "transformers": ["angular_to_react"],
        "data_preservation": True,
        "estimated_effort_hours": 60,
        "breaking_changes": True,
    },
    ("react", "svelte"): {
        "complexity": "medium",
        "supported_versions": {
            "react": ["17.0", "18.2"],
            "svelte": ["4"],
        },
        "transformers": ["react_to_svelte"],
        "data_preservation": True,
        "estimated_effort_hours": 35,
        "breaking_changes": True,
    },
    ("svelte", "react"): {
        "complexity": "medium",
        "supported_versions": {
            "svelte": ["4"],
            "react": ["17.0", "18.2"],
        },
        "transformers": ["svelte_to_react"],
        "data_preservation": True,
        "estimated_effort_hours": 35,
        "breaking_changes": True,
    },

    # =========================
    # Databases
    # =========================
    ("mysql", "postgresql"): {
        "complexity": "medium",
        "supported_versions": {
            "mysql": ["8.0"],
            "postgresql": ["14", "15", "16"],
        },
        "transformers": ["database"],
        "data_preservation": True,
        "estimated_effort_hours": 30,
        "breaking_changes": False,
    },
    ("postgresql", "mysql"): {
        "complexity": "medium",
        "supported_versions": {
            "postgresql": ["14", "15", "16"],
            "mysql": ["8.0"],
        },
        "transformers": ["database"],
        "data_preservation": True,
        "estimated_effort_hours": 30,
        "breaking_changes": True,
    },
    ("postgresql", "mongodb"): {
        "complexity": "high",
        "supported_versions": {
            "postgresql": ["14", "15", "16"],
            "mongodb": ["6.0", "7.0"],
        },
        "transformers": ["sql_to_nosql"],
        "data_preservation": True,
        "estimated_effort_hours": 50,
        "breaking_changes": True,
    },
    ("sqlite", "postgresql"): {
        "complexity": "low",
        "supported_versions": {
            "sqlite": ["3"],
            "postgresql": ["14", "15", "16"],
        },
        "transformers": ["database"],
        "data_preservation": True,
        "estimated_effort_hours": 15,
        "breaking_changes": False,
    },

    # =========================
    # Languages
    # =========================
    ("python2", "python3"): {
        "complexity": "medium",
        "supported_versions": {
            "python": ["2.7"],
            "python3": ["3.9", "3.10", "3.11", "3.12"],
        },
        "transformers": ["python"],
        "data_preservation": True,
        "estimated_effort_hours": 20,
        "breaking_changes": True,
    },
    ("javascript", "typescript"): {
        "complexity": "low",
        "supported_versions": {
            "javascript": ["es2018", "es2020"],
            "typescript": ["4.9", "5.0", "5.3"],
        },
        "transformers": ["js_to_ts"],
        "data_preservation": True,
        "estimated_effort_hours": 15,
        "breaking_changes": False,
    },
    ("typescript", "javascript"): {
        "complexity": "low",
        "supported_versions": {
            "typescript": ["4.9", "5.0", "5.3"],
            "javascript": ["es2018", "es2020"],
        },
        "transformers": ["ts_to_js"],
        "data_preservation": True,
        "estimated_effort_hours": 10,
        "breaking_changes": False,
    },
    ("java", "kotlin"): {
        "complexity": "medium",
        "supported_versions": {
            "java": ["11", "17", "21"],
            "kotlin": ["1.8", "1.9"],
        },
        "transformers": ["java_to_kotlin"],
        "data_preservation": True,
        "estimated_effort_hours": 30,
        "breaking_changes": False,
    },
    ("kotlin", "java"): {
        "complexity": "medium",
        "supported_versions": {
            "kotlin": ["1.8", "1.9"],
            "java": ["11", "17", "21"],
        },
        "transformers": ["kotlin_to_java"],
        "data_preservation": True,
        "estimated_effort_hours": 35,
        "breaking_changes": False,
    },
    ("python", "go"): {
        "complexity": "high",
        "supported_versions": {
            "python": ["3.9", "3.10", "3.11", "3.12"],
            "go": ["1.21", "1.22"],
        },
        "transformers": ["python_to_go"],
        "data_preservation": True,
        "estimated_effort_hours": 80,
        "breaking_changes": True,
    },

    # =========================
    # API Styles
    # =========================
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
    ("graphql", "rest"): {
        "complexity": "high",
        "supported_versions": {
            "graphql": ["1.0"],
            "rest": ["1.0"],
        },
        "transformers": ["graphql_to_rest"],
        "data_preservation": False,
        "estimated_effort_hours": 50,
        "breaking_changes": True,
    },

    # =========================
    # Backend Frameworks
    # =========================
    ("express", "fastify"): {
        "complexity": "medium",
        "supported_versions": {
            "express": ["4.18"],
            "fastify": ["4"],
        },
        "transformers": ["express_to_fastify"],
        "data_preservation": True,
        "estimated_effort_hours": 25,
        "breaking_changes": False,
    },
    ("django", "fastapi"): {
        "complexity": "high",
        "supported_versions": {
            "django": ["4.2", "5.0"],
            "fastapi": ["0.104", "0.110"],
        },
        "transformers": ["django_to_fastapi"],
        "data_preservation": True,
        "estimated_effort_hours": 65,
        "breaking_changes": True,
    },
    ("flask", "fastapi"): {
        "complexity": "medium",
        "supported_versions": {
            "flask": ["2.3"],
            "fastapi": ["0.104", "0.110"],
        },
        "transformers": ["flask_to_fastapi"],
        "data_preservation": True,
        "estimated_effort_hours": 35,
        "breaking_changes": False,
    },

    # =========================
    # Build Tools
    # =========================
    ("webpack", "vite"): {
        "complexity": "medium",
        "supported_versions": {
            "webpack": ["5"],
            "vite": ["4", "5"],
        },
        "transformers": ["webpack_to_vite"],
        "data_preservation": True,
        "estimated_effort_hours": 20,
        "breaking_changes": False,
    },

    # =========================
    # Testing
    # =========================
    ("jest", "vitest"): {
        "complexity": "low",
        "supported_versions": {
            "jest": ["29"],
            "vitest": ["0.34", "1.0"],
        },
        "transformers": ["jest_to_vitest"],
        "data_preservation": True,
        "estimated_effort_hours": 12,
        "breaking_changes": False,
    },
    ("unittest", "pytest"): {
        "complexity": "medium",
        "supported_versions": {
            "unittest": ["3.9"],
            "pytest": ["7", "8"],
        },
        "transformers": ["unittest_to_pytest"],
        "data_preservation": True,
        "estimated_effort_hours": 18,
        "breaking_changes": False,
    },

    # =========================
    # Mobile
    # =========================
    ("reactnative", "flutter"): {
        "complexity": "very_high",
        "supported_versions": {
            "reactnative": ["0.72", "0.73"],
            "flutter": ["3.16", "3.19"],
        },
        "transformers": ["rn_to_flutter"],
        "data_preservation": True,
        "estimated_effort_hours": 120,
        "breaking_changes": True,
    },

    # =========================
    # Package Managers
    # =========================
    ("npm", "yarn"): {
        "complexity": "low",
        "supported_versions": {
            "npm": ["9", "10"],
            "yarn": ["3", "4"],
        },
        "transformers": ["package_manager"],
        "data_preservation": True,
        "estimated_effort_hours": 2,
        "breaking_changes": False,
    },
    ("yarn", "pnpm"): {
        "complexity": "low",
        "supported_versions": {
            "yarn": ["3", "4"],
            "pnpm": ["8", "9"],
        },
        "transformers": ["package_manager"],
        "data_preservation": True,
        "estimated_effort_hours": 3,
        "breaking_changes": False,
    },
    ("pip", "poetry"): {
        "complexity": "low",
        "supported_versions": {
            "pip": ["23", "24"],
            "poetry": ["1.6", "1.7"],
        },
        "transformers": ["package_manager"],
        "data_preservation": True,
        "estimated_effort_hours": 4,
        "breaking_changes": False,
    },
}

# ============================================================
# Risk level thresholds
# ============================================================
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

# ============================================================
# Migration phases
# ============================================================
MIGRATION_PHASES = [
    {"id": "analysis", "name": "Analysis", "description": "Analyze source code and create migration plan"},
    {"id": "planning", "name": "Planning", "description": "Generate detailed step-by-step migration plan"},
    {"id": "backup", "name": "Backup & Checkpoint", "description": "Create backup and checkpoint for rollback"},
    {"id": "transformation", "name": "Code Transformation", "description": "Apply code transformations"},
    {"id": "validation", "name": "Validation & Testing", "description": "Validate transformations and run tests"},
    {"id": "fixup", "name": "Auto-Fix Issues", "description": "Automatically fix validation failures"},
    {"id": "reporting", "name": "Report Generation", "description": "Generate migration report and documentation"},
]

# ============================================================
# Timeouts (seconds)
# ============================================================
TIMEOUTS = {
    "analysis": 300,
    "planning": 300,
    "transformation": 1800,
    "validation": 600,
    "reporting": 300,
}

# ============================================================
# Feature flags
# ============================================================
FEATURE_FLAGS = {
    "enable_parallel_transformation": False,
    "enable_data_migration": False,
    "enable_custom_transformers": False,
    "enable_teams_collaboration": True,
    "enable_auto_fix": True,
    "enable_incremental_rollback": True,
}
