# Feature Ideas

> Idées de fonctionnalités pour WorkPilot AI. Triées par impact — les plus bangers en premier.

---

## Tier S — Game Changers

### 1. Agent Replay & Debug Mode

Rejouer visuellement le raisonnement d'un agent step-by-step : décisions prises, fichiers lus, outils utilisés, tokens consommés.

- **Principe :** Enregistrement structuré de chaque session agent (tool calls, fichiers modifiés, raisonnement). Interface de replay avec timeline interactive, diff des fichiers à chaque étape, et arbre de décision. Mode debug pour poser des breakpoints sur les décisions de l'agent.
- **Exploite :** Agent process, agent events, agent state
- **Effort :** Élevé
- **Pourquoi c'est banger :** Aucun concurrent ne propose ça. Transparence totale sur l'IA = confiance utilisateur massive. Killer feature pour le marketing.

### 2. Self-Healing Codebase

L'app surveille le repo en continu et corrige automatiquement les régressions détectées.

- **Principe :** Hook sur `git push` / CI. Quand les tests cassent, un agent analyse le diff, identifie la régression, génère un fix dans un worktree isolé, lance le QA, et ouvre une PR de correction — le tout sans intervention humaine.
- **Exploite :** Agent coder, worktree isolation, QA pipeline, GitHub/GitLab integration
- **Effort :** Élevé
- **Pourquoi c'est banger :** Le repo se répare tout seul. Ça vend du rêve en démo.

### 3. Incident Responder

Agent connecté aux sources de logs de production qui détecte les erreurs, identifie la root cause et génère un fix autonome.

- **Principe :** Connecté à Sentry, Datadog, CloudWatch, etc. L'agent détecte les erreurs en temps réel, corrèle avec le code source, identifie la cause probable, génère un fix dans un worktree isolé avec tests de régression, et ouvre une PR.
- **Exploite :** Agent coder, worktree isolation, QA pipeline, GitHub/GitLab integration
- **Effort :** Élevé
- **Pourquoi c'est banger :** On passe de "l'IA écrit du code" à "l'IA maintient la prod". Changement de paradigme.

### 4. Multi-Repo Orchestration

Un seul spec qui orchestre des modifications sur plusieurs repositories simultanément.

- **Principe :** Une tâche peut cibler plusieurs repos (microservices, frontend + backend, shared libs). L'agent coordonne les modifications, gère les dépendances inter-repos, et crée des PR liées avec des tests cross-repo.
- **Exploite :** Worktree isolation, agent queue, GitHub/GitLab integration
- **Effort :** Élevé
- **Pourquoi c'est banger :** Personne ne fait ça. Les architectures modernes sont multi-repo — WorkPilot serait le seul à les supporter nativement.

---

## Tier A — Strong Impact

### 5. Build Analytics Dashboard ✅ Implémenté

Métriques complètes sur les agents : taux de succès QA, coût tokens par phase, patterns d'échec, évolution dans le temps.

- **Principe :** Dashboard visuel avec graphiques d'évolution. Agrège les données de tous les builds : durée par phase, nombre d'itérations QA, tokens consommés, types d'erreurs récurrents. Comparaison entre modèles/configurations.
- **Exploite :** Agent events, spec directory structure, QA reports
- **Effort :** Moyen
- **Pourquoi c'est banger :** Feedback loop indispensable. Les power users vont adorer optimiser leurs agents.

#### 📊 Comment utiliser le Build Analytics Dashboard

Le Build Analytics Dashboard est maintenant disponible dans l'interface WorkPilot AI ! Voici comment l'utiliser :

##### 🚀 Accès au Dashboard

1. **Navigation** : Dans la barre latérale, cliquez sur **"Analytics"** dans le groupe "Planning" (raccourci clavier : `A`)
2. **Ouverture** : Le dashboard s'ouvre directement dans l'interface principale

##### 📈 Fonctionnalités principales

**🎯 Vue d'ensemble (Overview)**
- **KPIs principaux** : Nombre total de builds, taux de succès, tokens utilisés, coût total
- **Builds récents** : Liste des derniers builds avec statut, durée, consommation
- **Performance par phase** : Métriques détaillées pour chaque phase (planning, coding, QA)

**🔧 Vue Builds**
- **Liste complète** : Tous les builds avec filtres et pagination
- **Détails build** : Cliquez sur un build pour voir phases, résultats QA, erreurs
- **Statuts** : Visualisation rapide des builds réussis/échoués/en cours

**⚡ Vue Performance**
- **Performance des agents** : Succès, durée, tokens et coût par type d'agent
- **Tendance tokens** : Évolution de la consommation sur la période sélectionnée
- **Comparaison modèles** : Performance par LLM provider et modèle

**🐛 Vue Erreurs**
- **Types d'erreurs** : Classification et fréquence des erreurs
- **Taux de résolution** : Pourcentage d'erreurs résolues automatiquement
- **Patterns** : Identification des problèmes récurrents

##### 🎛️ Personnalisation

**Période temporelle**
- Sélectionnez la période d'analyse : 7 jours, 30 jours (par défaut), ou 90 jours
- Les KPIs et graphiques s'adaptent automatiquement

**Rafraîchissement**
- Cliquez sur "Refresh" pour mettre à jour les données en temps réel
- Les données se rafraîchissent automatiquement au chargement

##### 📊 Métriques disponibles

**Builds**
- Taux de succès global
- Durée moyenne des builds
- Nombre d'itérations QA
- Tokens par build

**Tokens**
- Consommation totale et par build
- Coût estimé en USD
- Répartition par provider/modèle

**QA**
- Taux de réussite des tests
- Couverture de code moyenne
- Score de qualité
- Issues de sécurité trouvées/résolues

**Erreurs**
- Classification par type et catégorie
- Taux de résolution
- Patterns récurrents

##### 🔍 Tips d'utilisation

1. **Optimisation** : Utilisez la vue "Performance" pour identifier les agents les plus efficaces
2. **Débogage** : La vue "Erreurs" aide à comprendre les problèmes récurrents
3. **Budget** : Surveillez les coûts tokens dans la vue d'ensemble
4. **Tendances** : Comparez les performances sur différentes périodes

##### 🛠️ Pour les développeurs

Le dashboard est alimenté par le système de collecte automatique qui :
- Capture les événements de phase en temps réel
- Agrège les données de token usage
- Enregistre les résultats QA
- Classifie les erreurs

