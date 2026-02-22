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
}: {
  node: TreeNode;
  depth: number;
  defaultExpanded: boolean;
  t: (key: string) => string;
}) {
  const [expanded, setExpanded] = useState(defaultExpanded);

  const toggleExpanded = useCallback(() => setExpanded((v) => !v), []);

  if (node.isFolder) {
    return (
      <>
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
            />
          ))}
      </>
    );
  }

  const file = node.file!;
  return (
    <div
      className="flex items-center justify-between p-1.5 rounded-lg bg-secondary/30 hover:bg-secondary/50 transition-colors"
      style={{ paddingLeft: depth * 16 + 8 }}
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

  const tree = useMemo(
    () => (worktreeDiff?.files ? buildFileTree(worktreeDiff.files) : []),
    [worktreeDiff?.files]
  );

  const hasFiles = worktreeDiff?.files && worktreeDiff.files.length > 0;

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent className="max-w-2xl max-h-[80vh] overflow-hidden flex flex-col">
        <AlertDialogHeader>
          <div className="flex items-center justify-between">
            <AlertDialogTitle className="flex items-center gap-2">
              <Eye className="h-5 w-5 text-purple-400" />
              {t('taskReview:diff.title')}
            </AlertDialogTitle>
            {hasFiles && (
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
            {worktreeDiff?.summary || t('taskReview:diff.noChanges')}
          </AlertDialogDescription>
        </AlertDialogHeader>

        <div className="flex-1 overflow-auto min-h-0 -mx-6 px-6">
          {hasFiles ? (
            viewMode === 'list' ? (
              <div className="space-y-2">
                {worktreeDiff!.files.map((file, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between p-2 rounded-lg bg-secondary/30 hover:bg-secondary/50 transition-colors"
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
