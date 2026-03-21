"""Test Generator Agent — LLM-powered test generation for any language.

Uses Claude to analyse source files and generate comprehensive test suites,
detecting the project's language and test framework automatically from
package.json, pyproject.toml, .csproj, pom.xml, etc.

Supported languages: Python, TypeScript, JavaScript, C#, Java, Go, Ruby, etc.

Example:
    >>> agent = TestGeneratorAgent()
    >>> gaps = agent.analyze_coverage("src/utils/calculator.ts", project_path="/my/project")
    >>> result = agent.generate_unit_tests("src/utils/calculator.ts", project_path="/my/project")
"""

import asyncio
import json
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ── Data models ─────────────────────────────────────────────────────


@dataclass
class FunctionInfo:
    """Information about a function/method extracted from source code."""

    name: str
    module: str
    class_name: str | None = None
    args: list[str] = field(default_factory=list)
    return_type: str | None = None
    docstring: str = ""
    line_number: int = 0
    is_async: bool = False
    decorators: list[str] = field(default_factory=list)
    complexity: int = 1

    @property
    def full_name(self) -> str:
        if self.class_name:
            return f"{self.class_name}.{self.name}"
        return self.name

    @property
    def is_private(self) -> bool:
        return self.name.startswith("_") and not self.name.startswith("__")

    @property
    def is_dunder(self) -> bool:
        return self.name.startswith("__") and self.name.endswith("__")


@dataclass
class CoverageGap:
    """Represents a gap in test coverage."""

    function: FunctionInfo
    priority: str = "medium"
    reason: str = ""
    suggested_test_count: int = 1


@dataclass
class GeneratedTest:
    """A generated test case."""

    test_name: str
    test_code: str
    target_function: str
    test_type: str = "unit"
    description: str = ""
    imports: list[str] = field(default_factory=list)
    fixtures: list[str] = field(default_factory=list)


@dataclass
class TestGenerationResult:
    """Result of a test generation run."""

    source_file: str
    functions_analyzed: int = 0
    tests_generated: int = 0
    coverage_gaps: list[CoverageGap] = field(default_factory=list)
    generated_tests: list[GeneratedTest] = field(default_factory=list)
    test_file_content: str = ""
    test_file_path: str = ""


# ── Project analyser ────────────────────────────────────────────────


