"""
Browser Agent CLI Commands
============================

CLI command handlers for the Built-in Browser Agent.
"""

import asyncio
import sys
from pathlib import Path


def handle_browser_agent_command(
    project_dir: Path,
    mode: str,
    url: str | None = None,
    name: str | None = None,
    verbose: bool = False,
) -> None:
    """Handle browser agent CLI commands.

    Args:
        project_dir: The project directory.
        mode: One of 'screenshot', 'compare', 'tests', 'dashboard'.
        url: URL for screenshot/compare operations.
        name: Name for screenshot/baseline operations.
        verbose: Enable verbose output.
    """
    from runners.browser_agent_runner import BrowserAgentRunner

    runner = BrowserAgentRunner(project_dir=project_dir)

    if mode == "screenshot":
        if not url:
            print("❌ --browser-url is required for screenshot mode")
            sys.exit(1)
        if not name:
            print("❌ --browser-name is required for screenshot mode")
            sys.exit(1)

        print(f"📸 Capturing screenshot of {url}...")
        result = asyncio.run(runner.run_screenshot(url=url, name=name))
        if result["success"]:
            print(f"✅ Screenshot saved: {result['data']['path']}")
        else:
            print(f"❌ {result.get('error', 'Failed')}")
            sys.exit(1)

    elif mode == "compare":
        if not name:
            print("❌ --browser-name is required for compare mode")
            sys.exit(1)

        print(f"🔍 Comparing '{name}' against baseline...")
        result = asyncio.run(runner.run_compare(name=name, url=url))
        if result["success"]:
            data = result["data"]
            emoji = "✅" if data["passed"] else "❌"
            print(
                f"{emoji} Match: {data['matchPercentage']}% (threshold: {data['threshold']}%)"
            )
        else:
            print(f"❌ {result.get('error', 'Failed')}")
            sys.exit(1)

    elif mode == "tests":
        print("🧪 Running E2E tests...")
        result = runner.run_tests()
        if result["success"]:
            data = result["data"]
            print(
                f"Results: {data['passed']} passed, {data['failed']} failed, {data['skipped']} skipped"
            )
        else:
            print(f"❌ {result.get('error', 'Failed')}")
            sys.exit(1)

    elif mode == "dashboard":
        result = runner.run_dashboard()
        if result["success"]:
            data = result["data"]
            stats = data["stats"]
            print("🌐 Browser Agent Dashboard")
            print(f"  Tests discovered: {stats['totalTests']}")
            print(f"  Screenshots: {stats['screenshotsCaptured']}")
            print(f"  Baselines: {len(data['baselines'])}")

    else:
        print(f"❌ Unknown browser agent mode: {mode}")
        print("   Valid modes: screenshot, compare, tests, dashboard")
        sys.exit(1)
