import { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Check, Copy, Loader2, Sparkles, WandSparkles, RotateCcw } from 'lucide-react';

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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select';

import {
  usePromptOptimizerStore,
  startOptimization,
  setupPromptOptimizerListeners,
} from '../../stores/prompt-optimizer-store';
import type { PromptOptimizerResult } from '../../stores/prompt-optimizer-store';
import { useProjectStore } from '../../stores/project-store';

const AGENT_TYPES = ['general', 'analysis', 'coding', 'verification'] as const;

/**
 * PromptOptimizerDialog — AI-powered prompt enhancement dialog.
 *
 * Shows a dialog where users can enter a prompt, pick an agent type,
 * and receive an AI-optimized version enriched with project context.
 *
 * Usage:
 *   const { openDialog, closeDialog, isOpen } = usePromptOptimizerStore();
 *   <PromptOptimizerDialog onUsePrompt={(optimized) => { ... }} />
 */
interface PromptOptimizerDialogProps {
  /** Called when the user clicks "Use This Prompt" with the optimized text */
  readonly onUsePrompt?: (optimizedPrompt: string) => void;
}

export function PromptOptimizerDialog({ onUsePrompt }: PromptOptimizerDialogProps) {
  const { t } = useTranslation(['promptOptimizer', 'common']);
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
    initialPrompt,
    agentType,
    setAgentType,
    reset,
  } = usePromptOptimizerStore();

  // Use store's openDialog sets the initialPrompt; we mirror it locally for editing
  const [editablePrompt, setEditablePrompt] = useState('');
  const selectedProjectId = useProjectStore((s) => s.selectedProjectId);

  // Setup IPC listeners once
  useEffect(() => {
    const cleanup = setupPromptOptimizerListeners();
    return cleanup;
  }, []);

  // Sync editable prompt when dialog opens
  useEffect(() => {
    if (isOpen) {
      setEditablePrompt(initialPrompt);
      setCopied(false);
    }
  }, [isOpen, initialPrompt]);

  // Auto-scroll streaming output
  useEffect(() => {
    if (streamOutputRef.current) {
      streamOutputRef.current.scrollTop = streamOutputRef.current.scrollHeight;
    }
  }, [streamingOutput]);

  const handleOptimize = useCallback(() => {
    if (!selectedProjectId) return;
    if (!editablePrompt.trim()) return;

    // Update the store's prompt to the edited version before starting
    usePromptOptimizerStore.setState({ initialPrompt: editablePrompt });
    startOptimization(selectedProjectId);
  }, [selectedProjectId, editablePrompt]);

  const handleCopy = useCallback(async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard not available
    }
  }, []);

  const handleUsePrompt = useCallback(() => {
    if (result?.optimized && onUsePrompt) {
      onUsePrompt(result.optimized);
      closeDialog();
    }
  }, [result, onUsePrompt, closeDialog]);

  const handleTryAgain = useCallback(() => {
    reset();
    usePromptOptimizerStore.setState({
      isOpen: true,
      initialPrompt: editablePrompt,
    });
  }, [reset, editablePrompt]);

  const handleClose = useCallback(() => {
    closeDialog();
  }, [closeDialog]);

  const isOptimizing = phase === 'optimizing';
  const isComplete = phase === 'complete';
  const isError = phase === 'error';
  const canOptimize = editablePrompt.trim().length > 0 && selectedProjectId && !isOptimizing;

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && handleClose()}>
      <DialogContent className="sm:max-w-[640px] max-h-[85vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <WandSparkles className="h-5 w-5 text-primary" />
            {t('promptOptimizer:title')}
          </DialogTitle>
          <DialogDescription>
            {t('promptOptimizer:description')}
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto space-y-4 py-2">
          {/* Prompt Input */}
          <div className="space-y-2">
            <Label htmlFor="optimizer-prompt">
              {t('promptOptimizer:prompt.label')}
            </Label>
            <Textarea
              id="optimizer-prompt"
              value={editablePrompt}
              onChange={(e) => setEditablePrompt(e.target.value)}
              placeholder={t('promptOptimizer:prompt.placeholder')}
              className="min-h-[120px] border-2 border-yellow-400 focus:border-yellow-500 focus-visible:border-yellow-500 focus:outline-none focus:ring-2 focus:ring-yellow-200"
              style={{
                border: '2px solid rgb(250, 204, 21)',
                borderRadius: '0.5rem',
                outline: 'none'
              }}
              disabled={isOptimizing}
            />
          </div>

          {/* Agent Type Selector */}
          <div className="space-y-2">
            <Label htmlFor="agent-type-select">
              {t('promptOptimizer:agentType.label')}
            </Label>
            <Select
              value={agentType}
              onValueChange={(value) =>
                setAgentType(value as typeof agentType)
              }
              disabled={isOptimizing}
            >
              <SelectTrigger id="agent-type-select">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {AGENT_TYPES.map((type) => (
                  <SelectItem key={type} value={type}>
                    <div className="flex flex-col">
                      <span>{t(`promptOptimizer:agentType.options.${type}`)}</span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              {t(`promptOptimizer:agentType.descriptions.${agentType}`)}
            </p>
          </div>

          {/* No Project Warning */}
          {!selectedProjectId && (
            <div className="bg-destructive/10 border border-destructive/30 rounded-lg p-3">
              <p className="text-sm text-destructive">
                {t('promptOptimizer:errors.noProject')}
              </p>
            </div>
          )}

          {/* Status / Streaming Output during optimization */}
          {isOptimizing && (
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin text-primary" />
                <span>{status || t('promptOptimizer:status.analyzing')}</span>
              </div>
              {streamingOutput && (
                <div className="space-y-1">
                  <Label className="text-xs text-muted-foreground">
                    {t('promptOptimizer:result.streamingOutput')}
                  </Label>
                  <pre
                    ref={streamOutputRef}
                    className="bg-muted/50 rounded-lg p-3 text-xs font-mono max-h-[200px] overflow-y-auto whitespace-pre-wrap wrap-break-word"
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
                {t('promptOptimizer:status.error')}
              </p>
              <p className="text-sm text-destructive/80">
                {error || t('promptOptimizer:errors.generic')}
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
                {t('promptOptimizer:actions.close')}
              </Button>
              <Button
                onClick={handleOptimize}
                disabled={!canOptimize}
                className="gap-2"
              >
                <Sparkles className="h-4 w-4" />
                {t('promptOptimizer:actions.optimize')}
              </Button>
            </>
          )}

          {/* Optimizing state */}
          {isOptimizing && (
            <Button variant="outline" onClick={handleClose}>
              {t('promptOptimizer:actions.close')}
            </Button>
          )}

          {/* Error state */}
          {isError && (
            <>
              <Button variant="outline" onClick={handleClose}>
                {t('promptOptimizer:actions.close')}
              </Button>
              <Button onClick={handleTryAgain} className="gap-2">
                <RotateCcw className="h-4 w-4" />
                {t('promptOptimizer:actions.tryAgain')}
              </Button>
            </>
          )}

          {/* Complete state */}
          {isComplete && result && (
            <>
              <Button variant="outline" onClick={handleClose}>
                {t('promptOptimizer:actions.close')}
              </Button>
              {onUsePrompt && (
                <Button onClick={handleUsePrompt} className="gap-2">
                  <Check className="h-4 w-4" />
                  {t('promptOptimizer:actions.usePrompt')}
                </Button>
              )}
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/**
 * Renders the optimization result: optimized prompt, changes list, and reasoning.
 */
function ResultView({
  result,
  copied,
  onCopy,
  t,
}: {
  readonly result: PromptOptimizerResult;
  readonly copied: boolean;
  readonly onCopy: (text: string) => void;
  readonly t: (key: string) => string;
}) {
  return (
    <div className="space-y-4">
      {/* Optimized Prompt */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label className="text-sm font-medium">
            {t('promptOptimizer:result.title')}
          </Label>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onCopy(result.optimized)}
            className="h-7 gap-1.5 text-xs"
          >
            {copied ? (
              <>
                <Check className="h-3 w-3" />
                {t('promptOptimizer:actions.copied')}
              </>
            ) : (
              <>
                <Copy className="h-3 w-3" />
                {t('promptOptimizer:actions.copy')}
              </>
            )}
          </Button>
        </div>
        <div className="bg-primary/5 border border-primary/20 rounded-lg p-3">
          <p className="text-sm whitespace-pre-wrap">{result.optimized}</p>
        </div>
      </div>

      {/* Changes */}
      <div className="space-y-2">
        <Label className="text-sm font-medium">
          {t('promptOptimizer:result.changes')}
        </Label>
        {result.changes.length > 0 ? (
          <ul className="space-y-1 pl-1">
            {result.changes.map((change) => (
              <li
                key={`change-${change}`}
                className="flex items-start gap-2 text-sm text-muted-foreground"
              >
                <span className="text-primary mt-1.5 shrink-0">•</span>
                <span>{change}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-muted-foreground italic">
            {t('promptOptimizer:result.noChanges')}
          </p>
        )}
      </div>

      {/* Reasoning */}
      {result.reasoning && (
        <div className="space-y-2">
          <Label className="text-sm font-medium">
            {t('promptOptimizer:result.reasoning')}
          </Label>
          <div className="bg-muted/50 rounded-lg p-3">
            <p className="text-sm text-muted-foreground">{result.reasoning}</p>
          </div>
        </div>
      )}
    </div>
  );
}

export default PromptOptimizerDialog;
