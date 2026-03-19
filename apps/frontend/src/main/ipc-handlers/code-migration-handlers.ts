import { ipcMain } from 'electron';
import { codeMigrationService, type CodeMigrationRequest } from '../code-migration-service';

export function registerCodeMigrationHandlers(): void {
  ipcMain.handle('codeMigration:start', async (_event, request: CodeMigrationRequest) => {
    try {
      await codeMigrationService.startMigration(request);
      return { success: true };
    } catch (error) {
      console.error('[CodeMigration] Start error:', error);
      return { success: false, error: error instanceof Error ? error.message : 'Unknown error' };
    }
  });

  ipcMain.handle('codeMigration:cancel', async () => {
    try {
      const cancelled = codeMigrationService.cancel();
      return { success: true, cancelled };
    } catch (error) {
      return { success: false, error: error instanceof Error ? error.message : 'Unknown error' };
    }
  });

  ipcMain.handle('codeMigration:configure', async (_event, config: { pythonPath?: string; autoBuildSourcePath?: string }) => {
    try {
      codeMigrationService.configure(config.pythonPath, config.autoBuildSourcePath);
      return { success: true };
    } catch (error) {
      return { success: false, error: error instanceof Error ? error.message : 'Unknown error' };
    }
  });
}

export function setupCodeMigrationEventForwarding(): void {
  codeMigrationService.on('status', (status: string) => {
    const mainWindow = globalThis.mainWindow;
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('codeMigration:status', status);
    }
  });

  codeMigrationService.on('stream-chunk', (chunk: string) => {
    const mainWindow = globalThis.mainWindow;
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('codeMigration:stream-chunk', chunk);
    }
  });

  codeMigrationService.on('error', (error: string) => {
    const mainWindow = globalThis.mainWindow;
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('codeMigration:error', error);
    }
  });

  codeMigrationService.on('complete', (result) => {
    const mainWindow = globalThis.mainWindow;
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('codeMigration:complete', result);
    }
  });

  codeMigrationService.on('task-progress', (progress) => {
    const mainWindow = globalThis.mainWindow;
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('codeMigration:task-progress', progress);
    }
  });
}
