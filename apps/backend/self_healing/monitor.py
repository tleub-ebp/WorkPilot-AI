﻿"""
Self-Healing Monitor
====================

Main orchestrator for a self-healing system.
Coordinates health checks, debt tracking, refactoring, and alerts.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from debug import debug, debug_error, debug_section, debug_success
except ImportError:
    def debug(module: str, message: str, **kwargs): pass
    def debug_section(module: str, message: str): pass
    def debug_success(module: str, message: str, **kwargs): pass
    def debug_error(module: str, message: str, **kwargs): pass

from .alert_manager import Alert, AlertLevel, AlertManager
from .config import HealingConfig, HealingMode
from .debt_tracker import DebtCategory, DebtItem, TechnicalDebtTracker
from .health_checker import HealthChecker, HealthReport
from .refactoring_engine import RefactoringEngine


class SelfHealingMonitor:
    """
    Main self-healing monitor.
    
    Orchestrates:
    - Health checks
    - Technical debt tracking
    - Automated refactoring
    - Alert management
    """
    
    def __init__(
        self,
        project_dir: str | Path,
        config: HealingConfig | None = None,
    ):
        self.project_dir = Path(project_dir)
        self.config = config or HealingConfig()
        
        # Initialize components
        self.health_checker = HealthChecker(project_dir)
        self.debt_tracker = TechnicalDebtTracker(project_dir)
        self.refactoring_engine = RefactoringEngine(
            project_dir,
            model=self.config.model,
        )
        self.alert_manager = AlertManager(project_dir)
        
        # State
        self.last_report: HealthReport | None = None
        self.history_file = self.project_dir / ".auto-claude" / "health-history.json"
        self.history: list[dict[str, Any]] = []
        
        self._load_history()
    
    def _load_history(self) -> None:
        """Load health check history."""
        if self.history_file.exists():
            try:
                self.history = json.loads(
                    self.history_file.read_text(encoding="utf-8")
                )
            except Exception as e:
                debug_error(f"Failed to load history: {e}")
    
    def _save_history(self) -> None:
        """Save health check history."""
        try:
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            self.history_file.write_text(
                json.dumps(self.history, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            debug_error(f"Failed to save history: {e}")
    
    async def run_health_check(self) -> HealthReport:
        """Run a complete health check."""
        debug_section("self_healing", "🧬 Self-Healing Health Check")
        
        # Run health check
        report = await self.health_checker.check_health()
        
        # Compare with previous
        if self.last_report:
            report.score_change = report.overall_score - self.last_report.overall_score
            report.is_degrading = report.score_change < -self.config.alert_threshold_change
        
        # Save to history
        self.history.append(report.to_dict())
        self._save_history()
        
        # Update state
        self.last_report = report
        
        # Track as technical debt
        if self.config.track_debt:
            await self._update_technical_debt(report)
        
        # Send alerts if needed
        if self.config.alert_on_degradation:
            await self._check_alerts(report)
        
        return report
    
    async def _update_technical_debt(self, report: HealthReport) -> None:
        """Update technical debt from health report."""
        debug("self_healing", "Updating technical debt items")
        
        for issue in report.all_issues:
            # Create debt item ID
            debt_id = f"{issue.type.value}_{issue.file}_{issue.line or 0}"
            
            # Map issue to debt category
            category_map = {
                "code_smell": DebtCategory.CODE_QUALITY,
                "performance": DebtCategory.PERFORMANCE,
                "security": DebtCategory.SECURITY,
                "testing": DebtCategory.TESTING,
                "documentation": DebtCategory.DOCUMENTATION,
                "complexity": DebtCategory.CODE_QUALITY,
            }
            
            category = category_map.get(
                issue.type.value,
                DebtCategory.CODE_QUALITY,
            )
            
            # Check if already exists
            if debt_id not in self.debt_tracker.debt_items:
                debt_item = DebtItem(
                    id=debt_id,
                    category=category,
                    title=issue.title,
                    description=issue.description,
                    file=issue.file,
                    severity=issue.severity,
                    effort=issue.effort,
                    created_at=datetime.now(),
                    line=issue.line,
                    suggested_fix=issue.suggestion,
                    auto_fixable=issue.severity in ["low", "medium"],
                )
                
                self.debt_tracker.add_item(debt_item)
    
    async def _check_alerts(self, report: HealthReport) -> None:
        """Check if alerts should be sent."""
        # Critical health score
        if report.overall_score < self.config.critical_threshold:
            alert = Alert(
                level=AlertLevel.CRITICAL,
                title="Critical Health Score",
                message=f"Codebase health has dropped to {report.overall_score:.1f}/100",
                health_score=report.overall_score,
                score_change=report.score_change,
                issue_count=len(report.all_issues),
                actions_suggested=[
                    "Review critical issues immediately",
                    "Run auto-healing to fix issues",
                    "Consider manual intervention",
                ],
            )
            await self.alert_manager.send_alert(alert, self.config.alert_channels)
        
        # Significant degradation
        elif report.is_degrading:
            alert = Alert(
                level=AlertLevel.WARNING,
                title="Health Score Degradation",
                message=f"Health score decreased by {abs(report.score_change):.1f} points",
                health_score=report.overall_score,
                score_change=report.score_change,
                issue_count=len(report.all_issues),
                actions_suggested=[
                    "Review recent changes",
                    "Run health check to identify issues",
                ],
            )
            await self.alert_manager.send_alert(alert, self.config.alert_channels)
        
        # Critical issues found
        critical_issues = report.get_critical_issues()
        if critical_issues and len(critical_issues) > 0:
            alert = Alert(
                level=AlertLevel.CRITICAL,
                title=f"{len(critical_issues)} Critical Issues Found",
                message=f"Found {len(critical_issues)} critical issues requiring immediate attention",
                health_score=report.overall_score,
                issue_count=len(critical_issues),
                actions_suggested=[
                    issue.title for issue in critical_issues[:3]
                ],
            )
            await self.alert_manager.send_alert(alert, self.config.alert_channels)
    
    async def auto_heal(self, max_fixes: int | None = None) -> dict[str, Any]:
        """
        Run automatic healing.
        
        Returns summary of actions taken.
        """
        debug_section("self_healing", "🧬 Running Auto-Heal")
        
        if not self.config.auto_fix_enabled:
            debug("self_healing", "Auto-fix is disabled")
            return {"status": "disabled"}
        
        max_fixes = max_fixes or self.config.max_fixes_per_run
        
        # Get current health
        report = await self.run_health_check()
        
        # Check if healing needed
        if report.overall_score >= self.config.min_health_score:
            debug_success(f"Health score {report.overall_score:.1f} is above threshold")
            return {
                "status": "healthy",
                "score": report.overall_score,
                "message": "No healing needed",
            }
        
        # Get priority issues
        issues_to_fix = []
        for issue in report.all_issues:
            if any(issue.severity == p.value for p in self.config.priorities):
                issues_to_fix.append(issue)
        
        issues_to_fix = issues_to_fix[:max_fixes]
        
        if not issues_to_fix:
            return {
                "status": "no_fixable_issues",
                "score": report.overall_score,
            }
        
        debug("self_healing", f"Fixing {len(issues_to_fix)} issues")
        
        # Generate refactoring plan
        plan = await self.refactoring_engine.generate_plan(issues_to_fix)
        
        # Apply in different modes
        if self.config.mode == HealingMode.PASSIVE:
            # Just report, don't fix
            return {
                "status": "passive_mode",
                "issues_found": len(issues_to_fix),
                "plan": plan.to_dict(),
            }
        
        elif self.config.mode in [HealingMode.ACTIVE, HealingMode.AGGRESSIVE]:
            # Apply fixes
            branch_name = None
            if self.config.create_branch_per_fix:
                branch_name = f"{self.config.branch_prefix}{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            
            success = await self.refactoring_engine.apply_plan(
                plan,
                create_branch=self.config.create_branch_per_fix,
                branch_name=branch_name,
            )
            
            # Create PR if configured
            pr_url = None
            if success and self.config.create_prs_for_fixes and branch_name:
                pr_url = await self.refactoring_engine.create_pr_for_plan(
                    plan,
                    branch_name,
                )
            
            # Verify improvement
            new_report = await self.run_health_check()
            improvement = new_report.overall_score - report.overall_score
            
            return {
                "status": "completed",
                "success": success,
                "issues_fixed": len(issues_to_fix),
                "actions_applied": len([a for a in plan.actions if a.success]),
                "score_before": report.overall_score,
                "score_after": new_report.overall_score,
                "improvement": improvement,
                "branch": branch_name,
                "pr_url": pr_url,
            }
        
        return {"status": "unknown"}
    
    async def generate_health_report(self) -> str:
        """Generate a comprehensive health report."""
        report = await self.run_health_check()
        debt_report = self.debt_tracker.generate_report()
        
        output = [
            "# 🧬 Self-Healing Codebase Report",
            f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "\n## Overall Health",
            f"- **Score**: {report.overall_score:.1f}/100",
            f"- **Status**: {report.status.value.upper()}",
            f"- **Total Issues**: {len(report.all_issues)}",
            f"- **Critical Issues**: {len(report.get_critical_issues())}",
        ]
        
        if report.score_change is not None:
            change_emoji = "📈" if report.score_change >= 0 else "📉"
            output.append(f"- **Change**: {change_emoji} {report.score_change:+.1f}")
        
        output.extend([
            "\n## Scores by Category",
            f"- Quality: {report.quality_score.score:.1f}/100",
            f"- Performance: {report.performance_score.score:.1f}/100",
            f"- Security: {report.security_score.score:.1f}/100",
            f"- Maintainability: {report.maintainability_score.score:.1f}/100",
            f"- Testing: {report.testing_score.score:.1f}/100",
            f"- Documentation: {report.documentation_score.score:.1f}/100",
            "\n---\n",
            debt_report,
        ])
        
        return "\n".join(output)
    
    def get_statistics(self) -> dict[str, Any]:
        """Get comprehensive statistics."""
        debt_stats = self.debt_tracker.get_statistics()
        
        stats = {
            "current_health": self.last_report.to_dict() if self.last_report else None,
            "technical_debt": debt_stats,
            "history_count": len(self.history),
            "alert_count": len(self.alert_manager.alert_history),
            "critical_alerts": len(self.alert_manager.get_critical_alerts()),
        }
        
        return stats
