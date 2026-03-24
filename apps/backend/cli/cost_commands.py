"""CLI commands for Cost Intelligence Engine.

Provides cost report, competitor comparison, and budget management.
"""

from pathlib import Path


def handle_cost_report_command(project_dir: Path, period: str = "monthly") -> None:
    """Print a cost report for the project.

    Args:
        project_dir: Path to the project root.
        period: Report period — ``'weekly'`` or ``'monthly'``.
    """
    from scheduling.cost_estimator import CostEstimator

    estimator = CostEstimator()
    data_path = project_dir / ".auto-claude" / "cost_data.json"
    estimator.load_from_file(data_path)

    if period == "weekly":
        report = estimator.get_weekly_report(str(project_dir))
    else:
        report = estimator.get_monthly_report(str(project_dir))

    if report["usage_count"] == 0:
        print("No cost data recorded yet.")
        return

    print(f"\n  Cost Report ({period})")
    print(f"  {'=' * 50}")
    print(f"  Total cost: ${report['total_cost']:.4f}")
    print(
        f"  Total tokens: {report['total_tokens']['input']:,} in / {report['total_tokens']['output']:,} out"
    )
    print(f"  Usage records: {report['usage_count']}")

    if report.get("by_agent_type"):
        print("\n  By Agent Type:")
        for agent, cost in sorted(report["by_agent_type"].items(), key=lambda x: -x[1]):
            print(f"    {agent:<20} ${cost:.4f}")

    if report.get("by_phase"):
        print("\n  By Phase:")
        for phase, cost in sorted(report["by_phase"].items(), key=lambda x: -x[1]):
            print(f"    {phase:<20} ${cost:.4f}")

    if report.get("by_spec"):
        print("\n  By Spec:")
        for spec, cost in sorted(report["by_spec"].items(), key=lambda x: -x[1]):
            print(f"    {spec:<30} ${cost:.4f}")

    if report.get("by_model"):
        print("\n  By Model:")
        for model, cost in sorted(report["by_model"].items(), key=lambda x: -x[1]):
            print(f"    {model:<40} ${cost:.4f}")

    if report.get("budget"):
        b = report["budget"]
        print(f"\n  Budget ({b.get('period', 'total')}):")
        print(
            f"    Limit: ${b['limit']:.2f} | Spent: ${b['spent']:.4f} | Remaining: ${b['remaining']:.4f}"
        )
        print(f"    Usage: {b['percentage']:.1f}%")

    print()


def handle_cost_compare_command(project_dir: Path) -> None:
    """Compare costs to competitors.

    Args:
        project_dir: Path to the project root.
    """
    from scheduling.competitor_comparison import (
        compare_to_competitors,
        format_comparison_table,
    )
    from scheduling.cost_estimator import CostEstimator

    estimator = CostEstimator()
    data_path = project_dir / ".auto-claude" / "cost_data.json"
    estimator.load_from_file(data_path)

    monthly_report = estimator.get_monthly_report(str(project_dir))
    monthly_cost = monthly_report["total_cost"]

    results = compare_to_competitors(monthly_cost)
    print()
    print(format_comparison_table(results))
    print()


def handle_cost_budget_command(
    project_dir: Path,
    limit: float | None = None,
    period: str = "monthly",
) -> None:
    """Set or view budget for the project.

    Args:
        project_dir: Path to the project root.
        limit: Budget limit in USD. If None, shows current budget.
        period: Budget period — ``'total'``, ``'monthly'``, or ``'weekly'``.
    """
    from scheduling.cost_estimator import CostEstimator

    estimator = CostEstimator()
    data_path = project_dir / ".auto-claude" / "cost_data.json"
    estimator.load_from_file(data_path)

    project_id = str(project_dir)

    if limit is not None:
        estimator.set_budget(project_id, limit, period=period)
        estimator.save_to_file(data_path)
        print(f"Budget set: ${limit:.2f} ({period})")
    else:
        budget = estimator.get_budget(project_id)
        if budget:
            total_cost = estimator.get_total_cost(project_id=project_id)
            pct = (total_cost / budget.limit * 100) if budget.limit > 0 else 0
            print(f"Budget: ${budget.limit:.2f} ({budget.period})")
            print(f"Spent:  ${total_cost:.4f} ({pct:.1f}%)")
            print(f"Remaining: ${max(0, budget.limit - total_cost):.4f}")
        else:
            print("No budget set. Use --cost-budget <amount> to set one.")
