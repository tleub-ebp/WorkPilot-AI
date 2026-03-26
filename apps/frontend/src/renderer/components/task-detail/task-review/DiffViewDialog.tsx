import { useState, useMemo, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Eye,
  FileCode,
  ChevronRight,
  ChevronDown,
  Folder,
  FolderOpen,
} from 'lucide-react';
import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '../../ui/alert-dialog';
import { Badge } from '../../ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../ui/select';
import { DiffViewer } from '../../ui/diff-viewer';
import { cn } from '../../../lib/utils';
import type { WorktreeDiff, WorktreeDiffFile } from '../../../../shared/types';

// ── Tree data structure ──────────────────────────────────────────────

interface TreeNode {
  name: string;
  path: string;
  isFolder: boolean;
  children: TreeNode[];
  file?: WorktreeDiffFile;
  additions: number;
  deletions: number;
}

function buildFileTree(files: WorktreeDiffFile[]): TreeNode[] {
  const root: TreeNode[] = [];

  for (const file of files) {
    const parts = file.path.replace(/\\/g, '/').split('/');
    let current = root;

    for (let i = 0; i < parts.length; i++) {
      const name = parts[i];
      const isLast = i === parts.length - 1;
      const partPath = parts.slice(0, i + 1).join('/');

      if (isLast) {
        current.push({
          name,
          path: partPath,
          isFolder: false,
          children: [],
          file,
          additions: file.additions,
          deletions: file.deletions,
        });
      } else {
        let folder = current.find((n) => n.isFolder && n.name === name);
        if (!folder) {
          folder = {
            name,
            path: partPath,
            isFolder: true,
            children: [],
            additions: 0,
            deletions: 0,
          };
          current.push(folder);
        }
        current = folder.children;
      }
    }
  }

  // Aggregate counts and sort recursively
  function processNode(nodes: TreeNode[]): void {
    for (const node of nodes) {
      if (node.isFolder) {
        processNode(node.children);
        node.additions = node.children.reduce((s, c) => s + c.additions, 0);
        node.deletions = node.children.reduce((s, c) => s + c.deletions, 0);
      }
    }
    nodes.sort((a, b) => {
      if (a.isFolder !== b.isFolder) return a.isFolder ? -1 : 1;
      return a.name.localeCompare(b.name);
    });
  }

  processNode(root);
  return root;
}

// ── Tree node component ──────────────────────────────────────────────

