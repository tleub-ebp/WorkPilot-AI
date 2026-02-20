import { create } from 'zustand';

/**
 * Loading domains represent distinct areas of the application
 * that can independently be in a loading state.
 */
export type LoadingDomain =
  | 'tasks'
  | 'projects'
  | 'terminals'
  | 'settings'
  | 'providers'
  | 'roadmap'
  | 'insights'
  | 'ideation'
  | 'github-issues'
  | 'gitlab-issues'
  | 'github-prs'
  | 'gitlab-merge-requests'
  | 'context';

interface LoadingState {
  /** Map of domain -> loading status */
  domains: Record<string, boolean>;
  /** Map of domain -> optional progress (0-100) */
  progress: Record<string, number>;
  /** Map of domain -> optional message */
  messages: Record<string, string>;

  // Actions
  startLoading: (domain: LoadingDomain, message?: string) => void;
  stopLoading: (domain: LoadingDomain) => void;
  setProgress: (domain: LoadingDomain, value: number, message?: string) => void;
  resetDomain: (domain: LoadingDomain) => void;
  resetAll: () => void;

  // Selectors
  isLoading: (domain: LoadingDomain) => boolean;
  isAnyLoading: () => boolean;
  getProgress: (domain: LoadingDomain) => number;
  getMessage: (domain: LoadingDomain) => string | undefined;
}

export const useLoadingStore = create<LoadingState>((set, get) => ({
  domains: {},
  progress: {},
  messages: {},

  startLoading: (domain, message) =>
    set((state) => ({
      domains: { ...state.domains, [domain]: true },
      messages: message
        ? { ...state.messages, [domain]: message }
        : state.messages,
    })),

  stopLoading: (domain) =>
    set((state) => {
      const { [domain]: _, ...restDomains } = state.domains;
      const { [domain]: __, ...restProgress } = state.progress;
      const { [domain]: ___, ...restMessages } = state.messages;
      return {
        domains: restDomains,
        progress: restProgress,
        messages: restMessages,
      };
    }),

  setProgress: (domain, value, message) =>
    set((state) => ({
      progress: { ...state.progress, [domain]: Math.max(0, Math.min(100, value)) },
      messages: message
        ? { ...state.messages, [domain]: message }
        : state.messages,
    })),

  resetDomain: (domain) =>
    set((state) => {
      const { [domain]: _, ...restDomains } = state.domains;
      const { [domain]: __, ...restProgress } = state.progress;
      const { [domain]: ___, ...restMessages } = state.messages;
      return {
        domains: restDomains,
        progress: restProgress,
        messages: restMessages,
      };
    }),

  resetAll: () => set({ domains: {}, progress: {}, messages: {} }),

  isLoading: (domain) => !!get().domains[domain],
  isAnyLoading: () => Object.values(get().domains).some(Boolean),
  getProgress: (domain) => get().progress[domain] ?? 0,
  getMessage: (domain) => get().messages[domain],
}));
