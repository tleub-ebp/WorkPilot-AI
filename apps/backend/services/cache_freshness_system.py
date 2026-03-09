#!/usr/bin/env python3
"""
Cache Freshness and Invalidation System

Advanced freshness scoring and intelligent invalidation strategies for context cache.
Implements multiple invalidation strategies and freshness metrics.
"""

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Callable
import sqlite3
import threading
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Constants for package files
PACKAGE_JSON = 'package.json'
REQUIREMENTS_TXT = 'requirements.txt'
PYPROJECT_TOML = 'pyproject.toml'


class InvalidationStrategy(Enum):
    """Different strategies for cache invalidation."""
    IMMEDIATE = "immediate"
    TIME_BASED = "time_based"
    DEPENDENCY_BASED = "dependency_based"
    SEMANTIC_DRIFT = "semantic_drift"
    MANUAL = "manual"
    ADAPTIVE = "adaptive"


class FreshnessFactor(Enum):
    """Factors that contribute to freshness scoring."""
    AGE = "age"
    GIT_CHANGES = "git_changes"
    FILE_MODIFICATIONS = "file_modifications"
    DEPENDENCY_UPDATES = "dependency_updates"
    ACCESS_PATTERN = "access_pattern"
    SEMANTIC_DRIFT = "semantic_drift"
    BUILD_FAILURES = "build_failures"


@dataclass
class FreshnessMetrics:
    """Detailed freshness metrics for a cache entry."""
    
    # Individual factor scores (0.0 to 1.0)
    age_score: float = 1.0
    git_score: float = 1.0
    file_score: float = 1.0
    dependency_score: float = 1.0
    access_score: float = 1.0
    semantic_score: float = 1.0
    build_score: float = 1.0
    
    # Combined scores
    overall_freshness: float = 1.0
    confidence_score: float = 1.0
    
    # Metadata
    calculated_at: float = field(default_factory=time.time)
    factors_considered: List[FreshnessFactor] = field(default_factory=list)
    
    # Change tracking
    files_changed: Set[str] = field(default_factory=set)
    dependencies_changed: Set[str] = field(default_factory=set)
    commits_since_cache: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'age_score': self.age_score,
            'git_score': self.git_score,
            'file_score': self.file_score,
            'dependency_score': self.dependency_score,
            'access_score': self.access_score,
            'semantic_score': self.semantic_score,
            'build_score': self.build_score,
            'overall_freshness': self.overall_freshness,
            'confidence_score': self.confidence_score,
            'calculated_at': self.calculated_at,
            'factors_considered': [f.value for f in self.factors_considered],
            'files_changed': list(self.files_changed),
            'dependencies_changed': list(self.dependencies_changed),
            'commits_since_cache': self.commits_since_cache
        }


@dataclass
class InvalidationRule:
    """Rule for cache invalidation."""
    
    name: str
    strategy: InvalidationStrategy
    conditions: Dict[str, Any]
    action: str  # 'invalidate', 'refresh', 'downgrade'
    priority: int = 0  # Higher priority rules are evaluated first
    
    # Metadata
    created_at: float = field(default_factory=time.time)
    last_triggered: float = 0.0
    trigger_count: int = 0


