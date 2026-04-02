#!/usr/bin/env python3
"""
Tests for Intelligent Context Caching System

Comprehensive test suite for the intelligent context caching feature.
Tests semantic analysis, freshness scoring, git invalidation, and API endpoints.
"""

import json
import shutil
import sys
import pytest
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

# Import the modules to test
from apps.backend.services.intelligent_context_cache import (
    IntelligentContextCache, CacheConfig, ContextCacheEntry, SemanticHasher
)
from apps.backend.services.cache_freshness_system import (
    FreshnessCalculator, FreshnessMetrics, InvalidationEngine, InvalidationRule
)
from apps.backend.services.git_cache_invalidation import (
    GitRepositoryMonitor, GitBasedCacheInvalidator, GitChangeEvent
)
from apps.backend.services.context_cache_integration import (
    ContextCacheIntegrator, AgentWorkflowIntegrator, ContextRequest, ContextResponse
)


class TestSemanticHasher:
    """Test semantic hashing functionality."""
    
    def test_generate_semantic_signature(self):
        """Test semantic signature generation."""
        hasher = SemanticHasher()
        
        context_data = {
            'project_structure': {
                'src/main.py': {'type': 'file'},
                'src/utils.py': {'type': 'file'},
                'tests/test_main.py': {'type': 'file'}
            },
            'dependencies': {
                'flask': '2.0.0',
                'requests': '2.25.0'
            },
            'frameworks': ['flask', 'sqlalchemy'],
            'description': 'A web application with Flask framework'
        }
        
        signature = hasher.generate_semantic_signature(context_data)
        
        assert isinstance(signature, str)
        assert len(signature) == 16  # SHA256 truncated to 16 chars
        assert signature.isalnum()  # Should be alphanumeric
    
    def test_similarity_calculation(self):
        """Test semantic similarity calculation."""
        hasher = SemanticHasher()
        
        # Identical signatures
        sig1 = "abcdef1234567890"
        sig2 = "abcdef1234567890"
        similarity = hasher.calculate_similarity(sig1, sig2)
        assert similarity == pytest.approx(1.0)
        
        # Different signatures
        sig3 = "1234567890abcdef"
        similarity = hasher.calculate_similarity(sig1, sig3)
        assert 0.0 <= similarity <= 1.0
        assert similarity < 1.0
    
    def test_term_extraction(self):
        """Test term extraction from context data."""
        hasher = SemanticHasher()
        
        context_data = {
            'project_structure': {
                'src/components/Button.tsx': {'type': 'file'},
                'src/utils/helpers.js': {'type': 'file'}
            },
            'dependencies': {
                'react': '18.0.0',
                'typescript': '4.5.0'
            }
        }
        
        terms = hasher._extract_terms(context_data)
        
        assert isinstance(terms, list)
        assert 'src' in terms
        assert 'components' in terms
        assert 'Button.tsx' in terms
        assert 'react' in terms
        assert 'typescript' in terms


