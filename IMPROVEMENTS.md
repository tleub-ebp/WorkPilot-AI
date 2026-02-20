# Audit & Améliorations — WorkPilot AI (Auto-Claude EBP)

> Audit complet réalisé le 20/02/2026 — Couvre le frontend Electron/React, le backend Python/FastAPI, l'architecture multi-provider LLM, la sécurité et la qualité de code.

---

## Table des matières

1. [Qualité de code — Frontend](#1-qualité-de-code--frontend)
2. [Qualité de code — Backend](#2-qualité-de-code--backend)
3. [Architecture & Design Patterns](#3-architecture--design-patterns)
4. [Sécurité](#4-sécurité)
5. [Performance](#5-performance)
6. [Tests & Couverture](#6-tests--couverture)
7. [DevOps & CI/CD](#7-devops--cicd)
8. [Documentation & i18n](#8-documentation--i18n)
9. [UX & Accessibilité](#9-ux--accessibilité)

---

## 1. Qualité de code — Frontend

### 1.1 — `console.log` massifs en production

**Constat :** 329 occurrences de `console.log` dans 65 fichiers du frontend. Les fichiers les plus touchés :
- `agent-process.ts` (40 occurrences)
- `KanbanBoard.tsx` (34 occurrences)
- `execution-handlers.ts` (15 occurrences)

**Risque :** Fuite d'informations sensibles (tokens, clés), bruit dans la console, impact léger sur les performances.

**Recommandation :**
- Remplacer tous les `console.log` par le logger existant (`electron-log` / `app-logger.ts`) ou le `debugLog` de `@shared/utils/debug-logger`.
- Ajouter une règle Biome pour interdire `console.log` en production.
- Garder uniquement `console.error` pour les erreurs critiques.

---

### 1.2 — Utilisation excessive de `any` (180 occurrences)

**Constat :** 180 matches de type `any` dans 84 fichiers renderer. Les pires :
- `UsageIndicator.tsx` (13 `any`)
- `ProviderManager.tsx` (8 `any`)
- `PRDetail.tsx` (8 `any`)

**Recommandation :**
- Remplacer progressivement par des types concrets ou `unknown` + type guards.
- Activer la règle Biome/TypeScript `noExplicitAny` en mode warning puis error.
- Prioriser les fichiers critiques (stores, IPC handlers, composants de sécurité).

---

### 1.3 — Composants géants (God Components)

**Constat :** Plusieurs composants dépassent largement la taille recommandée :

| Fichier | Taille |
|---------|--------|
| `KanbanBoard.tsx` | **82 734 octets** (~2 087 lignes) |
| `AgentTools.tsx` | **56 593 octets** |
| `cli-tool-manager.ts` | **80 546 octets** |
| `UsageIndicator.tsx` | **49 779 octets** |
| `Worktrees.tsx` | **41 974 octets** |
| `Terminal.tsx` | **36 545 octets** |
| `GitHubSetupModal.tsx` | **35 359 octets** |

**Recommandation :**
- Extraire les sous-composants logiques (ex: `KanbanColumn`, `KanbanHeader`, `KanbanDragOverlay`).
- Utiliser des custom hooks pour la logique métier complexe (`useKanbanDragDrop`, `useKanbanColumns`).
- Viser < 500 lignes par composant, < 300 lignes par fichier utilitaire.

---

### 1.4 — 57 TODO/FIXME/HACK non résolus

**Constat :** 57 annotations TODO/FIXME/HACK détectées dans 39 fichiers, certaines dans des zones critiques (OAuth handlers, terminal, worktree).

**Recommandation :**
- Trier par criticité et créer des issues/work items Azure DevOps pour chaque TODO.
- Supprimer ceux qui sont obsolètes.
- Interdire les TODO sans issue associée en pre-commit.

---

### 1.5 — Fichier mort `RepositoryProviderModal.tsx`

**Constat :** Le fichier `RepositoryProviderModal.tsx` fait 0 octets. Fichier `ProviderManager.tsx.REMOVED.txt` également présent.

**Recommandation :** Nettoyer les fichiers morts et les `.REMOVED.txt` du codebase.

---

## 2. Qualité de code — Backend

### 2.1 — `except:` (bare except) sans type d'exception

**Constat :** 9 occurrences de `except:` sans spécification d'exception dans :
- `migration/analyzer.py` (5)
- `migration/rollback.py` (2)
- `provider_api.py` (2)

**Risque :** Capture silencieuse de `KeyboardInterrupt`, `SystemExit`, masquage de bugs critiques.

**Recommandation :**
- Toujours spécifier le type d'exception : `except Exception as e:` minimum.
- Utiliser des exceptions plus spécifiques quand possible.
- Ajouter la règle Ruff `E722` (bare-except) en erreur bloquante.

---

### 2.2 — Variable globale mutable dans `provider_api.py`

**Constat :** `selected_provider = None` est une variable globale mutable utilisée pour stocker l'état du provider sélectionné.

**Risque :** Race condition en multi-thread/multi-worker, état partagé implicite, difficulté de test.

**Recommandation :**
- Utiliser un store Redis/SQLite ou un contexte FastAPI (Dependency Injection via `Depends`).
- Au minimum, utiliser `contextvars` pour l'isolation par requête.

---

### 2.3 — Routes dupliquées dans `provider_api.py`

**Constat :** Deux routes `@app.post("/providers/test/{provider}")` sont définies (lignes 179 et 196) avec des signatures différentes (`test_provider` et `test_provider_api_key`). La seconde écrase la première.

**Recommandation :** Fusionner en une seule route avec un body optionnel, ou créer deux endpoints distincts (`/test` et `/test-key`).

---

### 2.4 — `sys.path.insert` dynamiques

**Constat :** Plusieurs manipulations de `sys.path` dans `provider_api.py` (`sys.path.insert(0, ...)`), imports conditionnels éparpillés.

**Recommandation :**
- Structurer le projet avec un `pyproject.toml` et des packages installables.
- Utiliser des imports absolus cohérents.
- Supprimer tous les `sys.path.insert` et configurer correctement le PYTHONPATH.

---

### 2.5 — Clés API exposées dans les DEBUG prints

**Constat :** `force_claude_provider_config()` dans `llm_config.py` fait `print(f"DEBUG: ... config sauvegardée: {config}")` — ce qui affiche la clé API en clair dans les logs.

**Recommandation :**
- Ne jamais logger les valeurs de clés API. Masquer avec `api_key[:8]...` ou utiliser le logger avec un filtre de secrets.
- Remplacer tous les `print("DEBUG: ...")` par le module `logging` avec les niveaux appropriés.

---

### 2.6 — Stockage des configs LLM en JSON plaintext

**Constat :** `llm_config.py` stocke les configurations (y compris les clés API) dans `~/.work_pilot_ai_llm_providers.json` en texte clair.

**Recommandation :**
- Utiliser le credential store natif de l'OS (Keychain macOS, Windows Credential Manager, libsecret Linux) comme c'est déjà fait pour les profils Claude dans le frontend.
- Au minimum, chiffrer le fichier JSON avec une clé dérivée.

---

## 3. Architecture & Design Patterns

### 3.1 — Duplication de logique Provider entre Frontend et Backend

**Constat :** La détection et la gestion des providers LLM existe en double :
- Frontend : `src/shared/utils/providers.ts`, `ProviderSelector.tsx`, `ProviderManager.tsx`, `ProviderContext.tsx`
- Backend : `provider_api.py`, `src/connectors/llm_discovery.py`, `configured_providers.json`

**Recommandation :**
- Faire du backend la **source unique de vérité** pour la liste des providers, leur statut et leurs capabilities.
- Le frontend ne fait que consommer l'API REST, sans logique de détection dupliquée.

---

### 3.2 — Stores Zustand trop nombreux et fragmentés

**Constat :** 22+ stores Zustand, certains avec des responsabilités floues ou redondantes :
- `provider-refresh-store.ts` (304 octets — quasi vide)
- `auth-failure-store.ts` (1200 octets)
- `rate-limit-store.ts` (2397 octets)

**Recommandation :**
- Regrouper les micro-stores par domaine (ex: `auth-store.ts` combinant auth-failure + rate-limit + claude-profile).
- Utiliser les slices Zustand pour maintenir la séparation logique sans multiplier les fichiers.

---

### 3.3 — IPC Channel explosion

**Constat :** `ipc.ts` contient 607 lignes de constantes IPC, et `ipc-handlers/` contient 121 fichiers.

**Recommandation :**
- Implémenter un pattern de routing IPC centralisé avec auto-discovery des handlers.
- Regrouper par domaine avec des namespaces typés : `ipc.task.*`, `ipc.terminal.*`, etc.
- Générer les types IPC automatiquement via un script de codegen.

---

### 3.4 — CORS `allow_origins=["*"]` sur l'API backend

**Constat :** L'API FastAPI autorise toutes les origines.

**Recommandation :** Restreindre à `http://localhost:*` et aux origines Electron connues.

---

## 4. Sécurité

### 4.1 — Exécution de `subprocess.run` sans sanitization

**Constat :** `provider_api.py` exécute `subprocess.run(["gh", "auth", "status"], ...)` et `subprocess.run(["gh", "copilot", "--version"], ...)` directement. Bien que les arguments soient hardcodés ici, le pattern est risqué s'il est étendu.

**Recommandation :**
- Centraliser l'exécution de sous-processus dans un module sécurisé avec timeout, validation et logging.
- Utiliser le module `security/` existant pour valider toute commande shell.

---

### 4.2 — Absence de rate limiting sur l'API backend

**Constat :** Aucun rate limiting sur les endpoints FastAPI (`/providers/test/*`, `/providers/generate/*`).

**Recommandation :**
- Ajouter `slowapi` ou un middleware de rate limiting.
- Limiter notamment `/providers/test/*` (peut être utilisé pour tester des clés API en brute force).

---

### 4.3 — Endpoint `/providers/validate/{provider}` sans vérification

**Constat :** L'endpoint `validate_provider_key` marque une clé comme validée (`set_validated(provider, api_key, True)`) sans effectuer aucun test réel.

**Recommandation :** Supprimer cet endpoint ou y ajouter une vérification effective avant de marquer la clé comme valide.

---

## 5. Performance

### 5.1 — Re-renders excessifs sur le KanbanBoard

**Constat :** `KanbanBoard.tsx` (2 087 lignes) utilise de nombreux `useState`, `useEffect` et callbacks non mémoïsés. Avec beaucoup de tâches, les performances de rendu se dégradent.

**Recommandation :**
- Extraire les colonnes en composants `memo()` avec des comparaisons strictes.
- Utiliser `useMemo` et `useCallback` de manière systématique.
- Implémenter la virtualisation (`@tanstack/react-virtual` est déjà installé mais pas utilisé dans le Kanban).

---

### 5.2 — Absence de lazy loading pour les vues secondaires

**Constat :** Toutes les vues (Roadmap, Insights, Ideation, GitHub Issues, GitLab, Changelog) sont importées statiquement dans `App.tsx`.

**Recommandation :**
- Utiliser `React.lazy()` + `Suspense` pour charger les vues à la demande.
- Réduire le bundle initial et le temps de démarrage de l'application.

---

### 5.3 — Appels API synchrones bloquants dans `provider_api.py`

**Constat :** Les appels `requests.get(...)` dans les routes FastAPI sont synchrones et bloquants.

**Recommandation :**
- Utiliser `httpx` en mode async avec `await` dans les routes FastAPI.
- FastAPI est conçu pour l'async ; le code synchrone bloque le event loop.

---

## 6. Tests & Couverture

### 6.1 — Tests backend très complets, tests frontend insuffisants

**Constat :**
- Backend : **121+ fichiers de test** couvrant agents, sécurité, merge, QA, streaming, etc. Excellent.
- Frontend : Seulement quelques tests unitaires éparpillés (`AuthStatusIndicator.test.tsx`, `ProfileBadge.test.tsx`, `VisualProgrammingInterface.test.tsx`, etc.), aucune couverture systématique des stores ou des composants critiques.

**Recommandation :**
- Ajouter des tests pour les stores Zustand critiques (`task-store`, `project-store`, `settings-store`).
- Tester les composants complexes (KanbanBoard, Terminal, TaskCreationWizard).
- Implémenter des tests E2E Playwright pour les workflows critiques (création de tâche, démarrage agent, merge).

---

### 6.2 — Pas de test d'intégration Frontend ↔ Backend

**Constat :** Aucun test ne vérifie que l'API `provider_api.py` répond correctement aux appels du frontend.

**Recommandation :**
- Créer une suite de tests d'intégration avec un backend mocké ou un backend de test.
- Tester les scénarios : sélection de provider, test de clé API, génération.

---

## 7. DevOps & CI/CD

### 7.1 — `requirements.txt` racine quasi vide

**Constat :** Le `requirements.txt` à la racine ne contient que `openai>=1.0.0`. Le vrai fichier de dépendances est dans `apps/backend/requirements.txt`.

**Recommandation :** Supprimer le `requirements.txt` racine ou le transformer en lien vers celui du backend pour éviter la confusion.

---

### 7.2 — Absence de health check structuré

**Constat :** Seul un endpoint `/ping` très basique et un `/db/health` existent. Pas de health check complet.

**Recommandation :**
- Créer un endpoint `/health` retournant l'état de tous les sous-systèmes (DB, providers, mémoire Graphiti, etc.).
- L'utiliser dans les scripts de démarrage et le monitoring.

---

### 7.3 — Scripts de démarrage dupliqués

**Constat :** Multiples scripts de démarrage (`start_backend_and_frontend.cmd`, `.sh`, `start_provider_api.py`, `provider_api.py` en direct). Le README mentionne que `start_provider_api.py` est "obsolète mais compatible".

**Recommandation :** Unifier en un seul point d'entrée par plateforme et supprimer les scripts obsolètes.

---

## 8. Documentation & i18n

### 8.1 — README.md trop long et mixte FR/EN

**Constat :** Le README fait 448 lignes et mélange l'anglais (début) et le français (sections Grepai, dépannage, etc.). Les sections s'accumulent sans structure claire.

**Recommandation :**
- Séparer en plusieurs documents : `README.md` (EN, concis), `docs/SETUP.md`, `docs/TROUBLESHOOTING.md`, `docs/PROVIDERS.md`.
- Choisir une langue unique pour la documentation publique.

---

### 8.2 — Textes hardcodés dans l'ErrorBoundary

**Constat :** L'`ErrorBoundary` contient des textes en anglais hardcodés ("Something went wrong", "Try Again") au lieu d'utiliser `react-i18next` comme requis par les règles du projet.

**Recommandation :** Utiliser les traductions i18n dans l'ErrorBoundary (nécessite un wrapper fonctionnel pour accéder à `useTranslation`).

---

## 9. UX & Accessibilité

### 9.1 — Pas de gestion d'état de chargement global

**Constat :** Chaque composant gère son propre état de chargement de manière indépendante. Pas de skeleton screens ou de progression globale cohérente.

**Recommandation :**
- Implémenter un système de loading state centralisé.
- Ajouter des skeleton screens pour les vues principales (Kanban, Terminal Grid).

---

### 9.2 — Accessibilité (a11y) non vérifiée

**Constat :** Pas de tests d'accessibilité automatisés, pas de vérification ARIA sur les composants custom.

**Recommandation :**
- Ajouter `eslint-plugin-jsx-a11y` (ou équivalent Biome).
- Auditer les composants avec axe-core ou Lighthouse.
- Assurer le support clavier complet sur le Kanban drag-and-drop.

---

## Résumé des priorités

| Priorité | Amélioration | Impact |
|----------|-------------|--------|
| 🔴 Critique | Clés API en clair dans les logs/fichiers | Sécurité |
| 🔴 Critique | CORS `*` sur API backend | Sécurité |
| 🔴 Critique | Routes dupliquées + endpoint validate sans vérification | Bugs/Sécurité |
| 🟠 Haute | Remplacement `console.log` par logger structuré | Qualité |
| 🟠 Haute | Refactoring des God Components | Maintenabilité |
| 🟠 Haute | Bare `except:` dans le backend | Fiabilité |
| 🟡 Moyenne | Lazy loading des vues React | Performance |
| 🟡 Moyenne | Tests frontend + intégration | Fiabilité |
| 🟡 Moyenne | Migration `requests` → `httpx` async | Performance |
| 🟢 Basse | Nettoyage fichiers morts | Propreté |
| 🟢 Basse | Unification des scripts de démarrage | DX |
| 🟢 Basse | README restructuré | Documentation |
