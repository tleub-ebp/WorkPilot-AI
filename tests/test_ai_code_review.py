"""Tests for Feature 3.3 — Code review assisté par IA.

Tests for AICodeReviewer, ReviewComment, DiffFile, ReviewResult,
ReviewRule, diff parsing, static analysis, scoring, and LLM integration.

40 tests total:
- ReviewComment: 2
- DiffFile: 3
- ReviewResult: 4
- ReviewRule: 3
- parse_unified_diff: 5
- AICodeReviewer rules: 3
- AICodeReviewer review_diff: 8
- AICodeReviewer review_file_content: 3
- AICodeReviewer scoring: 3
- AICodeReviewer LLM integration: 3
- AICodeReviewer stats: 3
"""

import sys
import os
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apps.backend.review.ai_code_review import (
    AICodeReviewer,
    BUILTIN_RULES,
    DiffFile,
    ReviewCategory,
    ReviewComment,
    ReviewResult,
    ReviewRule,
    ReviewSeverity,
    parse_unified_diff,
    _detect_language,
)


# -----------------------------------------------------------------------
# Sample diffs for testing
# -----------------------------------------------------------------------

SAMPLE_DIFF = """\
diff --git a/src/auth.py b/src/auth.py
--- a/src/auth.py
+++ b/src/auth.py
@@ -10,6 +10,12 @@ class AuthService:
     def login(self, username, password):
+        result = eval(username)
+        password = "hardcoded_secret_123"
+        try:
+            pass
+        except:
+            pass
         return True
"""

SAMPLE_DIFF_JS = """\
diff --git a/app.js b/app.js
--- a/app.js
+++ b/app.js
@@ -1,4 +1,8 @@
+console.log("debug");
+document.innerHTML = userInput;
 function main() {
+    // TODO: refactor this
     return true;
 }
"""

SAMPLE_DIFF_CLEAN = """\
diff --git a/utils.py b/utils.py
--- a/utils.py
+++ b/utils.py
@@ -1,3 +1,5 @@
+def add(a: int, b: int) -> int:
+    return a + b
 def existing():
     pass
"""


# -----------------------------------------------------------------------
# ReviewComment
# -----------------------------------------------------------------------

class TestReviewComment:
    def test_create_comment(self):
        comment = ReviewComment(
            file_path="test.py", line=10,
            severity=ReviewSeverity.WARNING,
            category=ReviewCategory.BUG_RISK,
            message="Potential bug",
        )
        assert comment.file_path == "test.py"
        assert comment.severity == ReviewSeverity.WARNING

    def test_comment_to_dict(self):
        comment = ReviewComment(
            file_path="x.py", line=5,
            severity=ReviewSeverity.ERROR,
            category=ReviewCategory.SECURITY,
            message="Issue found", suggestion="Fix it",
            rule_id="SEC001",
        )
        d = comment.to_dict()
        assert d["severity"] == "error"
        assert d["category"] == "security"
        assert d["rule_id"] == "SEC001"


# -----------------------------------------------------------------------
# DiffFile
# -----------------------------------------------------------------------

class TestDiffFile:
    def test_create_diff_file(self):
        df = DiffFile(file_path="test.py", language="python")
        assert df.file_path == "test.py"
        assert df.total_changes == 0

    def test_diff_file_counts(self):
        df = DiffFile(
            file_path="test.py",
            added_lines={1: "line1", 2: "line2"},
            removed_lines={3: "old"},
        )
        assert df.total_additions == 2
        assert df.total_deletions == 1
        assert df.total_changes == 3

    def test_diff_file_new_file(self):
        df = DiffFile(file_path="new.py", is_new_file=True)
        assert df.is_new_file is True


# -----------------------------------------------------------------------
# ReviewResult
# -----------------------------------------------------------------------

class TestReviewResult:
    def test_empty_result(self):
        result = ReviewResult()
        assert result.overall_score == 100
        assert result.has_critical_issues is False
        assert result.error_count == 0

    def test_result_with_critical_issues(self):
        result = ReviewResult(
            comments=[
                ReviewComment("x.py", 1, ReviewSeverity.CRITICAL, ReviewCategory.SECURITY, "bad"),
            ],
        )
        assert result.has_critical_issues is True
        assert result.error_count == 1

    def test_result_warning_count(self):
        result = ReviewResult(
            comments=[
                ReviewComment("x.py", 1, ReviewSeverity.WARNING, ReviewCategory.STYLE, "w1"),
                ReviewComment("x.py", 2, ReviewSeverity.WARNING, ReviewCategory.STYLE, "w2"),
                ReviewComment("x.py", 3, ReviewSeverity.INFO, ReviewCategory.STYLE, "info"),
            ],
        )
        assert result.warning_count == 2

    def test_result_to_dict(self):
        result = ReviewResult(overall_score=85, files_reviewed=2, summary="Good")
        d = result.to_dict()
        assert d["overall_score"] == 85
        assert d["files_reviewed"] == 2
        assert "timestamp" in d


