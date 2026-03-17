import { ipcMain } from 'electron';
import { performanceProfilerService, type PerformanceProfilerRequest } from '../performance-profiler-service';

export function registerPerformanceProfilerHandlers(): void {
  ipcMain.handle('performanceProfiler:start', async (_event, request: PerformanceProfilerRequest) => {
    try {
      await performanceProfilerService.startProfiling(request);
      return { success: true };
    } catch (error) {
      console.error('[PerfProfiler] Start error:', error);
      return { success: false, error: error instanceof Error ? error.message : 'Unknown error' };
    }
  });

  ipcMain.handle('performanceProfiler:cancel', async () => {
    try {
      const cancelled = performanceProfilerService.cancel();
      return { success: true, cancelled };
    } catch (error) {
      return { success: false, error: error instanceof Error ? error.message : 'Unknown error' };
    }
  });

  ipcMain.handle('performanceProfiler:configure', async (_event, config: { pythonPath?: string; autoBuildSourcePath?: string }) => {
    try {
      performanceProfilerService.configure(config.pythonPath, config.autoBuildSourcePath);
      return { success: true };
    } catch (error) {
      return { success: false, error: error instanceof Error ? error.message : 'Unknown error' };
    }
  });
}

export function setupPerformanceProfilerEventForwarding(): void {
  performanceProfilerService.on('status', (status: string) => {
    const mainWindow = global.mainWindow;
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('performanceProfiler:status', status);
    }
  });

  performanceProfilerService.on('stream-chunk', (chunk: string) => {
    const mainWindow = global.mainWindow;
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('performanceProfiler:stream-chunk', chunk);
    }
  });

  performanceProfilerService.on('error', (error: string) => {
    const mainWindow = global.mainWindow;
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('performanceProfiler:error', error);
    }
  });

  performanceProfilerService.on('complete', (result) => {
    const mainWindow = global.mainWindow;
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('performanceProfiler:complete', result);
    }
  });

  performanceProfilerService.on('implementation-complete', (result) => {
    const mainWindow = global.mainWindow;
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('performanceProfiler:implementation-complete', result);
    }
  });
}
