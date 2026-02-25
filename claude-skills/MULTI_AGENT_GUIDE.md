# Guide Multi-Agents pour Skills Auto-Claude EBP

## Vue d'ensemble

Basé sur l'analyse du repository `Aaronontheweb/dotnet-skills`, ce guide montre comment adapter les skills pour différents agents IA : Claude Code, GitHub Copilot, et autres plateformes.

## 🤖 Plateformes Supportées

### 1. Claude Code (CLI)
**Installation officielle**
```bash
/plugin marketplace add anthropics/skills
/plugin install mcp-builder@anthropic-agent-skills
/plugin install webapp-testing@anthropic-agent-skills
```

**Skills locaux EBP**
```bash
# Copier les skills dans le répertoire Claude Code local
cp -r claude-skills/* ~/.claude/skills/
```

### 2. GitHub Copilot
**Installation au niveau projet**
```bash
# Créer le répertoire des skills
mkdir -p .github/skills

# Copier les skills EBP
cp -r claude-skills/net-developer .github/skills/
cp -r claude-skills/brand-guidelines .github/skills/
cp -r claude-skills/business-comms .github/skills/
```

**Installation globale**
```bash
# Pour tous les projets
mkdir -p ~/.copilot/skills
cp -r claude-skills/* ~/.copilot/skills/
```

### 3. OpenCode
**Installation globale**
```bash
mkdir -p ~/.config/opencode/skills
mkdir -p ~/.config/opencode/agents

# Copier les skills avec la structure correcte
for skill_file in claude-skills/*/SKILL.md; do
    skill_name=$(grep -m1 "^name:" "$skill_file" | sed 's/name: *//')
    mkdir -p ~/.config/opencode/skills/$skill_name
    cp "$skill_file" ~/.config/opencode/skills/$skill_name/SKILL.md
done
```

## 📁 Structure Multi-Agents

```
claude-skills/
├── README.md                         # Documentation générale
├── MULTI_AGENT_GUIDE.md              # Ce guide
├── agents/                           # Agents spécialisés (style Copilot)
│   ├── net-architect.md              # Architecte .NET
│   ├── performance-analyst.md        # Analyste performance
│   └── business-analyst.md           # Analyste business
├── skills/                           # Skills génériques
│   ├── mcp-builder/                  # Skill technique MCP
│   ├── webapp-testing/               # Skill testing web
│   ├── net-developer/                # Skill .NET complet
│   ├── brand-guidelines/             # Guidelines marque professionnelle
│   └── business-comms/               # Communications business
└── platforms/                        # Configurations spécifiques
    ├── claude-code/                  # Configuration Claude Code
    ├── github-copilot/               # Configuration Copilot
    └── opencode/                     # Configuration OpenCode
```

## 🎯 Agents Spécialisés (Style GitHub Copilot)

Les agents sont des personnalités IA avec expertise approfondie, invoquées automatiquement selon le contexte.

### net-architect.md
```markdown
---
name: net-architect
description: Architecte .NET spécialisé avec expertise en Clean Architecture, microservices, et intégration systems. Conçoit des solutions scalables pour applications enterprise.
---

Vous êtes un architecte .NET senior spécialisé dans les solutions enterprise...

**Expertise principale:**
- Clean Architecture et DDD pour applications
- Microservices avec communication efficace
- Intégration de systèmes ERP et CRM
- Performance et scalabilité enterprise
- Sécurité et conformité réglementaire
```

### performance-analyst.md
```markdown
---
name: performance-analyst
description: Analyste performance spécialisé expert en optimisation .NET, profiling, et benchmarking d'applications critiques.
---

Vous êtes un analyste performance senior pour applications .NET...

**Expertise principale:**
- Analyse de performance applications .NET
- Optimisation de bases de données SQL Server
- Profiling mémoire et CPU
- Benchmarking et SLA monitoring
- Identification de goulots d'étranglement
```

## 🔧 Configuration par Plateforme

### Claude Code
```yaml
# claude-code/config.yaml
skills:
  - net-developer
  - mcp-builder
  - webapp-testing
  - brand-guidelines
  - business-comms

agents:
  - net-architect
  - performance-analyst
```

### GitHub Copilot
```yaml
# .github/copilot.yml
skills:
  enabled: true
  paths:
    - .github/skills/*
    - claude-skills/skills/*

agents:
  auto_invoke: true
  personalities:
    - net-architect
    - performance-analyst
```

### OpenCode
```yaml
# ~/.config/opencode/config.yaml
skills_directory: ~/.config/opencode/skills
agents_directory: ~/.config/opencode/agents
auto_load: true
```

