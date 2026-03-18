/**
 * AgentBubble — Interactive comic-style speech bubble overlay.
 *
 * Appears when the user clicks an agent in the Pixel Office canvas.
 * Handles both terminal agents and Kanban task agents.
 */

import { useState, useRef, useEffect, useCallback } from 'react';
import {
  Maximize2,
  X,
  Square,
  Play,
  Send,
  Plus,
  Zap,
  LayoutDashboard,
  ChevronRight,
  ChevronDown,
  Terminal as TerminalIcon,
  Copy,
  Check,
} from 'lucide-react';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { useTaskStore } from '../../stores/task-store';
import { stripAnsiCodes } from '../../../shared/utils/ansi-sanitizer';
import type { PixelAgent } from '../../stores/pixel-office-store';
import type { Terminal } from '../../stores/terminal-store';

// ── Phase descriptions (human-friendly) ──────────────────────

interface PhaseInfo {
  emoji: string;
  label: string;
  description: string;
}

const PHASE_INFO: Record<string, PhaseInfo> = {
  idle:                { emoji: '😴', label: 'En veille',        description: "Prêt à démarrer." },
  planning:            { emoji: '📋', label: 'Planification',    description: "L'IA analyse ta demande et prépare un plan d'action détaillé." },
  coding:              { emoji: '✍️', label: 'Développement',    description: "Le code est en cours d'écriture. Les sous-tâches s'enchaînent automatiquement." },
  qa_review:           { emoji: '🔍', label: 'Vérification QA',  description: "Un agent vérifie la qualité du code produit : tests, cohérence, bonnes pratiques." },
  qa_fixing:           { emoji: '🔧', label: 'Correction QA',    description: "Des problèmes ont été détectés. L'agent les corrige avant livraison." },
  rate_limit_paused:   { emoji: '⏳', label: 'Limite API',       description: "L'API Claude a atteint sa limite. Reprise automatique dans quelques instants." },
  auth_failure_paused: { emoji: '🔑', label: 'Auth. échouée',    description: "Problème d'authentification. Vérifie tes profils Claude dans les paramètres." },
  complete:            { emoji: '✅', label: 'Terminé',           description: "La tâche est complète et prête pour ta revue." },
  failed:              { emoji: '❌', label: 'Échec',             description: "La tâche a échoué. Consulte les logs pour comprendre ce qui s'est passé." },
};

// ── Activity descriptions for terminal agents ─────────────────

interface ActivityInfo {
  emoji: string;
  label: string;
  description: (agent: PixelAgent) => string;
  color: string;
  bgColor: string;
}

const ACTIVITY_INFO: Record<string, ActivityInfo> = {
  typing: {
    emoji: '✍️', label: 'En train de coder',
    description: (a) => a.taskName
      ? `Implémentation de "${a.taskName}" — l'agent écrit du code activement.`
      : "L'agent est en train d'écrire du code.",
    color: '#4A90D9', bgColor: 'rgba(74,144,217,0.12)',
  },
  running: {
    emoji: '⚙️', label: 'Exécution',
    description: () => "L'agent exécute une commande (tests, build, installation…). Attends ou interromps-le.",
    color: '#1ABC9C', bgColor: 'rgba(26,188,156,0.12)',
  },
  reading: {
    emoji: '📖', label: 'Analyse',
    description: (a) => a.taskName
      ? `Lecture du code pour comprendre "${a.taskName}".`
      : "L'agent analyse les fichiers du projet.",
    color: '#27AE60', bgColor: 'rgba(39,174,96,0.12)',
  },
  waiting: {
    emoji: '💬', label: 'En attente',
    description: () => "L'agent attend ta réponse ou une approbation.",
    color: '#F39C12', bgColor: 'rgba(243,156,18,0.12)',
  },
  idle: {
    emoji: '😴', label: 'Au repos',
    description: () => "L'agent est disponible. Donne-lui un ordre ou démarre Claude.",
    color: '#6B7280', bgColor: 'rgba(107,114,128,0.12)',
  },
  exited: {
    emoji: '💤', label: 'Session terminée',
    description: () => "Ce terminal a été fermé.",
    color: '#E74C3C', bgColor: 'rgba(231,76,60,0.12)',
  },
};

