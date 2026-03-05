# WorkPilot AI

**Autonomous multi-agent coding framework that plans, builds, and validates software for you.**

![WorkPilot AI Kanban Board](.github/assets/Auto-Claude-Kanban.png)

[![License](https://img.shields.io/badge/license-AGPL--3.0-green?style=flat-square)](./agpl-3.0.txt)
[![Discord](https://img.shields.io/badge/Discord-Join%20Community-5865F2?style=flat-square&logo=discord&logoColor=white)](https://discord.gg/KCXaPBr4Dj)
[![YouTube](https://img.shields.io/badge/YouTube-Subscribe-FF0000?style=flat-square&logo=youtube&logoColor=white)](https://www.youtube.com/@AndreMikalsen)
[![CI](https://img.shields.io/github/actions/workflow/status/tleub-ebp/Auto-Claude_EBP/ci.yml?branch=main&style=flat-square&label=CI)](https://github.com/tleub-ebp/Auto-Claude_EBP/actions)

---

## Download

### Stable Release

<!-- STABLE_VERSION_BADGE -->
[![Stable](https://img.shields.io/badge/stable-2.7.5-blue?style=flat-square)](https://github.com/tleub-ebp/Auto-Claude_EBP/releases/tag/v2.7.5)
<!-- STABLE_VERSION_BADGE_END -->

<!-- STABLE_DOWNLOADS -->
| Platform | Download |
|----------|----------|
| **Windows** | [WorkPilot-AI-2.7.5-win32-x64.exe](https://github.com/tleub-ebp/Auto-Claude_EBP/releases/download/v2.7.5/WorkPilot-AI-2.7.5-win32-x64.exe) |
| **macOS (Apple Silicon)** | [WorkPilot-AI-2.7.5-darwin-arm64.dmg](https://github.com/tleub-ebp/Auto-Claude_EBP/releases/download/v2.7.5/WorkPilot-AI-2.7.5-darwin-arm64.dmg) |
| **macOS (Intel)** | [WorkPilot-AI-2.7.5-darwin-x64.dmg](https://github.com/tleub-ebp/Auto-Claude_EBP/releases/download/v2.7.5/WorkPilot-AI-2.7.5-darwin-x64.dmg) |
| **Linux** | [WorkPilot-AI-2.7.5-linux-x86_64.AppImage](https://github.com/tleub-ebp/Auto-Claude_EBP/releases/download/v2.7.5/WorkPilot-AI-2.7.5-linux-x86_64.AppImage) |
| **Linux (Debian)** | [WorkPilot-AI-2.7.5-linux-amd64.deb](https://github.com/tleub-ebp/Auto-Claude_EBP/releases/download/v2.7.5/WorkPilot-AI-2.7.5-linux-amd64.deb) |
| **Linux (Flatpak)** | [WorkPilot-AI-2.7.5-linux-x86_64.flatpak](https://github.com/tleub-ebp/Auto-Claude_EBP/releases/download/v2.7.5/WorkPilot-AI-2.7.5-linux-x86_64.flatpak) |
<!-- STABLE_DOWNLOADS_END -->

### Beta Release

> ⚠️ Beta releases may contain bugs and breaking changes. [View all releases](https://github.com/tleub-ebp/Auto-Claude_EBP/releases)

<!-- BETA_VERSION_BADGE -->
[![Beta](https://img.shields.io/badge/beta-2.7.6--beta.2-orange?style=flat-square)](https://github.com/tleub-ebp/Auto-Claude_EBP/releases/tag/v2.7.6-beta.2)
<!-- BETA_VERSION_BADGE_END -->

<!-- BETA_DOWNLOADS -->
| Platform | Download |
|----------|----------|
| **Windows** | [WorkPilot-AI-2.7.6-beta.2-win32-x64.exe](https://github.com/tleub-ebp/Auto-Claude_EBP/releases/download/v2.7.6-beta.2/WorkPilot-AI-2.7.6-beta.2-win32-x64.exe) |
| **macOS (Apple Silicon)** | [WorkPilot-AI-2.7.6-beta.2-darwin-arm64.dmg](https://github.com/tleub-ebp/Auto-Claude_EBP/releases/download/v2.7.6-beta.2/WorkPilot-AI-2.7.6-beta.2-darwin-arm64.dmg) |
| **macOS (Intel)** | [WorkPilot-AI-2.7.6-beta.2-darwin-x64.dmg](https://github.com/tleub-ebp/Auto-Claude_EBP/releases/download/v2.7.6-beta.2/WorkPilot-AI-2.7.6-beta.2-darwin-x64.dmg) |
| **Linux** | [WorkPilot-AI-2.7.6-beta.2-linux-x86_64.AppImage](https://github.com/tleub-ebp/Auto-Claude_EBP/releases/download/v2.7.6-beta.2/WorkPilot-AI-2.7.6-beta.2-linux-x86_64.AppImage) |
| **Linux (Debian)** | [WorkPilot-AI-2.7.6-beta.2-linux-amd64.deb](https://github.com/tleub-ebp/Auto-Claude_EBP/releases/download/v2.7.6-beta.2/WorkPilot-AI-2.7.6-beta.2-linux-amd64.deb) |
| **Linux (Flatpak)** | [WorkPilot-AI-2.7.6-beta.2-linux-x86_64.flatpak](https://github.com/tleub-ebp/Auto-Claude_EBP/releases/download/v2.7.6-beta.2/WorkPilot-AI-2.7.6-beta.2-linux-x86_64.flatpak) |
<!-- BETA_DOWNLOADS_END -->

> All releases include SHA256 checksums and VirusTotal scan results for security verification.

---

## Quick Start

1. **Download and install** the app for your platform
2. **Open your project** — select a git repository folder
3. **Connect Claude** — the app will guide you through OAuth setup
4. **Create a task** — describe what you want to build
5. **Watch it work** — agents plan, code, and validate autonomously

Or from source:

```sh
pnpm install
pnpm run dev
```

See the [Setup Guide](docs/SETUP.md) for detailed instructions.

---

## Features

| Feature | Description |
|---------|-------------|
| **Autonomous Tasks** | Describe your goal; agents handle planning, implementation, and validation |
| **Parallel Execution** | Run multiple builds simultaneously with up to 12 agent terminals |
| **Isolated Workspaces** | All changes happen in git worktrees — your main branch stays safe |
| **Self-Validating QA** | Built-in quality assurance loop catches issues before you review |
| **Auto-Fix Loops** | Intelligent test-fix-test automation ([Guide](docs/features/auto-fix-loops.md)) |
| **AI-Powered Merge** | Automatic conflict resolution when integrating back to main |
| **Memory Layer** | Agents retain insights across sessions for smarter builds |
| **GitHub/GitLab Integration** | Import issues, investigate with AI, create merge requests |
| **Linear Integration** | Sync tasks with Linear for team progress tracking |
| **Quality Scorer** | AI code review — 0-100 scoring, 7 languages, auto-fix ([Guide](docs/QUALITY_SCORER.md)) |
| **Multi-Provider LLM** | OpenAI, Claude, Mistral, Ollama and more ([Guide](docs/PROVIDERS.md)) |
| **Cross-Platform** | Native desktop apps for Windows, macOS, and Linux |

---

## Interface

### Kanban Board
Visual task management from planning through completion. Create tasks and monitor agent progress in real-time.

### Agent Terminals
AI-powered terminals with one-click task context injection. Spawn multiple agents for parallel work.

![Agent Terminals](.github/assets/Auto-Claude-Agents-terminals.png)

### Roadmap
AI-assisted feature planning with competitor analysis and audience targeting.

![Roadmap](.github/assets/Auto-Claude-roadmap.png)

### Additional Features
- **Insights** — Chat interface for exploring your codebase
- **Ideation** — Discover improvements, performance issues, and vulnerabilities
- **Changelog** — Generate release notes from completed tasks

---

## Project Structure

```
WorkPilot-AI/
├── apps/
│   ├── backend/     # Python agents, specs, QA pipeline
│   └── frontend/    # Electron desktop application
├── docs/            # Documentation
├── guides/          # Additional guides
├── tests/           # Test suite
└── scripts/         # Build utilities
```

---

## CLI Usage

For headless operation, CI/CD integration, or terminal-only workflows:

```bash
cd apps/backend
python spec_runner.py --interactive   # Create a spec interactively
python run.py --spec 001              # Run autonomous build
python run.py --spec 001 --review     # Review
python run.py --spec 001 --merge      # Merge
```

See [guides/CLI-USAGE.md](guides/CLI-USAGE.md) for the full CLI reference.

---

## Security

WorkPilot AI uses a three-layer security model:

1. **OS Sandbox** — Bash commands run in isolation
2. **Filesystem Restrictions** — Operations limited to project directory
3. **Dynamic Command Allowlist** — Only approved commands based on detected project stack

All releases include SHA256 checksums and VirusTotal scans.

---

## Documentation

| Document | Description |
|----------|-------------|
| [Setup Guide](docs/SETUP.md) | Installation, requirements, scripts, dev environment |
| [Troubleshooting](docs/TROUBLESHOOTING.md) | Common issues and fixes |
| [Providers Guide](docs/PROVIDERS.md) | Multi-provider LLM setup, Grepai integration |
| [CLI Usage](guides/CLI-USAGE.md) | Headless / CI usage |
| [Contributing](CONTRIBUTING.md) | Code style, testing, PR process |
| [Linux Guide](guides/linux.md) | Flatpak, AppImage builds |

---

## Contributing

We welcome contributions! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style, testing requirements, and PR process.

---

## Community

- **Discord** — [Join our community](https://discord.gg/KCXaPBr4Dj)
- **Issues** — [Report bugs or request features](https://github.com/tleub-ebp/Auto-Claude_EBP/issues)
- **Discussions** — [Ask questions](https://github.com/tleub-ebp/Auto-Claude_EBP/discussions)

---

## License

**AGPL-3.0** — GNU Affero General Public License v3.0

WorkPilot AI is free to use. If you modify and distribute it, or run it as a service, your code must also be open source under AGPL-3.0. Commercial licensing available for closed-source use cases.

---

## Star History

[![GitHub Repo stars](https://img.shields.io/github/stars/tleub-ebp/Auto-Claude_EBP?style=social)](https://github.com/tleub-ebp/Auto-Claude_EBP/stargazers)

[![Star History Chart](https://api.star-history.com/svg?repos=tleub-ebp/Auto-Claude_EBP&type=Date)](https://star-history.com/#tleub-ebp/Auto-Claude_EBP&Date)