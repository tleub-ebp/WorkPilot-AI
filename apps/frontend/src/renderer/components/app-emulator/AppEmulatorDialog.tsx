import { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Loader2,
  Monitor,
  RefreshCw,
  ExternalLink,
  Square,
  RotateCcw,
  Server,
  Terminal as TerminalIcon,
  Copy,
  Check,
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
import { Badge } from '../ui/badge';
import { ScrollArea } from '../ui/scroll-area';
import {
  useAppEmulatorStore,
  setupAppEmulatorListeners,
  startAppEmulator,
  stopAppEmulator,
} from '@/stores/app-emulator-store';
import { useProjectStore } from '@/stores/project-store';

/**
 * AppEmulatorDialog — Preview the application directly from WorkPilot.
 *
 * Detects project type, launches dev server, and shows preview in an iframe
 * (web apps) or terminal output (CLI/desktop apps).
 */
export function AppEmulatorDialog() {
  const { t } = useTranslation(['appEmulator', 'common']);
  const outputRef = useRef<HTMLPreElement>(null);
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const [copied, setCopied] = useState(false);

  const {
    isOpen,
    closeDialog,
    phase,
    config,
    url,
    output,
    error,
    status,
  } = useAppEmulatorStore();

  const selectedProjectId = useProjectStore((s) => s.selectedProjectId);
  const projects = useProjectStore((s) => s.projects);
  const selectedProject = projects.find((p) => p.id === selectedProjectId);

  // Setup IPC listeners
  useEffect(() => {
    const cleanup = setupAppEmulatorListeners();
    return cleanup;
  }, []);

  // Auto-scroll output
  useEffect(() => {
    if (outputRef.current) {
      outputRef.current.scrollTop = outputRef.current.scrollHeight;
    }
  }, [output]);

  // Auto-detect and start when dialog opens
  useEffect(() => {
    if (isOpen && phase === 'idle') {
      if (selectedProject?.path) {
        console.log('[AppEmulator] Starting with project path:', selectedProject.path);
        startAppEmulator(selectedProject.path);
      } else {
        console.warn('[AppEmulator] No project path available. selectedProjectId:', selectedProjectId, 'projects:', projects.length);
        useAppEmulatorStore.getState().setError(
          `No project path found. Please select a project with a valid path first. (projectId: ${selectedProjectId || 'none'}, projects: ${projects.length})`
        );
      }
    }
  }, [isOpen, phase, selectedProject?.path, selectedProjectId, projects.length]);

  const handleStop = useCallback(() => {
    stopAppEmulator();
  }, []);

  const handleRetry = useCallback(async () => {
    if (selectedProject?.path) {
      await stopAppEmulator();
      useAppEmulatorStore.getState().reset();
      useAppEmulatorStore.getState().openDialog();
      startAppEmulator(selectedProject.path);
    }
  }, [selectedProject?.path]);

  const handleRefresh = useCallback(() => {
    if (iframeRef.current && url) {
      iframeRef.current.src = url;
    }
  }, [url]);

  const handleOpenInBrowser = useCallback(() => {
    if (url && (globalThis as any).electronAPI?.openExternal) {
      (globalThis as any).electronAPI.openExternal(url);
    }
  }, [url]);

  const handleClose = useCallback(() => {
    closeDialog();
  }, [closeDialog]);

  const handleCopyLogs = useCallback(() => {
    if (output) {
      navigator.clipboard.writeText(output).then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      });
    }
  }, [output]);

  if (!isOpen) return null;

  const isLoading = phase === 'detecting' || phase === 'starting';
  const isWeb = config?.isWeb ?? false;

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && handleClose()}>
      <DialogContent className="max-w-5xl h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Monitor className="h-5 w-5" />
            {t('appEmulator:title')}
          </DialogTitle>
          <DialogDescription>{t('appEmulator:description')}</DialogDescription>
        </DialogHeader>

        {/* Project Info Bar */}
        {config && (
          <div className="flex items-center gap-3 text-sm flex-wrap">
            {config.services && config.services.length > 1 ? (
              config.services.map((svc) => (
                <Badge
                  key={svc.label}
                  variant={svc.isPrimary ? 'default' : 'outline'}
                  className="gap-1"
                >
                  <Server className="h-3 w-3" />
                  {svc.label}
                  {svc.port > 0 && <span className="opacity-70">:{svc.port}</span>}
                  {svc.isPrimary && <span className="text-xs opacity-70 ml-0.5">API</span>}
                </Badge>
              ))
            ) : (
              <>
                <Badge variant="outline" className="gap-1">
                  <Server className="h-3 w-3" />
                  {config.framework}
                </Badge>
                {config.port > 0 && (
                  <Badge variant="secondary">{t('appEmulator:projectInfo.port')}: {config.port}</Badge>
                )}
              </>
            )}
            {url && (
              <Badge variant="secondary" className="gap-1">
                {url}
              </Badge>
            )}
            <span className="text-muted-foreground text-xs ml-auto">{status}</span>
          </div>
        )}

        {/* Main Content Area */}
        <div className="flex-1 min-h-0 overflow-hidden rounded-lg border border-border">
          {/* Loading State */}
          {isLoading && (
            <div className="flex flex-col h-full">
              <div className="flex flex-col items-center gap-4 py-6 px-4 shrink-0">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
                <div className="text-center">
                  <p className="text-sm font-medium">
                    {phase === 'detecting' ? t('appEmulator:detecting') : t('appEmulator:starting')}
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">{status}</p>
                </div>
              </div>
              {output && (
                <div className="flex-1 min-h-0 mx-4 mb-4 overflow-hidden rounded-lg bg-muted/50">
                  <pre
                    ref={outputRef}
                    className="text-xs font-mono text-muted-foreground overflow-auto h-full p-3 whitespace-pre-wrap"
                  >
                    {output}
                  </pre>
                </div>
              )}
            </div>
          )}

          {/* Running State - Web App (iframe) */}
          {phase === 'running' && isWeb && url && (
            <iframe
              ref={iframeRef}
              src={url}
              className="w-full h-full border-0 bg-white"
              title={t('appEmulator:title')}
              sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-modals"
            />
          )}

          {/* Running State - Non-Web App (terminal output) */}
          {phase === 'running' && !isWeb && (
            <ScrollArea className="h-full">
              <div className="p-4">
                <div className="flex items-center gap-2 mb-3">
                  <TerminalIcon className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm font-medium">{t('appEmulator:output.title')}</span>
                </div>
                <pre
                  ref={outputRef}
                  className="text-xs font-mono text-foreground whitespace-pre-wrap bg-muted/50 rounded-lg p-3"
                >
                  {output || t('appEmulator:output.noOutput')}
                </pre>
              </div>
            </ScrollArea>
          )}

          {/* Error State */}
          {phase === 'error' && (
            <div className="flex flex-col h-full">
              <div className="flex flex-col items-center gap-2 py-6 px-4 shrink-0">
                <p className="text-sm font-medium text-destructive text-center max-w-md">{error}</p>
                {selectedProject?.path && (
                  <p className="text-xs text-muted-foreground text-center">
                    {t('appEmulator:errors.scannedPath')}: {selectedProject.path}
                  </p>
                )}
              </div>
              {output && (
                <div className="flex-1 min-h-0 mx-4 mb-4 overflow-hidden rounded-lg bg-muted/50">
                  <div className="flex items-center gap-2 px-3 py-2 border-b border-border shrink-0">
                    <TerminalIcon className="h-3 w-3 text-muted-foreground" />
                    <span className="text-xs font-medium">{t('appEmulator:output.title')}</span>
                  </div>
                  <pre
                    ref={outputRef}
                    className="text-xs font-mono text-muted-foreground overflow-auto h-[calc(100%-2rem)] p-3 whitespace-pre-wrap"
                  >
                    {output}
                  </pre>
                </div>
              )}
              {!output && <div className="flex-1" />}
            </div>
          )}

          {/* Stopped State */}
          {phase === 'stopped' && (
            <div className="flex flex-col items-center justify-center h-full gap-4">
              <p className="text-sm text-muted-foreground">{t('appEmulator:stopped')}</p>
            </div>
          )}

          {/* Idle State (no project) */}
          {phase === 'idle' && !selectedProject && (
            <div className="flex flex-col items-center justify-center h-full gap-4">
              <p className="text-sm text-muted-foreground">{t('appEmulator:errors.noProject')}</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <DialogFooter className="flex-row justify-between sm:justify-between">
          <div className="flex gap-2">
            {phase === 'running' && isWeb && (
              <>
                <Button variant="outline" size="sm" onClick={handleRefresh}>
                  <RefreshCw className="h-4 w-4 mr-1.5" />
                  {t('appEmulator:actions.refresh')}
                </Button>
                <Button variant="outline" size="sm" onClick={handleOpenInBrowser}>
                  <ExternalLink className="h-4 w-4 mr-1.5" />
                  {t('appEmulator:actions.openInBrowser')}
                </Button>
              </>
            )}
            {output && (
              <Button variant="outline" size="sm" onClick={handleCopyLogs}>
                {copied ? (
                  <Check className="h-4 w-4 mr-1.5 text-green-500" />
                ) : (
                  <Copy className="h-4 w-4 mr-1.5" />
                )}
                {t('appEmulator:actions.copyLogs')}
              </Button>
            )}
          </div>
          <div className="flex gap-2">
            {(phase === 'error' || phase === 'stopped') && (
              <Button variant="outline" size="sm" onClick={handleRetry}>
                <RotateCcw className="h-4 w-4 mr-1.5" />
                {t('appEmulator:actions.retry')}
              </Button>
            )}
            {(phase === 'running' || phase === 'starting') && (
              <Button variant="destructive" size="sm" onClick={handleStop}>
                <Square className="h-4 w-4 mr-1.5" />
                {t('appEmulator:actions.stop')}
              </Button>
            )}
            <Button variant="outline" size="sm" onClick={handleClose}>
              {t('appEmulator:actions.close')}
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
