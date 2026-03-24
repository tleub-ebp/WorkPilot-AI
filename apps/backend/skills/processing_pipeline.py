#!/usr/bin/env python3
"""
Skill Processing Pipeline

Optimized pipeline for processing skill queries with multiple stages:
- Query preprocessing and normalization
- Skill matching and filtering
- Context-aware ranking
- Token optimization
- Result aggregation

Features:
- Modular pipeline stages
- Early exit optimization
- Performance monitoring
- Configurable processing
"""

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class PipelineContext:
    """Context passed through pipeline stages."""

    query: str
    original_query: str
    user_context: dict[str, Any]
    metadata: dict[str, Any]
    stage_results: dict[str, Any]

    def __post_init__(self):
        if not self.metadata:
            self.metadata = {}
        if not self.stage_results:
            self.stage_results = {}


@dataclass
class SkillMatch:
    """Represents a skill match with metadata."""

    skill_name: str
    confidence: float
    relevance_score: float
    token_cost: int
    metadata: dict[str, Any]

    def __post_init__(self):
        if not self.metadata:
            self.metadata = {}


class PipelineStage(ABC):
    """Abstract base class for pipeline stages."""

    @abstractmethod
    def process(self, context: PipelineContext) -> PipelineContext | None:
        """Process the context and return updated context or None for early exit."""
        pass

    @property
    @abstractmethod
    def stage_name(self) -> str:
        """Return the stage name for logging."""
        pass


class QueryPreprocessor(PipelineStage):
    """Preprocesses and normalizes queries."""

    def __init__(self, enable_stemming: bool = False, remove_stopwords: bool = True):
        self.enable_stemming = enable_stemming
        self.remove_stopwords = remove_stopwords
        self.stop_words = {
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
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
        }

    def process(self, context: PipelineContext) -> PipelineContext | None:
        """Preprocess the query."""
        start_time = time.time()

        # Normalize query
        normalized_query = self._normalize_query(context.query)

        # Extract key terms
        key_terms = self._extract_key_terms(normalized_query)

        # Update context
        context.query = normalized_query
        context.stage_results["preprocessor"] = {
            "original_length": len(context.original_query),
            "normalized_length": len(normalized_query),
            "key_terms": key_terms,
            "processing_time": time.time() - start_time,
        }

        logger.debug(
            f"Preprocessed query: '{context.original_query}' -> '{normalized_query}'"
        )
        return context

    def _normalize_query(self, query: str) -> str:
        """Normalize the query string."""
        # Convert to lowercase
        normalized = query.lower()

        # Remove special characters
        import re

        normalized = re.sub(r"[^\w\s]", " ", normalized)

        # Remove extra whitespace
        normalized = " ".join(normalized.split())

        return normalized

    def _extract_key_terms(self, query: str) -> list[str]:
        """Extract key terms from query."""
        words = query.split()

        if self.remove_stopwords:
            words = [word for word in words if word not in self.stop_words]

        # Filter by length
        key_terms = [word for word in words if len(word) > 2]

        # Remove duplicates while preserving order
        seen = set()
        unique_terms = []
        for term in key_terms:
            if term not in seen:
                seen.add(term)
                unique_terms.append(term)

        return unique_terms

    @property
    def stage_name(self) -> str:
        return "QueryPreprocessor"


