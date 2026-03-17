import { createContext, useContext, useEffect, useState, useCallback, ReactNode, useMemo } from 'react';
import type { CopilotCliVersionInfo } from '@shared/types';

interface ClaudeVersionInfo {
  installed?: string;
  latest?: string;
  isOutdated?: boolean;
  path?: string;
}

interface CodexVersionInfo {
  installed?: string;
  latest?: string;
  isOutdated?: boolean;
  path?: string;
}

interface CliStatusData {
  copilot: {
    status: 'loading' | 'installed' | 'outdated' | 'not-found' | 'gh-missing' | 'error';
    versionInfo: CopilotCliVersionInfo | null;
    lastChecked: Date | null;
    authStatus: { authenticated: boolean; username?: string } | null;
  };
  claude: {
    status: 'loading' | 'installed' | 'outdated' | 'not-found' | 'error';
    versionInfo: ClaudeVersionInfo | null;
    lastChecked: Date | null;
  };
  codex: {
    status: 'loading' | 'installed' | 'outdated' | 'not-found' | 'error';
    versionInfo: CodexVersionInfo | null;
    lastChecked: Date | null;
  };
}

interface CliStatusContextType {
  readonly data: CliStatusData;
  refreshAll: () => Promise<void>;
  refreshCopilot: () => Promise<void>;
  refreshClaude: () => Promise<void>;
  refreshCodex: () => Promise<void>;
  readonly isRefreshing: boolean;
}

const CliStatusContext = createContext<CliStatusContextType | undefined>(undefined);

const CHECK_INTERVAL_MS = 24 * 60 * 60 * 1000; // 24 hours

export function CliStatusProvider({ children }: { readonly children: ReactNode }) {
  const [data, setData] = useState<CliStatusData>({
    copilot: { status: 'loading', versionInfo: null, lastChecked: null, authStatus: null },
    claude: { status: 'loading', versionInfo: null, lastChecked: null },
    codex: { status: 'loading', versionInfo: null, lastChecked: null },
  });
  const [isRefreshing, setIsRefreshing] = useState(false);

  const checkCopilotVersion = useCallback(async () => {
    try {
      if (!globalThis.electronAPI?.checkCopilotCliVersion) return;

      const result = await globalThis.electronAPI.checkCopilotCliVersion();
      
      if (result.success && result.data) {
        let status: CliStatusData['copilot']['status'] = 'installed';
        if (!result.data.ghVersion && !result.data.installed) {
          status = 'gh-missing';
        } else if (!result.data.installed) {
          status = 'not-found';
        } else if (result.data.isOutdated) {
          status = 'outdated';
        }

        setData(prev => ({
          ...prev,
          copilot: {
            ...prev.copilot,
            status,
            versionInfo: result.data,
            lastChecked: new Date(),
          }
        }));
      } else {
        setData(prev => ({
          ...prev,
          copilot: { ...prev.copilot, status: 'error' }
        }));
      }
    } catch (err) {
      console.error("Failed to check Copilot CLI version:", err);
      setData(prev => ({
        ...prev,
        copilot: { ...prev.copilot, status: 'error' }
      }));
    }
  }, []);

  const checkClaudeVersion = useCallback(async () => {
    try {
      if (!globalThis.electronAPI?.checkClaudeCodeVersion) return;

      const result = await globalThis.electronAPI.checkClaudeCodeVersion();
      
      if (result.success && result.data) {
        let status: CliStatusData['claude']['status'] = 'installed';
        if (!result.data.installed) {
          status = 'not-found';
        } else if (result.data.isOutdated) {
          status = 'outdated';
        }

        setData(prev => ({
          ...prev,
          claude: {
            ...prev.claude,
            status,
            versionInfo: result.data as ClaudeVersionInfo,
            lastChecked: new Date(),
          }
        }));
      } else {
        setData(prev => ({
          ...prev,
          claude: { ...prev.claude, status: 'error' }
        }));
      }
    } catch (err) {
      console.error("Failed to check Claude Code version:", err);
      setData(prev => ({
        ...prev,
        claude: { ...prev.claude, status: 'error' }
      }));
    }
  }, []);

  const checkCodexVersion = useCallback(async () => {
    try {
      if (!globalThis.electronAPI?.checkOpenAICodexOAuth) return;

      const result = await globalThis.electronAPI.checkOpenAICodexOAuth();

      const status: CliStatusData['codex']['status'] = result.isAuthenticated ? 'installed' : 'not-found';
      setData(prev => ({
        ...prev,
        codex: {
          ...prev.codex,
          status,
          versionInfo: result.isAuthenticated
            ? { installed: result.profileName ?? 'OpenAI Codex CLI' }
            : null,
          lastChecked: new Date(),
        }
      }));
    } catch (err) {
      console.error("Failed to check Codex CLI version:", err);
      setData(prev => ({
        ...prev,
        codex: { ...prev.codex, status: 'error' }
      }));
    }
  }, []);

  const checkCopilotAuth = useCallback(async () => {
    try {
      if (!globalThis.electronAPI?.checkCopilotAuth) return;
      const result = await globalThis.electronAPI.checkCopilotAuth();
      if (result.success && result.data) {
        setData(prev => ({
          ...prev,
          copilot: { ...prev.copilot, authStatus: result.data }
        }));
      }
    } catch (err) {
      console.error("Failed to check Copilot auth:", err);
    }
  }, []);

  const refreshAll = useCallback(async () => {
    setIsRefreshing(true);
    await Promise.all([
      checkCopilotVersion(),
      checkClaudeVersion(),
      checkCodexVersion(),
      checkCopilotAuth(),
    ]);
    setIsRefreshing(false);
  }, [checkCopilotVersion, checkClaudeVersion, checkCodexVersion, checkCopilotAuth]);

  const refreshCopilot = useCallback(async () => {
    await Promise.all([checkCopilotVersion(), checkCopilotAuth()]);
  }, [checkCopilotVersion, checkCopilotAuth]);

  const refreshClaude = useCallback(async () => {
    await checkClaudeVersion();
  }, [checkClaudeVersion]);

  const refreshCodex = useCallback(async () => {
    await checkCodexVersion();
  }, [checkCodexVersion]);

  // Initial check and periodic re-check
  useEffect(() => {
    refreshAll();

    const interval = setInterval(() => {
      refreshAll();
    }, CHECK_INTERVAL_MS);

    return () => clearInterval(interval);
  }, [refreshAll]);

  const value = useMemo<CliStatusContextType>(() => ({
    data,
    refreshAll,
    refreshCopilot,
    refreshClaude,
    refreshCodex,
    isRefreshing,
  }), [data, refreshAll, refreshCopilot, refreshClaude, refreshCodex, isRefreshing]);

  return (
    <CliStatusContext.Provider value={value}>
      {children}
    </CliStatusContext.Provider>
  );
}

export function useCliStatus() {
  const context = useContext(CliStatusContext);
  if (context === undefined) {
    throw new Error('useCliStatus must be used within a CliStatusProvider');
  }
  return context;
}
