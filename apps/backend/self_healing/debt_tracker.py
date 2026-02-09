"""
Technical Debt Tracker
======================

Tracks and prioritizes technical debt items.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

try:
    from debug import debug, debug_section
except ImportError:
    def debug(module: str, message: str, **kwargs): pass
    def debug_section(module: str, message: str): pass


class DebtCategory(str, Enum):
    """Categories of technical debt."""
    
    CODE_QUALITY = "code_quality"
    PERFORMANCE = "performance"
    SECURITY = "security"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    ARCHITECTURE = "architecture"
    DEPENDENCIES = "dependencies"


@dataclass
class DebtItem:
    """Represents a single technical debt item."""
    
    id: str
    category: DebtCategory
    title: str
    description: str
    file: str
    severity: str  # critical, high, medium, low
    effort: str  # low, medium, high
    created_at: datetime
    resolved_at: datetime | None = None
    age_days: int = 0
    priority_score: float = 0.0
    
    # Context
    line: int | None = None
    code_snippet: str | None = None
    
    # Resolution
    suggested_fix: str | None = None
    auto_fixable: bool = False
    
    def calculate_age(self) -> int:
        """Calculate age in days."""
        if self.resolved_at:
            return 0
        delta = datetime.now() - self.created_at
        self.age_days = delta.days
        return self.age_days
    
    def calculate_priority(self) -> float:
        """Calculate priority score (0-100)."""
        # Base severity score
        severity_scores = {
            "critical": 40,
            "high": 30,
            "medium": 20,
            "low": 10,
        }
        score = severity_scores.get(self.severity, 10)
        
        # Add age factor (older = higher priority)
        age_factor = min(30, self.calculate_age() / 2)
        score += age_factor
        
        # Add effort factor (easier = higher priority)
        effort_bonus = {
            "low": 20,
            "medium": 10,
            "high": 0,
        }
        score += effort_bonus.get(self.effort, 0)
        
        # Auto-fixable items get bonus
        if self.auto_fixable:
            score += 10
        
        self.priority_score = min(100, score)
        return self.priority_score
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "category": self.category.value,
            "title": self.title,
            "description": self.description,
            "file": self.file,
            "severity": self.severity,
            "effort": self.effort,
            "created_at": self.created_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "age_days": self.age_days,
            "priority_score": self.priority_score,
            "line": self.line,
            "code_snippet": self.code_snippet,
            "suggested_fix": self.suggested_fix,
            "auto_fixable": self.auto_fixable,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DebtItem:
        """Create from dictionary."""
        return cls(
            id=data["id"],
            category=DebtCategory(data["category"]),
            title=data["title"],
            description=data["description"],
            file=data["file"],
            severity=data["severity"],
            effort=data["effort"],
            created_at=datetime.fromisoformat(data["created_at"]),
            resolved_at=datetime.fromisoformat(data["resolved_at"]) if data.get("resolved_at") else None,
            age_days=data.get("age_days", 0),
            priority_score=data.get("priority_score", 0.0),
            line=data.get("line"),
            code_snippet=data.get("code_snippet"),
            suggested_fix=data.get("suggested_fix"),
            auto_fixable=data.get("auto_fixable", False),
        )


class TechnicalDebtTracker:
    """Tracks and manages technical debt."""
    
    def __init__(self, project_dir: str | Path):
        self.project_dir = Path(project_dir)
        self.debt_file = self.project_dir / ".auto-claude" / "technical-debt.json"
        self.debt_items: dict[str, DebtItem] = {}
        self._load()
    
    def _load(self) -> None:
        """Load debt items from file."""
        if not self.debt_file.exists():
            return
        
        try:
            data = json.loads(self.debt_file.read_text(encoding="utf-8"))
            self.debt_items = {
                item_id: DebtItem.from_dict(item_data)
                for item_id, item_data in data.items()
            }
        except Exception as e:
            debug("self_healing", f"Failed to load debt items: {e}")
    
    def _save(self) -> None:
        """Save debt items to file."""
        self.debt_file.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            item_id: item.to_dict()
            for item_id, item in self.debt_items.items()
        }
        
        self.debt_file.write_text(
            json.dumps(data, indent=2),
            encoding="utf-8",
        )
    
    def add_item(self, item: DebtItem) -> None:
        """Add a debt item."""
        item.calculate_age()
        item.calculate_priority()
        self.debt_items[item.id] = item
        self._save()
    
    def resolve_item(self, item_id: str) -> None:
        """Mark an item as resolved."""
        if item_id in self.debt_items:
            self.debt_items[item_id].resolved_at = datetime.now()
            self._save()
    
    def get_active_items(self) -> list[DebtItem]:
        """Get all unresolved debt items."""
        return [
            item for item in self.debt_items.values()
            if item.resolved_at is None
        ]
    
    def get_by_priority(self, limit: int | None = None) -> list[DebtItem]:
        """Get items sorted by priority."""
        items = self.get_active_items()
        
        # Update priorities
        for item in items:
            item.calculate_age()
            item.calculate_priority()
        
        # Sort by priority (highest first)
        items.sort(key=lambda x: x.priority_score, reverse=True)
        
        if limit:
            items = items[:limit]
        
        return items
    
    def get_by_category(self, category: DebtCategory) -> list[DebtItem]:
        """Get items by category."""
        return [
            item for item in self.get_active_items()
            if item.category == category
        ]
    
    def get_old_items(self, max_age_days: int = 30) -> list[DebtItem]:
        """Get items older than threshold."""
        return [
            item for item in self.get_active_items()
            if item.calculate_age() > max_age_days
        ]
    
    def get_auto_fixable(self) -> list[DebtItem]:
        """Get items that can be auto-fixed."""
        return [
            item for item in self.get_active_items()
            if item.auto_fixable
        ]
    
    def get_statistics(self) -> dict[str, Any]:
        """Get debt statistics."""
        active = self.get_active_items()
        resolved = [item for item in self.debt_items.values() if item.resolved_at]
        
        # By severity
        by_severity = {
            "critical": len([i for i in active if i.severity == "critical"]),
            "high": len([i for i in active if i.severity == "high"]),
            "medium": len([i for i in active if i.severity == "medium"]),
            "low": len([i for i in active if i.severity == "low"]),
        }
        
        # By category
        by_category = {}
        for cat in DebtCategory:
            by_category[cat.value] = len(self.get_by_category(cat))
        
        # Age distribution
        old_items = len(self.get_old_items(30))
        very_old_items = len(self.get_old_items(90))
        
        return {
            "total_active": len(active),
            "total_resolved": len(resolved),
            "auto_fixable": len(self.get_auto_fixable()),
            "by_severity": by_severity,
            "by_category": by_category,
            "old_items_30d": old_items,
            "old_items_90d": very_old_items,
        }
    
    def generate_report(self) -> str:
        """Generate a text report of technical debt."""
        stats = self.get_statistics()
        items = self.get_by_priority(10)
        
        report = ["# Technical Debt Report", ""]
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Summary
        report.append("## Summary")
        report.append(f"- Active Items: {stats['total_active']}")
        report.append(f"- Resolved Items: {stats['total_resolved']}")
        report.append(f"- Auto-fixable: {stats['auto_fixable']}")
        report.append(f"- Items >30 days old: {stats['old_items_30d']}")
        report.append(f"- Items >90 days old: {stats['old_items_90d']}")
        report.append("")
        
        # By severity
        report.append("## By Severity")
        for severity, count in stats["by_severity"].items():
            report.append(f"- {severity.capitalize()}: {count}")
        report.append("")
        
        # Top priority items
        report.append("## Top Priority Items")
        for i, item in enumerate(items, 1):
            report.append(f"\n### {i}. {item.title}")
            report.append(f"- **Priority**: {item.priority_score:.1f}/100")
            report.append(f"- **Severity**: {item.severity}")
            report.append(f"- **Category**: {item.category.value}")
            report.append(f"- **File**: {item.file}")
            report.append(f"- **Age**: {item.age_days} days")
            report.append(f"- **Effort**: {item.effort}")
            report.append(f"- **Auto-fixable**: {'Yes' if item.auto_fixable else 'No'}")
            if item.suggested_fix:
                report.append(f"- **Suggested Fix**: {item.suggested_fix}")
        
        return "\n".join(report)
