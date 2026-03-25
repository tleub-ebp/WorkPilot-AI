#!/usr/bin/env python3
"""
Intelligent Context Caching Service

Implements semantic caching of agent context to accelerate repetitive and similar builds.
Features:
- Semantic similarity analysis for cache matching
- Freshness scoring based on git commits and file changes
- Intelligent invalidation strategies
- Performance optimization for context building
- Integration with existing context and project analysis systems
"""

import hashlib
import json
import logging
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# SQL query constants
DELETE_CACHE_ENTRY_QUERY = "DELETE FROM context_cache WHERE cache_key = ?"


@dataclass
class ContextCacheEntry:
    """Represents a cached context entry with metadata."""

    # Cache key and content
    cache_key: str
    context_hash: str
    context_data: dict[str, Any]

    # Metadata
    created_at: float
    last_accessed: float
    access_count: int = 0

    # Freshness metrics
    freshness_score: float = 1.0
    git_commit_hash: str = ""
    files_changed: set[str] = field(default_factory=set)

    # Performance metrics
    build_time_saved: float = 0.0
    tokens_saved: int = 0

    # Similarity data
    semantic_signature: str = ""
    dependency_graph_hash: str = ""


@dataclass
class CacheConfig:
    """Configuration for the context caching system."""

    # Cache settings
    max_cache_size: int = 100
    max_entry_age_hours: float = 24.0
    freshness_threshold: float = 0.7

    # Semantic analysis
    similarity_threshold: float = 0.8
    enable_semantic_matching: bool = True

    # Performance
    enable_background_refresh: bool = True
    refresh_interval_minutes: float = 30.0

    # Database
    db_path: str = "context_cache.db"


class SemanticHasher:
    """Generates semantic hashes for context comparison."""

    def __init__(self):
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
            "being",
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

    def generate_semantic_signature(self, context_data: dict[str, Any]) -> str:
        """Generate semantic signature from context data."""
        # Extract key terms from context
        terms = self._extract_terms(context_data)

        # Remove stop words and normalize
        filtered_terms = [
            term.lower()
            for term in terms
            if term.lower() not in self.stop_words and len(term) > 2
        ]

        # Sort for consistency and create signature
        sorted_terms = sorted(set(filtered_terms))
        signature_text = " ".join(sorted_terms)

        return hashlib.sha256(signature_text.encode()).hexdigest()[:16]

    def _extract_terms(self, context_data: dict[str, Any]) -> list[str]:
        """Extract meaningful terms from context data."""
        terms = []

        # Extract from different context sections
        if "project_structure" in context_data:
            terms.extend(
                self._extract_from_structure(context_data["project_structure"])
            )

        if "dependencies" in context_data:
            terms.extend(context_data["dependencies"].keys())

        if "frameworks" in context_data:
            terms.extend(context_data["frameworks"])

        if "patterns" in context_data:
            patterns = context_data["patterns"]
            if isinstance(patterns, dict):
                terms.extend(patterns.keys())
            elif isinstance(patterns, list):
                terms.extend(patterns)

        if "description" in context_data:
            # Extract terms from description
            desc_terms = context_data["description"].split()
            terms.extend(desc_terms)

        return terms

    def _extract_from_structure(self, structure: dict) -> list[str]:
        """Extract terms from project structure."""
        terms = []

        for file_path, file_info in structure.items():
            # Extract from file paths
            path_parts = file_path.split("/")
            terms.extend(path_parts)

            # Extract from file types
            if "." in file_path:
                file_type = file_path.split(".")[-1]
                terms.append(file_type)

            # Extract from file content if available
            if isinstance(file_info, dict) and "content" in file_info:
                content_terms = file_info["content"].split()[
                    :50
                ]  # Limit to first 50 terms
                terms.extend(content_terms)

        return terms

    def calculate_similarity(self, signature1: str, signature2: str) -> float:
        """Calculate similarity between two semantic signatures."""
        if signature1 == signature2:
            return 1.0

        # For simplicity, use Hamming distance on the hex strings
        # In a more sophisticated implementation, we could use word embeddings
        common_chars = sum(c1 == c2 for c1, c2 in zip(signature1, signature2))
        max_len = max(len(signature1), len(signature2))

        return common_chars / max_len if max_len > 0 else 0.0


