import { ipcMain } from 'electron';
import { documentationAgentService, type DocumentationAgentRequest } from '../documentation-agent-service';

export function registerDocumentationAgentHandlers(): void {
  ipcMain.handle('documentationAgent:generate', async (_event, request: DocumentationAgentRequest) => {
    try {
      await documentationAgentService.generateDocs(request);
      return { success: true };
    } catch (error) {
      console.error('[DocAgent] Generate error:', error);
      return { success: false, error: error instanceof Error ? error.message : 'Unknown error' };
    }
  });

  ipcMain.handle('documentationAgent:cancel', async () => {
    try {
      const cancelled = documentationAgentService.cancel();
      return { success: true, cancelled };
    } catch (error) {
      return { success: false, error: error instanceof Error ? error.message : 'Unknown error' };
    }
  });

  ipcMain.handle('documentationAgent:configure', async (_event, config: { pythonPath?: string; autoBuildSourcePath?: string }) => {
    try {
      documentationAgentService.configure(config.pythonPath, config.autoBuildSourcePath);
      return { success: true };
    } catch (error) {
      return { success: false, error: error instanceof Error ? error.message : 'Unknown error' };
    }
  });
}

export function setupDocumentationAgentEventForwarding(): void {
  documentationAgentService.on('status', (status: string) => {
    const mainWindow = global.mainWindow;
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('documentationAgent:status', status);
    }
  });

  documentationAgentService.on('stream-chunk', (chunk: string) => {
    const mainWindow = global.mainWindow;
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('documentationAgent:stream-chunk', chunk);
    }
  });

  documentationAgentService.on('error', (error: string) => {
    const mainWindow = global.mainWindow;
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('documentationAgent:error', error);
    }
  });

  documentationAgentService.on('complete', (result) => {
    const mainWindow = global.mainWindow;
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('documentationAgent:complete', result);
    }
  });
}
