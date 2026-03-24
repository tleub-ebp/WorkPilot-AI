#!/usr/bin/env python3
"""
Optimized Skill Manager for Claude Agent Skills

Token-optimized implementation with advanced caching, semantic indexing,
and progressive loading for maximum efficiency.

Features:
- Semantic skill indexing for precise matching
- Intelligent caching with token usage tracking
- Lightweight metadata loading (Level 1 only)
- Context-aware skill discovery
- Token usage optimization

Usage:
    manager = OptimizedSkillManager("skills/")
    relevant = manager.get_relevant_skills("migrate react 18 to 19")
    skill = manager.load_skill_summary("framework-migration")
"""

import json
import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class SkillMetadata:
    """Optimized metadata with token efficiency."""

    name: str
    description: str
    triggers: list[str] = field(default_factory=list)
    category: str = "general"
    version: str = "1.0.0"
    author: str = ""
    skill_path: Path = field(default_factory=lambda: Path())
    token_count: int = 0  # Track token usage

    def __post_init__(self):
        # Calculate token count (rough estimation)
        self.token_count = len(self.description.split()) + len(self.triggers) * 2

    def matches_query(self, query: str, semantic_index: dict | None = None) -> bool:
        """Optimized query matching with semantic support."""
        query_lower = query.lower()

        # Quick trigger check (most efficient)
        for trigger in self.triggers:
            if trigger.lower() in query_lower:
                return True

        # Semantic matching if available
        if semantic_index:
            keywords = self._extract_keywords(query_lower)
            for keyword in keywords:
                if keyword in semantic_index.get(self.name, []):
                    return True

        # Fallback to basic text matching
        return any(word in self.description.lower() for word in query_lower.split()[:3])

    def _extract_keywords_from_query(self, query: str) -> list[str]:
        """Extract relevant keywords from query."""
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
            "with",
            "by",
        }
        return [
            word.lower()
            for word in query.split()
            if word.lower() not in stop_words and len(word) > 2
        ]


@dataclass
class SkillSummary:
    """Lightweight skill summary for token optimization."""

    name: str
    quick_actions: list[str]
    supported_frameworks: list[str]
    resources: dict[str, str]
    token_count: int = 0

    def __post_init__(self):
        self.token_count = len(str(self).split())