class SkillMatcher(PipelineStage):
    """Matches skills against the processed query."""

    def __init__(self, skill_manager, min_confidence: float = 0.3):
        self.skill_manager = skill_manager
        self.min_confidence = min_confidence

    def process(self, context: PipelineContext) -> PipelineContext | None:
        """Match skills against query."""
        start_time = time.time()

        # Get relevant skills from manager
        relevant_skills = self.skill_manager.get_relevant_skills(context.query)

        # Create skill matches
        matches = []
        for skill_name in relevant_skills:
            confidence = self._calculate_confidence(skill_name, context)
            if confidence >= self.min_confidence:
                match = SkillMatch(
                    skill_name=skill_name,
                    confidence=confidence,
                    relevance_score=self._calculate_relevance(skill_name, context),
                    token_cost=self._estimate_token_cost(skill_name),
                    metadata={"source": "matcher"},
                )
                matches.append(match)

        # Sort by confidence
        matches.sort(key=lambda m: m.confidence, reverse=True)

        # Update context
        context.stage_results["matcher"] = {
            "matches_count": len(matches),
            "matches": matches,
            "processing_time": time.time() - start_time,
        }

        logger.debug(f"Found {len(matches)} skill matches")
        return context if matches else None  # Early exit if no matches

    def _calculate_confidence(self, skill_name: str, context: PipelineContext) -> float:
        """Calculate confidence score for skill match."""
        # Get skill metadata
        metadata = self.skill_manager.get_skill_info(skill_name)
        if not metadata:
            return 0.0

        confidence = 0.0

        # Exact trigger match
        query_lower = context.query.lower()
        for trigger in metadata.triggers:
            if trigger in query_lower:
                confidence += 0.8
                break

        # Partial keyword match
        key_terms = context.stage_results.get("preprocessor", {}).get("key_terms", [])
        for term in key_terms:
            if term in metadata.description.lower():
                confidence += 0.2

        # Category match
        if metadata.category.lower() in query_lower:
            confidence += 0.3

        return min(confidence, 1.0)

    def _calculate_relevance(self, skill_name: str, context: PipelineContext) -> float:
        """Calculate relevance score based on context."""
        relevance = 0.5  # Base relevance

        # User context relevance
        user_context = context.user_context
        if "project_type" in user_context:
            # Boost relevance for project-specific skills
            relevance += 0.2

        if "recent_skills" in user_context:
            recent_skills = user_context["recent_skills"]
            # Boost relevance for skills similar to recently used ones
            if skill_name in recent_skills:
                relevance += 0.3

        return min(relevance, 1.0)

    def _estimate_token_cost(self, skill_name: str) -> int:
        """Estimate token cost for skill."""
        try:
            summary = self.skill_manager.load_skill_summary(skill_name)
            return summary.token_count
        except Exception:
            return 1000  # Default estimate

    @property
    def stage_name(self) -> str:
        return "SkillMatcher"


class ContextFilter(PipelineStage):
    """Filters skills based on context and constraints."""

    def __init__(self, max_results: int = 10, max_tokens: int = 5000):
        self.max_results = max_results
        self.max_tokens = max_tokens

    def process(self, context: PipelineContext) -> PipelineContext | None:
        """Filter skills based on context."""
        start_time = time.time()

        matches = context.stage_results["matcher"]["matches"]

        # Apply filters
        filtered_matches = self._apply_filters(matches, context)

        # Limit results
        limited_matches = filtered_matches[: self.max_results]

        # Update context
        context.stage_results["filter"] = {
            "original_count": len(matches),
            "filtered_count": len(filtered_matches),
            "final_count": len(limited_matches),
            "matches": limited_matches,
            "processing_time": time.time() - start_time,
        }

        logger.debug(f"Filtered {len(matches)} -> {len(limited_matches)} matches")
        return context

    def _apply_filters(
        self, matches: list[SkillMatch], context: PipelineContext
    ) -> list[SkillMatch]:
        """Apply various filters to matches."""
        filtered = matches.copy()

        # Token budget filter
        total_tokens = sum(m.token_cost for m in filtered)
        if total_tokens > self.max_tokens:
            # Sort by token efficiency (confidence / token_cost)
            filtered.sort(
                key=lambda m: m.confidence / max(m.token_cost, 1), reverse=True
            )

            # Keep within token budget
            accumulated_tokens = 0
            token_filtered = []
            for match in filtered:
                if accumulated_tokens + match.token_cost <= self.max_tokens:
                    token_filtered.append(match)
                    accumulated_tokens += match.token_cost
                else:
                    break

            filtered = token_filtered

        # Context-based filters
        user_context = context.user_context
        if "excluded_skills" in user_context:
            excluded = set(user_context["excluded_skills"])
            filtered = [m for m in filtered if m.skill_name not in excluded]

        if "required_categories" in user_context:
            required = set(user_context["required_categories"])
            # This would require access to skill metadata
            # For now, just pass through

        return filtered

    @property
    def stage_name(self) -> str:
        return "ContextFilter"


