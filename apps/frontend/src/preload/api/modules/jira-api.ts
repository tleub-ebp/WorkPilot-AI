import { IPC_CHANNELS } from '../../../shared/constants';
import type {
  JiraWorkItem,
  JiraSyncStatus,
  IPCResult
} from '../../../shared/types';
import { invokeIpc } from './ipc-utils';

/**
 * Jira Integration API operations
 */
export interface JiraAPI {
  getJiraIssues: (projectId: string, maxItems?: number) => Promise<IPCResult<JiraWorkItem[]>>;
  checkJiraConnection: (projectId: string) => Promise<IPCResult<JiraSyncStatus>>;
}

/**
 * Creates the Jira Integration API implementation
 */
export const createJiraAPI = (): JiraAPI => ({
  getJiraIssues: (projectId: string, maxItems?: number): Promise<IPCResult<JiraWorkItem[]>> =>
    invokeIpc(IPC_CHANNELS.JIRA_GET_ISSUES, projectId, maxItems),

  checkJiraConnection: (projectId: string): Promise<IPCResult<JiraSyncStatus>> =>
    invokeIpc(IPC_CHANNELS.JIRA_CHECK_CONNECTION, projectId),
});