class OptimizedSkillManager:
    """Token-optimized skill manager with advanced caching."""

    def __init__(self, skills_dir: str = "skills/"):
        self.skills_dir = Path(skills_dir)

        # Multi-level caching
        self._metadata_cache: dict[str, SkillMetadata] = {}
        self._summary_cache: dict[str, SkillSummary] = {}
        self._context_cache: dict[str, Any] = {}  # Script results cache

        # Advanced indexing
        self._semantic_index: dict[str, list[str]] = {}  # concept -> skills
        self._trigger_index: dict[str, list[str]] = {}  # trigger -> skills
        self._category_index: dict[str, list[str]] = {}  # category -> skills

        # Performance tracking
        self._usage_stats: dict[str, dict] = {}
        self._token_usage: int = 0

        # Predefined concepts for semantic indexing
        self._frameworks = {
            "react",
            "vue",
            "angular",
            "express",
            "fastify",
            "nextjs",
            "webpack",
            "vite",
        }
        self._languages = {"javascript", "typescript", "python", "java", "go", "rust"}
        self._actions = {
            "migration",
            "upgrade",
            "refactor",
            "convert",
            "switch",
            "update",
        }

        if self.skills_dir.exists():
            self._build_indexes()
        else:
            logger.warning(f"Skills directory not found: {self.skills_dir}")

    def _extract_keywords_from_query(self, query: str) -> list[str]:
        """Extract relevant keywords from query."""
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
            "with",
            "by",
        }
        return [
            word.lower()
            for word in query.split()
            if word.lower() not in stop_words and len(word) > 2
        ]

    def _build_indexes(self) -> None:
        """Build optimized indexes for fast skill discovery."""
        logger.info("Building optimized skill indexes...")
        start_time = time.time()

        # Load only metadata (Level 1 loading)
        for skill_dir in self.skills_dir.iterdir():
            if skill_dir.is_dir():
                skill_file = skill_dir / "SKILL.md"
                if skill_file.exists():
                    try:
                        metadata = self._extract_metadata(skill_file)
                        metadata.skill_path = skill_dir
                        self._metadata_cache[metadata.name] = metadata

                        # Build indexes
                        self._index_skill(metadata)

                    except Exception as e:
                        logger.error(f"Error indexing {skill_dir}: {e}")

        build_time = time.time() - start_time
        total_tokens = sum(m.token_count for m in self._metadata_cache.values())

        logger.info(
            f"Indexes built in {build_time:.2f}s: "
            f"{len(self._metadata_cache)} skills, "
            f"{total_tokens} tokens loaded"
        )

    def _index_skill(self, metadata: SkillMetadata) -> None:
        """Index a skill for fast discovery."""
        # Trigger index
        for trigger in metadata.triggers:
            if trigger not in self._trigger_index:
                self._trigger_index[trigger] = []
            self._trigger_index[trigger].append(metadata.name)

        # Category index
        if metadata.category not in self._category_index:
            self._category_index[metadata.category] = []
        self._category_index[metadata.category].append(metadata.name)

        # Semantic index
        concepts = self._extract_concepts(
            metadata.description + " " + " ".join(metadata.triggers)
        )
        for concept in concepts:
            if concept not in self._semantic_index:
                self._semantic_index[concept] = []
            self._semantic_index[concept].append(metadata.name)

    def _extract_concepts(self, text: str) -> set[str]:
        """Extract semantic concepts from text."""
        text_lower = text.lower()
        concepts = set()

        # Framework detection
        for framework in self._frameworks:
            if framework in text_lower:
                concepts.add(framework)

        # Language detection
        for language in self._languages:
            if language in text_lower:
                concepts.add(language)

        # Action detection
        for action in self._actions:
            if action in text_lower:
                concepts.add(action)

        return concepts

    def get_relevant_skills(self, query: str) -> list[str]:
        """Get relevant skills with optimized matching."""
        start_time = time.time()
        query_lower = query.lower()

        # Multi-strategy matching
        relevant = set()

        # 1. Direct trigger matching (fastest)
        for trigger in self._trigger_index:
            if trigger in query_lower:
                relevant.update(self._trigger_index[trigger])

        # 2. Semantic matching
        keywords = self._extract_keywords_from_query(query_lower)
        for keyword in keywords:
            if keyword in self._semantic_index:
                relevant.update(self._semantic_index[keyword])

        # 3. Category matching (fallback)
        for category, skills in self._category_index.items():
            if category in query_lower:
                relevant.update(skills)

        # Convert to list and sort by relevance
        result = list(relevant)
        result = self._sort_by_relevance(result, query_lower)

        # Track usage
        self._track_usage(query, result, time.time() - start_time)

        logger.debug(
            f"Found {len(result)} relevant skills for '{query}' in {time.time() - start_time:.3f}s"
        )
        return result

    def _sort_by_relevance(self, skills: list[str], query: str) -> list[str]:
        """Sort skills by relevance to query."""

        def relevance_score(skill_name: str) -> float:
            metadata = self._metadata_cache[skill_name]
            score = 0.0

            # Exact trigger matches get highest score
            for trigger in metadata.triggers:
                if trigger in query:
                    score += 10.0

            # Partial matches get medium score
            for trigger in metadata.triggers:
                if any(word in trigger for word in query.split()):
                    score += 5.0

            # Usage frequency bonus
            usage = self._usage_stats.get(skill_name, {})
            score += usage.get("frequency", 0) * 0.1

            return score

        return sorted(skills, key=relevance_score, reverse=True)

    def load_skill_summary(self, skill_name: str) -> SkillSummary:
        """Load only skill summary (token optimized)."""
        if skill_name in self._summary_cache:
            return self._summary_cache[skill_name]

        metadata = self._metadata_cache.get(skill_name)
        if not metadata:
            raise ValueError(f"Skill not found: {skill_name}")

        # Extract only essential information
        skill_file = metadata.skill_path / "SKILL.md"
        content = skill_file.read_text(encoding="utf-8")

        # Parse key sections
        quick_actions = self._extract_section(content, "Quick Actions")
        supported_frameworks = self._extract_section(content, "Supported Frameworks")
        resources = self._extract_resources(content)

        summary = SkillSummary(
            name=skill_name,
            quick_actions=quick_actions,
            supported_frameworks=supported_frameworks,
            resources=resources,
        )

        self._summary_cache[skill_name] = summary
        self._token_usage += summary.token_count

        return summary

    def _extract_section(self, content: str, section_name: str) -> list[str]:
        """Extract specific section from markdown content."""
        lines = content.split("\n")
        in_section = False
        section_lines = []

        for line in lines:
            if line.strip().startswith(f"## {section_name}"):
                in_section = True
                continue
            elif line.strip().startswith("## ") and in_section:
                break
            elif in_section and line.strip():
                # Clean up markdown formatting
                clean_line = re.sub(r"[*_`]", "", line.strip())
                if clean_line.startswith("- "):
                    clean_line = clean_line[2:]
                section_lines.append(clean_line)

        return section_lines

    def _extract_resources(self, content: str) -> dict[str, str]:
        """Extract resources section."""
        resources = {}
        lines = content.split("\n")
        in_resources = False

        for line in lines:
            if line.strip().startswith("## Resources"):
                in_resources = True
                continue
            elif line.strip().startswith("## ") and in_resources:
                break
            elif in_resources and line.strip().startswith("- **"):
                # Parse resource format: - **Scripts**: script1.py, script2.py
                match = re.match(r"- \*\*(\w+)\*\*: (.+)", line.strip())
                if match:
                    resource_type = match.group(1).lower()
                    resource_value = match.group(2)
                    resources[resource_type] = resource_value

        return resources

    def get_token_usage(self) -> dict[str, Any]:
        """Get token usage statistics."""
        return {
            "total_tokens_loaded": sum(
                m.token_count for m in self._metadata_cache.values()
            ),
            "summary_tokens": sum(s.token_count for s in self._summary_cache.values()),
            "cached_results": len(self._context_cache),
            "usage_stats": self._usage_stats,
            "optimization_ratio": self._calculate_optimization_ratio(),
        }

    def _calculate_optimization_ratio(self) -> float:
        """Calculate token optimization efficiency."""
        if not self._metadata_cache:
            return 0.0

        # Estimate what full loading would cost
        full_load_tokens = sum(
            len(open(m.skill_path / "SKILL.md").read().split())
            for m in self._metadata_cache.values()
        )

        current_tokens = self.get_token_usage()["total_tokens_loaded"]

        return (
            (full_load_tokens - current_tokens) / full_load_tokens
            if full_load_tokens > 0
            else 0.0
        )

    def _track_usage(self, query: str, skills: list[str], duration: float) -> None:
        """Track skill usage for optimization."""
        for skill_name in skills:
            if skill_name not in self._usage_stats:
                self._usage_stats[skill_name] = {
                    "frequency": 0,
                    "last_used": time.time(),
                    "total_queries": [],
                }

            stats = self._usage_stats[skill_name]
            stats["frequency"] += 1
            stats["last_used"] = time.time()
            stats["total_queries"].append(
                {"query": query, "timestamp": time.time(), "duration": duration}
            )

    def clear_cache(self) -> None:
        """Clear all caches to free memory."""
        self._summary_cache.clear()
        self._context_cache.clear()
        logger.info("Caches cleared")

    def optimize_indexes(self) -> None:
        """Optimize indexes based on usage patterns."""
        logger.info("Optimizing indexes based on usage patterns...")

        # Remove unused skills from memory
        unused_skills = [
            name
            for name, stats in self._usage_stats.items()
            if stats["frequency"] == 0 and time.time() - stats["last_used"] > 3600
        ]

        for skill_name in unused_skills:
            if skill_name in self._summary_cache:
                del self._summary_cache[skill_name]
            logger.debug(f"Removed unused skill from cache: {skill_name}")

        logger.info(f"Optimized: removed {len(unused_skills)} unused skills from cache")


