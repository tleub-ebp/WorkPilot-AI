# Propositions de Nouvelles Features — WorkPilot AI (Auto-Claude EBP)

> Propositions basées sur l'audit complet de l'application réalisé le 20/02/2026 — Classées par domaine et impact.

---

## Table des matières

1. [Dashboard & Analytics](#1-dashboard--analytics)
2. [Intelligence Agent](#2-intelligence-agent)
3. [Collaboration & Équipe](#3-collaboration--équipe)
4. [Intégrations Externes](#4-intégrations-externes)
5. [Expérience Développeur (DX)](#5-expérience-développeur-dx)
6. [Multi-Provider LLM — Évolutions](#6-multi-provider-llm--évolutions)
7. [Sécurité Avancée](#7-sécurité-avancée)
8. [Productivité & Automatisation](#8-productivité--automatisation)
9. [UI/UX Avancé](#9-uiux-avancé)

---

## 1. Dashboard & Analytics

### 1.1 — Dashboard de métriques projet

**Description :** Tableau de bord centralisé affichant les KPIs du projet en temps réel.

**Métriques proposées :**
- Nombre de tâches par statut (Kanban summary)
- Temps moyen de complétion par complexité de spec
- Taux de succès QA au premier passage
- Nombre de tokens consommés par provider/par jour/par semaine
- Coût estimé par tâche (basé sur les tokens × pricing du provider)
- Nombre de conflits de merge résolus automatiquement vs manuellement

**Implémentation :**
- Nouveau composant `Dashboard.tsx` dans le renderer
- Store `dashboard-store.ts` avec agrégation des données depuis les stores existants
- Graphiques avec une librairie légère (Recharts ou Chart.js)
- Export PDF/CSV des rapports

**Impact :** Élevé — Permet aux utilisateurs de comprendre et optimiser leur usage.

---

### 1.2 — Historique et replay des sessions agent

**Description :** Enregistrer l'intégralité des sessions agent (prompts, réponses, actions) et permettre le replay.

**Fonctionnalités :**
- Timeline visuelle des actions d'un agent sur une tâche
- Diff viewer intégré pour voir les changements fichier par fichier
- Possibilité de "rejouer" une session avec un prompt modifié
- Export de la session pour partage ou audit

**Impact :** Élevé — Transparence, debugging, amélioration continue des prompts.

---

## 2. Intelligence Agent

### 2.1 — Agent de refactoring autonome

**Description :** Un nouveau type d'agent spécialisé dans le refactoring de code existant, complémentaire aux agents planner/coder/QA actuels.

**Capacités :**
- Détection automatique de code smells (God classes, fonctions trop longues, duplication)
- Propositions de refactoring avec preview du diff
- Exécution du refactoring avec tests de non-régression automatiques
- Support des design patterns (Extract Method, Strategy, Observer, etc.)

**Implémentation :**
- Nouveau module `agents/refactorer.py` avec prompt dédié `prompts/refactorer.md`
- Intégration dans le pipeline existant comme phase optionnelle post-QA
- Vue dédiée dans le frontend avec visualisation avant/après

---

### 2.2 — Agent de documentation automatique

**Description :** Générer et maintenir automatiquement la documentation du projet.

**Fonctionnalités :**
- Génération de docstrings/JSDoc pour les fonctions non documentées
- Création automatique de README pour chaque module
- Génération de diagrammes d'architecture (Mermaid) à partir du code
- Mise à jour automatique de la documentation quand le code change
- Support des formats : Markdown, JSDoc, Sphinx, Storybook

**Impact :** Moyen-Élevé — Réduit considérablement la dette de documentation.

---

### 2.3 — Mode "Pair Programming" interactif

**Description :** Au lieu du mode full-autonome, permettre un mode interactif où l'agent propose et l'utilisateur valide chaque étape.

**Fonctionnalités :**
- L'agent propose un plan → l'utilisateur approuve/modifie
- L'agent code un fichier → preview en temps réel → validation
- Possibilité de guider l'agent via des commentaires inline
- Mode "suggestion" comme un code review en temps réel

**Impact :** Élevé — Attire les développeurs qui veulent garder le contrôle.

---

### 2.4 — Apprentissage par feedback (RLHF-like)

**Description :** Système de feedback utilisateur sur les outputs des agents pour améliorer les prompts et le comportement au fil du temps.

**Fonctionnalités :**
- Boutons 👍/👎 sur chaque action d'agent
- Collecte structurée du feedback (qualité du code, pertinence, style)
- Analyse des patterns de feedback pour ajuster les system prompts
- Stockage dans le système de mémoire Graphiti existant
- Prompts personnalisés par projet basés sur l'historique de feedback

---

## 3. Collaboration & Équipe

### 3.1 — Mode multi-utilisateurs en temps réel

**Description :** Permettre à plusieurs développeurs de travailler sur le même projet WorkPilot AI simultanément.

**Fonctionnalités :**
- Synchronisation du Kanban board en temps réel (WebSocket/SSE)
- Indicateur de présence (qui est connecté, qui travaille sur quelle tâche)
- Lock automatique quand un agent travaille sur une spec
- Notifications en temps réel des changements de statut
- Chat intégré entre les membres de l'équipe

**Implémentation :**
- Backend WebSocket server (FastAPI supporte nativement les WebSockets)
- Store partagé via un broker (Redis Pub/Sub ou SQLite WAL)
- Gestion des conflits de modification concurrente

**Impact :** Très élevé — Transforme l'outil d'un usage solo en outil d'équipe.

---

### 3.2 — Système de templates de tâches

**Description :** Bibliothèque de templates réutilisables pour la création de tâches.

**Fonctionnalités :**
- Templates prédéfinis par type : feature, bugfix, refactoring, migration, etc.
- Templates personnalisés par projet (stockés dans `.auto-claude/templates/`)
- Variables de substitution (nom du composant, endpoint, etc.)
- Partage de templates entre projets
- Import/export au format YAML

---

### 3.3 — Code review assisté par IA

**Description :** Avant le merge, proposer une revue de code IA détaillée avec scoring.

**Fonctionnalités :**
- Analyse statique + analyse sémantique du diff
- Commentaires inline sur les points d'attention
- Score de qualité (extension du Quality Scorer existant)
- Détection de régressions potentielles
- Suggestions d'amélioration avec diff preview
- Intégration avec le système de PR GitHub/GitLab existant

---

## 4. Intégrations Externes

### 4.1 — Intégration Jira ✅ Implémentée

**Statut :** Terminée — Nouveau connecteur Jira Cloud complet avec client HTTP, modèles de données, connecteur haut niveau et synchronisation bidirectionnelle (49 tests unitaires passent).

**Description :** En plus de Linear et GitHub Issues, ajouter le support de Jira, très utilisé en entreprise.

**Implémentation réalisée :**
- `src/connectors/jira/exceptions.py` — Hiérarchie d'exceptions dédiée (`JiraError`, `JiraAuthenticationError`, `JiraConfigurationError`, `JiraProjectNotFoundError`, `JiraIssueNotFoundError`, `JiraAPIError`)
- `src/connectors/jira/models.py` — Modèles `JiraUser`, `JiraProject`, `JiraStatus`, `JiraIssue`, `JiraTransition`, `JiraComment` avec parsing ADF (Atlassian Document Format)
- `src/connectors/jira/client.py` — Client HTTP avec auth email+token, méthodes GET/POST/PUT, mapping d'erreurs automatique
- `src/connectors/jira/connector.py` — `list_projects()`, `search_issues()`, `get_issue()`, `create_issue()`, `update_issue()`, `get_transitions()`, `transition_issue()`, `sync_status_to_jira()`, `map_jira_status_to_workpilot()`, `add_comment()`, `create_bug_from_qa()`, `import_issues_for_kanban()`
- `src/connectors/jira/__init__.py` — Exports publics
- `tests/connectors/jira/test_client.py` — 22 tests (init, config, connect, GET, POST, erreurs HTTP, disconnect)
- `tests/connectors/jira/test_connector.py` — 27 tests (projets, issues, création, transitions, sync statut, QA, Kanban, modèles)

**Fonctionnalités :**
- ✅ Import de tickets Jira dans le Kanban (format compatible WorkPilot)
- ✅ Synchronisation bidirectionnelle du statut (mapping WorkPilot ↔ Jira)
- ✅ Création automatique de tickets Jira depuis les résultats QA
- ✅ Mapping des champs custom Jira (`customfield_XXXXX`)
- ✅ Support JQL (Jira Query Language) pour la recherche
- ✅ Parsing Atlassian Document Format (ADF) pour les descriptions

**Configuration requise (variables d'environnement) :**
```
JIRA_URL=https://your-org.atlassian.net
JIRA_EMAIL=user@example.com
JIRA_API_TOKEN=your_api_token
```

**Impact :** Élevé — Jira est omniprésent dans les entreprises, cible principale d'Auto-Claude EBP.

---

### 4.2 — Intégration Azure DevOps Boards (enrichie) ✅ Implémentée

**Statut :** Terminée — Le connecteur Azure DevOps Boards a été enrichi avec des opérations d'écriture complètes (21 tests unitaires passent).

**Description :** L'intégration Azure DevOps existe déjà (import de work items), mais elle peut être enrichie.

**Implémentation réalisée :**
- `src/connectors/azure_devops/work_items.py` — `create_work_item()`, `update_work_item()`, `link_work_items()` (sync bidirectionnelle des statuts, liaison de work items)
- `src/connectors/azure_devops/repos.py` — `create_pull_request()` (création de PR Azure Repos avec reviewers, work items liés, mode draft)
- `src/connectors/azure_devops/models.py` — Nouveau modèle `PullRequest` dataclass
- `src/connectors/azure_devops/__init__.py` — Méthodes exposées sur `AzureDevOpsConnector`
- `tests/connectors/azure_devops/test_work_items_enriched.py` — 21 tests unitaires

**Améliorations proposées (initiales) :**
- ✅ Synchronisation bidirectionnelle des statuts (pas juste import)
- ✅ Lien automatique entre les tâches WorkPilot et les work items ADO
- ✅ Création automatique de PR Azure Repos (en plus de GitHub)
- Affichage du statut des pipelines CI/CD Azure directement dans l'UI
- Support des Azure DevOps Wikis pour la documentation générée

---

### 4.3 — Intégration Slack / Microsoft Teams

**Description :** Notifications et interactions depuis les outils de communication d'équipe.

**Fonctionnalités :**
- Notifications temps réel : tâche terminée, QA échoué, merge réussi, rate limit atteint
- Commandes slash : `/workpilot create-task "description"`, `/workpilot status`
- Résumé quotidien automatique des activités
- Alertes de sécurité envoyées dans un channel dédié

---

### 4.4 — Intégration SonarQube / SonarCloud ✅ Implémentée

**Statut :** Terminée — Nouveau connecteur SonarQube complet avec client HTTP, modèles de données et connecteur haut niveau (40 tests unitaires passent).

**Description :** Connecter le système de QA existant avec SonarQube pour enrichir l'analyse de qualité.

**Implémentation réalisée :**
- `src/connectors/sonarqube/client.py` — Client HTTP avec auth par token, gestion d'erreurs, mapping d'exceptions
- `src/connectors/sonarqube/connector.py` — `list_projects()`, `get_measures()`, `get_quality_gate_status()`, `get_issues()`, `get_measures_history()`, `get_project_summary()`
- `src/connectors/sonarqube/models.py` — Modèles `SonarProject`, `SonarMeasure`, `SonarIssue`, `QualityGateStatus`, `QualityGateCondition`
- `src/connectors/sonarqube/exceptions.py` — Hiérarchie d'exceptions dédiée
- `tests/connectors/sonarqube/test_client.py` — 19 tests (init, connect, GET, erreurs HTTP)
- `tests/connectors/sonarqube/test_connector.py` — 21 tests (projets, métriques, quality gate, issues, summary, modèles)

**Fonctionnalités :**
- ✅ Import des métriques SonarQube dans le dashboard
- ✅ Vérification automatique que la Quality Gate passe avant le merge
- ✅ Historique de l'évolution de la dette technique
- L'agent QA prend en compte les issues SonarQube dans son évaluation

**Note :** Le MCP SonarQube est déjà configuré dans l'environnement, ce qui facilite l'intégration.

---

### 4.5 — Intégration Postman ✅ Implémentée

**Statut :** Terminée — Nouveau connecteur Postman complet avec client HTTP, modèles de données, connecteur haut niveau, génération de collections et validation structurelle (45 tests unitaires passent).

**Description :** Utiliser les collections Postman pour valider automatiquement les APIs générées.

**Implémentation réalisée :**
- `src/connectors/postman/exceptions.py` — Hiérarchie d'exceptions dédiée (`PostmanError`, `PostmanAuthenticationError`, `PostmanConfigurationError`, `PostmanCollectionNotFoundError`, `PostmanEnvironmentNotFoundError`, `PostmanAPIError`)
- `src/connectors/postman/models.py` — Modèles `PostmanWorkspace`, `PostmanCollection`, `PostmanRequest`, `PostmanEnvironment`, `PostmanTestResult`, `PostmanCollectionRun`
- `src/connectors/postman/client.py` — Client HTTP avec auth API key, méthodes GET/POST/PUT/DELETE, mapping d'erreurs automatique
- `src/connectors/postman/connector.py` — `list_workspaces()`, `list_collections()`, `get_collection()`, `get_collection_requests()`, `import_collection_as_spec()`, `generate_collection_from_endpoints()`, `list_environments()`, `get_environment()`, `sync_environment()`, `validate_collection_structure()`, `get_collection_summary()`
- `src/connectors/postman/__init__.py` — Exports publics
- `tests/connectors/postman/test_client.py` — 18 tests (init, config, connect, GET, POST, DELETE, erreurs HTTP, disconnect)
- `tests/connectors/postman/test_connector.py` — 27 tests (workspaces, collections, requests, import spec, génération, environnements, validation, summary, modèles)

**Fonctionnalités :**
- ✅ Import de collections Postman pour servir de spécification API
- ✅ Extraction récursive des requêtes (dossiers imbriqués supportés)
- ✅ Génération automatique de collections Postman depuis les endpoints créés (avec scripts de test intégrés)
- ✅ Synchronisation des environnements Postman avec les configs du projet
- ✅ Validation structurelle des collections (URL, méthodes HTTP)
- ✅ Résumé de collection pour dashboard (métriques par méthode HTTP)

**Configuration requise (variables d'environnement) :**
```
POSTMAN_API_KEY=PMAK-your-api-key
```

**Note :** Le MCP Postman est déjà disponible dans l'environnement.

---

## 5. Expérience Développeur (DX)

### 5.1 — Plugin VSCode / IDE

**Description :** Extension pour interagir avec WorkPilot AI directement depuis l'IDE.

**Fonctionnalités :**
- Créer une tâche depuis un commentaire `// TODO:` dans le code
- Voir le statut des tâches dans la barre latérale
- Lancer un agent sur un fichier/fonction sélectionné
- Recevoir les résultats QA comme des diagnostics inline
- Go-to-definition vers le code généré par l'agent

---

### 5.2 — CLI enrichi avec mode interactif TUI

**Description :** Améliorer le CLI existant avec une interface terminal interactive (TUI).

**Fonctionnalités :**
- Dashboard TUI avec `rich` ou `textual` (Python)
- Vue Kanban en mode texte
- Streaming en temps réel des logs d'agent
- Sélection interactive des specs avec fuzzy search
- Support des raccourcis clavier

---

### 5.3 — API REST publique documentée

**Description :** Exposer une API REST complète et documentée pour l'intégration dans des workflows custom.

**Fonctionnalités :**
- Documentation OpenAPI/Swagger auto-générée (FastAPI le supporte nativement)
- Endpoints : CRUD tasks, lancer un agent, obtenir le statut, récupérer les résultats
- Authentification par token API
- Webhooks pour les événements (task completed, QA failed, merge done)
- SDK client TypeScript/Python généré automatiquement

---

## 6. Multi-Provider LLM — Évolutions

### 6.1 — Routing intelligent multi-provider

**Description :** Router automatiquement les requêtes vers le provider optimal selon le contexte.

**Fonctionnalités :**
- Routing basé sur le type de tâche : Claude pour la planification, GPT pour le code, Ollama pour le feedback rapide
- Fallback automatique si un provider est down ou rate-limité (extension du système existant)
- A/B testing : exécuter la même tâche sur 2 providers et comparer les résultats
- Scoring de performance par provider/modèle/type de tâche
- Configuration par phase du pipeline (planning → model A, coding → model B, QA → model C)

---

### 6.2 — Support des modèles locaux avancé

**Description :** Enrichir le support Ollama/LM Studio avec des fonctionnalités avancées.

**Fonctionnalités :**
- Auto-détection des modèles locaux installés (partiellement existant via `ollama_model_detector.py`)
- Benchmark automatique des modèles locaux sur des tâches de référence
- Download et installation de modèles recommandés depuis l'UI
- Gestion de la mémoire GPU/RAM et alertes de dépassement
- Mode hybride : modèle local pour le brouillon, cloud pour la validation

---

### 6.3 — Estimation et contrôle des coûts

**Description :** Suivi en temps réel des coûts par provider et par tâche.

**Fonctionnalités :**
- Calcul du coût par token (input/output) pour chaque provider
- Budget par projet avec alertes de dépassement
- Estimation du coût avant lancement d'une tâche
- Rapport de coûts hebdomadaire/mensuel
- Optimisation automatique : suggestion du modèle le moins cher pour une tâche donnée

---

## 7. Sécurité Avancée

### 7.1 — Audit trail complet

**Description :** Journal d'audit traçant toutes les actions de l'application.

**Fonctionnalités :**
- Log de toutes les actions : création de tâche, exécution d'agent, merge, suppression, changement de config
- Horodatage, utilisateur, action, résultat, métadonnées
- Stockage sécurisé et inaltérable (append-only)
- Export pour conformité (SOC2, ISO 27001)
- Recherche et filtrage dans l'UI

---

### 7.2 — Sandbox renforcé pour l'exécution d'agents

**Description :** Renforcer l'isolation des agents au-delà du modèle de sécurité actuel.

**Fonctionnalités :**
- Exécution dans des containers Docker éphémères (optionnel)
- Limitation des ressources (CPU, RAM, I/O, réseau) par agent
- Whitelist de fichiers/répertoires accessibles (plus fin que le worktree actuel)
- Snapshots automatiques avant chaque exécution d'agent pour rollback instantané
- Mode "dry-run" : l'agent produit un plan sans exécuter

---

### 7.3 — Détection d'anomalies comportementales

**Description :** Surveiller le comportement des agents et alerter en cas d'activité suspecte.

**Fonctionnalités :**
- Détection de patterns anormaux : suppression massive de fichiers, accès réseau non attendu, modification de fichiers de config système
- Score de confiance par session d'agent
- Pause automatique + alerte si le score tombe sous un seuil
- Historique des comportements pour analyse post-mortem

---

## 8. Productivité & Automatisation

### 8.1 — Scheduling de tâches (Cron-like)

**Description :** Planifier l'exécution automatique de tâches récurrentes.

**Fonctionnalités :**
- Tâches récurrentes : scan de sécurité quotidien, mise à jour des dépendances hebdomadaire
- Exécution programmée : "lancer cette tâche ce soir à 22h"
- Chaînage de tâches : "quand la tâche A est finie, lancer la tâche B"
- Queue intelligente avec priorités et créneaux

---

### 8.2 — Auto-detection et création de tâches

**Description :** L'application détecte automatiquement des problèmes et propose des tâches.

**Sources de détection :**
- Issues GitHub/GitLab nouvellement assignées → tâche auto-créée
- Alertes de sécurité (dépendances, vulnérabilités) → tâche de correction
- Résultats d'idéation (module existant) → conversion en tâches one-click
- Erreurs récurrentes dans les logs → tâche de debugging
- Merge conflicts fréquents → tâche de refactoring

---

### 8.3 — Génération automatique de tests ✅ Implémentée

**Statut :** Terminée — Agent spécialisé complet avec analyseur de code AST, détection de gaps de couverture, génération de tests unitaires/E2E/TDD (30 tests unitaires passent).

**Description :** Agent spécialisé dans la génération de tests pour le code existant.

**Implémentation réalisée :**
- `apps/backend/agents/test_generator.py` — Agent complet avec :
  - `CodeAnalyzer` — Analyseur AST Python : extraction de fonctions, classes, arguments, types de retour, docstrings, décorateurs, estimation de complexité cyclomatique
  - `TestGeneratorAgent` — Agent principal avec méthodes :
    - `analyze_coverage()` — Détection des gaps de couverture en comparant source vs tests existants
    - `generate_unit_tests()` — Génération de tests unitaires (happy path, edge cases, error handling)
    - `generate_tests_from_user_story()` — Génération de tests E2E depuis des user stories (format Given/When/Then)
    - `generate_tdd_tests()` — Mode TDD : génération de tests avant l'implémentation
  - Modèles de données : `FunctionInfo`, `CoverageGap`, `GeneratedTest`, `TestGenerationResult`
- `tests/test_test_generator.py` — 30 tests unitaires (analyseur, modèles, agent, utilitaires)

**Fonctionnalités :**
- ✅ Analyse de la couverture de code existante (détection intelligente via noms de tests)
- ✅ Génération de tests unitaires pour les fonctions non couvertes (avec priorité high/medium/low)
- ✅ Estimation de complexité cyclomatique pour prioriser les tests
- ✅ Génération de tests E2E à partir des user stories (format Given/When/Then et bullet points)
- ✅ Mode "test-first" : écrire les tests avant l'implémentation (TDD assisté)
- ✅ Génération de fichiers de test complets avec imports et structure pytest
- ✅ Support optionnel d'un LLM provider pour génération assistée par IA

---

### 8.4 — Migration de framework assistée

**Description :** Agent spécialisé dans les migrations de frameworks et versions.

**Exemples d'usage :**
- Migration React 18 → 19
- Migration Express → Fastify
- Migration JavaScript → TypeScript
- Upgrade de dépendances majeures avec résolution automatique des breaking changes

---

## 9. UI/UX Avancé

### 9.1 — Mode sombre/clair automatique + thème custom

**Description :** L'application supporte déjà 7 thèmes. Aller plus loin.

**Améliorations :**
- Détection automatique du mode système (clair/sombre)
- Éditeur de thème custom avec color picker
- Import/export de thèmes
- Thème par projet (un thème différent pour chaque projet ouvert)

---

### 9.2 — Vue graphe des dépendances de tâches

**Description :** Visualisation sous forme de graphe des relations entre tâches.

**Fonctionnalités :**
- Vue dag (directed acyclic graph) des tâches et leurs dépendances
- Identification automatique des chemins critiques
- Drag-and-drop pour créer des liens de dépendance
- Détection de cycles et blocages
- Intégration avec `reactflow` (déjà installé dans le projet)

---

### 9.3 — Notifications desktop natives enrichies

**Description :** Utiliser les notifications système de manière plus riche.

**Fonctionnalités :**
- Notification quand une tâche termine (succès ou échec)
- Notification de rate limit avec action rapide (switch de profil)
- Notification de résultats QA avec score
- Résumé périodique ("3 tâches terminées cette heure")
- Actions rapides depuis la notification (approuver le merge, relancer la QA)

---

### 9.4 — Raccourcis clavier globaux

**Description :** Navigation complète au clavier pour les power users.

**Raccourcis proposés :**
- `Ctrl+N` — Nouvelle tâche
- `Ctrl+K` — Command palette (recherche universelle)
- `Ctrl+Shift+T` — Nouveau terminal
- `Ctrl+1-5` — Naviguer entre les vues (Kanban, Terminals, Insights, etc.)
- `Ctrl+Enter` — Lancer/Reprendre l'agent sur la tâche sélectionnée
- `/` — Recherche rapide dans le Kanban

---

### 9.5 — Command Palette (type VSCode)

**Description :** Barre de commande universelle accessible par `Ctrl+K` ou `Cmd+K`.

**Fonctionnalités :**
- Recherche de tâches, specs, fichiers, paramètres
- Exécution de commandes : "Create task", "Switch provider", "Open terminal"
- Historique des commandes récentes
- Actions contextuelles basées sur la vue active
- Fuzzy search intelligent

---

## Matrice de priorisation

| Feature | Effort | Impact Business | Différenciation |
|---------|--------|----------------|-----------------|
| Dashboard métriques | Moyen | 🔥🔥🔥 | Moyen |
| Agent refactoring | Élevé | 🔥🔥🔥 | Élevé |
| Mode pair programming | Moyen | 🔥🔥🔥🔥 | Très élevé |
| Intégration Jira | Moyen | 🔥🔥🔥🔥 | Moyen |
| Azure DevOps enrichi | Moyen | 🔥🔥🔥 | Élevé |
| Intégration Slack/Teams | Faible | 🔥🔥🔥 | Moyen |
| Intégration SonarQube | Faible | 🔥🔥 | Moyen |
| Plugin VSCode | Élevé | 🔥🔥🔥🔥 | Très élevé |
| Routing intelligent LLM | Élevé | 🔥🔥🔥 | Très élevé |
| Estimation des coûts | Moyen | 🔥🔥🔥🔥 | Élevé |
| Scheduling de tâches | Moyen | 🔥🔥🔥 | Moyen |
| Génération de tests | Élevé | 🔥🔥🔥🔥 | Élevé |
| Command Palette | Faible | 🔥🔥 | Moyen |
| Multi-utilisateurs | Très élevé | 🔥🔥🔥🔥🔥 | Très élevé |
| Audit trail | Moyen | 🔥🔥🔥 | Élevé (entreprise) |

---

## Quick Wins recommandés (< 1 semaine)

1. **Command Palette** — Implémentation simple avec un composant dialog + fuzzy search
2. **Raccourcis clavier** — Ajout d'un hook `useHotkeys` global
3. **Estimation coûts basique** — Calcul coût par token affiché dans le dashboard existant
4. **Intégration SonarQube** — Le MCP est déjà disponible, il suffit de consommer les données
5. **Notifications desktop enrichies** — Electron supporte nativement les notifications
6. **Templates de tâches** — Fichiers YAML dans `.auto-claude/templates/` + UI de sélection

---

## Roadmap suggérée

### Phase 1 — Fondations (Q1 2026)
- Dashboard métriques
- Estimation des coûts
- Command Palette + raccourcis clavier
- Templates de tâches
- Quick wins ci-dessus

### Phase 2 — Intelligence (Q2 2026)
- Mode pair programming interactif
- Agent de refactoring autonome
- Routing intelligent multi-provider
- Génération automatique de tests

### Phase 3 — Entreprise (Q3 2026)
- Intégration Jira
- Azure DevOps enrichi
- Intégration Slack/Teams
- Audit trail complet
- Sandbox renforcé

### Phase 4 — Collaboration (Q4 2026)
- Mode multi-utilisateurs
- API REST publique + SDK
- Plugin VSCode
- Agent de documentation
