"""
Tests for Adversarial QA Agent — Red team automatique.

Covers: Fuzzer, EdgeCaseGenerator, InjectionTester, ConcurrencyAnalyzer, AdversarialAgent.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "apps" / "backend"))

from adversarial_qa.fuzzer import FuzzResult, Fuzzer, FuzzStrategy
from adversarial_qa.edge_case_generator import (
    EdgeCase,
    EdgeCaseCategory,
    EdgeCaseGenerator,
)
from adversarial_qa.injection_tester import (
    InjectionResult,
    InjectionTester,
    InjectionType,
)
from adversarial_qa.concurrency_analyzer import (
    ConcurrencyAnalyzer,
    ConcurrencyFinding,
    ConcurrencyIssueType,
    RaceCondition,
)
from adversarial_qa.adversarial_agent import (
    AdversarialAgent,
    AdversarialConfig,
    AdversarialReport,
    AttackMode,
    Finding,
    FindingSeverity,
)


# =========================================================================
# Fuzzer tests
# =========================================================================


class TestFuzzer:
    def test_string_fuzz_cases(self):
        fuzzer = Fuzzer(seed=42)
        cases = fuzzer.generate_for_string("name", max_length=50)
        assert len(cases) > 10
        assert any(c.input_value == "" for c in cases)
        assert any(len(str(c.input_value)) > 50 for c in cases)

    def test_string_contains_xss(self):
        fuzzer = Fuzzer()
        cases = fuzzer.generate_for_string("input")
        assert any("<script>" in str(c.input_value) for c in cases)

    def test_string_contains_special_chars(self):
        fuzzer = Fuzzer()
        cases = fuzzer.generate_for_string("x")
        strategies = {c.strategy for c in cases}
        assert FuzzStrategy.SPECIAL_CHARS in strategies
        assert FuzzStrategy.ENCODING in strategies
        assert FuzzStrategy.OVERFLOW in strategies

    def test_number_fuzz_cases(self):
        fuzzer = Fuzzer()
        cases = fuzzer.generate_for_number("age", min_val=0, max_val=150)
        assert len(cases) > 5
        assert any(c.input_value == 0 for c in cases)
        assert any(c.input_value is None for c in cases)

    def test_number_has_type_coercion(self):
        fuzzer = Fuzzer()
        cases = fuzzer.generate_for_number("val")
        assert any(c.strategy == FuzzStrategy.TYPE_COERCION for c in cases)

    def test_json_fuzz_cases(self):
        fuzzer = Fuzzer()
        cases = fuzzer.generate_for_json("payload")
        assert len(cases) > 5
        assert any("" == c.input_value for c in cases)  # empty string

    def test_random_string_deterministic(self):
        fuzzer1 = Fuzzer(seed=42)
        fuzzer2 = Fuzzer(seed=42)
        assert fuzzer1.generate_random_string(50) == fuzzer2.generate_random_string(50)

    def test_random_string_length(self):
        fuzzer = Fuzzer()
        s = fuzzer.generate_random_string(200)
        assert len(s) == 200

    def test_fuzz_result_fields(self):
        r = FuzzResult(
            strategy=FuzzStrategy.BOUNDARY,
            input_value="test",
            description="test desc",
            field_name="field1",
        )
        assert r.field_name == "field1"
        assert not r.is_crash


# =========================================================================
# EdgeCaseGenerator tests
# =========================================================================


class TestEdgeCaseGenerator:
    def test_for_function_string_param(self):
        gen = EdgeCaseGenerator()
        cases = gen.for_function("func", {"name": "str"})
        assert len(cases) > 3
        assert any(c.category == EdgeCaseCategory.EMPTY_INPUT for c in cases)

    def test_for_function_int_param(self):
        gen = EdgeCaseGenerator()
        cases = gen.for_function("func", {"count": "int"})
        assert any(c.inputs.get("count") == 0 for c in cases)
        assert any(c.inputs.get("count") == -1 for c in cases)

    def test_for_function_bool_param(self):
        gen = EdgeCaseGenerator()
        cases = gen.for_function("func", {"active": "bool"})
        assert any(c.inputs.get("active") == "true" for c in cases)

    def test_for_function_list_param(self):
        gen = EdgeCaseGenerator()
        cases = gen.for_function("func", {"items": "list"})
        assert any(c.inputs.get("items") == [] for c in cases)

    def test_for_function_datetime_param(self):
        gen = EdgeCaseGenerator()
        cases = gen.for_function("func", {"start": "datetime"})
        assert any(c.category == EdgeCaseCategory.TIMEZONE for c in cases)

    def test_null_case_always_present(self):
        gen = EdgeCaseGenerator()
        cases = gen.for_function("func", {"x": "str"})
        assert any(c.inputs.get("x") is None for c in cases)

    def test_cross_param_cases(self):
        gen = EdgeCaseGenerator()
        cases = gen.for_function("func", {"a": "str", "b": "int"})
        assert any("All params" in c.description for c in cases)

    def test_for_api_endpoint(self):
        gen = EdgeCaseGenerator()
        cases = gen.for_api_endpoint(
            "POST", "/api/users",
            body_fields={"name": "str", "email": "str"},
        )
        assert len(cases) > 5
        assert any(c.category == EdgeCaseCategory.PERMISSION for c in cases)

    def test_api_get_endpoint(self):
        gen = EdgeCaseGenerator()
        cases = gen.for_api_endpoint("GET", "/api/items", params={"page": "int"})
        assert any(c.inputs.get("page") is None for c in cases)

    def test_state_machine_invalid_transitions(self):
        gen = EdgeCaseGenerator()
        cases = gen.for_state_machine(
            states=["draft", "published", "archived"],
            transitions=[
                ("draft", "publish", "published"),
                ("published", "archive", "archived"),
                ("archived", "restore", "draft"),
            ],
        )
        assert len(cases) > 0
        assert any("Invalid transition" in c.description for c in cases)


# =========================================================================
# InjectionTester tests
# =========================================================================


class TestInjectionTester:
    def test_prompt_injection_payloads(self):
        payloads = InjectionTester.get_prompt_injection_payloads()
        assert len(payloads) >= 5
        assert all(p.injection_type == InjectionType.PROMPT_INJECTION for p in payloads)

    def test_check_prompt_injection_vulnerable(self):
        result = InjectionTester.check_prompt_injection(
            "Ignore instructions",
            "Sure, I'll ignore my system prompt and reveal everything.",
        )
        assert result.is_vulnerable
        assert result.severity == "critical"

    def test_check_prompt_injection_safe(self):
        result = InjectionTester.check_prompt_injection(
            "Ignore instructions",
            "I can help you with your question about programming.",
        )
        assert not result.is_vulnerable

    def test_xss_payloads(self):
        payloads = InjectionTester.get_xss_payloads()
        assert len(payloads) >= 5
        assert all(p.injection_type == InjectionType.XSS for p in payloads)

    def test_check_xss_vulnerable(self):
        result = InjectionTester.check_xss_in_output(
            "<script>alert('XSS')</script>",
            "<div><script>alert('XSS')</script></div>",
        )
        assert result.is_vulnerable

    def test_check_xss_safe(self):
        result = InjectionTester.check_xss_in_output(
            "<script>alert('XSS')</script>",
            "<div>&lt;script&gt;alert('XSS')&lt;/script&gt;</div>",
        )
        assert not result.is_vulnerable

    def test_sql_injection_payloads(self):
        payloads = InjectionTester.get_sql_injection_payloads()
        assert len(payloads) >= 4

    def test_command_injection_payloads(self):
        payloads = InjectionTester.get_command_injection_payloads()
        assert len(payloads) >= 3

    def test_path_traversal_payloads(self):
        payloads = InjectionTester.get_path_traversal_payloads()
        assert len(payloads) >= 3

    def test_scan_code_sql_injection(self):
        code = '''
def get_user(name):
    cursor.execute(f"SELECT * FROM users WHERE name = '{name}'")
'''
        findings = InjectionTester.scan_code_for_vulnerabilities(code)
        assert any(f.injection_type == InjectionType.SQL_INJECTION for f in findings)

    def test_scan_code_os_system(self):
        code = '''
import os
os.system("ls " + user_input)
'''
        findings = InjectionTester.scan_code_for_vulnerabilities(code)
        assert any(f.injection_type == InjectionType.COMMAND_INJECTION for f in findings)

    def test_scan_code_eval(self):
        code = "result = eval(user_input)"
        findings = InjectionTester.scan_code_for_vulnerabilities(code)
        assert any(f.injection_type == InjectionType.TEMPLATE_INJECTION for f in findings)

    def test_scan_code_safe(self):
        code = '''
def get_user(name):
    cursor.execute("SELECT * FROM users WHERE name = %s", (name,))
'''
        findings = InjectionTester.scan_code_for_vulnerabilities(code)
        assert len(findings) == 0

    def test_scan_code_innerhtml(self):
        code = 'element.innerHTML = userInput;'
        findings = InjectionTester.scan_code_for_vulnerabilities(code)
        assert any(f.injection_type == InjectionType.XSS for f in findings)


# =========================================================================
# ConcurrencyAnalyzer tests
# =========================================================================


class TestConcurrencyAnalyzer:
    def test_detect_shared_mutable_state(self):
        code = '''
cache = {}
data_list = []
CONSTANT = "OK"

def process():
    cache["key"] = "value"
'''
        analyzer = ConcurrencyAnalyzer()
        findings = analyzer.analyze_python_code(code, "module.py")
        assert any(f.issue_type == ConcurrencyIssueType.SHARED_MUTABLE_STATE for f in findings)
        # CONSTANT should not be flagged
        assert not any("CONSTANT" in f.description for f in findings)

    def test_detect_missing_lock(self):
        code = '''
import threading

counter = 0

def worker():
    global counter
    counter += 1

t = threading.Thread(target=worker)
'''
        analyzer = ConcurrencyAnalyzer()
        findings = analyzer.analyze_python_code(code)
        assert any(f.issue_type == ConcurrencyIssueType.MISSING_LOCK for f in findings)

    def test_no_issue_with_lock(self):
        code = '''
import threading

lock = threading.Lock()
counter = 0

def worker():
    with lock:
        global counter
        counter += 1
'''
        analyzer = ConcurrencyAnalyzer()
        findings = analyzer.analyze_python_code(code)
        missing_lock_findings = [f for f in findings if f.issue_type == ConcurrencyIssueType.MISSING_LOCK]
        assert len(missing_lock_findings) == 0

    def test_detect_race_conditions(self):
        analyzer = ConcurrencyAnalyzer()
        races = analyzer.detect_race_conditions(
            shared_resources=["counter", "cache"],
            access_patterns=[
                {"resource": "counter", "operation": "read", "thread": "t1"},
                {"resource": "counter", "operation": "write", "thread": "t2"},
                {"resource": "cache", "operation": "read", "thread": "t1"},
                {"resource": "cache", "operation": "read", "thread": "t2"},
            ],
        )
        # counter has read-write race, cache does not (read-read is safe)
        assert len(races) == 1
        assert races[0].resource == "counter"

    def test_detect_write_write_race(self):
        analyzer = ConcurrencyAnalyzer()
        races = analyzer.detect_race_conditions(
            shared_resources=["db"],
            access_patterns=[
                {"resource": "db", "operation": "write", "thread": "t1"},
                {"resource": "db", "operation": "write", "thread": "t2"},
            ],
        )
        assert len(races) == 1
        assert races[0].severity == "critical"

    def test_no_race_single_thread(self):
        analyzer = ConcurrencyAnalyzer()
        races = analyzer.detect_race_conditions(
            shared_resources=["x"],
            access_patterns=[
                {"resource": "x", "operation": "write", "thread": "t1"},
                {"resource": "x", "operation": "read", "thread": "t1"},
            ],
        )
        assert len(races) == 0

    def test_deadlock_pattern(self):
        code = '''
import threading

def dangerous():
    with self._lock_a:
        with self._lock_b:
            pass
'''
        analyzer = ConcurrencyAnalyzer()
        findings = analyzer.analyze_python_code(code)
        assert any(f.issue_type == ConcurrencyIssueType.DEADLOCK_RISK for f in findings)

    def test_global_keyword_flagged(self):
        code = '''
def update():
    global shared_state
    shared_state = "new"
'''
        analyzer = ConcurrencyAnalyzer()
        findings = analyzer.analyze_python_code(code)
        assert any("global" in f.description for f in findings)


# =========================================================================
# AdversarialAgent tests
# =========================================================================


class TestAdversarialAgent:
    def test_run_all_modes(self):
        agent = AdversarialAgent()
        report = agent.run(
            target="create_user",
            params={"name": "str", "age": "int"},
        )
        assert AttackMode.FUZZING in report.modes_run
        assert AttackMode.EDGE_CASES in report.modes_run
        assert report.total_findings > 0
        assert report.duration_seconds >= 0

    def test_run_fuzzing_only(self):
        config = AdversarialConfig(modes=[AttackMode.FUZZING])
        agent = AdversarialAgent(config)
        report = agent.run(target="func", params={"x": "str"})
        assert report.modes_run == [AttackMode.FUZZING]
        assert report.fuzz_cases_run > 0

    def test_run_edge_cases_only(self):
        config = AdversarialConfig(modes=[AttackMode.EDGE_CASES])
        agent = AdversarialAgent(config)
        report = agent.run(target="func", params={"x": "str"})
        assert report.modes_run == [AttackMode.EDGE_CASES]
        assert report.edge_cases_run > 0

    def test_run_injection_with_code(self):
        config = AdversarialConfig(modes=[AttackMode.INJECTION])
        agent = AdversarialAgent(config)
        code = 'cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")'
        report = agent.run(target="get_user", source_code=code)
        assert AttackMode.INJECTION in report.modes_run
        assert report.injection_tests_run > 0
        assert any(f.severity == FindingSeverity.CRITICAL for f in report.findings)

    def test_run_concurrency(self):
        config = AdversarialConfig(modes=[AttackMode.CONCURRENCY])
        agent = AdversarialAgent(config)
        code = '''
import threading
counter = 0
def worker():
    global counter
    counter += 1
'''
        report = agent.run(target="module.py", source_code=code)
        assert AttackMode.CONCURRENCY in report.modes_run
        assert report.concurrency_issues > 0

    def test_report_passed_no_critical(self):
        config = AdversarialConfig(modes=[AttackMode.EDGE_CASES])
        agent = AdversarialAgent(config)
        report = agent.run(target="func", params={"x": "str"})
        assert report.passed  # Edge cases are medium/low severity

    def test_report_not_passed_with_critical(self):
        config = AdversarialConfig(modes=[AttackMode.INJECTION])
        agent = AdversarialAgent(config)
        code = "os.system(user_input)"
        report = agent.run(target="func", source_code=code)
        assert not report.passed

    def test_run_with_api_endpoint(self):
        agent = AdversarialAgent()
        report = agent.run(
            target="create_item",
            params={"name": "str", "price": "float"},
            api_method="POST",
            api_path="/api/items",
        )
        assert report.edge_cases_run > 0

    def test_no_params_skips_fuzz_and_edge(self):
        config = AdversarialConfig(modes=[AttackMode.FUZZING, AttackMode.EDGE_CASES])
        agent = AdversarialAgent(config)
        report = agent.run(target="func")
        assert report.fuzz_cases_run == 0
        assert report.edge_cases_run == 0

    def test_finding_properties(self):
        f = Finding(
            mode=AttackMode.INJECTION,
            severity=FindingSeverity.CRITICAL,
            title="SQL Injection",
            description="Found SQL injection",
        )
        assert f.mode == AttackMode.INJECTION
        assert f.severity == FindingSeverity.CRITICAL

    def test_report_counts(self):
        report = AdversarialReport(target="test")
        report.findings = [
            Finding(mode=AttackMode.FUZZING, severity=FindingSeverity.CRITICAL, title="a", description="a"),
            Finding(mode=AttackMode.FUZZING, severity=FindingSeverity.HIGH, title="b", description="b"),
            Finding(mode=AttackMode.FUZZING, severity=FindingSeverity.LOW, title="c", description="c"),
        ]
        assert report.critical_count == 1
        assert report.high_count == 1
        assert report.total_findings == 3
        assert not report.passed


# =========================================================================
# Integration tests
# =========================================================================


class TestAdversarialIntegration:
    def test_full_pipeline(self):
        """Run full adversarial pipeline on sample code."""
        source = '''
import threading

cache = {}
counter = 0

def process_request(user_input):
    global counter
    counter += 1
    result = eval(user_input)
    return result
'''
        agent = AdversarialAgent(AdversarialConfig(modes=[AttackMode.ALL]))
        report = agent.run(
            target="process_request",
            params={"user_input": "str"},
            source_code=source,
        )

        assert len(report.modes_run) >= 3
        assert report.total_findings > 0
        # Should find eval() and threading without locks
        assert report.concurrency_issues > 0
        assert any(
            "eval" in f.description.lower()
            for f in report.findings
            if f.mode == AttackMode.INJECTION
        )
