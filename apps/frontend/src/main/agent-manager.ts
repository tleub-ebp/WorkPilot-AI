/**
 * AgentManager - Slim re-export facade
 *
 * This file maintains backward compatibility for imports using the old path.
 * The actual implementation has been refactored into modular components in ./agent/
 *
 * For new code, prefer importing directly from './agent':
 *   import { AgentManager } from './agent'
 *
 * This facade ensures existing imports continue to work:
 *   import { AgentManager } from './agent-manager'
 */

export type {
	AgentManagerEvents,
	AgentProcess,
	ExecutionProgressData,
	IdeationConfig,
	IdeationProgressData,
	ProcessType,
	RoadmapProgressData,
	SpecCreationMetadata,
	TaskExecutionOptions,
} from "./agent";
export {
	AgentEvents,
	AgentManager,
	AgentProcessManager,
	AgentQueueManager,
	AgentState,
} from "./agent";
