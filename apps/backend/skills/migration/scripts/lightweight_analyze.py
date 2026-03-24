#!/usr/bin/env python3
"""
Lightweight Stack Analysis Script

Optimized version that delegates complex logic to specialized modules.
Minimal token usage with fast execution.

Usage:
    python lightweight_analyze.py --project-root /path/to/project
"""

import argparse
import json


# Import specialized modules only when needed
def get_stack_analyzer():
    """Lazy import of stack analyzer to minimize token usage."""
    from .stack_analyzer_core import StackAnalyzerCore

    return StackAnalyzerCore()


def main():
    """Lightweight entry point with minimal logic."""
    parser = argparse.ArgumentParser(description="Lightweight stack analysis")
    parser.add_argument("--project-root", default=".", help="Project root directory")
    parser.add_argument("--output", help="Output file (JSON)")
    parser.add_argument("--languages", help="Languages (comma-separated)")
    parser.add_argument("--frameworks", help="Frameworks (comma-separated)")
    parser.add_argument("--dependencies", help="Dependencies (JSON)")

    args = parser.parse_args()

    # Delegate to core analyzer
    analyzer = get_stack_analyzer()

    if args.languages or args.frameworks or args.dependencies:
        # Test mode with provided data
        result = analyzer.analyze_from_data(
            languages=args.languages.split(",") if args.languages else None,
            frameworks=args.frameworks.split(",") if args.frameworks else None,
            dependencies=json.loads(args.dependencies) if args.dependencies else None,
        )
    else:
        # Real analysis mode
        result = analyzer.analyze(args.project_root)

    # Output result
    output_data = result.to_dict()

    if args.output:
        with open(args.output, "w") as f:
            json.dump(output_data, f, indent=2)
    else:
        print(json.dumps(output_data, indent=2))


if __name__ == "__main__":
    main()
