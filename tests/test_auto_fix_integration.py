"""
Quick integration test for auto-fix loop
Run this to verify the feature works
"""
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent / "apps" / "backend"
sys.path.insert(0, str(backend_dir))

def test_imports():
    """Test that all imports work correctly."""
    print("Testing imports...")

    try:
        from qa.auto_fix_loop import (
            AutoFixLoop,
            run_auto_fix_loop,
            DEFAULT_MAX_AUTO_FIX_ATTEMPTS,
            AutoFixTestResult,
            AutoFixAttempt,
        )
        print("✓ auto_fix_loop imports OK")
    except ImportError as e:
        print(f"✗ auto_fix_loop import failed: {e}")
        raise

    try:
        from qa.auto_fix_metrics import (
            AutoFixMetricsTracker,
            AutoFixStats,
            get_auto_fix_stats,
            record_auto_fix_run,
            get_auto_fix_dashboard_data,
            print_auto_fix_summary,
        )
        print("✓ auto_fix_metrics imports OK")
    except ImportError as e:
        print(f"✗ auto_fix_metrics import failed: {e}")
        raise

    try:
        from qa import (
            run_auto_fix_loop,
            AutoFixLoop,
            DEFAULT_MAX_AUTO_FIX_ATTEMPTS,
        )
        print("✓ qa package exports OK")
    except ImportError as e:
        print(f"✗ qa package export failed: {e}")
        raise

    try:
        from qa_loop import (
            run_auto_fix_loop,
            AutoFixLoop,
            DEFAULT_MAX_AUTO_FIX_ATTEMPTS,
        )
        print("✓ qa_loop facade exports OK")
    except ImportError as e:
        print(f"✗ qa_loop facade export failed: {e}")
        raise

def test_classes():
    """Test that classes can be instantiated."""
    print("\nTesting class instantiation...")

    try:
        from qa.auto_fix_loop import AutoFixTestResult, AutoFixAttempt

        # Test AutoFixTestResult
        result = AutoFixTestResult(
            executed=True,
            passed=False,
            output="test output",
            error="test error",
            duration=1.5,
            test_count=5,
            failed_count=2,
        )
        print(f"✓ AutoFixTestResult created: {result.test_count} tests, {result.failed_count} failed")

        # Test AutoFixAttempt
        attempt = AutoFixAttempt(
            attempt_number=1,
            test_result=result,
            fix_applied=True,
            fix_status="fixed",
            duration=30.0,
            error_pattern="assertion_failure",
            timestamp=1234567890.0,
        )
        print(f"✓ AutoFixAttempt created: attempt #{attempt.attempt_number}, status={attempt.fix_status}")
    except Exception as e:
        print(f"✗ Class instantiation failed: {e}")
        raise

def test_metrics():
    """Test metrics tracking."""
    print("\nTesting metrics...")

    try:
        import tempfile
        from qa.auto_fix_metrics import AutoFixMetricsTracker, AutoFixStats

        # Create temp spec dir
        with tempfile.TemporaryDirectory() as tmpdir:
            spec_dir = Path(tmpdir)

            # Create implementation_plan.json
            plan_file = spec_dir / "implementation_plan.json"
            plan_file.write_text('{"spec_name": "test"}')

            tracker = AutoFixMetricsTracker(spec_dir)
            print(f"✓ MetricsTracker created for {spec_dir}")

            # Test recording a run
            tracker.record_run(
                success=True,
                attempts=3,
                duration=45.0,
                error_patterns=["assertion_failure"],
                test_framework="pytest"
            )
            print("✓ Recorded test run")

            # Test loading stats
            stats = tracker.load_stats()
            print(f"✓ Loaded stats: {stats.total_runs} runs, {stats.success_rate*100:.0f}% success rate")

            # Test dashboard data
            dashboard = tracker.get_dashboard_data()
            print(f"✓ Dashboard data: {dashboard['totalRuns']} runs, {dashboard['successRate']}% success")

            # Test summary
            summary = tracker.get_summary()
            print(f"✓ Summary generated ({len(summary)} chars)")
    except Exception as e:
        print(f"✗ Metrics test failed: {e}")
        import traceback
        traceback.print_exc()
        raise

