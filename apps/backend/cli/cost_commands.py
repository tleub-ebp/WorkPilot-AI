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
    data_path = project_dir / ".workpilot" / "cost_data.json"
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
    data_path = project_dir / ".workpilot" / "cost_data.json"
    estimator.load_from_file(data_path)

    monthly_report = estimator.get_monthly_report(str(project_dir))
    monthly_cost = monthly_report["total_cost"]

    results = compare_to_competitors(monthly_cost)
    print()
    print(format_comparison_table(results))
    print()


def handle_cost_predict_command(
    project_dir: Path,
    spec_id: str,
    model: str | None = None,
    provider: str = "anthropic",
    compare: bool = True,
) -> None:
    """Predict the cost of running a spec before launch.

    Args:
        project_dir: Path to the project root.
        spec_id: Spec identifier, e.g. ``'001-feature-name'``.
        model: Model name to predict for. Defaults to ``'claude-sonnet-4-6'``.
        provider: Provider name. Defaults to ``'anthropic'``.
        compare: When True, include alternate models in the report.
    """
    from cost_intelligence import CostPredictor

    spec_dir = project_dir / ".workpilot" / "specs" / spec_id
    if not spec_dir.is_dir():
        print(f"Spec not found: {spec_dir}")
        return

    alternatives: list[tuple[str, str]] = []
    if compare:
        alternatives = [
            ("anthropic", "claude-opus-4-6"),
            ("anthropic", "claude-sonnet-4-6"),
            ("anthropic", "claude-haiku-4-5"),
            ("openai", "gpt-4o"),
            ("openai", "gpt-4o-mini"),
            ("google", "gemini-2.5-pro"),
            ("google", "gemini-2.5-flash"),
            ("grok", "grok-4"),
            ("copilot", "gpt-4.1"),
            ("windsurf", "windsurf-cascade"),
            ("ollama", "llama-3.3-70b"),
        ]

    predictor = CostPredictor()
    report = predictor.predict(
        spec_dir=spec_dir,
        project_root=project_dir,
        selected_model=model,
        selected_provider=provider,
        alternative_models=alternatives,
    )

    sel = report.selected
    print(f"\n  Cost Prediction — {report.spec_id}")
    print(f"  {'=' * 60}")
    print(f"  Subtasks: {report.footprint.subtask_count}")
    print(f"  Files in scope: {report.footprint.touched_files}")
    print(f"  LOC in scope: {report.footprint.loc_in_scope}")
    print(f"  Complexity: {report.footprint.complexity_score:.1f}")
    print(f"  History samples: {report.history_samples}")
    print()
    print(f"  Selected model: {sel.provider}/{sel.model}")
    print(
        f"    Tokens (in/out/thinking): "
        f"{sel.expected_input_tokens:,} / {sel.expected_output_tokens:,} / "
        f"{sel.expected_thinking_tokens:,}"
    )
    print(
        f"    Cost: ${sel.expected_cost_usd:.4f} "
        f"(low ${sel.low_cost_usd:.4f} / high ${sel.high_cost_usd:.4f})"
    )
    print(f"    Confidence: {sel.confidence:.0%}")
    print(f"    QA iterations expected: {sel.expected_qa_iterations}")

    if report.alternatives:
        print("\n  Alternatives:")
        print(f"    {'Model':<45} {'Cost':>12} {'Range':>22}")
        for alt in sorted(report.alternatives, key=lambda a: a.expected_cost_usd):
            tag = f"{alt.provider}/{alt.model}"
            print(
                f"    {tag:<45} ${alt.expected_cost_usd:>9.4f} "
                f"${alt.low_cost_usd:>7.4f} – ${alt.high_cost_usd:>7.4f}"
            )
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
    data_path = project_dir / ".workpilot" / "cost_data.json"
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
