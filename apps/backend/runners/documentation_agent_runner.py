#!/usr/bin/env python3
"""
Documentation Agent Runner

Generates and maintains technical documentation automatically:
- API docs
- README
- Contribution guides
- JSDoc / Python docstrings
- Sequence diagrams

Detects outdated documentation after code changes.
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
    from documentation import (
        DocumentationAnalyzer,
        DocumentationGenerator,
        DocumentationUpdater,
    )
    from documentation.models import DocType

    _DOCUMENTATION_AVAILABLE = True
except ImportError:
    _DOCUMENTATION_AVAILABLE = False


if _DOCUMENTATION_AVAILABLE:
    DOC_TYPE_MAP = {
        "api": DocType.API_DOCS,
        "readme": DocType.README,
        "contribution": DocType.CONTRIBUTION_GUIDE,
        "docstrings": DocType.INLINE_DOCSTRINGS,
        "diagrams": DocType.SEQUENCE_DIAGRAMS,
        "changelog": DocType.CHANGELOG,
    }
else:
    DOC_TYPE_MAP = {
        "api": "api",
        "readme": "readme",
        "contribution": "contribution",
        "docstrings": "docstrings",
        "diagrams": "diagrams",
        "changelog": "changelog",
    }

ALL_DOC_TYPES = list(DOC_TYPE_MAP.keys())


class DocumentationAgentRunner:
    """Runner for the Documentation Agent feature."""

    def __init__(
        self,
        project_dir: str,
        doc_types: list[str] | None = None,
        output_dir: str | None = None,
        insert_inline: bool = False,
        model: str | None = None,
        thinking_level: str | None = None,
    ):
        self.project_dir = Path(project_dir)
        self.doc_types = doc_types or ALL_DOC_TYPES
        self.output_dir = output_dir
        self.insert_inline = insert_inline
        self.model = model
        self.thinking_level = thinking_level or "medium"

    def setup(self):
        """Initialize the documentation agent."""
        print("📚 Initializing Documentation Agent...")
        print(f"📁 Project: {self.project_dir}")
        print(f"📄 Doc types: {', '.join(self.doc_types)}")
        if self.insert_inline:
            print("🔧 Inline docstring insertion enabled")

    def run_documentation(self) -> dict:
        """Run the full documentation generation workflow."""
        print("\n🔍 Phase 1: Analyzing documentation coverage...")
        analyzer = DocumentationAnalyzer(str(self.project_dir))
        coverage_before = analyzer.analyze_coverage()
        print(
            f"   Coverage: {coverage_before.coverage_percent:.1f}% "
            f"({coverage_before.documented_functions}/{coverage_before.total_functions} functions, "
            f"{coverage_before.documented_classes}/{coverage_before.total_classes} classes)"
        )

        outdated = analyzer.detect_outdated_docs()
        if outdated:
            print(f"   ⚠️  {len(outdated)} outdated doc file(s) detected")

        print("\n✍️  Phase 2: Generating documentation...")
        generator = DocumentationGenerator(
            str(self.project_dir),
            output_dir=self.output_dir,
        )

        generated_files = []
        results_by_type = {}

        # README
        if "readme" in self.doc_types:
            print("   📖 Generating README...")
            try:
                readme = analyzer.analyze_readme()
                project_context = {
                    "description": "",
                    "tech_stack": [],
                }
                section = generator.generate_readme(project_context)
                generated_files.append(section.file_path)
                results_by_type["readme"] = {
                    "status": "success",
                    "file": section.file_path,
                }
                print("      ✅ README.md written")
            except Exception as e:
                results_by_type["readme"] = {"status": "error", "error": str(e)}

        # Contribution guide
        if "contribution" in self.doc_types:
            print("   🤝 Generating CONTRIBUTING.md...")
            try:
                section = generator.generate_contribution_guide()
                generated_files.append(section.file_path)
                results_by_type["contribution"] = {
                    "status": "success",
                    "file": section.file_path,
                }
                print("      ✅ CONTRIBUTING.md written")
            except Exception as e:
                results_by_type["contribution"] = {"status": "error", "error": str(e)}

        # API docs
        if "api" in self.doc_types:
            print("   🔌 Analyzing API endpoints...")
            try:
                api_sections = analyzer.analyze_api_docs()
                endpoint_data = [
                    {"path": s.title.replace("API: ", ""), "method": "GET"}
                    for s in api_sections
                ]
                doc_sections = generator.generate_api_docs(endpoint_data)
                if doc_sections:
                    generated_files.append(doc_sections[0].file_path)
                results_by_type["api"] = {
                    "status": "success",
                    "endpoints_found": len(api_sections),
                }
                print(f"      ✅ {len(api_sections)} endpoint(s) documented")
            except Exception as e:
                results_by_type["api"] = {"status": "error", "error": str(e)}

        # Inline docstrings
        if "docstrings" in self.doc_types and self.insert_inline:
            print("   💬 Inserting missing docstrings...")
            missing = analyzer.find_missing_docs()
            symbols_needing_docs = []
            for entry in missing[:30]:
                parts = entry.split(":")
                if len(parts) >= 3:
                    file_path, line, name = parts[0], parts[1], parts[2]
                    symbols_needing_docs.append(
                        {
                            "file_path": str(self.project_dir / file_path),
                            "name": name,
                            "kind": "function",
                            "has_doc": False,
                        }
                    )
            if symbols_needing_docs:
                doc_sections = generator.generate_docstrings(
                    symbols_needing_docs, language="python"
                )
                updater = DocumentationUpdater(str(self.project_dir))
                total_inserted = 0
                for sym in symbols_needing_docs:
                    count = updater.insert_docstrings(
                        sym["file_path"],
                        [sym],
                        dry_run=False,
                    )
                    total_inserted += count
                results_by_type["docstrings"] = {
                    "status": "success",
                    "inserted": total_inserted,
                    "missing_before": len(missing),
                }
                print(f"      ✅ {total_inserted} docstring(s) inserted")

        print("\n🔄 Phase 3: Updating outdated docs...")
        if outdated:
            updater = DocumentationUpdater(str(self.project_dir))
            updated = updater.check_and_update()
            print(f"   Updated {len(updated)} outdated doc(s)")
        else:
            print("   No outdated docs found")

        # Re-check coverage
        coverage_after = analyzer.analyze_coverage()
        print(f"\n📊 Coverage after: {coverage_after.coverage_percent:.1f}%")

        result = {
            "status": "success",
            "doc_types_processed": self.doc_types,
            "generated_files": generated_files,
            "results_by_type": results_by_type,
            "coverage_before": coverage_before.to_dict(),
            "coverage_after": coverage_after.to_dict(),
            "outdated_found": len(outdated),
            "summary": self._generate_summary(
                coverage_before, coverage_after, generated_files
            ),
        }

        return result

    def _generate_summary(
        self, coverage_before, coverage_after, files: list[str]
    ) -> dict:
        """Generate a human-readable summary."""
        coverage_delta = (
            coverage_after.coverage_percent - coverage_before.coverage_percent
        )
        return {
            "files_written": len(files),
            "coverage_before": f"{coverage_before.coverage_percent:.1f}%",
            "coverage_after": f"{coverage_after.coverage_percent:.1f}%",
            "coverage_delta": f"+{coverage_delta:.1f}%"
            if coverage_delta >= 0
            else f"{coverage_delta:.1f}%",
            "missing_docs_before": len(coverage_before.missing_docs),
            "missing_docs_after": len(coverage_after.missing_docs),
        }


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Documentation Agent — Auto-generate and maintain technical docs"
    )
    parser.add_argument(
        "--project-dir",
        required=True,
        help="Project directory to document",
    )
    parser.add_argument(
        "--doc-types",
        default=",".join(ALL_DOC_TYPES),
        help=f"Comma-separated doc types to generate: {','.join(ALL_DOC_TYPES)}",
    )
    parser.add_argument(
        "--output-dir",
        help="Output directory for generated docs (default: project/docs/)",
    )
    parser.add_argument(
        "--insert-inline",
        action="store_true",
        help="Insert docstrings directly into source files",
    )
    parser.add_argument("--model", help="AI model to use")
    parser.add_argument(
        "--thinking-level",
        default="medium",
        choices=["none", "low", "medium", "high", "ultrathink"],
    )

    args = parser.parse_args()

    if not _DOCUMENTATION_AVAILABLE:
        error_result = {
            "status": "error",
            "error": "Documentation module not yet available. This feature is under development.",
            "files_generated": [],
        }
        print("__DOC_RESULT__:" + json.dumps(error_result))
        sys.exit(0)

    if not os.path.exists(args.project_dir):
        print(f"❌ Project directory not found: {args.project_dir}")
        sys.exit(1)

    doc_types = [
        t.strip() for t in args.doc_types.split(",") if t.strip() in ALL_DOC_TYPES
    ]
    if not doc_types:
        print(f"❌ No valid doc types specified. Valid: {','.join(ALL_DOC_TYPES)}")
        sys.exit(1)

    try:
        runner = DocumentationAgentRunner(
            project_dir=args.project_dir,
            doc_types=doc_types,
            output_dir=args.output_dir,
            insert_inline=args.insert_inline,
            model=args.model,
            thinking_level=args.thinking_level,
        )
        runner.setup()
        result = runner.run_documentation()

        print("__DOC_RESULT__:" + json.dumps(result))
        print("\n✅ Documentation generation complete!")
    except KeyboardInterrupt:
        print("\n⚠️ Documentation generation interrupted.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
