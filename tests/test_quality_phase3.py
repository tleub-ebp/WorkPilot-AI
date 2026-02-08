"""Tests for Phase 3 - Multi-language"""

import sys
import tempfile
from pathlib import Path

import pytest

# Ajouter le backend au path
sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend"))

from review.quality_autofix import AutoFix, AutoFixEngine
from review.quality_extended import ExtendedQualityScorer
from review.quality_multilang import (
    CSharpAnalyzer,
    GoAnalyzer,
    JavaAnalyzer,
    KotlinAnalyzer,
    RustAnalyzer,
    get_analyzer,
)
from review.quality_scorer import IssueSeverity, QualityCategory, QualityIssue


@pytest.fixture
def temp_project():
    """Crée un projet temporaire pour les tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        yield project_dir


class TestMultiLanguageSupport:
    """Tests pour le support multi-langages."""

    def test_java_analyzer(self, temp_project):
        """Test analyseur Java."""
        java_file = temp_project / "Test.java"
        java_file.write_text("""
public class Test {
    public void method() {
        System.out.println("Debug");
        String password = "hardcoded123";
        try {
            doSomething();
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
        """)
        
        analyzer = JavaAnalyzer()
        issues = analyzer.analyze(java_file, java_file.read_text())
        
        assert len(issues) >= 3
        assert any('println' in i.title.lower() for i in issues)
        assert any('password' in i.title.lower() or 'credential' in i.title.lower() for i in issues)
        assert any('Exception' in i.title for i in issues)

    def test_kotlin_analyzer(self, temp_project):
        """Test analyseur Kotlin."""
        kt_file = temp_project / "Test.kt"
        kt_file.write_text("""
fun main() {
    println("Debug")
    val result = getValue()!!
    try {
        doSomething()
    } catch (e: Exception) {
        println(e)
    }
}
        """)
        
        analyzer = KotlinAnalyzer()
        issues = analyzer.analyze(kt_file, kt_file.read_text())
        
        assert len(issues) >= 3
        assert any('println' in i.title.lower() for i in issues)
        assert any('!!' in i.title for i in issues)
        assert any('Exception' in i.title for i in issues)

    def test_csharp_analyzer(self, temp_project):
        """Test analyseur C#."""
        cs_file = temp_project / "Test.cs"
        cs_file.write_text("""
public class Test {
    public void Method() {
        Console.WriteLine("Debug");
        string connectionString = "Server=localhost;Database=db;";
        try {
            DoSomething();
        } catch (Exception ex) {
            Console.WriteLine(ex);
        }
    }
}
        """)
        
        analyzer = CSharpAnalyzer()
        issues = analyzer.analyze(cs_file, cs_file.read_text())
        
        assert len(issues) >= 2
        assert any('console' in i.title.lower() for i in issues)
        assert any('Exception' in i.title for i in issues)

    def test_go_analyzer(self, temp_project):
        """Test analyseur Go."""
        go_file = temp_project / "main.go"
        go_file.write_text("""
package main

import "fmt"

func main() {
    fmt.Println("Debug")
    err := doSomething()
    _ = err
    if err != nil {
        panic(err)
    }
}
        """)
        
        analyzer = GoAnalyzer()
        issues = analyzer.analyze(go_file, go_file.read_text())
        
        assert len(issues) >= 2
        assert any('println' in i.title.lower() for i in issues)
        assert any('panic' in i.title.lower() or 'error' in i.title.lower() for i in issues)

    def test_rust_analyzer(self, temp_project):
        """Test analyseur Rust."""
        rs_file = temp_project / "main.rs"
        rs_file.write_text("""
fn main() {
    println!("Debug");
    let value = get_value().unwrap();
    let other = get_other().expect("Failed");
    if value < 0 {
        panic!("Invalid value");
    }
}
        """)
        
        analyzer = RustAnalyzer()
        issues = analyzer.analyze(rs_file, rs_file.read_text())
        
        assert len(issues) >= 3
        assert any('println' in i.title.lower() for i in issues)
        assert any('unwrap' in i.title.lower() for i in issues)
        assert any('panic' in i.title.lower() for i in issues)

    def test_get_analyzer(self):
        """Test sélection d'analyseur par extension."""
        assert isinstance(get_analyzer(Path("test.java")), JavaAnalyzer)
        assert isinstance(get_analyzer(Path("test.kt")), KotlinAnalyzer)
        assert isinstance(get_analyzer(Path("test.cs")), CSharpAnalyzer)
        assert isinstance(get_analyzer(Path("test.go")), GoAnalyzer)
        assert isinstance(get_analyzer(Path("test.rs")), RustAnalyzer)
        assert get_analyzer(Path("test.unknown")) is None


class TestExtendedQualityScorer:
    """Tests pour le scorer étendu."""

    def test_extended_scorer_java(self, temp_project):
        """Test scoring d'un fichier Java."""
        java_file = temp_project / "Test.java"
        java_file.write_text("""
public class Test {
    public void method() {
        System.out.println("Debug");
        String password = "secret123";
    }
}
        """)
        
        scorer = ExtendedQualityScorer(temp_project)
        score = scorer.score_pr("", ["Test.java"], "")
        
        assert score.total_issues > 0
        assert score.critical_issues > 0  # password hardcodée

    def test_extended_scorer_kotlin(self, temp_project):
        """Test scoring d'un fichier Kotlin."""
        kt_file = temp_project / "Test.kt"
        kt_file.write_text("""
fun main() {
    val result = getValue()!!
    println("Debug: $result")
}
        """)
        
        scorer = ExtendedQualityScorer(temp_project)
        score = scorer.score_pr("", ["Test.kt"], "")
        
        assert score.total_issues >= 2


class TestAutoFixEngine:
    """Tests pour l'auto-fix engine."""

    def test_generate_fixes_bare_except(self, temp_project):
        """Test génération fix pour bare except."""
        py_file = temp_project / "test.py"
        py_file.write_text("""
try:
    do_something()
except:
    pass
""")
        
        issue = QualityIssue(
            category=QualityCategory.BUGS,
            severity=IssueSeverity.MEDIUM,
            title="bare except handler",
            description="Test",
            file="test.py",
            line=3,
            suggestion="Use except Exception",
        )
        
        engine = AutoFixEngine(temp_project)
        fixes = engine.generate_fixes([issue])
        
        assert len(fixes) == 1
        assert 'except Exception' in fixes[0].fixed_line

    def test_generate_fixes_console_log(self, temp_project):
        """Test génération fix pour console.log."""
        js_file = temp_project / "test.js"
        js_file.write_text("""
function debug() {
    console.log("Debug message");
}
""")
        
        issue = QualityIssue(
            category=QualityCategory.MAINTAINABILITY,
            severity=IssueSeverity.LOW,
            title="console.log detected",
            description="Test",
            file="test.js",
            line=2,
            suggestion="Remove console.log",
        )
        
        engine = AutoFixEngine(temp_project)
        fixes = engine.generate_fixes([issue])
        
        assert len(fixes) == 1
        assert '// console.log' in fixes[0].fixed_line

    def test_apply_fixes_dry_run(self, temp_project):
        """Test application fixes en dry run."""
        py_file = temp_project / "test.py"
        original_content = """
try:
    do_something()
except:
    pass
"""
        py_file.write_text(original_content)
        
        issue = QualityIssue(
            category=QualityCategory.BUGS,
            severity=IssueSeverity.MEDIUM,
            title="bare except handler",
            description="Test",
            file="test.py",
            line=4,
            suggestion="Use except Exception",
        )
        
        engine = AutoFixEngine(temp_project)
        fixes = engine.generate_fixes([issue])
        result = engine.apply_fixes(fixes, dry_run=True)
        
        assert result['dry_run'] is True
        assert result['total_fixes'] > 0
        assert py_file.read_text() == original_content  # Pas modifié

    def test_apply_fixes_real(self, temp_project):
        """Test application fixes réelle."""
        py_file = temp_project / "test.py"
        py_file.write_text("""try:
    do_something()
except:
    pass""")
        
        issue = QualityIssue(
            category=QualityCategory.BUGS,
            severity=IssueSeverity.MEDIUM,
            title="bare except handler",
            description="Test",
            file="test.py",
            line=3,
            suggestion="Use except Exception",
        )
        
        engine = AutoFixEngine(temp_project)
        fixes = engine.generate_fixes([issue])
        result = engine.apply_fixes(fixes, dry_run=False, min_confidence=0.5)
        
        assert result['applied'] > 0
        content = py_file.read_text()
        assert 'except Exception' in content

    def test_preview_fixes(self, temp_project):
        """Test preview des fixes."""
        py_file = temp_project / "test.py"
        py_file.write_text("""
try:
    do_something()
except:
    pass
""")
        
        issue = QualityIssue(
            category=QualityCategory.BUGS,
            severity=IssueSeverity.MEDIUM,
            title="bare except handler",
            description="Test",
            file="test.py",
            line=4,
            suggestion="Use except Exception",
        )
        
        engine = AutoFixEngine(temp_project)
        preview = engine.preview_fixes([issue])
        
        assert 'Auto-Fix Preview' in preview
        assert 'Before' in preview
        assert 'After' in preview
        assert 'Confidence' in preview


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