Les données sont stockées dans une base SQLite locale (`analytics.db`) et accessibles via l'API REST `/analytics/*`.

### 6. Test Generation Agent ✅ Implémenté

Agent IA spécialisé dans la génération automatique de tests et l'analyse de couverture de code.

- **Principe :** Analyse le code source pour identifier les zones non couvertes par les tests, détecte les conventions de test existantes, et génère automatiquement des tests unitaires, d'intégration et E2E. Supporte les approches TDD et post-build. S'intègre automatiquement dans le pipeline de build.
- **Exploite :** Code analyzer, convention detection, LLM generation, build pipeline integration
- **Effort :** Moyen
- **Pourquoi c'est banger :** La couverture de test s'améliore automatiquement. Plus besoin d'écrire manuellement les tests de base.

#### 🧪 Comment utiliser le Test Generation Agent

Le Test Generation Agent est maintenant disponible dans l'interface WorkPilot AI ! Voici comment l'utiliser :

##### 🚀 Accès au Test Generation Agent

1. **Navigation** : Dans la barre latérale, cliquez sur **"Test Generation"** dans le groupe "Tools" (icône 🧪)
2. **Ouverture** : Une boîte de dialogue modale s'ouvre avec les différentes options de génération

##### 📝 Modes d'utilisation

**🔍 Mode Analyse**
- Analyse la couverture de code d'un fichier ou module spécifique
- Identifie les fonctions et branches non testées
- Génère un rapport détaillé des gaps de couverture
- **Utilisation** : Entrez le chemin du fichier à analyser, cliquez sur "Analyze Coverage"

**🧪 Mode Unit Tests**
- Génère des tests unitaires pour un fichier source
- Détecte automatiquement les conventions de test existantes
- Crée des tests happy path, edge cases et gestion d'erreurs
- **Utilisation** : Spécifiez le fichier source et le fichier de test existant (optionnel)

**🌐 Mode E2E Tests**
- Génère des tests end-to-end depuis une user story
- Crée des scénarios de test complets avec étapes détaillées
- Supporte les frameworks Cypress, Playwright, ou Selenium
- **Utilisation** : Entrez votre user story, sélectionnez le framework cible

**🔄 Mode TDD**
- Génère des tests avant l'implémentation (Test-Driven Development)
- Crée des tests failing basés sur une spécification
- Suit les meilleures pratiques TDD
- **Utilisation** : Fournissez la spécification ou les requirements

##### 🎯 Ce que l'agent fait

L'agent effectue les tâches suivantes automatiquement :
- **Détection des conventions** : Analyse les tests existants pour identifier le framework, style, et patterns
- **Analyse de couverture** : Identifie les lignes, branches et fonctions non couvertes
- **Génération intelligente** : Crée des tests pertinents basés sur le code et les conventions
- **Écriture de fichiers** : Génère les fichiers de test directement dans le projet
- **Intégration build** : Peut se déclencher automatiquement après chaque build

##### ⚙️ Configuration avancée

Le modèle IA et le niveau de réflexion utilisés par l'agent sont configurables :
1. Allez dans **Paramètres** (⚙️)
2. Section **"Feature Model Configuration"**
3. Modifiez les réglages pour **"Test Generation Agent"** :
   - **Modèle** : Choisissez le modèle LLM (Sonnet, Opus, Haiku, etc.)
   - **Niveau de réflexion** : None, Low, Medium, High, ou Ultrathink

##### 🔄 Intégration avec le build pipeline

Pour activer la génération automatique après les builds :
1. **Configuration** : Activez l'option "Post-build test generation" dans les paramètres
2. **Déclenchement** : L'agent analyse automatiquement les fichiers modifiés après chaque build
3. **Rapports** : Les résultats sont disponibles dans les logs de build et le dashboard analytics

##### 📊 Résultats et rapports

Après chaque génération, l'agent fournit :
- **📁 Fichiers créés** : Liste des fichiers de test générés avec leur emplacement
- **📈 Couverture améliorée** : Pourcentage de couverture avant et après
- **🔍 Gaps identifiés** : Zones de code toujours non couvertes
- **⚠️ Recommandations** : Suggestions pour améliorer la couverture

##### 🛠️ Architecture technique

L'agent suit le flux suivant :
1. **Frontend** : Le composant `TestGenerationDialog` envoie les requêtes via IPC
2. **Backend** : Le service `TestGenerationService` analyse le code et détecte les conventions
3. **Agent** : Le `TestGeneratorAgent` génère les tests en utilisant le LLM configuré
4. **Écriture** : Les fichiers de test sont écrits directement dans le projet
5. **Intégration** : Hook post-build pour la génération automatique

##### 🧪 Tests

Pour exécuter les tests de cette fonctionnalité :

```bash
# Tests backend (Python)
cd apps/backend
.venv/bin/pytest tests/test_generation_service.py -v

# Tests frontend (Vitest)  
cd apps/frontend
npm test -- --run src/renderer/stores/__tests__/test-generation-store.test.ts
```

### 7. Dependency Sentinel ✅ Implémenté

Surveillance proactive 24/7 des dépendances : CVE, mises à jour breaking, licences incompatibles, avec PR automatique.

- **Principe :** Scan régulier de toutes les dépendances (npm, pip, cargo, etc.). Détecte les vulnérabilités connues, les versions obsolètes, les incompatibilités de licence. Génère des PR de mise à jour avec tests de non-régression automatiques.
- **Exploite :** GitHub/GitLab integration, worktree isolation, QA pipeline
- **Effort :** Moyen
- **Pourquoi c'est banger :** Valeur immédiate, continue, et silencieuse. Le projet reste sain sans effort.

### 8. AI Pair Programming Mode

Mode collaboratif temps réel où l'IA code en parallèle du développeur sur le même worktree.

- **Principe :** Le dev travaille sur une partie du code, l'IA travaille simultanément sur une autre partie (fichiers différents). Coordination via le context system pour éviter les conflits. Split-view dans l'UI pour voir les deux progressions.
- **Exploite :** Agent terminals, worktree isolation, conflict predictor, agent queue
- **Effort :** Élevé
- **Pourquoi c'est banger :** Le vrai pair programming avec une IA. Pas du copilot inline, du vrai travail parallèle coordonné.

### 9. AI Prompt Optimizer 