class ProjectAnalyzer:
    """Detects project language and test framework from config files."""

    EXTENSION_TO_LANGUAGE: dict[str, str] = {
        ".py": "python",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".js": "javascript",
        ".jsx": "javascript",
        ".mjs": "javascript",
        ".cjs": "javascript",
        ".cs": "csharp",
        ".java": "java",
        ".rb": "ruby",
        ".go": "go",
        ".rs": "rust",
        ".kt": "kotlin",
        ".kts": "kotlin",
        ".swift": "swift",
        ".php": "php",
        ".vue": "javascript",
        ".svelte": "javascript",
    }

    def detect(
        self,
        file_path: str,
        project_path: str | None = None,
    ) -> dict[str, str]:
        """Detect language and test framework for a source file.

        Args:
            file_path: Path to the source file.
            project_path: Optional explicit project root. When None, walks up
                the directory tree looking for config file markers.

        Returns:
            Dict with keys ``language``, ``test_framework``, ``project_root``,
            ``details``.
        """
        ext = Path(file_path).suffix.lower()
        language = self.EXTENSION_TO_LANGUAGE.get(ext, "unknown")

        root = project_path or self._find_project_root(file_path)

        if root:
            framework, details = self._scan_framework(root, language)
        else:
            framework = self._default_framework(language)
            details = ""

        return {
            "language": language,
            "test_framework": framework,
            "project_root": root or str(Path(file_path).parent),
            "details": details,
        }

    def _find_project_root(self, file_path: str) -> str | None:
        """Walk up from the file to find the project root."""
        markers = [
            "package.json",
            "pyproject.toml",
            "requirements.txt",
            "pom.xml",
            "build.gradle",
            "build.gradle.kts",
            "Cargo.toml",
            "go.mod",
            ".git",
        ]
        current = Path(file_path).resolve().parent
        for _ in range(7):
            for marker in markers:
                if (current / marker).exists():
                    return str(current)
            parent = current.parent
            if parent == current:
                break
            current = parent
        return None

    def _scan_framework(
        self, project_root: str, language: str
    ) -> tuple[str, str]:
        """Scan config files to detect the test framework in use."""
        root = Path(project_root)
        for detector in (
            self._detect_js_framework,
            self._detect_python_framework,
            self._detect_java_framework,
            self._detect_csharp_framework,
            self._detect_ruby_framework,
        ):
            result = detector(root, language)
            if result:
                return result
        return self._default_framework(language), ""

    def _detect_js_framework(
        self, root: Path, language: str
    ) -> tuple[str, str] | None:
        pkg_json = root / "package.json"
        if not pkg_json.exists():
            return None
        try:
            pkg = json.loads(pkg_json.read_text(encoding="utf-8"))
            deps: dict[str, str] = {
                **pkg.get("dependencies", {}),
                **pkg.get("devDependencies", {}),
            }
            for fw, dep in [
                ("vitest", "vitest"),
                ("jest", "jest"),
                ("mocha", "mocha"),
                ("jasmine", "jasmine"),
                ("playwright", "@playwright/test"),
                ("cypress", "cypress"),
            ]:
                if dep in deps:
                    return fw, f"{dep} {deps[dep]}"
            if language in ("typescript", "javascript"):
                return "jest", "(no test framework detected in package.json)"
        except Exception:
            pass
        return None

    def _detect_python_framework(
        self, root: Path, language: str  # noqa: ARG002
    ) -> tuple[str, str] | None:
        for fname in ("requirements.txt", "requirements-dev.txt", "requirements-test.txt"):
            req_path = root / fname
            if req_path.exists():
                try:
                    content = req_path.read_text(encoding="utf-8").lower()
                    if "pytest" in content:
                        return "pytest", f"pytest ({fname})"
                    if "nose2" in content:
                        return "nose2", f"nose2 ({fname})"
                except Exception:
                    pass
        pyproject = root / "pyproject.toml"
        if pyproject.exists():
            try:
                content = pyproject.read_text(encoding="utf-8").lower()
                if "pytest" in content:
                    return "pytest", "pytest (pyproject.toml)"
                if "unittest" in content:
                    return "unittest", "unittest (pyproject.toml)"
            except Exception:
                pass
        return None

    def _detect_java_framework(
        self, root: Path, language: str  # noqa: ARG002
    ) -> tuple[str, str] | None:
        pom = root / "pom.xml"
        if pom.exists():
            try:
                content = pom.read_text(encoding="utf-8")
                lower = content.lower()
                if "junit" in lower:
                    if "junit-jupiter" in content or "org.junit.jupiter" in content:
                        return "junit5", "JUnit 5 (pom.xml)"
                    return "junit4", "JUnit 4 (pom.xml)"
                if "testng" in lower:
                    return "testng", "TestNG (pom.xml)"
            except Exception:
                pass
        for gradle_file in ("build.gradle", "build.gradle.kts"):
            gradle = root / gradle_file
            if gradle.exists():
                try:
                    if "junit" in gradle.read_text(encoding="utf-8").lower():
                        return "junit5", f"JUnit ({gradle_file})"
                except Exception:
                    pass
        return None

    def _detect_csharp_framework(
        self, root: Path, language: str  # noqa: ARG002
    ) -> tuple[str, str] | None:
        try:
            for entry in root.iterdir():
                if entry.is_file() and entry.suffix == ".csproj":
                    try:
                        content = entry.read_text(encoding="utf-8")
                        if "NUnit" in content:
                            return "nunit", f"NUnit ({entry.name})"
                        if "xunit" in content.lower():
                            return "xunit", f"xUnit ({entry.name})"
                        if "MSTest" in content:
                            return "mstest", f"MSTest ({entry.name})"
                    except Exception:
                        pass
        except Exception:
            pass
        return None

    def _detect_ruby_framework(
        self, root: Path, language: str  # noqa: ARG002
    ) -> tuple[str, str] | None:
        gemfile = root / "Gemfile"
        if not gemfile.exists():
            return None
        try:
            content = gemfile.read_text(encoding="utf-8").lower()
            if "rspec" in content:
                return "rspec", "RSpec (Gemfile)"
            if "minitest" in content:
                return "minitest", "Minitest (Gemfile)"
        except Exception:
            pass
        return None

    def default_framework(self, language: str) -> str:
        """Return the conventional default test framework for a language."""
        return self._default_framework(language)

    def _default_framework(self, language: str) -> str:
        defaults: dict[str, str] = {
            "python": "pytest",
            "typescript": "jest",
            "javascript": "jest",
            "csharp": "xunit",
            "java": "junit5",
            "go": "testing",
            "rust": "built-in",
            "ruby": "rspec",
            "kotlin": "junit5",
            "swift": "xctest",
            "php": "phpunit",
        }
        return defaults.get(language, "unknown")