class FreshnessScorer:
    """Calculates freshness scores for cache entries."""

    def __init__(self):
        self.git_integration = GitIntegration()

    def calculate_freshness_score(
        self, entry: ContextCacheEntry, project_path: Path
    ) -> float:
        """Calculate freshness score based on various factors."""
        current_time = time.time()

        # Age factor (newer is better)
        age_hours = (current_time - entry.created_at) / 3600
        age_score = max(0.0, 1.0 - (age_hours / 24.0))  # Decay over 24 hours

        # Git changes factor
        git_score = self._calculate_git_freshness(entry, project_path)

        # File changes factor
        file_score = self._calculate_file_freshness(entry, project_path)

        # Access pattern factor (frequently accessed is more valuable)
        access_score = min(1.0, entry.access_count / 10.0)

        # Combine scores with weights
        total_score = (
            age_score * 0.3 + git_score * 0.4 + file_score * 0.2 + access_score * 0.1
        )

        return total_score

    def _calculate_git_freshness(
        self, entry: ContextCacheEntry, project_path: Path
    ) -> float:
        """Calculate freshness based on git commits."""
        try:
            current_commit = self.git_integration.get_current_commit(project_path)

            if entry.git_commit_hash == current_commit:
                return 1.0  # No changes since caching

            # Check if cached commit is ancestor of current
            if self.git_integration.is_ancestor(
                project_path, entry.git_commit_hash, current_commit
            ):
                # Count commits between
                commits_between = self.git_integration.count_commits_between(
                    project_path, entry.git_commit_hash, current_commit
                )
                return max(0.0, 1.0 - (commits_between / 10.0))  # Decay over 10 commits
            else:
                # Branch diverged - low freshness
                return 0.2

        except Exception as e:
            logger.warning(f"Error calculating git freshness: {e}")
            return 0.5  # Default score

    def _calculate_file_freshness(
        self, entry: ContextCacheEntry, project_path: Path
    ) -> float:
        """Calculate freshness based on file changes."""
        if not entry.files_changed:
            return 1.0  # No files to check

        try:
            changed_files = self.git_integration.get_changed_files_since(
                project_path, entry.git_commit_hash
            )

            # Calculate overlap between cached files and changed files
            overlap = len(entry.files_changed.intersection(changed_files))
            total_cached_files = len(entry.files_changed)

            if total_cached_files == 0:
                return 1.0

            # Lower score if many cached files have changed
            change_ratio = overlap / total_cached_files
            return max(0.0, 1.0 - change_ratio)

        except Exception as e:
            logger.warning(f"Error calculating file freshness: {e}")
            return 0.5