Amélioration automatique des prompts utilisateurs pour garantir les meilleurs résultats possibles des agents IA.

- **Principe :** Analyse le prompt initial de l'utilisateur, l'enrichit automatiquement avec le contexte du projet (stack, conventions, patterns existants), et l'optimise pour chaque type d'agent (analyse, coding, vérification). Le système apprend des builds précédents pour identifier les formulations qui donnent les meilleurs résultats.
- **Exploite :** Context system, Memory (Graphiti), build analytics, agent events
- **Effort :** Moyen
- **Pourquoi c'est banger :** Les utilisateurs n'ont plus besoin d'être experts en prompt engineering. L'IA garantit systématiquement les meilleurs prompts possibles = qualité constante et frustration zéro.

#### 🧙 Comment utiliser le AI Prompt Optimizer

Le AI Prompt Optimizer est maintenant disponible dans l'interface WorkPilot AI ! Voici comment l'utiliser :

##### 🚀 Accès au Prompt Optimizer

1. **Depuis le formulaire de tâche** : Lorsque vous créez ou éditez une tâche, cliquez sur le bouton **✨ AI Prompt Optimizer** situé à côté du champ de description
2. **Ouverture** : Une boîte de dialogue modale s'ouvre avec l'éditeur de prompt

##### 📝 Utilisation pas à pas

**Étape 1 — Saisir votre prompt**
- Entrez ou modifiez votre prompt dans la zone de texte
- Le prompt peut être n'importe quelle instruction destinée à un agent IA
- Exemple : *"Ajouter une page de login avec email et mot de passe"*

**Étape 2 — Choisir le type d'agent**
- Sélectionnez le type d'agent cible dans le menu déroulant :
  - **Général** : Optimisation polyvalente, adaptée à tout type de tâche
  - **Analyse** : Optimisé pour l'analyse de code, les revues et l'exploration du codebase
  - **Code** : Optimisé pour l'implémentation, la génération et la modification de code
  - **Vérification** : Optimisé pour les tests, l'assurance qualité et la validation

**Étape 3 — Lancer l'optimisation**
- Cliquez sur le bouton **"Optimiser le Prompt"** (icône ✨)
- L'optimiseur analyse votre prompt et le contexte du projet en temps réel
- Vous pouvez suivre la progression grâce au statut affiché et au flux de sortie en direct

**Étape 4 — Examiner le résultat**
- Une fois terminé, vous verrez :
  - 📄 **Le prompt optimisé** : Votre prompt enrichi avec le contexte projet
  - 📝 **Les modifications apportées** : Liste détaillée de ce qui a été amélioré
  - 💡 **Le raisonnement** : Explication de pourquoi ces améliorations ont été faites

**Étape 5 — Utiliser ou copier**
- Cliquez sur **"Utiliser ce Prompt"** pour injecter le prompt optimisé directement dans votre tâche
- Ou cliquez sur **"Copier"** pour le copier dans le presse-papiers

##### 🎯 Ce que l'optimiseur fait

L'IA enrichit automatiquement votre prompt avec :
- **Le contexte du projet** : Stack technique, langages, frameworks détectés
- **Les conventions** : Patterns de nommage, style de code existant
- **L'historique des builds** : Leçons tirées des builds précédents (taux de succès QA, erreurs récurrentes)
- **La roadmap** : Features en cours et terminées pour éviter les doublons
- **Les directives agent** : Instructions spécifiques au type d'agent sélectionné

##### ⚙️ Configuration avancée

Le modèle IA et le niveau de réflexion utilisés par l'optimiseur sont configurables :
1. Allez dans **Paramètres** (⚙️)
2. Section **"Feature Model Configuration"**
3. Modifiez les réglages pour **"Prompt Optimizer"** :
   - **Modèle** : Choisissez le modèle LLM (Sonnet, Opus, Haiku, etc.)
   - **Niveau de réflexion** : None, Low, Medium, High, ou Ultrathink

##### 🔄 En cas d'erreur

- Si l'optimisation échoue, un message d'erreur s'affiche
- Cliquez sur **"Réessayer"** pour relancer l'optimisation
- Vérifiez qu'un projet est bien sélectionné (nécessaire pour le contexte)

##### 🛠️ Architecture technique

L'optimiseur suit le flux suivant :
1. **Frontend** : Le composant `PromptOptimizerDialog` envoie le prompt via IPC
2. **Main process** : Le service `PromptOptimizerService` lance le runner Python en sous-processus
3. **Backend** : Le runner `prompt_optimizer_runner.py` charge le contexte projet, construit un system prompt enrichi, et utilise le Claude Agent SDK pour optimiser
4. **Streaming** : Les résultats sont streamés en temps réel vers l'UI via des événements IPC

##### 🧪 Tests

Pour exécuter les tests de cette fonctionnalité :

```bash
# Tests backend (Python)
cd apps/backend
.venv/bin/pytest tests/test_prompt_optimizer_runner.py -v

# Tests frontend (Vitest)
cd apps/frontend
npm test -- --run src/renderer/stores/__tests__/prompt-optimizer-store.test.ts
```

### 10. Conflict Predictor

Détection proactive des conflits potentiels entre branches/worktrees actifs avant qu'ils ne surviennent.

- **Principe :** Analyse les fichiers modifiés dans chaque worktree actif et alerte quand deux agents/développeurs touchent les mêmes zones. Propose des stratégies de résolution préventives ou réordonne les tâches.
- **Exploite :** Worktree isolation, semantic merge, agent state
- **Effort :** Moyen
- **Pourquoi c'est banger :** Prévenir plutôt que guérir. Élimine une des plus grosses frictions du dev parallèle.

---

## Tier B — Solid Value

### 11. Live Code Review AI

Review en temps réel pendant que le dev code, pas après.

- **Principe :** L'IA observe les modifications en cours dans les Agent Terminals et propose des améliorations, détecte les bugs potentiels, vérifie l'alignement avec le spec — avant même le commit. Suggestions non-intrusives en sidebar.
- **Exploite :** Terminal system, context system, spec pipeline
- **Effort :** Élevé
- **Pourquoi c'est banger :** Shift-left ultime. Les problèmes sont détectés à l'écriture, pas à la review.

### 11. Auto-Refactor Agent

Détection continue de code smells, dette technique et patterns obsolètes avec refactoring autonome.

