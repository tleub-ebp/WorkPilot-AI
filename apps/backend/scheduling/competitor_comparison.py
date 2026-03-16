"""Competitor Cost Comparison — Cost Intelligence Engine.

Static pricing data for competing AI coding tools.
Shows users how WorkPilot actual API costs compare to fixed-price alternatives.

Example:
    >>> from scheduling.competitor_comparison import compare_to_competitors
    >>> results = compare_to_competitors(8.50)
    >>> for r in results:
    ...     print(f"{r['competitor']}: saves ${r['savings']:.2f}")
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class CompetitorPlan:
    """Pricing plan for a competing AI coding tool."""
    name: str
    monthly_cost: float
    included_requests: str
    overage_info: str
    model_used: str
    notes: str = ""


COMPETITOR_PLANS: list[CompetitorPlan] = [
    CompetitorPlan(
        name="Cursor Pro",
        monthly_cost=20.0,
        included_requests="500 fast requests/month, unlimited slow",
        overage_info="$0.04/fast request after limit",
        model_used="claude-sonnet-4, gpt-4o",
        notes="Uses Sonnet/GPT-4o for fast requests, slower models for unlimited",
    ),
    CompetitorPlan(
        name="Cursor Business",
        monthly_cost=40.0,
        included_requests="500 fast requests/month, unlimited slow",
        overage_info="$0.04/fast request after limit",
        model_used="claude-sonnet-4, gpt-4o",
    ),
    CompetitorPlan(
        name="Windsurf Pro",
        monthly_cost=15.0,
        included_requests="Unlimited autocomplete, limited chat",
        overage_info="Usage-based after limits",
        model_used="Custom + Claude/GPT",
    ),
    CompetitorPlan(
        name="Windsurf Teams",
        monthly_cost=30.0,
        included_requests="Higher limits, team features",
        overage_info="Usage-based after limits",
        model_used="Custom + Claude/GPT",
    ),
    CompetitorPlan(
        name="Claude Code (Max 5x)",
        monthly_cost=100.0,
        included_requests="5x usage vs Pro plan",
        overage_info="Hard usage cap, no overage",
        model_used="claude-sonnet-4, claude-opus-4",
    ),
    CompetitorPlan(
        name="Claude Code (Max 20x)",
        monthly_cost=200.0,
        included_requests="20x usage vs Pro plan",
        overage_info="Hard usage cap, no overage",
        model_used="claude-sonnet-4, claude-opus-4",
    ),
    CompetitorPlan(
        name="GitHub Copilot Individual",
        monthly_cost=10.0,
        included_requests="Unlimited autocomplete + chat",
        overage_info="N/A",
        model_used="GPT-4o, Claude Sonnet (via extension)",
    ),
    CompetitorPlan(
        name="GitHub Copilot Business",
        monthly_cost=19.0,
        included_requests="Unlimited autocomplete + chat + agents",
        overage_info="N/A",
        model_used="GPT-4o, Claude Sonnet",
    ),
]


def compare_to_competitors(
    workpilot_monthly_cost: float,
) -> list[dict[str, Any]]:
    """Compare WorkPilot actual API cost to competitor fixed plans.

    Args:
        workpilot_monthly_cost: User's actual WorkPilot spend this month in USD.

    Returns:
        List of comparison dicts sorted by savings (highest first).
        Each dict has: competitor, competitor_monthly, workpilot_monthly,
        savings, savings_pct, included_requests, model_used, notes.
    """
    results = []
    for plan in COMPETITOR_PLANS:
        diff = plan.monthly_cost - workpilot_monthly_cost
        results.append({
            "competitor": plan.name,
            "competitor_monthly": plan.monthly_cost,
            "workpilot_monthly": round(workpilot_monthly_cost, 2),
            "savings": round(diff, 2),
            "savings_pct": round(diff / plan.monthly_cost * 100, 1) if plan.monthly_cost > 0 else 0,
            "included_requests": plan.included_requests,
            "model_used": plan.model_used,
            "notes": plan.notes,
        })
    return sorted(results, key=lambda r: r["savings"], reverse=True)


def format_comparison_table(results: list[dict[str, Any]]) -> str:
    """Format comparison results as a readable table.

    Args:
        results: Output from compare_to_competitors().

    Returns:
        Formatted string table.
    """
    lines = [
        "Cost Comparison: WorkPilot AI vs Competitors",
        "=" * 70,
        f"  WorkPilot monthly spend: ${results[0]['workpilot_monthly']:.2f}",
        "",
        f"  {'Competitor':<30} {'Price':>8} {'Savings':>10} {'%':>6}",
        f"  {'-' * 30} {'-' * 8} {'-' * 10} {'-' * 6}",
    ]
    for r in results:
        sign = "+" if r["savings"] >= 0 else ""
        lines.append(
            f"  {r['competitor']:<30} ${r['competitor_monthly']:>6.2f}"
            f"  {sign}${r['savings']:>7.2f}  {r['savings_pct']:>5.1f}%"
        )
    lines.append("")
    lines.append("  (+) = WorkPilot is cheaper  |  (-) = competitor is cheaper")
    return "\n".join(lines)