class FreshnessCalculator:
    """Calculates detailed freshness scores using multiple factors."""
    
    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.git_analyzer = GitChangeAnalyzer(project_path)
        self.dependency_analyzer = DependencyChangeAnalyzer(project_path)
        self.file_analyzer = FileChangeAnalyzer(project_path)
        self.semantic_analyzer = SemanticDriftAnalyzer(project_path)
        
        # Weights for different factors
        self.factor_weights = {
            FreshnessFactor.AGE: 0.15,
            FreshnessFactor.GIT_CHANGES: 0.25,
            FreshnessFactor.FILE_MODIFICATIONS: 0.20,
            FreshnessFactor.DEPENDENCY_UPDATES: 0.15,
            FreshnessFactor.ACCESS_PATTERN: 0.10,
            FreshnessFactor.SEMANTIC_DRIFT: 0.10,
            FreshnessFactor.BUILD_FAILURES: 0.05
        }
    
    def calculate_freshness(self, cache_entry: 'ContextCacheEntry') -> FreshnessMetrics:
        """Calculate comprehensive freshness metrics."""
        metrics = FreshnessMetrics()
        current_time = time.time()
        
        # Calculate individual factor scores
        metrics.age_score = self._calculate_age_score(cache_entry, current_time)
        metrics.git_score = self._calculate_git_score(cache_entry)
        metrics.file_score = self._calculate_file_score(cache_entry)
        metrics.dependency_score = self._calculate_dependency_score(cache_entry)
        metrics.access_score = self._calculate_access_score(cache_entry, current_time)
        metrics.semantic_score = self._calculate_semantic_score(cache_entry)
        metrics.build_score = self._calculate_build_score()
        
        # Track which factors were considered
        metrics.factors_considered = list(self.factor_weights.keys())
        
        # Calculate overall freshness (weighted average)
        metrics.overall_freshness = sum(
            getattr(metrics, f"{factor.value}_score") * weight
            for factor, weight in self.factor_weights.items()
        )
        
        # Calculate confidence based on data availability
        metrics.confidence_score = self._calculate_confidence_score(metrics)
        
        # Populate change tracking
        metrics.files_changed = self.file_analyzer.get_changed_files(cache_entry.git_commit_hash)
        metrics.dependencies_changed = self.dependency_analyzer.get_changed_dependencies(cache_entry.git_commit_hash)
        metrics.commits_since_cache = self.git_analyzer.count_commits_since(cache_entry.git_commit_hash)
        
        return metrics
    
    def _calculate_age_score(self, cache_entry: 'ContextCacheEntry', current_time: float) -> float:
        """Calculate age-based freshness score."""
        age_hours = (current_time - cache_entry.created_at) / 3600
        
        # Exponential decay over time
        decay_rate = 0.1  # Adjust for faster/slower decay
        score = max(0.0, 1.0 * (2.718 ** (-decay_rate * age_hours)))
        
        return score
    
    def _calculate_git_score(self, cache_entry: 'ContextCacheEntry') -> float:
        """Calculate git-based freshness score."""
        try:
            current_commit = self.git_analyzer.get_current_commit()
            
            if cache_entry.git_commit_hash == current_commit:
                return 1.0
            
            # Check if cache commit is ancestor
            if self.git_analyzer.is_ancestor(cache_entry.git_commit_hash, current_commit):
                commits_since = self.git_analyzer.count_commits_since(cache_entry.git_commit_hash)
                
                # Decay based on number of commits
                if commits_since == 0:
                    return 1.0
                elif commits_since <= 2:
                    return 0.8
                elif commits_since <= 5:
                    return 0.6
                elif commits_since <= 10:
                    return 0.4
                else:
                    return 0.2
            else:
                # Branch diverged
                return 0.1
                
        except Exception as e:
            logger.warning(f"Error calculating git score: {e}")
            return 0.5
    
    def _calculate_file_score(self, cache_entry: 'ContextCacheEntry') -> float:
        """Calculate file-based freshness score."""
        try:
            changed_files = self.file_analyzer.get_changed_files(cache_entry.git_commit_hash)
            cached_files = cache_entry.files_changed
            
            if not cached_files:
                return 1.0
            
            # Calculate overlap
            overlap = len(cached_files.intersection(changed_files))
            total_cached = len(cached_files)
            
            if total_cached == 0:
                return 1.0
            
            change_ratio = overlap / total_cached
            
            # Score based on change ratio
            if change_ratio == 0:
                return 1.0
            elif change_ratio <= 0.1:
                return 0.9
            elif change_ratio <= 0.25:
                return 0.7
            elif change_ratio <= 0.5:
                return 0.5
            else:
                return 0.3
                
        except Exception as e:
            logger.warning(f"Error calculating file score: {e}")
            return 0.5
    
    def _calculate_dependency_score(self, cache_entry: 'ContextCacheEntry') -> float:
        """Calculate dependency-based freshness score."""
        try:
            changed_deps = self.dependency_analyzer.get_changed_dependencies(cache_entry.git_commit_hash)
            cached_deps = set()
            
            # Extract dependencies from cached context
            if 'dependencies' in cache_entry.context_data:
                cached_deps.update(cache_entry.context_data['dependencies'].keys())
            
            if not cached_deps:
                return 1.0
            
            # Calculate overlap
            overlap = len(cached_deps.intersection(changed_deps))
            total_cached = len(cached_deps)
            
            if total_cached == 0:
                return 1.0
            
            change_ratio = overlap / total_cached
            
            # Dependencies are more critical than regular files
            if change_ratio == 0:
                return 1.0
            elif change_ratio <= 0.05:  # 5% or less
                return 0.9
            elif change_ratio <= 0.15:  # 15% or less
                return 0.7
            elif change_ratio <= 0.3:  # 30% or less
                return 0.5
            else:
                return 0.2
                
        except Exception as e:
            logger.warning(f"Error calculating dependency score: {e}")
            return 0.5
    
    def _calculate_access_score(self, cache_entry: 'ContextCacheEntry', current_time: float) -> float:
        """Calculate access pattern-based freshness score."""
        # Recent access indicates relevance
        time_since_access = current_time - cache_entry.last_accessed
        access_recency_hours = time_since_access / 3600
        
        # Access frequency
        access_frequency = cache_entry.access_count
        
        # Combine recency and frequency
        recency_score = max(0.0, 1.0 - (access_recency_hours / 24.0))  # Decay over 24 hours
        frequency_score = min(1.0, access_frequency / 5.0)  # Normalize to 5 accesses
        
        return (recency_score * 0.7) + (frequency_score * 0.3)
    
    def _calculate_semantic_score(self, cache_entry: 'ContextCacheEntry') -> float:
        """Calculate semantic drift score."""
        try:
            current_semantic_signature = self.semantic_analyzer.generate_current_signature()
            cached_signature = cache_entry.semantic_signature
            
            if not cached_signature or not current_semantic_signature:
                return 1.0
            
            # Calculate semantic similarity
            similarity = self.semantic_analyzer.calculate_similarity(cached_signature, current_semantic_signature)
            
            return similarity
            
        except Exception as e:
            logger.warning(f"Error calculating semantic score: {e}")
            return 0.5
    
    def _calculate_build_score(self) -> float:
        """Calculate build success/failure score."""
        # This would integrate with build analytics
        # For now, return default score
        return 1.0
    
    def _calculate_confidence_score(self, metrics: FreshnessMetrics) -> float:
        """Calculate confidence in the freshness assessment."""
        factor_scores = [
            metrics.age_score,
            metrics.git_score,
            metrics.file_score,
            metrics.dependency_score,
            metrics.access_score,
            metrics.semantic_score,
            metrics.build_score
        ]
        
        # Confidence based on consistency of scores
        # Lower variance = higher confidence
        mean_score = sum(factor_scores) / len(factor_scores)
        variance = sum((score - mean_score) ** 2 for score in factor_scores) / len(factor_scores)
        
        # Convert variance to confidence (lower variance = higher confidence)
        confidence = max(0.0, 1.0 - (variance * 2))
        
        return confidence


