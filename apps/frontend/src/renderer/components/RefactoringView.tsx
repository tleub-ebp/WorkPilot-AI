import { useState, useCallback } from 'react';
import {
  Wand2,
  Play,
  Loader2,
  AlertTriangle,
  Bug,
  Lightbulb,
  FileCode2,
  ClipboardPaste,
  Trash2,
  ChevronDown,
  ChevronRight
} from 'lucide-react';
import { Button } from './ui/button';
import { Card, CardContent } from './ui/card';
import { Badge } from './ui/badge';
import { Textarea } from './ui/textarea';
import { ScrollArea } from './ui/scroll-area';
import { cn } from '../lib/utils';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface CodeSmell {
  smell_type: string;
  severity: string;
  message: string;
  line?: number;
  symbol?: string;
  metric_value?: number;
  threshold?: number;
}

interface RefactoringProposal {
  pattern: string;
  description: string;
  risk_level: string;
  symbol?: string;
  impact?: string;
}

interface RefactoringViewProps {
  projectId: string;
}

// ---------------------------------------------------------------------------
// Severity helpers
// ---------------------------------------------------------------------------

const SEVERITY_CONFIG: Record<string, { color: string; bg: string; label: string }> = {
  critical: { color: 'text-red-500', bg: 'bg-red-500/10', label: 'Critical' },
  high: { color: 'text-red-400', bg: 'bg-red-400/10', label: 'High' },
  medium: { color: 'text-amber-500', bg: 'bg-amber-500/10', label: 'Medium' },
  low: { color: 'text-blue-500', bg: 'bg-blue-500/10', label: 'Low' },
  info: { color: 'text-gray-400', bg: 'bg-gray-400/10', label: 'Info' },
};