function FileTreeNode({
  node,
  depth,
  defaultExpanded,
  t,
  onFileClick,
}: {
  node: TreeNode;
  depth: number;
  defaultExpanded: boolean;
  t: (key: string) => string;
  onFileClick?: (file: WorktreeDiffFile) => void;
}) {
  const [expanded, setExpanded] = useState(defaultExpanded);

  const toggleExpanded = useCallback(() => setExpanded((v) => !v), []);

  if (node.isFolder) {
    return (
      <>
        {/* biome-ignore lint/a11y/noNoninteractiveElementInteractions lint/a11y/noStaticElementInteractions lint/a11y/useKeyWithClickEvents: interactive handler is intentional */}
        <div
          className="flex items-center justify-between p-1.5 rounded-lg hover:bg-secondary/50 transition-colors cursor-pointer select-none"
          style={{ paddingLeft: depth * 16 + 8 }}
          onClick={toggleExpanded}
        >
          <div className="flex items-center gap-1.5 min-w-0 flex-1">
            {expanded ? (
              <ChevronDown className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
            ) : (
              <ChevronRight className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
            )}
            {expanded ? (
              <FolderOpen className="h-4 w-4 shrink-0 text-amber-400" />
            ) : (
              <Folder className="h-4 w-4 shrink-0 text-amber-400" />
            )}
            <span className="text-sm font-medium truncate">{node.name}</span>
          </div>
          <div className="flex items-center gap-2 shrink-0 ml-2">
            <span className="text-xs text-success">+{node.additions}</span>
            <span className="text-xs text-destructive">-{node.deletions}</span>
          </div>
        </div>
        {expanded &&
          node.children.map((child) => (
            <FileTreeNode
              key={child.path}
              node={child}
              depth={depth + 1}
              defaultExpanded={false}
              t={t}
              onFileClick={onFileClick}
            />
          ))}
      </>
    );
  }

  // biome-ignore lint/style/noNonNullAssertion: value is guaranteed by context
  const file = node.file!;
  return (
    // biome-ignore lint/a11y/noNoninteractiveElementInteractions: interactive handler is intentional
    // biome-ignore lint/a11y/noStaticElementInteractions: interactive handler is intentional
    // biome-ignore lint/a11y/useKeyWithClickEvents: keyboard events handled elsewhere
    <div
      className="flex items-center justify-between p-1.5 rounded-lg bg-secondary/30 hover:bg-secondary/50 transition-colors cursor-pointer"
      style={{ paddingLeft: depth * 16 + 8 }}
      onClick={() => onFileClick?.(file)}
    >
      <div className="flex items-center gap-1.5 min-w-0 flex-1">
        <span className="w-3.5 shrink-0" />
        <FileCode
          className={cn(
            'h-4 w-4 shrink-0',
            file.status === 'added' && 'text-success',
            file.status === 'deleted' && 'text-destructive',
            file.status === 'modified' && 'text-info',
            file.status === 'renamed' && 'text-warning'
          )}
        />
        <span className="text-sm font-mono truncate">{node.name}</span>
      </div>
      <div className="flex items-center gap-2 shrink-0 ml-2">
        <Badge
          variant="secondary"
          className={cn(
            'text-xs',
            file.status === 'added' && 'bg-success/10 text-success',
            file.status === 'deleted' && 'bg-destructive/10 text-destructive',
            file.status === 'modified' && 'bg-info/10 text-info',
            file.status === 'renamed' && 'bg-warning/10 text-warning'
          )}
        >
          {t(`taskReview:diff.status.${file.status}`)}
        </Badge>
        <span className="text-xs text-success">+{file.additions}</span>
        <span className="text-xs text-destructive">-{file.deletions}</span>
      </div>
    </div>
  );
}

// ── Main dialog ──────────────────────────────────────────────────────

type ViewMode = 'list' | 'tree';

interface DiffViewDialogProps {
  open: boolean;
  worktreeDiff: WorktreeDiff | null;
  onOpenChange: (open: boolean) => void;
}

/**
 * Dialog displaying the list of changed files with their status and line changes.
 * Supports flat list and tree view modes, switchable via a dropdown.
 */
