#!/usr/bin/env python3
"""
Streaming Test Runner
====================

Script to run all streaming-related tests.
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd, cwd=None, description=""):
    """Run a command and return success status."""
    print(f"\n🚀 {description}")
    print(f"📁 Directory: {cwd or Path.cwd()}")
    print(f"💻 Command: {' '.join(cmd)}")
    print("-" * 60)
    
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.stdout:
            print(result.stdout)
        
        if result.stderr:
            print("STDERR:", result.stderr)
        
        if result.returncode == 0:
            print(f"✅ {description} - PASSED")
            return True
        else:
            print(f"❌ {description} - FAILED (exit code: {result.returncode})")
            return False
            
    except Exception as e:
        print(f"❌ {description} - ERROR: {e}")
        return False

def main():
    """Run all streaming tests."""
    print("🎯 Streaming Live Coding Test Suite")
    print("=" * 60)
    
    project_root = Path(__file__).parent
    backend_path = project_root / "apps" / "backend"
    frontend_path = project_root / "apps" / "frontend"
    
    all_passed = True
    
    # Backend unit tests
    print("\n📦 Backend Unit Tests")
    print("-" * 30)
    
    backend_tests = [
        (["python", "-m", "pytest", "streaming/test_agent_wrapper.py", "-v"],
         backend_path, "Agent Wrapper Tests"),
        (["python", "-m", "pytest", "streaming/test_websocket_server.py", "-v"],
         backend_path, "WebSocket Server Tests"),
        (["python", "-m", "pytest", "streaming/test_cli_integration.py", "-v"],
         backend_path, "CLI Integration Tests"),
    ]
    
    for cmd, cwd, desc in backend_tests:
        if not run_command(cmd, cwd, desc):
            all_passed = False
    
    # End-to-end test
    print("\n🔄 End-to-End Test")
    print("-" * 30)
    
    e2e_cmd = ["python", "test_streaming_e2e.py"]
    if not run_command(e2e_cmd, project_root, "End-to-End Streaming Test"):
        all_passed = False
    
    # Frontend tests (if available)
    print("\n🌐 Frontend Tests")
    print("-" * 30)
    
    # Check if frontend test runner is available
    frontend_test_cmd = ["npm", "test", "--", "--run", "streaming"]
    if (frontend_path / "package.json").exists():
        if not run_command(frontend_test_cmd, frontend_path, "Frontend Streaming Tests"):
            print("⚠️ Frontend tests failed or not available")
    else:
        print("⚠️ Frontend tests not available (no package.json)")
    
    # Summary
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 ALL STREAMING TESTS PASSED!")
        print("✅ The streaming live coding functionality is working correctly!")
        return 0
    else:
        print("❌ SOME TESTS FAILED!")
        print("🔧 Please check the test output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
