"""
Context Discovery Module
=========================

Discovers relevant files and context for the task.
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def run_context_discovery(
    project_dir: Path,
    spec_dir: Path,
    task_description: str,
    services: list[str],
) -> tuple[bool, str]:
    """Run context.py script to discover relevant files.

    Args:
        project_dir: Project root directory
        spec_dir: Spec directory
        task_description: Task description string
        services: List of service names involved

    Returns:
        (success, output_message)
    """
    context_file = spec_dir / "context.json"

    if context_file.exists():
        return True, "context.json already exists"

    script_path = project_dir / ".workpilot" / "context.py"
    if not script_path.exists():
        return False, f"Script not found: {script_path}"

    args = [
        sys.executable,
        str(script_path),
        "--task",
        task_description or "unknown task",
        "--output",
        str(context_file),
    ]

    if services:
        args.extend(["--services", ",".join(services)])

    try:
        result = subprocess.run(
            args,
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode == 0 and context_file.exists():
            # Validate and fix common schema issues
            try:
                with open(context_file, encoding="utf-8") as f:
                    ctx = json.load(f)

                # Check for required field and fix common issues
                if "task_description" not in ctx:
                    # Common issue: field named "task" instead of "task_description"
                    if "task" in ctx:
                        ctx["task_description"] = ctx.pop("task")
                    else:
                        ctx["task_description"] = task_description or "unknown task"

                    with open(context_file, "w", encoding="utf-8") as f:
                        json.dump(ctx, f, indent=2)
            except (OSError, json.JSONDecodeError, UnicodeDecodeError):
                context_file.unlink(missing_ok=True)
                return False, "Invalid context.json created"

            return True, "Created context.json"
        else:
            return False, result.stderr or result.stdout

    except subprocess.TimeoutExpired:
        return False, "Script timed out"
    except Exception as e:
        return False, str(e)


def create_minimal_context(
    spec_dir: Path,
    task_description: str,
    services: list[str],
) -> Path:
    """Create minimal context.json when script fails."""
    context_file = spec_dir / "context.json"

    # Extract potential file paths from task description
    potential_files = []
    potential_patterns = []
    potential_services = []

    if task_description:
        # Look for file paths in the task description
        # Find all words that look like file paths with extensions
        words = task_description.split()
        for word in words:
            # Check if word looks like a file path (contains dots and valid extensions)
            if "." in word and any(
                word.endswith(ext)
                for ext in [
                    ".py",
                    ".ts",
                    ".tsx",
                    ".js",
                    ".jsx",
                    ".json",
                    ".md",
                    ".yaml",
                    ".yml",
                ]
            ):
                # Clean up the word (remove punctuation at the end)
                clean_word = word.rstrip(".,;:!?)(")
                if clean_word.endswith(
                    (
                        ".py",
                        ".ts",
                        ".tsx",
                        ".js",
                        ".jsx",
                        ".json",
                        ".md",
                        ".yaml",
                        ".yml",
                    )
                ):
                    potential_files.append(clean_word)

        # Smart pattern matching based on keywords
        task_lower = task_description.lower()

        # API/Backend patterns
        if "api" in task_lower and (
            "endpoint" in task_lower or "resource" in task_lower
        ):
            if "planning" in task_lower:
                potential_files.extend(
                    [
                        "src/api/planning.py",
                        "src/controllers/planning_controller.py",
                        "src/routes/planning_routes.py",
                        "src/middleware/planning_auth.py",
                    ]
                )
                potential_patterns.extend(
                    [
                        "REST API endpoint pattern with Express/FastAPI",
                        "Middleware pattern for API authentication",
                        "Controller pattern for API endpoints",
                    ]
                )
                potential_services.extend(["planning-api", "backend-api"])
            else:
                potential_files.extend(
                    [
                        "src/api/auth.py",
                        "src/controllers/api_controller.py",
                        "src/middleware/auth_middleware.py",
                    ]
                )
                potential_patterns.extend(
                    ["REST API authentication pattern", "JWT token validation pattern"]
                )
                potential_services.extend(["backend-api"])

        # Security/Authorization patterns
        if (
            "sécuris" in task_lower
            or "securiz" in task_lower
            or "authorization" in task_lower
            or "auth" in task_lower
        ):
            if "scope" in task_lower:
                potential_files.extend(
                    [
                        "src/middleware/scope_validation.py",
                        "src/auth/scope_middleware.py",
                        "src/decorators/require_scope.py",
                    ]
                )
                potential_patterns.extend(
                    [
                        "OAuth2 scope validation pattern",
                        "JWT scope checking middleware",
                        "Role-based access control (RBAC)",
                    ]
                )
            if "token" in task_lower:
                potential_files.extend(
                    [
                        "src/auth/token_validation.py",
                        "src/middleware/jwt_middleware.py",
                        "src/services/auth_service.py",
                    ]
                )
                potential_patterns.extend(
                    [
                        "JWT token validation pattern",
                        "Bearer token authentication",
                        "Token refresh pattern",
                    ]
                )
            potential_services.extend(["auth-service", "oauth-provider"])

        # Frontend patterns
        if "frontend" in task_lower:
            potential_files.extend(
                [
                    "src/frontend/components/",
                    "src/frontend/pages/",
                    "src/frontend/services/api.js",
                ]
            )
            potential_patterns.extend(
                [
                    "React component pattern",
                    "Frontend service pattern",
                    "API client pattern",
                ]
            )
            potential_services.extend(["frontend"])

        # Database patterns
        if "database" in task_lower or "bdd" in task_lower:
            potential_files.extend(
                [
                    "src/models/database.py",
                    "src/services/database_service.py",
                    "src/config/database.py",
                ]
            )
            potential_patterns.extend(
                [
                    "Database repository pattern",
                    "ORM pattern (SQLAlchemy/Prisma)",
                    "Database connection pooling",
                ]
            )
            potential_services.extend(["database"])

        # Remove duplicates while preserving order
        seen = set()
        potential_files = [x for x in potential_files if not (x in seen or seen.add(x))]
        seen = set()
        potential_patterns = [
            x for x in potential_patterns if not (x in seen or seen.add(x))
        ]
        seen = set()
        potential_services = [
            x for x in potential_services if not (x in seen or seen.add(x))
        ]

    # Create fallback context with some useful information
    # Re-calculate task_lower for keyword detection
    task_lower = task_description.lower() if task_description else ""

    minimal_context = {
        "task_description": task_description or "unknown task",
        "scoped_services": services + potential_services,  # Include detected services
        "files_to_modify": potential_files,  # Use extracted files instead of empty array
        "files_to_reference": [],  # Keep empty for now, could be enhanced later
        "patterns": {
            pattern: f"Detected pattern: {pattern}" for pattern in potential_patterns
        },
        "created_at": datetime.now().isoformat(),
        "fallback_mode": True,  # Flag to indicate this is fallback context
        "detected_keywords": {
            "api": "api" in task_lower,
            "security": any(
                word in task_lower
                for word in ["sécuris", "securiz", "auth", "authorization"]
            ),
            "frontend": "frontend" in task_lower,
            "database": any(word in task_lower for word in ["database", "bdd"]),
            "planning": "planning" in task_lower,
            "scope": "scope" in task_lower,
            "token": "token" in task_lower,
        },
    }

    with open(context_file, "w", encoding="utf-8") as f:
        json.dump(minimal_context, f, indent=2)

    return context_file


def get_context_stats(spec_dir: Path) -> dict:
    """Get statistics from context file if available."""
    context_file = spec_dir / "context.json"
    if not context_file.exists():
        return {}

    try:
        with open(context_file, encoding="utf-8") as f:
            ctx = json.load(f)
        return {
            "files_to_modify": len(ctx.get("files_to_modify", [])),
            "files_to_reference": len(ctx.get("files_to_reference", [])),
        }
    except Exception:
        return {}
