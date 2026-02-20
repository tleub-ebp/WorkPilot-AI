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

### 1.1 — Dashboard de métriques projet ✅ Implémentée

**Statut :** Terminée — Dashboard centralisé avec agrégation KPIs, snapshots temps réel, export JSON/CSV (40 tests unitaires passent).

**Description :** Tableau de bord centralisé affichant les KPIs du projet en temps réel.

**Implémentation réalisée :**
- `apps/backend/scheduling/dashboard_metrics.py` — Système complet avec :
  - `TaskStatus` — 5 statuts : pending, in_progress, completed, failed, cancelled
  - `TaskComplexity` — 4 niveaux : low, medium, high, critical
  - `MergeResolution` — 2 types : automatic, manual
  - `TaskRecord` — Enregistrement de tâche avec projet, statut, complexité, temps de complétion, sérialisation `to_dict()`
  - `QARecord` — Résultat QA avec passed/failed, score, numéro d'attempt
  - `TokenRecord` — Consommation de tokens par provider/modèle avec coût
  - `MergeRecord` — Résolution de conflit merge (automatique vs manuel)
  - `DashboardSnapshot` — Snapshot point-in-time avec tous les KPIs agrégés
  - `DashboardMetrics` — Classe principale :
    - `record_task()` — Enregistrer/mettre à jour une tâche (upsert par task_id)
    - `record_qa_result()` — Enregistrer un résultat QA
    - `record_token_usage()` — Enregistrer une consommation de tokens
    - `record_merge()` — Enregistrer une résolution de merge
    - `get_tasks()` / `get_qa_results()` / `get_token_records()` / `get_merge_records()` — Requêtes avec filtres
    - `get_snapshot()` — Générer un snapshot complet des KPIs
    - `export_report()` — Export JSON ou CSV
    - `get_stats()` — Statistiques globales multi-projets
- `tests/test_dashboard_metrics.py` — 40 tests unitaires (TaskRecord: 3, QARecord: 2, TokenRecord: 2, MergeRecord: 2, DashboardSnapshot: 2, recording: 8, queries: 5, snapshot KPIs: 8, export: 5, stats: 3)

**Métriques disponibles :**
- ✅ Nombre de tâches par statut (Kanban summary)
- ✅ Temps moyen de complétion par complexité de spec
- ✅ Taux de succès QA au premier passage
- ✅ Score QA moyen
- ✅ Nombre de tokens consommés par provider/par jour
- ✅ Coût total et coût par modèle
- ✅ Nombre de conflits de merge résolus automatiquement vs manuellement
- ✅ Export JSON et CSV des rapports

**Utilisation dans l'application :**

