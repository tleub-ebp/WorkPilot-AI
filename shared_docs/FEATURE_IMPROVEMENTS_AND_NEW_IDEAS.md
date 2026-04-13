# WorkPilot AI — Améliorations & Nouvelles Pistes

> Document d'analyse complémentaire à [FEATURE_IDEAS.md](FEATURE_IDEAS.md).
> Les 49 features de la roadmap initiale étant implémentées, ce document identifie :
> 1. Les **améliorations concrètes** à apporter aux features existantes (renforcement, polish, intégrations manquantes).
> 2. Les **nouvelles features** qui combleraient les angles morts actuels du produit.
>
> Principe d'écriture : privilégier l'impact utilisateur réel à la nouveauté gadget. Chaque proposition indique *pourquoi maintenant* et *ce qu'elle débloque*.

---

## 🌐 Contrainte transverse — Multi-provider first

**Règle non négociable : toutes les features (améliorations existantes ET nouvelles) doivent fonctionner avec n'importe quel LLM de n'importe quel provider, pas uniquement Anthropic Claude.**

WorkPilot AI supporte déjà nativement : Anthropic, OpenAI, Google (Gemini), xAI (Grok), GitHub Copilot, Ollama (local), ainsi que tout endpoint compatible OpenAI (z.ai pour GLM, Groq, Together, etc.). Cette contrainte s'applique de bout en bout.

### Principes d'implémentation

1. **Abstraction obligatoire** — Toujours passer par `core.client.create_client()` qui encapsule les différences de provider. Jamais appeler un SDK provider-spécifique (`anthropic.Anthropic()`, `openai.OpenAI()`, etc.) en dehors de cette couche.
2. **Capability detection, pas name matching** — Tester ce qu'un modèle peut faire (`supports_vision`, `supports_tool_use`, `supports_thinking`, `max_context_window`) via un registre centralisé, pas via `if model.startswith("claude")`.
3. **Dégradation gracieuse** — Si une feature dépend d'une capability manquante (ex : extended thinking absent sur Haiku ou GPT-4o-mini), fallback documenté et annoncé à l'utilisateur, pas d'erreur silencieuse.
4. **Prompts portables** — Les prompts d'agents sont rédigés en style neutre (pas de « you are Claude »), testés sur au moins Anthropic + OpenAI + Google + Ollama local avant merge.
5. **Format structuré via JSON Schema / tool use** — Ne jamais reposer sur un format de sortie provider-spécifique (ex : Claude XML tags uniquement). Utiliser tool use ou JSON Schema contraint, supporté par tous les providers majeurs.
6. **Coûts normalisés** — La feature Cost Intelligence doit mapper les tarifs de tous les providers vers une unité commune (tokens → USD) à partir d'un catalogue versionné.
7. **Tests cross-provider** — Chaque feature d'agent doit avoir au moins un test d'intégration qui tourne avec un provider non-Anthropic (OpenAI ou Ollama) en CI.

### Checklist par feature

Lors de l'implémentation d'une amélioration ou d'une nouvelle feature, valider :

- [ ] Le code passe par `create_client()` / la couche provider abstraction.
- [ ] Les capabilities requises sont détectées, pas devinées.
- [ ] Le prompt système est neutre, testé sur ≥3 providers.
- [ ] Un chemin de fallback existe pour les modèles qui ne supportent pas la capability.
- [ ] La feature est utilisable avec un modèle Ollama local (validation offline).
- [ ] Le catalogue de coûts couvre le nouveau modèle si applicable.
- [ ] La doc utilisateur mentionne la liste des providers compatibles.

### Conséquence sur les features existantes

Dans les sections ci-dessous, chaque amélioration contient désormais un bloc **« Multi-provider »** qui précise les points d'attention pour l'implémentation dans un contexte non-Anthropic. Les features d'orchestration (Mission Control, Arena, Cost Intelligence) sont naturellement multi-provider par design ; les features reposant sur extended thinking ou long context (1M tokens Claude) doivent expliciter leur fallback sur les autres providers.

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

**Multi-provider :**
- Le session planner (LLM léger qui propose la composition) doit accepter n'importe quel modèle « fast tier » : Haiku, GPT-4o-mini, Gemini Flash, Grok Mini, Llama 3.1 8B via Ollama.
- Les compositions suggérées mixent les providers : `1 archi GPT-4o + 3 coders Sonnet + 1 reviewer Gemini Pro + 1 tester Llama local` est un cas valide et doit être présenté comme tel dans l'UI.
- Le calcul de budget normalise les coûts via le catalogue Cost Intelligence (voir F.20), pas via une tarification Anthropic-only.
- Le registre de capabilities (`supports_tool_use`, `max_context`) est consulté pour filtrer les modèles inappropriés à un rôle donné (ex : refuser un modèle sans tool use comme reviewer).
- Templates validés en CI avec un run contre Ollama local pour garantir l'offline-friendliness.

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

**Multi-provider :**
- Le format `.wpreplay` doit capturer les événements de n'importe quel provider (Anthropic, OpenAI, Google, Grok, Ollama, Copilot) via un schéma d'événements commun — pas de champs Claude-only.
- Le champ `thinking` est optionnel : certains modèles (GPT-4o, Gemini, Ollama) n'exposent pas d'extended thinking ; le viewer affiche « no thinking trace available for this model » sans casser.
- Le rendu côté viewer (fichier → diff → tool call → thinking) doit rester lisible même sans thinking trace, en remplaçant par un récapitulatif textuel généré par un LLM au moment de l'export si souhaité (avec n'importe quel provider).
- Redaction des secrets indépendante du provider : regex universelles + option « strip tokens » pour supprimer les token counts qui pourraient révéler le modèle utilisé.
- Viewer public minimal : zéro dépendance à un SDK provider côté client, juste du JSON rendu.

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

**Multi-provider :**
- Les achievements se basent sur des événements agent normalisés (spec terminé, incident résolu, review passée), pas sur des signaux provider-spécifiques (ex : « Opus streaks »). Ça reste honnête quel que soit le provider utilisé.
- Les sprites d'agents en pixel art sont parametrables par provider : une palette par famille (Anthropic, OpenAI, Google, Ollama, Copilot, Grok, custom). L'utilisateur peut reconnaître visuellement quels providers tournent.
- Le leaderboard pondère par coût normalisé, pas par token count brut — sinon un utilisateur Ollama local (gratuit mais verbeux) ou un utilisateur Haiku serait pénalisé vs. un utilisateur Opus. Pondération via le catalogue Cost Intelligence.
- Les mini-narratifs générés (« Coder vient de rendre sa copie ») sont générés par un LLM léger au choix de l'utilisateur — Haiku, GPT-4o-mini, Gemini Flash ou Ollama local.
- Mode kiosque testé offline avec Ollama pour démo salons / salles de réunion sans réseau.

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

**Multi-provider :**
- Les policies s'appliquent uniformément quel que soit le provider qui exécute l'agent — le check est au niveau du tool call avant délégation au SDK. Aucun contournement possible en changeant de provider.
- Les budgets (tokens/h, cost/day) utilisent le catalogue de coûts normalisé de Cost Intelligence (voir F.20), qui couvre Anthropic, OpenAI, Google, Grok, Copilot, Ollama (coût = 0 + coût énergétique optionnel).
- Le circuit breaker détecte les « boucles infinies » via hash de tool call + diff de state, indépendamment du provider. Un agent Ollama qui boucle est arrêté aussi vite qu'un agent Claude.
- L'audit trail capture `provider + model + version` à chaque action, pour traçabilité post-mortem (« cette erreur vient-elle du modèle GPT-4o ou de Sonnet 4.6 ? »).
- Le kill switch est un signal backend unique propagé à toutes les sessions actives, quel que soit leur provider — routage via `core.client.terminate_all()`.

**Débloque :** adoption enterprise sereine, déploiement en autonomie 24/7 avec confiance, compliance (SOC2 audit trail natif).

**Effort :** Moyen-Élevé | **Impact :** Très haut pour l'enterprise

---

### B. Qualité, Test & Review

#### 5. Test Generation Agent — Mutation testing

**Aujourd'hui :** l'agent génère des tests, ils passent, on coche la case « couverture ajoutée ». Mais rien ne valide que ces tests détectent réellement les régressions. Un test qui ne fait qu'instancier la classe et vérifier qu'elle n'est pas `null` augmente la couverture sans protéger quoi que ce soit. Résultat : des suites de tests volumineuses mais peu utiles.

**Amélioration proposée :**
- **Mutation testing intégré** : après génération, lancer automatiquement un outil de mutation testing adapté au langage :
  - Python : `mutmut` ou `cosmic-ray`
  - JavaScript/TypeScript : `Stryker`
  - Java : `PIT`
  - Go : `go-mutesting`
  - C# : `Stryker.NET`
- **Score minimum configurable** : `mutation_score_threshold: 70%` dans le project config. Si le score est en-dessous, l'agent reçoit la liste des mutants survivants et itère : « mutant X ligne Y a survécu, renforce le test ».
- **Affichage dans le QA report** : section dédiée « Mutation score: 84% — 2 survived mutants detected ». Cliquable pour voir les mutants non tués.
- **Feedback loop avec Learning Loop** : les patterns de mutants survivants sont mémorisés et l'agent apprend à écrire des assertions plus strictes au fil du temps.
- **Budget de mutation** : pour éviter les runs trop longs sur de gros modules, définir un échantillonnage (ex : tester 50 mutants aléatoires au lieu de tous).