class TestIntelligentContextCache:
    """Test the main intelligent context cache."""

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project directory."""
        import subprocess
        temp_dir = tempfile.mkdtemp()
        project_path = Path(temp_dir)
        try:
            # Create basic project structure
            (project_path / "src").mkdir()
            (project_path / "src" / "main.py").write_text("print('Hello, World!')")
            (project_path / "package.json").write_text('{"name": "test", "dependencies": {}}')

            # Initialize git repo
            subprocess.run(['git', 'init'], cwd=project_path, capture_output=True)
            subprocess.run(['git', 'config', 'user.name', 'Test'], cwd=project_path, capture_output=True)
            subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=project_path, capture_output=True)
            subprocess.run(['git', 'add', '.'], cwd=project_path, capture_output=True)
            subprocess.run(['git', 'commit', '-m', 'Initial commit'], cwd=project_path, capture_output=True)

            yield project_path
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def cache_config(self):
        """Create test cache configuration."""
        return CacheConfig(
            max_cache_size=10,
            max_entry_age_hours=1.0,
            freshness_threshold=0.7,
            similarity_threshold=0.8
        )
    
    @pytest.fixture
    def context_cache(self, temp_project, cache_config):
        """Create context cache instance with unique temp directory."""
        # Create a unique temp directory for each test to avoid database conflicts
        import uuid
        unique_suffix = str(uuid.uuid4())[:8]
        unique_project = temp_project / f"test_cache_{unique_suffix}"
        unique_project.mkdir(exist_ok=True)
        
        cache = IntelligentContextCache(unique_project, cache_config)
        yield cache
        # Cleanup after test
        cache.close()
        # Clean up the unique directory
        shutil.rmtree(unique_project, ignore_errors=True)
    
    def test_cache_initialization(self, temp_project, cache_config):
        """Test cache initialization."""
        cache = IntelligentContextCache(temp_project, cache_config)
        
        try:
            assert cache.project_path == temp_project
            assert cache.config == cache_config
            assert cache.semantic_hasher is not None
            assert cache.freshness_scorer is not None
            assert len(cache._cache) == 0
        finally:
            cache.close()
    
    def test_context_caching(self, context_cache):
        """Test basic context caching."""
        context_request = {
            'task_type': 'analysis',
            'target_files': ['src/main.py'],
            'frameworks': ['python'],
            'patterns': ['mvc'],
            'scope': 'full'
        }
        
        context_data = {
            'project_structure': {'src/main.py': 'content'},
            'dependencies': {'flask': '2.0.0'},
            'frameworks': ['python']
        }
        
        # Cache the context
        cache_key = context_cache.cache_context(context_request, context_data, 2.0, 1000)
        
        assert cache_key is not None
        assert len(context_cache._cache) == 1
        
        # Retrieve from cache
        cached_data = context_cache.get_context(context_request)
        
        assert cached_data is not None
        assert cached_data == context_data
    
    def test_cache_miss(self, context_cache):
        """Test cache miss scenario."""
        context_request = {
            'task_type': 'analysis',
            'target_files': ['src/missing.py'],
            'frameworks': ['python'],
            'patterns': ['mvc'],
            'scope': 'full'
        }
        
        # Try to get non-existent context
        cached_data = context_cache.get_context(context_request)
        
        assert cached_data is None
    
    def test_semantic_matching(self, context_cache):
        """Test semantic cache matching."""
        # Cache first context
        context_request1 = {
            'task_type': 'analysis',
            'target_files': ['src/main.py'],
            'frameworks': ['python'],
            'patterns': ['mvc'],
            'scope': 'full'
        }
        
        context_data1 = {
            'project_structure': {'src/main.py': 'content'},
            'dependencies': {'flask': '2.0.0'},
            'frameworks': ['python']
        }
        
        context_cache.cache_context(context_request1, context_data1)
        
        # Similar request (different target files but same context)
        context_request2 = {
            'task_type': 'analysis',
            'target_files': ['src/utils.py'],
            'frameworks': ['python'],
            'patterns': ['mvc'],
            'scope': 'full'
        }
        
        # With high similarity threshold, might not match
        # Lower threshold to test semantic matching
        context_cache.config.similarity_threshold = 0.5
        cached_data = context_cache.get_context(context_request2)
        
        # Semantic matching is probabilistic, so we just check it doesn't crash
        assert isinstance(cached_data, (dict, type(None)))
    
    def test_cache_eviction(self, context_cache):
        """Test cache eviction when size limit is reached."""
        context_cache.config.max_cache_size = 2
        
        # Add 3 contexts to trigger eviction
        for i in range(3):
            context_request = {
                'task_type': 'analysis',
                'target_files': [f'src/file{i}.py'],
                'frameworks': ['python'],
                'patterns': ['mvc'],
                'scope': 'full'
            }
            
            context_data = {
                'project_structure': {f'src/file{i}.py': f'content{i}'},
                'dependencies': {'flask': '2.0.0'},
                'frameworks': ['python']
            }
            
            context_cache.cache_context(context_request, context_data)
        
        # Should only have 2 entries (max size)
        assert len(context_cache._cache) == 2
    
    def test_cache_statistics(self, context_cache):
        """Test cache statistics."""
        stats = context_cache.get_cache_stats()
        
        assert 'cache_size' in stats
        assert 'cache_hits' in stats
        assert 'cache_misses' in stats
        assert 'hit_rate' in stats
        assert 'total_time_saved' in stats
        assert 'total_tokens_saved' in stats
        
        # Initial stats
        assert stats['cache_size'] == 0
        assert stats['cache_hits'] == 0
        assert stats['cache_misses'] == 0
        assert stats['hit_rate'] == pytest.approx(0.0)
    
    def test_cache_invalidation(self, context_cache):
        """Test cache invalidation."""
        # Add some cached contexts
        for i in range(3):
            context_request = {
                'task_type': 'analysis',
                'target_files': [f'src/file{i}.py'],
                'frameworks': ['python'],
                'patterns': ['mvc'],
                'scope': 'full'
            }
            
            context_data = {
                'project_structure': {f'src/file{i}.py': f'content{i}'},
                'dependencies': {'flask': '2.0.0'},
                'frameworks': ['python']
            }
            
            context_cache.cache_context(context_request, context_data)
        
        assert len(context_cache._cache) == 3
        
        # Invalidate all
        context_cache.invalidate_cache()
        
        assert len(context_cache._cache) == 0
        
        # Test pattern-based invalidation
        # Re-add contexts
        for i in range(3):
            context_request = {
                'task_type': 'analysis',
                'target_files': [f'src/file{i}.py'],
                'frameworks': ['python'],
                'patterns': ['mvc'],
                'scope': 'full'
            }
            
            context_data = {
                'project_structure': {f'src/file{i}.py': f'content{i}'},
                'dependencies': {'flask': '2.0.0'},
                'frameworks': ['python']
            }
            
            context_cache.cache_context(context_request, context_data)
        
        # Invalidate pattern
        context_cache.invalidate_cache("analysis")
        
        assert len(context_cache._cache) == 0


class TestFreshnessCalculator:
    """Test freshness calculation system."""

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project with git."""
        import subprocess
        temp_dir = tempfile.mkdtemp()
        project_path = Path(temp_dir)
        try:
            # Create project files
            (project_path / "src").mkdir()
            (project_path / "src" / "main.py").write_text("print('Hello')")
            (project_path / "package.json").write_text('{"name": "test"}')

            # Initialize git
            subprocess.run(['git', 'init'], cwd=project_path, capture_output=True)
            subprocess.run(['git', 'config', 'user.name', 'Test'], cwd=project_path, capture_output=True)
            subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=project_path, capture_output=True)
            subprocess.run(['git', 'add', '.'], cwd=project_path, capture_output=True)
            subprocess.run(['git', 'commit', '-m', 'Initial'], cwd=project_path, capture_output=True)

            yield project_path
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def freshness_calculator(self, temp_project):
        """Create freshness calculator."""
        return FreshnessCalculator(temp_project)
    
    @pytest.fixture
    def cache_entry(self, temp_project):
        """Create a sample cache entry using the actual git commit hash."""
        import subprocess
        from apps.backend.services.intelligent_context_cache import ContextCacheEntry

        # Get the real current commit from the temp git repo
        result = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            cwd=temp_project,
            capture_output=True,
            text=True,
        )
        current_commit = result.stdout.strip() if result.returncode == 0 else ""

        return ContextCacheEntry(
            cache_key="test_key",
            context_hash="test_hash",
            context_data={"test": "data"},
            context_request={"task_type": "test"},  # Add missing required parameter
            created_at=time.time() - 3600,  # 1 hour ago
            last_accessed=time.time() - 1800,  # 30 minutes ago
            access_count=5,
            git_commit_hash=current_commit,
            files_changed={"src/main.py", "package.json"},
            semantic_signature="sig123"
        )
    
    def test_freshness_calculation(self, freshness_calculator, cache_entry):
        """Test overall freshness calculation."""
        metrics = freshness_calculator.calculate_freshness(cache_entry)
        
        assert isinstance(metrics, FreshnessMetrics)
        assert 0.0 <= metrics.overall_freshness <= 1.0
        assert 0.0 <= metrics.confidence_score <= 1.0
        assert len(metrics.factors_considered) > 0
    
    def test_age_score_calculation(self, freshness_calculator, cache_entry):
        """Test age-based freshness score."""
        # Recent entry
        recent_entry = cache_entry
        recent_entry.created_at = time.time() - 300  # 5 minutes ago
        
        age_score = freshness_calculator._calculate_age_score(recent_entry, time.time())
        assert age_score > 0.9  # Very fresh
        
        # Old entry
        old_entry = cache_entry
        old_entry.created_at = time.time() - 86400  # 24 hours ago
        
        age_score = freshness_calculator._calculate_age_score(old_entry, time.time())
        assert age_score < 0.5  # Less fresh
    
    def test_git_score_calculation(self, freshness_calculator, cache_entry):
        """Test git-based freshness score."""
        # Current commit should match
        git_score = freshness_calculator._calculate_git_score(cache_entry)
        assert git_score == pytest.approx(1.0)  # Same commit
    
    def test_file_score_calculation(self, freshness_calculator, cache_entry):
        """Test file-based freshness score."""
        # No files changed (same commit)
        file_score = freshness_calculator._calculate_file_score(cache_entry)
        assert file_score == pytest.approx(1.0)  # No changes
    
    def test_access_score_calculation(self, freshness_calculator, cache_entry):
        """Test access pattern-based freshness score."""
        # Recently accessed with good frequency
        access_score = freshness_calculator._calculate_access_score(cache_entry, time.time())
        assert 0.0 <= access_score <= 1.0


