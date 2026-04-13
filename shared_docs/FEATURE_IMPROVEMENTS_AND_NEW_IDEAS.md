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