def main():
    """Command line interface for Optimized Skill Manager."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Optimized Claude Agent Skills Manager"
    )
    parser.add_argument("--skills-dir", default="skills/", help="Skills directory path")
    parser.add_argument("--query", help="Find relevant skills for a query")
    parser.add_argument("--summary", help="Get skill summary")
    parser.add_argument(
        "--stats", action="store_true", help="Show token usage statistics"
    )
    parser.add_argument("--optimize", action="store_true", help="Optimize indexes")
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    manager = OptimizedSkillManager(args.skills_dir)

    if args.query:
        relevant = manager.get_relevant_skills(args.query)
        print(f"Relevant skills for '{args.query}' ({len(relevant)}):")
        for skill_name in relevant:
            metadata = manager._metadata_cache[skill_name]
            print(f"  - {skill_name}: {metadata.description[:80]}...")

    elif args.summary:
        try:
            summary = manager.load_skill_summary(args.summary)
            print(f"Summary for {args.summary}:")
            print(f"Quick Actions: {summary.quick_actions}")
            print(f"Supported Frameworks: {summary.supported_frameworks}")
            print(f"Resources: {summary.resources}")
        except ValueError as e:
            print(f"Error: {e}")

    elif args.stats:
        stats = manager.get_token_usage()
        print("Token Usage Statistics:")
        print(json.dumps(stats, indent=2))

    elif args.optimize:
        manager.optimize_indexes()
        print("Indexes optimized")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
