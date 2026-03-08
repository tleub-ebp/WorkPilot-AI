# Plan d'implémentation — Feature "App Emulator" (#12)

## Résumé

L'App Emulator permet de lancer et prévisualiser l'application du projet directement depuis l'interface WorkPilot AI. Un bouton "Preview" apparaît sur les tâches terminées dans le Kanban. L'émulateur détecte automatiquement le type de projet (web, Node, Python, etc.), lance le serveur de développement, et affiche le résultat dans un iframe intégré (apps web) ou un terminal (apps CLI/desktop).

## Architecture

```
Backend Runner (Python)        → Analyse le projet, détecte le type & la commande de démarrage
    ↓
Main Process Service (TS)      → Gère le cycle de vie du dev server (spawn/kill/port detection)
    ↓
IPC Handlers (TS)              → Pont main ↔ renderer
    ↓
Preload API (TS)               → Expose les méthodes au renderer
    ↓
Zustand Store (TS)             → État de l'émulateur (phase, url, logs, etc.)
    ↓
Dialog Component (React)       → UI avec iframe/terminal + contrôles
```

---

## Étape 1 — Backend Runner (`apps/backend/runners/app_emulator_runner.py`)

**Nouveau fichier.** Analyse le projet pour détecter :
- Le type d'application (web-react, web-vue, web-angular, node, python-flask, python-django, python-fastapi, electron, generic)
- La commande de démarrage (ex: `npm run dev`, `python manage.py runserver`)
- Le port par défaut (3000, 5000, 8000, etc.)
- Les dépendances requises

Structure :
```python
class AppEmulatorRunner:
    def __init__(self, project_dir: str):
        self.project_dir = Path(project_dir)

    def detect_project_type(self) -> dict:
        """Analyse package.json, requirements.txt, pyproject.toml, etc."""
        # Retourne: { type, startCommand, port, framework, dependencies }

    def detect_from_package_json(self) -> dict | None: ...
    def detect_from_python(self) -> dict | None: ...
    def detect_from_electron(self) -> dict | None: ...

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-dir", required=True)
    args = parser.parse_args()
    runner = AppEmulatorRunner(args.project_dir)
    result = runner.detect_project_type()
    print("__APP_EMULATOR_RESULT__:" + json.dumps(result))
```

**Pas besoin de Claude Agent SDK** — c'est une analyse de fichiers, pas de LLM nécessaire.

---

## Étape 2 — Main Process Service (`apps/frontend/src/main/app-emulator-service.ts`)

**Nouveau fichier.** Gère le cycle de vie complet du serveur de développement.

```typescript
export interface AppEmulatorConfig {
  type: string;          // 'web-react' | 'node' | 'python-flask' | etc.
  startCommand: string;  // 'npm run dev'
  port: number;          // 3000
  framework: string;     // 'react' | 'vue' | 'django' | etc.
  projectDir: string;
}

export class AppEmulatorService extends EventEmitter {
  private activeProcess: ChildProcess | null = null;
  private config: AppEmulatorConfig | null = null;

  // Events: 'status', 'ready', 'output', 'error', 'stopped'

  async detectProject(projectDir: string): Promise<AppEmulatorConfig>
  async startServer(config: AppEmulatorConfig): Promise<void>
  async stopServer(): Promise<void>
  isRunning(): boolean
  getUrl(): string | null
}
```

Fonctionnalités :
- Spawn le runner Python pour la détection
- Lance le dev server avec la commande détectée
- Détecte quand le serveur est prêt (poll HTTP sur le port)
- Stream la sortie stdout/stderr
- Cleanup propre du process (kill + descendants)

---

## Étape 3 — IPC Handlers (`apps/frontend/src/main/ipc-handlers/app-emulator-handlers.ts`)

**Nouveau fichier.**

```typescript
export function registerAppEmulatorHandlers(getMainWindow: () => BrowserWindow | null): void {
  ipcMain.handle('app-emulator:detect', async (_, { projectDir }) => { ... })
  ipcMain.handle('app-emulator:start', async (_, { config }) => { ... })
  ipcMain.handle('app-emulator:stop', async () => { ... })
  ipcMain.handle('app-emulator:status', async () => { ... })

  // Forward events to renderer
  appEmulatorService.on('status', ...)
  appEmulatorService.on('ready', ...)
  appEmulatorService.on('output', ...)
  appEmulatorService.on('error', ...)
  appEmulatorService.on('stopped', ...)
}
```

