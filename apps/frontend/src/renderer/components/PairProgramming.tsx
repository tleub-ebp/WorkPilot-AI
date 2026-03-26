/**
 * AI Pair Programming View (Feature 10)
 *
 * Split-view interface for real parallel coordinated development:
 * - Left panel: Developer's scope summary
 * - Center panel: Bidirectional chat
 * - Right panel: AI work log (live actions + streaming output)
 */

import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Users,
  Square,
  Send,
  FileCode2,
  FilePlus,
  Terminal as TerminalIcon,
  AlertTriangle,
  CheckCircle2,
  Loader2,
  ChevronRight,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';
import {
  usePairProgrammingStore,
  startPairSession,
  stopPairSession,
  sendPairMessage,
  setupPairProgrammingListeners,
  type PairStatus,
  type AiAction,
  type PairMessage,
  type StartSessionParams,
} from '@/stores/pair-programming-store';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface PairProgrammingProps {
  readonly projectId: string;
}

// ---------------------------------------------------------------------------
// Status badge
// ---------------------------------------------------------------------------

function StatusBadge({ status }: { status: PairStatus }) {
  const { t } = useTranslation('pairProgramming');
  const variants: Record<PairStatus, 'default' | 'secondary' | 'destructive' | 'outline'> = {
    idle: 'outline',
    planning: 'secondary',
    active: 'default',
    paused: 'outline',
    completed: 'secondary',
    error: 'destructive',
  };
  return (
    <Badge variant={variants[status]}>
      {status === 'active' && <span className="mr-1.5 inline-block h-1.5 w-1.5 rounded-full bg-green-500 animate-pulse" />}
      {t(`status.${status}`)}
    </Badge>
  );
}

// ---------------------------------------------------------------------------
// Setup form
// ---------------------------------------------------------------------------

interface SetupFormProps {
  onStart: (params: StartSessionParams) => void;
}

function SetupForm({ onStart }: SetupFormProps) {
  const { t } = useTranslation('pairProgramming');
  const [goal, setGoal] = useState('');
  const [devScope, setDevScope] = useState('');
  const [aiScope, setAiScope] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!goal.trim() || !devScope.trim() || !aiScope.trim()) return;
    onStart({ projectId: '', goal: goal.trim(), devScope: devScope.trim(), aiScope: aiScope.trim() });
  };

  return (
    <div className="flex flex-col items-center justify-center h-full max-w-xl mx-auto px-4 py-8">
      {/* Hero */}
      <div className="text-center mb-8">
        <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-primary/10 mb-4">
          <Users className="w-7 h-7 text-primary" />
        </div>
        <h2 className="text-xl font-semibold mb-1">{t('empty.title')}</h2>
        <p className="text-sm text-muted-foreground">{t('empty.description')}</p>
      </div>

      {/* Feature bullets */}
      <div className="flex flex-col gap-2 text-sm text-muted-foreground mb-8 self-stretch">
        {(['feature1', 'feature2', 'feature3'] as const).map((f) => (
          <div key={f} className="flex items-center gap-2">
            <ChevronRight className="w-3.5 h-3.5 text-primary flex-shrink-0" />
            {t(`empty.${f}`)}
          </div>
        ))}
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit} className="flex flex-col gap-4 w-full">
        <div className="flex flex-col gap-1.5">
          // biome-ignore lint/a11y/noLabelWithoutControl: label association is implicit
{/* biome-ignore lint/a11y/noLabelWithoutControl: intentional  */}
          <label className="text-sm font-medium">{t('setup.goalLabel')}</label>
          <Textarea
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            placeholder={t('setup.goalPlaceholder')}
            rows={2}
          />
        </div>
        <div className="flex flex-col gap-1.5">
          // biome-ignore lint/a11y/noLabelWithoutControl: label association is implicit
{/* biome-ignore lint/a11y/noLabelWithoutControl: intentional  */}
          <label className="text-sm font-medium">{t('setup.devScopeLabel')}</label>
          <Textarea
            value={devScope}
            onChange={(e) => setDevScope(e.target.value)}
            placeholder={t('setup.devScopePlaceholder')}
            rows={2}
          />
        </div>
        <div className="flex flex-col gap-1.5">
          // biome-ignore lint/a11y/noLabelWithoutControl: label association is implicit
{/* biome-ignore lint/a11y/noLabelWithoutControl: intentional  */}
          <label className="text-sm font-medium">{t('setup.aiScopeLabel')}</label>
          <Textarea
            value={aiScope}
            onChange={(e) => setAiScope(e.target.value)}
            placeholder={t('setup.aiScopePlaceholder')}
            rows={2}
          />
        </div>
        <p className="text-xs text-muted-foreground">{t('setup.hint')}</p>
        <Button
          type="submit"
          disabled={!goal.trim() || !devScope.trim() || !aiScope.trim()}
          className="w-full"
        >
          <Users className="w-4 h-4 mr-2" />
          {t('setup.startButton')}
        </Button>
      </form>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Action icon
