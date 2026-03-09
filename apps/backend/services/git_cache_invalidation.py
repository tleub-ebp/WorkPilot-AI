#!/usr/bin/env python3
"""
Git-based Cache Invalidation Service

Monitors git repository for changes and automatically invalidates context cache
when relevant changes are detected.
"""

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Callable
import subprocess
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class GitChangeEvent:
    """Represents a git change event."""
    
    commit_hash: str
    commit_message: str
    author: str
    timestamp: float
    files_added: Set[str] = field(default_factory=set)
    files_modified: Set[str] = field(default_factory=set)
    files_deleted: Set[str] = field(default_factory=set)
    files_renamed: Dict[str, str] = field(default_factory=dict)  # old -> new
    
    def get_all_changed_files(self) -> Set[str]:
        """Get all files affected by this change."""
        all_files = set()
        all_files.update(self.files_added)
        all_files.update(self.files_modified)
        all_files.update(self.files_deleted)
        all_files.update(self.files_renamed.keys())
        all_files.update(self.files_renamed.values())
        return all_files


@dataclass
class CacheInvalidationEvent:
    """Represents a cache invalidation event."""
    
    timestamp: float
    reason: str
    git_commit: str
    cache_keys_invalidated: List[str] = field(default_factory=list)
    entries_affected: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            'timestamp': self.timestamp,
            'reason': self.reason,
            'git_commit': self.git_commit,
            'cache_keys_invalidated': self.cache_keys_invalidated,
            'entries_affected': self.entries_affected
        }


