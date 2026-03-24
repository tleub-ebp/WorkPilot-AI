#!/usr/bin/env python3
"""
Performance Profiler Agent Runner

Profiles the codebase, identifies bottlenecks, and proposes optimizations.
Can automatically implement fixes for auto-implementable suggestions.
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Add the apps/backend directory to the Python path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

try:
    from performance import (
        BenchmarkRunner,
        PerformanceOptimizer,
        PerformanceProfiler,
        PerformanceReport,
    )

    _PERFORMANCE_AVAILABLE = True
except ImportError:
    _PERFORMANCE_AVAILABLE = False

PERF_RESULT_MARKER = "__PERF_RESULT__:"


class PerformanceProfilerRunner:
    """Runner for the Performance Profiler Agent feature."""

    def __init__(
        self,
        project_dir: str,
        auto_implement: bool = False,
        model: str | None = None,
        thinking_level: str | None = None,
    ):
        self.project_dir = Path(project_dir)
        self.auto_implement = auto_implement
        self.model = model
        self.thinking_level = thinking_level or "high"

    def setup(self):
        """Initialize the profiler."""
        print("⚡ Initializing Performance Profiler Agent...")
        print(f"📁 Project: {self.project_dir}")
        if self.auto_implement:
            print("🔧 Auto-implementation enabled")

    def run_profiling(self) -> dict:
        """Run the full performance profiling workflow."""
        print("\n🔍 Phase 1: Static code analysis...")
        profiler = PerformanceProfiler(str(self.project_dir))
        report = profiler.profile()

        print(f"\n📊 Found {len(report.bottlenecks)} bottlenecks")
        for b in report.bottlenecks[:5]:
            print(
                f"   [{b.severity.value.upper()}] {b.file_path}:{b.line_start} — {b.description[:60]}"
            )

        print("\n🏃 Phase 2: Running benchmarks...")
        benchmark_runner = BenchmarkRunner(str(self.project_dir))
        try:
            benchmarks = benchmark_runner.run_benchmarks(timeout_seconds=30)
            report.benchmarks = benchmarks
            print(f"   Ran {len(benchmarks)} benchmark(s)")
        except Exception as e:
            print(f"   ⚠️  Benchmark warning: {e}")

        print("\n💡 Phase 3: Generating optimization suggestions...")
        optimizer = PerformanceOptimizer(str(self.project_dir), report)
        suggestions = optimizer.generate_suggestions()
        report.suggestions = suggestions
        report.compute_summary()

        print(f"   Generated {len(suggestions)} suggestions")
        auto_fix_count = sum(1 for s in suggestions if s.auto_implementable)
        if auto_fix_count:
            print(f"   {auto_fix_count} can be auto-implemented")

        result = {
            "status": "success",
            "report": report.to_dict(),
            "summary": self._generate_summary(report),
        }

        if self.auto_implement and auto_fix_count > 0:
            print("\n🔧 Phase 4: Auto-implementing fixes...")
            impl_results = []
            for suggestion in suggestions:
                if suggestion.auto_implementable:
                    impl_result = optimizer.implement_suggestion(
                        suggestion, dry_run=False
                    )
                    impl_results.append(impl_result)
                    print(f"   ✅ {suggestion.title}")
            result["implementation"] = impl_results
            print("__PERF_IMPLEMENTATION__:" + json.dumps(impl_results))

        return result

    def _generate_summary(self, report: PerformanceReport) -> dict:
        """Generate a human-readable summary."""
        summary = report.summary.copy()
        if report.bottlenecks:
            top_severity = max(
                report.bottlenecks,
                key=lambda b: ["low", "medium", "high", "critical"].index(
                    b.severity.value
                ),
            )
            summary["top_issue"] = (
                f"{top_severity.file_path}: {top_severity.description[:80]}"
            )
        return summary


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Performance Profiler Agent — Profile and optimize your codebase"
    )
    parser.add_argument(
        "--project-dir",
        required=True,
        help="Project directory to profile",
    )
    parser.add_argument(
        "--auto-implement",
        action="store_true",
        help="Automatically implement safe optimizations",
    )
    parser.add_argument("--model", help="AI model to use")
    parser.add_argument(
        "--thinking-level",
        default="high",
        choices=["none", "low", "medium", "high", "ultrathink"],
    )

    args = parser.parse_args()

    if not _PERFORMANCE_AVAILABLE:
        error_result = {
            "status": "error",
            "error": "Performance profiler module not yet available. This feature is under development.",
            "report": None,
            "summary": {},
        }
        print(PERF_RESULT_MARKER + json.dumps(error_result))
        sys.exit(0)

    if not os.path.exists(args.project_dir):
        print(f"❌ Project directory not found: {args.project_dir}")
        sys.exit(1)

    try:
        runner = PerformanceProfilerRunner(
            project_dir=args.project_dir,
            auto_implement=args.auto_implement,
            model=args.model,
            thinking_level=args.thinking_level,
        )
        runner.setup()
        result = runner.run_profiling()

        print(PERF_RESULT_MARKER + json.dumps(result))
        print("\n✅ Performance profiling complete!")
    except KeyboardInterrupt:
        print("\n⚠️ Profiling interrupted.")
        sys.exit(1)
    except Exception as e:
        error_result = {
            "status": "error",
            "error": str(e),
            "report": None,
            "summary": {},
        }
        print(PERF_RESULT_MARKER + json.dumps(error_result))
        sys.exit(1)


if __name__ == "__main__":
    main()
