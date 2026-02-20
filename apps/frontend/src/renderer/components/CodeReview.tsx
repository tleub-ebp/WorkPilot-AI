import { useState, useCallback } from 'react';
import {
  FileCode2,
  Play,
  Loader2,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Info,
  ClipboardPaste,
  Trash2
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

interface ReviewIssue {
  rule: string;
  severity: string;
  message: string;
  line?: number;
  file?: string;
  suggestion?: string;
}

interface ReviewResult {
  score: number;
  issues: ReviewIssue[];
  summary?: string;
  passed: boolean;
}

interface CodeReviewProps {
  projectId: string;
}

// ---------------------------------------------------------------------------
// Severity badge
// ---------------------------------------------------------------------------

function SeverityBadge({ severity }: { severity: string }) {
  const variants: Record<string, { className: string; icon: React.ElementType }> = {
    critical: { className: 'bg-red-500/10 text-red-500 border-red-500/20', icon: XCircle },
    high: { className: 'bg-red-400/10 text-red-400 border-red-400/20', icon: XCircle },
    medium: { className: 'bg-amber-500/10 text-amber-500 border-amber-500/20', icon: AlertTriangle },
    low: { className: 'bg-blue-500/10 text-blue-500 border-blue-500/20', icon: Info },
    info: { className: 'bg-gray-500/10 text-gray-500 border-gray-500/20', icon: Info },
  };
  const v = variants[severity.toLowerCase()] || variants.info;
  const Icon = v.icon;

  return (
    <Badge variant="outline" className={cn('gap-1 text-xs', v.className)}>
      <Icon className="h-3 w-3" />
      {severity}
    </Badge>
  );
}

// ---------------------------------------------------------------------------
// Score gauge
// ---------------------------------------------------------------------------

function ScoreGauge({ score }: { score: number }) {
  const color =
    score >= 80 ? 'text-emerald-500' : score >= 60 ? 'text-amber-500' : 'text-red-500';
  const bgColor =
    score >= 80 ? 'bg-emerald-500' : score >= 60 ? 'bg-amber-500' : 'bg-red-500';

  return (
    <div className="flex items-center gap-4">
      <div className="relative h-20 w-20">
        <svg className="h-20 w-20 -rotate-90" viewBox="0 0 36 36">
          <path
            d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
            fill="none"
            stroke="currentColor"
            className="text-secondary"
            strokeWidth="3"
          />
          <path
            d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
            fill="none"
            stroke="currentColor"
            className={color}
            strokeWidth="3"
            strokeDasharray={`${score}, 100`}
            strokeLinecap="round"
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className={cn('text-lg font-bold', color)}>{score}</span>
        </div>
      </div>
      <div>
        <p className="text-sm font-semibold text-foreground">Quality Score</p>
        <div className="mt-1 flex items-center gap-1.5">
          <div className={cn('h-2 w-2 rounded-full', bgColor)} />
          <span className="text-xs text-muted-foreground">
            {score >= 80 ? 'Good' : score >= 60 ? 'Needs improvement' : 'Poor'}
          </span>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function CodeReview({ projectId }: CodeReviewProps) {
  const [diff, setDiff] = useState('');
  const [result, setResult] = useState<ReviewResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleReview = useCallback(async () => {
    if (!diff.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const backendUrl = import.meta.env?.VITE_BACKEND_URL || '';
      const res = await fetch(`${backendUrl}/api/code-review/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ diff }),
      });
      const data = await res.json();
      if (data.success) {
        setResult(data.review);
      } else {
        setError(data.error || 'Review failed');
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Network error');
    } finally {
      setLoading(false);
    }
  }, [diff]);

  const handlePaste = useCallback(async () => {
    try {
      const text = await navigator.clipboard.readText();
      setDiff(text);
    } catch {
      // clipboard access denied
    }
  }, []);

  return (
    <ScrollArea className="h-full">
      <div className="p-6 space-y-6 max-w-5xl mx-auto">
        {/* Header */}
        <div className="flex items-center gap-3">
          <FileCode2 className="h-6 w-6 text-primary" />
          <div>
            <h1 className="text-xl font-bold text-foreground">AI Code Review</h1>
            <p className="text-sm text-muted-foreground">
              Paste a diff or code snippet to get an automated quality review
            </p>
          </div>
        </div>

        {/* Input */}
        <Card>
          <CardContent className="p-5 space-y-3">
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium text-foreground">Diff / Code to review</label>
              <div className="flex gap-2">
                <Button variant="ghost" size="sm" onClick={handlePaste}>
                  <ClipboardPaste className="h-3.5 w-3.5 mr-1.5" />
                  Paste
                </Button>
                {diff && (
                  <Button variant="ghost" size="sm" onClick={() => { setDiff(''); setResult(null); }}>
                    <Trash2 className="h-3.5 w-3.5 mr-1.5" />
                    Clear
                  </Button>
                )}
              </div>
            </div>
            <Textarea
              value={diff}
              onChange={(e) => setDiff(e.target.value)}
              placeholder={'Paste your git diff or code snippet here...\n\nExample:\n--- a/src/auth.py\n+++ b/src/auth.py\n@@ -10,6 +10,7 @@\n def login(username, password):\n+    password = base64.b64decode(password)  # security issue\n     user = db.query(username)'}
              className="min-h-[200px] font-mono text-xs"
              spellCheck={false}
            />
            <Button onClick={handleReview} disabled={loading || !diff.trim()}>
              {loading ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Play className="h-4 w-4 mr-2" />
              )}
              {loading ? 'Analyzing...' : 'Run Review'}
            </Button>
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

        {/* Results */}
        {result && (
          <div className="space-y-6">
            {/* Score & Summary */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card>
                <CardContent className="p-5">
                  <ScoreGauge score={result.score} />
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-5">
                  <div className="flex items-center gap-2 mb-3">
                    {result.passed ? (
                      <CheckCircle2 className="h-5 w-5 text-emerald-500" />
                    ) : (
                      <XCircle className="h-5 w-5 text-red-500" />
                    )}
                    <span className={cn('text-sm font-semibold', result.passed ? 'text-emerald-500' : 'text-red-500')}>
                      {result.passed ? 'Review Passed' : 'Review Failed'}
                    </span>
                  </div>
                  {result.summary && (
                    <p className="text-sm text-muted-foreground">{result.summary}</p>
                  )}
                  <div className="mt-3 flex gap-3 text-xs text-muted-foreground">
                    <span>{result.issues.length} issue{result.issues.length !== 1 ? 's' : ''} found</span>
                    <span>{result.issues.filter(i => i.severity === 'critical' || i.severity === 'high').length} critical/high</span>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Issues list */}
            {result.issues.length > 0 && (
              <Card>
                <CardContent className="p-5">
                  <h3 className="text-sm font-semibold text-foreground mb-4">Issues</h3>
                  <div className="space-y-3">
                    {result.issues.map((issue, idx) => (
                      <div
                        key={idx}
                        className="rounded-lg border border-border p-4 space-y-2"
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="flex items-center gap-2 flex-wrap">
                            <SeverityBadge severity={issue.severity} />
                            <span className="text-xs font-mono text-muted-foreground">{issue.rule}</span>
                            {issue.line && (
                              <span className="text-xs text-muted-foreground">line {issue.line}</span>
                            )}
                          </div>
                        </div>
                        <p className="text-sm text-foreground">{issue.message}</p>
                        {issue.suggestion && (
                          <div className="rounded-md bg-secondary/50 p-3 text-xs text-muted-foreground">
                            <span className="font-medium text-foreground">Suggestion: </span>
                            {issue.suggestion}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        )}
      </div>
    </ScrollArea>
  );
}
