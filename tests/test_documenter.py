"""Tests for Feature 2.2 — Agent de documentation automatique.

Tests for DocumentationAgent, DocAnalyzer, DocGenerator, SymbolDoc,
ModuleInfo, DocGenerationResult, and all generation formats.

40 tests total:
- SymbolDoc: 2
- ModuleInfo: 2
- DocGenerationResult: 2
- DocAnalyzer — file analysis: 5
- DocAnalyzer — directory analysis: 3
- DocGenerator — Google format: 3
- DocGenerator — NumPy format: 2
- DocGenerator — Sphinx format: 2
- DocGenerator — JSDoc format: 2
- DocGenerator — README: 3
- DocGenerator — Mermaid diagrams: 3
- DocumentationAgent — docstrings: 4
- DocumentationAgent — README: 2
- DocumentationAgent — coverage: 3
- DocumentationAgent — stats: 2
"""

import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apps.backend.agents.documenter import (
    DiagramType,
    DocAnalyzer,
    DocFormat,
    DocGenerationResult,
    DocGenerator,
    DocStatus,
    DocumentationAgent,
    ModuleInfo,
    SymbolDoc,
)

# -----------------------------------------------------------------------
# SymbolDoc
# -----------------------------------------------------------------------

class TestSymbolDoc:
    def test_create_symbol_doc(self):
        sym = SymbolDoc(
            name="my_func", symbol_type="function",
            file_path="f.py", line_number=10,
            status=DocStatus.MISSING, args=["x", "y"],
        )
        assert sym.name == "my_func"
        assert sym.status == DocStatus.MISSING
        assert len(sym.args) == 2

    def test_symbol_doc_to_dict(self):
        sym = SymbolDoc(name="MyClass", symbol_type="class", status=DocStatus.DOCUMENTED)
        d = sym.to_dict()
        assert d["status"] == "documented"
        assert d["symbol_type"] == "class"


# -----------------------------------------------------------------------
# ModuleInfo
# -----------------------------------------------------------------------

class TestModuleInfo:
    def test_create_module_info(self):
        info = ModuleInfo(
            module_path="/src/connectors",
            name="connectors",
            files=["__init__.py", "base.py"],
            classes=["BaseConnector"],
        )
        assert info.name == "connectors"
        assert len(info.files) == 2

    def test_module_info_to_dict(self):
        info = ModuleInfo(module_path="/src", name="src")
        d = info.to_dict()
        assert d["name"] == "src"
        assert "files" in d


# -----------------------------------------------------------------------
# DocGenerationResult
# -----------------------------------------------------------------------

class TestDocGenerationResult:
    def test_create_result(self):
        result = DocGenerationResult(
            source_path="f.py",
            symbols_analyzed=10,
            symbols_documented=3,
        )
        assert result.symbols_analyzed == 10
        assert result.symbols_documented == 3

    def test_result_to_dict(self):
        result = DocGenerationResult(source_path="f.py")
        d = result.to_dict()
        assert d["source_path"] == "f.py"
        assert "output_format" in d


# -----------------------------------------------------------------------
# DocAnalyzer — file analysis
# -----------------------------------------------------------------------

SAMPLE_SOURCE = '''
class Calculator:
    """A simple calculator."""

    def add(self, a, b):
        """Add two numbers."""
        return a + b

    def subtract(self, a, b):
        return a - b

    def _internal(self):
        pass

def standalone_func(x, y):
    return x * y

def documented_func(data: list) -> int:
    """Process data and return count."""
    return len(data)
'''


class TestDocAnalyzerFile:
    def test_analyze_source_finds_symbols(self):
        analyzer = DocAnalyzer()
        symbols = analyzer.analyze_source(SAMPLE_SOURCE, "calc.py")
        assert len(symbols) > 0

    def test_analyze_detects_class(self):
        analyzer = DocAnalyzer()
        symbols = analyzer.analyze_source(SAMPLE_SOURCE, "calc.py")
        classes = [s for s in symbols if s.symbol_type == "class"]
        assert len(classes) == 1
        assert classes[0].name == "Calculator"
        assert classes[0].status == DocStatus.DOCUMENTED

    def test_analyze_detects_methods(self):
        analyzer = DocAnalyzer()
        symbols = analyzer.analyze_source(SAMPLE_SOURCE, "calc.py")
        methods = [s for s in symbols if s.symbol_type == "method"]
        assert len(methods) >= 2

    def test_analyze_detects_missing_docstring(self):
        analyzer = DocAnalyzer()
        symbols = analyzer.analyze_source(SAMPLE_SOURCE, "calc.py")
        missing = [s for s in symbols if s.status == DocStatus.MISSING]
        assert len(missing) > 0
        names = [s.name for s in missing]
        assert "standalone_func" in names

    def test_analyze_detects_partial_doc(self):
        source = 'def func_with_args(a, b, c):\n    """Does something."""\n    pass\n'
        analyzer = DocAnalyzer()
        symbols = analyzer.analyze_source(source, "f.py")
        # Has docstring but no Args: section
        partial = [s for s in symbols if s.status == DocStatus.PARTIAL]
        assert len(partial) >= 1