**Modification** de `apps/frontend/src/main/ipc-handlers/index.ts` :
- Import + appel de `registerAppEmulatorHandlers`

---

## Étape 4 — Preload API (`apps/frontend/src/preload/api/modules/app-emulator-api.ts`)

**Nouveau fichier.**

```typescript
export interface AppEmulatorAPI {
  detectAppProject: (projectDir: string) => Promise<IPCResult<AppEmulatorConfig>>
  startAppEmulator: (config: AppEmulatorConfig) => void
  stopAppEmulator: () => void
  getAppEmulatorStatus: () => Promise<IPCResult<{ running: boolean; url?: string }>>

  onAppEmulatorStatus: (cb: (status: string) => void) => () => void
  onAppEmulatorReady: (cb: (url: string) => void) => () => void
  onAppEmulatorOutput: (cb: (line: string) => void) => () => void
  onAppEmulatorError: (cb: (error: string) => void) => () => void
  onAppEmulatorStopped: (cb: () => void) => () => void
}
```

**Modification** de `apps/frontend/src/preload/api/index.ts` :
- Import `AppEmulatorAPI` + `createAppEmulatorAPI`
- Ajouter à l'interface `ElectronAPI` et à `createElectronAPI()`

---

## Étape 5 — Zustand Store (`apps/frontend/src/renderer/stores/app-emulator-store.ts`)

**Nouveau fichier.**

```typescript
type AppEmulatorPhase = 'idle' | 'detecting' | 'starting' | 'running' | 'stopped' | 'error'

interface AppEmulatorState {
  isOpen: boolean
  phase: AppEmulatorPhase
  config: AppEmulatorConfig | null
  url: string | null          // URL du serveur (pour l'iframe)
  output: string              // Logs du serveur
  error: string | null
  status: string
  taskId: string | null       // ID de la tâche associée (optionnel)

  // Actions
  openDialog(taskId?: string)
  closeDialog()
  setPhase(phase)
  setConfig(config)
  setUrl(url)
  appendOutput(line)
  setError(error)
  setStatus(status)
  reset()
}

// Helpers externes
export function startAppEmulator(projectDir: string): void
export function stopAppEmulator(): void
export function setupAppEmulatorListeners(): () => void
export function openAppEmulatorDialog(taskId?: string): void
```

---

## Étape 6 — Dialog Component (`apps/frontend/src/renderer/components/app-emulator/AppEmulatorDialog.tsx`)

**Nouveau fichier.** Dialog modale avec :

### Phase `idle` / `detecting`
- Spinner avec message "Detecting project type..."
- Auto-détection au mount

### Phase `starting`
- Spinner + logs du serveur en streaming
- Message "Starting dev server..."

### Phase `running`
- **Pour web apps** : iframe en pleine largeur avec la URL du serveur
- **Pour non-web** : terminal output scrollable
- Barre d'outils : Refresh, Open in Browser, Fullscreen, Stop
- Indicateur de port/URL

### Phase `error`
- Message d'erreur
- Bouton "Retry"

### Phase `stopped`
- Message "Server stopped"
- Bouton "Restart"

### Contrôles communs (footer)
- Stop / Close
- Open in Browser (lien externe)

---

## Étape 7 — i18n Translations

### `apps/frontend/src/shared/i18n/locales/en/appEmulator.json` (nouveau)
```json
{
  "title": "App Emulator",
  "description": "Preview your application directly from WorkPilot",
  "detecting": "Detecting project type...",
  "starting": "Starting development server...",
  "running": "Application is running",
  "stopped": "Server stopped",
  "actions": { "start", "stop", "refresh", "openInBrowser", "retry", "close", "fullscreen" },
  "status": { ... },
  "errors": { "noProject", "detectionFailed", "serverFailed", "portInUse" },
  "projectType": { "webReact", "webVue", ... },
  "serverInfo": { "port", "url", "command", "framework" }
}
```

### `apps/frontend/src/shared/i18n/locales/fr/appEmulator.json` (nouveau)
- Même structure, textes en français

### Modifications navigation (en + fr)
- Ajouter `"appEmulator": "App Emulator"` / `"appEmulator": "Émulateur d'application"`

### Modifications tasks (en + fr)
- Ajouter `"preview": "Preview"` dans `actions`
- Ajouter `"previewApp": "Preview application"` dans `tooltips`

### Modification i18n/index.ts
- Import + enregistrement du namespace `appEmulator`

---

## Étape 8 — Intégration Sidebar (`apps/frontend/src/renderer/components/Sidebar.tsx`)

**Modifications :**

