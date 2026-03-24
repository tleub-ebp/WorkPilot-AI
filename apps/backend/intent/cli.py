#!/usr/bin/env python3
"""
Intent Analysis CLI
===================

Command-line interface for intent recognition, feedback, and recommendations.

Usage:
    python -m intent.cli analyze "Add OAuth2 authentication"
    python -m intent.cli analyze --spec-dir ./auto-claude/specs/001-feature/
    python -m intent.cli feedback --task-id 001 --detected bug_fix --actual new_feature
    python -m intent.cli metrics
    python -m intent.cli recommend --spec-dir ./auto-claude/specs/001-feature/
"""

import argparse
import json
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .learner import IntentLearner
from .models import IntentCategory
from .recognizer import IntentRecognizer
from .recommender import IntentRecommender

console = Console()


def cmd_analyze(args):
    """Analyze intent from task description or spec directory."""
    recognizer = IntentRecognizer()

    if args.spec_dir:
        spec_dir = Path(args.spec_dir)
        if not spec_dir.exists():
            console.print(f"[red]Error: Spec directory not found: {spec_dir}[/red]")
            sys.exit(1)

        console.print(f"[cyan]Analyzing intent from spec directory: {spec_dir}[/cyan]")
        analysis = recognizer.analyze_from_spec_dir(spec_dir)
    else:
        if not args.description:
            console.print(
                "[red]Error: Either --description or --spec-dir required[/red]"
            )
            sys.exit(1)

        console.print(f"[cyan]Analyzing intent: {args.description}[/cyan]\n")
        analysis = recognizer.analyze_intent(args.description)

    # Display results
    _display_intent_analysis(analysis)

    # Save to file if requested
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(analysis.to_dict(), f, indent=2)
        console.print(f"\n[green]✓ Analysis saved to: {output_path}[/green]")


def cmd_feedback(args):
    """Record user feedback on intent detection."""
    learner = IntentLearner()

    try:
        detected = IntentCategory(args.detected)
        actual = IntentCategory(args.actual)
    except ValueError as e:
        console.print(f"[red]Error: Invalid intent category: {e}[/red]")
        console.print("\n[yellow]Valid categories:[/yellow]")
        for cat in IntentCategory:
            console.print(f"  - {cat.value}")
        sys.exit(1)

    learner.record_feedback(
        task_id=args.task_id,
        task_description=args.description or "",
        detected_category=detected,
        detected_confidence=args.confidence,
        actual_category=actual,
        user_notes=args.notes or "",
        project_id=args.project_id or "",
    )

    console.print("[green]✓ Feedback recorded successfully[/green]")

    # Show if this was correct or incorrect
    if detected == actual:
        console.print("[green]Intent was correctly detected! 🎉[/green]")
    else:
        console.print(
            f"[yellow]Intent was misclassified: {detected.value} → {actual.value}[/yellow]"
        )


def cmd_metrics(args):
    """Display intent detection accuracy metrics."""
    learner = IntentLearner()

    metrics = learner.get_accuracy_metrics(args.project_id)

    if metrics["total_feedbacks"] == 0:
        console.print("[yellow]No feedback data available yet.[/yellow]")
        console.print("Record feedback using: [cyan]intent.cli feedback[/cyan]")
        return

    # Overall accuracy
    console.print("\n[bold cyan]Intent Detection Accuracy[/bold cyan]\n")
    console.print(
        f"Total Feedbacks: {metrics['total_feedbacks']}\n"
        f"Overall Accuracy: {metrics['overall_accuracy']:.1%}\n"
        f"Correct Predictions: {metrics['correct_predictions']}"
    )

    # Per-category accuracy
    if metrics["by_category"]:
        console.print("\n[bold]By Category:[/bold]\n")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Category", style="cyan")
        table.add_column("Accuracy", justify="right")
        table.add_column("Correct", justify="right")
        table.add_column("Total", justify="right")

        for category, stats in sorted(
            metrics["by_category"].items(), key=lambda x: x[1]["accuracy"], reverse=True
        ):
            accuracy = stats["accuracy"]
            color = (
                "green" if accuracy >= 0.8 else "yellow" if accuracy >= 0.6 else "red"
            )
            table.add_row(
                category,
                f"[{color}]{accuracy:.1%}[/{color}]",
                str(stats["correct"]),
                str(stats["total"]),
            )

        console.print(table)

    # Common misclassifications
    misclass = learner.get_common_misclassifications(limit=5)
    if misclass:
        console.print("\n[bold]Common Misclassifications:[/bold]\n")

        table = Table(show_header=True, header_style="bold red")
        table.add_column("Detected As", style="yellow")
        table.add_column("Actually Was", style="green")
        table.add_column("Count", justify="right")

        for item in misclass:
            table.add_row(
                item["detected"],
                item["actual"],
                str(item["count"]),
            )

        console.print(table)


def cmd_recommend(args):
    """Generate recommendations for a task."""
    recognizer = IntentRecognizer()
    recommender = IntentRecommender()

    if args.spec_dir:
        spec_dir = Path(args.spec_dir)
        if not spec_dir.exists():
            console.print(f"[red]Error: Spec directory not found: {spec_dir}[/red]")
            sys.exit(1)

        analysis = recognizer.analyze_from_spec_dir(spec_dir)
    else:
        if not args.description:
            console.print(
                "[red]Error: Either --description or --spec-dir required[/red]"
            )
            sys.exit(1)

        analysis = recognizer.analyze_intent(args.description)

    # Generate recommendations
    recommendations = recommender.generate_recommendations(
        analysis, project_id=args.project_id or ""
    )

    # Display
    _display_recommendations(recommendations)


