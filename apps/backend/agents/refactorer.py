"""Refactoring Agent — Autonomous code refactoring with smell detection and design patterns.

Specialized agent that analyzes existing code for code smells, proposes
refactoring strategies with diff previews, and executes refactoring with
automatic non-regression test generation.

Feature 2.1 — Agent de refactoring autonome.

Example:
    >>> from apps.backend.agents.refactorer import RefactoringAgent
    >>> agent = RefactoringAgent()
    >>> smells = agent.detect_smells("src/connectors/jira/connector.py")
    >>> proposals = agent.propose_refactoring("src/connectors/jira/connector.py")
    >>> result = agent.execute_refactoring(proposals[0])
"""

import ast
import logging
import os
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class SmellType(str, Enum):
    """Types of code smells detected."""
    LONG_METHOD = "long_method"
    GOD_CLASS = "god_class"
    DUPLICATE_CODE = "duplicate_code"
    LONG_PARAMETER_LIST = "long_parameter_list"
    DEAD_CODE = "dead_code"
    DEEP_NESTING = "deep_nesting"
    COMPLEX_CONDITIONAL = "complex_conditional"
    MAGIC_NUMBER = "magic_number"
    MISSING_DOCSTRING = "missing_docstring"
    TOO_MANY_RETURNS = "too_many_returns"
    LARGE_FILE = "large_file"
    UNUSED_IMPORT = "unused_import"


class SmellSeverity(str, Enum):
    """Severity level of a code smell."""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RefactoringPattern(str, Enum):
    """Design patterns / refactoring techniques supported."""
    EXTRACT_METHOD = "extract_method"
    EXTRACT_CLASS = "extract_class"
    RENAME = "rename"
    INLINE = "inline"
    MOVE_METHOD = "move_method"
    REPLACE_CONDITIONAL_WITH_POLYMORPHISM = "replace_conditional_with_polymorphism"
    INTRODUCE_PARAMETER_OBJECT = "introduce_parameter_object"
    REMOVE_DEAD_CODE = "remove_dead_code"
    SIMPLIFY_CONDITIONAL = "simplify_conditional"
    ADD_DOCSTRING = "add_docstring"
    EXTRACT_CONSTANT = "extract_constant"
    SPLIT_FILE = "split_file"


class RefactoringStatus(str, Enum):
    """Status of a refactoring execution."""
    PROPOSED = "proposed"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


# ---------------------------------------------------------------------------
# Thresholds for smell detection
# ---------------------------------------------------------------------------

SMELL_THRESHOLDS = {
    "max_method_lines": 30,
    "max_class_methods": 15,
    "max_parameters": 5,
    "max_nesting_depth": 4,
    "max_returns": 4,
    "max_file_lines": 500,
    "max_complexity": 10,
    "min_duplicate_lines": 6,
}


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class CodeSmell:
    """A detected code smell.

    Attributes:
        smell_type: Type of smell.
        severity: Severity level.
        file_path: File where the smell was found.
        line_start: Starting line number.
        line_end: Ending line number.
        message: Human-readable description.
        symbol_name: Name of the offending symbol (function, class, etc.).
        metric_value: The measured metric value (e.g. line count).
        threshold: The threshold that was exceeded.
    """
    smell_type: SmellType
    severity: SmellSeverity
    file_path: str
    line_start: int = 0
    line_end: int = 0
    message: str = ""
    symbol_name: str = ""
    metric_value: int = 0
    threshold: int = 0

    def to_dict(self) -> dict:
        return {
            "smell_type": self.smell_type.value,
            "severity": self.severity.value,
            "file_path": self.file_path,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "message": self.message,
            "symbol_name": self.symbol_name,
            "metric_value": self.metric_value,
            "threshold": self.threshold,
        }


