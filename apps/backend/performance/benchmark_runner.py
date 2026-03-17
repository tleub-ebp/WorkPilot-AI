"""Benchmark Runner - Runs available benchmarks and measures performance."""
import subprocess
import time
from pathlib import Path
from typing import List, Optional, Tuple

from .models import BenchmarkResult

IGNORE_PATTERNS = {
    "node_modules", ".git", "__pycache__", "dist", "build", ".venv",
}


class BenchmarkRunner:
    """Runs benchmarks for the project and captures timing/memory data."""

    def __init__(self, project_dir: str):
        self.project_dir = Path(project_dir)

    def detect_test_framework(self) -> str:
        """Detect which test framework the project uses."""
        package_json = self.project_dir / "package.json"
        if package_json.exists():
            try:
                import json
                data = json.loads(package_json.read_text(encoding="utf-8"))
                deps = {
                    **data.get("dependencies", {}),
                    **data.get("devDependencies", {}),
                }
                if "vitest" in deps:
                    return "vitest"
                if "jest" in deps:
                    return "jest"
                if "mocha" in deps:
                    return "mocha"
            except Exception:
                pass

        # Check for pytest
        for marker in ["pytest.ini", "setup.cfg", "pyproject.toml"]:
            if (self.project_dir / marker).exists():
                return "pytest"

        requirements = self.project_dir / "requirements.txt"
        if requirements.exists():
            content = requirements.read_text(encoding="utf-8", errors="ignore")
            if "pytest" in content:
                return "pytest"

        return "unknown"

    def run_benchmarks(self, timeout_seconds: int = 60) -> List[BenchmarkResult]:
        """Run available benchmarks and return results."""
        results = []

        # Try build timing
        build_result = self.run_build_timing()
        if build_result:
            results.append(build_result)

        # Try test suite timing
        framework = self.detect_test_framework()
        if framework in ("vitest", "jest"):
            result = self._run_js_tests(framework, timeout_seconds)
            if result:
                results.append(result)
        elif framework == "pytest":
            result = self._run_pytest(timeout_seconds)
            if result:
                results.append(result)

        return results

    def run_python_profiling(self, entry_point: Optional[str] = None) -> Optional[BenchmarkResult]:
        """Profile a Python entry point using cProfile."""
        if not entry_point:
            # Try to find a common entry point
            candidates = ["main.py", "app.py", "run.py", "server.py"]
            for c in candidates:
                if (self.project_dir / c).exists():
                    entry_point = c
                    break

        if not entry_point:
            return None

        try:
            cmd = ["python", "-m", "cProfile", "-s", "cumulative", entry_point]
            duration, output = self._run_command_timed(cmd, str(self.project_dir), timeout=30)
            return BenchmarkResult(
                name="python_profiling",
                duration_ms=duration,
                metadata={"output_preview": output[:500], "entry_point": entry_point},
            )
        except Exception as e:
            return BenchmarkResult(
                name="python_profiling",
                duration_ms=0,
                metadata={"error": str(e)},
            )

    def run_build_timing(self) -> Optional[BenchmarkResult]:
        """Time the build process if a build script is detected."""
        package_json = self.project_dir / "package.json"
        if not package_json.exists():
            return None

        try:
            import json
            data = json.loads(package_json.read_text(encoding="utf-8"))
            scripts = data.get("scripts", {})
            if "build" not in scripts:
                return None

            # Don't actually run a full build — just report the script exists
            return BenchmarkResult(
                name="build_check",
                duration_ms=0,
                metadata={
                    "build_command": scripts["build"],
                    "note": "Build timing not executed to avoid side effects",
                },
            )
        except Exception:
            return None

    def _run_js_tests(self, framework: str, timeout: int) -> Optional[BenchmarkResult]:
        """Run JS test suite and capture timing."""
        cmds = {
            "vitest": ["npx", "vitest", "run", "--reporter=verbose"],
            "jest": ["npx", "jest", "--passWithNoTests"],
        }
        cmd = cmds.get(framework)
        if not cmd:
            return None

        try:
            duration, output = self._run_command_timed(cmd, str(self.project_dir), timeout)
            return BenchmarkResult(
                name=f"{framework}_tests",
                duration_ms=duration,
                metadata={"output_preview": output[-500:]},
            )
        except Exception as e:
            return BenchmarkResult(
                name=f"{framework}_tests",
                duration_ms=0,
                metadata={"error": str(e)},
            )

    def _run_pytest(self, timeout: int) -> Optional[BenchmarkResult]:
        """Run pytest and capture timing."""
        try:
            cmd = ["python", "-m", "pytest", "--tb=no", "-q"]
            duration, output = self._run_command_timed(cmd, str(self.project_dir), timeout)
            return BenchmarkResult(
                name="pytest",
                duration_ms=duration,
                metadata={"output_preview": output[-500:]},
            )
        except Exception as e:
            return BenchmarkResult(
                name="pytest",
                duration_ms=0,
                metadata={"error": str(e)},
            )

    def _run_command_timed(
        self, cmd: List[str], cwd: str, timeout: int
    ) -> Tuple[float, str]:
        """Run a command and return (duration_ms, stdout_output)."""
        start = time.time()
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            duration = (time.time() - start) * 1000
            output = result.stdout + result.stderr
            return duration, output
        except subprocess.TimeoutExpired:
            duration = timeout * 1000
            return duration, "Timed out"
        except FileNotFoundError:
            return 0.0, f"Command not found: {cmd[0]}"
