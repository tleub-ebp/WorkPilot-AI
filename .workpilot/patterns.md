# Project Patterns

This file defines reusable patterns and best practices discovered through project evolution.

## Version History
- v1.0.0 - Initial pattern collection
- Last updated: 2025-01-16

## Code Patterns

### Agent Implementation Pattern
```python
# Standard agent structure
from core.client import create_client
from core.workflow_logger import workflow_logger

class StandardAgent:
    def __init__(self, project_dir, spec_dir, model=None):
        self.client = create_client(
            project_dir=project_dir,
            spec_dir=spec_dir,
            model=model,
            agent_type="standard",
        )
        self.logger = workflow_logger
    
    async def execute(self, task_context):
        trace_id = self.logger.log_agent_start("StandardAgent", "execute", task_context)
        try:
            # Agent implementation here
            result = await self._process_task(task_context)
            self.logger.log_agent_end("StandardAgent", "success", result, trace_id)
            return result
        except Exception as e:
            self.logger.log_agent_end("StandardAgent", "error", {"error": str(e)}, trace_id)
            raise
```

### Frontend Component Pattern
```tsx
// Standard React component structure
import { useTranslation } from 'react-i18next';
import { cn } from '@/lib/utils';

interface ComponentProps {
  // Props definition
}

export function Component({ ...props }: ComponentProps) {
  const { t } = useTranslation(['common']);
  
  return (
    <div className={cn("base-styles", props.className)}>
      {/* Component content */}
    </div>
  );
}
```

### State Management Pattern
```typescript
// Zustand store pattern
import { create } from 'zustand';
import { devtools } from 'zustand/middleware';

interface StoreState {
  // State definition
  actions: {
    // Action definitions
  };
}

export const useStore = create<StoreState>()(
  devtools(
    (set, get) => ({
      // Initial state
      actions: {
        // Action implementations
      },
    }),
    { name: 'store-name' }
  )
);
```

## Architecture Patterns

### Multi-Agent Coordination Pattern
1. **Task Decomposition** → Planner breaks complex tasks
2. **Parallel Execution** → Multiple coders work on subtasks
3. **Semantic Merge** → Intelligent conflict resolution
4. **QA Validation** → Systematic quality assurance

### Context Building Pattern
```python
def build_task_context(project_dir, task_description):
    context = {
        'project_structure': analyze_project_structure(project_dir),
        'existing_patterns': extract_patterns(project_dir),
        'conventions': load_conventions(),
        'architecture': load_architecture(),
        'task_requirements': analyze_requirements(task_description),
    }
    return optimize_context(context)
```

### Error Recovery Pattern
```python
async def execute_with_recovery(agent_func, context, max_retries=3):
    for attempt in range(max_retries):
        try:
            return await agent_func(context)
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            await analyze_and_adapt(context, e)
```

## Integration Patterns

### External Service Pattern
```python
class ExternalServiceClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = create_session_with_retries()
    
    async def call_with_fallback(self, endpoint: str, data: dict):
        try:
            return await self._call_service(endpoint, data)
        except ServiceUnavailable:
            return await self._fallback_handler(endpoint, data)
```

### IPC Communication Pattern
```typescript
// Main process handler
export const handlerName: IpcHandler = async (event, data) => {
  try {
    const result = await processRequest(data);
    event.reply('handler-name-success', result);
  } catch (error) {
    event.reply('handler-name-error', { error: error.message });
  }
};

// Renderer process usage
const result = await window.electronAPI.handlerName(data);
```

## Testing Patterns

### Agent Testing Pattern
```python
@pytest.mark.asyncio
async def test_agent_execution():
    # Arrange
    agent = TestAgent(project_dir, spec_dir)
    context = create_test_context()
    
    # Act
    result = await agent.execute(context)
    
    # Assert
    assert result.success
    assert validate_output(result.data)
```

### Frontend Testing Pattern
```typescript
test('component behavior', async () => {
  render(<Component />);
  
  const element = screen.getByTestId('test-id');
  await userEvent.click(element);
  
  expect(screen.getByText('expected-text')).toBeInTheDocument();
});
```

## Performance Patterns