const PHASE_COLOR: Record<string, string> = {
  planning: '#27AE60', coding: '#4A90D9', qa_review: '#9B59B6',
  qa_fixing: '#E67E22', rate_limit_paused: '#F39C12', auth_failure_paused: '#E74C3C',
  complete: '#2ECC71', failed: '#E74C3C', idle: '#6B7280',
};

function getAgentColor(agent: PixelAgent): string {
  if (agent.type === 'task') return PHASE_COLOR[agent.phase ?? 'idle'] ?? '#6B7280';
  return ACTIVITY_INFO[agent.activity]?.color ?? '#6B7280';
}

// ── Syntax-highlighted inline code chip ──────────────────────

function CodeChip({ text }: { readonly text: string }) {
  return (
    <span
      className="inline-block font-mono text-[10px] px-1.5 py-0.5 rounded"
      style={{ background: 'rgba(99,102,241,0.15)', color: '#818CF8' }}
    >
      {text}
    </span>
  );
}

// ── Progress bar ──────────────────────────────────────────────

function ProgressBar({ value, color }: { readonly value: number; readonly color: string }) {
  return (
    <div className="w-full bg-white/10 rounded-full h-1.5 overflow-hidden">
      <div
        className="h-full rounded-full transition-all duration-500"
        style={{ width: `${Math.max(2, value)}%`, background: color }}
      />
    </div>
  );
}

// ── Live log stream ───────────────────────────────────────────

const LOG_KEEP = 5000;

function logLineColor(line: string): string {
  if (/\[ERROR\]|error:/i.test(line) || /\bError\b/.test(line)) return '#F87171';
  if (/\[WARN\]|warning/i.test(line)) return '#FCD34D';
  if (line.startsWith('✅') || /\[OK\]|\bsuccess\b/i.test(line)) return '#6EE7B7';
  if (/\[INFO\]/.test(line)) return 'rgba(255,255,255,0.65)';
  return 'rgba(255,255,255,0.42)';
}

