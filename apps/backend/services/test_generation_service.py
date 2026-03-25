"""
Test Generation Service
======================

Service that runs automatic test generation after builds.

This service integrates with the build pipeline to automatically
generate tests for modified code, ensuring comprehensive test
coverage without manual intervention.

Usage:
    from services.test_generation_service import TestGenerationService

    service = TestGenerationService(project_path)
    result = service.run_post_build_generation(modified_files)
"""

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from agents.test_generator import TestGenerationResult, TestGeneratorAgent

logger = logging.getLogger(__name__)


@dataclass
class PostBuildGenerationResult:
    """Result of post-build test generation."""

    success: bool
    files_processed: int
    files_with_tests: int
    total_tests_generated: int
    generated_files: list[dict[str, Any]]
    errors: list[str]


class TestGenerationService:
    """Service for automatic test generation after builds."""

    __test__ = False  # Exclude from pytest collection

    def __init__(self, project_path: Path):
        """
        Initialize the test generation service.

        Args:
            project_path: Path to the project root
        """
        self.project_path = Path(project_path)
        self.agent = TestGeneratorAgent()

        # Configuration from environment or defaults
        self.enabled = os.getenv("TEST_GENERATION_ENABLED", "true").lower() == "true"
        self.max_tests_per_function = int(os.getenv("MAX_TESTS_PER_FUNCTION", "3"))
        self.skip_existing_tests = (
            os.getenv("SKIP_EXISTING_TESTS", "false").lower() == "true"
        )

    def is_enabled(self) -> bool:
        """Check if test generation is enabled."""
        return self.enabled

    def run_post_build_generation(
        self, modified_files: list[str], project_path: str | None = None
    ) -> PostBuildGenerationResult:
        """
        Run automatic test generation for modified files.

        This is the main post-build hook that analyzes modified files
        and generates tests for any uncovered functions.

        Args:
            modified_files: List of modified file paths
            project_path: Override project path (for testing)

        Returns:
            PostBuildGenerationResult with generation statistics
        """
        if not self.is_enabled():
            logger.info("[TestGenerationService] Test generation is disabled")
            return PostBuildGenerationResult(
                success=True,
                files_processed=0,
                files_with_tests=0,
                total_tests_generated=0,
                generated_files=[],
                errors=[],
            )

        logger.info(
            f"[TestGenerationService] Starting post-build test generation "
            f"for {len(modified_files)} modified files"
        )

        project_root = Path(project_path) if project_path else self.project_path
        results = []
        errors = []

        for file_path in modified_files:
            try:
                # Process only Python files
                if not file_path.endswith(".py"):
                    continue

                # Skip test files themselves
                if "test_" in file_path or "/tests/" in file_path:
                    logger.debug(
                        f"[TestGenerationService] Skipping test file: {file_path}"
                    )
                    continue

                # Check if file exists
                full_path = project_root / file_path
                if not full_path.exists():
                    logger.warning(
                        f"[TestGenerationService] File not found: {file_path}"
                    )
                    continue

                # Generate tests for this file
                result = self._generate_tests_for_file(full_path, file_path)
                if result:
                    results.append(result)

            except Exception as e:
                error_msg = f"Error processing {file_path}: {str(e)}"
                logger.error(f"[TestGenerationService] {error_msg}")
                errors.append(error_msg)

        # Compile final result
        total_tests = sum(r["tests_generated"] for r in results)

        logger.info(
            f"[TestGenerationService] Post-build generation complete: "
            f"{len(results)} files with {total_tests} tests generated"
        )

        return PostBuildGenerationResult(
            success=len(errors) == 0,
            files_processed=len(modified_files),
            files_with_tests=len(results),
            total_tests_generated=total_tests,
            generated_files=results,
            errors=errors,
        )

    def _generate_tests_for_file(
        self, full_path: Path, relative_path: str
    ) -> dict[str, Any] | None:
        """
        Generate tests for a single file.

        Args:
            full_path: Full path to the file
            relative_path: Relative path from project root

        Returns:
            Dict with generation result or None if no tests generated
        """
        logger.debug(f"[TestGenerationService] Processing file: {relative_path}")

        # Find existing test file
        test_file_path = self.agent._compute_test_file_path(str(full_path))
        existing_test_path = test_file_path if Path(test_file_path).exists() else None

        # Skip if existing tests and configured to skip
        if existing_test_path and self.skip_existing_tests:
            logger.debug(
                f"[TestGenerationService] Skipping file with existing tests: {relative_path}"
            )
            return None

        # Generate unit tests
        try:
            result: TestGenerationResult = self.agent.generate_unit_tests(
                str(full_path), existing_test_path, self.max_tests_per_function
            )

            if result.tests_generated == 0:
                logger.debug(
                    f"[TestGenerationService] No tests generated for: {relative_path}"
                )
                return None

            # Write test file to disk
            self._write_test_file(result.test_file_path, result.test_file_content)

            logger.info(
                f"[TestGenerationService] Generated {result.tests_generated} tests "
                f"for {relative_path} -> {result.test_file_path}"
            )

            return {
                "source_file": relative_path,
                "tests_generated": result.tests_generated,
                "test_file_path": result.test_file_path,
                "test_file_content": result.test_file_content,
                "functions_analyzed": result.functions_analyzed,
                "coverage_gaps": len(result.coverage_gaps),
            }

        except Exception as e:
            logger.error(
                f"[TestGenerationService] Failed to generate tests for {relative_path}: {e}"
            )
            raise

    def _write_test_file(self, test_file_path: str, content: str) -> None:
        """
        Write generated test file to disk.

        Args:
            test_file_path: Path where to write the test file
            content: Test file content
        """
        # Convert relative path to absolute
        if not os.path.isabs(test_file_path):
            test_file_path = self.project_path / test_file_path

        test_path = Path(test_file_path)

        # Create directory if it doesn't exist
        test_path.parent.mkdir(parents=True, exist_ok=True)

        # Write the file
        with open(test_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.debug(f"[TestGenerationService] Wrote test file: {test_path}")

    def analyze_coverage_only(self, file_path: str) -> dict[str, Any]:
        """
        Analyze test coverage without generating tests.

        Useful for reporting and analytics.

        Args:
            file_path: Path to the source file

        Returns:
            Dict with coverage analysis results
        """
        try:
            full_path = self.project_path / file_path
            if not full_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")

            # Find existing test file
            test_file_path = self.agent._compute_test_file_path(str(full_path))
            existing_test_path = (
                test_file_path if Path(test_file_path).exists() else None
            )

            # Analyze coverage gaps
            gaps = self.agent.analyze_coverage(str(full_path), existing_test_path)

            return {
                "file_path": file_path,
                "existing_test_path": existing_test_path,
                "coverage_gaps": len(gaps),
                "gaps": [
                    {
                        "function": gap.function.full_name,
                        "priority": gap.priority,
                        "reason": gap.reason,
                        "suggested_tests": gap.suggested_test_count,
                    }
                    for gap in gaps
                ],
                "high_priority_gaps": len([g for g in gaps if g.priority == "high"]),
                "medium_priority_gaps": len(
                    [g for g in gaps if g.priority == "medium"]
                ),
                "low_priority_gaps": len([g for g in gaps if g.priority == "low"]),
            }

        except Exception as e:
            logger.error(
                f"[TestGenerationService] Coverage analysis failed for {file_path}: {e}"
            )
            raise


# =============================================================================
# POST-BUILD HOOK INTEGRATION
# =============================================================================


def run_post_build_hook(project_path: str, modified_files: list[str]) -> dict[str, Any]:
    """
    Post-build hook for integration with build pipeline.

    This function can be called from build systems, CI/CD pipelines,
    or the task completion service.

    Args:
        project_path: Path to the project root
        modified_files: List of modified files in the build

    Returns:
        Dict with hook execution results
    """
    logger.info("[TestGenerationService] Running post-build test generation hook")

    try:
        service = TestGenerationService(Path(project_path))
        result = service.run_post_build_generation(modified_files)

        return {
            "success": result.success,
            "files_processed": result.files_processed,
            "files_with_tests": result.files_with_tests,
            "total_tests_generated": result.total_tests_generated,
            "generated_files": result.generated_files,
            "errors": result.errors,
            "message": f"Generated {result.total_tests_generated} tests for {result.files_with_tests} files",
        }

    except Exception as e:
        logger.error(f"[TestGenerationService] Post-build hook failed: {e}")
        return {
            "success": False,
            "files_processed": 0,
            "files_with_tests": 0,
            "total_tests_generated": 0,
            "generated_files": [],
            "errors": [str(e)],
            "message": f"Post-build test generation failed: {str(e)}",
        }