### Token Optimization Pattern
```python
def optimize_context(context: dict, max_tokens: int) -> dict:
    if count_tokens(context) > max_tokens:
        return {
            'essential': keep_essential_info(context),
            'compressed': compress_metadata(context),
            'cached': use_cached_data(context),
        }
    return context
```

### Caching Pattern
```typescript
// Multi-level caching
const cache = {
  memory: new Map(),
  disk: createDiskCache(),
  remote: createRemoteCache(),
};

async function getWithCache(key: string) {
  return cache.memory.get(key) ||
         await cache.disk.get(key) ||
         await cache.remote.get(key);
}
```

## Security Patterns

### Input Validation Pattern
```python
def validate_file_path(file_path: str, allowed_dirs: List[str]) -> str:
    normalized = os.path.normpath(file_path)
    if not any(normalized.startswith(dir) for dir in allowed_dirs):
        raise SecurityError("Path not allowed")
    return normalized
```

### Command Allowlist Pattern
```python
ALLOWED_COMMANDS = {
    'git': ['status', 'add', 'commit', 'push'],
    'npm': ['install', 'test', 'build'],
    'python': ['-m', 'pytest'],
}

def validate_command(command: List[str]) -> bool:
    return command[0] in ALLOWED_COMMANDS and \
           all(arg in ALLOWED_COMMANDS[command[0]] for arg in command[1:])
```

## UI/UX Patterns

### Loading State Pattern
```tsx
interface LoadingState {
  isLoading: boolean;
  progress?: number;
  message?: string;
}

function useAsyncOperation<T>(
  operation: () => Promise<T>
): [T | null, LoadingState, () => void] {
  // Implementation
}
```

### Error Handling Pattern
```tsx
function ErrorBoundary({ children }: { children: React.ReactNode }) {
  return (
    <div>
      {/* Error boundary implementation */}
    </div>
  );
}
```

## Data Patterns

### Configuration Pattern
```python
# Hierarchical configuration
def load_config():
    return {
        'base': load_base_config(),
        'environment': load_env_config(),
        'user': load_user_config(),
        'project': load_project_config(),
    }
```

### Logging Pattern
```python
# Structured logging
logger = workflow_logger

def log_operation(operation: str, context: dict, result: any = None):
    trace_id = logger.log_agent_start("Agent", operation, context)
    if result:
        logger.log_agent_end("Agent", "success", result, trace_id)
```

## Migration Patterns

### Version Migration Pattern
```python
def migrate_data(old_version: str, new_version: str):
    migrations = get_migration_chain(old_version, new_version)
    for migration in migrations:
        migration.apply()
```

### API Evolution Pattern
```typescript
// Backward compatible API
export function apiFunction(params: Params): Result {
  if (params.legacy) {
    return handleLegacyRequest(params);
  }
  return handleNewRequest(params);
}
```

## Learning Loop Patterns

### Pattern Discovery Pattern
```python
def discover_successful_patterns(build_history: List[Build]):
    successful_builds = [b for b in build_history if b.success]
    patterns = extract_common_patterns(successful_builds)
    return rank_by_success_rate(patterns)
```

### Convention Evolution Pattern
```python
def evolve_conventions(current_conventions: dict, new_patterns: List[Pattern]):
    for pattern in new_patterns:
        if pattern.success_rate > EVOLUTION_THRESHOLD:
            current_conventions = merge_pattern(current_conventions, pattern)
    return version_conventions(current_conventions)
```

## Anti-Patterns

### Common Pitfalls
- **Direct API Usage**: Never use `anthropic.Anthropic()` directly
- **Hardcoded Paths**: Always use platform abstraction
- **Missing i18n**: All UI text must use translation keys
- **Blocking Operations**: Use async patterns throughout
- **Memory Leaks**: Proper cleanup in all components

### Performance Anti-Patterns
- **Large Context**: Avoid sending entire codebase to AI
- **Synchronous I/O**: Use async/await consistently
- **Unnecessary Re-renders**: Optimize React component updates
- **Memory Bloat**: Implement proper cleanup patterns

---

*This patterns file is continuously updated by the Learning Loop based on successful project outcomes.*