- **Principe :** Un agent analyse périodiquement le codebase et propose des refactorings (extract method, dead code, patterns dépréciés, duplication excessive). L'utilisateur valide et l'agent exécute dans un worktree isolé avec QA.
- **Exploite :** Agent coder, worktree isolation, QA reviewer
- **Effort :** Moyen
- **Pourquoi c'est banger :** La dette technique se réduit toute seule.

### 12. Pipeline Generator

Génération automatique de CI/CD complète adaptée au projet.

- **Principe :** Analyse la stack, les tests, le linting, le build du projet et génère un fichier CI/CD (GitHub Actions, GitLab CI) complet et fonctionnel. Cache, matrix, deploy, notifications inclus.
- **Exploite :** Project analysis, context system
- **Effort :** Moyen
- **Pourquoi c'est banger :** Setup CI/CD en 30 secondes au lieu de 2 heures.

### 13. Smart Estimation ✅ Implémenté

Scores de complexité basés sur l'historique réel des builds passés.

- **Principe :** Analyse les builds précédents pour scorer la complexité relative des nouvelles tâches (fichiers impactés, itérations QA probables, risque). Scores comparatifs type story points, pas de fausses promesses temporelles.
- **Exploite :** Memory (Graphiti), spec pipeline, build analytics
- **Effort :** Moyen
- **Pourquoi c'est banger :** Priorisation data-driven. Plus on utilise WorkPilot, plus les estimations sont précises.

#### 🧠 Comment utiliser la Smart Estimation

La Smart Estimation est maintenant disponible dans l'interface WorkPilot AI ! Voici comment l'utiliser :

##### 🚀 Accès à la Smart Estimation

1. **Navigation** : Dans la barre latérale, cliquez sur **"Smart Estimation"** dans le groupe "AI Tools" (icône 📈, raccourci clavier : `S`)
2. **Ouverture** : Une boîte de dialogue modale s'ouvre avec l'interface d'estimation

##### 📝 Utilisation pas à pas

**Étape 1 — Décrire votre tâche**
- Entrez une description détaillée de la tâche que vous voulez estimer
- Soyez spécifique sur les fonctionnalités et technologies impliquées
- Exemples :
  - *"Ajouter l'authentification utilisateur avec JWT"*
  - *"Créer un dashboard avec graphiques interactifs"*
  - *"Refactoriser le service de paiement pour supporter Stripe"*
  - *"Implémenter un système de cache Redis"*

**Étape 2 — Lancer l'analyse**
- Cliquez sur le bouton **"Estimer la Complexité"** pour commencer l'analyse
- L'IA analyse votre description et la compare avec l'historique des builds
- Suivez la progression en temps réel avec les messages de statut

**Étape 3 — Consulter les résultats**
Une fois l'analyse terminée, vous obtenez :
- 📊 **Score de complexité** : Échelle 1-13 basée sur l'historique
- ⏱️ **Durée estimée** : Temps de développement prévu
- 🔄 **Itérations QA** : Nombre de cycles qualité estimés
- 💰 **Coût estimé** : Tokens et coûts d'IA prévus
- 🚨 **Facteurs de risque** : Éléments qui pourraient compliquer la tâche
- 💡 **Recommandations** : Suggestions pour réussir
- 📈 **Tâches similaires** : Historique des tâches similaires

##### 🎯 Interprétation des résultats

**Score de Complexité (1-13)**
- **1-3** : Tâche simple, faible risque
- **4-6** : Tâche modérée, complexité moyenne  
- **7-9** : Tâche complexe, plusieurs composants
- **10-13** : Tâche très complexe, haut risque

**Niveau de Confiance**
- Basé sur le nombre de tâches similaires dans l'historique
- Plus de données = meilleure précision
- Score de 0% à 100%

##### 🛠️ Configuration avancée

Le modèle IA et le niveau de réflexion utilisés par la Smart Estimation sont configurables :
1. Allez dans **Paramètres** (⚙️)
2. Section **"Feature Model Configuration"**
3. Modifiez les réglages pour **"Smart Estimation"** :
   - **Modèle** : Choisissez le modèle LLM (Sonnet, Opus, Haiku, etc.)
   - **Niveau de réflexion** : None, Low, Medium, High, ou Ultrathink

##### 📊 Algorithmes utilisés

**Calcul du score de complexité**
- **Impact fichiers** (0-4 points) : Nombre et type de fichiers concernés
- **Couverture codebase** (0-3 points) : Pourcentage du codebase affecté
- **Similarité historique** (0-3 points) : Moyenne des tâches similaires
- **Facteurs de risque** (0-2 points) : Risques identifiés
- **Indicateurs de complexité** (0-1 point) : Marqueurs techniques

**Estimation de durée**
- Basée sur la durée moyenne des tâches similaires
- Ajustée selon le score de complexité
- Multipliée par les facteurs de risque identifiés

##### 🎯 Cas d'usage idéaux

**Planification de sprints**
- Estimer l'effort pour les prochaines tâches
- Allouer les ressources de manière optimale
- Identifier les tâches à haut risque

**Évaluation de features**
- Comprendre la complexité avant développement
- Négocier les délais avec les stakeholders
- Prioriser le backlog

**Formation d'équipe**
- Estimer la difficulté pour les nouveaux membres
- Identifier les besoins de formation
- Partager les connaissances sur les complexités

##### 📈 Amélioration continue

La Smart Estimation apprend de votre historique :
- Plus de builds = estimations plus précises
- Descriptions détaillées = meilleure analyse
- Feedback régulier = modèles affinés

##### 🧪 Tests

Pour exécuter les tests de cette fonctionnalité :

```bash
# Tests backend (Python)
cd apps/backend
.venv/bin/pytest tests/services/test_smart_estimation_service.py -v
.venv/bin/pytest tests/runners/test_smart_estimation_runner.py -v

# Tests frontend (Vitest)
cd apps/frontend
npm test -- --run src/renderer/stores/__tests__/smart-estimation-store.test.ts
npm test -- --run src/renderer/components/smart-estimation/__tests__/SmartEstimationDialog.test.tsx
```

##### 🛠️ Architecture technique

La Smart Estimation suit le flux suivant :
1. **Frontend** : Le composant `SmartEstimationDialog` envoie la description via IPC
2. **Main process** : Le service `smart-estimation-handlers.ts` lance le runner Python
3. **Backend** : Le service `SmartEstimationService` analyse et calcule les estimations
4. **Runner** : `smart_estimation_runner.py` exécute et streame les résultats
5. **Résultats** : Structure JSON complète avec tous les métriques d'estimation