function LogStream({ taskId }: { readonly taskId: string }) {
  const logs = useTaskStore(
    (s) => s.tasks.find(t => t.id === taskId)?.logs ?? []
  );
  const [open, setOpen]     = useState(true);
  const [copied, setCopied] = useState(false);
  const scrollRef           = useRef<HTMLDivElement>(null);
  const atBottomRef         = useRef(true);

  const visibleLines = logs
    .slice(-LOG_KEEP)
    .map(l => stripAnsiCodes(l).trim())
    .filter(l => l.length > 0);

  const handleScroll = () => {
    const el = scrollRef.current;
    if (!el) return;
    atBottomRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < 32;
  };

  useEffect(() => {
    if (open && atBottomRef.current && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs.length, open]);

  const copyLogs = useCallback(() => {
    navigator.clipboard.writeText(visibleLines.join('\n')).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }, [visibleLines]);

  const lastLine = visibleLines.at(-1);

  return (
    <div className="flex flex-col flex-1 min-h-0" style={{ borderTop: '1px solid rgba(255,255,255,0.08)' }}>
      {/* Toggle header */}
      <div className="flex items-center justify-between px-4 py-2 shrink-0">
        <button
          type="button"
          className="flex items-center gap-1.5 text-[11px] text-white/50 hover:text-white/80 transition-colors font-mono"
          onClick={() => setOpen(v => !v)}
        >
          <TerminalIcon className="h-3.5 w-3.5" />
          <span>Logs de l&apos;agent</span>
          {visibleLines.length > 0 && (
            <span className="px-1.5 py-0.5 rounded text-[10px] bg-white/10 text-white/50">
              {visibleLines.length}
            </span>
          )}
          <ChevronDown
            className="h-3 w-3 transition-transform ml-0.5"
            style={{ transform: open ? 'rotate(180deg)' : 'none' }}
          />
        </button>

        {visibleLines.length > 0 && (
          <button
            type="button"
            onClick={copyLogs}
            className="flex items-center gap-1 text-[10px] font-mono px-2 py-1 rounded transition-all"
            style={{
              color: copied ? '#6EE7B7' : 'rgba(255,255,255,0.35)',
              background: copied ? 'rgba(110,231,183,0.12)' : 'rgba(255,255,255,0.06)',
              border: `1px solid ${copied ? 'rgba(110,231,183,0.3)' : 'rgba(255,255,255,0.08)'}`,
            }}
            title="Copier tous les logs"
          >
            {copied
              ? <><Check className="h-3 w-3" /> Copié</>
              : <><Copy className="h-3 w-3" /> Copier</>
            }
          </button>
        )}
      </div>

      {/* Last line preview (collapsed) */}
      {!open && lastLine && (
        <div className="px-4 pb-2.5 shrink-0">
          <p className="text-[10px] font-mono truncate" style={{ color: logLineColor(lastLine) }}>
            {lastLine}
          </p>
        </div>
      )}

      {/* Expanded log area — flex-1 fills remaining space */}
      {open && (
        <div
          ref={scrollRef}
          onScroll={handleScroll}
          className="mx-3 mb-3 rounded-xl overflow-y-auto flex-1 min-h-0"
          style={{
            background: 'rgba(0,0,0,0.55)',
            border: '1px solid rgba(255,255,255,0.10)',
            scrollbarWidth: 'thin',
            scrollbarColor: 'rgba(255,255,255,0.2) transparent',
          }}
        >
          {visibleLines.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full gap-2 text-white/20">
              <TerminalIcon className="h-5 w-5" />
              <p className="text-[10px] font-mono">En attente de logs…</p>
            </div>
          ) : (
            <div className="p-3 space-y-1">
              {visibleLines.map((line, i) => (
                <p
                  // biome-ignore lint/suspicious/noArrayIndexKey: log lines have no stable id
                  key={i}
                  className="text-[11px] font-mono leading-relaxed break-all"
                  style={{ color: logLineColor(line) }}
                >
                  {line}
                </p>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Task agent panel ──────────────────────────────────────────

function TaskPanel({
  agent,
  color,
  onGoToTask,
  onStopTask,
  onClose,
}: {
  readonly agent: PixelAgent;
  readonly color: string;
  readonly onGoToTask: () => void;
  readonly onStopTask: () => void;
  readonly onClose: () => void;
}) {
  const taskId    = agent.taskId ?? '';
  const phaseInfo = PHASE_INFO[agent.phase ?? 'idle'] ?? PHASE_INFO.idle;
  const isRunning = agent.activity !== 'idle' && agent.activity !== 'exited';
  const isPaused  = agent.phase === 'rate_limit_paused' || agent.phase === 'auth_failure_paused';

  return (
    <div className="flex flex-col flex-1 min-h-0">
      {/* Phase status — fixed */}
      <div className="px-4 py-3 shrink-0">
        <p className="text-xs text-white/75 leading-relaxed">{phaseInfo.description}</p>
        {agent.currentSubtask && (
          <div className="mt-2 flex items-start gap-1.5 text-xs">
            <ChevronRight className="h-3 w-3 text-white/40 mt-0.5 shrink-0" />
            <span className="text-white/60 font-mono leading-relaxed">{agent.currentSubtask}</span>
          </div>
        )}
      </div>

      {/* Progress — fixed */}
      {agent.progress !== undefined && (
        <div className="px-4 pb-3 shrink-0">
          <div className="flex justify-between text-[10px] text-white/40 font-mono mb-1.5">
            <span>Progression globale</span>
            <span>{Math.round(agent.progress)}%</span>
          </div>
          <ProgressBar value={agent.progress} color={color} />
        </div>
      )}

      {/* Live log stream — expands to fill remaining space */}
      {taskId && <LogStream taskId={taskId} />}

      {/* Actions — fixed */}
      <div
        className="flex flex-wrap gap-1.5 px-4 pb-4 shrink-0"
        style={{ borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: '10px', marginTop: '2px' }}
      >
        <Button
          size="sm" variant="ghost"
          className="h-7 px-2.5 text-[11px] text-white/60 hover:text-white hover:bg-white/10"
          onClick={onGoToTask}
        >
          <LayoutDashboard className="h-3 w-3 mr-1" />
          Voir dans Kanban
        </Button>

        {isRunning && !isPaused && (
          <Button
            size="sm" variant="ghost"
            className="h-7 px-2.5 text-[11px] text-red-400/70 hover:text-red-300 hover:bg-red-400/10 ml-auto"
            onClick={onStopTask}
          >
            <Square className="h-3 w-3 mr-1" />
            Arrêter
          </Button>
        )}

        {!isRunning && (
          <Button
            size="sm" variant="ghost"
            className="h-7 px-2.5 text-[11px] text-white/40 hover:text-white/60 ml-auto"
            onClick={onClose}
          >
            <X className="h-3 w-3 mr-1" />
            Fermer
          </Button>
        )}
      </div>
    </div>
  );
}

// ── Terminal agent panel ──────────────────────────────────────

function TerminalPanel({
  agent,
  terminal,
  onGoToTerminal,
  onKill,
  onInterrupt,
  onResumeClaude,
  onSendCommand,
}: {
  readonly agent: PixelAgent;
  readonly terminal: Terminal | undefined;
  readonly onGoToTerminal: () => void;
  readonly onKill: () => void;
  readonly onInterrupt: () => void;
  readonly onResumeClaude: () => void;
  readonly onSendCommand: (cmd: string) => void;
}) {
  const [command, setCommand] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);
  const info      = ACTIVITY_INFO[agent.activity] ?? ACTIVITY_INFO.idle;
  const isExited  = agent.activity === 'exited';
  const isBusy    = agent.activity === 'typing' || agent.activity === 'running';
  const isWaiting = agent.activity === 'waiting';

  useEffect(() => {
    if (!isExited) setTimeout(() => inputRef.current?.focus(), 50);
  }, [agent.id, isExited]);

  const handleSend = () => {
    const trimmed = command.trim();
    if (!trimmed) return;
    onSendCommand(trimmed);
    setCommand('');
  };

  return (
    <>
      {/* Description */}
      <div className="px-4 py-3">
        <p className="text-xs text-white/75 leading-relaxed">{info.description(agent)}</p>

        {agent.taskName && (
          <div className="mt-2 flex items-center gap-1.5 text-xs text-white/50">
            <span>📋 Tâche :</span>
            <CodeChip text={agent.taskName} />
          </div>
        )}

        {terminal && (
          <div className="mt-2 flex flex-wrap gap-1.5 text-[10px] text-white/40 font-mono">
            {terminal.cwd && (
              <span className="flex items-center gap-1">
                📁 <CodeChip text={terminal.cwd.split(/[\\/]/).slice(-2).join('/')} />
              </span>
            )}
            {terminal.claudeSessionId && (
              <span className="flex items-center gap-1">
                🔑 <CodeChip text={`${terminal.claudeSessionId.slice(0, 8)}…`} />
              </span>
            )}
            {terminal.worktreeConfig && (
              <span className="flex items-center gap-1">
                🌿 <CodeChip text={terminal.worktreeConfig.branchName} />
              </span>
            )}
          </div>
        )}
      </div>

      {/* Command input */}
      {!isExited && (
        <div className="px-4 pb-3">
          <div className="flex gap-2">
            <input
              ref={inputRef}
              type="text"
              value={command}
              onChange={(e) => setCommand(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              placeholder={isWaiting ? "Réponds à l'agent…" : "Donne un ordre au terminal…"}
              className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-xs text-white placeholder:text-white/30 font-mono focus:outline-none focus:border-white/30"
            />
            <Button
              size="sm" variant="ghost"
              className="h-7 px-2.5 text-xs"
              style={{ background: ACTIVITY_INFO[agent.activity]?.bgColor, color: ACTIVITY_INFO[agent.activity]?.color }}
              onClick={handleSend}
              disabled={!command.trim()}
            >
              <Send className="h-3 w-3" />
            </Button>
          </div>
          {isWaiting && (
            <p className="text-[10px] text-white/30 mt-1 font-mono">
              ↵ Entrée pour envoyer · Tapé directement dans le terminal
            </p>
          )}
        </div>
      )}

      {/* Actions */}
      <div
        className="flex flex-wrap gap-1.5 px-4 pb-4"
        style={{ borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: '10px', marginTop: '2px' }}
      >
        <Button size="sm" variant="ghost"
          className="h-7 px-2.5 text-[11px] text-white/60 hover:text-white hover:bg-white/10"
          onClick={onGoToTerminal}
        >
          <Maximize2 className="h-3 w-3 mr-1" />
          Voir terminal
        </Button>

        {isBusy && (
          <Button size="sm" variant="ghost"
            className="h-7 px-2.5 text-[11px] text-amber-400/80 hover:text-amber-300 hover:bg-amber-400/10"
            onClick={onInterrupt}
          >
            <Square className="h-3 w-3 mr-1" />
            Interrompre
          </Button>
        )}

        {!isBusy && terminal?.isClaudeMode && !isExited && (
          <Button size="sm" variant="ghost"
            className="h-7 px-2.5 text-[11px] text-orange-400/80 hover:text-orange-300 hover:bg-orange-400/10"
            onClick={onResumeClaude}
          >
            <Play className="h-3 w-3 mr-1" />
            Reprendre Claude
          </Button>
        )}

        {!isExited && (
          <Button size="sm" variant="ghost"
            className="h-7 px-2.5 text-[11px] text-red-400/70 hover:text-red-300 hover:bg-red-400/10 ml-auto"
            onClick={onKill}
          >
            <X className="h-3 w-3 mr-1" />
            Fermer
          </Button>
        )}
      </div>
    </>
  );
}

// ── Main component ────────────────────────────────────────────

export interface AgentBubbleProps {
  readonly agent: PixelAgent;
  readonly terminal: Terminal | undefined;
  readonly anchorX: number;
  readonly anchorY: number;
  readonly onClose: () => void;
  readonly onGoToTerminal: () => void;
  readonly onGoToTask: () => void;
  readonly onKill: () => void;
  readonly onInterrupt: () => void;
  readonly onResumeClaude: () => void;
  readonly onSendCommand: (cmd: string) => void;
  readonly onStopTask: () => void;
}

export function AgentBubble({
  agent, terminal, anchorX, anchorY,
  onClose, onGoToTerminal, onGoToTask,
  onKill, onInterrupt, onResumeClaude, onSendCommand, onStopTask,
}: AgentBubbleProps) {
  const bubbleRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    globalThis.addEventListener('keydown', handler);
    return () => globalThis.removeEventListener('keydown', handler);
  }, [onClose]);

  const color = getAgentColor(agent);
  const top   = Math.round(anchorY) + 16;
  // Arrow points up to the agent: clamp so it stays within the bubble bounds
  const arrowLeft = Math.max(20, Math.min(anchorX - 16, (globalThis.innerWidth ?? 1200) - 32 - 20));

  const isTaskAgent = agent.type === 'task';
  const phaseInfo   = PHASE_INFO[agent.phase ?? 'idle'] ?? PHASE_INFO.idle;
  const actInfo     = ACTIVITY_INFO[agent.activity] ?? ACTIVITY_INFO.idle;
  const headerEmoji = isTaskAgent ? phaseInfo.emoji : actInfo.emoji;
  const headerLabel = isTaskAgent ? phaseInfo.label : actInfo.label;

  return (
    // biome-ignore lint/a11y/noNoninteractiveElementInteractions: bubble captures clicks to prevent backdrop close
    <div
      ref={bubbleRef}
      role="dialog"
      aria-modal="false"
      className="absolute z-50 select-none flex flex-col"
      style={{ left: 16, right: 16, top, bottom: 16 }}
      onClick={(e) => e.stopPropagation()}
      onKeyDown={(e) => e.key === 'Escape' && onClose()}
    >
      {/* Arrow pointing up to the clicked agent */}
      <div style={{ paddingLeft: arrowLeft, lineHeight: 0 }}>
        <div
          className="w-0 h-0 inline-block"
          style={{
            borderLeft: '10px solid transparent',
            borderRight: '10px solid transparent',
            borderBottom: `10px solid ${color}60`,
          }}
        />
      </div>

      <div
        className="rounded-2xl shadow-2xl border border-white/10 flex flex-col min-h-0 flex-1"
        style={{
          background: 'linear-gradient(135deg, #1A1A2E 0%, #16213E 100%)',
          boxShadow: `0 0 0 2px ${color}40, 0 20px 60px rgba(0,0,0,0.5)`,
        }}
      >
        {/* Header */}
        <div
          className="flex items-center justify-between px-5 py-4 shrink-0"
          style={{ borderBottom: `1px solid ${color}30`, background: `${color}15` }}
        >
          <div className="flex items-center gap-3 min-w-0">
            <span className="text-2xl shrink-0">{headerEmoji}</span>
            <span className="font-mono font-bold text-xl text-white leading-tight">{agent.fullName}</span>

            {isTaskAgent && (
              <Badge variant="outline" className="text-xs px-2 py-0.5 border-orange-500/50 text-orange-400 shrink-0">
                <LayoutDashboard className="h-3 w-3 mr-1" />
                Kanban
              </Badge>
            )}
            {agent.isClaudeMode && !isTaskAgent && (
              <Badge variant="outline" className="text-xs px-2 py-0.5 border-orange-500/50 text-orange-400 shrink-0">
                <Zap className="h-3 w-3 mr-1" />
                Claude
              </Badge>
            )}
          </div>

          <div className="flex items-center gap-2 shrink-0 ml-3">
            <span
              className="text-sm font-mono font-semibold px-3 py-1 rounded-full"
              style={{ background: `${color}20`, color, border: `1px solid ${color}50` }}
            >
              {headerLabel}
            </span>
            <button
              type="button"
              onClick={onClose}
              className="text-white/40 hover:text-white/80 transition-colors rounded-full w-7 h-7 flex items-center justify-center text-lg"
            >
              ×
            </button>
          </div>
        </div>

        {/* Body — split by agent type */}
        <div className="flex flex-col flex-1 min-h-0">
          {isTaskAgent ? (
            <TaskPanel
              agent={agent}
              color={color}
              onGoToTask={onGoToTask}
              onStopTask={onStopTask}
              onClose={onClose}
            />
          ) : (
            <TerminalPanel
              agent={agent}
              terminal={terminal}
              onGoToTerminal={onGoToTerminal}
              onKill={onKill}
              onInterrupt={onInterrupt}
              onResumeClaude={onResumeClaude}
              onSendCommand={onSendCommand}
            />
          )}
        </div>
      </div>
    </div>
  );
}

// ── Add Agent Button ──────────────────────────────────────────

export function AddAgentButton({ onClick, disabled }: { readonly onClick: () => void; readonly disabled?: boolean }) {
  return (
    <Button
      variant="outline" size="sm"
      className="h-8 px-3 text-xs font-mono border-dashed border-emerald-500/50 text-emerald-400 hover:bg-emerald-500/10 hover:border-emerald-400"
      onClick={onClick}
      disabled={disabled}
    >
      <Plus className="h-3.5 w-3.5 mr-1.5" />
      Nouveau terminal
    </Button>
  );
}
