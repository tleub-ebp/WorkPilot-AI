import { ipcMain } from 'electron';
import { codePlaygroundService, type PlaygroundResult } from '../code-playground-service';

/**
 * Setup IPC handlers for code playground functionality
 */
export function setupCodePlaygroundHandlers() {
  // Handle playground generation requests
  ipcMain.handle('code-playground:start', async (_, { projectId, idea, playgroundType, sandboxType }) => {
    try {
      // Get project directory from project store or similar
      const projectDir = getProjectDirectory(projectId);
      if (!projectDir) {
        throw new Error('Project not found');
      }

      await codePlaygroundService.generate({
        projectDir,
        idea,
        playgroundType,
        sandboxType,
      });
    } catch (error) {
      console.error('[CodePlayground] Error starting playground:', error);
      throw error;
    }
  });

  // Handle cancellation requests
  ipcMain.handle('code-playground:cancel', () => {
    return codePlaygroundService.cancel();
  });

  // Forward service events to renderer
  codePlaygroundService.on('status', (status: string) => {
    ipcMain.emit('code-playground:status', null, status);
  });

  codePlaygroundService.on('stream-chunk', (chunk: string) => {
    ipcMain.emit('code-playground:stream-chunk', null, chunk);
  });

  codePlaygroundService.on('error', (error: string) => {
    ipcMain.emit('code-playground:error', null, error);
  });

  codePlaygroundService.on('complete', (result: PlaygroundResult) => {
    ipcMain.emit('code-playground:complete', null, result);
  });
}

/**
 * Get project directory by ID
 * This should be integrated with the existing project store
 */
function getProjectDirectory(projectId: string): string | null {
  // TODO: Integrate with existing project management
  // For now, return a placeholder or current working directory
  return process.cwd(); // Placeholder
}