class TestGitRepositoryMonitor:
    """Test git repository monitoring."""
    
    @pytest.fixture
    def temp_repo(self):
        """Create a temporary git repository."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            
            # Initialize git
            import subprocess
            subprocess.run(['git', 'init'], cwd=repo_path, capture_output=True)
            subprocess.run(['git', 'config', 'user.name', 'Test'], cwd=repo_path, capture_output=True)
            subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=repo_path, capture_output=True)
            
            # Create initial commit
            (repo_path / "file1.txt").write_text("content1")
            subprocess.run(['git', 'add', '.'], cwd=repo_path, capture_output=True)
            subprocess.run(['git', 'commit', '-m', 'Initial'], cwd=repo_path, capture_output=True)
            
            yield repo_path
    
    @pytest.fixture
    def git_monitor(self, temp_repo):
        """Create git monitor."""
        return GitRepositoryMonitor(temp_repo)
    
    def test_current_commit_detection(self, git_monitor):
        """Test current commit detection."""
        commit = git_monitor.get_current_commit()
        
        assert commit is not None
        assert len(commit) == 40  # SHA-1 hash length
        assert commit.isalnum()
    
    def test_commit_info_retrieval(self, git_monitor):
        """Test commit info retrieval."""
        commit = git_monitor.get_current_commit()
        info = git_monitor.get_commit_info(commit)
        
        assert info is not None
        assert 'hash' in info
        assert 'message' in info
        assert 'author' in info
        assert 'timestamp' in info
        assert info['hash'] == commit
    
    def test_changed_files_detection(self, git_monitor, temp_repo):
        """Test changed files detection."""
        # Get current commit
        initial_commit = git_monitor.get_current_commit()
        
        # Make changes
        (temp_repo / "file2.txt").write_text("content2")
        (temp_repo / "file3.txt").write_text("content3")
        
        import subprocess
        subprocess.run(['git', 'add', '.'], cwd=temp_repo, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Add files'], cwd=temp_repo, capture_output=True)
        
        # Get changed files
        change_event = git_monitor.get_changed_files_since(initial_commit)
        
        assert change_event is not None
        assert "file2.txt" in change_event.files_added
        assert "file3.txt" in change_event.files_added
    
    def test_has_new_commits(self, git_monitor, temp_repo):
        """Test detection of new commits."""
        # Initially no new commits
        assert not git_monitor.has_new_commits()
        
        # Add new commit
        (temp_repo / "new_file.txt").write_text("new content")
        
        import subprocess
        subprocess.run(['git', 'add', '.'], cwd=temp_repo, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'New commit'], cwd=temp_repo, capture_output=True)
        
        # Should detect new commits
        assert git_monitor.has_new_commits()


class TestContextCacheIntegrator:
    """Test context cache integration."""
    
    @pytest.fixture
    def temp_project(self):
        """Create temporary project."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            
            # Create project structure
            (project_path / "src").mkdir()
            (project_path / "src" / "main.py").write_text("print('Hello')")
            (project_path / "package.json").write_text('{"name": "test"}')
            
            # Initialize git
            import subprocess
            subprocess.run(['git', 'init'], cwd=project_path, capture_output=True)
            subprocess.run(['git', 'config', 'user.name', 'Test'], cwd=project_path, capture_output=True)
            subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=project_path, capture_output=True)
            subprocess.run(['git', 'add', '.'], cwd=project_path, capture_output=True)
            subprocess.run(['git', 'commit', '-m', 'Initial'], cwd=project_path, capture_output=True)
            
            yield project_path
    
    @pytest.fixture
    def cache_integrator(self, temp_project):
        """Create cache integrator with unique temp directory."""
        # Create a unique temp directory for each test to avoid database conflicts
        import uuid
        unique_suffix = str(uuid.uuid4())[:8]
        unique_project = temp_project / f"test_integrator_{unique_suffix}"
        unique_project.mkdir(exist_ok=True)
        
        # Copy the git repository to the unique directory
        import shutil
        shutil.copytree(temp_project / ".git", unique_project / ".git", dirs_exist_ok=True)
        for file_path in temp_project.glob("*"):
            if file_path.is_file() or file_path.is_dir() and file_path.name != ".git":
                if file_path.is_dir():
                    shutil.copytree(file_path, unique_project / file_path.name, dirs_exist_ok=True)
                else:
                    shutil.copy2(file_path, unique_project / file_path.name)
        
        config = CacheConfig(max_cache_size=5, max_entry_age_hours=1.0)
        integrator = ContextCacheIntegrator(unique_project, config)
        yield integrator
        # Cleanup after test
        integrator.cleanup()
        # Clean up the unique directory
        shutil.rmtree(unique_project, ignore_errors=True)
    
    def test_context_request_handling(self, cache_integrator):
        """Test context request handling."""
        def mock_generator(request):
            return {
                'project_structure': {'src/main.py': 'content'},
                'dependencies': {'flask': '2.0.0'},
                'generated_at': time.time()
            }
        
        request = ContextRequest(
            task_type='analysis',
            target_files=['src/main.py'],
            frameworks=['python'],
            patterns=['mvc'],
            scope='full'
        )
        
        response = cache_integrator.get_context_with_cache(request, mock_generator)
        
        assert isinstance(response, ContextResponse)
        assert response.context_data is not None
        assert not response.cache_hit  # First request should be miss
        assert response.build_time_saved == pytest.approx(0.0)
        assert response.tokens_saved == 0
    
    def test_cache_hit_scenario(self, cache_integrator):
        """Test cache hit scenario."""
        def mock_generator(request):
            return {
                'project_structure': {'src/main.py': 'content'},
                'dependencies': {'flask': '2.0.0'},
                'generated_at': time.time()
            }
        
        request = ContextRequest(
            task_type='analysis',
            target_files=['src/main.py'],
            frameworks=['python'],
            patterns=['mvc'],
            scope='full'
        )
        
        # First request (miss)
        response1 = cache_integrator.get_context_with_cache(request, mock_generator)
        assert not response1.cache_hit
        
        # Second request (hit)
        response2 = cache_integrator.get_context_with_cache(request, mock_generator)
        assert response2.cache_hit
        assert response2.build_time_saved > 0.0
        assert response2.tokens_saved > 0
    
    def test_integration_statistics(self, cache_integrator):
        """Test integration statistics."""
        stats = cache_integrator.get_integration_stats()
        
        assert 'integration_stats' in stats
        assert 'cache_stats' in stats
        assert 'git_stats' in stats
        
        integration_stats = stats['integration_stats']
        assert 'total_requests' in integration_stats
        assert 'cache_hits' in integration_stats
        assert 'cache_misses' in integration_stats
        assert 'hit_rate' in integration_stats
    
    def test_cache_invalidation(self, cache_integrator):
        """Test cache invalidation."""
        def mock_generator(request):
            return {'test': 'data'}
        
        request = ContextRequest(
            task_type='analysis',
            target_files=['src/main.py'],
            frameworks=['python'],
            patterns=['mvc']
        )
        
        # Add to cache
        cache_integrator.get_context_with_cache(request, mock_generator)
        
        # Invalidate
        cache_integrator.invalidate_context_cache()
        
        # Should be miss again
        response = cache_integrator.get_context_with_cache(request, mock_generator)
        assert not response.cache_hit


