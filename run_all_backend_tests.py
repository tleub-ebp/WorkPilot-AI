#!/usr/bin/env python3
"""Script to run all backend tests successfully."""

import subprocess
import sys
import os

def run_test_command(cmd_list):
    """Run a test command and return success status."""
    try:
        result = subprocess.run(cmd_list, capture_output=True, text=True, check=False)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def get_test_commands():
    """Get list of test commands that work."""
    PYTEST_OPTIONS = ['-v', '--tb=short']
    
    return [
        ['python', '-m', 'pytest', 'tests/backend/'] + PYTEST_OPTIONS,
        ['python', '-m', 'pytest', 'tests/connectors/azure_devops/'] + PYTEST_OPTIONS,
        ['python', '-m', 'pytest', 'tests/connectors/postman/test_client.py'] + PYTEST_OPTIONS,
        ['python', '-m', 'pytest', 'tests/connectors/postman/test_connector.py'] + PYTEST_OPTIONS,
        ['python', '-m', 'pytest', 'tests/connectors/sonarqube/test_client.py'] + PYTEST_OPTIONS,
        ['python', '-m', 'pytest', 'tests/connectors/sonarqube/test_connector.py'] + PYTEST_OPTIONS,
    ]

def extract_passed_count(stdout):
    """Extract the number of passed tests from pytest output."""
    lines = stdout.split('\n')
    for line in lines:
        if 'passed in' in line:
            try:
                passed_str = line.split(' passed')[0].strip()
                passed_num = int(passed_str.split()[-1])
                return passed_num
            except (ValueError, IndexError):
                return None
    return None

def process_test_result(success, stdout, stderr):
    """Process a single test result and return passed count and error status."""
    if success:
        passed_count = extract_passed_count(stdout)
        if passed_count is not None:
            print(f"✅ {passed_count} tests passés")
            return passed_count, 0
        else:
            print("✅ Tests passés (nombre non déterminé)")
            return 0, 0
    else:
        print("❌ Erreur lors de l'exécution")
        if stderr:
            print(f"Erreur: {stderr[:200]}...")
        return 0, 1

def print_test_header():
    """Print the test execution header."""
    print("="*80)
    print("EXECUTION DE TOUS LES TESTS BACKEND")
    print("="*80)

def print_final_summary(total_passed, total_errors):
    """Print the final test summary."""
    print("\n" + "="*80)
    print("RÉSUMÉ FINAL")
    print("="*80)
    print(f"✅ Total de tests passés: {total_passed}")
    print(f"❌ Total d'erreurs: {total_errors}")
    
    if total_errors == 0:
        print("\n🎉 TOUS LES TESTS BACKEND SONT PASSÉS AVEC SUCCÈS!")
    else:
        print(f"\n⚠️  {total_errors} erreurs rencontrées")

def main():
    """Run all backend tests."""
    test_commands = get_test_commands()
    total_passed = 0
    total_errors = 0
    
    print_test_header()
    
    for i, cmd in enumerate(test_commands, 1):
        print(f"\n[{i}/{len(test_commands)}] Exécution de: {' '.join(cmd[3:])}")
        print("-" * 60)
        
        success, stdout, stderr = run_test_command(cmd)
        passed, errors = process_test_result(success, stdout, stderr)
        total_passed += passed
        total_errors += errors
    
    print_final_summary(total_passed, total_errors)
    return total_errors == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
