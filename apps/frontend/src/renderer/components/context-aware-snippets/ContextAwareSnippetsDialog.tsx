import { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Check, Copy, Loader2, Code, RotateCcw, Zap } from 'lucide-react';
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
import { Switch } from '../ui/switch';
import {
  useContextAwareSnippetsStore,
  startSnippetGeneration,
  setupContextAwareSnippetsListeners,
  cancelSnippetGeneration,
} from '../../stores/context-aware-snippets-store';
import type { ContextAwareSnippetResult } from '../../stores/context-aware-snippets-store';
import { useProjectStore } from '../../stores/project-store';

const SNIPPET_TYPES = [
  'component',
  'function', 
  'class',
  'hook',
  'utility',
  'api',
  'test'
] as const;

const COMMON_LANGUAGES = [
  'javascript',
  'typescript',
  'python',
  'java',
  'csharp',
  'cpp',
  'go',
  'rust',
  'php',
  'ruby'
];

/**
 * ContextAwareSnippetsDialog — AI-powered context-aware code snippet generator.
 *
 * Shows a dialog where users can describe a snippet, choose type and language,
 * and receive an AI-generated snippet adapted to their project's style and conventions.
 *
 * Usage:
 *   const { openDialog, closeDialog, isOpen } = useContextAwareSnippetsStore();
 *   <ContextAwareSnippetsDialog />
 */
interface ContextAwareSnippetsDialogProps {
  /** Called when the user clicks "Copy Snippet" with the generated code */
  readonly onCopySnippet?: (snippet: string) => void;
}

