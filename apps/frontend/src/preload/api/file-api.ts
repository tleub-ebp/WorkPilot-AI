import { ipcRenderer } from 'electron';
import os from 'os';
import { IPC_CHANNELS } from '../../shared/constants';
import type { IPCResult } from '../../shared/types';

export interface FileAPI {
  // File Explorer Operations
  listDirectory: (dirPath: string) => Promise<IPCResult<import('../../shared/types').FileNode[]>>;
  readFile: (filePath: string) => Promise<IPCResult<string>>;
  // biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
  saveJsonFile: (dirPath: string, fileName: string, data: any) => Promise<IPCResult<boolean>>;
  getUserHome: () => string;
}

export const createFileAPI = (): FileAPI => ({
  // File Explorer Operations
  listDirectory: (dirPath: string): Promise<IPCResult<import('../../shared/types').FileNode[]>> =>
    ipcRenderer.invoke(IPC_CHANNELS.FILE_EXPLORER_LIST, dirPath),
  readFile: (filePath: string): Promise<IPCResult<string>> =>
    ipcRenderer.invoke(IPC_CHANNELS.FILE_EXPLORER_READ, filePath),
  // biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
  saveJsonFile: (dirPath: string, fileName: string, data: any): Promise<IPCResult<boolean>> =>
    ipcRenderer.invoke(IPC_CHANNELS.FILE_EXPLORER_SAVE, dirPath, fileName, data),
  getUserHome: (): string => os.homedir(),
});