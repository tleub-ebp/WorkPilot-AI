"""
Quick test to validate self_healing CLI works
"""
import subprocess
import sys

print("Testing self_healing CLI...")
print("=" * 70)

# Test import
print("\n1. Testing import...")
try:
    result = subprocess.run(
        [sys.executable, "-c", "from apps.backend import self_healing; print('Import OK')"],
        cwd=r"c:\Users\thomas.leberre\Repositories\WorkPilot-AI",
        capture_output=True,
        text=True,
        timeout=10
    )
    
    if result.returncode == 0:
        print("   ✅ Import successful")
    else:
        print(f"   ❌ Import failed: {result.stderr}")
        sys.exit(1)
except Exception as e:
    print(f"   ❌ Import test failed: {e}")
    sys.exit(1)

# Test CLI help
print("\n2. Testing CLI help...")
try:
    result = subprocess.run(
        [sys.executable, "-m", "apps.backend.self_healing", "--help"],
        cwd=r"c:\Users\thomas.leberre\Repositories\WorkPilot-AI",
        capture_output=True,
        text=True,
        timeout=10
    )
    
    if result.returncode == 0 and "Self-Healing Codebase System" in result.stdout:
        print("   ✅ CLI help works")
    else:
        print(f"   ❌ CLI help failed")
        print(f"   stdout: {result.stdout}")
        print(f"   stderr: {result.stderr}")
        sys.exit(1)
except Exception as e:
    print(f"   ❌ CLI test failed: {e}")
    sys.exit(1)

# Test check command (dry run)
print("\n3. Testing 'check' command...")
try:
    result = subprocess.run(
        [sys.executable, "-m", "apps.backend.self_healing", "check", "--project-dir", "apps/backend"],
        cwd=r"c:\Users\thomas.leberre\Repositories\WorkPilot-AI",
        capture_output=True,
        text=True,
        timeout=60
    )
    
    print(f"   Return code: {result.returncode}")
    print(f"   Output preview: {result.stdout[:500] if result.stdout else 'No stdout'}")
    
    if result.stderr and "Error:" in result.stderr:
        print(f"   stderr: {result.stderr}")
    
    if result.returncode in [0, 1]:  # 0 = healthy, 1 = needs attention
        print("   ✅ Check command executed")
    else:
        print(f"   ⚠️ Check command returned code {result.returncode}")
        
except Exception as e:
    print(f"   ⚠️ Check command test failed: {e}")

print("\n" + "=" * 70)
print("✅ Basic CLI tests complete!")
print("\nTo run full health check:")
print("  cd apps/backend")
print("  python -m self_healing check --verbose")
