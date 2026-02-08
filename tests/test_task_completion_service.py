"""
Tests pour le service de complétion de tâches
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from services.task_completion_service import (
    TaskCompletionService,
    create_task_completion_service,
)

@pytest.fixture
def temp_project_dir():
    """Crée un répertoire de projet temporaire"""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)
        # Initialiser un repo git de base
        (project_path / ".git").mkdir()
        yield project_path


@pytest.fixture
def mock_worktree_manager():
    """Mock du WorktreeManager"""
    with patch("services.task_completion_service.WorktreeManager") as mock:
        yield mock


def test_create_task_completion_service(temp_project_dir):
    """Test de la factory de création du service"""
    service = create_task_completion_service(
        temp_project_dir, base_branch="main"
    )
    
    assert service is not None
    assert isinstance(service, TaskCompletionService)
    assert service.project_path == temp_project_dir
    assert service.base_branch == "main"


def test_complete_task_success(temp_project_dir, mock_worktree_manager):
    """Test de complétion réussie d'une tâche"""
    # Setup mock
    mock_instance = MagicMock()
    mock_worktree_manager.return_value = mock_instance
    
    # Mock push_branch success
    mock_instance.push_branch.return_value = {
        "success": True,
        "branch": "auto-claude/test-spec",
    }
    
    # Mock create_pull_request success
    mock_instance.create_pull_request.return_value = {
        "success": True,
        "pr_url": "https://github.com/owner/repo/pull/123",
        "already_exists": False,
    }
    
    # Create service
    service = TaskCompletionService(
        project_path=temp_project_dir, base_branch="develop"
    )
    service.worktree_manager = mock_instance
    
    # Complete task
    result = service.complete_task(
        spec_id="test-spec",
        task_title="Test Task",
        task_description="Test description",
    )
    
    # Assertions
    assert result["success"] is True
    assert result["pr_url"] == "https://github.com/owner/repo/pull/123"
    assert result["pr_already_exists"] is False
    assert result["error"] is None
    
    # Vérifier les appels
    mock_instance.push_branch.assert_called_once_with("test-spec", force=False)
    mock_instance.create_pull_request.assert_called_once()


def test_complete_task_push_failure(temp_project_dir, mock_worktree_manager):
    """Test de complétion avec échec du push"""
    # Setup mock
    mock_instance = MagicMock()
    mock_worktree_manager.return_value = mock_instance
    
    # Mock push_branch failure
    mock_instance.push_branch.return_value = {
        "success": False,
        "error": "Network error",
    }
    
    # Create service
    service = TaskCompletionService(
        project_path=temp_project_dir, base_branch="develop"
    )
    service.worktree_manager = mock_instance
    
    # Complete task
    result = service.complete_task(
        spec_id="test-spec",
        task_title="Test Task",
    )
    
    # Assertions
    assert result["success"] is False
    assert result["pr_url"] is None
    assert "Échec du push de la branche" in result["error"]
    
    # Vérifier que create_pull_request n'a pas été appelé
    mock_instance.create_pull_request.assert_not_called()


def test_complete_task_pr_creation_failure(
    temp_project_dir, mock_worktree_manager
):
    """Test de complétion avec échec de création de PR"""
    # Setup mock
    mock_instance = MagicMock()
    mock_worktree_manager.return_value = mock_instance
    
    # Mock push_branch success
    mock_instance.push_branch.return_value = {
        "success": True,
        "branch": "auto-claude/test-spec",
    }
    
    # Mock create_pull_request failure
    mock_instance.create_pull_request.return_value = {
        "success": False,
        "error": "Authentication failed",
    }
    
    # Create service
    service = TaskCompletionService(
        project_path=temp_project_dir, base_branch="develop"
    )
    service.worktree_manager = mock_instance
    
    # Complete task
    result = service.complete_task(
        spec_id="test-spec",
        task_title="Test Task",
    )
    
    # Assertions
    assert result["success"] is False
    assert result["pr_url"] is None
    assert "Échec de la création de la PR" in result["error"]


def test_complete_task_with_custom_target_branch(
    temp_project_dir, mock_worktree_manager
):
    """Test de complétion avec branche cible personnalisée"""
    # Setup mock
    mock_instance = MagicMock()
    mock_worktree_manager.return_value = mock_instance
    
    # Mock success
    mock_instance.push_branch.return_value = {"success": True, "branch": "test"}
    mock_instance.create_pull_request.return_value = {
        "success": True,
        "pr_url": "https://github.com/owner/repo/pull/123",
        "already_exists": False,
    }
    
    # Create service
    service = TaskCompletionService(
        project_path=temp_project_dir, base_branch="develop"
    )
    service.worktree_manager = mock_instance
    
    # Complete task with custom target
    result = service.complete_task(
        spec_id="test-spec",
        task_title="Test Task",
        target_branch="main",
    )
    
    # Assertions
    assert result["success"] is True
    
    # Vérifier que la branche cible est bien passée
    call_args = mock_instance.create_pull_request.call_args
    assert call_args[1]["target_branch"] == "main"


def test_complete_task_pr_already_exists(
    temp_project_dir, mock_worktree_manager
):
    """Test de complétion quand la PR existe déjà"""
    # Setup mock
    mock_instance = MagicMock()
    mock_worktree_manager.return_value = mock_instance
    
    # Mock success with existing PR
    mock_instance.push_branch.return_value = {"success": True, "branch": "test"}
    mock_instance.create_pull_request.return_value = {
        "success": True,
        "pr_url": "https://github.com/owner/repo/pull/123",
        "already_exists": True,
    }
    
    # Create service
    service = TaskCompletionService(
        project_path=temp_project_dir, base_branch="develop"
    )
    service.worktree_manager = mock_instance
    
    # Complete task
    result = service.complete_task(
        spec_id="test-spec",
        task_title="Test Task",
    )
    
    # Assertions
    assert result["success"] is True
    assert result["pr_already_exists"] is True
    assert result["pr_url"] == "https://github.com/owner/repo/pull/123"


def test_build_pr_body():
    """Test de construction du corps de la PR"""
    service = TaskCompletionService(
        project_path=Path("/tmp/test"), base_branch="develop"
    )
    
    # Test avec description
    body = service._build_pr_body("My Task", "This is a test task")
    assert "My Task" in body
    assert "This is a test task" in body
    assert "Checklist de vérification" in body
    assert "validation humaine" in body
    
    # Test sans description
    body_no_desc = service._build_pr_body("My Task", None)
    assert "My Task" in body_no_desc
    assert "This is a test task" not in body_no_desc
    assert "Checklist de vérification" in body_no_desc

