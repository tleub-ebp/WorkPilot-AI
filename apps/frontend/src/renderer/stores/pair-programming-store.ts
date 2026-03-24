/**
 * AI Pair Programming Store (Feature 10)
 *
 * Manages the state of the active pair programming session including:
 * - Session metadata (goal, dev scope, AI scope, status)
 * - Bidirectional chat messages between developer and AI
 * - AI action log (files created/modified)
 * - Streaming AI output
 * - Conflict warnings
 */

import { create } from 'zustand';
import type {
  PairSession,
  PairMessage,
  AiAction,
  PairStreamChunk,
  StartSessionParams,
} from '../../preload/api/modules/pair-programming-api';

// Re-export types for convenience
export type { PairSession, PairMessage, AiAction, StartSessionParams };

// ---------------------------------------------------------------------------
// Store types
// ---------------------------------------------------------------------------

export type PairStatus =
  | 'idle'
  | 'planning'
  | 'active'
  | 'paused'
  | 'completed'
  | 'error';

export interface ConflictWarning {
  id: string;
  filePath: string;
  message: string;
  timestamp: string;
}

interface PairProgrammingState {
  // Session
  session: PairSession | null;
  status: PairStatus;
  statusMessage: string;

  // Chat
  messages: PairMessage[];
  pendingMessage: string;
  streamingContent: string;

  // AI work log
  aiActions: AiAction[];

  // Conflicts
  conflicts: ConflictWarning[];

  // Actions
  setSession: (session: PairSession | null) => void;
  setStatus: (status: PairStatus, message?: string) => void;
  setPendingMessage: (msg: string) => void;
  addMessage: (message: PairMessage) => void;
  appendStreamContent: (content: string) => void;
  finalizeAiMessage: () => void;
  clearStreamContent: () => void;
  addAiAction: (action: AiAction) => void;
  addConflict: (filePath: string, message: string) => void;
  reset: () => void;
}

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

export const usePairProgrammingStore = create<PairProgrammingState>((set, get) => ({
  session: null,
  status: 'idle',
  statusMessage: '',
  messages: [],
  pendingMessage: '',
  streamingContent: '',
  aiActions: [],
  conflicts: [],

  setSession: (session) => set({ session }),

  setStatus: (status, message = '') =>
    set({
      status,
      statusMessage: message,
      session: get().session
        ? { ...get().session!, status: status === 'idle' ? get().session?.status : (status as PairSession['status']), updatedAt: new Date().toISOString() }
        : null,
    }),

  setPendingMessage: (pendingMessage) => set({ pendingMessage }),

  addMessage: (message) =>
    set((state) => ({ messages: [...state.messages, message] })),

  appendStreamContent: (content) =>
    set((state) => ({ streamingContent: state.streamingContent + content })),

  clearStreamContent: () => set({ streamingContent: '' }),

  finalizeAiMessage: () =>
    set((state) => {
      const content = state.streamingContent.trim();
      if (!content) return { streamingContent: '' };
      const aiMsg: PairMessage = {
        id: `msg_${Date.now()}`,
        role: 'ai',
        content,
        timestamp: new Date().toISOString(),
      };
      return {
        streamingContent: '',
        messages: [...state.messages, aiMsg],
      };
    }),

  addAiAction: (action) =>
    set((state) => ({ aiActions: [...state.aiActions, action] })),

  addConflict: (filePath, message) =>
    set((state) => ({
      conflicts: [
        ...state.conflicts,
        {
          id: `conflict_${Date.now()}`,
          filePath,
          message,
          timestamp: new Date().toISOString(),
        },
      ],
    })),

  reset: () =>
    set({
      session: null,
      status: 'idle',
      statusMessage: '',
      messages: [],
      pendingMessage: '',
      streamingContent: '',
      aiActions: [],
      conflicts: [],
    }),
}));

// ---------------------------------------------------------------------------
// Actions (IPC wrappers)
// ---------------------------------------------------------------------------

export async function startPairSession(params: StartSessionParams): Promise<void> {
  const store = usePairProgrammingStore.getState();
  store.reset();
  store.setStatus('planning', 'Starting pair programming session...');

  const result = await window.electronAPI.startPairSession(params);
  if (result.success && result.data) {
    store.setSession(result.data);
    store.setStatus('planning', 'Analyzing project and planning AI scope...');
  } else {
    store.setStatus('error', result.error || 'Failed to start session');
  }
}

export async function stopPairSession(projectId: string, sessionId: string): Promise<void> {
  await window.electronAPI.stopPairSession(projectId, sessionId);
  usePairProgrammingStore.getState().setStatus('completed', 'Session stopped.');
}

export function sendPairMessage(projectId: string, sessionId: string, message: string): void {
  const store = usePairProgrammingStore.getState();

  // Optimistically add user message to UI
  const userMsg: PairMessage = {
    id: `msg_${Date.now()}`,
    role: 'user',
    content: message,
    timestamp: new Date().toISOString(),
  };
  store.addMessage(userMsg);
  store.setPendingMessage('');

  // Send to main process
  window.electronAPI.sendPairMessage(projectId, sessionId, message);
}

export async function loadPairSession(projectId: string): Promise<void> {
  const result = await window.electronAPI.getPairSession(projectId);
  if (result.success && result.data) {
    const store = usePairProgrammingStore.getState();
    store.setSession(result.data);
    store.setStatus(result.data.status as PairStatus);
  }
}

// ---------------------------------------------------------------------------
// IPC listener setup — call once on component mount, cleanup on unmount
// ---------------------------------------------------------------------------

export function setupPairProgrammingListeners(projectId: string): () => void {
  const store = usePairProgrammingStore.getState;

  const unsubChunk = window.electronAPI.onPairStreamChunk(
    (pid: string, chunk: PairStreamChunk) => {
      if (pid !== projectId) return;
      switch (chunk.type) {
        case 'stream':
          if (chunk.content) store().appendStreamContent(chunk.content);
          break;
        case 'question':
          if (chunk.content) {
            // Finalize any ongoing stream first
            store().finalizeAiMessage();
            store().addMessage({
              id: `q_${Date.now()}`,
              role: 'ai',
              content: chunk.content,
              timestamp: new Date().toISOString(),
              isQuestion: true,
            });
          }
          break;
        case 'done':
          store().finalizeAiMessage();
          store().setStatus('completed', chunk.summary || 'Session completed.');
          break;
        case 'error':
          store().finalizeAiMessage();
          store().setStatus('error', chunk.message || 'An error occurred.');
          break;
      }
    }
  );

  const unsubStatus = window.electronAPI.onPairStatus(
    (pid: string, status: string, message: string) => {
      if (pid !== projectId) return;
      store().setStatus(status as PairStatus, message);
    }
  );

  const unsubAction = window.electronAPI.onPairAiAction(
    (pid: string, action: AiAction) => {
      if (pid !== projectId) return;
      store().addAiAction(action);
    }
  );

  const unsubConflict = window.electronAPI.onPairConflict(
    (pid: string, filePath: string, message: string) => {
      if (pid !== projectId) return;
      store().addConflict(filePath, message);
    }
  );

  const unsubError = window.electronAPI.onPairError(
    (pid: string, error: string) => {
      if (pid !== projectId) return;
      store().setStatus('error', error);
    }
  );

  const unsubComplete = window.electronAPI.onPairComplete(
    (pid: string, summary: string) => {
      if (pid !== projectId) return;
      store().finalizeAiMessage();
      store().setStatus('completed', summary);
    }
  );

  return () => {
    unsubChunk();
    unsubStatus();
    unsubAction();
    unsubConflict();
    unsubError();
    unsubComplete();
  };
}
