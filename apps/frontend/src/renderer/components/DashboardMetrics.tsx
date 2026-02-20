import { useState, useEffect, useCallback } from 'react';
import {
  BarChart3,
  CheckCircle2,
  Clock,
  AlertTriangle,
  Coins,
  GitMerge,
  Download,
  RefreshCw,
  Loader2,
  TrendingUp,
  Zap,
  Target
} from 'lucide-react';
import { Button } from './ui/button';
import { Card, CardContent } from './ui/card';
import { Badge } from './ui/badge';
import { ScrollArea } from './ui/scroll-area';
import { cn } from '../lib/utils';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface DashboardSnapshot {
  tasks_by_status: Record<string, number>;
  avg_completion_by_complexity: Record<string, number>;
  qa_first_pass_rate: number;
  qa_avg_score: number;
  total_tokens: number;
  tokens_by_provider: Record<string, number>;
  total_cost: number;
  cost_by_model: Record<string, number>;
  merge_auto_count: number;
  merge_manual_count: number;
}

interface DashboardMetricsProps {
  projectId: string;
}

// ---------------------------------------------------------------------------
// KPI Card
// ---------------------------------------------------------------------------

function KpiCard({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
  color = 'primary',
}: {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ElementType;
  trend?: string;
  color?: 'primary' | 'green' | 'amber' | 'red' | 'blue';
}) {
  const colorClasses = {
    primary: 'text-primary bg-primary/10',
    green: 'text-emerald-500 bg-emerald-500/10',
    amber: 'text-amber-500 bg-amber-500/10',
    red: 'text-red-500 bg-red-500/10',
    blue: 'text-blue-500 bg-blue-500/10',
  };

  return (
    <Card className="relative overflow-hidden">
      <CardContent className="p-5">
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">{title}</p>
            <p className="mt-1.5 text-2xl font-bold text-foreground">{value}</p>
            {subtitle && <p className="mt-0.5 text-xs text-muted-foreground">{subtitle}</p>}
            {trend && (
              <div className="mt-2 flex items-center gap-1">
                <TrendingUp className="h-3 w-3 text-emerald-500" />
                <span className="text-xs text-emerald-500 font-medium">{trend}</span>
              </div>
            )}
          </div>
          <div className={cn('rounded-lg p-2.5', colorClasses[color])}>
            <Icon className="h-5 w-5" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Status bar (horizontal)
// ---------------------------------------------------------------------------

function StatusBar({ data }: { data: Record<string, number> }) {
  const total = Object.values(data).reduce((a, b) => a + b, 0);
  if (total === 0) return <div className="text-xs text-muted-foreground">No tasks</div>;

  const statusColors: Record<string, string> = {
    completed: 'bg-emerald-500',
    in_progress: 'bg-blue-500',
    pending: 'bg-amber-500',
    failed: 'bg-red-500',
    cancelled: 'bg-gray-400',
  };

  return (
    <div className="space-y-2">
      <div className="flex h-3 w-full overflow-hidden rounded-full bg-secondary">
        {Object.entries(data).map(([status, count]) => {
          const pct = (count / total) * 100;
          if (pct === 0) return null;
          return (
            <div
              key={status}
              className={cn('h-full transition-all', statusColors[status] || 'bg-gray-300')}
              style={{ width: `${pct}%` }}
              title={`${status}: ${count} (${pct.toFixed(0)}%)`}
            />
          );
        })}
      </div>
      <div className="flex flex-wrap gap-3">
        {Object.entries(data).map(([status, count]) => (
          <div key={status} className="flex items-center gap-1.5 text-xs">
            <div className={cn('h-2.5 w-2.5 rounded-full', statusColors[status] || 'bg-gray-300')} />
            <span className="text-muted-foreground capitalize">{status.replace('_', ' ')}</span>
            <span className="font-medium text-foreground">{count}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Cost breakdown
// ---------------------------------------------------------------------------

function CostBreakdown({ costByModel }: { costByModel: Record<string, number> }) {
  if (!costByModel || typeof costByModel !== 'object') {
    return <div className="text-xs text-muted-foreground">No cost data</div>;
  }
  
  const entries = Object.entries(costByModel).sort(([, a], [, b]) => b - a);
  const total = entries.reduce((sum, [, v]) => sum + v, 0);

  if (entries.length === 0) {
    return <div className="text-xs text-muted-foreground">No cost data</div>;
  }

  return (
    <div className="space-y-2">
      {entries.map(([model, cost]) => {
        const pct = total > 0 ? (cost / total) * 100 : 0;
        return (
          <div key={model} className="space-y-1">
            <div className="flex items-center justify-between text-xs">
              <span className="text-foreground font-medium truncate">{model}</span>
              <span className="text-muted-foreground">${cost.toFixed(4)} ({pct.toFixed(0)}%)</span>
            </div>
            <div className="h-1.5 w-full rounded-full bg-secondary overflow-hidden">
              <div
                className="h-full rounded-full bg-primary transition-all"
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function DashboardMetrics({ projectId }: DashboardMetricsProps) {
  const [snapshot, setSnapshot] = useState<DashboardSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSnapshot = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const backendUrl = import.meta.env?.VITE_BACKEND_URL || '';
      const res = await fetch(`${backendUrl}/api/dashboard/snapshot/${projectId}`);
      const data = await res.json();
      if (data.success) {
        setSnapshot(data.snapshot);
      } else {
        setError(data.error || 'Failed to load dashboard');
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Network error');
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    fetchSnapshot();
  }, [fetchSnapshot]);

  const handleExport = async (fmt: 'json' | 'csv') => {
    try {
      const backendUrl = import.meta.env?.VITE_BACKEND_URL || '';
      const res = await fetch(`${backendUrl}/api/dashboard/export/${projectId}?fmt=${fmt}`);
      const data = await res.json();
      if (data.success) {
        const blob = new Blob([typeof data.report === 'string' ? data.report : JSON.stringify(data.report, null, 2)], {
          type: fmt === 'csv' ? 'text/csv' : 'application/json',
        });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `dashboard-${projectId}.${fmt}`;
        a.click();
        URL.revokeObjectURL(url);
      }
    } catch {
      // silently fail export
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4 text-muted-foreground">
        <AlertTriangle className="h-8 w-8" />
        <p className="text-sm">{error}</p>
        <Button variant="outline" size="sm" onClick={fetchSnapshot}>
          <RefreshCw className="h-3.5 w-3.5 mr-2" />
          Retry
        </Button>
      </div>
    );
  }

  // Default values when no data yet
  const snap = snapshot || {
    tasks_by_status: { pending: 0, in_progress: 0, completed: 0, failed: 0 },
    avg_completion_by_complexity: {},
    qa_first_pass_rate: 0,
    qa_avg_score: 0,
    total_tokens: 0,
    tokens_by_provider: {},
    total_cost: 0,
    cost_by_model: {},
    merge_auto_count: 0,
    merge_manual_count: 0,
  };

  const totalTasks = Object.values(snap.tasks_by_status).reduce((a, b) => a + b, 0);
  const completedTasks = snap.tasks_by_status.completed || 0;
  const mergeTotal = snap.merge_auto_count + snap.merge_manual_count;
  const mergeAutoRate = mergeTotal > 0 ? ((snap.merge_auto_count / mergeTotal) * 100).toFixed(0) : '0';

  return (
    <ScrollArea className="h-full">
      <div className="p-6 space-y-6 max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <BarChart3 className="h-6 w-6 text-primary" />
            <div>
              <h1 className="text-xl font-bold text-foreground">Dashboard</h1>
              <p className="text-sm text-muted-foreground">Project metrics & KPIs</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={fetchSnapshot}>
              <RefreshCw className="h-3.5 w-3.5 mr-2" />
              Refresh
            </Button>
            <Button variant="outline" size="sm" onClick={() => handleExport('json')}>
              <Download className="h-3.5 w-3.5 mr-2" />
              JSON
            </Button>
            <Button variant="outline" size="sm" onClick={() => handleExport('csv')}>
              <Download className="h-3.5 w-3.5 mr-2" />
              CSV
            </Button>
          </div>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <KpiCard
            title="Total Tasks"
            value={totalTasks}
            subtitle={`${completedTasks} completed`}
            icon={Target}
            color="primary"
          />
          <KpiCard
            title="QA First-Pass Rate"
            value={`${snap.qa_first_pass_rate.toFixed(1)}%`}
            subtitle={`Avg score: ${snap.qa_avg_score.toFixed(1)}`}
            icon={CheckCircle2}
            color="green"
          />
          <KpiCard
            title="Total Tokens"
            value={snap.total_tokens.toLocaleString()}
            subtitle={`$${snap.total_cost.toFixed(4)} total cost`}
            icon={Zap}
            color="amber"
          />
          <KpiCard
            title="Auto Merges"
            value={`${mergeAutoRate}%`}
            subtitle={`${snap.merge_auto_count} auto / ${snap.merge_manual_count} manual`}
            icon={GitMerge}
            color="blue"
          />
        </div>

        {/* Task Status & Completion Times */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card>
            <CardContent className="p-5">
              <h3 className="text-sm font-semibold text-foreground mb-4">Tasks by Status</h3>
              <StatusBar data={snap.tasks_by_status} />
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-5">
              <h3 className="text-sm font-semibold text-foreground mb-4">Avg Completion Time by Complexity</h3>
              {Object.keys(snap.avg_completion_by_complexity).length === 0 ? (
                <div className="text-xs text-muted-foreground">No completion data yet</div>
              ) : (
                <div className="space-y-3">
                  {Object.entries(snap.avg_completion_by_complexity).map(([complexity, seconds]) => (
                    <div key={complexity} className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Clock className="h-3.5 w-3.5 text-muted-foreground" />
                        <span className="text-sm capitalize text-foreground">{complexity}</span>
                      </div>
                      <Badge variant="secondary" className="text-xs">
                        {seconds < 3600
                          ? `${Math.round(seconds / 60)}m`
                          : `${(seconds / 3600).toFixed(1)}h`}
                      </Badge>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Costs & Tokens */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card>
            <CardContent className="p-5">
              <h3 className="text-sm font-semibold text-foreground mb-4">Cost by Model</h3>
              <CostBreakdown costByModel={snap.cost_by_model} />
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-5">
              <h3 className="text-sm font-semibold text-foreground mb-4">Tokens by Provider</h3>
              {Object.keys(snap.tokens_by_provider).length === 0 ? (
                <div className="text-xs text-muted-foreground">No token data yet</div>
              ) : (
                <div className="space-y-2">
                  {Object.entries(snap.tokens_by_provider)
                    .sort(([, a], [, b]) => b - a)
                    .map(([provider, tokens]) => (
                      <div key={provider} className="flex items-center justify-between text-sm">
                        <span className="text-foreground capitalize">{provider}</span>
                        <span className="text-muted-foreground font-mono">{tokens.toLocaleString()}</span>
                      </div>
                    ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Merge Resolution */}
        <Card>
          <CardContent className="p-5">
            <h3 className="text-sm font-semibold text-foreground mb-4">Merge Resolution</h3>
            <div className="flex items-center gap-8">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-full bg-emerald-500/10 flex items-center justify-center">
                  <Zap className="h-5 w-5 text-emerald-500" />
                </div>
                <div>
                  <p className="text-lg font-bold text-foreground">{snap.merge_auto_count}</p>
                  <p className="text-xs text-muted-foreground">Automatic</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-full bg-amber-500/10 flex items-center justify-center">
                  <GitMerge className="h-5 w-5 text-amber-500" />
                </div>
                <div>
                  <p className="text-lg font-bold text-foreground">{snap.merge_manual_count}</p>
                  <p className="text-xs text-muted-foreground">Manual</p>
                </div>
              </div>
              {mergeTotal > 0 && (
                <div className="ml-auto text-right">
                  <p className="text-sm text-muted-foreground">Auto-resolution rate</p>
                  <p className="text-xl font-bold text-foreground">{mergeAutoRate}%</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </ScrollArea>
  );
}
