import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  BarChart3,
  CheckCircle2,
  Clock,
  AlertTriangle,
  Coins,
  TrendingUp,
  Zap,
  Target,
  RefreshCw,
  Loader2,
  Activity,
  DollarSign,
  Bug,
  Code,
  TestTube
} from 'lucide-react';
import { Button } from './ui/button';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { ScrollArea } from './ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Progress } from './ui/progress';
import { cn } from '../lib/utils';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface BuildSummary {
  build_id: string;
  spec_id: string;
  spec_name?: string;
  started_at: string;
  completed_at?: string;
  status: string;
  total_duration_seconds?: number;
  total_tokens_used: number;
  total_cost_usd: number;
  qa_iterations: number;
  qa_success_rate: number;
  llm_provider?: string;
  llm_model?: string;
}

interface PhaseMetrics {
  phase_name: string;
  phase_type: string;
  duration_seconds?: number;
  tokens_used: number;
  cost_usd: number;
  success: boolean;
  builds_count: number;
}

interface TokenMetrics {
  date: string;
  total_tokens: number;
  total_cost_usd: number;
  builds_count: number;
  avg_tokens_per_build: number;
}

interface QAMetrics {
  date: string;
  avg_success_rate: number;
  total_iterations: number;
  builds_tested: number;
  avg_coverage: number;
}

interface ErrorMetrics {
  error_type: string;
  error_category: string;
  count: number;
  resolved_count: number;
  resolution_rate: number;
}

interface AgentPerformanceMetrics {
  agent_type: string;
  llm_provider?: string;
  llm_model?: string;
  total_builds: number;
  success_rate: number;
  avg_duration_seconds: number;
  avg_tokens_per_build: number;
  avg_cost_per_build: number;
}

interface DashboardOverview {
  total_builds: number;
  successful_builds: number;
  success_rate: number;
  total_tokens_used: number;
  total_cost_usd: number;
  avg_build_duration: number;
  recent_builds: BuildSummary[];
  top_error_types: ErrorMetrics[];
  phase_performance: PhaseMetrics[];
}

interface AnalyticsDashboardProps {
  readonly className?: string;
}

// ---------------------------------------------------------------------------
// Helper Functions
// ---------------------------------------------------------------------------

const formatDuration = (seconds?: number): string => {
  if (!seconds) return 'N/A';
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  if (seconds < 3600) return `${(seconds / 60).toFixed(1)}m`;
  return `${(seconds / 3600).toFixed(1)}h`;
};

const formatTokens = (tokens: number): string => {
  if (tokens < 1000) return tokens.toString();
  if (tokens < 1000000) return `${(tokens / 1000).toFixed(1)}K`;
  return `${(tokens / 1000000).toFixed(1)}M`;
};

const formatCost = (cost: number): string => {
  return `$${cost.toFixed(4)}`;
};

const formatDate = (dateString: string): string => {
  return new Date(dateString).toLocaleDateString();
};

const getStatusColor = (status: string): string => {
  switch (status) {
    case 'complete': return 'text-green-600';
    case 'failed': return 'text-red-600';
    case 'coding': return 'text-blue-600';
    case 'qa_review': return 'text-purple-600';
    case 'planning': return 'text-orange-600';
    default: return 'text-gray-600';
  }
};

const getStatusIcon = (status: string) => {
  switch (status) {
    case 'complete': return <CheckCircle2 className="h-4 w-4" />;
    case 'failed': return <AlertTriangle className="h-4 w-4" />;
    case 'coding': return <Code className="h-4 w-4" />;
    case 'qa_review': return <TestTube className="h-4 w-4" />;
    case 'planning': return <Target className="h-4 w-4" />;
    default: return <Clock className="h-4 w-4" />;
  }
};

// ---------------------------------------------------------------------------
// KPI Card Component
// ---------------------------------------------------------------------------

interface KpiCardProps {
  readonly title: string;
  readonly value: string | number;
  readonly subtitle?: string;
  readonly icon: React.ReactNode;
  readonly trend?: {
    readonly value: number;
    readonly isPositive: boolean;
  };
  readonly className?: string;
}

