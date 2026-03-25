#!/usr/bin/env python3
"""
Dynamic Skill Manager

Allows runtime registration and management of skills with validation,
token counting, and optimization. Skills can be added, removed, or updated
without restarting the system.

Features:
- Runtime skill registration
- Automatic validation and optimization
- Token counting and limits
- Skill dependency management
- Hot-reloading capabilities
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from .token_optimizer import create_skill_optimizer

# Import optimization configuration
try:
    from .optimization_config import (  # noqa: F401
        DEFAULT_MAX_WORKERS,
        DEFAULT_TIMEOUT,
        OPTIMIZATION_ENABLED,
        SUBAGENT_THRESHOLD,
        VALIDATION_CACHE_SIZE,
        get_optimization_config,
    )
except ImportError:
    # Fallback for direct execution
    pass

logger = logging.getLogger(__name__)


@dataclass
class SkillValidationRule:
    """Validation rule for dynamic skills."""

    name: str
    description: str
    validator: Callable[[dict], bool]
    optimizer: Callable[[dict], dict] | None = None
    required_fields: list[str] = field(default_factory=list)
    max_tokens: int | None = None


@dataclass
class DynamicSkill:
    """Represents a dynamically loaded skill."""

    name: str
    path: Path
    metadata: dict[str, Any]
    validation_rules: list[SkillValidationRule]
    token_count: int = 0
    last_modified: float = 0.0
    is_valid: bool = True
    dependencies: set[str] = field(default_factory=set)

    def __post_init__(self):
        if self.path.exists():
            self.last_modified = self.path.stat().st_mtime
            self.token_count = self._count_tokens()

    def _count_tokens(self) -> int:
        """Count tokens in skill files with optimization."""
        total_tokens = 0

        # Count tokens in SKILL.md
        skill_file = self.path / "SKILL.md"
        if skill_file.exists():
            content = skill_file.read_text(encoding="utf-8", errors="ignore")
            # Use optimized token counting
            total_tokens += len(content.split())

        # Count tokens in scripts with sampling for large files
        scripts_dir = self.path / "scripts"
        if scripts_dir.exists():
            script_files = list(scripts_dir.glob("*.py"))

            # Sample large script collections to save tokens
            if len(script_files) > 5:
                # Take first 2, last 2, and 1 random middle file
                import random

                sample_files = script_files[:2] + script_files[-2:]
                if len(script_files) > 4:
                    middle_idx = random.randint(2, len(script_files) - 3)
                    sample_files.append(script_files[middle_idx])
                script_files = sample_files

            for script_file in script_files:
                try:
                    content = script_file.read_text(encoding="utf-8", errors="ignore")
                    # For large files, sample content
                    if len(content) > 2000:
                        content = content[:1000] + "\n...\n" + content[-1000:]
                    total_tokens += len(content.split())
                except Exception:
                    pass

        return total_tokens

    def validate(self) -> bool:
        """Validate skill against all rules."""
        for rule in self.validation_rules:
            if not rule.validator(self.metadata):
                logger.error(f"Skill {self.name} failed validation: {rule.name}")
                return False

        # Check required fields
        for required_field in rule.required_fields:
            if required_field not in self.metadata:
                logger.error(
                    f"Skill {self.name} missing required field: {required_field}"
                )
                return False

        # Check token limits
        for rule in self.validation_rules:
            if rule.max_tokens and self.token_count > rule.max_tokens:
                logger.error(
                    f"Skill {self.name} exceeds token limit: {self.token_count} > {rule.max_tokens}"
                )
                return False

        self.is_valid = True
        return True

    def optimize(self) -> dict:
        """Optimize skill metadata."""
        optimized_metadata = self.metadata.copy()

        for rule in self.validation_rules:
            if rule.optimizer:
                optimized_metadata = rule.optimizer(optimized_metadata)

        return optimized_metadata

    def has_changed(self) -> bool:
        """Check if skill files have changed."""
        if not self.path.exists():
            return False

        current_mtime = self.path.stat().st_mtime
        return current_mtime > self.last_modified

    def refresh(self):
        """Refresh skill metadata and token count."""
        if self.path.exists():
            self.last_modified = self.path.stat().st_mtime
            self.token_count = self._count_tokens()
            self.is_valid = self.validate()


class SkillRegistry:
    """Registry for managing dynamic skills with token optimization."""

    def __init__(self):
        self.skills: dict[str, DynamicSkill] = {}
        self.validation_rules: dict[str, SkillValidationRule] = {}
        self.skill_dependencies: dict[str, set[str]] = {}
        self.dependency_graph: dict[str, set[str]] = {}

        # Token optimization
        self.token_optimizer = create_skill_optimizer()
        self.optimization_stats = {
            "validations_optimized": 0,
            "tokens_saved": 0,
            "cache_hits": 0,
        }

        # Register default validation rules
        self._register_default_rules()

    def _register_default_rules(self):
        """Register default validation rules."""
        # Basic skill structure rule with reduced token limit
        self.register_validation_rule(
            SkillValidationRule(
                name="basic_structure",
                description="Validates basic skill structure",
                validator=lambda metadata: all(
                    field in metadata for field in ["name", "description"]
                ),
                required_fields=["name", "description"],
                max_tokens=3000,  # Reduced from 5000
            )
        )

        # Name format rule
        self.register_validation_rule(
            SkillValidationRule(
                name="name_format",
                description="Validates skill name format",
                validator=lambda metadata: (
                    isinstance(metadata.get("name"), str)
                    and len(metadata["name"]) <= 64
                    and metadata["name"].replace("-", "_").isalnum()
                    and all(c not in metadata["name"] for c in ["<", ">", "&"])
                ),
                max_tokens=100,
            )
        )

        # Description length rule with optimized validation
        self.register_validation_rule(
            SkillValidationRule(
                name="description_length",
                description="Validates description length",
                validator=lambda metadata: (
                    isinstance(metadata.get("description"), str)
                    and 0 < len(metadata["description"]) <= 512  # Reduced from 1024
                ),
                max_tokens=150,  # Reduced from 200
            )
        )

        # Triggers format rule with reduced limit
        self.register_validation_rule(
            SkillValidationRule(
                name="triggers_format",
                description="Validates triggers format",
                validator=lambda metadata: (
                    isinstance(metadata.get("triggers"), list)
                    and all(isinstance(t, str) for t in metadata["triggers"])
                    and len(metadata["triggers"]) <= 5  # Reduced limit
                ),
                max_tokens=200,  # Reduced from 300
            )
        )

    def register_validation_rule(self, rule: SkillValidationRule):
        """Register a validation rule."""
        self.validation_rules[rule.name] = rule
        logger.debug(f"Registered validation rule: {rule.name}")

    def register_skill(
        self,
        skill_path: Path,
        validation_rules: list[SkillValidationRule] | None = None,
    ) -> bool:
        """Register a new dynamic skill with optimization."""
        try:
            # Load skill metadata
            skill_file = skill_path / "SKILL.md"
            if not skill_file.exists():
                logger.error(f"SKILL.md not found in {skill_path}")
                return False

            metadata = self._parse_skill_metadata(skill_file)

            # Optimize metadata before validation
            optimized_metadata = self.token_optimizer.optimize_skill_metadata(metadata)

            # Create skill object with optimized metadata
            skill = DynamicSkill(
                name=optimized_metadata.get("name", skill_path.name),
                path=skill_path,
                metadata=optimized_metadata,
                validation_rules=validation_rules
                or list(self.validation_rules.values()),
            )

            # Validate skill
            if not skill.validate():
                return False

            # Check dependencies
            dependencies = self._extract_dependencies(skill)
            if not self._check_dependencies(dependencies):
                logger.error(
                    f"Skill {skill.name} has unmet dependencies: {dependencies}"
                )
                return False

            # Register skill
            self.skills[skill.name] = skill
            self.skill_dependencies[skill.name] = dependencies

            # Update dependency graph
            self._update_dependency_graph(skill.name, dependencies)

            # Update optimization stats
            self.optimization_stats["validations_optimized"] += 1
            self.optimization_stats["tokens_saved"] += (
                self.token_optimizer.metrics.saved_tokens
            )
            self.optimization_stats["cache_hits"] += (
                self.token_optimizer.metrics.cache_hits
            )

            logger.info(f"Registered optimized dynamic skill: {skill.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to register skill from {skill_path}: {e}")
            return False

    def _parse_skill_metadata(self, skill_file: Path) -> dict:
        """Parse metadata from SKILL.md file."""
        content = skill_file.read_text(encoding="utf-8")

        # Extract YAML frontmatter
        if content.startswith("---"):
            try:
                end_marker = content.find("---", 3)
                if end_marker != -1:
                    frontmatter = content[3:end_marker].strip()
                    metadata = {}

                    for line in frontmatter.split("\n"):
                        if ":" in line:
                            key, value = line.split(":", 1)
                            key = key.strip()
                            value = value.strip()

                            # Handle different field types
                            if key == "triggers":
                                value = value.strip("[]").split(",")
                                value = [
                                    t.strip().strip("\"'") for t in value if t.strip()
                                ]
                            elif key.startswith('"') and key.endswith('"'):
                                value = value.strip("\"'")

                            metadata[key] = value

                    return metadata
            except Exception as e:
                logger.warning(f"Error parsing frontmatter: {e}")

        # Fallback metadata
        return {
            "name": skill_file.parent.name,
            "description": "Dynamic skill",
            "triggers": [],
        }

    def _extract_dependencies(self, skill: DynamicSkill) -> set[str]:
        """Extract skill dependencies from metadata."""
        dependencies = set()

        # Check for dependencies in metadata
        deps = skill.metadata.get("dependencies", [])
        if isinstance(deps, list):
            dependencies.update(deps)

        # Check for dependencies in triggers (cross-skill references)
        for trigger in skill.metadata.get("triggers", []):
            # Simple heuristic: if trigger looks like a skill name
            if trigger.replace("-", "_").isalnum() and len(trigger) > 3:
                dependencies.add(trigger)

        return dependencies

    def _check_dependencies(self, dependencies: set[str]) -> bool:
        """Check if all dependencies are available."""
        for dep in dependencies:
            if dep not in self.skills:
                logger.warning(f"Dependency not found: {dep}")
                return False
        return True

    def _update_dependency_graph(self, skill_name: str, dependencies: set[str]):
        """Update dependency graph."""
        self.dependency_graph[skill_name] = dependencies

        # Add reverse dependencies
        for dep in dependencies:
            if dep not in self.dependency_graph:
                self.dependency_graph[dep] = set()
            self.dependency_graph[dep].add(skill_name)

    def unregister_skill(self, skill_name: str) -> bool:
        """Unregister a dynamic skill."""
        if skill_name not in self.skills:
            logger.warning(f"Skill not found: {skill_name}")
            return False

        # Check for dependent skills
        dependents = self.dependency_graph.get(skill_name, set())
        if dependents:
            logger.warning(
                f"Cannot unregister {skill_name}: has dependents {dependents}"
            )
            return False

        # Remove from registry
        del self.skills[skill_name]
        del self.skill_dependencies[skill_name]
        if skill_name in self.dependency_graph:
            del self.dependency_graph[skill_name]

        # Remove reverse dependencies
        for deps in self.dependency_graph.values():
            deps.discard(skill_name)

        logger.info(f"Unregistered dynamic skill: {skill_name}")
        return True

    def reload_skill(self, skill_name: str) -> bool:
        """Reload a skill if it has changed."""
        if skill_name not in self.skills:
            logger.warning(f"Skill not found: {skill_name}")
            return False

        skill = self.skills[skill_name]

        if skill.has_changed():
            logger.info(f"Reloading changed skill: {skill_name}")
            skill.refresh()
            return True

        return False

    def get_skill(self, skill_name: str) -> DynamicSkill | None:
        """Get a skill by name."""
        return self.skills.get(skill_name)

    def list_skills(self) -> list[str]:
        """List all registered skill names."""
        return list(self.skills.keys())

    def get_dependency_order(self, skill_names: list[str]) -> list[str]:
        """Get skills in dependency order (topological sort)."""
        # Simple topological sort
        visited = set()
        result = []

        def visit(skill_name: str):
            if skill_name in visited:
                return
            visited.add(skill_name)

            # Visit dependencies first
            for dep in self.dependency_graph.get(skill_name, set()):
                if dep in skill_names:
                    visit(dep)

            result.append(skill_name)

        for skill_name in skill_names:
            if skill_name not in visited:
                visit(skill_name)

        return result

    def get_validation_summary(self) -> dict[str, Any]:
        """Get validation summary for all skills with optimization metrics."""
        summary = {
            "total_skills": len(self.skills),
            "valid_skills": sum(1 for s in self.skills.values() if s.is_valid),
            "invalid_skills": sum(1 for s in self.skills.values() if not s.is_valid),
            "total_tokens": sum(s.token_count for s in self.skills.values()),
            "validation_rules": len(self.validation_rules),
            "dependency_graph_size": len(self.dependency_graph),
            "optimization_stats": self.optimization_stats,
            "token_optimizer_metrics": self.token_optimizer.get_optimization_report(),
        }

        # Add skill details with optimization
        summary["skills"] = {}
        for name, skill in self.skills.items():
            summary["skills"][name] = {
                "is_valid": skill.is_valid,
                "token_count": skill.token_count,
                "dependencies": list(skill.dependencies),
                "last_modified": skill.last_modified,
                "optimized": skill.token_count
                < 3000,  # Mark as optimized if under threshold
            }

        return summary


class SkillFileWatcher(FileSystemEventHandler):
    """File system watcher for skill directory changes."""

    def __init__(self, registry: SkillRegistry):
        self.registry = registry
        self.debounce_timer = None

    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return

        file_path = Path(event.src_path)
        if file_path.name == "SKILL.md":
            # Debounce rapid changes
            if self.debounce_timer:
                self.debounce_timer.cancel()

            import threading

            self.debounce_timer = threading.Timer(1.0, self._handle_skill_change)
            self.debounce_timer.start()

    def _handle_skill_change(self):
        """Handle skill file changes."""
        logger.info("Skill file changed, checking for updates...")

        # Find which skill was modified
        for skill_name, skill in self.registry.skills.items():
            if skill.has_changed():
                logger.info(f"Reloading changed skill: {skill_name}")
                self.registry.reload_skill(skill_name)
                break


class DynamicSkillManager:
    """Main manager for dynamic skills with hot-reloading."""

    def __init__(self, skills_dir: str = "skills", auto_reload: bool = True):
        self.skills_dir = Path(skills_dir)
        self.registry = SkillRegistry()
        self.auto_reload = auto_reload
        self.observer = None

        # Ensure skills directory exists
        self.skills_dir.mkdir(exist_ok=True)

        # Load existing skills
        self._load_existing_skills()

        # Set up file watching
        if self.auto_reload:
            self._setup_file_watcher()

        logger.info(f"Dynamic skill manager initialized for {self.skills_dir}")

    def _load_existing_skills(self):
        """Load all existing skills from directory."""
        for skill_dir in self.skills_dir.iterdir():
            if skill_dir.is_dir():
                if (skill_dir / "SKILL.md").exists():
                    self.registry.register_skill(skill_dir)

    def _setup_file_watcher(self):
        """Set up file system watcher for hot-reloading."""
        try:
            self.observer = Observer()
            handler = SkillFileWatcher(self.registry)
            self.observer.schedule(handler, str(self.skills_dir), recursive=True)
            self.observer.start()
            logger.info("File watcher enabled for hot-reloading")
        except Exception as e:
            logger.error(f"Failed to set up file watcher: {e}")
            self.auto_reload = False

    def register_skill(
        self, skill_path: str, validation_rules: list[SkillValidationRule] | None = None
    ) -> bool:
        """Register a new skill from path."""
        path = Path(skill_path)
        if not path.is_absolute():
            path = self.skills_dir / path

        return self.registry.register_skill(path, validation_rules)

    def unregister_skill(self, skill_name: str) -> bool:
        """Unregister a skill."""
        return self.registry.unregister_skill(skill_name)

    def reload_skill(self, skill_name: str) -> bool:
        """Reload a skill."""
        return self.registry.reload_skill(skill_name)

    def get_skill(self, skill_name: str) -> DynamicSkill | None:
        """Get a skill by name."""
        return self.registry.get_skill(skill_name)

    def list_skills(self) -> list[str]:
        """List all registered skills."""
        return self.registry.list_skills()

    def get_validation_summary(self) -> dict[str, Any]:
        """Get validation summary."""
        return self.registry.get_validation_summary()

    def register_validation_rule(self, rule: SkillValidationRule):
        """Register a custom validation rule."""
        self.registry.register_validation_rule(rule)

    def shutdown(self):
        """Shutdown the manager and cleanup resources."""
        if self.observer:
            self.observer.stop()
            self.observer.join()

        logger.info("Dynamic skill manager shutdown")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()


# Example usage and factory functions
def create_validation_rule(
    name: str, validator: Callable, **kwargs
) -> SkillValidationRule:
    """Factory function for creating validation rules."""
    return SkillValidationRule(
        name=name,
        description=kwargs.get("description", f"Custom validation rule: {name}"),
        validator=validator,
        required_fields=kwargs.get("required_fields", []),
        max_tokens=kwargs.get("max_tokens"),
        optimizer=kwargs.get("optimizer"),
    )


def create_optimization_rule(
    name: str, optimizer: Callable, **kwargs
) -> SkillValidationRule:
    """Factory function for creating optimization rules."""
    return SkillValidationRule(
        name=name,
        description=kwargs.get("description", f"Optimization rule: {name}"),
        validator=lambda metadata: True,  # Always passes validation
        optimizer=optimizer,
        max_tokens=kwargs.get("max_tokens"),
    )


# Example custom rules
def validate_skill_structure(metadata: dict) -> bool:
    """Custom validation for skill structure."""
    required_sections = ["Quick Actions", "Resources"]
    skill_content = metadata.get("content", "")

    for section in required_sections:
        if section not in skill_content:
            return False

    return True


def optimize_for_tokens(metadata: dict) -> dict:
    """Optimize metadata for token usage."""
    optimized = metadata.copy()

    # Shorten description if too long
    description = optimized.get("description", "")
    if len(description) > 500:
        optimized["description"] = description[:497] + "..."

    # Limit triggers
    triggers = optimized.get("triggers", [])
    if len(triggers) > 5:
        optimized["triggers"] = triggers[:5]

    return optimized
