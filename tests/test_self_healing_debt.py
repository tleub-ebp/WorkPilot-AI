"""
Tests for Self-Healing Codebase - Technical Debt Tracker
========================================================
"""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from apps.backend.self_healing.debt_tracker import (
    DebtCategory,
    DebtItem,
    TechnicalDebtTracker,
)


@pytest.fixture
def temp_project():
    """Create a temporary project directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def tracker(temp_project):
    """Create a debt tracker."""
    return TechnicalDebtTracker(temp_project)


def test_debt_item_creation():
    """Test creating a debt item."""
    item = DebtItem(
        id="test-1",
        category=DebtCategory.CODE_QUALITY,
        title="Test Issue",
        description="Test description",
        file="test.py",
        severity="high",
        effort="medium",
        created_at=datetime.now(),
    )
    
    assert item.id == "test-1"
    assert item.category == DebtCategory.CODE_QUALITY
    assert item.severity == "high"
    assert item.resolved_at is None


def test_debt_item_age_calculation():
    """Test age calculation."""
    # Create item from 10 days ago
    past_date = datetime.now() - timedelta(days=10)
    item = DebtItem(
        id="test-1",
        category=DebtCategory.PERFORMANCE,
        title="Old Issue",
        description="Test",
        file="test.py",
        severity="medium",
        effort="low",
        created_at=past_date,
    )
    
    age = item.calculate_age()
    assert age == 10
    assert item.age_days == 10


def test_debt_item_priority_calculation():
    """Test priority score calculation."""
    item = DebtItem(
        id="test-1",
        category=DebtCategory.SECURITY,
        title="Critical Issue",
        description="Test",
        file="test.py",
        severity="critical",
        effort="low",
        created_at=datetime.now() - timedelta(days=30),
        auto_fixable=True,
    )
    
    priority = item.calculate_priority()
    
    # High severity + old + easy + auto-fixable = high priority
    assert priority > 70
    assert item.priority_score > 70


def test_debt_item_serialization():
    """Test to_dict and from_dict."""
    item = DebtItem(
        id="test-1",
        category=DebtCategory.TESTING,
        title="Test Issue",
        description="Description",
        file="test.py",
        severity="low",
        effort="high",
        created_at=datetime.now(),
        line=42,
        suggested_fix="Fix suggestion",
        auto_fixable=False,
    )
    
    # Serialize
    data = item.to_dict()
    assert data["id"] == "test-1"
    assert data["category"] == "testing"
    assert data["line"] == 42
    
    # Deserialize
    restored = DebtItem.from_dict(data)
    assert restored.id == item.id
    assert restored.category == item.category
    assert restored.line == item.line


def test_tracker_add_item(tracker):
    """Test adding debt items."""
    item = DebtItem(
        id="test-1",
        category=DebtCategory.CODE_QUALITY,
        title="Test",
        description="Test",
        file="test.py",
        severity="medium",
        effort="low",
        created_at=datetime.now(),
    )
    
    tracker.add_item(item)
    
    assert "test-1" in tracker.debt_items
    assert tracker.debt_items["test-1"].id == "test-1"


def test_tracker_resolve_item(tracker):
    """Test resolving debt items."""
    item = DebtItem(
        id="test-1",
        category=DebtCategory.PERFORMANCE,
        title="Test",
        description="Test",
        file="test.py",
        severity="high",
        effort="medium",
        created_at=datetime.now(),
    )
    
    tracker.add_item(item)
    tracker.resolve_item("test-1")
    
    assert tracker.debt_items["test-1"].resolved_at is not None


def test_tracker_get_active_items(tracker):
    """Test getting active items."""
    # Add resolved item
    item1 = DebtItem(
        id="test-1",
        category=DebtCategory.SECURITY,
        title="Resolved",
        description="Test",
        file="test.py",
        severity="high",
        effort="low",
        created_at=datetime.now(),
        resolved_at=datetime.now(),
    )
    
    # Add active item
    item2 = DebtItem(
        id="test-2",
        category=DebtCategory.CODE_QUALITY,
        title="Active",
        description="Test",
        file="test.py",
        severity="medium",
        effort="medium",
        created_at=datetime.now(),
    )
    
    tracker.add_item(item1)
    tracker.add_item(item2)
    
    active = tracker.get_active_items()
    
    assert len(active) == 1
    assert active[0].id == "test-2"


def test_tracker_get_by_priority(tracker):
    """Test getting items by priority."""
    # Add items with different priorities
    items = [
        DebtItem(
            id=f"test-{i}",
            category=DebtCategory.CODE_QUALITY,
            title=f"Issue {i}",
            description="Test",
            file="test.py",
            severity=["low", "medium", "high", "critical"][i % 4],
            effort="medium",
            created_at=datetime.now() - timedelta(days=i * 10),
        )
        for i in range(5)
    ]
    
    for item in items:
        tracker.add_item(item)
    
    priority_items = tracker.get_by_priority(limit=3)
    
    assert len(priority_items) == 3
    # Should be sorted by priority
    for i in range(len(priority_items) - 1):
        assert priority_items[i].priority_score >= priority_items[i + 1].priority_score


def test_tracker_get_by_category(tracker):
    """Test getting items by category."""
    categories = [
        DebtCategory.SECURITY,
        DebtCategory.PERFORMANCE,
        DebtCategory.SECURITY,
    ]
    
    for i, cat in enumerate(categories):
        item = DebtItem(
            id=f"test-{i}",
            category=cat,
            title=f"Issue {i}",
            description="Test",
            file="test.py",
            severity="medium",
            effort="low",
            created_at=datetime.now(),
        )
        tracker.add_item(item)
    
    security_items = tracker.get_by_category(DebtCategory.SECURITY)
    
    assert len(security_items) == 2
    assert all(item.category == DebtCategory.SECURITY for item in security_items)


def test_tracker_get_old_items(tracker):
    """Test getting old items."""
    # Add old item
    old_item = DebtItem(
        id="test-old",
        category=DebtCategory.CODE_QUALITY,
        title="Old Issue",
        description="Test",
        file="test.py",
        severity="medium",
        effort="low",
        created_at=datetime.now() - timedelta(days=60),
    )
    
    # Add new item
    new_item = DebtItem(
        id="test-new",
        category=DebtCategory.PERFORMANCE,
        title="New Issue",
        description="Test",
        file="test.py",
        severity="high",
        effort="medium",
        created_at=datetime.now(),
    )
    
    tracker.add_item(old_item)
    tracker.add_item(new_item)
    
    old_items = tracker.get_old_items(max_age_days=30)
    
    assert len(old_items) == 1
    assert old_items[0].id == "test-old"


def test_tracker_get_auto_fixable(tracker):
    """Test getting auto-fixable items."""
    items = [
        DebtItem(
            id="test-1",
            category=DebtCategory.CODE_QUALITY,
            title="Auto-fixable",
            description="Test",
            file="test.py",
            severity="low",
            effort="low",
            created_at=datetime.now(),
            auto_fixable=True,
        ),
        DebtItem(
            id="test-2",
            category=DebtCategory.ARCHITECTURE,
            title="Manual fix",
            description="Test",
            file="test.py",
            severity="high",
            effort="high",
            created_at=datetime.now(),
            auto_fixable=False,
        ),
    ]
    
    for item in items:
        tracker.add_item(item)
    
    auto_fixable = tracker.get_auto_fixable()
    
    assert len(auto_fixable) == 1
    assert auto_fixable[0].id == "test-1"


def test_tracker_statistics(tracker):
    """Test getting statistics."""
    # Add various items
    items = [
        DebtItem(
            id="test-1",
            category=DebtCategory.SECURITY,
            title="Critical Security",
            description="Test",
            file="test.py",
            severity="critical",
            effort="low",
            created_at=datetime.now() - timedelta(days=50),
            auto_fixable=True,
        ),
        DebtItem(
            id="test-2",
            category=DebtCategory.PERFORMANCE,
            title="Performance Issue",
            description="Test",
            file="test.py",
            severity="high",
            effort="medium",
            created_at=datetime.now(),
            auto_fixable=False,
        ),
        DebtItem(
            id="test-3",
            category=DebtCategory.CODE_QUALITY,
            title="Resolved Issue",
            description="Test",
            file="test.py",
            severity="medium",
            effort="low",
            created_at=datetime.now(),
            resolved_at=datetime.now(),
        ),
    ]
    
    for item in items:
        tracker.add_item(item)
    
    stats = tracker.get_statistics()
    
    assert stats["total_active"] == 2
    assert stats["total_resolved"] == 1
    assert stats["auto_fixable"] == 1
    assert stats["by_severity"]["critical"] == 1
    assert stats["by_severity"]["high"] == 1
    assert stats["old_items_30d"] >= 1


def test_tracker_generate_report(tracker):
    """Test generating a report."""
    item = DebtItem(
        id="test-1",
        category=DebtCategory.SECURITY,
        title="Test Issue",
        description="Test description",
        file="test.py",
        severity="critical",
        effort="low",
        created_at=datetime.now(),
        auto_fixable=True,
        suggested_fix="Use environment variables",
    )
    
    tracker.add_item(item)
    report = tracker.generate_report()
    
    assert "Technical Debt Report" in report
    assert "Active Items" in report
    assert "Test Issue" in report
    assert "critical" in report.lower()


def test_tracker_persistence(temp_project):
    """Test loading and saving debt items."""
    # Create tracker and add item
    tracker1 = TechnicalDebtTracker(temp_project)
    item = DebtItem(
        id="test-persist",
        category=DebtCategory.DOCUMENTATION,
        title="Persistence Test",
        description="Test",
        file="test.py",
        severity="low",
        effort="medium",
        created_at=datetime.now(),
    )
    tracker1.add_item(item)
    
    # Create new tracker (should load from file)
    tracker2 = TechnicalDebtTracker(temp_project)
    
    assert "test-persist" in tracker2.debt_items
    assert tracker2.debt_items["test-persist"].title == "Persistence Test"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
