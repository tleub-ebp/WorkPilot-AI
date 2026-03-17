import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Coins,
  RefreshCw,
  Loader2,
  AlertTriangle,
  TrendingUp,
  TrendingDown,
  DollarSign,
  Zap,
  PieChart,
  Bell
} from 'lucide-react';
import { Button } from './ui/button';
import { Card, CardContent } from './ui/card';
import { Badge } from './ui/badge';
import { ScrollArea } from './ui/scroll-area';
import { cn } from '../lib/utils';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface CostSummary {
  total_cost: number;
  cost_by_provider: Record<string, number>;
  cost_by_model: Record<string, number>;
  total_tokens: number;
  tokens_input: number;
  tokens_output: number;
  period_days: number;
  daily_avg: number;
  trend_pct: number;
}

interface BudgetInfo {
  monthly_budget: number;
  spent_this_month: number;
  remaining: number;
  utilization_pct: number;
  alerts: string[];
  forecast_end_of_month: number;
}

interface CostEstimatorProps {
  projectId: string;
}

// ---------------------------------------------------------------------------
// KPI Card
// ---------------------------------------------------------------------------

function CostKpiCard({
  title,
  value,
  subtitle,
  icon: Icon,
  color = 'primary',
}: {
  title: string;
  value: string;
  subtitle?: string;
  icon: React.ElementType;
  color?: 'primary' | 'green' | 'amber' | 'red';
}) {
  const colorClasses = {
    primary: 'text-primary bg-primary/10',
    green: 'text-emerald-500 bg-emerald-500/10',
    amber: 'text-amber-500 bg-amber-500/10',
    red: 'text-red-500 bg-red-500/10',
  };

  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">{title}</p>
            <p className="mt-1 text-xl font-bold text-foreground">{value}</p>
            {subtitle && <p className="mt-0.5 text-xs text-muted-foreground">{subtitle}</p>}
          </div>
          <div className={cn('rounded-lg p-2', colorClasses[color])}>
            <Icon className="h-4 w-4" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Budget progress bar
// ---------------------------------------------------------------------------

function BudgetBar({ budget }: { budget: BudgetInfo }) {
  const { t } = useTranslation('costEstimator');
  const pct = Math.min(budget.utilization_pct, 100);
  const barColor =
    pct >= 90 ? 'bg-red-500' : pct >= 70 ? 'bg-amber-500' : 'bg-emerald-500';
  const textColor =
    pct >= 90 ? 'text-red-500' : pct >= 70 ? 'text-amber-500' : 'text-emerald-500';

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-foreground">{t('budget.title')}</span>
        <span className={cn('text-sm font-bold', textColor)}>{t('budget.pctUsed', { pct: pct.toFixed(0) })}</span>
      </div>
      <div className="h-3 w-full rounded-full bg-secondary overflow-hidden">
        <div
          className={cn('h-full rounded-full transition-all', barColor)}
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="flex justify-between text-xs text-muted-foreground">
        <span>{t('budget.spent', { amount: budget.spent_this_month.toFixed(2) })}</span>
        <span>{t('budget.remaining', { amount: budget.remaining.toFixed(2) })}</span>
        <span>{t('budget.total', { amount: budget.monthly_budget.toFixed(2) })}</span>
      </div>
      {budget.forecast_end_of_month > 0 && (
        <div className="flex items-center gap-2 text-xs">
          <TrendingUp className="h-3 w-3 text-muted-foreground" />
          <span className="text-muted-foreground">
            {t('budget.forecast')} <span className="font-medium text-foreground">${budget.forecast_end_of_month.toFixed(2)}</span>
          </span>
          {budget.forecast_end_of_month > budget.monthly_budget && (
            <Badge variant="outline" className="text-[10px] text-red-500 border-red-500/20">{t('budget.overBudget')}</Badge>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Provider breakdown
// ---------------------------------------------------------------------------

function ProviderBreakdown({ data }: { data: Record<string, number> }) {
  const { t } = useTranslation('costEstimator');
  const entries = Object.entries(data).sort(([, a], [, b]) => b - a);
  const total = entries.reduce((sum, [, v]) => sum + v, 0);

  if (entries.length === 0) return <div className="text-xs text-muted-foreground">{t('breakdown.noData')}</div>;

  const colors = ['bg-primary', 'bg-blue-500', 'bg-emerald-500', 'bg-amber-500', 'bg-purple-500', 'bg-pink-500'];

  return (
    <div className="space-y-3">
      {entries.map(([name, cost], idx) => {
        const pct = total > 0 ? (cost / total) * 100 : 0;
        return (
          <div key={name} className="space-y-1">
            <div className="flex items-center justify-between text-xs">
              <span className="text-foreground font-medium capitalize">{name}</span>
              <span className="text-muted-foreground">${cost.toFixed(4)} ({pct.toFixed(0)}%)</span>
            </div>
            <div className="h-1.5 w-full rounded-full bg-secondary overflow-hidden">
              <div
                className={cn('h-full rounded-full transition-all', colors[idx % colors.length])}
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

export function CostEstimator({ projectId }: CostEstimatorProps) {
  const { t } = useTranslation('costEstimator');
  const [summary, setSummary] = useState<CostSummary | null>(null);
  const [budget, setBudget] = useState<BudgetInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const backendUrl = import.meta.env?.VITE_BACKEND_URL || '';
      const [summaryRes, budgetRes] = await Promise.allSettled([
        fetch(`${backendUrl}/api/costs/summary/${projectId}`).then(r => r.json()),
        fetch(`${backendUrl}/api/costs/budget/${projectId}`).then(r => r.json()),
      ]);

      if (summaryRes.status === 'fulfilled' && summaryRes.value.success) {
        setSummary(summaryRes.value.summary);
      }
      if (budgetRes.status === 'fulfilled' && budgetRes.value.success) {
        setBudget(budgetRes.value.budget);
      }

      // If both failed, show error
      if (
        (summaryRes.status === 'rejected' || !summaryRes.value?.success) &&
        (budgetRes.status === 'rejected' || !budgetRes.value?.success)
      ) {
        const msg = summaryRes.status === 'fulfilled' ? summaryRes.value.error : 'Failed to load';
        setError(msg || 'Failed to load cost data');
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Network error');
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error && !summary && !budget) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4 text-muted-foreground">
        <AlertTriangle className="h-8 w-8" />
        <p className="text-sm">{error}</p>
        <Button variant="outline" size="sm" onClick={fetchData}>
          <RefreshCw className="h-3.5 w-3.5 mr-2" />
          {t('retry')}
        </Button>
      </div>
    );
  }

  return (
    <ScrollArea className="h-full">
      <div className="p-6 space-y-6 max-w-5xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Coins className="h-6 w-6 text-primary" />
            <div>
              <h1 className="text-xl font-bold text-foreground">{t('title')}</h1>
              <p className="text-sm text-muted-foreground">{t('subtitle')}</p>
            </div>
          </div>
          <Button variant="outline" size="sm" onClick={fetchData}>
            <RefreshCw className="h-3.5 w-3.5 mr-2" />
            {t('common:buttons.refresh')}
          </Button>
        </div>

        {/* KPI cards */}
        {summary && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <CostKpiCard
              title={t('kpi.totalCost.title')}
              value={`$${summary.total_cost.toFixed(4)}`}
              subtitle={t('kpi.totalCost.period', { days: summary.period_days })}
              icon={DollarSign}
              color="primary"
            />
            <CostKpiCard
              title={t('kpi.dailyAverage.title')}
              value={`$${summary.daily_avg.toFixed(4)}`}
              subtitle={summary.trend_pct >= 0 ? `↑ ${summary.trend_pct.toFixed(0)}%` : `↓ ${Math.abs(summary.trend_pct).toFixed(0)}%`}
              icon={summary.trend_pct >= 0 ? TrendingUp : TrendingDown}
              color={summary.trend_pct > 20 ? 'red' : summary.trend_pct > 0 ? 'amber' : 'green'}
            />
            <CostKpiCard
              title={t('kpi.totalTokens.title')}
              value={summary.total_tokens.toLocaleString()}
              subtitle={t('kpi.totalTokens.inOut', { input: summary.tokens_input.toLocaleString(), output: summary.tokens_output.toLocaleString() })}
              icon={Zap}
              color="amber"
            />
            <CostKpiCard
              title={t('kpi.providers.title')}
              value={`${Object.keys(summary.cost_by_provider).length}`}
              subtitle={t('kpi.providers.models', { count: Object.keys(summary.cost_by_model).length })}
              icon={PieChart}
              color="green"
            />
          </div>
        )}

        {/* Budget */}
        {budget && (
          <Card>
            <CardContent className="p-5">
              <BudgetBar budget={budget} />
              {budget.alerts.length > 0 && (
                <div className="mt-4 space-y-2">
                  {budget.alerts.map((alert, idx) => (
                    <div key={idx} className="flex items-center gap-2 text-xs text-amber-500">
                      <Bell className="h-3.5 w-3.5 shrink-0" />
                      <span>{alert}</span>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Breakdowns */}
        {summary && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardContent className="p-5">
                <h3 className="text-sm font-semibold text-foreground mb-4">{t('breakdown.costByProvider')}</h3>
                <ProviderBreakdown data={summary.cost_by_provider} />
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-5">
                <h3 className="text-sm font-semibold text-foreground mb-4">{t('breakdown.costByModel')}</h3>
                <ProviderBreakdown data={summary.cost_by_model} />
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </ScrollArea>
  );
}