export function ContextAwareSnippetsDialog({ onCopySnippet }: ContextAwareSnippetsDialogProps) {
  const { t } = useTranslation(['contextAwareSnippets', 'common']);
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
    snippetType,
    description,
    language,
    autoDetectLanguage,
    setSnippetType,
    setDescription,
    setLanguage,
    setAutoDetectLanguage,
    reset,
  } = useContextAwareSnippetsStore();

  const selectedProjectId = useProjectStore((s) => s.selectedProjectId);

  // Setup IPC listeners once
  useEffect(() => {
    const cleanup = setupContextAwareSnippetsListeners();
    return cleanup;
  }, []);

  // Auto-scroll streaming output
  useEffect(() => {
    if (streamOutputRef.current) {
      streamOutputRef.current.scrollTop = streamOutputRef.current.scrollHeight;
    }
  }, []);

  const handleGenerate = useCallback(() => {
    if (!selectedProjectId) return;
    if (!description.trim()) return;

    startSnippetGeneration(selectedProjectId);
  }, [selectedProjectId, description]);

  const handleCopy = useCallback(async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
      if (onCopySnippet) {
        onCopySnippet(text);
      }
    } catch {
      // Clipboard not available
    }
  }, [onCopySnippet]);

  const handleCancel = useCallback(() => {
    cancelSnippetGeneration();
  }, []);

  const handleTryAgain = useCallback(() => {
    reset();
    useContextAwareSnippetsStore.setState({
      isOpen: true,
      snippetType,
      description,
      language,
      autoDetectLanguage,
    });
  }, [reset, snippetType, description, language, autoDetectLanguage]);

  const handleClose = useCallback(() => {
    if (phase === 'generating') {
      handleCancel();
    }
    closeDialog();
  }, [closeDialog, phase, handleCancel]);

  const isGenerating = phase === 'generating';
  const isComplete = phase === 'complete';
  const isError = phase === 'error';
  const canGenerate = description.trim().length > 0 && selectedProjectId && !isGenerating;

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && handleClose()}>
      <DialogContent className="sm:max-w-[800px] max-h-[90vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Zap className="h-5 w-5 text-primary" />
            {t('contextAwareSnippets:title')}
          </DialogTitle>
          <DialogDescription>
            {t('contextAwareSnippets:description')}
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto space-y-4 py-2">
          {/* Snippet Type Selector */}
          <div className="space-y-2">
            <Label htmlFor="snippet-type-select">
              {t('contextAwareSnippets:snippetType.label')}
            </Label>
            <Select
              value={snippetType}
              onValueChange={(value) =>
                setSnippetType(value as typeof snippetType)
              }
              disabled={isGenerating}
            >
              <SelectTrigger id="snippet-type-select" className="border-2 border-yellow-400 focus:border-yellow-500 focus-visible:border-yellow-500 focus:outline-none focus:ring-2 focus:ring-yellow-200" style={{ border: '2px solid rgb(250, 204, 21)', borderRadius: '0.5rem', outline: 'none' }}>
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="z-70">
                {SNIPPET_TYPES.map((type) => (
                  <SelectItem key={type} value={type}>
                    <div className="flex flex-col">
                      <span>{t(`contextAwareSnippets:snippetType.options.${type}`)}</span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              {t(`contextAwareSnippets:snippetType.descriptions.${snippetType}`)}
            </p>
          </div>

          {/* Description */}
          <div className="space-y-2">
            <Label htmlFor="snippet-description">
              {t('contextAwareSnippets:snippetDescription.label')}
            </Label>
            <Textarea
              id="snippet-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder={t('contextAwareSnippets:snippetDescription.placeholder')}
              className="min-h-[100px] border-2 border-yellow-400 focus:border-yellow-500 focus-visible:border-yellow-500 focus:outline-none focus:ring-2 focus:ring-yellow-200"
              style={{
                border: '2px solid rgb(250, 204, 21)',
                borderRadius: '0.5rem',
                outline: 'none'
              }}
              disabled={isGenerating}
            />
          </div>

          {/* Language Selection */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="language-select">
                {t('contextAwareSnippets:language.label')}
              </Label>
              <div className="flex items-center space-x-2">
                <Switch
                  id="auto-detect"
                  checked={autoDetectLanguage}
                  onCheckedChange={setAutoDetectLanguage}
                  disabled={isGenerating}
                />
                <Label htmlFor="auto-detect" className="text-sm">
                  {t('contextAwareSnippets:language.autoDetect')}
                </Label>
              </div>
            </div>
            <Select
              value={language}
              onValueChange={setLanguage}
              disabled={isGenerating || autoDetectLanguage}
            >
              <SelectTrigger id="language-select" className="border-2 border-yellow-400 focus:border-yellow-500 focus-visible:border-yellow-500 focus:outline-none focus:ring-2 focus:ring-yellow-200" style={{ border: '2px solid rgb(250, 204, 21)', borderRadius: '0.5rem', outline: 'none' }}>
                <SelectValue placeholder={t('contextAwareSnippets:language.placeholder')} />
              </SelectTrigger>
              <SelectContent className="z-70">
                {COMMON_LANGUAGES.map((lang) => (
                  <SelectItem key={lang} value={lang}>
                    {lang.charAt(0).toUpperCase() + lang.slice(1)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {autoDetectLanguage && (
              <p className="text-xs text-muted-foreground">
                {t('contextAwareSnippets:language.autoDetectDescription')}
              </p>
            )}
          </div>

          {/* No Project Warning */}
          {!selectedProjectId && (
            <div className="bg-destructive/10 border border-destructive/30 rounded-lg p-3">
              <p className="text-sm text-destructive">
                {t('contextAwareSnippets:errors.noProject')}
              </p>
            </div>
          )}

          {/* Status / Streaming Output during generation */}
          {isGenerating && (
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin text-primary" />
                <span>{status || t('contextAwareSnippets:status.analyzing')}</span>
              </div>
              <div className="flex items-center gap-2">
                <Button variant="outline" size="sm" onClick={handleCancel}>
                  {t('contextAwareSnippets:actions.cancel')}
                </Button>
              </div>
              {streamingOutput && (
                <div className="space-y-1">
                  <Label className="text-xs text-muted-foreground">
                    {t('contextAwareSnippets:result.streamingOutput')}
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
                {t('contextAwareSnippets:status.error')}
              </p>
              <p className="text-sm text-destructive/80">
                {error || t('contextAwareSnippets:errors.generic')}
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
                {t('contextAwareSnippets:actions.close')}
              </Button>
              <Button
                onClick={handleGenerate}
                disabled={!canGenerate}
                className="gap-2"
              >
                <Code className="h-4 w-4" />
                {t('contextAwareSnippets:actions.generate')}
              </Button>
            </>
          )}

          {/* Generating state */}
          {isGenerating && (
            <Button variant="outline" onClick={handleCancel}>
              {t('contextAwareSnippets:actions.cancel')}
            </Button>
          )}

          {/* Error state */}
          {isError && (
            <>
              <Button variant="outline" onClick={handleClose}>
                {t('contextAwareSnippets:actions.close')}
              </Button>
              <Button onClick={handleTryAgain} className="gap-2">
                <RotateCcw className="h-4 w-4" />
                {t('contextAwareSnippets:actions.tryAgain')}
              </Button>
            </>
          )}

          {/* Complete state */}
          {isComplete && result && (
            <>
              <Button variant="outline" onClick={handleClose}>
                {t('contextAwareSnippets:actions.close')}
              </Button>
              <Button onClick={() => handleCopy(result.snippet)} className="gap-2">
                {copied ? (
                  <>
                    <Check className="h-4 w-4" />
                    {t('contextAwareSnippets:actions.copied')}
                  </>
                ) : (
                  <>
                    <Copy className="h-4 w-4" />
                    {t('contextAwareSnippets:actions.copy')}
                  </>
                )}
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/**
 * Renders the generated snippet result with context information
 */
function ResultView({
  result,
  copied,
  onCopy,
  t,
}: {
  readonly result: ContextAwareSnippetResult;
  readonly copied: boolean;
  readonly onCopy: (text: string) => void;
  readonly t: (key: string) => string;
}) {
  return (
    <div className="space-y-4">
      {/* Generated Snippet */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label className="text-sm font-medium flex items-center gap-2">
            <Code className="h-4 w-4" />
            {t('contextAwareSnippets:result.snippet')} ({result.language})
          </Label>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onCopy(result.snippet)}
            className="h-7 gap-1.5 text-xs"
          >
            {copied ? (
              <>
                <Check className="h-3 w-3" />
                {t('contextAwareSnippets:actions.copied')}
              </>
            ) : (
              <>
                <Copy className="h-3 w-3" />
                {t('contextAwareSnippets:actions.copy')}
              </>
            )}
          </Button>
        </div>
        <div className="bg-primary/5 border border-primary/20 rounded-lg p-3">
          <pre className="text-sm whitespace-pre-wrap font-mono overflow-x-auto">
            {result.snippet}
          </pre>
        </div>
      </div>

      {/* Description */}
      <div className="space-y-2">
        <Label className="text-sm font-medium">
          {t('contextAwareSnippets:result.description')}
        </Label>
        <p className="text-sm text-muted-foreground">{result.description}</p>
      </div>

      {/* Context Used */}
      {result.context_used.length > 0 && (
        <div className="space-y-2">
          <Label className="text-sm font-medium">
            {t('contextAwareSnippets:result.contextUsed')}
          </Label>
          <div className="flex flex-wrap gap-1">
            {result.context_used.map((context) => (
              <span
                key={`context-${context}`}
                className="bg-secondary text-secondary-foreground px-2 py-1 rounded-md text-xs"
              >
                {context}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Adaptations */}
      {result.adaptations.length > 0 && (
        <div className="space-y-2">
          <Label className="text-sm font-medium">
            {t('contextAwareSnippets:result.adaptations')}
          </Label>
          <ul className="space-y-1 pl-1">
            {result.adaptations.map((adaptation) => (
              <li
                key={`adaptation-${adaptation}`}
                className="flex items-start gap-2 text-sm text-muted-foreground"
              >
                <span className="text-primary mt-1.5 shrink-0">•</span>
                <span>{adaptation}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Reasoning */}
      {result.reasoning && (
        <div className="space-y-2">
          <Label className="text-sm font-medium">
            {t('contextAwareSnippets:result.reasoning')}
          </Label>
          <div className="bg-muted/50 rounded-lg p-3">
            <p className="text-sm text-muted-foreground">{result.reasoning}</p>
          </div>
        </div>
      )}
    </div>
  );
}

export default ContextAwareSnippetsDialog;
