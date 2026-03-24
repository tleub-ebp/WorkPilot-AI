import { useEffect, useRef, useCallback } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import { FileTreeItem } from './FileTreeItem';
import { useFileExplorerStore } from '../stores/file-explorer-store';
import { useVirtualizedTree } from '../hooks/useVirtualizedTree';
import { Loader2, AlertCircle, FolderOpen } from 'lucide-react';

interface FileTreeProps {
  rootPath: string;
}

// Estimated height of each tree item in pixels
const ITEM_HEIGHT = 28;
// Number of items to render outside the visible area for smoother scrolling
const OVERSCAN = 10;

export function FileTree({ rootPath, onSelectFolder, selectedFolder }: FileTreeProps & { onSelectFolder?: (path: string) => void, selectedFolder?: string }) {
  const parentRef = useRef<HTMLDivElement>(null);

  const {
    loadDirectory,
    isLoadingDir,
    error
  } = useFileExplorerStore();

  const {
    flattenedNodes,
    count,
    handleToggle,
    isRootLoading,
    hasRootFiles
  } = useVirtualizedTree(rootPath);

  const loading = isLoadingDir(rootPath);

  // Load root directory on mount
  useEffect(() => {
    if (!hasRootFiles && !loading) {
      loadDirectory(rootPath);
    }
  }, [rootPath, hasRootFiles, loading, loadDirectory]);

  // Set up the virtualizer
  const rowVirtualizer = useVirtualizer({
    count,
    getScrollElement: () => parentRef.current,
    estimateSize: () => ITEM_HEIGHT,
    overscan: OVERSCAN,
  });

  // Create toggle handler for each item
  const createToggleHandler = useCallback(
    (index: number) => {
      return () => {
        const item = flattenedNodes[index];
        if (item) {
          handleToggle(item.node);
        }
      };
    },
    [flattenedNodes, handleToggle]
  );

  // Ajout d'un bouton pour naviguer vers le dossier parent
  if (rootPath !== "C:\\" && rootPath !== "/") {
    return (
      <div>
        <button className="mb-2 px-2 py-1 border rounded bg-muted" onClick={() => {
          // Navigue vers le parent
          const parent = rootPath.replace(/\\$/, "");
          const parentPath = parent.substring(0, parent.lastIndexOf("\\")) || "C:\\";
          onSelectFolder?.(parentPath);
        }}>⬆ Parent</button>
        {/* The large inner element to hold all of the items */}
        <div
          style={{
            height: `${rowVirtualizer.getTotalSize()}px`,
            width: '100%',
            position: 'relative',
          }}
        >
          {/* Only the visible items in the virtualizer */}
          {rowVirtualizer.getVirtualItems().map((virtualItem) => {
            const item = flattenedNodes[virtualItem.index];
            if (!item) return null;

            return (
              <div
                key={item.key}
                style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  width: '100%',
                  height: `${virtualItem.size}px`,
                  transform: `translateY(${virtualItem.start}px)`,
                }}
              >
                {/* Passe selectedFolder à FileTreeItem pour le highlight */}
                <FileTreeItem
                  node={item.node}
                  depth={item.depth}
                  isExpanded={item.isExpanded}
                  isLoading={item.isLoading}
                  onToggle={createToggleHandler(virtualItem.index)}
                  onSelectFolder={onSelectFolder}
                  selectedFolder={selectedFolder}
                />
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  if (isRootLoading && !hasRootFiles) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-8 px-4 text-center">
        <AlertCircle className="h-5 w-5 text-destructive mb-2" />
        <p className="text-xs text-destructive">{error}</p>
      </div>
    );
  }

  // Ajout d'un feedback d'erreur explicite dans FileTree si aucun dossier n'est trouvé ou si l'API échoue
  if (!hasRootFiles || count === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-8 px-4 text-center">
        <FolderOpen className="h-6 w-6 text-muted-foreground mb-2" />
        <p className="text-xs text-muted-foreground">
          Aucun dossier trouvé.<br />
          Vérifiez le chemin ou vos droits d'accès.<br />
          Racine actuelle : {rootPath}
        </p>
      </div>
    );
  }

  return (
    <div
      ref={parentRef}
      className="h-full overflow-auto py-1"
      style={{ maxHeight: '100vh', overflowY: 'auto' }}
    >
      {/* The large inner element to hold all of the items */}
      <div
        style={{
          height: `${rowVirtualizer.getTotalSize()}px`,
          width: '100%',
          position: 'relative',
        }}
      >
        {/* Only the visible items in the virtualizer */}
        {rowVirtualizer.getVirtualItems().map((virtualItem) => {
          const item = flattenedNodes[virtualItem.index];
          if (!item) return null;

          return (
            <div
              key={item.key}
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                height: `${virtualItem.size}px`,
                transform: `translateY(${virtualItem.start}px)`,
              }}
            >
              {/* Passe selectedFolder à FileTreeItem pour le highlight */}
              <FileTreeItem
                node={item.node}
                depth={item.depth}
                isExpanded={item.isExpanded}
                isLoading={item.isLoading}
                onToggle={createToggleHandler(virtualItem.index)}
                onSelectFolder={onSelectFolder}
                selectedFolder={selectedFolder}
              />
            </div>
          );
        })}
      </div>
    </div>
  );
}