import { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { 
  Check, 
  Copy, 
  Loader2, 
  TrendingUp, 
  AlertTriangle, 
  Clock, 
  DollarSign, 
  RotateCcw, 
  Info,
  Target,
  Zap,
  Shield
} from 'lucide-react';

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '../ui/dialog';
import { Button } from '../ui/button';
import { Textarea } from '../ui/textarea';
import { Label } from '../ui/label';
import { Badge } from '../ui/badge';
import { Progress } from '../ui/progress';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';

import {
  useSmartEstimationStore,
  startSmartEstimation,
  setupSmartEstimationListeners,
} from '../../stores/smart-estimation-store';
import type { SmartEstimationResult } from '../../stores/smart-estimation-store';
import { useProjectStore } from '../../stores/project-store';

/**
 * SmartEstimationDialog — AI-powered task complexity estimation dialog.
 *
 * Shows a dialog where users can enter a task description and receive
 * an intelligent complexity score based on historical build data.
 *
 * Usage:
 *   const { openDialog, closeDialog, isOpen } = useSmartEstimationStore();
 *   <SmartEstimationDialog />
 */
export function SmartEstimationDialog() {
  const { t } = useTranslation(['smartEstimation', 'common']);
  const [copied, setCopied] = useState(false);
  const streamOutputRef = useRef<HTMLPreElement>(null);

  const {
    isOpen,
    closeDialog,
    phase,
    status,
    streamingOutput,
    result,
    error,
    initialTaskDescription,
    reset,
  } = useSmartEstimationStore();

  const [editableTaskDescription, setEditableTaskDescription] = useState('');
  const selectedProjectId = useProjectStore((s) => s.selectedProjectId);

  // Setup IPC listeners once
  useEffect(() => {
    const cleanup = setupSmartEstimationListeners();
    return cleanup;
  }, []);

  // Sync editable task description when dialog opens
  useEffect(() => {
    if (isOpen) {
      setEditableTaskDescription(initialTaskDescription);
      setCopied(false);
    }
  }, [isOpen, initialTaskDescription]);

  // Auto-scroll streaming output
  useEffect(() => {
    if (streamOutputRef.current) {
      streamOutputRef.current.scrollTop = streamOutputRef.current.scrollHeight;
    }
  }, []);

  const handleEstimate = useCallback(() => {
    if (!selectedProjectId) return;
    if (!editableTaskDescription.trim()) return;

    // Update the store's task description to the edited version before starting
    useSmartEstimationStore.setState({ initialTaskDescription: editableTaskDescription });
    startSmartEstimation(selectedProjectId);
  }, [selectedProjectId, editableTaskDescription]);

  const handleCopy = useCallback(async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard not available
    }
  }, []);

  const handleTryAgain = useCallback(() => {
    reset();
    useSmartEstimationStore.setState({
      isOpen: true,
      initialTaskDescription: editableTaskDescription,
    });
  }, [reset, editableTaskDescription]);

  const handleClose = useCallback(() => {
    closeDialog();
  }, [closeDialog]);

  const isAnalyzing = phase === 'analyzing';
  const isComplete = phase === 'complete';
  const isError = phase === 'error';
  const canEstimate = editableTaskDescription.trim().length > 0 && selectedProjectId && !isAnalyzing;

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && handleClose()}>
      <DialogContent className="sm:max-w-[800px] max-h-[90vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-primary" />
            {t('smartEstimation:title')}
          </DialogTitle>
          <DialogDescription>
            {t('smartEstimation:description')}
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto space-y-4 py-2">
          {/* Task Description Input */}
          <div className="space-y-2">
            <Label htmlFor="estimation-task">
              {t('smartEstimation:task.label')}
            </Label>
            <Textarea
              id="estimation-task"
              value={editableTaskDescription}
              onChange={(e) => setEditableTaskDescription(e.target.value)}
              placeholder={t('smartEstimation:task.placeholder')}
              className="min-h-[100px]"
              disabled={isAnalyzing}
            />
          </div>

          {/* No Project Warning */}
          {!selectedProjectId && (
            <div className="bg-destructive/10 border border-destructive/30 rounded-lg p-3">
              <p className="text-sm text-destructive">
                {t('smartEstimation:errors.noProject')}
              </p>
            </div>
          )}

          {/* Status / Streaming Output during analysis */}
          {isAnalyzing && (
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin text-primary" />
                <span>{status || t('smartEstimation:status.analyzing')}</span>
              </div>
              {streamingOutput && (
                <div className="space-y-1">
                  <Label className="text-xs text-muted-foreground">
                    {t('smartEstimation:result.analysisProgress')}
                  </Label>
                  <pre
                    ref={streamOutputRef}
                    className="bg-muted/50 rounded-lg p-3 text-xs font-mono max-h-[150px] overflow-y-auto whitespace-pre-wrap wrap-break-word"
                  >
                    {streamingOutput}
                  </pre>
                </div>
              )}
            </div>
          )}

          {/* Error state */}
          {isError && (
            <div className="bg-destructive/10 border border-destructive/30 rounded-lg p-4 space-y-2">
              <p className="text-sm font-medium text-destructive">
                {t('smartEstimation:status.error')}
              </p>
              <p className="text-sm text-destructive/80">
                {error || t('smartEstimation:errors.generic')}
              </p>
            </div>
          )}

          {/* Result */}
          {isComplete && result && (
            <ResultView
              result={result}
              copied={copied}
              onCopy={handleCopy}
              t={t}
            />
          )}
        </div>

        {/* Footer Buttons */}
        <DialogFooter className="gap-2 sm:gap-0">
          {/* Idle / Input state */}
          {phase === 'idle' && (
            <>
              <Button variant="outline" onClick={handleClose}>
                {t('smartEstimation:actions.close')}
              </Button>
              <Button
                onClick={handleEstimate}
                disabled={!canEstimate}
                className="gap-2"
              >
                <TrendingUp className="h-4 w-4" />
                {t('smartEstimation:actions.estimate')}
              </Button>
            </>
          )}

          {/* Analyzing state */}
          {isAnalyzing && (
            <Button variant="outline" onClick={handleClose}>
              {t('smartEstimation:actions.close')}
            </Button>
          )}

          {/* Error state */}
          {isError && (
            <>
              <Button variant="outline" onClick={handleClose}>
                {t('smartEstimation:actions.close')}
              </Button>
              <Button onClick={handleTryAgain} className="gap-2">
                <RotateCcw className="h-4 w-4" />
                {t('smartEstimation:actions.tryAgain')}
              </Button>
            </>
          )}

          {/* Complete state */}
          {isComplete && (
            <Button variant="outline" onClick={handleClose}>
              {t('smartEstimation:actions.close')}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/**
 * Renders the estimation result with all metrics and insights
 */
function ResultView({
  result,
  copied,
  onCopy,
  t,
}: {
  readonly result: SmartEstimationResult;
  readonly copied: boolean;
  readonly onCopy: (text: string) => void;
  readonly t: (key: string) => string;
}) {
  const getComplexityColor = (score: number) => {
    if (score <= 3) return 'bg-green-500';
    if (score <= 7) return 'bg-yellow-500';
    if (score <= 10) return 'bg-orange-500';
    return 'bg-red-500';
  };

  const getComplexityLabel = (score: number) => {
    if (score <= 3) return 'Simple';
    if (score <= 7) return 'Moderate';
    if (score <= 10) return 'Complex';
    return 'Very Complex';
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'text-green-600';
    if (confidence >= 0.6) return 'text-yellow-600';
    return 'text-red-600';
  };

  return (
    <div className="space-y-6">
      {/* Complexity Score Header */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center justify-between">
            <span className="flex items-center gap-2">
              <Target className="h-5 w-5" />
              {t('smartEstimation:result.complexityScore')}
            </span>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onCopy(JSON.stringify(result, null, 2))}
              className="h-7 gap-1.5 text-xs"
            >
              {copied ? (
                <>
                  <Check className="h-3 w-3" />
                  {t('smartEstimation:actions.copied')}
                </>
              ) : (
                <>
                  <Copy className="h-3 w-3" />
                  {t('smartEstimation:actions.copy')}
                </>
              )}
            </Button>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <div className={`w-4 h-4 rounded-full ${getComplexityColor(result.complexity_score)}`} />
              <span className="text-2xl font-bold">{result.complexity_score}</span>
              <span className="text-sm text-muted-foreground">/13</span>
            </div>
            <Badge variant="outline" className="text-sm">
              {getComplexityLabel(result.complexity_score)}
            </Badge>
            <div className="flex items-center gap-1">
              <Info className="h-4 w-4" />
              <span className={`text-sm font-medium ${getConfidenceColor(result.confidence_level)}`}>
                {Math.round(result.confidence_level * 100)}% confidence
              </span>
            </div>
          </div>
          <Progress value={(result.complexity_score / 13) * 100} className="h-2" />
        </CardContent>
      </Card>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Duration Estimate */}
        {result.estimated_duration_hours && (
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
                <Clock className="h-4 w-4" />
                {t('smartEstimation:result.estimatedDuration')}
              </div>
              <div className="text-xl font-semibold">
                {result.estimated_duration_hours.toFixed(1)}h
              </div>
            </CardContent>
          </Card>
        )}

        {/* QA Iterations */}
        {result.estimated_qa_iterations && (
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
                <Zap className="h-4 w-4" />
                {t('smartEstimation:result.qaIterations')}
              </div>
              <div className="text-xl font-semibold">
                {Math.ceil(result.estimated_qa_iterations)} {t('smartEstimation:result.iterations')}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Cost Estimate */}
        {result.token_cost_estimate && (
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
                <DollarSign className="h-4 w-4" />
                {t('smartEstimation:result.estimatedCost')}
              </div>
              <div className="text-xl font-semibold">
                ${result.token_cost_estimate.toFixed(2)}
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Reasoning */}
      {result.reasoning.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">{t('smartEstimation:result.reasoning')}</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {result.reasoning.map((reason) => (
                <li key={reason} className="flex items-start gap-2 text-sm">
                  <span className="text-primary mt-1.5 shrink-0">•</span>
                  <span>{reason}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Risk Factors */}
      {result.risk_factors.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <AlertTriangle className="h-5 w-5 text-orange-500" />
              {t('smartEstimation:result.riskFactors')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {result.risk_factors.map((risk) => (
                <li key={risk} className="flex items-start gap-2 text-sm">
                  <span className="text-orange-500 mt-1.5 shrink-0">⚠</span>
                  <span>{risk}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Recommendations */}
      {result.recommendations.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Shield className="h-5 w-5 text-blue-500" />
              {t('smartEstimation:result.recommendations')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {result.recommendations.map((rec) => (
                <li key={rec} className="flex items-start gap-2 text-sm">
                  <span className="text-blue-500 mt-1.5 shrink-0">💡</span>
                  <span>{rec}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Similar Tasks */}
      {result.similar_tasks.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">{t('smartEstimation:result.similarTasks')}</CardTitle>
            <CardDescription>
              {t('smartEstimation:result.similarTasksDescription')}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {result.similar_tasks.slice(0, 3).map((task) => (
                <div key={task.spec_name} className="border rounded-lg p-3">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-medium text-sm">{task.spec_name}</span>
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="text-xs">
                        Score: {task.complexity_score}
                      </Badge>
                      <Badge variant={task.status === 'COMPLETE' ? 'default' : 'destructive'} className="text-xs">
                        {task.status}
                      </Badge>
                    </div>
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {Math.round(task.similarity_score * 100)}% similar
                    {task.duration_hours && ` • ${task.duration_hours.toFixed(1)}h`}
                    {task.cost_usd && ` • $${task.cost_usd.toFixed(2)}`}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

export default SmartEstimationDialog;



