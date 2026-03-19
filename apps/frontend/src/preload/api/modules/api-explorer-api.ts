import { ipcRenderer } from 'electron';
import { IPC_CHANNELS } from '../../../shared/constants';

export interface ApiExplorerAPI {
  scanProjectRoutes: (
    projectPath: string,
    projectName: string
  ) => Promise<{
    success: boolean;
    data?: Record<string, unknown>;
    routeCount?: number;
    error?: string;
  }>;
}

export const createApiExplorerAPI = (): ApiExplorerAPI => ({
  scanProjectRoutes: (projectPath: string, projectName: string) =>
    ipcRenderer.invoke(IPC_CHANNELS.API_EXPLORER_SCAN_ROUTES, projectPath, projectName),
});
