# Claude Agent Skills

Ce dossier contient les skills Claude refactorisés selon les meilleures pratiques d'Agent Skills de Claude.

## Architecture

### Structure des Skills

```
skills/
├── skill_manager.py                # Gestionnaire des skills (chargement progressif)
├── migration/                      # Skill de migration de framework
│   ├── SKILL.md                    # Métadonnées et instructions du skill
│   ├── scripts/                    # Scripts exécutables
│   │   ├── analyze_stack.py        # Analyse du stack technologique
│   │   └── execute_migration.py    # Exécution de la migration
│   ├── data/                       # Données et ressources
│   │   └── breaking_changes.json   # Base de données des changements cassants
│   └── templates/                  # Templates de documents
│       └── migration_plan.md       # Template de plan de migration
└── README.md                       # Ce fichier
```

## Concepts Clés

### Chargement Progressif (3 Niveaux)

1. **Niveau 1 - Métadonnées** : Toujours chargées, découverte automatique
2. **Niveau 2 - Instructions** : Chargées quand le skill est déclenché
3. **Niveau 3 - Ressources** : Scripts et templates chargés à la demande

### Découverte Automatique

Les skills sont découverts automatiquement via leurs métadonnées YAML :

```yaml
---
name: framework-migration
description: Automate framework and version upgrades...
triggers: ["migration", "upgrade", "framework switch"]
---
```

## Utilisation

### Via le Skill Manager

```python
from skills.skill_manager import SkillManager

# Initialiser
manager = SkillManager("skills/")

# Trouver les skills pertinents
relevant = manager.get_relevant_skills("migrate react 18 to 19")

# Charger un skill spécifique
skill = manager.load_skill("framework-migration")

# Exécuter un script
result = skill.execute_script("analyze_stack.py", {
    "project-root": "/path/to/project"
})
```

### Via le Wrapper (Compatibilité)

```python
# Ancienne utilisation (toujours compatible)
from agents.migration_agent_skill_wrapper import MigrationAgent

agent = MigrationAgent(project_root="/path/to/project")
analysis = agent.analyze_stack()
plan = agent.create_migration_plan("react", "18.2", "19.0")
result = agent.execute_migration(plan.plan_id)
```

## Skills Disponibles

### Framework Migration (`framework-migration`)

**Description** : Automatisation des migrations de framework avec plans détaillés, résolution de dépendances, et support de rollback.

**Déclencheurs** :
- "migration", "upgrade", "framework switch"
- "react upgrade", "express to fastify"
- "javascript to typescript"

**Fonctionnalités** :
- Analyse automatique du stack technologique
- Base de données des changements cassants
- Génération de plans de migration
- Exécution avec rollback
- Tests de régression

**Scripts disponibles** :
- `analyze_stack.py` - Analyse du stack
- `execute_migration.py` - Exécution de la migration

## Avantages de l'Architecture Skills

### 1. Performance
- **Chargement progressif** : Réduction de l'usage de tokens
- **Découverte automatique** : Pas de chargement inutile
- **Exécution à la demande** : Scripts chargés seulement quand nécessaire

### 2. Maintenabilité
- **Skills isolés** : Chaque skill est indépendant
- **Tests unitaires** : Skills testables individuellement
- **Structure standardisée** : SKILL.md, scripts/, data/, templates/

### 3. Extensibilité
- **Ajout facile** : Nouveaux skills sans modifier le code
- **Réutilisabilité** : Skills portables entre projets
- **Composition** : Skills peuvent être combinés

### 4. Découverte
- **Matching automatique** : Basé sur les métadonnées
- **Tags et catégories** : Organisation facile
- **Déclencheurs intelligents** : Activation contextuelle

## Développement de Skills

### Créer un Nouveau Skill

1. **Créer la structure** :
```bash
mkdir skills/mon-skill
mkdir skills/mon-skill/scripts
mkdir skills/mon-skill/data
mkdir skills/mon-skill/templates
```

2. **Créer SKILL.md** :
```yaml
---
name: mon-skill
description: Description de ce que fait le skill
triggers: ["mot-clé1", "mot-clé2"]
category: development
---

# Mon Skill

Instructions détaillées de ce que fait le skill...
```

3. **Ajouter des scripts** dans `scripts/`
4. **Ajouter des données** dans `data/`
5. **Ajouter des templates** dans `templates/`

### Meilleures Pratiques

- **Métadonnées riches** : Description claire et déclencheurs pertinents
- **Scripts autonomes** : Chaque script doit être exécutable indépendamment
- **Gestion d'erreurs** : Retourner des résultats structurés avec succès/échec
- **Documentation** : Commentaires dans le code et exemples d'utilisation

## Migration depuis l'Ancienne Architecture

### Étapes de Migration

1. **Analyser l'agent existant** : Identifier les fonctionnalités principales
2. **Créer la structure du skill** : Dossiers scripts/, data/, templates/
3. **Extraire la logique** : Déplacer le code dans des scripts autonomes
4. **Créer SKILL.md** : Métadonnées et documentation
5. **Créer un wrapper** : Maintenir la compatibilité si nécessaire
6. **Tester** : Valider que tout fonctionne comme avant

### Exemple : Migration Agent

L'ancien `MigrationAgent` a été migré vers :
- **Skill** : `skills/migration/`
- **Scripts** : `analyze_stack.py`, `execute_migration.py`
- **Données** : `breaking_changes.json`
- **Wrapper** : `migration_agent_skill_wrapper.py`

Le wrapper maintient 100% de compatibilité avec l'interface originale.

## Commandes Utiles

### Lister les Skills
```bash
python skills/skill_manager.py --list
```

### Rechercher un Skill
```bash
python skills/skill_manager.py --search "migration"
```

### Trouver des Skills Pertinents
```bash
python skills/skill_manager.py --query "migrate react 18 to 19"
```

### Exécuter un Script de Skill
```bash
python skills/skill_manager.py --load framework-migration --execute analyze_stack.py --project-root /path/to/project
```

## Prochaines Étapes

### Skills à Créer

1. **Code Review Skills** : Pour les différents types de revue (logique, sécurité, qualité)
2. **Team Collaboration Skills** : Pour les rôles d'équipe (Developer, Architect, QA)
3. **Documentation Skills** : Pour la génération et mise à jour de documentation
4. **Testing Skills** : Pour la création et exécution de tests

### Améliorations

1. **Cache intelligent** : Mise en cache des résultats de scripts
2. **Parallélisation** : Exécution parallèle de scripts indépendants
3. **Monitoring** : Métriques d'utilisation des skills
4. **Versioning** : Gestion des versions de skills

---

Cette architecture basée sur les Agent Skills de Claude offre une foundation solide pour le développement d'agents spécialisés, réutilisables et performants.