class TokenOptimizer(PipelineStage):
    """Optimizes token usage for selected skills."""

    def __init__(self, enable_summaries: bool = True, enable_caching: bool = True):
        self.enable_summaries = enable_summaries
        self.enable_caching = enable_caching

    def process(self, context: PipelineContext) -> PipelineContext | None:
        """Optimize token usage."""
        start_time = time.time()

        matches = context.stage_results["filter"]["matches"]

        # Optimize each match
        optimized_matches = []
        for match in matches:
            optimized_match = self._optimize_match(match, context)
            optimized_matches.append(optimized_match)

        # Update context
        context.stage_results["optimizer"] = {
            "optimized_matches": optimized_matches,
            "original_tokens": sum(m.token_cost for m in matches),
            "optimized_tokens": sum(m.token_cost for m in optimized_matches),
            "token_savings": sum(m.token_cost for m in matches)
            - sum(m.token_cost for m in optimized_matches),
            "processing_time": time.time() - start_time,
        }

        return context

    def _optimize_match(
        self, match: SkillMatch, context: PipelineContext
    ) -> SkillMatch:
        """Optimize a single skill match."""
        optimized_match = SkillMatch(
            skill_name=match.skill_name,
            confidence=match.confidence,
            relevance_score=match.relevance_score,
            token_cost=match.token_cost,
            metadata=match.metadata.copy(),
        )

        # Apply optimizations
        if self.enable_summaries:
            # Use summary instead of full skill
            optimized_match.token_cost = int(optimized_match.token_cost * 0.3)
            optimized_match.metadata["using_summary"] = True

        if self.enable_caching and "cache_hit" in context.metadata:
            # Reduce cost for cached results
            optimized_match.token_cost = int(optimized_match.token_cost * 0.5)
            optimized_match.metadata["cached"] = True

        return optimized_match

    @property
    def stage_name(self) -> str:
        return "TokenOptimizer"


class ResultRanker(PipelineStage):
    """Ranks and aggregates final results."""

    def __init__(self, ranking_weights: dict[str, float] | None = None):
        self.ranking_weights = ranking_weights or {
            "confidence": 0.4,
            "relevance": 0.3,
            "token_efficiency": 0.2,
            "frequency": 0.1,
        }

    def process(self, context: PipelineContext) -> PipelineContext | None:
        """Rank and aggregate final results."""
        start_time = time.time()

        matches = context.stage_results["optimizer"]["optimized_matches"]

        # Calculate final scores
        ranked_matches = []
        for match in matches:
            final_score = self._calculate_final_score(match, context)
            ranked_match = SkillMatch(
                skill_name=match.skill_name,
                confidence=match.confidence,
                relevance_score=match.relevance_score,
                token_cost=match.token_cost,
                metadata={**match.metadata, "final_score": final_score},
            )
            ranked_matches.append(ranked_match)

        # Sort by final score
        ranked_matches.sort(key=lambda m: m.metadata["final_score"], reverse=True)

        # Create final result
        final_result = {
            "query": context.original_query,
            "processed_query": context.query,
            "matches": ranked_matches,
            "total_matches": len(ranked_matches),
            "processing_time": time.time() - start_time,
            "pipeline_stages": list(context.stage_results.keys()),
            "metadata": {
                "total_tokens": sum(m.token_cost for m in ranked_matches),
                "avg_confidence": sum(m.confidence for m in ranked_matches)
                / len(ranked_matches)
                if ranked_matches
                else 0,
                "high_confidence_count": sum(
                    1 for m in ranked_matches if m.confidence > 0.7
                ),
            },
        }

        context.stage_results["final"] = final_result
        return context

    def _calculate_final_score(
        self, match: SkillMatch, context: PipelineContext
    ) -> float:
        """Calculate final ranking score."""
        score = 0.0

        # Confidence score
        score += match.confidence * self.ranking_weights["confidence"]

        # Relevance score
        score += match.relevance_score * self.ranking_weights["relevance"]

        # Token efficiency (inverse of token cost)
        token_efficiency = (
            1.0 / (match.token_cost / 100) if match.token_cost > 0 else 1.0
        )
        score += min(token_efficiency, 1.0) * self.ranking_weights["token_efficiency"]

        # Frequency bonus (if available)
        user_context = context.user_context
        if "skill_frequencies" in user_context:
            freq = user_context["skill_frequencies"].get(match.skill_name, 0)
            freq_score = min(freq / 10.0, 1.0)  # Normalize to 0-1
            score += freq_score * self.ranking_weights["frequency"]

        return min(score, 1.0)

    @property
    def stage_name(self) -> str:
        return "ResultRanker"


