/**
 * Mock implementation for terminal operations
 */

export const terminalMock = {
  createTerminal: async () => {
    console.warn('[Browser Mock] createTerminal called');
    return { success: true };
  },

  destroyTerminal: async () => {
    console.warn('[Browser Mock] destroyTerminal called');
    return { success: true };
  },

  sendTerminalInput: () => {
    console.warn('[Browser Mock] sendTerminalInput called');
  },

  resizeTerminal: async () => {
    console.warn('[Browser Mock] resizeTerminal called');
    return { success: true, data: { success: true } };
  },

  invokeClaudeInTerminal: () => {
    console.warn('[Browser Mock] invokeClaudeInTerminal called');
  },

  generateTerminalName: async () => ({
    success: true,
    data: 'Mock Terminal'
  }),

  setTerminalTitle: () => {
    console.warn('[Browser Mock] setTerminalTitle called');
  },

  setTerminalWorktreeConfig: () => {
    console.warn('[Browser Mock] setTerminalWorktreeConfig called');
  },

  // Terminal session management
  getTerminalSessions: async () => ({
    success: true,
    data: []
  }),

  restoreTerminalSession: async () => ({
    success: true,
    data: {
      success: true,
      terminalId: 'restored-terminal'
    }
  }),

  clearTerminalSessions: async () => ({ success: true }),

  resumeClaudeInTerminal: () => {
    console.warn('[Browser Mock] resumeClaudeInTerminal called');
  },

  activateDeferredClaudeResume: () => {
    console.warn('[Browser Mock] activateDeferredClaudeResume called');
  },

  getTerminalSessionDates: async () => ({
    success: true,
    data: []
  }),

  getTerminalSessionsForDate: async () => ({
    success: true,
    data: []
  }),

  restoreTerminalSessionsFromDate: async () => ({
    success: true,
    data: {
      restored: 0,
      failed: 0,
      sessions: []
    }
  }),

  saveTerminalBuffer: async () => { /* noop */ },

  checkTerminalPtyAlive: async () => ({
    success: true,
    data: { alive: false }
  }),

  updateTerminalDisplayOrders: async () => ({
    success: true
  }),

  // Terminal Event Listeners (no-op in browser)
  onTerminalOutput: () => () => { /* noop */ },
  onTerminalExit: () => () => { /* noop */ },
  onTerminalTitleChange: () => () => { /* noop */ },
  onTerminalWorktreeConfigChange: () => () => { /* noop */ },
  onTerminalClaudeSession: () => () => { /* noop */ },
  onTerminalRateLimit: () => () => { /* noop */ },
  onTerminalOAuthToken: () => () => { /* noop */ },
  onTerminalAuthCreated: () => () => { /* noop */ },
  onTerminalClaudeBusy: () => () => { /* noop */ },
  onTerminalClaudeExit: () => () => { /* noop */ },
  onTerminalOnboardingComplete: () => () => { /* noop */ },
  onTerminalPendingResume: () => () => { /* noop */ },
  onTerminalProfileChanged: () => () => { /* noop */ },
  onTerminalOAuthCodeNeeded: () => () => { /* noop */ },

  // OAuth code submission
  submitOAuthCode: async () => ({
    success: true
  })
};
