import { IPC_CHANNELS } from '../../../shared/constants';
import type {
  IPCResult,
  MultiRepoOrchestration,
  MultiRepoCreateConfig,
  MultiRepoStatus,
  RepoExecutionState,
} from '../../../shared/types';
import { createIpcListener, invokeIpc, type IpcListenerCleanup } from './ipc-utils';

/**
 * Multi-Repo Orchestration API
 */
export interface MultiRepoAPI {
  // Operations
  createMultiRepoOrchestration: (
    projectId: string,
    config: MultiRepoCreateConfig
  ) => Promise<IPCResult<MultiRepoOrchestration>>;

  getMultiRepoOrchestration: (
    orchestrationId: string,
    projectId: string
  ) => Promise<IPCResult<MultiRepoOrchestration | null>>;

  listMultiRepoOrchestrations: (
    projectId: string
  ) => Promise<IPCResult<MultiRepoOrchestration[]>>;

  startMultiRepoOrchestration: (
    projectId: string,
    orchestrationId: string
  ) => Promise<IPCResult>;

  stopMultiRepoOrchestration: (
    orchestrationId: string
  ) => Promise<IPCResult>;

  getMultiRepoStatus: (
    orchestrationId: string,
    projectId: string
  ) => Promise<IPCResult<{ status: MultiRepoStatus; repoStates: RepoExecutionState[] }>>;

  // Event listeners
  onMultiRepoProgress: (
    callback: (orchestrationId: string, data: Record<string, unknown>) => void
  ) => IpcListenerCleanup;

  onMultiRepoRepoStart: (
    callback: (orchestrationId: string, data: Record<string, unknown>) => void
  ) => IpcListenerCleanup;

  onMultiRepoRepoComplete: (
    callback: (orchestrationId: string, data: Record<string, unknown>) => void
  ) => IpcListenerCleanup;

  onMultiRepoComplete: (
    callback: (orchestrationId: string, data: Record<string, unknown>) => void
  ) => IpcListenerCleanup;

  onMultiRepoError: (
    callback: (orchestrationId: string, data: Record<string, unknown>) => void
  ) => IpcListenerCleanup;

  onMultiRepoBreakingChange: (
    callback: (orchestrationId: string, data: Record<string, unknown>) => void
  ) => IpcListenerCleanup;

  onMultiRepoGraph: (
    callback: (orchestrationId: string, data: Record<string, unknown>) => void
  ) => IpcListenerCleanup;
}

/**
 * Creates the Multi-Repo API implementation
 */
export const createMultiRepoAPI = (): MultiRepoAPI => ({
  // Operations
  createMultiRepoOrchestration: (
    projectId: string,
    config: MultiRepoCreateConfig
  ): Promise<IPCResult<MultiRepoOrchestration>> =>
    invokeIpc(IPC_CHANNELS.MULTI_REPO_CREATE, projectId, config),

  getMultiRepoOrchestration: (
    orchestrationId: string,
    projectId: string
  ): Promise<IPCResult<MultiRepoOrchestration | null>> =>
    invokeIpc(IPC_CHANNELS.MULTI_REPO_GET, orchestrationId, projectId),

  listMultiRepoOrchestrations: (
    projectId: string
  ): Promise<IPCResult<MultiRepoOrchestration[]>> =>
    invokeIpc(IPC_CHANNELS.MULTI_REPO_LIST, projectId),

  startMultiRepoOrchestration: (
    projectId: string,
    orchestrationId: string
  ): Promise<IPCResult> =>
    invokeIpc(IPC_CHANNELS.MULTI_REPO_START, projectId, orchestrationId),

  stopMultiRepoOrchestration: (
    orchestrationId: string
  ): Promise<IPCResult> =>
    invokeIpc(IPC_CHANNELS.MULTI_REPO_STOP, orchestrationId),

  getMultiRepoStatus: (
    orchestrationId: string,
    projectId: string
  ): Promise<IPCResult<{ status: MultiRepoStatus; repoStates: RepoExecutionState[] }>> =>
    invokeIpc(IPC_CHANNELS.MULTI_REPO_GET_STATUS, orchestrationId, projectId),

  // Event listeners
  onMultiRepoProgress: (
    callback: (orchestrationId: string, data: Record<string, unknown>) => void
  ): IpcListenerCleanup =>
    createIpcListener(IPC_CHANNELS.MULTI_REPO_PROGRESS, callback),

  onMultiRepoRepoStart: (
    callback: (orchestrationId: string, data: Record<string, unknown>) => void
  ): IpcListenerCleanup =>
    createIpcListener(IPC_CHANNELS.MULTI_REPO_REPO_START, callback),

  onMultiRepoRepoComplete: (
    callback: (orchestrationId: string, data: Record<string, unknown>) => void
  ): IpcListenerCleanup =>
    createIpcListener(IPC_CHANNELS.MULTI_REPO_REPO_COMPLETE, callback),

  onMultiRepoComplete: (
    callback: (orchestrationId: string, data: Record<string, unknown>) => void
  ): IpcListenerCleanup =>
    createIpcListener(IPC_CHANNELS.MULTI_REPO_COMPLETE, callback),

  onMultiRepoError: (
    callback: (orchestrationId: string, data: Record<string, unknown>) => void
  ): IpcListenerCleanup =>
    createIpcListener(IPC_CHANNELS.MULTI_REPO_ERROR, callback),

  onMultiRepoBreakingChange: (
    callback: (orchestrationId: string, data: Record<string, unknown>) => void
  ): IpcListenerCleanup =>
    createIpcListener(IPC_CHANNELS.MULTI_REPO_BREAKING_CHANGE, callback),

  onMultiRepoGraph: (
    callback: (orchestrationId: string, data: Record<string, unknown>) => void
  ): IpcListenerCleanup =>
    createIpcListener(IPC_CHANNELS.MULTI_REPO_GRAPH, callback),
});