// ---------------------------------------------------------------------------

function ActionIcon({ type }: { type: string }) {
  switch (type) {
    case 'file_created': return <FilePlus className="w-3.5 h-3.5 text-green-500" />;
    case 'file_modified': return <FileCode2 className="w-3.5 h-3.5 text-blue-500" />;
    case 'command_run': return <TerminalIcon className="w-3.5 h-3.5 text-yellow-500" />;
    default: return <ChevronRight className="w-3.5 h-3.5 text-muted-foreground" />;
  }
}

// ---------------------------------------------------------------------------
// AI action log entry
// ---------------------------------------------------------------------------

function ActionEntry({ action }: { action: AiAction }) {
  const { t } = useTranslation('pairProgramming');
  const label = t(`actions.${action.actionType}`, { defaultValue: action.actionType });
  return (
    <div className="flex items-start gap-2 py-1.5 border-b border-border/50 last:border-0">
      <ActionIcon type={action.actionType} />
      <div className="min-w-0 flex-1">
        <span className="text-xs font-medium text-muted-foreground mr-1">{label}</span>
        {action.filePath && (
          <span className="text-xs font-mono text-foreground truncate block">{action.filePath}</span>
        )}
        {!action.filePath && (
          <span className="text-xs text-muted-foreground">{action.description}</span>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Chat message bubble
// ---------------------------------------------------------------------------

function MessageBubble({ message }: { message: PairMessage }) {
  const { t } = useTranslation('pairProgramming');
  const isUser = message.role === 'user';
  return (
    <div className={cn('flex flex-col gap-0.5', isUser ? 'items-end' : 'items-start')}>
      <span className="text-[10px] text-muted-foreground px-1">
        {isUser ? t('chat.you') : message.isQuestion ? t('chat.question') : t('chat.ai')}
      </span>
      <div className={cn(
        'rounded-xl px-3 py-2 max-w-[85%] text-sm',
        isUser
          ? 'bg-primary text-primary-foreground'
          : message.isQuestion
            ? 'bg-amber-500/10 border border-amber-500/30 text-foreground'
            : 'bg-muted text-foreground'
      )}>
        {message.content}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function PairProgramming({ projectId }: PairProgrammingProps) {
  const { t } = useTranslation('pairProgramming');

  const session = usePairProgrammingStore((s) => s.session);
  const status = usePairProgrammingStore((s) => s.status);
  const statusMessage = usePairProgrammingStore((s) => s.statusMessage);
  const messages = usePairProgrammingStore((s) => s.messages);
  const pendingMessage = usePairProgrammingStore((s) => s.pendingMessage);
  const streamingContent = usePairProgrammingStore((s) => s.streamingContent);
  const aiActions = usePairProgrammingStore((s) => s.aiActions);
  const conflicts = usePairProgrammingStore((s) => s.conflicts);
  const setPendingMessage = usePairProgrammingStore((s) => s.setPendingMessage);

  const chatEndRef = useRef<HTMLDivElement>(null);
  const streamEndRef = useRef<HTMLDivElement>(null);

  // Setup IPC listeners
  useEffect(() => {
    const cleanup = setupPairProgrammingListeners(projectId);
    return cleanup;
  }, [projectId]);

  // Auto-scroll chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  // Auto-scroll AI stream
  useEffect(() => {
    streamEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  const handleStart = (params: StartSessionParams) => {
    startPairSession({ ...params, projectId });
  };

  const handleStop = () => {
    if (session) stopPairSession(projectId, session.id);
  };

  const handleSendMessage = () => {
    if (!session || !pendingMessage.trim()) return;
    sendPairMessage(projectId, session.id, pendingMessage.trim());
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const isRunning = status === 'planning' || status === 'active';

  // Show setup form when no active session
  if (status === 'idle' && !session) {
    return (
      <div className="h-full overflow-auto">
        <SetupForm onStart={handleStart} />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border flex-shrink-0">
        <div className="flex items-center gap-2.5">
          <Users className="w-4 h-4 text-primary" />
          <span className="font-semibold text-sm">{t('title')}</span>
          {session && <StatusBadge status={status} />}
          {statusMessage && (
            <span className="text-xs text-muted-foreground">{statusMessage}</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {isRunning && (
            <Button size="sm" variant="outline" onClick={handleStop}>
              <Square className="w-3.5 h-3.5 mr-1.5" />
              {t('stopSession')}
            </Button>
          )}
          {(status === 'completed' || status === 'error') && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => usePairProgrammingStore.getState().reset()}
            >
              {t('newSession')}
            </Button>
          )}
        </div>
      </div>

      {/* Conflicts banner */}
      {conflicts.length > 0 && (
        <div className="flex items-center gap-2 px-4 py-2 bg-amber-500/10 border-b border-amber-500/30 text-amber-600 text-xs flex-shrink-0">
          <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" />
          <span>{t('conflicts.description')}</span>
          <span className="font-mono">{conflicts.map((c) => c.filePath).join(', ')}</span>
        </div>
      )}

      {/* Three-panel layout */}
      <div className="flex flex-1 min-h-0 divide-x divide-border">

        {/* LEFT â€” Developer scope */}
        <div className="w-56 flex-shrink-0 flex flex-col">
          <div className="px-3 py-2 border-b border-border text-xs font-semibold text-muted-foreground uppercase tracking-wide">
            {t('sections.yourWork')}
          </div>
          <ScrollArea className="flex-1">
            <div className="p-3 space-y-3">
              {session && (
                <>
                  <div>
                    <div className="text-xs font-medium text-muted-foreground mb-1">{t('devWork.scope')}</div>
                    <p className="text-xs text-foreground leading-relaxed">{session.devScope}</p>
                  </div>
                  <div className="rounded-md bg-muted/50 px-2.5 py-2 text-xs text-muted-foreground">
                    {t('devWork.reminder')}
                  </div>
                  {session.goal && (
                    <div>
                      <div className="text-xs font-medium text-muted-foreground mb-1">Goal</div>
                      <p className="text-xs text-foreground leading-relaxed">{session.goal}</p>
                    </div>
                  )}
                </>
              )}
            </div>
          </ScrollArea>
        </div>

        {/* CENTER â€” Chat */}
        <div className="flex-1 flex flex-col min-w-0">
          <div className="px-3 py-2 border-b border-border text-xs font-semibold text-muted-foreground uppercase tracking-wide">
            {t('sections.chat')}
          </div>

          <ScrollArea className="flex-1 px-3 py-3">
            {messages.length === 0 ? (
              <p className="text-xs text-muted-foreground text-center py-8">{t('chat.empty')}</p>
            ) : (
              <div className="space-y-3">
                {messages.map((msg) => (
                  <MessageBubble key={msg.id} message={msg} />
                ))}
                <div ref={chatEndRef} />
              </div>
            )}
          </ScrollArea>

          {/* Input */}
          <div className="p-3 border-t border-border flex-shrink-0">
            <div className="flex gap-2">
              <Textarea
                value={pendingMessage}
                onChange={(e) => setPendingMessage(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={t('messagePlaceholder')}
                rows={2}
                className="resize-none text-sm"
                disabled={!isRunning}
              />
              <Button
                size="sm"
                onClick={handleSendMessage}
                disabled={!isRunning || !pendingMessage.trim()}
                className="self-end"
              >
                <Send className="w-3.5 h-3.5" />
              </Button>
            </div>
          </div>
        </div>

        {/* RIGHT â€” AI work */}
        <div className="w-72 flex-shrink-0 flex flex-col">
          <div className="px-3 py-2 border-b border-border text-xs font-semibold text-muted-foreground uppercase tracking-wide flex items-center justify-between">
            <span>{t('sections.aiWork')}</span>
            {isRunning && <Loader2 className="w-3 h-3 animate-spin text-muted-foreground" />}
            {status === 'completed' && <CheckCircle2 className="w-3 h-3 text-green-500" />}
          </div>

          {/* AI scope */}
          {session && (
            <div className="px-3 py-2 border-b border-border/50 bg-muted/30">
              <p className="text-xs text-muted-foreground leading-relaxed">{session.aiScope}</p>
            </div>
          )}

          {/* Streaming output */}
          {(streamingContent || isRunning) && (
            <div className="border-b border-border/50 max-h-40">
              <ScrollArea className="h-full">
                <pre className="p-3 text-xs text-foreground font-mono whitespace-pre-wrap leading-relaxed">
                  {streamingContent}
                  {isRunning && <span className="animate-pulse">â–Œ</span>}
                </pre>
                <div ref={streamEndRef} />
              </ScrollArea>
            </div>
          )}

          {/* Action log */}
          <div className="px-3 py-2 border-b border-border/50 text-[10px] font-semibold text-muted-foreground uppercase tracking-wide">
            {t('aiWork.actionLog')}
          </div>
          <ScrollArea className="flex-1">
            <div className="px-3 py-2">
              {aiActions.length === 0 ? (
                <p className="text-xs text-muted-foreground py-4 text-center">{t('aiWork.noActions')}</p>
              ) : (
                aiActions.map((action) => (
                  <ActionEntry key={action.id} action={action} />
                ))
              )}
            </div>
          </ScrollArea>
        </div>
      </div>
    </div>
  );
}