class GitChangeAnalyzer:
    """Analyzes git changes for freshness calculation."""
    
    def __init__(self, project_path: Path):
        self.project_path = project_path
    
    def get_current_commit(self) -> str:
        """Get current git commit hash."""
        import subprocess
        
        try:
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception as e:
            logger.warning(f"Error getting current commit: {e}")
        
        return ""
    
    def is_ancestor(self, ancestor_hash: str, descendant_hash: str) -> bool:
        """Check if ancestor_hash is ancestor of descendant_hash."""
        import subprocess
        
        try:
            result = subprocess.run(
                ['git', 'merge-base', '--is-ancestor', ancestor_hash, descendant_hash],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception as e:
            logger.warning(f"Error checking ancestor relationship: {e}")
        
        return False
    
    def count_commits_since(self, commit_hash: str) -> int:
        """Count commits since specified commit."""
        import subprocess
        
        try:
            result = subprocess.run(
                ['git', 'rev-list', '--count', f'{commit_hash}..HEAD'],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return int(result.stdout.strip())
        except Exception as e:
            logger.warning(f"Error counting commits: {e}")
        
        return 0


class FileChangeAnalyzer:
    """Analyzes file changes for freshness calculation."""
    
    def __init__(self, project_path: Path):
        self.project_path = project_path
    
    def get_changed_files(self, since_commit: str) -> Set[str]:
        """Get files changed since specified commit."""
        import subprocess
        
        try:
            result = subprocess.run(
                ['git', 'diff', '--name-only', since_commit, 'HEAD'],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                changed = result.stdout.strip().split('\n') if result.stdout.strip() else []
                return set(changed)
        except Exception as e:
            logger.warning(f"Error getting changed files: {e}")
        
        return set()


class DependencyChangeAnalyzer:
    """Analyzes dependency changes for freshness calculation."""
    
    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.cached_dependencies = {}
    
    def get_changed_dependencies(self, since_commit: str) -> Set[str]:
        """Get dependencies changed since specified commit."""
        import subprocess
        
        changed_deps = set()
        
        # Check package files
        package_files = [
            PACKAGE_JSON,
            REQUIREMENTS_TXT,
            'Pipfile',
            PYPROJECT_TOML,
            'Cargo.toml',
            'composer.json',
            'Gemfile'
        ]
        
        for pkg_file in package_files:
            try:
                # Check if package file has changed
                result = subprocess.run(
                    ['git', 'diff', '--name-only', since_commit, 'HEAD', '--', pkg_file],
                    cwd=self.project_path,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0 and result.stdout.strip():
                    # Parse dependencies from current file
                    current_deps = self._parse_dependencies(pkg_file)
                    changed_deps.update(current_deps.keys())
                    
            except Exception as e:
                logger.warning(f"Error checking {pkg_file}: {e}")
        
        return changed_deps
    
    def _parse_dependencies(self, package_file: str) -> Dict[str, str]:
        """Parse dependencies from package file."""
        file_path = self.project_path / package_file
        
        if not file_path.exists():
            return {}
        
        try:
            if package_file == PACKAGE_JSON:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    return data.get('dependencies', {})
            
            elif package_file == REQUIREMENTS_TXT:
                deps = {}
                with open(file_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            pkg = line.split('==')[0].split('>=')[0].split('[')[0].strip()
                            if pkg:
                                deps[pkg] = line
                return deps
            
            # Add more package file parsers as needed
            
        except Exception as e:
            logger.warning(f"Error parsing {package_file}: {e}")
        
        return {}


class SemanticDriftAnalyzer:
    """Analyzes semantic drift for freshness calculation."""
    
    def __init__(self, project_path: Path):
        self.project_path = project_path
    
    def generate_current_signature(self) -> str:
        """Generate current semantic signature."""
        # This would analyze current project structure and patterns
        # For now, return a simple hash of project structure
        structure_hash = self._analyze_project_structure()
        return hashlib.sha256(structure_hash.encode()).hexdigest()[:16]
    
    def calculate_similarity(self, signature1: str, signature2: str) -> float:
        """Calculate similarity between semantic signatures."""
        if signature1 == signature2:
            return 1.0
        
        # Simple character-based similarity
        common_chars = sum(c1 == c2 for c1, c2 in zip(signature1, signature2))
        max_len = max(len(signature1), len(signature2))
        
        return common_chars / max_len if max_len > 0 else 0.0
    
    def _analyze_project_structure(self) -> str:
        """Analyze project structure for semantic signature."""
        structure_parts = []
        
        # Get directory structure
        for root, dirs, files in self.project_path.rglob('*'):
            if root.is_dir():
                relative_path = root.relative_to(self.project_path)
                structure_parts.append(str(relative_path))
        
        # Sort for consistency
        structure_parts.sort()
        
        return '|'.join(structure_parts)


class InvalidationEngine:
    """Engine for applying invalidation strategies."""
    
    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.freshness_calculator = FreshnessCalculator(project_path)
        self.rules: List[InvalidationRule] = []
        self._lock = threading.RLock()
        
        # Load default rules
        self._load_default_rules()
    
    def _load_default_rules(self):
        """Load default invalidation rules."""
        default_rules = [
            InvalidationRule(
                name="Low Freshness Invalidation",
                strategy=InvalidationStrategy.ADAPTIVE,
                conditions={
                    'freshness_threshold': 0.3,
                    'confidence_threshold': 0.5
                },
                action="invalidate",
                priority=100
            ),
            InvalidationRule(
                name="Critical File Changes",
                strategy=InvalidationStrategy.DEPENDENCY_BASED,
                conditions={
                    'critical_files': [PACKAGE_JSON, REQUIREMENTS_TXT, PYPROJECT_TOML],
                    'min_file_changes': 1
                },
                action="invalidate",
                priority=90
            ),
            InvalidationRule(
                name="High Commit Count",
                strategy=InvalidationStrategy.TIME_BASED,
                conditions={
                    'max_commits': 10,
                    'min_freshness': 0.4
                },
                action="downgrade",
                priority=80
            ),
            InvalidationRule(
                name="Semantic Drift",
                strategy=InvalidationStrategy.SEMANTIC_DRIFT,
                conditions={
                    'min_semantic_similarity': 0.7
                },
                action="refresh",
                priority=70
            )
        ]
        
        self.rules.extend(default_rules)
    
    def evaluate_invalidation(self, cache_entry: 'ContextCacheEntry') -> List[str]:
        """Evaluate invalidation rules and return recommended actions."""
        return self._evaluate_invalidation_internal(cache_entry)
    
    def _evaluate_invalidation_internal(self, cache_entry: 'ContextCacheEntry') -> List[str]:
        """Internal method for evaluating invalidation rules."""
        actions = []
        
        # Calculate freshness metrics
        metrics = self.freshness_calculator.calculate_freshness(cache_entry)
        
        with self._lock:
            # Sort rules by priority (highest first)
            sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)
            
            for rule in sorted_rules:
                if self._evaluate_rule(rule, cache_entry, metrics):
                    actions.append(rule.action)
                    
                    # Update rule statistics
                    rule.last_triggered = time.time()
                    rule.trigger_count += 1
                    
                    # Stop after first action unless it's a downgrade
                    if rule.action != "downgrade":
                        break
        
        return actions
    
    def _evaluate_rule(self, rule: InvalidationRule, _cache_entry: 'ContextCacheEntry', 
                      metrics: FreshnessMetrics) -> bool:
        """Evaluate if a rule should be triggered."""
        # Strategy evaluator mapping
        strategy_evaluators = {
            InvalidationStrategy.ADAPTIVE: self._evaluate_adaptive_strategy,
            InvalidationStrategy.DEPENDENCY_BASED: self._evaluate_dependency_strategy,
            InvalidationStrategy.TIME_BASED: self._evaluate_time_strategy,
            InvalidationStrategy.SEMANTIC_DRIFT: self._evaluate_semantic_strategy
        }
        
        evaluator = strategy_evaluators.get(rule.strategy)
        if evaluator:
            return evaluator(rule.conditions, metrics)
        
        return False
    
    def _evaluate_adaptive_strategy(self, conditions: Dict[str, Any], metrics: FreshnessMetrics) -> bool:
        """Evaluate adaptive invalidation strategy."""
        # Check freshness threshold
        if 'freshness_threshold' in conditions:
            if metrics.overall_freshness < conditions['freshness_threshold']:
                return True
        
        # Check confidence threshold
        if 'confidence_threshold' in conditions:
            if metrics.confidence_score < conditions['confidence_threshold']:
                return True
        
        return False
    
    def _evaluate_dependency_strategy(self, conditions: Dict[str, Any], metrics: FreshnessMetrics) -> bool:
        """Evaluate dependency-based invalidation strategy."""
        if 'critical_files' not in conditions:
            return False
        
        critical_files = set(conditions['critical_files'])
        changed_files = metrics.files_changed
        
        if not critical_files.intersection(changed_files):
            return False
        
        min_changes = conditions.get('min_file_changes', 1)
        return len(critical_files.intersection(changed_files)) >= min_changes
    
    def _evaluate_time_strategy(self, conditions: Dict[str, Any], metrics: FreshnessMetrics) -> bool:
        """Evaluate time-based invalidation strategy."""
        if 'max_commits' not in conditions:
            return False
        
        if metrics.commits_since_cache <= conditions['max_commits']:
            return False
        
        # Check minimum freshness
        min_freshness = conditions.get('min_freshness', 0.0)
        return metrics.overall_freshness < min_freshness
    
    def _evaluate_semantic_strategy(self, conditions: Dict[str, Any], metrics: FreshnessMetrics) -> bool:
        """Evaluate semantic drift invalidation strategy."""
        if 'min_semantic_similarity' not in conditions:
            return False
        
        return metrics.semantic_score < conditions['min_semantic_similarity']
    
    def add_rule(self, rule: InvalidationRule):
        """Add a new invalidation rule."""
        with self._lock:
            self.rules.append(rule)
    
    def remove_rule(self, rule_name: str) -> bool:
        """Remove an invalidation rule by name."""
        with self._lock:
            for i, rule in enumerate(self.rules):
                if rule.name == rule_name:
                    del self.rules[i]
                    return True
        return False
    
    def get_rules(self) -> List[InvalidationRule]:
        """Get all invalidation rules."""
        with self._lock:
            return self.rules.copy()


# Import ContextCacheEntry for type hints
from .intelligent_context_cache import ContextCacheEntry
