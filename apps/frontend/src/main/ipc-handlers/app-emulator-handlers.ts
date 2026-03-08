import { ipcMain, type BrowserWindow } from 'electron';
import { appEmulatorService, type AppEmulatorConfig } from '../app-emulator-service';

/**
 * Register App Emulator IPC handlers and event forwarding.
 */
export function registerAppEmulatorHandlers(getMainWindow: () => BrowserWindow | null): void {
  // Detect project type
  ipcMain.handle('app-emulator:detect', async (_event, { projectDir }: { projectDir: string }) => {
    try {
      const config = await appEmulatorService.detectProject(projectDir);
      return { success: true, data: config };
    } catch (error: unknown) {
      return { success: false, error: error instanceof Error ? error.message : String(error) };
    }
  });

  // Start dev server
  ipcMain.handle('app-emulator:start', async (_event, { config }: { config: AppEmulatorConfig }) => {
    try {
      await appEmulatorService.startServer(config);
      return { success: true };
    } catch (error: unknown) {
      return { success: false, error: error instanceof Error ? error.message : String(error) };
    }
  });

  // Stop dev server
  ipcMain.handle('app-emulator:stop', async () => {
    appEmulatorService.stopServer();
    return { success: true };
  });

  // Get current status
  ipcMain.handle('app-emulator:status', async () => {
    return {
      success: true,
      data: {
        running: appEmulatorService.isRunning(),
        url: appEmulatorService.getUrl(),
        config: appEmulatorService.getConfig(),
      },
    };
  });

  // Forward service events to renderer
  const sendToRenderer = (channel: string, ...args: unknown[]) => {
    const mainWindow = getMainWindow();
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send(channel, ...args);
    }
  };

  appEmulatorService.on('status', (status: string) => {
    sendToRenderer('app-emulator:status-update', status);
  });

  appEmulatorService.on('ready', (url: string) => {
    sendToRenderer('app-emulator:ready', url);
  });

  appEmulatorService.on('output', (line: string) => {
    sendToRenderer('app-emulator:output', line);
  });

  appEmulatorService.on('error', (error: string) => {
    sendToRenderer('app-emulator:error', error);
  });

  appEmulatorService.on('stopped', () => {
    sendToRenderer('app-emulator:stopped');
  });

  appEmulatorService.on('config', (config: AppEmulatorConfig) => {
    sendToRenderer('app-emulator:config', config);
  });
}
