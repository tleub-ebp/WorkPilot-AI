/**
 * Central export point for all shared types
 */

// Common types
export * from './common';

// Domain-specific types
export * from './project';
export * from './task';
export * from './kanban';
export * from './terminal';
export * from './agent';
export * from './settings';
export * from './changelog';
export * from './insights';
export * from './roadmap';
export * from './integrations';
export * from './app-update';
export * from './cli';

// MCP Marketplace types
export * from './mcp-marketplace';

// Multi-Repo Orchestration types
export * from './multi-repo';

// Context Mesh types (Cross-Project Intelligence)
export * from './context-mesh';

// Live Companion types (Real-time pair programming)
export * from './live-companion';

// IPC types (must be last to use types from other modules)
export * from './ipc';
