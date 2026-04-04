/**
 * Agent module - modular agent management system
 *
 * This module provides a clean separation of concerns for agent process management:
 * - AgentManager: Main facade for orchestrating agent lifecycle
 * - AgentState: Process tracking and state management
 * - AgentEvents: Event handling and progress parsing
 * - AgentProcessManager: Process spawning and lifecycle
 * - AgentQueueManager: Ideation and roadmap queue management
 */

// Re-export IdeationConfig from shared types for consistency
export type { IdeationConfig } from "../../shared/types";
export { AgentEvents } from "./agent-events";
export { AgentManager } from "./agent-manager";
export { AgentProcessManager } from "./agent-process";
export { AgentQueueManager } from "./agent-queue";
export { AgentState } from "./agent-state";
export type {
	AgentManagerEvents,
	AgentProcess,
	ExecutionProgressData,
	IdeationProgressData,
	ProcessType,
	RoadmapProgressData,
	SpecCreationMetadata,
	TaskExecutionOptions,
} from "./types";
