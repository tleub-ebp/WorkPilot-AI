#!/usr/bin/env python3
"""
Personalized Context Manager for Claude Agent Skills

Provides context-aware skill discovery and personalization based on:
- User preferences and history
- Project-specific patterns
- Team collaboration context
- Learning from usage patterns

Features:
- User profile management
- Project type detection
- Personalized skill ranking
- Context-aware filtering
- Learning and adaptation
"""

import hashlib
import json
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .context_optimizer import ContextOptimizer
from .token_optimizer import TokenOptimizer

logger = logging.getLogger(__name__)


@dataclass
class UserProfile:
    """User profile for personalization."""

    user_id: str
    preferences: dict[str, Any] = field(default_factory=dict)
    skill_history: list[str] = field(default_factory=list)
    project_types: list[str] = field(default_factory=list)
    team_context: dict[str, Any] = field(default_factory=dict)
    usage_patterns: dict[str, int] = field(default_factory=dict)
    last_active: float = field(default_factory=time.time)

    def add_skill_usage(self, skill_name: str):
        """Add skill to usage history."""
        self.skill_history.append(skill_name)
        self.usage_patterns[skill_name] = self.usage_patterns.get(skill_name, 0) + 1
        self.last_active = time.time()

        # Keep history manageable - reduced from 1000 to 500 for token optimization
        if len(self.skill_history) > 500:
            self.skill_history = self.skill_history[-250:]

    def get_frequent_skills(
        self, limit: int = 5
    ) -> list[tuple[str, int]]:  # Reduced from 10 to 5
        """Get most frequently used skills."""
        sorted_skills = sorted(
            self.usage_patterns.items(), key=lambda x: x[1], reverse=True
        )
        return sorted_skills[:limit]

    def update_preferences(self, preferences: dict[str, Any]):
        """Update user preferences."""
        self.preferences.update(preferences)
        self.last_active = time.time()


@dataclass
class ProjectContext:
    """Context information about the current project."""

    project_id: str
    project_type: str
    detected_frameworks: list[str] = field(default_factory=list)
    detected_languages: list[str] = field(default_factory=list)
    file_structure: dict[str, Any] = field(default_factory=dict)
    build_tools: list[str] = field(default_factory=list)
    recent_changes: list[str] = field(default_factory=list)

    def add_framework(self, framework: str):
        """Add detected framework."""
        if framework not in self.detected_frameworks:
            self.detected_frameworks.append(framework)

    def add_language(self, language: str):
        """Add detected language."""
        if language not in self.detected_languages:
            self.detected_languages.append(language)

    def get_relevance_score(self, skill_name: str, skill_metadata: dict) -> float:
        """Calculate relevance score for a skill based on project context."""
        score = 0.5  # Base score

        # Framework matching
        if skill_metadata.get("category") == "development":
            for framework in self.detected_frameworks:
                if (
                    framework.lower() in skill_name.lower()
                    or skill_name.lower() in framework.lower()
                ):
                    score += 0.3
                    break

        # Language matching
        for language in self.detected_languages:
            if (
                language.lower() in skill_name.lower()
                or skill_name.lower() in language.lower()
            ):
                score += 0.2
                break

        # Build tool matching
        for tool in self.build_tools:
            if tool.lower() in skill_name.lower():
                score += 0.1
                break

        return min(score, 1.0)