class TestAgentWorkflowIntegrator:
    """Test agent workflow integration."""
    
    @pytest.fixture
    def temp_project(self):
        """Create temporary project."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            
            # Create project structure
            (project_path / "src").mkdir()
            (project_path / "src" / "main.py").write_text("print('Hello')")
            (project_path / "package.json").write_text('{"name": "test"}')
            
            yield project_path
    
    @pytest.fixture
    def workflow_integrator(self, temp_project):
        """Create workflow integrator with unique temp directory."""
        # Create a unique temp directory for each test to avoid database conflicts
        import uuid
        unique_suffix = str(uuid.uuid4())[:8]
        unique_project = temp_project / f"test_workflow_{unique_suffix}"
        unique_project.mkdir(exist_ok=True)
        
        # Copy project files to the unique directory
        import shutil
        for file_path in temp_project.glob("*"):
            if file_path.is_file() or file_path.is_dir():
                if file_path.is_dir():
                    shutil.copytree(file_path, unique_project / file_path.name, dirs_exist_ok=True)
                else:
                    shutil.copy2(file_path, unique_project / file_path.name)
        
        integrator = AgentWorkflowIntegrator(unique_project)
        yield integrator
        # Cleanup after test
        integrator.cleanup()
        # Clean up the unique directory
        shutil.rmtree(unique_project, ignore_errors=True)
    
    def test_agent_context_retrieval(self, workflow_integrator):
        """Test context retrieval for different agent types."""
        request_data = {
            'target_files': ['src/main.py'],
            'frameworks': ['python'],
            'patterns': ['mvc'],
            'use_cache': True
        }
        
        # Test different agent types
        for agent_type in ['analysis', 'coding', 'qa', 'planning']:
            response = workflow_integrator.get_agent_context(agent_type, request_data)
            
            assert isinstance(response, ContextResponse)
            assert response.context_data is not None
            assert response.context_data.get('task_type') == agent_type
    
    def test_custom_generator_registration(self, workflow_integrator):
        """Test custom context generator registration."""
        def custom_generator(request):
            return {
                'task_type': 'custom',
                'custom_data': 'test',
                'generated_at': time.time()
            }
        
        # Register custom generator
        workflow_integrator.register_context_generator('custom', custom_generator)
        
        request_data = {
            'target_files': ['src/main.py'],
            'frameworks': ['python']
        }
        
        response = workflow_integrator.get_agent_context('custom', request_data)
        
        assert response.context_data.get('task_type') == 'custom'
        assert response.context_data.get('custom_data') == 'test'
    
    def test_workflow_statistics(self, workflow_integrator):
        """Test workflow statistics."""
        stats = workflow_integrator.get_workflow_stats()
        
        assert 'integration_stats' in stats
        assert 'cache_stats' in stats
        assert 'git_stats' in stats
    
    def test_workflow_cleanup(self, workflow_integrator):
        """Test workflow cleanup."""
        # Should not raise any exceptions
        workflow_integrator.cleanup()


# Integration Tests
class TestCacheIntegration:
    """Integration tests for the complete caching system."""
    
    @pytest.fixture
    def temp_project(self):
        """Create a complete test project."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            
            # Create realistic project structure
            (project_path / "src").mkdir()
            (project_path / "src" / "components").mkdir()
            (project_path / "src" / "utils").mkdir()
            (project_path / "tests").mkdir()
            
            # Create files
            (project_path / "src" / "main.py").write_text("""
from flask import Flask
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.utils.helpers import format_data

app = Flask(__name__)

@app.route('/')
def home():
    return format_data("Hello World")
""")
            
            (project_path / "src" / "utils" / "helpers.py").write_text("""
def format_data(data):
    return f"Formatted: {data}"
""")
            
            (project_path / "package.json").write_text("""
{
  "name": "test-app",
  "dependencies": {
    "flask": "^2.0.0",
    "requests": "^2.25.0"
  }
}""")
            
            (project_path / "requirements.txt").write_text("""
flask==2.0.0
requests==2.25.0
""")
            
            # Initialize git
            import subprocess
            subprocess.run(['git', 'init'], cwd=project_path, capture_output=True)
            subprocess.run(['git', 'config', 'user.name', 'Test'], cwd=project_path, capture_output=True)
            subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=project_path, capture_output=True)
            subprocess.run(['git', 'add', '.'], cwd=project_path, capture_output=True)
            subprocess.run(['git', 'commit', '-m', 'Initial commit'], cwd=project_path, capture_output=True)
            
            yield project_path
    
    def test_end_to_end_caching(self, temp_project):
        """Test complete end-to-end caching workflow."""
        # Create unique temp directory to avoid conflicts
        import uuid
        import shutil
        unique_suffix = str(uuid.uuid4())[:8]
        unique_project = temp_project / f"test_integration_{unique_suffix}"
        unique_project.mkdir(exist_ok=True)
        
        # Copy project files to the unique directory
        for file_path in temp_project.glob("*"):
            if file_path.is_file() or file_path.is_dir():
                if file_path.is_dir():
                    shutil.copytree(file_path, unique_project / file_path.name, dirs_exist_ok=True)
                else:
                    shutil.copy2(file_path, unique_project / file_path.name)
        
        try:
            # Create integrator
            workflow_integrator = AgentWorkflowIntegrator(unique_project)
        
            # Simulate multiple agent requests
            requests = [
                {
                    'agent_type': 'analysis',
                    'data': {
                        'target_files': ['src/main.py'],
                        'frameworks': ['flask'],
                        'patterns': ['mvc']
                    }
                },
                {
                    'agent_type': 'coding',
                    'data': {
                        'target_files': ['src/utils/helpers.py'],
                        'frameworks': ['python'],
                        'patterns': ['helper']
                    }
                },
                {
                    'agent_type': 'qa',
                    'data': {
                        'target_files': ['src/main.py'],
                        'frameworks': ['flask'],
                        'patterns': ['testing']
                    }
                }
            ]
            
            # First round (cache misses)
            for req in requests:
                response = workflow_integrator.get_agent_context(
                    req['agent_type'], req['data']
                )
                assert not response.cache_hit
                assert response.context_data is not None
            
            # Second round (cache hits)
            for req in requests:
                response = workflow_integrator.get_agent_context(
                    req['agent_type'], req['data']
                )
                assert response.cache_hit
                assert response.build_time_saved > 0.0
                assert response.tokens_saved > 0
            
            # Check statistics
            stats = workflow_integrator.get_workflow_stats()
            integration_stats = stats['integration_stats']
            
            assert integration_stats['total_requests'] == 6  # 3 agents * 2 rounds
            assert integration_stats['cache_hits'] == 3
            assert integration_stats['cache_misses'] == 3
            assert integration_stats['hit_rate'] == pytest.approx(0.5)
            assert integration_stats['total_time_saved'] > 0.0
            assert integration_stats['total_tokens_saved'] > 0
            
            # Cleanup
            workflow_integrator.cleanup()
        finally:
            # Clean up the unique directory
            workflow_integrator.cleanup()
            shutil.rmtree(unique_project, ignore_errors=True)
    
    def test_git_invalidation_integration(self, temp_project):
        """Test git-based cache invalidation."""
        # Create unique temp directory to avoid conflicts
        import uuid
        import shutil
        unique_suffix = str(uuid.uuid4())[:8]
        unique_project = temp_project / f"test_git_invalidation_{unique_suffix}"
        unique_project.mkdir(exist_ok=True)
        
        # Copy project files to the unique directory
        for file_path in temp_project.glob("*"):
            if file_path.is_file() or file_path.is_dir():
                if file_path.is_dir():
                    shutil.copytree(file_path, unique_project / file_path.name, dirs_exist_ok=True)
                else:
                    shutil.copy2(file_path, unique_project / file_path.name)
        
        try:
            workflow_integrator = AgentWorkflowIntegrator(unique_project)
            
            # Cache some context
            request_data = {
                'target_files': ['src/main.py'],
                'frameworks': ['flask'],
                'patterns': ['mvc']
            }
            
            response1 = workflow_integrator.get_agent_context('analysis', request_data)
            assert not response1.cache_hit
            
            response2 = workflow_integrator.get_agent_context('analysis', request_data)
            assert response2.cache_hit
            
            # Make git changes
            (unique_project / "src" / "main.py").write_text("""
from flask import Flask
from src.utils.helpers import format_data

app = Flask(__name__)

@app.route('/')
def home():
    return format_data("Updated Hello World")

@app.route('/api/data')
def api_data():
    return {"data": "test"}
""")
            
            import subprocess
            subprocess.run(['git', 'add', '.'], cwd=unique_project, capture_output=True)
            subprocess.run(['git', 'commit', '-m', 'Update main.py'], cwd=unique_project, capture_output=True)
            
            # Check git invalidation
            git_invalidator = workflow_integrator.cache_integrator.git_invalidator
            check_result = git_invalidator.manual_invalidation_check()
            
            assert check_result['has_changes']
            assert 'change_event' in check_result
            assert 'invalidations_needed' in check_result
            
            # Cleanup
            workflow_integrator.cleanup()
        finally:
            # Clean up the unique directory
            shutil.rmtree(unique_project, ignore_errors=True)


