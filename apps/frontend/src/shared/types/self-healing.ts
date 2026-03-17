/**
 * Self-Healing Codebase + Incident Responder Types
 *
 * Feature #3 (Tier S+) - Unified surveillance, detection and auto-correction.
 */

// ── Enums ──────────────────────────────────────────────────

export type IncidentMode = 'cicd' | 'production' | 'proactive';

export type IncidentSeverity = 'critical' | 'high' | 'medium' | 'low' | 'info';

export type HealingStatus =
  | 'pending'
  | 'analyzing'
  | 'fixing'
  | 'qa_running'
  | 'pr_created'
  | 'resolved'
  | 'escalated'
  | 'failed';

export type IncidentSource =
  | 'git_push'
  | 'ci_failure'
  | 'sentry'
  | 'datadog'
  | 'cloudwatch'
  | 'new_relic'
  | 'pagerduty'
  | 'proactive_scan';

// ── Core Models ────────────────────────────────────────────

export interface Incident {
  id: string;
  mode: IncidentMode;
  source: IncidentSource;
  severity: IncidentSeverity;
  title: string;
  description: string;
  status: HealingStatus;
  created_at: string;
  resolved_at?: string;
  source_data: Record<string, unknown>;
  root_cause?: string;
  affected_files: string[];
  regression_commit?: string;
  fix_branch?: string;
  fix_pr_url?: string;
  fix_worktree?: string;
  qa_result?: Record<string, unknown>;
  error_message?: string;
  stack_trace?: string;
}

export interface HealingStep {
  name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  detail?: string;
  started_at?: string;
  completed_at?: string;
}

export interface HealingOperation {
  id: string;
  incident: Incident | null;
  started_at: string;
  completed_at?: string;
  steps: HealingStep[];
  duration_seconds?: number;
  success: boolean;
}

export interface FragilityReport {
  file_path: string;
  risk_score: number;
  cyclomatic_complexity: number;
  git_churn_count: number;
  test_coverage_percent: number;
  last_incident_days?: number;
  suggested_tests: string[];
}

// ── Configuration ──────────────────────────────────────────

export interface CICDConfig {
  enabled: boolean;
  watchBranches: string[];
  autoFixEnabled: boolean;
  autoCreatePR: boolean;
}

export interface ProductionConfig {
  enabled: boolean;
  connectedSources: IncidentSource[];
  autoAnalyze: boolean;
  autoFix: boolean;
  severityThreshold: IncidentSeverity;
}

export interface ProactiveConfig {
  enabled: boolean;
  scanFrequency: 'daily' | 'weekly' | 'on_push';
  riskThreshold: number;
  autoGenerateTests: boolean;
}

// ── Dashboard ──────────────────────────────────────────────

export interface SelfHealingStats {
  totalIncidents: number;
  resolvedIncidents: number;
  activeIncidents: number;
  avgResolutionTime: number;
  autoFixRate: number;
}

export interface SelfHealingDashboardData {
  incidents: Incident[];
  activeOperations: HealingOperation[];
  fragilityReports: FragilityReport[];
  stats: SelfHealingStats;
  productionStatus: {
    connected_sources: string[];
    configs: Record<string, unknown>;
  };
  proactiveSummary: {
    scanned: boolean;
    files_at_risk: number;
    avg_risk: number;
    max_risk: number;
    top_files: Array<{ file: string; risk: number }>;
  };
}

// ── IPC Payloads ───────────────────────────────────────────

export interface SelfHealingConfigUpdate {
  cicd?: Partial<CICDConfig>;
  production?: Partial<ProductionConfig>;
  proactive?: Partial<ProactiveConfig>;
}

export interface TriggerFixRequest {
  incidentId: string;
}

export interface ConnectSourceRequest {
  source: IncidentSource;
  serverUrl: string;
  apiKey?: string;
  projectId?: string;
  environment?: string;
}

export interface DisconnectSourceRequest {
  source: IncidentSource;
}
