#!/usr/bin/env python3
"""
Browser Agent Runner
=====================

CLI entry point for the Built-in Browser Agent.

Subcommands:
  screenshot    Capture a screenshot of a URL
  compare       Compare a screenshot against its baseline
  baseline      Manage baselines (set, list, delete)
  tests         Run E2E tests
  dashboard     Show browser agent dashboard data
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Add the apps/backend directory to the Python path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))


class BrowserAgentRunner:
    """Runner for the Built-in Browser Agent."""

    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir)

    def _get_controller(self):
        from browser_agent.browser_controller import BrowserController
        return BrowserController(project_dir=self.project_dir)

    def _get_regression_engine(self):
        from browser_agent.visual_regression import VisualRegressionEngine
        return VisualRegressionEngine(project_dir=self.project_dir)

    def _get_test_executor(self):
        from browser_agent.test_executor import TestExecutor
        return TestExecutor(project_dir=self.project_dir)

    async def run_screenshot(self, url: str, name: str, full_page: bool = False) -> dict:
        """Capture a screenshot of a URL."""
        controller = self._get_controller()
        try:
            await controller.launch()
            info = await controller.screenshot(name=name, url=url, full_page=full_page)
            return {"success": True, "data": info.to_dict()}
        finally:
            await controller.close()

    async def run_compare(self, name: str, url: str | None = None) -> dict:
        """Compare a screenshot against its baseline."""
        engine = self._get_regression_engine()

        # If URL provided, capture a fresh screenshot first
        if url:
            controller = self._get_controller()
            try:
                await controller.launch()
                info = await controller.screenshot(name=name, url=url)
                current_path = Path(info.path)
            finally:
                await controller.close()
        else:
            # Find most recent screenshot with this name
            controller = self._get_controller()
            screenshots = controller.list_screenshots()
            matching = [s for s in screenshots if s.name == name]
            if not matching:
                return {"success": False, "error": f"No screenshot found for '{name}'. Capture one first."}
            current_path = Path(matching[0].path)

        result = engine.compare(name=name, current_path=current_path)
        return {"success": True, "data": result.to_dict()}

    def run_set_baseline(self, name: str, screenshot_path: str | None = None) -> dict:
        """Set a screenshot as baseline."""
        engine = self._get_regression_engine()

        if screenshot_path:
            path = Path(screenshot_path)
        else:
            # Find most recent screenshot with this name
            controller = self._get_controller()
            screenshots = controller.list_screenshots()
            matching = [s for s in screenshots if s.name == name]
            if not matching:
                return {"success": False, "error": f"No screenshot found for '{name}'."}
            path = Path(matching[0].path)

        info = engine.set_baseline(name=name, screenshot_path=path)
        return {"success": True, "data": info.to_dict()}

    def run_list_baselines(self) -> dict:
        """List all baselines."""
        engine = self._get_regression_engine()
        baselines = engine.list_baselines()
        return {"success": True, "data": [b.to_dict() for b in baselines]}

    def run_delete_baseline(self, name: str) -> dict:
        """Delete a baseline."""
        engine = self._get_regression_engine()
        deleted = engine.delete_baseline(name)
        return {"success": deleted, "data": {"deleted": deleted}}

    def run_tests(self, test_files: list[str] | None = None) -> dict:
        """Run E2E tests."""
        executor = self._get_test_executor()
        result = executor.run_tests(test_files=test_files)
        return {"success": True, "data": result.to_dict()}

    def run_dashboard(self) -> dict:
        """Get dashboard data with stats, baselines, screenshots, and recent results."""
        from browser_agent.models import BrowserAgentStats

        controller = self._get_controller()
        engine = self._get_regression_engine()
        executor = self._get_test_executor()

        screenshots = controller.list_screenshots()
        baselines = engine.list_baselines()
        discovered_tests = executor.discover_tests()

        # Compute stats
        stats = BrowserAgentStats(
            total_tests=len(discovered_tests),
            pass_rate=0.0,
            screenshots_captured=len(screenshots),
            regressions_detected=0,
        )

        return {
            "success": True,
            "data": {
                "stats": stats.to_dict(),
                "screenshots": [s.to_dict() for s in screenshots[:20]],
                "baselines": [b.to_dict() for b in baselines],
                "comparisons": [],
                "recentTestRun": None,
            },
        }


def main():
    parser = argparse.ArgumentParser(
        description="Browser Agent - Built-in browser for testing and visual validation"
    )
    parser.add_argument(
        "--project", type=str, required=True, help="Project directory path"
    )
    parser.add_argument(
        "--json", action="store_true", help="Output results as JSON"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # screenshot
    screenshot_parser = subparsers.add_parser("screenshot", help="Capture a screenshot")
    screenshot_parser.add_argument("--url", type=str, required=True, help="URL to screenshot")
    screenshot_parser.add_argument("--name", type=str, required=True, help="Screenshot name")
    screenshot_parser.add_argument("--full-page", action="store_true", help="Capture full page")

    # compare
    compare_parser = subparsers.add_parser("compare", help="Compare against baseline")
    compare_parser.add_argument("--name", type=str, required=True, help="Baseline name")
    compare_parser.add_argument("--url", type=str, help="URL to capture fresh screenshot")

    # baseline
    baseline_parser = subparsers.add_parser("baseline", help="Manage baselines")
    baseline_sub = baseline_parser.add_subparsers(dest="baseline_action")

    set_parser = baseline_sub.add_parser("set", help="Set a baseline")
    set_parser.add_argument("--name", type=str, required=True, help="Baseline name")
    set_parser.add_argument("--screenshot", type=str, help="Screenshot path (uses latest if omitted)")

    list_parser = baseline_sub.add_parser("list", help="List baselines")

    delete_parser = baseline_sub.add_parser("delete", help="Delete a baseline")
    delete_parser.add_argument("--name", type=str, required=True, help="Baseline name")

    # tests
    tests_parser = subparsers.add_parser("tests", help="Run E2E tests")
    tests_parser.add_argument("--files", nargs="*", help="Specific test files to run")

    # dashboard
    subparsers.add_parser("dashboard", help="Show dashboard data")

    args = parser.parse_args()
    project_dir = Path(args.project).resolve()

    if not project_dir.exists():
        print(f"Error: Project directory not found: {project_dir}", file=sys.stderr)
        sys.exit(1)

    runner = BrowserAgentRunner(project_dir=project_dir)

    def output(result: dict):
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            if result.get("success"):
                data = result.get("data", {})
                if isinstance(data, dict):
                    for key, value in data.items():
                        print(f"  {key}: {value}")
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            print(f"  - {item.get('name', item)}")
                        else:
                            print(f"  - {item}")
            else:
                print(f"Error: {result.get('error', 'Unknown error')}", file=sys.stderr)

    try:
        if args.command == "screenshot":
            print(f"📸 Capturing screenshot of {args.url}...")
            result = asyncio.run(runner.run_screenshot(args.url, args.name, args.full_page))
            if result["success"]:
                print(f"✅ Screenshot saved: {result['data']['path']}")
            output(result)

        elif args.command == "compare":
            print(f"🔍 Comparing '{args.name}' against baseline...")
            result = asyncio.run(runner.run_compare(args.name, args.url))
            if result["success"]:
                data = result["data"]
                emoji = "✅" if data["passed"] else "❌"
                print(f"{emoji} Match: {data['matchPercentage']}% (threshold: {data['threshold']}%)")
                if data["diffPixels"] > 0:
                    print(f"   Diff pixels: {data['diffPixels']}")
                    if data.get("diffImagePath"):
                        print(f"   Diff image: {data['diffImagePath']}")
            output(result)

        elif args.command == "baseline":
            if args.baseline_action == "set":
                result = runner.run_set_baseline(args.name, getattr(args, "screenshot", None))
                if result["success"]:
                    print(f"✅ Baseline set for '{args.name}'")
                output(result)
            elif args.baseline_action == "list":
                result = runner.run_list_baselines()
                if result["success"]:
                    baselines = result["data"]
                    if baselines:
                        print(f"📋 {len(baselines)} baseline(s):")
                        for b in baselines:
                            print(f"  - {b['name']} ({b['width']}x{b['height']}) created {b['createdAt']}")
                    else:
                        print("No baselines found.")
                output(result)
            elif args.baseline_action == "delete":
                result = runner.run_delete_baseline(args.name)
                if result["success"] and result["data"]["deleted"]:
                    print(f"🗑️ Baseline '{args.name}' deleted.")
                else:
                    print(f"No baseline found for '{args.name}'.")
                output(result)
            else:
                baseline_parser.print_help()

        elif args.command == "tests":
            print("🧪 Running E2E tests...")
            result = runner.run_tests(getattr(args, "files", None))
            if result["success"]:
                data = result["data"]
                print(f"Results: {data['passed']} passed, {data['failed']} failed, {data['skipped']} skipped")
                print(f"Duration: {data['durationMs']:.0f}ms")
            output(result)

        elif args.command == "dashboard":
            result = runner.run_dashboard()
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                data = result["data"]
                stats = data["stats"]
                print("🌐 Browser Agent Dashboard")
                print(f"  Tests discovered: {stats['totalTests']}")
                print(f"  Screenshots: {stats['screenshotsCaptured']}")
                print(f"  Baselines: {len(data['baselines'])}")

        else:
            parser.print_help()

    except Exception as e:
        error_result = {"success": False, "error": str(e)}
        if args.json:
            print(json.dumps(error_result))
        else:
            print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
