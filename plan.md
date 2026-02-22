# Plan: Add Tree View to DiffViewDialog

## Goal
Add a tree view mode to the changed files listing in `DiffViewDialog.tsx`, with a Select dropdown to switch between flat list and tree view.

## Steps

### 1. Add i18n keys for the diff view
**Files:** `apps/frontend/src/shared/i18n/locales/en/taskReview.json`, `apps/frontend/src/shared/i18n/locales/fr/taskReview.json`

Add a new `"diff"` section with keys:
- `diff.title` — "Changed Files" / "Fichiers modifiés"
- `diff.noChanges` — "No changes found" / "Aucun changement trouvé"
- `diff.noFiles` — "No changed files found" / "Aucun fichier modifié trouvé"
- `diff.close` — "Close" / "Fermer"
- `diff.viewMode` — "View" / "Vue"
- `diff.flatList` — "Flat list" / "Liste plate"
- `diff.treeView` — "Tree view" / "Vue arborescente"
- `diff.status.added` — "added" / "ajouté"
- `diff.status.deleted` — "deleted" / "supprimé"
- `diff.status.modified` — "modified" / "modifié"
- `diff.status.renamed` — "renamed" / "renommé"

### 2. Create a `buildFileTree` utility function
**File:** `apps/frontend/src/renderer/components/task-detail/task-review/DiffViewDialog.tsx` (inline)

- Takes `WorktreeDiffFile[]` as input
- Converts flat paths into a hierarchical tree structure
- Each tree node has: `name`, `path`, `children[]`, `isFolder`, and optionally `file` (for leaf nodes)
- Folder nodes aggregate `additions` and `deletions` from their children
- Sort: folders first (alphabetical), then files (alphabetical)

### 3. Create a `FileTreeNode` inline component
**File:** Same `DiffViewDialog.tsx`

- Renders a single tree node (folder or file)
- Folders: clickable to expand/collapse with ChevronRight/ChevronDown + Folder/FolderOpen icons
- Files: FileCode icon with status badge and +/- stats (same styling as current flat list)
- Depth-based indentation (`paddingLeft: depth * 16 + 8`)
- Recursive rendering for children
- Root-level folders start expanded by default

### 4. Modify `DiffViewDialog` to support both views
**File:** `DiffViewDialog.tsx`

- Add `viewMode` state (`'list' | 'tree'`, default `'list'`)
- Add a compact `Select` dropdown in the dialog header (next to title) to switch view modes
- When `viewMode === 'list'`: render the existing flat list (with i18n applied)
- When `viewMode === 'tree'`: render the tree view using `buildFileTree()` + `FileTreeNode`
- Replace all hardcoded English strings with `t()` calls using the new i18n keys
