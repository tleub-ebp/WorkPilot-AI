/**
 * Code Migration Agent API module
 */

export interface CodeMigrationRequest {
  projectDir: string;
  migrationDescription: string;
  dryRun?: boolean;
  batchSize?: number;
  model?: string;
  thinkingLevel?: string;
}

export interface CodeMigrationResult {
  migration_description: string;
  dry_run: boolean;
  summary: { files_modified: number; plan_status: string; execution_status: string };
}

export interface CodeMigrationAPI {
  startCodeMigration: (request: CodeMigrationRequest) => Promise<{ success: boolean; error?: string }>;
  cancelCodeMigration: () => Promise<{ success: boolean; cancelled: boolean; error?: string }>;
  configureCodeMigration: (config: { pythonPath?: string }) => Promise<{ success: boolean; error?: string }>;
  onCodeMigrationStatus: (callback: (status: string) => void) => () => void;
  onCodeMigrationStreamChunk: (callback: (chunk: string) => void) => () => void;
  onCodeMigrationError: (callback: (error: string) => void) => () => void;
  onCodeMigrationComplete: (callback: (result: CodeMigrationResult) => void) => () => void;
  onCodeMigrationTaskProgress: (callback: (progress: { current: number; total: number; file: string }) => void) => () => void;
}

export function createCodeMigrationAPI(): CodeMigrationAPI {
  return {
    startCodeMigration: (request) =>
      window.electronAPI.invoke('codeMigration:start', request),
    cancelCodeMigration: () =>
      window.electronAPI.invoke('codeMigration:cancel'),
    configureCodeMigration: (config) =>
      window.electronAPI.invoke('codeMigration:configure', config),
    onCodeMigrationStatus: (callback) =>
      window.electronAPI.on('codeMigration:status', callback),
    onCodeMigrationStreamChunk: (callback) =>
      window.electronAPI.on('codeMigration:streamChunk', callback),
    onCodeMigrationError: (callback) =>
      window.electronAPI.on('codeMigration:error', callback),
    onCodeMigrationComplete: (callback) =>
      window.electronAPI.on('codeMigration:complete', callback),
    onCodeMigrationTaskProgress: (callback) =>
      window.electronAPI.on('codeMigration:taskProgress', callback),
  };
}
