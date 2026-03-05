#!/usr/bin/env python3
"""
Git Hooks for Security Scanning
================================

Automatic security scanning integrated into Git workflows:
- pre-commit: Quick secret scan on staged files
- pre-push: Full security scan before push
- CI/CD integration: Comprehensive scan with reporting

Installation:
    python -m security.git_hooks install

Usage in CI/CD:
    python -m security.git_hooks ci-scan

Part of Feature 8: Security-First Features.
"""

from __future__ import annotations

import sys
from pathlib import Path

from .security_orchestrator import SecurityOrchestrator, SecurityScanConfig


class GitHookManager:
    """Manages Git hooks for security scanning."""

    def __init__(self, repo_path: Path | str):
        """
        Initialize Git hook manager.

        Args:
            repo_path: Path to Git repository
        """
        self.repo_path = Path(repo_path)
        self.git_dir = self.repo_path / ".git"
        self.hooks_dir = self.git_dir / "hooks"

    def install_hooks(self) -> bool:
        """
        Install Git hooks for security scanning.

        Returns:
            True if successful
        """
        if not self.git_dir.exists():
            print("❌ Not a Git repository")
            return False

        self.hooks_dir.mkdir(exist_ok=True)

        # Install pre-commit hook
        pre_commit_installed = self._install_pre_commit_hook()

        # Install pre-push hook
        pre_push_installed = self._install_pre_push_hook()

        if pre_commit_installed and pre_push_installed:
            print("✅ Git hooks installed successfully")
            print()
            print("Installed hooks:")
            print("  - pre-commit: Quick secret scan on staged files")
            print("  - pre-push: Full security scan before push")
            return True
        else:
            print("⚠️ Some hooks failed to install")
            return False

    def uninstall_hooks(self) -> bool:
        """
        Uninstall security scanning Git hooks.

        Returns:
            True if successful
        """
        hooks = ["pre-commit", "pre-push"]
        success = True

        for hook_name in hooks:
            hook_path = self.hooks_dir / hook_name
            if hook_path.exists():
                # Check if it's our hook
                content = hook_path.read_text()
                if "WorkPilot AI Security Scanner" in content:
                    hook_path.unlink()
                    print(f"✅ Removed {hook_name} hook")
                else:
                    print(f"⚠️ {hook_name} hook exists but is not ours - skipping")
                    success = False

        return success

    def _install_pre_commit_hook(self) -> bool:
        """Install pre-commit hook for quick secret scanning."""
        hook_path = self.hooks_dir / "pre-commit"

        # Check if hook already exists
        if hook_path.exists():
            print(f"⚠️ pre-commit hook already exists at {hook_path}")
            response = input("Overwrite? (y/N): ")
            if response.lower() != "y":
                return False

        # Create hook script
        hook_script = """#!/usr/bin/env python3
\"\"\"
WorkPilot AI Security Scanner - Pre-Commit Hook
================================================

Scans staged files for secrets before commit.
\"\"\"

import subprocess
import sys
from pathlib import Path

def get_staged_files():
    \"\"\"Get list of staged files.\"\"\"
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        capture_output=True,
        text=True,
    )
    return [f for f in result.stdout.strip().split("\\n") if f]

def main():
    print("🔒 Running WorkPilot AI security scan on staged files...")
    
    staged_files = get_staged_files()
    if not staged_files:
        print("✅ No files staged for commit")
        return 0
    
    # Import here to avoid startup overhead
    try:
        from security.security_orchestrator import SecurityOrchestrator, SecurityScanConfig
    except ImportError:
        print("⚠️ Security scanner not installed - skipping scan")
        return 0
    
    # Run quick scan on staged files
    config = SecurityScanConfig()
    config.scan_secrets = True
    config.scan_sast = False  # Too slow for pre-commit
    config.scan_dependencies = False
    config.generate_json = False
    config.generate_markdown = False
    config.generate_html = False
    
    orchestrator = SecurityOrchestrator(Path.cwd(), config)
    result = orchestrator.scan_commit(staged_files)
    
    if result.should_block:
        print()
        print("❌ Security issues found - commit blocked!")
        print("Fix the issues above or use 'git commit --no-verify' to bypass")
        return 1
    
    print("✅ Security scan passed")
    return 0

if __name__ == "__main__":
    sys.exit(main())
"""

        try:
            hook_path.write_text(hook_script)
            hook_path.chmod(0o755)  # Make executable
            print(f"✅ Installed pre-commit hook at {hook_path}")
            return True
        except Exception as e:
            print(f"❌ Failed to install pre-commit hook: {e}")
            return False

    def _install_pre_push_hook(self) -> bool:
        """Install pre-push hook for full security scanning."""
        hook_path = self.hooks_dir / "pre-push"

        # Check if hook already exists
        if hook_path.exists():
            print(f"⚠️ pre-push hook already exists at {hook_path}")
            response = input("Overwrite? (y/N): ")
            if response.lower() != "y":
                return False

        # Create hook script
        hook_script = """#!/usr/bin/env python3
\"\"\"
WorkPilot AI Security Scanner - Pre-Push Hook
============================================

Runs full security scan before push.
Can be bypassed with: git push --no-verify
\"\"\"

import sys
from pathlib import Path

def main():
    print("🔒 Running WorkPilot AI full security scan before push...")
    print("(This may take a minute...)")
    print()
    
    # Import here to avoid startup overhead
    try:
        from security.security_orchestrator import SecurityOrchestrator, SecurityScanConfig
    except ImportError:
        print("⚠️ Security scanner not installed - skipping scan")
        return 0
    
    # Run full scan
    config = SecurityScanConfig()
    config.scan_secrets = True
    config.scan_sast = True
    config.scan_dependencies = True
    config.generate_json = True
    config.generate_markdown = True
    config.generate_html = False
    
    orchestrator = SecurityOrchestrator(Path.cwd(), config)
    result = orchestrator.run_full_scan()
    
    if result.should_block:
        print()
        print("❌ Security scan FAILED - push blocked!")
        print("Fix the critical issues or use 'git push --no-verify' to bypass")
        return 1
    
    print()
    print("✅ Security scan passed - proceeding with push")
    return 0

if __name__ == "__main__":
    sys.exit(main())
"""

        try:
            hook_path.write_text(hook_script)
            hook_path.chmod(0o755)  # Make executable
            print(f"✅ Installed pre-push hook at {hook_path}")
            return True
        except Exception as e:
            print(f"❌ Failed to install pre-push hook: {e}")
            return False