1. `SidebarView` type → ajouter `'app-emulator'`
2. Groupe `ai-tools` → ajouter nav item :
   ```typescript
   { id: 'app-emulator', labelKey: 'navigation:items.appEmulator', icon: Monitor, shortcut: 'E' }
   ```
3. Import `openAppEmulatorDialog` du store
4. Import `AppEmulatorDialog` component
5. `handleNavClick` → ajouter case `'app-emulator'` → `openAppEmulatorDialog()`
6. Ajouter `<AppEmulatorDialog />` dans les dialogs AI Tools

---

## Étape 9 — Intégration TaskCard (`apps/frontend/src/renderer/components/TaskCard.tsx`)

**Modifications :**

1. Ajouter prop `onPreviewApp?: (taskId: string) => void` à `TaskCardProps`
2. Dans `ActionButtons`, pour `task.status === 'done'` : ajouter un bouton "Preview" (icône `Monitor`) avant le bouton Archive
3. Le bouton appelle `onPreviewApp(task.id)`
4. Mettre à jour `taskCardPropsAreEqual` pour comparer `onPreviewApp`

---

## Étape 10 — Intégration KanbanBoard (`apps/frontend/src/renderer/components/KanbanBoard.tsx`)

**Modifications :**

1. Ajouter prop `onPreviewApp` à `KanbanBoardProps` et `DroppableColumnProps`
2. Passer le handler à travers la hiérarchie Board → Column → TaskCard
3. Dans le composant parent (probablement `App.tsx` ou le conteneur Kanban) : connecter le handler pour ouvrir l'App Emulator dialog avec le task context

---

## Ordre d'implémentation

| # | Fichier | Action | Dépend de |
|---|---------|--------|-----------|
| 1 | `runners/app_emulator_runner.py` | Créer | — |
| 2 | `main/app-emulator-service.ts` | Créer | #1 |
| 3 | `ipc-handlers/app-emulator-handlers.ts` | Créer | #2 |
| 4 | `ipc-handlers/index.ts` | Modifier | #3 |
| 5 | `preload/api/modules/app-emulator-api.ts` | Créer | #3 |
| 6 | `preload/api/index.ts` | Modifier | #5 |
| 7 | `stores/app-emulator-store.ts` | Créer | #5 |
| 8 | `i18n/locales/en/appEmulator.json` | Créer | — |
| 9 | `i18n/locales/fr/appEmulator.json` | Créer | — |
| 10 | `i18n/locales/en/navigation.json` | Modifier | — |
| 11 | `i18n/locales/fr/navigation.json` | Modifier | — |
| 12 | `i18n/locales/en/tasks.json` | Modifier | — |
| 13 | `i18n/locales/fr/tasks.json` | Modifier | — |
| 14 | `i18n/index.ts` | Modifier | #8, #9 |
| 15 | `components/app-emulator/AppEmulatorDialog.tsx` | Créer | #7 |
| 16 | `components/Sidebar.tsx` | Modifier | #7, #15 |
| 17 | `components/TaskCard.tsx` | Modifier | #7 |
| 18 | `components/KanbanBoard.tsx` | Modifier | #17 |

## Fichiers créés (8)
- `apps/backend/runners/app_emulator_runner.py`
- `apps/frontend/src/main/app-emulator-service.ts`
- `apps/frontend/src/main/ipc-handlers/app-emulator-handlers.ts`
- `apps/frontend/src/preload/api/modules/app-emulator-api.ts`
- `apps/frontend/src/renderer/stores/app-emulator-store.ts`
- `apps/frontend/src/renderer/components/app-emulator/AppEmulatorDialog.tsx`
- `apps/frontend/src/shared/i18n/locales/en/appEmulator.json`
- `apps/frontend/src/shared/i18n/locales/fr/appEmulator.json`

## Fichiers modifiés (8)
- `apps/frontend/src/main/ipc-handlers/index.ts`
- `apps/frontend/src/preload/api/index.ts`
- `apps/frontend/src/shared/i18n/index.ts`
- `apps/frontend/src/shared/i18n/locales/en/navigation.json`
- `apps/frontend/src/shared/i18n/locales/fr/navigation.json`
- `apps/frontend/src/shared/i18n/locales/en/tasks.json`
- `apps/frontend/src/shared/i18n/locales/fr/tasks.json`
- `apps/frontend/src/renderer/components/Sidebar.tsx`
- `apps/frontend/src/renderer/components/TaskCard.tsx`
- `apps/frontend/src/renderer/components/KanbanBoard.tsx`
