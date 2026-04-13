# WorkPilot AI — Améliorations & Nouvelles Pistes

> Document d'analyse complémentaire à [FEATURE_IDEAS.md](FEATURE_IDEAS.md).
> Les 49 features de la roadmap initiale étant implémentées, ce document identifie :
> 1. Les **améliorations concrètes** à apporter aux features existantes (renforcement, polish, intégrations manquantes).
> 2. Les **nouvelles features** qui combleraient les angles morts actuels du produit.
>
> Principe d'écriture : privilégier l'impact utilisateur réel à la nouveauté gadget. Chaque proposition indique *pourquoi maintenant* et *ce qu'elle débloque*.

---

## Table des matières

- [Partie 1 — Améliorations des features existantes](#partie-1--améliorations-des-features-existantes)
  - [A. Orchestration & Agents](#a-orchestration--agents)
  - [B. Qualité, Test & Review](#b-qualité-test--review)
  - [C. Self-Healing & Production](#c-self-healing--production)
  - [D. Expérience développeur](#d-expérience-développeur)
  - [E. Mémoire & Apprentissage](#e-mémoire--apprentissage)
  - [F. Coûts & Analytics](#f-coûts--analytics)
  - [G. Collaboration & Enterprise](#g-collaboration--enterprise)
- [Partie 2 — Nouvelles features proposées](#partie-2--nouvelles-features-proposées)
  - [Tier S — Différenciateurs forts](#tier-s--différenciateurs-forts)
  - [Tier A — Impact élevé](#tier-a--impact-élevé)
  - [Tier B — Valeur solide](#tier-b--valeur-solide)
- [Partie 3 — Priorisation suggérée](#partie-3--priorisation-suggérée)

---

## Partie 1 — Améliorations des features existantes

### A. Orchestration & Agents

#### 1. Mission Control — Auto-scaling & load balancing intelligent

**Aujourd'hui :** l'utilisateur crée manuellement chaque agent slot via `AddAgentDialog.tsx`. Aucune recommandation automatique du nombre, du rôle ou du provider à assigner. Un débutant face au dashboard doit deviner « combien d'agents pour refactorer ce module ? ».

**Amélioration proposée :**
- **Session planner** : à partir d'un spec existant (ou d'un prompt libre), un LLM léger (Haiku) analyse la complexité, les fichiers probablement touchés, la présence de tests, les domaines (frontend/backend/DB) et propose une composition : `1 archi Opus + 3 coders Sonnet + 1 reviewer Sonnet + 1 tester Haiku`.
- **Budget-aware degradation** : l'utilisateur fixe un budget max ($ ou tokens). Si la simulation dépasse, Mission Control propose une version dégradée (Sonnet → Haiku sur les rôles non critiques) et affiche le Δ coût / qualité attendu.
- **Live rebalancing** : si un agent bloque (erreurs répétées, thinking loops détectés via `decision_tree.py`), Mission Control spawn un agent secondaire ou escalate le modèle avec notification.
- **Templates de session** : « Bug fix », « New feature », « Refactor module », « Incident response » — chaque template pré-configure la composition.

**Fichiers à toucher :**
- `apps/backend/mission_control/orchestrator.py` — ajout `suggest_composition(spec_id, budget)`.
- `apps/backend/mission_control/composition_planner.py` — nouveau module (LLM + règles heuristiques).
- `apps/frontend/src/renderer/components/mission-control/SessionTemplates.tsx` — nouveau.
- `AddAgentDialog.tsx` — bouton « Auto-compose from spec ».
- i18n : `apps/frontend/src/shared/i18n/locales/{en,fr}/missionControl.json`.

**Métriques à suivre :**
- % de sessions démarrées via auto-compose (adoption).
- Δ tokens moyen entre compositions auto et manuelles.
- Nombre de rebalancings déclenchés / session.
- Taux de dépassement budget (doit tendre vers 0).

**Edge cases :**
- Spec trop vague → fallback sur template générique + warning UI.
- Budget absurdement bas → refuser de démarrer avec message explicite.
- Provider indisponible (rate limit) → rerouter sur profil de secours via Claude Profile System.

**Débloque :** onboarding zéro-friction, maîtrise des coûts, résilience automatique face aux agents bloqués.

**Effort :** Moyen | **Impact :** Haut

#### 2. Agent Replay — Sessions partageables & export

**Aujourd'hui :** le replay est strictement local. La session enregistrée (tool calls, diffs, thinking) reste dans le `.workpilot/` du dev et n'est ni partageable, ni versionnable, ni collaborative. Résultat : impossible de dire « regarde comment l'agent a résolu ça » à un coéquipier sans screen share.

**Amélioration proposée :**
- **Export signé** : bouton « Share session » qui produit un bundle `.wpreplay` (JSON structuré compressé) avec URL signée temporaire (TTL 7j par défaut, configurable).
- **Format video** : export MP4/WebM en rendu side-by-side (timeline + diff + thinking) pour demos marketing, stand-ups, issues GitHub.
- **Bookmarks & annotations** : l'utilisateur pose des marqueurs sur un step (`t=2:34 → decision weird`) avec commentaire markdown, discutables en async.
- **Comparaison 2 replays** : pas juste A/B live, mais deux sessions archivées (« comment cette refacto s'est passée en v2 vs v1 ? »).
- **Viewer public minimal** : mini-app web (ou même statique, généré côté electron) qui charge un `.wpreplay` sans WorkPilot installé — utile pour onboarder ou partager à un client.

**Fichiers à toucher :**
- `apps/backend/agents/session_recorder.py` — ajout `export_session(session_id, format)`.
- `apps/frontend/src/main/ipc-handlers/replay-handlers.ts` — IPC pour export + partage.
- `apps/frontend/src/renderer/components/replay/ReplayViewer.tsx` — bookmarks UI, comparison mode.
- `apps/frontend/src/renderer/components/replay/ReplayExportDialog.tsx` — nouveau dialog.
- `apps/frontend/src/shared/types/replay.ts` — types Bookmark, ExportBundle.

**Format `.wpreplay` (proposé) :**
```json
{
  "version": "1.0",
  "sessionId": "...",
  "agent": { "role": "coder", "model": "claude-sonnet-4-6" },
  "events": [{ "t": 0.0, "type": "tool_call", ... }],
  "diffs": [{ "t": 12.3, "file": "...", "patch": "..." }],
  "thinking": [{ "t": 1.2, "text": "..." }],
  "bookmarks": [{ "t": 154.0, "note": "...", "author": "..." }],
  "redacted": true
}
```

**Sécurité & confidentialité :**
- Redaction automatique des secrets (regex `API_KEY`, `Bearer`, chemins absolus du home dir) avant export.
- Option « strip thinking » pour ne partager que les actions (cas enterprise strict).
- URLs signées avec expiration, révocables depuis Settings.

**Métriques :**
- Nombre de sessions exportées / semaine.
- Taux d'ouverture des liens partagés.
- % de replays avec bookmarks (engagement).

**Débloque :** revue async en équipe, onboarding visuel, démos marketing, support client premium (« envoyez-nous le replay, on regarde »).

**Effort :** Moyen | **Impact :** Haut

#### 3. Pixel Office — Gamification & métriques d'équipe

**Aujourd'hui :** Pixel Office est une visualisation esthétique des agents en pixel art. Aucune couche de gamification, pas d'agrégation équipe, pas de contenu long terme qui donne envie de revenir le regarder. Le moteur est là, la matière narrative ne l'est pas.

**Amélioration proposée :**
- **Achievements individuels et équipe** : « First incident fixed autonomously », « 10 specs shipped this week », « Zero flaky tests for 30 days ». Badges affichables dans le profil utilisateur et dans Pixel Office.
- **Saisons** : cycles de 3 mois avec objectifs d'équipe (« réduire la dette technique de X% », « 100 PRs shippées »), récompenses cosmétiques (skins d'agents, décors d'office).
- **Leaderboard** : classement d'équipe par spec terminé, incident résolu, score Self-Healing proactif. Anti-pattern à éviter : ne pas transformer en course individualiste, pondérer pour valoriser l'entraide (reviews, pair programming).
- **Mode kiosque (TV mode)** : URL dédiée optimisée pour affichage sur un grand écran (fullscreen, polices grosses, refresh auto, overlay stats temps réel). Utile pour les équipes en open space / remote daily.
- **Mini-narratifs** : quand un agent finit une tâche, Pixel Office génère une mini-scène narrative (« Coder Claude vient de rendre sa copie à Reviewer Sonnet pour le spec #042 »). Ton léger, immersif.

**Fichiers à toucher :**
- `apps/backend/pixel_office/achievements.py` — nouveau module (règles, évaluation).
- `apps/frontend/src/renderer/stores/pixel-office-store.ts` — ajout state achievements, season.
- `apps/frontend/src/renderer/components/pixel-office/KioskMode.tsx` — nouveau composant fullscreen.
- `apps/frontend/src/renderer/components/pixel-office/AchievementToast.tsx` — notif visuelle.
- i18n : `pixelOffice.json` (achievements names, season labels).

**Risques à surveiller :**
- **Gamification toxique** : si le leaderboard devient le but, les devs gameront (plus de petits specs pour monter, moins de gros chantiers). Pondérer par complexité estimée.
- **Bruit visuel en kiosque** : trop d'animations = fatigue. Prévoir un toggle « calm mode » pour le fond sonore / animations.
- **Vie privée** : opt-out individuel du leaderboard (pas d'affichage public du nom si l'utilisateur refuse).

**Métriques :**
- Engagement : temps moyen passé sur l'onglet Pixel Office / semaine / utilisateur.
- Nombre d'équipes ayant activé le mode kiosque.
- % d'utilisateurs ayant obtenu au moins un achievement.

**Débloque :** argument marketing démontrable (screenshot viral), engagement quotidien des équipes, culture d'équipe positive autour de l'agent.

**Effort :** Moyen | **Impact :** Moyen (fort sur perception produit)

#### 4. Swarm Mode & Continuous AI — Gouvernance & garde-fous

**Aujourd'hui :** Swarm Mode et Continuous AI tournent en exécution libre. Aucune enveloppe de gouvernance : pas de plafond de tokens/h, pas de fenêtre horaire, pas de fichiers en liste rouge, pas de circuit breaker sur boucle infinie. Pour un dev solo c'est acceptable ; pour une équipe ou un déploiement nuit, c'est un non-starter.

**Amélioration proposée :**
- **Policies locales** (complément de la future feature Policy-as-Code décrite plus bas) : fichier `.workpilot/policies.yaml` versionné, chargé au démarrage de Swarm/Continuous.
  - `budget.max_tokens_per_hour: 500000`
  - `budget.max_cost_per_day: 50`
  - `schedule.allowed_hours: ["08:00-19:00 Europe/Paris"]`
  - `files.forbidden: ["**/migrations/**", ".env*", "package-lock.json"]`
  - `files.requires_review: ["infra/**", ".github/workflows/**"]`
  - `loop_detection.max_same_tool_call: 5`
- **Circuit breaker** : si un agent répète le même tool call (même signature) N fois sans progrès mesurable, il est suspendu automatiquement et l'utilisateur est notifié.
- **Kill switch global** : raccourci clavier + bouton UI « Stop all agents » qui termine proprement toutes les sessions en cours (sauvegarde de state pour reprise).
- **Audit trail** : chaque action agent loggée avec `user, timestamp, spec, tool, file, decision` — exportable pour compliance.

**Fichiers à toucher :**
- `apps/backend/core/governance/policy_loader.py` — nouveau.
- `apps/backend/core/governance/circuit_breaker.py` — nouveau (hook via `session recorder`).
- `apps/backend/agents/continuous_ai.py` — intégration enforce avant chaque action.
- `apps/frontend/src/main/ipc-handlers/governance-handlers.ts` — IPC kill switch.
- `apps/frontend/src/renderer/components/settings/GovernancePanel.tsx` — éditeur visuel du fichier policies.
- Schéma JSON pour validation du YAML.

**Cas limites :**
- Policy invalide au démarrage → refuser de lancer Swarm avec message explicite (pas de fallback silencieux).
- Horaire frontière → agent en cours d'action au passage de `19:00` : laisser finir l'action atomique en cours, puis stopper.
- Circuit breaker faux positif sur un agent qui vérifie légitimement 10 fichiers similaires → pondérer la détection par « progrès mesurable » (changement du diff, thinking token count qui évolue).

**Métriques :**
- Nombre de policies violations bloquées / jour.
- Nombre de circuit breaker triggers / semaine.
- Temps moyen entre kill switch et arrêt effectif des agents (doit être < 2s).

**Débloque :** adoption enterprise sereine, déploiement en autonomie 24/7 avec confiance, compliance (SOC2 audit trail natif).

**Effort :** Moyen-Élevé | **Impact :** Très haut pour l'enterprise

---

### B. Qualité, Test & Review

#### 5. Test Generation Agent — Mutation testing
**Aujourd'hui :** génère des tests mais rien ne valide leur *qualité réelle*.
**Amélioration :** intégrer un pass de mutation testing (Stryker/Mutmut) qui mesure si les tests générés détectent vraiment les bugs. Si score faible → l'agent régénère.
**Débloque :** passer de "tests verts" à "tests qui protègent réellement", argument Enterprise majeur.

#### 6. Conflict Predictor — Planification d'exécution
**Aujourd'hui :** prédit les conflits.
**Amélioration :** suggère aussi l'**ordre optimal** d'exécution des specs pour minimiser les conflits cumulés, et regroupe automatiquement les specs compatibles en "waves" exécutables en parallèle sûr.
**Débloque :** gains réels sur le multi-agent parallèle (évite les merges douloureux en fin de sprint).

#### 7. AI Code Review Agent — Apprentissage des faux positifs
**Aujourd'hui :** produit des review comments.
**Amélioration :** tracker quelles suggestions l'utilisateur rejette et pourquoi (via Learning Loop), puis ajuster. Un reviewer qui devient *vraiment* meilleur sur ton repo au fil du temps — pas juste statique.
**Débloque :** réduction drastique du "review fatigue".

#### 8. QA Security Scanner — Contexte runtime
**Aujourd'hui :** scan statique.
**Amélioration :** corréler avec les logs APM (via l'intégration Self-Healing Production déjà branchée à Sentry/Datadog) pour prioriser les vulnérabilités **réellement exposées** vs. dead code.
**Débloque :** sortir du bruit "10 000 CVE" pour ne remonter que celles atteignables en prod.

#### 9. Smart Estimation — Boucle de calibration
**Aujourd'hui :** estimation one-shot.
**Amélioration :** capture `estimé vs réel` sur chaque spec terminé, réinjecté dans le modèle d'estimation (via Learning Loop) avec un score de confiance affiché.
**Débloque :** estimations qui deviennent prédictives pour *votre* équipe, pas génériques.

---

### C. Self-Healing & Production

#### 10. Mode Proactif — Tendances ML sur les métriques
**Aujourd'hui :** score de risque instantané (complexité + churn + couverture).
**Amélioration :** analyser la **trajectoire** sur 90 jours (un fichier qui passe de risque 30 à 70 en 2 semaines est plus alarmant qu'un fichier à risque 70 stable). Afficher des "canaris" temporels.
**Débloque :** alertes early warning avant l'incident.

#### 11. Mode Production — Groupement d'incidents
**Aujourd'hui :** traite les erreurs individuellement.
**Amélioration :** fingerprinting automatique + déduplication cross-source (Sentry + Datadog peuvent remonter la même erreur). Un seul fix pour N alertes corrélées.
**Débloque :** moins de PR de correction redondantes, moins de bruit.

#### 12. Mode CI/CD — Bisect assisté
**Aujourd'hui :** analyse le diff du dernier commit.
**Amélioration :** si la régression vient de plus loin, déclenche automatiquement un `git bisect` piloté par l'agent (relance les tests sur commits intermédiaires).
**Débloque :** regression hunting réellement autonome.

---

### D. Expérience développeur

#### 13. Design-to-Code — Boucle de rendu itérative
**Aujourd'hui :** one-shot design → code.
**Amélioration :** l'agent lance le rendu via App Emulator, prend un screenshot, diffe visuellement avec la target (pixel-diff + embeddings), identifie les écarts et itère jusqu'à convergence (budget de N tours).
**Débloque :** fidélité visuelle réellement élevée au lieu de "ça ressemble à peu près".

#### 14. App Emulator — Presets device & responsive matrix
**Aujourd'hui :** preview d'app.
**Amélioration :** grille de devices (iPhone 15, Pixel, iPad, desktop 4K) simultanée. Capture des screenshots pour chaque breakpoint, détection auto de bugs responsive.
**Débloque :** QA visuel multi-device sans quitter WorkPilot.

#### 15. Voice Control — Streaming & interruption
**Aujourd'hui :** commande vocale basique.
**Amélioration :** mode conversation continue avec détection d'interruption (utilisateur peut stopper l'agent à la voix : "non, arrête, essaie plutôt X").
**Débloque :** vrai pair programming vocal, utile en accessibilité et mobilité.

#### 16. Browser Agent — Recording & rejeu human-to-test
**Aujourd'hui :** automatisation browser par agent.
**Amélioration :** capture les actions manuelles de l'utilisateur dans une session et génère un test E2E Playwright depuis l'interaction. Human-in-the-loop → test automatisé en 1 clic.
**Débloque :** adoption test E2E sans rédaction manuelle.

---

### E. Mémoire & Apprentissage

#### 17. Learning Loop → Spec Creation
**Aujourd'hui :** alimente l'agent coder.
**Amélioration :** injection directe dans le spec_writer : "sur ce repo, les specs Frontend prennent en moyenne 3 itérations QA — le spec writer doit donc être plus précis sur les critères d'acceptation UI dès le départ".
**Débloque :** boucle d'amélioration de bout en bout, pas juste sur le coding.

#### 18. Memory Lifecycle Manager — Explication des décisions
**Aujourd'hui :** gère TTL et éviction.
**Amélioration :** journal human-readable : "cette mémoire a été supprimée car elle était contredite par X commits récents". Bouton "restaurer" et "épingler".
**Débloque :** confiance dans le système de mémoire (pas une boîte noire qui oublie).

#### 19. Team Knowledge Sync — Résolution de conflits
**Aujourd'hui :** synchro basique.
**Amélioration :** détection des mémoires contradictoires entre coéquipiers + arbitrage automatique ou manuel ("Alice dit X, Bob dit Y — quel est le canon ?").
**Débloque :** sain fonctionnement en équipe >3 personnes.

---

### F. Coûts & Analytics

#### 20. Cost Intelligence — Budgets temps réel & circuit breaker
**Aujourd'hui :** rapports post-hoc.
**Amélioration :** budgets live par équipe/projet/spec avec **interruption auto** d'un agent qui explose le budget (avec escalade optionnelle). Dégradation progressive : Opus → Sonnet → Haiku selon consommation.
**Débloque :** contrôle réel des coûts, adoption enterprise.

#### 21. Build Analytics — Comparaisons concurrents normalisées
**Aujourd'hui :** métriques internes.
**Amélioration :** benchmarks anonymisés "votre équipe vs moyenne WorkPilot" (avec opt-in). Médianes globales sur les métriques clés.
**Débloque :** argument marketing ("nos users sont 2.3x plus rapides") + feedback utile pour les équipes.

---

### G. Collaboration & Enterprise

#### 22. Spec Approval Workflow — SSO & RBAC réel
**Aujourd'hui :** approbation simple.
**Amélioration :** intégration Okta/Entra ID, rôles granulaires (Reviewer, Approver, Deployer), délégation, approbations requises N-of-M selon criticité du spec.
**Débloque :** conformité SOC2/ISO sans workarounds.

#### 23. CI/CD Triggers — Rollback intelligent
**Aujourd'hui :** déclenche les pipelines.
**Amélioration :** surveiller les métriques post-déploiement (erreur, latence) et rollback automatique si dégradation détectée, avec escalation au responsable. Canary analysis intégrée.
**Débloque :** confiance dans le "ship from WorkPilot" sans veille manuelle.

#### 24. MCP Marketplace — Scoring sécurité
**Aujourd'hui :** catalogue d'installation.
**Amélioration :** score de sécurité automatique pour chaque MCP (scan du code, vérif des permissions demandées, signature éditeur, communauté). Alertes quand un MCP installé change de mainteneur.
**Débloque :** adoption sereine de MCPs tiers en entreprise (supply chain).

---

## Partie 2 — Nouvelles features proposées

### Tier S — Différenciateurs forts

#### 🧪 1. Agent Simulation Sandbox — Dry run avec mocks hallucinés
**Concept :** avant d'exécuter un spec sur le vrai repo, l'agent le joue dans une **sandbox simulée** où les APIs externes sont mockées par un LLM (hallucinations contrôlées). Permet de détecter rapidement les plans foireux sans coût en tokens réels ni risque sur le worktree.
**Différence avec Agent Replay :** Replay rejoue du passé, Sandbox simule le futur.
**Débloque :** rapidité d'itération sur la planification + safe mode pour juniors.
**Effort :** Élevé | **Impact :** Haut

#### 🛡️ 2. Policy-as-Code for Agents — Garde-fous non-contournables
**Concept :** un fichier `workpilot.policy.yaml` à la racine définit ce que les agents **ne peuvent pas faire** : ne jamais modifier `/migrations`, toujours passer par l'ORM X, jamais supprimer de tests existants, jamais augmenter les dépendances critiques sans review humaine. Appliqué côté hook, donc impossible à bypasser.
**Différence avec l'allowlist de commandes actuelle :** l'allowlist est au niveau commande shell, Policy-as-Code est au niveau **sémantique du diff**.
**Débloque :** adoption enterprise massive (compliance, dette technique maîtrisée, multi-équipe).
**Effort :** Moyen | **Impact :** Très haut

#### 🔴 3. Adversarial QA Agent — Red team automatique
**Concept :** un agent dédié dont l'unique objectif est de **casser** ce qu'un autre agent vient de produire. Il génère des inputs malformés, des edge cases, des attaques prompt injection sur les endpoints IA, teste les race conditions. Chaque spec Tier critique passe par lui.
**Différence avec QA Reviewer :** Reviewer vérifie la conformité, Adversarial **attaque**.
**Débloque :** robustesse réelle, différenciateur face aux concurrents qui ne font que du "happy path testing".
**Effort :** Moyen | **Impact :** Haut

#### 📊 4. Regression Guardian — Tests générés depuis les incidents prod
**Concept :** chaque incident Sentry/Datadog/CloudWatch devient automatiquement un test de régression. L'agent lit la stack trace + les breadcrumbs utilisateur, reproduit l'état, et génère un test qui échoue. Quand le fix passe, le test entre en suite perm.
**Intégration :** branché sur Self-Healing Production (mode prod).
**Débloque :** le "plus jamais deux fois la même erreur" devient automatique.
**Effort :** Moyen | **Impact :** Haut

#### 🗄️ 5. Database Schema Agent — Zéro-downtime migration planner
**Concept :** agent spécialisé pour les changements de schéma. Génère des migrations en **2 étapes** (ajout non-destructif → bascule code → suppression), plans de backfill, estimation de durée sur le volume réel, stratégie de rollback. Détecte les verrous et propose `CREATE INDEX CONCURRENTLY` au lieu de `CREATE INDEX`.
**Différence avec Code Migration :** celui-ci est spécifique DB, sujet à part entière.
**Débloque :** un des angles morts majeurs de tous les outils IA actuels.
**Effort :** Élevé | **Impact :** Très haut

---

### Tier A — Impact élevé

#### 🔐 6. Prompt Injection Guard
Détection en temps réel des tentatives d'injection dans les résultats d'outils (fichiers lus, pages web crawlées, commentaires GitHub). Si un tool result contient une instruction suspecte ("ignore all previous instructions..."), l'agent est alerté via hook et demande confirmation. Essentiel alors que le produit consomme de plus en plus de contenu externe (issues GitHub, Jira, Slack).

#### 🧬 7. API Contract Watcher
Compare les contrats OpenAPI/GraphQL/gRPC/protobuf entre branches, détecte les changements breaking (suppression de champ, changement de type, renommage), alerte les équipes consommatrices et génère un guide de migration auto. Intégration naturelle avec la feature Breaking Change Detector existante, mais au niveau contrat public.

#### ♿ 8. Accessibility Agent
Scan WCAG 2.2 AA/AAA sur les composants React/HTML, suggestions ARIA, corrections auto des erreurs simples (alt manquants, contrastes, focus trap), rapports par page. Briqué sur App Emulator pour tests dynamiques (focus order, screen reader).

#### 🌐 9. i18n Agent (vs. guidelines actuelles)
Il y a déjà des règles i18n dans le CLAUDE.md mais pas d'**agent dédié** qui patrouille : détecte les strings hardcodées, propose des clés de traduction, maintient la parité `en/fr/...`, appelle un service de traduction pour les langues manquantes, flag les clés obsolètes. Particulièrement pertinent vu les 55 namespaces actuels.

#### 🎓 10. Onboarding Agent / Code Storytelling
Quand un nouveau dev arrive, l'agent génère un **tour interactif** du repo : points d'entrée, modules critiques, dette connue, zones à éviter, historique des décisions importantes (piochées dans Graphiti). Se présente comme un tutoriel dans l'IDE, pas un doc statique.

#### 🪲 11. Flaky Test Detective
Détecte, quarantaine et diagnostique les tests flaky. Relance N fois, score de flakiness, analyse de cause (timing, ordre, ressource partagée, setup oublié), propose un fix ou un `@flaky` tag. Réduit le "CI rouge pour rien" qui empoisonne toutes les équipes.

#### 📜 12. Documentation Drift Detector
Scanne les fichiers `.md`/docstrings et détecte quand ils divergent du code (fonctions renommées, params changés, exemples cassés). Propose un sync automatique. Branché sur Doc Agent existant mais côté **audit passif**.

#### 🔑 13. Compliance Evidence Collector (SOC2 / ISO 27001)
Collecte automatique des preuves d'audit à partir des actions agents : qui a approuvé quoi, quels tests sont passés, quel code a été reviewé. Exporte un rapport mensuel conforme. Complément naturel du Spec Approval Workflow pour l'enterprise.

---

### Tier B — Valeur solide

#### 🔀 14. Git History Surgeon
Interactive rebase assisté par IA : squash intelligent ("regroupe ces 7 commits de fix en 1 commit cohérent"), rewrite de messages, split de gros commits, conservation du contexte.

#### 🚂 15. Release Train Coordinator
Coordonne plusieurs releases interdépendantes (mobile + backend + frontend). Ordre de déploiement calculé, gates (ne pas déployer le frontend tant que le backend n'est pas en prod + healthy), feature flags synchronisés.

#### 🌱 16. Carbon / Energy Profiler
Track le coût énergétique/carbone de chaque run d'agent (via datasets publics kWh → tCO₂). Propose des optimisations (cache, modèles plus petits, offloading). Argument ESG pour les grandes entreprises françaises notamment.

#### 🧩 17. Cross-Agent Consensus Arbiter
Quand 2 agents en parallèle produisent des approches divergentes sur un même problème, un arbitre spawnable examine les 2 options et tranche (avec justification). Complément à Arena Mode mais pendant l'exécution, pas en évaluation.

#### 📔 18. Notebook Agent (Jupyter / Polyglot)
Agent spécialisé pour les notebooks (data science, polyglot .NET Interactive). Exécute, valide les outputs, refactor cell → function, détecte les variables fuites. Marché sous-exploité par tous les concurrents.

#### 🗣️ 19. Incremental Spec Refinement
Pendant l'exécution d'un spec, l'utilisateur peut ajouter du feedback en langage naturel qui **raffine le spec in-place** sans arrêter l'agent. Évite les "Stop → relance → perte de contexte".

#### 📈 20. Personal Agent Coach
L'agent apprend ton style personnel (préférences de code, verbosité des commentaires, conventions de nommage) et adapte ses suggestions. Distillé depuis ton historique de diffs acceptés/refusés. Différent du Learning Loop qui est *équipe*, celui-ci est *individu*.

---

## Partie 3 — Priorisation suggérée

Si je devais choisir **5 chantiers** parmi ces 44 pistes pour les 3 prochains mois :

| # | Piste | Type | Pourquoi en priorité |
|---|-------|------|----------------------|
| 1 | **Policy-as-Code for Agents** (nouvelle S) | Nouveau | Déverrouille l'enterprise, effort modéré, sécurise toutes les autres features |
| 2 | **Cost Intelligence — budgets live + circuit breaker** (amélioration F.20) | Amélioration | Coût = friction #1 actuelle, gain immédiat pour tous les users |
| 3 | **Database Schema Agent** (nouvelle S) | Nouveau | Angle mort majeur du marché, différenciateur fort, demande éprouvée |
| 4 | **Design-to-Code — boucle de rendu itérative** (amélioration D.13) | Amélioration | Feature démo spectaculaire, tourne déjà mais qualité à augmenter |
| 5 | **Adversarial QA Agent** (nouvelle S) | Nouveau | Effort moyen, marketing fort ("red team IA"), synergie avec QA existant |

**Logique :** 2 améliorations à haut ROI sur des features existantes (cost, design-to-code) + 3 nouvelles features qui creusent l'écart concurrentiel sur des sujets où personne n'est sérieux aujourd'hui (policies, DB, adversarial).

---

## Annexe — Ce que ce document ne couvre pas volontairement

- **Refactor architectural interne** (ex: passer tel store Zustand à tel pattern) — hors scope, dépend du code réel.
- **Features "me too"** qui existent déjà chez les concurrents sans différenciation (ex: "ajouter un chat générique") — WorkPilot a déjà son Insights.
- **Intégrations verticales spécifiques** (ex: "plugin Shopify") — à traiter au cas par cas selon la demande client.
- **Optimisations perf bas niveau** — mesurer avant de proposer.

Ces points méritent leur propre document si/quand ils deviennent prioritaires.