**Fichiers à toucher :**
- `apps/backend/qa/mutation_runner.py` — nouveau module avec adaptateurs par langage.
- `apps/backend/agents/test_generator.py` — intégration boucle génération → mutation → régénération.
- `apps/backend/prompts/test_generator_mutation_feedback.md` — nouveau prompt pour l'itération.
- `apps/frontend/src/renderer/components/qa/MutationReport.tsx` — affichage des résultats.
- `apps/frontend/src/shared/types/mutation.ts` — types Mutant, MutationReport.

**Edge cases :**
- Tests non déterministes (flaky) qui font échouer le mutation runner → marquer et exclure de l'analyse.
- Code avec side effects qui rend la mutation trop coûteuse → budget time-boxed + échantillonnage.
- Langage non supporté → fallback sur métrique simple (branch coverage + assertion count).

**Métriques :**
- Mutation score moyen des specs générés avant / après la feature.
- Nombre d'itérations moyennes pour atteindre le seuil.
- Nombre de régressions prod évitées grâce à des tests renforcés (à mesurer post-hoc).

**Multi-provider :**
- L'agent générateur de tests tourne avec n'importe quel modèle capable de tool use : Claude Sonnet, GPT-4o, Gemini 1.5/2.5 Pro, Grok, Llama 3.3 via Ollama, Qwen Coder, DeepSeek Coder.
- Les outils de mutation (Stryker, mutmut, PIT, etc.) sont 100% provider-agnostic — ils tournent sur le code, pas sur le LLM. La boucle « génère → mute → régénère » est identique quel que soit le provider.
- Le prompt de feedback mutation (« mutant survived at line X ») est rédigé sans vocabulaire Claude-specific, testé sur ≥3 providers.
- Si un modèle a un context window limité (ex : 32k), le prompt de feedback exclut les tests non pertinents et ne passe que le contexte minimal — adaptation via `get_phase_thinking_budget()` et capability detection.
- Mode Ollama local : mutation testing + génération tourne entièrement offline, critique pour les repos air-gap.

**Débloque :** passer de « tests verts » à « tests qui protègent vraiment », argument Enterprise majeur pour convaincre les équipes QA et les responsables compliance.

**Effort :** Moyen | **Impact :** Très haut

#### 6. Conflict Predictor — Planification d'exécution & waves

**Aujourd'hui :** le Conflict Predictor détecte les conflits potentiels entre deux branches ou deux specs en cours. C'est réactif : on sait qu'il va y avoir un conflit, mais on doit gérer manuellement l'ordre. Sur un sprint avec 15 specs en parallèle, ça reste un casse-tête.

**Amélioration proposée :**
- **Graphe de dépendances des specs** : pour chaque paire de specs, calculer un score de conflit prédit (fichiers communs, symboles renommés, imports croisés, zones fragiles).
- **Topological ordering** : proposer un ordre optimal qui minimise les conflits cumulés (algo type « minimum feedback arc set » approché).
- **Waves auto-groupées** : identifier les clusters de specs indépendants exécutables en parallèle sans risque. Ex : Wave 1 = [spec 1, 4, 7] (aucun fichier commun), Wave 2 = [2, 5], etc. Afficher un Gantt prévisionnel.
- **Replanification dynamique** : si un spec dérape (touche plus de fichiers que prévu), le planner recalcule les waves à la volée.
- **Intégration Mission Control** : un bouton « Execute in optimal order » qui lance automatiquement les agents dans les bonnes waves avec le bon niveau de parallélisme.

**Fichiers à toucher :**
- `apps/backend/conflict_predictor/planner.py` — nouveau (algo de planification).
- `apps/backend/conflict_predictor/conflict_scorer.py` — extraction du score par paire.
- `apps/frontend/src/renderer/components/conflict-predictor/WavesView.tsx` — Gantt + waves.
- `apps/backend/mission_control/orchestrator.py` — API `schedule_waves(spec_ids)`.
- i18n : `conflictPredictor.json` (labels waves, actions).

**Edge cases :**
- Cycle de dépendances (spec A dépend de B qui dépend de A) → détecter et afficher un warning, pas de planification possible sans intervention humaine.
- Sur-estimation des conflits (deux specs touchent le même fichier mais à des endroits disjoints) → tolérance configurable + option « merge préventif pour vérif ».
- Spec qui grossit en cours d'exécution → seuil de replanification (« le spec 3 a touché 5 fichiers de plus, voulez-vous replanifier ? »).

**Métriques :**
- Nombre de conflits de merge évités / sprint.
- Temps de résolution moyen des conflits résiduels.
- Gain de temps sur la durée totale du sprint grâce au parallélisme.

**Multi-provider :**
- Le scoring et le graphe sont purement statiques (AST + diff), zéro LLM — donc 100% provider-indépendant et gratuit.
- Si une couche LLM est ajoutée pour scorer la *sémantique* du conflit (ex : « les deux specs modifient la même classe mais pour des raisons orthogonales »), elle utilise un modèle léger au choix (Haiku, GPT-4o-mini, Gemini Flash, Ollama).
- L'orchestrateur de waves lance les agents avec leurs providers respectifs : wave 1 peut mixer 3 agents Anthropic + 1 agent OpenAI + 1 agent Ollama sans problème.
- Le calcul du score de conflit est déterministe et reproductible, quel que soit l'environnement — utile pour la CI cross-provider.

**Débloque :** vrais gains sur le multi-agent parallèle (évite les merges douloureux en fin de sprint), confiance sur le scaling > 5 agents simultanés.

**Effort :** Moyen | **Impact :** Haut

#### 7. AI Code Review Agent — Apprentissage des faux positifs

**Aujourd'hui :** l'agent produit des commentaires de review pertinents mais statiques. Il ne sait pas quelles suggestions l'utilisateur a rejetées par le passé, il n'apprend pas les conventions propres au repo, et il répète les mêmes remarques à chaque PR. Résultat : « review fatigue » — les devs finissent par scroller sans lire.

**Amélioration proposée :**
- **Feedback capture** : chaque commentaire de review a 3 boutons `Accept / Reject / Not applicable`. Ces signaux alimentent un dataset local `.workpilot/code_review_feedback.jsonl`.
- **Rejection reasons** : optionnel mais fortement encouragé — dropdown avec raisons prédéfinies (`too pedantic`, `project convention differs`, `false positive on AST`, `legacy code exception`, `custom reason`).
- **Learning Loop intégration** : après N rejections d'un même pattern, le reviewer apprend à ne plus le signaler ou à pondérer son niveau de confiance. Les règles apprises sont stockées dans Graphiti (mémoire) et rechargées à chaque run.
- **Project conventions file** : génération assistée d'un `.workpilot/review-conventions.md` qui agrège les règles tacites du repo (« jamais de `any` en TS », « toujours Optional en Python », « classes avant fonctions »).
- **Confidence scoring** : chaque commentaire a un niveau de confiance affiché (🔴 high, 🟡 medium, 🟢 nitpick), trié par sévérité pour éviter la noyade.
- **Self-critique pass** : avant de poster, le reviewer relit ses propres commentaires et supprime ceux contradictoires ou redondants.

**Fichiers à toucher :**
- `apps/backend/qa/review_feedback_store.py` — persistance du dataset.
- `apps/backend/qa/review_learning.py` — boucle d'apprentissage.
- `apps/backend/prompts/qa_reviewer.md` — ajouter instructions sur les conventions chargées.
- `apps/frontend/src/renderer/components/github/ReviewCommentActions.tsx` — boutons feedback.
- `apps/frontend/src/shared/types/code-review.ts` — types pour le feedback.
- `integrations/graphiti/review_memory.py` — stockage des règles apprises.

**Edge cases :**
- Reviewer qui désapprend trop (tout rejeté, finit par ne plus rien remonter) → seuil minimum de règles protégées (sécurité, perf critique).
- Nouveau contributeur qui rejette sans comprendre → notification du maintainer pour review des rejections avant intégration au dataset.
- Changement de convention au milieu d'un projet → reset manuel ou dataset versionné par période.

**Métriques :**
- Taux d'acceptation des commentaires du reviewer (viser >60%).
- Nombre de commentaires par PR (tendance à la baisse sur les repos matures).
- Nombre de « règles apprises » capitalisées par repo / mois.

**Multi-provider :**
- Le reviewer tourne avec tout provider supportant le tool use + long context (pour lire des PRs complètes) : Sonnet, GPT-4o/4.1, Gemini 1.5/2.5 Pro, Grok Code, Qwen 2.5 Coder, Llama 3.3 via Ollama.
- Le prompt `qa_reviewer.md` est rédigé en style neutre, sans références au vocabulaire Claude (`<thinking>`, `<result>`). Format de sortie imposé via tool use JSON Schema, supporté partout.
- Le dataset de feedback est indépendant du modèle qui l'a produit — un commentaire rejeté l'est pour tout le monde, pas seulement pour Claude. L'utilisateur peut switcher de provider sans perdre son apprentissage.
- Les règles apprises stockées dans Graphiti sont des règles en langage naturel, ré-injectables dans n'importe quel prompt provider.
- Fallback offline : reviewer Ollama local sur les PRs sensibles (code confidentiel), avec la même qualité d'apprentissage.

**Débloque :** réduction drastique de la review fatigue, un reviewer qui devient réellement meilleur sur ton repo au fil du temps, capitalisation des conventions tacites.

**Effort :** Moyen | **Impact :** Haut

#### 8. QA Security Scanner — Contexte runtime & atteignabilité

