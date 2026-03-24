# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

WorkPilot AI is an autonomous multi-agent coding framework that plans, builds, and validates software for you. It's a monorepo with a Python backend (CLI + agent logic) and an Electron/React frontend (desktop UI).

> **Deep-dive reference:** [ARCHITECTURE.md](shared_docs/ARCHITECTURE.md) | [Architecture Deep Dives](shared_docs/README.md) | **Frontend contributing:** [apps/frontend/CONTRIBUTING.md](apps/frontend/CONTRIBUTING.md)

## Table of Contents

- [Product Overview](#product-overview)
- [Critical Rules](#critical-rules)
- [Project Structure](#project-structure)
- [Commands Quick Reference](#commands-quick-reference)
- [Backend Development](#backend-development)
  - [Claude Agent SDK Usage](#claude-agent-sdk-usage)
  - [Agent Prompts](#agent-prompts)
  - [Spec Directory Structure](#spec-directory-structure)
  - [Memory System (Graphiti)](#memory-system-graphiti)
  - [Skills System](#skills-system)
  - [Workflow Logger](#workflow-logger)
- [Frontend Development](#frontend-development)
  - [Tech Stack](#tech-stack)
  - [Path Aliases](#path-aliases)
  - [State Management (Zustand)](#state-management-zustand)
  - [Styling](#styling)
  - [IPC Communication](#ipc-communication)
  - [Agent Management](#agent-management)
  - [Claude Profile System](#claude-profile-system)
  - [Terminal System](#terminal-system)
- [Code Quality](#code-quality)
- [i18n Guidelines](#i18n-guidelines)
- [Cross-Platform](#cross-platform)
- [E2E Testing (Electron MCP)](#e2e-testing-electron-mcp)
- [Chrome DevTools MCP](#chrome-devtools-mcp)
- [Integrated Tools](#integrated-tools)
  - [grepai Integration](#grepai-integration)
- [Running the Application](#running-the-application)
- [Troubleshooting](#troubleshooting)

## Product Overview

WorkPilot AI is a desktop application (+ CLI) where users describe a goal and AI agents autonomously handle planning, implementation, and QA validation. All work happens in isolated git worktrees so the main branch stays safe.

**Core workflow:** User creates a task → Spec creation pipeline assesses complexity and writes a specification → Planner agent breaks it into subtasks → Coder agent implements (can spawn parallel subagents) → QA reviewer validates → QA fixer resolves issues → User reviews and merges.

**Main features:**

- **Autonomous Tasks** — Multi-agent pipeline (planner, coder, QA) that builds features end-to-end
- **Kanban Board** — Visual task management from planning through completion with preview/emulator support
- **Agent Terminals** — Up to 12 parallel AI-powered terminals with task context injection
- **Insights** — AI chat interface for exploring and understanding your codebase
- **Roadmap** — AI-assisted feature planning with strategic roadmap generation
- **Ideation** — Discover improvements, performance issues, and security vulnerabilities
- **GitHub/GitLab Integration** — Import issues, AI-powered investigation, PR/MR review and creation
- **Azure DevOps/Jira Integration** — Import work items, sync statuses
- **Microsoft Teams Notifications** — Webhook-based notifications for task completion and PR creation
- **Changelog** — Generate release notes from completed tasks
- **Memory System** — Graphiti-based knowledge graph retains insights across sessions
- **Isolated Workspaces** — Git worktree isolation for every build; AI-powered semantic merge
- **Self-Healing** — Incident response system with CI/CD failure analysis, proactive monitoring, and production responder
- **Pixel Office** — Multi-agent coordination visualization with task queue UI
- **Learning Loop** — Analytics and learning system for continuous improvement
- **App Emulator** — Preview running applications directly in the Kanban board (human review, AI review, done columns)
- **Chrome DevTools MCP** — Browser automation for coding and QA agents via Chrome DevTools Protocol
- **Pair Programming** — AI-assisted pair programming mode
- **Code Migration** — AI-guided code migration workflows
- **Design-to-Code** — Convert designs into code implementations
- **Performance Profiler** — AI-powered performance analysis and profiling
- **Documentation Agent** — Automated documentation generation and maintenance
- **Smart Estimation** — AI-based task complexity and effort estimation
- **Test Generation** — Automated test creation for existing code
- **Conflict Predictor** — AI-powered git conflict prediction
- **Arena Mode** — Compare AI model outputs side-by-side
- **MCP Marketplace** — Browse and install Model Context Protocol servers
- **Flexible Authentication** — Use a Claude Code subscription (OAuth) or API profiles with any Anthropic-compatible endpoint (e.g., Anthropic API, z.ai for GLM models)
- **Multi-Account Swapping** — Register multiple Claude accounts; when one hits a rate limit, WorkPilot AI automatically switches to an available account
- **Cross-Platform** — Native desktop app for Windows, macOS, and Linux with auto-updates

## Critical Rules

**Claude Agent SDK only** — All AI interactions use `claude-agent-sdk`. NEVER use `anthropic.Anthropic()` directly. Always use `create_client()` from `core.client`.

**i18n required** — All frontend user-facing text MUST use `react-i18next` translation keys. Never hardcode strings in JSX/TSX. Add keys to both `en/*.json` and `fr/*.json`.

**Platform abstraction** — Never use `process.platform` directly. Import from `apps/frontend/src/main/platform/` or `apps/backend/core/platform/`. CI tests all three platforms.

**No time estimates** — Never provide duration predictions. Use priority-based ordering instead.

**PR target** — Always target the `develop` branch for PRs to tleub-ebp/Auto-Claude_EBP, NOT `main`.

## Project Structure

WorkPilot_AI/
├── apps/
│   ├── backend/                      # Python backend/CLI — ALL agent logic
│   │   ├── core/                     # client.py, auth.py, worktree.py, platform/, workflow_logger.py
│   │   ├── security/                 # Command allowlisting, validators, hooks
│   │   ├── agents/                   # planner, coder, session management
│   │   ├── qa/                       # reviewer, fixer, loop, criteria
│   │   ├── spec/                     # Spec creation pipeline
│   │   ├── skills/                   # AI skills system with optimization
│   │   ├── cli/                      # CLI commands (spec, build, workspace, QA)
│   │   ├── context/                  # Task context building, semantic search
│   │   ├── runners/                  # 33 standalone runners (spec, roadmap, insights, github, self-healing, etc.)
│   │   ├── services/                 # Background services, recovery orchestration
│   │   ├── integrations/             # graphiti/, linear, github, windsurf_proxy
│   │   ├── project/                  # Project analysis, security profiles
│   │   ├── merge/                    # Intent-aware semantic merge for parallel agents
│   │   └── prompts/                  # Agent system prompts (.md)
│   └── frontend/                     # Electron desktop UI
│       └── src/
│           ├── main/                 # Electron main process
│           │   ├── agent/            # Agent queue, process, state, events
│           │   ├── claude-profile/   # Multi-profile credentials, token refresh, usage
│           │   ├── terminal/         # PTY daemon, lifecycle, Claude integration
│           │   ├── platform/         # Cross-platform abstraction
│           │   ├── ipc-handlers/     # 68 handler modules by domain
│           │   ├── services/         # SDK session recovery, profile service
│           │   └── changelog/        # Changelog generation and formatting
│           ├── preload/              # Electron preload scripts (electronAPI bridge)
│           ├── renderer/             # React UI
│           │   ├── components/       # UI components (onboarding, settings, task, terminal, github, etc.)
│           │   ├── stores/           # 60+ Zustand state stores
│           │   ├── contexts/         # React contexts (ViewStateContext)
│           │   ├── hooks/            # Custom hooks (useIpc, useTerminal, etc.)
│           │   ├── styles/           # CSS / Tailwind styles
│           │   └── App.tsx           # Root component
│           ├── shared/               # Shared types, i18n, constants, utils
│           │   ├── i18n/locales/     # en/*.json, fr/*.json
│           │   ├── constants/        # themes.ts, etc.
│           │   ├── types/            # 30+ type definition files
│           │   └── utils/            # ANSI sanitizer, shell escape, provider detection
│           └── types/                # TypeScript type definitions
├── src/                              # Shared connectors and utilities
│   └── connectors/
│       └── grepai/                   # grepai semantic search integration
├── guides/                           # Documentation
├── tests/                            # Backend test suite
└── scripts/                          # Build and utility scripts

## Commands Quick Reference

### Setup

**Prerequisites:**
- Python 3.8+ with `uv` package manager
- Node.js 20+ with `pnpm 8+` package manager
- Git

```bash
# Install all dependencies from root
pnpm run install:all

# Or separately:
cd apps/backend && uv venv && uv pip install -r requirements.txt
cd apps/frontend && pnpm install
```

### Backend
```bash
cd apps/backend
python spec_runner.py --interactive            # Create spec interactively
python spec_runner.py --task "description"      # Create from task
python run.py --spec 001                        # Run autonomous build
python run.py --spec 001 --qa                   # Run QA validation
python run.py --spec 001 --merge                # Merge completed build
python run.py --list                            # List all specs
```

### Frontend
```bash
cd apps/frontend
npm run dev              # Dev mode (Electron + Vite HMR)
npm run build            # Production build
npm run test             # Vitest unit tests
npm run test:watch       # Vitest watch mode
npm run lint             # Biome check
npm run lint:fix         # Biome auto-fix
npm run typecheck        # TypeScript strict check
npm run package          # Package for distribution
```

### Testing

| Stack | Command | Tool |
|-------|---------|------|
| Backend | `apps/backend/.venv/bin/pytest tests/ -v` | pytest |
| Frontend unit | `cd apps/frontend && npm test` | Vitest |
| Frontend E2E | `cd apps/frontend && npm run test:e2e` | Playwright |
| All backend | `npm run test:backend` (from root) | pytest |

### Releases
```bash
node scripts/bump-version.js patch|minor|major  # Bump version
git push && gh pr create --base main             # PR to main triggers release
```

See [RELEASE.md](RELEASE.md) for full release process.

## Backend Development

### Claude Agent SDK Usage

Client: `apps/backend/core/client.py` — `create_client()` returns a configured `ClaudeSDKClient` with security hooks, tool permissions, and MCP server integration.

Model and thinking level are user-configurable (via the Electron UI settings or CLI override). Use `phase_config.py` helpers to resolve the correct values:

```python
from core.client import create_client
from phase_config import get_phase_model, get_phase_thinking_budget

# Resolve model/thinking from user settings (Electron UI or CLI override)
phase_model = get_phase_model(spec_dir, "coding", cli_model=None)
phase_thinking = get_phase_thinking_budget(spec_dir, "coding", cli_thinking=None)

client = create_client(
    project_dir=project_dir,
    spec_dir=spec_dir,
    model=phase_model,
    agent_type="coder",          # planner | coder | qa_reviewer | qa_fixer
    max_thinking_tokens=phase_thinking,
)

# Run agent session (uses context manager + run_agent_session helper)
async with client:
    status, response = await run_agent_session(client, prompt, spec_dir)
```

Working examples: `agents/planner.py`, `agents/coder.py`, `qa/reviewer.py`, `qa/fixer.py`, `spec/`

### Agent Prompts (`apps/backend/prompts/`)

37 root-level prompts + 22 GitHub-specific prompts in `prompts/github/`.

| Category | Prompts |
|----------|---------|
| **Core Build** | planner.md, coder.md, coder_recovery.md |
| **QA** | qa_reviewer.md, qa_fixer.md, validation_fixer.md |
| **Spec Pipeline** | spec_gatherer.md, spec_researcher.md, spec_writer.md, spec_critic.md, spec_quick.md, complexity_assessor.md |
| **Ideation** | ideation_code_improvements.md, ideation_code_quality.md, ideation_documentation.md, ideation_performance.md, ideation_security.md, ideation_ui_ux.md |
| **Incidents** | incident_cicd_analyzer.md, incident_proactive_analyzer.md, incident_production_responder.md |
| **Analysis** | architecture_reviewer.md, architecture_visualizer.md, breaking_change_detector.md, performance_profiler.md, insight_extractor.md, learning_analyzer.md |
| **Advanced** | browser_agent.md, code_migration.md, documentation_agent.md, environment_cloner.md, multi_repo_planner.md, intent_templates.md, followup_planner.md |
| **Roadmap** | roadmap_discovery.md, roadmap_features.md, competitor_analysis.md |
| **GitHub** | issue_analyzer.md, issue_triager.md, duplicate_detector.md, pr_reviewer.md, pr_orchestrator.md, pr_parallel_orchestrator.md, pr_fixer.md, pr_finding_validator.md, pr_template_filler.md, pr_ai_triage.md, pr_codebase_fit_agent.md, + 11 more |

### Spec Directory Structure

Each spec in `.auto-claude/specs/XXX-name/` contains: `spec.md`, `requirements.json`, `context.json`, `implementation_plan.json`, `qa_report.md`, `QA_FIX_REQUEST.md`

### Memory System (Graphiti)

Graph-based semantic memory in `integrations/graphiti/`. Configured through the Electron app's onboarding/settings UI (CLI users can alternatively set `GRAPHITI_ENABLED=true` in `.env-files/.env`). See [ARCHITECTURE.md](shared_docs/ARCHITECTURE.md#memory-system) for details.

### Skills System

Advanced AI skills system in `apps/backend/skills/` with token optimization and dynamic context management:

**Key Features:**
- **Token Optimization:** Compress metadata, limit descriptions to 512 chars, cache operations
- **Context Management:** Aggressive compaction at 70% limit, checkpoint system
- **Performance:** Default max_workers=3, timeout=25s, subagent delegation
- **Dynamic Registration:** Runtime skill validation and registration

**Usage Example:**
```python
from apps.backend.skills.skill_manager import skill_manager

# Execute optimized skill
result = await skill_manager.execute_skill(
    skill_name="framework-migration",
    action="analyze",
    context={"framework": "react", "project_path": "/path/to/project"}
)
```

**Files:**
- `skill_manager.py` - Main skill orchestration
- `context_optimizer.py` - Context compaction and checkpoints
- `token_optimizer.py` - Token counting and compression
- `dynamic_skill_manager.py` - Runtime skill registration

See `apps/backend/skills/CLAUDE.md` for detailed guidelines.

### Workflow Logger

Centralized logging system for tracking all AI agents, skills, hooks and workflows:

**Features:**
- Structured logging with visual indicators (🤖 agents, ⚡ skills, 🪝 hooks)
- Automatic duration tracking and trace IDs
- Both human-readable and JSON structured output
- Active trace monitoring

**Usage:**
```python
from core.workflow_logger import workflow_logger

# Log agent execution
trace_id = workflow_logger.log_agent_start("Claude Code", "refactor_task", {"file": "app.py"})
workflow_logger.log_agent_end("Claude Code", "success", {"changes": 5}, trace_id=trace_id)

# Log skill execution
skill_trace = workflow_logger.log_skill_start("framework-migration", "analyze", {"framework": "react"})
workflow_logger.log_skill_end("framework-migration", "success", {"migrations_found": 3}, trace_id=skill_trace)

# Monitor active traces
active = workflow_logger.get_active_traces()
```

## Frontend Development

### Tech Stack

React 19, TypeScript (strict), Electron 40, Zustand 5, Tailwind CSS v4, Radix UI, xterm.js 6, Vite 7, Vitest 4, Biome 2, Motion (Framer Motion)

### Path Aliases (tsconfig.json)

| Alias | Maps to |
|-------|---------|
| `@/*` | `src/renderer/*` |
| `@shared/*` | `src/shared/*` |
| `@preload/*` | `src/preload/*` |
| `@features/*` | `src/renderer/features/*` |
| `@components/*` | `src/renderer/shared/components/*` |
| `@hooks/*` | `src/renderer/shared/hooks/*` |
| `@lib/*` | `src/renderer/lib/*` |

### State Management (Zustand)

60+ stores in `src/renderer/stores/`. Key stores:

- `project-store.ts` — Active project, project list
- `task-store.ts` — Tasks/specs management
- `terminal-store.ts` — Terminal sessions and state
- `settings-store.ts` — User preferences
- `github/issues-store.ts`, `github/pr-review-store.ts` — GitHub integration
- `insights-store.ts`, `roadmap-store.ts`, `kanban-settings-store.ts`
- `self-healing-store.ts` — Incident management and production response
- `pixel-office-store.ts` — Multi-agent Pixel Office visualization
- `learning-loop-store.ts` — Learning analytics
- `app-emulator-store.ts` — App preview/emulator
- `arena-store.ts` — Model comparison arena
- `mcp-marketplace-store.ts` — MCP server marketplace
- `code-migration-store.ts`, `design-to-code-store.ts`, `visual-to-code-store.ts` — Code transformation
- `performance-profiler-store.ts`, `conflict-predictor-store.ts` — Analysis

Main process also has stores: `src/main/project-store.ts`, `src/main/terminal-session-store.ts`

### Styling

- **Tailwind CSS v4** with `@tailwindcss/postcss` plugin
- **7 color themes** (Default, Dusk, Lime, Ocean, Retro, Neo + more) defined in `src/shared/constants/themes.ts`
- Each theme has light/dark mode variants via CSS custom properties
- Utility: `clsx` + `tailwind-merge` via `cn()` helper
- Component variants: `class-variance-authority` (CVA)

### IPC Communication

Main ↔ Renderer communication via Electron IPC:
- **Handlers:** `src/main/ipc-handlers/` — organized by domain (github, gitlab, ideation, context, etc.)
- **Preload:** `src/preload/` — exposes safe APIs to renderer
- Pattern: renderer calls via `window.electronAPI.*`, main handles in IPC handler modules

### Agent Management (`src/main/agent/`)

The frontend manages agent lifecycle end-to-end:
- **`agent-queue.ts`** — Queue routing, prioritization, spec number locking
- **`agent-process.ts`** — Spawns and manages agent subprocess communication
- **`agent-state.ts`** — Tracks running agent state and status
- **`agent-events.ts`** — Agent lifecycle events and state transitions

### Claude Profile System (`src/main/claude-profile/`)

Multi-profile credential management for switching between Claude accounts:
- **`credential-utils.ts`** — OS credential storage (Keychain/Windows Credential Manager)
- **`token-refresh.ts`** — OAuth token lifecycle and automatic refresh
- **`usage-monitor.ts`** — API usage tracking and rate limiting per profile
- **`profile-scorer.ts`** — Scores profiles by usage and availability

### Terminal System (`src/main/terminal/`)

Full PTY-based terminal integration:
- **`pty-daemon.ts`** / **`pty-manager.ts`** — Background PTY process management
- **`terminal-lifecycle.ts`** — Session creation, cleanup, event handling
- **`claude-integration-handler.ts`** — Claude SDK integration within terminals
- Renderer: xterm.js 6 with WebGL, fit, web-links, serialize addons. Store: `terminal-store.ts`

## Code Quality

### Frontend
- **Linting:** Biome (`npm run lint` / `npm run lint:fix`)
- **Type checking:** `npm run typecheck` (strict mode)
- **Pre-commit:** Husky + lint-staged runs Biome on staged `.ts/.tsx/.js/.jsx/.json`
- **Testing:** Vitest + React Testing Library + jsdom

### Backend
- **Linting:** Ruff
- **Testing:** pytest (`apps/backend/.venv/bin/pytest tests/ -v`)

## i18n Guidelines

All frontend UI text uses `react-i18next`. Translation files: `apps/frontend/src/shared/i18n/locales/{en,fr}/*.json`

55 namespace files per language. Core namespaces: `common`, `navigation`, `settings`, `dialogs`, `tasks`, `errors`, `onboarding`, `welcome`, `analytics`, `appEmulator`, `arena`, `browserAgent`, `dashboard`, `github`, `gitlab`, `ideation`, `insights`, `kanban`, `learningLoop`, `llm`, `multiRepo`, `pairProgramming`, `pixelOffice`, `roadmap`, `selfHealing`, `streaming`, `terminal`, `testGeneration`, `voiceControl`, and more.

```tsx
import { useTranslation } from 'react-i18next';
const { t } = useTranslation(['navigation', 'common']);

<span>{t('navigation:items.githubPRs')}</span>     // CORRECT
<span>GitHub PRs</span>                             // WRONG

// With interpolation:
<span>{t('errors:task.parseError', { error })}</span>
```

When adding new UI text: add keys to ALL language files, use `namespace:section.key` format.

## Cross-Platform

Supports Windows, macOS, Linux. CI tests all three.

**Platform modules:** `apps/frontend/src/main/platform/` and `apps/backend/core/platform/`

| Function | Purpose |
|----------|---------|
| `isWindows()` / `isMacOS()` / `isLinux()` | OS detection |
| `getPathDelimiter()` | `;` (Win) or `:` (Unix) |
| `findExecutable(name)` | Cross-platform executable lookup |
| `requiresShell(command)` | `.cmd/.bat` shell detection (Win) |

Never hardcode paths. Use `findExecutable()` and `joinPaths()`. See [ARCHITECTURE.md](shared_docs/ARCHITECTURE.md#cross-platform-development) for extended guide.

## E2E Testing (Electron MCP)

QA agents can interact with the running Electron app via Chrome DevTools Protocol:

1. Start app: `npm run dev:debug` (debug mode for AI self-validation via Electron MCP)
2. Set `ELECTRON_MCP_ENABLED=true` in `.env-files/.env`
3. Run QA: `python run.py --spec 001 --qa`

Tools: `take_screenshot`, `click_by_text`, `fill_input`, `get_page_structure`, `send_keyboard_shortcut`, `eval`. See [ARCHITECTURE.md](shared_docs/ARCHITECTURE.md#end-to-end-testing) for full capabilities.

## Chrome DevTools MCP

Browser automation via [chrome-devtools-mcp](https://github.com/ChromeDevTools/chrome-devtools-mcp) is available for **coder** and **QA** agents. It provides 29 tools for navigation, input, screenshots, debugging, emulation, and network inspection.

**Enable:** Toggle "Chrome DevTools" in project Settings → Agent Tools → MCP Servers, or set `CHROME_DEVTOOLS_MCP_ENABLED=true` in `.env-files/.env`.

**Optional:** Set `CHROME_DEVTOOLS_PORT=9222` to connect to a running Chrome instance (e.g., the app emulator). Without it, agents launch a headless Chrome.

**Key tools:** `navigate_page`, `click`, `fill`, `take_screenshot`, `take_snapshot`, `evaluate_script`, `wait_for`, `emulate`, `list_network_requests`.

**Kanban integration:** The preview button (Monitor icon) is available on tasks in Human Review and AI Review columns, allowing visual validation before PR approval.

## Running the Application

```bash
# CLI only
cd apps/backend && python run.py --spec 001

# Desktop app
npm start          # Production build + run
npm run dev        # Development mode with HMR

# Project data: .auto-claude/specs/ (gitignored)
```

## Integrated Tools

### grepai Integration

Semantic code search tool integrated for enhanced AI agent code exploration:

**Setup:**
```bash
# Start grepai server (Docker or CLI on http://localhost:9000)
cd src/connectors/grepai
python test_grepai.py  # Test integration
```

**Usage in Agents:**
```python
from src.connectors.grepai.client import GrepaiClient

client = GrepaiClient("http://localhost:9000")
results = client.search("user authentication flow", top_k=5)
```

**Features:**
- Natural language code search
- Vector embeddings for semantic matching
- Call graph tracing with `grepai trace`
- JSON output for AI agent integration
- Fallback to standard grep when unavailable

**Files:**
- `src/connectors/grepai/client.py` - Python client
- `src/connectors/grepai/grepai/` - Embedded grepai tool
- `docs/grepai_integration.md` - Integration guide

## Troubleshooting

### Common Issues

**Claude Authentication Problems:**
```bash
# Check profile configuration
cat ~/.claude/profiles.json
# Refresh tokens automatically via UI or:
python -c "from main.claude_profile.token_refresh import refresh_all_tokens; refresh_all_tokens()"
```

**Build Issues Cross-Platform:**
```bash
# Use platform abstraction functions
from core.platform import isWindows, findExecutable, joinPaths

# Never hardcode paths
exe_path = findExecutable("node")  # Works on Win/Mac/Linux
full_path = joinPaths(["src", "components"])  # OS-agnostic
```

**grepai Connection Issues:**
```bash
# Check if grepai is running
curl http://localhost:9000/health
# Start grepai if needed
cd src/connectors/grepai && python grepai_launcher.py
```

**Memory System Issues:**
```bash
# Check Graphiti status
python -c "from integrations.graphiti.client import check_connection; print(check_connection())"
# Enable via environment if needed
export GRAPHITI_ENABLED=true
```

**Performance Issues:**
- Check skill optimization: `python apps/backend/skills/performance_test.py`
- Monitor workflow logs: `tail -f logs/workflow.log`
- Reduce concurrent agents in settings

### Getting Help

- Check `logs/workflow.log` for detailed execution traces
- Run `python apps/backend/.venv/bin/pytest tests/ -v` for test failures
- See [guides/](guides/) for detailed setup instructions
- Check [ARCHITECTURE.md](shared_docs/ARCHITECTURE.md) for system design
