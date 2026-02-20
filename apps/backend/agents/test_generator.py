"""Test Generator Agent — Automatic test generation for existing code.

Specialized agent that analyzes source code and generates comprehensive
test suites including unit tests, integration tests, and E2E tests.

Capabilities:
- Analyze code coverage gaps and generate tests for uncovered functions
- Generate unit tests with mocks, fixtures, and edge cases
- Generate integration tests based on detected workflows
- Generate E2E tests from user stories
- TDD mode: generate tests before implementation

Example:
    >>> from apps.backend.agents.test_generator import TestGeneratorAgent
    >>> agent = TestGeneratorAgent(llm_provider=provider)
    >>> result = agent.analyze_coverage("src/connectors/jira/connector.py")
    >>> tests = agent.generate_unit_tests("src/connectors/jira/connector.py")
"""

import ast
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ── Data models ─────────────────────────────────────────────────────


@dataclass
class FunctionInfo:
    """Information about a function extracted from source code.

    Attributes:
        name: The function name.
        module: The module path.
        class_name: The parent class name, or None if top-level.
        args: List of argument names (excluding self/cls).
        return_type: The return type annotation, or None.
        docstring: The function docstring, or empty string.
        line_number: The line number where the function starts.
        is_async: Whether the function is async.
        decorators: List of decorator names.
        complexity: Estimated cyclomatic complexity.
    """

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
        """Get the fully qualified function name."""
        if self.class_name:
            return f"{self.class_name}.{self.name}"
        return self.name

    @property
    def is_private(self) -> bool:
        """Check if the function is private (starts with _)."""
        return self.name.startswith("_") and not self.name.startswith("__")

    @property
    def is_dunder(self) -> bool:
        """Check if the function is a dunder method."""
        return self.name.startswith("__") and self.name.endswith("__")


@dataclass
class CoverageGap:
    """Represents a gap in test coverage.

    Attributes:
        function: The uncovered function.
        priority: Priority for test generation (``'high'``, ``'medium'``, ``'low'``).
        reason: Why this function needs tests.
        suggested_test_count: Estimated number of tests needed.
    """

    function: FunctionInfo
    priority: str = "medium"
    reason: str = ""
    suggested_test_count: int = 1


@dataclass
class GeneratedTest:
    """A generated test case.

    Attributes:
        test_name: The test function name.
        test_code: The generated test code.
        target_function: The function being tested.
        test_type: Type of test (``'unit'``, ``'integration'``, ``'e2e'``).
        description: What the test verifies.
        imports: Required import statements.
        fixtures: Required pytest fixtures.
    """

    test_name: str
    test_code: str
    target_function: str
    test_type: str = "unit"
    description: str = ""
    imports: list[str] = field(default_factory=list)
    fixtures: list[str] = field(default_factory=list)


@dataclass
class TestGenerationResult:
    """Result of a test generation run.

    Attributes:
        source_file: The source file that was analyzed.
        functions_analyzed: Number of functions analyzed.
        tests_generated: Number of tests generated.
        coverage_gaps: Identified coverage gaps.
        generated_tests: The generated test cases.
        test_file_content: The complete test file content.
        test_file_path: Suggested path for the test file.
    """

    source_file: str
    functions_analyzed: int = 0
    tests_generated: int = 0
    coverage_gaps: list[CoverageGap] = field(default_factory=list)
    generated_tests: list[GeneratedTest] = field(default_factory=list)
    test_file_content: str = ""
    test_file_path: str = ""


# ── Code analyzer ───────────────────────────────────────────────────