class ContextLearner:
    """Learns from user patterns and adapts recommendations."""

    def __init__(self):
        self.user_patterns: dict[str, dict] = {}
        self.skill_transitions: defaultdict(lambda: defaultdict(int))
        self.query_patterns: dict[str, list[str]] = defaultdict(list)
        self.success_patterns: dict[str, float] = defaultdict(float)

    def learn_from_interaction(
        self, query: str, selected_skills: list[str], success: bool, context: dict
    ):
        """Learn from user interaction."""
        # Learn query patterns
        normalized_query = self._normalize_query(query)
        self.query_patterns[normalized_query].extend(selected_skills)

        # Learn skill transitions
        for i in range(len(selected_skills) - 1):
            from_skill = selected_skills[i]
            to_skill = selected_skills[i + 1]
            self.skill_transitions[from_skill][to_skill] += 1

        # Learn success patterns
        pattern_key = self._create_pattern_key(query, selected_skills)
        if success:
            self.success_patterns[pattern_key] = (
                self.success_patterns[pattern_key] * 0.9
                + 0.1  # Exponential moving average
            )
        else:
            self.success_patterns[pattern_key] = (
                self.success_patterns[pattern_key] * 0.9  # Decay on failure
            )

    def predict_next_skills(
        self, query: str, context: dict, limit: int = 5
    ) -> list[tuple[str, float]]:
        """Predict next skills based on learned patterns."""
        normalized_query = self._normalize_query(query)

        # Direct pattern match
        if normalized_query in self.query_patterns:
            skills = self.query_patterns[normalized_query]
            # Sort by frequency
            skill_freq = [
                (skill, self.skill_transitions.get(skill, 0)) for skill in skills
            ]
            skill_freq.sort(key=lambda x: x[1], reverse=True)
            return skill_freq[:limit]

        # Context-based prediction
        if "recent_skills" in context:
            recent_skills = context["recent_skills"]
            if recent_skills:
                last_skill = recent_skills[-1]
                transitions = self.skill_transitions.get(last_skill, {})
                if transitions:
                    sorted_transitions = sorted(
                        transitions.items(), key=lambda x: x[1], reverse=True
                    )
                    return sorted_transitions[:limit]

        return []

    def _normalize_query(self, query: str) -> str:
        """Normalize query for pattern matching."""
        import re

        # Convert to lowercase
        normalized = query.lower()

        # Remove special characters
        normalized = re.sub(r"[^\w\s]", " ", normalized)

        # Remove extra whitespace
        normalized = " ".join(normalized.split())

        # Extract key terms
        words = normalized.split()
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
        }
        key_terms = [word for word in words if word not in stop_words and len(word) > 2]

        return " ".join(sorted(key_terms))

    def _create_pattern_key(self, query: str, skills: list[str]) -> str:
        """Create a pattern key for learning."""
        normalized_query = self._normalize_query(query)
        skill_sequence = "|".join(sorted(skills))
        return f"{normalized_query}:{skill_sequence}"