# -----------------------------------------------------------------------
# DocAnalyzer — directory analysis
# -----------------------------------------------------------------------

class TestDocAnalyzerDirectory:
    def test_analyze_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a simple module
            init = os.path.join(tmpdir, "__init__.py")
            with open(init, "w") as f:
                f.write('"""My module."""\n')
            mod = os.path.join(tmpdir, "utils.py")
            with open(mod, "w") as f:
                f.write("def helper():\n    pass\n")

            analyzer = DocAnalyzer()
            info = analyzer.analyze_directory(tmpdir)
            assert info.name != ""
            assert "__init__.py" in info.files
            assert "utils.py" in info.files

    def test_analyze_directory_extracts_description(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            init = os.path.join(tmpdir, "__init__.py")
            with open(init, "w") as f:
                f.write('"""My awesome module."""\n')

            analyzer = DocAnalyzer()
            info = analyzer.analyze_directory(tmpdir)
            assert "My awesome module" in info.description

    def test_analyze_directory_detects_submodules(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sub = os.path.join(tmpdir, "sub")
            os.makedirs(sub)
            with open(os.path.join(sub, "__init__.py"), "w") as f:
                f.write("")

            analyzer = DocAnalyzer()
            info = analyzer.analyze_directory(tmpdir)
            assert "sub" in info.submodules


# -----------------------------------------------------------------------
# DocGenerator — Google format
# -----------------------------------------------------------------------

class TestDocGeneratorGoogle:
    def test_generate_google_docstring(self):
        sym = SymbolDoc(name="my_func", args=["x", "y"], return_type="int")
        gen = DocGenerator()
        doc = gen.generate_docstring(sym, DocFormat.GOOGLE)
        assert "Args:" in doc
        assert "x:" in doc
        assert "Returns:" in doc

    def test_google_no_args(self):
        sym = SymbolDoc(name="no_args_func", args=[], return_type=None)
        gen = DocGenerator()
        doc = gen.generate_docstring(sym, DocFormat.GOOGLE)
        assert "Args:" not in doc

    def test_google_no_return(self):
        sym = SymbolDoc(name="void_func", args=["a"], return_type="None")
        gen = DocGenerator()
        doc = gen.generate_docstring(sym, DocFormat.GOOGLE)
        assert "Returns:" not in doc


# -----------------------------------------------------------------------
# DocGenerator — NumPy format
# -----------------------------------------------------------------------

class TestDocGeneratorNumpy:
    def test_generate_numpy_docstring(self):
        sym = SymbolDoc(name="func", args=["data"], return_type="list")
        gen = DocGenerator()
        doc = gen.generate_docstring(sym, DocFormat.NUMPY)
        assert "Parameters" in doc
        assert "Returns" in doc

    def test_numpy_has_dashes(self):
        sym = SymbolDoc(name="func", args=["x"])
        gen = DocGenerator()
        doc = gen.generate_docstring(sym, DocFormat.NUMPY)
        assert "----------" in doc


# -----------------------------------------------------------------------
# DocGenerator — Sphinx format
# -----------------------------------------------------------------------

class TestDocGeneratorSphinx:
    def test_generate_sphinx_docstring(self):
        sym = SymbolDoc(name="func", args=["x"], return_type="str")
        gen = DocGenerator()
        doc = gen.generate_docstring(sym, DocFormat.SPHINX)
        assert ":param x:" in doc
        assert ":returns:" in doc

    def test_sphinx_has_type(self):
        sym = SymbolDoc(name="func", args=["x"])
        gen = DocGenerator()
        doc = gen.generate_docstring(sym, DocFormat.SPHINX)
        assert ":type x:" in doc


# -----------------------------------------------------------------------
# DocGenerator — JSDoc format
# -----------------------------------------------------------------------

class TestDocGeneratorJSDoc:
    def test_generate_jsdoc(self):
        sym = SymbolDoc(name="myFunc", args=["data"], return_type="Array")
        gen = DocGenerator()
        doc = gen.generate_docstring(sym, DocFormat.JSDOC)
        assert "@param" in doc
        assert "@returns" in doc

    def test_jsdoc_starts_with_comment(self):
        sym = SymbolDoc(name="func")
        gen = DocGenerator()
        doc = gen.generate_docstring(sym, DocFormat.JSDOC)
        assert doc.startswith("/**")
        assert doc.endswith("*/")


# -----------------------------------------------------------------------
# DocGenerator — README
# -----------------------------------------------------------------------

class TestDocGeneratorReadme:
    def test_generate_readme(self):
        info = ModuleInfo(
            module_path="/src/connectors",
            name="connectors",
            description="Connection utilities",
            files=["__init__.py", "base.py"],
            classes=["BaseConnector"],
            functions=["connect"],
        )
        gen = DocGenerator()
        readme = gen.generate_readme(info)
        assert "# connectors" in readme
        assert "Connection utilities" in readme

    def test_readme_has_files_section(self):
        info = ModuleInfo(
            module_path="/src", name="src",
            files=["main.py", "utils.py"],
        )
        gen = DocGenerator()
        readme = gen.generate_readme(info)
        assert "## Files" in readme
        assert "`main.py`" in readme

    def test_readme_has_auto_generated_note(self):
        info = ModuleInfo(module_path="/src", name="src")
        gen = DocGenerator()
        readme = gen.generate_readme(info)
        assert "Auto-generated" in readme


# -----------------------------------------------------------------------
# DocGenerator — Mermaid diagrams
# -----------------------------------------------------------------------

class TestDocGeneratorDiagrams:
    def test_class_diagram(self):
        symbols = [
            SymbolDoc(name="Calculator", symbol_type="class"),
            SymbolDoc(name="Calculator.add", symbol_type="method", args=["a", "b"], return_type="int"),
            SymbolDoc(name="Calculator.sub", symbol_type="method", args=["a", "b"]),
        ]
        gen = DocGenerator()
        diagram = gen.generate_mermaid_class_diagram(symbols)
        assert "classDiagram" in diagram
        assert "Calculator" in diagram

    def test_module_diagram(self):
        info = ModuleInfo(
            module_path="/src", name="mymod",
            submodules=["sub1", "sub2"],
            dependencies=["os", "json"],
        )
        gen = DocGenerator()
        diagram = gen.generate_mermaid_module_diagram(info)
        assert "graph TD" in diagram
        assert "mymod" in diagram

    def test_diagram_has_mermaid_fences(self):
        symbols = [SymbolDoc(name="Foo", symbol_type="class")]
        gen = DocGenerator()
        diagram = gen.generate_mermaid_class_diagram(symbols)
        assert "```mermaid" in diagram
        assert "```" in diagram


# -----------------------------------------------------------------------
# DocumentationAgent — docstrings
# -----------------------------------------------------------------------

class TestDocumentationAgentDocstrings:
    def test_generate_docstrings_from_source(self):
        agent = DocumentationAgent()
        result = agent.generate_docstrings(source=SAMPLE_SOURCE)
        assert result.symbols_analyzed > 0
        assert result.symbols_documented > 0

    def test_generate_docstrings_populates_generated_doc(self):
        agent = DocumentationAgent()
        result = agent.generate_docstrings(source=SAMPLE_SOURCE)
        missing = [d for d in result.generated_docs if d.status == DocStatus.MISSING]
        assert all(d.generated_doc != "" for d in missing)

    def test_generate_docstrings_with_format(self):
        agent = DocumentationAgent(default_format=DocFormat.SPHINX)
        result = agent.generate_docstrings(source=SAMPLE_SOURCE)
        # Check that at least one generated doc uses Sphinx format
        has_sphinx = any(":param" in d.generated_doc for d in result.generated_docs if d.generated_doc)
        assert has_sphinx

    def test_generate_docstrings_empty_source(self):
        agent = DocumentationAgent()
        result = agent.generate_docstrings(source="")
        assert result.symbols_analyzed == 0


# -----------------------------------------------------------------------
# DocumentationAgent — README
# -----------------------------------------------------------------------

class TestDocumentationAgentReadme:
    def test_generate_module_readme(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "__init__.py"), "w") as f:
                f.write('"""Test module."""\n')
            with open(os.path.join(tmpdir, "main.py"), "w") as f:
                f.write("def main():\n    pass\n")

            agent = DocumentationAgent()
            result = agent.generate_module_readme(tmpdir)
            assert result.readme_content != ""
            assert "## Files" in result.readme_content

    def test_readme_includes_diagram(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "__init__.py"), "w") as f:
                f.write("")

            agent = DocumentationAgent()
            result = agent.generate_module_readme(tmpdir)
            assert result.diagram_content != ""


