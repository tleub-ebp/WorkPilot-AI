"""
Architecture Configuration
===========================

Loads architecture rules from explicit config or infers them from project analysis.
"""

from __future__ import annotations

import json
from pathlib import Path

from .models import (
    ArchitectureConfig,
    BoundedContextConfig,
    ForbiddenPattern,
    LayerConfig,
    RulesConfig,
)

CONFIG_FILENAME = "architecture_rules.json"


def load_architecture_config(project_dir: Path) -> ArchitectureConfig | None:
    """
    Load explicit architecture rules from .auto-claude/architecture_rules.json.

    Returns None if no config file exists.
    """
    config_path = project_dir / ".auto-claude" / CONFIG_FILENAME
    if not config_path.exists():
        return None

    try:
        with open(config_path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None

    return _parse_config(data)


def _parse_config(data: dict) -> ArchitectureConfig:
    """Parse a raw JSON dict into an ArchitectureConfig."""
    layers = [
        LayerConfig(
            name=layer.get("name", ""),
            patterns=layer.get("patterns", []),
            allowed_imports=layer.get("allowed_imports", []),
            forbidden_imports=layer.get("forbidden_imports", []),
        )
        for layer in data.get("layers", [])
    ]

    bounded_contexts = [
        BoundedContextConfig(
            name=ctx.get("name", ""),
            patterns=ctx.get("patterns", []),
            allowed_cross_context_imports=ctx.get("allowed_cross_context_imports", []),
        )
        for ctx in data.get("bounded_contexts", [])
    ]

    rules_data = data.get("rules", {})
    forbidden_patterns = [
        ForbiddenPattern(
            from_pattern=fp.get("from", ""),
            import_pattern=fp.get("import_pattern", ""),
            description=fp.get("description", ""),
        )
        for fp in rules_data.get("forbidden_patterns", [])
    ]

    rules = RulesConfig(
        no_circular_dependencies=rules_data.get("no_circular_dependencies", True),
        max_dependency_depth=rules_data.get("max_dependency_depth", 10),
        forbidden_patterns=forbidden_patterns,
    )

    return ArchitectureConfig(
        version=data.get("version", "1.0"),
        architecture_style=data.get("architecture_style", "layered"),
        layers=layers,
        bounded_contexts=bounded_contexts,
        rules=rules,
        ai_review=data.get("ai_review", True),
        inferred=False,
    )


def infer_architecture_config(
    project_dir: Path, project_index: dict | None = None
) -> ArchitectureConfig:
    """
    Auto-generate architecture rules from project structure.

    Uses project_index.json (from ProjectAnalyzer) to detect patterns
    and produce reasonable default rules. Inferred rules produce warnings
    instead of errors (only explicit configs produce errors).
    """
    if project_index is None:
        project_index = _load_project_index(project_dir)

    layers: list[LayerConfig] = []
    bounded_contexts: list[BoundedContextConfig] = []
    forbidden_patterns: list[ForbiddenPattern] = []

    project_type = project_index.get("project_type", "single")
    services = project_index.get("services", {})

    # Detect frameworks from services or detected_stack
    frameworks = _get_frameworks(project_index)
    languages = _get_languages(project_index)

    # Monorepo: enforce service boundaries
    if project_type == "monorepo" and len(services) > 1:
        for svc_name, svc_info in services.items():
            svc_path = svc_info.get("path", svc_name)
            bounded_contexts.append(
                BoundedContextConfig(
                    name=svc_name,
                    patterns=[f"{svc_path}/**"],
                    allowed_cross_context_imports=["shared", "common", "lib", "utils"],
                )
            )

    # React/Vue/Angular: presentation/logic separation
    if _has_frontend_framework(frameworks):
        layers.extend(_infer_frontend_layers(services, project_type))
        forbidden_patterns.append(
            ForbiddenPattern(
                from_pattern="**/components/**",
                import_pattern=r"database|prisma|typeorm|sequelize|mongoose|knex",
                description="No direct database imports from UI components",
            )
        )

    # Django: MVC separation
    if "django" in frameworks:
        layers.extend(_infer_django_layers())

    # FastAPI/Flask: service layer separation
    if "fastapi" in frameworks or "flask" in frameworks:
        layers.extend(_infer_python_api_layers())

    # NestJS: module boundaries
    if "nestjs" in frameworks or "nest" in frameworks:
        layers.extend(_infer_nestjs_layers())

    # General: if no specific framework detected, try common patterns
    if not layers and not bounded_contexts:
        layers = _infer_generic_layers(project_dir)

    rules = RulesConfig(
        no_circular_dependencies=True,
        max_dependency_depth=10,
        forbidden_patterns=forbidden_patterns,
    )

    return ArchitectureConfig(
        version="1.0",
        architecture_style="layered" if layers else "modular",
        layers=layers,
        bounded_contexts=bounded_contexts,
        rules=rules,
        ai_review=True,
        inferred=True,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_project_index(project_dir: Path) -> dict:
    """Load project_index.json from .auto-claude/."""
    index_path = project_dir / ".auto-claude" / "project_index.json"
    if not index_path.exists():
        return {}
    try:
        with open(index_path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return {}


def _get_frameworks(project_index: dict) -> list[str]:
    """Extract framework list from project index."""
    frameworks = []
    # From detected_stack
    detected = project_index.get("detected_stack", {})
    if isinstance(detected, dict):
        frameworks.extend(detected.get("frameworks", []))
    # From services
    for svc in project_index.get("services", {}).values():
        fw = svc.get("framework", "")
        if fw:
            frameworks.append(fw)
    return [f.lower() for f in frameworks]


def _get_languages(project_index: dict) -> list[str]:
    """Extract language list from project index."""
    detected = project_index.get("detected_stack", {})
    if isinstance(detected, dict):
        return [lang.lower() for lang in detected.get("languages", [])]
    return []


def _has_frontend_framework(frameworks: list[str]) -> bool:
    """Check if any frontend framework is detected."""
    frontend_fws = {
        "react",
        "vue",
        "angular",
        "svelte",
        "next",
        "nuxt",
        "nextjs",
        "gatsby",
    }
    return bool(frontend_fws & set(frameworks))


def _infer_frontend_layers(services: dict, project_type: str) -> list[LayerConfig]:
    """Infer layers for React/Vue/Angular projects."""
    # Find the frontend service path prefix
    prefix = ""
    for svc_name, svc_info in services.items():
        svc_type = svc_info.get("type", "").lower()
        if svc_type == "frontend" or svc_name in ("frontend", "web", "app", "client"):
            prefix = svc_info.get("path", "") + "/"
            break

    return [
        LayerConfig(
            name="presentation",
            patterns=[
                f"{prefix}src/components/**",
                f"{prefix}src/pages/**",
                f"{prefix}src/views/**",
                f"{prefix}src/renderer/**",
            ],
            allowed_imports=["application", "shared"],
            forbidden_imports=["infrastructure", "data"],
        ),
        LayerConfig(
            name="application",
            patterns=[
                f"{prefix}src/hooks/**",
                f"{prefix}src/stores/**",
                f"{prefix}src/services/**",
                f"{prefix}src/features/**",
            ],
            allowed_imports=["domain", "shared"],
            forbidden_imports=[],
        ),
        LayerConfig(
            name="infrastructure",
            patterns=[
                f"{prefix}src/api/**",
                f"{prefix}src/lib/**",
                f"{prefix}src/adapters/**",
            ],
            allowed_imports=["domain", "shared"],
            forbidden_imports=["presentation"],
        ),
    ]


def _infer_django_layers() -> list[LayerConfig]:
    """Infer layers for Django projects."""
    return [
        LayerConfig(
            name="views",
            patterns=["**/views.py", "**/views/**"],
            allowed_imports=["forms", "models", "services", "utils"],
            forbidden_imports=[],
        ),
        LayerConfig(
            name="models",
            patterns=["**/models.py", "**/models/**"],
            allowed_imports=["utils"],
            forbidden_imports=["views", "forms", "urls"],
        ),
        LayerConfig(
            name="services",
            patterns=["**/services.py", "**/services/**"],
            allowed_imports=["models", "utils"],
            forbidden_imports=["views", "forms", "urls"],
        ),
    ]


def _infer_python_api_layers() -> list[LayerConfig]:
    """Infer layers for FastAPI/Flask API projects."""
    return [
        LayerConfig(
            name="routes",
            patterns=["**/routes/**", "**/routers/**", "**/api/**", "**/endpoints/**"],
            allowed_imports=["services", "models", "schemas", "utils"],
            forbidden_imports=[],
        ),
        LayerConfig(
            name="models",
            patterns=["**/models/**", "**/entities/**"],
            allowed_imports=["utils"],
            forbidden_imports=["routes", "routers", "api", "endpoints"],
        ),
        LayerConfig(
            name="services",
            patterns=["**/services/**", "**/core/**"],
            allowed_imports=["models", "repositories", "utils"],
            forbidden_imports=["routes", "routers", "api", "endpoints"],
        ),
    ]


def _infer_nestjs_layers() -> list[LayerConfig]:
    """Infer layers for NestJS projects."""
    return [
        LayerConfig(
            name="controllers",
            patterns=["**/*.controller.ts"],
            allowed_imports=["services", "dto", "entities", "guards"],
            forbidden_imports=["repositories"],
        ),
        LayerConfig(
            name="services",
            patterns=["**/*.service.ts"],
            allowed_imports=["repositories", "entities", "dto", "utils"],
            forbidden_imports=["controllers"],
        ),
        LayerConfig(
            name="repositories",
            patterns=["**/*.repository.ts"],
            allowed_imports=["entities", "utils"],
            forbidden_imports=["controllers", "services"],
        ),
    ]


def _infer_generic_layers(project_dir: Path) -> list[LayerConfig]:
    """Infer generic layers by checking common directory names."""
    common_structures = {
        "src/presentation": "presentation",
        "src/domain": "domain",
        "src/infrastructure": "infrastructure",
        "src/application": "application",
        "src/ui": "presentation",
        "src/core": "domain",
        "src/data": "infrastructure",
        "lib": "domain",
        "app": "application",
    }

    layers = []
    for dir_path, layer_name in common_structures.items():
        if (project_dir / dir_path).is_dir():
            # Only add if we don't already have this layer
            if not any(l.name == layer_name for l in layers):
                layers.append(
                    LayerConfig(
                        name=layer_name,
                        patterns=[f"{dir_path}/**"],
                        allowed_imports=[],
                        forbidden_imports=[],
                    )
                )

    return layers
