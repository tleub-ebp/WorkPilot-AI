"""
Tests for Learning Mode module
"""

from datetime import datetime
from pathlib import Path

import pytest

from apps.backend.learning import (
    DocType,
    DocumentationGenerator,
    ExplanationLevel,
    LearningMode,
    LearningModeConfig,
)


def test_learning_mode_initialization():
    """Test Learning Mode initializes correctly"""
    config = LearningModeConfig(
        enabled=True,
        explanation_level=ExplanationLevel.INTERMEDIATE
    )
    learning_mode = LearningMode(config)
    
    assert learning_mode.config.enabled is True
    assert learning_mode.config.explanation_level == ExplanationLevel.INTERMEDIATE
    assert len(learning_mode.explanations) == 0


def test_explain_tool_use():
    """Test tool usage explanation"""
    learning_mode = LearningMode()
    
    explanation = learning_mode.explain_tool_use(
        tool_name="Read",
        tool_input={"file_path": "test.py"},
        reason="Analyzing code",
        expected_outcome="Understanding structure"
    )
    
    assert explanation is not None
    assert explanation.category == "tool_use"
    assert "Read" in explanation.title
    assert len(learning_mode.explanations) == 1


def test_explain_decision():
    """Test decision explanation"""
    learning_mode = LearningMode()
    
    explanation = learning_mode.explain_decision(
        decision="Use async/await",
        reasoning="Better performance for I/O operations",
        alternatives_considered=[
            {
                "name": "Threading",
                "pros": "Familiar",
                "cons": "GIL limitations",
                "reason_rejected": "Not efficient for I/O"
            }
        ]
    )
    
    assert explanation is not None
    assert explanation.category == "decision"
    assert "async/await" in explanation.title
    assert len(explanation.alternative_approaches) == 1


def test_explanation_levels():
    """Test different explanation levels"""
    levels = [
        ExplanationLevel.BEGINNER,
        ExplanationLevel.INTERMEDIATE,
        ExplanationLevel.ADVANCED,
        ExplanationLevel.EXPERT
    ]
    
    for level in levels:
        config = LearningModeConfig(explanation_level=level)
        learning_mode = LearningMode(config)
        
        explanation = learning_mode.explain_tool_use(
            tool_name="Grep",
            tool_input={"pattern": "*.py"},
            reason="Finding Python files",
            expected_outcome="List of files"
        )
        
        assert explanation is not None
        assert explanation.difficulty == level


def test_session_summary():
    """Test session summary generation"""
    learning_mode = LearningMode()
    
    # Add some explanations
    learning_mode.explain_tool_use(
        "Read", {"file": "test.py"}, "Testing", "Result"
    )
    learning_mode.explain_decision(
        "Use FastAPI", "Modern and fast", []
    )
    
    summary = learning_mode.generate_session_summary()
    
    assert summary["total_explanations"] == 2
    assert "tool_use" in summary["explanations_by_category"]
    assert "decision" in summary["explanations_by_category"]


def test_markdown_report():
    """Test markdown report generation"""
    learning_mode = LearningMode()
    
    learning_mode.explain_tool_use(
        "Read", {"file": "test.py"}, "Testing", "Result"
    )
    
    report = learning_mode.generate_markdown_report()
    
    assert "# Learning Session Report" in report
    assert "Tool Usage" in report
    assert "Session Summary" in report


def test_save_session(tmp_path):
    """Test saving learning session"""
    learning_mode = LearningMode()
    
    learning_mode.explain_tool_use(
        "Read", {"file": "test.py"}, "Testing", "Result"
    )
    
    output_dir = tmp_path / "learning"
    session_file = learning_mode.save_session(output_dir)
    
    assert session_file is not None
    assert session_file.exists()
    assert session_file.suffix == ".json"


def test_disabled_learning_mode():
    """Test that disabled Learning Mode doesn't generate explanations"""
    config = LearningModeConfig(enabled=False)
    learning_mode = LearningMode(config)
    
    explanation = learning_mode.explain_tool_use(
        "Read", {"file": "test.py"}, "Testing", "Result"
    )
    
    assert explanation is None
    assert len(learning_mode.explanations) == 0


@pytest.mark.asyncio
async def test_documentation_generator():
    """Test documentation generator"""
    doc_gen = DocumentationGenerator(Path("/tmp/test"))
    
    readme = await doc_gen.generate_readme(
        project_name="Test Project",
        description="A test project",
        features=["Feature 1", "Feature 2"]
    )
    
    assert "# Test Project" in readme
    assert "Feature 1" in readme
    assert "Feature 2" in readme


@pytest.mark.asyncio
async def test_api_documentation():
    """Test API documentation generation"""
    doc_gen = DocumentationGenerator(Path("/tmp/test"))
    
    api_doc = await doc_gen.generate_api_documentation(
        api_name="Test API",
        endpoints=[
            {
                "method": "GET",
                "path": "/users",
                "description": "List users"
            }
        ]
    )
    
    assert "# Test API" in api_doc
    assert "GET /users" in api_doc
    assert "List users" in api_doc


def test_explanation_to_dict():
    """Test explanation serialization"""
    learning_mode = LearningMode()
    
    explanation = learning_mode.explain_tool_use(
        "Read", {"file": "test.py"}, "Testing", "Result"
    )
    
    data = explanation.to_dict()
    
    assert "timestamp" in data
    assert "category" in data
    assert "title" in data
    assert "explanation" in data
    assert "difficulty" in data
    assert data["category"] == "tool_use"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