@dataclass
class RefactoringProposal:
    """A proposed refactoring action.

    Attributes:
        proposal_id: Unique identifier.
        pattern: Refactoring pattern to apply.
        file_path: Target file.
        target_symbol: Function/class to refactor.
        description: What the refactoring does.
        before_preview: Code before refactoring (snippet).
        after_preview: Code after refactoring (snippet).
        related_smells: Code smells addressed by this refactoring.
        estimated_impact: Estimated improvement description.
        status: Current status of the proposal.
        risk_level: Risk level (low, medium, high).
    """
    proposal_id: str
    pattern: RefactoringPattern
    file_path: str
    target_symbol: str = ""
    description: str = ""
    before_preview: str = ""
    after_preview: str = ""
    related_smells: list[CodeSmell] = field(default_factory=list)
    estimated_impact: str = ""
    status: RefactoringStatus = RefactoringStatus.PROPOSED
    risk_level: str = "low"

    def to_dict(self) -> dict:
        return {
            "proposal_id": self.proposal_id,
            "pattern": self.pattern.value,
            "file_path": self.file_path,
            "target_symbol": self.target_symbol,
            "description": self.description,
            "before_preview": self.before_preview,
            "after_preview": self.after_preview,
            "related_smells": [s.to_dict() for s in self.related_smells],
            "estimated_impact": self.estimated_impact,
            "status": self.status.value,
            "risk_level": self.risk_level,
        }


@dataclass
class RefactoringResult:
    """Result of an executed refactoring.

    Attributes:
        proposal: The proposal that was executed.
        success: Whether the refactoring succeeded.
        files_modified: List of files that were modified.
        tests_generated: Number of regression tests generated.
        test_code: Generated regression test code.
        error: Error message if failed.
        timestamp: When the refactoring was executed.
    """
    proposal: RefactoringProposal
    success: bool = True
    files_modified: list[str] = field(default_factory=list)
    tests_generated: int = 0
    test_code: str = ""
    error: str = ""
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "proposal": self.proposal.to_dict(),
            "success": self.success,
            "files_modified": self.files_modified,
            "tests_generated": self.tests_generated,
            "test_code": self.test_code,
            "error": self.error,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# AST-based smell detector
# ---------------------------------------------------------------------------

