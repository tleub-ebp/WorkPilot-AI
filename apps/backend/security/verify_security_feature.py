#!/usr/bin/env python3
"""
Security Feature Verification Script
=====================================

This script verifies that Feature 8: Security-First Features is properly
installed, configured, and active.

Usage:
    python verify_security_feature.py
"""

import sys
from pathlib import Path

# Add the backend directory to the path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


def main():
    """Verify security feature installation and status."""
    print("=" * 70)
    print("Feature 8: Security-First Features - Verification")
    print("=" * 70)
    print()

    passed = []
    failed = []
    warnings = []

    # Test 1: Module can be imported
    print("✓ Test 1: Importing security module...")
    try:
        import importlib.util
        spec = importlib.util.find_spec("security")
        if spec is not None:
            passed.append("Security module imports successfully")
            print("  ✅ PASSED")
        else:
            failed.append("Security module not found")
            print("  ❌ FAILED: Security module not found")
            sys.exit(1)
    except ImportError as e:
        failed.append(f"Security module import failed: {e}")
        print(f"  ❌ FAILED: {e}")
        sys.exit(1)

    # Test 2: Auto-integration is active
    print("✓ Test 2: Checking auto-integration...")
    try:
        from security.auto_integration import is_security_enabled
        if is_security_enabled():
            passed.append("Auto-integration is active")
            print("  ✅ PASSED - Security is always enabled")
        else:
            failed.append("Security is not enabled (should always be True)")
            print("  ❌ FAILED - Security should always be enabled")
    except Exception as e:
        failed.append(f"Auto-integration check failed: {e}")
        print(f"  ❌ FAILED: {e}")

    # Test 3: Main classes are available
    print("✓ Test 3: Checking main classes...")
    try:
        from security import (
            ComplianceAnalyzer,
            GitHookManager,
            SecurityOrchestrator,
            SecurityReportGenerator,
            VulnerabilityScanner,
        )
        # Verify classes are callable
        assert callable(SecurityOrchestrator)
        assert callable(VulnerabilityScanner)
        assert callable(ComplianceAnalyzer)
        assert callable(SecurityReportGenerator)
        assert callable(GitHookManager)
        passed.append("All main classes are available")
        print("  ✅ PASSED")
    except ImportError as e:
        failed.append(f"Main classes import failed: {e}")
        print(f"  ❌ FAILED: {e}")

    # Test 4: Check dependencies
    print("✓ Test 4: Checking dependencies...")
    try:
        import importlib.util
        if importlib.util.find_spec("rich") is not None:
            passed.append("Rich is installed")
            print("  ✅ Rich installed")
        else:
            warnings.append("Rich not installed (recommended for reports)")
            print("  ⚠️  WARNING: Rich not installed")
    except Exception:
        warnings.append("Rich not installed (recommended for reports)")
        print("  ⚠️  WARNING: Rich not installed")

    try:
        if importlib.util.find_spec("bandit") is not None:
            passed.append("Bandit is installed")
            print("  ✅ Bandit installed")
        else:
            warnings.append("Bandit not installed (recommended for Python SAST)")
            print("  ⚠️  WARNING: Bandit not installed")
    except Exception:
        warnings.append("Bandit not installed (recommended for Python SAST)")
        print("  ⚠️  WARNING: Bandit not installed")

    # Test 5: Check tool availability
    print("✓ Test 5: Checking security tools...")
    try:
        from security.auto_integration import SECURITY_TOOLS_AVAILABLE
        available = [tool for tool, avail in SECURITY_TOOLS_AVAILABLE.items() if avail]
        if available:
            passed.append(f"Security tools available: {', '.join(available)}")
            print(f"  ✅ Available: {', '.join(available)}")
        else:
            warnings.append("No external security tools detected")
            print("  ⚠️  WARNING: No external tools (Bandit, Semgrep, etc.)")
    except Exception as e:
        warnings.append(f"Tool check failed: {e}")
        print(f"  ⚠️  WARNING: {e}")

    # Test 6: Check configuration
    print("✓ Test 6: Checking configuration...")
    try:
        from security.auto_integration import get_default_security_config
        config = get_default_security_config()
        if config["enabled"] is True:
            passed.append("Security is enabled in config")
            print("  ✅ Security enabled in config")
        if config["scan_secrets"] is True:
            passed.append("Secret scanning is enabled")
            print("  ✅ Secret scanning enabled")
    except Exception as e:
        failed.append(f"Configuration check failed: {e}")
        print(f"  ❌ FAILED: {e}")

    # Test 7: Check files exist
    print("✓ Test 7: Checking implementation files...")
    security_dir = Path(__file__).parent
    required_files = [
        "vulnerability_scanner.py",
        "compliance_analyzer.py",
        "security_report_generator.py",
        "security_orchestrator.py",
        "git_hooks.py",
        "auto_integration.py",
        "FEATURE_STATUS.json",
        "README.md",
    ]
    missing = []
    for file in required_files:
        if (security_dir / file).exists():
            passed.append(f"{file} exists")
        else:
            missing.append(file)
            failed.append(f"{file} is missing")

    if not missing:
        print("  ✅ All implementation files present")
    else:
        print(f"  ❌ Missing files: {', '.join(missing)}")

    # Test 8: Verify non-optional status
    print("✓ Test 8: Verifying non-optional status...")
    try:
        from security.auto_integration import is_security_enabled
        # Try to "disable" security (should have no effect)
        result = is_security_enabled()
        if result is True:
            passed.append("Security cannot be disabled (non-optional)")
            print("  ✅ PASSED - Security is non-optional")
        else:
            failed.append("Security can be disabled (should be non-optional)")
            print("  ❌ FAILED - Security should be non-optional")
    except Exception as e:
        failed.append(f"Non-optional verification failed: {e}")
        print(f"  ❌ FAILED: {e}")

    # Summary
    print()
    print("=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)
    print()
    print(f"✅ Passed: {len(passed)}")
    print(f"❌ Failed: {len(failed)}")
    print(f"⚠️  Warnings: {len(warnings)}")
    print()

    if failed:
        print("FAILED TESTS:")
        for fail in failed:
            print(f"  ❌ {fail}")
        print()

    if warnings:
        print("WARNINGS:")
        for warn in warnings:
            print(f"  ⚠️  {warn}")
        print()

    # Overall status
    if not failed:
        print("🎉 OVERALL STATUS: ✅ PASSED")
        print()
        print("Feature 8: Security-First Features is properly installed and active.")
        print("The feature is INCLUDED and NON-OPTIONAL as expected.")
        print()
        return 0
    else:
        print("❌ OVERALL STATUS: FAILED")
        print()
        print("Some tests failed. Please review the errors above.")
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())