export function DiffViewDialog({
  open,
  worktreeDiff,
  onOpenChange,
}: DiffViewDialogProps) {
  const { t } = useTranslation(['taskReview']);
  const [viewMode, setViewMode] = useState<ViewMode>('list');
  const [selectedFile, setSelectedFile] = useState<WorktreeDiffFile | null>(null);

  const tree = useMemo(
    () => (worktreeDiff?.files ? buildFileTree(worktreeDiff.files) : []),
    [worktreeDiff?.files]
  );

  const hasFiles = worktreeDiff?.files && worktreeDiff.files.length > 0;

  const handleFileClick = useCallback((file: WorktreeDiffFile) => {
    setSelectedFile(file);
  }, []);

  const handleBackToList = useCallback(() => {
    setSelectedFile(null);
  }, []);

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent className="max-w-7xl max-h-[95vh] w-[95vw] h-[90vh] overflow-hidden flex flex-col">
        <AlertDialogHeader>
          <div className="flex items-center justify-between">
            <AlertDialogTitle className="flex items-center gap-2">
              {selectedFile ? (
                <>
                  <button type="button"
                    onClick={handleBackToList}
                    className="mr-2 p-1 hover:bg-muted rounded transition-colors"
                    title={t('taskReview:diff.backToList')}
                  >
                    <ChevronRight className="h-4 w-4 rotate-180" />
                  </button>
                  <FileCode className="h-5 w-5 text-blue-400" />
                  {selectedFile.path.split('/').pop()}
                </>
              ) : (
                <>
                  <Eye className="h-5 w-5 text-purple-400" />
                  {t('taskReview:diff.title')}
                </>
              )}
            </AlertDialogTitle>
            {!selectedFile && hasFiles && (
              <Select
                value={viewMode}
                onValueChange={(v) => setViewMode(v as ViewMode)}
              >
                <SelectTrigger className="w-[140px] h-8 text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="list">
                    {t('taskReview:diff.flatList')}
                  </SelectItem>
                  <SelectItem value="tree">
                    {t('taskReview:diff.treeView')}
                  </SelectItem>
                </SelectContent>
              </Select>
            )}
          </div>
          <AlertDialogDescription>
            {selectedFile 
              ? `${selectedFile.path} - ${t(`taskReview:diff.status.${selectedFile.status}`)} (+${selectedFile.additions}, -${selectedFile.deletions})`
              : worktreeDiff?.summary || t('taskReview:diff.noChanges')
            }
          </AlertDialogDescription>
        </AlertDialogHeader>

        <div className="flex-1 overflow-auto min-h-0 -mx-6 px-6">
          {selectedFile ? (
            <div className="h-full">
              <DiffViewer 
                patch={selectedFile.patch || ''} 
                className="h-full max-h-[75vh] overflow-auto border rounded"
              />
            </div>
          ) : hasFiles ? (
            viewMode === 'list' ? (
              <div className="space-y-2">
                {worktreeDiff?.files.map((file, idx) => (
                  // biome-ignore lint/a11y/noNoninteractiveElementInteractions: interactive handler is intentional
                  // biome-ignore lint/a11y/noStaticElementInteractions: interactive handler is intentional
                  // biome-ignore lint/a11y/useKeyWithClickEvents: keyboard events handled elsewhere
                  <div
                    // biome-ignore lint/suspicious/noArrayIndexKey: no stable key available
                    key={idx}
                    className="flex items-center justify-between p-2 rounded-lg bg-secondary/30 hover:bg-secondary/50 transition-colors cursor-pointer"
                    onClick={() => handleFileClick(file)}
                  >
                    <div className="flex items-center gap-2 min-w-0 flex-1">
                      <FileCode
                        className={cn(
                          'h-4 w-4 shrink-0',
                          file.status === 'added' && 'text-success',
                          file.status === 'deleted' && 'text-destructive',
                          file.status === 'modified' && 'text-info',
                          file.status === 'renamed' && 'text-warning'
                        )}
                      />
                      <span className="text-sm font-mono truncate">
                        {file.path}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 shrink-0 ml-2">
                      <Badge
                        variant="secondary"
                        className={cn(
                          'text-xs',
                          file.status === 'added' &&
                            'bg-success/10 text-success',
                          file.status === 'deleted' &&
                            'bg-destructive/10 text-destructive',
                          file.status === 'modified' && 'bg-info/10 text-info',
                          file.status === 'renamed' &&
                            'bg-warning/10 text-warning'
                        )}
                      >
                        {t(`taskReview:diff.status.${file.status}`)}
                      </Badge>
                      <span className="text-xs text-success">
                        +{file.additions}
                      </span>
                      <span className="text-xs text-destructive">
                        -{file.deletions}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="space-y-0.5">
                {tree.map((node) => (
                  <FileTreeNode
                    key={node.path}
                    node={node}
                    depth={0}
                    defaultExpanded={true}
                    t={t}
                    onFileClick={handleFileClick}
                  />
                ))}
              </div>
            )
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              {t('taskReview:diff.noFiles')}
            </div>
          )}
        </div>

        <AlertDialogFooter className="mt-4">
          <AlertDialogCancel>{t('taskReview:diff.close')}</AlertDialogCancel>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
