import { create } from 'zustand';
import type { Terminal } from './terminal-store';
import type { Task, ExecutionPhase } from '../../shared/types/task';
import type { SubtaskNode, SubtaskState as SwarmSubtaskState, Wave } from '../../shared/types/swarm';

// ── Types ────────────────────────────────────────────────────

export type AgentActivity = 'idle' | 'typing' | 'reading' | 'running' | 'waiting' | 'pending' | 'exited';
export type PixelAgentType = 'terminal' | 'task' | 'swarm';

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
  // Waiting queue fields
  waitingIndex?: number;       // Position in the waiting queue (pending/planning tasks only)
  // Swarm fields
  swarmWaveIndex?: number;     // Wave this agent belongs to (swarm mode)
  swarmSubtaskId?: string;     // Subtask ID (swarm mode)
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
  /** Sync swarm agents from wave/subtask data */
  syncSwarmAgents: (nodes: Record<string, SubtaskNode>, currentWave: number) => void;
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
  if (task.status === 'backlog') return 'pending';
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
  'in_progress', 'ai_review', 'human_review', 'error', 'backlog',
]);

/** Map swarm subtask state to pixel agent activity */
function mapSwarmStateToActivity(state: SwarmSubtaskState): AgentActivity {
  switch (state) {
    case 'pending':
    case 'queued':   return 'pending';
    case 'running':  return 'typing';
    case 'completed': return 'idle';
    case 'failed':   return 'exited';
    case 'retrying': return 'running';
    case 'skipped':  return 'exited';
    default:         return 'waiting';
  }
}

// ── Agent builder helpers ─────────────────────────────────────

function shortTitle(title: string): string {
  return title.length > 40 ? `${title.slice(0, 39)}…` : title;
}

function buildTerminalAgent(
  terminal: Terminal,
  existing: PixelAgent | undefined,
  nextIdx: number,
  seatIndex: number,
): PixelAgent {
  const name = shortTitle(terminal.title);
  const activity = mapTerminalToActivity(terminal);
  if (existing) {
    return { ...existing, type: 'terminal', name, fullName: terminal.title, activity, isClaudeMode: terminal.isClaudeMode, seatIndex: existing.seatIndex };
  }
  return { id: terminal.id, type: 'terminal', name, fullName: terminal.title, characterIndex: nextIdx % 6, activity, seatIndex, isClaudeMode: terminal.isClaudeMode };
}

function buildTaskAgent(
  task: Task,
  existing: PixelAgent | undefined,
  nextIdx: number,
  seatIndex: number,
  waitingIdx: number,
): PixelAgent {
  const agentId = `task:${task.id}`;
  const name = shortTitle(task.title);
  const activity = mapTaskToActivity(task);
  const isPending = activity === 'pending';
  const progress = { phase: task.executionProgress?.phase, progress: task.executionProgress?.overallProgress, currentSubtask: task.executionProgress?.currentSubtask };

  if (existing) {
    return {
      ...existing,
      type: 'task', name, fullName: task.title,
      activity, ...progress,
      isClaudeMode: !isPending, taskId: task.id,
      ...(isPending ? { seatIndex: -1, waitingIndex: waitingIdx } : {}),
    };
  }
  return {
    id: agentId, type: 'task', name, fullName: task.title,
    characterIndex: nextIdx % 6, activity,
    seatIndex: isPending ? -1 : seatIndex,
    waitingIndex: isPending ? waitingIdx : undefined,
    isClaudeMode: !isPending, taskId: task.id, taskName: task.title,
    ...progress,
  };
}

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
      const agent = buildTerminalAgent(terminal, existingMap.get(terminal.id), nextIdx, seatIndex);
      newAgents.push(agent);
      if (!existingMap.has(terminal.id)) { nextIdx++; seatIndex++; }
    }

    // Advance seatIndex past all terminal seats
    const usedSeats = new Set(newAgents.map(a => a.seatIndex));
    seatIndex = Math.max(newAgents.length, ...Array.from(usedSeats)) + 1;

    // ── Task agents ───────────────────────────────────
    let waitingIdx = 0;
    for (const task of tasks.filter(t => ACTIVE_TASK_STATUSES.has(t.status))) {
      const agentId = `task:${task.id}`;
      const agent = buildTaskAgent(task, existingMap.get(agentId), nextIdx, seatIndex, waitingIdx);
      newAgents.push(agent);
      if (!existingMap.has(agentId)) nextIdx++;
      if (agent.activity === 'pending') { waitingIdx++; } else if (!existingMap.has(agentId)) { seatIndex++; }
    }

    set({ agents: newAgents, nextCharacterIndex: nextIdx });
  },

  syncSwarmAgents: (nodes: Record<string, SubtaskNode>, currentWave: number) => {
    const state = get();
    // Keep non-swarm agents, replace swarm agents
    const nonSwarmAgents = state.agents.filter(a => a.type !== 'swarm');
    const existingSwarmMap = new Map(
      state.agents.filter(a => a.type === 'swarm').map(a => [a.id, a]),
    );
    let nextIdx = state.nextCharacterIndex;
    let seatIndex = nonSwarmAgents.length;
    let waitingIdx = 0;
    const swarmAgents: PixelAgent[] = [];

    for (const [subtaskId, node] of Object.entries(nodes)) {
      const agentId = `swarm:${subtaskId}`;
      const existing = existingSwarmMap.get(agentId);
      const activity = mapSwarmStateToActivity(node.state);
      const isPending = activity === 'pending';
      const name = shortTitle(node.description || subtaskId);

      if (existing) {
        swarmAgents.push({
          ...existing,
          name,
          fullName: node.description || subtaskId,
          activity,
          swarmWaveIndex: node.waveIndex,
          swarmSubtaskId: subtaskId,
          ...(isPending ? { seatIndex: -1, waitingIndex: waitingIdx } : {}),
        });
      } else {
        swarmAgents.push({
          id: agentId,
          type: 'swarm',
          name,
          fullName: node.description || subtaskId,
          characterIndex: nextIdx % 6,
          activity,
          seatIndex: isPending ? -1 : seatIndex,
          waitingIndex: isPending ? waitingIdx : undefined,
          isClaudeMode: true,
          swarmWaveIndex: node.waveIndex,
          swarmSubtaskId: subtaskId,
        });
        nextIdx++;
        if (!isPending) seatIndex++;
      }

      if (isPending) waitingIdx++;
    }

    set({
      agents: [...nonSwarmAgents, ...swarmAgents],
      nextCharacterIndex: nextIdx,
    });
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
