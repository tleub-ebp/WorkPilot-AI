"""Tests for Feature 2.1 — Agent de refactoring autonome.

Tests for RefactoringAgent, SmellDetector, CodeSmell, RefactoringProposal,
RefactoringResult, and all smell detection heuristics.

40 tests total:
- CodeSmell: 2
- RefactoringProposal: 2
- RefactoringResult: 2
- SmellDetector — long method: 3
- SmellDetector — god class: 2
- SmellDetector — parameters: 2
- SmellDetector — nesting: 2
- SmellDetector — missing docstring: 2
- SmellDetector — large file: 2
- SmellDetector — unused imports: 2
- SmellDetector — duplicates: 2
- SmellDetector — magic numbers: 2
- RefactoringAgent — detect smells: 3
- RefactoringAgent — proposals: 5
- RefactoringAgent — execution: 3
- RefactoringAgent — stats: 4
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apps.backend.agents.refactorer import (
    CodeSmell,
    RefactoringAgent,
    RefactoringPattern,
    RefactoringProposal,
    RefactoringResult,
    RefactoringStatus,
    SmellDetector,
    SmellSeverity,
    SmellType,
)

# -----------------------------------------------------------------------
# CodeSmell
# -----------------------------------------------------------------------

class TestCodeSmell:
    def test_create_code_smell(self):
        smell = CodeSmell(
            smell_type=SmellType.LONG_METHOD,
            severity=SmellSeverity.HIGH,
            file_path="f.py",
            line_start=10,
            line_end=80,
            message="Method too long",
            symbol_name="process_data",
            metric_value=70,
            threshold=30,
        )
        assert smell.smell_type == SmellType.LONG_METHOD
        assert smell.metric_value == 70

    def test_code_smell_to_dict(self):
        smell = CodeSmell(
            smell_type=SmellType.GOD_CLASS,
            severity=SmellSeverity.HIGH,
            file_path="f.py",
            symbol_name="BigClass",
        )
        d = smell.to_dict()
        assert d["smell_type"] == "god_class"
        assert d["severity"] == "high"


# -----------------------------------------------------------------------
# RefactoringProposal
# -----------------------------------------------------------------------

class TestRefactoringProposal:
    def test_create_proposal(self):
        proposal = RefactoringProposal(
            proposal_id="r1",
            pattern=RefactoringPattern.EXTRACT_METHOD,
            file_path="f.py",
            target_symbol="long_func",
        )
        assert proposal.pattern == RefactoringPattern.EXTRACT_METHOD
        assert proposal.status == RefactoringStatus.PROPOSED

    def test_proposal_to_dict(self):
        proposal = RefactoringProposal(
            proposal_id="r1",
            pattern=RefactoringPattern.EXTRACT_CLASS,
            file_path="f.py",
        )
        d = proposal.to_dict()
        assert d["pattern"] == "extract_class"
        assert d["status"] == "proposed"


# -----------------------------------------------------------------------
# RefactoringResult
# -----------------------------------------------------------------------

class TestRefactoringResult:
    def test_create_result(self):
        proposal = RefactoringProposal(
            proposal_id="r1",
            pattern=RefactoringPattern.EXTRACT_METHOD,
            file_path="f.py",
        )
        result = RefactoringResult(proposal=proposal, success=True)
        assert result.success is True
        assert result.timestamp != ""

    def test_result_to_dict(self):
        proposal = RefactoringProposal(
            proposal_id="r1",
            pattern=RefactoringPattern.RENAME,
            file_path="f.py",
        )
        result = RefactoringResult(proposal=proposal, success=False, error="Failed")
        d = result.to_dict()
        assert d["success"] is False
        assert d["error"] == "Failed"


# -----------------------------------------------------------------------
# SmellDetector — long method
# -----------------------------------------------------------------------

class TestSmellDetectorLongMethod:
    def test_detects_long_method(self):
        source = "def long_func():\n" + "    x = 1\n" * 40
        detector = SmellDetector(thresholds={"max_method_lines": 30})
        smells = detector.detect_from_source(source, "f.py")
        long_methods = [s for s in smells if s.smell_type == SmellType.LONG_METHOD]
        assert len(long_methods) >= 1
        assert long_methods[0].symbol_name == "long_func"

    def test_no_smell_short_method(self):
        source = "def short_func():\n    return 1\n"
        detector = SmellDetector()
        smells = detector.detect_from_source(source, "f.py")
        long_methods = [s for s in smells if s.smell_type == SmellType.LONG_METHOD]
        assert len(long_methods) == 0

    def test_long_method_severity_scales(self):
        source = "def very_long():\n" + "    x = 1\n" * 80
        detector = SmellDetector(thresholds={"max_method_lines": 30})
        smells = detector.detect_from_source(source, "f.py")
        long_methods = [s for s in smells if s.smell_type == SmellType.LONG_METHOD]
        assert len(long_methods) >= 1
        assert long_methods[0].severity == SmellSeverity.HIGH


# -----------------------------------------------------------------------
# SmellDetector — god class
# -----------------------------------------------------------------------

class TestSmellDetectorGodClass:
    def test_detects_god_class(self):
        methods = "\n".join(f"    def method_{i}(self):\n        pass\n" for i in range(20))
        source = f"class BigClass:\n{methods}"
        detector = SmellDetector(thresholds={"max_class_methods": 15})
        smells = detector.detect_from_source(source, "f.py")
        god_classes = [s for s in smells if s.smell_type == SmellType.GOD_CLASS]
        assert len(god_classes) >= 1

    def test_no_god_class_small(self):
        source = "class SmallClass:\n    def method_a(self):\n        pass\n"
        detector = SmellDetector()
        smells = detector.detect_from_source(source, "f.py")
        god_classes = [s for s in smells if s.smell_type == SmellType.GOD_CLASS]
        assert len(god_classes) == 0


# -----------------------------------------------------------------------
# SmellDetector — parameters
# -----------------------------------------------------------------------

class TestSmellDetectorParameters:
    def test_detects_long_param_list(self):
        source = "def func(a, b, c, d, e, f, g):\n    pass\n"
        detector = SmellDetector(thresholds={"max_parameters": 5})
        smells = detector.detect_from_source(source, "f.py")
        param_smells = [s for s in smells if s.smell_type == SmellType.LONG_PARAMETER_LIST]
        assert len(param_smells) >= 1

    def test_no_smell_few_params(self):
        source = "def func(a, b):\n    pass\n"
        detector = SmellDetector()
        smells = detector.detect_from_source(source, "f.py")
        param_smells = [s for s in smells if s.smell_type == SmellType.LONG_PARAMETER_LIST]
        assert len(param_smells) == 0


# -----------------------------------------------------------------------
# SmellDetector — nesting
# -----------------------------------------------------------------------

class TestSmellDetectorNesting:
    def test_detects_deep_nesting(self):
        source = (
            "def deep():\n"
            "    if True:\n"
            "        for i in range(10):\n"
            "            while True:\n"
            "                if True:\n"
            "                    if True:\n"
            "                        pass\n"
        )
        detector = SmellDetector(thresholds={"max_nesting_depth": 4})
        smells = detector.detect_from_source(source, "f.py")
        nesting_smells = [s for s in smells if s.smell_type == SmellType.DEEP_NESTING]
        assert len(nesting_smells) >= 1

    def test_no_deep_nesting(self):
        source = "def flat():\n    if True:\n        pass\n"
        detector = SmellDetector()
        smells = detector.detect_from_source(source, "f.py")
        nesting_smells = [s for s in smells if s.smell_type == SmellType.DEEP_NESTING]
        assert len(nesting_smells) == 0


# -----------------------------------------------------------------------
# SmellDetector — missing docstring
# -----------------------------------------------------------------------

class TestSmellDetectorDocstring:
    def test_detects_missing_docstring(self):
        source = "def public_func():\n    pass\n"
        detector = SmellDetector()
        smells = detector.detect_from_source(source, "f.py")
        doc_smells = [s for s in smells if s.smell_type == SmellType.MISSING_DOCSTRING]
        assert len(doc_smells) >= 1

    def test_no_smell_with_docstring(self):
        source = 'def documented():\n    """This is documented."""\n    pass\n'
        detector = SmellDetector()
        smells = detector.detect_from_source(source, "f.py")
        doc_smells = [s for s in smells if s.smell_type == SmellType.MISSING_DOCSTRING and s.symbol_name == "documented"]
        assert len(doc_smells) == 0


# -----------------------------------------------------------------------
# SmellDetector — large file
# -----------------------------------------------------------------------

class TestSmellDetectorLargeFile:
    def test_detects_large_file(self):
        source = "x = 1\n" * 600
        detector = SmellDetector(thresholds={"max_file_lines": 500})
        smells = detector.detect_from_source(source, "f.py")
        large = [s for s in smells if s.smell_type == SmellType.LARGE_FILE]
        assert len(large) >= 1

    def test_no_large_file(self):
        source = "x = 1\n" * 10
        detector = SmellDetector()
        smells = detector.detect_from_source(source, "f.py")
        large = [s for s in smells if s.smell_type == SmellType.LARGE_FILE]
        assert len(large) == 0


# -----------------------------------------------------------------------
# SmellDetector — unused imports
# -----------------------------------------------------------------------

class TestSmellDetectorUnusedImports:
    def test_detects_unused_import(self):
        source = "import os\nimport sys\nprint(sys.argv)\n"
        detector = SmellDetector()
        smells = detector.detect_from_source(source, "f.py")
        unused = [s for s in smells if s.smell_type == SmellType.UNUSED_IMPORT and s.symbol_name == "os"]
        assert len(unused) >= 1

    def test_no_unused_import(self):
        source = "import os\nprint(os.getcwd())\n"
        detector = SmellDetector()
        smells = detector.detect_from_source(source, "f.py")
        unused = [s for s in smells if s.smell_type == SmellType.UNUSED_IMPORT and s.symbol_name == "os"]
        assert len(unused) == 0


# -----------------------------------------------------------------------
# SmellDetector — duplicates
# -----------------------------------------------------------------------

class TestSmellDetectorDuplicates:
    def test_detects_duplicate_block(self):
        block = "    x = 1\n    y = 2\n    z = 3\n    a = 4\n    b = 5\n    c = 6\n"
        source = f"def func1():\n{block}\ndef func2():\n{block}"
        detector = SmellDetector(thresholds={"min_duplicate_lines": 6})
        smells = detector.detect_from_source(source, "f.py")
        dups = [s for s in smells if s.smell_type == SmellType.DUPLICATE_CODE]
        assert len(dups) >= 1

    def test_no_duplicates(self):
        source = "def func1():\n    x = 1\n\ndef func2():\n    y = 2\n"
        detector = SmellDetector()
        smells = detector.detect_from_source(source, "f.py")
        dups = [s for s in smells if s.smell_type == SmellType.DUPLICATE_CODE]
        assert len(dups) == 0


# -----------------------------------------------------------------------
# SmellDetector — magic numbers
# -----------------------------------------------------------------------

class TestSmellDetectorMagicNumbers:
    def test_detects_magic_number(self):
        source = "def func():\n    timeout = 42\n    return timeout\n"
        detector = SmellDetector()
        smells = detector.detect_from_source(source, "f.py")
        magic = [s for s in smells if s.smell_type == SmellType.MAGIC_NUMBER]
        assert len(magic) >= 1

    def test_no_magic_for_safe_numbers(self):
        source = "def func():\n    x = 0\n    y = 1\n    return x + y\n"
        detector = SmellDetector()
        smells = detector.detect_from_source(source, "f.py")
        magic = [s for s in smells if s.smell_type == SmellType.MAGIC_NUMBER]
        assert len(magic) == 0


# -----------------------------------------------------------------------
# RefactoringAgent — detect smells
# -----------------------------------------------------------------------

class TestRefactoringAgentDetection:
    def test_detect_smells_from_source(self):
        source = "def long_func():\n" + "    x = 1\n" * 40
        agent = RefactoringAgent(thresholds={"max_method_lines": 30})
        smells = agent.detect_smells_from_source(source)
        assert len(smells) > 0

    def test_detect_empty_source(self):
        agent = RefactoringAgent()
        smells = agent.detect_smells_from_source("")
        assert len(smells) == 0

    def test_detect_syntax_error(self):
        agent = RefactoringAgent()
        smells = agent.detect_smells_from_source("def broken(:\n  pass")
        assert isinstance(smells, list)


# -----------------------------------------------------------------------
# RefactoringAgent — proposals
# -----------------------------------------------------------------------

class TestRefactoringAgentProposals:
    def test_propose_from_smells(self):
        source = "def long_func():\n" + "    x = 1\n" * 40
        agent = RefactoringAgent(thresholds={"max_method_lines": 30})
        proposals = agent.propose_refactoring(source=source)
        assert len(proposals) > 0

    def test_proposal_pattern_for_long_method(self):
        source = "def long_func():\n" + "    x = 1\n" * 40
        agent = RefactoringAgent(thresholds={"max_method_lines": 30})
        proposals = agent.propose_refactoring(source=source)
        extract_method = [p for p in proposals if p.pattern == RefactoringPattern.EXTRACT_METHOD]
        assert len(extract_method) >= 1

    def test_proposal_for_god_class(self):
        methods = "\n".join(f"    def m_{i}(self):\n        pass\n" for i in range(20))
        source = f"class Big:\n{methods}"
        agent = RefactoringAgent(thresholds={"max_class_methods": 15})
        proposals = agent.propose_refactoring(source=source)
        extract_class = [p for p in proposals if p.pattern == RefactoringPattern.EXTRACT_CLASS]
        assert len(extract_class) >= 1

    def test_proposal_has_description(self):
        source = "def long_func():\n" + "    x = 1\n" * 40
        agent = RefactoringAgent(thresholds={"max_method_lines": 30})
        proposals = agent.propose_refactoring(source=source)
        assert all(p.description for p in proposals)

    def test_no_proposals_clean_code(self):
        source = '"""Module."""\ndef clean():\n    """Docstring."""\n    return 1\n'
        agent = RefactoringAgent(thresholds={"max_method_lines": 100, "max_file_lines": 1000})
        proposals = agent.propose_refactoring(source=source)
        # May have some info-level suggestions like magic numbers but no major refactoring
        major = [p for p in proposals if p.risk_level in ("medium", "high")]
        assert len(major) == 0


# -----------------------------------------------------------------------
# RefactoringAgent — execution
# -----------------------------------------------------------------------

class TestRefactoringAgentExecution:
    def test_execute_refactoring(self):
        source = "def long_func():\n" + "    x = 1\n" * 40
        agent = RefactoringAgent(thresholds={"max_method_lines": 30})
        proposals = agent.propose_refactoring(source=source)
        result = agent.execute_refactoring(proposals[0])
        assert result.success is True
        assert result.tests_generated >= 1

    def test_execute_generates_test_code(self):
        source = "def long_func():\n" + "    x = 1\n" * 40
        agent = RefactoringAgent(thresholds={"max_method_lines": 30})
        proposals = agent.propose_refactoring(source=source)
        result = agent.execute_refactoring(proposals[0])
        assert "def test_" in result.test_code
        assert "Regression tests" in result.test_code

    def test_execute_updates_status(self):
        source = "def long_func():\n" + "    x = 1\n" * 40
        agent = RefactoringAgent(thresholds={"max_method_lines": 30})
        proposals = agent.propose_refactoring(source=source)
        agent.execute_refactoring(proposals[0])
        assert proposals[0].status == RefactoringStatus.COMPLETED


# -----------------------------------------------------------------------
# RefactoringAgent — stats
# -----------------------------------------------------------------------

class TestRefactoringAgentStats:
    def test_stats_empty(self):
        agent = RefactoringAgent()
        stats = agent.get_stats()
        assert stats["total_proposals"] == 0

    def test_stats_after_proposals(self):
        source = "def long_func():\n" + "    x = 1\n" * 40
        agent = RefactoringAgent(thresholds={"max_method_lines": 30})
        agent.propose_refactoring(source=source)
        stats = agent.get_stats()
        assert stats["total_proposals"] > 0

    def test_stats_after_execution(self):
        source = "def long_func():\n" + "    x = 1\n" * 40
        agent = RefactoringAgent(thresholds={"max_method_lines": 30})
        proposals = agent.propose_refactoring(source=source)
        agent.execute_refactoring(proposals[0])
        stats = agent.get_stats()
        assert stats["total_executions"] == 1
        assert stats["successful_executions"] == 1

    def test_get_proposals_by_status(self):
        source = "def long_func():\n" + "    x = 1\n" * 40
        agent = RefactoringAgent(thresholds={"max_method_lines": 30})
        proposals = agent.propose_refactoring(source=source)
        agent.execute_refactoring(proposals[0])
        proposed = agent.get_proposals(status="proposed")
        completed = agent.get_proposals(status="completed")
        assert len(completed) == 1
