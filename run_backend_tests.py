#!/usr/bin/env python3
"""Script to run all backend tests with proper Python path configuration."""

import sys
import os
import subprocess

def setup_environment():
    """Set up Python path and environment for tests."""
    project_root = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, project_root)
    
    env = os.environ.copy()
    env['PYTHONPATH'] = project_root
    
    return project_root, env

def get_test_commands():
    """Get list of test commands to run."""
    PYTEST_OPTIONS = ['-v', '--tb=short']
    
    return [
        ['python', '-m', 'pytest', 'tests/backend/'] + PYTEST_OPTIONS,
        ['python', '-m', 'pytest', 'tests/connectors/azure_devops/'] + PYTEST_OPTIONS,
        ['python', '-m', 'pytest', 'tests/connectors/postman/'] + PYTEST_OPTIONS,
        ['python', '-m', 'pytest', 'tests/connectors/sonarqube/'] + PYTEST_OPTIONS,
    ]

def extract_passed_count(stdout):
    """Extract the number of passed tests from pytest output."""
    lines = stdout.split('\n')
    for line in lines:
        if 'passed in' in line:
            passed_count = line.split(' passed')[0].strip()
            try:
                return int(passed_count.split()[-1])
            except (ValueError, IndexError):
                pass
    return 0

def run_single_test_command(cmd, project_root, env):
    """Run a single test command and return results."""
    print(f"\n{'='*80}")
    print(f"Running: {' '.join(cmd)}")
    print('='*80)
    
    try:
        result = subprocess.run(cmd, cwd=project_root, env=env, capture_output=True, text=True)
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        if result.returncode == 0:
            passed_count = extract_passed_count(result.stdout)
            return passed_count, 0
        else:
            return 0, 1
            
    except (subprocess.SubprocessError, OSError) as e:
        print(f"Error running command: {e}")
        return 0, 1

def print_summary(total_passed, total_errors):
    """Print the final test summary."""
    print(f"\n{'='*80}")
    print("SUMMARY")
    print('='*80)
    print(f"Total passed: {total_passed}")
    print(f"Total errors: {total_errors}")

def run_backend_tests():
    """Run all backend tests with proper Python path."""
    project_root, env = setup_environment()
    test_commands = get_test_commands()
    
    total_passed = 0
    total_errors = 0
    
    for cmd in test_commands:
        passed, errors = run_single_test_command(cmd, project_root, env)
        total_passed += passed
        total_errors += errors
    
    print_summary(total_passed, total_errors)
    return total_errors == 0

if __name__ == "__main__":
    success = run_backend_tests()
    sys.exit(0 if success else 1)