const RISK_CONFIG: Record<string, { color: string; bg: string }> = {
  high: { color: 'text-red-500', bg: 'bg-red-500/10' },
  medium: { color: 'text-amber-500', bg: 'bg-amber-500/10' },
  low: { color: 'text-emerald-500', bg: 'bg-emerald-500/10' },
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function RefactoringView({ projectId }: RefactoringViewProps) {
  const [source, setSource] = useState('');
  const [smells, setSmells] = useState<CodeSmell[]>([]);
  const [proposals, setProposals] = useState<RefactoringProposal[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingProposals, setLoadingProposals] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedSmells, setExpandedSmells] = useState<Set<number>>(new Set());

  const toggleSmell = (idx: number) => {
    setExpandedSmells((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  };

  const handleDetectSmells = useCallback(async () => {
    if (!source.trim()) return;
    setLoading(true);
    setError(null);
    setSmells([]);
    setProposals([]);
    try {
      const backendUrl = import.meta.env?.VITE_BACKEND_URL || '';
      const res = await fetch(`${backendUrl}/api/refactoring/detect-smells`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source }),
      });
      const data = await res.json();
      if (data.success) {
        setSmells(data.smells || []);
      } else {
        setError(data.error || 'Detection failed');
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Network error');
    } finally {
      setLoading(false);
    }
  }, [source]);

  const handleProposeRefactoring = useCallback(async () => {
    if (!source.trim()) return;
    setLoadingProposals(true);
    setError(null);
    try {
      const backendUrl = import.meta.env?.VITE_BACKEND_URL || '';
      const res = await fetch(`${backendUrl}/api/refactoring/propose`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source }),
      });
      const data = await res.json();
      if (data.success) {
        setProposals(data.proposals || []);
      } else {
        setError(data.error || 'Proposal generation failed');
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Network error');
    } finally {
      setLoadingProposals(false);
    }
  }, [source]);

  const handlePaste = useCallback(async () => {
    try {
      const text = await navigator.clipboard.readText();
      setSource(text);
    } catch {
      // clipboard access denied
    }
  }, []);

  const handleClear = () => {
    setSource('');
    setSmells([]);
    setProposals([]);
    setError(null);
  };

  return (
    <ScrollArea className="h-full">
      <div className="p-6 space-y-6 max-w-5xl mx-auto">
        {/* Header */}
        <div className="flex items-center gap-3">
          <Wand2 className="h-6 w-6 text-primary" />
          <div>
            <h1 className="text-xl font-bold text-foreground">Refactoring Agent</h1>
            <p className="text-sm text-muted-foreground">
              Detect code smells and get refactoring proposals
            </p>
          </div>
        </div>

        {/* Source input */}
        <Card>
          <CardContent className="p-5 space-y-3">
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium text-foreground">Python source code</label>
              <div className="flex gap-2">
                <Button variant="ghost" size="sm" onClick={handlePaste}>
                  <ClipboardPaste className="h-3.5 w-3.5 mr-1.5" />
                  Paste
                </Button>
                {source && (
                  <Button variant="ghost" size="sm" onClick={handleClear}>
                    <Trash2 className="h-3.5 w-3.5 mr-1.5" />
                    Clear
                  </Button>
                )}
              </div>
            </div>
            <Textarea
              value={source}
              onChange={(e) => setSource(e.target.value)}
              placeholder="Paste Python source code here to analyze..."
              className="min-h-[200px] font-mono text-xs"
              spellCheck={false}
            />
            <div className="flex gap-2">
              <Button onClick={handleDetectSmells} disabled={loading || !source.trim()}>
                {loading ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Bug className="h-4 w-4 mr-2" />
                )}
                {loading ? 'Detecting...' : 'Detect Code Smells'}
              </Button>
              <Button variant="outline" onClick={handleProposeRefactoring} disabled={loadingProposals || !source.trim()}>
                {loadingProposals ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Lightbulb className="h-4 w-4 mr-2" />
                )}
                {loadingProposals ? 'Generating...' : 'Propose Refactoring'}
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Error */}
        {error && (
          <Card className="border-red-500/30">
            <CardContent className="p-4 flex items-center gap-3 text-red-500">
              <AlertTriangle className="h-5 w-5 shrink-0" />
              <p className="text-sm">{error}</p>
            </CardContent>
          </Card>
        )}

        {/* Smells */}
        {smells.length > 0 && (
          <Card>
            <CardContent className="p-5">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-semibold text-foreground">
                  Code Smells ({smells.length})
                </h3>
                <div className="flex gap-2">
                  {Object.entries(
                    smells.reduce<Record<string, number>>((acc, s) => {
                      const sev = s.severity?.toLowerCase() || 'info';
                      acc[sev] = (acc[sev] || 0) + 1;
                      return acc;
                    }, {})
                  ).map(([sev, count]) => {
                    const cfg = SEVERITY_CONFIG[sev] || SEVERITY_CONFIG.info;
                    return (
                      <Badge key={sev} variant="outline" className={cn('text-xs', cfg.color, cfg.bg)}>
                        {cfg.label}: {count}
                      </Badge>
                    );
                  })}
                </div>
              </div>
              <div className="space-y-2">
                {smells.map((smell, idx) => {
                  const sev = smell.severity?.toLowerCase() || 'info';
                  const cfg = SEVERITY_CONFIG[sev] || SEVERITY_CONFIG.info;
                  const expanded = expandedSmells.has(idx);

                  return (
                    <button
                      key={idx}
                      onClick={() => toggleSmell(idx)}
                      className="w-full text-left rounded-lg border border-border p-3 hover:bg-accent/30 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        {expanded ? (
                          <ChevronDown className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                        ) : (
                          <ChevronRight className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                        )}
                        <div className={cn('h-2 w-2 rounded-full shrink-0', cfg.color.replace('text-', 'bg-'))} />
                        <span className="text-sm font-medium text-foreground flex-1 truncate">
                          {smell.smell_type?.replace(/_/g, ' ')}
                        </span>
                        {smell.symbol && (
                          <span className="text-xs font-mono text-muted-foreground">{smell.symbol}</span>
                        )}
                        {smell.line && (
                          <span className="text-xs text-muted-foreground">L{smell.line}</span>
                        )}
                        <Badge variant="outline" className={cn('text-xs', cfg.color, cfg.bg)}>
                          {cfg.label}
                        </Badge>
                      </div>
                      {expanded && (
                        <div className="mt-2 pl-7 space-y-1.5">
                          <p className="text-xs text-muted-foreground">{smell.message}</p>
                          {smell.metric_value !== undefined && smell.threshold !== undefined && (
                            <p className="text-xs text-muted-foreground">
                              Measured: <span className="font-mono">{smell.metric_value}</span> / Threshold:{' '}
                              <span className="font-mono">{smell.threshold}</span>
                            </p>
                          )}
                        </div>
                      )}
                    </button>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Proposals */}
        {proposals.length > 0 && (
          <Card>
            <CardContent className="p-5">
              <h3 className="text-sm font-semibold text-foreground mb-4">
                Refactoring Proposals ({proposals.length})
              </h3>
              <div className="space-y-3">
                {proposals.map((p, idx) => {
                  const risk = p.risk_level?.toLowerCase() || 'low';
                  const rcfg = RISK_CONFIG[risk] || RISK_CONFIG.low;

                  return (
                    <div key={idx} className="rounded-lg border border-border p-4 space-y-2">
                      <div className="flex items-center gap-3">
                        <FileCode2 className="h-4 w-4 text-primary shrink-0" />
                        <span className="text-sm font-semibold text-foreground">{p.pattern?.replace(/_/g, ' ')}</span>
                        {p.symbol && (
                          <span className="text-xs font-mono text-muted-foreground">{p.symbol}</span>
                        )}
                        <Badge variant="outline" className={cn('text-xs ml-auto', rcfg.color, rcfg.bg)}>
                          Risk: {risk}
                        </Badge>
                      </div>
                      <p className="text-sm text-muted-foreground">{p.description}</p>
                      {p.impact && (
                        <p className="text-xs text-muted-foreground">
                          <span className="font-medium text-foreground">Impact:</span> {p.impact}
                        </p>
                      )}
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </ScrollArea>
  );
}
