/**
 * Agent Decision Logger — shared types
 */

export type DecisionType =
  | 'tool_call'
  | 'file_read'
  | 'file_write'
  | 'reasoning'
  | 'decision'
  | 'phase_transition'
  | 'error_recovery';

export interface DecisionEntry {
  id: number;
  session_id: string;
  agent_type: string;
  decision_type: DecisionType;
  timestamp: string;            // ISO8601 UTC

  // Content fields (all optional)
  summary: string;
  tool_name?: string;
  tool_input_summary?: string;
  tool_outcome?: 'success' | 'error' | 'partial';
  files?: string[];
  alternatives?: string[];
  selected?: string;
  reasoning_text?: string;
  phase_from?: string;
  phase_to?: string;
  error_type?: string;
  recovery_approach?: string;
  subtask_id?: string;
}

export interface DecisionLog {
  taskId: string;
  specId: string;
  entries: DecisionEntry[];
  loaded_at: string;
}