# -----------------------------------------------------------------------
# ReviewRule
# -----------------------------------------------------------------------

class TestReviewRule:
    def test_rule_applies_to_all(self):
        rule = ReviewRule(
            rule_id="X", pattern="test", message="msg",
            severity=ReviewSeverity.INFO, category=ReviewCategory.STYLE,
        )
        assert rule.applies_to("python") is True
        assert rule.applies_to("javascript") is True

    def test_rule_applies_to_specific(self):
        rule = ReviewRule(
            rule_id="X", pattern="test", message="msg",
            severity=ReviewSeverity.INFO, category=ReviewCategory.STYLE,
            languages=["python"],
        )
        assert rule.applies_to("python") is True
        assert rule.applies_to("javascript") is False

    def test_builtin_rules_exist(self):
        assert len(BUILTIN_RULES) > 0
        for rule in BUILTIN_RULES:
            assert rule.rule_id
            assert rule.pattern
            assert rule.message


# -----------------------------------------------------------------------
# parse_unified_diff
# -----------------------------------------------------------------------

class TestParseUnifiedDiff:
    def test_parse_python_diff(self):
        files = parse_unified_diff(SAMPLE_DIFF)
        assert len(files) == 1
        assert files[0].file_path == "src/auth.py"
        assert files[0].total_additions > 0

    def test_parse_js_diff(self):
        files = parse_unified_diff(SAMPLE_DIFF_JS)
        assert len(files) == 1
        assert files[0].language == "javascript"

    def test_parse_clean_diff(self):
        files = parse_unified_diff(SAMPLE_DIFF_CLEAN)
        assert len(files) == 1
        assert files[0].total_additions == 2

    def test_parse_empty_diff(self):
        files = parse_unified_diff("")
        assert len(files) == 0

    def test_detect_language(self):
        assert _detect_language("test.py") == "python"
        assert _detect_language("app.js") == "javascript"
        assert _detect_language("main.ts") == "typescript"
        assert _detect_language("unknown.xyz") == ""


# -----------------------------------------------------------------------
# AICodeReviewer — Rules
# -----------------------------------------------------------------------

class TestReviewerRules:
    def test_get_all_rules(self):
        reviewer = AICodeReviewer()
        rules = reviewer.get_rules()
        assert len(rules) > 0

    def test_get_rules_by_language(self):
        reviewer = AICodeReviewer()
        python_rules = reviewer.get_rules(language="python")
        js_rules = reviewer.get_rules(language="javascript")
        # There should be some overlap and some differences
        assert len(python_rules) > 0
        assert len(js_rules) > 0

    def test_add_custom_rule(self):
        reviewer = AICodeReviewer()
        initial_count = len(reviewer.get_rules())
        reviewer.add_rule(ReviewRule(
            rule_id="CUSTOM001", pattern=r"debug_mode\s*=\s*True",
            message="Debug mode enabled", severity=ReviewSeverity.WARNING,
            category=ReviewCategory.BEST_PRACTICE,
        ))
        assert len(reviewer.get_rules()) == initial_count + 1


# -----------------------------------------------------------------------
# AICodeReviewer — review_diff
# -----------------------------------------------------------------------

class TestReviewerDiff:
    def test_review_diff_detects_eval(self):
        reviewer = AICodeReviewer()
        result = reviewer.review_diff(SAMPLE_DIFF, language="python")
        eval_comments = [c for c in result.comments if c.rule_id == "SEC001"]
        assert len(eval_comments) >= 1

    def test_review_diff_detects_hardcoded_secret(self):
        reviewer = AICodeReviewer()
        result = reviewer.review_diff(SAMPLE_DIFF, language="python")
        secret_comments = [c for c in result.comments if c.rule_id == "SEC002"]
        assert len(secret_comments) >= 1

    def test_review_diff_detects_bare_except(self):
        reviewer = AICodeReviewer()
        result = reviewer.review_diff(SAMPLE_DIFF, language="python")
        except_comments = [c for c in result.comments if c.rule_id == "BUG001"]
        assert len(except_comments) >= 1

    def test_review_diff_js_detects_console_log(self):
        reviewer = AICodeReviewer()
        result = reviewer.review_diff(SAMPLE_DIFF_JS, language="javascript")
        console_comments = [c for c in result.comments if c.rule_id == "BUG003"]
        assert len(console_comments) >= 1

    def test_review_diff_js_detects_innerhtml(self):
        reviewer = AICodeReviewer()
        result = reviewer.review_diff(SAMPLE_DIFF_JS, language="javascript")
        xss_comments = [c for c in result.comments if c.rule_id == "SEC004"]
        assert len(xss_comments) >= 1

    def test_review_clean_diff_high_score(self):
        reviewer = AICodeReviewer()
        result = reviewer.review_diff(SAMPLE_DIFF_CLEAN, language="python")
        assert result.overall_score >= 80

    def test_review_diff_has_summary(self):
        reviewer = AICodeReviewer()
        result = reviewer.review_diff(SAMPLE_DIFF)
        assert result.summary
        assert "Score:" in result.summary

    def test_review_diff_files_reviewed_count(self):
        reviewer = AICodeReviewer()
        result = reviewer.review_diff(SAMPLE_DIFF)
        assert result.files_reviewed == 1