class PersonalizedSkillManager:
    """Manager for personalized skill discovery and ranking."""

    def __init__(self, base_skill_manager, user_data_dir: str = "user_data"):
        self.base_skill_manager = base_skill_manager
        self.user_data_dir = Path(user_data_dir)
        self.user_data_dir.mkdir(exist_ok=True)

        # User profiles
        self.user_profiles: dict[str, UserProfile] = {}

        # Project contexts
        self.project_contexts: dict[str, ProjectContext] = {}

        # Learning system
        self.learner = ContextLearner()

        # Optimization systems
        self.context_optimizer = ContextOptimizer(
            max_context_size=8000
        )  # Reduced from default
        self.token_optimizer = TokenOptimizer(
            cache_size=500, cache_ttl=1800.0
        )  # 30 min TTL

        # Load existing data
        self._load_user_data()

        # User session tracking
        self.active_sessions: set[str] = set()

        # Optimization metrics
        self.optimization_stats = {
            "context_compactions": 0,
            "token_savings": 0,
            "cache_hits": 0,
        }

        logger.info("Personalized skill manager initialized with optimization")

    def _load_user_data(self):
        """Load existing user data."""
        # Load user profiles
        profiles_file = self.user_data_dir / "user_profiles.json"
        if profiles_file.exists():
            try:
                with open(profiles_file) as f:
                    data = json.load(f)
                    for user_id, profile_data in data.items():
                        profile = UserProfile(
                            user_id=user_id,
                            preferences=profile_data.get("preferences", {}),
                            skill_history=profile_data.get("skill_history", []),
                            project_types=profile_data.get("project_types", []),
                            team_context=profile_data.get("team_context", {}),
                            usage_patterns=profile_data.get("usage_patterns", {}),
                            last_active=profile_data.get("last_active", time.time()),
                        )
                        self.user_profiles[user_id] = profile
                logger.info(f"Loaded {len(self.user_profiles)} user profiles")
            except Exception as e:
                logger.warning(f"Failed to load user profiles: {e}")

        # Load project contexts
        contexts_file = self.user_data_dir / "project_contexts.json"
        if contexts_file.exists():
            try:
                with open(contexts_file) as f:
                    data = json.load(f)
                    for project_id, context_data in data.items():
                        context = ProjectContext(
                            project_id=project_id,
                            project_type=context_data.get("project_type", "unknown"),
                            detected_frameworks=context_data.get(
                                "detected_frameworks", []
                            ),
                            detected_languages=context_data.get(
                                "detected_languages", []
                            ),
                            file_structure=context_data.get("file_structure", {}),
                            build_tools=context_data.get("build_tools", []),
                            recent_changes=context_data.get("recent_changes", []),
                        )
                        self.project_contexts[project_id] = context
                logger.info(f"Loaded {len(self.project_contexts)} project contexts")
            except Exception as e:
                logger.warning(f"Failed to load project contexts: {e}")

    def _save_user_data(self):
        """Save user data to files."""
        try:
            # Save user profiles
            profiles_data = {}
            for user_id, profile in self.user_profiles.items():
                profiles_data[user_id] = {
                    "preferences": profile.preferences,
                    "skill_history": profile.skill_history,
                    "project_types": profile.project_types,
                    "team_context": profile.team_context,
                    "usage_patterns": profile.usage_patterns,
                    "last_active": profile.last_active,
                }

            profiles_file = self.user_data_dir / "user_profiles.json"
            with open(profiles_file, "w") as f:
                json.dump(profiles_data, f, indent=2)

            # Save project contexts
            contexts_data = {}
            for project_id, context in self.project_contexts.items():
                contexts_data[project_id] = {
                    "project_type": context.project_type,
                    "detected_frameworks": context.detected_frameworks,
                    "detected_languages": context.detected_languages,
                    "file_structure": context.file_structure,
                    "build_tools": context.build_tools,
                    "recent_changes": context.recent_changes,
                }

            contexts_file = self.user_data_dir / "project_contexts.json"
            with open(contexts_file, "w") as f:
                json.dump(contexts_data, f, indent=2)

            logger.debug("User data saved")
        except Exception as e:
            logger.error(f"Failed to save user data: {e}")

    def start_session(self, user_id: str, project_id: str | None = None) -> str:
        """Start a personalized session."""
        session_id = hashlib.sha256(
            f"{user_id}:{project_id}:{time.time()}".encode()
        ).hexdigest()[:16]

        self.active_sessions.add(session_id)

        # Load or create user profile
        if user_id not in self.user_profiles:
            self.user_profiles[user_id] = UserProfile(user_id=user_id)

        # Load or create project context
        if project_id and project_id not in self.project_contexts:
            self.project_contexts[project_id] = ProjectContext(project_id=project_id)
            self._analyze_project(project_id)

        logger.info(
            f"Started personalized session: {session_id[:8]} for user {user_id}"
        )
        return session_id

    def end_session(self, session_id: str):
        """End a personalized session."""
        if session_id in self.active_sessions:
            self.active_sessions.remove(session_id)
            self._save_user_data()
            logger.info(f"Ended personalized session: {session_id[:8]}")

    def get_relevant_skills(
        self, query: str, session_id: str, context: dict | None = None
    ) -> list[str]:
        """Get relevant skills with personalization and optimization."""
        # Extract user and project info from session ID
        user_id, project_id = self._parse_session_id(session_id)

        if user_id not in self.user_profiles:
            user_id = "default"

        # Optimize query and context
        optimized_query = self.token_optimizer.optimize_query(query, context)

        # Get base skills from manager
        base_skills = self.base_skill_manager.get_relevant_skills(query)

        # Apply personalization with optimization
        personalized_skills = self._apply_personalization(
            base_skills, user_id, project_id, optimized_query.get("context"), query
        )

        # Optimize results before returning
        optimized_skills, _ = self.token_optimizer.optimize_content(
            personalized_skills, "list", use_cache=True
        )

        # Record usage for learning
        self._record_usage(user_id, query, optimized_skills)

        # Apply context optimization if needed
        if len(optimized_skills) > 8:  # Reduced from 10
            optimized_skills = self._optimize_skill_list(optimized_skills)
            self.optimization_stats["context_compactions"] += 1

        return optimized_skills

    def _parse_session_id(self, session_id: str) -> tuple[str, str | None]:
        """Parse session ID to extract user_id and project_id."""
        parts = session_id.split(":")
        user_id = parts[0] if len(parts) > 0 else "default"
        project_id = parts[1] if len(parts) > 1 else None
        return user_id, project_id

    def _apply_personalization(
        self,
        base_skills: list[str],
        user_id: str,
        project_id: str | None,
        context: dict | None,
        query: str,
    ) -> list[str]:
        """Apply personalization to skill results with optimization."""
        user_profile = self.user_profiles[user_id]

        # Get frequent skills from user history (reduced limit)
        frequent_skills = user_profile.get_frequent_skills(limit=3)  # Reduced from 5
        frequent_skill_names = [skill[0] for skill in frequent_skills]

        # Combine base skills with frequent skills
        combined_skills = list(set(base_skills + frequent_skill_names))

        # Apply project context filtering
        if project_id and project_id in self.project_contexts:
            project_context = self.project_contexts[project_id]

            # Score skills based on project relevance
            scored_skills = []
            for skill_name in combined_skills:
                skill_metadata = self.base_skill_manager.get_skill_info(skill_name)
                if skill_metadata:
                    # Optimize metadata before scoring
                    optimized_metadata = self.token_optimizer.optimize_skill_metadata(
                        skill_metadata
                    )
                    relevance = project_context.get_relevance_score(
                        skill_name, optimized_metadata
                    )
                    scored_skills.append((skill_name, relevance))
                else:
                    scored_skills.append((skill_name, 0.5))  # Default relevance

            # Sort by relevance and return top skills (reduced limit)
            scored_skills.sort(key=lambda x: x[1], reverse=True)
            personalized_skills = [skill[0] for skill in scored_skills]
        else:
            # No project context, use user preferences
            personalized_skills = self._apply_user_preferences(
                combined_skills, user_profile
            )

        # Apply learning-based predictions (reduced limit)
        if context:
            predicted_skills = self.learner.predict_next_skills(
                query,
                context,
                limit=2,  # noqa: F821
            )  # Reduced from 3
            predicted_skill_names = [skill[0] for skill in predicted_skills]

            # Add predicted skills if not already present
            for skill_name in predicted_skill_names:
                if skill_name not in personalized_skills:
                    personalized_skills.append(skill_name)

        return personalized_skills[:8]  # Reduced from 10

    def _apply_user_preferences(
        self, skills: list[str], profile: UserProfile
    ) -> list[str]:
        """Apply user preferences to skill ranking."""
        preferences = profile.preferences

        # Get skill metadata for preference-based filtering
        skill_scores = []
        for skill_name in skills:
            score = 0.5  # Base score

            skill_metadata = self.base_skill_manager.get_skill_info(skill_name)
            if skill_metadata:
                # Category preference
                preferred_categories = preferences.get("preferred_categories", [])
                if skill_metadata.get("category") in preferred_categories:
                    score += 0.3

                # Avoid excluded skills
                excluded_skills = preferences.get("excluded_skills", [])
                if skill_name in excluded_skills:
                    score = 0.0

                # Priority skills
                priority_skills = preferences.get("priority_skills", [])
                if skill_name in priority_skills:
                    score += 0.4

            skill_scores.append((skill_name, score))

        # Sort by score and return
        skill_scores.sort(key=lambda x: x[1], reverse=True)
        return [skill[0] for skill in skill_scores]

    def _record_usage(self, user_id: str, query: str, skills_used: list[str]):
        """Record usage for learning with optimization."""
        if user_id in self.user_profiles:
            self.user_profiles[user_id].add_skill_usage(
                skills_used[0] if skills_used else "unknown"
            )

            # Optimize context before updating learner
            user_context = {
                "user_id": user_id,
                "recent_skills": self.user_profiles[user_id].skill_history[-5:]
                if self.user_profiles[user_id].skill_history
                else [],  # Reduced from 10
            }

            # Update learner
            self.learner.learn_from_interaction(query, skills_used, True, user_context)

            # Update optimization stats
            self.optimization_stats["token_savings"] = (
                self.token_optimizer.metrics.saved_tokens
            )
            self.optimization_stats["cache_hits"] = (
                self.token_optimizer.metrics.cache_hits
            )

    def analyze_project(self, project_id: str):
        """Analyze project to extract context."""
        project_path = Path(project_id)
        if not project_path.exists():
            return

        context = self.project_contexts[project_id]

        # Detect project type
        if (project_path / "package.json").exists():
            try:
                with open(project_path / "package.json") as f:
                    package_data = json.load(f)

                    # Detect project type from dependencies
                    deps = package_data.get("dependencies", {})
                    if "react" in deps:
                        context.project_type = "react"
                    elif "vue" in deps:
                        context.project_type = "vue"
                    elif "@angular/core" in deps:
                        context.project_type = "angular"
                    elif "express" in deps:
                        context.project_type = "express"
                    elif "django" in deps:
                        context.project_type = "django"
                    elif "fastify" in deps:
                        context.project_type = "fastify"

                    # Detect build tools
                    dev_deps = package_data.get("devDependencies", {})
                    if "webpack" in dev_deps:
                        context.build_tools.append("webpack")
                    if "vite" in dev_deps:
                        context.build_tools.append("vite")
                    if "rollup" in dev_deps:
                        context.build_tools.append("rollup")
                    if "next" in dev_deps:
                        context.build_tools.append("nextjs")
                    if "@angular/cli" in dev_deps:
                        context.build_tools.append("angular-cli")
                    if "@angular/build" in dev_deps:
                        context.build_tools.append("angular-build")

            except Exception as e:
                logger.warning(f"Error analyzing package.json: {e}")

        # Detect frameworks from file structure
        if (project_path / "tsconfig.json").exists():
            context.detected_frameworks.append("typescript")

        framework_configs = [
            ("webpack", ["webpack.config.js", "webpack.config.ts"]),
            ("vite", ["vite.config.js", "vite.config.ts"]),
            ("angular", ["angular.json", "angular-cli.json"]),
        ]

        for framework, config_files in framework_configs:
            if any(
                (project_path / config_file).exists() for config_file in config_files
            ):
                context.detected_frameworks.append(framework)

        # Detect languages from file extensions
        language_extensions = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "javascript-react",
            ".tsx": "typescript-react",
            ".vue": "vue",
            ".java": "java",
            ".go": "go",
            ".rs": "rust",
            ".component.ts": "angular-component",
            ".service.ts": "angular-service",
            ".module.ts": "angular-module",
            ".pipe.ts": "angular-pipe",
            ".directive.ts": "angular-directive",
        }

        detected_languages = set()
        for file_path in project_path.rglob("*"):
            if file_path.is_file():
                ext = file_path.suffix.lower()
                if ext in language_extensions:
                    detected_languages.add(language_extensions[ext])

        context.detected_languages = list(detected_languages)

        logger.info(
            f"Analyzed project {project_id}: {context.project_type}, "
            f"frameworks: {context.detected_frameworks}, "
            f"languages: {context.detected_languages}"
        )

    def get_user_profile(self, user_id: str) -> UserProfile | None:
        """Get user profile by ID."""
        return self.user_profiles.get(user_id)

    def get_project_context(self, project_id: str) -> ProjectContext | None:
        """Get project context by ID."""
        return self.project_contexts.get(project_id)

    def update_user_preferences(self, user_id: str, preferences: dict[str, Any]):
        """Update user preferences."""
        if user_id in self.user_profiles:
            self.user_profiles[user_id].update_preferences(preferences)
            self._save_user_data()

    def get_learning_insights(self) -> dict[str, Any]:
        """Get insights from the learning system."""
        return {
            "total_patterns": len(self.learner.query_patterns),
            "total_transitions": len(self.learner.skill_transitions),
            "success_patterns": len(self.learner.success_patterns),
            "top_patterns": sorted(
                self.learner.success_patterns.items(), key=lambda x: x[1], reverse=True
            )[:10],
        }

    def get_optimization_stats(self) -> dict[str, Any]:
        """Get optimization statistics."""
        stats = self.optimization_stats.copy()
        stats.update(
            {
                "context_optimizer_metrics": self.context_optimizer.get_metrics(),
                "token_optimizer_metrics": self.token_optimizer.get_optimization_report(),
            }
        )
        return stats

    def _optimize_skill_list(self, skills: list[str]) -> list[str]:
        """Optimize skill list using context optimizer."""
        context_dict = {"skills": skills}
        optimized = self.context_optimizer.optimize_context(context_dict)
        return optimized.get("skills", skills[:8])

    def create_context_checkpoint(self, metadata: dict | None = None) -> str:
        """Create a context checkpoint."""
        context_data = {
            "user_profiles": {
                uid: profile.__dict__ for uid, profile in self.user_profiles.items()
            },
            "project_contexts": {
                pid: context.__dict__ for pid, context in self.project_contexts.items()
            },
            "optimization_stats": self.optimization_stats,
        }
        return self.context_optimizer.create_checkpoint(context_data, metadata)

    def restore_context_checkpoint(self, checkpoint_id: str) -> bool:
        """Restore from context checkpoint."""
        context_data = self.context_optimizer.restore_checkpoint(checkpoint_id)
        if context_data:
            # Restore user profiles
            for uid, profile_data in context_data.get("user_profiles", {}).items():
                self.user_profiles[uid] = UserProfile(**profile_data)

            # Restore project contexts
            for pid, ctx_data in context_data.get("project_contexts", {}).items():
                self.project_contexts[pid] = ProjectContext(**ctx_data)

            # Restore optimization stats
            self.optimization_stats = context_data.get("optimization_stats", {})

            logger.info(f"Restored from checkpoint: {checkpoint_id}")
            return True

        return False

    def export_user_data(self, filepath: str):
        """Export all user data to file."""
        try:
            # Optimize data before export
            optimized_profiles = {}
            for user_id, profile in self.user_profiles.items():
                optimized_profiles[user_id] = {
                    "preferences": profile.preferences,
                    "skill_history": self.token_optimizer.optimize_user_history(
                        profile.skill_history, max_items=100
                    ),
                    "project_types": profile.project_types,
                    "team_context": profile.team_context,
                    "usage_patterns": profile.usage_patterns,
                    "last_active": profile.last_active,
                }

            export_data = {
                "user_profiles": optimized_profiles,
                "project_contexts": {
                    project_id: {
                        "project_type": context.project_type,
                        "detected_frameworks": context.detected_frameworks,
                        "detected_languages": context.detected_languages,
                        "file_structure": context.file_structure,
                        "build_tools": context.build_tools,
                        "recent_changes": context.recent_changes,
                    }
                    for project_id, context in self.project_contexts.items()
                },
                "learning_insights": self.get_learning_insights(),
                "optimization_stats": self.optimization_stats,
            }

            with open(filepath, "w") as f:
                json.dump(export_data, f, indent=2)

            logger.info(f"Exported optimized user data to {filepath}")
        except Exception as e:
            logger.error(f"Failed to export user data: {e}")

    def import_user_data(self, filepath: str):
        """Import user data from file."""
        try:
            with open(filepath) as f:
                data = json.load(f)

            # Import user profiles
            if "user_profiles" in data:
                for user_id, profile_data in data["user_profiles"].items():
                    profile = UserProfile(
                        user_id=user_id,
                        preferences=profile_data.get("preferences", {}),
                        skill_history=profile_data.get("skill_history", []),
                        project_types=profile_data.get("project_types", []),
                        team_context=profile_data.get("team_context", {}),
                        usage_patterns=profile_data.get("usage_patterns", {}),
                        last_active=profile_data.get("last_active", time.time()),
                    )
                    self.user_profiles[user_id] = profile

            # Import project contexts
            if "project_contexts" in data:
                for project_id, context_data in data["project_contexts"].items():
                    context = ProjectContext(
                        project_id=project_id,
                        project_type=context_data.get("project_type", "unknown"),
                        detected_frameworks=context_data.get("detected_frameworks", []),
                        detected_languages=context_data.get("detected_languages", []),
                        file_structure=context_data.get("file_structure", {}),
                        build_tools=context_data.get("build_tools", []),
                        recent_changes=context_data.get("recent_changes", []),
                    )
                    self.project_contexts[project_id] = context

            logger.info(f"Imported user data from {filepath}")
        except Exception as e:
            logger.error(f"Failed to import user data: {e}")
