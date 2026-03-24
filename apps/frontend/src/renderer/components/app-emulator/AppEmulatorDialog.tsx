import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
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
  Globe,
  Search,
  X,
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

/** Special tab value for the webview preview panel. */
const PREVIEW_TAB = '__preview__';

function execCommandCopy(text: string, onSuccess: () => void) {
  const el = document.createElement('textarea');
  el.value = text;
  el.style.cssText = 'position:fixed;left:-9999px;top:-9999px;opacity:0';
  document.body.appendChild(el);
  el.focus();
  el.select();
  try {
    document.execCommand('copy');
    onSuccess();
  } finally {
    document.body.removeChild(el);
  }
}

/** Maps a matched level keyword to its Tailwind color class. */
function classifyLogLevel(keyword: string): string {
  const k = keyword.toLowerCase();
  if (/^(error|err|fatal|critical|crit|panic|exception|severe|fail(ed)?)$/.test(k)) return 'text-red-400';
  if (/^(warn|warning|wrn)$/.test(k)) return 'text-amber-400';
  if (/^(info|information|inf|notice)$/.test(k)) return 'text-sky-400';
  if (/^(debug|dbg|dbug|trace|trce|trc|verbose|verb|vrb)$/.test(k)) return 'text-slate-400';
  return '';
}

/**
 * Classify a log line and return its Tailwind color class.
 * Generic — works across any language, framework, or log format.
 *
 * Priority order:
 *  1. Bracket notation  — [ERROR], (WARN), {INFO}
 *  2. Keyword prefix    — "ERROR:", "warn |", "fail -" at line start
 *  3. Uppercase keyword — standalone ERROR/WARN/INFO/DEBUG anywhere in line
 *  4. Success symbols   — ✓, ✔, ✅ or common "ready" phrases
 */
function classifyLogLine(line: string): string {
  // 1. Bracket notation: [LEVEL], (LEVEL), {LEVEL}
  const bracketMatch = line.match(/[[({]([a-z]+)[\])}]/i);
  if (bracketMatch) {
    const cls = classifyLogLevel(bracketMatch[1]);
    if (cls) return cls;
  }

  // 2. Keyword prefix at start of line, optionally after a timestamp in brackets.
  //    Covers: "ERROR:", "warn:", "fail:", "DEBUG |", "TRACE -"
  const prefixMatch = line.match(/^\s*(?:\[[^\]]*\]\s*)?([a-z]+)\s*[:|]/i);
  if (prefixMatch) {
    const cls = classifyLogLevel(prefixMatch[1]);
    if (cls) return cls;
  }

  // 3. Uppercase standalone keyword anywhere in the line.
  //    Uppercase-only avoids false positives on ordinary words ("error" in a sentence).
  const upperMatch = line.match(/\b(ERROR|FATAL|CRITICAL|EXCEPTION|PANIC|FAILED|WARNING|WARN|INFO|INFORMATION|DEBUG|TRACE|VERBOSE)\b/);
  if (upperMatch) {
    return classifyLogLevel(upperMatch[1]);
  }

  // 4. Success / ready indicators (symbols or common phrases)
  if (/[✓✔✅]/.test(line) || /\b(compiled successfully|ready in|ready on|application started|now listening|server (started|running))\b/i.test(line)) {
    return 'text-green-400';
  }

  return '';
}

