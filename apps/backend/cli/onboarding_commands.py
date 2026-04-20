"""CLI commands for the Onboarding Agent."""

from pathlib import Path


def handle_onboard_command(project_dir: Path, output: Path | None = None) -> None:
    """Generate an onboarding package for ``project_dir``.

    Args:
        project_dir: Path to the project root.
        output: Optional path for the rendered markdown. When omitted, the
            result is printed to stdout.
    """
    from onboarding_agent import OnboardingPackageBuilder, render_markdown

    package = OnboardingPackageBuilder().build(project_dir)
    markdown = render_markdown(package)

    if output is None:
        print(markdown)
        return

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(markdown, encoding="utf-8")
    print(f"Onboarding guide written to {output}")
    print(
        f"  {len(package.tour)} tour step(s), "
        f"{len(package.quiz)} quiz question(s), "
        f"{len(package.first_tasks)} first task(s), "
        f"{len(package.glossary)} glossary term(s)"
    )
