#!/usr/bin/env python3
"""
Architecture Visualizer Runner

Analyzes the codebase and generates interactive architecture diagrams:
module dependencies, data flow, component hierarchy, and database schema.
Auto-updates on each build.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Add the apps/backend directory to the Python path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from architecture_visualizer import ArchitectureAnalyzer, DiagramGenerator


class ArchitectureVisualizerRunner:
    """Runner for the Architecture Visualizer feature."""

    def __init__(
        self,
        project_dir: str,
        output_dir: Optional[str] = None,
        diagram_types: Optional[List[str]] = None,
        model: Optional[str] = None,
        thinking_level: Optional[str] = None,
    ):
        self.project_dir = Path(project_dir)
        self.output_dir = Path(output_dir) if output_dir else self.project_dir / ".auto-claude" / "architecture"
        self.diagram_types = diagram_types or ["module_dependencies", "component_hierarchy", "data_flow", "database_schema"]
        self.model = model
        self.thinking_level = thinking_level or "medium"
        self.analyzer: Optional[ArchitectureAnalyzer] = None

    def setup(self):
        """Initialize the analyzer."""
        print("🏗️  Initializing Architecture Visualizer...")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.analyzer = ArchitectureAnalyzer(str(self.project_dir))
        print(f"📁 Project: {self.project_dir}")
        print(f"📊 Diagram types: {', '.join(self.diagram_types)}")

    def run_analysis(self) -> Dict:
        """Run the architecture analysis and return structured results."""
        if not self.analyzer:
            self.setup()

        print("🔍 Analyzing project architecture...")
        all_diagrams = self.analyzer.analyze_all()

        results = {}
        for diagram_type, diagram in all_diagrams.items():
            if diagram_type not in self.diagram_types:
                continue
            print(f"✅ {diagram.title}: {len(diagram.nodes)} nodes, {len(diagram.edges)} edges")
            results[diagram_type] = diagram.to_dict()

        return {
            "status": "success",
            "diagrams": results,
            "project_dir": str(self.project_dir),
            "diagram_types_analyzed": list(results.keys()),
            "summary": self._generate_summary(results),
        }

    def save_diagrams(self, result: Dict) -> str:
        """Save diagrams to .auto-claude/architecture/ and return output path."""
        diagrams = result.get("diagrams", {})
        for diagram_type, diagram_data in diagrams.items():
            mermaid_code = diagram_data.get("mermaid_code", "")
            if mermaid_code:
                output_file = self.output_dir / f"{diagram_type}.md"
                title = diagram_data.get("title", diagram_type)
                content = f"# {title}\n\n```mermaid\n{mermaid_code}\n```\n\n"
                content += f"*Generated at: {diagram_data.get('generated_at', '')}*\n"
                content += f"*Nodes: {len(diagram_data.get('nodes', []))}, Edges: {len(diagram_data.get('edges', []))}*\n"
                output_file.write_text(content, encoding="utf-8")
                print(f"💾 Saved: {output_file}")

        # Save JSON data
        json_file = self.output_dir / "architecture.json"
        json_file.write_text(json.dumps(result, indent=2), encoding="utf-8")
        return str(self.output_dir)

    def _generate_summary(self, diagrams: Dict) -> Dict:
        """Generate a summary of the architecture analysis."""
        total_nodes = sum(len(d.get("nodes", [])) for d in diagrams.values())
        total_edges = sum(len(d.get("edges", [])) for d in diagrams.values())
        return {
            "total_diagrams": len(diagrams),
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "diagram_types": list(diagrams.keys()),
        }


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Architecture Visualizer — Generate architecture diagrams from code"
    )
    parser.add_argument(
        "--project-dir",
        required=True,
        help="Project directory to analyze",
    )
    parser.add_argument(
        "--output-dir",
        help="Output directory for diagram files (default: .auto-claude/architecture/)",
    )
    parser.add_argument(
        "--diagram-types",
        help="Comma-separated diagram types: module_dependencies,component_hierarchy,data_flow,database_schema",
        default="module_dependencies,component_hierarchy,data_flow,database_schema",
    )
    parser.add_argument("--model", help="AI model to use")
    parser.add_argument(
        "--thinking-level",
        default="medium",
        choices=["none", "low", "medium", "high", "ultrathink"],
    )

    args = parser.parse_args()

    if not os.path.exists(args.project_dir):
        print(f"❌ Project directory not found: {args.project_dir}")
        sys.exit(1)

    diagram_types = [t.strip() for t in args.diagram_types.split(",") if t.strip()]

    try:
        runner = ArchitectureVisualizerRunner(
            project_dir=args.project_dir,
            output_dir=args.output_dir,
            diagram_types=diagram_types,
            model=args.model,
            thinking_level=args.thinking_level,
        )
        runner.setup()
        result = runner.run_analysis()
        output_path = runner.save_diagrams(result)
        result["output_dir"] = output_path

        print("__ARCH_VIZ_RESULT__:" + json.dumps(result))
        print(f"\n✅ Architecture diagrams saved to: {output_path}")
    except KeyboardInterrupt:
        print("\n⚠️ Architecture visualization interrupted.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