# -----------------------------------------------------------------------
# AICodeReviewer — review_file_content
# -----------------------------------------------------------------------

class TestReviewerFileContent:
    def test_review_python_file(self):
        code = """
def MyBadFunction():
    result = eval("something")
    try:
        pass
    except:
        pass
"""
        reviewer = AICodeReviewer()
        result = reviewer.review_file_content(code, file_path="bad.py", language="python")
        assert len(result.comments) > 0
        assert result.files_reviewed == 1

    def test_review_clean_file(self):
        code = """
def add(a: int, b: int) -> int:
    \"\"\"Add two numbers.\"\"\"
    return a + b
"""
        reviewer = AICodeReviewer()
        result = reviewer.review_file_content(code, file_path="clean.py", language="python")
        # Should have very few or no issues
        error_comments = [c for c in result.comments if c.severity in (ReviewSeverity.ERROR, ReviewSeverity.CRITICAL)]
        assert len(error_comments) == 0

    def test_review_file_detects_language_from_path(self):
        code = "console.log('hello');"
        reviewer = AICodeReviewer()
        result = reviewer.review_file_content(code, file_path="app.js")
        # Should detect JavaScript and apply JS rules
        console_comments = [c for c in result.comments if c.rule_id == "BUG003"]
        assert len(console_comments) >= 1


# -----------------------------------------------------------------------
# AICodeReviewer — Scoring
# -----------------------------------------------------------------------

class TestReviewerScoring:
    def test_perfect_score_no_issues(self):
        reviewer = AICodeReviewer()
        result = reviewer.review_diff(SAMPLE_DIFF_CLEAN, language="python")
        # Clean code should score high
        assert result.overall_score >= 80

    def test_low_score_many_issues(self):
        reviewer = AICodeReviewer()
        result = reviewer.review_diff(SAMPLE_DIFF, language="python")
        # Code with eval, hardcoded secrets, bare except should score low
        assert result.overall_score < 80

    def test_category_scores_present(self):
        reviewer = AICodeReviewer()
        result = reviewer.review_diff(SAMPLE_DIFF, language="python")
        assert len(result.category_scores) > 0
        assert "security" in result.category_scores


# -----------------------------------------------------------------------
# AICodeReviewer — LLM integration
# -----------------------------------------------------------------------

class TestReviewerLLM:
    def test_review_without_llm(self):
        reviewer = AICodeReviewer(llm_provider=None)
        result = reviewer.review_with_llm(SAMPLE_DIFF)
        # Should still return static analysis results
        assert result.files_reviewed > 0

    def test_review_with_llm_provider(self):
        mock_llm = MagicMock()
        mock_llm.generate.return_value = (
            "- LINE: 12\n"
            "- SEVERITY: warning\n"
            "- CATEGORY: design\n"
            "- MESSAGE: Consider extracting this into a separate method\n"
            "- SUGGESTION: Use dependency injection"
        )
        reviewer = AICodeReviewer(llm_provider=mock_llm)
        result = reviewer.review_with_llm(SAMPLE_DIFF)
        # Should have both static and LLM comments
        llm_comments = [c for c in result.comments if c.rule_id == "LLM"]
        assert len(llm_comments) >= 1

    def test_review_with_llm_failure_graceful(self):
        mock_llm = MagicMock()
        mock_llm.generate.side_effect = Exception("LLM unavailable")
        reviewer = AICodeReviewer(llm_provider=mock_llm)
        result = reviewer.review_with_llm(SAMPLE_DIFF)
        # Should still return static analysis results
        assert result.files_reviewed > 0


# -----------------------------------------------------------------------
# AICodeReviewer — Stats & History
# -----------------------------------------------------------------------

class TestReviewerStats:
    def test_review_history(self):
        reviewer = AICodeReviewer()
        reviewer.review_diff(SAMPLE_DIFF)
        reviewer.review_diff(SAMPLE_DIFF_CLEAN)
        history = reviewer.get_review_history()
        assert len(history) == 2

    def test_stats(self):
        reviewer = AICodeReviewer()
        reviewer.review_diff(SAMPLE_DIFF)
        stats = reviewer.get_stats()
        assert stats["total_reviews"] == 1
        assert stats["total_rules"] > 0
        assert stats["total_findings"] > 0

    def test_stats_avg_score(self):
        reviewer = AICodeReviewer()
        reviewer.review_diff(SAMPLE_DIFF_CLEAN, language="python")
        reviewer.review_diff(SAMPLE_DIFF, language="python")
        stats = reviewer.get_stats()
        assert stats["avg_score"] > 0
        assert stats["total_reviews"] == 2
