import { useState, useCallback, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Wand2,
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
import { useContextStore } from '../stores/context-store';

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

// biome-ignore lint/correctness/noUnusedFunctionParameters: parameter kept for API compatibility
export function RefactoringView({ projectId }: RefactoringViewProps) {
  const { t } = useTranslation(['refactoring']);
  const [source, setSource] = useState('');
  const [smells, setSmells] = useState<CodeSmell[]>([]);
  const [proposals, setProposals] = useState<RefactoringProposal[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingProposals, setLoadingProposals] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedSmells, setExpandedSmells] = useState<Set<number>>(new Set());

  const projectIndex = useContextStore((s) => s.projectIndex);
  const detectedLanguages = useMemo(() => {
    if (!projectIndex?.services) return [];
    return [...new Set(
      Object.values(projectIndex.services)
        .map((s) => s.language)
        .filter((l): l is string => Boolean(l))
    )];
  }, [projectIndex]);
  const primaryLanguage = detectedLanguages[0] ?? null;

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
        body: JSON.stringify({ source, language: primaryLanguage }),
      });
      const data = await res.json();
      if (data.success) {
        setSmells(data.smells || []);
      } else {
        setError(data.error || t('refactoring:errors.detectionFailed'));
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : t('refactoring:errors.networkError'));
    } finally {
      setLoading(false);
    }
  }, [source, primaryLanguage, t]);

  const handleProposeRefactoring = useCallback(async () => {
    if (!source.trim()) return;
    setLoadingProposals(true);
    setError(null);
    try {
      const backendUrl = import.meta.env?.VITE_BACKEND_URL || '';
      const res = await fetch(`${backendUrl}/api/refactoring/propose`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source, language: primaryLanguage }),
      });
      const data = await res.json();
      if (data.success) {
        setProposals(data.proposals || []);
      } else {
        setError(data.error || t('refactoring:errors.proposalFailed'));
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : t('refactoring:errors.networkError'));
    } finally {
      setLoadingProposals(false);
    }
  }, [source, primaryLanguage, t]);

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
            <h1 className="text-xl font-bold text-foreground">{t('refactoring:title')}</h1>
            <p className="text-sm text-muted-foreground">
              {t('refactoring:description')}
            </p>
          </div>
        </div>

        {/* Source input */}
        <Card>
          <CardContent className="p-5 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                // biome-ignore lint/a11y/noLabelWithoutControl: label association is implicit
{/* biome-ignore lint/a11y/noLabelWithoutControl: intentional  */}
                <label className="text-sm font-medium text-foreground">
                  {primaryLanguage
                    ? t('refactoring:input.labelWithLanguage', { language: primaryLanguage })
                    : t('refactoring:input.label')}
                </label>
                {detectedLanguages.length > 1 && detectedLanguages.slice(1).map((lang) => (
                  <Badge key={lang} variant="outline" className="text-xs text-muted-foreground">{lang}</Badge>
                ))}
              </div>
              <div className="flex gap-2">
                <Button variant="ghost" size="sm" onClick={handlePaste}>
                  <ClipboardPaste className="h-3.5 w-3.5 mr-1.5" />
                  {t('refactoring:actions.paste')}
                </Button>
                {source && (
                  <Button variant="ghost" size="sm" onClick={handleClear}>
                    <Trash2 className="h-3.5 w-3.5 mr-1.5" />
                    {t('refactoring:actions.clear')}
                  </Button>
                )}
              </div>
            </div>
            <Textarea
              value={source}
              onChange={(e) => setSource(e.target.value)}
              placeholder={primaryLanguage
                ? t('refactoring:input.placeholderWithLanguage', { language: primaryLanguage })
                : t('refactoring:input.placeholder')}
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
                {loading ? t('refactoring:actions.detecting') : t('refactoring:actions.detectSmells')}
              </Button>
              <Button variant="outline" onClick={handleProposeRefactoring} disabled={loadingProposals || !source.trim()}>
                {loadingProposals ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Lightbulb className="h-4 w-4 mr-2" />
                )}
                {loadingProposals ? t('refactoring:actions.generating') : t('refactoring:actions.proposeRefactoring')}
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
                  {t('refactoring:smells.title', { count: smells.length })}
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
                    <button type="button"
                      // biome-ignore lint/suspicious/noArrayIndexKey: no stable key available
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
                          <span className="text-xs text-muted-foreground">{t('refactoring:smells.line', { line: smell.line })}</span>
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
                              {t('refactoring:smells.measured')} <span className="font-mono">{smell.metric_value}</span> {t('refactoring:smells.threshold')}:{' '}
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
                {t('refactoring:proposals.title', { count: proposals.length })}
              </h3>
              <div className="space-y-3">
                {proposals.map((p, idx) => {
                  const risk = p.risk_level?.toLowerCase() || 'low';
                  const rcfg = RISK_CONFIG[risk] || RISK_CONFIG.low;

                  return (
{/* biome-ignore lint/suspicious/noArrayIndexKey: no stable key available */}
                    <div key={idx} className="rounded-lg border border-border p-4 space-y-2">
                      <div className="flex items-center gap-3">
                        <FileCode2 className="h-4 w-4 text-primary shrink-0" />
                        <span className="text-sm font-semibold text-foreground">{p.pattern?.replace(/_/g, ' ')}</span>
                        {p.symbol && (
                          <span className="text-xs font-mono text-muted-foreground">{p.symbol}</span>
                        )}
                        <Badge variant="outline" className={cn('text-xs ml-auto', rcfg.color, rcfg.bg)}>
                          {t('refactoring:proposals.risk')}: {risk}
                        </Badge>
                      </div>
                      <p className="text-sm text-muted-foreground">{p.description}</p>
                      {p.impact && (
                        <p className="text-xs text-muted-foreground">
                          <span className="font-medium text-foreground">{t('refactoring:proposals.impact')}:</span> {p.impact}
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



