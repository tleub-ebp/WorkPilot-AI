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
} from 'lucide-react';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import type { PixelAgent } from '../../stores/pixel-office-store';
import type { Terminal } from '../../stores/terminal-store';
import type { ExecutionPhase } from '../../../shared/types/task';

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

function getAgentColor(agent: PixelAgent): string {
  if (agent.type === 'task') {
    const phase = PHASE_INFO[agent.phase ?? 'idle'];
    const map: Record<string, string> = {
      planning: '#27AE60', coding: '#4A90D9', qa_review: '#9B59B6',
      qa_fixing: '#E67E22', rate_limit_paused: '#F39C12', auth_failure_paused: '#E74C3C',
      complete: '#2ECC71', failed: '#E74C3C', idle: '#6B7280',
    };
    void phase;
    return map[agent.phase ?? 'idle'] ?? '#6B7280';
  }
  return ACTIVITY_INFO[agent.activity]?.color ?? '#6B7280';
}

// ── Syntax-highlighted inline code chip ──────────────────────

function CodeChip({ text }: { text: string }) {
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

function ProgressBar({ value, color }: { value: number; color: string }) {
  return (
    <div className="w-full bg-white/10 rounded-full h-1.5 overflow-hidden">
      <div
        className="h-full rounded-full transition-all duration-500"
        style={{ width: `${Math.max(2, value)}%`, background: color }}
      />
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
  agent: PixelAgent;
  color: string;
  onGoToTask: () => void;
  onStopTask: () => void;
  onClose: () => void;
}) {
  const phaseInfo = PHASE_INFO[agent.phase ?? 'idle'] ?? PHASE_INFO.idle;
  const isRunning = agent.activity !== 'idle' && agent.activity !== 'exited';
  const isPaused  = agent.phase === 'rate_limit_paused' || agent.phase === 'auth_failure_paused';

  return (
    <>
      {/* Phase status */}
      <div className="px-4 py-3">
        <p className="text-xs text-white/75 leading-relaxed">{phaseInfo.description}</p>

        {/* Current subtask */}
        {agent.currentSubtask && (
          <div className="mt-2 flex items-start gap-1.5 text-xs">
            <ChevronRight className="h-3 w-3 text-white/40 mt-0.5 shrink-0" />
            <span className="text-white/60 font-mono leading-relaxed">{agent.currentSubtask}</span>
          </div>
        )}
      </div>

      {/* Progress */}
      {agent.progress !== undefined && (
        <div className="px-4 pb-3">
          <div className="flex justify-between text-[10px] text-white/40 font-mono mb-1.5">
            <span>Progression globale</span>
            <span>{Math.round(agent.progress)}%</span>
          </div>
          <ProgressBar value={agent.progress} color={color} />
        </div>
      )}

      {/* Actions */}
      <div
        className="flex flex-wrap gap-1.5 px-4 pb-4"
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
    </>
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
  agent: PixelAgent;
  terminal: Terminal | undefined;
  onGoToTerminal: () => void;
  onKill: () => void;
  onInterrupt: () => void;
  onResumeClaude: () => void;
  onSendCommand: (cmd: string) => void;
}) {
  const [command, setCommand] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);
  const info = ACTIVITY_INFO[agent.activity] ?? ACTIVITY_INFO.idle;
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
              style={{ background: `${ACTIVITY_INFO[agent.activity]?.bgColor}`, color: ACTIVITY_INFO[agent.activity]?.color }}
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
  agent: PixelAgent;
  terminal: Terminal | undefined;
  anchorX: number;
  anchorY: number;
  onClose: () => void;
  onGoToTerminal: () => void;
  onGoToTask: () => void;
  onKill: () => void;
  onInterrupt: () => void;
  onResumeClaude: () => void;
  onSendCommand: (cmd: string) => void;
  onStopTask: () => void;
}

export function AgentBubble({
  agent, terminal, anchorX, anchorY,
  onClose, onGoToTerminal, onGoToTask,
  onKill, onInterrupt, onResumeClaude, onSendCommand, onStopTask,
}: AgentBubbleProps) {
  const bubbleRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  const color = getAgentColor(agent);
  const BUBBLE_W = 320;
  const left = Math.min(anchorX - 20, window.innerWidth - BUBBLE_W - 24);
  const top  = Math.max(8, anchorY - 300);

  // Header info
  const isTaskAgent = agent.type === 'task';
  const phaseInfo   = isTaskAgent ? (PHASE_INFO[agent.phase ?? 'idle'] ?? PHASE_INFO.idle) : null;
  const actInfo     = !isTaskAgent ? (ACTIVITY_INFO[agent.activity] ?? ACTIVITY_INFO.idle) : null;
  const headerEmoji = isTaskAgent ? phaseInfo!.emoji : actInfo!.emoji;
  const headerLabel = isTaskAgent ? phaseInfo!.label : actInfo!.label;

  return (
    <div
      ref={bubbleRef}
      className="absolute z-50 select-none"
      style={{ left, top, width: BUBBLE_W }}
      onClick={(e) => e.stopPropagation()}
    >
      <div
        className="rounded-2xl shadow-2xl overflow-hidden border border-white/10"
        style={{
          background: 'linear-gradient(135deg, #1A1A2E 0%, #16213E 100%)',
          boxShadow: `0 0 0 2px ${color}40, 0 20px 60px rgba(0,0,0,0.5)`,
        }}
      >
        {/* Header */}
        <div
          className="flex items-center justify-between px-4 py-3"
          style={{ borderBottom: `1px solid ${color}30`, background: `${color}15` }}
        >
          <div className="flex items-center gap-2">
            <span className="text-base">{headerEmoji}</span>
            <span className="font-mono font-bold text-sm text-white">{agent.name}</span>

            {isTaskAgent && (
              <Badge variant="outline" className="text-[10px] px-1.5 py-0 border-orange-500/50 text-orange-400">
                <LayoutDashboard className="h-2.5 w-2.5 mr-0.5" />
                Kanban
              </Badge>
            )}
            {agent.isClaudeMode && !isTaskAgent && (
              <Badge variant="outline" className="text-[10px] px-1.5 py-0 border-orange-500/50 text-orange-400">
                <Zap className="h-2.5 w-2.5 mr-0.5" />
                Claude
              </Badge>
            )}
          </div>

          <div className="flex items-center gap-1.5">
            <span
              className="text-xs font-mono px-2 py-0.5 rounded-full"
              style={{ background: `${color}20`, color, border: `1px solid ${color}50` }}
            >
              {headerLabel}
            </span>
            <button
              type="button"
              onClick={onClose}
              className="text-white/40 hover:text-white/80 transition-colors rounded-full w-5 h-5 flex items-center justify-center"
            >
              ×
            </button>
          </div>
        </div>

        {/* Body — split by agent type */}
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

      {/* Arrow */}
      <div className="flex" style={{ paddingLeft: 24 }}>
        <div
          className="w-0 h-0"
          style={{
            borderLeft: '10px solid transparent',
            borderRight: '10px solid transparent',
            borderTop: `10px solid ${color}40`,
          }}
        />
      </div>
    </div>
  );
}

// ── Add Agent Button ──────────────────────────────────────────

export function AddAgentButton({ onClick, disabled }: { onClick: () => void; disabled?: boolean }) {
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
