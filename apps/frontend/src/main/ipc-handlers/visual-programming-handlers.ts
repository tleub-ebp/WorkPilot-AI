import { ipcMain } from 'electron';
import { visualProgrammingService, type VisualProgrammingRequest } from '../visual-programming-service';

export function registerVisualProgrammingHandlers(getMainWindow: () => import('electron').BrowserWindow | null): void {
  ipcMain.handle('visualProgramming:run', async (_event, request: VisualProgrammingRequest) => {
    try {
      await visualProgrammingService.run(request);
      return { success: true };
    } catch (error) {
      console.error('[VisualProg] Run error:', error);
      return { success: false, error: error instanceof Error ? error.message : 'Unknown error' };
    }
  });

  ipcMain.handle('visualProgramming:cancel', async () => {
    try {
      const cancelled = visualProgrammingService.cancel();
      return { success: true, cancelled };
    } catch (error) {
      return { success: false, error: error instanceof Error ? error.message : 'Unknown error' };
    }
  });

  ipcMain.handle('visualProgramming:configure', async (_event, config: { pythonPath?: string; sourcePath?: string }) => {
    try {
      visualProgrammingService.configure(config.pythonPath, config.sourcePath);
      return { success: true };
    } catch (error) {
      return { success: false, error: error instanceof Error ? error.message : 'Unknown error' };
    }
  });
}

export function setupVisualProgrammingEventForwarding(getMainWindow: () => import('electron').BrowserWindow | null): void {
  visualProgrammingService.on('status', (msg: string) => {
    const win = getMainWindow();
    if (win && !win.isDestroyed()) {
      win.webContents.send('visualProgramming:status', msg);
    }
  });

  visualProgrammingService.on('error', (err: string) => {
    const win = getMainWindow();
    if (win && !win.isDestroyed()) {
      win.webContents.send('visualProgramming:error', err);
    }
  });

  visualProgrammingService.on('complete', (result: unknown) => {
    const win = getMainWindow();
    if (win && !win.isDestroyed()) {
      win.webContents.send('visualProgramming:complete', result);
    }
  });
}
