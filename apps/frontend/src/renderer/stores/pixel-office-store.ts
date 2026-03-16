import { create } from 'zustand';
import type { Terminal } from './terminal-store';

// ── Types ────────────────────────────────────────────────────

export type AgentActivity = 'idle' | 'typing' | 'reading' | 'running' | 'waiting' | 'exited';

export interface PixelAgent {
  id: string;                  // Maps to terminal ID
  name: string;                // Terminal title
  characterIndex: number;      // Which character sprite to use (0-5)
  activity: AgentActivity;     // Current visual activity
  seatIndex: number;           // Which desk the agent sits at
  taskName?: string;           // Associated task name (for speech bubble)
  isClaudeMode: boolean;       // Whether in Claude mode
  speechBubble?: string;       // Text to show in speech bubble
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
  syncFromTerminals: (terminals: Terminal[]) => void;
  selectAgent: (id: string | null) => void;
  updateSettings: (updates: Partial<PixelOfficeSettings>) => void;
  setSpeechBubble: (agentId: string, text: string | undefined) => void;
}

/**
 * Map terminal status to pixel agent activity
 */
function mapTerminalToActivity(terminal: Terminal): AgentActivity {
  if (terminal.status === 'exited') return 'exited';
  if (terminal.isClaudeBusy) return 'typing';
  if (terminal.isClaudeMode && terminal.status === 'claude-active') {
    return terminal.isClaudeBusy ? 'typing' : 'waiting';
  }
  if (terminal.status === 'running') return 'running';
  return 'idle';
}

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

  syncFromTerminals: (terminals: Terminal[]) => {
    const state = get();
    const existingMap = new Map(state.agents.map(a => [a.id, a]));
    let nextIdx = state.nextCharacterIndex;

    const newAgents: PixelAgent[] = terminals
      .filter(t => t.status !== 'exited')
      .map((terminal, index) => {
        const existing = existingMap.get(terminal.id);
        if (existing) {
          return {
            ...existing,
            name: terminal.title,
            activity: mapTerminalToActivity(terminal),
            isClaudeMode: terminal.isClaudeMode,
          };
        }
        const charIdx = nextIdx % 6;
        nextIdx++;
        return {
          id: terminal.id,
          name: terminal.title,
          characterIndex: charIdx,
          activity: mapTerminalToActivity(terminal),
          seatIndex: index,
          isClaudeMode: terminal.isClaudeMode,
        };
      });

    set({ agents: newAgents, nextCharacterIndex: nextIdx });
  },

  selectAgent: (id) => set({ selectedAgentId: id }),

  updateSettings: (updates) =>
    set((state) => ({
      settings: { ...state.settings, ...updates },
    })),

  setSpeechBubble: (agentId, text) =>
    set((state) => ({
      agents: state.agents.map((a) =>
        a.id === agentId ? { ...a, speechBubble: text } : a
      ),
    })),
}));
