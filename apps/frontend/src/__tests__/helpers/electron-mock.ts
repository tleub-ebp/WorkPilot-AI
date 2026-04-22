/**
 * Shared test helpers for mocking Electron's `ipcRenderer`, `ipcMain`,
 * and `contextBridge`.
 *
 * Usage (in a test file):
 *
 *     import { vi } from "vitest";
 *     import { createElectronRendererMock } from "../helpers/electron-mock";
 *
 *     const { mockIpcRenderer, mockContextBridge, exposedApis } =
 *         createElectronRendererMock();
 *
 *     vi.mock("electron", () => ({
 *         ipcRenderer: mockIpcRenderer,
 *         contextBridge: mockContextBridge,
 *     }));
 *
 * The factory returns fresh ``vi.fn()`` instances per call, so individual
 * tests can reset them with ``vi.clearAllMocks()`` without leaking state
 * across files.
 */

import { type Mock, vi } from "vitest";

// We deliberately expose each mock as ``Mock`` (vitest's unparameterized
// Mock) rather than a narrowed variant. ``Mock`` keeps the full
// ``mockResolvedValueOnce`` / ``mockImplementation`` API callable on every
// field, which is the whole point of this shared helper.
export interface ElectronRendererMock {
	mockIpcRenderer: {
		invoke: Mock;
		send: Mock;
		on: Mock;
		once: Mock;
		off: Mock;
		removeListener: Mock;
		removeAllListeners: Mock;
		setMaxListeners: Mock;
	};
	mockContextBridge: {
		exposeInMainWorld: Mock;
	};
	/**
	 * Registry of every API exposed via ``contextBridge.exposeInMainWorld``.
	 * Populated by the mock so tests can introspect what the preload script
	 * exposed to the renderer.
	 */
	exposedApis: Record<string, unknown>;
}

export function createElectronRendererMock(): ElectronRendererMock {
	const exposedApis: Record<string, unknown> = {};
	return {
		mockIpcRenderer: {
			invoke: vi.fn(),
			send: vi.fn(),
			on: vi.fn(),
			once: vi.fn(),
			off: vi.fn(),
			removeListener: vi.fn(),
			removeAllListeners: vi.fn(),
			setMaxListeners: vi.fn(),
		},
		mockContextBridge: {
			exposeInMainWorld: vi.fn((name: string, api: unknown) => {
				exposedApis[name] = api;
			}),
		},
		exposedApis,
	};
}

export interface ElectronMainMock {
	mockIpcMain: {
		handle: Mock;
		handleOnce: Mock;
		on: Mock;
		removeHandler: Mock;
		removeAllListeners: Mock;
	};
	mockApp: {
		getPath: Mock;
		getAppPath: Mock;
		getVersion: Mock;
		isPackaged: boolean;
		on: Mock;
		quit: Mock;
	};
}

export function createElectronMainMock(): ElectronMainMock {
	return {
		mockIpcMain: {
			handle: vi.fn(),
			handleOnce: vi.fn(),
			on: vi.fn(),
			removeHandler: vi.fn(),
			removeAllListeners: vi.fn(),
		},
		mockApp: {
			getPath: vi.fn((_name: string) => "/tmp/test"),
			getAppPath: vi.fn(() => "/tmp/test-app"),
			getVersion: vi.fn(() => "0.1.0"),
			isPackaged: false,
			on: vi.fn(),
			quit: vi.fn(),
		},
	};
}
