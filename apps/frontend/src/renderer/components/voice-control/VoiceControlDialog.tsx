import { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { 
  Check, 
  Copy, 
  Loader2, 
  Mic, 
  MicOff, 
  RotateCcw,
  Volume2,
  Clock,
  AlertCircle
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
import { Label } from '../ui/label';
import { Progress } from '../ui/progress';
import { Badge } from '../ui/badge';

import {
  useVoiceControlStore,
  startRecording,
  stopRecording,
  setupVoiceControlListeners,
} from '../../stores/voice-control-store';
import type { VoiceControlResult } from '../../stores/voice-control-store';
import { useProjectStore } from '../../stores/project-store';

/**
 * VoiceControlDialog — Voice-powered command interface.
 *
 * Shows a dialog where users can record voice commands,
 * see real-time audio levels, and receive AI-processed commands.
 *
 * Usage:
 *   const { openDialog, closeDialog, isOpen } = useVoiceControlStore();
 *   <VoiceControlDialog onExecuteCommand={(cmd) => { ... }} />
 */
interface VoiceControlDialogProps {
  /** Called when a voice command is successfully processed */
  readonly onExecuteCommand?: (result: VoiceControlResult) => void;
}

export function VoiceControlDialog({ onExecuteCommand }: VoiceControlDialogProps) {
  const { t } = useTranslation(['voiceControl', 'common']);
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
    isListening,
    audioLevel,
    duration,
    reset,
  } = useVoiceControlStore();

  const selectedProjectId = useProjectStore((s) => s.selectedProjectId);

  // Setup IPC listeners once
  useEffect(() => {
    const cleanup = setupVoiceControlListeners();
    return cleanup;
  }, []);

  // Auto-scroll streaming output
  useEffect(() => {
    if (streamOutputRef.current) {
      streamOutputRef.current.scrollTop = streamOutputRef.current.scrollHeight;
    }
  }, []);

  // Auto-execute and close when result arrives with a known action
  useEffect(() => {
    if (phase === 'complete' && result && onExecuteCommand && result.action !== 'unknown' && result.action !== 'error') {
      onExecuteCommand(result);
      closeDialog();
    }
  }, [phase, result, onExecuteCommand, closeDialog]);

  const handleStartRecording = useCallback(() => {
    startRecording();
  }, []);

  const handleStopRecording = useCallback(() => {
    stopRecording();
  }, []);

  const handleCopy = useCallback(async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard not available
    }
  }, []);

  const handleExecuteCommand = useCallback(() => {
    if (result && onExecuteCommand) {
      onExecuteCommand(result);
      closeDialog();
    }
  }, [result, onExecuteCommand, closeDialog]);

  const handleTryAgain = useCallback(() => {
    reset();
    useVoiceControlStore.setState({ isOpen: true });
  }, [reset]);

  const handleClose = useCallback(() => {
    if (isListening) {
      stopRecording();
    }
    closeDialog();
  }, [isListening, closeDialog]);

  const isRecording = phase === 'recording';
  const isProcessing = phase === 'processing';
  const isComplete = phase === 'complete';
  const isError = phase === 'error';
  const canRecord = !isRecording && !isProcessing && selectedProjectId;

  // Format duration display
  const formatDuration = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && handleClose()}>
      <DialogContent className="sm:max-w-[640px] max-h-[85vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Mic className="h-5 w-5 text-primary" />
            {t('voiceControl:title')}
          </DialogTitle>
          <DialogDescription>
            {t('voiceControl:description')}
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto space-y-4 py-2">
          {/* No Project Warning */}
          {!selectedProjectId && (
            <div className="bg-destructive/10 border border-destructive/30 rounded-lg p-3">
              <div className="flex items-center gap-2">
                <AlertCircle className="h-4 w-4 text-destructive" />
                <p className="text-sm text-destructive">
                  {t('voiceControl:errors.noProject')}
                </p>
              </div>
            </div>
          )}

          {/* Recording Interface */}
          <div className="space-y-4">
            {/* Audio Level Visualizer */}
            {(isRecording || isProcessing) && (
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label className="text-sm font-medium">
                    {isRecording ? t('voiceControl:recording.level') : t('voiceControl:processing.level')}
                  </Label>
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Clock className="h-3 w-3" />
                    {formatDuration(duration)}
                  </div>
                </div>
                <div className="relative">
                  <Progress 
                    value={isRecording ? audioLevel * 100 : 0} 
                    className="h-2"
                  />
                  {isRecording && (
                    <div className="absolute inset-0 flex items-center justify-center">
                      <Volume2 className="h-3 w-3 text-primary animate-pulse" />
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Status Display */}
            {(isRecording || isProcessing) && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                {isRecording ? (
                  <Mic className="h-4 w-4 text-red-500 animate-pulse" />
                ) : (
                  <Loader2 className="h-4 w-4 animate-spin text-primary" />
                )}
                <span>{status || t('voiceControl:status.listening')}</span>
              </div>
            )}

            {/* Recording Controls */}
            {phase === 'idle' && (
              <div className="flex flex-col items-center space-y-4 py-8">
                <div className="relative">
                  <Button
                    size="lg"
                    onClick={handleStartRecording}
                    disabled={!canRecord}
                    className="h-16 w-16 rounded-full"
                  >
                    <Mic className="h-6 w-6" />
                  </Button>
                  {canRecord && (
                    <div className="absolute -inset-2 rounded-full border-2 border-primary/20 animate-ping pointer-events-none" />
                  )}
                </div>
                <p className="text-center text-sm text-muted-foreground">
                  {t('voiceControl:instructions.clickToRecord')}
                </p>
              </div>
            )}

            {/* Stop Recording Button */}
            {isRecording && (
              <div className="flex flex-col items-center space-y-4 py-8">
                <Button
                  size="lg"
                  onClick={handleStopRecording}
                  className="h-16 w-16 rounded-full bg-red-500 hover:bg-red-600"
                >
                  <MicOff className="h-6 w-6" />
                </Button>
                <p className="text-center text-sm text-muted-foreground">
                  {t('voiceControl:instructions.clickToStop')}
                </p>
              </div>
            )}
          </div>

          {/* Error state */}
          {isError && (
            <div className="bg-destructive/10 border border-destructive/30 rounded-lg p-4 space-y-2">
              <div className="flex items-center gap-2">
                <AlertCircle className="h-4 w-4 text-destructive" />
                <p className="text-sm font-medium text-destructive">
                  {t('voiceControl:status.error')}
                </p>
              </div>
              <p className="text-sm text-destructive/80">
                {error || t('voiceControl:errors.generic')}
              </p>
            </div>
          )}

          {/* Streaming Output */}
          {streamingOutput && (
            <div className="space-y-2">
              <Label className="text-xs text-muted-foreground">
                {t('voiceControl:result.streamingOutput')}
              </Label>
              <pre
                ref={streamOutputRef}
                className="bg-muted/50 rounded-lg p-3 text-xs font-mono max-h-[200px] overflow-y-auto whitespace-pre-wrap wrap-break-word"
              >
                {streamingOutput}
              </pre>
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
            <Button variant="outline" onClick={handleClose}>
              {t('voiceControl:actions.close')}
            </Button>
          )}

          {/* Recording / Processing state */}
          {(isRecording || isProcessing) && (
            <Button variant="outline" onClick={handleClose}>
              {t('voiceControl:actions.cancel')}
            </Button>
          )}

          {/* Error state */}
          {isError && (
            <>
              <Button variant="outline" onClick={handleClose}>
                {t('voiceControl:actions.close')}
              </Button>
              <Button onClick={handleTryAgain} className="gap-2">
                <RotateCcw className="h-4 w-4" />
                {t('voiceControl:actions.tryAgain')}
              </Button>
            </>
          )}

          {/* Complete state */}
          {isComplete && result && (
            <>
              <Button variant="outline" onClick={handleClose}>
                {t('voiceControl:actions.close')}
              </Button>
              {onExecuteCommand && (
                <Button onClick={handleExecuteCommand} className="gap-2">
                  <Check className="h-4 w-4" />
                  {t('voiceControl:actions.execute')}
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
 * Renders the voice command result: transcript, command, action, and parameters
 */
function ResultView({
  result,
  copied,
  onCopy,
  t,
}: {
  readonly result: VoiceControlResult;
  readonly copied: boolean;
  readonly onCopy: (text: string) => void;
  readonly t: (key: string) => string;
}) {
  return (
    <div className="space-y-4">
      {/* Transcript */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label className="text-sm font-medium">
            {t('voiceControl:result.transcript')}
          </Label>
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="text-xs">
              {Math.round(result.confidence * 100)}% confidence
            </Badge>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onCopy(result.transcript)}
              className="h-7 gap-1.5 text-xs"
            >
              {copied ? (
                <>
                  <Check className="h-3 w-3" />
                  {t('voiceControl:actions.copied')}
                </>
              ) : (
                <>
                  <Copy className="h-3 w-3" />
                  {t('voiceControl:actions.copy')}
                </>
              )}
            </Button>
          </div>
        </div>
        <div className="bg-primary/5 border border-primary/20 rounded-lg p-3">
          <p className="text-sm">{result.transcript}</p>
        </div>
      </div>

      {/* Command */}
      <div className="space-y-2">
        <Label className="text-sm font-medium">
          {t('voiceControl:result.command')}
        </Label>
        <div className="bg-muted/50 rounded-lg p-3">
          <p className="text-sm font-mono">{result.command}</p>
        </div>
      </div>

      {/* Action */}
      <div className="space-y-2">
        <Label className="text-sm font-medium">
          {t('voiceControl:result.action')}
        </Label>
        <Badge variant="secondary" className="text-sm">
          {result.action}
        </Badge>
      </div>

      {/* Parameters */}
      {Object.keys(result.parameters).length > 0 && (
        <div className="space-y-2">
          <Label className="text-sm font-medium">
            {t('voiceControl:result.parameters')}
          </Label>
          <div className="bg-muted/30 rounded-lg p-3">
            <pre className="text-xs text-muted-foreground">
              {JSON.stringify(result.parameters, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}

export default VoiceControlDialog;