def run_ci_scan() -> int:
    """
    Run security scan for CI/CD pipeline.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    print("=" * 80)
    print("WorkPilot AI Security Scanner - CI/CD Mode")
    print("=" * 80)
    print()

    # Full scan with all reports
    config = SecurityScanConfig()
    config.scan_secrets = True
    config.scan_sast = True
    config.scan_dependencies = True
    config.scan_containers = True
    config.generate_json = True
    config.generate_markdown = True
    config.generate_html = True
    config.generate_sarif = True  # For GitHub Security tab
    config.block_on_critical = True

    orchestrator = SecurityOrchestrator(Path.cwd(), config)
    result = orchestrator.run_full_scan()

    # Print summary for CI logs
    print()
    print("=" * 80)
    print("CI/CD Security Scan Summary")
    print("=" * 80)
    summary = result.summary
    print(f"Vulnerabilities: {summary['vulnerabilities']['total']}")
    print(f"  - Critical: {summary['vulnerabilities']['critical']}")
    print(f"  - High: {summary['vulnerabilities']['high']}")
    print(f"  - Medium: {summary['vulnerabilities']['medium']}")
    print(f"  - Low: {summary['vulnerabilities']['low']}")

    if result.compliance_report:
        print(f"Compliance Violations: {summary['compliance']['total']}")
        print(f"  - Critical: {summary['compliance']['critical']}")
        print(f"  - High: {summary['compliance']['high']}")
        print(
            f"  - Status: {'✅ COMPLIANT' if summary['compliance']['is_compliant'] else '❌ NON-COMPLIANT'}"
        )

    print("=" * 80)
    print()

    if result.should_block:
        print("❌ CI/CD Security Scan FAILED")
        print("Critical security issues must be resolved before deployment")
        return 1
    else:
        print("✅ CI/CD Security Scan PASSED")
        return 0


def run_github_action() -> int:
    """
    Run security scan for GitHub Actions.
    Uploads SARIF report to GitHub Security tab.

    Returns:
        Exit code
    """
    print("🔒 Running security scan for GitHub Actions...")

    orchestrator = SecurityOrchestrator(Path.cwd())
    sarif_path = orchestrator.generate_github_security_report()

    print(f"✅ SARIF report generated: {sarif_path}")
    print()
    print("To upload to GitHub Security tab, add to your workflow:")
    print()
    print("    - name: Upload SARIF")
    print("      uses: github/codeql-action/upload-sarif@v2")
    print("      with:")
    print(f"        sarif_file: {sarif_path}")
    print()

    return 0


# =============================================================================
# CLI Interface
# =============================================================================


def main():
    """CLI entry point for Git hooks management."""
    import argparse

    parser = argparse.ArgumentParser(
        description="WorkPilot AI Security Scanner - Git Hooks"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Install command
    install_parser = subparsers.add_parser("install", help="Install Git hooks")
    install_parser.add_argument(
        "--repo-path",
        type=Path,
        default=Path.cwd(),
        help="Path to Git repository (default: current directory)",
    )

    # Uninstall command
    uninstall_parser = subparsers.add_parser("uninstall", help="Uninstall Git hooks")
    uninstall_parser.add_argument(
        "--repo-path",
        type=Path,
        default=Path.cwd(),
        help="Path to Git repository (default: current directory)",
    )

    # CI scan command
    ci_parser = subparsers.add_parser("ci-scan", help="Run CI/CD security scan")

    # GitHub Action command
    github_parser = subparsers.add_parser(
        "github-action", help="Run security scan for GitHub Actions"
    )

    args = parser.parse_args()

    if args.command == "install":
        manager = GitHookManager(args.repo_path)
        success = manager.install_hooks()
        return 0 if success else 1

    elif args.command == "uninstall":
        manager = GitHookManager(args.repo_path)
        success = manager.uninstall_hooks()
        return 0 if success else 1

    elif args.command == "ci-scan":
        return run_ci_scan()

    elif args.command == "github-action":
        return run_github_action()

    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())