class CodeAnalyzer:
    """Analyzes Python source code to extract function signatures and metadata.

    Uses the ``ast`` module to parse Python files and extract
    function definitions, class structures, and complexity estimates.
    """

    def analyze_file(self, file_path: str) -> list[FunctionInfo]:
        """Analyze a Python file and extract function information.

        Args:
            file_path: Path to the Python source file.

        Returns:
            A list of FunctionInfo objects for all functions in the file.

        Raises:
            FileNotFoundError: If the file does not exist.
            SyntaxError: If the file contains invalid Python.
        """
        logger.info("Analyzing file: %s", file_path)

        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()

        return self.analyze_source(source, module=file_path)

    def analyze_source(
        self,
        source: str,
        module: str = "<unknown>",
    ) -> list[FunctionInfo]:
        """Analyze Python source code and extract function information.

        Args:
            source: The Python source code string.
            module: The module name/path for context.

        Returns:
            A list of FunctionInfo objects.
        """
        try:
            tree = ast.parse(source)
        except SyntaxError:
            logger.error("Failed to parse source from %s.", module)
            return []

        functions: list[FunctionInfo] = []
        self._visit_node(tree, functions, module, class_name=None)
        return functions

    def _visit_node(
        self,
        node: ast.AST,
        functions: list[FunctionInfo],
        module: str,
        class_name: str | None,
    ) -> None:
        """Recursively visit AST nodes to extract functions.

        Args:
            node: The current AST node.
            functions: Accumulator list.
            module: The module path.
            class_name: Current class name if inside a class.
        """
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef):
                # Visit class methods
                self._visit_node(child, functions, module, class_name=child.name)
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_info = self._extract_function_info(
                    child, module, class_name
                )
                functions.append(func_info)

    def _extract_function_info(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        module: str,
        class_name: str | None,
    ) -> FunctionInfo:
        """Extract FunctionInfo from an AST function node.

        Args:
            node: The AST function definition node.
            module: The module path.
            class_name: Parent class name, or None.

        Returns:
            A FunctionInfo instance.
        """
        # Extract arguments (skip self/cls)
        args = []
        for arg in node.args.args:
            name = arg.arg
            if name not in ("self", "cls"):
                args.append(name)

        # Extract return type annotation
        return_type = None
        if node.returns:
            try:
                return_type = ast.unparse(node.returns)
            except Exception:
                return_type = None

        # Extract docstring
        docstring = ast.get_docstring(node) or ""

        # Extract decorators
        decorators = []
        for dec in node.decorator_list:
            try:
                decorators.append(ast.unparse(dec))
            except Exception:
                pass

        # Estimate complexity
        complexity = self._estimate_complexity(node)

        return FunctionInfo(
            name=node.name,
            module=module,
            class_name=class_name,
            args=args,
            return_type=return_type,
            docstring=docstring,
            line_number=node.lineno,
            is_async=isinstance(node, ast.AsyncFunctionDef),
            decorators=decorators,
            complexity=complexity,
        )

    def _estimate_complexity(self, node: ast.AST) -> int:
        """Estimate cyclomatic complexity of a function.

        Counts branches (if, elif, for, while, except, and, or)
        to estimate complexity.

        Args:
            node: The AST node to analyze.

        Returns:
            The estimated complexity score.
        """
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.IfExp)):
                complexity += 1
            elif isinstance(child, (ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(child, (ast.While,)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        return complexity


# ── Test generator agent ────────────────────────────────────────────


class TestGeneratorAgent:
    """Agent specialized in automatic test generation.

    Analyzes source code, identifies coverage gaps, and generates
    comprehensive test suites using templates and LLM assistance.

    Attributes:
        _analyzer: The code analyzer instance.
        _llm_provider: Optional LLM provider for AI-assisted generation.

    Example:
        >>> agent = TestGeneratorAgent()
        >>> result = agent.generate_unit_tests("src/connectors/jira/connector.py")
        >>> print(result.test_file_content)
    """

    def __init__(self, llm_provider: Any = None) -> None:
        """Initialize the test generator agent.

        Args:
            llm_provider: Optional LLM provider for AI-assisted test
                generation. If None, uses template-based generation.
        """
        self._analyzer = CodeAnalyzer()
        self._llm_provider = llm_provider

    def analyze_coverage(
        self,
        file_path: str,
        existing_test_path: str | None = None,
    ) -> list[CoverageGap]:
        """Analyze coverage gaps for a source file.

        Identifies functions that lack corresponding test coverage
        by comparing source functions against existing test files.

        Args:
            file_path: Path to the source file to analyze.
            existing_test_path: Optional path to existing test file.

        Returns:
            A list of CoverageGap objects sorted by priority.
        """
        logger.info("Analyzing coverage for: %s", file_path)

        functions = self._analyzer.analyze_file(file_path)

        # Find existing tested functions
        tested_functions: set[str] = set()
        if existing_test_path and os.path.exists(existing_test_path):
            tested_functions = self._find_tested_functions(existing_test_path)

        gaps: list[CoverageGap] = []
        for func in functions:
            if func.is_dunder and func.name not in ("__init__",):
                continue

            if func.full_name in tested_functions or func.name in tested_functions:
                continue

            priority = self._assess_priority(func)
            test_count = max(1, func.complexity)

            reason = self._generate_gap_reason(func, tested_functions)

            gaps.append(CoverageGap(
                function=func,
                priority=priority,
                reason=reason,
                suggested_test_count=test_count,
            ))

        # Sort by priority
        priority_order = {"high": 0, "medium": 1, "low": 2}
        gaps.sort(key=lambda g: priority_order.get(g.priority, 1))

        logger.info(
            "Found %d coverage gaps (%d functions analyzed).",
            len(gaps),
            len(functions),
        )
        return gaps

    def _find_tested_functions(self, test_file_path: str) -> set[str]:
        """Extract function names that are tested in a test file.

        Parses test function names to infer which source functions
        they cover (e.g., ``test_connect`` → ``connect``).

        Args:
            test_file_path: Path to the test file.

        Returns:
            A set of function names that appear to be tested.
        """
        try:
            with open(test_file_path, "r", encoding="utf-8") as f:
                source = f.read()
        except (FileNotFoundError, OSError):
            return set()

        tested = set()
        # Pattern: test_<function_name> or test_<function_name>_<variant>
        for match in re.finditer(r"def\s+test_(\w+)", source):
            name = match.group(1)
            # Add the full name
            tested.add(name)
            # Also add all possible underscore-split prefixes so that
            # e.g. "get_user_returns_expected" matches function "get_user"
            parts = name.split("_")
            for i in range(1, len(parts)):
                prefix = "_".join(parts[:i])
                tested.add(prefix)

        return tested

    def _assess_priority(self, func: FunctionInfo) -> str:
        """Assess test generation priority for a function.

        Args:
            func: The function to assess.

        Returns:
            Priority string: ``'high'``, ``'medium'``, or ``'low'``.
        """
        if func.is_private:
            return "low"
        if func.complexity >= 5:
            return "high"
        if "property" in func.decorators:
            return "low"
        if any(d in func.decorators for d in ("abstractmethod", "staticmethod")):
            return "medium"
        if func.class_name and not func.is_private:
            return "high"
        return "medium"

    def _generate_gap_reason(
        self,
        func: FunctionInfo,
        tested: set[str],
    ) -> str:
        """Generate a human-readable reason for a coverage gap.

        Args:
            func: The uncovered function.
            tested: Set of already-tested function names.

        Returns:
            A reason string.
        """
        if func.complexity >= 5:
            return f"High complexity ({func.complexity}) — needs thorough testing"
        if func.class_name and not func.is_private:
            return f"Public method on {func.class_name} — part of public API"
        if not func.is_private:
            return "Public function without test coverage"
        return "Private function — low priority but may need edge case tests"

    def generate_unit_tests(
        self,
        file_path: str,
        existing_test_path: str | None = None,
        max_tests_per_function: int = 3,
    ) -> TestGenerationResult:
        """Generate unit tests for a source file.

        Analyzes the file, identifies coverage gaps, and generates
        test cases for uncovered functions.

        Args:
            file_path: Path to the source file.
            existing_test_path: Optional path to existing test file.
            max_tests_per_function: Maximum tests per function.

        Returns:
            A TestGenerationResult with generated tests.
        """
        logger.info("Generating unit tests for: %s", file_path)

        functions = self._analyzer.analyze_file(file_path)
        gaps = self.analyze_coverage(file_path, existing_test_path)

        generated_tests: list[GeneratedTest] = []
        for gap in gaps:
            tests = self._generate_tests_for_function(
                gap.function,
                max_tests=max_tests_per_function,
            )
            generated_tests.extend(tests)

        # Build complete test file
        test_file_path = self._compute_test_file_path(file_path)
        test_file_content = self._build_test_file(
            file_path, functions, generated_tests
        )

        result = TestGenerationResult(
            source_file=file_path,
            functions_analyzed=len(functions),
            tests_generated=len(generated_tests),
            coverage_gaps=gaps,
            generated_tests=generated_tests,
            test_file_content=test_file_content,
            test_file_path=test_file_path,
        )

        logger.info(
            "Generated %d tests for %d functions in '%s'.",
            result.tests_generated,
            result.functions_analyzed,
            file_path,
        )
        return result

    def generate_tests_from_user_story(
        self,
        user_story: str,
        target_module: str,
    ) -> TestGenerationResult:
        """Generate E2E tests from a user story description.

        Args:
            user_story: The user story text.
            target_module: The module/file to test.

        Returns:
            A TestGenerationResult with E2E test cases.
        """
        logger.info("Generating E2E tests from user story for: %s", target_module)

        # Parse user story into test scenarios
        scenarios = self._parse_user_story(user_story)

        generated_tests: list[GeneratedTest] = []
        for i, scenario in enumerate(scenarios):
            test = GeneratedTest(
                test_name=f"test_e2e_{self._slugify(scenario['title'])}",
                test_code=self._generate_e2e_test_code(scenario),
                target_function=target_module,
                test_type="e2e",
                description=scenario.get("description", ""),
                imports=["import pytest"],
            )
            generated_tests.append(test)

        test_file_content = self._build_e2e_test_file(
            target_module, generated_tests
        )

        return TestGenerationResult(
            source_file=target_module,
            functions_analyzed=0,
            tests_generated=len(generated_tests),
            generated_tests=generated_tests,
            test_file_content=test_file_content,
            test_file_path=f"tests/e2e/test_{self._slugify(target_module)}.py",
        )

    def generate_tdd_tests(
        self,
        spec: dict[str, Any],
    ) -> TestGenerationResult:
        """Generate tests before implementation (TDD mode).

        Creates test stubs based on a function specification that
        define the expected behavior before the code is written.

        Args:
            spec: Function specification with keys:
                ``'name'``, ``'args'``, ``'returns'``, ``'description'``,
                ``'module'``, ``'edge_cases'``.

        Returns:
            A TestGenerationResult with TDD test stubs.
        """
        func_name = spec.get("name", "unknown")
        module = spec.get("module", "")
        description = spec.get("description", "")
        args = spec.get("args", [])
        returns = spec.get("returns", "Any")
        edge_cases = spec.get("edge_cases", [])

        logger.info("Generating TDD tests for: %s.%s", module, func_name)

        generated_tests: list[GeneratedTest] = []

        # Happy path test
        generated_tests.append(GeneratedTest(
            test_name=f"test_{func_name}_happy_path",
            test_code=self._generate_tdd_happy_path(spec),
            target_function=func_name,
            test_type="unit",
            description=f"Verify {func_name} works with valid inputs",
            imports=["import pytest"],
        ))

        # Edge case tests
        for i, case in enumerate(edge_cases):
            generated_tests.append(GeneratedTest(
                test_name=f"test_{func_name}_{self._slugify(case)}",
                test_code=self._generate_tdd_edge_case(spec, case),
                target_function=func_name,
                test_type="unit",
                description=f"Edge case: {case}",
                imports=["import pytest"],
            ))

        # Error handling test
        generated_tests.append(GeneratedTest(
            test_name=f"test_{func_name}_error_handling",
            test_code=self._generate_tdd_error_test(spec),
            target_function=func_name,
            test_type="unit",
            description=f"Verify {func_name} handles errors correctly",
            imports=["import pytest"],
        ))

        test_content = self._build_tdd_test_file(module, func_name, generated_tests)

        return TestGenerationResult(
            source_file=module,
            functions_analyzed=0,
            tests_generated=len(generated_tests),
            generated_tests=generated_tests,
            test_file_content=test_content,
            test_file_path=f"tests/test_{func_name}.py",
        )

    # ── Internal generation methods ──────────────────────────────────

    def _generate_tests_for_function(
        self,
        func: FunctionInfo,
        max_tests: int = 3,
    ) -> list[GeneratedTest]:
        """Generate test cases for a single function.

        Args:
            func: The function to generate tests for.
            max_tests: Maximum number of tests to generate.

        Returns:
            A list of GeneratedTest objects.
        """
        tests: list[GeneratedTest] = []

        # Happy path test
        tests.append(GeneratedTest(
            test_name=f"test_{func.name}_returns_expected",
            test_code=self._generate_happy_path_test(func),
            target_function=func.full_name,
            test_type="unit",
            description=f"Verify {func.full_name} returns expected result",
        ))

        # Edge case: empty/None inputs
        if func.args and len(tests) < max_tests:
            tests.append(GeneratedTest(
                test_name=f"test_{func.name}_with_empty_input",
                test_code=self._generate_edge_case_test(func),
                target_function=func.full_name,
                test_type="unit",
                description=f"Verify {func.full_name} handles empty/None inputs",
            ))

        # Error handling test
        if func.complexity >= 3 and len(tests) < max_tests:
            tests.append(GeneratedTest(
                test_name=f"test_{func.name}_error_handling",
                test_code=self._generate_error_test(func),
                target_function=func.full_name,
                test_type="unit",
                description=f"Verify {func.full_name} handles errors correctly",
            ))

        return tests

    def _generate_happy_path_test(self, func: FunctionInfo) -> str:
        """Generate a happy path test for a function."""
        args_str = ", ".join(f"{a}=mock_{a}" for a in func.args)
        if func.class_name:
            setup = f"    instance = {func.class_name}(mock_dependency)\n"
            call = f"    result = instance.{func.name}({args_str})"
        else:
            call = f"    result = {func.name}({args_str})"
            setup = ""

        return (
            f"def test_{func.name}_returns_expected({', '.join(func.args) if func.args else ''}):\n"
            f'    """{func.full_name} returns expected result with valid inputs."""\n'
            f"    # Arrange\n"
            f"{setup}"
            f"    # Act\n"
            f"{call}\n"
            f"    # Assert\n"
            f"    assert result is not None\n"
        )

    def _generate_edge_case_test(self, func: FunctionInfo) -> str:
        """Generate an edge case test for a function."""
        if func.class_name:
            call_prefix = f"instance.{func.name}"
        else:
            call_prefix = func.name

        return (
            f"def test_{func.name}_with_empty_input():\n"
            f'    """{func.full_name} handles empty/None inputs gracefully."""\n'
            f"    # Test with empty/default parameters\n"
            f"    # TODO: Customize arguments for specific edge case\n"
            f"    pass\n"
        )

    def _generate_error_test(self, func: FunctionInfo) -> str:
        """Generate an error handling test for a function."""
        return (
            f"def test_{func.name}_error_handling():\n"
            f'    """{func.full_name} raises appropriate errors."""\n'
            f"    # Test error conditions\n"
            f"    with pytest.raises(Exception):\n"
            f"        # TODO: Call with invalid inputs\n"
            f"        pass\n"
        )

    def _generate_tdd_happy_path(self, spec: dict[str, Any]) -> str:
        """Generate a TDD happy path test."""
        name = spec.get("name", "func")
        args = spec.get("args", [])
        returns = spec.get("returns", "Any")
        args_str = ", ".join(f"{a}=valid_{a}" for a in args)

        return (
            f"def test_{name}_happy_path():\n"
            f'    """Verify {name} works with valid inputs."""\n'
            f"    # TODO: Define valid input values\n"
            f"    result = {name}({args_str})\n"
            f"    assert result is not None\n"
            f"    # TODO: Assert specific return value / type\n"
        )

    def _generate_tdd_edge_case(self, spec: dict[str, Any], case: str) -> str:
        """Generate a TDD edge case test."""
        name = spec.get("name", "func")
        slug = self._slugify(case)

        return (
            f"def test_{name}_{slug}():\n"
            f'    """Edge case: {case}."""\n'
            f"    # TODO: Implement edge case test\n"
            f"    pass\n"
        )

    def _generate_tdd_error_test(self, spec: dict[str, Any]) -> str:
        """Generate a TDD error handling test."""
        name = spec.get("name", "func")

        return (
            f"def test_{name}_error_handling():\n"
            f'    """Verify {name} handles errors correctly."""\n'
            f"    with pytest.raises(Exception):\n"
            f"        # TODO: Call with invalid inputs\n"
            f"        {name}()\n"
        )

    def _generate_e2e_test_code(self, scenario: dict[str, Any]) -> str:
        """Generate E2E test code from a scenario."""
        title = scenario.get("title", "scenario")
        steps = scenario.get("steps", [])

        steps_code = "\n".join(
            f"    # Step: {step}" for step in steps
        )

        return (
            f"def test_e2e_{self._slugify(title)}():\n"
            f'    """E2E: {title}."""\n'
            f"{steps_code}\n"
            f"    # TODO: Implement E2E steps\n"
            f"    pass\n"
        )

    # ── File building ────────────────────────────────────────────────

    def _build_test_file(
        self,
        source_file: str,
        functions: list[FunctionInfo],
        tests: list[GeneratedTest],
    ) -> str:
        """Build a complete test file from generated tests.

        Args:
            source_file: The source file path.
            functions: All analyzed functions.
            tests: The generated tests.

        Returns:
            The complete test file content as a string.
        """
        module_name = self._path_to_module(source_file)

        # Collect unique imports
        all_imports = {"from unittest.mock import MagicMock, patch", "import pytest"}
        for t in tests:
            all_imports.update(t.imports)

        imports_str = "\n".join(sorted(all_imports))

        # Group tests by target function
        header = (
            f'"""Auto-generated unit tests for {source_file}.\n'
            f'\n'
            f'Generated by TestGeneratorAgent (Feature 8.3).\n'
            f'"""\n'
        )

        test_code = "\n\n".join(t.test_code for t in tests)

        return f"{header}\n{imports_str}\n\n\n{test_code}\n"

    def _build_e2e_test_file(
        self,
        target_module: str,
        tests: list[GeneratedTest],
    ) -> str:
        """Build a complete E2E test file."""
        header = (
            f'"""Auto-generated E2E tests for {target_module}.\n'
            f'\n'
            f'Generated by TestGeneratorAgent (Feature 8.3).\n'
            f'"""\n'
        )

        test_code = "\n\n".join(t.test_code for t in tests)

        return f"{header}\nimport pytest\n\n\n{test_code}\n"

    def _build_tdd_test_file(
        self,
        module: str,
        func_name: str,
        tests: list[GeneratedTest],
    ) -> str:
        """Build a TDD test file."""
        header = (
            f'"""TDD tests for {module}.{func_name}.\n'
            f'\n'
            f'Tests written BEFORE implementation (TDD mode).\n'
            f'Generated by TestGeneratorAgent (Feature 8.3).\n'
            f'"""\n'
        )

        test_code = "\n\n".join(t.test_code for t in tests)

        return f"{header}\nimport pytest\n\n\n{test_code}\n"

    # ── Utilities ────────────────────────────────────────────────────

    def _compute_test_file_path(self, source_path: str) -> str:
        """Compute the test file path for a source file.

        Args:
            source_path: The source file path.

        Returns:
            The corresponding test file path.
        """
        # Convert source path to test path
        # e.g., src/connectors/jira/connector.py -> tests/connectors/jira/test_connector.py
        parts = source_path.replace("\\", "/").split("/")
        filename = parts[-1]
        test_filename = f"test_{filename}"

        if "src/" in source_path:
            rel = source_path.split("src/", 1)[1]
            return f"tests/{os.path.dirname(rel)}/{test_filename}".replace("\\", "/")

        return f"tests/{test_filename}"

    def _path_to_module(self, file_path: str) -> str:
        """Convert a file path to a Python module path.

        Args:
            file_path: The file path (e.g., ``'src/connectors/jira/connector.py'``).

        Returns:
            The module path (e.g., ``'src.connectors.jira.connector'``).
        """
        module = file_path.replace("\\", "/").replace("/", ".")
        if module.endswith(".py"):
            module = module[:-3]
        return module

    def _slugify(self, text: str) -> str:
        """Convert text to a valid Python identifier slug.

        Args:
            text: The text to slugify.

        Returns:
            A valid Python identifier string.
        """
        slug = re.sub(r"[^a-zA-Z0-9]+", "_", text.lower())
        slug = slug.strip("_")
        return slug or "unnamed"

    def _parse_user_story(self, user_story: str) -> list[dict[str, Any]]:
        """Parse a user story into test scenarios.

        Args:
            user_story: The user story text.

        Returns:
            A list of scenario dictionaries with ``'title'``,
            ``'description'``, and ``'steps'`` keys.
        """
        scenarios: list[dict[str, Any]] = []

        # Simple parsing: split on "Given/When/Then" or numbered steps
        lines = user_story.strip().split("\n")
        current_scenario: dict[str, Any] = {
            "title": lines[0] if lines else "Default scenario",
            "description": user_story,
            "steps": [],
        }

        for line in lines[1:]:
            stripped = line.strip()
            if stripped.lower().startswith(("given ", "when ", "then ", "and ")):
                current_scenario["steps"].append(stripped)
            elif stripped.startswith(("- ", "* ", "1.", "2.", "3.")):
                current_scenario["steps"].append(stripped.lstrip("-* 0123456789."))

        if not current_scenario["steps"]:
            current_scenario["steps"] = [user_story]

        scenarios.append(current_scenario)
        return scenarios
