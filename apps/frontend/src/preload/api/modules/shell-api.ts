import { IPC_CHANNELS } from "../../../shared/constants";
import type { IPCResult } from "../../../shared/types";
import { invokeIpc } from "./ipc-utils";

/**
 * Shell Operations API
 */
export interface ShellAPI {
	openExternal: (url: string) => Promise<void>;
	openTerminal: (dirPath: string) => Promise<IPCResult<void>>;
	openTerminalWithCommand: (command: string) => Promise<void>;
}

/**
 * Creates the Shell Operations API implementation
 */
export const createShellAPI = (): ShellAPI => ({
	openExternal: (url: string): Promise<void> =>
		invokeIpc(IPC_CHANNELS.SHELL_OPEN_EXTERNAL, url),
	openTerminal: (dirPath: string): Promise<IPCResult<void>> =>
		invokeIpc(IPC_CHANNELS.SHELL_OPEN_TERMINAL, dirPath),
	openTerminalWithCommand: (command: string): Promise<void> =>
		invokeIpc(IPC_CHANNELS.SHELL_OPEN_TERMINAL_WITH_COMMAND, command),
});