**Aujourd'hui :** le scanner remonte toutes les vulnérabilités statiques trouvées (CVE dans deps, patterns OWASP, secrets hardcodés, injection SQL potentielle). Problème : sur un gros repo, ça produit des centaines d'alertes dont 80% concernent du dead code, du code non exposé en prod, ou des chemins non atteignables. Les équipes sécurité apprennent vite à ignorer le rapport.

**Amélioration proposée :**
- **Corrélation avec APM** : via les intégrations Self-Healing Production (Sentry, Datadog, CloudWatch, New Relic), croiser chaque vulnérabilité avec les endpoints réellement touchés en prod dans les 30 derniers jours. Priorité = `(severity × exposure × reach)`.
- **Reachability analysis** : à partir des points d'entrée (routes HTTP, handlers d'événements, CLI), calculer un graphe d'atteignabilité statique. Une fonction vulnérable jamais appelée est dégradée en « informational ».
- **Score combiné** : `priority = base_cvss × reach_factor × runtime_hit_factor`. Affichage trié par score décroissant.
- **Sections du rapport** :
  1. 🔴 **Critical & exposed** : CVE critique dans du code atteint en prod cette semaine.
  2. 🟠 **Critical but dormant** : CVE critique mais code non exécuté en prod (à surveiller).
  3. 🟡 **Medium** : tout le reste trié.
  4. 🟢 **Informational** : dead code, legacy non exposé.
- **Traçage user-facing** : si la vulnérabilité touche un endpoint utilisé par N users (stat PAM), le report affiche cet impact.
- **Auto-PR pour les critical & exposed** : intégration avec Self-Healing pour générer automatiquement une PR de fix quand le score dépasse un seuil.

**Fichiers à toucher :**
- `apps/backend/qa/security/reachability.py` — nouveau module d'analyse statique.
- `apps/backend/qa/security/apm_correlator.py` — consomme les APIs Sentry/DD/CW.
- `apps/backend/qa/security/priority_scorer.py` — calcul combiné.
- `apps/backend/qa/security/scanner.py` — refactor pour intégrer les nouveaux scores.
- `apps/frontend/src/renderer/components/qa/SecurityReport.tsx` — vue segmentée.
- `apps/frontend/src/shared/types/security.ts` — types Finding, PriorityScore.

**Edge cases :**
- APM non configuré → fallback sur reachability seule + message explicite « corrélation APM désactivée, branchez Sentry pour plus de pertinence ».
- Vulnérabilité dans une lib transitive → remonter quand même avec un tag « transitive » car exploitable indirectement.
- Code généré au runtime (reflection, codegen) qui fausse la reachability statique → flag « dynamic code detected, reachability uncertain ».

**Métriques :**
- Nombre d'alertes `Critical & exposed` trouvées / scan (doit être bas mais utile).
- Ratio bruit / signal avant et après la feature (objectif : diviser par 5 minimum).
- Taux de fix dans les 48h des alertes top-priority.

