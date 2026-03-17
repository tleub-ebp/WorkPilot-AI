/**
 * Agent Decision Logger Preload API (Feature 30)
 */

import type { DecisionEntry, DecisionLog } from '../../../shared/types/decision-logger';
import { invokeIpc, createIpcListener } from './ipc-utils';

export interface DecisionLoggerAPI {
  /** Load the persisted decision log for a spec. */
  getDecisionLog: (
    specDirPath: string,
    taskId: string,
    specId: string,
  ) => Promise<{ success: boolean; data?: DecisionLog; error?: string }>;

  /** Delete the decision_log.json file for a spec. */
  clearDecisionLog: (
    specDirPath: string,
  ) => Promise<{ success: boolean; error?: string }>;

  /** Subscribe to live decision entries emitted during an active agent session. */
  onDecisionLogEntry: (
    callback: (taskId: string, entry: DecisionEntry, projectId?: string) => void,
  ) => () => void;
}

export function createDecisionLoggerAPI(): DecisionLoggerAPI {
  return {
    getDecisionLog: (specDirPath, taskId, specId) =>
      invokeIpc('agentDecision:getLog', specDirPath, taskId, specId),

    clearDecisionLog: (specDirPath) =>
      invokeIpc('agentDecision:clearLog', specDirPath),

    onDecisionLogEntry: (callback) =>
      createIpcListener<[string, DecisionEntry, string | undefined]>(
        'agentDecision:entry',
        callback,
      ),
  };
}