##### 📚 Documentation complète

- Documentation technique : `docs/smart-estimation.md`
- Guide d'utilisation : `docs/smart-estimation-usage-guide.md`
- Code source : `apps/backend/services/smart_estimation_service.py`
- Composant UI : `apps/frontend/src/renderer/components/smart-estimation/SmartEstimationDialog.tsx`

### 14. Natural Language Git ✅ Implémenté

Manipuler git en langage naturel directement depuis l'interface.

- **Principe :** "Annule mes 3 derniers commits", "montre ce qui a changé depuis lundi", "crée une branche depuis le dernier tag stable", "cherry-pick le fix de la PR #42". Traduction en commandes git avec confirmation avant exécution.
- **Exploite :** Terminal system, Insights chat
- **Effort :** Faible
- **Pourquoi c'est banger :** Quick win à fort impact. Git devient accessible à tous.

**Implémentation :**
- Interface dialog avec input en langage naturel
- Conversion AI vers commandes Git via Claude
- Exécution avec confirmation et affichage des résultats
- Support des commandes Git les plus courantes
- Gestion d'erreurs et streaming en temps réel

### 15. Context-Aware Snippets

Snippets intelligents qui s'adaptent au style et aux conventions du projet.

- **Principe :** Génère du code adapté aux imports existants, conventions de nommage, patterns utilisés dans le projet. Alimenté par le context system et la mémoire Graphiti. Accessible via palette de commandes.
- **Exploite :** Context system, Memory (Graphiti), project analysis
- **Effort :** Moyen
- **Pourquoi c'est banger :** Chaque snippet "semble écrit par quelqu'un qui connaît le projet".

---

## Tier C — Nice to Have

### 16. Team Knowledge Sync

Memory System partagé entre tous les membres de l'équipe.

- **Principe :** Le graphe Graphiti devient partagé (serveur centralisé ou sync P2P). Décisions architecturales, patterns découverts, pièges identifiés sont accessibles à toute l'équipe.
- **Exploite :** Graphiti Memory System
- **Effort :** Élevé
- **Pourquoi c'est banger :** L'expérience collective capitalise automatiquement. Onboarding d'un nouveau dev en quelques minutes.

### 17. Environment Cloner

Reproduction d'environnements prod/staging en local pour debug.

- **Principe :** Capture la config d'un environnement distant (variables d'env, versions de services, données de seed) et reproduit un équivalent local via Docker Compose ou scripts.
- **Exploite :** Platform abstraction, terminal system
- **Effort :** Élevé
- **Pourquoi c'est banger :** "Ça marche en local mais pas en prod" disparaît.

### 18. Architecture Visualizer

Génération automatique de diagrammes d'architecture depuis le code.

- **Principe :** Analyse le codebase et génère des diagrammes interactifs : dépendances entre modules, flux de données, hiérarchie de composants, schéma de base de données. Mis à jour automatiquement à chaque build.
- **Exploite :** Context system, project analysis
- **Effort :** Moyen
- **Pourquoi c'est banger :** La doc d'archi se génère et se maintient toute seule.

### 19. Code Migration Agent

Migration automatique entre frameworks, versions majeures ou langages.

- **Principe :** "Migre ce projet de React Class Components vers des Hooks", "Upgrade de Python 3.9 à 3.12", "Convertis ce module JS en TypeScript". L'agent analyse le code, planifie la migration, exécute par batch, et valide avec QA.
- **Exploite :** Agent coder, worktree isolation, QA pipeline, context system
- **Effort :** Élevé
- **Pourquoi c'est banger :** Les migrations sont le cauchemar de tout dev. L'automatiser est un selling point énorme.

### 20. Performance Profiler Agent

Agent qui profile le code, identifie les bottlenecks et propose des optimisations.

- **Principe :** Lance des benchmarks, analyse les résultats, identifie les hot paths et propose des optimisations concrètes (algorithme, caching, lazy loading, query optimization). Peut implémenter les fixes automatiquement.
- **Exploite :** Agent coder, terminal system, QA pipeline
- **Effort :** Élevé
- **Pourquoi c'est banger :** L'app s'optimise toute seule. Plus besoin d'experts perf.

### 21. Documentation Agent

Génération et maintenance automatique de la documentation technique.

- **Principe :** Analyse le code et génère/met à jour la documentation : API docs, README, guides de contribution, JSDoc/docstrings, diagrammes de séquence. Détecte la doc obsolète après chaque changement.
- **Exploite :** Context system, project analysis, Memory (Graphiti)
- **Effort :** Moyen
- **Pourquoi c'est banger :** La doc n'est plus jamais outdated.

### 22. Plugin Marketplace

Écosystème de plugins communautaires pour étendre WorkPilot.

- **Principe :** SDK pour créer des plugins : nouveaux agents, intégrations tierces, templates de specs, thèmes UI, custom prompts. Marketplace in-app avec installation en un clic.
- **Exploite :** Architecture modulaire existante
- **Effort :** Élevé
- **Pourquoi c'est banger :** Effet réseau. La communauté étend le produit. Verrouille les utilisateurs dans l'écosystème.

### 23. Voice Control ✅ Implémenté

Contrôler WorkPilot à la voix : décrire des tâches, naviguer dans l'UI, commander des builds.

- **Principe :** Whisper/Deepgram pour le speech-to-text. "Lance un build sur le spec 42", "Montre-moi le kanban", "Crée une tâche pour refactorer le module auth". Feedback audio optionnel sur les résultats.
- **Exploite :** Insights chat, terminal system, agent queue
- **Effort :** Moyen
- **Pourquoi c'est banger :** Effet wow en démo. Hands-free coding.

#### 🎤 Comment utiliser le Voice Control

Le Voice Control est maintenant disponible dans l'interface WorkPilot AI ! Voici comment l'utiliser :

##### 🚀 Accès au Voice Control

1. **Navigation** : Dans la barre latérale, cliquez sur **"Contrôle Vocal"** dans le groupe "Utilities" (icône 🎤, raccourci clavier : `V`)
2. **Ouverture** : Une boîte de dialogue modale s'ouvre avec l'interface d'enregistrement vocal

##### 📝 Utilisation pas à pas