# ── Test generator agent ────────────────────────────────────────────


class TestGeneratorAgent:
    """LLM-powered agent that generates tests for any programming language.

    Detects the project's language and test framework automatically, then
    uses Claude to generate real, production-quality test code — not stubs.

    Example:
        >>> agent = TestGeneratorAgent()
        >>> result = agent.generate_unit_tests(
        ...     "src/utils/calculator.ts",
        ...     project_path="/path/to/project",
        ... )
        >>> print(result.test_file_content)
    """

    def __init__(self, llm_provider: Any = None) -> None:
        self._project_analyzer = ProjectAnalyzer()
        # llm_provider kept for backward compatibility but not used

    # ── Public API ───────────────────────────────────────────────────

    def analyze_coverage(
        self,
        file_path: str,
        existing_test_path: str | None = None,
        project_path: str | None = None,
    ) -> list[CoverageGap]:
        """Identify functions/methods in *file_path* that lack test coverage."""
        return asyncio.run(
            self._analyze_coverage_async(file_path, existing_test_path, project_path)
        )

    def generate_unit_tests(
        self,
        file_path: str,
        existing_test_path: str | None = None,
        max_tests_per_function: int = 3,
        project_path: str | None = None,
    ) -> TestGenerationResult:
        """Generate a complete unit test file for *file_path*."""
        return asyncio.run(
            self._generate_unit_async(
                file_path, existing_test_path, max_tests_per_function, project_path
            )
        )

    def generate_tests_from_user_story(
        self,
        user_story: str,
        target_module: str,
        project_path: str | None = None,
    ) -> TestGenerationResult:
        """Generate E2E tests from a user story."""
        return asyncio.run(
            self._generate_e2e_async(user_story, target_module, project_path)
        )

    def generate_tdd_tests(
        self,
        spec: dict[str, Any],
        project_path: str | None = None,
    ) -> TestGenerationResult:
        """Generate failing tests (TDD red phase) based on a spec."""
        return asyncio.run(self._generate_tdd_async(spec, project_path))

    # ── Async implementations ────────────────────────────────────────

    async def _analyze_coverage_async(
        self, file_path: str, existing_test_path: str | None, project_path: str | None
    ) -> list[CoverageGap]:
        framework_info = self._project_analyzer.detect(file_path, project_path)
        source = self._read_file(file_path)
        if not source:
            raise FileNotFoundError(f"Cannot read source file: {file_path}")

        existing = (
            self._read_file(existing_test_path)
            if existing_test_path and os.path.exists(existing_test_path)
            else ""
        )

        print(
            f"Detected {framework_info['language']} project with {framework_info['test_framework']}",
            flush=True,
        )
        print("Asking Claude to analyse coverage gaps...", flush=True)

        prompt = self._analyze_coverage_prompt(source, file_path, framework_info, existing)
        response = await self._call_claude(prompt)
        return self._parse_gaps(response, file_path)

    async def _generate_unit_async(
        self,
        file_path: str,
        existing_test_path: str | None,
        max_tests_per_function: int,
        project_path: str | None,
    ) -> TestGenerationResult:
        framework_info = self._project_analyzer.detect(file_path, project_path)
        source = self._read_file(file_path)
        if not source:
            raise FileNotFoundError(f"Cannot read source file: {file_path}")

        existing = (
            self._read_file(existing_test_path)
            if existing_test_path and os.path.exists(existing_test_path)
            else ""
        )

        print(
            f"Detected {framework_info['language']} + {framework_info['test_framework']}",
            flush=True,
        )
        print("Asking Claude to generate unit tests...", flush=True)

        prompt = self._generate_unit_prompt(
            source, file_path, framework_info, existing, max_tests_per_function
        )
        response = await self._call_claude(prompt)
        return self._parse_generation_result(response, file_path, "unit", framework_info)

    async def _generate_e2e_async(
        self, user_story: str, target_module: str, project_path: str | None
    ) -> TestGenerationResult:
        # Try to detect framework from target module; fall back to project_path
        if os.path.exists(target_module):
            framework_info = self._project_analyzer.detect(target_module, project_path)
        elif project_path:
            framework_info = self._project_analyzer.detect(
                os.path.join(project_path, "dummy.ts"), project_path
            )
        else:
            framework_info = {
                "language": "unknown",
                "test_framework": "jest",
                "project_root": "",
                "details": "",
            }

        print(
            f"Detected {framework_info['language']} + {framework_info['test_framework']}",
            flush=True,
        )
        print("Asking Claude to generate E2E tests...", flush=True)

        prompt = self._generate_e2e_prompt(user_story, target_module, framework_info)
        response = await self._call_claude(prompt)
        return self._parse_generation_result(response, target_module, "e2e", framework_info)

    async def _generate_tdd_async(
        self, spec: dict[str, Any], project_path: str | None
    ) -> TestGenerationResult:
        language = spec.get("language", "python")

        # Detect framework from project if possible
        framework = self._project_analyzer.default_framework(language)
        if project_path:
            # Build a dummy file path with the right extension to trigger detection
            ext_map = {
                "typescript": ".ts",
                "javascript": ".js",
                "python": ".py",
                "csharp": ".cs",
                "java": ".java",
                "ruby": ".rb",
                "go": ".go",
                "kotlin": ".kt",
                "rust": ".rs",
            }
            ext = ext_map.get(language, f".{language[:2]}")
            dummy_path = os.path.join(project_path, f"dummy{ext}")
            detected = self._project_analyzer.detect(dummy_path, project_path)
            framework = detected.get("test_framework", framework)

        framework_info = {
            "language": language,
            "test_framework": framework,
            "project_root": project_path or "",
            "details": "",
        }

        print(
            f"Generating TDD tests for {language} ({framework})",
            flush=True,
        )
        print("Asking Claude to generate failing tests (TDD red phase)...", flush=True)

        prompt = self._generate_tdd_prompt(spec, framework_info)
        response = await self._call_claude(prompt)
        slug = re.sub(r"[^a-z0-9_]", "_", spec.get("snippet_type", "feature").lower())
        return self._parse_generation_result(response, f"tdd_{slug}", "unit", framework_info)

    # ── Claude call ──────────────────────────────────────────────────

    async def _call_claude(self, prompt: str) -> str:
        """Call Claude via the Agent SDK and return the text response."""
        from core.auth import ensure_claude_code_oauth_token
        from core.model_config import get_utility_model_config
        from core.simple_client import create_simple_client

        ensure_claude_code_oauth_token()
        model, thinking_budget = get_utility_model_config(
            default_model="claude-sonnet-4-6"
        )

        client = create_simple_client(
            agent_type="batch_analysis",
            model=model,
            max_thinking_tokens=thinking_budget,
        )

        response_text = ""
        try:
            async with client:
                await client.query(prompt)
                async for msg in client.receive_response():
                    if (
                        type(msg).__name__ == "AssistantMessage"
                        and hasattr(msg, "content")
                    ):
                        for block in msg.content:
                            if hasattr(block, "text"):
                                response_text += block.text
        except Exception as exc:
            logger.error("Claude call failed: %s", exc)
            raise

        return response_text

    # ── Prompts ──────────────────────────────────────────────────────

    def _analyze_coverage_prompt(
        self,
        source: str,
        file_path: str,
        framework_info: dict[str, str],
        existing: str,
    ) -> str:
        language = framework_info["language"]
        framework = framework_info["test_framework"]
        existing_section = (
            f"\n\nExisting test file (exclude already-tested functions from gaps):\n```\n{existing}\n```"
            if existing
            else ""
        )
        return f"""Analyse this {language} source file and identify which functions / methods / components lack test coverage.

Source file: {file_path}
Test framework used in this project: {framework}

Source code:
```{language}
{source}
```{existing_section}

Return ONLY a raw JSON object (no markdown, no explanation) matching this schema:
{{
  "functions_analyzed": <integer>,
  "gaps": [
    {{
      "name": "<function or method name>",
      "full_name": "<ClassName.method or bare function name>",
      "class_name": "<class name or null>",
      "line_number": <integer>,
      "priority": "<high | medium | low>",
      "reason": "<one sentence explaining why it needs tests>",
      "suggested_test_count": <integer>
    }}
  ]
}}

Priority rules:
- high  → public API / business logic / multiple branches / external I/O
- medium → helper functions, utility methods
- low   → trivial getters / setters, private helpers

Skip dunder / magic methods except __init__ when it has non-trivial logic.
Only include items NOT already covered by the existing test file."""

    def _generate_unit_prompt(
        self,
        source: str,
        file_path: str,
        framework_info: dict[str, str],
        existing: str,
        max_tests_per_function: int,
    ) -> str:
        language = framework_info["language"]
        framework = framework_info["test_framework"]
        existing_section = (
            f"\n\nExisting tests (extend, avoid duplicates):\n```\n{existing}\n```"
            if existing
            else ""
        )
        stem = Path(file_path).stem
        # Convention hints per language
        path_convention = {
            "python": f"tests/test_{stem}.py",
            "typescript": f"src/__tests__/{stem}.test.ts",
            "javascript": f"src/__tests__/{stem}.test.js",
            "csharp": f"{stem}Tests.cs",
            "java": f"{stem}Test.java",
            "go": f"{stem}_test.go",
            "ruby": f"spec/{stem}_spec.rb",
            "kotlin": f"{stem}Test.kt",
        }.get(language, f"tests/{stem}_test")

        return f"""Generate a complete, production-quality test file for this {language} source file.

Source file: {file_path}
Test framework: {framework}
Max tests per function: {max_tests_per_function}

Source code:
```{language}
{source}
```{existing_section}

Requirements:
1. Use {framework} syntax, imports, and conventions exactly as they appear in real projects.
2. Write REAL, MEANINGFUL tests — no stubs, no TODOs, no "pass".
3. Cover: happy path, edge cases, error handling, boundary values.
4. Mock / stub external dependencies (I/O, network, database) appropriately.
5. Generate up to {max_tests_per_function} tests per function.
6. Include all necessary imports at the top of the file.

Return ONLY a raw JSON object (no markdown, no explanation) matching this schema:
{{
  "test_file_content": "<complete test file as a single escaped string>",
  "test_file_path": "{path_convention}",
  "tests_generated": <integer>,
  "functions_analyzed": <integer>,
  "generated_tests": [
    {{
      "test_name": "<test name>",
      "description": "<one sentence: what this test verifies>"
    }}
  ]
}}"""

    def _generate_e2e_prompt(
        self,
        user_story: str,
        target_module: str,
        framework_info: dict[str, str],
    ) -> str:
        language = framework_info["language"]
        framework = framework_info["test_framework"]
        stem = re.sub(r"[^a-z0-9_]", "_", Path(target_module).stem.lower())

        return f"""Generate E2E / acceptance tests that verify the following user story end-to-end.

User story:
{user_story}

Target module/file: {target_module}
Test framework: {framework}
Language: {language}

Requirements:
1. Map each acceptance criterion to one or more test scenarios.
2. Use Given / When / Then structure in test descriptions.
3. Use {framework} syntax and imports.
4. Write realistic assertions, not just "expect(true).toBe(true)".

Return ONLY a raw JSON object (no markdown) matching this schema:
{{
  "test_file_content": "<complete test file as a single escaped string>",
  "test_file_path": "e2e/test_{stem}.{language == 'typescript' and 'ts' or language == 'python' and 'py' or 'js'}",
  "tests_generated": <integer>,
  "functions_analyzed": 0,
  "generated_tests": [
    {{
      "test_name": "<scenario name>",
      "description": "<user story acceptance criterion covered>"
    }}
  ]
}}"""

    def _generate_tdd_prompt(
        self,
        spec: dict[str, Any],
        framework_info: dict[str, str],
    ) -> str:
        language = framework_info["language"]
        framework = framework_info["test_framework"]
        description = spec.get("description", "")
        snippet_type = spec.get("snippet_type", "function")
        slug = re.sub(r"[^a-z0-9_]", "_", description[:40].lower().strip())

        return f"""Generate failing tests for not-yet-implemented {language} code (TDD red phase).

What needs to be implemented:
{description}

Snippet type: {snippet_type}
Language: {language}
Test framework: {framework}

Requirements:
1. Tests MUST FAIL until the implementation exists — this is the TDD red phase.
2. DO NOT implement the function/class — only write tests.
3. Each test precisely documents one expected behaviour.
4. Cover: normal inputs, boundary values, invalid inputs / error conditions.
5. Use descriptive test names that serve as a living specification.
6. Import the function/class from a logical module path even though it doesn't exist yet.

Return ONLY a raw JSON object (no markdown) matching this schema:
{{
  "test_file_content": "<complete test file as a single escaped string>",
  "test_file_path": "tests/test_{slug}.{language == 'python' and 'py' or language in ('typescript',) and 'ts' or 'js'}",
  "tests_generated": <integer>,
  "functions_analyzed": 0,
  "generated_tests": [
    {{
      "test_name": "<test name>",
      "description": "<behaviour specified by this test>"
    }}
  ]
}}"""

    # ── Response parsing ─────────────────────────────────────────────

    def _parse_gaps(self, response: str, file_path: str) -> list[CoverageGap]:
        data = self._extract_json(response)
        gaps: list[CoverageGap] = []
        for g in data.get("gaps", []):
            func = FunctionInfo(
                name=g.get("name", "unknown"),
                module=file_path,
                class_name=g.get("class_name"),
                line_number=g.get("line_number", 0),
            )
            gaps.append(
                CoverageGap(
                    function=func,
                    priority=g.get("priority", "medium"),
                    reason=g.get("reason", ""),
                    suggested_test_count=g.get("suggested_test_count", 1),
                )
            )
        return gaps

    def _parse_generation_result(
        self,
        response: str,
        file_path: str,
        test_type: str,
        framework_info: dict[str, str],
    ) -> TestGenerationResult:
        data = self._extract_json(response)

        test_file_content = data.get("test_file_content", "")
        if not test_file_content:
            # Last resort: the whole response might be the test file
            test_file_content = response

        test_file_path = data.get(
            "test_file_path",
            self._compute_test_file_path(file_path, framework_info),
        )
        tests_generated = data.get("tests_generated", 0)
        functions_analyzed = data.get("functions_analyzed", 0)

        generated_tests = [
            GeneratedTest(
                test_name=t.get("test_name", ""),
                test_code="",
                target_function=file_path,
                test_type=test_type,
                description=t.get("description", ""),
            )
            for t in data.get("generated_tests", [])
        ]

        return TestGenerationResult(
            source_file=file_path,
            functions_analyzed=functions_analyzed,
            tests_generated=tests_generated,
            generated_tests=generated_tests,
            test_file_content=test_file_content,
            test_file_path=test_file_path,
        )

    def _extract_json(self, text: str) -> dict[str, Any]:
        """Extract JSON from a Claude response, handling markdown fences."""
        # Strip markdown code fences
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            if end > start:
                text = text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            if end > start:
                text = text[start:end].strip()

        # Direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Find first { ... last }
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass

        logger.error("Failed to parse JSON from response: %.200s", text)
        return {}

    def _compute_test_file_path(
        self, source_path: str, framework_info: dict[str, str]
    ) -> str:
        language = framework_info.get("language", "python")
        stem = Path(source_path).stem
        if language == "python":
            return f"tests/test_{stem}.py"
        if language in ("typescript",):
            return f"src/__tests__/{stem}.test.ts"
        if language in ("javascript",):
            return f"src/__tests__/{stem}.test.js"
        if language == "csharp":
            return f"{stem}Tests.cs"
        if language == "java":
            return f"{stem}Test.java"
        if language == "go":
            return f"{stem}_test.go"
        if language == "ruby":
            return f"spec/{stem}_spec.rb"
        return f"tests/test_{stem}"

    # ── Utilities ────────────────────────────────────────────────────

    def _read_file(self, path: str) -> str:
        try:
            with open(path, encoding="utf-8") as f:
                return f.read()
        except Exception as exc:
            logger.warning("Could not read %s: %s", path, exc)
            return ""