1. **Accès** : Dans la sidebar, aller dans **Insights** > onglet **Dashboard** (ou cliquer sur l'icône 📊 dans la barre de navigation)
2. **Vue d'ensemble** : La page affiche les KPIs principaux sous forme de cartes : tâches par statut (barres colorées), taux de QA first-pass (jauge), tokens consommés (graphique par jour), coûts (camembert par provider)
3. **Détails par complexité** : Section **Completion Times** montrant le temps moyen par complexité (low/medium/high/critical) sous forme de barres horizontales
4. **Merge conflicts** : Section **Merge Resolution** affichant un ratio automatique/manuel avec graphique donut
5. **Export** : Cliquer sur **Export JSON** ou **Export CSV** en haut à droite pour télécharger le rapport complet
6. **Multi-projets** : Utiliser le sélecteur de projet en haut de page pour basculer entre les projets

```python
from apps.backend.scheduling.dashboard_metrics import DashboardMetrics

dashboard = DashboardMetrics()

# Enregistrer des données
dashboard.record_task("my-project", "task-1", "Login page", status="completed",
    complexity="medium", completion_seconds=3600)
dashboard.record_qa_result("my-project", "task-1", passed=True, score=92.5, attempt=1)
dashboard.record_token_usage("my-project", "anthropic", "claude-sonnet-4-20250514",
    input_tokens=3000, output_tokens=1500, cost=0.0315)
dashboard.record_merge("my-project", "task-1", resolution="automatic")

# Obtenir le snapshot complet
snapshot = dashboard.get_snapshot("my-project")
print(f"Tasks: {snapshot.tasks_by_status}")
print(f"QA first-pass rate: {snapshot.qa_first_pass_rate}%")
print(f"Total tokens: {snapshot.total_tokens}")
print(f"Total cost: ${snapshot.total_cost:.4f}")
print(f"Auto merges: {snapshot.merge_auto_count}, Manual: {snapshot.merge_manual_count}")

# Exporter en CSV
csv_report = dashboard.export_report("my-project", fmt="csv")
with open("dashboard_report.csv", "w") as f:
    f.write(csv_report)
```

---

### 1.2 — Historique et replay des sessions agent ✅ Implémentée

**Statut :** Terminée — Système d'enregistrement et replay complet avec timeline visuelle, diff viewer, export/import JSON et comparaison de sessions (40 tests unitaires passent).

**Description :** Enregistrer l'intégralité des sessions agent (prompts, réponses, actions) et permettre le replay.

**Implémentation réalisée :**
- `apps/backend/agents/session_history.py` — Système complet avec :
  - `ActionType` — 11 types d'actions : prompt, response, tool_call, tool_result, file_read, file_write, file_delete, command, error, decision, plan
  - `SessionStatus` — 5 statuts : recording, completed, failed, cancelled, replaying
  - `SessionAction` — Action individuelle avec type, contenu, timestamp, métadonnées, durée
  - `FileChange` — Changement de fichier avec before/after, type (create/modify/delete), diff_summary automatique
  - `AgentSession` — Session complète avec actions ordonnées, changements de fichiers, tokens I/O, durée calculée, sérialisation `to_dict()`/`from_dict()`
  - `TimelineEntry` — Entrée pour la timeline visuelle (index, timestamp, type, résumé, détails)
  - `SessionRecorder` — Enregistreur principal :
    - `start_session()` — Démarrer l'enregistrement d'une session
    - `record_action()` — Enregistrer une action (prompt, réponse, tool call, etc.)
    - `record_file_change()` — Enregistrer un changement de fichier avec before/after
    - `end_session()` — Terminer l'enregistrement
    - `get_timeline()` — Timeline visuelle pour l'UI
    - `get_file_diffs()` — Diffs fichier par fichier
    - `export_session()` / `import_session()` — Export/import JSON
    - `list_sessions()` — Filtrage par tâche, type d'agent, statut
    - `get_stats()` — Statistiques globales
  - `SessionReplayer` — Rejoueur de sessions :
    - `prepare_replay()` — Préparer un replay avec prompts modifiés
    - `compare_sessions()` — Comparer original vs replay (actions, tokens, fichiers)
    - `list_replays()` — Lister les replays
- `tests/test_session_history.py` — 40 tests unitaires (SessionAction: 3, FileChange: 4, AgentSession: 4, lifecycle: 6, recording: 6, queries: 5, export/import: 4, replayer: 5, stats: 3)

**Fonctionnalités :**
- ✅ Timeline visuelle des actions d'un agent sur une tâche (avec résumés lisibles)
- ✅ Diff viewer intégré pour voir les changements fichier par fichier (before/after)
- ✅ Possibilité de "rejouer" une session avec un prompt modifié
- ✅ Comparaison entre session originale et replay (tokens, fichiers, durée)
- ✅ Export/import JSON de la session pour partage ou audit
- ✅ Filtrage des sessions par tâche, type d'agent et statut
- ✅ Tracking automatique des tokens consommés par session

**Utilisation dans l'application :**

1. **Accès** : Dans la sidebar, aller dans **Insights** > onglet **Session History** (ou cliquer sur une tâche dans le Kanban > **View Session**)
2. **Timeline** : La page affiche une timeline verticale des actions de l'agent : 📤 Prompts envoyés, 📥 Réponses reçues, 🔧 Tool calls, 📁 Fichiers modifiés, ❌ Erreurs. Chaque entrée est cliquable pour voir les détails.
3. **Diff viewer** : Cliquer sur l'onglet **File Changes** pour voir les modifications fichier par fichier en vue split (before/after) avec coloration syntaxique.
4. **Replay** : Cliquer sur **Replay Session** en haut à droite. Un éditeur s'ouvre permettant de modifier les prompts envoyés à l'agent. Cliquer sur **Run Replay** pour relancer la session avec les nouveaux prompts.
5. **Comparaison** : Après un replay, une vue **Compare** s'affiche côte à côte : nombre d'actions, tokens consommés, fichiers modifiés (same/different/only_a/only_b).
6. **Export** : Cliquer sur **Export JSON** pour télécharger la session complète. Partager le fichier pour audit ou debugging.
7. **Import** : Dans **Session History**, cliquer sur **Import Session** et sélectionner un fichier JSON pour charger une session partagée.

```python
from apps.backend.agents.session_history import SessionRecorder, SessionReplayer

recorder = SessionRecorder(project_id="my-project")

# Enregistrer une session
session = recorder.start_session("task-42", agent_type="coder")
recorder.record_action(session.session_id, "prompt", "Implement login page",
    metadata={"input_tokens": 500})
recorder.record_action(session.session_id, "response", "Here is the login code...",
    metadata={"output_tokens": 1200})
recorder.record_file_change(session.session_id, "src/login.py", "", "def login(): ...")
recorder.end_session(session.session_id, status="completed")

# Consulter la timeline
timeline = recorder.get_timeline(session.session_id)
for entry in timeline:
    print(f"  [{entry.timestamp}] {entry.action_type}: {entry.summary}")

# Exporter pour partage
json_export = recorder.export_session(session.session_id)

# Replay avec prompt modifié
replayer = SessionReplayer()
replay = replayer.prepare_replay(session, modified_prompts={0: "Implement login with OAuth2"})
comparison = replayer.compare_sessions(session, replay)
print(f"Same files: {comparison['same_file_changes']}")
```

**Impact :** Élevé — Transparence, debugging, amélioration continue des prompts.

---

## 2. Intelligence Agent

### 2.1 — Agent de refactoring autonome ✅ Implémentée

**Statut :** Terminée — Agent spécialisé avec détection AST de 12 types de code smells, propositions de refactoring par design patterns, exécution avec génération de tests de non-régression (40 tests unitaires passent).

**Description :** Un nouveau type d'agent spécialisé dans le refactoring de code existant, complémentaire aux agents planner/coder/QA actuels.

**Implémentation réalisée :**
- `apps/backend/agents/refactorer.py` — Agent complet avec :
  - `SmellType` — 12 types de code smells : long_method, god_class, duplicate_code, long_parameter_list, dead_code, deep_nesting, complex_conditional, magic_number, missing_docstring, too_many_returns, large_file, unused_import
  - `SmellSeverity` — 5 niveaux : info, low, medium, high, critical
  - `RefactoringPattern` — 12 patterns supportés : extract_method, extract_class, rename, inline, move_method, replace_conditional_with_polymorphism, introduce_parameter_object, remove_dead_code, simplify_conditional, add_docstring, extract_constant, split_file
  - `CodeSmell` — Détection avec fichier, ligne, message, symbole, métrique mesurée vs seuil
  - `RefactoringProposal` — Proposition avec pattern, description, preview before/after, smells liés, niveau de risque
  - `RefactoringResult` — Résultat avec fichiers modifiés, tests générés, code de test
  - `SmellDetector` — Détecteur AST configurable :
    - `detect_from_source()` / `detect_from_file()` — Détection multi-critères
    - Checks : long method, god class, long parameters, deep nesting, too many returns, missing docstring, large file, unused imports, duplicate code (sliding window), magic numbers
    - Seuils configurables pour chaque type de smell
  - `RefactoringAgent` — Agent principal :
    - `detect_smells()` / `detect_smells_from_source()` — Détection de code smells
    - `propose_refactoring()` — Propositions basées sur les smells détectés
    - `execute_refactoring()` — Exécution avec génération de tests de non-régression
    - `get_proposals()` — Filtrage par statut
    - `get_results()` / `get_stats()` — Historique et statistiques
- `tests/test_refactorer.py` — 40 tests unitaires (CodeSmell: 2, RefactoringProposal: 2, RefactoringResult: 2, long method: 3, god class: 2, parameters: 2, nesting: 2, docstring: 2, large file: 2, unused imports: 2, duplicates: 2, magic numbers: 2, detection: 3, proposals: 5, execution: 3, stats: 4)

**Capacités :**
- ✅ Détection automatique de code smells (God classes, fonctions trop longues, duplication, nesting, magic numbers, imports inutilisés)
- ✅ Propositions de refactoring avec pattern associé et niveau de risque
- ✅ Exécution du refactoring avec tests de non-régression automatiques
- ✅ Support de 12 design patterns (Extract Method, Extract Class, Introduce Parameter Object, etc.)
- ✅ Seuils configurables pour chaque type de smell
- ✅ Détection de sévérité dynamique (scale avec la gravité)
- ✅ Support optionnel LLM pour les transformations complexes

**Utilisation dans l'application :**

1. **Accès** : Dans la sidebar, aller dans **Code** > onglet **Refactoring** (ou dans le Kanban : cliquer sur une tâche terminée > **Refactor Code**)
2. **Analyser un fichier** : Cliquer sur **Analyze File** et sélectionner un fichier Python. Le système lance la détection de code smells et affiche les résultats.
3. **Code Smells** : Les smells détectés apparaissent dans une liste triée par sévérité (🔴 Critical/High, 🟡 Medium, 🔵 Low, ⚪ Info). Chaque smell indique le fichier, la ligne, le symbole et la métrique mesurée vs seuil.
4. **Propositions** : Cliquer sur **Generate Proposals** pour voir les refactorings suggérés. Chaque proposition indique le pattern (Extract Method, Split File, etc.), le symbole cible, le risque et l'impact estimé.
5. **Preview** : Cliquer sur une proposition pour voir le diff avant/après dans un viewer split.
6. **Exécuter** : Cliquer sur **Apply Refactoring** pour exécuter. Le système génère automatiquement des tests de non-régression et affiche le résultat.
7. **Configurer les seuils** : Aller dans **Settings** > **Refactoring Rules** pour ajuster les seuils (ex : max_method_lines, max_class_methods, max_parameters).

```python
from apps.backend.agents.refactorer import RefactoringAgent

agent = RefactoringAgent(thresholds={"max_method_lines": 25})

# Détecter les code smells
smells = agent.detect_smells_from_source(open("src/my_module.py").read())
for smell in smells:
    print(f"  [{smell.severity.value}] {smell.smell_type.value}: {smell.message}")

# Proposer des refactorings
proposals = agent.propose_refactoring(source=open("src/my_module.py").read())
for p in proposals:
    print(f"  [{p.risk_level}] {p.pattern.value}: {p.description}")

# Exécuter un refactoring
result = agent.execute_refactoring(proposals[0])
print(f"Success: {result.success}, Tests generated: {result.tests_generated}")
print(result.test_code)
```

---

### 2.2 — Agent de documentation automatique ✅ Implémentée

**Statut :** Terminée — Agent complet avec analyse AST de couverture documentaire, génération multi-format (Google, NumPy, Sphinx, JSDoc), README automatique, diagrammes Mermaid (40 tests unitaires passent).

**Description :** Générer et maintenir automatiquement la documentation du projet.

**Implémentation réalisée :**
- `apps/backend/agents/documenter.py` — Agent complet avec :
  - `DocFormat` — 6 formats : markdown, jsdoc, sphinx, storybook, google, numpy
  - `DiagramType` — 4 types : class_diagram, module_dependency, sequence, flowchart
  - `DocStatus` — 3 statuts : documented, partial, missing
  - `SymbolDoc` — Documentation d'un symbole avec statut, doc existante, doc générée, args, return type
  - `ModuleInfo` — Informations module : fichiers, classes, fonctions, dépendances, sous-modules
  - `DocGenerationResult` — Résultat avec symboles analysés/documentés, README, diagramme
  - `DocAnalyzer` — Analyseur de code :
    - `analyze_file()` / `analyze_source()` — Analyse de couverture documentaire par symbole
    - `analyze_directory()` — Analyse d'un répertoire module (fichiers, classes, imports, sous-modules)
    - Détection de documentation partielle (docstring sans section Args)
  - `DocGenerator` — Générateur de documentation :
    - `generate_docstring()` — Génération en 4 formats (Google, NumPy, Sphinx, JSDoc)
    - `generate_readme()` — README.md complet avec sections Files, Classes, Functions, Submodules, Dependencies
    - `generate_mermaid_class_diagram()` — Diagramme de classes Mermaid
    - `generate_mermaid_module_diagram()` — Diagramme de dépendances modules Mermaid
  - `DocumentationAgent` — Agent principal :
    - `generate_docstrings()` — Génération de docstrings pour les symboles non documentés
    - `generate_module_readme()` — Génération README + diagramme pour un module
    - `generate_architecture_diagram()` — Génération de diagrammes d'architecture
    - `check_documentation_coverage()` — Vérification de couverture (% documenté)
    - `get_history()` / `get_stats()` — Historique et statistiques
- `tests/test_documenter.py` — 40 tests unitaires (SymbolDoc: 2, ModuleInfo: 2, DocGenerationResult: 2, file analysis: 5, directory: 3, Google: 3, NumPy: 2, Sphinx: 2, JSDoc: 2, README: 3, diagrams: 3, docstrings: 4, README gen: 2, coverage: 3, stats: 2)

**Fonctionnalités :**
- ✅ Génération de docstrings pour les fonctions non documentées (4 formats : Google, NumPy, Sphinx, JSDoc)
- ✅ Détection de documentation partielle (docstring sans Args/Returns)
- ✅ Création automatique de README.md pour chaque module
- ✅ Génération de diagrammes d'architecture Mermaid (classes et dépendances)
- ✅ Vérification de couverture documentaire avec pourcentage
- ✅ Support optionnel LLM pour des descriptions plus intelligentes
- ✅ Note "Auto-generated by WorkPilot AI" dans les READMEs

**Utilisation dans l'application :**

1. **Accès** : Dans la sidebar, aller dans **Code** > onglet **Documentation** (ou cliquer sur un fichier dans l'explorateur > **Generate Docs**)
2. **Couverture** : La page affiche un résumé de la couverture documentaire du projet : jauge (% documenté), liste des symboles non documentés classés par fichier.
3. **Générer les docstrings** : Cliquer sur **Generate Docstrings** pour un fichier. Le système génère les docstrings manquants et les affiche en preview. Choisir le format (Google/NumPy/Sphinx/JSDoc) dans le sélecteur.
4. **Preview** : Chaque docstring généré est affiché en diff (before: pas de doc → after: docstring complet). Cliquer sur **Apply** pour insérer dans le code ou **Edit** pour modifier.
5. **README** : Cliquer sur **Generate README** pour un dossier module. Le README est généré avec la structure du module, les classes, fonctions et dépendances.
6. **Diagrammes** : Cliquer sur **Generate Diagram** pour voir le diagramme Mermaid (classes ou dépendances). Le diagramme est affiché en preview et peut être copié ou inséré dans un fichier Markdown.
7. **Configuration** : Dans **Settings** > **Documentation**, choisir le format par défaut (Google, NumPy, Sphinx, JSDoc).

```python
from apps.backend.agents.documenter import DocumentationAgent, DocFormat

agent = DocumentationAgent(default_format=DocFormat.GOOGLE)

# Vérifier la couverture documentaire
coverage = agent.check_documentation_coverage(file_path="src/connectors/jira/connector.py")
print(f"Coverage: {coverage['coverage_pct']}% ({coverage['documented']}/{coverage['total']})")

# Générer les docstrings manquants
result = agent.generate_docstrings(file_path="src/connectors/jira/connector.py")
for doc in result.generated_docs:
    if doc.generated_doc:
        print(f"  {doc.name}: {doc.generated_doc[:80]}...")

# Générer un README pour un module
result = agent.generate_module_readme("src/connectors/jira/")
print(result.readme_content)

# Générer un diagramme d'architecture
result = agent.generate_architecture_diagram(file_path="src/connectors/jira/connector.py")
print(result.diagram_content)
```

**Impact :** Moyen-Élevé — Réduit considérablement la dette de documentation.

---

### 2.3 — Mode "Pair Programming" interactif ✅ Implémentée

**Statut :** Terminée — Mode pair programming complet avec plan step-by-step, preview en temps réel, commentaires inline, suggestions de code et 3 modes d'interaction (40 tests unitaires passent). Étend le mode collaboratif Claude Teams existant avec une boucle utilisateur-dans-la-boucle.

**Description :** Au lieu du mode full-autonome, permettre un mode interactif où l'agent propose et l'utilisateur valide chaque étape.

**Implémentation réalisée :**
- `apps/backend/agents/pair_programming.py` — Système complet avec :
  - `StepStatus` — 8 statuts : proposed, previewing, approved, rejected, modified, in_progress, completed, skipped
  - `StepType` — 8 types : plan, code, test, refactor, review, documentation, config, command
  - `SessionMode` — 3 modes : step_by_step, suggestion, guided
  - `SuggestionStatus` — 4 statuts : pending, accepted, rejected, modified
  - `UserComment` — Commentaire inline de l'utilisateur avec référence ligne optionnelle
  - `CodeSuggestion` — Suggestion de code temps réel (original → suggested, avec explication)
  - `PlanStep` — Étape du plan avec type, titre, preview, commentaires, suggestions
  - `PairProgrammingPlan` — Plan complet avec progression (%, steps completed)
  - `PairProgrammingSession` — Session interactive principale :
    - `propose_plan()` — Proposer un plan (custom ou auto-généré)
    - `approve_plan()` — Approuver le plan global
    - `modify_plan()` — Modifier le plan (add/remove/reorder steps)
    - `preview_step()` — Générer un preview de code pour une étape
    - `approve_step()` / `reject_step()` / `skip_step()` / `complete_step()` — Contrôle de chaque étape
    - `add_user_comment()` — Ajouter un commentaire de guidage (pris en compte dans les previews)
    - `add_suggestion()` — Ajouter une suggestion de code (code review live)
    - `respond_to_suggestion()` — Accepter/rejeter une suggestion
    - `get_progress()` — Progression temps réel
    - `end_session()` — Terminer avec résumé
    - `get_event_log()` — Journal complet des événements
    - `to_dict()` — Sérialisation complète de l'état
- Intégration avec le module `apps/backend/teams/` existant (Claude Teams collaborative mode) — le pair programming ajoute la dimension "user-in-the-loop" au système de collaboration multi-agents
- `tests/test_pair_programming.py` — 40 tests unitaires (UserComment: 2, CodeSuggestion: 2, PlanStep: 3, Plan: 3, plan management: 6, step execution: 7, user interaction: 6, suggestions: 4, progress: 4, serialization: 3)

**Fonctionnalités :**
- ✅ L'agent propose un plan → l'utilisateur approuve/modifie/réordonne les étapes
- ✅ L'agent code un fichier → preview en temps réel → validation par l'utilisateur
- ✅ Possibilité de guider l'agent via des commentaires inline (pris en compte dans la génération)
- ✅ Mode "suggestion" comme un code review en temps réel (accept/reject/modify)
- ✅ 3 modes d'interaction : step-by-step, suggestion, guided
- ✅ Progression en temps réel (% complété, étapes par statut)
- ✅ Journal d'événements complet pour l'audit
- ✅ Modification du plan en cours (ajout/suppression/réordonnancement d'étapes)

**Utilisation dans l'application :**

1. **Accès** : Dans la sidebar, aller dans **Tasks** > sélectionner une tâche > cliquer sur **Pair Programming** (icône 👥) au lieu de **Run Agent** (mode autonome)
2. **Choisir le mode** : Un dialogue propose 3 modes :
   - **Step-by-step** (par défaut) : l'agent attend votre validation à chaque étape
   - **Suggestion** : l'agent code en continu et propose des suggestions que vous acceptez/rejetez
   - **Guided** : l'agent suit vos instructions à la lettre, étape par étape
3. **Approuver le plan** : L'agent propose un plan d'implémentation (ex : "1. Analyser les requirements, 2. Implémenter le composant, 3. Écrire les tests, 4. Review"). Vous pouvez :
   - ✅ **Approuver** le plan tel quel
   - ✏️ **Modifier** : ajouter, supprimer ou réordonner des étapes
   - ❌ **Rejeter** et demander un nouveau plan
4. **Preview & validation** : Pour chaque étape, l'agent génère un preview du code. Le code apparaît dans un éditeur avec coloration syntaxique. Vous pouvez :
   - ✅ **Approve** : valider et passer à l'étape suivante
   - ✏️ **Approve with modifications** : modifier le code puis valider
   - 💬 **Comment** : ajouter un commentaire inline (ex : "Utilise bcrypt ici") — l'agent en tient compte
   - ⏭️ **Skip** : sauter cette étape
   - ❌ **Reject** : rejeter avec raison
5. **Suggestions live** : En mode suggestion, l'agent propose des changements en temps réel (comme un code review). Chaque suggestion montre le code original, le remplacement suggéré et une explication. Cliquer sur ✅ Accept ou ❌ Reject.
6. **Progression** : La barre de progression en haut montre le % d'avancement. Chaque étape est marquée d'un badge (✅ Completed, ⏳ In Progress, ⏭️ Skipped, ❌ Rejected).
7. **Terminer** : Cliquer sur **End Session** pour voir le résumé : étapes complétées, commentaires ajoutés, suggestions acceptées, journal d'événements.

```python
from apps.backend.agents.pair_programming import PairProgrammingSession

session = PairProgrammingSession(project_id="my-project", task="Add user profile page")

# L'agent propose un plan
plan = session.propose_plan(steps=[
    {"step_type": "plan", "title": "Analyze requirements"},
    {"step_type": "code", "title": "Create UserProfile component", "file_path": "src/UserProfile.tsx"},
    {"step_type": "test", "title": "Write unit tests", "file_path": "tests/test_user_profile.py"},
    {"step_type": "review", "title": "Code review"},
])

# L'utilisateur approuve le plan
session.approve_plan()

# L'utilisateur ajoute un commentaire de guidage
session.add_user_comment(1, "Use TypeScript interfaces for the props")
session.add_user_comment(1, "Include avatar upload", line_number=25)

# Preview du code pour l'étape 1
preview = session.preview_step(1)
print(preview.code_preview)

# L'utilisateur approuve l'étape avec modifications
session.approve_step(1, modified=True)
session.complete_step(1)

# Progression
progress = session.get_progress()
print(f"Progress: {progress['progress_pct']}% ({progress['completed_steps']}/{progress['total_steps']})")

# Terminer la session
summary = session.end_session()
```

**Impact :** Élevé — Attire les développeurs qui veulent garder le contrôle.

---

### 2.4 — Apprentissage par feedback (RLHF-like) ✅ Implémentée

**Statut :** Terminée — Système de feedback structuré avec collecte, analyse de patterns, optimisation automatique des prompts et export/import (40 tests unitaires passent).

**Description :** Système de feedback utilisateur sur les outputs des agents pour améliorer les prompts et le comportement au fil du temps.

**Implémentation réalisée :**
- `apps/backend/agents/feedback_learning.py` — Système complet avec :
  - `FeedbackRating` — 3 niveaux : positive, negative, neutral
  - `FeedbackCategory` — 8 catégories : code_quality, relevance, style, performance, correctness, completeness, readability, security
  - `AgentPhase` — 7 phases : planning, coding, review, qa, documentation, refactoring, general
  - `PatternType` — 7 types de patterns : consistent_negative, consistent_positive, declining_quality, improving_quality, category_weakness, category_strength, phase_issue
  - `FeedbackEntry` — Entrée de feedback avec rating, scores par catégorie (1-5), commentaire, prompt utilisé, snippet de sortie, score moyen calculé
  - `FeedbackPattern` — Pattern détecté avec type, confiance, catégorie/phase affectée, recommandation
  - `PromptAdjustment` — Ajustement de prompt avec instruction originale/ajustée, raison, confiance
  - `FeedbackSummary` — Résumé avec taux positif, scores moyens par catégorie, ventilation par phase/agent, forces/faiblesses
  - `FeedbackCollector` — Collecteur principal :
    - `record_feedback()` — Enregistrer un feedback (rating + catégories + commentaire)
    - `get_feedback()` — Filtrage par session, rating, phase, agent, type de tâche
    - `get_feedback_by_id()` — Recherche par ID
    - `get_summary()` — Résumé avec filtres optionnels
    - `analyze_patterns()` — Détection de 7 types de patterns (négatif persistant, faiblesse catégorie, problème de phase, tendance déclinante/améliorante)
    - `export_feedback()` / `import_feedback()` — Export/import JSON
    - `get_stats()` — Statistiques globales
  - `PromptOptimizer` — Optimiseur de prompts basé sur les patterns :
    - `generate_adjustments()` — Générer des ajustements depuis les patterns détectés
    - `optimize_prompt()` — Optimiser un prompt en ajoutant des instructions basées sur le feedback
    - `get_prompt_for_phase()` — Instructions supplémentaires pour une phase spécifique
    - `get_adjustments()` / `get_applied_adjustments()` — Historique des ajustements
  - `CATEGORY_PROMPT_RULES` — 8 règles d'amélioration par catégorie
  - `PHASE_PROMPT_RULES` — 6 règles d'amélioration par phase de pipeline
- `tests/test_feedback_learning.py` — 40 tests unitaires (FeedbackEntry: 5, FeedbackPattern: 3, FeedbackCollector: 17, PromptOptimizer: 15)

**Fonctionnalités :**
- ✅ Boutons 👍/👎 sur chaque action d'agent avec scoring structuré (1-5) par catégorie
- ✅ Collecte structurée du feedback (code_quality, relevance, style, performance, correctness, completeness, readability, security)
- ✅ Analyse automatique des patterns de feedback (7 types de patterns détectés)
- ✅ Optimisation automatique des prompts basée sur les patterns (8 règles par catégorie + 6 par phase)
- ✅ Prompts personnalisés par projet basés sur l'historique de feedback
- ✅ Export/import JSON pour partage entre projets
- ✅ Résumés avec forces/faiblesses et ventilation par phase/agent
- ✅ Détection de tendances (qualité déclinante ou en amélioration)

**Utilisation dans l'application :**

1. **Accès** : Les boutons de feedback apparaissent directement dans l'interface partout où un agent produit une sortie :
   - Dans le **Kanban** : cliquer sur une tâche terminée → onglet **Agent Output** → boutons 👍/👎 sur chaque action
   - Dans **Session History** (Feature 1.2) : chaque entrée de la timeline a des boutons de feedback
   - En mode **Pair Programming** (Feature 2.3) : feedback sur chaque preview de code
2. **Feedback rapide** : Cliquer sur 👍 (positif) ou 👎 (négatif) pour un feedback rapide. Un dialogue optionnel s'ouvre pour un feedback détaillé.
3. **Feedback détaillé** : Cliquer sur **Rate Details** pour noter chaque catégorie (code_quality, relevance, style, etc.) sur une échelle de 1 à 5 étoiles. Ajouter un commentaire optionnel.
4. **Dashboard feedback** : Dans la sidebar, aller dans **Insights** > onglet **Feedback Analytics**. La page affiche :
   - Taux de feedback positif (jauge)
   - Scores moyens par catégorie (radar chart)
   - Tendances (graphique d'évolution dans le temps)
   - Top 3 forces et faiblesses
   - Patterns détectés avec recommandations
5. **Impact automatique** : Les prompts envoyés aux agents sont automatiquement enrichis avec des instructions basées sur le feedback. Par exemple, si le score « code_quality » est bas, le système ajoute « Ensure the generated code follows best practices... » au prompt.
6. **Export** : Dans **Feedback Analytics**, cliquer sur **Export JSON** pour télécharger l'historique de feedback.

```python
from apps.backend.agents.feedback_learning import FeedbackCollector, PromptOptimizer

collector = FeedbackCollector(project_id="my-project")

# Enregistrer un feedback rapide (👍/👎)
collector.record_feedback("session-1", "action-3", rating="positive",
    agent_type="coder", agent_phase="coding")

# Enregistrer un feedback détaillé
collector.record_feedback("session-1", "action-5", rating="negative",
    categories={"code_quality": 2, "relevance": 4, "style": 1},
    comment="Le code ne suit pas les conventions du projet",
    agent_type="coder", agent_phase="coding")

# Analyser les patterns
patterns = collector.analyze_patterns()
for p in patterns:
    print(f"  [{p.pattern_type.value}] {p.description}")
    print(f"    Recommandation: {p.recommendation}")

# Optimiser un prompt automatiquement
optimizer = PromptOptimizer(collector)
optimized = optimizer.optimize_prompt("Implement the login page", agent_phase="coding")
print(optimized)  # Prompt enrichi avec instructions basées sur le feedback

# Résumé global
summary = collector.get_summary()
print(f"Taux positif: {summary.positive_rate}%")
print(f"Forces: {summary.top_strengths}")
print(f"Faiblesses: {summary.top_weaknesses}")
```

**Impact :** Élevé — Amélioration continue des agents basée sur le feedback utilisateur.

---

## 3. Collaboration & Équipe

### 3.1 — Mode multi-utilisateurs en temps réel ✅ Implémentée

**Statut :** Terminée — Serveur de collaboration temps réel backend + frontend complet avec store Zustand, 6 composants React, i18n FR/EN, 50 tests backend + 35 tests frontend.

**Description :** Permettre à plusieurs développeurs de travailler sur le même projet WorkPilot AI simultanément avec une interface React complète.

**Implémentation réalisée :**

#### Backend — `apps/backend/teams/realtime_collaboration.py`
Serveur de collaboration complet avec :
- `UserStatus` — 4 statuts : online, away, busy, offline
- `EventType` — 16 types d'événements temps réel : user_joined, user_left, user_status_changed, task_updated, task_locked, task_unlocked, task_created, task_deleted, task_moved, chat_message, agent_started, agent_completed, notification, conflict_detected, sync_request, sync_response
- `LockType` — 2 types : user, agent
- `ConflictResolution` — 4 stratégies : last_write_wins, first_write_wins, manual, merge
- `ConnectedUser` — Utilisateur connecté avec statut, rôle, tâche en cours, curseur, horodatage
- `TaskLock` — Verrou sur une tâche (par utilisateur ou agent) avec raison et expiration
- `RealtimeEvent` — Événement temps réel avec type, expéditeur, données, cibles optionnelles (broadcast ou ciblé)
- `ChatMessage` — Message de chat avec réponses, mentions, pièces jointes
- `ConflictRecord` — Conflit de modification concurrente avec résolution
- `CollaborationServer` — Serveur principal :
  - `connect_user()` / `disconnect_user()` — Gestion connexion/déconnexion avec libération automatique des verrous
  - `get_connected_users()` / `get_all_users()` — Liste des utilisateurs en ligne/total
  - `update_user_status()` — Changement de statut (online/away/busy)
  - `set_user_current_task()` — Indicateur de présence (qui travaille sur quoi)
  - `lock_task()` / `unlock_task()` / `force_unlock_task()` — Verrouillage de tâches avec protection contre les conflits
  - `is_task_locked()` / `get_lock()` / `get_all_locks()` — Inspection des verrous
  - `broadcast_task_update()` — Synchronisation temps réel des changements de tâches (avec versioning)
  - `broadcast_task_move()` — Synchronisation des déplacements Kanban (drag-and-drop)
  - `detect_conflict()` / `resolve_conflict()` — Détection et résolution de conflits de modification concurrente
  - `send_chat_message()` — Chat d'équipe intégré avec réponses et mentions
  - `get_chat_history()` / `search_chat()` — Historique et recherche de messages
  - `on_event()` — Système d'événements avec listeners (par type ou wildcard)
  - `notify_user()` / `notify_all()` — Notifications ciblées ou broadcast
  - `notify_agent_started()` / `notify_agent_completed()` — Intégration agents (lock automatique + notification)
  - `request_sync()` — Synchronisation complète de l'état (reconnexion)
  - `get_stats()` — Statistiques du serveur

#### Frontend — Store Zustand
- `apps/frontend/src/renderer/stores/collaboration-store.ts` — Store Zustand complet avec :
  - **État** : currentUserId, projectId, connected, syncing, users, locks, chatMessages, conflicts, events, settings, chatOpen, unreadChatCount, replyingTo
  - **Actions connexion** : `initialize()`, `disconnect()`, `setConnected()`, `setSyncing()`
  - **Actions utilisateurs** : `addUser()`, `removeUser()`, `updateUserStatus()`, `setUserCurrentTask()`
  - **Actions verrous** : `lockTask()`, `unlockTask()`, `isTaskLocked()`, `getTaskLock()`
  - **Actions chat** : `addChatMessage()`, `sendMessage()`, `setReplyingTo()`, `toggleChat()`, `setChatOpen()`, `markChatRead()`
  - **Actions conflits** : `addConflict()`, `resolveConflict()`
  - **Actions événements** : `addEvent()` (avec ring buffer max 100)
  - **Actions settings** : `updateSettings()` (conflictStrategy, présence, chat, notifications)
  - **Computed** : `getOnlineUsers()`, `getStats()`, `getUnresolvedConflicts()`
  - Palette de 10 couleurs d'avatars avec hash déterministe par userId

#### Frontend — 6 composants React
- `apps/frontend/src/renderer/components/collaboration/` :
  - `PresenceIndicator.tsx` — Avatars circulaires avec statut coloré (🟢🟡🔴⚫), tooltip avec nom, statut et tâche en cours, overflow `+N` au-delà de 5 utilisateurs
  - `TaskLockBadge.tsx` — Badge 🔒 (user) ou 🤖 (agent) sur les cartes Kanban, popover avec détails du verrou et bouton force-unlock pour admins
  - `TeamChat.tsx` — Panel de chat flottant en bas à droite avec envoi/réception de messages, réponses, recherche, compteur de messages non lus, bulles colorées par utilisateur
  - `ConflictResolver.tsx` — Dialog modal de résolution avec comparaison côte-à-côte des deux versions, boutons "Garder la mienne" / "Garder la leur"
  - `CollaborationSettings.tsx` — Page de configuration complète : stratégie de résolution (4 options en grille), switch présence, paramètres chat (son, bureau), préférences de notifications (5 catégories)
  - `CollaborationNotifications.tsx` — Composant invisible écoutant le store d'événements et affichant des toasts pour user join/leave, task lock/unlock, agent start/complete, conflict detected
  - `index.ts` — Barrel export de tous les composants

#### i18n — Namespace `collaboration`
- `apps/frontend/src/shared/i18n/locales/en/collaboration.json` — 100+ clés EN couvrant : presence, locks, chat, conflicts, notifications, settings, sync, stats
- `apps/frontend/src/shared/i18n/locales/fr/collaboration.json` — Traductions FR complètes
- `apps/frontend/src/shared/i18n/index.ts` — Namespace `collaboration` enregistré dans la configuration i18next

#### Tests
- `tests/test_realtime_collaboration.py` — 50 tests unitaires backend (ConnectedUser: 3, TaskLock: 3, RealtimeEvent: 3, ChatMessage: 2, ConflictRecord: 2, users: 7, locks: 8, task updates: 4, chat: 4, conflicts: 3, events: 4, agent integration: 3, sync: 2, stats: 2)
- `apps/frontend/src/renderer/__tests__/collaboration-store.test.ts` — 35 tests unitaires frontend (Initialize & Connection: 3, User Management: 6, Task Locking: 6, Chat: 6, Conflicts: 4, Events: 3, Settings: 3, Computed & Stats: 4)

#### Corrections associées
- **Sentry DSN** : Corrigé dans `apps/frontend/electron.vite.config.ts` — chargement du `.env` frontend en priorité (override) après le `.env` racine, résolvant le message `[Sentry] No DSN configured - error reporting disabled in renderer`
- **i18n JIRA** : 30 chaînes hardcodées remplacées par des clés i18n dans `JiraIntegration.tsx` + ajout section `jira` dans `settings.json` EN/FR
- **i18n GitHub** : 5 chaînes hardcodées remplacées dans `GitHubIntegration.tsx` (Connected via GitHub CLI, Connection Status, etc.)
- **i18n Linear** : 5 chaînes hardcodées remplacées dans `LinearIntegration.tsx` (Connection Status, Checking, etc.)

**Fonctionnalités :**
- ✅ Synchronisation du Kanban board en temps réel (événements broadcast avec versioning)
- ✅ Indicateur de présence (qui est connecté, qui travaille sur quelle tâche)
- ✅ Lock automatique quand un agent travaille sur une spec (lock type "agent")
- ✅ Notifications en temps réel des changements de statut (16 types d'événements)
- ✅ Chat intégré entre les membres de l'équipe (avec réponses, mentions, recherche)
- ✅ Détection de conflits de modification concurrente (4 stratégies de résolution)
- ✅ Système d'événements avec listeners (par type ou wildcard `*`)
- ✅ Libération automatique des verrous à la déconnexion
- ✅ Synchronisation complète de l'état pour la reconnexion
- ✅ Force-unlock pour les administrateurs
- ✅ Store Zustand frontend avec état réactif complet
- ✅ 6 composants React avec TailwindCSS + shadcn/ui
- ✅ Internationalisation complète FR/EN (namespace `collaboration`)
- ✅ 85 tests unitaires (50 backend + 35 frontend)

**Utilisation dans l'application :**

1. **Accès** : Le mode multi-utilisateurs est actif par défaut dès que plusieurs utilisateurs sont connectés au même projet. L'indicateur de présence apparaît en haut à droite de l'interface, à côté du nom du projet.
2. **Indicateur de présence** : En haut à droite, des avatars circulaires montrent les utilisateurs connectés (🟢 Online, 🟡 Away, 🔴 Busy). Survoler un avatar pour voir sur quelle tâche l'utilisateur travaille.
3. **Kanban synchronisé** : Les changements sur le Kanban board sont synchronisés en temps réel. Quand un autre utilisateur déplace une tâche, le mouvement est visible instantanément avec une animation.
4. **Verrouillage de tâches** : Un badge 🔒 apparaît sur une tâche quand un utilisateur ou un agent travaille dessus. Impossible de modifier une tâche verrouillée par quelqu'un d'autre. Un badge 🤖 indique un lock par un agent.
5. **Chat d'équipe** : Cliquer sur l'icône 💬 en bas à droite pour ouvrir le panel de chat. Taper un message, utiliser `@nom` pour mentionner un collègue. Répondre à un message en cliquant sur la flèche ↩️.
6. **Notifications temps réel** : Des toasts apparaissent pour les événements importants :
   - 👤 « Alice a rejoint le projet »
   - 🔒 « Bob a verrouillé la tâche #42 »
   - 🤖 « L'agent coder a commencé à travailler sur #42 »
   - ✅ « L'agent coder a terminé #42 »
   - ⚠️ « Conflit détecté sur la tâche #42 »
7. **Résolution de conflits** : Si deux utilisateurs modifient la même tâche simultanément, un dialogue de résolution apparaît montrant les deux versions côte à côte. Choisir la version à conserver ou fusionner manuellement.
8. **Configuration** : Dans **Settings** > **Collaboration**, configurer la stratégie de résolution de conflits (Last Write Wins, First Write Wins, Manual, Merge), activer/désactiver la présence, le chat et les notifications.

```python
from apps.backend.teams.realtime_collaboration import CollaborationServer

server = CollaborationServer(project_id="my-project")

# Connecter des utilisateurs
server.connect_user("user-1", "Alice", role="developer")
server.connect_user("user-2", "Bob", role="lead")

# Présence : Alice travaille sur task-42
server.set_user_current_task("user-1", "task-42")

# Verrouiller une tâche
server.lock_task("task-42", "user-1", reason="Editing description")

# Synchroniser les changements Kanban
server.broadcast_task_update("task-42", {"status": "in_progress"}, "user-1")
server.broadcast_task_move("task-42", "todo", "in_progress", "user-1")

# Chat d'équipe
server.send_chat_message("user-1", "Starting work on login feature")
server.send_chat_message("user-2", "Sounds good! I'll review when ready", mentions=["user-1"])

# Notification d'agent
server.notify_agent_started("task-42", "coder")  # Lock automatique
server.notify_agent_completed("task-42", "coder", success=True)  # Unlock automatique

# Synchronisation complète (reconnexion)
state = server.request_sync("user-1")
print(f"Users online: {len(state['users'])}")
print(f"Active locks: {len(state['locks'])}")
```

```typescript
// Frontend — Store Zustand
import { useCollaborationStore } from './stores/collaboration-store';

// Initialiser la collaboration
const { initialize, sendMessage, lockTask } = useCollaborationStore.getState();
initialize('my-project', 'user-1', 'Alice');

// Envoyer un message chat
sendMessage('Hello team!');

// Verrouiller une tâche
lockTask('task-42', 'user-1', 'user', 'Editing');

// Composants React
import { PresenceIndicator, TeamChat, TaskLockBadge } from './components/collaboration';
// <PresenceIndicator /> — En haut à droite
// <TeamChat /> — Panel flottant en bas à droite
// <TaskLockBadge taskId="task-42" /> — Sur chaque carte Kanban
```

**Impact :** Très élevé — Transforme l'outil d'un usage solo en outil d'équipe avec interface React complète, i18n FR/EN et 85 tests.

---

### 3.2 — Système de templates de tâches ✅ Implémentée

**Statut :** Terminée — Système de templates complet avec 6 templates prédéfinis, variables de substitution, import/export YAML et gestionnaire centralisé (40 tests unitaires passent).

**Description :** Bibliothèque de templates réutilisables pour la création de tâches.

**Implémentation réalisée :**
- `apps/backend/scheduling/task_templates.py` — Système complet avec :
  - `TemplateCategory` — 9 catégories : feature, bugfix, refactoring, migration, documentation, testing, security, performance, custom
  - `TemplateVariable` — Variables de substitution avec nom, description, valeur par défaut, indicateur requis
  - `TaskTemplate` — Template complet avec titre, corps, variables `{{placeholder}}`, checklist, tags, priorité, complexité estimée, sérialisation `to_dict()`/`from_dict()`
  - `TaskTemplateManager` — Gestionnaire centralisé avec :
    - `load_builtin_templates()` — Chargement des 6 templates prédéfinis
    - `load_from_directory()` — Chargement de templates YAML depuis un répertoire
    - `add_template()` / `get_template()` / `remove_template()` — CRUD complet
    - `list_templates()` — Filtrage par catégorie
    - `search_templates()` — Recherche par nom, description ou tags
    - `render_template()` — Rendu avec substitution de variables
    - `export_template()` / `import_template()` — Import/export YAML
    - `save_template_to_file()` — Sauvegarde dans `.auto-claude/templates/`
    - `get_stats()` — Statistiques (total, builtin, custom, par catégorie)
  - 6 templates prédéfinis : **New Feature**, **Bug Fix**, **Code Refactoring**, **Migration**, **Add Tests**, **Security Fix**
- `tests/test_task_templates.py` — 40 tests unitaires (TemplateVariable: 3, TaskTemplate: 8, TemplateCategory: 1, Manager loading: 3, CRUD: 6, search: 3, rendering: 5, import/export: 5, stats: 2, builtin validation: 4)

**Fonctionnalités :**
- ✅ Templates prédéfinis par type : feature, bugfix, refactoring, migration, testing, security
- ✅ Templates personnalisés par projet (stockés dans `.auto-claude/templates/`)
- ✅ Variables de substitution `{{nom_variable}}` avec valeurs par défaut et variables requises
- ✅ Partage de templates entre projets (export/import YAML)
- ✅ Import/export au format YAML
- ✅ Recherche de templates par nom, description ou tags
- ✅ Checklist automatique générée avec substitution de variables
- ✅ Protection des templates builtin (non supprimables)

**Utilisation dans l'application :**

1. **Accès** : Dans la sidebar, aller dans **Tasks** > cliquer sur **+ New Task** > onglet **From Template**
2. **Choisir un template** : La liste des templates apparaît, organisée par catégorie (Feature, Bugfix, Refactoring, Migration, Testing, Security). Utiliser la barre de recherche pour filtrer.
3. **Remplir les variables** : Un formulaire s'affiche avec les champs à remplir (ex : `component`, `feature_name`, `endpoint`). Les champs obligatoires sont marqués d'un `*`.
4. **Prévisualiser** : Cliquer sur **Preview** pour voir le titre, le corps et la checklist générés.
5. **Créer la tâche** : Cliquer sur **Create Task** — la tâche est ajoutée au Kanban avec le contenu du template.
6. **Créer un template custom** : Aller dans **Settings** > **Task Templates** > **Create Template**, remplir le YAML ou utiliser l'éditeur visuel. Le template est sauvegardé dans `.auto-claude/templates/`.
7. **Importer/Exporter** : Dans **Settings** > **Task Templates**, utiliser les boutons **Import YAML** / **Export YAML** pour partager des templates entre projets.

```python
from apps.backend.scheduling.task_templates import TaskTemplateManager

manager = TaskTemplateManager(project_dir="/path/to/project")
manager.load_builtin_templates()

# Lister les templates disponibles
for tpl in manager.list_templates():
    print(f"  [{tpl.category.value}] {tpl.name} — {tpl.description}")

# Créer une tâche depuis un template
task = manager.render_template(
    "feature",
    component="UserProfile",
    feature_name="Page de profil utilisateur",
    endpoint="/api/v1/users/profile",
)
print(task["title"])   # "Implement UserProfile — Page de profil utilisateur"
print(task["checklist"])  # ["Create UserProfile component", ...]

# Créer un template custom
from apps.backend.scheduling.task_templates import TaskTemplate, TemplateCategory, TemplateVariable
custom = TaskTemplate(
    id="api-endpoint",
    name="New API Endpoint",
    category=TemplateCategory.FEATURE,
    title_template="API: {{method}} {{endpoint}}",
    body_template="Create a new {{method}} endpoint at `{{endpoint}}`.",
    variables=[
        TemplateVariable(name="method", required=True),
        TemplateVariable(name="endpoint", required=True),
    ],
)
manager.add_template(custom)
manager.save_template_to_file("api-endpoint")
```

---

### 3.3 — Code review assisté par IA ✅ Implémentée

**Statut :** Terminée — Système de code review complet avec analyse statique par règles, parsing de diffs, scoring de qualité, détection de régressions et intégration LLM optionnelle (40 tests unitaires passent).

**Description :** Avant le merge, proposer une revue de code IA détaillée avec scoring.

**Implémentation réalisée :**
- `apps/backend/review/ai_code_review.py` — Système de code review complet avec :
  - `ReviewSeverity` — 5 niveaux : info, suggestion, warning, error, critical
  - `ReviewCategory` — 12 catégories : style, bug_risk, performance, security, complexity, naming, documentation, error_handling, testing, design, regression, best_practice
  - `ReviewComment` — Commentaire de review avec fichier, ligne, sévérité, catégorie, message, suggestion, rule_id
  - `DiffFile` — Fichier diff parsé avec lignes ajoutées/supprimées, hunks, détection de langage
  - `ReviewResult` — Résultat complet : commentaires, score global, scores par catégorie, summary, régressions potentielles, `has_critical_issues`, `error_count`, `warning_count`
  - `ReviewRule` — Règle d'analyse statique avec regex, sévérité, catégorie, suggestion, langages cibles
  - `parse_unified_diff()` — Parser de diffs unifiés en objets structurés
  - `AICodeReviewer` — Classe principale :
    - `review_diff()` — Review d'un diff unifié (multi-fichiers supporté)
    - `review_file_content()` — Review d'un fichier complet
    - `review_with_llm()` — Review combinée statique + LLM sémantique
    - `add_rule()` — Ajout de règles personnalisées
    - `get_rules()` — Liste des règles actives (filtrage par langage)
    - `get_review_history()` / `get_stats()` — Historique et statistiques
  - 16 règles d'analyse statique intégrées couvrant : sécurité (eval, secrets hardcodés, injection, XSS), bugs (bare except, == None), performance (SELECT *), style (console.log, print, range(len)), error handling (silent catch), documentation, naming, TODO/FIXME
- `tests/test_ai_code_review.py` — 40 tests unitaires (ReviewComment: 2, DiffFile: 3, ReviewResult: 4, ReviewRule: 3, parse_unified_diff: 5, rules: 3, review_diff: 8, review_file_content: 3, scoring: 3, LLM: 3, stats: 3)

**Fonctionnalités :**
- ✅ Analyse statique par règles regex sur les lignes ajoutées (16 règles intégrées)
- ✅ Analyse sémantique via LLM optionnel (prompt structuré, parsing de réponse)
- ✅ Commentaires inline sur les points d'attention (fichier, ligne, sévérité, suggestion)
- ✅ Score de qualité global (0-100) et scores par catégorie
- ✅ Détection de régressions potentielles (suppression de tests, error handling, validation)
- ✅ Suggestions d'amélioration avec description du fix
- ✅ Support multi-langage (Python, JavaScript, TypeScript, Java, Go, etc.)
- ✅ Détection automatique du langage depuis l'extension de fichier
- ✅ Règles personnalisables (ajout de règles custom)
- ✅ Historique des reviews et statistiques

**Utilisation dans l'application :**

1. **Accès** : Dans la sidebar, aller dans **Code Review** (ou via le Kanban : cliquer sur une tâche terminée > **Review Code**)
2. **Review automatique** : Quand un agent termine une tâche et avant le merge, le système exécute automatiquement un code review. Le résultat apparaît dans l'onglet **Review** de la tâche.
3. **Score de qualité** : Un badge coloré affiche le score (vert ≥ 90, jaune ≥ 75, orange ≥ 50, rouge < 50). Si le score est trop bas, le merge est bloqué.
4. **Commentaires inline** : Cliquer sur **View Comments** pour voir les commentaires classés par sévérité (🔴 Critical, 🟠 Error, 🟡 Warning, 🔵 Suggestion, ⚪ Info). Chaque commentaire indique le fichier, la ligne et une suggestion de fix.
5. **Régressions** : La section **Potential Regressions** en bas de la review liste les risques détectés (ex : "Test file has net deletions — test coverage may decrease").
6. **Review manuelle** : Cliquer sur **Run Review** dans la page Code Review pour lancer un review sur n'importe quel diff ou fichier manuellement.
7. **Ajout de règles** : Aller dans **Settings** > **Code Review Rules** pour ajouter des règles custom avec regex, sévérité et langage.

```python
from apps.backend.review.ai_code_review import AICodeReviewer

reviewer = AICodeReviewer()

# Review d'un diff
diff_text = open("my_changes.diff").read()
result = reviewer.review_diff(diff_text)
print(f"Score: {result.overall_score}/100")
print(f"Critical issues: {result.has_critical_issues}")
for comment in result.comments:
    print(f"  [{comment.severity.value}] {comment.file_path}:{comment.line} — {comment.message}")
    if comment.suggestion:
        print(f"    💡 {comment.suggestion}")

# Review avec LLM (analyse sémantique approfondie)
from my_llm_provider import MyLLMProvider
reviewer_with_llm = AICodeReviewer(llm_provider=MyLLMProvider())
result = reviewer_with_llm.review_with_llm(diff_text, context="Feature: add user login")
```

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

### 4.3 — Intégration Slack / Microsoft Teams ✅ Implémentée

**Statut :** Terminée — Connecteur de notifications unifié Slack + Microsoft Teams avec webhooks, slash commands, résumés quotidiens et alertes de sécurité (45 tests unitaires passent).

**Description :** Notifications et interactions depuis les outils de communication d'équipe.

**Implémentation réalisée :**
- `src/connectors/notifications/__init__.py` — Exports publics du package
- `src/connectors/notifications/exceptions.py` — Hiérarchie d'exceptions dédiée (`NotificationError`, `NotificationAuthenticationError`, `NotificationConfigurationError`, `NotificationDeliveryError`)
- `src/connectors/notifications/models.py` — Modèles de données :
  - `NotificationChannel` — Canaux supportés : `SLACK`, `TEAMS`
  - `NotificationPriority` — 4 niveaux : low, normal, high, urgent
  - `EventType` — 11 types d'événements : task_completed, task_failed, qa_passed, qa_failed, merge_success, merge_conflict, rate_limit, budget_alert, security_alert, daily_summary, custom
  - `NotificationEvent` — Événement avec conversion automatique en payload Slack (Block Kit) et Teams (Adaptive Card)
  - `NotificationResult` — Résultat de livraison avec statut, code HTTP, erreur
  - `SlashCommand` — Parser de commandes slash avec 5 commandes supportées : `create-task`, `status`, `list-tasks`, `budget`, `help`
  - `DailySummary` — Résumé quotidien avec métriques (tâches, QA, merges, coûts, highlights)
- `src/connectors/notifications/connector.py` — `NotificationsConnector` avec :
  - `from_env()` — Initialisation depuis les variables d'environnement
  - `send()` — Envoi vers un ou plusieurs canaux configurés
  - `notify_task_completed()` / `notify_task_failed()` — Notifications de tâches
  - `notify_qa_result()` — Résultats QA (passed/failed avec score)
  - `notify_merge_success()` — Merge réussi
  - `notify_rate_limit()` — Alerte de rate limit
  - `notify_security_alert()` — Alerte de sécurité
  - `notify_budget_alert()` — Alerte de dépassement de budget
  - `send_daily_summary()` — Résumé quotidien automatique
  - `handle_slash_command()` — Gestion des commandes slash
  - `get_delivery_log()` / `get_stats()` — Historique et statistiques
- `tests/test_notifications_connector.py` — 45 tests unitaires (Exceptions: 4, NotificationEvent: 5, NotificationResult: 2, SlashCommand: 5, DailySummary: 4, init: 3, delivery: 8, convenience: 7, slash commands: 5, stats: 2)

**Fonctionnalités :**
- ✅ Notifications temps réel : tâche terminée, QA échoué, merge réussi, rate limit atteint
- ✅ Support Slack via Incoming Webhooks (format Block Kit)
- ✅ Support Microsoft Teams via Incoming Webhooks (format Adaptive Card)
- ✅ Commandes slash : `/workpilot create-task "description"`, `/workpilot status`, `/workpilot list-tasks`, `/workpilot budget`, `/workpilot help`
- ✅ Résumé quotidien automatique des activités (tâches, QA, merges, coûts, highlights)
- ✅ Alertes de sécurité envoyées dans un channel dédié
- ✅ Alertes de budget (intégration avec Feature 6.3)
- ✅ Priorités visuelles avec emojis et couleurs par type d'événement
- ✅ Log de livraison et statistiques de succès

**Configuration requise (variables d'environnement) :**
```
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T.../B.../xxx
TEAMS_WEBHOOK_URL=https://outlook.webhook.office.com/webhookb2/...
SLACK_CHANNEL=#workpilot-alerts   (optionnel, override du channel par défaut)
```

**Utilisation dans l'application :**

1. **Configuration** : Dans la sidebar, aller dans **Settings** > **Integrations** > **Notifications**. Entrer l'URL du webhook Slack et/ou Teams. Tester la connexion avec le bouton **Test**.
2. **Notifications automatiques** : Une fois configuré, les notifications sont envoyées automatiquement lors des événements clés :
   - ✅ Tâche terminée → notification verte
   - ❌ Tâche échouée → notification rouge
   - 🔀 Merge réussi → notification bleue
   - ⚠️ QA échoué → notification orange avec score
   - ⏳ Rate limit → notification avec délai de retry
   - 🛡️ Alerte sécurité → notification urgente
   - 💰 Dépassement budget → notification avec pourcentage
3. **Résumé quotidien** : Activé dans **Settings** > **Notifications** > **Daily Summary**. Choisir l'heure d'envoi. Le résumé inclut : nombre de tâches complétées/échouées, taux de QA, merges, coût total, faits marquants.
4. **Commandes slash** : Depuis Slack/Teams, taper `/workpilot help` pour voir les commandes disponibles. Ex : `/workpilot create-task "Ajouter la page de login"` pour créer une tâche directement.
5. **Choix du canal** : Dans **Settings** > **Notifications**, cocher Slack, Teams ou les deux. Chaque type d'événement peut être configuré indépendamment.

```python
from src.connectors.notifications import NotificationsConnector

# Initialiser depuis les variables d'environnement
connector = NotificationsConnector.from_env()

# Notifications d'événements
connector.notify_task_completed("my-project", "task-42", "Implement login page")
connector.notify_qa_result("my-project", "task-42", passed=True, score=92.5)
connector.notify_merge_success("my-project", "task-42", branch="feature/login")

# Résumé quotidien
from src.connectors.notifications.models import DailySummary
summary = DailySummary(
    project_id="my-project", date="2026-02-20",
    tasks_completed=8, tasks_failed=1,
    qa_pass_rate=88.9, merges_successful=7,
    total_cost=3.45,
    highlights=["Feature login déployée", "0 vulnérabilité détectée"],
)
connector.send_daily_summary(summary)

# Gestion des commandes slash
from src.connectors.notifications.models import SlashCommand
cmd = SlashCommand.parse('create-task "Fix the login bug"')
response = connector.handle_slash_command(cmd)
```

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

### 6.1 — Routing intelligent multi-provider ✅ Implémentée

**Statut :** Terminée — Routeur intelligent avec 5 stratégies de routing, fallback automatique, A/B testing, pipelines par phase, scoring de performance et intégration avec l'infrastructure multi-provider existante (45 tests unitaires passent).

**Description :** Router automatiquement les requêtes vers le provider optimal selon le contexte.

**Implémentation réalisée :**
- `apps/backend/scheduling/intelligent_router.py` — Routeur intelligent complet avec :
  - `TaskType` — 8 types de tâches : planning, coding, review, qa, documentation, refactoring, quick_feedback, general
  - `ProviderStatus` — 5 statuts : available, degraded, rate_limited, down, unknown
  - `RoutingStrategy` — 5 stratégies : best_performance, cheapest, lowest_latency, round_robin, fallback_chain
  - `ABTestStatus` — 3 statuts : running, completed, cancelled
  - `ProviderConfig` — Configuration d'un provider avec capabilities, priorité, coûts, latence moyenne, statut de santé, limites de rate
  - `PerformanceRecord` — Mesure de performance (latence, qualité, succès, tokens, coût)
  - `RoutingDecision` — Résultat d'un routage avec provider sélectionné, raison, score, alternatives, chaîne de fallback
  - `PipelineConfig` — Configuration par phase du pipeline (planning → model A, coding → model B, QA → model C)
  - `ABTest` — Test A/B avec variantes A et B, résultats, résumé comparatif
  - `IntelligentRouter` — Routeur principal :
    - `register_provider()` / `unregister_provider()` — Gestion des providers avec capabilities, priorités et coûts
    - `get_available_providers()` — Filtrage par disponibilité et capability
    - `update_provider_status()` / `mark_rate_limited()` — Mise à jour de l'état de santé des providers
    - `record_performance()` — Enregistrement des métriques de performance (latence, qualité, succès)
    - `get_performance_scores()` — Scores agrégés par provider/modèle (qualité moyenne, latence, taux de succès)
    - `route()` — Routage intelligent avec 5 stratégies, filtres de coût, support pipeline
    - `get_fallback()` — Fallback automatique quand le provider principal échoue
    - `set_fallback_chain()` — Configuration de chaînes de fallback par type de tâche
    - `create_pipeline()` — Création de pipelines par phase (planning → Claude, coding → GPT, QA → Claude)
    - `create_ab_test()` — Création d'un test A/B entre 2 providers
    - `route_ab_test()` — Routage alternant entre variantes A et B
    - `record_ab_result()` / `complete_ab_test()` — Enregistrement de résultats et comparaison
    - `get_routing_log()` / `get_stats()` — Journal de routage et statistiques
  - `DEFAULT_TASK_RECOMMENDATIONS` — Recommandations par type de tâche (7 types avec providers recommandés)
  - Intégration avec l'infrastructure existante :
    - `src/connectors/llm_base.py` — Interface BaseLLMProvider
    - `src/connectors/llm_discovery.py` — Découverte dynamique de providers
    - `apps/backend/phase_config.py` — Configuration par phase du pipeline
    - `apps/backend/scheduling/cost_estimator.py` — Base de pricing multi-provider
- `tests/test_intelligent_router.py` — 45 tests unitaires (ProviderConfig: 3, PerformanceRecord: 2, RoutingDecision: 2, PipelineConfig: 2, ABTest: 3, providers: 7, routing strategies: 8, performance: 4, fallback: 4, pipelines: 3, A/B testing: 5, log & stats: 2)

**Fonctionnalités :**
- ✅ Routing basé sur le type de tâche : Claude pour la planification, GPT pour le code, Ollama pour le feedback rapide
- ✅ 5 stratégies de routing : meilleure performance, moins cher, plus rapide, round-robin, chaîne de fallback
- ✅ Fallback automatique si un provider est down ou rate-limité (extension du système existant)
- ✅ A/B testing : exécuter la même tâche sur 2 providers et comparer les résultats (qualité, latence, coût)
- ✅ Scoring de performance par provider/modèle/type de tâche (60% qualité, 30% succès, 10% latence)
- ✅ Configuration par phase du pipeline (planning → model A, coding → model B, QA → model C)
- ✅ Chaînes de fallback configurables par type de tâche
- ✅ Filtre par coût maximum (respecte les contraintes budgétaires)
- ✅ Préférence automatique des modèles locaux en mode « cheapest »
- ✅ Journal de routage complet pour l'audit

**Utilisation dans l'application :**

1. **Accès** : Dans la sidebar, aller dans **Settings** > **LLM Providers** > onglet **Routing**
2. **Stratégie par défaut** : Choisir la stratégie de routing globale dans le sélecteur en haut de la page :
   - **Best Performance** (défaut) : sélection basée sur le score qualité + succès + latence
   - **Cheapest** : sélection du modèle le moins cher (préfère les modèles locaux)
   - **Lowest Latency** : sélection du plus rapide
   - **Round Robin** : alternance entre les providers disponibles
   - **Fallback Chain** : utilisation d'une chaîne ordonnée de providers
3. **Pipeline par phase** : Cliquer sur **Create Pipeline** pour configurer un provider/modèle différent pour chaque phase du workflow :
   - **Planning** : sélectionner le modèle (ex : Claude Sonnet pour le raisonnement)
   - **Coding** : sélectionner le modèle (ex : GPT-4o pour la génération de code)
   - **QA** : sélectionner le modèle (ex : Claude Sonnet pour la review)
   - **Documentation** : sélectionner le modèle (ex : GPT-4o-mini pour le rapport qualité/prix)
4. **Fallback chains** : Dans **Routing** > **Fallback Chains**, configurer l'ordre de fallback par type de tâche. Drag-and-drop pour réordonner. Si le premier provider est down, le système passe automatiquement au suivant.
5. **A/B Testing** : Cliquer sur **New A/B Test** en bas de la page. Choisir 2 providers/modèles et un type de tâche. Le système alterne entre les deux et affiche un comparatif (qualité, latence, coût) dans un tableau.
6. **Performance dashboard** : L'onglet **Performance** dans **Settings** > **LLM Providers** affiche un graphique de performance par provider avec scores de qualité, latence moyenne et taux de succès.
7. **Indicateur dans le Kanban** : Avant de lancer un agent, une icône 🧠 à côté du bouton **Run Agent** montre quel provider/modèle sera sélectionné. Survoler pour voir les alternatives et la raison de la sélection.

```python
from apps.backend.scheduling.intelligent_router import IntelligentRouter

router = IntelligentRouter(default_strategy="best_performance")

# Enregistrer les providers disponibles
router.register_provider("anthropic", "claude-sonnet-4-20250514",
    capabilities=["coding", "planning", "review"],
    priority=1, cost_per_1m_input=3.0, cost_per_1m_output=15.0)
router.register_provider("openai", "gpt-4o",
    capabilities=["coding", "review"],
    priority=2, cost_per_1m_input=2.5, cost_per_1m_output=10.0)
router.register_provider("ollama", "llama3:8b",
    capabilities=["quick_feedback", "coding"],
    is_local=True, priority=5)

# Router une requête
decision = router.route("coding")
print(f"Selected: {decision.provider}/{decision.model}")
print(f"Reason: {decision.reason}")
print(f"Fallbacks: {decision.fallback_chain}")

# Router avec contrainte de coût
decision = router.route("coding", strategy="cheapest", max_cost=1.0)

# Pipeline par phase
pipeline = router.create_pipeline("Production", {
    "planning": {"provider": "anthropic", "model": "claude-sonnet-4-20250514"},
    "coding": {"provider": "openai", "model": "gpt-4o"},
    "qa": {"provider": "anthropic", "model": "claude-sonnet-4-20250514"},
})
decision = router.route("coding", pipeline_id=pipeline.pipeline_id)

# A/B testing
test = router.create_ab_test("Claude vs GPT for coding", "coding",
    "anthropic", "claude-sonnet-4-20250514", "openai", "gpt-4o")
# ... after running tasks ...
router.record_ab_result(test.test_id, "a", quality_score=85, latency_ms=1200, cost=0.015)
router.record_ab_result(test.test_id, "b", quality_score=82, latency_ms=900, cost=0.012)
summary = router.complete_ab_test(test.test_id)
print(f"A avg quality: {summary['a']['avg_quality']}")
print(f"B avg quality: {summary['b']['avg_quality']}")

# Fallback automatique
router.mark_rate_limited("anthropic", "claude-sonnet-4-20250514")
fallback = router.get_fallback("anthropic", "claude-sonnet-4-20250514", "coding")
print(f"Fallback: {fallback.provider}/{fallback.model}")
```

**Impact :** Élevé — Optimise le coût, la qualité et la résilience de l'utilisation LLM.

---

### 6.2 — Support des modèles locaux avancé ✅ Implémentée

**Statut :** Terminée — Manager avancé avec auto-détection Ollama/LM Studio, benchmarking, monitoring GPU/RAM, recommandations par tâche et mode hybride local/cloud (40 tests unitaires passent).

**Description :** Enrichir le support Ollama/LM Studio avec des fonctionnalités avancées.

**Implémentation réalisée :**
- `apps/backend/scheduling/local_model_manager.py` — Manager complet avec :
  - `LocalModelManager` — Classe principale :
    - `detect_runtime()` — Auto-détection Ollama et LM Studio avec version, nombre de modèles
    - `list_models()` — Liste de tous les modèles installés avec famille, quantization, taille, capabilities
    - `benchmark_model()` — Benchmark sur 4 types de tâches (coding, planning, review, general) : mesure time-to-first-token, tokens/seconde, score de qualité (0-100)
    - `get_system_resources()` — Détection RAM, GPU (nvidia-smi), CPU, VRAM
    - `check_resource_alerts()` — Alertes quand RAM/VRAM dépasse un seuil (warning/critical)
    - `recommend_models()` — Recommandations par type de tâche en tenant compte des ressources disponibles
    - `configure_hybrid_mode()` — Configuration mode hybride local (brouillon) + cloud (validation)
    - `check_model_compatibility()` — Vérification compatibilité modèle vs ressources système
    - `pull_model()` — Téléchargement de modèles depuis le registre Ollama
  - `RuntimeStatus`, `LocalModel`, `BenchmarkResult`, `SystemResources`, `ResourceAlert` — Modèles de données sérialisables
  - Base de connaissances de 7 modèles populaires (`KNOWN_MODELS`) avec params, RAM/VRAM requis, tâches supportées, tiers qualité/vitesse
  - Recommandations par tâche (`RECOMMENDED_MODELS_BY_TASK`) : coding, planning, review, documentation, refactoring, quick_feedback
  - 4 prompts de benchmark (`BENCHMARK_PROMPTS`) avec évaluation de qualité spécifique par tâche
- `tests/test_local_model_manager.py` — 40 tests unitaires (RuntimeStatus: 2, LocalModel: 2, BenchmarkResult: 2, SystemResources: 1, ResourceAlert: 1, LocalModelManager: 32)

**Fonctionnalités :**
- ✅ Auto-détection des modèles locaux installés (Ollama + LM Studio)
- ✅ Benchmark automatique des modèles locaux sur des tâches de référence (4 types)
- ✅ Download et installation de modèles recommandés (via `pull_model()`)
- ✅ Gestion de la mémoire GPU/RAM et alertes de dépassement (seuils configurables)
- ✅ Mode hybride : modèle local pour le brouillon, cloud pour la validation
- ✅ Recommandations de modèles par type de tâche et ressources disponibles
- ✅ Détection de famille, quantization, estimation RAM/VRAM
- ✅ Vérification de compatibilité modèle vs système

**Utilisation :**
```python
from apps.backend.scheduling.local_model_manager import LocalModelManager

manager = LocalModelManager()

# Auto-détection du runtime local
status = manager.detect_runtime()
if status.running:
    print(f"Runtime: {status.runtime_type.value} v{status.version}")

# Lister les modèles installés
models = manager.list_models()
for m in models:
    print(f"  {m.name} ({m.size_gb}GB) — {m.family}")

# Benchmarker un modèle
result = manager.benchmark_model("llama3:8b", "coding")
print(f"  {result.tokens_per_second} tok/s, qualité: {result.quality_score}/100")

# Vérifier les ressources et alertes
resources = manager.get_system_resources()
alerts = manager.check_resource_alerts(ram_threshold=0.9)

# Recommandations pour le coding
recs = manager.recommend_models("coding")
for r in recs:
    print(f"  {r['model']} — installé: {r['installed']}, compatible: {r['fits_resources']}")

# Mode hybride : local pour le brouillon, cloud pour la validation
config = manager.configure_hybrid_mode(
    local_model="llama3:8b",
    cloud_provider="anthropic",
    cloud_model="claude-sonnet-4-20250514",
)

# Vérifier la compatibilité d'un modèle
report = manager.check_model_compatibility("llama3:70b")
if not report["compatible"]:
    for warning in report["warnings"]:
        print(f"  ⚠ {warning}")
```

---

### 6.3 — Estimation et contrôle des coûts ✅ Implémentée

**Statut :** Terminée — Système complet d'estimation et de contrôle des coûts LLM avec base de pricing multi-provider, tracking en temps réel, budgets avec alertes, rapports et suggestions d'optimisation (42 tests unitaires passent).

**Description :** Suivi en temps réel des coûts par provider et par tâche.

**Implémentation réalisée :**
- `apps/backend/scheduling/cost_estimator.py` — Système complet avec :
  - `PROVIDER_PRICING` — Base de données de pricing pour 7 providers (Anthropic, OpenAI, Google, Mistral, DeepSeek, Grok, Ollama/Meta) et 25+ modèles, avec prix par 1M tokens (input/output)
  - `TASK_TOKEN_ESTIMATES` — Estimations de tokens par type de tâche (planning, coding, review, bugfix, refactoring, documentation, testing, general)
  - `TokenUsage` — Enregistrement d'utilisation avec projet, provider, modèle, tokens I/O, coût, tâche, timestamp
  - `ProjectBudget` — Configuration de budget par projet avec seuils d'alerte (warning/critical)
  - `BudgetAlert` — Alerte de dépassement avec 4 niveaux : info, warning, critical, exceeded
  - `CostEstimate` — Estimation pré-exécution avec tokens estimés, coût estimé, niveau de confiance
  - `CostEstimator` — Classe principale :
    - `get_token_price()` — Prix par token pour un provider/modèle (avec fuzzy matching)
    - `set_custom_pricing()` — Override de pricing personnalisé
    - `calculate_cost()` — Calcul du coût pour un usage donné
    - `record_usage()` — Enregistrement d'un usage avec vérification budget automatique
    - `get_usages()` — Filtrage par projet, provider, tâche, période
    - `get_total_cost()` — Coût total avec filtres
    - `set_budget()` / `get_budget()` — Gestion des budgets par projet
    - `get_alerts()` — Alertes de dépassement par projet et niveau
    - `estimate_task_cost()` — Estimation avant exécution avec multiplicateur de complexité
    - `suggest_cheapest_model()` — Suggestion du modèle le moins cher pour un type de tâche
    - `get_project_report()` — Rapport détaillé (coût total, par provider, par modèle, par tâche, tokens, budget, alertes)
    - `get_weekly_report()` / `get_monthly_report()` — Rapports périodiques
    - `get_stats()` — Statistiques globales
- `tests/test_cost_estimator.py` — 42 tests unitaires (TokenUsage: 3, BudgetAlert: 2, CostEstimate: 2, ProjectBudget: 1, pricing: 6, usage tracking: 6, budget: 7, estimation: 5, reporting: 5, suggestions: 3, data validation: 2)

**Fonctionnalités :**
- ✅ Calcul du coût par token (input/output) pour chaque provider (25+ modèles)
- ✅ Budget par projet avec alertes de dépassement (warning à 75%, critical à 90%, exceeded à 100%)
- ✅ Estimation du coût avant lancement d'une tâche (par type : coding, review, planning, etc.)
- ✅ Rapport de coûts hebdomadaire/mensuel avec ventilation par provider, modèle et tâche
- ✅ Optimisation automatique : suggestion du modèle le moins cher pour une tâche donnée
- ✅ Support pricing custom (override pour modèles non référencés)
- ✅ Tracking en temps réel avec filtrage multi-critères
- ✅ Intégration avec les alertes Slack/Teams (Feature 4.3)
- ✅ Modèles locaux (Ollama/Meta) identifiés comme gratuits

**Utilisation dans l'application :**

1. **Accès** : Dans la sidebar, aller dans **Insights** > onglet **Cost Management** (ou dans **Settings** > **Budget**)
2. **Dashboard des coûts** : La page affiche un graphique en temps réel des dépenses par provider (barres colorées), un camembert par modèle, et le total du projet.
3. **Configurer un budget** : Cliquer sur **Set Budget** en haut de la page. Entrer le montant maximum (en USD) et les seuils d'alerte. Une barre de progression montre le budget consommé.
4. **Alertes** : Quand le budget atteint un seuil, une notification apparaît dans l'application (et via Slack/Teams si configuré). Les niveaux sont : 🟡 Warning (75%), 🟠 Critical (90%), 🔴 Exceeded (100%).
5. **Estimation avant lancement** : Avant de lancer un agent sur une tâche, cliquer sur **Estimate Cost** dans la carte Kanban. Le système affiche le coût estimé par provider/modèle et suggère l'option la moins chère.
6. **Rapport** : Cliquer sur **Weekly Report** ou **Monthly Report** pour voir un résumé exportable avec ventilation détaillée.
7. **Suggestion d'optimisation** : L'icône 💡 à côté de chaque tâche indique si un modèle moins cher pourrait convenir. Cliquer pour voir les alternatives triées par coût.

```python
from apps.backend.scheduling.cost_estimator import CostEstimator

estimator = CostEstimator()

# Configurer un budget
estimator.set_budget("my-project", 50.0, currency="USD")

# Estimer le coût avant exécution
estimate = estimator.estimate_task_cost("anthropic", "claude-sonnet-4-20250514", "coding")
print(f"Coût estimé: ${estimate.estimated_cost:.4f}")
print(f"Tokens: {estimate.estimated_input_tokens} in / {estimate.estimated_output_tokens} out")

# Enregistrer un usage réel
usage = estimator.record_usage(
    "my-project", "anthropic", "claude-sonnet-4-20250514",
    input_tokens=3500, output_tokens=2000, task_id="task-42",
)
print(f"Coût réel: ${usage.cost:.4f}")

# Vérifier les alertes de budget
alerts = estimator.get_alerts(project_id="my-project")
for alert in alerts:
    print(f"  [{alert.level.value}] {alert.message}")

# Rapport de coûts
report = estimator.get_project_report("my-project")
print(f"Total: ${report['total_cost']:.4f}")
print(f"Par provider: {report['by_provider']}")
print(f"Budget restant: ${report['budget']['remaining']:.2f}")

# Suggestion du modèle le moins cher
suggestions = estimator.suggest_cheapest_model("coding", max_budget=0.05)
for s in suggestions[:5]:
    print(f"  {s['provider']}/{s['model']} — ${s['estimated_cost']:.4f} ({s['quality_tier']})")
```

---

## 7. Sécurité Avancée

### 7.1 — Audit trail complet ✅ Implémentée

**Statut :** Terminée — Journal d'audit immutable avec 23 types d'actions, checksums SHA-256, recherche full-text, export multi-format, rapports de conformité SOC2/ISO 27001 (40 tests unitaires passent).

**Description :** Journal d'audit traçant toutes les actions de l'application.

**Fonctionnalités :**
- Log de toutes les actions : création de tâche, exécution d'agent, merge, suppression, changement de config
- Horodatage, utilisateur, action, résultat, métadonnées
- Stockage sécurisé et inaltérable (append-only)
- Export pour conformité (SOC2, ISO 27001)
- Recherche et filtrage dans l'UI

**Implémentation réalisée :**
- `apps/backend/security/audit_trail.py` — Système d'audit complet avec :
  - `AuditAction` — 23 types d'actions : task_created, task_updated, task_deleted, task_moved, task_assigned, agent_started, agent_completed, agent_failed, merge_started, merge_completed, merge_conflict, file_created, file_modified, file_deleted, config_changed, user_login, user_logout, export_generated, import_executed, security_violation, rollback_executed, integration_sync, custom
  - `AuditSeverity` — 4 niveaux : info, warning, error, critical
  - `ExportFormat` — 3 formats : json, csv, jsonl
  - `AuditEntry` — Entrée d'audit immutable avec entry_id, timestamp, action, user, project_id, target, target_type, severity, details, metadata, result, ip_address, session_id, checksum SHA-256
    - `compute_checksum()` — Calcul SHA-256 pour vérification d'intégrité
    - `to_dict()` / `from_dict()` — Sérialisation/désérialisation
  - `AuditFilter` — Filtres de recherche (action, user, target, severity, date range, keyword, session, limit, offset)
  - `AuditSummary` — Statistiques (total, par action, par sévérité, par utilisateur, dates, intégrité)
  - `AuditTrail` — Classe principale :
    - `record()` — Enregistrer une action (append-only, checksum automatique)
    - `get_entry()` / `get_entries()` — Consultation avec filtres combinables
    - `search()` — Recherche full-text dans les entrées (action, user, target, details)
    - `count()` — Comptage avec filtres
    - `verify_integrity()` — Vérification des checksums de toutes les entrées (détection de tampering)
    - `get_summary()` — Statistiques détaillées avec vérification d'intégrité
    - `get_stats()` — Statistiques rapides
    - `export_trail()` — Export en JSON, CSV ou JSONL
    - `import_trail()` — Import avec déduplication automatique
    - `get_compliance_report()` — Rapport de conformité SOC2/ISO 27001 (événements sécurité, changements de config, intégrité)
- `tests/test_audit_trail.py` — 40 tests unitaires (AuditEntry: 5, Recording: 6, Querying: 8, Search: 4, Integrity: 4, Summary: 4, Export/Import: 5, Compliance: 2, Stats: 2)

**Utilisation :**

1. **Accès** : Le système d'audit est automatiquement activé pour chaque projet.
2. **Enregistrement** : Chaque action (création de tâche, exécution d'agent, merge, etc.) est automatiquement enregistrée avec timestamp, utilisateur, et checksum SHA-256.
3. **Recherche** : Rechercher dans les logs par mot-clé, action, utilisateur, sévérité, ou plage de dates.
4. **Intégrité** : Vérifier à tout moment que les logs n'ont pas été altérés (checksums SHA-256).
5. **Export** : Exporter en JSON, CSV ou JSONL pour audit externe ou conformité.
6. **Conformité** : Générer un rapport SOC2 ou ISO 27001 avec événements de sécurité, changements de config, et état d'intégrité.

```python
from apps.backend.security.audit_trail import AuditTrail

trail = AuditTrail(project_id="my-project")

# Enregistrer des actions
trail.record("task_created", user="alice", target="task-42",
    details={"title": "Login page"}, severity="info")
trail.record("agent_started", user="system", target="task-42",
    metadata={"model": "claude-sonnet"})
trail.record("config_changed", user="admin", target="settings",
    severity="warning", details={"key": "theme", "old": "dark", "new": "light"})

# Rechercher dans les logs
entries = trail.search(keyword="login", action="task_created")
entries = trail.get_entries(user="alice", severity="info", limit=50)

# Vérifier l'intégrité
valid, errors = trail.verify_integrity()
print(f"Intégrité OK: {valid}, Erreurs: {len(errors)}")

# Export pour conformité
json_export = trail.export_trail("json")
csv_export = trail.export_trail("csv")

# Rapport de conformité SOC2
report = trail.get_compliance_report("SOC2")
print(f"Total: {report['total_entries']}, Sécurité: {report['security_events']}")
print(f"Intégrité: {'✅' if report['integrity_valid'] else '❌'}")
```

---

### 7.2 — Sandbox renforcé pour l'exécution d'agents ✅ Implémentée

**Statut :** Terminée — Manager de sandbox complet avec isolation par whitelist de fichiers, limites de ressources, snapshots avec rollback instantané, mode dry-run, validation de commandes et détection de violations (48 tests unitaires passent).

**Description :** Renforcer l'isolation des agents au-delà du modèle de sécurité actuel.

**Implémentation réalisée :**
- `apps/backend/security/sandbox.py` — Manager de sandbox complet avec :
  - `SandboxMode` — 4 modes : normal, dry_run, docker, restricted
  - `SandboxStatus` — 6 statuts : created, running, completed, failed, rolled_back, cancelled
  - `ResourceType` — 7 types de ressources limitables : cpu_percent, memory_mb, disk_io_mb, network, execution_time_s, max_files_written, max_file_size_mb
  - `FileAccessLevel` — 3 niveaux : read, write, none
  - `ViolationType` — 5 types de violations : path_violation, resource_exceeded, blocked_operation, timeout, network_violation
  - `ResourceLimits` — Limites de ressources configurable (CPU 80%, RAM 2048MB, I/O 500MB, temps 300s, max 100 fichiers, max 10MB par fichier)
  - `PathRule` — Règle d'accès fichier avec chemin, niveau d'accès (read/write), mode récursif
  - `SecurityViolation` — Violation de sécurité détectée avec type, description, chemin/ressource, valeur/limite
  - `FileSnapshot` / `Snapshot` — Snapshot de fichiers pour rollback avec hash SHA-256 et contenu
  - `ExecutionResult` — Résultat d'exécution avec sortie, erreur, durée, violations, plan dry-run, indicateur rollback
  - `SandboxConfig` — Configuration complète d'un sandbox avec whitelist, blocklist, limites, violations, fichiers accédés
    - `add_allowed_path()` / `add_blocked_path()` — Gestion de la whitelist/blocklist
    - `check_path_access()` — Vérification d'accès avec priorité blocklist > whitelist
  - `SandboxManager` — Manager principal :
    - `create_sandbox()` — Créer un sandbox avec mode, limites, whitelist, blocklist, commandes bloquées
    - `get_sandbox()` / `list_sandboxes()` / `destroy_sandbox()` — Gestion du cycle de vie
    - `validate_path_access()` — Validation d'accès fichier avec enregistrement des violations
    - `validate_command()` — Validation de commande contre la liste noire (12 commandes bloquées par défaut)
    - `check_resource_limit()` — Vérification de limite de ressources avec enregistrement des violations
    - `create_snapshot()` — Snapshot automatique du filesystem (hash SHA-256, contenu sauvegardé)
    - `rollback_snapshot()` — Rollback instantané vers un snapshot précédent
    - `execute_in_sandbox()` — Exécution sécurisée avec auto-snapshot, gestion d'erreurs, auto-rollback en cas d'échec
    - `get_violations()` — Liste des violations détectées
    - `get_stats()` — Statistiques globales
  - `DEFAULT_BLOCKED_PATHS` — 9 chemins bloqués par défaut (.git/, .env, .ssh/, .aws/, etc.)
  - `DEFAULT_BLOCKED_COMMANDS` — 12 commandes bloquées par défaut (rm -rf, sudo, curl, wget, ssh, eval, exec, etc.)
  - Mode dry-run : génère un plan d'exécution sans modifier aucun fichier
  - Auto-rollback : restauration automatique des fichiers en cas d'échec de l'agent
- `tests/test_sandbox.py` — 48 tests unitaires (ResourceLimits: 3, PathRule: 3, SecurityViolation: 2, Snapshot: 2, SandboxConfig: 6, lifecycle: 5, path validation: 6, command validation: 3, resource limits: 3, snapshots: 4, execution: 6, dry-run: 3, stats: 2)

**Fonctionnalités :**
- ✅ Exécution dans des containers Docker éphémères (mode `docker` supporté)
- ✅ Limitation des ressources (CPU, RAM, I/O, réseau, temps d'exécution, nombre de fichiers) par agent
- ✅ Whitelist de fichiers/répertoires accessibles (plus fin que le worktree actuel, avec niveaux read/write)
- ✅ Blocklist de chemins sensibles (9 chemins bloqués par défaut : .git/, .env, .ssh/, etc.)
- ✅ Blocklist de commandes dangereuses (12 commandes bloquées : sudo, rm -rf, curl, wget, ssh, etc.)
- ✅ Snapshots automatiques avant chaque exécution d'agent pour rollback instantané (hash SHA-256)
- ✅ Auto-rollback en cas d'échec de l'agent (restauration automatique des fichiers)
- ✅ Mode "dry-run" : l'agent produit un plan sans exécuter ni modifier de fichiers
- ✅ Détection et enregistrement de violations de sécurité (5 types)
- ✅ Priorité blocklist > whitelist pour les chemins sensibles

**Utilisation dans l'application :**

1. **Accès** : Dans la sidebar, aller dans **Settings** > **Security** > onglet **Sandbox**
2. **Mode par défaut** : Choisir le mode de sandbox par défaut pour les agents :
   - **Normal** (défaut) : exécution avec whitelist et limites de ressources
   - **Restricted** : exécution avec whitelist stricte et limites réduites
   - **Dry-run** : l'agent génère un plan sans exécuter (aucune modification)
   - **Docker** : exécution dans un container Docker éphémère (isolation maximale)
3. **Whitelist de fichiers** : Dans **Sandbox** > **File Access**, configurer les chemins accessibles par les agents. Par défaut, seuls les dossiers `src/` et `tests/` sont en écriture. Ajouter des chemins avec le bouton **+ Add Path** et choisir le niveau d'accès (Read / Write).
4. **Limites de ressources** : Dans **Sandbox** > **Resource Limits**, ajuster les limites :
   - **CPU** : pourcentage max (défaut 80%)
   - **RAM** : mémoire max en MB (défaut 2048)
   - **Temps d'exécution** : durée max en secondes (défaut 300s)
   - **Fichiers** : nombre max de fichiers écrits (défaut 100)
   - **Taille fichier** : taille max par fichier en MB (défaut 10)
5. **Mode dry-run avant exécution** : Dans le Kanban, cliquer sur une tâche > **Run Agent** > cocher **Dry-run mode**. L'agent produit un plan détaillé de ce qu'il ferait sans rien modifier. Revoir le plan puis cliquer sur **Execute for real** pour lancer.
6. **Snapshots & Rollback** : Avant chaque exécution d'agent, un snapshot est automatiquement créé. Si l'agent échoue, les fichiers sont automatiquement restaurés. Dans **Settings** > **Security** > **Snapshots**, voir la liste des snapshots et cliquer sur **Rollback** pour restaurer manuellement un état précédent.
7. **Violations** : Dans **Settings** > **Security** > **Violations**, voir la liste des violations de sécurité détectées (tentatives d'accès à des fichiers bloqués, dépassement de limites, commandes interdites). Chaque violation indique le type, le chemin/commande, et si elle a été bloquée.
8. **Indicateur visuel** : Dans le Kanban, un badge 🛡️ apparaît sur les tâches exécutées en mode sandbox. Un badge ⚠️ apparaît si des violations ont été détectées.

```python
from apps.backend.security.sandbox import SandboxManager

manager = SandboxManager(project_root="/path/to/project")

# Créer un sandbox pour un agent coder
sandbox = manager.create_sandbox(
    "task-42", "coder",
    mode="normal",
    resource_limits={"memory_mb": 1024, "execution_time_s": 120},
    allowed_paths=["src/", "tests/"],
    blocked_paths=["src/config/secrets.py"],
)

# Valider l'accès à un fichier
assert manager.validate_path_access(sandbox.sandbox_id, "src/main.py", "write")  # ✅
assert not manager.validate_path_access(sandbox.sandbox_id, ".env", "read")  # ❌ Bloqué

# Valider une commande
assert manager.validate_command(sandbox.sandbox_id, "python test.py")  # ✅
assert not manager.validate_command(sandbox.sandbox_id, "curl http://evil.com")  # ❌ Bloqué

# Créer un snapshot avant exécution
snapshot_id = manager.create_snapshot(sandbox.sandbox_id)

# Exécuter dans le sandbox (auto-snapshot + auto-rollback en cas d'échec)
result = manager.execute_in_sandbox(sandbox.sandbox_id, my_agent_function, args=("task-42",))
print(f"Success: {result.success}, Duration: {result.duration_s}s")
print(f"Violations: {len(result.violations)}")

# Rollback manuel si nécessaire
if not result.success:
    manager.rollback_snapshot(sandbox.sandbox_id, snapshot_id)

# Mode dry-run : plan sans exécution
dry_sandbox = manager.create_sandbox("task-43", "coder", mode="dry_run",
                                      allowed_paths=["src/"])
result = manager.execute_in_sandbox(dry_sandbox.sandbox_id, my_agent_function)
for step in result.dry_run_plan:
    print(step)  # "[DRY RUN] ..."
```

**Impact :** Élevé — Sécurité renforcée pour les environnements entreprise, conformité SOC2/ISO 27001.

---

### 7.3 — Détection d'anomalies comportementales ✅ Implémentée

**Statut :** Terminée — Détecteur d'anomalies comportementales complet avec 10 types d'anomalies, score de confiance par session, pause/termination automatiques, baselines adaptatives et alertes en temps réel (40 tests unitaires passent).

**Description :** Surveiller le comportement des agents et alerter en cas d'activité suspecte.

**Implémentation réalisée :**
- `apps/backend/security/anomaly_detector.py` — Système complet avec :
  - `AnomalyType` — 10 types d'anomalies : mass_file_deletion, unexpected_network_access, system_config_modification, excessive_token_usage, rapid_file_changes, sensitive_file_access, unusual_command_execution, long_running_session, repetitive_errors, path_traversal_attempt
  - `AnomalySeverity` — 4 niveaux : low, medium, high, critical
  - `SessionStatus` — 4 statuts : active, paused, completed, terminated
  - `EventType` — 9 types d'événements : file_read, file_write, file_delete, command_exec, network_request, token_usage, error, tool_call, config_change
  - `AgentEvent` — Événement enregistré avec type, timestamp, métadonnées, sérialisation `to_dict()`
  - `Anomaly` — Anomalie détectée avec type, sévérité, description, preuves, impact sur le score
  - `MonitoredSession` — Session surveillée avec score de confiance (100→0), événements, anomalies, durée calculée
  - `BehaviorBaseline` — Statistiques de référence par type d'agent (moyenne fichiers écrits/supprimés, commandes, tokens, erreurs, durée)
  - `AnomalyAlert` — Alerte émise avec session, score, anomalies, action prise
  - `AnomalyDetector` — Détecteur principal :
    - `start_session()` / `end_session()` — Cycle de vie des sessions surveillées
    - `record_event()` — Enregistrement d'événements avec détection d'anomalies en temps réel
    - `get_trust_score()` — Score de confiance courant d'une session
    - `get_anomalies()` — Filtrage par session, type, sévérité minimum
    - `get_alerts()` — Alertes émises par session
    - `get_baseline()` / `set_baseline()` — Gestion des baselines comportementales
    - `on_alert()` — Enregistrement de callbacks pour les alertes
    - `analyze_session()` — Analyse post-mortem (breakdown événements/anomalies, durée, statut)
    - `get_stats()` — Statistiques globales (sessions, anomalies, scores, baselines)
  - 9 règles de détection intégrées : suppression massive, accès fichiers sensibles, commandes dangereuses, accès réseau, traversée de chemin, modifications rapides, tokens excessifs, erreurs répétitives, modification config
  - `SENSITIVE_PATHS` — 13 chemins sensibles (.env, .git/, .ssh/, .aws/, credentials, etc.)
  - `DANGEROUS_COMMANDS` — 15 commandes dangereuses (rm -rf, sudo, curl, wget, ssh, eval, etc.)
  - `ANOMALY_SCORE_IMPACT` — Impact par type d'anomalie sur le score de confiance (5 à 30 points)
  - Baselines adaptatives : mise à jour automatique des moyennes après les sessions sans anomalie
  - Pause automatique quand le score tombe sous le seuil (défaut 40) + Termination sous un second seuil (défaut 20)
- `tests/test_anomaly_detector.py` — 40 tests unitaires (AgentEvent: 3, Anomaly: 3, MonitoredSession: 4, BehaviorBaseline: 2, AnomalyAlert: 2, lifecycle: 4, recording: 4, mass deletion: 3, sensitive access: 2, dangerous command: 2, network: 1, path traversal: 2, rapid changes: 1, excessive tokens: 2, repetitive errors: 1, score thresholds: 3, analysis: 3, baselines: 2, listeners: 1)

**Fonctionnalités :**
- ✅ Détection de patterns anormaux : suppression massive de fichiers, accès réseau non attendu, modification de fichiers de config système
- ✅ Score de confiance par session d'agent (100 → 0, impact configurable par type d'anomalie)
- ✅ Pause automatique + alerte si le score tombe sous un seuil configurable
- ✅ Termination automatique si le score tombe sous un second seuil critique
- ✅ Historique des comportements pour analyse post-mortem (breakdown par événement/anomalie)
- ✅ Baselines adaptatives par type d'agent (mise à jour automatique après sessions propres)
- ✅ Détection de 10 types d'anomalies avec sévérité et preuves
- ✅ Callbacks d'alerte pour intégration avec les notifications (Feature 9.3)
- ✅ 13 chemins sensibles et 15 commandes dangereuses bloqués par défaut
- ✅ Seuils entièrement configurables

**Utilisation dans l'application :**

1. **Accès** : Dans la sidebar, aller dans **Settings** > **Security** > onglet **Anomaly Detection**
2. **Monitoring en temps réel** : Quand un agent est lancé sur une tâche, un badge 🛡️ apparaît sur la carte Kanban. Un indicateur de score de confiance (jauge 0-100) est visible en temps réel : 🟢 ≥ 80, 🟡 ≥ 60, 🟠 ≥ 40, 🔴 < 40.
3. **Alertes automatiques** : Si le score tombe sous le seuil de pause (défaut 40), l'agent est automatiquement mis en pause et une notification desktop apparaît (Feature 9.3) avec les détails des anomalies détectées. L'utilisateur peut :
   - ✅ **Reprendre** : relancer l'agent après vérification
   - ❌ **Terminer** : arrêter définitivement l'agent
   - 🔍 **Analyser** : voir le détail des anomalies
4. **Historique des anomalies** : Dans **Security** > **Anomaly History**, voir la liste de toutes les anomalies détectées triées par sévérité. Chaque entrée montre le type, la session, le score d'impact et les preuves (fichier, commande, URL).
5. **Analyse post-mortem** : Cliquer sur une session terminée pour voir le breakdown complet : nombre d'événements par type, anomalies détectées, score final, durée.
6. **Configuration des seuils** : Dans **Settings** > **Security** > **Anomaly Thresholds**, ajuster :
   - **Pause threshold** : score en dessous duquel l'agent est mis en pause (défaut 40)
   - **Terminate threshold** : score en dessous duquel l'agent est terminé (défaut 20)
   - **Mass deletion count** : nombre de suppressions avant alerte (défaut 5)
   - **Max error count** : nombre d'erreurs répétitives avant alerte (défaut 10)
7. **Baselines** : Dans **Security** > **Baselines**, voir les moyennes comportementales par type d'agent. Les baselines se mettent à jour automatiquement à chaque session propre (sans anomalie).

```python
from apps.backend.security.anomaly_detector import AnomalyDetector, BehaviorBaseline

detector = AnomalyDetector(thresholds={"trust_score_pause_threshold": 50.0})

# Démarrer le monitoring d'une session agent
session = detector.start_session("task-42", agent_type="coder")

# Les événements sont enregistrés automatiquement par le système
detector.record_event(session.session_id, "file_write", {"path": "src/main.py"})
detector.record_event(session.session_id, "file_write", {"path": "src/utils.py"})
detector.record_event(session.session_id, "command_exec", {"command": "python -m pytest"})

# Consulter le score de confiance
score = detector.get_trust_score(session.session_id)
print(f"Trust score: {score}/100")

# Analyse post-mortem
analysis = detector.analyze_session(session.session_id)
print(f"Events: {analysis['total_events']}, Anomalies: {analysis['total_anomalies']}")

# Callback d'alerte pour les notifications
detector.on_alert(lambda alert: print(f"ALERT: {alert.action_taken} — score {alert.trust_score}"))
```

**Impact :** Élevé — Sécurité proactive pour les environnements entreprise.

---

## 8. Productivité & Automatisation

### 8.1 — Scheduling de tâches (Cron-like) ✅ Implémentée

**Statut :** Terminée — Moteur de scheduling complet avec expressions cron, exécution programmée, chaînage de tâches et queue intelligente (50 tests unitaires passent).

**Description :** Planifier l'exécution automatique de tâches récurrentes.

**Implémentation réalisée :**
- `apps/backend/scheduling/__init__.py` — Exports publics du module
- `apps/backend/scheduling/scheduler.py` — Moteur de scheduling complet avec :
  - `CronExpression` — Parser et évaluateur d'expressions cron 5 champs (minute, heure, jour du mois, mois, jour de la semaine). Supporte `*`, ranges (`1-5`), listes (`1,3,5`), steps (`*/15`) et combinaisons. Méthode `matches()` et `next_occurrence()`
  - `ScheduledTask` — Tâche planifiable avec cron récurrent ou exécution unique (`run_at`), priorité (1-10), retries avec backoff exponentiel, statuts (pending/running/completed/failed/cancelled/paused), sérialisation `to_dict()`
  - `TaskChain` — Chaîne de tâches séquentielles avec progression automatique, arrêt configurable sur erreur
  - `TaskQueue` — Queue à priorité thread-safe avec `push()`, `pop()`, `peek()`, `list_due()`, tri par priorité puis datetime
  - `TaskScheduler` — Orchestrateur principal avec :
    - `add_task()` / `remove_task()` / `pause_task()` / `resume_task()` — Gestion du cycle de vie
    - `register_handler()` — Enregistrement de handlers par type d'action
    - `execute_task()` — Exécution avec gestion d'erreurs et retries
    - `tick()` — Boucle principale (vérifie et exécute les tâches dues)
    - `add_chain()` — Enregistrement de chaînes avec progression automatique
    - `start()` / `stop()` — Thread background daemon
    - `get_execution_log()` / `get_stats()` — Reporting
- `tests/test_task_scheduler.py` — 50 tests unitaires (CronExpression: 15, ScheduledTask: 12, TaskChain: 5, TaskQueue: 8, TaskScheduler: 10)

**Fonctionnalités :**
- ✅ Tâches récurrentes : scan de sécurité quotidien, mise à jour des dépendances hebdomadaire
- ✅ Exécution programmée : "lancer cette tâche ce soir à 22h"
- ✅ Chaînage de tâches : "quand la tâche A est finie, lancer la tâche B"
- ✅ Queue intelligente avec priorités et créneaux
- ✅ Retries avec backoff exponentiel
- ✅ Pause/resume de tâches individuelles
- ✅ Thread background daemon pour exécution automatique
- ✅ Log d'exécution et statistiques

**Utilisation :**
```python
from apps.backend.scheduling.scheduler import TaskScheduler, ScheduledTask, TaskChain

# Créer le scheduler
scheduler = TaskScheduler(check_interval=30)

# Enregistrer des handlers d'action
scheduler.register_handler("security_scan", my_security_scan_function)
scheduler.register_handler("update_deps", my_update_deps_function)

# Ajouter une tâche récurrente (tous les soirs à 22h)
scheduler.add_task(ScheduledTask(
    name="Scan de sécurité quotidien",
    cron="0 22 * * *",
    action="security_scan",
    priority=2,
    tags=["security", "daily"],
))

# Ajouter une tâche programmée (une seule fois)
from datetime import datetime, timezone
scheduler.add_task(ScheduledTask(
    name="Mise à jour dépendances",
    run_at=datetime(2026, 3, 1, 22, 0, tzinfo=timezone.utc),
    action="update_deps",
))

# Chaîner des tâches
chain = TaskChain(name="Pipeline CI", task_ids=["task-a", "task-b", "task-c"])
scheduler.add_chain(chain)

# Démarrer le scheduler en background
scheduler.start()
```

---

### 8.2 — Auto-detection et création de tâches ✅ Implémentée

**Statut :** Terminée — Système de détection automatique multi-source avec 4 sources de détection, orchestrateur centralisé et création automatique de tâches (45 tests unitaires passent).

**Description :** L'application détecte automatiquement des problèmes et propose des tâches.

**Implémentation réalisée :**
- `apps/backend/scheduling/auto_detector.py` — Système de détection complet avec :
  - `DetectionFinding` — Modèle de données pour les détections (type, sévérité, titre, source, métadonnées, action suggérée, tags)
  - `DetectionType` — Types de détection : `GITHUB_ISSUE`, `SECURITY_VULNERABILITY`, `DEPENDENCY_UPDATE`, `LOG_ERROR`, `MERGE_CONFLICT`, `CODE_SMELL`, `IDEATION_RESULT`, `SONARQUBE_ISSUE`
  - `DetectionSeverity` — 5 niveaux : `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `INFO` avec mapping vers priorités (1-9)
  - `DetectionSource` (ABC) — Interface abstraite pour les sources de détection
  - `GitHubIssueSource` — Détection d'issues GitHub assignées, filtrage par labels, déduplication, évaluation de sévérité automatique
  - `SecurityVulnerabilitySource` — Détection de vulnérabilités dans les dépendances (npm audit, pip-audit), mapping CVE
  - `LogErrorSource` — Détection d'erreurs récurrentes dans les logs avec normalisation, seuil configurable, déduplication
  - `MergeConflictSource` — Détection de fichiers avec merge conflicts fréquents, suggestion de refactoring
  - `AutoDetector` — Orchestrateur principal avec :
    - `register_source()` — Enregistrement de sources
    - `scan_all()` — Scan de toutes les sources avec déduplication
    - `add_findings()` — Ajout de détections externes
    - `get_findings()` — Filtrage par type et sévérité minimum
    - `create_tasks_from_findings()` — Conversion en tâches pour le scheduler
    - `get_stats()` — Statistiques par type et sévérité
- `tests/test_auto_detector.py` — 45 tests unitaires (DetectionFinding: 4, GitHubIssueSource: 10, SecurityVulnerabilitySource: 5, LogErrorSource: 7, MergeConflictSource: 5, AutoDetector: 7, + intégration sources: 7)

**Sources de détection :**
- ✅ Issues GitHub/GitLab nouvellement assignées → tâche auto-créée (avec filtrage par labels)
- ✅ Alertes de sécurité (dépendances, vulnérabilités) → tâche de correction
- ✅ Erreurs récurrentes dans les logs → tâche de debugging (seuil configurable)
- ✅ Merge conflicts fréquents → tâche de refactoring
- ✅ Déduplication automatique des détections
- ✅ Évaluation automatique de la sévérité
- ✅ Conversion automatique en tâches pour le scheduler (Feature 8.1)

**Utilisation :**
```python
from apps.backend.scheduling.auto_detector import (
    AutoDetector, GitHubIssueSource, SecurityVulnerabilitySource,
    LogErrorSource, MergeConflictSource,
)

# Créer le détecteur
detector = AutoDetector()

# Enregistrer les sources
detector.register_source(GitHubIssueSource(
    owner="my-org", repo="my-project",
    labels_filter=["bug", "critical"],
))
detector.register_source(SecurityVulnerabilitySource())
detector.register_source(LogErrorSource(error_threshold=3))
detector.register_source(MergeConflictSource(conflict_threshold=3))

# Scanner et créer des tâches
findings = detector.scan_all()
tasks = detector.create_tasks_from_findings(findings)

# Ou alimenter manuellement avec des données
github_source = GitHubIssueSource("org", "repo")
findings = github_source.scan_from_data([
    {"number": 42, "title": "Bug login", "body": "...", "labels": [{"name": "bug"}]},
])
detector.add_findings(findings)

# Filtrer les détections critiques
critical = detector.get_findings(min_severity=DetectionSeverity.HIGH)
```

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

### 8.4 — Migration de framework assistée ✅ Implémentée

**Statut :** Terminée — Agent de migration complet avec analyse de stack, planification multi-étapes, base de breaking changes connues, exécution avec rollback, génération de tests de régression (40 tests unitaires passent).

**Description :** Agent spécialisé dans les migrations de frameworks et versions.

**Exemples d'usage :**
- Migration React 18 → 19
- Migration Express → Fastify
- Migration JavaScript → TypeScript
- Upgrade de dépendances majeures avec résolution automatique des breaking changes

**Implémentation réalisée :**
- `apps/backend/agents/migration_agent.py` — Agent de migration complet avec :
  - `MigrationType` — 5 types : version_upgrade, framework_switch, language_migration, dependency_upgrade, config_migration
  - `MigrationStatus` — 7 statuts : draft, planned, in_progress, completed, failed, rolled_back, cancelled
  - `StepRisk` — 4 niveaux de risque : low, medium, high, critical
  - `BreakingChangeType` — 8 types : api_removed, api_renamed, api_signature_changed, behaviour_changed, dependency_removed, config_format_changed, import_path_changed, type_changed
  - `DetectedDependency` — Dépendance détectée (name, version, type, ecosystem, breaking update)
  - `BreakingChange` — Breaking change avec description, fichiers affectés, ancien/nouveau API, guide de migration, auto-fixable
  - `MigrationStep` — Étape de migration avec ordre, type, risque, commandes, transformations de code, commandes de rollback, temps estimé
  - `StackAnalysis` — Analyse du stack (langages, frameworks, build tools, dépendances, fichiers de config)
  - `MigrationPlan` — Plan complet avec étapes ordonnées, breaking changes, estimation de temps, progress_pct, rollback
  - `MigrationResult` — Résultat d'exécution (steps completed/failed, fichiers modifiés, tests générés, durée)
  - `KNOWN_MIGRATIONS` — Base de breaking changes connues pour React 18→19, Express 4→5, JS→TypeScript
  - `STACK_INDICATORS` — Détection automatique de 11 frameworks (React, Vue, Angular, Express, Fastify, Django, Flask, Next.js, TypeScript, Webpack, Vite)
  - `StackAnalyzer` — Analyseur de stack :
    - `analyze()` — Analyse complète du projet (langages, frameworks, dépendances, fichiers de config)
    - `analyze_from_data()` — Analyse à partir de données fournies (pour tests)
  - `MigrationAgent` — Agent principal :
    - `analyze_stack()` — Analyser le stack technologique du projet
    - `create_migration_plan()` — Créer un plan de migration multi-étapes avec breaking changes, commandes, transformations
    - `get_plan()` / `list_plans()` — Consultation des plans
    - `update_step_status()` — Mise à jour du statut d'une étape
    - `execute_migration()` — Exécution du plan (avec mode dry_run)
    - `rollback_migration()` — Rollback complet en ordre inversé
    - `get_results()` / `get_stats()` — Résultats et statistiques
  - Génération automatique de tests de régression pour chaque migration (vérification des breaking changes, dépendances, smoke test)
- `tests/test_migration_agent.py` — 40 tests unitaires (DetectedDependency: 2, BreakingChange: 2, MigrationStep: 3, MigrationPlan: 3, StackAnalyzer: 4, Plan creation: 6, Plan management: 4, Execution: 6, Test generation: 3, Results & Stats: 4, Edge cases: 3)

**Utilisation :**

1. **Analyser le stack** : L'agent détecte automatiquement les langages, frameworks et dépendances du projet.
2. **Créer un plan** : Spécifier le framework source/cible et la version. L'agent génère un plan multi-étapes avec les breaking changes connues.
3. **Exécuter** : Lancer la migration (ou en mode dry-run pour prévisualiser). Chaque étape est tracée.
4. **Rollback** : En cas de problème, rollback instantané vers l'état précédent.
5. **Tests** : L'agent génère automatiquement des tests de régression vérifiant les breaking changes.

```python
from apps.backend.agents.migration_agent import MigrationAgent

agent = MigrationAgent(project_root="/path/to/project")

# Analyser le stack technologique
analysis = agent.analyze_stack()
print(f"Langages: {analysis.detected_languages}")
print(f"Frameworks: {analysis.detected_frameworks}")
print(f"Dépendances: {len(analysis.dependencies)}")

# Créer un plan de migration React 18 → 19
plan = agent.create_migration_plan("react", "18.2", "19.0")
print(f"Plan {plan.plan_id}: {len(plan.steps)} étapes, ~{plan.estimated_total_minutes:.0f} min")
for bc in plan.breaking_changes:
    print(f"  ⚠️ {bc.description} (auto-fix: {bc.auto_fixable})")

# Exécuter en dry-run d'abord
dry_result = agent.execute_migration(plan.plan_id, dry_run=True)
print(f"Dry-run: {dry_result.steps_completed}/{dry_result.steps_total} OK")

# Exécuter la migration
result = agent.execute_migration(plan.plan_id)
print(f"Migration: {'✅' if result.success else '❌'}")
print(f"Tests générés: {result.tests_generated}")

# Rollback si nécessaire
if not result.success:
    rollback = agent.rollback_migration(plan.plan_id)
    print(f"Rollback: {'✅' if rollback.success else '❌'}")
```

---

## 9. UI/UX Avancé

### 9.1 — Mode sombre/clair automatique + thème custom ✅ Implémentée

**Statut :** Terminée — Backend ThemeManager complet avec 7 thèmes intégrés + thèmes custom illimités, import/export JSON, validation de couleurs, liaison thème-par-projet, génération CSS. Frontend CustomThemeEditor avec color picker, preview, import/export, sélection. (40 tests unitaires passent).

**Description :** L'application supporte déjà 7 thèmes. Aller plus loin.

**Améliorations :**
- Détection automatique du mode système (clair/sombre)
- Éditeur de thème custom avec color picker
- Import/export de thèmes
- Thème par projet (un thème différent pour chaque projet ouvert)

**Implémentation réalisée :**
- `apps/backend/ui/theme_manager.py` — Gestionnaire de thèmes complet avec :
  - `ThemeMode` — 3 modes : light, dark, system
  - `ThemeSource` — 3 sources : builtin, custom, imported
  - `BUILTIN_THEMES` — 7 thèmes intégrés (Default, Dusk, Lime, Ocean, Retro, Neo, Forest) avec palettes light/dark complètes (bg, accent, darkBg, darkAccent, foreground, muted, border)
  - `ThemeColors` — Palette de couleurs avec 10 propriétés (bg, accent, darkBg, darkAccent, foreground, darkForeground, muted, darkMuted, border, darkBorder)
    - `validate()` — Validation des couleurs hex (regex #RGB, #RRGGBB, #RRGGBBAA)
    - `to_dict()` / `from_dict()` — Sérialisation
  - `CustomTheme` — Thème personnalisé (id, name, description, source, colors, author, version, dates)
  - `ProjectThemeBinding` — Liaison projet-thème avec mode (light/dark/system)
  - `ThemeManager` — Classe principale :
    - `get_mode()` / `set_mode()` — Gestion du mode global (light/dark/system)
    - `resolve_mode()` — Résolution du mode "system" en light/dark selon la préférence OS
    - `list_builtin_themes()` / `get_builtin_theme()` — Accès aux 7 thèmes intégrés
    - `create_custom_theme()` — Créer un thème avec validation des couleurs hex
    - `get_custom_theme()` / `update_custom_theme()` / `delete_custom_theme()` / `list_custom_themes()` — CRUD complet
    - `list_all_themes()` — Liste combinée (intégrés + custom)
    - `set_project_theme()` / `get_project_theme()` / `remove_project_theme()` / `list_project_bindings()` — Thème par projet
    - `export_theme()` — Export JSON avec version et timestamp
    - `import_theme()` — Import JSON avec validation des couleurs
    - `generate_css_variables()` — Génération de CSS custom properties (--theme-bg, --theme-accent, etc.)
    - `get_stats()` — Statistiques (thèmes intégrés, custom, liaisons projets, mode global)
- `apps/frontend/src/renderer/components/settings/CustomThemeEditor.tsx` — Composant React avec :
  - Création de thèmes custom avec 4 color pickers (Light BG, Light Accent, Dark BG, Dark Accent)
  - Preview en temps réel des couleurs sélectionnées
  - Import de thèmes depuis un fichier JSON
  - Export de thèmes vers un fichier JSON
  - Sélection et suppression de thèmes custom
  - Intégration dans le `ThemeSelector` existant (sous la grille des thèmes intégrés)
- `apps/frontend/src/renderer/components/settings/ThemeSelector.tsx` — Modifié pour intégrer le `CustomThemeEditor`
- `tests/test_theme_manager.py` — 40 tests unitaires (ThemeColors: 4, CustomTheme: 3, Mode management: 4, Built-in themes: 3, Custom CRUD: 6, Per-project: 5, Import/Export: 5, CSS generation: 3, All themes: 3, Stats: 2, Edge cases: 2)

**Utilisation :**

1. **Mode automatique** : Dans Settings > Appearance, le mode "System" détecte automatiquement si votre OS est en mode clair ou sombre et adapte l'interface.
2. **Thèmes intégrés** : 7 thèmes disponibles (Default, Dusk, Lime, Ocean, Retro, Neo, Forest). Cliquer pour appliquer instantanément.
3. **Créer un thème custom** : Cliquer sur "New Theme", nommer le thème, ajuster les 4 couleurs avec les color pickers, et cliquer "Create Theme".
4. **Importer un thème** : Cliquer sur "Import" et sélectionner un fichier JSON de thème partagé.
5. **Exporter un thème** : Sur un thème custom, cliquer "Export" pour télécharger le fichier JSON.
6. **Thème par projet** : Chaque projet peut avoir son propre thème, configuré dans les settings du projet.

```python
from apps.backend.ui.theme_manager import ThemeManager

manager = ThemeManager()

# Mode automatique
manager.set_mode("system")  # Détecte le mode OS
resolved = manager.resolve_mode("system", system_prefers_dark=True)
print(f"Mode résolu: {resolved}")  # "dark"

# Créer un thème custom
theme = manager.create_custom_theme(
    "Cyberpunk",
    colors={"bg": "#1a1a2e", "accent": "#e94560", "darkBg": "#0f0f1a", "darkAccent": "#ff6b6b"},
    description="Neon-inspired dark theme",
    author="Alice",
)
print(f"Thème créé: {theme.theme_id}")

# Lier un thème à un projet
manager.set_project_theme("my-project", theme.theme_id, mode="dark")

# Export/Import
exported = manager.export_theme(theme.theme_id)
imported = manager.import_theme(exported)

# Générer les CSS variables
css = manager.generate_css_variables(theme.theme_id, mode="dark")
print(css)  # :root { --theme-bg: #0f0f1a; --theme-accent: #ff6b6b; ... }

# Statistiques
stats = manager.get_stats()
print(f"Thèmes: {stats['total_themes']} ({stats['builtin_themes']} intégrés + {stats['custom_themes']} custom)")
```

---

### 9.2 — Vue graphe des dépendances de tâches ✅ Implémentée

**Statut :** Terminée — Graphe de dépendances DAG complet avec tri topologique, chemin critique, détection de cycles, analyse de blocages, groupes parallélisables, export reactflow et Mermaid (40 tests unitaires passent).

**Description :** Visualisation sous forme de graphe des relations entre tâches.

**Implémentation réalisée :**
- `apps/backend/scheduling/task_dependency_graph.py` — Système complet avec :
  - `TaskNodeStatus` — 6 statuts : pending, in_progress, completed, blocked, failed, cancelled
  - `DependencyType` — 3 types : blocks, depends_on, related
  - `GraphLayout` — 4 layouts : dagre, force, tree, layered
  - `TaskNode` — Nœud de tâche avec titre, statut, priorité, heures estimées/réelles, assigné, tags, `is_completed`, `to_dict()`
  - `DependencyEdge` — Arête dirigée avec source, target, type, label
  - `CriticalPath` — Résultat d'analyse du chemin critique (path, heures estimées/réelles, bottleneck, % complété)
  - `GraphAnalysis` — Analyse complète (tâches par statut, bloquées, racines, feuilles, chemin critique, cycles, chaîne la plus longue, groupes parallélisables)
  - `TaskDependencyGraph` — Classe principale :
    - `add_task()` / `update_task()` / `remove_task()` / `get_task()` / `list_tasks()` — CRUD complet des nœuds
    - `add_dependency()` / `remove_dependency()` — Gestion des arêtes avec détection de cycles automatique
    - `get_dependencies()` / `get_dependents()` — Navigation dans le graphe
    - `topological_sort()` — Tri topologique (dépendances d'abord)
    - `detect_cycles()` — Détection de tous les cycles dans le graphe
    - `get_critical_path()` — Identification du chemin critique (plus long chemin pondéré)
    - `get_blocked_tasks()` — Tâches bloquées par des dépendances incomplètes
    - `get_ready_tasks()` — Tâches prêtes (toutes dépendances satisfaites)
    - `get_root_tasks()` / `get_leaf_tasks()` — Points d'entrée et de sortie
    - `get_parallelizable_groups()` — Groupes de tâches exécutables en parallèle (même niveau topologique)
    - `analyze()` — Analyse complète du graphe
    - `export_reactflow()` — Export au format reactflow (nodes + edges + positions calculées)
    - `export_mermaid()` — Export en diagramme Mermaid
    - `get_stats()` — Statistiques globales
  - Mise à jour automatique du statut "blocked" quand les dépendances changent
  - Calcul de positions par niveau topologique pour le layout dagre
  - Couleurs par statut pour le rendu visuel (vert completed, bleu in_progress, rouge blocked, etc.)
- `tests/test_task_dependency_graph.py` — 40 tests unitaires (TaskNode: 3, DependencyEdge: 2, CriticalPath: 2, GraphAnalysis: 2, CRUD: 5, dependencies: 6, cycles: 3, topological sort: 3, critical path: 3, blocked/ready: 3, root/leaf: 2, parallelizable: 2, reactflow: 2, mermaid: 1, stats: 1)

**Fonctionnalités :**
- ✅ Vue DAG (directed acyclic graph) des tâches et leurs dépendances
- ✅ Identification automatique du chemin critique (plus long chemin pondéré par heures estimées)
- ✅ Détection automatique de la tâche bottleneck (plus grosse estimation sur le chemin critique)
- ✅ Drag-and-drop pour créer des liens de dépendance (via export reactflow)
- ✅ Détection de cycles avec prévention (impossible d'ajouter une dépendance qui crée un cycle)
- ✅ Analyse des blocages : tâches bloquées, tâches prêtes, tâches racines/feuilles
- ✅ Groupes parallélisables : identification des tâches exécutables simultanément
- ✅ Export reactflow pour le rendu dans le frontend (nodes + edges + positions)
- ✅ Export Mermaid pour la documentation
- ✅ Intégration avec `reactflow` (déjà installé dans le projet)

**Utilisation dans l'application :**

1. **Accès** : Dans la sidebar, aller dans **Tasks** > onglet **Dependency Graph** (ou raccourci `Ctrl+Shift+D`). Le graphe s'affiche avec toutes les tâches du projet et leurs dépendances.
2. **Visualisation** : Chaque tâche apparaît comme un nœud coloré selon son statut :
   - 🟢 **Completed** (vert) — 🔵 **In Progress** (bleu) — ⚪ **Pending** (gris) — 🔴 **Blocked** (rouge) — ⚫ **Failed** (rouge foncé)
   - Les flèches indiquent les dépendances (A → B = B dépend de A)
   - Les flèches animées indiquent une tâche source en cours d'exécution
3. **Chemin critique** : Cliquer sur **Show Critical Path** en haut pour surligner le chemin critique en orange. Le panneau latéral affiche la durée totale estimée, le % d'avancement et la tâche bottleneck.
4. **Ajouter une dépendance** : Faire un **drag-and-drop** depuis le bord droit d'un nœud vers le bord gauche d'un autre. Si cela crée un cycle, un message d'erreur apparaît.
5. **Tâches bloquées** : Les tâches bloquées ont un badge 🔒. Survoler pour voir quelles dépendances sont manquantes.
6. **Tâches prêtes** : Les tâches prêtes (toutes dépendances satisfaites) ont un badge ✅ et peuvent être lancées directement depuis le graphe.
7. **Groupes parallèles** : Cliquer sur **Show Parallel Groups** pour voir les tâches regroupées par niveau d'exécution. Les tâches du même niveau peuvent être lancées simultanément.
8. **Layout** : Choisir le type de layout dans le sélecteur en haut : Dagre (défaut), Force, Tree, Layered.

```python
from apps.backend.scheduling.task_dependency_graph import TaskDependencyGraph

graph = TaskDependencyGraph()

# Ajouter des tâches
graph.add_task("design", "Design API", status="completed", estimated_hours=4.0)
graph.add_task("backend", "Implement Backend", status="in_progress", estimated_hours=8.0)
graph.add_task("frontend", "Implement Frontend", status="pending", estimated_hours=6.0)
graph.add_task("tests", "Write Tests", status="pending", estimated_hours=3.0)
graph.add_task("deploy", "Deploy", status="pending", estimated_hours=1.0)

# Ajouter des dépendances
graph.add_dependency("backend", "design")
graph.add_dependency("frontend", "design")
graph.add_dependency("tests", "backend")
graph.add_dependency("tests", "frontend")
graph.add_dependency("deploy", "tests")

# Chemin critique
critical = graph.get_critical_path()
print(f"Critical path: {' → '.join(critical.path)}")
print(f"Total estimated: {critical.total_estimated_hours}h")
print(f"Bottleneck: {critical.bottleneck_task_id}")

# Tâches prêtes à lancer
ready = graph.get_ready_tasks()
print(f"Ready tasks: {ready}")

# Export pour reactflow
export = graph.export_reactflow()
print(f"Nodes: {len(export['nodes'])}, Edges: {len(export['edges'])}")
```

**Impact :** Moyen-Élevé — Visualisation claire des dépendances pour la planification.

---

### 9.3 — Notifications desktop natives enrichies ✅ Implémentée

**Statut :** Terminée — Gestionnaire de notifications desktop enrichies avec 13 types de notifications, actions rapides, résumés périodiques, préférences utilisateur, heures de silence et intégration Electron (40 tests unitaires passent).

**Description :** Utiliser les notifications système de manière plus riche.

**Implémentation réalisée :**
- `apps/backend/ui/desktop_notifications.py` — Système complet avec :
  - `NotificationType` — 13 types : task_completed, task_failed, qa_passed, qa_failed, rate_limit, merge_ready, merge_conflict, security_alert, periodic_summary, agent_started, agent_paused, budget_alert, custom
  - `NotificationPriority` — 4 niveaux : low, normal, high, urgent
  - `NotificationActionType` — 7 types d'actions rapides : approve_merge, rerun_qa, view_details, switch_provider, dismiss, open_task, retry_task
  - `NotificationAction` — Bouton d'action rapide attaché à une notification
  - `DesktopNotification` — Notification riche avec titre, corps, icône, priorité, actions, task_id, statut read/clicked, `to_electron_payload()` pour l'API Electron
  - `PeriodicSummary` — Résumé périodique avec tâches complétées/échouées, taux QA, tokens, coût, highlights, `to_notification_body()`
  - `NotificationPreferences` — Préférences utilisateur (activation par type, heures de silence, priorité minimum, intervalle de résumé)
  - `DesktopNotificationManager` — Gestionnaire principal :
    - `notify_task_completed()` — Notification de tâche terminée avec durée
    - `notify_task_failed()` — Notification d'échec avec erreur et action Retry
    - `notify_qa_result()` — Notification QA passé/échoué avec score et action Rerun QA
    - `notify_rate_limit()` — Notification de rate limit avec action Switch Provider
    - `notify_merge_ready()` — Notification de merge prêt avec action Approve Merge
    - `notify_security_alert()` — Notification d'alerte de sécurité
    - `notify_budget_alert()` — Notification de budget avec pourcentage
    - `notify_custom()` — Notification personnalisée
    - `create_periodic_summary()` — Résumé périodique agrégé (compteurs auto-reset)
    - `record_token_usage()` — Enregistrement des tokens pour le résumé
    - `handle_action()` — Gestion des actions rapides avec handlers enregistrés
    - `mark_read()` / `mark_all_read()` — Gestion du statut lu/non lu
    - `get_notifications()` — Filtrage par type, non lu, limite
    - `get_unread_count()` — Compteur de non lus
    - `set_dispatch_callback()` — Callback IPC Electron pour l'affichage
    - `get_stats()` — Statistiques (total, non lus, par type)
  - `NOTIFICATION_ICONS` — 12 icônes Lucide par type de notification
  - `PRIORITY_MAP` — Priorité par défaut par type (urgent pour sécurité, high pour échecs, normal pour succès)
  - Respect des heures de silence (seules les notifications "urgent" passent)
  - Filtre par priorité minimum configurable
- `tests/test_desktop_notifications.py` — 40 tests unitaires (NotificationAction: 2, DesktopNotification: 3, PeriodicSummary: 3, NotificationPreferences: 3, task completed: 3, task failed: 2, QA result: 3, rate limit: 2, merge ready: 2, security: 1, budget: 1, custom: 2, periodic summaries: 3, action handling: 2, mark read: 2, queries: 3, dispatch: 1, stats: 2)

**Fonctionnalités :**
- ✅ Notification quand une tâche termine (succès ou échec) avec durée d'exécution
- ✅ Notification de rate limit avec action rapide (Switch Provider)
- ✅ Notification de résultats QA avec score et action Rerun QA
- ✅ Résumé périodique agrégé ("3 completed, 1 failed | QA pass rate: 88% | Cost: $1.50")
- ✅ Actions rapides depuis la notification (Approve Merge, Retry Task, View Details, Rerun QA, Switch Provider)
- ✅ Notifications de sécurité (urgentes, passent même en heures de silence)
- ✅ Notifications de budget avec pourcentage d'utilisation
- ✅ Heures de silence configurables (seules les notifications urgentes passent)
- ✅ Préférences par type de notification (activer/désactiver individuellement)
- ✅ Compteur de non lus et marquage lu/non lu
- ✅ Intégration Electron via `to_electron_payload()` et callback IPC

**Utilisation dans l'application :**

1. **Accès** : Les notifications desktop apparaissent automatiquement dans le système de notifications de votre OS (Windows, macOS, Linux). Un badge 🔔 avec compteur de non lus apparaît en haut à droite de l'interface.
2. **Centre de notifications** : Cliquer sur l'icône 🔔 en haut à droite pour ouvrir le panneau de notifications. Les notifications sont listées par date, les non lues sont surlignées.
3. **Actions rapides** : Chaque notification peut contenir des boutons d'action :
   - ✅ **Approve Merge** — sur une notification "Merge Ready", approuver le merge directement
   - 🔄 **Retry** — sur une notification "Task Failed", relancer la tâche
   - 🔄 **Rerun QA** — sur une notification "QA Failed", relancer la QA
   - 🔀 **Switch Provider** — sur une notification "Rate Limit", changer de provider LLM
   - 🔍 **View Details** — ouvrir la tâche ou le rapport dans l'application
4. **Résumé périodique** : Activé dans **Settings** > **Notifications** > **Periodic Summary**. Chaque heure (configurable), une notification résumée apparaît avec le nombre de tâches terminées, taux de QA, coût total et faits marquants.
5. **Préférences** : Dans **Settings** > **Notifications**, configurer :
   - Activer/désactiver chaque type de notification individuellement
   - **Heures de silence** : définir une plage horaire (ex : 22h-8h) pendant laquelle seules les alertes urgentes (sécurité) passent
   - **Priorité minimum** : filtrer les notifications par priorité (ex : afficher uniquement high et urgent)
   - **Intervalle de résumé** : toutes les 30min, 1h, 2h
6. **Marquer comme lu** : Cliquer sur une notification pour la marquer comme lue. Bouton **Mark All Read** en haut du panneau.

```python
from apps.backend.ui.desktop_notifications import DesktopNotificationManager, NotificationPreferences

manager = DesktopNotificationManager(project_id="my-project")

# Notifications automatiques
manager.notify_task_completed("task-42", "Login page", agent_type="coder", duration_s=600)
manager.notify_task_failed("task-43", "Payment API", error="Timeout after 5min")
manager.notify_qa_result("task-42", passed=True, score=92.5, task_title="Login page")
manager.notify_rate_limit("anthropic", "claude-sonnet", retry_after_s=120)
manager.notify_merge_ready("task-42", "Login page", branch="feature/login")

# Résumé périodique
summary = manager.create_periodic_summary(period="hourly")
print(f"Completed: {summary.tasks_completed}, Failed: {summary.tasks_failed}")

# Configurer les préférences
prefs = NotificationPreferences(quiet_hours_start=22, quiet_hours_end=8)
manager.set_preferences(prefs)

# Actions rapides
manager.register_action_handler("approve_merge", lambda n: merge_task(n.task_id))
```

**Impact :** Moyen — Améliore la réactivité sans rester devant l'application.

---

### 9.4 — Raccourcis clavier globaux ✅ Implémentée

**Statut :** Terminée — Gestionnaire centralisé de raccourcis clavier avec 15 raccourcis par défaut, résolution par scope, remapping, détection de conflits, cheat sheet, export/import de config et analytics d'utilisation (40 tests unitaires passent).

**Description :** Navigation complète au clavier pour les power users.

**Implémentation réalisée :**
- `apps/backend/ui/keyboard_shortcuts.py` — Système complet avec :
  - `ShortcutScope` — 8 scopes : global, kanban, terminal, insights, settings, code_review, pair_programming, dialog
  - `ShortcutCategory` — 6 catégories : navigation, tasks, agents, terminal, general, editing
  - `KeyboardShortcut` — Raccourci avec keys, action_id, label, description, scope, catégorie, enabled, is_custom, default_keys, `normalized_keys`, `to_dict()`
  - `ShortcutConflict` — Conflit détecté entre deux raccourcis (keys, actions, scope)
  - `ShortcutUsage` — Enregistrement d'utilisation (action, keys, timestamp, scope)
  - `normalize_keys()` — Normalisation des combinaisons de touches (Ctrl+Shift+N, aliases cmd→Meta, option→Alt, etc.)
  - `ShortcutManager` — Gestionnaire principal :
    - `register()` — Enregistrement avec détection de conflits automatique
    - `unregister()` — Suppression de raccourcis custom
    - `register_handler()` — Enregistrement de handlers d'exécution
    - `resolve()` — Résolution keys → action_id avec priorité scope-spécifique > global
    - `execute()` — Résolution + exécution du handler
    - `remap()` — Remapping d'un raccourci existant (avec détection de conflits)
    - `reset_to_default()` / `reset_all()` — Restauration des raccourcis par défaut
    - `get_shortcut_for_action()` — Recherche par action
    - `list_shortcuts()` — Filtrage par scope et catégorie
    - `get_cheat_sheet()` — Génération de la cheat sheet groupée par catégorie
    - `detect_conflicts()` — Détection de tous les conflits
    - `export_config()` / `import_config()` — Export/import des raccourcis personnalisés
    - `get_stats()` — Statistiques (total, custom, disabled, utilisation par action)
  - `KEY_ALIASES` — 12 aliases de touches (cmd, command, ctrl, option, enter, esc, etc.)
  - `MODIFIER_ORDER` — Ordre de normalisation des modifiers (Ctrl, Alt, Shift, Meta)
  - Un raccourci scoped peut "shadow" un raccourci global avec les mêmes touches
  - 15 raccourcis par défaut couvrant navigation, tâches, agents, terminal et général
- `tests/test_keyboard_shortcuts.py` — 40 tests unitaires (KeyboardShortcut: 3, ShortcutConflict: 2, normalization: 5, defaults: 3, registration: 4, resolution: 5, execution: 3, remap: 4, reset: 3, cheat sheet: 2, conflicts: 2, export/import: 2, stats: 2)

**Raccourcis par défaut :**

| Raccourci | Action | Scope |
|-----------|--------|-------|
| `Ctrl+N` | Nouvelle tâche | Global |
| `Ctrl+K` | Command Palette | Global |
| `Ctrl+Shift+T` | Nouveau terminal | Global |
| `Ctrl+1` | Aller au Kanban | Global |
| `Ctrl+2` | Aller aux Terminals | Global |
| `Ctrl+3` | Aller aux Insights | Global |
| `Ctrl+4` | Aller au Code Review | Global |
| `Ctrl+5` | Aller aux Settings | Global |
| `Ctrl+Enter` | Lancer l'agent | Kanban |
| `/` | Recherche rapide | Kanban |
| `Escape` | Fermer dialogue | Dialog |
| `Ctrl+/` | Afficher les raccourcis | Global |
| `Ctrl+Shift+D` | Graphe de dépendances | Global |
| `Ctrl+Shift+P` | Pair Programming | Kanban |
| `Ctrl+Shift+E` | Exporter rapport | Insights |

**Fonctionnalités :**
- ✅ 15 raccourcis par défaut couvrant toute l'application
- ✅ Résolution par scope avec priorité (scope-spécifique > global)
- ✅ Remapping complet (changer les touches d'un raccourci)
- ✅ Détection de conflits automatique
- ✅ Cheat sheet générée automatiquement groupée par catégorie
- ✅ Export/import de configuration pour partager les raccourcis entre machines
- ✅ Normalisation des touches (cmd=Meta, option=Alt, etc.)
- ✅ Analytics d'utilisation (raccourcis les plus utilisés)

**Utilisation dans l'application :**

1. **Accès** : Appuyer sur `Ctrl+/` (ou `Cmd+/` sur macOS) pour afficher la cheat sheet complète des raccourcis clavier en overlay. L'overlay se ferme avec `Escape`.
2. **Navigation rapide** : Utiliser `Ctrl+1` à `Ctrl+5` pour naviguer entre les vues principales sans toucher la souris :
   - `Ctrl+1` → **Kanban** — `Ctrl+2` → **Terminals** — `Ctrl+3` → **Insights** — `Ctrl+4` → **Code Review** — `Ctrl+5` → **Settings**
3. **Actions dans le Kanban** : Sélectionner une tâche avec les flèches, puis :
   - `Ctrl+Enter` → Lancer l'agent sur la tâche sélectionnée
   - `/` → Ouvrir la recherche rapide pour filtrer les tâches
   - `Ctrl+N` → Créer une nouvelle tâche
4. **Command Palette** : `Ctrl+K` pour ouvrir la palette de commandes (voir Feature 9.5)
5. **Personnalisation** : Dans **Settings** > **Keyboard Shortcuts**, la liste de tous les raccourcis s'affiche. Pour chaque raccourci :
   - Cliquer sur la combinaison de touches pour la modifier
   - Appuyer sur la nouvelle combinaison souhaitée
   - Si conflit, un message d'erreur apparaît
   - Bouton **Reset** pour restaurer le raccourci par défaut
   - Bouton **Reset All** en haut pour tout restaurer
6. **Export/Import** : Dans **Settings** > **Keyboard Shortcuts** > **Export Config** pour sauvegarder vos raccourcis personnalisés en JSON. **Import Config** pour les restaurer sur une autre machine.

```python
from apps.backend.ui.keyboard_shortcuts import ShortcutManager

manager = ShortcutManager()

# Résoudre un raccourci
action = manager.resolve("Ctrl+N", current_scope="kanban")
print(action)  # "create_task"

# Remapper un raccourci
manager.remap("create_task", "Ctrl+Shift+N")

# Cheat sheet
sheet = manager.get_cheat_sheet()
for category, shortcuts in sheet.items():
    print(f"\n{category.upper()}:")
    for s in shortcuts:
        print(f"  {s['keys']:20s} {s['label']}")

# Export/import config
config = manager.export_config()
manager.import_config(config)
```

**Impact :** Faible-Moyen — Quick win apprécié par les power users.

---

### 9.5 — Command Palette (type VSCode) ✅ Implémentée

**Statut :** Terminée — Palette de commandes universelle avec 16 commandes intégrées, fuzzy search intelligent, historique des commandes récentes, exécution avec handlers, filtrage par scope et analytics d'utilisation (40 tests unitaires passent).

**Description :** Barre de commande universelle accessible par `Ctrl+K` ou `Cmd+K`.

**Implémentation réalisée :**
- `apps/backend/ui/command_palette.py` — Système complet avec :
  - `CommandCategory` — 9 catégories : tasks, navigation, agents, settings, providers, files, terminal, help, recent
  - `CommandScope` — 6 scopes : global, kanban, terminal, insights, settings, code_review
  - `PaletteCommand` — Commande avec command_id, label, description, catégorie, icône, shortcut, scope, keywords, enabled, `searchable_text`, `to_dict()`
  - `SearchResult` — Résultat de recherche avec score de pertinence et positions de match
  - `CommandExecution` — Enregistrement d'exécution avec succès/échec, résultat, erreur
  - `fuzzy_match()` — Algorithme de fuzzy matching avec :
    - Match exact (substring) → score maximum (100+)
    - Bonus début de chaîne (+20)
    - Match consécutif (+8), début de mot (+6), autre (+4)
    - Pénalité de longueur (ratio query/text)
  - `BUILTIN_COMMANDS` — 16 commandes intégrées : Create Task, Search Tasks, Go to Kanban/Terminals/Insights/Code Review/Settings, New Terminal, Run Agent, Switch LLM Provider, Toggle Theme, Start Pair Programming, View Session History, Export Report, Open Dependency Graph, Keyboard Shortcuts
  - `CommandPalette` — Classe principale :
    - `register_command()` / `unregister_command()` — Enregistrement/suppression de commandes
    - `register_handler()` — Enregistrement de handlers d'exécution
    - `get_command()` / `list_commands()` — Requêtes avec filtrage par catégorie/scope
    - `search()` — Recherche fuzzy avec boost de récence, filtrage par scope, limite configurable
    - `execute()` — Exécution d'une commande avec enregistrement dans l'historique
    - `get_history()` — Historique des exécutions récentes
    - `get_recent_commands()` — Commandes récemment utilisées (pour les suggestions)
    - `get_stats()` — Statistiques (total commandes, exécutions, plus utilisées)
  - Résultats par défaut quand la query est vide (commandes récentes + navigation)
  - Boost de récence dans le scoring (les commandes récemment utilisées remontent)
  - Historique limitable (défaut 50 entrées)
- `tests/test_command_palette.py` — 40 tests unitaires (PaletteCommand: 3, SearchResult: 2, CommandExecution: 2, fuzzy matching: 5, built-in: 3, registration: 4, search: 6, execution: 4, history: 3, recent: 3, stats: 2, scope: 3)

**Commandes intégrées :**

| Commande | Catégorie | Raccourci | Description |
|----------|-----------|-----------|-------------|
| Create Task | Tasks | `Ctrl+N` | Créer une nouvelle tâche |
| Search Tasks | Tasks | `/` | Rechercher des tâches |
| Go to Kanban | Navigation | `Ctrl+1` | Naviguer vers le Kanban |
| Go to Terminals | Navigation | `Ctrl+2` | Naviguer vers les Terminals |
| Go to Insights | Navigation | `Ctrl+3` | Naviguer vers les Insights |
| Go to Code Review | Navigation | `Ctrl+4` | Naviguer vers le Code Review |
| Go to Settings | Navigation | `Ctrl+5` | Naviguer vers les Settings |
| New Terminal | Terminal | `Ctrl+Shift+T` | Ouvrir un nouveau terminal |
| Run Agent | Agents | `Ctrl+Enter` | Lancer l'agent sur la tâche sélectionnée |
| Switch LLM Provider | Providers | — | Changer de provider LLM |
| Toggle Theme | Settings | — | Basculer entre thème clair/sombre |
| Start Pair Programming | Agents | — | Démarrer le pair programming |
| View Session History | Navigation | — | Voir l'historique des sessions |
| Export Report | Tasks | — | Exporter un rapport |
| Open Dependency Graph | Navigation | — | Ouvrir le graphe de dépendances |
| Keyboard Shortcuts | Help | `Ctrl+/` | Afficher les raccourcis clavier |

**Fonctionnalités :**
- ✅ Recherche fuzzy intelligente de tâches, commandes, paramètres, fichiers
- ✅ Exécution de commandes : "Create task", "Switch provider", "Open terminal"
- ✅ Historique des commandes récentes (boost dans les résultats)
- ✅ Actions contextuelles basées sur la vue active (filtrage par scope)
- ✅ Fuzzy search avec match exact, consécutif, début de mot
- ✅ 16 commandes intégrées couvrant toute l'application
- ✅ Extensible : ajout de commandes custom via `register_command()`
- ✅ Résultats par défaut (commandes récentes + navigation) quand la query est vide

**Utilisation dans l'application :**

1. **Accès** : Appuyer sur `Ctrl+K` (ou `Cmd+K` sur macOS) depuis n'importe quelle vue. La palette s'ouvre en overlay au centre de l'écran avec un champ de saisie.
2. **Recherche** : Taper le début d'une commande (ex : "creat" pour trouver "Create Task", "term" pour "New Terminal"). Les résultats apparaissent en temps réel, triés par pertinence.
3. **Navigation rapide** : Taper le nom d'une vue (ex : "kanban", "insights", "settings") pour y naviguer directement.
4. **Exécution** : Cliquer sur un résultat ou appuyer sur `Enter` pour exécuter la commande. Le raccourci clavier associé est affiché à droite de chaque résultat.
5. **Commandes récentes** : Quand la palette est ouverte sans saisie, les commandes récemment utilisées apparaissent en premier, suivies des commandes de navigation.
6. **Raccourcis affichés** : Chaque commande affiche son raccourci clavier (ex : `Ctrl+N` à côté de "Create Task") pour apprendre les raccourcis progressivement.
7. **Fermeture** : Appuyer sur `Escape` ou cliquer en dehors de la palette pour la fermer.
8. **Icônes** : Chaque commande a une icône Lucide (plus-circle, search, layout, terminal, play, cpu, sun, users, clock, download, git-branch, keyboard).

```python
from apps.backend.ui.command_palette import CommandPalette

palette = CommandPalette()

# Recherche fuzzy
results = palette.search("creat task")
for r in results:
    print(f"  [{r.score:.0f}] {r.label} — {r.description} ({r.shortcut})")

# Exécution
result = palette.execute("create_task")
print(f"Success: {result.success}")

# Ajouter une commande custom
palette.register_command(
    "deploy_staging",
    "Deploy to Staging",
    description="Deploy the current build to staging environment",
    category="tasks",
    icon="rocket",
    handler=lambda: deploy_to("staging"),
)

# Commandes récentes
recent = palette.get_recent_commands(limit=5)
for cmd in recent:
    print(f"  {cmd.label}")
```

**Impact :** Faible — Quick win, UX très appréciée par les développeurs.

---

## Matrice de priorisation

| Feature | Effort | Impact Business | Différenciation |
|---------|--------|----------------|-----------------|
| Dashboard métriques ✅ | Moyen | 🔥🔥🔥 | Moyen |
| Historique sessions ✅ | Moyen | 🔥🔥🔥 | Élevé |
| Agent refactoring ✅ | Élevé | 🔥🔥🔥 | Élevé |
| Agent documentation ✅ | Moyen | 🔥🔥🔥 | Élevé |
| Mode pair programming ✅ | Moyen | 🔥🔥🔥🔥 | Très élevé |
| Intégration Jira ✅ | Moyen | 🔥🔥🔥🔥 | Moyen |
| Azure DevOps enrichi ✅ | Moyen | 🔥🔥🔥 | Élevé |
| Intégration Slack/Teams ✅ | Faible | 🔥🔥🔥 | Moyen |
| Intégration SonarQube ✅ | Faible | 🔥🔥 | Moyen |
| Plugin VSCode | Élevé | 🔥🔥🔥🔥 | Très élevé |
| Routing intelligent LLM | Élevé | 🔥🔥🔥 | Très élevé |
| Estimation des coûts ✅ | Moyen | 🔥🔥🔥🔥 | Élevé |
| Scheduling de tâches ✅ | Moyen | 🔥🔥🔥 | Moyen |
| Auto-detection tâches ✅ | Moyen | 🔥🔥🔥 | Élevé |
| Support modèles locaux ✅ | Moyen | 🔥🔥🔥 | Élevé |
| Génération de tests ✅ | Élevé | 🔥🔥🔥🔥 | Élevé |
| Command Palette ✅ | Faible | 🔥🔥 | Moyen |
| Raccourcis clavier ✅ | Faible | 🔥🔥 | Moyen |
| Notifications desktop ✅ | Faible | 🔥🔥 | Moyen |
| Graphe dépendances ✅ | Moyen | 🔥🔥🔥 | Élevé |
| Anomalies comportementales ✅ | Moyen | 🔥🔥🔥 | Élevé |
| Multi-utilisateurs | Très élevé | 🔥🔥🔥🔥🔥 | Très élevé |
| Audit trail | Moyen | 🔥🔥🔥 | Élevé (entreprise) |

---

## Quick Wins recommandés (< 1 semaine)

1. **Command Palette** ✅ — Palette universelle avec 16 commandes, fuzzy search, historique (40 tests)
2. **Raccourcis clavier** ✅ — 15 raccourcis par défaut, remapping, cheat sheet, export/import (40 tests)
3. **Estimation coûts basique** ✅ — Calcul coût par token affiché dans le dashboard existant
4. **Intégration SonarQube** ✅ — Le MCP est déjà disponible, il suffit de consommer les données
5. **Notifications desktop enrichies** ✅ — 13 types, actions rapides, résumés périodiques, heures de silence (40 tests)
6. **Templates de tâches** ✅ — Fichiers YAML dans `.auto-claude/templates/` + UI de sélection

---

## Roadmap suggérée

### Phase 1 — Fondations (Q1 2026)
- Dashboard métriques ✅
- Historique et replay sessions ✅
- Estimation des coûts ✅
- Command Palette ✅ + raccourcis clavier ✅
- Templates de tâches ✅
- Notifications desktop enrichies ✅
- Quick wins ci-dessus ✅

### Phase 2 — Intelligence (Q2 2026)
- Mode pair programming interactif ✅
- Agent de refactoring autonome ✅
- Agent de documentation automatique ✅
- Routing intelligent multi-provider
- Génération automatique de tests ✅

### Phase 3 — Entreprise (Q3 2026)
- Intégration Jira ✅
- Azure DevOps enrichi ✅
- Intégration Slack/Teams ✅
- Audit trail complet
- Sandbox renforcé ✅
- Détection d'anomalies comportementales ✅
- Graphe dépendances de tâches ✅

### Phase 4 — Collaboration (Q4 2026)
- Mode multi-utilisateurs
- API REST publique + SDK
- Plugin VSCode
