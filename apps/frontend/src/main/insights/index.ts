/**
 * Insights module - modular architecture for AI-powered codebase insights
 *
 * This module provides a clean separation of concerns:
 * - config: Environment and configuration management
 * - paths: Path resolution utilities
 * - session-storage: Filesystem persistence layer
 * - session-manager: Session lifecycle management
 * - insights-executor: Python process execution
 */

export { InsightsConfig } from "./config";
export { InsightsExecutor } from "./insights-executor";
export { InsightsPaths } from "./paths";
export { SessionManager } from "./session-manager";
export { SessionStorage } from "./session-storage";
