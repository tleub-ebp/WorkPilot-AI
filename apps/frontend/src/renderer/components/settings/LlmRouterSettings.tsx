import { useState } from 'react';
import { Router, Zap, FlaskConical, ArrowDownUp, BarChart3 } from 'lucide-react';
import { SettingsSection } from './SettingsSection';
import { cn } from '@/lib/utils';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type RoutingStrategy = 'best_performance' | 'cheapest' | 'lowest_latency' | 'round_robin';

interface ProviderEntry {
  provider: string;
  model: string;
  capabilities: string[];
  priority: number;
  isLocal: boolean;
  enabled: boolean;
}

interface FallbackChain {
  taskType: string;
  chain: string[];
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function LlmRouterSettings() {
  const [strategy, setStrategy] = useState<RoutingStrategy>('best_performance');

  const [providers] = useState<ProviderEntry[]>([
    { provider: 'Anthropic', model: 'claude-sonnet-4-20250514', capabilities: ['coding', 'planning', 'review'], priority: 1, isLocal: false, enabled: true },
    { provider: 'OpenAI', model: 'gpt-4o', capabilities: ['coding', 'review'], priority: 2, isLocal: false, enabled: true },
    { provider: 'Mistral', model: 'mistral-large', capabilities: ['coding', 'planning'], priority: 3, isLocal: false, enabled: false },
    { provider: 'Ollama', model: 'llama3:8b', capabilities: ['quick_feedback', 'coding'], priority: 5, isLocal: true, enabled: true },
  ]);

  const [fallbacks] = useState<FallbackChain[]>([
    { taskType: 'coding', chain: ['Anthropic / claude-sonnet-4-20250514', 'OpenAI / gpt-4o', 'Ollama / llama3:8b'] },
    { taskType: 'planning', chain: ['Anthropic / claude-sonnet-4-20250514', 'Mistral / mistral-large'] },
    { taskType: 'review', chain: ['Anthropic / claude-sonnet-4-20250514', 'OpenAI / gpt-4o'] },
  ]);

  const strategies: { id: RoutingStrategy; label: string; desc: string; icon: React.ReactNode }[] = [
    { id: 'best_performance', label: 'Best Performance', desc: 'Prioritize quality score', icon: <Zap className="h-4 w-4" /> },
    { id: 'cheapest', label: 'Cheapest', desc: 'Minimize cost per task', icon: <ArrowDownUp className="h-4 w-4" /> },
    { id: 'lowest_latency', label: 'Lowest Latency', desc: 'Fastest response time', icon: <BarChart3 className="h-4 w-4" /> },
    { id: 'round_robin', label: 'Round Robin', desc: 'Distribute evenly', icon: <Router className="h-4 w-4" /> },
  ];

  return (
    <SettingsSection
      title="LLM Router"
      description="Configure intelligent provider routing with fallback chains, A/B testing, and strategy-based selection."
    >
      <div className="space-y-8">
        {/* Routing Strategy */}
        <div>
          <h4 className="text-sm font-semibold mb-1 flex items-center gap-2">
            <Router className="h-4 w-4 text-primary" />
            Default Routing Strategy
          </h4>
          <p className="text-xs text-muted-foreground mb-3">
            How the router selects a provider when multiple are available.
          </p>
          <div className="grid grid-cols-2 gap-3">
            {strategies.map((s) => (
              <button
                key={s.id}
                onClick={() => setStrategy(s.id)}
                className={cn(
                  'flex items-start gap-3 rounded-lg border p-3 text-left transition-colors',
                  strategy === s.id
                    ? 'border-primary bg-primary/5 ring-1 ring-primary'
                    : 'border-border hover:bg-accent/50'
                )}
              >
                <span className={cn('mt-0.5', strategy === s.id ? 'text-primary' : 'text-muted-foreground')}>{s.icon}</span>
                <div>
                  <span className="text-sm font-medium">{s.label}</span>
                  <p className="text-xs text-muted-foreground">{s.desc}</p>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Registered Providers */}
        <div>
          <h4 className="text-sm font-semibold mb-1 flex items-center gap-2">
            <Zap className="h-4 w-4 text-primary" />
            Registered Providers
          </h4>
          <p className="text-xs text-muted-foreground mb-3">
            Providers available for routing. Configure accounts in Settings &gt; Accounts.
          </p>
          <div className="rounded-md border border-border overflow-hidden">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border bg-muted/40">
                  <th className="text-left px-3 py-2 font-medium text-muted-foreground">Provider / Model</th>
                  <th className="text-left px-3 py-2 font-medium text-muted-foreground">Capabilities</th>
                  <th className="text-center px-3 py-2 font-medium text-muted-foreground">Priority</th>
                  <th className="text-center px-3 py-2 font-medium text-muted-foreground">Status</th>
                </tr>
              </thead>
              <tbody>
                {providers.map((p) => (
                  <tr key={`${p.provider}-${p.model}`} className="border-b border-border last:border-0">
                    <td className="px-3 py-2">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{p.provider}</span>
                        <span className="text-muted-foreground">/ {p.model}</span>
                        {p.isLocal && (
                          <span className="rounded-full bg-green-500/15 text-green-600 px-1.5 py-0 text-[10px] font-medium">local</span>
                        )}
                      </div>
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex flex-wrap gap-1">
                        {p.capabilities.map((c) => (
                          <span key={c} className="rounded bg-accent px-1.5 py-0 text-[10px]">{c}</span>
                        ))}
                      </div>
                    </td>
                    <td className="px-3 py-2 text-center font-mono">{p.priority}</td>
                    <td className="px-3 py-2 text-center">
                      <span className={cn(
                        'rounded-full px-2 py-0.5 text-[10px] font-medium',
                        p.enabled ? 'bg-green-500/15 text-green-600' : 'bg-muted text-muted-foreground'
                      )}>
                        {p.enabled ? 'Active' : 'Disabled'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Fallback Chains */}
        <div>
          <h4 className="text-sm font-semibold mb-1 flex items-center gap-2">
            <ArrowDownUp className="h-4 w-4 text-primary" />
            Fallback Chains
          </h4>
          <p className="text-xs text-muted-foreground mb-3">
            If the primary provider is rate-limited or unavailable, the router automatically falls back to the next in the chain.
          </p>
          <div className="space-y-3">
            {fallbacks.map((fb) => (
              <div key={fb.taskType} className="rounded-md border border-border p-3">
                <p className="text-xs font-semibold text-foreground mb-2 capitalize">{fb.taskType}</p>
                <div className="flex items-center gap-1.5 flex-wrap">
                  {fb.chain.map((entry, i) => (
                    <span key={i} className="flex items-center gap-1.5">
                      <span className="rounded bg-accent px-2 py-0.5 text-[10px] font-mono">{entry}</span>
                      {i < fb.chain.length - 1 && <span className="text-muted-foreground text-xs">→</span>}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* A/B Testing */}
        <div>
          <h4 className="text-sm font-semibold mb-1 flex items-center gap-2">
            <FlaskConical className="h-4 w-4 text-primary" />
            A/B Testing
          </h4>
          <p className="text-xs text-muted-foreground mb-3">
            Compare two providers on the same task type. The router alternates between them and tracks quality, latency, and cost.
          </p>
          <div className="rounded-md border border-dashed border-border bg-muted/20 p-6 text-center">
            <FlaskConical className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
            <p className="text-sm text-muted-foreground">No active A/B tests</p>
            <p className="text-xs text-muted-foreground mt-1">
              Create a test from the Command Palette or from the task detail view.
            </p>
          </div>
        </div>
      </div>
    </SettingsSection>
  );
}
