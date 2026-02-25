# Claude Skills pour Auto-Claude EBP

Ce répertoire contient les skills Claude Code adaptés pour le projet Auto-Claude EBP (Business Planning).

## Skills disponibles

### Skills techniques
- **mcp-builder** : Guide pour créer des serveurs MCP de haute qualité
- **webapp-testing** : Boîte à outils pour tester les applications web locales avec Playwright

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

## Installation

Pour utiliser ces skills dans Claude Code :

```bash
/plugin marketplace add anthropics/skills
```

Puis installer les skills spécifiques :
```bash
/plugin install mcp-builder@anthropic-agent-skills
/plugin install webapp-testing@anthropic-agent-skills
```

## Adaptation EBP

Les skills sont adaptés pour le contexte Business Planning avec :
- Modèles de documents EBP
- Workflows d'analyse business
- Intégrations avec les outils EBP existants