**Étape 1 — Démarrer l'enregistrement**
- Cliquez sur le bouton microphone 🎤 pour commencer l'enregistrement
- Le bouton devient rouge et indique "Écoute..."
- Un visualisateur de niveau audio s'affiche en temps réel
- Un chronomètre indique la durée d'enregistrement

**Étape 2 — Donner votre commande vocale**
- Parlez naturellement votre commande
- Exemples de commandes :
  - *"Montre-moi le kanban"*
  - *"Crée une nouvelle tâche pour l'authentification utilisateur"*
  - *"Ouvre les paramètres du projet"*
  - *"Lance un build sur le spec 42"*
  - *"Affiche le dashboard analytics"*
  - *"Navigue vers la revue de code"*

**Étape 3 — Arrêter l'enregistrement**
- Cliquez à nouveau sur le bouton microphone 🎤 pour arrêter
- Le système commence automatiquement le traitement

**Étape 4 — Examiner le résultat**
- Une fois le traitement terminé, vous verrez :
  - 📄 **La transcription** : Votre commande retranscrite en texte
  - 🎯 **La commande interprétée** : La commande structurée par l'IA
  - ⚡ **L'action** : L'action principale (navigate, create, show, start, etc.)
  - ⚙️ **Les paramètres** : Détails spécifiques de la commande
  - 📊 **Le niveau de confiance** : Fiabilité de l'interprétation (0-100%)

**Étape 5 — Exécuter ou copier**
- Cliquez sur **"Exécuter la Commande"** pour lancer l'action
- Ou cliquez sur **"Copier"** pour copier la transcription

##### 🎯 Ce que le Voice Control fait

L'IA interprète automatiquement vos commandes vocales et :
- **Transcription** : Convertit votre parole en texte avec speech-to-text
- **Analyse sémantique** : Comprend l'intention derrière vos mots
- **Structuration** : Extrait action et paramètres de manière structurée
- **Navigation intelligente** : Identifie les vues et actions disponibles
- **Confidence scoring** : Évalue la fiabilité de l'interprétation

##### 🎛️ Configuration avancée

Le modèle IA et le niveau de réflexion utilisés par le Voice Control sont configurables :
1. Allez dans **Paramètres** (⚙️)
2. Section **"Feature Model Configuration"**
3. Modifiez les réglages pour **"Voice Control"** :
   - **Modèle** : Choisissez le modèle LLM (Sonnet, Opus, Haiku, etc.)
   - **Niveau de réflexion** : None, Low, Medium, High, ou Ultrathink

##### 🎭 Actions disponibles

**Navigation**
- `"Montre-moi le kanban"` → Navigate to kanban
- `"Ouvre les terminaux"` → Navigate to terminals
- `"Affiche analytics"` → Navigate to analytics
- `"Voir la roadmap"` → Navigate to roadmap

**Création**
- `"Crée une tâche pour login"` → Create task
- `"Nouveau projet auth"` → Create project
- `"Ajoute une issue GitHub"` → Create GitHub issue

**Affichage**
- `"Montre-moi les insights"` → Show insights
- `"Affiche le contexte"` → Show context
- `"Ouvre la documentation"` → Show documentation

**Actions système**
- `"Lance un build"` → Start build
- `"Ouvre les paramètres"` → Open settings
- `"Rafraîchit le projet"` → Refresh project

##### 🔄 En cas d'erreur

- Si la transcription échoue, un message d'erreur s'affiche
- Vérifiez que votre micro fonctionne correctement
- Assurez-vous d'avoir les permissions audio nécessaires
- Cliquez sur **"Réessayer"** pour relancer l'enregistrement

##### 🛠️ Architecture technique

Le Voice Control suit le flux suivant :
1. **Frontend** : Le composant `VoiceControlDialog` gère l'interface d'enregistrement
2. **Service** : Le `VoiceControlService` gère l'enregistrement audio et la communication
3. **Backend** : Le runner `voice_control_runner.py` effectue speech-to-text et interprétation IA
4. **IA** : Utilise Claude SDK pour analyser et structurer les commandes
5. **Résultat** : Retourne une structure JSON avec transcription, action et paramètres

##### 🎯 Exemples de commandes avancées

**Commandes avec paramètres**
- *"Crée une tâche urgent pour fixer le bug d'auth"* → Create task with priority and description
- *"Montre-moi les insights des 7 derniers jours"* → Navigate with time filter
- *"Lance un build sur le spec 42 avec mode fast"* → Start build with options

**Navigation multi-étapes**
- *"Va dans analytics puis montre-moi les coûts"* → Sequential navigation
- *"Ouvre les paramètres puis va dans la section providers"* → Multi-step navigation

**Commandes contextuelles**
- *"Crée une sous-tâche pour la story en cours"* → Context-aware creation
- *"Montre-moi les commits du projet actuel"* → Project-specific actions

##### 🧪 Tests et qualité

Le système inclut des validations :
- **Détection de silence** : Arrêt automatique si pas de parole
- **Qualité audio** : Monitoring du niveau sonore en temps réel
- **Confidence scoring** : Indicateur de fiabilité de l'interprétation
- **Fallback textuel** : Option de copier/coller manuel si nécessaire

##### 🎙️ Configuration technique

Pour les développeurs, le Voice Control utilise :
- **Speech-to-text** : Whisper ou Deepgram pour la transcription
- **Claude SDK** : Pour l'interprétation sémantique des commandes
- **Audio streaming** : Niveaux audio en temps réel pendant l'enregistrement
- **IPC communication** : Architecture sécurisée entre frontend et backend
- **Error handling** : Gestion robuste des erreurs audio et IA

##### 🌐 Support multilingue

Le Voice Control supporte plusieurs langues :
- **Français** : Commandes en français avec interprétation contextuelle
- **Anglais** : Support natif avec vocabulaire technique étendu
- **Extension** : Possibilité d'ajouter d'autres langues via configuration

##### 📊 Performance et optimisation

- **Latence** : < 2 secondes pour transcription + interprétation
- **Précision** : > 90% de confiance sur commandes standards
- **Adaptation** : Apprend des patterns de commandes utilisateur
- **Cache** : Mémorisation des commandes fréquentes pour accélération

### 24. AI Code Playground ✅ Implémenté

Sandbox interactive pour prototyper rapidement des idées avec l'IA avant de les intégrer au projet.

