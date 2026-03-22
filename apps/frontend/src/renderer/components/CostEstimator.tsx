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
import { getEurRate, formatCurrency } from '../lib/currency';
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
  readonly projectPath: string;
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
  readonly title: string;
  readonly value: string;
  readonly subtitle?: string;
  readonly icon: React.ElementType;
  readonly color?: 'primary' | 'green' | 'amber' | 'red';
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

function BudgetBar({ budget, formatAmount }: { readonly budget: BudgetInfo; readonly formatAmount: (usd: number, decimals?: number) => string }) {
  const { t } = useTranslation('costEstimator');
  const pct = Math.min(budget.utilization_pct, 100);

  // Determine bar color based on utilization percentage
  let barColor: string;
  if (pct >= 90) {
    barColor = 'bg-red-500';
  } else if (pct >= 70) {
    barColor = 'bg-amber-500';
  } else {
    barColor = 'bg-emerald-500';
  }

  // Determine text color based on utilization percentage
  let textColor: string;
  if (pct >= 90) {
    textColor = 'text-red-500';
  } else if (pct >= 70) {
    textColor = 'text-amber-500';
  } else {
    textColor = 'text-emerald-500';
  }

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
        <span>{t('budget.spent', { amount: formatAmount(budget.spent_this_month, 2) })}</span>
        <span>{t('budget.remaining', { amount: formatAmount(budget.remaining, 2) })}</span>
        <span>{t('budget.total', { amount: formatAmount(budget.monthly_budget, 2) })}</span>
      </div>
      {budget.forecast_end_of_month > 0 && (
        <div className="flex items-center gap-2 text-xs">
          <TrendingUp className="h-3 w-3 text-muted-foreground" />
          <span className="text-muted-foreground">
            {t('budget.forecast')} <span className="font-medium text-foreground">{formatAmount(budget.forecast_end_of_month, 2)}</span>
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

function ProviderBreakdown({ data, formatAmount }: { readonly data: Record<string, number>; readonly formatAmount: (usd: number, decimals?: number) => string }) {
  const { t } = useTranslation('costEstimator');
  const allEntries = Object.entries(data).sort(([, a], [, b]) => b - a);
  const used = allEntries.filter(([, v]) => v > 0);
  const unused = allEntries.filter(([, v]) => v === 0);
  const total = used.reduce((sum, [, v]) => sum + v, 0);

  if (allEntries.length === 0) return <div className="text-xs text-muted-foreground">{t('breakdown.noData')}</div>;

  const colors = ['bg-primary', 'bg-blue-500', 'bg-emerald-500', 'bg-amber-500', 'bg-purple-500', 'bg-pink-500'];

  return (
    <div className="space-y-3">
      {used.map(([name, cost], idx) => {
        const pct = total > 0 ? (cost / total) * 100 : 0;
        return (
          <div key={name} className="space-y-1">
            <div className="flex items-center justify-between text-xs">
              <span className="text-foreground font-medium capitalize">{name}</span>
              <span className="text-muted-foreground">{formatAmount(cost)} ({pct.toFixed(0)}%)</span>
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
      {unused.length > 0 && (
        <div className="pt-1 border-t border-border/40">
          <div className="flex flex-wrap gap-x-3 gap-y-1">
            {unused.map(([name]) => (
              <span key={name} className="text-[10px] text-muted-foreground/60 capitalize">{name} — {formatAmount(0, 2)}</span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// Currency formatting — imported from ../lib/currency

// ---------------------------------------------------------------------------
// Helper functions
// ---------------------------------------------------------------------------

function getTrendColor(trendPct: number): 'primary' | 'green' | 'amber' | 'red' {
  if (trendPct > 20) {
    return 'red';
  } else if (trendPct > 0) {
    return 'amber';
  } else {
    return 'green';
  }
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function CostEstimator({ projectPath }: CostEstimatorProps) {
  const { t, i18n } = useTranslation('costEstimator');
  const [eurRate, setEurRate] = useState(0.92);
  const [summary, setSummary] = useState<CostSummary | null>(null);
  const [budget, setBudget] = useState<BudgetInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fmtCurrency = (usd: number, decimals = 4) => formatCurrency(usd, i18n.language, eurRate, decimals);

  // Fetch live EUR rate when in FR mode
  useEffect(() => {
    if (i18n.language.startsWith('fr')) {
      getEurRate().then(setEurRate);
    }
  }, [i18n.language]);

  // Helper function to handle API response
  const handleApiResponse = useCallback((result: PromiseSettledResult<any>, setter: (value: any) => void, silent: boolean, errorKey: string) => {
    if (result.status === 'fulfilled' && result.value?.success) {
      setter(result.value.success ? result.value.summary || result.value.budget : null);
      return true;
    }
    
    if (!silent && (result.status === 'rejected' || !result.value?.success)) {
      const msg = result.status === 'fulfilled' ? result.value?.error : undefined;
      setError(msg || t(errorKey));
    }
    
    return false;
  }, [t]);

  // Helper function to fetch data from APIs
  const fetchFromAPIs = useCallback(async (silent: boolean) => {
    try {
      const [summaryRes, budgetRes] = await Promise.allSettled([
        globalThis.electronAPI.getCostSummary(projectPath),
        globalThis.electronAPI.getCostBudget(projectPath),
      ]);

      const summarySuccess = handleApiResponse(summaryRes, setSummary, silent, 'error');
      const budgetSuccess = handleApiResponse(budgetRes, setBudget, silent, 'error');
      
      return summarySuccess || budgetSuccess;
    } catch (e) {
      if (!silent) {
        setError(e instanceof Error ? e.message : t('error'));
      }
      return false;
    }
  }, [projectPath, handleApiResponse, t]);

  // Main fetchData function
  const fetchData = useCallback(async (silent = false) => {
    if (!silent) {
      setLoading(true);
      setError(null);
    }
    
    try {
      await fetchFromAPIs(silent);
    } finally {
      if (!silent) {
        setLoading(false);
      }
    }
  }, [fetchFromAPIs]);

  // Initial load
  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Auto-refresh when cost_data.json changes (pushed by main process)
  useEffect(() => {
    if (typeof globalThis.electronAPI?.onCostsUpdated !== 'function') return;
    const unsubscribe = globalThis.electronAPI.onCostsUpdated((updatedPath: string) => {
      if (updatedPath === projectPath) fetchData(true);
    });
    return unsubscribe;
  }, [projectPath, fetchData]);

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
        <Button variant="outline" size="sm" onClick={() => fetchData()}>
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
          <Button variant="outline" size="sm" onClick={() => fetchData()}>
            <RefreshCw className="h-3.5 w-3.5 mr-2" />
            {t('common:buttons.refresh')}
          </Button>
        </div>

        {/* KPI cards */}
        {summary && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <CostKpiCard
              title={t('kpi.totalCost.title')}
              value={fmtCurrency(summary.total_cost)}
              subtitle={t('kpi.totalCost.period', { days: summary.period_days })}
              icon={DollarSign}
              color="primary"
            />
            <CostKpiCard
              title={t('kpi.dailyAverage.title')}
              value={fmtCurrency(summary.daily_avg)}
              subtitle={summary.trend_pct >= 0 ? `↑ ${summary.trend_pct.toFixed(0)}%` : `↓ ${Math.abs(summary.trend_pct).toFixed(0)}%`}
              icon={summary.trend_pct >= 0 ? TrendingUp : TrendingDown}
              color={getTrendColor(summary.trend_pct)}
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
              value={`${Object.values(summary.cost_by_provider).filter(v => v > 0).length}`}
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
              <BudgetBar budget={budget} formatAmount={fmtCurrency} />
              {budget.alerts.length > 0 && (
                <div className="mt-4 space-y-2">
                  {budget.alerts.map((alert) => (
                    <div key={alert} className="flex items-center gap-2 text-xs text-amber-500">
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
                <ProviderBreakdown data={summary.cost_by_provider} formatAmount={fmtCurrency} />
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-5">
                <h3 className="text-sm font-semibold text-foreground mb-4">{t('breakdown.costByModel')}</h3>
                <ProviderBreakdown data={summary.cost_by_model} formatAmount={fmtCurrency} />
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </ScrollArea>
  );
}