class GitRepositoryMonitor:
    """Monitors git repository for changes."""
    
    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.last_known_commit = ""
        self._lock = threading.RLock()
        
        # Initialize with current commit
        self.last_known_commit = self.get_current_commit()
    
    def get_current_commit(self) -> str:
        """Get current git commit hash."""
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
    
    def get_commit_info(self, commit_hash: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a commit."""
        try:
            # Get commit details
            result = subprocess.run(
                ['git', 'show', '--format=%H|%s|%an|%ct', '--no-patch', commit_hash],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return None
            
            parts = result.stdout.strip().split('|')
            if len(parts) < 4:
                return None
            
            return {
                'hash': parts[0],
                'message': parts[1],
                'author': parts[2],
                'timestamp': float(parts[3])
            }
            
        except Exception as e:
            logger.warning(f"Error getting commit info for {commit_hash}: {e}")
        
        return None
    
    def get_changed_files_since(self, from_commit: str) -> Optional[GitChangeEvent]:
        """Get files changed since specified commit."""
        try:
            # Get commit information
            to_commit = self.get_current_commit()
            commit_info = self.get_commit_info(to_commit)
            
            if not commit_info:
                return None
            
            # Create change event
            event = self._create_change_event(to_commit, commit_info)
            
            # Get and parse file changes
            changes_output = self._get_git_diff_output(from_commit, to_commit)
            if changes_output is None:
                return None
            
            self._parse_file_changes(changes_output, event)
            
            return event
            
        except Exception as e:
            logger.warning(f"Error getting changed files since {from_commit}: {e}")
            return None
    
    def _create_change_event(self, commit_hash: str, commit_info: Dict[str, Any]) -> GitChangeEvent:
        """Create a GitChangeEvent from commit information."""
        return GitChangeEvent(
            commit_hash=commit_hash,
            commit_message=commit_info['message'],
            author=commit_info['author'],
            timestamp=commit_info['timestamp']
        )
    
    def _get_git_diff_output(self, from_commit: str, to_commit: str) -> Optional[str]:
        """Get git diff output between two commits."""
        try:
            result = subprocess.run(
                ['git', 'diff', '--name-status', from_commit, to_commit],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if result.returncode != 0:
                return None
            
            return result.stdout.strip()
            
        except Exception as e:
            logger.warning(f"Error getting git diff: {e}")
            return None
    
    def _parse_file_changes(self, diff_output: str, event: GitChangeEvent):
        """Parse git diff output and populate the change event."""
        if not diff_output:
            return
        
        for line in diff_output.split('\n'):
            if not line:
                continue
            
            self._process_file_change_line(line, event)
    
    def _process_file_change_line(self, line: str, event: GitChangeEvent):
        """Process a single line of git diff output."""
        parts = line.split('\t')
        if len(parts) < 2:
            return
        
        status, file_path = parts[0], parts[1]
        
        # Use a mapping for cleaner code
        status_handlers = {
            'A': lambda fp: event.files_added.add(fp),
            'M': lambda fp: event.files_modified.add(fp),
            'D': lambda fp: event.files_deleted.add(fp),
            'T': lambda fp: event.files_modified.add(fp),
            'C': lambda fp: event.files_modified.add(fp)
        }
        
        if status == 'R' and len(parts) >= 3:
            # Handle renamed files separately
            old_path, new_path = file_path, parts[2]
            event.files_renamed[old_path] = new_path
        elif status in status_handlers:
            # Use the handler mapping
            status_handlers[status](file_path)
    
    def has_new_commits(self) -> bool:
        """Check if there are new commits since last check."""
        current_commit = self.get_current_commit()
        
        with self._lock:
            if current_commit != self.last_known_commit:
                return True
        
        return False
    
    def update_last_known_commit(self, commit_hash: str):
        """Update the last known commit."""
        with self._lock:
            self.last_known_commit = commit_hash


class CacheInvalidationStrategy:
    """Base class for cache invalidation strategies."""
    
    def should_invalidate(self, change_event: GitChangeEvent, cache_entry: 'ContextCacheEntry') -> bool:
        """Determine if cache entry should be invalidated."""
        raise NotImplementedError
    
    def get_invalidation_reason(self) -> str:
        """Get reason for invalidation."""
        raise NotImplementedError


class FileBasedInvalidationStrategy(CacheInvalidationStrategy):
    """Invalidates cache based on file changes."""
    
    def __init__(self, critical_files: Set[str], file_patterns: List[str]):
        self.critical_files = critical_files
        self.file_patterns = file_patterns
    
    def should_invalidate(self, change_event: GitChangeEvent, cache_entry: 'ContextCacheEntry') -> bool:
        """Check if critical files were modified."""
        changed_files = change_event.get_all_changed_files()
        cached_files = cache_entry.files_changed
        
        # Check for critical file changes
        for critical_file in self.critical_files:
            if any(critical_file in changed_file for changed_file in changed_files):
                return True
        
        # Check for pattern matches
        import fnmatch
        
        for pattern in self.file_patterns:
            for changed_file in changed_files:
                if fnmatch.fnmatch(changed_file, pattern):
                    return True
        
        # Check for overlap with cached files
        overlap = len(cached_files.intersection(changed_files))
        if overlap > 0:
            # If more than 50% of cached files changed, invalidate
            if len(cached_files) > 0 and overlap / len(cached_files) > 0.5:
                return True
        
        return False
    
    def get_invalidation_reason(self) -> str:
        return "Critical files or significant file changes detected"


class CommitMessageBasedInvalidationStrategy(CacheInvalidationStrategy):
    """Invalidates cache based on commit message patterns."""
    
    def __init__(self, invalidation_patterns: List[str]):
        self.invalidation_patterns = invalidation_patterns
    
    def should_invalidate(self, change_event: GitChangeEvent, cache_entry: 'ContextCacheEntry') -> bool:
        """Check if commit message indicates cache-breaking changes."""
        message = change_event.commit_message.lower()
        
        for pattern in self.invalidation_patterns:
            if pattern.lower() in message:
                return True
        
        return False
    
    def get_invalidation_reason(self) -> str:
        return "Cache-breaking commit detected"


class DependencyChangeInvalidationStrategy(CacheInvalidationStrategy):
    """Invalidates cache when dependencies change."""
    
    def __init__(self):
        self.dependency_files = {
            'package.json', 'requirements.txt', 'Pipfile', 'pyproject.toml',
            'Cargo.toml', 'composer.json', 'Gemfile', 'go.mod'
        }
    
    def should_invalidate(self, change_event: GitChangeEvent, cache_entry: 'ContextCacheEntry') -> bool:
        """Check if dependency files were modified."""
        changed_files = change_event.get_all_changed_files()
        
        for dep_file in self.dependency_files:
            if any(dep_file in changed_file for changed_file in changed_files):
                return True
        
        return False
    
    def get_invalidation_reason(self) -> str:
        return "Dependency changes detected"


class GitBasedCacheInvalidator:
    """Main service for git-based cache invalidation."""
    
    def __init__(self, project_path: Path, context_cache: 'IntelligentContextCache'):
        self.project_path = project_path
        self.context_cache = context_cache
        
        # Git monitoring
        self.git_monitor = GitRepositoryMonitor(project_path)
        
        # Invalidation strategies
        self.strategies: List[CacheInvalidationStrategy] = []
        self._setup_default_strategies()
        
        # Monitoring state
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # Statistics
        self.invalidation_history: List[CacheInvalidationEvent] = []
        self.stats = {
            'total_invalidations': 0,
            'entries_invalidated': 0,
            'monitoring_cycles': 0,
            'last_invalidation': 0.0
        }
    
    def _setup_default_strategies(self):
        """Setup default invalidation strategies."""
        # File-based strategy
        critical_files = {
            'package.json', 'requirements.txt', 'pyproject.toml',
            'Dockerfile', 'docker-compose.yml', '.env.example'
        }
        file_patterns = [
            '*.config.js', '*.config.ts', 'webpack.config.*',
            'tsconfig.json', 'babel.config.*', '.eslintrc.*'
        ]
        
        self.strategies.append(
            FileBasedInvalidationStrategy(critical_files, file_patterns)
        )
        
        # Commit message strategy
        invalidation_patterns = [
            'breaking change', 'major refactor', 'architecture',
            'cache invalidat', 'cleanup', 'restructure'
        ]
        
        self.strategies.append(
            CommitMessageBasedInvalidationStrategy(invalidation_patterns)
        )
        
        # Dependency change strategy
        self.strategies.append(DependencyChangeInvalidationStrategy())
    
    def add_strategy(self, strategy: CacheInvalidationStrategy):
        """Add a custom invalidation strategy."""
        self.strategies.append(strategy)
    
    def start_monitoring(self, interval_seconds: float = 30.0):
        """Start background git monitoring."""
        if self._monitoring:
            logger.warning("Git monitoring is already running")
            return
        
        self._monitoring = True
        self._stop_event.clear()
        
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval_seconds,),
            daemon=True
        )
        
        self._monitor_thread.start()
        logger.info(f"Started git monitoring with {interval_seconds}s interval")
    
    def stop_monitoring(self):
        """Stop background git monitoring."""
        if not self._monitoring:
            return
        
        self._monitoring = False
        self._stop_event.set()
        
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5.0)
        
        logger.info("Stopped git monitoring")
    
    def _monitor_loop(self, interval_seconds: float):
        """Main monitoring loop."""
        while self._monitoring and not self._stop_event.is_set():
            try:
                self._check_for_changes()
                self.stats['monitoring_cycles'] += 1
                
                # Wait for next cycle or stop signal
                self._stop_event.wait(interval_seconds)
                
            except Exception as e:
                logger.error(f"Error in git monitoring loop: {e}")
                self._stop_event.wait(5.0)  # Brief pause on error
    
    def _check_for_changes(self):
        """Check for git changes and invalidate cache if needed."""
        if not self.git_monitor.has_new_commits():
            return
        
        # Get change event
        change_event = self.git_monitor.get_changed_files_since(
            self.git_monitor.last_known_commit
        )
        
        if not change_event:
            return
        
        logger.info(f"Detected git changes: {change_event.commit_hash[:8]} - {change_event.commit_message[:50]}")
        
        # Check each cache entry
        invalidated_entries = []
        
        with self.context_cache._cache_lock:
            for cache_key, cache_entry in self.context_cache._cache.items():
                for strategy in self.strategies:
                    if strategy.should_invalidate(change_event, cache_entry):
                        invalidated_entries.append(cache_key)
                        break
        
        # Invalidate cache entries
        if invalidated_entries:
            self._invalidate_entries(invalidated_entries, change_event)
        
        # Update monitoring state
        self.git_monitor.update_last_known_commit(change_event.commit_hash)
    
    def _invalidate_entries(self, cache_keys: List[str], change_event: GitChangeEvent):
        """Invalidate specified cache entries."""
        # Determine invalidation reason
        reason = "Git changes detected"
        for strategy in self.strategies:
            if any(strategy.should_invalidate(change_event, entry) 
                   for entry in self.context_cache._cache.values()
                   if entry.cache_key in cache_keys):
                reason = strategy.get_invalidation_reason()
                break
        
        # Create invalidation event
        invalidation_event = CacheInvalidationEvent(
            timestamp=time.time(),
            reason=reason,
            git_commit=change_event.commit_hash,
            cache_keys_invalidated=cache_keys,
            entries_affected=len(cache_keys)
        )
        
        # Perform invalidation
        for cache_key in cache_keys:
            if cache_key in self.context_cache._cache:
                del self.context_cache._cache[cache_key]
                
                # Remove from database
                import sqlite3
                db_path = self.context_cache.project_path / ".auto-claude" / self.context_cache.config.db_path
                with sqlite3.connect(db_path) as conn:
                    conn.execute('DELETE FROM context_cache WHERE cache_key = ?', (cache_key,))
        
        # Update statistics
        self.invalidation_history.append(invalidation_event)
        self.stats['total_invalidations'] += 1
        self.stats['entries_invalidated'] += len(cache_keys)
        self.stats['last_invalidation'] = invalidation_event.timestamp
        
        # Keep history manageable
        if len(self.invalidation_history) > 100:
            self.invalidation_history = self.invalidation_history[-50:]
        
        logger.info(f"Invalidated {len(cache_keys)} cache entries: {reason}")
    
    def manual_invalidation_check(self) -> Dict[str, Any]:
        """Perform manual invalidation check and return results."""
        if not self.git_monitor.has_new_commits():
            return {
                'has_changes': False,
                'current_commit': self.git_monitor.last_known_commit,
                'invalidations_needed': []
            }
        
        # Get change event
        change_event = self.git_monitor.get_changed_files_since(
            self.git_monitor.last_known_commit
        )
        
        if not change_event:
            return {
                'has_changes': False,
                'current_commit': self.git_monitor.last_known_commit,
                'invalidations_needed': []
            }
        
        # Check what would be invalidated
        would_invalidate = []
        
        with self.context_cache._cache_lock:
            for cache_key, cache_entry in self.context_cache._cache.items():
                for strategy in self.strategies:
                    if strategy.should_invalidate(change_event, cache_entry):
                        would_invalidate.append({
                            'cache_key': cache_key,
                            'reason': strategy.get_invalidation_reason(),
                            'strategy': strategy.__class__.__name__
                        })
                        break
        
        return {
            'has_changes': True,
            'change_event': {
                'commit_hash': change_event.commit_hash,
                'message': change_event.commit_message,
                'author': change_event.author,
                'files_changed': list(change_event.get_all_changed_files())
            },
            'current_commit': self.git_monitor.last_known_commit,
            'invalidations_needed': would_invalidate
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get invalidation statistics."""
        recent_invalidations = [
            event for event in self.invalidation_history
            if time.time() - event.timestamp < 3600  # Last hour
        ]
        
        return {
            'monitoring_active': self._monitoring,
            'current_commit': self.git_monitor.last_known_commit,
            'total_invalidations': self.stats['total_invalidations'],
            'entries_invalidated': self.stats['entries_invalidated'],
            'monitoring_cycles': self.stats['monitoring_cycles'],
            'last_invalidation': self.stats['last_invalidation'],
            'recent_invalidations': len(recent_invalidations),
            'strategies_active': len(self.strategies),
            'invalidation_history': [event.to_dict() for event in self.invalidation_history[-10:]]
        }
    
    def export_invalidation_log(self, filepath: str):
        """Export invalidation log to file."""
        export_data = {
            'export_timestamp': time.time(),
            'project_path': str(self.project_path),
            'statistics': self.get_statistics(),
            'strategies': [
                {
                    'type': strategy.__class__.__name__,
                    'reason': strategy.get_invalidation_reason()
                }
                for strategy in self.strategies
            ],
            'invalidation_history': [event.to_dict() for event in self.invalidation_history]
        }
        
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        logger.info(f"Exported invalidation log to {filepath}")


# Import for type hints
from .intelligent_context_cache import IntelligentContextCache, ContextCacheEntry
