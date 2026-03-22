import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  BarChart3,
  CheckCircle2,
  Clock,
  AlertTriangle,
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
import { getEurRate, formatCurrency } from '../lib/currency';

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
  projectPath: string;
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
  const { t } = useTranslation('dashboard');
  const total = Object.values(data).reduce((a, b) => a + b, 0);
  if (total === 0) return <div className="text-xs text-muted-foreground">{t('empty.noTasks')}</div>;

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

function CostBreakdown({ costByModel, fmtCost }: { costByModel: Record<string, number>; fmtCost: (usd: number, decimals?: number) => string }) {
  const { t } = useTranslation('dashboard');
  if (!costByModel || typeof costByModel !== 'object') {
    return <div className="text-xs text-muted-foreground">{t('empty.noCostData')}</div>;
  }

  const entries = Object.entries(costByModel).sort(([, a], [, b]) => b - a);
  const total = entries.reduce((sum, [, v]) => sum + v, 0);

  if (entries.length === 0) {
    return <div className="text-xs text-muted-foreground">{t('empty.noCostData')}</div>;
  }

  return (
    <div className="space-y-2">
      {entries.map(([model, cost]) => {
        const pct = total > 0 ? (cost / total) * 100 : 0;
        return (
          <div key={model} className="space-y-1">
            <div className="flex items-center justify-between text-xs">
              <span className="text-foreground font-medium truncate">{model}</span>
              <span className="text-muted-foreground">{fmtCost(cost)} ({pct.toFixed(0)}%)</span>
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

export function DashboardMetrics({ projectPath }: DashboardMetricsProps) {
  const { t, i18n } = useTranslation('dashboard');
  const lang = i18n.language;
  const [snapshot, setSnapshot] = useState<DashboardSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [eurRate, setEurRate] = useState(0.92);

  const fmtCost = useCallback(
    (usd: number, decimals = 4) => formatCurrency(usd, lang, eurRate, decimals),
    [lang, eurRate],
  );

  const fetchSnapshot = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await window.electronAPI.getDashboardSnapshot(projectPath);
      if (result.success) {
        setSnapshot(result.snapshot!);
      } else {
        setError(result.error || 'Failed to load dashboard');
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Network error');
    } finally {
      setLoading(false);
    }
  }, [projectPath]);

  useEffect(() => {
    fetchSnapshot();
    getEurRate().then(setEurRate);
  }, [fetchSnapshot]);

  // Subscribe to real-time updates when dashboard_snapshot.json changes
  useEffect(() => {
    const unsubscribe = window.electronAPI.onDashboardSnapshotUpdated((updatedPath: string) => {
      if (updatedPath === projectPath) {
        fetchSnapshot();
      }
    });
    return () => unsubscribe();
  }, [projectPath, fetchSnapshot]);

  const handleExport = async (fmt: 'json' | 'csv') => {
    try {
      const result = await window.electronAPI.getDashboardSnapshot(projectPath);
      if (!result.success || !result.snapshot) return;
      const snap = result.snapshot;
      let content: string;
      if (fmt === 'csv') {
        const rows = [
          ['metric', 'value'],
          ['total_tokens', String(snap.total_tokens)],
          ['total_cost', String(snap.total_cost)],
          ['qa_first_pass_rate', String(snap.qa_first_pass_rate)],
          ['qa_avg_score', String(snap.qa_avg_score)],
          ['merge_auto_count', String(snap.merge_auto_count)],
          ['merge_manual_count', String(snap.merge_manual_count)],
          ...Object.entries(snap.tasks_by_status).map(([k, v]) => [`tasks_${k}`, String(v)]),
          ...Object.entries(snap.tokens_by_provider).map(([k, v]) => [`tokens_${k}`, String(v)]),
          ...Object.entries(snap.cost_by_model).map(([k, v]) => [`cost_${k}`, String(v)]),
        ];
        content = rows.map(r => r.join(',')).join('\n');
      } else {
        content = JSON.stringify(snap, null, 2);
      }
      const blob = new Blob([content], { type: fmt === 'csv' ? 'text/csv' : 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `dashboard-export.${fmt}`;
      a.click();
      URL.revokeObjectURL(url);
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
          {t('common:buttons.retry')}
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
              <h1 className="text-xl font-bold text-foreground">{t('title')}</h1>
              <p className="text-sm text-muted-foreground">{t('subtitle')}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={fetchSnapshot}>
              <RefreshCw className="h-3.5 w-3.5 mr-2" />
              {t('common:buttons.refresh')}
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
            title={t('kpi.totalTasks.title')}
            value={totalTasks}
            subtitle={t('kpi.totalTasks.completed', { count: completedTasks })}
            icon={Target}
            color="primary"
          />
          <KpiCard
            title={t('kpi.qaFirstPassRate.title')}
            value={`${snap.qa_first_pass_rate.toFixed(1)}%`}
            subtitle={t('kpi.qaFirstPassRate.avgScore', { score: snap.qa_avg_score.toFixed(1) })}
            icon={CheckCircle2}
            color="green"
          />
          <KpiCard
            title={t('kpi.totalTokens.title')}
            value={snap.total_tokens.toLocaleString()}
            subtitle={t('kpi.totalTokens.totalCost', { cost: fmtCost(snap.total_cost) })}
            icon={Zap}
            color="amber"
          />
          <KpiCard
            title={t('kpi.autoMerges.title')}
            value={`${mergeAutoRate}%`}
            subtitle={t('kpi.autoMerges.autoManual', { auto: snap.merge_auto_count, manual: snap.merge_manual_count })}
            icon={GitMerge}
            color="blue"
          />
        </div>

        {/* Task Status & Completion Times */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card>
            <CardContent className="p-5">
              <h3 className="text-sm font-semibold text-foreground mb-4">{t('sections.tasksByStatus')}</h3>
              <StatusBar data={snap.tasks_by_status} />
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-5">
              <h3 className="text-sm font-semibold text-foreground mb-4">{t('sections.avgCompletionTime')}</h3>
              {Object.keys(snap.avg_completion_by_complexity).length === 0 ? (
                <div className="text-xs text-muted-foreground">{t('empty.noCompletionData')}</div>
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
              <h3 className="text-sm font-semibold text-foreground mb-4">{t('sections.costByModel')}</h3>
              <CostBreakdown costByModel={snap.cost_by_model} fmtCost={fmtCost} />
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-5">
              <h3 className="text-sm font-semibold text-foreground mb-4">{t('sections.tokensByProvider')}</h3>
              {Object.keys(snap.tokens_by_provider).length === 0 ? (
                <div className="text-xs text-muted-foreground">{t('empty.noTokenData')}</div>
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
            <h3 className="text-sm font-semibold text-foreground mb-4">{t('sections.mergeResolution')}</h3>
            <div className="flex items-center gap-8">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-full bg-emerald-500/10 flex items-center justify-center">
                  <Zap className="h-5 w-5 text-emerald-500" />
                </div>
                <div>
                  <p className="text-lg font-bold text-foreground">{snap.merge_auto_count}</p>
                  <p className="text-xs text-muted-foreground">{t('merge.automatic')}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-full bg-amber-500/10 flex items-center justify-center">
                  <GitMerge className="h-5 w-5 text-amber-500" />
                </div>
                <div>
                  <p className="text-lg font-bold text-foreground">{snap.merge_manual_count}</p>
                  <p className="text-xs text-muted-foreground">{t('merge.manual')}</p>
                </div>
              </div>
              {mergeTotal > 0 && (
                <div className="ml-auto text-right">
                  <p className="text-sm text-muted-foreground">{t('merge.autoResolutionRate')}</p>
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
