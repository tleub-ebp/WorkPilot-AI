# Claude Skills pour Auto-Claude EBP

Ce répertoire contient les skills Claude Code adaptés pour le projet Auto-Claude EBP (Business Planning).

## Skills disponibles

### Skills techniques
- **mcp-builder** : Guide pour créer des serveurs MCP de haute qualité
- **webapp-testing** : Boîte à outils pour tester les applications web locales avec Playwright
- **net-developer** : Agent IA spécialisé pour le développement .NET (C#, ASP.NET Core, EF Core)

### Skills business (à adapter)
- **brand-guidelines** : Guidelines de marque pour les documents EBP
- **internal-comms** : Communications internes et reporting
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
```

#### GitHub Copilot
**Niveau projet:**
```bash
mkdir -p .github/skills
cp -r claude-skills/net-developer .github/skills/
cp -r claude-skills/ebp-brand-guidelines .github/skills/
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
```

#### Cursor IDE
```bash
mkdir -p ~/.cursor/skills
cp -r claude-skills/* ~/.cursor/skills/
```

## Adaptation EBP

Les skills sont adaptés pour le contexte Business Planning avec :
- Modèles de documents EBP
- Workflows d'analyse business
- Intégrations avec les outils EBP existants
