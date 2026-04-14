# Claude Skills pour WorkPilot AI

Ce répertoire contient les skills Claude Code adaptés pour le projet WorkPilot AI (Business Planning).

## Skills disponibles

### Skills techniques .NET (mis à jour pour .NET 10)
- **net-developer** : Agent IA spécialisé pour le développement .NET 10 (C# 13, ASP.NET Core 10, EF Core 10)
- **akka-net-patterns** : Expertise Akka.NET pour systèmes distribués avec actors et clustering
- **aspire-orchestration** : Expertise .NET Aspire pour orchestration cloud-native
- **benchmark-dotnet** : Expertise BenchmarkDotNet pour performance testing et optimisation
- **testcontainers-integration** : Expertise TestContainers pour tests d'intégration distribués
- **mcp-builder** : Guide pour créer des serveurs MCP de haute qualité
- **webapp-testing** : Boîte à outils pour tester les applications web locales avec Playwright

### Skills business (à adapter)
- **brand-guidelines** : Guidelines de marque professionnelle pour les documents business
- **business-comms** : Communications business standards professionnels
- **doc-coauthoring** : Co-création de documents business

## Structure

Chaque skill est un dossier contenant :
- `SKILL.md` : Métadonnées et instructions du skill
- `scripts/` : Scripts utilitaires (si applicable)
- `examples/` : Exemples d'utilisation (si applicable)
- `reference/` : Documentation de référence (si applicable)

## Installation Multi-Agents

### 🚀 Installation Rapide (Windows)
```bash
# Exécuter le script d'installation
claude-skills\install-multi-agent.bat

# Options disponibles:
# --all      : Toutes les plateformes
# --claude   : Claude Code uniquement  
# --copilot  : GitHub Copilot uniquement
# --opencode : OpenCode uniquement
# --cursor   : Cursor IDE uniquement
# --menu     : Menu interactif
```

### 🚀 Installation Rapide (Linux/Mac)
```bash
# Rendre exécutable et lancer
chmod +x claude-skills/install-multi-agent.sh
./claude-skills/install-multi-agent.sh --all
```

### 🤖 Plateformes Supportées

#### Claude Code (CLI)
```bash
/plugin marketplace add anthropics/skills
/plugin install mcp-builder@anthropic-agent-skills
/plugin install webapp-testing@anthropic-agent-skills
/plugin install net-developer@anthropic-agent-skills
/plugin install akka-net-patterns@anthropic-agent-skills
/plugin install aspire-orchestration@anthropic-agent-skills
/plugin install benchmark-dotnet@anthropic-agent-skills
/plugin install testcontainers-integration@anthropic-agent-skills
```

#### GitHub Copilot
**Niveau projet:**
```bash
mkdir -p .github/skills
cp -r claude-skills/net-developer .github/skills/
cp -r claude-skills/akka-net-patterns .github/skills/
cp -r claude-skills/aspire-orchestration .github/skills/
cp -r claude-skills/benchmark-dotnet .github/skills/
cp -r claude-skills/testcontainers-integration .github/skills/
cp -r claude-skills/brand-guidelines .github/skills/
```

**Niveau global:**
```bash
mkdir -p ~/.copilot/skills
cp -r claude-skills/* ~/.copilot/skills/
```

#### OpenCode
```bash
mkdir -p ~/.config/opencode/skills
cp -r claude-skills/skills/* ~/.config/opencode/skills/
cp -r claude-skills/agents/* ~/.config/opencode/agents/
```

#### Cursor IDE
```bash
mkdir -p ~/.cursor/skills
cp -r claude-skills/* ~/.cursor/skills/
```

## Agents IA Spécialisés

### Agents .NET (hybrides BMAD + Autonomous)
- **net-architect** : Architecte .NET senior avec expertise Clean Architecture et microservices
- **bmad-net-architect** : Architecte .NET hybride combinant exécution autonome et workflows BMAD structurés
- **dotnet-framework-48-expert** : Expert .NET Framework 4.8 spécialisé dans WCF, ASP.NET MVC 5, et maintenance d'applications legacy enterprise

### Agents Business
- **performance-analyst** : Analyste performance pour optimisation et benchmarking
- **business-analyst** : Analyste business pour requirements et modélisation métier

## Adaptation EBP

Les skills sont adaptés pour le contexte Business Planning avec :
- Modèles de documents EBP
- Workflows d'analyse business
- Intégrations avec les outils EBP existants
- Support .NET 10 avec principes modernes (immutabilité, type safety, performance)

## Nouvelles Fonctionnalités .NET 10

### Principes Modernes Intégrés
- **Immutabilité par défaut** : Records et value objects
- **Type safety** : Nullable reference types activés globalement
- **Performance-aware** : Span<T>, pooling, async streams
- **No magic** : Pas d'AutoMapper, pas de réflexion lourde
- **Composition over inheritance** : Classes sealed par défaut

### Technologies Pointues
- **Akka.NET** : Systèmes distribués avec actors
- **.NET Aspire** : Orchestration cloud-native
- **BenchmarkDotNet** : Performance testing automatisé
- **TestContainers** : Tests d'intégration distribués
- **OpenTelemetry** : Télémétrie distribuée
- **Playwright** : Testing E2E moderne