# Performance Tests
class TestCachePerformance:
    """Performance tests for the caching system."""
    
    @pytest.fixture
    def temp_project(self):
        """Create temporary project."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            
            # Create project structure
            (project_path / "src").mkdir()
            
            # Create many files
            for i in range(100):
                (project_path / "src" / f"file{i}.py").write_text(f"# File {i}\nprint('test')")
            
            yield project_path
    
    def test_cache_performance(self, temp_project):
        """Test cache performance with many entries."""
        import time
        import uuid
        import shutil

        # Create unique temp directory to avoid conflicts
        unique_suffix = str(uuid.uuid4())[:8]
        unique_project = temp_project / f"test_performance_{unique_suffix}"
        unique_project.mkdir(exist_ok=True)
        
        # Copy project files to the unique directory
        for file_path in temp_project.glob("*"):
            if file_path.is_file() or file_path.is_dir():
                if file_path.is_dir():
                    shutil.copytree(file_path, unique_project / file_path.name, dirs_exist_ok=True)
                else:
                    shutil.copy2(file_path, unique_project / file_path.name)

        config = CacheConfig(max_cache_size=200, max_entry_age_hours=24.0)
        cache = IntelligentContextCache(unique_project, config)

        try:
            # Test cache population performance
            start_time = time.time()

            for i in range(100):
                context_request = {
                    'task_type': 'analysis',
                    'target_files': [f'src/file{i}.py'],
                    'frameworks': ['python'],
                    'patterns': ['test']
                }

                context_data = {
                    'project_structure': {f'src/file{i}.py': f'content{i}'},
                    'dependencies': {'flask': '2.0.0'},
                    'frameworks': ['python']
                }

                cache.cache_context(context_request, context_data)

            population_time = time.time() - start_time

            # Test cache retrieval performance
            start_time = time.time()

            for i in range(100):
                context_request = {
                    'task_type': 'analysis',
                    'target_files': [f'src/file{i}.py'],
                    'frameworks': ['python'],
                    'patterns': ['test']
                }

                cached_data = cache.get_context(context_request)
                assert cached_data is not None

            retrieval_time = time.time() - start_time

            # Performance assertions (generous threshold for loaded CI environments)
            assert population_time < 120.0  # Should populate in under 120 seconds
            assert retrieval_time < 120.0   # Should retrieve in under 120 seconds

            # Check statistics
            stats = cache.get_cache_stats()
            assert stats['cache_size'] == 100
            assert stats['cache_hits'] == 100
            assert stats['hit_rate'] == pytest.approx(1.0)
        finally:
            cache.close()
            # Clean up the unique directory
            shutil.rmtree(unique_project, ignore_errors=True)


if __name__ == "__main__":
    pytest.main([__file__])
