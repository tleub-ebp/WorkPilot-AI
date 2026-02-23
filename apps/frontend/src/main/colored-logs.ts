/**
 * Colored Logs Utility for Frontend
 * =================================
 * 
 * Utility for differentiating frontend logs with distinct colors.
 * Provides purple/pink theme to distinguish from backend blue/cyan theme.
 * 
 * Usage:
 * import { frontendLog } from './colored-logs';
 * 
 * frontendLog.debug('Main process started');
 * frontendLog.info('Window created');
 * frontendLog.error('Failed to load config');
 */

import { app } from 'electron';

// ANSI color codes for terminal output
class FrontendColors {
  static readonly RESET = '\x1b[0m';
  static readonly BOLD = '\x1b[1m';
  static readonly DIM = '\x1b[2m';
  
  // Frontend color scheme - Purple/Pink theme
  static readonly PREFIX = '\x1b[95m';    // Magenta
  static readonly DEBUG = '\x1b[95m';     // Magenta
  static readonly DEBUG_DIM = '\x1b[38;5;183m';  // Light magenta
  static readonly INFO = '\x1b[38;5;147m';      // Light purple
  static readonly SUCCESS = '\x1b[38;5;120m';   // Teal green
  static readonly WARNING = '\x1b[38;5;221m';   // Light yellow
  static readonly ERROR = '\x1b[38;5;196m';     // Red
  
  // Common colors
  static readonly TIMESTAMP = '\x1b[90m';  // Gray
  static readonly MODULE = '\x1b[33m';     // Yellow  
  static readonly KEY = '\x1b[35m';        // Magenta
  static readonly VALUE = '\x1b[37m';      // White
}

function supportsColor(): boolean {
  // Check for common environment variables
  if (process.env.NO_COLOR) {
    return false;
  }
  if (process.env.FORCE_COLOR) {
    return true;
  }
  
  // Check if we're in a terminal
  if (!process.stdout.isTTY) {
    return false;
  }
  
  // Check TERM environment variable
  const term = process.env.TERM || '';
  if (term === 'dumb' || term === 'unknown') {
    return false;
  }
  
  // Check for common color-supporting terminals
  return /color|256|xterm|screen|tmux/i.test(term);
}

function getTimestamp(): string {
  return new Date().toLocaleTimeString('en-US', { 
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    fractionalSecondDigits: 3
  });
}

function formatValue(value: any, maxLength: number = 200): string {
  if (value === null || value === undefined) {
    return 'None';
  }
  
  if (typeof value === 'object') {
    try {
      const formatted = JSON.stringify(value, null, 2);
      return formatted.length > maxLength ? formatted.substring(0, maxLength) + '...' : formatted;
    } catch (error) {
      return String(value).substring(0, maxLength);
    }
  }
  
  const strValue = String(value);
  return strValue.length > maxLength ? strValue.substring(0, maxLength) + '...' : strValue;
}

function formatFrontendLog(
  message: string,
  level: string = 'DEBUG',
  module: string = 'frontend',
  timestamp?: string,
  ...kwargs: any[]
): string {
  if (!supportsColor()) {
    // Return non-colored version for non-color terminals
    return `[${timestamp || getTimestamp()}] [FRONTEND] [${level}] [${module}] ${message}`;
  }
  
  const ts = timestamp || getTimestamp();
  
  // Get the appropriate color for the level
  const levelColors: Record<string, string> = {
    'DEBUG': FrontendColors.DEBUG,
    'INFO': FrontendColors.INFO,
    'SUCCESS': FrontendColors.SUCCESS,
    'WARNING': FrontendColors.WARNING,
    'ERROR': FrontendColors.ERROR,
  };
  const levelColor = levelColors[level.toUpperCase()] || FrontendColors.DEBUG;
  
  // Build the log line
  const parts = [
    `${FrontendColors.TIMESTAMP}[${ts}]${FrontendColors.RESET}`,
    `${FrontendColors.PREFIX}[FRONTEND]${FrontendColors.RESET}`,
    `${levelColor}[${level}]${FrontendColors.RESET}`,
    `${FrontendColors.MODULE}[${module}]${FrontendColors.RESET}`,
    `${FrontendColors.DEBUG_DIM}${message}${FrontendColors.RESET}`,
  ];
  
  let logLine = parts.join(' ');
  
  // Add additional arguments on separate lines if present
  if (kwargs.length > 0) {
    kwargs.forEach((arg, index) => {
      const formattedValue = formatValue(arg);
      if (formattedValue.includes('\n')) {
        // Multi-line value
        logLine += `\n  ${FrontendColors.KEY}arg${index}${FrontendColors.RESET}:`;
        formattedValue.split('\n').forEach(line => {
          logLine += `\n    ${FrontendColors.VALUE}${line}${FrontendColors.RESET}`;
        });
      } else {
        logLine += `\n  ${FrontendColors.KEY}arg${index}${FrontendColors.RESET}: ${FrontendColors.VALUE}${formattedValue}${FrontendColors.RESET}`;
      }
    });
  }
  
  return logLine;
}

function writeFrontendLog(message: string, level: string = 'DEBUG', module?: string, ...kwargs: any[]): void {
  const formatted = formatFrontendLog(message, level, module, undefined, ...kwargs);
  // Use process.stderr.write to avoid recursion with overridden console methods
  if (process.stderr && process.stderr.write) {
    process.stderr.write(formatted + '\n');
  } else {
    // Fallback to original console if available
    const originalConsole = (console as any).original;
    if (originalConsole && originalConsole.error) {
      originalConsole.error(formatted);
    } else {
      // Last resort - use writeFileSync
      try {
        require('fs').writeFileSync(1, formatted + '\n');
      } catch (e) {
        // If all else fails, stay silent to avoid infinite recursion
      }
    }
  }
}

