import { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Check, Copy, Loader2, Play, RotateCcw, X, Code, Zap, Monitor, FolderTree } from 'lucide-react';

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
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';

import { useCodePlaygroundStore, setupCodePlaygroundListeners, startPlayground } from '@/stores/code-playground-store';
import type { PlaygroundResult } from '@/stores/code-playground-store';
import { useProjectStore } from '@/stores/project-store';

const PLAYGROUND_TYPES = ['html', 'react', 'vanilla-js', 'python', 'node'] as const;
const SANDBOX_TYPES = ['iframe', 'docker', 'webworker'] as const;

/**
 * CodePlaygroundDialog — AI-powered code playground dialog.
 *
 * Shows a dialog where users can enter a code idea, pick a playground type,
 * and receive an AI-generated sandbox environment with live preview and integration options.
 *
 * Usage:
 *   const { openDialog, closeDialog, isOpen } = useCodePlaygroundStore();
 *   <CodePlaygroundDialog onIntegrate={(result) => { ... }} />
 */
interface CodePlaygroundDialogProps {
  /** Called when the user clicks "Integrate to Project" with the generated code */
  onIntegrate?: (result: PlaygroundResult) => void;
}

export function CodePlaygroundDialog({ onIntegrate }: CodePlaygroundDialogProps) {
  const { t } = useTranslation(['codePlayground', 'common']);
  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState('code');
  const previewRef = useRef<HTMLIFrameElement>(null);
  const streamOutputRef = useRef<HTMLPreElement>(null);

  const {
    isOpen,
    closeDialog,
    phase,
    status,
    streamingOutput,
    result,
    error,
    initialIdea,
    playgroundType,
    sandboxType,
    setPlaygroundType,
    setSandboxType,
    reset,
  } = useCodePlaygroundStore();

  // Use store's openDialog sets the initialIdea; we mirror it locally for editing
  const [editableIdea, setEditableIdea] = useState('');
  const selectedProjectId = useProjectStore((s) => s.selectedProjectId);

  // Setup IPC listeners once
  useEffect(() => {
    const cleanup = setupCodePlaygroundListeners();
    return cleanup;
  }, []);

  // Sync editable idea when dialog opens
  useEffect(() => {
    if (isOpen) {
      setEditableIdea(initialIdea);
      setCopied(false);
      setActiveTab('code');
    }
  }, [isOpen, initialIdea]);

  // Auto-scroll streaming output
  useEffect(() => {
    if (streamOutputRef.current) {
      streamOutputRef.current.scrollTop = streamOutputRef.current.scrollHeight;
    }
  }, [streamingOutput]);

  // Update preview when result changes
  useEffect(() => {
    if (result?.html && previewRef.current && activeTab === 'preview') {
      previewRef.current.srcdoc = result.html;
    }
  }, [result, activeTab]);

  const handleStart = useCallback(() => {
    if (!selectedProjectId) return;
    if (!editableIdea.trim()) return;

    // Update the store's idea to the edited version before starting
    useCodePlaygroundStore.setState({ initialIdea: editableIdea });
    startPlayground(selectedProjectId, editableIdea, playgroundType, sandboxType);
  }, [selectedProjectId, editableIdea, playgroundType, sandboxType]);

  const handleCopy = useCallback(async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard not available
    }
  }, []);

  const handleIntegrate = useCallback(() => {
    if (result && onIntegrate) {
      onIntegrate(result);
      closeDialog();
    }
  }, [result, onIntegrate, closeDialog]);

  const handleTryAgain = useCallback(() => {
    reset();
    useCodePlaygroundStore.setState({
      isOpen: true,
      initialIdea: editableIdea,
    });
  }, [reset, editableIdea]);

  const handleClose = useCallback(() => {
    closeDialog();
  }, [closeDialog]);

  const isGenerating = phase === 'generating';
  const isReady = phase === 'ready';
  const isError = phase === 'error';
  const canStart = editableIdea.trim().length > 0 && selectedProjectId && !isGenerating;

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && handleClose()}>
      <DialogContent className="sm:max-w-[900px] max-h-[90vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Zap className="h-5 w-5 text-primary" />
            {t('codePlayground:title')}
          </DialogTitle>
          <DialogDescription>
            {t('codePlayground:description')}
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto space-y-4 py-2">
          {/* Idea Input */}
          <div className="space-y-2">
            <Label htmlFor="playground-idea">
              {t('codePlayground:idea.label')}
            </Label>
            <Textarea
              id="playground-idea"
              value={editableIdea}
              onChange={(e) => setEditableIdea(e.target.value)}
              placeholder={t('codePlayground:idea.placeholder')}
              className="min-h-[100px]"
              disabled={isGenerating}
            />
          </div>

          {/* Configuration */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="playground-type-select">
                {t('codePlayground:playgroundType.label')}
              </Label>
              <Select
                value={playgroundType}
                onValueChange={(value) =>
                  setPlaygroundType(value as typeof playgroundType)
                }
                disabled={isGenerating}
              >
                <SelectTrigger id="playground-type-select">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {PLAYGROUND_TYPES.map((type) => (
                    <SelectItem key={type} value={type}>
                      <div className="flex items-center gap-2">
                        <Code className="h-4 w-4" />
                        <span>{t(`codePlayground:playgroundType.options.${type}`)}</span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="sandbox-type-select">
                {t('codePlayground:sandboxType.label')}
              </Label>
              <Select
                value={sandboxType}
                onValueChange={(value) =>
                  setSandboxType(value as typeof sandboxType)
                }
                disabled={isGenerating}
              >
                <SelectTrigger id="sandbox-type-select">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {SANDBOX_TYPES.map((type) => (
                    <SelectItem key={type} value={type}>
                      <div className="flex items-center gap-2">
                        <Monitor className="h-4 w-4" />
                        <span>{t(`codePlayground:sandboxType.options.${type}`)}</span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* No Project Warning */}
          {!selectedProjectId && (
            <div className="bg-destructive/10 border border-destructive/30 rounded-lg p-3">
              <p className="text-sm text-destructive">
                {t('codePlayground:errors.noProject')}
              </p>
            </div>
          )}

          {/* Status / Streaming Output during generation */}
          {isGenerating && (
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin text-primary" />
                <span>{status || t('codePlayground:status.generating')}</span>
              </div>
              {streamingOutput && (
                <div className="space-y-1">
                  <Label className="text-xs text-muted-foreground">
                    {t('codePlayground:result.streamingOutput')}
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
                {t('codePlayground:status.error')}
              </p>
              <p className="text-sm text-destructive/80">
                {error || t('codePlayground:errors.generic')}
              </p>
            </div>
          )}

          {/* Result */}
          {isReady && result && (
            <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="code" className="flex items-center gap-2">
                  <Code className="h-4 w-4" />
                  {t('codePlayground:tabs.code')}
                </TabsTrigger>
                <TabsTrigger value="preview" className="flex items-center gap-2">
                  <Monitor className="h-4 w-4" />
                  {t('codePlayground:tabs.preview')}
                </TabsTrigger>
                <TabsTrigger value="files" className="flex items-center gap-2">
                  <FolderTree className="h-4 w-4" />
                  {t('codePlayground:tabs.files')}
                </TabsTrigger>
              </TabsList>

              <TabsContent value="code" className="space-y-4">
                <CodeView result={result} copied={copied} onCopy={handleCopy} t={t} />
              </TabsContent>

              <TabsContent value="preview" className="space-y-4">
                <PreviewView result={result} previewRef={previewRef} t={t} />
              </TabsContent>

              <TabsContent value="files" className="space-y-4">
                <FilesView result={result} t={t} />
              </TabsContent>
            </Tabs>
          )}
        </div>

        {/* Footer Buttons */}
        <DialogFooter className="gap-2 sm:gap-0">
          {/* Idle / Input state */}
          {phase === 'idle' && (
            <>
              <Button variant="outline" onClick={handleClose}>
                {t('codePlayground:actions.close')}
              </Button>
              <Button
                onClick={handleStart}
                disabled={!canStart}
                className="gap-2"
              >
                <Play className="h-4 w-4" />
                {t('codePlayground:actions.start')}
              </Button>
            </>
          )}

          {/* Generating state */}
          {isGenerating && (
            <Button variant="outline" onClick={handleClose}>
              {t('codePlayground:actions.close')}
            </Button>
          )}

          {/* Error state */}
          {isError && (
            <>
              <Button variant="outline" onClick={handleClose}>
                {t('codePlayground:actions.close')}
              </Button>
              <Button onClick={handleTryAgain} className="gap-2">
                <RotateCcw className="h-4 w-4" />
                {t('codePlayground:actions.tryAgain')}
              </Button>
            </>
          )}

          {/* Ready state */}
          {isReady && result && (
            <>
              <Button variant="outline" onClick={handleClose}>
                {t('codePlayground:actions.close')}
              </Button>
              {onIntegrate && (
                <Button onClick={handleIntegrate} className="gap-2">
                  <FolderTree className="h-4 w-4" />
                  {t('codePlayground:actions.integrate')}
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
 * Renders the code view with syntax highlighting
 */
function CodeView({
  result,
  copied,
  onCopy,
  t,
}: {
  result: PlaygroundResult;
  copied: boolean;
  onCopy: (text: string) => void;
  t: (key: string) => string;
}) {
  return (
    <div className="space-y-4">
      {result.html && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm">HTML</CardTitle>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => result.html && onCopy(result.html)}
                className="h-7 gap-1.5 text-xs"
              >
                {copied ? (
                  <>
                    <Check className="h-3 w-3" />
                    {t('codePlayground:actions.copied')}
                  </>
                ) : (
                  <>
                    <Copy className="h-3 w-3" />
                    {t('codePlayground:actions.copy')}
                  </>
                )}
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <pre className="bg-muted/50 rounded-lg p-3 text-xs font-mono max-h-[300px] overflow-y-auto">
              <code>{result.html}</code>
            </pre>
          </CardContent>
        </Card>
      )}

      {result.css && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm">CSS</CardTitle>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => result.css && onCopy(result.css)}
                className="h-7 gap-1.5 text-xs"
              >
                {copied ? (
                  <>
                    <Check className="h-3 w-3" />
                    {t('codePlayground:actions.copied')}
                  </>
                ) : (
                  <>
                    <Copy className="h-3 w-3" />
                    {t('codePlayground:actions.copy')}
                  </>
                )}
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <pre className="bg-muted/50 rounded-lg p-3 text-xs font-mono max-h-[300px] overflow-y-auto">
              <code>{result.css}</code>
            </pre>
          </CardContent>
        </Card>
      )}

      {result.javascript && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm">JavaScript</CardTitle>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => result.javascript && onCopy(result.javascript)}
                className="h-7 gap-1.5 text-xs"
              >
                {copied ? (
                  <>
                    <Check className="h-3 w-3" />
                    {t('codePlayground:actions.copied')}
                  </>
                ) : (
                  <>
                    <Copy className="h-3 w-3" />
                    {t('codePlayground:actions.copy')}
                  </>
                )}
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <pre className="bg-muted/50 rounded-lg p-3 text-xs font-mono max-h-[300px] overflow-y-auto">
              <code>{result.javascript}</code>
            </pre>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

/**
 * Renders the live preview
 */
function PreviewView({
  result,
  previewRef,
  t,
}: {
  result: PlaygroundResult;
  previewRef: React.RefObject<HTMLIFrameElement | null>;
  t: (key: string) => string;
}) {
  if (!result.html) {
    return (
      <div className="bg-muted/50 rounded-lg p-8 text-center text-muted-foreground">
        <Monitor className="h-12 w-12 mx-auto mb-4 opacity-50" />
        <p>{t('codePlayground:preview.noPreview')}</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <Label className="text-sm font-medium">
        {t('codePlayground:preview.title')}
      </Label>
      <iframe
        ref={previewRef}
        className="w-full h-[400px] border rounded-lg bg-white"
        title="Code Preview"
        sandbox="allow-scripts allow-same-origin"
      />
    </div>
  );
}

/**
 * Renders the files structure and integration info
 */
function FilesView({
  result,
  t,
}: {
  result: PlaygroundResult;
  t: (key: string) => string;
}) {
  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-sm flex items-center gap-2">
            <FolderTree className="h-4 w-4" />
            {t('codePlayground:files.structure')}
          </CardTitle>
          <CardDescription>
            {t('codePlayground:files.description')}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {result.files && result.files.length > 0 ? (
            <div className="space-y-2">
              {result.files.map((file, index) => (
                <div
                  key={index}
                  className="flex items-center gap-2 p-2 bg-muted/30 rounded"
                >
                  <Code className="h-4 w-4 text-primary" />
                  <span className="text-sm font-mono">{file.path}</span>
                  <span className="text-xs text-muted-foreground">
                    ({file.size} bytes)
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground italic">
              {t('codePlayground:files.noFiles')}
            </p>
          )}
        </CardContent>
      </Card>

      {result.integrationNotes && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">
              {t('codePlayground:integration.title')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              {result.integrationNotes}
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

export default CodePlaygroundDialog;
