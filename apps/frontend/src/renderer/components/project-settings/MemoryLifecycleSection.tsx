import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Scissors, Download, RefreshCw, Loader2 } from 'lucide-react';
import { Label } from '../ui/label';
import { Input } from '../ui/input';
import { Switch } from '../ui/switch';
import { Button } from '../ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Separator } from '../ui/separator';
import { useMemoryLifecycleStore, type PruneStrategy } from '../../stores/memory-lifecycle-store';

interface MemoryLifecycleSectionProps {
  projectPath: string;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function MemoryLifecycleSection({ projectPath }: MemoryLifecycleSectionProps) {
  const { t } = useTranslation('settings');
  const {
    status,
    isLoading,
    isPruning,
    error,
    loadStatus,
    runPrune,
    setPolicy,
    exportMemories,
    clearError,
  } = useMemoryLifecycleStore();

  const [pruneResult, setPruneResult] = useState<{ pruned: number; remaining: number } | null>(null);
  const [exportPath, setExportPath] = useState<string | null>(null);

  const [retentionDays, setRetentionDays] = useState(90);
  const [maxEpisodes, setMaxEpisodes] = useState(10000);
  const [pruneStrategy, setPruneStrategy] = useState<PruneStrategy>('lru');
  const [autoPrune, setAutoPrune] = useState(false);

  useEffect(() => {
    if (projectPath) loadStatus(projectPath);
  }, [projectPath, loadStatus]);

  // Sync local state when status loads
  useEffect(() => {
    if (!status) return;
    setRetentionDays(status.retention_days);
    setMaxEpisodes(status.max_episodes);
    setPruneStrategy(status.prune_strategy);
    setAutoPrune(status.auto_prune);
  }, [status]);

  const handleRunPrune = async () => {
    setPruneResult(null);
    const result = await runPrune(projectPath, { strategy: pruneStrategy });
    if (result) {
      setPruneResult(result);
      loadStatus(projectPath);
    }
  };

  const handleExport = async () => {
    setExportPath(null);
    const ts = new Date().toISOString().slice(0, 19).replace(/[:.]/g, '-');
    const outputPath = `${projectPath}/.workpilot/memory-export-${ts}.json`;
    const result = await exportMemories(projectPath, outputPath);
    if (result) setExportPath(result.path);
  };

  return (
    <div className="space-y-4">
      <Separator />

      <div className="flex items-center justify-between">
        <div>
          <h4 className="text-sm font-semibold text-foreground">{t('memoryLifecycle.title')}</h4>
          <p className="text-xs text-muted-foreground mt-0.5">{t('memoryLifecycle.description')}</p>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => loadStatus(projectPath)}
          disabled={isLoading}
          className="h-7 px-2"
        >
          <RefreshCw className={`h-3 w-3 ${isLoading ? 'animate-spin' : ''}`} />
        </Button>
      </div>

      {/* Status */}
      {isLoading && !status ? (
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Loader2 className="h-3 w-3 animate-spin" />
          <span>{t('memoryLifecycle.status')}…</span>
        </div>
      ) : status ? (
        <div className="grid grid-cols-2 gap-3 rounded-md border border-border bg-muted/30 p-3">
          <div>
            <p className="text-xs text-muted-foreground">{t('memoryLifecycle.episodeCount')}</p>
            <p className="text-sm font-medium">{status.episode_count.toLocaleString()}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">{t('memoryLifecycle.diskUsage')}</p>
            <p className="text-sm font-medium">{formatBytes(status.disk_usage_bytes)}</p>
          </div>
        </div>
      ) : null}

      {/* Retention policy */}
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-1">
          <Label className="text-xs text-muted-foreground">{t('memoryLifecycle.retentionDays')}</Label>
          <Input
            type="number"
            min={1}
            value={retentionDays}
            onChange={(e) => setRetentionDays(Number(e.target.value) || 1)}
            onBlur={(e) => setPolicy(projectPath, { retention_days: Number(e.target.value) || 90 })}
          />
        </div>
        <div className="space-y-1">
          <Label className="text-xs text-muted-foreground">{t('memoryLifecycle.maxEpisodes')}</Label>
          <Input
            type="number"
            min={1}
            value={maxEpisodes}
            onChange={(e) => setMaxEpisodes(Number(e.target.value) || 1)}
            onBlur={(e) => setPolicy(projectPath, { max_episodes: Number(e.target.value) || 10000 })}
          />
        </div>
      </div>

      {/* Prune strategy */}
      <div className="space-y-1">
        <Label className="text-xs text-muted-foreground">{t('memoryLifecycle.pruneStrategy')}</Label>
        <Select
          value={pruneStrategy}
          onValueChange={(v) => {
            setPruneStrategy(v as PruneStrategy);
            setPolicy(projectPath, { prune_strategy: v as PruneStrategy });
          }}
        >
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="lru">{t('memoryLifecycle.pruneStrategies.lru')}</SelectItem>
            <SelectItem value="oldest">{t('memoryLifecycle.pruneStrategies.oldest')}</SelectItem>
            <SelectItem value="duplicates">{t('memoryLifecycle.pruneStrategies.duplicates')}</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Auto-prune */}
      <div className="flex items-center justify-between">
        <Label className="font-normal text-foreground">{t('memoryLifecycle.autoPrune')}</Label>
        <Switch
          checked={autoPrune}
          onCheckedChange={(checked) => {
            setAutoPrune(checked);
            setPolicy(projectPath, { auto_prune: checked });
          }}
        />
      </div>

      {/* Action buttons */}
      <div className="flex gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={handleRunPrune}
          disabled={isPruning}
          className="flex-1"
        >
          {isPruning ? (
            <Loader2 className="h-3 w-3 animate-spin mr-2" />
          ) : (
            <Scissors className="h-3 w-3 mr-2" />
          )}
          {t('memoryLifecycle.runPrune')}
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={handleExport}
          className="flex-1"
        >
          <Download className="h-3 w-3 mr-2" />
          {t('memoryLifecycle.export')}
        </Button>
      </div>

      {pruneResult && (
        <div className="rounded-md bg-success/10 p-2 text-xs text-success">
          Pruned {pruneResult.pruned} · {pruneResult.remaining} remaining
        </div>
      )}
      {exportPath && (
        <div className="rounded-md bg-success/10 p-2 text-xs text-success break-all">
          Exported → {exportPath}
        </div>
      )}
      {error && (
        <div className="flex items-center justify-between rounded-md bg-destructive/10 p-2 text-xs text-destructive">
          <span>{error}</span>
          <button type="button" onClick={clearError} className="ml-2 hover:opacity-70">✕</button>
        </div>
      )}
    </div>
  );
}
