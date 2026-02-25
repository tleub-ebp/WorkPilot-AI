# Phase 1 Implementation Guide
# GitHub Copilot Only Optimization

This guide provides step-by-step instructions for implementing Phase 1 of the GitHub Copilot optimization without affecting Claude Code agents.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Integration Steps](#integration-steps)
5. [Testing](#testing)
6. [Monitoring](#monitoring)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements
- Python 3.8+
- GitHub CLI (`gh`) installed and authenticated
- Existing GitHub Copilot integration
- Token budget tracking requirements

### Dependencies
```bash
# Ensure required packages are installed
pip install aiohttp asyncio
```

### Current System Status
- ✅ Original CopilotRuntime (`apps/backend/core/runtimes/copilot_runtime.py`)
- ✅ Original CopilotAgentClient (`apps/backend/core/agent_client/copilot_agent_client.py`)
- ✅ GitHub Copilot connectors and services
- ✅ Claude Code agents (untouched)

---

## Installation

### 1. Create Optimization Module Structure

The optimization module has already been created with the following structure:

```
apps/backend/core/optimization/
├── __init__.py
├── token_tracker.py
├── token_aware_agent.py
├── hierarchical_prompt.py
├── dynamic_prompt_template.py
├── tests/
│   └── test_optimized_copilot.py
└── README.md
```

### 2. Verify Installation

```bash
# Check that the optimization module is properly installed
python -c "from apps.backend.core.optimization import TokenTracker; print('Optimization module loaded successfully')"
```

---

## Configuration

### 1. Token Budget Configuration

Create a configuration file for token budgets:

```python
# apps/backend/core/optimization/config.py
from typing import Dict, Optional

# Default token budgets
DEFAULT_BUDGETS = {
    'copilot_runtime': 2000,
    'copilot_client': 3000,
    'global': 10000
}

# Agent-specific settings
AGENT_SETTINGS = {
    'copilot_runtime': {
        'auto_decompose': True,
        'max_tokens_per_task': 1000,
        'complexity_threshold': 0.7
    },
    'copilot_client': {
        'auto_optimize_prompts': True,
        'optimize_subagents': True,
        'context_level': 'standard'
    }
}

# Optimization levels
OPTIMIZATION_LEVELS = {
    'minimal': {'max_tokens': 300, 'context_level': 'minimal'},
    'standard': {'max_tokens': 800, 'context_level': 'standard'},
    'comprehensive': {'max_tokens': 1500, 'context_level': 'comprehensive'}
}
```

### 2. Environment Configuration

Add to your `.env` file:

```bash
# GitHub Copilot Optimization Settings
COPILOT_TOKEN_BUDGET=2000
COPILOT_GLOBAL_BUDGET=10000
COPILOT_OPTIMIZATION_ENABLED=true
COPILOT_AUTO_DECOMPOSE=true
COPILOT_PROMPT_LEVEL=standard
```

---

## Integration Steps

### Step 1: Update Provider Registry

Modify `apps/backend/services/provider_registry.py` to include optimized Copilot options:

```python
# Add to the _initialize_providers method in ProviderRegistry

# --- GitHub Copilot (Optimized) ---
self._providers['copilot_optimized'] = Provider(
    name='copilot_optimized',
    label='GitHub Copilot (Optimized)',
    description='GitHub Copilot CLI models with token optimization',
    category='special',
    requires_api_key=False,
    requires_oauth=False,
    requires_cli=True,
    models=[
        {'value': 'gpt-4o', 'label': 'GPT-4o (Copilot Optimized)', 'tier': 'flagship'},
        {'value': 'claude-3.5-sonnet', 'label': 'Claude 3.5 Sonnet (Copilot Optimized)', 'tier': 'standard'},
        {'value': 'o3-mini', 'label': 'o3-mini (Copilot Optimized)', 'tier': 'standard', 'supportsThinking': True},
        {'value': 'gpt-4o-mini', 'label': 'GPT-4o mini (Copilot Optimized)', 'tier': 'fast'},
    ]
)
```

### Step 2: Create Factory for Optimized Components

Create `apps/backend/core/optimization\factory.py`:

```python
"""
Factory for creating optimized GitHub Copilot components.
"""

from typing import Optional
from ..runtimes.optimized_copilot_runtime import OptimizedCopilotRuntime
from ..agent_client.optimized_copilot_agent_client import OptimizedCopilotAgentClient
from .config import DEFAULT_BUDGETS, AGENT_SETTINGS

class OptimizedCopilotFactory:
    """Factory for creating optimized GitHub Copilot components."""
    
    @staticmethod
    def create_runtime(*args, **kwargs) -> OptimizedCopilotRuntime:
        """Create an optimized Copilot runtime."""
        # Extract token budget from kwargs or use default
        token_budget = kwargs.pop('token_budget', DEFAULT_BUDGETS['copilot_runtime'])
        
        return OptimizedCopilotRuntime(
            *args,
            token_budget=token_budget,
            **kwargs
        )
    
    @staticmethod
    def create_agent_client(*args, **kwargs) -> OptimizedCopilotAgentClient:
        """Create an optimized Copilot agent client."""
        # Extract token budget from kwargs or use default
        token_budget = kwargs.pop('token_budget', DEFAULT_BUDGETS['copilot_client'])
        
        return OptimizedCopilotAgentClient(
            *args,
            token_budget=token_budget,
            **kwargs
        )
    
    @staticmethod
    def create_runtime_with_config(config: dict, *args, **kwargs) -> OptimizedCopilotRuntime:
        """Create runtime with configuration."""
        settings = AGENT_SETTINGS.get('copilot_runtime', {})
        
        # Merge config with settings
        merged_kwargs = {**settings, **config, **kwargs}
        
        return OptimizedCopilotFactory.create_runtime(*args, **merged_kwargs)
    
    @staticmethod
    def create_client_with_config(config: dict, *args, **kwargs) -> OptimizedCopilotAgentClient:
        """Create client with configuration."""
        settings = AGENT_SETTINGS.get('copilot_client', {})
        
        # Merge config with settings
        merged_kwargs = {**settings, **config, **kwargs}
        
        return OptimizedCopilotFactory.create_agent_client(*args, **merged_kwargs)
```

### Step 3: Update Runtime Factory

Modify the runtime factory in `apps/backend/core/__init__.py`:

```python
# Add to the runtime factory function
def create_agent_runtime(provider: str, **kwargs) -> AgentRuntime:
    """Factory function for creating agent runtimes."""
    
    if provider == "copilot":
        # Check if optimization is enabled
        optimization_enabled = os.getenv("COPILOT_OPTIMIZATION_ENABLED", "false").lower() == "true"
        
        if optimization_enabled:
            from .optimization.factory import OptimizedCopilotFactory
            return OptimizedCopilotFactory.create_runtime_with_config(kwargs)
        else:
            from .runtimes.copilot_runtime import CopilotRuntime
            return CopilotRuntime(**kwargs)
    
    # ... existing provider logic ...
```

### Step 4: Update Agent Client Factory

Modify the agent client factory in `apps/backend/core/__init__.py`:

```python
# Add to the agent client factory function
def create_agent_client(provider: str, **kwargs) -> AgentClient:
    """Factory function for creating agent clients."""
    
    if provider == "copilot":
        # Check if optimization is enabled
        optimization_enabled = os.getenv("COPILOT_OPTIMIZATION_ENABLED", "false").lower() == "true"
        
        if optimization_enabled:
            from .optimization.factory import OptimizedCopilotFactory
            return OptimizedCopilotFactory.create_client_with_config(kwargs)
        else:
            from .agent_client.copilot_agent_client import CopilotAgentClient
            return CopilotAgentClient(**kwargs)
    
    # ... existing provider logic ...
```

### Step 5: Update Provider Registry Check

Modify the provider status check in `apps/backend/services/provider_registry.py`:

```python
def _check_copilot_optimized_auth(self) -> bool:
    """Check if optimized GitHub Copilot CLI is authenticated and functional."""
    try:
        # First check regular Copilot authentication
        regular_auth = self._check_copilot_auth()
        if not regular_auth:
            return False
        
        # Check if optimization module is available
        try:
            from ..core.optimization import TokenTracker
            tracker = TokenTracker()
            # Test token tracking functionality
            tracker.record_usage("test", "test", "input", 1)
            return True
        except ImportError:
            logger.warning("Optimization module not available, falling back to regular Copilot")
            return False
            
    except Exception as e:
        logger.error(f"Error checking optimized Copilot auth: {e}")
        return False
```

---

## Testing

### 1. Run Unit Tests

```bash
# Run all optimization tests
python -m pytest apps/backend/core/optimization/tests/ -v

# Run specific test categories
python -m pytest apps/backend/core/optimization/tests/test_optimized_copilot.py::TestTokenTracker -v
python -m pytest apps/backend/core/optimization/tests/test_optimized_copilot.py::TestHierarchicalPrompt -v
```

### 2. Run Integration Tests

```bash
# Test optimized runtime
python -m pytest apps/backend/core/optimization/tests/test_optimized_copilot.py::TestIntegration::test_optimized_runtime_compatibility -v

# Test optimized client
python -m pytest apps/backend/core/optimization/tests/test_optimized_copilot.py::TestIntegration::test_optimized_client_compatibility -v
```

### 3. Manual Testing

Create a test script `test_optimization.py`:

```python
#!/usr/bin/env python3
"""
Manual test script for GitHub Copilot optimization.
"""

import asyncio
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

async def test_optimized_runtime():
    """Test the optimized Copilot runtime."""
    print("Testing Optimized Copilot Runtime...")
    
    try:
        from apps.backend.core.optimization.factory import OptimizedCopilotFactory
        
        # Create optimized runtime
        runtime = OptimizedCopilotFactory.create_runtime(
            spec_dir="test/specs",
            phase="test",
            project_dir="test/project",
            agent_type="test",
            token_budget=1000
        )
        
        print(f"✅ Optimized runtime created with budget: {runtime.token_budget}")
        
        # Test performance stats
        stats = runtime.get_optimization_stats()
        print(f"✅ Performance stats: {stats}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing optimized runtime: {e}")
        return False

async def test_optimized_client():
    """Test the optimized Copilot agent client."""
    print("Testing Optimized Copilot Agent Client...")
    
    try:
        from apps.backend.core.optimization.factory import OptimizedCopilotFactory
        
        # Create optimized client
        client = OptimizedCopilotFactory.create_agent_client(
            model="gpt-4o",
            token_budget=1500
        )
        
        print(f"✅ Optimized client created with budget: {client.token_budget}")
        
        # Test performance stats
        stats = client.get_optimization_stats()
        print(f"✅ Performance stats: {stats}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing optimized client: {e}")
        return False

async def main():
    """Run all tests."""
    print("🚀 GitHub Copilot Phase 1 Optimization Tests")
    print("=" * 50)
    
    # Check environment
    optimization_enabled = os.getenv("COPILOT_OPTIMIZATION_ENABLED", "false").lower() == "true"
    print(f"Optimization enabled: {optimization_enabled}")
    
    if not optimization_enabled:
        print("❌ Optimization not enabled. Set COPILOT_OPTIMIZATION_ENABLED=true in .env")
        return
    
    # Run tests
    tests = [
        test_optimized_runtime,
        test_optimized_client
    ]
    
    results = []
    for test in tests:
        result = await test()
        results.append(result)
    
    # Summary
    print("\n" + "=" * 50)
    print("Test Results:")
    print(f"✅ Passed: {sum(results)}/{len(results)}")
    print(f"❌ Failed: {len(results) - sum(results)}/{len(results)}")
    
    if all(results):
        print("🎉 All tests passed! Phase 1 implementation is ready.")
    else:
        print("⚠️  Some tests failed. Check the logs above.")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Monitoring

### 1. Token Usage Monitoring

Create a monitoring script `monitor_tokens.py`:

```python
#!/usr/bin/env python3
"""
Monitor GitHub Copilot token usage.
"""

import time
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

def monitor_tokens():
    """Monitor token usage for GitHub Copilot components."""
    print("📊 GitHub Copilot Token Usage Monitor")
    print("=" * 50)
    
    try:
        from apps.backend.core.optimization import TokenTracker
        
        # Create tracker
        tracker = TokenTracker()
        
        # Set budgets from environment
        global_budget = int(os.getenv("COPILOT_GLOBAL_BUDGET", "10000"))
        runtime_budget = int(os.getenv("COPILOT_TOKEN_BUDGET", "2000"))
        client_budget = int(os.getenv("COPILOT_CLIENT_BUDGET", "3000"))
        
        tracker.set_global_budget(global_budget)
        tracker.set_budget("copilot_runtime", runtime_budget)
        tracker.set_budget("copilot_client", client_budget)
        
        print(f"Global budget: {global_budget}")
        print(f"Runtime budget: {runtime_budget}")
        print(f"Client budget: {client_budget}")
        
        # Monitor loop
        while True:
            try:
                global_stats = tracker.get_global_stats()
                runtime_stats = tracker.get_agent_stats("copilot_runtime")
                client_stats = tracker.get_agent_stats("copilot_client")
                
                print("\n" + "=" * 50)
                print(f"📊 Token Usage Report - {time.strftime('%Y-%m-%d %H:%M:%S')}")
                print("-" * 50)
                
                print(f"Global:")
                print(f"  Total tokens: {global_stats.total_tokens}")
                print(f"  Success rate: {global_stats.successful_tasks / max(global_stats.successful_tasks + global_stats.failed_tasks, 1):.2%}")
                print(f"  Average per task: {global_stats.average_tokens_per_task:.1f}")
                
                print(f"Runtime:")
                print(f"  Tokens used: {runtime_stats.total_tokens}")
                print(f"  Success rate: {runtime_stats.successful_tasks / max(runtime_stats.successful_tasks + runtime_stats.failed_tasks, 1):.2%}")
                print(f"  Average per task: {runtime_stats.average_tokens_per_task:.1f}")
                print(f"  Budget remaining: {runtime_budget - runtime_stats.total_tokens}")
                
                print(f"Client:")
                print(f"  Tokens used: {client_stats.total_tokens}")
                print(f"  Success rate: {client_stats.successful_tasks / max(client_stats.successful_tasks + client_stats.failed_tasks, 1):.2%}")
                print(f"  Average per task: {client_stats.average_tokens_per_task:.1f}")
                print(f"  Budget remaining: {client_budget - client_stats.total_tokens}")
                
                # Check efficiency scores
                runtime_efficiency = tracker.get_efficiency_score("copilot_runtime")
                client_efficiency = tracker.get_efficiency_score("copilot_client")
                
                print(f"Efficiency Scores:")
                print(f"  Runtime: {runtime_efficiency:.3f}")
                print(f"  Client: {client_efficiency:.3f}")
                
                # Check if any budgets are exceeded
                if runtime_stats.total_tokens > runtime_budget * 0.9:
                    print("⚠️  Runtime budget warning!")
                
                if client_stats.total_tokens > client_budget * 0.9:
                    print("⚠️  Client budget warning!")
                
                time.sleep(30)  # Wait 30 seconds
                
            except KeyboardInterrupt:
                print("\n👋 Monitoring stopped by user")
                break
            except Exception as e:
                print(f"❌ Error in monitoring: {e}")
                time.sleep(30)
                
    except Exception as e:
        print(f"❌ Error setting up monitoring: {e}")

if __name__ == "__main__":
    monitor_tokens()
```

### 2. Performance Dashboard

Create a simple dashboard script `dashboard.py`:

```python
#!/usr/bin/env python3
"""
GitHub Copilot Optimization Dashboard
"""

import json
import time
from pathlib import Path
from datetime import datetime

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

def generate_dashboard():
    """Generate a performance dashboard."""
    
    try:
        from apps.backend.core.optimization import TokenTracker
        
        tracker = TokenTracker()
        
        # Collect data
        global_stats = tracker.get_global_stats()
        runtime_stats = tracker.get_agent_stats("copilot_runtime")
        client_stats = tracker.get_agent_stats("copilot_client")
        
        # Create dashboard data
        dashboard = {
            "timestamp": datetime.now().isoformat(),
            "global": {
                "total_tokens": global_stats.total_tokens,
                "success_rate": global_stats.successful_tasks / max(global_stats.successful_tasks + global_stats.failed_tasks, 1),
                "average_tokens_per_task": global_stats.average_tokens_per_task,
                "budget_usage": global_stats.total_tokens / int(os.getenv("COPILOT_GLOBAL_BUDGET", "10000"))
            },
            "runtime": {
                "total_tokens": runtime_stats.total_tokens,
                "success_rate": runtime_stats.successful_tasks / max(runtime_stats.successful_tasks + runtime_stats.failed_tasks, 1),
                "average_tokens_per_task": runtime_stats.average_tokens_per_task,
                "budget_usage": runtime_stats.total_tokens / int(os.getenv("COPILOT_TOKEN_BUDGET", "2000")),
                "efficiency_score": tracker.get_efficiency_score("copilot_runtime")
            },
            "client": {
                "total_tokens": client_stats.total_tokens,
                "success_rate": client_stats.successful_tasks / max(client_stats.successful_tasks + client_stats.failed_tasks, 1),
                "average_tokens_per_task": client_stats.average_tokens_per_task,
                "budget_usage": client_stats.total_tokens / int(os.getenv("COPILOT_CLIENT_BUDGET", "3000")),
                "efficiency_score": tracker.get_efficiency_score("copilot_client")
            }
        }
        
        # Save dashboard
        dashboard_path = project_root / "copilot_dashboard.json"
        with open(dashboard_path, 'w') as f:
            json.dump(dashboard, f, indent=2)
        
        print(f"📊 Dashboard saved to {dashboard_path}")
        return dashboard_path
        
    except Exception as e:
        print(f"❌ Error generating dashboard: {e}")
        return None

if __name__ == "__main__":
    dashboard_path = generate_dashboard()
    if dashboard_path:
        print(f"Open {dashboard_path} to view the dashboard")
```

---

## Troubleshooting

### Common Issues and Solutions

#### Issue: Import Errors
**Problem**: `ImportError: No module named 'apps.backend.core.optimization'`

**Solution**:
1. Verify the optimization module is in the correct path
2. Check that `__init__.py` exists in the optimization module
3. Ensure Python path includes the project root

#### Issue: Token Budget Exceeded
**Problem**: Tasks failing due to insufficient token budget

**Solution**:
1. Increase token budget in environment variables
2. Enable task decomposition for complex tasks
3. Reduce prompt complexity level

#### Issue: Poor Response Quality
**Problem**: Responses are not as good as expected

**Solution**:
1. Increase prompt level from MINIMAL to STANDARD
2. Add more context and examples
3. Check if optimization is actually enabled

#### Issue: Performance Degradation
**Problem**: System is slower than before optimization

**Solution**:
1. Check cache hit rates
2. Verify token tracking overhead is minimal
3. Disable optimization temporarily to compare performance

### Debug Mode

Enable debug logging:

```python
import logging
import os

# Set debug level
logging.basicConfig(level=logging.DEBUG)

# Enable optimization debug logging
os.environ['COPILOT_OPTIMIZATION_DEBUG'] = 'true'
```

### Validation Commands

```bash
# Validate module imports
python -c "from apps.backend.core.optimization import TokenTracker; print('✅ Module imports working')"

# Test token tracking
python -c "from apps.backend.core.optimization import TokenTracker; t = TokenTracker(); print('✅ TokenTracker working')"

# Test hierarchical prompts
python -c "from apps.backend.core.optimization import HierarchicalPrompt; p = HierarchicalPrompt(); print('✅ HierarchicalPrompt working')"

# Test factory
python -c "from apps.backend.core.optimization.factory import OptimizedCopilotFactory; print('✅ Factory working')"
```

### Environment Validation

```bash
# Check environment variables
echo "COPILOT_OPTIMIZATION_ENABLED=$COPILOT_OPTIMIZATION_ENABLED"
echo "COPILOT_TOKEN_BUDGET=$COPILOT_TOKEN_BUDGET"
echo "COPILOT_GLOBAL_BUDGET=$COPILOT_GLOBAL_BUDGET"
echo "COPILOT_CLIENT_BUDGET=$COPILOT_CLIENT_BUDGET"

# Check GitHub CLI
gh auth status
gh copilot --version
```

---

## Next Steps

After completing Phase 1:

1. **Monitor Performance**: Use the monitoring scripts for 1-2 weeks
2. **Collect Metrics**: Gather data on token savings and performance
3. **Adjust Settings**: Fine-tune budgets and optimization levels
4. **Prepare for Phase 2**: Document lessons learned and improvements needed

Phase 2 can then proceed with extending optimizations to other components if Phase 1 is successful.

---

## Support

For issues or questions:

1. Check the logs in the monitoring scripts
2. Review the test suite output
3. Consult the documentation in the README files
4. Verify environment configuration

Remember: This implementation is **completely isolated** from Claude Code agents and will not affect their functionality.
