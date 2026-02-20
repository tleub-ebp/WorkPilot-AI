import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Shield, Plus, Trash2, FolderOpen, Lock, AlertTriangle, RotateCcw } from 'lucide-react';
import { SettingsSection } from './SettingsSection';
import { cn } from '@/lib/utils';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type SandboxMode = 'normal' | 'restricted' | 'dry_run' | 'docker';

interface PathRule {
  path: string;
  access: 'read' | 'write';
}

interface ResourceLimits {
  cpu_percent: number;
  memory_mb: number;
  execution_time_s: number;
  max_files_written: number;
  max_file_size_mb: number;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function SandboxSettings() {
  const { t } = useTranslation('settings');

  const [mode, setMode] = useState<SandboxMode>('normal');
  const [allowedPaths, setAllowedPaths] = useState<PathRule[]>([
    { path: 'src/', access: 'write' },
    { path: 'tests/', access: 'write' },
  ]);
  const [newPath, setNewPath] = useState('');
  const [newAccess, setNewAccess] = useState<'read' | 'write'>('write');
  const [limits, setLimits] = useState<ResourceLimits>({
    cpu_percent: 80,
    memory_mb: 2048,
    execution_time_s: 300,
    max_files_written: 100,
    max_file_size_mb: 10,
  });

  const handleAddPath = () => {
    if (!newPath.trim()) return;
    setAllowedPaths((prev) => [...prev, { path: newPath.trim(), access: newAccess }]);
    setNewPath('');
  };

  const handleRemovePath = (index: number) => {
    setAllowedPaths((prev) => prev.filter((_, i) => i !== index));
  };

  const handleLimitChange = (key: keyof ResourceLimits, value: number) => {
    setLimits((prev) => ({ ...prev, [key]: value }));
  };

  const modes: { id: SandboxMode; label: string; desc: string }[] = [
    { id: 'normal', label: 'Normal', desc: 'Whitelist + resource limits' },
    { id: 'restricted', label: 'Restricted', desc: 'Strict whitelist, reduced limits' },
    { id: 'dry_run', label: 'Dry-run', desc: 'Plan only, no file changes' },
    { id: 'docker', label: 'Docker', desc: 'Full container isolation' },
  ];

  return (
    <SettingsSection
      title="Sandbox"
      description="Configure agent execution isolation, file access whitelist, resource limits, and rollback behavior."
    >
      <div className="space-y-8">
        {/* Sandbox Mode */}
        <div>
          <h4 className="text-sm font-semibold mb-1 flex items-center gap-2">
            <Shield className="h-4 w-4 text-primary" />
            Default Sandbox Mode
          </h4>
          <p className="text-xs text-muted-foreground mb-3">
            Choose the default isolation mode for agent execution.
          </p>
          <div className="grid grid-cols-2 gap-3">
            {modes.map((m) => (
              <button
                key={m.id}
                onClick={() => setMode(m.id)}
                className={cn(
                  'flex flex-col items-start gap-1 rounded-lg border p-3 text-left transition-colors',
                  mode === m.id
                    ? 'border-primary bg-primary/5 ring-1 ring-primary'
                    : 'border-border hover:bg-accent/50'
                )}
              >
                <span className="text-sm font-medium">{m.label}</span>
                <span className="text-xs text-muted-foreground">{m.desc}</span>
              </button>
            ))}
          </div>
        </div>

        {/* File Access Whitelist */}
        <div>
          <h4 className="text-sm font-semibold mb-1 flex items-center gap-2">
            <FolderOpen className="h-4 w-4 text-primary" />
            File Access Whitelist
          </h4>
          <p className="text-xs text-muted-foreground mb-3">
            Paths agents are allowed to access. Sensitive paths (.git/, .env, .ssh/) are always blocked.
          </p>
          <div className="space-y-2">
            {allowedPaths.map((rule, i) => (
              <div key={i} className="flex items-center gap-2 rounded-md border border-border px-3 py-2 text-sm">
                <FolderOpen className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                <span className="flex-1 font-mono text-xs">{rule.path}</span>
                <span className={cn(
                  'rounded-full px-2 py-0.5 text-[10px] font-medium',
                  rule.access === 'write' ? 'bg-amber-500/15 text-amber-600' : 'bg-blue-500/15 text-blue-600'
                )}>
                  {rule.access === 'write' ? 'Read/Write' : 'Read Only'}
                </span>
                <button onClick={() => handleRemovePath(i)} className="text-muted-foreground hover:text-destructive">
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            ))}
            <div className="flex items-center gap-2">
              <input
                value={newPath}
                onChange={(e) => setNewPath(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleAddPath()}
                placeholder="e.g. lib/ or config/app.json"
                className="flex-1 rounded-md border border-border bg-background px-3 py-1.5 text-sm placeholder:text-muted-foreground outline-none focus:ring-1 focus:ring-primary"
              />
              <select
                value={newAccess}
                onChange={(e) => setNewAccess(e.target.value as 'read' | 'write')}
                className="rounded-md border border-border bg-background px-2 py-1.5 text-sm outline-none"
              >
                <option value="read">Read</option>
                <option value="write">Write</option>
              </select>
              <button
                onClick={handleAddPath}
                disabled={!newPath.trim()}
                className="flex items-center gap-1 rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground disabled:opacity-50"
              >
                <Plus className="h-3.5 w-3.5" />
                Add
              </button>
            </div>
          </div>
        </div>

        {/* Resource Limits */}
        <div>
          <h4 className="text-sm font-semibold mb-1 flex items-center gap-2">
            <Lock className="h-4 w-4 text-primary" />
            Resource Limits
          </h4>
          <p className="text-xs text-muted-foreground mb-3">
            Maximum resources an agent can consume per execution.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {[
              { key: 'cpu_percent' as const, label: 'CPU (%)', min: 10, max: 100, step: 5 },
              { key: 'memory_mb' as const, label: 'RAM (MB)', min: 256, max: 8192, step: 256 },
              { key: 'execution_time_s' as const, label: 'Max Time (s)', min: 30, max: 3600, step: 30 },
              { key: 'max_files_written' as const, label: 'Max Files', min: 1, max: 500, step: 10 },
              { key: 'max_file_size_mb' as const, label: 'Max File Size (MB)', min: 1, max: 100, step: 1 },
            ].map(({ key, label, min, max, step }) => (
              <div key={key} className="space-y-1">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-medium text-muted-foreground">{label}</label>
                  <span className="text-xs font-mono tabular-nums text-foreground">{limits[key]}</span>
                </div>
                <input
                  type="range"
                  min={min}
                  max={max}
                  step={step}
                  value={limits[key]}
                  onChange={(e) => handleLimitChange(key, Number(e.target.value))}
                  className="w-full accent-primary"
                />
              </div>
            ))}
          </div>
        </div>

        {/* Snapshots & Rollback */}
        <div>
          <h4 className="text-sm font-semibold mb-1 flex items-center gap-2">
            <RotateCcw className="h-4 w-4 text-primary" />
            Snapshots & Rollback
          </h4>
          <p className="text-xs text-muted-foreground mb-3">
            A file snapshot is automatically created before each agent execution. If the agent fails, files are restored automatically.
          </p>
          <div className="rounded-md border border-border bg-muted/30 p-4 text-sm text-muted-foreground">
            <div className="flex items-start gap-2">
              <AlertTriangle className="h-4 w-4 text-amber-500 mt-0.5 shrink-0" />
              <span>
                Snapshots are created per-sandbox and stored in memory. Auto-rollback triggers when an agent execution fails or is terminated by the anomaly detector. Manual rollback is available in the task detail view.
              </span>
            </div>
          </div>
        </div>

        {/* Blocked Commands */}
        <div>
          <h4 className="text-sm font-semibold mb-1 flex items-center gap-2">
            <Shield className="h-4 w-4 text-destructive" />
            Blocked Commands (default)
          </h4>
          <p className="text-xs text-muted-foreground mb-3">
            These commands are always blocked inside the sandbox.
          </p>
          <div className="flex flex-wrap gap-1.5">
            {['rm -rf', 'sudo', 'curl', 'wget', 'ssh', 'scp', 'eval', 'exec', 'chmod 777', 'mkfs', 'dd', 'nc'].map((cmd) => (
              <span key={cmd} className="rounded-full bg-destructive/10 px-2.5 py-0.5 text-xs font-mono text-destructive">
                {cmd}
              </span>
            ))}
          </div>
        </div>
      </div>
    </SettingsSection>
  );
}
