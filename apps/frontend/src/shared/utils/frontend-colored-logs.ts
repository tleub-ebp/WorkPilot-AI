/**
 * Frontend Colored Logs Utility
 * 
 * Provides colored logging for frontend with scope-based coloring.
 * Scopes are detected between brackets [scope] and colored differently.
 * 
 * Usage:
 * import { formatFrontendLog, frontendDebugLog } from './frontend-colored-logs';
 * 
 * frontendDebugLog('[UsageMonitor:TRACE] Starting usage monitoring');
 */

// ANSI color codes
const COLORS = {
  RESET: '\x1b[0m',
  BOLD: '\x1b[1m',
  DIM: '\x1b[2m',
  
  // Timestamp
  TIMESTAMP: '\x1b[90m', // Gray
  
  // Frontend prefix
  FRONTEND_PREFIX: '\x1b[95m', // Magenta
  
  // Log levels
  DEBUG: '\x1b[95m', // Magenta
  INFO: '\x1b[38;5;147m', // Light purple
  SUCCESS: '\x1b[38;5;120m', // Teal green
  WARNING: '\x1b[38;5;221m', // Light yellow
  ERROR: '\x1b[38;5;196m', // Red
  
  // Scope colors (rotating palette for different scopes)
  SCOPE_COLORS: [
    '\x1b[38;5;45m', // Sky blue
    '\x1b[38;5;220m', // Peach
    '\x1b[38;5;154m', // Mint green
    '\x1b[38;5;213m', // Pink
    '\x1b[38;5;226m', // Light yellow
    '\x1b[38;5;87m', // Cornflower blue
    '\x1b[38;5;150m', // Light cyan
    '\x1b[38;5;185m', // Light rose
  ],
  
  // Message
  MESSAGE: '\x1b[37m', // White
};

// Scope color mapping for consistency
const scopeColorMap = new Map<string, string>();
let scopeColorIndex = 0;

/**
 * Check if the terminal supports ANSI colors
 * Enhanced with better PowerShell detection
 */
function supportsColor(): boolean {
  if (typeof process === 'undefined') return false;
  
  // Check environment variables
  if (process.env.NO_COLOR) return false;
  if (process.env.FORCE_COLOR) return true;
  
  // Check if we're in a TTY
  if (!process.stdout.isTTY) return false;
  
  // Check TERM environment variable
  const term = process.env.TERM || '';
  if (term === 'dumb' || term === 'unknown') return false;
  
  // Enhanced PowerShell detection
  if (process.platform === 'win32') {
    // Windows PowerShell or Windows Terminal
    if (process.env.PSModulePath || process.env.WINDIR) {
      return true;
    }
    
    // Check for Windows Terminal, ConEmu, etc.
    if (process.env.WT_SESSION || process.env.ConEmuANSI || process.env.TERM_PROGRAM) {
      return true;
    }
    
    // On Windows, assume color support if we're in a terminal
    return true;
  }
  
  return true;
}

/**
 * Get a consistent color for a scope
 */
function getScopeColor(scope: string): string {
  if (!scopeColorMap.has(scope)) {
    const color = COLORS.SCOPE_COLORS[scopeColorIndex % COLORS.SCOPE_COLORS.length];
    scopeColorMap.set(scope, color);
    scopeColorIndex++;
  }
  return scopeColorMap.get(scope) ?? COLORS.SCOPE_COLORS[0];
}

/**
 * Extract scope from message (text between first pair of brackets)
 */
function extractScope(message: string): { scope: string | null, cleanMessage: string } {
  const scopeMatch = /^\[([^\]]+)\]/.exec(message);
  if (scopeMatch) {
    return {
      scope: scopeMatch[1],
      cleanMessage: message.substring(scopeMatch[0].length).trim()
    };
  }
  return {
    scope: null,
    cleanMessage: message
  };
}

/**
 * Get current timestamp
 */
function getTimestamp(): string {
  const now = new Date();
  return now.toTimeString().split(' ')[0] + '.' + now.getMilliseconds().toString().padStart(3, '0');
}

/**
 * Format a frontend log message with colors and scope highlighting
 */
export function formatFrontendLog(
  message: string,
  level: 'DEBUG' | 'INFO' | 'SUCCESS' | 'WARNING' | 'ERROR' = 'DEBUG',
  module: string = 'frontend'
): string {
  if (!supportsColor()) {
    return message;
  }
  
  const timestamp = getTimestamp();
  const { scope, cleanMessage } = extractScope(message);
  
  // Get colors
  const levelColor = COLORS[level] ?? COLORS.DEBUG;
  
  // Build parts
  const parts = [
    `${COLORS.TIMESTAMP}[${timestamp}]${COLORS.RESET}`,
    `${COLORS.FRONTEND_PREFIX}[FRONTEND]${COLORS.RESET}`,
    `${levelColor}[${level}]${COLORS.RESET}`,
    `${COLORS.FRONTEND_PREFIX}[${module}]${COLORS.RESET}`,
  ];
  
  // Add scope if present
  if (scope) {
    const scopeColor = getScopeColor(scope);
    parts.push(`${scopeColor}[${scope}]${COLORS.RESET}`);
  }
  
  // Add message
  parts.push(`${COLORS.MESSAGE}${cleanMessage}${COLORS.RESET}`);
  
  return parts.join(' ');
}

/**
 * Enhanced console.log replacement for frontend debugging
 */
export function frontendDebugLog(message: string, ...args: any[]): void {
  if (process.env.DEBUG !== 'true') return;
  
  const formattedMessage = formatFrontendLog(message, 'DEBUG');
  console.warn(formattedMessage, ...args);
}

export function frontendInfoLog(message: string, ...args: any[]): void {
  const formattedMessage = formatFrontendLog(message, 'INFO');
  console.info(formattedMessage, ...args);
}

export function frontendSuccessLog(message: string, ..._args: any[]): void {
  const _formattedMessage = formatFrontendLog(message, 'SUCCESS');
}

export function frontendWarningLog(message: string, ...args: any[]): void {
  const formattedMessage = formatFrontendLog(message, 'WARNING');
  console.warn(formattedMessage, ...args);
}

export function frontendErrorLog(message: string, ...args: any[]): void {
  const formattedMessage = formatFrontendLog(message, 'ERROR');
  console.error(formattedMessage, ...args);
}

/**
 * Legacy debugLog function that maps to the new colored system
 */
export function debugLog(message: string, ...args: any[]): void {
  frontendDebugLog(message, ...args);
}

export function debugWarn(message: string, ...args: any[]): void {
  frontendWarningLog(message, ...args);
}

export function debugError(message: string, ...args: any[]): void {
  frontendErrorLog(message, ...args);
}

/**
 * Get colored scope string for use in other contexts
 */
export function getColoredScope(scope: string): string {
  if (!supportsColor()) {
    return `[${scope}]`;
  }
  const scopeColor = getScopeColor(scope);
  return `${scopeColor}[${scope}]${COLORS.RESET}`;
}

/**
 * Clear the scope color mapping (useful for testing)
 */
export function clearScopeColors(): void {
  scopeColorMap.clear();
  scopeColorIndex = 0;
}

// Export supportsColor for use in other modules
export { supportsColor };
