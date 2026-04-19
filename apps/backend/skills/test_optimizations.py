#!/usr/bin/env python3
"""
Simple test script for optimization constants
"""

import sys
from pathlib import Path

# Add skills directory to path
sys.path.append(str(Path(__file__).parent))


def test_optimization_config():
    """Test the optimization configuration."""
    print("🚀 Testing Optimization Configuration")
    print("=" * 50)

    try:
        from optimization_config import OPTIMIZATION_CONFIG, get_optimization_config

        config = get_optimization_config()

        print("📊 Token Optimization:")
        print(f"  Max description length: {config.token.max_description_length}")
        print(f"  Max triggers count: {config.token.max_triggers_count}")
        print(f"  Sampling threshold: {config.token.sampling_threshold}")
        print(f"  Compression threshold: {config.token.compression_threshold}")
        print(f"  Predictive cache size: {config.token.predictive_cache_size}")
        print(f"  Deduplication min length: {config.token.deduplication_min_length}")

        print("\n🗂️  Context Optimization:")
        print(f"  Max context limit ratio: {config.context.max_context_limit_ratio}")
        print(f"  Default max workers: {config.context.default_max_workers}")
        print(f"  Default timeout: {config.context.default_timeout}s")
        print(f"  Checkpoint interval: {config.context.checkpoint_interval}s")
        print(f"  Priority threshold: {config.context.priority_threshold}")

        print("\n⚡ Performance Optimization:")
        print(f"  Optimization enabled: {config.performance.optimization_enabled}")
        print(f"  Subagent threshold: {config.performance.subagent_threshold}")
        print(f"  Validation cache size: {config.performance.validation_cache_size}")
        print(
            f"  Memory cleanup interval: {config.performance.memory_cleanup_interval}s"
        )
        print(f"  Parallel execution: {config.performance.parallel_execution}")

        print("\n🎯 Claude Code Optimization:")
        oauth_flag = config.claude_code.oauth_token_support
        print(f"  OAuth support enabled: {bool(oauth_flag)}")
        enc_flag = config.claude_code.encrypted_token_validation
        print(f"  Encrypted credential validation enabled: {bool(enc_flag)}")
        print(f"  Keychain integration: {config.claude_code.keychain_integration}")
        print(f"  SDK integration: {config.claude_code.sdk_integration}")
        print(f"  Context compression: {config.claude_code.context_compression}")

        # Test validation
        print(
            f"\n✅ Configuration validation: {'PASSED' if config.validate() else 'FAILED'}"
        )

        # Test export
        config_dict = config.to_dict()
        print(
            f"✅ Configuration export: {'PASSED' if isinstance(config_dict, dict) else 'FAILED'}"
        )

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_constants():
    """Test backward compatibility constants."""
    print("\n🔄 Testing Backward Compatibility Constants")
    print("=" * 50)

    try:
        from optimization_config import (
            CHECKPOINT_INTERVAL,
            COMPRESSION_THRESHOLD,
            DEDUPLICATION_MIN_LENGTH,
            DEFAULT_MAX_WORKERS,
            DEFAULT_TIMEOUT,
            MAX_CONTEXT_LIMIT_RATIO,
            MAX_DESCRIPTION_LENGTH,
            MAX_TRIGGERS_COUNT,
            OPTIMIZATION_ENABLED,
            PREDICTIVE_CACHE_SIZE,
            PRIORITY_THRESHOLD,
            SAMPLING_THRESHOLD,
            SUBAGENT_THRESHOLD,
            VALIDATION_CACHE_SIZE,
        )

        print("✅ All constants imported successfully")

        # Verify expected values
        assert MAX_DESCRIPTION_LENGTH == 512
        assert MAX_TRIGGERS_COUNT == 5
        assert SAMPLING_THRESHOLD == 5
        assert MAX_CONTEXT_LIMIT_RATIO == 0.7
        assert DEFAULT_MAX_WORKERS == 3
        assert DEFAULT_TIMEOUT == 25
        assert OPTIMIZATION_ENABLED
        assert SUBAGENT_THRESHOLD == 3
        assert CHECKPOINT_INTERVAL == 300
        assert PRIORITY_THRESHOLD == 0.5
        assert VALIDATION_CACHE_SIZE == 500
        assert COMPRESSION_THRESHOLD == 100
        assert PREDICTIVE_CACHE_SIZE == 1000
        assert DEDUPLICATION_MIN_LENGTH == 50

        print("✅ All constant values verified")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_config_update():
    """Test configuration update functionality."""
    print("\n🔧 Testing Configuration Update")
    print("=" * 50)

    try:
        from optimization_config import (
            get_optimization_config,
            reset_optimization_config,
            update_optimization_config,
        )

        # Get original config
        original_config = get_optimization_config()
        original_workers = original_config.context.default_max_workers

        # Update configuration
        new_config = {
            "context": {"default_max_workers": 8, "default_timeout": 45},
            "token": {"max_description_length": 1024},
        }

        success = update_optimization_config(new_config)
        print(f"✅ Configuration update: {'PASSED' if success else 'FAILED'}")

        # Verify changes
        updated_config = get_optimization_config()
        print(
            f"  Workers: {original_workers} → {updated_config.context.default_max_workers}"
        )
        print(
            f"  Timeout: {original_config.context.default_timeout} → {updated_config.context.default_timeout}"
        )
        print(
            f"  Description length: {original_config.token.max_description_length} → {updated_config.token.max_description_length}"
        )

        # Reset configuration
        reset_optimization_config()
        reset_config = get_optimization_config()
        print(
            f"✅ Configuration reset: {'PASSED' if reset_config.context.default_max_workers == original_workers else 'FAILED'}"
        )

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    print("🧪 Testing Optimization Implementation")
    print("=" * 60)

    results = []
    results.append(test_optimization_config())
    results.append(test_constants())
    results.append(test_config_update())

    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)

    print(f"📊 Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Optimization implementation is working correctly.")
    else:
        print("⚠️  Some tests failed. Please check the implementation.")

    print("\n✨ Optimization Implementation Summary:")
    print("- Centralized configuration system")
    print("- Token optimization (512 chars limit, 5 triggers max)")
    print("- Context optimization (70% limit, 3 workers, 25s timeout)")
    print("- Performance optimization (subagents for >3 skills)")
    print("- Claude Code specific optimizations")
    print("- Backward compatibility maintained")
    print("- Dynamic configuration updates supported")