/** Render log text with per-line color highlighting based on log level. */
function renderColorizedContent(text: string) {
  return text.split('\n').map((line, i) => (
    <span key={i} className={`block ${classifyLogLine(line)}`}>
      {line}
    </span>
  ));
}

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
  /** Active tab: PREVIEW_TAB | service label | null (no explicit selection yet) */
  const [activeTab, setActiveTab] = useState<string | null>(null);
  /** Per-tab log search query */
  const [searchQuery, setSearchQuery] = useState('');

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

  const isWeb = config?.isWeb ?? false;
  const services = config?.services;
  const isMultiService = !!(services && services.length > 1);

  // Reset tab when config changes (new project / retry)
  useEffect(() => {
    setActiveTab(null);
    setSearchQuery('');
  }, []);

  // Auto-switch to Preview tab when the server becomes ready (web apps)
  useEffect(() => {
    if (phase === 'running' && isWeb) {
      setActiveTab(PREVIEW_TAB);
    }
  }, [phase, isWeb]);

  /**
   * Resolved active tab:
   * - During loading or non-web: first service label (for filtering) or null
   * - When running web: PREVIEW_TAB (unless user picked something else)
   */
  const resolvedTab = useMemo(() => {
    if (activeTab !== null) return activeTab;
    if (phase === 'running' && isWeb) return PREVIEW_TAB;
    if (isMultiService && services) return services[0].label;
    return null;
  }, [activeTab, phase, isWeb, isMultiService, services]);

  // Reset search when active tab changes
  useEffect(() => {
    setSearchQuery('');
  }, []);

  const showPreview = resolvedTab === PREVIEW_TAB && phase === 'running' && isWeb && !!url;

  // Filter output lines to the active service tab (no filtering for PREVIEW_TAB or null)
  const filteredOutput = useMemo(() => {
    if (!resolvedTab || resolvedTab === PREVIEW_TAB || !isMultiService) return output;
    const prefix = `[${resolvedTab}] `;
    return output
      .split('\n')
      .filter((line) => line.startsWith(prefix))
      .map((line) => line.slice(prefix.length))
      .join('\n');
  }, [output, resolvedTab, isMultiService]);

  // Apply search filter on top of the tab-filtered output
  const searchFilteredOutput = useMemo(() => {
    if (!searchQuery.trim()) return filteredOutput;
    const q = searchQuery.toLowerCase();
    return filteredOutput
      .split('\n')
      .filter((line) => line.toLowerCase().includes(q))
      .join('\n');
  }, [filteredOutput, searchQuery]);

  // Setup IPC listeners
  useEffect(() => {
    const cleanup = setupAppEmulatorListeners();
    return cleanup;
  }, []);

  // Auto-scroll output (only when the log panel is visible and not actively searching)
  useEffect(() => {
    if (!showPreview && !searchQuery && outputRef.current) {
      outputRef.current.scrollTop = outputRef.current.scrollHeight;
    }
  }, [showPreview, searchQuery]);

  // Auto-detect and start when dialog opens
  useEffect(() => {
    if (isOpen && phase === 'idle') {
      if (selectedProject?.path) {
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
    if (iframeRef.current) {
      (iframeRef.current as any).reload?.();
    }
  }, []);

  const handleOpenInBrowser = useCallback(() => {
    const currentUrl = (iframeRef.current as any)?.getURL?.() ?? url;
    if (currentUrl && (globalThis as any).electronAPI?.openExternal) {
      (globalThis as any).electronAPI.openExternal(currentUrl);
    }
  }, [url]);

  const handleClose = useCallback(() => {
    closeDialog();
  }, [closeDialog]);

  const handleCopyLogs = useCallback(() => {
    if (!searchFilteredOutput) return;

    const markCopied = () => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    };

    if (navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(searchFilteredOutput).then(markCopied).catch(() => {
        execCommandCopy(searchFilteredOutput, markCopied);
      });
    } else {
      execCommandCopy(searchFilteredOutput, markCopied);
    }
  }, [searchFilteredOutput]);

  if (!isOpen) return null;

  const isLoading = phase === 'detecting' || phase === 'starting';

  /** Shared badge class builder for clickable tabs */
  const tabClass = (isActive: boolean) =>
    `gap-1 cursor-pointer select-none transition-colors ${
      isActive
        ? 'border-yellow-500 bg-yellow-500/10 text-yellow-400 hover:bg-yellow-500/20'
        : 'hover:border-muted-foreground/60'
    }`;

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

        {/* Project Info Bar — tabs row */}
        {config && (
          <div className="flex items-center gap-3 text-sm flex-wrap">
            {isMultiService ? (
              <>
                {services?.map((svc) => (
                  <Badge
                    key={svc.label}
                    variant="outline"
                    className={tabClass(resolvedTab === svc.label)}
                    onClick={() => setActiveTab(svc.label)}
                  >
                    <Server className="h-3 w-3" />
                    {svc.label}
                    {svc.port > 0 && <span className="opacity-70">:{svc.port}</span>}
                    {svc.isPrimary && <span className="text-xs opacity-70 ml-0.5">API</span>}
                  </Badge>
                ))}
                {/* Preview tab — only shown once the server is running */}
                {phase === 'running' && isWeb && (
                  <Badge
                    variant="outline"
                    className={tabClass(resolvedTab === PREVIEW_TAB)}
                    onClick={() => setActiveTab(PREVIEW_TAB)}
                  >
                    <Globe className="h-3 w-3" />
                    {t('appEmulator:tabs.preview')}
                  </Badge>
                )}
              </>
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
          </div>
        )}

        {/* Main Content Area */}
        <div className="flex-1 min-h-0 overflow-hidden rounded-lg border border-border flex flex-col">

          {/* Loading State — step indicator + live terminal */}
          {isLoading && (
            <div className="flex-1 min-h-0 flex flex-col overflow-hidden">
              {/* Step bar */}
              <div className="flex items-center gap-3 px-4 py-3 border-b border-border shrink-0">
                {/* Step 1 — Detection */}
                <div className="flex items-center gap-1.5">
                  {phase !== 'detecting' ? (
                    <span className="flex h-4 w-4 items-center justify-center rounded-full bg-green-500/15">
                      <Check className="h-2.5 w-2.5 text-green-500" />
                    </span>
                  ) : (
                    <Loader2 className="h-4 w-4 animate-spin text-primary shrink-0" />
                  )}
                  <span className={`text-xs font-medium ${phase === 'detecting' ? 'text-foreground' : 'text-muted-foreground'}`}>
                    {t('appEmulator:steps.detect')}
                  </span>
                  {phase !== 'detecting' && config && (
                    <span className="text-xs text-green-600 dark:text-green-400">· {config.framework}</span>
                  )}
                </div>

                <span className="text-muted-foreground/50 text-xs">›</span>

                {/* Step 2 — Starting */}
                <div className="flex items-center gap-1.5">
                  {phase === 'starting' ? (
                    <Loader2 className="h-4 w-4 animate-spin text-primary shrink-0" />
                  ) : (
                    <span className="flex h-4 w-4 items-center justify-center rounded-full border border-muted-foreground/30" />
                  )}
                  <span className={`text-xs font-medium ${phase === 'starting' ? 'text-foreground' : 'text-muted-foreground'}`}>
                    {t('appEmulator:steps.start')}
                  </span>
                </div>

                {/* Current status — single source of truth, only in the step bar */}
                {status && (
                  <span className="ml-auto text-xs text-muted-foreground truncate max-w-xs">{status}</span>
                )}
              </div>

              {/* Search bar */}
              <div className="flex items-center gap-2 px-3 py-1.5 border-b border-border shrink-0">
                <div className="flex-1 relative">
                  <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground pointer-events-none" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder={t('appEmulator:output.searchPlaceholder')}
                    className="w-full h-7 pl-7 pr-7 text-xs rounded-md border border-border bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                  />
                  {searchQuery && (
                    <button
                      type="button"
                      onClick={() => setSearchQuery('')}
                      className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                    >
                      <X className="h-3.5 w-3.5" />
                    </button>
                  )}
                </div>
                {searchQuery && (
                  <span className="text-xs text-muted-foreground shrink-0">
                    {searchFilteredOutput ? searchFilteredOutput.split('\n').filter(Boolean).length : 0}{' '}
                    {t('appEmulator:output.searchResults')}
                  </span>
                )}
              </div>

              {/* Live terminal output */}
              <pre
                ref={outputRef}
                className="flex-1 min-h-0 m-3 overflow-y-auto text-xs font-mono text-muted-foreground p-3 whitespace-pre-wrap bg-muted/50 rounded-lg"
              >
                {searchFilteredOutput
                  ? renderColorizedContent(searchFilteredOutput)
                  : <span className="italic opacity-50">{t('appEmulator:steps.waitingOutput')}</span>}
              </pre>
            </div>
          )}

          {/* Running State — webview (Preview tab) */}
          {/* Keep webview mounted to avoid reloads; toggle visibility via CSS */}
          {phase === 'running' && isWeb && url && (
            <webview
              ref={iframeRef as any}
              src={url}
              className="flex-1 min-h-0 w-full border-0 bg-white"
              style={{ display: showPreview ? 'flex' : 'none' }}
            />
          )}

          {/* Running State — log tabs (service tabs or non-web terminal) */}
          {phase === 'running' && !showPreview && (
            <div className="flex-1 min-h-0 flex flex-col overflow-hidden">
              <div className="flex items-center gap-2 px-4 py-2 border-b border-border shrink-0">
                <TerminalIcon className="h-4 w-4 text-muted-foreground shrink-0" />
                <span className="text-sm font-medium shrink-0">
                  {isMultiService && resolvedTab !== PREVIEW_TAB
                    ? resolvedTab
                    : t('appEmulator:output.title')}
                </span>
                <div className="flex-1 relative">
                  <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground pointer-events-none" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder={t('appEmulator:output.searchPlaceholder')}
                    className="w-full h-7 pl-7 pr-7 text-xs rounded-md border border-border bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                  />
                  {searchQuery && (
                    <button
                      type="button"
                      onClick={() => setSearchQuery('')}
                      className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                    >
                      <X className="h-3.5 w-3.5" />
                    </button>
                  )}
                </div>
                {searchQuery && (
                  <span className="text-xs text-muted-foreground shrink-0">
                    {searchFilteredOutput
                      ? searchFilteredOutput.split('\n').filter(Boolean).length
                      : 0}{' '}
                    {t('appEmulator:output.searchResults')}
                  </span>
                )}
              </div>
              <ScrollArea className="flex-1 min-h-0">
                <div className="p-4">
                  <pre
                    ref={outputRef}
                    className="text-xs font-mono text-foreground whitespace-pre-wrap bg-muted/50 rounded-lg p-3"
                  >
                    {searchFilteredOutput
                      ? renderColorizedContent(searchFilteredOutput)
                      : (searchQuery
                          ? t('appEmulator:output.noResults', { query: searchQuery })
                          : t('appEmulator:output.noOutput'))}
                  </pre>
                </div>
              </ScrollArea>
            </div>
          )}

          {/* Error State */}
          {phase === 'error' && (
            <div className="flex-1 min-h-0 flex flex-col overflow-hidden">
              <div className="flex flex-col items-center gap-2 py-6 px-4 shrink-0">
                <p className="text-sm font-medium text-destructive text-center max-w-md">{error}</p>
                {selectedProject?.path && (
                  <p className="text-xs text-muted-foreground text-center">
                    {t('appEmulator:errors.scannedPath')}: {selectedProject.path}
                  </p>
                )}
              </div>
              {searchFilteredOutput && (
                <pre
                  ref={outputRef}
                  className="flex-1 min-h-0 mx-4 mb-4 overflow-y-auto text-xs font-mono text-muted-foreground p-3 whitespace-pre-wrap bg-muted/50 rounded-lg"
                >
                  {renderColorizedContent(searchFilteredOutput)}
                </pre>
              )}
            </div>
          )}

          {/* Stopped State */}
          {phase === 'stopped' && (
            <div className="flex-1 flex flex-col items-center justify-center gap-4">
              <p className="text-sm text-muted-foreground">{t('appEmulator:stopped')}</p>
            </div>
          )}

          {/* Idle State (no project) */}
          {phase === 'idle' && !selectedProject && (
            <div className="flex-1 flex flex-col items-center justify-center gap-4">
              <p className="text-sm text-muted-foreground">{t('appEmulator:errors.noProject')}</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <DialogFooter className="flex-row justify-between sm:justify-between">
          <div className="flex gap-2">
            {showPreview && (
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
            {!showPreview && searchFilteredOutput && (
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