- **Principe :** Environnement isolé (sandbox Docker ou iframe) pour tester du code généré par l'IA. Preview live, hot reload, et bouton "Intégrer au projet" qui crée automatiquement un spec + worktree.
- **Exploite :** Worktree isolation, agent coder, terminal system
- **Effort :** Moyen
- **Pourquoi c'est banger :** Prototypage instantané sans polluer le projet. Test avant d'investir.

#### 🛝 Comment utiliser l'AI Code Playground

L'AI Code Playground est maintenant disponible dans l'interface WorkPilot AI ! Voici comment l'utiliser :

##### 🚀 Accès au Code Playground

1. **Navigation** : Dans la barre latérale, cliquez sur **"Code Playground"** dans le groupe "AI Tools" (icône ⚡, raccourci clavier : `G`)
2. **Ouverture** : Une boîte de dialogue modale s'ouvre avec l'interface du bac à sable de code

##### 📝 Utilisation pas à pas

**Étape 1 — Décrire votre idée**
- Entrez une description de ce que vous voulez créer
- Soyez spécifique sur les fonctionnalités et technologies
- Exemples :
  - *"Crée un composant React pour un formulaire de contact avec validation"*
  - *"Génère une page HTML avec un dashboard animé en CSS"*
  - *"Écris une fonction Python qui analyse des données CSV"*
  - *"Crée un mini-jeu en JavaScript avec canvas"*

**Étape 2 — Choisir le type de playground**
- **HTML** : Pages web statiques avec HTML/CSS/JS
- **React** : Composants React avec hooks et state
- **Vanilla JS** : Applications JavaScript pures
- **Python** : Scripts Python avec interface CLI
- **Node.js** : Applications serveur Node.js

**Étape 3 — Sélectionner le type de sandbox**
- **iframe** : Isolation légère dans le navigateur (recommandé pour le web)
- **Docker** : Conteneur isolé complet (pour Python/Node.js)
- **Web Worker** : Thread isolé pour calculs lourds

**Étape 4 — Lancer la génération**
- Cliquez sur **"Générer le Code"** pour commencer
- L'IA génère le code en temps réel avec streaming
- Suivez la progression avec les messages de statut

**Étape 5 — Tester et prévisualiser**
- **Onglet Code** : Voir le code généré avec coloration syntaxique
- **Onglet Preview** : Prévisualisation en temps réel du résultat
- **Onglet Fichiers** : Structure des fichiers générés
- Copiez le code ou intégrez-le directement

##### 🎯 Ce que le Code Playground fait

L'IA génère automatiquement :
- **Code complet** : Fichiers source avec imports et structure
- **HTML/CSS/JS** : Pages web interactives et stylées
- **Composants React** : Hooks, state management, et événements
- **Scripts Python** : Fonctions, classes, et interfaces CLI
- **Applications Node.js** : Serveurs, APIs, et middleware
- **Preview live** : Exécution en temps réel du code généré

##### 🛠️ Fonctionnalités avancées

**Types de projets supportés**
- **Web frontend** : HTML5, CSS3, JavaScript ES6+
- **React** : Hooks, Context API, Router
- **Python** : Scripts, CLI,数据分析
- **Node.js** : Express, APIs, filesystem
- **Vanilla JS** : DOM manipulation, Canvas, Web APIs

**Sécurité et isolation**
- **iframe sandbox** : Restrictions CORS et scripts
- **Docker isolation** : Environnement complètement isolé
- **Web Worker** : Exécution non-bloquante
- **No filesystem access** : Protection des données locales

##### 🎛️ Configuration avancée

Le modèle IA et le niveau de réflexion utilisés par le Code Playground sont configurables :
1. Allez dans **Paramètres** (⚙️)
2. Section **"Feature Model Configuration"**
3. Modifiez les réglages pour **"Code Playground"** :
   - **Modèle** : Choisissez le modèle LLM (Sonnet, Opus, Haiku, etc.)
   - **Niveau de réflexion** : None, Low, Medium, High, ou Ultrathink

##### 🔄 Intégration au projet

Pour intégrer le code généré dans votre projet :
1. **Générez** votre code dans le playground
2. **Testez** le résultat en preview
3. **Cliquez** sur **"Intégrer au Projet"**
4. **Spécifiez** l'emplacement cible
5. **Validez** l'intégration automatique

L'intégration crée automatiquement :
- Un nouveau worktree isolé
- Les fichiers de code aux emplacements appropriés
- Un spec de build pour validation
- Tests de non-régression

##### 📁 Structure des fichiers générés

**Projets Web**
```
index.html          # Page principale
styles.css          # Styles CSS
script.js           # Logique JavaScript
assets/              # Images et ressources
```

**Projets React**
```
Component.jsx        # Composant principal
Component.module.css # Styles scoped
hooks/              # Hooks personnalisés
utils/              # Fonctions utilitaires
```

**Projets Python**
```
main.py              # Script principal
requirements.txt     # Dépendances
README.md            # Documentation
tests/               # Tests unitaires
```

##### 🧪 Tests et qualité

Le Code Playground inclut des validations :
- **Syntax checking** : Vérification syntaxique en temps réel
- **Security scanning** : Détection de code malveillant
- **Performance monitoring** : Analyse des performances
- **Compatibility testing** : Vérification cross-browser

##### 🎨 Exemples d'utilisation

**Prototypage rapide**
- *"Crée un carousel d'images avec swipe"* → Composant React testable
- *"Génère un dashboard avec graphiques"* → Interface admin complète
- *"Fais un jeu de memory en JavaScript"* → Jeu interactif

**Proof of concept**
- *"Teste une API REST avec fetch"* → Code client fonctionnel
- *"Crée un parser JSON en Python"* → Script de traitement
- *"Build un chat WebSocket"* → Application temps réel

**Learning et expérimentation**
- *"Montre-moi comment utiliser Canvas"* → Exemple éducatif
- *"Explique les React Hooks avec code"* → Tutoriel interactif
- *"Démontre Web Workers"* → Code d'exemple

##### 🛠️ Architecture technique

Le Code Playground suit le flux suivant :
1. **Frontend** : Le composant `CodePlaygroundDialog` gère l'interface
2. **Service** : Le `CodePlaygroundService` orchestre la génération
3. **Backend** : Le runner `code_playground_runner.py` exécute et streame
4. **Sandbox** : Exécution isolée du code généré
5. **Preview** : Mise à jour en temps réel de la prévisualisation

