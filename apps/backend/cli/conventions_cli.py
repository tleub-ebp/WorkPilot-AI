"""
CLI Commands for Convention Management

This module provides CLI commands for managing project conventions,
learning loop, and steering files.
"""

import json
from pathlib import Path

import click

from ..core.convention_engine import create_convention_engine
from ..core.convention_integration import (
    get_convention_integration,
    initialize_convention_system,
)
from ..core.learning_loop import create_learning_loop


@click.group()
def conventions():
    """Project convention management commands."""
    pass


@conventions.command()
@click.option("--project-root", default=".", help="Project root directory")
@click.option("--files", "-f", multiple=True, help="Specific files to validate")
def validate(project_root: str, files: list[str]):
    """Validate project conventions."""
    click.echo("🔍 Validating project conventions...")

    integration = get_convention_integration(project_root)
    file_list = list(files) if files else None

    results = integration.validate_project_conventions(file_list)

    click.echo("\n📊 Validation Results:")
    click.echo(f"Files validated: {results['files_validated']}")
    click.echo(f"Total violations: {results['total_violations']}")

    if results["total_violations"] > 0:
        click.echo("\n🚨 Violations by severity:")
        severity_counts = results["summary"]["severity_counts"]
        for severity, count in severity_counts.items():
            if count > 0:
                emoji = {"error": "❌", "warning": "⚠️", "info": "ℹ️"}[severity]
                click.echo(f"  {emoji} {severity}: {count}")

        click.echo("\n📋 Most violated rules:")
        for rule, count in results["summary"]["most_violated_rules"]:
            click.echo(f"  • {rule}: {count} violations")

        if click.confirm("\n🔧 Show detailed violations?"):
            for file_path, violations in results["validation_results"].items():
                click.echo(f"\n📁 {file_path}:")
                for violation in violations:
                    emoji = {"error": "❌", "warning": "⚠️", "info": "ℹ️"}[
                        violation.severity
                    ]
                    click.echo(f"  {emoji} {violation.rule_type}: {violation.message}")
                    if violation.suggestion:
                        click.echo(f"    💡 {violation.suggestion}")
    else:
        click.echo("✅ No convention violations found!")


@conventions.command()
@click.option("--project-root", default=".", help="Project root directory")
def status(project_root: str):
    """Show convention system status."""
    click.echo("📈 Convention System Status")
    click.echo("=" * 40)

    integration = get_convention_integration(project_root)
    system_status = integration.get_system_status()

    click.echo(f"🤖 Registered agents: {system_status['registered_agents']}")
    click.echo(f"🔄 Active builds: {system_status['active_builds']}")
    click.echo(f"📋 Convention rules: {system_status['convention_rules']}")
    click.echo(f"⏳ Pending evolutions: {system_status['pending_evolutions']}")

    # Learning summary
    learning = system_status["learning_summary"]
    click.echo("\n📚 Learning Loop Summary:")
    click.echo(f"  Total builds: {learning['total_builds']}")
    click.echo(f"  Recent builds (30d): {learning['recent_builds']}")
    click.echo(f"  Recent success rate: {learning['recent_success_rate']:.1%}")
    click.echo(f"  Patterns discovered: {learning['patterns_discovered']}")
    click.echo(f"  High confidence patterns: {learning['high_confidence_patterns']}")

    if learning["pattern_types"]:
        click.echo("\n🎯 Pattern Types:")
        for ptype, count in learning["pattern_types"].items():
            click.echo(f"  • {ptype}: {count}")


@conventions.command()
@click.option("--project-root", default=".", help="Project root directory")
@click.option(
    "--auto-apply", is_flag=True, help="Auto-apply high confidence evolutions"
)
def evolutions(project_root: str, auto_apply: bool):
    """Manage convention evolutions."""
    click.echo("🧬 Convention Evolutions")
    click.echo("=" * 30)

    integration = get_convention_integration(project_root)
    learning_loop = integration.learning_loop

    pending_evolutions = learning_loop.get_pending_evolutions()

    if not pending_evolutions:
        click.echo("✅ No pending evolutions")
        return

    click.echo(f"⏳ {len(pending_evolutions)} pending evolutions:")

    for i, evolution in enumerate(pending_evolutions, 1):
        click.echo(f"\n{i}. 📝 {evolution.target_file} - {evolution.section}")
        click.echo(f"   🎯 Type: {evolution.evolution_type}")
        click.echo(f"   📊 Confidence: {evolution.confidence_score:.1%}")
        click.echo(f"   💡 Rationale: {evolution.rationale}")
        click.echo(f"   📈 Impact: {evolution.impact_assessment}")

        if auto_apply and evolution.confidence_score >= 0.9:
            if learning_loop.apply_evolution(evolution.evolution_id):
                click.echo("   ✅ Auto-applied!")
            else:
                click.echo("   ❌ Failed to apply")
        elif not auto_apply:
            if click.confirm("   🔄 Apply this evolution?"):
                if learning_loop.apply_evolution(evolution.evolution_id):
                    click.echo("   ✅ Applied!")
                else:
                    click.echo("   ❌ Failed to apply")
            elif click.confirm("   🗑️  Reject this evolution?"):
                learning_loop.reject_evolution(evolution.evolution_id)
                click.echo("   🗑️  Rejected")


