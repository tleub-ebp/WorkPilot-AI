#!/usr/bin/env python3
"""
Context Cache Integration for Agent Workflows

Integrates intelligent context caching into existing agent workflows
to accelerate repetitive and similar builds.
"""

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Import cache services
from .git_cache_invalidation import GitBasedCacheInvalidator
from .intelligent_context_cache import CacheConfig, get_context_cache


@dataclass
class ContextRequest:
    """Request for context generation with caching."""

    # Core request data
    task_type: str
    target_files: list[str]
    frameworks: list[str]
    patterns: list[str]
    scope: str = "full"

    # Optional metadata
    agent_type: str | None = None
    build_id: str | None = None
    user_context: dict[str, Any] | None = None

    # Cache options
    use_cache: bool = True
    cache_result: bool = True
    semantic_matching: bool = True


@dataclass
class ContextResponse:
    """Response from context generation with caching."""

    context_data: dict[str, Any]
    cache_hit: bool = False
    cache_key: str | None = None
    build_time_saved: float = 0.0
    tokens_saved: int = 0
    freshness_score: float = 1.0
    metadata: dict[str, Any] = None


class ContextCacheIntegrator:
    """Integrates context caching into agent workflows."""

    def __init__(self, project_path: Path, config: CacheConfig | None = None):
        self.project_path = project_path
        self.context_cache = get_context_cache(project_path, config)
        self.git_invalidator = GitBasedCacheInvalidator(
            project_path, self.context_cache
        )

        # Statistics
        self.integration_stats = {
            "total_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "total_time_saved": 0.0,
            "total_tokens_saved": 0,
        }

        # Start git monitoring
        self.git_invalidator.start_monitoring()

    def get_context_with_cache(
        self, request: ContextRequest, context_generator: callable
    ) -> ContextResponse:
        """Get context with intelligent caching."""
        start_time = time.time()
        self.integration_stats["total_requests"] += 1

        # Build cache request
        cache_request = {
            "task_type": request.task_type,
            "target_files": request.target_files,
            "frameworks": request.frameworks,
            "patterns": request.patterns,
            "scope": request.scope,
            "agent_type": request.agent_type,
        }

        # Try to get from cache
        cached_context = None
        cache_hit = False

        if request.use_cache:
            cached_context = self.context_cache.get_context(cache_request)
            if cached_context:
                cache_hit = True
                self.integration_stats["cache_hits"] += 1
                logger.info(f"Cache hit for {request.task_type} task")
            else:
                self.integration_stats["cache_misses"] += 1
                logger.info(f"Cache miss for {request.task_type} task")

        # Generate context if not cached
        if cached_context:
            context_data = cached_context
            build_time = time.time() - start_time
            time_saved = build_time  # Full build time saved
            tokens_saved = self._estimate_tokens_saved(context_data)
        else:
            # Generate context using provided generator
            logger.info(f"Generating context for {request.task_type} task")
            context_data = context_generator(request)

            build_time = time.time() - start_time
            time_saved = 0.0
            tokens_saved = 0

            # Cache the result if requested
            if request.cache_result:
                cache_key = self.context_cache.cache_context(
                    cache_request,
                    context_data,
                    build_time,
                    self._estimate_tokens_used(context_data),
                )
                logger.info(f"Cached context with key {cache_key[:8]}...")

        # Update statistics
        self.integration_stats["total_time_saved"] += time_saved
        self.integration_stats["total_tokens_saved"] += tokens_saved

        # Get freshness score if available
        freshness_score = 1.0
        if cache_hit:
            # Try to get freshness from cache entry
            cache_key = self._generate_cache_key(cache_request)
            with self.context_cache._cache_lock:
                if cache_key in self.context_cache._cache:
                    entry = self.context_cache._cache[cache_key]
                    freshness_score = entry.freshness_score

        return ContextResponse(
            context_data=context_data,
            cache_hit=cache_hit,
            cache_key=self._generate_cache_key(cache_request) if cache_hit else None,
            build_time_saved=time_saved,
            tokens_saved=tokens_saved,
            freshness_score=freshness_score,
            metadata={
                "task_type": request.task_type,
                "agent_type": request.agent_type,
                "build_id": request.build_id,
                "request_timestamp": start_time,
            },
        )

    def invalidate_context_cache(self, pattern: str | None = None):
        """Invalidate context cache entries."""
        self.context_cache.invalidate_cache(pattern)
        logger.info(f"Invalidated context cache with pattern: {pattern}")

    def get_integration_stats(self) -> dict[str, Any]:
        """Get integration statistics."""
        total_requests = self.integration_stats["total_requests"]
        hit_rate = (
            self.integration_stats["cache_hits"] / total_requests
            if total_requests > 0
            else 0.0
        )

        # Get cache statistics
        cache_stats = self.context_cache.get_cache_stats()

        # Get git invalidation statistics
        git_stats = self.git_invalidator.get_statistics()

        return {
            "integration_stats": {
                "total_requests": total_requests,
                "cache_hits": self.integration_stats["cache_hits"],
                "cache_misses": self.integration_stats["cache_misses"],
                "hit_rate": hit_rate,
                "total_time_saved": self.integration_stats["total_time_saved"],
                "total_tokens_saved": self.integration_stats["total_tokens_saved"],
            },
            "cache_stats": cache_stats,
            "git_stats": git_stats,
        }

    def _generate_cache_key(self, cache_request: dict[str, Any]) -> str:
        """Generate cache key from request."""
        import hashlib
        import json

        normalized = {
            "task_type": cache_request.get("task_type", ""),
            "target_files": sorted(cache_request.get("target_files", [])),
            "frameworks": sorted(cache_request.get("frameworks", [])),
            "patterns": sorted(cache_request.get("patterns", [])),
            "scope": cache_request.get("scope", "full"),
        }

        key_str = json.dumps(normalized, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()

    def _estimate_tokens_saved(self, context_data: dict[str, Any]) -> int:
        """Estimate tokens saved by cache hit."""
        # Rough estimation based on context size
        context_str = json.dumps(context_data, default=str)
        estimated_tokens = len(context_str) // 4  # Rough estimate: 1 token ≈ 4 chars

        return max(1000, estimated_tokens)  # Minimum 1000 tokens saved

    def _estimate_tokens_used(self, context_data: dict[str, Any]) -> int:
        """Estimate tokens used to generate context."""
        # Similar to tokens saved estimation
        return self._estimate_tokens_saved(context_data)

    def cleanup(self):
        """Cleanup resources."""
        self.git_invalidator.stop_monitoring()


class AgentWorkflowIntegrator:
    """Integrates context caching into specific agent workflows."""

    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.cache_integrator = ContextCacheIntegrator(project_path)

        # Workflow-specific generators
        self.context_generators = {}
        self._setup_default_generators()

    def _setup_default_generators(self):
        """Setup default context generators for different agent types."""

        def analysis_context_generator(request: ContextRequest) -> dict[str, Any]:
            """Generate context for analysis agents."""
            from ..analysis.analyzers.context_analyzer import ContextAnalyzer
            from ..analysis.project_analyzer import ProjectAnalyzer

            # Create analysis context
            analyzer = ContextAnalyzer(self.project_path, {})
            project_analyzer = ProjectAnalyzer(self.project_path)

            context = {
                "task_type": "analysis",
                "project_structure": project_analyzer.analyze_structure(),
                "dependencies": project_analyzer.analyze_dependencies(),
                "frameworks": request.frameworks,
                "target_files": request.target_files,
                "patterns": request.patterns,
                "generated_at": time.time(),
            }

            # Run specific analyzers
            analyzer.detect_environment_variables()
            analyzer.detect_external_services()
            analyzer.detect_auth_patterns()

            context.update(analyzer.analysis)

            return context

        def coding_context_generator(request: ContextRequest) -> dict[str, Any]:
            """Generate context for coding agents."""
            from ..analysis.project_analyzer import ProjectAnalyzer

            project_analyzer = ProjectAnalyzer(self.project_path)

            context = {
                "task_type": "coding",
                "project_structure": project_analyzer.analyze_structure(),
                "dependencies": project_analyzer.analyze_dependencies(),
                "frameworks": request.frameworks,
                "target_files": request.target_files,
                "code_patterns": request.patterns,
                "conventions": project_analyzer.analyze_conventions(),
                "imports": project_analyzer.analyze_imports(),
                "generated_at": time.time(),
            }

            return context

        def qa_context_generator(request: ContextRequest) -> dict[str, Any]:
            """Generate context for QA agents."""
            from ..analysis.project_analyzer import ProjectAnalyzer

            project_analyzer = ProjectAnalyzer(self.project_path)

            context = {
                "task_type": "qa",
                "project_structure": project_analyzer.analyze_structure(),
                "test_files": project_analyzer.find_test_files(),
                "dependencies": project_analyzer.analyze_dependencies(),
                "frameworks": request.frameworks,
                "target_files": request.target_files,
                "quality_metrics": project_analyzer.analyze_quality_metrics(),
                "generated_at": time.time(),
            }

            return context

        # Register generators
        self.context_generators["analysis"] = analysis_context_generator
        self.context_generators["coding"] = coding_context_generator
        self.context_generators["qa"] = qa_context_generator
        self.context_generators["planning"] = (
            analysis_context_generator  # Use analysis for planning
        )
        self.context_generators["review"] = (
            analysis_context_generator  # Use analysis for review
        )

    def get_agent_context(
        self, agent_type: str, request_data: dict[str, Any]
    ) -> ContextResponse:
        """Get context for a specific agent type."""
        # Build context request
        request = ContextRequest(
            task_type=request_data.get("task_type", agent_type),
            target_files=request_data.get("target_files", []),
            frameworks=request_data.get("frameworks", []),
            patterns=request_data.get("patterns", []),
            scope=request_data.get("scope", "full"),
            agent_type=agent_type,
            build_id=request_data.get("build_id"),
            user_context=request_data.get("user_context"),
            use_cache=request_data.get("use_cache", True),
            cache_result=request_data.get("cache_result", True),
            semantic_matching=request_data.get("semantic_matching", True),
        )

        # Get appropriate generator
        generator = self.context_generators.get(agent_type)
        if not generator:
            # Fallback to analysis generator
            generator = self.context_generators["analysis"]
            logger.warning(
                f"No specific generator for {agent_type}, using analysis generator"
            )

        # Get context with caching
        return self.cache_integrator.get_context_with_cache(request, generator)

    def register_context_generator(self, agent_type: str, generator: callable):
        """Register a custom context generator for an agent type."""
        self.context_generators[agent_type] = generator
        logger.info(f"Registered custom context generator for {agent_type}")

    def get_workflow_stats(self) -> dict[str, Any]:
        """Get workflow integration statistics."""
        return self.cache_integrator.get_integration_stats()

    def invalidate_workflow_cache(self, agent_type: str | None = None):
        """Invalidate cache for specific agent type or all."""
        pattern = f"*{agent_type}*" if agent_type else None
        self.cache_integrator.invalidate_context_cache(pattern)

    def cleanup(self):
        """Cleanup workflow integration resources."""
        self.cache_integrator.cleanup()


# Global workflow integrators
_workflow_integrators: dict[str, AgentWorkflowIntegrator] = {}


def get_workflow_integrator(project_path: Path) -> AgentWorkflowIntegrator:
    """Get or create workflow integrator for a project."""
    project_key = str(project_path.resolve())

    if project_key not in _workflow_integrators:
        _workflow_integrators[project_key] = AgentWorkflowIntegrator(project_path)

    return _workflow_integrators[project_key]


def cleanup_all_integrators():
    """Cleanup all workflow integrators."""
    for integrator in _workflow_integrators.values():
        integrator.cleanup()

    _workflow_integrators.clear()


# Decorator for automatic context caching
def cached_context(agent_type: str):
    """Decorator to automatically add context caching to agent functions."""

    def decorator(func):
        def wrapper(*args, **kwargs):
            # Extract project path from kwargs or args
            project_path = kwargs.get("project_path")
            if not project_path and args:
                project_path = args[0]

            if not project_path:
                logger.warning("No project path provided for cached context")
                return func(*args, **kwargs)

            # Get workflow integrator
            integrator = get_workflow_integrator(Path(project_path))

            # Build request data
            request_data = {
                "task_type": kwargs.get("task_type", agent_type),
                "target_files": kwargs.get("target_files", []),
                "frameworks": kwargs.get("frameworks", []),
                "patterns": kwargs.get("patterns", []),
                "scope": kwargs.get("scope", "full"),
                "build_id": kwargs.get("build_id"),
                "user_context": kwargs.get("user_context"),
                "use_cache": kwargs.get("use_cache", True),
                "cache_result": kwargs.get("cache_result", True),
                "semantic_matching": kwargs.get("semantic_matching", True),
            }

            # Get context with caching
            context_response = integrator.get_agent_context(agent_type, request_data)

            # Add context to kwargs
            kwargs["cached_context"] = context_response.context_data
            kwargs["cache_metadata"] = {
                "cache_hit": context_response.cache_hit,
                "time_saved": context_response.build_time_saved,
                "tokens_saved": context_response.tokens_saved,
                "freshness_score": context_response.freshness_score,
            }

            # Call original function
            return func(*args, **kwargs)

        return wrapper

    return decorator
