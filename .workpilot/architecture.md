# Project Architecture

This file defines the architectural patterns and structural decisions for the project.

## Version History
- v1.0.0 - Initial architecture definition
- Last updated: 2025-01-16

## High-Level Architecture

### Monorepo Structure
```
Auto-Claude_EBP/
├── apps/
│   ├── backend/          # Python backend - CLI + agent logic
│   └── frontend/         # Electron desktop UI
├── src/                  # Shared connectors and utilities
├── guides/               # Documentation
├── tests/                # Backend test suite
└── scripts/              # Build and utility scripts
```

### Multi-Agent System
- **Planner Agent**: Breaks tasks into subtasks
- **Coder Agent**: Implements features with parallel subagents
- **QA Reviewer**: Validates implementations
- **QA Fixer**: Resolves identified issues

## Core Components

### Backend Architecture (`apps/backend/`)
```
apps/backend/
├── core/                 # Client, auth, worktree, platform
├── agents/               # Planner, coder, session management
├── qa/                   # Reviewer, fixer, loop, criteria
├── spec/                 # Spec creation pipeline
├── skills/               # AI skills system with optimization
├── cli/                  # CLI commands
├── context/              # Task context building
├── runners/              # Standalone runners
├── services/             # Background services
├── integrations/         # External integrations
├── project/              # Project analysis
└── merge/                # Semantic merge system
```

### Frontend Architecture (`apps/frontend/`)
```
apps/frontend/src/
├── main/                 # Electron main process
│   ├── agent/            # Agent queue and process management
│   ├── claude-profile/   # Multi-profile credentials
│   ├── terminal/         # PTY daemon and lifecycle
│   ├── platform/         # Cross-platform abstraction
│   ├── ipc-handlers/     # 40+ handler modules
│   └── services/         # SDK session recovery
├── renderer/             # React UI
│   ├── components/       # UI components
│   ├── stores/           # Zustand state stores
│   ├── contexts/         # React contexts
│   ├── hooks/            # Custom hooks
│   └── styles/           # CSS/Tailwind styles
└── shared/               # Shared types, i18n, utils
```

## Data Flow Architecture

### Agent Execution Flow
1. **Task Creation** → User creates task in UI/CLI
2. **Spec Generation** → AI analyzes complexity and creates specification
3. **Planning Phase** → Planner breaks into subtasks
4. **Implementation** → Coder executes with parallel subagents
5. **QA Validation** → Reviewer validates implementation
6. **Issue Resolution** → Fixer resolves identified problems
7. **Merge Phase** → Semantic merge to main branch

### State Management Flow
- **Project State** → `project-store.ts`
- **Task/Spec State** → `task-store.ts`
- **Terminal State** → `terminal-store.ts`
- **Agent State** → `agent-state.ts`
- **Settings State** → `settings-store.ts`

## Integration Patterns

### Claude Agent SDK Integration
- **Required**: All AI interactions use `claude-agent-sdk`
- **Client Creation**: `create_client()` from `core.client`
- **Security**: Built-in security hooks and tool permissions
- **Context Management**: Dynamic context optimization

### IPC Communication Pattern
- **Main Process**: IPC handlers in `src/main/ipc-handlers/`
- **Renderer Process**: Calls via `window.electronAPI.*`
- **Preload Bridge**: Safe API exposure in `src/preload/`
- **Domain Organization**: Handlers organized by functionality

### External Service Integration
- **grepai**: Semantic code search (localhost:9000)
- **Graphiti**: Memory system for knowledge retention
- **GitHub/GitLab**: Issue import and PR management
- **Claude API**: Multi-profile authentication

## Security Architecture

### Authentication Layers
1. **Claude Profile System** → OAuth token management
2. **API Key Management** → Environment variable storage
3. **Command Allowlisting** → Validated operation permissions
4. **Process Isolation** → Git worktree separation

### Data Protection
- **Credential Storage** → OS keychain/credential manager
- **Token Refresh** → Automatic OAuth token lifecycle
- **Input Validation** → Sanitized file paths and commands
- **Audit Logging** → Complete operation tracking

## Performance Architecture

### Concurrency Model
- **Agent Parallelism** → Up to 12 parallel AI terminals
- **Async Operations** → Non-blocking I/O throughout
- **Resource Pooling** → Reused connections and sessions
- **Load Balancing** → Multi-account Claude profile switching

### Optimization Strategies
- **Token Optimization** → Context compression and caching
- **Memory Management** → Aggressive cleanup and checkpoints
- **Network Optimization** → Connection pooling and retries
- **UI Performance** → Virtual scrolling and lazy loading

## Testing Architecture

### Test Organization
```
tests/
├── connectors/           # Integration tests
├── fixtures/             # Test data and examples
├── runners/              # Test runners
├── services/             # Service tests
└── conftest.py           # Pytest configuration
```

### Test Types
- **Unit Tests** → pytest for backend, Vitest for frontend
- **Integration Tests** → External service connectivity
- **E2E Tests** → Playwright with Electron MCP
- **Performance Tests** → Load and timing validation

## Deployment Architecture

### Build System
- **Backend** → Python packaging with uv
- **Frontend** → Electron with Vite bundling
- **Cross-Platform** → Windows, macOS, Linux support
- **Auto-Updates** → Built-in update mechanism

### Distribution
- **Desktop App** → Electron installer packages
- **CLI Tool** → Python package distribution
- **Documentation** → Markdown-based guides
- **Release Process** → Automated version bumping

## Evolution Strategy

### Architecture Evolution
- **Modular Design** → Clear separation of concerns
- **Plugin Architecture** → Extensible skill system
- **API Stability** → Versioned interfaces
- **Backward Compatibility** → Graceful migration paths

### Learning Loop Integration
- **Pattern Discovery** → Analyze successful builds
- **Convention Updates** → Auto-evolving steering files
- **Performance Tuning** → Adaptive optimization
- **Architecture Refactoring** → Guided improvements

---

*This architecture document evolves with the project through the Learning Loop system.*
