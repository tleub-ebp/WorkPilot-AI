# Guide d'Intégration des Skills Claude pour Auto-Claude EBP

## Vue d'ensemble

Ce guide explique comment les skills Claude Code ont été intégrés et adaptés pour le projet Auto-Claude EBP (Business Planning).

## Skills Intégrés

### 1. Skills Techniques (Originels)

#### mcp-builder
- **Source**: anthropics/skills/mcp-builder
- **Purpose**: Guide pour créer des serveurs MCP de haute qualité
- **Adaptation**: Traduction en français, maintien des fonctionnalités techniques
- **Utilisation**: Développement de connecteurs MCP pour les systèmes EBP

#### webapp-testing
- **Source**: anthropics/skills/webapp-testing  
- **Purpose**: Test d'applications web avec Playwright
- **Adaptation**: Traduction des scripts helper, maintien des fonctionnalités
- **Utilisation**: Testing des interfaces frontend EBP

### 2. Skills Business (Adaptés EBP)

#### ebp-brand-guidelines
- **Source**: Adapté de anthropics/skills/brand-guidelines
- **Purpose**: Guidelines de marque EBP pour documents business
- **Adaptation**: 
  - Couleurs EBP (Bleu #0056b3, Orange #ff6b35, Vert #27ae60, Rouge #e74c3c)
  - Typographie (Inter pour titres, Open Sans pour corps)
  - Templates de documents business
- **Utilisation**: Formatting cohérent des documents EBP

#### ebp-business-comms
- **Source**: Adapté de anthropics/skills/internal-comms
- **Purpose**: Communications business EBP standards
- **Adaptation**:
  - Templates de rapports de projet
  - Formats de newsletters business
  - Guidelines de communication interne
- **Utilisation**: Communications structurées et professionnelles

## Structure des Répertoires

```
claude-skills/
├── README.md                           # Vue d'ensemble
├── INTEGRATION_GUIDE.md               # Ce document
├── mcp-builder/                       # Skill technique MCP
│   ├── SKILL.md                       # Instructions complètes (FR)
│   └── scripts/                       # Scripts utilitaires
├── webapp-testing/                    # Skill technique web
│   ├── SKILL.md                       # Instructions (FR)
│   └── scripts/
│       └── with_server.py             # Script serveur (FR)
├── ebp-brand-guidelines/              # Skill business branding
│   ├── SKILL.md                       # Guidelines EBP
│   └── examples/
│       └── business-report-template.md # Template de rapport
└── ebp-business-comms/                # Skill business communications
    ├── SKILL.md                       # Guidelines communications
    └── examples/
        └── project-reports.md         # Template de rapport de projet
```

## Installation dans Claude Code

### Méthode 1: Marketplace Officiel
```bash
# Ajouter le marketplace
/plugin marketplace add anthropics/skills

# Installer les skills originaux
/plugin install mcp-builder@anthropic-agent-skills
/plugin install webapp-testing@anthropic-agent-skills
```

### Méthode 2: Skills EBP Adaptés
Les skills EBP adaptés sont disponibles localement dans le projet:

1. **Copier les skills** dans le répertoire Claude Code local
2. **Activer les skills** via les paramètres Claude Code
3. **Utiliser les skills** en mentionnant leur nom dans les prompts

## Cas d'Usage EBP

### 1. Développement de Connecteurs MCP
```bash
# Utiliser mcp-builder pour créer un connecteur ERP
"Utilise le skill mcp-builder pour créer un serveur MCP qui se connecte à notre système ERP EBP"
```

### 2. Testing d'Applications Frontend
```bash
# Utiliser webapp-testing pour les interfaces EBP
"Utilise le skill webapp-testing pour tester notre dashboard de KPIs sur localhost:3000"
```

### 3. Création de Documents Business
```bash
# Utiliser ebp-brand-guidelines pour le formatting
"Utilise le skill ebp-brand-guidelines pour formater ce rapport business selon les standards EBP"
```

### 4. Communications de Projet
```bash
# Utiliser ebp-business-comms pour les rapports
"Utilise le skill ebp-business-comms pour créer un rapport de statut hebdomadaire pour le projet X"
```

## Adaptations Spécifiques EBP

### Guidelines de Marque
- **Couleurs**: Adaptées au branding EBP
- **Typographie**: Polices modernes et professionnelles
- **Templates**: Spécifiques aux documents business

### Communications Business
- **Format**: Standards de rapports de projet
- **KPIs**: Métriques business pertinentes
- **Structure**: Adaptée au contexte EBP

### Traduction
- **Interface**: Tous les textes traduits en français
- **Maintien**: Fonctionnalités techniques préservées
- **Contexte**: Terminologie business appropriée

## Maintenance et Mises à Jour

### Sync avec Skills Originels
1. **Surveiller** les mises à jour du repository anthropics/skills
2. **Évaluer** la pertinence des nouvelles fonctionnalités
3. **Adapter** les changements au contexte EBP
4. **Tester** l'intégration avec les workflows EBP

### Évolution des Skills EBP
1. **Collecter** les feedbacks des utilisateurs EBP
2. **Identifier** les besoins spécifiques non couverts
3. **Développer** de nouveaux templates et guidelines
4. **Documenter** les nouvelles fonctionnalités

## Bonnes Pratiques

### Utilisation des Skills
1. **Contexte**: Fournir un contexte clair sur les besoins EBP
2. **Templates**: Utiliser les templates fournis comme base
3. **Cohérence**: Maintenir la cohérence visuelle et structurelle
4. **Feedback**: Documenter les problèmes et suggestions d'amélioration

### Développement
1. **Standards**: Suivre les guidelines EBP dans tout développement
2. **Testing**: Utiliser webapp-testing pour les nouvelles interfaces
3. **Documentation**: Maintenir la documentation à jour
4. **Versioning**: Gérer les versions des skills et templates

## Support et Dépannage

### Problèmes Communs
- **Skills non reconnus**: Vérifier l'installation dans Claude Code
- **Templates incorrects**: Utiliser les dernières versions des examples
- **Traduction**: Signaler les textes mal traduits

### Ressources
- **Documentation**: Voir les fichiers SKILL.md pour les instructions détaillées
- **Examples**: Consulter les répertoires examples/ pour des cas concrets
- **Community**: Participer aux discussions sur les améliorations EBP

## Prochaines Étapes

1. **Expansion**: Ajouter plus de templates business spécifiques
2. **Intégration**: Connecter avec les systèmes EBP existants
3. **Automatisation**: Développer des workflows automatisés
4. **Formation**: Créer des guides de formation pour les équipes

---

*Ce guide sera mis à jour régulièrement pour refléter les évolutions des skills et les besoins changeants du projet Auto-Claude EBP.*