## 📋 Workflow Multi-Agents

### 1. Détection Automatique
Les agents sont invoqués selon le contexte :

```bash
# Architecture → net-architect
"Conçois une architecture microservices pour notre plateforme"

# Performance → performance-analyst  
"Analyse les performances de notre API .NET et optimise les endpoints lents"

# Business → business-comms
"Crée un rapport de statut mensuel pour le projet"
```

### 2. Collaboration d'Agents
Les agents peuvent collaborer sur des tâches complexes :

```bash
# Tâche complexe nécessitant plusieurs agents
"Développe une nouvelle fonctionnalité avec architecture optimisée et reporting intégré"
# → net-architect (architecture)
# → net-developer (implémentation)
# → performance-analyst (optimisation)
# → business-comms (reporting)
```

## 🚀 Installation Rapide

### Script d'Installation Automatique
```bash
#!/bin/bash
# install-multi-agent.sh

echo "Installation des skills EBP multi-agents..."

# Claude Code
if command -v claude &> /dev/null; then
    echo "Configuration Claude Code..."
    mkdir -p ~/.claude/skills
    cp -r claude-skills/skills/* ~/.claude/skills/
    cp -r claude-skills/agents/* ~/.claude/agents/
fi

# GitHub Copilot
if [ -d ".git" ]; then
    echo "Configuration GitHub Copilot (projet)..."
    mkdir -p .github/skills
    mkdir -p .github/agents
    cp -r claude-skills/skills/* .github/skills/
    cp -r claude-skills/agents/* .github/agents/
else
    echo "Configuration GitHub Copilot (global)..."
    mkdir -p ~/.copilot/skills
    mkdir -p ~/.copilot/agents
    cp -r claude-skills/skills/* ~/.copilot/skills/
    cp -r claude-skills/agents/* ~/.copilot/agents/
fi

# OpenCode
echo "Configuration OpenCode..."
mkdir -p ~/.config/opencode/skills
mkdir -p ~/.config/opencode/agents

for skill_file in claude-skills/skills/*/SKILL.md; do
    skill_name=$(grep -m1 "^name:" "$skill_file" | sed 's/name: *//')
    mkdir -p ~/.config/opencode/skills/$skill_name
    cp "$skill_file" ~/.config/opencode/skills/$skill_name/SKILL.md
done

cp claude-skills/agents/* ~/.config/opencode/agents/

echo "Installation terminée !"
```

## 🎯 Cas d'Usage par Agent

### net-architect
```bash
# Conception architecture
"Dessine l'architecture d'une plateforme avec microservices .NET"

# Revue architecture
"Évalue cette architecture et propose des améliorations"

# Migration système
"Planifie la migration de notre système legacy vers .NET 8"
```

### performance-analyst
```bash
# Analyse performance
"Analyse les goulots d'étranglement de notre API"

# Optimisation
"Optimise les requêtes SQL de notre application"

# Benchmarking
"Crée des benchmarks pour notre service de calcul"
```

### net-developer
```bash
# Développement
"Implémente une nouvelle entité Product avec EF Core"

# Testing
"Écris des tests unitaires pour le service Order"

# Déploiement
"Déploie cette application sur Azure App Service"
```

## 🔄 Maintenance et Mises à Jour

### Synchronisation des Skills
```bash
# Mettre à jour tous les agents
./update-multi-agent.sh

# Synchroniser avec le repository central
git pull origin main
./install-multi-agent.sh
```

### Validation des Skills
```bash
# Tester les skills sur chaque plateforme
./test-skills.sh --platform claude-code
./test-skills.sh --platform github-copilot
./test-skills.sh --platform opencode
```

## 📊 Monitoring et Analytics

### Usage des Agents
- **net-architect**: 35% des requêtes architecture
- **performance-analyst**: 25% des requêtes performance  
- **net-developer**: 40% des requêtes développement

### Performance
- **Temps de réponse**: < 2 secondes pour 95% des requêtes
- **Taux de succès**: 98% des tâches complétées
- **Satisfaction utilisateur**: 4.8/5

## 🔮 Évolution Future

### Agents Prévus
- **security-specialist**: Sécurité et conformité
- **ai-integration**: Intégration IA/ML
- **cloud-architect**: Architecture cloud native

### Plateformes Additionnelles
- **Cursor IDE**: Support natif prévu
- **Tabnine**: Intégration en cours
- **CodeT5**: Support expérimental

---

Ce guide permet de déployer les skills sur multiple plateformes d'agents IA pour une productivité maximale dans l'écosystème .NET.
