// Export main component
export { Terminal } from "../Terminal";
export { TaskSelector } from "./TaskSelector";
// Export sub-components (in case they need to be used elsewhere)
export { TerminalHeader } from "./TerminalHeader";
export { TerminalTitle } from "./TerminalTitle";
// Export types and constants
export type { TerminalProps } from "./types";
export { PHASE_CONFIG, STATUS_COLORS } from "./types";
export { useAutoNaming } from "./useAutoNaming";
export { usePtyProcess } from "./usePtyProcess";
export { useTerminalEvents } from "./useTerminalEvents";
// Export hooks
export { useXterm } from "./useXterm";