class SkillProcessingPipeline:
    """Main pipeline for processing skill queries."""

    def __init__(self, skill_manager, config: dict | None = None):
        self.skill_manager = skill_manager
        self.config = config or {}

        # Initialize pipeline stages
        self.stages = [
            QueryPreprocessor(
                enable_stemming=self.config.get("enable_stemming", False),
                remove_stopwords=self.config.get("remove_stopwords", True),
            ),
            SkillMatcher(
                skill_manager=skill_manager,
                min_confidence=self.config.get("min_confidence", 0.3),
            ),
            ContextFilter(
                max_results=self.config.get("max_results", 10),
                max_tokens=self.config.get("max_tokens", 5000),
            ),
            TokenOptimizer(
                enable_summaries=self.config.get("enable_summaries", True),
                enable_caching=self.config.get("enable_caching", True),
            ),
            ResultRanker(ranking_weights=self.config.get("ranking_weights")),
        ]

        self.pipeline_stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "stage_timings": {},
            "average_processing_time": 0.0,
        }

    def process(self, query: str, user_context: dict | None = None) -> dict | None:
        """Process a query through the pipeline."""
        start_time = time.time()

        # Initialize context
        context = PipelineContext(
            query=query,
            original_query=query,
            user_context=user_context or {},
            metadata={},
            stage_results={},
        )

        # Process through stages
        for stage in self.stages:
            stage_start = time.time()

            try:
                context = stage.process(context)
                if context is None:
                    # Early exit
                    logger.debug(f"Pipeline early exit at stage: {stage.stage_name}")
                    break
            except Exception as e:
                logger.error(f"Error in stage {stage.stage_name}: {e}")
                context.stage_results[f"{stage.stage_name}_error"] = str(e)
                break

            # Record stage timing
            stage_time = time.time() - stage_start
            if stage.stage_name not in self.pipeline_stats["stage_timings"]:
                self.pipeline_stats["stage_timings"][stage.stage_name] = []
            self.pipeline_stats["stage_timings"][stage.stage_name].append(stage_time)

        # Update stats
        total_time = time.time() - start_time
        self.pipeline_stats["total_requests"] += 1
        if "final" in context.stage_results:
            self.pipeline_stats["successful_requests"] += 1

        # Update average processing time
        total_processed = self.pipeline_stats["total_requests"]
        current_avg = self.pipeline_stats["average_processing_time"]
        self.pipeline_stats["average_processing_time"] = (
            current_avg * (total_processed - 1) + total_time
        ) / total_processed

        return context.stage_results.get("final")

    def get_pipeline_stats(self) -> dict:
        """Get comprehensive pipeline statistics."""
        stats = self.pipeline_stats.copy()

        # Calculate stage averages
        stage_averages = {}
        for stage_name, timings in stats["stage_timings"].items():
            if timings:
                stage_averages[stage_name] = sum(timings) / len(timings)

        stats["stage_averages"] = stage_averages
        stats["success_rate"] = (
            stats["successful_requests"] / stats["total_requests"]
            if stats["total_requests"] > 0
            else 0.0
        )

        return stats

    def add_stage(self, stage: PipelineStage, position: int | None = None):
        """Add a custom stage to the pipeline."""
        if position is None:
            self.stages.append(stage)
        else:
            self.stages.insert(position, stage)

        logger.info(f"Added stage {stage.stage_name} to pipeline")

    def remove_stage(self, stage_name: str):
        """Remove a stage from the pipeline."""
        self.stages = [s for s in self.stages if s.stage_name != stage_name]
        logger.info(f"Removed stage {stage_name} from pipeline")
