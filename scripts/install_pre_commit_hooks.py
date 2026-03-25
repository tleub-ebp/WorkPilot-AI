#!/usr/bin/env python3
"""
Script to install pre-commit hooks for the project.
Run this script after installing dependencies to set up automatic code formatting.
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"\n🔧 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
        print(f"✅ {description} completed successfully")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(f"Error: {e.stderr}")
        return False


def main():
    """Install pre-commit hooks."""
    print("🚀 Setting up pre-commit hooks for automatic code formatting...")
    
    # Check if we're in the right directory
    if not Path(".pre-commit-config.yaml").exists():
        print("❌ Error: .pre-commit-config.yaml not found in current directory")
        print("Please run this script from the project root directory")
        sys.exit(1)
    
    # Install pre-commit if not available
    try:
        subprocess.run(["pre-commit", "--version"], capture_output=True, check=True)
        print("✅ pre-commit is already installed")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("📦 Installing pre-commit...")
        if not run_command(f"{sys.executable} -m pip install pre-commit", "Installing pre-commit"):
            sys.exit(1)
    
    # Install the hooks
    if not run_command("pre-commit install", "Installing pre-commit hooks"):
        sys.exit(1)
    
    # Install pre-commit commit-msg hook (optional)
    if not run_command("pre-commit install --hook-type commit-msg", "Installing commit-msg hook"):
        print("⚠️  Warning: Could not install commit-msg hook (this is optional)")
    
    print("\n🎉 Pre-commit hooks installed successfully!")
    print("\n📋 What's been set up:")
    print("   • Automatic ruff linting and fixing for backend code")
    print("   • Automatic ruff formatting for backend code")
    print("   • Hooks will run automatically before each commit")
    print("\n💡 To run hooks manually on all files:")
    print("   pre-commit run --all-files")
    print("\n💡 To skip hooks (not recommended):")
    print("   git commit --no-verify")


if __name__ == "__main__":
    main()
