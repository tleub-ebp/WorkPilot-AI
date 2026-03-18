import { create } from 'zustand';
import type { Terminal } from './terminal-store';
import type { Task, ExecutionPhase } from '../../shared/types/task';

// ── Types ────────────────────────────────────────────────────

export type AgentActivity = 'idle' | 'typing' | 'reading' | 'running' | 'waiting' | 'exited';
export type PixelAgentType = 'terminal' | 'task';

export interface PixelAgent {
  id: string;                  // Terminal ID or Task ID
  type: PixelAgentType;        // Source of this agent
  name: string;                // Short display name (canvas label, ≤16 chars)
  fullName: string;            // Full untruncated name (used in bubble header)
  characterIndex: number;      // Which character sprite to use (0-5)
  activity: AgentActivity;     // Current visual activity
  seatIndex: number;           // Which desk the agent sits at
  isClaudeMode: boolean;       // Whether in Claude mode (terminals) / always true for tasks
  // Task-specific fields
  taskId?: string;             // Kanban task ID (for type === 'task')
  phase?: ExecutionPhase;      // Current execution phase
  progress?: number;           // Overall progress 0-100
  currentSubtask?: string;     // Current subtask description
  // Terminal-specific fields
  taskName?: string;           // Associated task name (for speech bubble)
  speechBubble?: string;       // Text to show in canvas speech bubble
  speechBubbleTimer?: number;  // Auto-dismiss timer
}

export interface PixelOfficeSettings {
  zoom: number;
  showGrid: boolean;
  soundEnabled: boolean;
  autoAssignSeats: boolean;
}

interface PixelOfficeState {
  agents: PixelAgent[];
  selectedAgentId: string | null;
  settings: PixelOfficeSettings;
  nextCharacterIndex: number;

  // Actions
  syncAll: (terminals: Terminal[], tasks: Task[]) => void;
  /** @deprecated use syncAll */
  syncFromTerminals: (terminals: Terminal[]) => void;
  selectAgent: (id: string | null) => void;
  updateSettings: (updates: Partial<PixelOfficeSettings>) => void;
  setSpeechBubble: (agentId: string, text: string | undefined) => void;
}

// ── Activity mapping ──────────────────────────────────────────

function mapTerminalToActivity(terminal: Terminal): AgentActivity {
  if (terminal.status === 'exited') return 'exited';
  if (terminal.isClaudeBusy) return 'typing';
  if (terminal.isClaudeMode && terminal.status === 'claude-active') {
    return terminal.isClaudeBusy ? 'typing' : 'waiting';
  }
  if (terminal.status === 'running') return 'running';
  return 'idle';
}

function mapTaskToActivity(task: Task): AgentActivity {
  if (task.status === 'error') return 'exited';
  if (task.status === 'human_review') return 'waiting';
  const phase = task.executionProgress?.phase;
  if (!phase) return 'running';
  switch (phase) {
    case 'planning':             return 'reading';
    case 'coding':               return 'typing';
    case 'qa_review':            return 'reading';
    case 'qa_fixing':            return 'typing';
    case 'rate_limit_paused':
    case 'auth_failure_paused':  return 'waiting';
    case 'complete':             return 'idle';
    case 'failed':               return 'exited';
    default:                     return 'running';
  }
}

/** Task statuses that should appear in Pixel Office */
const ACTIVE_TASK_STATUSES = new Set<Task['status']>([
  'in_progress', 'ai_review', 'human_review', 'error',
]);

// ── Store ─────────────────────────────────────────────────────

export const usePixelOfficeStore = create<PixelOfficeState>((set, get) => ({
  agents: [],
  selectedAgentId: null,
  nextCharacterIndex: 0,
  settings: {
    zoom: 3,
    showGrid: false,
    soundEnabled: false,
    autoAssignSeats: true,
  },

  syncAll: (terminals: Terminal[], tasks: Task[]) => {
    const state = get();
    const existingMap = new Map(state.agents.map(a => [a.id, a]));
    let nextIdx = state.nextCharacterIndex;

    const newAgents: PixelAgent[] = [];
    let seatIndex = 0;

    // ── Terminal agents ───────────────────────────────
    for (const terminal of terminals.filter(t => t.status !== 'exited')) {
      const existing = existingMap.get(terminal.id);
      const shortTitle = terminal.title.length > 40 ? `${terminal.title.slice(0, 39)}…` : terminal.title;
      if (existing) {
        newAgents.push({
          ...existing,
          type: 'terminal',
          name: shortTitle,
          fullName: terminal.title,
          activity: mapTerminalToActivity(terminal),
          isClaudeMode: terminal.isClaudeMode,
          seatIndex: existing.seatIndex,
        });
      } else {
        newAgents.push({
          id: terminal.id,
          type: 'terminal',
          name: shortTitle,
          fullName: terminal.title,
          characterIndex: nextIdx++ % 6,
          activity: mapTerminalToActivity(terminal),
          seatIndex: seatIndex,
          isClaudeMode: terminal.isClaudeMode,
        });
        seatIndex++;
      }
    }

    // Update seatIndex counter past terminal agents
    const usedSeats = new Set(newAgents.map(a => a.seatIndex));
    seatIndex = Math.max(newAgents.length, ...Array.from(usedSeats)) + 1;

    // ── Task agents ───────────────────────────────────
    for (const task of tasks.filter(t => ACTIVE_TASK_STATUSES.has(t.status))) {
      const agentId = `task:${task.id}`;
      const existing = existingMap.get(agentId);
      const activity = mapTaskToActivity(task);
      const shortTitle = task.title.length > 40 ? `${task.title.slice(0, 39)}…` : task.title;

      if (existing) {
        newAgents.push({
          ...existing,
          type: 'task',
          name: shortTitle,
          fullName: task.title,
          activity,
          phase: task.executionProgress?.phase,
          progress: task.executionProgress?.overallProgress,
          currentSubtask: task.executionProgress?.currentSubtask,
          isClaudeMode: true,
          taskId: task.id,
        });
      } else {
        newAgents.push({
          id: agentId,
          type: 'task',
          name: shortTitle,
          fullName: task.title,
          characterIndex: nextIdx++ % 6,
          activity,
          seatIndex: seatIndex,
          isClaudeMode: true,
          taskId: task.id,
          taskName: task.title,
          phase: task.executionProgress?.phase,
          progress: task.executionProgress?.overallProgress,
          currentSubtask: task.executionProgress?.currentSubtask,
        });
        seatIndex++;
      }
    }

    set({ agents: newAgents, nextCharacterIndex: nextIdx });
  },

  /** @deprecated use syncAll */
  syncFromTerminals: (terminals: Terminal[]) => {
    get().syncAll(terminals, []);
  },

  selectAgent: (id) => set({ selectedAgentId: id }),

  updateSettings: (updates) =>
    set((state) => ({ settings: { ...state.settings, ...updates } })),

  setSpeechBubble: (agentId, text) =>
    set((state) => ({
      agents: state.agents.map(a => a.id === agentId ? { ...a, speechBubble: text } : a),
    })),
}));