def _display_intent_analysis(analysis):
    """Display intent analysis in a nice format."""
    intent = analysis.primary_intent

    # Confidence color
    conf = intent.confidence_score
    conf_color = "green" if conf >= 0.75 else "yellow" if conf >= 0.5 else "red"

    # Primary intent panel
    content = Text()
    content.append("Category: ", style="bold")
    content.append(f"{intent.category.value}\n", style="cyan")
    content.append("Workflow: ", style="bold")
    content.append(f"{intent.workflow_type.value}\n", style="cyan")
    content.append("Confidence: ", style="bold")
    content.append(f"{conf:.1%}", style=conf_color)
    content.append(f" ({intent.confidence_level.value})\n\n", style=conf_color)
    content.append("Reasoning:\n", style="bold")
    content.append(f"{intent.reasoning}\n", style="white")

    if intent.keywords_found:
        content.append("\nKeywords: ", style="bold")
        content.append(", ".join(intent.keywords_found), style="dim")

    console.print(Panel(content, title="🎯 Primary Intent", border_style="green"))

    # Alternative intents
    if analysis.alternative_intents:
        console.print("\n[bold yellow]Alternative Interpretations:[/bold yellow]\n")

        for i, alt in enumerate(analysis.alternative_intents, 1):
            alt_conf = alt.confidence_score
            alt_color = "yellow" if alt_conf >= 0.5 else "dim"
            console.print(
                f"  {i}. [{alt_color}]{alt.category.value}[/{alt_color}] "
                f"({alt_conf:.1%}) - {alt.reasoning}"
            )

    # Clarification needed?
    if analysis.requires_clarification:
        console.print("\n[bold red]⚠️  Clarification Needed[/bold red]\n")
        for i, question in enumerate(analysis.clarification_questions, 1):
            console.print(f"  {i}. {question}")


def _display_recommendations(recs):
    """Display recommendations in a nice format."""
    # Header
    console.print(
        f"\n[bold cyan]Recommendations for: {recs.task_description[:80]}[/bold cyan]\n"
    )

    # Estimates
    console.print(f"[bold]Estimated Complexity:[/bold] {recs.estimated_complexity}")
    console.print(
        f"[bold]Estimated Duration:[/bold] {recs.estimated_duration_hours[0]:.1f}-{recs.estimated_duration_hours[1]:.1f} hours"
    )

    if recs.required_skills:
        console.print(
            f"[bold]Required Skills:[/bold] {', '.join(recs.required_skills)}"
        )

    if recs.suggested_tests:
        console.print(
            f"[bold]Suggested Tests:[/bold] {', '.join(recs.suggested_tests)}"
        )

    # Recommendations
    if recs.recommendations:
        console.print("\n[bold cyan]Recommendations:[/bold cyan]\n")

        for rec in recs.recommendations:
            # Icon by type
            icons = {
                "warning": "⚠️",
                "tip": "💡",
                "tool": "🔧",
                "pattern": "📋",
                "similar_task": "🔗",
            }
            icon = icons.get(rec.type, "•")

            # Color by type
            colors = {
                "warning": "yellow",
                "tip": "cyan",
                "tool": "green",
                "pattern": "blue",
                "similar_task": "magenta",
            }
            color = colors.get(rec.type, "white")

            console.print(
                f"  {icon} [{color}]{rec.title}[/{color}] ({rec.confidence:.0%})"
            )
            console.print(f"     {rec.description}\n")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Intent Recognition CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze task intent")
    analyze_parser.add_argument(
        "description", nargs="?", help="Task description to analyze"
    )
    analyze_parser.add_argument("--spec-dir", help="Spec directory to analyze")
    analyze_parser.add_argument("--output", "-o", help="Output file for analysis JSON")

    # Feedback command
    feedback_parser = subparsers.add_parser(
        "feedback", help="Record feedback on intent detection"
    )
    feedback_parser.add_argument("--task-id", required=True, help="Task identifier")
    feedback_parser.add_argument(
        "--detected", required=True, help="Detected intent category"
    )
    feedback_parser.add_argument(
        "--actual", required=True, help="Actual intent category"
    )
    feedback_parser.add_argument(
        "--confidence", type=float, default=0.5, help="Detection confidence (0-1)"
    )
    feedback_parser.add_argument("--description", help="Task description")
    feedback_parser.add_argument("--notes", help="Additional notes")
    feedback_parser.add_argument("--project-id", help="Project identifier")

    # Metrics command
    metrics_parser = subparsers.add_parser("metrics", help="Show accuracy metrics")
    metrics_parser.add_argument("--project-id", help="Filter by project")

    # Recommend command
    recommend_parser = subparsers.add_parser(
        "recommend", help="Generate recommendations"
    )
    recommend_parser.add_argument("description", nargs="?", help="Task description")
    recommend_parser.add_argument("--spec-dir", help="Spec directory")
    recommend_parser.add_argument("--project-id", help="Project identifier")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Execute command
    if args.command == "analyze":
        cmd_analyze(args)
    elif args.command == "feedback":
        cmd_feedback(args)
    elif args.command == "metrics":
        cmd_metrics(args)
    elif args.command == "recommend":
        cmd_recommend(args)


if __name__ == "__main__":
    main()
