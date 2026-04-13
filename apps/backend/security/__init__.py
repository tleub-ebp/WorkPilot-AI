"""
Security Module for Auto-Build Framework
=========================================

Provides comprehensive security features for the WorkPilot AI framework:

1. Command Validation - Dynamic allowlists for bash commands
2. Vulnerability Scanning - Multi-tool security scanning (Bandit, Semgrep, etc.)
3. Secret Detection - Automatic detection of hardcoded credentials
4. Compliance Analysis - GDPR, SOC2, HIPAA, PCI-DSS compliance checking
5. Security Reports - Multiple formats (JSON, HTML, Markdown, SARIF)
6. Git Integration - Automatic scanning via Git hooks
7. CI/CD Integration - Security gates for deployment pipelines

Feature 8: Security-First Features
-----------------------------------
⚠️ IMPORTANT: This feature is INCLUDED and NON-OPTIONAL.
Security scanning is a core safety feature that cannot be disabled.

This module implements the complete Feature 8 roadmap:
- Automatic vulnerability scanning on every commit
- Detection of secrets/credentials in code
- Compliance analysis (GDPR, SOC2, HIPAA, PCI-DSS, ISO 27001, CCPA)
- Automatic generation of security reports
- Integration with Snyk, Dependabot, Bandit, Semgrep, etc.

Public API - Command Validation
--------------------------------
Main functions:
- bash_security_hook: Pre-tool-use hook for command validation
- validate_command: Standalone validation function for testing
- get_security_profile: Get or create security profile for a project
- reset_profile_cache: Reset cached security profile

Command parsing:
- extract_commands: Extract command names from shell strings
- split_command_segments: Split compound commands into segments

Public API - Security Scanning
------------------------------
Main classes:
- SecurityOrchestrator: Main entry point for security scanning
- VulnerabilityScanner: Multi-tool vulnerability scanner
- ComplianceAnalyzer: Compliance framework analyzer
- SecurityReportGenerator: Multi-format report generator
- GitHookManager: Git hooks for automatic scanning

Quick Start:
    from security import SecurityOrchestrator

    orchestrator = SecurityOrchestrator(project_path)
    result = orchestrator.run_full_scan()

    if result.should_block:
        print("Security issues found!")

Validators:
- All validators are available via the VALIDATORS dict
"""

# Import from parent modules
from project_analyzer import (
    BASE_COMMANDS,
    SecurityProfile,
    is_command_allowed,
    needs_validation,
)

from . import auto_integration  # noqa: F401
from .compliance_analyzer import (
    ComplianceAnalyzer,
    ComplianceFramework,
    ComplianceReport,
    ComplianceSeverity,
    ComplianceViolation,
)
from .git_hooks import GitHookManager
from .hooks import bash_security_hook, validate_command
from .parser import (
    extract_commands,
    get_command_for_validation,
    split_command_segments,
)
from .profile import (
    get_security_profile,
    reset_profile_cache,
)
from .secure_subprocess import (
    SubprocessResult,
    SubprocessSecurityError,
    check_tool_available,
    run_secure,
)
from .security_orchestrator import (
    SecurityOrchestrator,
    SecurityScanConfig,
    SecurityScanResult,
)
from .security_report_generator import SecurityReportGenerator
from .tool_input_validator import (
    get_safe_tool_input,
    validate_tool_input,
)
from .validator import (
    VALIDATORS,
    validate_bash_command,
    validate_chmod_command,
    validate_dropdb_command,
    validate_dropuser_command,
    validate_git_command,
    validate_git_commit,
    validate_git_config,
    validate_init_script,
    validate_kill_command,
    validate_killall_command,
    validate_mongosh_command,
    validate_mysql_command,
    validate_mysqladmin_command,
    validate_pkill_command,
    validate_psql_command,
    validate_redis_cli_command,
    validate_rm_command,
    validate_sh_command,
    validate_shell_c_command,
    validate_zsh_command,
)
from .vulnerability_scanner import (
    ScanResult,
    Severity,
    Vulnerability,
    VulnerabilityScanner,
    VulnerabilitySource,
)

__all__ = [
    # Main API
    "bash_security_hook",
    "validate_command",
    "get_security_profile",
    "reset_profile_cache",
    # Parsing utilities
    "extract_commands",
    "split_command_segments",
    "get_command_for_validation",
    # Security-First
    "SecurityOrchestrator",
    "SecurityScanConfig",
    "SecurityScanResult",
    "VulnerabilityScanner",
    "Vulnerability",
    "ScanResult",
    "Severity",
    "VulnerabilitySource",
    "ComplianceAnalyzer",
    "ComplianceFramework",
    "ComplianceViolation",
    "ComplianceReport",
    "ComplianceSeverity",
    "SecurityReportGenerator",
    "GitHookManager",
    # Validators
    "VALIDATORS",
    "validate_pkill_command",
    "validate_kill_command",
    "validate_killall_command",
    "validate_chmod_command",
    "validate_rm_command",
    "validate_init_script",
    "validate_git_command",
    "validate_git_commit",
    "validate_git_config",
    "validate_shell_c_command",
    "validate_bash_command",
    "validate_sh_command",
    "validate_zsh_command",
    "validate_dropdb_command",
    "validate_dropuser_command",
    "validate_psql_command",
    "validate_mysql_command",
    "validate_redis_cli_command",
    "validate_mongosh_command",
    "validate_mysqladmin_command",
    # From project_analyzer
    "SecurityProfile",
    "is_command_allowed",
    "needs_validation",
    "BASE_COMMANDS",
    # Tool input validation
    "validate_tool_input",
    "get_safe_tool_input",
    # Secure subprocess
    "run_secure",
    "SubprocessResult",
    "SubprocessSecurityError",
    "check_tool_available",
    # Prompt Injection Guard
    "InjectionScanner",
    "ScanResult",
    "ThreatLevel",
    "ScanFinding",
    "InjectionClassifier",
    "ClassificationResult",
    "injection_patterns",
]

# Prompt Injection Guard imports
from . import injection_patterns  # noqa: E402
from .injection_classifier import (  # noqa: E402
    ClassificationResult,
    InjectionClassifier,
)
from .injection_scanner import (
    InjectionScanner,
    ScanFinding,
    ThreatLevel,
)  # noqa: E402
from .injection_scanner import (
    ScanResult as InjectionScanResult,
)