##### 📊 Performance et optimisation

- **Génération** : < 5 secondes pour code simple
- **Preview** : Mise à jour en temps réel (< 100ms)
- **Memory** : Isolation stricte des ressources
- **Cache** : Mémorisation des templates réutilisables

##### 🌐 Support multi-langages

Le Code Playground supporte :
- **Français** : Interface et messages en français
- **Anglais** : Support natif complet
- **Code** : Support universel des langages de programmation

---

## Tier C — Nice to Have

### 16. Team Knowledge Sync

Memory System partagé entre tous les membres de l'équipe.

- **Principe :** Le graphe Graphiti devient partagé (serveur centralisé ou sync P2P). Décisions architecturales, patterns découverts, pièges identifiés sont accessibles à toute l'équipe.
- **Exploite :** Graphiti Memory System
- **Effort :** Élevé
- **Pourquoi c'est banger :** L'expérience collective capitalise automatiquement. Onboarding d'un nouveau dev en quelques minutes.

### 17. Environment Cloner

Reproduction d'environnements prod/staging en local pour debug.

- **Principe :** Capture la config d'un environnement distant (variables d'env, versions de services, données de seed) et reproduit un équivalent local via Docker Compose ou scripts.
- **Exploite :** Platform abstraction, terminal system
- **Effort :** Élevé
- **Pourquoi c'est banger :** "Ça marche en local mais pas en prod" disparaît.

### 18. Architecture Visualizer

Génération automatique de diagrammes d'architecture depuis le code.

- **Principe :** Analyse le codebase et génère des diagrammes interactifs : dépendances entre modules, flux de données, hiérarchie de composants, schéma de base de données. Mis à jour automatiquement à chaque build.
- **Exploite :** Context system, project analysis
- **Effort :** Moyen
- **Pourquoi c'est banger :** La doc d'archi se génère et se maintient toute seule.

### 19. Code Migration Agent

Migration automatique entre frameworks, versions majeures ou langages.

- **Principe :** "Migre ce projet de React Class Components vers des Hooks", "Upgrade de Python 3.9 à 3.12", "Convertis ce module JS en TypeScript". L'agent analyse le code, planifie la migration, exécute par batch, et valide avec QA.
- **Exploite :** Agent coder, worktree isolation, QA pipeline, context system
- **Effort :** Élevé
- **Pourquoi c'est banger :** Les migrations sont le cauchemar de tout dev. L'automatiser est un selling point énorme.

### 20. Performance Profiler Agent

Agent qui profile le code, identifie les bottlenecks et propose des optimisations.

- **Principe :** Lance des benchmarks, analyse les résultats, identifie les hot paths et propose des optimisations concrètes (algorithme, caching, lazy loading, query optimization). Peut implémenter les fixes automatiquement.
- **Exploite :** Agent coder, terminal system, QA pipeline
- **Effort :** Élevé
- **Pourquoi c'est banger :** L'app s'optimise toute seule. Plus besoin d'experts perf.

### 21. Documentation Agent

Génération et maintenance automatique de la documentation technique.

- **Principe :** Analyse le code et génère/met à jour la documentation : API docs, README, guides de contribution, JSDoc/docstrings, diagrammes de séquence. Détecte la doc obsolète après chaque changement.
- **Exploite :** Context system, project analysis, Memory (Graphiti)
- **Effort :** Moyen
- **Pourquoi c'est banger :** La doc n'est plus jamais outdated.

### 22. Plugin Marketplace

Écosystème de plugins communautaires pour étendre WorkPilot.

- **Principe :** SDK pour créer des plugins : nouveaux agents, intégrations tierces, templates de specs, thèmes UI, custom prompts. Marketplace in-app avec installation en un clic.
- **Exploite :** Architecture modulaire existante
- **Effort :** Élevé
- **Pourquoi c'est banger :** Effet réseau. La communauté étend le produit. Verrouille les utilisateurs dans l'écosystème.

### 23. Voice Control ✅ Implémenté

Contrôler WorkPilot à la voix : décrire des tâches, naviguer dans l'UI, commander des builds.

- **Principe :** Whisper/Deepgram pour le speech-to-text. "Lance un build sur le spec 42", "Montre-moi le kanban", "Crée une tâche pour refactorer le module auth". Feedback audio optionnel sur les résultats.
- **Exploite :** Insights chat, terminal system, agent queue
- **Effort :** Moyen
- **Pourquoi c'est banger :** Effet wow en démo. Hands-free coding.

### 24. AI Code Playground ✅ Implémenté

Sandbox interactive pour prototyper rapidement des idées avec l'IA avant de les intégrer au projet.

- **Principe :** Environnement isolé (sandbox Docker ou iframe) pour tester du code généré par l'IA. Preview live, hot reload, et bouton "Intégrer au projet" qui crée automatiquement un spec + worktree.
- **Exploite :** Worktree isolation, agent coder, terminal system
- **Effort :** Moyen
- **Pourquoi c'est banger :** Prototypage instantané sans polluer le projet. Test avant d'investir.

### 25. Cross-Language Translation

Traduire du code entre langages tout en préservant la logique et les patterns idiomatiques.

- **Principe :** "Convertis ce service Python en Go", "Porte ce composant React en Svelte". L'agent analyse la logique, traduit en respectant les patterns idiomatiques du langage cible, et génère les tests équivalents.
- **Exploite :** Agent coder, context system, QA pipeline
- **Effort :** Élevé
- **Pourquoi c'est banger :** Les migrations de stack deviennent triviales.

---

## Résumé par Tier

| Tier | # | Features | Impact |
|------|---|----------|--------|
| **S** | 4 | Agent Replay, Self-Healing, Incident Responder, Multi-Repo | Game changers — différenciateurs marché uniques |
| **A** | 5 | Analytics ✅, Test Gen ✅, Dependency Sentinel ✅, AI Pair, Prompt Optimizer ✅, Conflict Predictor | Strong impact — features attendues par les power users |
| **B** | 6 | Live Review, Auto-Refactor, Pipeline Gen, Smart Estimation ✅, NL Git ✅, Snippets | Solid value — améliorations significatives du quotidien |
| **C** | 10 | Team Sync, Env Cloner, Arch Viz, Migration, Perf Profiler, Doc Agent, Marketplace, Voice ✅, Playground ✅, Cross-Lang | Nice to have — vision long terme |
