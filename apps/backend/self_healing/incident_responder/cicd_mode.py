"""
CI/CD Mode - Self-Healing Codebase
====================================

Detects test regressions after git push / CI pipeline failures,
analyzes the diff, generates a fix in an isolated worktree,
runs QA validation, and opens a correction PR automatically.

Flow:
1. on_test_failure() triggered by git hook or CI webhook
2. Runs git diff to identify changed files
3. Launches CI/CD analyzer agent with diff + test failures
4. Creates isolated worktree, applies fix
5. Runs QA pipeline in worktree
6. If QA passes -> creates PR with auto-heal label
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Any, Optional

from .models import (
    CICDIncidentData,
    HealingOperation,
    HealingStatus,
    Incident,
    IncidentMode,
    IncidentSeverity,
    IncidentSource,
)

logger = logging.getLogger(__name__)


class CICDMode:
    """CI/CD regression detection and auto-fix mode."""

    def __init__(self, project_dir: str | Path):
        self.project_dir = Path(project_dir)

    async def on_test_failure(
        self,
        commit_sha: str,
        branch: str,
        test_output: str,
        failing_tests: list[str] | None = None,
        ci_log_url: str | None = None,
        pipeline_id: str | None = None,
    ) -> Incident:
        """Handle a test failure event from CI/CD.

        Creates an incident and prepares it for the healing pipeline.

        Args:
            commit_sha: The commit that caused the failure.
            branch: The branch where the failure occurred.
            test_output: Raw test runner output.
            failing_tests: List of specific failing test names.
            ci_log_url: URL to the CI pipeline logs.
            pipeline_id: CI pipeline identifier.

        Returns:
            Created Incident ready for healing.
        """
        # Get the diff for the failing commit
        diff_summary = self._get_commit_diff(commit_sha)

        # Parse failing tests from output if not provided
        if not failing_tests:
            failing_tests = self._parse_failing_tests(test_output)

        # Determine severity based on failure count
        if len(failing_tests) > 10:
            severity = IncidentSeverity.CRITICAL
        elif len(failing_tests) > 3:
            severity = IncidentSeverity.HIGH
        else:
            severity = IncidentSeverity.MEDIUM

        # Build incident data
        cicd_data = CICDIncidentData(
            commit_sha=commit_sha,
            branch=branch,
            failing_tests=failing_tests,
            diff_summary=diff_summary,
            ci_log_url=ci_log_url,
            pipeline_id=pipeline_id,
            test_output=test_output,
        )

        incident = Incident(
            mode=IncidentMode.CICD,
            source=IncidentSource.CI_FAILURE if pipeline_id else IncidentSource.GIT_PUSH,
            severity=severity,
            title=f"Test regression: {len(failing_tests)} test(s) failing after {commit_sha[:7]}",
            description=f"Tests broke after commit {commit_sha[:7]} on branch {branch}. "
            f"{len(failing_tests)} test(s) affected.",
            status=HealingStatus.PENDING,
            source_data=cicd_data.to_dict(),
            regression_commit=commit_sha,
        )

        logger.info(
            f"CI/CD incident created: {incident.title} "
            f"(severity={severity.value}, tests={len(failing_tests)})"
        )
        return incident

    def build_agent_prompt(self, incident: Incident) -> str:
        """Build the prompt for the CI/CD analyzer agent.

        Injects the diff, test failures, and commit context into the prompt template.
        """
        data = incident.source_data
        prompt_path = Path(__file__).parent.parent.parent / "prompts" / "incident_cicd_analyzer.md"

        try:
            template = prompt_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            template = self._fallback_prompt()

        # Replace template variables
        replacements = {
            "{{DIFF}}": data.get("diff_summary", "No diff available"),
            "{{TEST_FAILURES}}": data.get("test_output", "No test output"),
            "{{COMMIT_SHA}}": data.get("commit_sha", "unknown"),
            "{{COMMIT_MESSAGE}}": self._get_commit_message(data.get("commit_sha", "")),
            "{{BRANCH}}": data.get("branch", "unknown"),
            "{{FAILING_TESTS}}": "\n".join(
                f"- {t}" for t in data.get("failing_tests", [])
            ),
        }

        for key, value in replacements.items():
            template = template.replace(key, value)

        return template

    async def run_tests(self, working_dir: Path | None = None) -> tuple[bool, str, list[str]]:
        """Run the project test suite and return results.

        Returns:
            Tuple of (all_passed, output, failing_test_names)
        """
        cwd = str(working_dir or self.project_dir)
        test_cmd = self._detect_test_command()

        try:
            result = subprocess.run(
                test_cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=300,
                shell=True,
            )
            output = result.stdout + "\n" + result.stderr
            passed = result.returncode == 0
            failing = self._parse_failing_tests(output) if not passed else []
            return passed, output, failing
        except subprocess.TimeoutExpired:
            return False, "Test execution timed out after 300s", ["TIMEOUT"]
        except (FileNotFoundError, OSError) as e:
            return False, f"Failed to run tests: {e}", ["EXECUTION_ERROR"]

    def _detect_test_command(self) -> str:
        """Detect the appropriate test command for the project."""
        project = self.project_dir

        # Python
        if (project / "pytest.ini").exists() or (project / "pyproject.toml").exists():
            if (project / ".venv").exists():
                return ".venv/bin/pytest -v --tb=short 2>&1"
            return "pytest -v --tb=short 2>&1"

        # Node.js
        if (project / "package.json").exists():
            import json
            try:
                pkg = json.loads((project / "package.json").read_text())
                scripts = pkg.get("scripts", {})
                if "test" in scripts:
                    if (project / "pnpm-lock.yaml").exists():
                        return "pnpm test 2>&1"
                    elif (project / "yarn.lock").exists():
                        return "yarn test 2>&1"
                    return "npm test 2>&1"
            except (json.JSONDecodeError, OSError):
                pass

        # Go
        if (project / "go.mod").exists():
            return "go test ./... 2>&1"

        # Rust
        if (project / "Cargo.toml").exists():
            return "cargo test 2>&1"

        return "echo 'No test command detected'"

    def _get_commit_diff(self, commit_sha: str) -> str:
        """Get the diff for a specific commit."""
        try:
            result = subprocess.run(
                ["git", "diff", f"{commit_sha}~1..{commit_sha}", "--stat"],
                cwd=str(self.project_dir),
                capture_output=True,
                text=True,
                timeout=30,
            )
            stat = result.stdout

            result = subprocess.run(
                ["git", "diff", f"{commit_sha}~1..{commit_sha}"],
                cwd=str(self.project_dir),
                capture_output=True,
                text=True,
                timeout=30,
            )
            # Limit diff size to avoid context overflow
            diff = result.stdout
            if len(diff) > 50000:
                diff = diff[:50000] + "\n... [diff truncated at 50KB]"

            return f"--- Stats ---\n{stat}\n--- Full Diff ---\n{diff}"
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
            logger.warning(f"Failed to get commit diff: {e}")
            return f"Failed to get diff for {commit_sha}: {e}"

    def _get_commit_message(self, commit_sha: str) -> str:
        """Get the commit message for a specific commit."""
        if not commit_sha:
            return ""
        try:
            result = subprocess.run(
                ["git", "log", "-1", "--format=%B", commit_sha],
                cwd=str(self.project_dir),
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return ""

    def _parse_failing_tests(self, output: str) -> list[str]:
        """Parse failing test names from test runner output."""
        failing: list[str] = []

        for line in output.splitlines():
            line_stripped = line.strip()

            # pytest: FAILED tests/test_foo.py::test_bar
            if line_stripped.startswith("FAILED "):
                failing.append(line_stripped[7:].split(" ")[0])

            # jest/vitest: FAIL src/foo.test.ts
            elif line_stripped.startswith("FAIL "):
                failing.append(line_stripped[5:].strip())

            # go: --- FAIL: TestFoo (0.00s)
            elif line_stripped.startswith("--- FAIL:"):
                test_name = line_stripped[9:].split("(")[0].strip()
                failing.append(test_name)

            # cargo: test result: FAILED. N passed; M failed
            elif "test " in line_stripped and "... FAILED" in line_stripped:
                test_name = line_stripped.split("test ")[1].split(" ...")[0]
                failing.append(test_name)

        return failing

    def _fallback_prompt(self) -> str:
        return """## YOUR ROLE - CI/CD INCIDENT ANALYZER

You analyze test regressions and generate fixes.

## CONTEXT
- Commit: {{COMMIT_SHA}}
- Branch: {{BRANCH}}
- Commit message: {{COMMIT_MESSAGE}}

## DIFF
{{DIFF}}

## FAILING TESTS
{{FAILING_TESTS}}

## TEST OUTPUT
{{TEST_FAILURES}}

## INSTRUCTIONS
1. Identify which changes in the diff caused the test failures
2. Generate the minimal fix to make all tests pass
3. Do not change the tests unless they are incorrect
4. Commit with message: "fix: auto-heal regression from {{COMMIT_SHA}}"
"""
