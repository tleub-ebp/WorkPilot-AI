"""
Adversarial Agent — Orchestrate all attack modes and produce reports.

Coordinates fuzzer, edge case generator, injection tester, and
concurrency analyzer into a unified adversarial testing pipeline.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum

from .concurrency_analyzer import ConcurrencyAnalyzer
from .edge_case_generator import EdgeCaseGenerator
from .fuzzer import Fuzzer
from .injection_tester import InjectionResult, InjectionTester

logger = logging.getLogger(__name__)


class AttackMode(str, Enum):
    FUZZING = "fuzzing"
    EDGE_CASES = "edge_cases"
    INJECTION = "injection"
    CONCURRENCY = "concurrency"
    ALL = "all"


class FindingSeverity(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Finding:
    """A unified finding from any attack mode."""

    mode: AttackMode
    severity: FindingSeverity
    title: str
    description: str
    evidence: str = ""
    remediation: str = ""
    tags: list[str] = field(default_factory=list)


@dataclass
class AdversarialReport:
    """Complete adversarial testing report."""

    target: str
    modes_run: list[AttackMode] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    fuzz_cases_run: int = 0
    edge_cases_run: int = 0
    injection_tests_run: int = 0
    concurrency_issues: int = 0
    duration_seconds: float = 0.0
    timestamp: float = field(default_factory=time.time)

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == FindingSeverity.CRITICAL)

    @property
    def high_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == FindingSeverity.HIGH)

    @property
    def total_findings(self) -> int:
        return len(self.findings)

    @property
    def passed(self) -> bool:
        return self.critical_count == 0


@dataclass
class AdversarialConfig:
    """Configuration for the adversarial agent."""

    modes: list[AttackMode] = field(default_factory=lambda: [AttackMode.ALL])
    fuzz_seed: int | None = 42
    max_fuzz_cases: int = 100
    scan_code: bool = True


class AdversarialAgent:
    """Orchestrate adversarial testing across all attack modes.

    Usage::

        agent = AdversarialAgent()
        report = agent.run(
            target="create_user",
            params={"name": "str", "age": "int"},
            source_code=source,
        )
        print(f"Found {report.total_findings} issues ({report.critical_count} critical)")
    """

    def __init__(self, config: AdversarialConfig | None = None) -> None:
        self._config = config or AdversarialConfig()
        self._fuzzer = Fuzzer(seed=self._config.fuzz_seed)
        self._edge_gen = EdgeCaseGenerator()
        self._injection = InjectionTester()
        self._concurrency = ConcurrencyAnalyzer()

    def run(
        self,
        target: str,
        params: dict[str, str] | None = None,
        source_code: str | None = None,
        api_method: str | None = None,
        api_path: str | None = None,
    ) -> AdversarialReport:
        """Run adversarial testing and return a report."""
        start = time.time()
        report = AdversarialReport(target=target)
        modes = self._resolve_modes()

        if AttackMode.FUZZING in modes and params:
            report.modes_run.append(AttackMode.FUZZING)
            fuzz_findings, fuzz_count = self._run_fuzzing(params)
            report.findings.extend(fuzz_findings)
            report.fuzz_cases_run = fuzz_count

        if AttackMode.EDGE_CASES in modes and params:
            report.modes_run.append(AttackMode.EDGE_CASES)
            edge_findings, edge_count = self._run_edge_cases(
                target, params, api_method, api_path
            )
            report.findings.extend(edge_findings)
            report.edge_cases_run = edge_count

        if AttackMode.INJECTION in modes:
            report.modes_run.append(AttackMode.INJECTION)
            inj_findings, inj_count = self._run_injection(source_code)
            report.findings.extend(inj_findings)
            report.injection_tests_run = inj_count

        if AttackMode.CONCURRENCY in modes and source_code:
            report.modes_run.append(AttackMode.CONCURRENCY)
            conc_findings = self._run_concurrency(source_code, target)
            report.findings.extend(conc_findings)
            report.concurrency_issues = len(conc_findings)

        report.duration_seconds = time.time() - start
        return report

    def _resolve_modes(self) -> list[AttackMode]:
        if AttackMode.ALL in self._config.modes:
            return [
                AttackMode.FUZZING,
                AttackMode.EDGE_CASES,
                AttackMode.INJECTION,
                AttackMode.CONCURRENCY,
            ]
        return list(self._config.modes)

    def _run_fuzzing(self, params: dict[str, str]) -> tuple[list[Finding], int]:
        """Run fuzzing for each parameter."""
        findings: list[Finding] = []
        count = 0

        for name, ptype in params.items():
            if "str" in ptype.lower():
                cases = self._fuzzer.generate_for_string(name)
            elif "int" in ptype.lower() or "float" in ptype.lower():
                cases = self._fuzzer.generate_for_number(name)
            elif "json" in ptype.lower():
                cases = self._fuzzer.generate_for_json(name)
            else:
                cases = self._fuzzer.generate_for_string(name)

            for case in cases[: self._config.max_fuzz_cases]:
                count += 1
                # Each fuzz case is a potential finding to investigate
                findings.append(
                    Finding(
                        mode=AttackMode.FUZZING,
                        severity=FindingSeverity.LOW,
                        title=f"Fuzz: {case.description}",
                        description=f"Fuzz case for '{name}': {case.description}",
                        tags=["fuzz", case.strategy.value],
                    )
                )

        return findings, count

    def _run_edge_cases(
        self,
        target: str,
        params: dict[str, str],
        api_method: str | None,
        api_path: str | None,
    ) -> tuple[list[Finding], int]:
        """Generate and report edge cases."""
        findings: list[Finding] = []

        if api_method and api_path:
            cases = self._edge_gen.for_api_endpoint(
                api_method, api_path, body_fields=params
            )
        else:
            cases = self._edge_gen.for_function(target, params)

        for case in cases:
            severity = self._map_severity(case.severity)
            findings.append(
                Finding(
                    mode=AttackMode.EDGE_CASES,
                    severity=severity,
                    title=f"Edge: {case.description}",
                    description=case.description,
                    tags=["edge_case", case.category.value],
                )
            )

        return findings, len(cases)

    def _run_injection(self, source_code: str | None) -> tuple[list[Finding], int]:
        """Run injection tests."""
        findings: list[Finding] = []
        count = 0

        # Always generate payload inventory
        all_payloads: list[InjectionResult] = []
        all_payloads.extend(self._injection.get_prompt_injection_payloads())
        all_payloads.extend(self._injection.get_xss_payloads())
        all_payloads.extend(self._injection.get_sql_injection_payloads())
        all_payloads.extend(self._injection.get_command_injection_payloads())
        all_payloads.extend(self._injection.get_path_traversal_payloads())
        count += len(all_payloads)

        # Scan source code if available
        if source_code and self._config.scan_code:
            code_findings = self._injection.scan_code_for_vulnerabilities(source_code)
            for cf in code_findings:
                findings.append(
                    Finding(
                        mode=AttackMode.INJECTION,
                        severity=FindingSeverity.CRITICAL
                        if cf.is_vulnerable
                        else FindingSeverity.MEDIUM,
                        title=f"Injection: {cf.description}",
                        description=cf.description,
                        evidence=cf.evidence,
                        remediation=cf.remediation,
                        tags=["injection", cf.injection_type.value],
                    )
                )
            count += len(code_findings)

        return findings, count

    def _run_concurrency(self, source_code: str, target: str) -> list[Finding]:
        """Run concurrency analysis."""
        findings: list[Finding] = []
        conc_findings = self._concurrency.analyze_python_code(
            source_code, filename=target
        )

        for cf in conc_findings:
            findings.append(
                Finding(
                    mode=AttackMode.CONCURRENCY,
                    severity=self._map_severity(cf.severity),
                    title=f"Concurrency: {cf.description}",
                    description=cf.description,
                    evidence=cf.code_snippet,
                    remediation=cf.suggestion,
                    tags=["concurrency", cf.issue_type.value],
                )
            )

        return findings

    @staticmethod
    def _map_severity(sev: str) -> FindingSeverity:
        mapping = {
            "critical": FindingSeverity.CRITICAL,
            "high": FindingSeverity.HIGH,
            "medium": FindingSeverity.MEDIUM,
            "low": FindingSeverity.LOW,
        }
        return mapping.get(sev.lower(), FindingSeverity.MEDIUM)