**Multi-provider :**
- Le scan statique et la reachability analysis sont purement algorithmiques (AST, graphe d'appels, pattern matching), zéro LLM — 100% provider-indépendants.
- Le LLM intervient pour l'explication pédagogique des findings (« cette injection SQL est due à... ») et pour la génération du fix auto-PR — modèle au choix de l'utilisateur, pas de dépendance à un provider particulier.
- La corrélation APM consomme des APIs REST (Sentry, Datadog, etc.) — également LLM-free.
- L'agent de génération de fix utilise `create_client()` avec le provider configuré ; un Llama 3.3 via Ollama peut générer les fixs sur un repo air-gap sans problème, avec le même pipeline de priorisation.
- Le prompt de génération de fix de sécurité est volontairement court et structuré via tool use, pour maximiser la portabilité cross-provider.

**Débloque :** sortir du bruit « 10 000 CVE », faire réellement vivre le rapport sécurité, crédibilité auprès des équipes sécu et RSSI, argument SOC2 / ISO 27001.

**Effort :** Élevé | **Impact :** Très haut pour l'enterprise

#### 9. Smart Estimation — Boucle de calibration

**Aujourd'hui :** Smart Estimation produit un score de complexité et un effort estimé one-shot à partir du spec et du repo. Mais il n'apprend pas. Sur un repo avec ses particularités (architecture legacy, conventions non standard, tests lents, CI capricieuse), l'estimation initiale est souvent à côté. Et l'utilisateur n'a aucun moyen de dire au système « sur ce repo, multiplie par 1.5 ».

**Amélioration proposée :**
- **Capture actual vs estimated** : à la fin de chaque spec, enregistrer automatiquement `estimated_complexity, estimated_tokens, estimated_files_touched` et comparer aux valeurs réelles (`actual_tokens`, `actual_files`, `actual_duration_wall_clock`, `qa_iterations`).
- **Modèle de calibration par repo** : régression simple (Ridge ou modèle bayésien léger) qui apprend un facteur de correction par repo + par catégorie de spec (frontend, backend, infra, bug fix, feature).
- **Confidence interval** : au lieu d'un chiffre unique, afficher une fourchette `5-8 hours (confidence 72%)`. La confiance augmente au fur et à mesure que le dataset grossit.
- **Breakdown par dimension** : afficher séparément `complexité algorithmique` / `complexité intégration` / `risque de conflit` / `effort tests`. L'utilisateur voit où l'estimation est incertaine.
- **Recalibration manuelle** : bouton « Adjust estimate » où l'utilisateur peut saisir son propre chiffre ; le différentiel est stocké et pris en compte.
- **Red flags explicites** : « cette spec touche des zones fragiles du repo (score Self-Healing 82) — multiplicateur ×1.4 appliqué ».

**Fichiers à toucher :**
- `apps/backend/spec/estimator.py` — refactor pour accepter un modèle de calibration.
- `apps/backend/spec/calibration.py` — nouveau (persistence + fit du modèle).
- `apps/backend/spec/estimate_capture.py` — hook en fin de spec pour enregistrer actuals.
- `apps/frontend/src/renderer/components/spec/EstimationBreakdown.tsx` — UI fourchette + breakdown.
- `apps/frontend/src/shared/types/estimation.ts` — types.

**Edge cases :**
- Dataset trop petit (repo neuf) → fallback sur l'estimation générique + warning « pas assez d'historique pour calibrer ».
- Spec annulé en cours → ne pas alimenter le dataset (biais).
- Changement majeur de contexte (refonte archi) → option « reset calibration » manuel.
- Outliers (un spec qui a explosé à cause d'un incident externe) → détection IQR et exclusion automatique.

**Métriques :**
- MAPE (Mean Absolute Percentage Error) de l'estimation par repo, dans le temps.
- Taux d'acceptation de l'estimation par l'utilisateur (ajustements manuels rares = bon signe).
- Intervalle de confiance moyen (rétrécit avec le temps = bon signe).

**Multi-provider :**
- Le modèle de calibration est un simple régresseur ML local (scikit-learn ou statsmodels), aucun LLM impliqué — 100% provider-agnostique.
- L'analyse initiale du spec (qui alimente l'estimation base) utilise un LLM, au choix du provider. Haiku / GPT-4o-mini / Gemini Flash / Llama 8B suffisent — pas besoin d'un flagship.
- Les features extraites du spec (nombre de fichiers, mots-clés, domaines) sont produites par un prompt court et portable, testé sur ≥3 providers.
- Les actuals capturés sont indépendants du provider qui a exécuté le spec — un spec exécuté en Sonnet et un autre en GPT-4o alimentent le même dataset de calibration.
- L'intervalle de confiance tient compte du provider utilisé (« sur ce repo, Claude Sonnet est 15% plus rapide que GPT-4o en moyenne ») — statistique utile pour choisir le provider des specs futurs.

**Débloque :** estimations qui deviennent réellement prédictives pour *votre* équipe, pas des chiffres génériques. Confiance dans la planification de sprints.

**Effort :** Moyen | **Impact :** Moyen-Haut

---

### C. Self-Healing & Production

#### 10. Self-Healing Mode Proactif — Tendances ML sur les métriques

**Aujourd'hui :** le mode Proactif calcule un score de risque instantané à partir de trois métriques (complexité cyclomatique, churn git, couverture de tests). C'est une photo : `fichier X a un risque de 72 aujourd'hui`. Mais un fichier à risque 72 stable depuis 6 mois est moins inquiétant qu'un fichier qui est passé de 35 à 68 en 3 semaines — pourtant les deux apparaissent identiques.

**Amélioration proposée :**
- **Historisation** : snapshot hebdomadaire des scores par fichier, stocké dans `.workpilot/health_history.sqlite`.
- **Analyse de trajectoire** : pour chaque fichier, calculer la dérivée et l'accélération du score de risque. Classer en 4 catégories :
  - 🟢 Stable (bas ou haut, peu de variation).
  - 📈 Dégradation lente (pente positive modérée).
  - 🔥 Dégradation rapide (pente forte, risque d'incident imminent).
  - ✅ Amélioration (le refactor paye).
- **Canaris visuels** : sur l'onglet Self-Healing, une vue « hot list » des fichiers en dégradation rapide, avec courbe 90 jours.
- **Alertes proactives** : notification quand un fichier entre en 🔥. Option « générer un spec de refacto préventif » qui alimente la Roadmap.
- **Corrélation multi-fichiers** : détecter les clusters de fichiers qui se dégradent ensemble (signe d'un module entier en train de pourrir).
- **Explications LLM** : « ce fichier se dégrade parce que sa complexité a augmenté de 40% suite aux 5 derniers commits, dont 3 incluent le mot-clé 'fix' ». Factuel, pas spéculatif.

**Fichiers à toucher :**
- `apps/backend/self_healing/proactive/history_store.py` — nouveau (SQLite snapshots).
- `apps/backend/self_healing/proactive/trajectory_analyzer.py` — nouveau (analyse temporelle).
- `apps/backend/self_healing/proactive/cluster_detector.py` — co-dégradation.
- `apps/frontend/src/renderer/components/self-healing/ProactiveHotlist.tsx` — UI canaris.
- `apps/frontend/src/renderer/components/self-healing/RiskTrajectoryChart.tsx` — sparkline par fichier.
- Runner standalone : `runners/self_healing_runner.py proactive --trajectory`.

**Edge cases :**
- Fichier récemment créé (pas d'historique) → classé « neutre » jusqu'à 4 snapshots.
- Fichier refactorisé massivement (reset du churn) → détection et exclusion temporaire.
- Projet qui a migré de repo → seed initial avec l'historique git import.

**Métriques :**
- Nombre d'incidents prod précédés d'une alerte 🔥 dans les 14 jours précédents (taux de prédiction).
- Temps moyen entre alerte 🔥 et résolution (refacto préventif ou incident).
- Taux de faux positifs (🔥 sans incident dans les 30 jours).

**Multi-provider :**
- L'historisation, le calcul de trajectoire, la détection de clusters sont 100% déterministes et locaux — zéro LLM, zéro dépendance réseau, tournent sur n'importe quel repo y compris air-gap.
- L'explication en langage naturel (« ce fichier se dégrade parce que... ») est produite par un LLM au choix : Haiku / GPT-4o-mini / Gemini Flash / Qwen / Llama via Ollama. C'est une feature cosmétique, désactivable.
- Le prompt d'explication est court (< 500 tokens), testé sur ≥3 providers, sortie JSON contrainte via tool use.
- La génération du spec de refacto préventif (si l'utilisateur clique « créer une tâche ») passe par le pipeline spec_writer standard, qui est déjà multi-provider.
- Mode 100% offline possible avec Ollama pour toute la chaîne, utile pour les repos confidentiels.

**Débloque :** alertes early warning avant l'incident, passage d'un self-healing réactif à *prédictif*, ROI démontrable (« 12 incidents évités ce trimestre grâce aux refactos proactifs »).

**Effort :** Moyen | **Impact :** Haut

#### 11. Self-Healing Mode Production — Groupement d'incidents & dédup

**Aujourd'hui :** chaque erreur détectée en prod déclenche un traitement individuel. Problème : un même bug remonte souvent via Sentry (stack trace) + Datadog (logs) + PagerDuty (alerte) + New Relic (APM). L'agent ouvre parfois plusieurs PRs pour la même cause racine, ou passe du temps sur des erreurs qui sont en réalité des symptômes d'une seule régression.

**Amélioration proposée :**
- **Fingerprinting unifié** : pour chaque incident reçu, calculer une empreinte stable à partir de `(type d'erreur, fichier, numéro de ligne, signature de fonction, version du service)`. Les erreurs partageant la même empreinte sont regroupées.
- **Dédup cross-source** : table de correspondance `(source_externe → fingerprint interne)`. Quand Sentry remonte un `TypeError at line 42` et Datadog un log similaire, ils sont fusionnés en un seul incident WorkPilot.
- **Incident root cause clustering** : pour un même service, détecter les incidents co-occurrents qui partagent un commit parent suspect. Un seul fix couvre tous les incidents du cluster.
- **Priority inheritance** : un incident qui est un symptôme hérite de la sévérité de sa cause racine. Corrélativement, si un cluster touche 50 incidents, le fix est top priority même si individuellement chaque incident est moyen.
- **Occurrence counter** : chaque incident conserve le nombre d'occurrences et de users impactés (tiré des APM) pour le tri par impact réel.
- **Auto-correlation avec les commits** : l'incident est automatiquement corrélé avec les commits récents qui touchent la zone d'erreur, triés par probabilité de cause.

**Fichiers à toucher :**
- `apps/backend/self_healing/production/fingerprint.py` — nouveau.
- `apps/backend/self_healing/production/incident_deduper.py` — nouveau, consomme Sentry/DD/CW/NR/PD.
- `apps/backend/self_healing/production/cluster_analyzer.py` — root cause clustering.
- `apps/backend/self_healing/production/responder.py` — refactor pour fix par cluster.
- `apps/frontend/src/renderer/components/self-healing/IncidentCluster.tsx` — vue cluster avec liste d'incidents fusionnés.
- `apps/frontend/src/shared/types/incident.ts` — ajout `fingerprint`, `clusterId`, `sources`.

**Edge cases :**
- Deux incidents qui *ont l'air* identiques mais sont sur deux versions différentes → fingerprint inclut la version du service.
- Erreur polymorphe (même endroit, messages différents selon l'input) → seuil de similarité + option de fusion manuelle.
- Incidents d'une même famille mais traités par des équipes différentes → tagging par owner pour ne pas écraser les responsabilités.
- Source externe qui change de format → couche d'adaptation versionnée.

**Métriques :**
- Ratio incidents bruts / incidents dédupliqués (objectif : réduire de 50%+).
- Nombre de PRs de correction par incident-source (objectif : 1 PR pour N alertes).
- Taux de fix groupés qui résolvent effectivement tous les incidents du cluster.

**Multi-provider :**
- Le fingerprinting, la dédup et le clustering sont 100% algorithmiques (hashing, graph analysis), zéro LLM — provider-indépendant par construction.
- Les intégrations APM (Sentry, Datadog, CloudWatch, New Relic, PagerDuty) passent par leurs APIs officielles, pas par des SDKs provider-spécifiques.
- Le LLM intervient uniquement pour (1) la root cause analysis textuelle de l'incident (résumé de la stack trace) et (2) la génération du fix — dans les deux cas via `create_client()` avec le provider configuré par l'utilisateur.
- Le prompt de root cause analysis est court et rédigé en style neutre, testé sur Claude / GPT-4o / Gemini / Ollama local.
- Un incident critique peut être traité par un modèle flagship (Opus, GPT-4.1, Gemini 2.5 Pro) et un mineur par un fast model — mix configurable par criticité.
- Mode Ollama disponible pour les équipes ayant des logs avec PII qui ne doivent pas quitter le réseau privé.

**Débloque :** moins de PRs redondantes, focus sur les incidents qui comptent vraiment, confiance dans le système qui ne « s'affole » plus sur chaque alerte, adoption par les équipes SRE.

**Effort :** Élevé | **Impact :** Haut

#### 12. Self-Healing Mode CI/CD — Bisect assisté par agent

**Aujourd'hui :** quand la CI échoue, l'agent analyse le diff du *dernier* commit et tente un fix. Si la régression a été introduite 12 commits plus tôt et n'est révélée que maintenant (test écrit récemment, condition race découverte plus tard, deps mise à jour), l'analyse part dans le mauvais sens et produit des PRs qui manquent la cause réelle.

**Amélioration proposée :**
- **Bisect triggers intelligents** : si l'agent détecte une des conditions suivantes, il active automatiquement le mode bisect :
  1. Le diff du dernier commit est trivial (< 10 lignes, docstrings, imports) mais casse un test majeur.
  2. Le test qui casse est ancien (pas modifié depuis > 30 jours) → la régression vient probablement d'ailleurs.
  3. Un commit précédent a modifié une dépendance transitive du test.
  4. Le pattern de l'erreur (stack trace, message) apparaît pour la première fois dans l'historique récent.
- **Bisect agent-driven** : pas un `git bisect` shell classique — un agent qui, à chaque étape, choisit intelligemment le prochain commit à tester (pas forcément binaire : si les 3 derniers commits touchent la zone, prioriser ces 3 d'abord). L'agent peut aussi vérifier partiellement (skip builds lourds si un flag évident est là).
- **Cache des résultats bisect** : éviter de re-bisecter deux fois la même régression si elle touche plusieurs tests.
- **Budget bisect** : max N commits testés, max Y minutes, max Z dollars de coûts. Au-delà → fallback sur fix sur le HEAD avec warning.
- **Rapport post-bisect** : commit coupable identifié + lien PR/auteur + analyse de la raison + fix ou revert proposé.

**Fichiers à toucher :**
- `apps/backend/self_healing/cicd/bisect_agent.py` — nouveau, orchestration bisect.
- `apps/backend/self_healing/cicd/bisect_strategy.py` — stratégies (binaire classique, priorité par zone, hybrid).
- `apps/backend/self_healing/cicd/cache.py` — cache des résultats de build par commit SHA.
- `apps/backend/self_healing/cicd/analyzer.py` — ajout de l'heuristique de déclenchement.
- `apps/frontend/src/renderer/components/self-healing/BisectProgress.tsx` — UI live (commit en cours de test, progression).
- `apps/frontend/src/shared/types/bisect.ts` — types.

**Edge cases :**
- Test flaky qui passe un coup sur deux → le bisect se perd. Prérequis : détecter la flakiness (3 runs) avant de lancer le bisect sur un test suspect.
- Historique rebase/squash qui perd des commits intermédiaires → détecter et fallback.
- Grosse matrice CI (tests qui prennent 45 min par commit) → autoriser un bisect « shallow » qui ne relance que le test cassé, pas toute la suite.
- Régression due à une dep mise à jour, pas à un commit interne → détecter via lockfile diff et traiter séparément.

**Métriques :**
- % de régressions où le bon commit coupable est identifié (vérifiable a posteriori).
- Temps moyen du bisect (objectif : < 15 min sur 20 commits).
- Taux de fix mergé issu du bisect.

**Multi-provider :**
- L'orchestration du bisect est purement logique (git, runner de tests, cache), zéro LLM pour la mécanique de base.
- Le LLM intervient pour (1) la décision « faut-il bisect ou pas ? », (2) le choix du prochain commit à tester quand il y a ambiguïté, (3) l'analyse du diff coupable et la génération du fix. Les 3 étapes utilisent `create_client()` avec le provider configuré.
- Les prompts sont courts, orientés décision (JSON Schema via tool use), testés sur Claude / GPT-4o / Gemini / Ollama.
- Un bisect peut être mené avec un fast model (Haiku, GPT-4o-mini, Llama 8B) pour les décisions simples et escalader vers un flagship uniquement pour la génération du fix final — économie substantielle.
- Mode Ollama fonctionnel pour les repos dont le code source ne peut pas sortir.

**Débloque :** regression hunting réellement autonome, capacité à traiter les régressions à latence longue (celles qui n'apparaissent qu'au run CI nocturne après 5 PRs dans la journée).

**Effort :** Moyen-Élevé | **Impact :** Haut

---

### D. Expérience développeur

#### 13. Design-to-Code — Boucle de rendu itérative avec auto-correction

**Aujourd'hui :** la pipeline Design-to-Code génère du code React/HTML en one-shot à partir d'un screenshot ou d'un lien Figma. Le résultat est « à peu près bon » mais avec des écarts visibles : mauvais gap, couleur approchée, padding décalé, typo légèrement différente. L'utilisateur doit corriger manuellement, ce qui tue une partie de la valeur.

**Amélioration proposée :**
- **Boucle render → diff → correct** :
  1. L'agent génère la première version du code.
  2. Il lance le rendu via App Emulator (ou headless Chrome via Chrome DevTools MCP).
  3. Il prend un screenshot aux mêmes dimensions que la target.
  4. Comparaison visuelle : **pixel diff** (tolerance colorimétrique + structural SSIM) + **semantic diff** via embeddings visuels (CLIP ou équivalent) sur des régions.
  5. L'agent reçoit un feedback structuré : « header padding-top 12px au lieu de 20px », « le bouton CTA est orange mais devrait être rouge `#e63946` », « la grille est 3 colonnes au lieu de 4 en desktop ».
  6. Itération jusqu'à convergence (score de diff < seuil) ou budget épuisé.
- **Breakdown par région** : découpage en zones (header, hero, content, footer) et itération ciblée au lieu de régénérer tout.
- **Responsive pass** : répéter la boucle sur 3 breakpoints (mobile, tablet, desktop) et détecter les régressions d'un breakpoint à l'autre.
- **Budget visuel** : max 5 itérations, max $X en tokens. Si non convergé, rapport final avec les écarts résiduels.
- **Diff UI** : panneau side-by-side target / rendu / diff map coloré + liste des écarts avec statut (résolu, en cours, abandonné).

**Fichiers à toucher :**
- `apps/backend/design_to_code/render_loop.py` — nouveau (orchestration boucle).
- `apps/backend/design_to_code/visual_diff.py` — pixel diff + SSIM + régions.
- `apps/backend/design_to_code/semantic_diff.py` — embeddings visuels.
- `apps/backend/prompts/design_to_code_iteration.md` — prompt de feedback pour corrections ciblées.
- `apps/frontend/src/renderer/components/design-to-code/IterationPanel.tsx` — UI progression + diff.
- Intégration App Emulator : hook pour screenshots automatiques.

**Edge cases :**
- Contenu dynamique (dates, données random) qui crée du bruit dans le diff → masque des zones dynamiques avant comparaison.
- Fonts non installées dans l'env de rendu → warning + fallback.
- Target elle-même basse qualité (artefacts de compression JPEG) → seuil de tolérance adaptatif.
- Composants utilisant du state (hover, active) non capturés dans le screenshot statique → option de capture multi-state.

**Métriques :**
- Score de diff moyen après convergence (viser < 5% pixel diff).
- Nombre d'itérations moyennes pour converger.
- Taux de specs Design-to-Code acceptés sans retouche humaine.

**Multi-provider :**
- La boucle visuelle requiert un modèle **vision-capable**. Providers compatibles : Claude (3.5+/4+/4.6), GPT-4o/4.1, Gemini 1.5/2.5 Pro, Llama 3.2 Vision, Qwen 2.5 VL, Pixtral via Ollama.
- Le registre de capabilities filtre automatiquement les modèles sans vision (`supports_vision: false`) — ex : Haiku 3, GPT-3.5, Llama text-only. Si l'utilisateur tente, message explicite.
- Le prompt de correction est neutre (« the button padding is 12px but should be 20px »), testé sur ≥3 providers vision. Format de sortie JSON imposé via tool use.
- Le pixel diff et le SSIM sont algorithmiques (OpenCV, scikit-image), 100% provider-indépendants. Les embeddings visuels utilisent un modèle open source (CLIP) ou un endpoint embedding du provider de l'utilisateur.
- Mode offline via Ollama + Llama Vision pour les maquettes confidentielles.
- Un design-to-code peut combiner un modèle vision pour l'analyse (GPT-4o) et un modèle text pour la génération de code (Claude Sonnet 4.6) si cela améliore le ratio qualité/coût — orchestration possible dans Mission Control.

**Débloque :** fidélité visuelle réellement élevée, demo spectaculaire, adoption par les designers, réduction drastique du temps de front.

**Effort :** Élevé | **Impact :** Très haut (wow effect + productivité)

#### 14. App Emulator — Presets device & matrix responsive

**Aujourd'hui :** App Emulator permet de prévisualiser une app dans une iframe unique, taille fixe. Tester le responsive impose de redimensionner à la main et on oublie des breakpoints. Pas de screenshot automatique, pas de détection de bug responsive, pas de vue « toutes les tailles en même temps ».

**Amélioration proposée :**
- **Bibliothèque de devices** : presets prêts à l'emploi — iPhone 15 / 15 Pro Max, Pixel 8 / 9, iPad Mini / Pro, Galaxy Fold, desktop 1920x1080, desktop 4K, TV 16:9. Chaque preset = (viewport, pixel ratio, user agent, orientation).
- **Mode matrix** : grille 2×N affichant simultanément le même rendu sur N devices choisis, avec navigation synchronisée (scroll, state, events).
- **Responsive detector** : analyse automatique des breakpoints (au premier rendu, puis sur chaque resize significatif) et détection des bugs classiques :
  - Overflow horizontal.
  - Texte tronqué / débordant.
  - Éléments overlappés.
  - Touch targets < 44×44 px (accessibilité mobile).
  - Navigation cassée en mobile.
- **Screenshots batch** : bouton « Capture all devices » qui exporte une grille PDF / PNG des rendus.
- **Intégration Kanban** : lors du review d'une tâche UI, afficher automatiquement la matrix sur 3-4 devices critiques sans action de l'utilisateur.
- **Hot reload cross-device** : quand le code change, les N iframes se mettent à jour simultanément.
- **Device emulation avancée** : throttle réseau (Slow 3G, Fast 3G, 4G), throttle CPU (4x slowdown), cookies preset pour tester des personas utilisateur.

**Fichiers à toucher :**
- `apps/frontend/src/renderer/components/app-emulator/DeviceMatrix.tsx` — nouveau composant principal.
- `apps/frontend/src/renderer/components/app-emulator/DevicePresets.ts` — catalogue.
- `apps/frontend/src/renderer/components/app-emulator/ResponsiveDetector.tsx` — observation + alerting.
- `apps/frontend/src/main/app-emulator/screenshot-service.ts` — capture via Electron capturePage.
- `apps/frontend/src/shared/types/device.ts` — types DevicePreset, ResponsiveIssue.
- i18n : `appEmulator.json` (noms de devices, messages d'erreur).

**Edge cases :**
- App lourde qui met 10s à charger × 6 devices = 60s → lazy loading par priorité (devices visibles d'abord).
- CPU host surchargé par 6 iframes en parallèle → option « render sequential » plus lente mais moins gourmande.
- Auth / session qui diffère selon user agent → option de synchro des cookies ou session.
- Site qui bloque iframe (CSP, X-Frame-Options) → détection et fallback sur WebView natif.

**Métriques :**
- Nombre de sessions utilisant le mode matrix / semaine.
- Nombre de bugs responsive détectés automatiquement.
- Temps gagné vs. test manuel multi-device (mesurable via feedback user).

**Multi-provider :**
- App Emulator est une feature purement frontend (Electron + iframes + Chrome DevTools Protocol), zéro LLM impliqué dans son fonctionnement de base. 100% provider-indépendant par construction.
- Si une couche d'assistance IA est ajoutée pour *expliquer* un bug responsive détecté (« le texte déborde parce que le `min-width` du parent est trop grand »), elle utilise `create_client()` avec le provider configuré.
- Le screenshot batch + l'analyse visuelle des résultats peuvent être branchés sur la boucle Design-to-Code (D.13) pour valider qu'un changement UI n'a pas cassé le rendu sur d'autres devices — même contrat multi-provider vision-capable.
- Mode 100% offline possible, rendu local, aucune dépendance provider.

**Débloque :** QA visuel multi-device sans quitter WorkPilot, détection automatique des bugs responsive, argument fort pour les équipes frontend.

**Effort :** Moyen | **Impact :** Haut

#### 15. Voice Control — Streaming, interruption & conversation continue

**Aujourd'hui :** Voice Control fonctionne en mode commande : appui sur un raccourci, enregistrement, transcription, envoi. C'est utile mais statique — impossible de corriger l'agent en vol, pas de conversation fluide, pas d'accessibilité vraie pour les devs qui ne peuvent pas utiliser le clavier longtemps.

**Amélioration proposée :**
- **Mode conversation continue** : le micro reste actif (opt-in), détection de l'activité vocale (VAD) pour distinguer parole vs. silence vs. bruit ambiant.
- **Interruption en vol** : pendant qu'un agent parle/agit, l'utilisateur peut dire « non, stop » ou « attends, change ça » et l'agent s'arrête proprement (transactionnellement : le tool call en cours finit, mais le suivant n'est pas lancé).
- **Wake word optionnel** : « Hey WorkPilot » ou custom (« Hey Otto »). Activable uniquement quand le mode continu est désactivé pour ne pas être invasif.
- **Retour vocal (TTS)** : l'agent répond à voix haute ses décisions courtes (« je lance les tests », « j'ai trouvé 3 erreurs », « fait »). Configurable : muet / court / verbeux.
- **Multi-langue** : détection automatique de la langue parlée (FR/EN/ES/DE/...), prompt system adapté. Pas besoin de changer de paramètre.
- **Transcription live overlay** : afficher en temps réel ce qui est transcrit pour feedback immédiat à l'utilisateur (« t'as dit *rerun the tests* — c'est bien ça ? »).
- **Mode pair programming** : session vocale dédiée où l'agent explique ce qu'il fait à voix haute pendant qu'il code, l'utilisateur le guide, c'est une vraie conversation.
- **Accessibilité** : raccourci d'activation au pied (via pédale MIDI / HID) pour les devs avec troubles moteurs.

**Fichiers à toucher :**
- `apps/frontend/src/main/voice/voice-stream.ts` — nouveau, streaming audio + VAD.
- `apps/frontend/src/main/voice/interruption-handler.ts` — détection mot d'arrêt + propagation.
- `apps/frontend/src/main/voice/tts-service.ts` — TTS service.
- `apps/frontend/src/renderer/components/voice/VoiceOverlay.tsx` — UI transcription live.
- `apps/backend/voice/transcription.py` — abstraction STT (Whisper local / Deepgram / provider cloud).
- `apps/backend/voice/speech.py` — abstraction TTS.
- `apps/frontend/src/shared/i18n/locales/{en,fr,es,de}/voiceControl.json`.

**Edge cases :**
- Bruit ambiant fort → calibrage VAD automatique au démarrage, seuil configurable.
- Utilisateur change de langue en cours → transcription rebascule sans perdre le contexte.
- Faux positifs d'interruption (quelqu'un parle à côté) → confirmation rapide avant d'arrêter un tool call coûteux.
- Confidentialité : micro toujours actif = inquiétude vie privée → indicateur visuel rouge pulsant + bouton physique mute très visible.

**Métriques :**
- Temps moyen de session vocale / utilisateur actif.
- Taux d'interruptions qui aboutissent à une correction vs. arrêt complet.
- Satisfaction utilisateur sur l'accessibilité (survey).

**Multi-provider :**
- **STT (speech-to-text)** : abstraction qui supporte plusieurs backends — Whisper local (faster-whisper ou whisper.cpp pour offline), OpenAI Whisper API, Deepgram, Google Speech-to-Text, Azure Speech, Groq Whisper. L'utilisateur choisit dans les settings.
- **TTS (text-to-speech)** : abstraction similaire — Piper local (offline), OpenAI TTS, ElevenLabs, Google TTS, Azure. Mode 100% local via Piper + Whisper pour confidentialité max.
- **LLM de conversation** : utilise `create_client()` avec le provider configuré par l'utilisateur — Claude Sonnet, GPT-4o, Gemini 2.5, Grok, Llama 3.3. Capability requise : streaming + tool use.
- Les prompts de conversation sont courts, en style neutre, testés sur ≥3 providers. Format de sortie JSON contraint pour les commandes d'agent.
- Mode 100% offline fonctionnel : Whisper local + Llama 3.3 8B via Ollama + Piper TTS. Démontrable en démo sans réseau.
- Détection de la langue parlée côté STT (Whisper supporte 99 langues), puis le prompt system est traduit automatiquement si le provider LLM est multilingue (la plupart le sont).

**Débloque :** vrai pair programming vocal, accessibilité réelle pour les devs avec contraintes ergonomiques, usage en mobilité (tablette + casque), wow effect en démo.

**Effort :** Élevé | **Impact :** Moyen (fort pour les niches accessibilité + démo)

#### 16. Browser Agent — Recording & conversion human-to-test

**Aujourd'hui :** le Browser Agent automatise la navigation web via Chrome DevTools MCP (click, fill, navigate, take_screenshot). Cela fonctionne bien pour un agent qui agit seul, mais il manque un chemin pour *capturer* une session utilisateur manuelle et la convertir en test reproductible. Écrire un test Playwright à la main reste un frein majeur à l'adoption du E2E.

**Amélioration proposée :**
- **Mode recording** : un bouton « Record session » qui active un listener sur le browser (via Chrome DevTools Protocol). Toutes les interactions sont capturées : clicks (avec sélecteurs), saisies, navigations, scrolls, hovers, appuis clavier, ouvertures de dialogs.
- **Sélecteurs robustes** : au lieu de capturer `#btn-a1b2c3`, l'agent utilise des heuristiques pour privilégier `getByRole("button", { name: "Save" })`, `data-testid`, `aria-label`, text content — l'ordre suit les best practices Playwright / Testing Library.
- **Waits intelligents** : l'agent déduit les `waitFor` nécessaires en observant les transitions (disparition de spinners, apparition d'éléments, requêtes réseau).
- **Assertions auto-suggérées** : après chaque action significative, l'agent propose des assertions pertinentes (« après le clic, ce texte apparaît — l'ajouter en assertion ? »).
- **Export multi-frameworks** : Playwright (défaut), Cypress, Selenium, WebdriverIO — l'utilisateur choisit.
- **Reshoot en cas d'échec** : si le test généré échoue à la première exécution, l'agent relance la session d'enregistrement comme référence et propose un diff des sélecteurs qui ont changé.
- **Test data abstraction** : l'agent détecte les valeurs paramétrables (email, mot de passe, dates) et les extrait en fixtures au lieu de les hardcoder.
- **Intégration QA** : un test généré peut être ajouté directement à la suite E2E du projet via un bouton « Add to test suite » qui fait un commit sur une branche dédiée.

**Fichiers à toucher :**
- `apps/backend/browser_agent/recorder.py` — nouveau, orchestration du recording via CDP.
- `apps/backend/browser_agent/selector_builder.py` — génération de sélecteurs robustes.
- `apps/backend/browser_agent/test_generator.py` — export multi-frameworks.
- `apps/backend/browser_agent/assertion_suggester.py` — suggestions d'assertions via LLM.
- `apps/frontend/src/renderer/components/browser-agent/RecordingPanel.tsx` — UI enregistrement + review.
- `apps/backend/prompts/browser_agent_assertions.md` — prompt pour suggestions.

**Edge cases :**
- Shadow DOM → fallback sur une stratégie composée (`>>>` syntax Playwright).
- SPA avec state interne qui ne se reflète pas dans l'URL → capture d'état via eval script.
- Iframes tierces (auth provider, 3DS) → gestion explicite du contexte de frame.
- Random data à chaque visite (produits, prix) → détection et substitution par placeholders.
- Captcha / MFA → l'agent signale et demande un workaround manuel (fixture, bypass test-only).

**Métriques :**
- Taux de tests générés qui passent au premier run (objectif : > 70%).
- Ratio temps d'enregistrement / temps d'écriture manuelle équivalente.
- Nombre de tests E2E ajoutés au repo / semaine / équipe.
- Taux de flakiness des tests générés vs. tests écrits à la main.

**Multi-provider :**
- Le recording et la génération de sélecteurs sont purement basés sur Chrome DevTools Protocol + heuristiques statiques, zéro LLM — 100% provider-indépendants et très rapides.
- Le LLM intervient uniquement pour (1) suggérer des assertions pertinentes après chaque action significative, (2) proposer un nom de test et de description à partir du flow, (3) extraire les fixtures. Les 3 cas utilisent un modèle léger via `create_client()` — Haiku, GPT-4o-mini, Gemini Flash, Llama 3.1 8B via Ollama suffisent.
- Le prompt est court (< 1000 tokens typiquement) et structuré via tool use JSON Schema, testé cross-provider.
- Le reshoot en cas d'échec (diff de sélecteurs) peut utiliser un modèle vision (screenshots avant/après) — capability detection comme pour D.13.
- Mode Ollama totalement fonctionnel pour les tests sur des apps internes confidentielles.
- L'export multi-frameworks est déterministe et provider-indépendant.

**Débloque :** adoption test E2E dans les équipes qui ne l'ont jamais fait, création de suites de régression en continu (chaque session de dev = tests gratuits), réduction du « test debt ».

**Effort :** Élevé | **Impact :** Haut

---

### E. Mémoire & Apprentissage

#### 17. Learning Loop — Injection dans la spec creation

**Aujourd'hui :** le Learning Loop collecte des insights (patterns de succès, causes d'échec, préférences du repo) et les injecte principalement dans le prompt du coder au moment de l'exécution. Résultat : on corrige l'erreur après coup, alors qu'une spec mieux formulée dès le départ aurait évité des itérations. Le Learning Loop intervient trop tard dans le pipeline.

**Amélioration proposée :**
- **Feedback dans spec_writer** : quand un spec est créé, charger les insights pertinents du Learning Loop avant la rédaction. Exemples :
  - « Les specs UI sur ce repo passent en moyenne 3 itérations QA — sois plus précis sur les critères d'acceptation visuels et ajoute systématiquement des cas de responsive. »
  - « Les specs backend qui touchent le module `auth/` ont 80% de chances de casser les tests `session_*` — ajoute un requirement explicite sur la préservation des sessions. »
  - « Les specs migrations DB ont échoué 4 fois sur 5 quand elles étaient one-shot — décompose systématiquement en migration additive + backfill + bascule code. »
- **Feedback dans spec_critic** : le critic reçoit aussi les insights et peut flagger un spec comme « incomplet compte tenu de l'historique » avec suggestions concrètes.
- **Templates enrichis** : les templates de spec (bug fix, new feature, refactor) sont auto-enrichis par les insights du repo — par ex. pour un « bug fix » sur un repo donné, ajouter automatiquement des checkpoints « reproduire en test unitaire avant de fixer ».
- **Insights priorisés** : seuls les top-N insights sont injectés (éviter la dilution). Pondération par récence + pertinence contextuelle.
- **Retour utilisateur** : l'UI affiche « 3 insights appliqués à la création de ce spec » avec possibilité de les consulter / désactiver ponctuellement.

**Fichiers à toucher :**
- `apps/backend/spec/spec_writer.py` — hook de chargement des insights pertinents.
- `apps/backend/spec/insight_injector.py` — nouveau, matching insights ↔ contexte du spec.
- `apps/backend/learning_loop/insight_store.py` — API `get_relevant_insights(domain, files, spec_type)`.
- `apps/backend/prompts/spec_writer.md` — section dédiée pour les insights (formatage clair).
- `apps/frontend/src/renderer/components/spec/InsightsApplied.tsx` — UI de transparence.

**Edge cases :**
- Repo neuf sans historique → fallback sur template générique, pas d'insights forcés.
- Insights contradictoires → priorité à la récence + confidence score.
- Insight obsolète (refacto majeur rend un insight caduque) → intégration avec Memory Lifecycle Manager (feature E.18).
- Sur-injection (trop d'insights dans le prompt, noyage) → cap strict, rotation.

**Métriques :**
- Nombre moyen d'itérations QA par spec avant / après la feature (objectif : réduire).
- % de specs créés qui référencent au moins 1 insight.
- Corrélation insights appliqués ↔ taux de succès du spec.

**Multi-provider :**
- Le matching des insights (quel insight est pertinent pour ce spec ?) est fait par un LLM léger ou par recherche vectorielle locale (embeddings) — les deux chemins sont provider-agnostiques via l'abstraction `core.client.create_client()` ou via un modèle d'embedding local (sentence-transformers, multilingual-e5).
- Le spec_writer final peut utiliser n'importe quel provider flagship ou standard (Claude Sonnet, GPT-4o, Gemini 2.5, Grok, Llama 3.3, Qwen 2.5). Les insights sont injectés en texte neutre dans le prompt.
- Le stockage des insights est dans Graphiti (mémoire centralisée), indépendant du provider qui les a générés. Un insight capturé par un run Claude peut servir un run GPT-4o sans perte.
- Mode Ollama disponible pour toute la chaîne (matching + writing + critic), utile en environnement air-gap.
- Les prompts sont rédigés pour être rétro-compatibles avec les petits modèles (< 8k context) en priorisant les insights les plus pertinents et en tronquant si nécessaire.

**Débloque :** boucle d'amélioration réellement de bout en bout (spec → code → QA → spec), moins d'itérations, confiance montante de l'équipe dans le système qui « apprend » visiblement.

**Effort :** Moyen | **Impact :** Haut

#### 18. Memory Lifecycle Manager — Explicabilité des décisions

**Aujourd'hui :** le Memory Lifecycle Manager gère automatiquement le TTL, l'éviction LRU, la compression des mémoires dans Graphiti. Il fait son travail mais c'est une boîte noire : l'utilisateur voit une mémoire disparaître sans savoir pourquoi, ne peut pas la restaurer, ne peut pas l'épingler, et perd confiance dans la persistance des insights critiques.

**Amélioration proposée :**
- **Journal d'audit human-readable** : chaque action du lifecycle (création, mise à jour, suppression, fusion, compression) est journalée avec :
  - Horodatage précis.
  - Acteur (qui : utilisateur, agent coder, lifecycle auto, learning loop).
  - Raison explicite (« contredit par 3 commits récents », « TTL expiré », « remplacé par mémoire plus spécifique », « évincé par LRU car inactif 90 jours »).
  - Aperçu de la mémoire concernée (titre + premier paragraphe).
- **Timeline par mémoire** : pour chaque mémoire, accès à son historique complet (créations, mises à jour, éditions manuelles, fusions).
- **Bouton « Restore »** : réactive une mémoire supprimée (dans la limite d'une rétention de 30 jours par défaut). La restauration est tracée comme un événement.
- **Bouton « Pin »** : marque une mémoire comme permanente, elle échappe à toute éviction automatique. Limite : 50 pinned par projet pour éviter l'abus.
- **Raison avant suppression** : le lifecycle annonce à l'utilisateur les suppressions prévues dans les 7 prochains jours (« 12 mémoires vont être évincées — voulez-vous en épingler ? »).
- **Merge explicable** : quand deux mémoires sont fusionnées, le log explique les deux sources et le résultat, avec option de dé-fusion manuelle.
- **Undo global** : bouton « Undo last lifecycle action » (dans les 1h) pour annuler une décision automatique récente.

**Fichiers à toucher :**
- `apps/backend/memory_lifecycle/audit_log.py` — nouveau, persistance du journal.
- `apps/backend/memory_lifecycle/decision_explainer.py` — formatage lisible des raisons.
- `apps/backend/memory_lifecycle/restore.py` — API de restauration.
- `integrations/graphiti/memory_store.py` — ajout métadonnées `pinned`, `restore_available_until`.
- `apps/frontend/src/renderer/components/memory/MemoryTimeline.tsx` — UI timeline.
- `apps/frontend/src/renderer/components/memory/LifecycleAuditLog.tsx` — UI journal.
- `apps/frontend/src/shared/types/memory.ts` — types AuditEntry, LifecycleAction.

**Edge cases :**
- Suppression accidentelle d'une mémoire critique → rétention prolongée pour les mémoires pinned récemment.
- Conflit entre utilisateur (pin) et lifecycle (pense à évincer) → pin gagne toujours, log le conflit pour transparence.
- Dataset qui explose (trop de logs) → rotation du journal par mois + compression.
- Restauration d'une mémoire devenue factuellement fausse → warning utilisateur (« cette mémoire contredit l'état actuel du code »).

**Métriques :**
- Nombre de restaurations / semaine (indicateur : trop → lifecycle trop agressif).
- Taux de mémoires pinned / projet.
- Nombre de « why was this deleted? » vues par l'utilisateur (engagement dans la transparence).

**Multi-provider :**
- Le lifecycle lui-même est purement algorithmique (TTL, LRU, scoring, dedup) — zéro LLM, 100% provider-indépendant.
- Le LLM intervient uniquement pour (1) formuler la raison en langage naturel (« cette mémoire a été supprimée parce qu'elle est contredite par... »), (2) détecter les contradictions sémantiques entre une nouvelle mémoire et les existantes, (3) suggérer des fusions. Les 3 cas utilisent un modèle léger via `create_client()` — Haiku, GPT-4o-mini, Gemini Flash, Llama 8B via Ollama.
- Le stockage est dans Graphiti (backend indépendant), utilisable avec n'importe quel provider comme source des mémoires.
- Les prompts sont courts, neutres, en JSON Schema via tool use. Testés sur ≥3 providers.
- Le mode offline via Ollama couvre toute la chaîne (détection contradiction, formulation raison, merge suggestion).
- L'audit log est indépendant du provider — une mémoire créée avec Claude et modifiée avec GPT-4o garde un historique cohérent.

**Débloque :** confiance totale dans le système de mémoire, capacité pour les équipes enterprise d'auditer les décisions du lifecycle (compliance), meilleure adoption car les utilisateurs ne subissent plus des oublis inexplicables.

**Effort :** Moyen | **Impact :** Moyen-Haut (confiance critique)

#### 19. Team Knowledge Sync — Résolution de conflits sémantiques

**Aujourd'hui :** Team Knowledge Sync permet à plusieurs coéquipiers de partager leur mémoire Graphiti via un serveur central ou peer-to-peer. Ça fonctionne tant que tout le monde pense la même chose. Dès que deux devs capturent des mémoires contradictoires (« il faut utiliser l'ORM X » vs. « il faut utiliser l'ORM Y pour ce module »), le système fusionne naïvement et tout le monde se retrouve avec des conseils incohérents.

**Amélioration proposée :**
- **Détection de contradictions** : lors d'un sync, un agent compare sémantiquement les mémoires nouvellement reçues avec les mémoires existantes et flagge les contradictions (négations, recommandations opposées, valeurs numériques incompatibles).
- **Arbitrage automatique** quand c'est sûr :
  - La mémoire la plus récente gagne si elle est corroborée par N commits postérieurs.
  - La mémoire avec la plus forte confidence (learning loop) gagne.
  - Les mémoires pinned l'emportent sur les non-pinned.
- **Arbitrage manuel** quand c'est ambigu : UI de résolution qui présente les deux mémoires côte à côte avec les auteurs, dates, sources, et demande à l'utilisateur (ou à un maintainer désigné) de trancher.
- **Canonicalisation** : après arbitrage, une mémoire canonique est créée (`source: team-consensus-2026-04-12`) et les variantes individuelles sont archivées avec un lien vers la canonique.
- **Notification d'équipe** : quand un conflit est détecté, notifier les auteurs concernés (intégration Slack/Teams) pour qu'ils puissent discuter.
- **Branches de mémoire** : possibilité d'avoir des mémoires scopées par équipe / branche / module (« sur `auth/` on fait comme ça, sur `payments/` on fait autrement »), pour éviter les conflits artificiels dus à des contextes différents.
- **Historique des consensus** : traçabilité de qui a voté quoi à l'arbitrage manuel, pour post-mortem.

**Fichiers à toucher :**
- `apps/backend/team_sync/contradiction_detector.py` — nouveau, détection sémantique.
- `apps/backend/team_sync/arbitration_engine.py` — règles d'arbitrage auto.
- `apps/backend/team_sync/canonical_memory.py` — création/gestion des mémoires canoniques.
- `apps/backend/team_sync/notification_service.py` — intégration Slack/Teams/email.
- `apps/frontend/src/renderer/components/team-sync/ConflictResolver.tsx` — UI de résolution.
- `apps/frontend/src/renderer/components/team-sync/MemoryScope.tsx` — sélecteur de scope.
- `integrations/graphiti/memory_store.py` — ajout métadonnées `scope`, `canonical_of`.

**Edge cases :**
- Contradiction faussement détectée sur des formulations différentes mais équivalentes → utiliser des embeddings sémantiques pour raffiner la détection.
- Arbitrage infini (deux devs qui flip-flop) → seuil de « cooldown » et escalade au maintainer.
- Sync depuis un coéquipier malveillant ou avec un dataset corrompu → signature cryptographique des snapshots et liste blanche des sources.
- Équipe trop grande (> 20 devs) → hiérarchie de scopes + maintainers désignés par module.

**Métriques :**
- Nombre de contradictions détectées / sync (à surveiller, pas à minimiser).
- Temps moyen de résolution manuelle.
- Nombre de mémoires canoniques créées / mois.
- Taux d'adoption des mémoires canoniques par l'équipe (via analytics du reviewer).

**Multi-provider :**
- La détection de contradictions peut se faire de deux façons complémentaires :
  1. **Embeddings locaux** : cosine similarity + règles heuristiques, 100% offline et provider-agnostique (sentence-transformers, multilingual-e5).
  2. **LLM léger** : un modèle comme Haiku / GPT-4o-mini / Gemini Flash / Llama 3.1 8B via Ollama pour raffiner (« ces deux mémoires se contredisent-elles vraiment ou sont-elles complémentaires ? »).
- Les deux chemins passent par des abstractions (`EmbeddingProvider`, `LLMProvider`) qui délèguent au backend de l'utilisateur.
- L'arbitrage automatique est purement algorithmique (règles sur métadonnées) — zéro LLM, zéro ambiguïté cross-provider.
- L'arbitrage manuel n'implique pas de LLM dans la décision — l'humain tranche. Le LLM peut éventuellement résumer les deux positions pour aider à décider.
- Le sync entre machines utilise un format de snapshot neutre (JSON + signatures), indépendant du provider qui a créé les mémoires.
- Mode Ollama fonctionne pour toute la chaîne : détection, arbitrage, notification.

**Débloque :** sain fonctionnement en équipe >3 personnes, fin des conseils contradictoires, création d'un corpus de connaissances cohérent à l'échelle de l'entreprise.

**Effort :** Moyen-Élevé | **Impact :** Très haut pour les équipes

---

### F. Coûts & Analytics

#### 20. Cost Intelligence — Budgets live, dégradation & circuit breaker

**Aujourd'hui :** Cost Intelligence produit des rapports post-hoc : coût du sprint passé, coût par spec, top modèles consommés. Utile mais rétrospectif. Quand un agent dérape et consomme $200 en 1h (boucle infinie, over-thinking, trop de parallélisme), personne ne s'en rend compte avant le rapport du lendemain.

**Amélioration proposée :**
- **Budgets live** : définis à 3 niveaux — `organization`, `project`, `spec`. Chacun a ses seuils `soft_warn, hard_stop`.
- **Tracking temps réel** : chaque tool call / message LLM incrémente un compteur live (Redis ou SQLite + WAL). Latence d'affichage < 2s.
- **Alertes progressives** :
  - À 50% du budget : notification passive dans l'UI.
  - À 75% : notification modale + suggestion de dégradation.
  - À 90% : suggestion forte de stop ou switch vers un modèle moins cher.
  - À 100% : hard stop automatique (configurable).
- **Dégradation automatique** : quand un seuil est franchi, le système peut automatiquement :
  1. Switcher du tier flagship (Opus, GPT-4.1, Gemini 2.5 Pro) vers le tier standard (Sonnet, GPT-4o, Gemini 2.5 Flash).
  2. Puis vers le fast tier (Haiku, GPT-4o-mini, Gemini Flash, Llama local).
  3. Puis vers Ollama local (coût effectif = 0).
- **Circuit breaker intelligent** : si un agent consomme >3x son budget estimé sans progresser (diff vide), il est suspendu avec notification — distinct d'une simple dégradation de modèle.
- **Réservation budgétaire** : avant de lancer un spec, « réserver » le budget estimé dans l'enveloppe globale pour éviter les dépassements simultanés.
- **Rapport en direct** : dashboard live avec heatmap par équipe / projet / agent et burn rate.
- **Export compliance** : format CSV/JSON pour facturation refacturée (charge back) aux équipes.

**Fichiers à toucher :**
- `apps/backend/cost_intelligence/live_tracker.py` — nouveau, tracking temps réel.
- `apps/backend/cost_intelligence/budget_enforcer.py` — circuit breaker + dégradation.
- `apps/backend/cost_intelligence/reservation.py` — réservation budgétaire.
- `apps/backend/cost_intelligence/catalog.py` — catalogue de prix versionné (voir multi-provider ci-dessous).
- `apps/frontend/src/renderer/components/cost/LiveDashboard.tsx` — UI live.
- `apps/frontend/src/renderer/components/cost/BudgetAlert.tsx` — notifications progressives.
- `apps/backend/core/client.py` — hook d'enforcement avant chaque call.

**Edge cases :**
- Rate limit du provider qui cause des retries → ne pas compter les retries échoués dans le budget.
- Facturation à la session Claude OAuth (pas à l'API) → différencier les profils OAuth (budget = quotas conversation) vs. API (budget = $).
- Budget soft_warn trop bas → spam de notifications → cooldown + throttling.
- Perte de connexion Redis / SQLite → fallback mémoire + resync.

**Métriques :**
- Nombre de circuit breaker triggers / semaine (doit rester bas après stabilisation).
- Δ coût moyen par spec avant / après la feature (objectif : -20%).
- Taux de dépassements budget / total specs (objectif : < 2%).
- Adoption des alertes live (utilisateurs qui configurent des budgets).

**Multi-provider :**
- **Catalogue de prix versionné** : fichier JSON/YAML qui couvre TOUS les providers supportés avec leurs prix par modèle et par type de token (input / output / cache read / cache write / vision tokens / thinking tokens). Exemple :
  ```yaml
  anthropic:
    claude-opus-4-6: { input: 15.00, output: 75.00, cache_write: 18.75, cache_read: 1.50, thinking: 75.00 }
    claude-sonnet-4-6: { input: 3.00, output: 15.00, cache_write: 3.75, cache_read: 0.30 }
    claude-haiku-4-5: { input: 0.80, output: 4.00 }
  openai:
    gpt-4.1: { input: 2.50, output: 10.00 }
    gpt-4o-mini: { input: 0.15, output: 0.60 }
  google:
    gemini-2.5-pro: { input: 1.25, output: 5.00 }
  xai:
    grok-4: { input: 5.00, output: 15.00 }
  ollama:
    llama-3.3-70b: { input: 0.00, output: 0.00, energy_kwh_per_million_tok: 0.08 }
  ```
- Le catalogue est mis à jour via un script `runners/update_pricing_catalog.py` qui peut récupérer les prix depuis les pages tarifs officielles (hebdomadaire).
- L'unité normalisée est l'USD. Les coûts Ollama sont tracés en kWh (voir feature Carbon Profiler nouvelle Tier B).
- Le tracker est indépendant du provider : il intercepte chaque call via `core.client.create_client()` et compte les tokens retournés par le SDK correspondant, converti en USD via le catalogue.
- La dégradation progressive utilise des tiers abstraits (`flagship → standard → fast → local`) plutôt que des noms de modèles, ce qui permet des compositions mixed-provider. Exemple : un agent peut dégrader de Claude Opus → Claude Sonnet → GPT-4o → Llama 3.3 Ollama sans casser.
- Les budgets sont exprimés en USD global, peu importe le mix de providers utilisés. Un budget de 10$/spec peut être dépensé en Claude, OpenAI, ou mix.
- Les profils Claude OAuth / Copilot qui n'ont pas de facturation token-based sont trackés en « sessions consommées » ou « ratelimit progress », avec un modèle d'équivalence configurable.
- Mode Ollama : budget monétaire = 0 par défaut, option d'ajouter un coût énergétique (kWh × tarif local) pour un ROI réaliste sur le matériel local.

**Débloque :** contrôle réel des coûts en temps réel, adoption enterprise (finance accepte enfin de budgétiser), fin des dérapages silencieux, charge-back facile aux équipes, possibilité de laisser tourner Swarm Mode la nuit sans stress.

**Effort :** Élevé | **Impact :** Très haut (critique pour enterprise)

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
