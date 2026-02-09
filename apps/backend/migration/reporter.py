"""
Migration Report Generator: Creates comprehensive migration reports.
"""

from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path

from .models import MigrationContext, MigrationPlan, ValidationReport


class MigrationReporter:
    """Generates migration reports."""

    def __init__(self, context: MigrationContext):
        self.context = context
        self.project_dir = Path(context.project_dir)

    def generate_report(self) -> str:
        """Generate comprehensive migration report in Markdown."""
        sections = [
            self._header(),
            self._summary(),
            self._source_target(),
            self._risk_assessment(),
            self._migration_plan(),
            self._transformations(),
            self._validation_results(),
            self._timeline(),
            self._recommendations(),
        ]
        return "\n\n".join(filter(None, sections))

    def generate_html_report(self) -> str:
        """Generate HTML migration report."""
        markdown = self.generate_report()
        # Simple HTML wrapper - would use markdown2html library in production
        html = f"""
<html>
<head>
    <title>Migration Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        h2 {{ color: #666; border-bottom: 1px solid #ccc; }}
        .summary {{ background: #f0f0f0; padding: 10px; border-radius: 5px; }}
        .success {{ color: green; }}
        .warning {{ color: orange; }}
        .error {{ color: red; }}
    </style>
</head>
<body>
{markdown}
</body>
</html>
"""
        return html

    def save_report(self, output_path: str = None) -> str:
        """Save report to file."""
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = str(
                self.project_dir / f".auto-claude/migration/report_{timestamp}.md"
            )

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(self.generate_report())
        return output_path

    def _header(self) -> str:
        """Generate report header."""
        return f"""# Migration Report

**Migration ID:** {self.context.migration_id}
**Date:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Status:** {self.context.state.value.upper()}
"""

    def _summary(self) -> str:
        """Generate summary section."""
        if not self.context.plan:
            return ""

        return f"""## Summary

- **Source Stack:** {self.context.source_stack.framework} ({self.context.source_stack.language})
- **Target Stack:** {self.context.target_stack.framework} ({self.context.target_stack.language})
- **Total Steps:** {self.context.plan.total_steps}
- **Total Phases:** {len(self.context.plan.phases)}
- **Risk Level:** {self.context.plan.risk_level.value.upper()}
- **Estimated Effort:** {self.context.plan.estimated_effort}
- **Estimated Duration:** {self.context.plan.estimated_duration_hours:.1f} hours
"""

    def _source_target(self) -> str:
        """Generate source/target stack details."""
        source = self.context.source_stack
        target = self.context.target_stack

        return f"""## Source & Target Stacks

### Source Stack
- **Framework:** {source.framework} (v{source.version})
- **Language:** {source.language}
- **Database:** {source.database or 'N/A'}
- **Package Manager:** {source.package_manager}
- **Dependencies:** {len(source.dependencies)}

### Target Stack
- **Framework:** {target.framework} (v{target.version})
- **Language:** {target.language}
- **Database:** {target.database or 'N/A'}
- **Package Manager:** {target.package_manager}
"""

    def _risk_assessment(self) -> str:
        """Generate risk assessment section."""
        if not self.context.plan:
            return ""

        return f"""## Risk Assessment

- **Overall Risk Level:** {self.context.plan.risk_level.value.upper()}
- **Breaking Changes:** {'Yes' if any(p.risk_level.value in ['high', 'critical'] for p in self.context.plan.phases) else 'No'}
- **Data Preservation:** Required
- **Rollback Available:** {'Yes' if self.context.rollback_available else 'No'}
- **Approval Required:** {'Yes' if self.context.plan.approvals_required else 'No'}
"""

    def _migration_plan(self) -> str:
        """Generate migration plan section."""
        if not self.context.plan:
            return ""

        plan_section = "## Migration Plan\n\n"
        for phase in self.context.plan.phases:
            plan_section += f"### {phase.name} ({phase.id})\n\n"
            plan_section += f"**Description:** {phase.description}\n"
            plan_section += f"**Effort:** {phase.estimated_effort}\n"
            plan_section += f"**Risk:** {phase.risk_level.value}\n"
            plan_section += f"**Steps:** {len(phase.steps)}\n\n"

            for step in phase.steps:
                plan_section += f"- **{step.title}** ({step.category})\n"
                plan_section += f"  - {step.description}\n"
                plan_section += f"  - Files affected: {len(step.files_affected)}\n"
                if step.rollback_procedure:
                    plan_section += f"  - Rollback: {step.rollback_procedure}\n"

            plan_section += "\n"

        return plan_section

    def _transformations(self) -> str:
        """Generate transformations section."""
        if not self.context.transformations:
            return "## Transformations\n\nNo transformations applied.\n"

        trans_section = f"## Transformations\n\n**Total:** {len(self.context.transformations)}\n\n"
        
        for trans in self.context.transformations[:10]:  # Show first 10
            trans_section += f"### {trans.file_path}\n"
            trans_section += f"- **Type:** {trans.transformation_type}\n"
            trans_section += f"- **Changes:** {trans.changes_count} lines\n"
            trans_section += f"- **Confidence:** {trans.confidence:.0%}\n"
            if trans.errors:
                trans_section += f"- **Errors:** {', '.join(trans.errors)}\n"
            trans_section += "\n"

        if len(self.context.transformations) > 10:
            trans_section += f"\n... and {len(self.context.transformations) - 10} more transformations\n"

        return trans_section

    def _validation_results(self) -> str:
        """Generate validation results section."""
        if not self.context.test_results:
            return ""

        test_info = self.context.test_results.get("tests", {})
        build_info = self.context.test_results.get("build", {})
        lint_info = self.context.test_results.get("lint", {})

        return f"""## Validation Results

### Tests
- **Status:** {'✓ Passed' if test_info.get('success') else '✗ Failed'}
- **Total:** {test_info.get('total', 'N/A')}
- **Passed:** {test_info.get('passed', 'N/A')}
- **Failed:** {test_info.get('failed', 'N/A')}

### Build
- **Status:** {'✓ Success' if build_info.get('success') else '✗ Failed'}

### Linting
- **Status:** {'✓ Passed' if lint_info.get('success') else '⚠ Issues'}
"""

    def _timeline(self) -> str:
        """Generate timeline section."""
        timeline = "## Timeline\n\n"
        if self.context.started_at:
            timeline += f"- **Started:** {self.context.started_at.isoformat()}\n"
        if self.context.completed_at:
            timeline += f"- **Completed:** {self.context.completed_at.isoformat()}\n"
            duration = (
                self.context.completed_at - self.context.started_at
            ).total_seconds() / 3600
            timeline += f"- **Duration:** {duration:.2f} hours\n"
        timeline += f"- **Status:** {self.context.state.value}\n"
        timeline += f"- **Checkpoints:** {len(self.context.checkpoints)}\n"
        return timeline

    def _recommendations(self) -> str:
        """Generate recommendations section."""
        recs = "## Recommendations\n\n"

        if self.context.plan:
            if self.context.plan.risk_level.value == "critical":
                recs += "- **Review manually:** This is a high-risk migration, review changes carefully\n"
            
            if any(p.risk_level.value == "high" for p in self.context.plan.phases):
                recs += "- **Stage the migration:** Consider applying changes in smaller batches\n"

        recs += "- **Test thoroughly:** Run comprehensive test suite post-migration\n"
        recs += "- **Backup production:** Always backup before deploying migrations\n"
        recs += "- **Monitor closely:** Watch logs closely for any issues\n"

        return recs
