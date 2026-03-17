import { ipcMain } from 'electron';
import { architectureVisualizerService, type ArchitectureVisualizerRequest } from '../architecture-visualizer-service';

export function registerArchitectureVisualizerHandlers(): void {
  ipcMain.handle('architectureVisualizer:generate', async (_event, request: ArchitectureVisualizerRequest) => {
    try {
      await architectureVisualizerService.generate(request);
      return { success: true };
    } catch (error) {
      console.error('[ArchViz] Generate error:', error);
      return { success: false, error: error instanceof Error ? error.message : 'Unknown error' };
    }
  });

  ipcMain.handle('architectureVisualizer:cancel', async () => {
    try {
      const cancelled = architectureVisualizerService.cancel();
      return { success: true, cancelled };
    } catch (error) {
      return { success: false, error: error instanceof Error ? error.message : 'Unknown error' };
    }
  });

  ipcMain.handle('architectureVisualizer:configure', async (_event, config: { pythonPath?: string; autoBuildSourcePath?: string }) => {
    try {
      architectureVisualizerService.configure(config.pythonPath, config.autoBuildSourcePath);
      return { success: true };
    } catch (error) {
      return { success: false, error: error instanceof Error ? error.message : 'Unknown error' };
    }
  });
}

export function setupArchitectureVisualizerEventForwarding(): void {
  architectureVisualizerService.on('status', (status: string) => {
    const mainWindow = global.mainWindow;
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('architectureVisualizer:status', status);
    }
  });

  architectureVisualizerService.on('stream-chunk', (chunk: string) => {
    const mainWindow = global.mainWindow;
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('architectureVisualizer:stream-chunk', chunk);
    }
  });

  architectureVisualizerService.on('error', (error: string) => {
    const mainWindow = global.mainWindow;
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('architectureVisualizer:error', error);
    }
  });

  architectureVisualizerService.on('complete', (result) => {
    const mainWindow = global.mainWindow;
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('architectureVisualizer:complete', result);
    }
  });
}
