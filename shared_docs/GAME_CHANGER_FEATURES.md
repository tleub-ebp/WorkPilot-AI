# Game Changer Features — WorkPilot AI

> Roadmap des fonctionnalités transformatrices qui différencieront WorkPilot AI de tout outil de développement assisté par IA existant.

---

## Table des matières

1. [Swarm Mode — Exécution Multi-Agent Parallèle](#1-swarm-mode)
2. [Continuous AI — Agent Autonome Always-On](#2-continuous-ai)
3. [Agent Time Travel — Replay avec Rembobinage](#3-agent-time-travel)
4. [Context Mesh — Intelligence Cross-Projets](#4-context-mesh)
5. [Live Development Companion — Pair Programming Temps Réel](#5-live-development-companion)

---

## 1. Swarm Mode

### Vision

Passer d'un pipeline séquentiel (spec → plan → code → QA) à une **équipe IA parallèle** où 2-8 agents travaillent simultanément sur des sous-tâches indépendantes, chacun dans son propre worktree, avec un Coordinator agent qui orchestre et un semantic merge qui fusionne les résultats.

**Impact attendu :** Une feature qui prend 45 min en séquentiel pourrait être livrée en 10-15 min.

### Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    Swarm Orchestrator                    │
│  ┌──────────────┐  ┌───────────────┐  ┌───────────────┐  │
│  │  Dependency  │  │     Wave      │  │    Merge      │  │
│  │  Analyzer    │──│   Executor    │──│  Coordinator  │  │
│  └──────────────┘  └───────────────┘  └───────────────┘  │
│         │                  │                    │        │
│         ▼                  ▼                    ▼        │
│  ┌──────────┐    ┌──────────────┐     ┌──────────────┐   │
│  │ Subtask  │    │  Wave 1      │     │  Semantic    │   │
│  │ Graph    │    │  ┌──┐┌──┐┌──┐│     │  Merge       │   │
│  │ (DAG)    │    │  │A1││A2││A3││     │  Pipeline    │   │
│  └──────────┘    │  └──┘└──┘└──┘│     └──────────────┘   │
│                  │  Wave 2      │                        │
│                  │  ┌──┐┌──┐    │                        │
│                  │  │A4││A5│    │                        │
│                  │  └──┘└──┘    │                        │
│                  └──────────────┘                        │
└──────────────────────────────────────────────────────────┘
```

### Concept de "Waves"

Les sous-tâches du plan d'implémentation sont organisées en **waves** (vagues) basées sur leurs dépendances :

- **Wave 1** : Toutes les sous-tâches sans dépendances (fondations, types, interfaces)
- **Wave 2** : Sous-tâches qui dépendent de Wave 1 (implémentations core)
- **Wave 3** : Sous-tâches qui dépendent de Wave 2 (intégrations, tests)
- **Wave N** : Suite jusqu'à complétion

Chaque wave exécute ses sous-tâches en parallèle. Entre chaque wave, un **semantic merge** fusionne les résultats dans le worktree principal avant de lancer la wave suivante.

### Dependency Analyzer

Analyse le `implementation_plan.json` pour construire un DAG (Directed Acyclic Graph) :

**Signaux de dépendance détectés :**
- Références explicites entre sous-tâches (`depends_on`, `after`)
- Analyse des fichiers modifiés : deux sous-tâches touchant le même fichier → dépendance
- Analyse sémantique : une sous-tâche crée une interface, une autre l'implémente → dépendance
- Types/imports : une sous-tâche exporte des types utilisés par une autre

**Résultat :** Un plan d'exécution en waves avec estimation du parallélisme maximal.

### Wave Executor

Pour chaque wave :

1. **Création de worktrees** — Un worktree isolé par sous-tâche (`workpilot/{specId}/swarm-{subtaskId}`)
2. **Spawn des agents** — Un processus Python par sous-tâche, chacun exécutant `run_autonomous_agent()` avec le contexte de sa sous-tâche uniquement
3. **Monitoring temps réel** — Suivi de progression via les marqueurs `__EXEC_PHASE__` stdout
4. **Gestion des échecs** — Si un agent échoue, retry automatique ou marquage pour exécution séquentielle dans la wave suivante
5. **Rate limit coordination** — Répartition intelligente des agents sur les profils Claude disponibles via `getRunningTasksByProfile()`

### Merge Coordinator

Après chaque wave :

1. Collecte les worktrees de toutes les sous-tâches complétées
2. Appelle `MergeOrchestrator.merge_tasks()` avec les `TaskMergeRequest` de la wave
3. Gère les conflits :
   - **Auto-résolu** → Continue
   - **AI-résolu** → Appelle `ai_resolver` avec le contexte des deux sous-tâches
   - **Humain requis** → Pause le swarm, notifie l'utilisateur
4. Applique le merge au worktree principal du spec
5. Met à jour le contexte pour la wave suivante

### Configuration

```json
{
  "swarm": {
    "enabled": true,
    "max_parallel_agents": 4,
    "wave_strategy": "dependency_graph",
    "merge_strategy": "semantic_auto",
    "fail_fast": false,
    "profile_distribution": "round_robin"
  }
}
```

### Intégration Pixel Office

Le Pixel Office visualise le swarm en temps réel :
- Chaque agent actif a un siège et un sprite animé
- Les agents en attente (wave suivante) sont dans la file d'attente
- Les connexions entre agents montrent les dépendances
- L'agent Coordinator est au centre avec une vue d'ensemble
- Les phases de merge sont animées (agents convergent vers le centre)

### Infrastructure existante réutilisée

| Composant | État actuel | Adaptation requise |
|-----------|-------------|-------------------|
| `AgentState` (Map<taskId, Process>) | Prêt | Ajouter `maxConcurrent` et grouping par swarm |
| `AgentProcessManager.spawnProcess()` | Prêt | Aucune modification |
| `MergeOrchestrator.merge_tasks()` | Prêt | Exposer via IPC handler |
| Worktrees (`workpilot/{specId}`) | Prêt | Sous-worktrees par subtask |
| `FileEvolutionTracker` | Prêt | Ajouter locking pour concurrent access |
| `PixelOfficeStore` | 6 sprites | Étendre pour N agents |
| Profile auto-swap | Prêt | Coordonner entre agents parallèles |

### Fichiers à créer/modifier

**Backend (Python) :**
- `apps/backend/agents/swarm/__init__.py` — Module package
- `apps/backend/agents/swarm/orchestrator.py` — Orchestrateur principal
- `apps/backend/agents/swarm/dependency_analyzer.py` — Analyse des dépendances et construction du DAG
- `apps/backend/agents/swarm/wave_executor.py` — Exécution parallèle d'une wave
- `apps/backend/agents/swarm/types.py` — Modèles de données (SwarmConfig, Wave, SubtaskNode, SwarmStatus)
- `apps/backend/runners/swarm_runner.py` — Runner entry point pour Electron

**Frontend (TypeScript) :**
- `apps/frontend/src/renderer/stores/swarm-store.ts` — État du swarm
- `apps/frontend/src/main/ipc-handlers/swarm-handlers.ts` — IPC handlers
- Modifications de `agent-queue.ts` pour supporter le spawn multi-agents
- Modifications de `pixel-office-store.ts` pour la visualisation swarm

---

## 2. Continuous AI

### Vision

Un **daemon IA** qui tourne en arrière-plan et agit proactivement sur le projet — pas un outil à la demande, mais un coéquipier toujours actif qui surveille, détecte et corrige automatiquement.

**Impact attendu :** Les bugs CI, les dépendances vulnérables et les issues triviales sont traités avant même que le développeur ne les voie.

### Modules

#### 2.1 CI/CD Watcher
- Écoute les webhooks GitHub Actions / GitLab CI / Azure Pipelines
- Sur échec CI : lance automatiquement le `self_healing_runner` avec le contexte du build
- Crée une PR de correction sans intervention humaine
- Notifie via Teams/Slack avec le résumé et le lien PR

#### 2.2 Dependency Sentinel (actuellement un shell UI de 22 lignes)
- Scan quotidien des dépendances (npm audit, pip-audit, cargo audit)
- Sur vulnérabilité détectée : analyse l'impact, propose un upgrade
- Si upgrade sûr (patch/minor, tests passent) : PR automatique
- Si upgrade risqué (major) : crée un ticket avec l'analyse d'impact

#### 2.3 Issue Auto-Responder
- Surveille les nouvelles issues GitHub/GitLab
- Auto-triage : assigne les labels, estime la complexité via `smart_estimation_runner`
- Pour les bug reports : tente de reproduire, localise le code fautif, propose un fix
- Pour les feature requests : crée un draft de spec via `spec_runner`

#### 2.4 PR Auto-Reviewer
- Review automatique de toute PR externe avant review humaine
- Utilise `pr_reviewer` + `pr_codebase_fit_agent` existants
- Génère un rapport structuré (sécurité, performance, conventions, tests manquants)
- Approuve automatiquement les PRs triviales (typos, docs) si configuré

#### 2.5 Performance Watchdog
- Monitore les métriques de performance (via Grafana/Datadog webhooks)
- Sur régression détectée : lance `performance_profiler_runner` automatiquement
- Corrèle la régression avec les commits récents via `git bisect` automatisé
- Propose un fix ou un revert

### Configuration

```json
{
  "continuous_ai": {
    "enabled": true,
    "modules": {
      "cicd_watcher": { "enabled": true, "auto_fix": true, "max_retries": 2 },
      "dependency_sentinel": { "enabled": true, "scan_interval": "daily", "auto_pr_patch": true },
      "issue_responder": { "enabled": true, "auto_triage": true, "auto_fix_bugs": false },
      "pr_reviewer": { "enabled": true, "auto_approve_trivial": false },
      "performance_watchdog": { "enabled": false, "grafana_url": "" }
    },
    "quiet_hours": { "start": "22:00", "end": "07:00" },
    "daily_budget_usd": 5.00
  }
}
```

### Infrastructure existante

- `self_healing_runner.py` (720 lignes) — CI failure analysis → à brancher sur webhook
- `smart_estimation_runner.py` — Estimation de complexité → triage automatique
- `github/pr_review_runner.py` (14,000+ lignes) — PR review complet → à déclencher automatiquement
- `dependency-sentinel-store.ts` (22 lignes) — Shell UI → à implémenter complètement

---

## 3. Agent Time Travel

### Vision

Transformer le système Agent Replay existant (recorder: 669 lignes, store: 457 lignes) en un véritable **debugger temporel** pour les agents IA. L'utilisateur peut rembobiner à n'importe quel point de décision d'un agent, modifier le contexte, et relancer l'exécution à partir de ce point.

**Impact attendu :** Résout le problème fondamental de confiance envers l'IA autonome — "pourquoi a-t-il fait ça ?" devient "je vais changer sa décision et voir le résultat".

### Fonctionnalités

#### 3.1 Timeline Interactive
- Visualisation chronologique de chaque décision de l'agent
- Chaque nœud affiche : le prompt envoyé, le raisonnement (thinking), les tool calls, les fichiers modifiés
- Filtre par type d'action (edit, create, delete, tool_use, thinking)
- Diff inline pour chaque modification de fichier

#### 3.2 Checkpoint System
- Snapshots automatiques à chaque décision clé (creation fichier, modification majeure, tool call)
- Snapshots du worktree à chaque point (git stash-like)
- Restauration instantanée de l'état du worktree à n'importe quel checkpoint

#### 3.3 Fork & Re-execute
- Sélectionner un checkpoint → modifier le contexte (ajouter une contrainte, changer une instruction)
- Relancer l'agent à partir de ce point avec le nouveau contexte
- L'agent hérite de tout le travail fait jusqu'au checkpoint
- Deux branches d'exécution comparables en A/B (déjà partiellement supporté par le replay store)

#### 3.4 Decision Heatmap
- Carte thermique des fichiers les plus modifiés par l'agent
- Identification des "points de décision critiques" (là où un mauvais choix a le plus d'impact)
- Score de confiance par décision basé sur le temps de réflexion et les hésitations de l'agent

### Infrastructure existante

- `replay/recorder.py` (669 lignes) — Enregistre déjà chaque step, tool call, file diff, token cost
- `replay-store.ts` (457 lignes) — Modèle complet avec breakpoints, A/B comparison, token timeline
- `session_history.py` (699 lignes) — Persistance des sessions

### Nouveau à construire

- Système de checkpoint worktree (git-based)
- UI de timeline interactive (composant React)
- Fork engine (re-créer le contexte agent à partir d'un checkpoint)
- Decision scoring algorithm

---

## 4. Context Mesh

### Vision

Exploiter le système Graphiti (3000+ lignes) pour créer une **intelligence cross-projets** — un réseau de connaissances qui s'enrichit à chaque interaction et transfère les patterns entre tous les projets de l'utilisateur.

**Impact attendu :** Plus l'utilisateur utilise WorkPilot AI, plus il devient intelligent. Un moat compétitif massif basé sur l'effet réseau personnel.

### Fonctionnalités

#### 4.1 Pattern Recognition Cross-Projet
- Détection automatique de patterns architecturaux récurrents
- "Dans le projet A, tu as résolu l'authentification avec JWT + refresh tokens. Le projet B utilise encore des sessions. Veux-tu migrer ?"
- Base de patterns : conventions de nommage, structures de projet, patterns de test, architectures

#### 4.2 Engineering Handbook Auto-Généré
- Document vivant qui capture les décisions d'architecture de tous les projets
- Organisé par domaine : auth, API design, state management, testing, deployment
- Chaque entrée liée aux commits et PRs qui l'ont introduite
- Consultable par les agents pendant la planification et le coding

#### 4.3 Skill Transfer
- Quand un agent apprend à utiliser une API/framework dans un projet, ce savoir est disponible pour tous les projets
- Propagation de conventions : si tu adoptes un pattern de test dans un projet, suggestion automatique dans les autres
- Détection de divergences : "Tes 3 projets React utilisent des patterns de state management différents"

#### 4.4 Contextual Recommendations
- Pendant la phase de spec/planning : "Basé sur tes projets précédents, cette feature prendrait typiquement X subtasks"
- Pendant le coding : "Ce pattern a causé un bug dans le projet X, voici comment le corriger"
- Pendant le QA : "Ce type de changement a historiquement introduit des régressions dans tes projets"

### Architecture Graphiti étendue

```
┌─────────────────────────────────────────┐
│              Context Mesh                │
│                                          │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐ │
│  │Project A │  │Project B │  │Project C │ │
│  │ Graphiti │  │ Graphiti │  │ Graphiti │ │
│  │  Graph   │  │  Graph   │  │  Graph   │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘ │
│       │              │              │       │
│       └──────┬───────┴──────┬───────┘       │
│              ▼              ▼               │
│  ┌───────────────────────────────────────┐ │
│  │       Cross-Project Knowledge Graph    │ │
│  │  Patterns │ Conventions │ Decisions    │ │
│  │  Skills   │ Failures   │ Preferences  │ │
│  └───────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
```

### Infrastructure existante

- `integrations/graphiti/` (8+ fichiers, 3000+ lignes) — Graph semantic memory
- `agents/feedback_learning.py` (746 lignes) — Pattern extraction et prompt optimization
- `learning_loop/` (1066 lignes) — Pattern extraction d'builds complétés
- `agents/memory.py` + `memory_manager.py` — Gestion mémoire par session

### Nouveau à construire

- Cross-project graph federation (lier les graphs Graphiti de projets différents)
- Pattern matcher cross-projet
- Engineering handbook generator
- UI pour visualiser et naviguer le knowledge graph

---

## 5. Live Development Companion

### Vision

Transformer le pair programming actuel (768 lignes, pas de file-watching) en un véritable **compagnon de développement temps réel** qui observe, comprend et intervient pendant que le développeur code — pas après.

**Impact attendu :** La vraie promesse du "pair programming IA" que personne n'a encore livrée. Un assistant qui connaît ton contexte et intervient au bon moment.

### Fonctionnalités

#### 5.1 File Watcher Intelligent
- Observe les modifications de fichiers en temps réel via `fs.watch` / chokidar
- Debounce intelligent : attend que le développeur finisse une séquence d'édition
- Analyse incrémentale : ne re-analyse que le delta, pas tout le fichier
- Connaissance du contexte : sait sur quelle feature/subtask le développeur travaille

#### 5.2 Bug Detection en Temps Réel
- Analyse statique incrémentale à chaque sauvegarde
- Détection de patterns de bugs connus (null pointer, race conditions, memory leaks)
- Vérification de cohérence : "Tu viens de modifier l'interface mais pas les implémentations"
- Vérification de contrats : "Cette modification casse le contrat API défini dans spec.md"

#### 5.3 Suggestions Proactives Contextuelles
- "Tu es en train de ré-implémenter un utilitaire qui existe déjà dans `utils/string-helpers.ts`"
- "Ce pattern est similaire à ce que tu as fait dans `auth/middleware.ts`, veux-tu extraire un helper ?"
- "Tu as oublié de mettre à jour les tests qui couvrent cette fonction"
- Suggestions non-intrusives : notification discrète, pas de popup bloquant

#### 5.4 Takeover Intelligent
- Détection de blocage : si le développeur ne progresse pas sur un fichier pendant > 2 min
- Proposition de prise en main : "Tu sembles bloqué sur le parsing. Je peux m'en occuper pendant que tu continues sur le composant ?"
- Mode hybride : l'IA prend en charge un fichier pendant que le développeur travaille sur un autre
- Transition fluide : l'IA montre ce qu'elle a fait, le développeur valide ou ajuste

#### 5.5 Context Awareness LSP
- Intégration avec le Language Server Protocol pour comprendre le code sémantiquement
- Navigation de types : comprend les relations d'héritage, les interfaces, les generics
- Scope awareness : sait quelles variables sont en scope, quels imports sont disponibles
- Refactoring assistance : détecte quand un renommage devrait propager à d'autres fichiers

### Architecture

```
┌─────────────────────────────────────────────────┐
│              Live Companion Engine                │
│                                                   │
│  ┌────────────┐  ┌──────────────┐  ┌───────────┐│
│  │ File Watch  │  │  Incremental │  │ Suggestion ││
│  │ Service     │──│  Analyzer    │──│ Engine     ││
│  │ (chokidar)  │  │  (debounced) │  │ (Claude)   ││
│  └────────────┘  └──────────────┘  └───────────┘│
│        │                │                 │       │
│        ▼                ▼                 ▼       │
│  ┌────────────┐  ┌──────────────┐  ┌───────────┐│
│  │ LSP Bridge  │  │  Takeover    │  │ Notif     ││
│  │             │  │  Detector    │  │ Manager   ││
│  └────────────┘  └──────────────┘  └───────────┘│
└─────────────────────────────────────────────────┘
```

### Infrastructure existante

- `agents/pair_programming.py` (768 lignes) — Agent logic (sans file watching)
- `pair_programming_runner.py` (382 lignes) — Runner (avec fallback demo mode)
- Terminal system (PTY daemon) — Infrastructure de communication
- Agent Replay — Enregistrement des actions pour review

### Nouveau à construire

- File watcher service (chokidar-based dans Electron main)
- Incremental analyzer (diff-based, pas full-file)
- Suggestion engine avec scoring de pertinence et timing
- Takeover detector (inactivité + complexité du code)
- LSP bridge pour context sémantique
- UI non-intrusive pour les suggestions (toast/sidebar)

---

## Priorité d'implémentation

| # | Feature | Effort estimé | Infrastructure existante | Différenciation |
|---|---------|---------------|--------------------------|-----------------|
| 1 | **Swarm Mode** | Moyen | Élevée (worktrees, merge, queue, pixel office) | Unique sur le marché |
| 2 | **Continuous AI** | Moyen-élevé | Moyenne (self-healing, PR review, estimation) | Game changer d'usage |
| 3 | **Context Mesh** | Moyen | Élevée (Graphiti, learning loop, feedback) | Moat compétitif |
| 4 | **Agent Time Travel** | Moyen | Élevée (replay recorder, session history) | Confiance utilisateur |
| 5 | **Live Companion** | Élevé | Faible (pair prog basique) | Promesse non tenue du marché |

---

## Métriques de succès

| Feature | KPI principal | Cible |
|---------|--------------|-------|
| Swarm Mode | Temps de completion d'une feature | -60% vs séquentiel |
| Continuous AI | Issues résolues sans intervention humaine | 30% des bugs triviaux |
| Agent Time Travel | Taux de re-run réussis après fork | >70% |
| Context Mesh | Suggestions cross-projet acceptées | >40% taux d'adoption |
| Live Companion | Bugs détectés avant commit | >50% des bugs de type |
