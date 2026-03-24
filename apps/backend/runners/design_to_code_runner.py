#!/usr/bin/env python3
"""
Design-to-Code Runner - Convert visual designs to production-ready code

This runner orchestrates the Design-to-Code pipeline:
1. Accepts a design image (screenshot, Figma, wireframe, whiteboard photo)
2. Analyzes with Vision AI (Claude Vision, GPT-4o)
3. Generates structured component specification
4. Produces pixel-perfect code for the target framework
5. Integrates project design tokens
6. Generates visual regression tests
7. Optionally syncs with Figma bidirectionally
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Add auto-claude to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cli.utils import import_dotenv
from debug import (
    debug,
    debug_error,
    debug_section,
    debug_success,
)

# Load .env file
load_dotenv = import_dotenv()
env_file = Path(__file__).parent.parent.parent.parent / ".env-files" / ".env"
if env_file.exists():
    load_dotenv(env_file)


class DesignToCodeRunner:
    """Runner for the Design-to-Code pipeline."""

    def __init__(
        self,
        project_dir: str,
        image_path: str = "",
        image_data: str = "",
        framework: str = "react",
        source_type: str = "screenshot",
        design_system_path: str = "",
        figma_url: str = "",
        generate_tests: bool = True,
        custom_instructions: str = "",
        output_dir: str = "",
    ):
        self.project_dir = Path(project_dir)
        self.image_path = image_path
        self.image_data = image_data
        self.framework = framework
        self.source_type = source_type
        self.design_system_path = design_system_path
        self.figma_url = figma_url
        self.generate_tests = generate_tests
        self.custom_instructions = custom_instructions
        self.output_dir = output_dir or str(self.project_dir)

    async def run(self) -> dict:
        """Run the complete design-to-code pipeline."""
        debug_section("Design-to-Code Pipeline")
        debug(f"Project: {self.project_dir}")
        debug(f"Framework: {self.framework}")
        debug(f"Source type: {self.source_type}")

        # Resolve image data
        image_data = await self._resolve_image_data()
        if not image_data:
            debug_error("No image data provided")
            return {
                "success": False,
                "error": "No image data provided. Provide --image-path or --image-data.",
            }

        # Parse Figma URL if provided
        figma_file_key = None
        figma_node_id = None
        if self.figma_url:
            from src.connectors.figma_connector import FigmaConnector

            parsed = FigmaConnector.parse_figma_url(self.figma_url)
            if parsed:
                figma_file_key = parsed.get("file_key")
                figma_node_id = parsed.get("node_id")
                debug(f"Figma file: {figma_file_key}, node: {figma_node_id}")

        # Run the pipeline
        from services.design_to_code_service import DesignToCodeService

        service = DesignToCodeService(str(self.project_dir))

        # Register phase callback for console output
        def on_phase(phase, status):
            phase_icons = {
                "analyzing": "🔍",
                "spec_generation": "📋",
                "code_generation": "💻",
                "design_token_integration": "🎨",
                "visual_test_generation": "🧪",
                "figma_sync": "🔄",
                "complete": "✅",
                "error": "❌",
            }
            icon = phase_icons.get(phase.value, "⏳")
            print(f"  {icon} [{phase.value}] {status}")

        service.on_phase_change(on_phase)

        result = await service.run_pipeline(
            image_data=image_data,
            framework=self.framework,
            design_system_path=self.design_system_path or None,
            source_type=self.source_type,
            figma_file_key=figma_file_key,
            figma_node_id=figma_node_id,
            generate_tests=self.generate_tests,
            custom_instructions=self.custom_instructions,
        )

        # Write generated files to disk
        if result.success and result.generated_files:
            await self._write_generated_files(result)

        # Print summary
        self._print_summary(result)

        return self._serialize_result(result)

    async def _resolve_image_data(self) -> str:
        """Resolve image data from path, base64, or Figma URL."""
        import base64

        import aiofiles

        # Direct base64 data
        if self.image_data:
            return self.image_data

        # Load from file
        if self.image_path:
            path = Path(self.image_path)
            if not path.exists():
                debug_error(f"Image file not found: {self.image_path}")
                return ""

            async with aiofiles.open(path, "rb") as f:
                data = await f.read()

            # Detect MIME type
            mime_map = {
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".gif": "image/gif",
                ".webp": "image/webp",
                ".svg": "image/svg+xml",
            }
            mime = mime_map.get(path.suffix.lower(), "image/png")
            b64 = base64.b64encode(data).decode("utf-8")
            return f"data:{mime};base64,{b64}"

        # Load from Figma
        if self.figma_url:
            try:
                from src.connectors.figma_connector import FigmaConnector

                connector = FigmaConnector()
                parsed = connector.parse_figma_url(self.figma_url)
                if parsed and parsed.get("node_id"):
                    debug(f"Exporting image from Figma node {parsed['node_id']}...")
                    export = await connector.export_node_image(
                        parsed["file_key"], parsed["node_id"]
                    )
                    if export.image_data:
                        return f"data:image/png;base64,{export.image_data}"
            except Exception as e:
                debug_error(f"Could not fetch Figma image: {e}")

        return ""

    async def _write_generated_files(self, result) -> None:
        """Write generated files to the output directory."""

        import aiofiles

        output_base = Path(self.output_dir)

        print(f"\n📁 Writing {len(result.generated_files)} files:")
        for gf in result.generated_files:
            file_path = output_base / gf.path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
                await f.write(gf.content)
            print(f"  ✅ {gf.path}")

        # Write visual tests
        if result.visual_tests:
            print(f"\n🧪 Writing {len(result.visual_tests)} visual tests:")
            for vt in result.visual_tests:
                test_path = output_base / "tests" / "visual" / f"{vt.name}.spec.ts"
                test_path.parent.mkdir(parents=True, exist_ok=True)
                async with aiofiles.open(test_path, "w", encoding="utf-8") as f:
                    await f.write(vt.test_code)
                print(f"  ✅ tests/visual/{vt.name}.spec.ts")

    def _print_summary(self, result) -> None:
        """Print a pipeline summary."""
        print("\n" + "=" * 60)
        if result.success:
            debug_success("Design-to-Code Pipeline Complete!")
            print(f"  📄 Files generated: {len(result.generated_files)}")
            print(f"  🧪 Visual tests: {len(result.visual_tests)}")
            print(f"  🎨 Design tokens used: {len(result.design_tokens_used)}")
            if result.design_spec:
                print(
                    f"  🧩 Components identified: {len(result.design_spec.components)}"
                )
            if result.figma_sync_status:
                sync = result.figma_sync_status.get("status", "unknown")
                print(f"  🔄 Figma sync: {sync}")
            print(f"  ⏱️  Duration: {result.duration_seconds:.1f}s")
        else:
            debug_error("Pipeline Failed!")
            for error in result.errors:
                print(f"  ❌ {error}")
        print("=" * 60)

    def _serialize_result(self, result) -> dict:
        """Serialize the pipeline result for JSON output."""
        return {
            "success": result.success,
            "phase": result.phase.value,
            "files_generated": len(result.generated_files),
            "visual_tests_generated": len(result.visual_tests),
            "design_tokens_used": len(result.design_tokens_used),
            "components_identified": len(result.design_spec.components)
            if result.design_spec
            else 0,
            "duration_seconds": result.duration_seconds,
            "errors": result.errors,
            "generated_files": [
                {"path": f.path, "language": f.language, "description": f.description}
                for f in result.generated_files
            ],
        }


async def main():
    """CLI entry point for the Design-to-Code runner."""
    parser = argparse.ArgumentParser(
        description="Design-to-Code Pipeline — Convert visual designs to production-ready code"
    )
    parser.add_argument(
        "--project-dir", required=True, help="Path to the project directory"
    )
    parser.add_argument(
        "--image-path", default="", help="Path to the design image file"
    )
    parser.add_argument("--image-data", default="", help="Base64-encoded image data")
    parser.add_argument(
        "--framework",
        default="react",
        choices=["react", "vue", "angular", "svelte", "nextjs", "nuxt"],
        help="Target framework (default: react)",
    )
    parser.add_argument(
        "--source-type",
        default="screenshot",
        choices=["screenshot", "figma", "wireframe", "whiteboard", "photo"],
        help="Type of design source (default: screenshot)",
    )
    parser.add_argument(
        "--design-system-path", default="", help="Path to the project's design system"
    )
    parser.add_argument(
        "--figma-url", default="", help="Figma file/node URL for bidirectional sync"
    )
    parser.add_argument(
        "--no-tests", action="store_true", help="Skip visual test generation"
    )
    parser.add_argument(
        "--instructions", default="", help="Additional instructions for code generation"
    )
    parser.add_argument(
        "--output-dir", default="", help="Output directory (default: project dir)"
    )
    parser.add_argument("--json", action="store_true", help="Output result as JSON")

    args = parser.parse_args()

    runner = DesignToCodeRunner(
        project_dir=args.project_dir,
        image_path=args.image_path,
        image_data=args.image_data,
        framework=args.framework,
        source_type=args.source_type,
        design_system_path=args.design_system_path,
        figma_url=args.figma_url,
        generate_tests=not args.no_tests,
        custom_instructions=args.instructions,
        output_dir=args.output_dir,
    )

    result = await runner.run()

    if args.json:
        print(json.dumps(result, indent=2))

    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    asyncio.run(main())