function KpiCard({ title, value, subtitle, icon, trend, className }: KpiCardProps) {
  return (
    <Card className={cn('relative overflow-hidden', className)}>
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <p className="text-sm font-medium text-muted-foreground">{title}</p>
            <p className="text-2xl font-bold">{value}</p>
            {subtitle && (
              <p className="text-xs text-muted-foreground">{subtitle}</p>
            )}
          </div>
          <div className="flex items-center space-x-2">
            <div className="p-2 bg-muted rounded-lg">
              {icon}
            </div>
            {trend && (
              <div className={cn(
                'flex items-center text-xs',
                trend.isPositive ? 'text-green-600' : 'text-red-600'
              )}>
                <TrendingUp className="h-3 w-3 mr-1" />
                {trend.value}%
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Main Analytics Dashboard Component
// ---------------------------------------------------------------------------

export function AnalyticsDashboard({ className }: AnalyticsDashboardProps) {
  const { t } = useTranslation('analytics');
  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [builds, setBuilds] = useState<BuildSummary[]>([]);
  const [tokenMetrics, setTokenMetrics] = useState<TokenMetrics[]>([]);
  const [qaMetrics, setQaMetrics] = useState<QAMetrics[]>([]);
  const [agentPerformance, setAgentPerformance] = useState<AgentPerformanceMetrics[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedDays, setSelectedDays] = useState(30);

  const fetchAnalytics = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch dashboard overview
      const overviewResponse = await fetch(`/analytics/overview?days=${selectedDays}`);
      if (!overviewResponse.ok) throw new Error('Failed to fetch overview');
      const overviewData = await overviewResponse.json();
      setOverview(overviewData);

      // Fetch builds
      const buildsResponse = await fetch(`/analytics/builds?limit=20`);
      if (!buildsResponse.ok) throw new Error('Failed to fetch builds');
      const buildsData = await buildsResponse.json();
      setBuilds(buildsData);

      // Fetch token metrics
      const tokenResponse = await fetch(`/analytics/metrics/tokens?days=${selectedDays}`);
      if (!tokenResponse.ok) throw new Error('Failed to fetch token metrics');
      const tokenData = await tokenResponse.json();
      setTokenMetrics(tokenData);

      // Fetch QA metrics
      const qaResponse = await fetch(`/analytics/metrics/qa?days=${selectedDays}`);
      if (!qaResponse.ok) throw new Error('Failed to fetch QA metrics');
      const qaData = await qaResponse.json();
      setQaMetrics(qaData);

      // Fetch agent performance
      const agentResponse = await fetch(`/analytics/metrics/agent-performance?days=${selectedDays}`);
      if (!agentResponse.ok) throw new Error('Failed to fetch agent performance');
      const agentData = await agentResponse.json();
      setAgentPerformance(agentData);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error occurred');
    } finally {
      setLoading(false);
    }
  }, [selectedDays]);

  useEffect(() => {
    fetchAnalytics();
  }, [fetchAnalytics]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="flex items-center space-x-2">
          <Loader2 className="h-6 w-6 animate-spin" />
          <span>{t('status.loading')}</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-96">
        <Card className="max-w-md">
          <CardContent className="p-6 text-center">
            <AlertTriangle className="h-12 w-12 text-red-500 mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">{t('status.error')}</h3>
            <p className="text-muted-foreground mb-4">{error}</p>
            <Button onClick={fetchAnalytics}>
              <RefreshCw className="h-4 w-4 mr-2" />
              {t('status.retry')}
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!overview) {
    return null;
  }

  return (
    <div className={cn('space-y-6', className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">{t('title')}</h2>
          <p className="text-muted-foreground">
            {t('subtitle')}
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <select
            value={selectedDays}
            onChange={(e) => setSelectedDays(Number(e.target.value))}
            className="px-3 py-2 border rounded-md"
          >
            <option value={7}>{t('periodSelector.last7Days')}</option>
            <option value={30}>{t('periodSelector.last30Days')}</option>
            <option value={90}>{t('periodSelector.last90Days')}</option>
          </select>
          <Button onClick={fetchAnalytics} variant="outline" size="sm">
            <RefreshCw className="h-4 w-4 mr-2" />
            {t('actions.refresh')}
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <KpiCard
          title={t('kpis.totalBuilds.title')}
          value={overview.total_builds}
          subtitle={`${overview.successful_builds} ${t('kpis.successfulBuilds.title').toLowerCase()}`}
          icon={<BarChart3 className="h-5 w-5 text-blue-500" />}
          trend={{
            value: 12,
            isPositive: true
          }}
        />
        <KpiCard
          title={t('kpis.successRate.title')}
          value={`${overview.success_rate.toFixed(1)}%`}
          subtitle={t('kpis.successRate.description')}
          icon={<CheckCircle2 className="h-5 w-5 text-green-500" />}
        />
        <KpiCard
          title={t('kpis.totalTokens.title')}
          value={formatTokens(overview.total_tokens_used)}
          subtitle={t('kpis.totalTokens.description')}
          icon={<Coins className="h-5 w-5 text-orange-500" />}
        />
        <KpiCard
          title={t('kpis.totalCost.title')}
          value={`$${overview.total_cost_usd.toFixed(4)}`}
          subtitle={t('kpis.totalCost.description')}
          icon={<DollarSign className="h-5 w-5 text-purple-500" />}
        />
      </div>

      {/* Main Content Tabs */}
      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">{t('tabs.overview')}</TabsTrigger>
          <TabsTrigger value="builds">{t('tabs.builds')}</TabsTrigger>
          <TabsTrigger value="performance">{t('tabs.performance')}</TabsTrigger>
          <TabsTrigger value="errors">{t('tabs.errors')}</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Recent Builds */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <Clock className="h-5 w-5 mr-2" />
                  {t('sections.recentBuilds')}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-64">
                  <div className="space-y-3">
                    {overview.recent_builds.map((build) => (
                      <div key={build.build_id} className="flex items-center justify-between p-3 border rounded-lg">
                        <div className="flex-1">
                          <div className="flex items-center space-x-2">
                            {getStatusIcon(build.status)}
                            <span className="font-medium">{build.spec_name || build.spec_id}</span>
                            <Badge variant="outline" className={getStatusColor(build.status)}>
                              {build.status}
                            </Badge>
                          </div>
                          <div className="text-sm text-muted-foreground mt-1">
                            {formatDate(build.started_at)} • {formatDuration(build.total_duration_seconds)}
                          </div>
                        </div>
                        <div className="text-right text-sm">
                          <div>{formatTokens(build.total_tokens_used)} tokens</div>
                          <div>{formatCost(build.total_cost_usd)}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>

            {/* Phase Performance */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <Activity className="h-5 w-5 mr-2" />
                  {t('sections.phasePerformance')}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {overview.phase_performance.map((phase) => (
                    <div key={phase.phase_name} className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="font-medium">{phase.phase_name}</span>
                        <span className="text-sm text-muted-foreground">
                          {phase.builds_count} builds
                        </span>
                      </div>
                      <div className="flex items-center space-x-4 text-sm">
                        <span>{formatDuration(phase.duration_seconds)}</span>
                        <span>{formatTokens(phase.tokens_used)} tokens</span>
                        <span>{formatCost(phase.cost_usd)}</span>
                        <Badge variant={phase.success ? 'default' : 'destructive'}>
                          {phase.success ? 'Success' : 'Failed'}
                        </Badge>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="builds" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>All Builds</CardTitle>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-96">
                <div className="space-y-3">
                  {builds.map((build) => (
                    <div key={build.build_id} className="p-4 border rounded-lg">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center space-x-2">
                          {getStatusIcon(build.status)}
                          <span className="font-medium">{build.spec_name || build.spec_id}</span>
                          <Badge variant="outline" className={getStatusColor(build.status)}>
                            {build.status}
                          </Badge>
                        </div>
                        <div className="text-sm text-muted-foreground">
                          {formatDate(build.started_at)}
                        </div>
                      </div>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                        <div>
                          <span className="text-muted-foreground">Duration:</span>
                          <div>{formatDuration(build.total_duration_seconds)}</div>
                        </div>
                        <div>
                          <span className="text-muted-foreground">Tokens:</span>
                          <div>{formatTokens(build.total_tokens_used)}</div>
                        </div>
                        <div>
                          <span className="text-muted-foreground">Cost:</span>
                          <div>{formatCost(build.total_cost_usd)}</div>
                        </div>
                        <div>
                          <span className="text-muted-foreground">QA Iterations:</span>
                          <div>{build.qa_iterations}</div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="performance" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Agent Performance */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <Zap className="h-5 w-5 mr-2" />
                  Agent Performance
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {agentPerformance.map((agent) => (
                    <div key={`${agent.agent_type}-${agent.llm_provider}`} className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="font-medium">{agent.agent_type}</span>
                        <Badge variant="outline">
                          {agent.llm_provider} • {agent.llm_model}
                        </Badge>
                      </div>
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <span className="text-muted-foreground">Success Rate:</span>
                          <div>{agent.success_rate.toFixed(1)}%</div>
                        </div>
                        <div>
                          <span className="text-muted-foreground">Avg Duration:</span>
                          <div>{formatDuration(agent.avg_duration_seconds)}</div>
                        </div>
                        <div>
                          <span className="text-muted-foreground">Avg Tokens:</span>
                          <div>{formatTokens(agent.avg_tokens_per_build)}</div>
                        </div>
                        <div>
                          <span className="text-muted-foreground">Avg Cost:</span>
                          <div>{formatCost(agent.avg_cost_per_build)}</div>
                        </div>
                      </div>
                      <Progress value={agent.success_rate} className="h-2" />
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Token Usage Trend */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <Coins className="h-5 w-5 mr-2" />
                  Token Usage Trend
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {tokenMetrics.slice(-7).map((metric) => (
                    <div key={metric.date} className="flex items-center justify-between">
                      <span className="text-sm">{formatDate(metric.date)}</span>
                      <div className="flex items-center space-x-4 text-sm">
                        <span>{formatTokens(metric.total_tokens)}</span>
                        <span>{formatCost(metric.total_cost_usd)}</span>
                        <span>{metric.builds_count} builds</span>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="errors" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <Bug className="h-5 w-5 mr-2" />
                Top Error Types
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {overview.top_error_types.map((error) => (
                  <div key={error.error_type} className="flex items-center justify-between p-3 border rounded-lg">
                    <div className="flex-1">
                      <div className="flex items-center space-x-2">
                        <span className="font-medium">{error.error_type}</span>
                        <Badge variant="outline">{error.error_category}</Badge>
                      </div>
                      <div className="text-sm text-muted-foreground mt-1">
                        {error.count} occurrences
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-sm font-medium">{error.resolution_rate.toFixed(1)}% resolved</div>
                      <div className="text-xs text-muted-foreground">
                        {error.resolved_count}/{error.count}
                      </div>
                    </div>
                    <Progress value={error.resolution_rate} className="w-20 h-2 ml-4" />
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