# -----------------------------------------------------------------------
# DocumentationAgent — coverage
# -----------------------------------------------------------------------

class TestDocumentationAgentCoverage:
    def test_check_coverage(self):
        agent = DocumentationAgent()
        coverage = agent.check_documentation_coverage(source=SAMPLE_SOURCE)
        assert coverage["total"] > 0
        assert "documented" in coverage
        assert "missing" in coverage
        assert "coverage_pct" in coverage

    def test_coverage_pct_calculated(self):
        source = '"""Module."""\ndef a():\n    """Doc."""\n    pass\ndef b():\n    pass\n'
        agent = DocumentationAgent()
        coverage = agent.check_documentation_coverage(source=source)
        # a is documented, b is missing
        assert coverage["coverage_pct"] > 0

    def test_coverage_empty(self):
        agent = DocumentationAgent()
        coverage = agent.check_documentation_coverage(source="")
        assert coverage["total"] == 0
        assert coverage["coverage_pct"] == 0.0


# -----------------------------------------------------------------------
# DocumentationAgent — stats
# -----------------------------------------------------------------------

class TestDocumentationAgentStats:
    def test_stats_empty(self):
        agent = DocumentationAgent()
        stats = agent.get_stats()
        assert stats["total_runs"] == 0

    def test_stats_after_runs(self):
        agent = DocumentationAgent()
        agent.generate_docstrings(source=SAMPLE_SOURCE)
        stats = agent.get_stats()
        assert stats["total_runs"] == 1
        assert stats["total_symbols_analyzed"] > 0
        assert stats["total_symbols_documented"] > 0