def test_error_patterns():
    """Test error pattern detection."""
    print("\nTesting error pattern detection...")

    try:
        import tempfile
        from qa.auto_fix_loop import AutoFixLoop, AutoFixTestResult

        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            spec_dir = Path(tmpdir) / "spec"
            spec_dir.mkdir()

            # Create implementation_plan.json
            (spec_dir / "implementation_plan.json").write_text('{"spec_name": "test"}')

            loop = AutoFixLoop(project_dir, spec_dir, "test-model")

            # Test assertion failure
            result = AutoFixTestResult(
                executed=True,
                passed=False,
                output="AssertionError: expected 5 but got 3",
                error="assertion failed",
                duration=1.0,
            )
            pattern = loop._analyze_failure(result)
            assert pattern == "assertion_failure", f"Expected 'assertion_failure', got '{pattern}'"
            print(f"✓ Assertion failure detected: {pattern}")

            # Test timeout
            result = AutoFixTestResult(
                executed=True,
                passed=False,
                output="Test timeout after 30 seconds",
                error="timeout",
                duration=30.0,
            )
            pattern = loop._analyze_failure(result)
            assert pattern == "timeout", f"Expected 'timeout', got '{pattern}'"
            print(f"✓ Timeout detected: {pattern}")

            # Test import error
            result = AutoFixTestResult(
                executed=True,
                passed=False,
                output="ImportError: No module named 'foo'",
                error="import error",
                duration=0.5,
            )
            pattern = loop._analyze_failure(result)
            assert pattern == "import_error", f"Expected 'import_error', got '{pattern}'"
            print(f"✓ Import error detected: {pattern}")
    except Exception as e:
        print(f"✗ Error pattern test failed: {e}")
        import traceback
        traceback.print_exc()
        raise

def test_test_count_parsing():
    """Test parsing test counts from output."""
    print("\nTesting test count parsing...")

    try:
        import tempfile
        from qa.auto_fix_loop import AutoFixLoop

        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            spec_dir = Path(tmpdir) / "spec"
            spec_dir.mkdir()
            (spec_dir / "implementation_plan.json").write_text('{"spec_name": "test"}')

            loop = AutoFixLoop(project_dir, spec_dir, "test-model")

            # Test pytest format
            output = "5 passed, 2 failed in 1.2s"
            total, failed = loop._parse_test_counts(output)
            assert total == 7 and failed == 2, f"Expected (7, 2), got ({total}, {failed})"
            print(f"✓ pytest format: {total} total, {failed} failed")

            # Test jest format
            output = "Tests: 2 failed, 5 passed, 7 total"
            total, failed = loop._parse_test_counts(output)
            assert total == 7 and failed == 2, f"Expected (7, 2), got ({total}, {failed})"
            print(f"✓ jest format: {total} total, {failed} failed")

            # Test only passed
            output = "5 passed in 1.2s"
            total, failed = loop._parse_test_counts(output)
            assert total == 5 and failed == 0, f"Expected (5, 0), got ({total}, {failed})"
            print(f"✓ only passed: {total} total, {failed} failed")
    except Exception as e:
        print(f"✗ Test count parsing failed: {e}")
        import traceback
        traceback.print_exc()
        raise

def main():
    """Run all tests."""
    print("=" * 60)
    print("Auto-Fix Loop Integration Test")
    print("=" * 60)

    tests = [
        ("Imports", test_imports),
        ("Classes", test_classes),
        ("Metrics", test_metrics),
        ("Error Patterns", test_error_patterns),
        ("Test Count Parsing", test_test_count_parsing),
    ]

    results = []
    for name, test_func in tests:
        try:
            test_func()
            results.append((name, True))
        except Exception as e:
            print(f"\n✗ {name} test crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    # Summary
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")

    print(f"\n{passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed! Feature is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