class GitIntegration:
    """Integration with git for cache invalidation."""

    def get_current_commit(self, project_path: Path) -> str:
        """Get current git commit hash."""
        import subprocess

        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception as e:
            logger.warning(f"Error getting current commit: {e}")

        return ""

    def is_ancestor(
        self, project_path: Path, ancestor_hash: str, descendant_hash: str
    ) -> bool:
        """Check if ancestor_hash is ancestor of descendant_hash."""
        import subprocess

        try:
            result = subprocess.run(
                ["git", "merge-base", "--is-ancestor", ancestor_hash, descendant_hash],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0
        except Exception as e:
            logger.warning(f"Error checking ancestor relationship: {e}")

        return False

    def count_commits_between(
        self, project_path: Path, from_hash: str, to_hash: str
    ) -> int:
        """Count commits between two hashes."""
        import subprocess

        try:
            result = subprocess.run(
                ["git", "rev-list", "--count", f"{from_hash}..{to_hash}"],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return int(result.stdout.strip())
        except Exception as e:
            logger.warning(f"Error counting commits: {e}")

        return 0

    def get_changed_files_since(self, project_path: Path, commit_hash: str) -> set[str]:
        """Get files changed since specified commit."""
        import subprocess

        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", commit_hash, "HEAD"],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return (
                    set(result.stdout.strip().split("\n"))
                    if result.stdout.strip()
                    else set()
                )
        except Exception as e:
            logger.warning(f"Error getting changed files: {e}")

        return set()


class IntelligentContextCache:
    """Main intelligent context caching service."""

    def __init__(self, project_path: Path, config: CacheConfig | None = None):
        self.project_path = project_path
        self.config = config or CacheConfig()

        # Components
        self.semantic_hasher = SemanticHasher()
        self.freshness_scorer = FreshnessScorer()

        # In-memory cache
        self._cache: dict[str, ContextCacheEntry] = {}
        self._cache_lock = threading.RLock()

        # Database setup
        self._init_database()

        # Performance tracking
        self.stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "semantic_hits": 0,
            "total_time_saved": 0.0,
            "total_tokens_saved": 0,
        }

        # Load existing cache
        self._load_cache_from_db()

    def close(self):
        """Close database connections and cleanup resources."""
        with self._cache_lock:
            self._cache.clear()
        # On Windows, run a WAL checkpoint so SQLite releases journal files
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        except Exception:
            pass  # Ignore errors during cleanup
        # Force garbage collection to help with file locks on Windows
        import gc

        gc.collect()

    def __del__(self):
        """Cleanup when object is destroyed."""
        try:
            self.close()
        except Exception:
            pass  # Ignore errors during cleanup

    def _init_database(self):
        """Initialize SQLite database for persistent cache."""
        self.db_path = self.project_path / ".workpilot" / self.config.db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS context_cache (
                    cache_key TEXT PRIMARY KEY,
                    context_hash TEXT NOT NULL,
                    context_data TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    last_accessed REAL NOT NULL,
                    access_count INTEGER DEFAULT 0,
                    freshness_score REAL DEFAULT 1.0,
                    git_commit_hash TEXT DEFAULT "",
                    files_changed TEXT DEFAULT "",
                    build_time_saved REAL DEFAULT 0.0,
                    tokens_saved INTEGER DEFAULT 0,
                    semantic_signature TEXT DEFAULT "",
                    dependency_graph_hash TEXT DEFAULT ""
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_semantic_signature
                ON context_cache(semantic_signature)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_created_at
                ON context_cache(created_at)
            """)

    def get_context(self, context_request: dict[str, Any]) -> dict[str, Any] | None:
        """Get context from cache, using semantic matching if needed."""
        start_time = time.time()

        # Generate cache key
        cache_key = self._generate_cache_key(context_request)

        with self._cache_lock:
            # Direct cache hit
            if cache_key in self._cache:
                entry = self._cache[cache_key]
                self._update_access(entry)
                self.stats["cache_hits"] += 1

                # Update freshness score
                entry.freshness_score = self.freshness_scorer.calculate_freshness_score(
                    entry, self.project_path
                )

                # Save updated stats
                self._save_entry_to_db(entry)

                build_time = time.time() - start_time
                entry.build_time_saved += build_time
                self.stats["total_time_saved"] += build_time

                logger.info(
                    f"Cache hit for key {cache_key[:8]}... (saved {build_time:.2f}s)"
                )
                return entry.context_data.copy()

        # Semantic cache matching
        if self.config.enable_semantic_matching:
            semantic_match = self._find_semantic_match(context_request)
            if semantic_match:
                self.stats["semantic_hits"] += 1

                build_time = time.time() - start_time
                semantic_match.build_time_saved += build_time
                self.stats["total_time_saved"] += build_time

                logger.info(f"Semantic match found (saved {build_time:.2f}s)")
                return semantic_match.context_data.copy()

        # Cache miss
        self.stats["cache_misses"] += 1
        logger.info(f"Cache miss for key {cache_key[:8]}...")
        return None

    def cache_context(
        self,
        context_request: dict[str, Any],
        context_data: dict[str, Any],
        build_time: float = 0.0,
        tokens_used: int = 0,
    ) -> str:
        """Cache context data with intelligent metadata."""
        # Generate cache keys and signatures
        cache_key = self._generate_cache_key(context_request)
        context_hash = self._generate_context_hash(context_data)
        semantic_signature = self.semantic_hasher.generate_semantic_signature(
            context_data
        )

        # Get current git state
        current_commit = self.freshness_scorer.git_integration.get_current_commit(
            self.project_path
        )

        # Extract files from context
        files_changed = self._extract_files_from_context(context_data)

        # Create cache entry
        entry = ContextCacheEntry(
            cache_key=cache_key,
            context_hash=context_hash,
            context_data=context_data,
            created_at=time.time(),
            last_accessed=time.time(),
            access_count=1,
            freshness_score=1.0,
            git_commit_hash=current_commit,
            files_changed=files_changed,
            build_time_saved=build_time,
            tokens_saved=tokens_used,
            semantic_signature=semantic_signature,
            dependency_graph_hash=self._generate_dependency_hash(context_data),
        )

        with self._cache_lock:
            # Check cache size limit
            if len(self._cache) >= self.config.max_cache_size:
                self._evict_least_fresh()

            # Add to cache
            self._cache[cache_key] = entry

            # Save to database
            self._save_entry_to_db(entry)

        logger.info(
            f"Cached context with key {cache_key[:8]}... ({len(context_data)} items)"
        )
        return cache_key

    def _find_semantic_match(
        self, context_request: dict[str, Any]
    ) -> ContextCacheEntry | None:
        """Find semantically similar cached context."""
        request_signature = self.semantic_hasher.generate_semantic_signature(
            context_request
        )

        with self._cache_lock:
            best_match = None
            best_similarity = 0.0

            for entry in self._cache.values():
                # Check freshness first
                if entry.freshness_score < self.config.freshness_threshold:
                    continue

                # Calculate semantic similarity
                similarity = self.semantic_hasher.calculate_similarity(
                    request_signature, entry.semantic_signature
                )

                if (
                    similarity > best_similarity
                    and similarity >= self.config.similarity_threshold
                ):
                    best_similarity = similarity
                    best_match = entry

            if best_match:
                self._update_access(best_match)
                return best_match

        return None

    def _generate_cache_key(self, context_request: dict[str, Any]) -> str:
        """Generate cache key from context request."""
        # Normalize request for consistent key generation
        normalized = {
            "task_type": context_request.get("task_type", ""),
            "target_files": sorted(context_request.get("target_files", [])),
            "frameworks": sorted(context_request.get("frameworks", [])),
            "patterns": sorted(context_request.get("patterns", [])),
            "scope": context_request.get("scope", "full"),
        }

        key_str = json.dumps(normalized, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()

    def _generate_context_hash(self, context_data: dict[str, Any]) -> str:
        """Generate hash for context data."""
        # Create deterministic representation
        normalized = json.dumps(context_data, sort_keys=True, default=str)
        return hashlib.sha256(normalized.encode()).hexdigest()

    def _generate_dependency_hash(self, context_data: dict[str, Any]) -> str:
        """Generate hash for dependency graph."""
        dependencies = []

        if "dependencies" in context_data:
            dependencies.extend(context_data["dependencies"].keys())

        if "imports" in context_data:
            for file_imports in context_data["imports"].values():
                dependencies.extend(file_imports)

        dependencies = sorted(set(dependencies))
        dep_str = json.dumps(dependencies, sort_keys=True)
        return hashlib.sha256(dep_str.encode()).hexdigest()

    def _extract_files_from_context(self, context_data: dict[str, Any]) -> set[str]:
        """Extract file paths from context data."""
        files = set()

        if "project_structure" in context_data:
            files.update(context_data["project_structure"].keys())

        if "target_files" in context_data:
            files.update(context_data["target_files"])

        if "files" in context_data:
            files.update(context_data["files"])

        return files

    def _update_access(self, entry: ContextCacheEntry):
        """Update access statistics for entry."""
        entry.last_accessed = time.time()
        entry.access_count += 1

    def _evict_least_fresh(self):
        """Evict least fresh entry from cache."""
        if not self._cache:
            return

        # Find entry with lowest freshness score
        worst_entry = min(self._cache.values(), key=lambda e: e.freshness_score)

        del self._cache[worst_entry.cache_key]

        # Remove from database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                DELETE_CACHE_ENTRY_QUERY,
                (worst_entry.cache_key,),
            )

        logger.debug(f"Evicted cache entry {worst_entry.cache_key[:8]}...")

    def _save_entry_to_db(self, entry: ContextCacheEntry):
        """Save cache entry to database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO context_cache (
                    cache_key, context_hash, context_data, created_at, last_accessed,
                    access_count, freshness_score, git_commit_hash, files_changed,
                    build_time_saved, tokens_saved, semantic_signature, dependency_graph_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    entry.cache_key,
                    entry.context_hash,
                    json.dumps(entry.context_data),
                    entry.created_at,
                    entry.last_accessed,
                    entry.access_count,
                    entry.freshness_score,
                    entry.git_commit_hash,
                    json.dumps(list(entry.files_changed)),
                    entry.build_time_saved,
                    entry.tokens_saved,
                    entry.semantic_signature,
                    entry.dependency_graph_hash,
                ),
            )

    def _load_cache_from_db(self):
        """Load cache entries from database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT * FROM context_cache")
            rows = cursor.fetchall()

            for row in rows:
                try:
                    entry = ContextCacheEntry(
                        cache_key=row[0],
                        context_hash=row[1],
                        context_data=json.loads(row[2]),
                        created_at=row[3],
                        last_accessed=row[4],
                        access_count=row[5],
                        freshness_score=row[6],
                        git_commit_hash=row[7],
                        files_changed=set(json.loads(row[8])),
                        build_time_saved=row[9],
                        tokens_saved=row[10],
                        semantic_signature=row[11],
                        dependency_graph_hash=row[12],
                    )

                    # Update freshness score
                    entry.freshness_score = (
                        self.freshness_scorer.calculate_freshness_score(
                            entry, self.project_path
                        )
                    )

                    self._cache[entry.cache_key] = entry

                except Exception as e:
                    logger.warning(f"Error loading cache entry: {e}")

        logger.info(f"Loaded {len(self._cache)} cache entries from database")

    def invalidate_cache(self, pattern: str | None = None):
        """Invalidate cache entries, optionally filtered by pattern.

        The pattern is matched against the cache key, the semantic signature,
        and any string values in the context data (e.g. task_type).
        """
        with self._cache_lock:
            if pattern:
                # Invalidate entries matching pattern in key OR context data
                keys_to_remove = []
                for key, entry in self._cache.items():
                    if pattern in key:
                        keys_to_remove.append(key)
                    elif pattern in entry.semantic_signature:
                        keys_to_remove.append(key)
                    else:
                        # Check string values in context_data
                        context_str = json.dumps(entry.context_data, default=str)
                        if pattern in context_str:
                            keys_to_remove.append(key)
            else:
                # Invalidate all entries
                keys_to_remove = list(self._cache.keys())

            for key in keys_to_remove:
                del self._cache[key]

            # Remove from database
            with sqlite3.connect(self.db_path) as conn:
                if pattern:
                    for key in keys_to_remove:
                        conn.execute(
                            DELETE_CACHE_ENTRY_QUERY,
                            (key,),
                        )
                else:
                    conn.execute("DELETE FROM context_cache")

        logger.info(f"Invalidated {len(keys_to_remove)} cache entries")

    def get_cache_stats(self) -> dict[str, Any]:
        """Get comprehensive cache statistics."""
        with self._cache_lock:
            total_requests = self.stats["cache_hits"] + self.stats["cache_misses"]
            hit_rate = (
                self.stats["cache_hits"] / total_requests if total_requests > 0 else 0.0
            )

            # Calculate cache efficiency
            total_build_time_saved = sum(
                entry.build_time_saved for entry in self._cache.values()
            )
            total_tokens_saved = sum(
                entry.tokens_saved for entry in self._cache.values()
            )

            # Freshness distribution
            freshness_scores = [entry.freshness_score for entry in self._cache.values()]
            avg_freshness = (
                sum(freshness_scores) / len(freshness_scores)
                if freshness_scores
                else 0.0
            )

            return {
                "cache_size": len(self._cache),
                "max_cache_size": self.config.max_cache_size,
                "cache_hits": self.stats["cache_hits"],
                "cache_misses": self.stats["cache_misses"],
                "semantic_hits": self.stats["semantic_hits"],
                "hit_rate": hit_rate,
                "total_time_saved": total_build_time_saved,
                "total_tokens_saved": total_tokens_saved,
                "avg_freshness": avg_freshness,
                "freshness_threshold": self.config.freshness_threshold,
                "similarity_threshold": self.config.similarity_threshold,
                "semantic_matching_enabled": self.config.enable_semantic_matching,
            }

    def optimize_cache(self):
        """Optimize cache by removing stale entries and refreshing scores."""
        with self._cache_lock:
            # Update freshness scores
            for entry in self._cache.values():
                entry.freshness_score = self.freshness_scorer.calculate_freshness_score(
                    entry, self.project_path
                )

            # Remove stale entries
            stale_keys = [
                key
                for key, entry in self._cache.items()
                if entry.freshness_score < 0.3  # Very low freshness
            ]

            for key in stale_keys:
                del self._cache[key]

                with sqlite3.connect(self.db_path) as conn:
                    conn.execute(
                        DELETE_CACHE_ENTRY_QUERY, (key,)
                    )

            logger.info(f"Optimized cache: removed {len(stale_keys)} stale entries")

    def export_cache_data(self, filepath: str):
        """Export cache data for analysis."""
        export_data = {
            "config": {
                "max_cache_size": self.config.max_cache_size,
                "freshness_threshold": self.config.freshness_threshold,
                "similarity_threshold": self.config.similarity_threshold,
            },
            "stats": self.get_cache_stats(),
            "entries": [],
        }

        with self._cache_lock:
            for entry in self._cache.values():
                entry_data = {
                    "cache_key": entry.cache_key,
                    "created_at": entry.created_at,
                    "access_count": entry.access_count,
                    "freshness_score": entry.freshness_score,
                    "build_time_saved": entry.build_time_saved,
                    "tokens_saved": entry.tokens_saved,
                    "files_count": len(entry.files_changed),
                }
                export_data["entries"].append(entry_data)

        with open(filepath, "w") as f:
            json.dump(export_data, f, indent=2)

        logger.info(f"Exported cache data to {filepath}")


# Global instance registry
_cache_instances: dict[str, IntelligentContextCache] = {}
_cache_lock = threading.Lock()


def get_context_cache(
    project_path: Path, config: CacheConfig | None = None
) -> IntelligentContextCache:
    """Get or create context cache instance for project."""
    project_key = str(project_path.resolve())

    with _cache_lock:
        if project_key not in _cache_instances:
            _cache_instances[project_key] = IntelligentContextCache(
                project_path, config
            )

        return _cache_instances[project_key]


def clear_all_caches():
    """Clear all cache instances."""
    with _cache_lock:
        _cache_instances.clear()