// Main frontend logger object
export const frontendLog = {
  debug: (message: string, ...kwargs: any[]) => {
    writeFrontendLog(message, 'DEBUG', 'frontend', ...kwargs);
  },
  
  info: (message: string, ...kwargs: any[]) => {
    writeFrontendLog(message, 'INFO', 'frontend', ...kwargs);
  },
  
  success: (message: string, ...kwargs: any[]) => {
    writeFrontendLog(message, 'SUCCESS', 'frontend', ...kwargs);
  },
  
  warn: (message: string, ...kwargs: any[]) => {
    writeFrontendLog(message, 'WARNING', 'frontend', ...kwargs);
  },
  
  error: (message: string, ...kwargs: any[]) => {
    writeFrontendLog(message, 'ERROR', 'frontend', ...kwargs);
  },
  
  // Module-specific loggers
  main: {
    debug: (message: string, ...kwargs: any[]) => {
      writeFrontendLog(message, 'DEBUG', 'main', ...kwargs);
    },
    info: (message: string, ...kwargs: any[]) => {
      writeFrontendLog(message, 'INFO', 'main', ...kwargs);
    },
    success: (message: string, ...kwargs: any[]) => {
      writeFrontendLog(message, 'SUCCESS', 'main', ...kwargs);
    },
    warn: (message: string, ...kwargs: any[]) => {
      writeFrontendLog(message, 'WARNING', 'main', ...kwargs);
    },
    error: (message: string, ...kwargs: any[]) => {
      writeFrontendLog(message, 'ERROR', 'main', ...kwargs);
    },
  },
  
  renderer: {
    debug: (message: string, ...kwargs: any[]) => {
      writeFrontendLog(message, 'DEBUG', 'renderer', ...kwargs);
    },
    info: (message: string, ...kwargs: any[]) => {
      writeFrontendLog(message, 'INFO', 'renderer', ...kwargs);
    },
    success: (message: string, ...kwargs: any[]) => {
      writeFrontendLog(message, 'SUCCESS', 'renderer', ...kwargs);
    },
    warn: (message: string, ...kwargs: any[]) => {
      writeFrontendLog(message, 'WARNING', 'renderer', ...kwargs);
    },
    error: (message: string, ...kwargs: any[]) => {
      writeFrontendLog(message, 'ERROR', 'renderer', ...kwargs);
    },
  },
  
  ipc: {
    debug: (message: string, ...kwargs: any[]) => {
      writeFrontendLog(message, 'DEBUG', 'ipc', ...kwargs);
    },
    info: (message: string, ...kwargs: any[]) => {
      writeFrontendLog(message, 'INFO', 'ipc', ...kwargs);
    },
    success: (message: string, ...kwargs: any[]) => {
      writeFrontendLog(message, 'SUCCESS', 'ipc', ...kwargs);
    },
    warn: (message: string, ...kwargs: any[]) => {
      writeFrontendLog(message, 'WARNING', 'ipc', ...kwargs);
    },
    error: (message: string, ...kwargs: any[]) => {
      writeFrontendLog(message, 'ERROR', 'ipc', ...kwargs);
    },
  },
};

// Export convenience functions
export const logFrontendDebug = (message: string, ...kwargs: any[]) => frontendLog.debug(message, ...kwargs);
export const logFrontendInfo = (message: string, ...kwargs: any[]) => frontendLog.info(message, ...kwargs);
export const logFrontendSuccess = (message: string, ...kwargs: any[]) => frontendLog.success(message, ...kwargs);
export const logFrontendWarning = (message: string, ...kwargs: any[]) => frontendLog.warn(message, ...kwargs);
export const logFrontendError = (message: string, ...kwargs: any[]) => frontendLog.error(message, ...kwargs);

// NOTE: Console override disabled to prevent recursion issues
// Use frontendLog directly instead of overriding console methods
/*
// Enhanced console object override for development
if (process.env.NODE_ENV === 'development') {
  const originalConsole = {
    log: console.log,
    debug: console.debug,
    info: console.info,
    warn: console.warn,
    error: console.error,
  };
  
  // Override console methods to use colored logging
  console.log = (...args: any[]) => {
    if (args.length > 0) {
      frontendLog.info(String(args[0]), ...args.slice(1));
    } else {
      originalConsole.log(...args);
    }
  };
  
  console.debug = (...args: any[]) => {
    if (args.length > 0) {
      frontendLog.debug(String(args[0]), ...args.slice(1));
    } else {
      originalConsole.debug(...args);
    }
  };
  
  console.info = (...args: any[]) => {
    if (args.length > 0) {
      frontendLog.info(String(args[0]), ...args.slice(1));
    } else {
      originalConsole.info(...args);
    }
  };
  
  console.warn = (...args: any[]) => {
    if (args.length > 0) {
      frontendLog.warn(String(args[0]), ...args.slice(1));
    } else {
      originalConsole.warn(...args);
    }
  };
  
  console.error = (...args: any[]) => {
    if (args.length > 0) {
      frontendLog.error(String(args[0]), ...args.slice(1));
    } else {
      originalConsole.error(...args);
    }
  };
  
  // Keep original methods available if needed
  (console as any).original = originalConsole;
}
*/

export default frontendLog;
