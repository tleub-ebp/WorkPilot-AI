import { ipcMain } from 'electron';
import type { BrowserWindow } from 'electron';
import { pipelineGeneratorService, type PipelineGeneratorRequest, type PipelineGeneratorResult } from '../pipeline-generator-service';

export function registerPipelineGeneratorHandlers(): void {
  ipcMain.handle('pipelineGenerator:generate', async (_event, request: PipelineGeneratorRequest) => {
    try {
      await pipelineGeneratorService.generate(request);
      return { success: true };
    } catch (error) {
      console.error('[PipelineGenerator] Generate error:', error);
      return { success: false, error: error instanceof Error ? error.message : 'Unknown error' };
    }
  });

  ipcMain.handle('pipelineGenerator:cancel', async () => {
    try {
      const cancelled = pipelineGeneratorService.cancel();
      return { success: true, cancelled };
    } catch (error) {
      return { success: false, error: error instanceof Error ? error.message : 'Unknown error' };
    }
  });

  ipcMain.handle('pipelineGenerator:configure', async (_event, config: { pythonPath?: string; autoBuildSourcePath?: string }) => {
    try {
      pipelineGeneratorService.configure(config.pythonPath, config.autoBuildSourcePath);
      return { success: true };
    } catch (error) {
      return { success: false, error: error instanceof Error ? error.message : 'Unknown error' };
    }
  });
}

export function setupPipelineGeneratorEventForwarding(getMainWindow: () => BrowserWindow | null): void {
  pipelineGeneratorService.on('status', (status: string) => {
    const mainWindow = getMainWindow();
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('pipelineGenerator:status', status);
    }
  });

  pipelineGeneratorService.on('stream-chunk', (chunk: string) => {
    const mainWindow = getMainWindow();
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('pipelineGenerator:streamChunk', chunk);
    }
  });

  pipelineGeneratorService.on('error', (error: string) => {
    const mainWindow = getMainWindow();
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('pipelineGenerator:error', error);
    }
  });

  pipelineGeneratorService.on('complete', (result: PipelineGeneratorResult) => {
    const mainWindow = getMainWindow();
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('pipelineGenerator:complete', result);
    }
  });
}