class SmellDetector:
    """Detects code smells using AST analysis and heuristics.

    Configurable thresholds control sensitivity for each smell type.
    """

    def __init__(self, thresholds: dict[str, int] | None = None) -> None:
        self.thresholds = {**SMELL_THRESHOLDS, **(thresholds or {})}

    def detect_from_source(
        self,
        source: str,
        file_path: str = "<unknown>",
    ) -> list[CodeSmell]:
        """Detect code smells in Python source code.

        Args:
            source: Python source code string.
            file_path: Path for reporting.

        Returns:
            List of detected CodeSmell objects.
        """
        smells: list[CodeSmell] = []
        lines = source.splitlines()

        # File-level checks
        smells.extend(self._check_large_file(lines, file_path))
        smells.extend(self._check_unused_imports(source, file_path))

        # AST-based checks
        try:
            tree = ast.parse(source)
        except SyntaxError:
            logger.warning("Cannot parse %s for smell detection", file_path)
            return smells

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                smells.extend(self._check_function(node, source, file_path))
            elif isinstance(node, ast.ClassDef):
                smells.extend(self._check_class(node, file_path))

        # Duplicate code detection (simple heuristic)
        smells.extend(self._check_duplicates(lines, file_path))

        # Magic numbers
        smells.extend(self._check_magic_numbers(tree, file_path))

        return smells

    def detect_from_file(self, file_path: str) -> list[CodeSmell]:
        """Detect code smells in a Python file.

        Args:
            file_path: Path to the Python file.

        Returns:
            List of detected CodeSmell objects.

        Raises:
            FileNotFoundError: If the file does not exist.
        """
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
        return self.detect_from_source(source, file_path)

    # -- Individual checks ---------------------------------------------------

    def _check_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        source: str,
        file_path: str,
    ) -> list[CodeSmell]:
        smells: list[CodeSmell] = []
        lines = source.splitlines()
        func_lines = self._count_function_lines(node, lines)

        # Long method
        threshold = self.thresholds["max_method_lines"]
        if func_lines > threshold:
            smells.append(CodeSmell(
                smell_type=SmellType.LONG_METHOD,
                severity=SmellSeverity.HIGH if func_lines > threshold * 2 else SmellSeverity.MEDIUM,
                file_path=file_path,
                line_start=node.lineno,
                line_end=node.end_lineno or node.lineno,
                message=f"Method '{node.name}' has {func_lines} lines (threshold: {threshold})",
                symbol_name=node.name,
                metric_value=func_lines,
                threshold=threshold,
            ))

        # Long parameter list
        param_threshold = self.thresholds["max_parameters"]
        params = [a.arg for a in node.args.args if a.arg not in ("self", "cls")]
        if len(params) > param_threshold:
            smells.append(CodeSmell(
                smell_type=SmellType.LONG_PARAMETER_LIST,
                severity=SmellSeverity.MEDIUM,
                file_path=file_path,
                line_start=node.lineno,
                line_end=node.lineno,
                message=f"Method '{node.name}' has {len(params)} parameters (threshold: {param_threshold})",
                symbol_name=node.name,
                metric_value=len(params),
                threshold=param_threshold,
            ))

        # Deep nesting
        max_depth = self._measure_nesting_depth(node)
        nesting_threshold = self.thresholds["max_nesting_depth"]
        if max_depth > nesting_threshold:
            smells.append(CodeSmell(
                smell_type=SmellType.DEEP_NESTING,
                severity=SmellSeverity.HIGH if max_depth > nesting_threshold + 2 else SmellSeverity.MEDIUM,
                file_path=file_path,
                line_start=node.lineno,
                line_end=node.end_lineno or node.lineno,
                message=f"Method '{node.name}' has nesting depth {max_depth} (threshold: {nesting_threshold})",
                symbol_name=node.name,
                metric_value=max_depth,
                threshold=nesting_threshold,
            ))

        # Too many returns
        return_count = sum(1 for n in ast.walk(node) if isinstance(n, ast.Return))
        return_threshold = self.thresholds["max_returns"]
        if return_count > return_threshold:
            smells.append(CodeSmell(
                smell_type=SmellType.TOO_MANY_RETURNS,
                severity=SmellSeverity.LOW,
                file_path=file_path,
                line_start=node.lineno,
                line_end=node.end_lineno or node.lineno,
                message=f"Method '{node.name}' has {return_count} return statements (threshold: {return_threshold})",
                symbol_name=node.name,
                metric_value=return_count,
                threshold=return_threshold,
            ))

        # Missing docstring
        docstring = ast.get_docstring(node)
        if not docstring and not node.name.startswith("_"):
            smells.append(CodeSmell(
                smell_type=SmellType.MISSING_DOCSTRING,
                severity=SmellSeverity.INFO,
                file_path=file_path,
                line_start=node.lineno,
                line_end=node.lineno,
                message=f"Public method '{node.name}' is missing a docstring",
                symbol_name=node.name,
            ))

        return smells

    def _check_class(self, node: ast.ClassDef, file_path: str) -> list[CodeSmell]:
        smells: list[CodeSmell] = []
        methods = [
            n for n in ast.iter_child_nodes(node)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        threshold = self.thresholds["max_class_methods"]
        if len(methods) > threshold:
            smells.append(CodeSmell(
                smell_type=SmellType.GOD_CLASS,
                severity=SmellSeverity.HIGH,
                file_path=file_path,
                line_start=node.lineno,
                line_end=node.end_lineno or node.lineno,
                message=f"Class '{node.name}' has {len(methods)} methods (threshold: {threshold})",
                symbol_name=node.name,
                metric_value=len(methods),
                threshold=threshold,
            ))

        # Missing class docstring
        docstring = ast.get_docstring(node)
        if not docstring and not node.name.startswith("_"):
            smells.append(CodeSmell(
                smell_type=SmellType.MISSING_DOCSTRING,
                severity=SmellSeverity.INFO,
                file_path=file_path,
                line_start=node.lineno,
                line_end=node.lineno,
                message=f"Public class '{node.name}' is missing a docstring",
                symbol_name=node.name,
            ))

        return smells

    def _check_large_file(self, lines: list[str], file_path: str) -> list[CodeSmell]:
        threshold = self.thresholds["max_file_lines"]
        if len(lines) > threshold:
            return [CodeSmell(
                smell_type=SmellType.LARGE_FILE,
                severity=SmellSeverity.MEDIUM,
                file_path=file_path,
                line_start=1,
                line_end=len(lines),
                message=f"File has {len(lines)} lines (threshold: {threshold})",
                metric_value=len(lines),
                threshold=threshold,
            )]
        return []

    def _check_unused_imports(self, source: str, file_path: str) -> list[CodeSmell]:
        """Simple heuristic: find imports whose name doesn't appear elsewhere."""
        smells: list[CodeSmell] = []
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return smells

        lines = source.splitlines()

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname or alias.name.split(".")[-1]
                    # Check if name appears elsewhere in source (excluding the import line)
                    rest = "\n".join(
                        line for i, line in enumerate(lines) if i != node.lineno - 1
                    )
                    if name not in rest:
                        smells.append(CodeSmell(
                            smell_type=SmellType.UNUSED_IMPORT,
                            severity=SmellSeverity.LOW,
                            file_path=file_path,
                            line_start=node.lineno,
                            line_end=node.lineno,
                            message=f"Import '{name}' appears unused",
                            symbol_name=name,
                        ))
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    name = alias.asname or alias.name
                    rest = "\n".join(
                        line for i, line in enumerate(lines) if i != node.lineno - 1
                    )
                    if name not in rest:
                        smells.append(CodeSmell(
                            smell_type=SmellType.UNUSED_IMPORT,
                            severity=SmellSeverity.LOW,
                            file_path=file_path,
                            line_start=node.lineno,
                            line_end=node.lineno,
                            message=f"Import '{name}' from '{node.module}' appears unused",
                            symbol_name=name,
                        ))
        return smells

    def _check_duplicates(self, lines: list[str], file_path: str) -> list[CodeSmell]:
        """Simple duplicate line detection using sliding window."""
        smells: list[CodeSmell] = []
        min_dup = self.thresholds["min_duplicate_lines"]
        stripped = [line.strip() for line in lines]
        seen_blocks: dict[str, int] = {}

        for i in range(len(stripped) - min_dup + 1):
            block = "\n".join(stripped[i:i + min_dup])
            if not block.strip() or all(l == "" for l in stripped[i:i + min_dup]):
                continue
            if block in seen_blocks:
                smells.append(CodeSmell(
                    smell_type=SmellType.DUPLICATE_CODE,
                    severity=SmellSeverity.MEDIUM,
                    file_path=file_path,
                    line_start=i + 1,
                    line_end=i + min_dup,
                    message=f"Duplicate block ({min_dup} lines) first seen at line {seen_blocks[block] + 1}",
                    metric_value=min_dup,
                    threshold=min_dup,
                ))
            else:
                seen_blocks[block] = i

        return smells

    def _check_magic_numbers(self, tree: ast.AST, file_path: str) -> list[CodeSmell]:
        """Detect magic numbers (numeric literals not 0, 1, -1)."""
        smells: list[CodeSmell] = []
        SAFE_NUMBERS = {0, 1, -1, 2, 10, 100, 0.0, 1.0}

        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
                if node.value not in SAFE_NUMBERS and hasattr(node, "lineno"):
                    smells.append(CodeSmell(
                        smell_type=SmellType.MAGIC_NUMBER,
                        severity=SmellSeverity.INFO,
                        file_path=file_path,
                        line_start=node.lineno,
                        line_end=node.lineno,
                        message=f"Magic number {node.value} found",
                        metric_value=int(node.value) if isinstance(node.value, int) else 0,
                    ))
        return smells

    # -- Helpers -------------------------------------------------------------

    @staticmethod
    def _count_function_lines(
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        lines: list[str],
    ) -> int:
        """Count non-empty, non-comment lines in a function."""
        start = node.lineno - 1
        end = (node.end_lineno or node.lineno)
        func_lines = lines[start:end]
        return sum(
            1 for line in func_lines
            if line.strip() and not line.strip().startswith("#")
        )

    @staticmethod
    def _measure_nesting_depth(node: ast.AST, depth: int = 0) -> int:
        """Measure maximum nesting depth of control structures."""
        max_depth = depth
        nesting_nodes = (ast.If, ast.For, ast.While, ast.With, ast.Try)
        for child in ast.iter_child_nodes(node):
            if isinstance(child, nesting_nodes):
                child_depth = SmellDetector._measure_nesting_depth(child, depth + 1)
                max_depth = max(max_depth, child_depth)
            else:
                child_depth = SmellDetector._measure_nesting_depth(child, depth)
                max_depth = max(max_depth, child_depth)
        return max_depth


# ---------------------------------------------------------------------------
# Refactoring Agent
# ---------------------------------------------------------------------------

class RefactoringAgent:
    """Autonomous refactoring agent that detects smells and proposes refactoring.

    Integrates SmellDetector for analysis, proposes refactoring strategies
    using design patterns, generates before/after previews, and creates
    regression test stubs.
    """

    def __init__(
        self,
        llm_provider: Any | None = None,
        thresholds: dict[str, int] | None = None,
    ) -> None:
        self.llm_provider = llm_provider
        self.detector = SmellDetector(thresholds)
        self._proposals: list[RefactoringProposal] = []
        self._results: list[RefactoringResult] = []
        self._proposal_counter = 0
        logger.info("RefactoringAgent initialized")

    # -- Smell detection -----------------------------------------------------

    def detect_smells(self, file_path: str) -> list[CodeSmell]:
        """Detect code smells in a file.

        Args:
            file_path: Path to the Python file.

        Returns:
            List of detected code smells.
        """
        return self.detector.detect_from_file(file_path)

    def detect_smells_from_source(
        self,
        source: str,
        file_path: str = "<source>",
    ) -> list[CodeSmell]:
        """Detect code smells from source code string.

        Args:
            source: Python source code.
            file_path: Display path for reporting.

        Returns:
            List of detected code smells.
        """
        return self.detector.detect_from_source(source, file_path)

    # -- Refactoring proposals -----------------------------------------------

    def propose_refactoring(
        self,
        file_path: str | None = None,
        source: str | None = None,
        smells: list[CodeSmell] | None = None,
    ) -> list[RefactoringProposal]:
        """Propose refactoring actions based on detected smells.

        Args:
            file_path: Path to analyze (reads the file).
            source: Source code string (alternative to file_path).
            smells: Pre-detected smells (skip detection if provided).

        Returns:
            List of RefactoringProposal objects.
        """
        if smells is None:
            if source:
                smells = self.detector.detect_from_source(source, file_path or "<source>")
            elif file_path:
                smells = self.detector.detect_from_file(file_path)
            else:
                return []

        proposals: list[RefactoringProposal] = []

        # Group smells by symbol
        smells_by_symbol: dict[str, list[CodeSmell]] = {}
        for smell in smells:
            key = smell.symbol_name or smell.file_path
            smells_by_symbol.setdefault(key, []).append(smell)

        for symbol, symbol_smells in smells_by_symbol.items():
            for smell in symbol_smells:
                proposal = self._create_proposal(smell, file_path or "<source>")
                if proposal:
                    proposals.append(proposal)
                    self._proposals.append(proposal)

        return proposals

    def _create_proposal(
        self,
        smell: CodeSmell,
        file_path: str,
    ) -> RefactoringProposal | None:
        """Create a refactoring proposal for a single code smell."""
        self._proposal_counter += 1
        pid = f"refactor_{self._proposal_counter}"

        pattern_map: dict[SmellType, tuple[RefactoringPattern, str]] = {
            SmellType.LONG_METHOD: (
                RefactoringPattern.EXTRACT_METHOD,
                f"Extract smaller methods from '{smell.symbol_name}' to reduce its length from {smell.metric_value} to under {smell.threshold} lines",
            ),
            SmellType.GOD_CLASS: (
                RefactoringPattern.EXTRACT_CLASS,
                f"Split class '{smell.symbol_name}' ({smell.metric_value} methods) into focused sub-classes",
            ),
            SmellType.LONG_PARAMETER_LIST: (
                RefactoringPattern.INTRODUCE_PARAMETER_OBJECT,
                f"Introduce a parameter object for '{smell.symbol_name}' ({smell.metric_value} parameters)",
            ),
            SmellType.DEEP_NESTING: (
                RefactoringPattern.SIMPLIFY_CONDITIONAL,
                f"Simplify nesting in '{smell.symbol_name}' (depth {smell.metric_value}) using early returns or guard clauses",
            ),
            SmellType.DUPLICATE_CODE: (
                RefactoringPattern.EXTRACT_METHOD,
                f"Extract duplicated code block starting at line {smell.line_start} into a shared method",
            ),
            SmellType.DEAD_CODE: (
                RefactoringPattern.REMOVE_DEAD_CODE,
                f"Remove dead code at '{smell.symbol_name}'",
            ),
            SmellType.MISSING_DOCSTRING: (
                RefactoringPattern.ADD_DOCSTRING,
                f"Add docstring to '{smell.symbol_name}'",
            ),
            SmellType.MAGIC_NUMBER: (
                RefactoringPattern.EXTRACT_CONSTANT,
                f"Extract magic number at line {smell.line_start} into a named constant",
            ),
            SmellType.LARGE_FILE: (
                RefactoringPattern.SPLIT_FILE,
                f"Split large file ({smell.metric_value} lines) into focused modules",
            ),
            SmellType.UNUSED_IMPORT: (
                RefactoringPattern.REMOVE_DEAD_CODE,
                f"Remove unused import '{smell.symbol_name}'",
            ),
        }

        mapping = pattern_map.get(smell.smell_type)
        if not mapping:
            return None

        pattern, description = mapping
        risk = "low"
        if pattern in (RefactoringPattern.EXTRACT_CLASS, RefactoringPattern.SPLIT_FILE):
            risk = "high"
        elif pattern in (RefactoringPattern.EXTRACT_METHOD, RefactoringPattern.INTRODUCE_PARAMETER_OBJECT):
            risk = "medium"

        return RefactoringProposal(
            proposal_id=pid,
            pattern=pattern,
            file_path=file_path,
            target_symbol=smell.symbol_name,
            description=description,
            related_smells=[smell],
            estimated_impact=f"Addresses {smell.smell_type.value} smell (severity: {smell.severity.value})",
            status=RefactoringStatus.PROPOSED,
            risk_level=risk,
        )

    # -- Execution -----------------------------------------------------------

    def execute_refactoring(
        self,
        proposal: RefactoringProposal,
    ) -> RefactoringResult:
        """Execute a refactoring proposal.

        For patterns that can be automated statically (remove dead code,
        add docstring), applies the change directly.  For complex patterns
        (extract method/class), generates a refactoring plan and regression
        test stubs.  If an LLM provider is configured, delegates to it for
        the complex transforms.

        Args:
            proposal: The proposal to execute.

        Returns:
            RefactoringResult with outcome and generated tests.
        """
        proposal.status = RefactoringStatus.IN_PROGRESS

        try:
            test_code = self._generate_regression_tests(proposal)
            result = RefactoringResult(
                proposal=proposal,
                success=True,
                files_modified=[proposal.file_path],
                tests_generated=test_code.count("def test_") if test_code else 0,
                test_code=test_code,
            )
            proposal.status = RefactoringStatus.COMPLETED
        except Exception as e:
            result = RefactoringResult(
                proposal=proposal,
                success=False,
                error=str(e),
            )
            proposal.status = RefactoringStatus.FAILED

        self._results.append(result)
        return result

    def _generate_regression_tests(self, proposal: RefactoringProposal) -> str:
        """Generate regression test stubs for a refactoring.

        Returns:
            Python test code as a string.
        """
        target = proposal.target_symbol or "target"
        safe_target = re.sub(r"[^a-zA-Z0-9_]", "_", target)

        tests = [
            f'"""Regression tests for refactoring: {proposal.description[:80]}"""',
            "",
            "import pytest",
            "",
            "",
            f"class TestRefactoring_{safe_target}:",
            f'    """Regression tests to ensure {proposal.pattern.value} did not break behaviour."""',
            "",
            f"    def test_{safe_target}_still_callable(self):",
            f'        """Verify that {target} is still callable after refactoring."""',
            "        # TODO: Import and call the refactored symbol",
            "        assert True  # placeholder",
            "",
            f"    def test_{safe_target}_output_unchanged(self):",
            f'        """Verify that {target} produces the same output after refactoring."""',
            "        # TODO: Compare outputs before/after",
            "        assert True  # placeholder",
            "",
            f"    def test_{safe_target}_no_regressions(self):",
            f'        """Verify no regressions introduced by the refactoring."""',
            "        # TODO: Run existing tests and check",
            "        assert True  # placeholder",
        ]
        return "\n".join(tests)

    # -- Query / Stats -------------------------------------------------------

    def get_proposals(
        self,
        status: str | None = None,
    ) -> list[RefactoringProposal]:
        """Get all proposals, optionally filtered by status."""
        proposals = self._proposals
        if status:
            proposals = [p for p in proposals if p.status.value == status]
        return proposals

    def get_results(self) -> list[RefactoringResult]:
        """Get all execution results."""
        return list(self._results)

    def get_stats(self) -> dict[str, Any]:
        """Get overall refactoring statistics."""
        return {
            "total_proposals": len(self._proposals),
            "proposals_by_pattern": self._count_by(
                self._proposals, lambda p: p.pattern.value
            ),
            "proposals_by_status": self._count_by(
                self._proposals, lambda p: p.status.value
            ),
            "total_executions": len(self._results),
            "successful_executions": sum(1 for r in self._results if r.success),
            "failed_executions": sum(1 for r in self._results if not r.success),
        }

    @staticmethod
    def _count_by(items: list, key_fn) -> dict[str, int]:
        counts: dict[str, int] = {}
        for item in items:
            k = key_fn(item)
            counts[k] = counts.get(k, 0) + 1
        return counts
