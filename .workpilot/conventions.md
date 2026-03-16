# Project Conventions

This file defines project-specific conventions and patterns that all AI agents must follow.

## Version History
- v1.0.0 - Initial conventions setup
- Last updated: 2025-01-16

## Code Style Conventions

### Python Backend
- Use Ruff for linting and formatting
- Follow PEP 8 with 4-space indentation
- Type hints required for all public functions
- Docstrings follow Google style

### TypeScript Frontend  
- Use Biome for linting and formatting
- Strict TypeScript mode enabled
- Functional components with hooks
- Tailwind CSS for styling

### File Naming
- Python: `snake_case.py`
- TypeScript: `PascalCase.tsx` for components, `camelCase.ts` for utilities
- Markdown: `kebab-case.md`
- Directories: `kebab-case`

## Architecture Patterns

### Agent Structure
- All agents inherit from base agent class
- Use structured prompts with clear sections
- Implement proper error handling and recovery
- Log all decisions and reasoning

### Frontend Components
- Use atomic design principles
- Components in `components/` directory
- Shared components in `shared/` subdirectory
- Feature-specific components in feature folders

### State Management
- Zustand for global state
- Local state with useState/useReducer
- Async state with React Query

## Development Workflow

### Git Conventions
- Feature branches: `feature/feature-name`
- Target: `develop` branch (not `main`)
- Conventional commits with semantic versioning

### Testing Requirements
- Backend: pytest with >80% coverage
- Frontend: Vitest + React Testing Library
- E2E: Playwright for critical user flows

### Code Review Process
- All PRs require automated checks
- Human review for architecture changes
- QA validation for feature branches

## AI Agent Guidelines

### Context Building
- Always build comprehensive task context
- Include relevant file contents and project structure
- Reference existing patterns and conventions

### Decision Making
- Explain reasoning for major decisions
- Reference this conventions file
- Ask for clarification when conventions conflict

### Output Formatting
- Use structured output with clear sections
- Include file paths and change summaries
- Provide testable and reviewable code

## Technology Stack

### Backend Dependencies
- Python 3.8+
- Claude Agent SDK (required)
- FastAPI for APIs
- SQLAlchemy for database

### Frontend Dependencies  
- React 19
- TypeScript strict
- Electron 39
- Tailwind CSS v4
- Zustand 5

## Security Guidelines

### Authentication
- Use Claude Agent SDK for all AI interactions
- Never expose API keys in code
- Use environment variables for secrets

### Input Validation
- Validate all user inputs
- Sanitize file paths and commands
- Use allowlists for dangerous operations

## Performance Standards

### Response Times
- Agent responses: <30 seconds
- UI interactions: <100ms
- File operations: progress indicators

### Memory Usage
- Monitor token usage in AI interactions
- Implement context optimization
- Cache frequently accessed data

## Integration Requirements

### External Services
- grepai for semantic search (localhost:9000)
- Graphiti for memory system
- GitHub/GitLab for issue tracking

### Internal APIs
- Use IPC handlers for Electron communication
- Follow established API patterns
- Implement proper error handling

---

*This file is automatically updated by the Learning Loop based on successful build patterns and project evolution.*
