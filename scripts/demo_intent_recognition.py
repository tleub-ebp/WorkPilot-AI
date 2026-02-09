#!/usr/bin/env python3
"""
Intent Recognition Demo
=======================

Demonstrates the intent recognition system with various task examples.
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend"))

from rich.console import Console
from rich.panel import Panel

from intent import IntentRecognizer, IntentRecommender

console = Console()


def demo_task(description: str):
    """Demonstrate intent recognition for a task."""
    console.print(f"\n[bold cyan]Task:[/bold cyan] {description}\n")

    # Analyze intent
    recognizer = IntentRecognizer()
    analysis = recognizer.analyze_intent(description)

    intent = analysis.primary_intent

    # Display results
    console.print(
        f"  [bold]Category:[/bold] {intent.category.value}\n"
        f"  [bold]Workflow:[/bold] {intent.workflow_type.value}\n"
        f"  [bold]Confidence:[/bold] {intent.confidence_score:.1%}\n"
        f"  [bold]Reasoning:[/bold] {intent.reasoning[:100]}...\n"
    )

    # Get recommendations
    recommender = IntentRecommender()
    recs = recommender.generate_recommendations(analysis)

    console.print(
        f"  [bold]Complexity:[/bold] {recs.estimated_complexity}\n"
        f"  [bold]Duration:[/bold] {recs.estimated_duration_hours[0]:.1f}-{recs.estimated_duration_hours[1]:.1f}h\n"
    )

    if recs.recommendations:
        console.print(f"  [bold]Recommendations:[/bold]")
        for rec in recs.recommendations[:2]:
            console.print(f"    • {rec.title}")

    console.print("\n" + "─" * 80)


def main():
    """Run the demo."""
    console.print(
        Panel.fit(
            "[bold cyan]Intent Recognition & Smart Routing Demo[/bold cyan]\n\n"
            "Analyzing various task types to demonstrate semantic understanding",
            border_style="cyan",
        )
    )

    tasks = [
        # Bug fixes
        "The login page returns 500 error when password has special characters",
        "Users can't upload files larger than 10MB - getting timeout errors",
        
        # Features
        "Add OAuth2 authentication with Google and GitHub",
        "Implement real-time notifications using WebSockets",
        
        # Performance
        "Dashboard is loading very slowly for users",
        "API response times are too high, need to optimize",
        
        # Refactoring
        "Migrate from REST to GraphQL for better flexibility",
        "Convert class components to functional components with hooks",
        
        # Security
        "Fix XSS vulnerability in comment rendering",
        "Update authentication to use JWT instead of sessions",
        
        # Data
        "Migrate user data from MongoDB to PostgreSQL",
        "Import historical data from CSV files into the database",
    ]

    for task in tasks:
        try:
            demo_task(task)
        except KeyboardInterrupt:
            console.print("\n[yellow]Demo interrupted by user[/yellow]")
            sys.exit(0)
        except Exception as e:
            console.print(f"\n[red]Error: {e}[/red]")
            continue

    console.print(
        "\n[bold green]✓ Demo complete![/bold green]\n\n"
        "Try it yourself:\n"
        "  [cyan]python -m intent analyze \"Your task description\"[/cyan]\n"
    )


if __name__ == "__main__":
    main()

