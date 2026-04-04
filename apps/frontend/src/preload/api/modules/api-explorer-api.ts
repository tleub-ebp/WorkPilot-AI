import { ipcRenderer } from "electron";
import { IPC_CHANNELS } from "../../../shared/constants";

export interface ApiExplorerProxyResponse {
	success: boolean;
	status?: number;
	statusText?: string;
	headers?: Record<string, string>;
	body?: string;
	time?: number;
	error?: string;
}

export interface ApiExplorerAPI {
	scanProjectRoutes: (
		projectPath: string,
		projectName: string,
	) => Promise<{
		success: boolean;
		data?: Record<string, unknown>;
		routeCount?: number;
		error?: string;
	}>;
	proxyHttpRequest: (payload: {
		url: string;
		method: string;
		headers: Record<string, string>;
		body?: string;
	}) => Promise<ApiExplorerProxyResponse>;
}

export const createApiExplorerAPI = (): ApiExplorerAPI => ({
	scanProjectRoutes: (projectPath: string, projectName: string) =>
		ipcRenderer.invoke(
			IPC_CHANNELS.API_EXPLORER_SCAN_ROUTES,
			projectPath,
			projectName,
		),
	proxyHttpRequest: (payload) =>
		ipcRenderer.invoke(IPC_CHANNELS.API_EXPLORER_PROXY_REQUEST, payload),
});
