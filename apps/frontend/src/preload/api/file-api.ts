import os from "node:os";
import { ipcRenderer } from "electron";
import { IPC_CHANNELS } from "../../shared/constants";
import type { IPCResult } from "../../shared/types";

export interface FileAPI {
	// File Explorer Operations
	listDirectory: (
		dirPath: string,
	) => Promise<IPCResult<import("../../shared/types").FileNode[]>>;
	readFile: (filePath: string) => Promise<IPCResult<string>>;
	saveJsonFile: (
		dirPath: string,
		fileName: string,
		data: unknown,
	) => Promise<IPCResult<boolean>>;
	getUserHome: () => string;
}

export const createFileAPI = (): FileAPI => ({
	// File Explorer Operations
	listDirectory: (
		dirPath: string,
	): Promise<IPCResult<import("../../shared/types").FileNode[]>> =>
		ipcRenderer.invoke(IPC_CHANNELS.FILE_EXPLORER_LIST, dirPath),
	readFile: (filePath: string): Promise<IPCResult<string>> =>
		ipcRenderer.invoke(IPC_CHANNELS.FILE_EXPLORER_READ, filePath),
	saveJsonFile: (
		dirPath: string,
		fileName: string,
		data: unknown,
	): Promise<IPCResult<boolean>> =>
		ipcRenderer.invoke(
			IPC_CHANNELS.FILE_EXPLORER_SAVE,
			dirPath,
			fileName,
			data,
		),
	getUserHome: (): string => os.homedir(),
});
