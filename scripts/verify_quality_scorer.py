#!/usr/bin/env python3
"""Quick test to verify quality_scorer.py is properly encoded"""

import sys
from pathlib import Path

target = Path(__file__).parent.parent / "apps" / "backend" / "review" / "quality_scorer.py"

if not target.exists():
    print(f"✗ File not found: {target}")
    sys.exit(1)

try:
    # Try to read and parse it
    content = target.read_text(encoding='utf-8')
    
    # Check for null bytes
    if '\x00' in content:
        print("✗ File contains null bytes")
        sys.exit(1)
    
    # Try to compile it
    compile(content, str(target), 'exec')
    
    # Try to import it
    sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend"))
    from review.quality_scorer import (
        QualityScorer,
    )
    
    print("✓ File is valid Python!")
    print(f"✓ QualityScorer class: {QualityScorer}")
    print("✓ All imports successful")
    sys.exit(0)
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
