import { useState } from 'react';
import { ShieldAlert, Activity, AlertTriangle, BarChart3, Settings2 } from 'lucide-react';
import { SettingsSection } from './SettingsSection';
import { cn } from '@/lib/utils';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface AnomalyThresholds {
  trust_score_pause: number;
  trust_score_terminate: number;
  mass_deletion_count: number;
  max_error_count: number;
  rapid_change_window_s: number;
  excessive_token_multiplier: number;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function AnomalyDetectionSettings() {
  const [enabled, setEnabled] = useState(true);
  const [thresholds, setThresholds] = useState<AnomalyThresholds>({
    trust_score_pause: 40,
    trust_score_terminate: 20,
    mass_deletion_count: 5,
    max_error_count: 10,
    rapid_change_window_s: 10,
    excessive_token_multiplier: 5,
  });

  const handleChange = (key: keyof AnomalyThresholds, value: number) => {
    setThresholds((prev) => ({ ...prev, [key]: value }));
  };

  const anomalyTypes = [
    { type: 'Mass file deletion', severity: 'critical', impact: -30 },
    { type: 'Sensitive file access', severity: 'high', impact: -25 },
    { type: 'Dangerous command', severity: 'high', impact: -25 },
    { type: 'Unexpected network access', severity: 'high', impact: -20 },
    { type: 'Path traversal attempt', severity: 'high', impact: -20 },
    { type: 'Rapid file changes', severity: 'medium', impact: -15 },
    { type: 'Excessive token usage', severity: 'medium', impact: -15 },
    { type: 'System config modification', severity: 'medium', impact: -15 },
    { type: 'Repetitive errors', severity: 'low', impact: -10 },
    { type: 'Long running session', severity: 'low', impact: -5 },
  ];

  const severityColor: Record<string, string> = {
    critical: 'bg-red-500/15 text-red-600',
    high: 'bg-orange-500/15 text-orange-600',
    medium: 'bg-amber-500/15 text-amber-600',
    low: 'bg-blue-500/15 text-blue-600',
  };

  return (
    <SettingsSection
      title="Anomaly Detection"
      description="Monitor agent behavior in real time. Automatically pause or terminate sessions when suspicious activity is detected."
    >
      <div className="space-y-8">
        {/* Enable toggle */}
        <div className="flex items-center justify-between rounded-lg border border-border p-4">
          <div className="flex items-center gap-3">
            <ShieldAlert className="h-5 w-5 text-primary" />
            <div>
              <p className="text-sm font-medium">Enable Anomaly Detection</p>
              <p className="text-xs text-muted-foreground">Monitor all agent sessions for suspicious behavior</p>
            </div>
          </div>
          <button
            onClick={() => setEnabled(!enabled)}
            className={cn(
              'relative h-6 w-11 rounded-full transition-colors',
              enabled ? 'bg-primary' : 'bg-muted-foreground/30'
            )}
          >
            <span className={cn(
              'absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform',
              enabled ? 'translate-x-5.5 left-0' : 'left-0.5'
            )} />
          </button>
        </div>

        {/* Trust Score Thresholds */}
        <div>
          <h4 className="text-sm font-semibold mb-1 flex items-center gap-2">
            <Activity className="h-4 w-4 text-primary" />
            Trust Score Thresholds
          </h4>
          <p className="text-xs text-muted-foreground mb-3">
            Each agent session starts at 100. Anomalies reduce the score. Actions trigger at these thresholds.
          </p>
          <div className="space-y-4">
            <div className="space-y-1">
              <div className="flex items-center justify-between">
                <label className="text-xs font-medium text-muted-foreground">Pause threshold</label>
                <span className="text-xs font-mono tabular-nums text-amber-600">{thresholds.trust_score_pause}</span>
              </div>
              <input
                type="range" min={10} max={80} step={5}
                value={thresholds.trust_score_pause}
                onChange={(e) => handleChange('trust_score_pause', Number(e.target.value))}
                className="w-full accent-amber-500"
              />
              <p className="text-[10px] text-muted-foreground">Agent is paused and a notification is sent</p>
            </div>
            <div className="space-y-1">
              <div className="flex items-center justify-between">
                <label className="text-xs font-medium text-muted-foreground">Terminate threshold</label>
                <span className="text-xs font-mono tabular-nums text-red-600">{thresholds.trust_score_terminate}</span>
              </div>
              <input
                type="range" min={0} max={50} step={5}
                value={thresholds.trust_score_terminate}
                onChange={(e) => handleChange('trust_score_terminate', Number(e.target.value))}
                className="w-full accent-red-500"
              />
              <p className="text-[10px] text-muted-foreground">Agent is terminated immediately</p>
            </div>
          </div>
        </div>

        {/* Detection Limits */}
        <div>
          <h4 className="text-sm font-semibold mb-1 flex items-center gap-2">
            <Settings2 className="h-4 w-4 text-primary" />
            Detection Limits
          </h4>
          <p className="text-xs text-muted-foreground mb-3">
            Fine-tune when specific anomaly types trigger.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {[
              { key: 'mass_deletion_count' as const, label: 'Mass deletion count', min: 1, max: 20, step: 1, desc: 'File deletions before alert' },
              { key: 'max_error_count' as const, label: 'Max repetitive errors', min: 3, max: 30, step: 1, desc: 'Errors before alert' },
              { key: 'rapid_change_window_s' as const, label: 'Rapid change window (s)', min: 5, max: 60, step: 5, desc: 'Time window for rapid changes' },
              { key: 'excessive_token_multiplier' as const, label: 'Token usage multiplier', min: 2, max: 10, step: 1, desc: '× baseline before alert' },
            ].map(({ key, label, min, max, step, desc }) => (
              <div key={key} className="space-y-1">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-medium text-muted-foreground">{label}</label>
                  <span className="text-xs font-mono tabular-nums text-foreground">{thresholds[key]}</span>
                </div>
                <input
                  type="range" min={min} max={max} step={step}
                  value={thresholds[key]}
                  onChange={(e) => handleChange(key, Number(e.target.value))}
                  className="w-full accent-primary"
                />
                <p className="text-[10px] text-muted-foreground">{desc}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Anomaly Types Reference */}
        <div>
          <h4 className="text-sm font-semibold mb-1 flex items-center gap-2">
            <BarChart3 className="h-4 w-4 text-primary" />
            Anomaly Types
          </h4>
          <p className="text-xs text-muted-foreground mb-3">
            10 anomaly types are monitored. Each reduces the trust score by a fixed amount.
          </p>
          <div className="rounded-md border border-border overflow-hidden">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border bg-muted/40">
                  <th className="text-left px-3 py-2 font-medium text-muted-foreground">Anomaly</th>
                  <th className="text-left px-3 py-2 font-medium text-muted-foreground">Severity</th>
                  <th className="text-right px-3 py-2 font-medium text-muted-foreground">Score Impact</th>
                </tr>
              </thead>
              <tbody>
                {anomalyTypes.map((a) => (
                  <tr key={a.type} className="border-b border-border last:border-0">
                    <td className="px-3 py-1.5">{a.type}</td>
                    <td className="px-3 py-1.5">
                      <span className={cn('rounded-full px-2 py-0.5 text-[10px] font-medium', severityColor[a.severity])}>
                        {a.severity}
                      </span>
                    </td>
                    <td className="px-3 py-1.5 text-right font-mono text-destructive">{a.impact}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Sensitive Paths */}
        <div>
          <h4 className="text-sm font-semibold mb-1 flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-destructive" />
            Sensitive Paths (always monitored)
          </h4>
          <div className="flex flex-wrap gap-1.5 mt-2">
            {['.env', '.git/', '.ssh/', '.aws/', 'credentials', 'id_rsa', '.npmrc', '.pypirc', 'secrets', '.gnupg/', 'authorized_keys', '.docker/config.json', 'shadow'].map((p) => (
              <span key={p} className="rounded-full bg-destructive/10 px-2.5 py-0.5 text-xs font-mono text-destructive">
                {p}
              </span>
            ))}
          </div>
        </div>
      </div>
    </SettingsSection>
  );
}
