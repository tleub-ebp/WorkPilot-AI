import { useState, useEffect } from 'react';
import { GitMerge, GitBranch, Loader2, CheckCircle, AlertTriangle } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../../ui/dialog';
import { Button } from '../../ui/button';
import { Label } from '../../ui/label';
import { Combobox } from '../../ui/combobox';
import { buildBranchOptions } from '../../../lib/branch-utils';
import type { Task } from '../../../../shared/types';

type Strategy = 'merge' | 'rebase';

interface SyncFromBranchDialogProps {
  open: boolean;
  task: Task;
  projectPath: string;
  onOpenChange: (open: boolean) => void;
}

export function SyncFromBranchDialog({
  open,
  task,
  projectPath,
  onOpenChange,
}: SyncFromBranchDialogProps) {
  const { t } = useTranslation(['taskReview', 'common']);
  const [sourceBranch, setSourceBranch] = useState('');
  const [strategy, setStrategy] = useState<Strategy>('merge');
  const [branches, setBranches] = useState<{ name: string; displayName: string; type: 'local' | 'remote' }[]>([]);
  const [isLoadingBranches, setIsLoadingBranches] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [result, setResult] = useState<{ success: boolean; message: string; conflictFiles?: string[] } | null>(null);

  // Load branches when dialog opens
  useEffect(() => {
    if (!open) {
      setResult(null);
      setSourceBranch('');
      setIsSyncing(false);
      return;
    }

    let isMounted = true;
    setIsLoadingBranches(true);

    globalThis.electronAPI.getGitBranchesWithInfo(projectPath)
      .then((res) => {
        if (!isMounted) return;
        if (res.success && res.data) {
          setBranches(res.data);
        }
      })
      .catch((err: unknown) => {
        console.error('[SyncFromBranchDialog] Failed to fetch branches:', err);
      })
      .finally(() => {
        if (isMounted) setIsLoadingBranches(false);
      });

    return () => { isMounted = false; };
  }, [open, projectPath]);

  const branchOptions = buildBranchOptions(branches, { t });

  const handleSync = async () => {
    if (!sourceBranch) return;
    setIsSyncing(true);
    setResult(null);

    try {
      const res = await globalThis.electronAPI.syncWorktreeFromBranch(task.id, sourceBranch, strategy);
      if (res.success && res.data?.success) {
        setResult({ success: true, message: res.data.message });
      } else {
        setResult({
          success: false,
          message: res.data?.message || res.error || t('taskReview:syncBranch.errors.unknown'),
          conflictFiles: res.data?.conflictFiles,
        });
      }
    } catch (err) {
      setResult({
        success: false,
        message: err instanceof Error ? err.message : t('taskReview:syncBranch.errors.unknown'),
      });
    } finally {
      setIsSyncing(false);
    }
  };

  const canSync = !!sourceBranch && !isSyncing && !result?.success;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[480px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <GitMerge className="h-5 w-5 text-primary" />
            {t('taskReview:syncBranch.title')}
          </DialogTitle>
          <DialogDescription>
            {t('taskReview:syncBranch.description', { branch: task.title })}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* Source branch selector */}
          <div className="space-y-2">
            <Label htmlFor="sync-source-branch">
              {t('taskReview:syncBranch.sourceBranchLabel')}
            </Label>
            <Combobox
              id="sync-source-branch"
              value={sourceBranch}
              onValueChange={setSourceBranch}
              options={branchOptions}
              placeholder={isLoadingBranches ? t('taskReview:syncBranch.loadingBranches') : t('taskReview:syncBranch.selectBranch')}
              searchPlaceholder={t('taskReview:syncBranch.searchBranch')}
              emptyMessage={t('taskReview:syncBranch.noBranchFound')}
              disabled={isLoadingBranches || isSyncing}
              className="w-full"
            />
          </div>

          {/* Strategy selector */}
          <div className="space-y-2">
            <Label>{t('taskReview:syncBranch.strategyLabel')}</Label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setStrategy('merge')}
                disabled={isSyncing}
                className={`flex items-start gap-2 rounded-lg border p-3 text-left transition-colors ${
                  strategy === 'merge'
                    ? 'border-primary bg-primary/10 text-foreground'
                    : 'border-border bg-background text-muted-foreground hover:border-primary/50 hover:bg-muted/50'
                }`}
              >
                <GitMerge className="h-4 w-4 mt-0.5 shrink-0" />
                <div>
                  <p className="text-sm font-medium">{t('taskReview:syncBranch.strategies.merge.label')}</p>
                  <p className="text-xs mt-0.5">{t('taskReview:syncBranch.strategies.merge.description')}</p>
                </div>
              </button>
              <button
                type="button"
                onClick={() => setStrategy('rebase')}
                disabled={isSyncing}
                className={`flex items-start gap-2 rounded-lg border p-3 text-left transition-colors ${
                  strategy === 'rebase'
                    ? 'border-primary bg-primary/10 text-foreground'
                    : 'border-border bg-background text-muted-foreground hover:border-primary/50 hover:bg-muted/50'
                }`}
              >
                <GitBranch className="h-4 w-4 mt-0.5 shrink-0" />
                <div>
                  <p className="text-sm font-medium">{t('taskReview:syncBranch.strategies.rebase.label')}</p>
                  <p className="text-xs mt-0.5">{t('taskReview:syncBranch.strategies.rebase.description')}</p>
                </div>
              </button>
            </div>
          </div>

          {/* Result feedback */}
          {result && (
            <div className={`flex items-start gap-2 p-3 rounded-lg border ${
              result.success
                ? 'bg-success/10 border-success/20'
                : 'bg-destructive/10 border-destructive/20'
            }`}>
              {result.success ? (
                <CheckCircle className="h-4 w-4 text-success mt-0.5 shrink-0" />
              ) : (
                <AlertTriangle className="h-4 w-4 text-destructive mt-0.5 shrink-0" />
              )}
              <div className="flex-1 min-w-0">
                <p className={`text-sm font-medium ${result.success ? 'text-success' : 'text-destructive'}`}>
                  {result.message}
                </p>
                {result.conflictFiles && result.conflictFiles.length > 0 && (
                  <ul className="mt-2 text-xs text-muted-foreground space-y-0.5">
                    {result.conflictFiles.slice(0, 8).map((f) => (
                      <li key={f} className="truncate font-mono">• {f}</li>
                    ))}
                    {result.conflictFiles.length > 8 && (
                      <li className="text-muted-foreground">
                        {t('taskReview:syncBranch.moreConflicts', { count: result.conflictFiles.length - 8 })}
                      </li>
                    )}
                  </ul>
                )}
              </div>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)} disabled={isSyncing}>
            {result?.success ? t('common:buttons.close') : t('common:buttons.cancel')}
          </Button>
          <Button
            variant="default"
            onClick={handleSync}
            disabled={!canSync}
          >
            {isSyncing ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                {t('taskReview:syncBranch.syncing')}
              </>
            ) : (
              <>
                <GitMerge className="mr-2 h-4 w-4" />
                {t('taskReview:syncBranch.syncButton', { strategy: t(`taskReview:syncBranch.strategies.${strategy}.label`) })}
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