@conventions.command()
@click.option("--project-root", default=".", help="Project root directory")
def init(project_root: str):
    """Initialize convention system for project."""
    click.echo("🚀 Initializing convention system...")

    integration = initialize_convention_system(project_root)

    # Create steering files if they don't exist
    workpilot_dir = Path(project_root) / ".workpilot"

    steering_files = {
        "conventions.md": """# Project Conventions

This file defines project-specific conventions and patterns that all AI agents must follow.

## Code Style Conventions

### Python Backend
- Use Ruff for linting and formatting
- Follow PEP 8 with 4-space indentation
- Type hints required for all public functions

### TypeScript Frontend  
- Use Biome for linting and formatting
- Strict TypeScript mode enabled
- Functional components with hooks

*This file is automatically updated by the Learning Loop based on successful build patterns.*""",
        "architecture.md": """# Project Architecture

This file defines the architectural patterns and structural decisions for the project.

## High-Level Architecture

### Monorepo Structure
```
project/
├── apps/
│   ├── backend/          # Python backend
│   └── frontend/         # Frontend UI
├── src/                  # Shared utilities
└── docs/                 # Documentation
```

*This architecture document evolves with the project through the Learning Loop system.*""",
        "patterns.md": """# Project Patterns

This file defines reusable patterns and best practices discovered through project evolution.

## Code Patterns

### Agent Implementation Pattern
```python
# Standard agent structure
class StandardAgent:
    def __init__(self, project_dir, spec_dir):
        self.client = create_client(project_dir, spec_dir)
    
    async def execute(self, task_context):
        # Agent implementation here
        pass
```

*This patterns file is continuously updated by the Learning Loop based on successful project outcomes.*""",
    }

    created_files = []
    for filename, content in steering_files.items():
        file_path = workpilot_dir / filename
        if not file_path.exists():
            file_path.write_text(content, encoding="utf-8")
            created_files.append(filename)
            click.echo(f"✅ Created {filename}")
        else:
            click.echo(f"ℹ️  {filename} already exists")

    if created_files:
        click.echo("\n🎉 Convention system initialized!")
        click.echo(f"📁 Steering files created: {', '.join(created_files)}")
        click.echo(f"📍 Location: {workpilot_dir}")
    else:
        click.echo("\n✅ Convention system already initialized")

    # Show system status
    status = integration.get_system_status()
    click.echo(f"📊 Ready with {status['convention_rules']} built-in rules")


@conventions.command()
@click.option("--project-root", default=".", help="Project root directory")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["json", "table"]),
    default="table",
    help="Output format",
)
def patterns(project_root: str, output: str):
    """Show discovered patterns."""
    click.echo("🎯 Discovered Patterns")
    click.echo("=" * 30)

    learning_loop = create_learning_loop(project_root)
    patterns = learning_loop.patterns

    if not patterns:
        click.echo("🔍 No patterns discovered yet")
        click.echo("💡 Run some builds first to discover patterns")
        return

    if output == "json":
        pattern_data = {pid: pattern.to_dict() for pid, pattern in patterns.items()}
        click.echo(json.dumps(pattern_data, indent=2))
    else:
        # Group by pattern type
        pattern_types = {}
        for pattern in patterns.values():
            if pattern.pattern_type not in pattern_types:
                pattern_types[pattern.pattern_type] = []
            pattern_types[pattern.pattern_type].append(pattern)

        for ptype, patts in pattern_types.items():
            click.echo(f"\n📂 {ptype.title()} Patterns ({len(patts)}):")
            for pattern in sorted(
                patts, key=lambda p: p.confidence_score, reverse=True
            ):
                confidence_emoji = (
                    "🔥"
                    if pattern.confidence_score >= 0.9
                    else "⭐"
                    if pattern.confidence_score >= 0.7
                    else "💡"
                )
                click.echo(f"  {confidence_emoji} {pattern.description}")
                click.echo(
                    f"     📊 Success: {pattern.success_rate:.1%} | 🔄 Frequency: {pattern.frequency} | 🎯 Confidence: {pattern.confidence_score:.1%}"
                )


@conventions.command()
@click.option("--project-root", default=".", help="Project root directory")
@click.argument("file-path", type=click.Path(exists=True))
def check_file(project_root: str, file_path: str):
    """Check a specific file for convention compliance."""
    click.echo(f"🔍 Checking {file_path}...")

    engine = create_convention_engine(project_root)
    violations = engine.validate_file(file_path)

    if violations:
        click.echo(f"\n🚨 {len(violations)} violations found:")
        for violation in violations:
            emoji = {"error": "❌", "warning": "⚠️", "info": "ℹ️"}[violation.severity]
            line_info = f":{violation.line_number}" if violation.line_number else ""
            click.echo(
                f"  {emoji} {violation.rule_type}{line_info}: {violation.message}"
            )
            if violation.suggestion:
                click.echo(f"    💡 {violation.suggestion}")
            if violation.auto_fixable:
                click.echo("    🔧 Auto-fixable")
    else:
        click.echo("✅ No convention violations found!")


@conventions.command()
@click.option("--project-root", default=".", help="Project root directory")
def learn(project_root: str):
    """Trigger learning loop analysis."""
    click.echo("🧠 Running learning loop analysis...")

    learning_loop = create_learning_loop(project_root)
    summary = learning_loop.get_learning_summary()

    click.echo("📊 Learning Summary:")
    click.echo(f"  Total builds analyzed: {summary['total_builds']}")
    click.echo(f"  Recent success rate: {summary['recent_success_rate']:.1%}")
    click.echo(f"  Patterns discovered: {summary['patterns_discovered']}")
    click.echo(f"  Pending evolutions: {summary['pending_evolutions']}")

    if summary["pending_evolutions"] > 0:
        click.echo(
            "\n💡 Run 'conventions evolutions' to review and apply pending changes"
        )


if __name__ == "__main__":
    conventions()
