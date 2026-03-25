/**
 * Renderer Logger Service
 * =======================
 * 
 * Service de logging coloré pour le processus renderer (frontend).
 * Utilise IPC pour communiquer avec le système de logs colorés du main process.
 * 
 * Usage:
 * import { rendererLog } from './renderer-logger';
 * 
 * rendererLog.debug('Composant monté');
 * rendererLog.info('Action utilisateur');
 * rendererLog.error('Erreur survenue');
 */

import type { ElectronAPI } from '../../shared/types';

// Extend global interface for electronAPI
declare global {
  interface Window {
    electronAPI: ElectronAPI;
  }
}

// Interface pour les messages de log
interface LogMessage {
  level: 'debug' | 'info' | 'success' | 'warning' | 'error';
  message: string;
  module?: string;
  // biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
  args?: any[];
}

// Service de logging pour le renderer
export const rendererLog = {
  // biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
  debug: (message: string, ...args: any[]) => {
    const logMessage: LogMessage = {
      level: 'debug',
      message,
      module: 'renderer',
      args
    };
    sendToMainProcess(logMessage);
  },

  // biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
  info: (message: string, ...args: any[]) => {
    const logMessage: LogMessage = {
      level: 'info',
      message,
      module: 'renderer',
      args
    };
    sendToMainProcess(logMessage);
  },

  // biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
  success: (message: string, ...args: any[]) => {
    const logMessage: LogMessage = {
      level: 'success',
      message,
      module: 'renderer',
      args
    };
    sendToMainProcess(logMessage);
  },

  // biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
  warning: (message: string, ...args: any[]) => {
    const logMessage: LogMessage = {
      level: 'warning',
      message,
      module: 'renderer',
      args
    };
    sendToMainProcess(logMessage);
  },

  // biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
  error: (message: string, ...args: any[]) => {
    const logMessage: LogMessage = {
      level: 'error',
      message,
      module: 'renderer',
      args
    };
    sendToMainProcess(logMessage);
  },

  // Module-specific loggers
  context: {
    // biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
    debug: (message: string, ...args: any[]) => {
      sendToMainProcess({ level: 'debug', message, module: 'context', args });
    },
    // biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
    info: (message: string, ...args: any[]) => {
      sendToMainProcess({ level: 'info', message, module: 'context', args });
    },
    // biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
    success: (message: string, ...args: any[]) => {
      sendToMainProcess({ level: 'success', message, module: 'context', args });
    },
    // biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
    warning: (message: string, ...args: any[]) => {
      sendToMainProcess({ level: 'warning', message, module: 'context', args });
    },
    // biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
    error: (message: string, ...args: any[]) => {
      sendToMainProcess({ level: 'error', message, module: 'context', args });
    },
  },

  github: {
    // biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
    debug: (message: string, ...args: any[]) => {
      sendToMainProcess({ level: 'debug', message, module: 'github', args });
    },
    // biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
    info: (message: string, ...args: any[]) => {
      sendToMainProcess({ level: 'info', message, module: 'github', args });
    },
    // biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
    success: (message: string, ...args: any[]) => {
      sendToMainProcess({ level: 'success', message, module: 'github', args });
    },
    // biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
    warning: (message: string, ...args: any[]) => {
      sendToMainProcess({ level: 'warning', message, module: 'github', args });
    },
    // biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
    error: (message: string, ...args: any[]) => {
      sendToMainProcess({ level: 'error', message, module: 'github', args });
    },
  },

  azure: {
    // biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
    debug: (message: string, ...args: any[]) => {
      sendToMainProcess({ level: 'debug', message, module: 'azure', args });
    },
    // biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
    info: (message: string, ...args: any[]) => {
      sendToMainProcess({ level: 'info', message, module: 'azure', args });
    },
    // biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
    success: (message: string, ...args: any[]) => {
      sendToMainProcess({ level: 'success', message, module: 'azure', args });
    },
    // biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
    warning: (message: string, ...args: any[]) => {
      sendToMainProcess({ level: 'warning', message, module: 'azure', args });
    },
    // biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
    error: (message: string, ...args: any[]) => {
      sendToMainProcess({ level: 'error', message, module: 'azure', args });
    },
  },

  changelog: {
    // biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
    debug: (message: string, ...args: any[]) => {
      sendToMainProcess({ level: 'debug', message, module: 'changelog', args });
    },
    // biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
    info: (message: string, ...args: any[]) => {
      sendToMainProcess({ level: 'info', message, module: 'changelog', args });
    },
    // biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
    success: (message: string, ...args: any[]) => {
      sendToMainProcess({ level: 'success', message, module: 'changelog', args });
    },
    // biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
    warning: (message: string, ...args: any[]) => {
      sendToMainProcess({ level: 'warning', message, module: 'changelog', args });
    },
    // biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
    error: (message: string, ...args: any[]) => {
      sendToMainProcess({ level: 'error', message, module: 'changelog', args });
    },
  },
};

// Fonction pour envoyer les logs au main process
function sendToMainProcess(logMessage: LogMessage): void {
  try {
    // Envoyer via IPC au main process
    globalThis.electronAPI?.send?.('renderer-log', logMessage);
  } catch (error) {
    // Fallback vers console standard en cas d'erreur IPC
    const fallbackMessage = `[Renderer Log Error] ${logMessage.level.toUpperCase()}: ${logMessage.message}`;
    console.error(fallbackMessage, error);
    
    // Afficher le message original avec console standard
    switch (logMessage.level) {
      case 'debug':
        break;
      case 'info':
        console.info(logMessage.message, ...(logMessage.args || []));
        break;
      case 'success':
        break;
      case 'warning':
        console.warn(`⚠️ ${logMessage.message}`, ...(logMessage.args || []));
        break;
      case 'error':
        console.error(`❌ ${logMessage.message}`, ...(logMessage.args || []));
        break;
    }
  }
}

// Export convenience functions
// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
export const logRendererDebug = (message: string, ...args: any[]) => rendererLog.debug(message, ...args);
// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
export const logRendererInfo = (message: string, ...args: any[]) => rendererLog.info(message, ...args);
// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
export const logRendererSuccess = (message: string, ...args: any[]) => rendererLog.success(message, ...args);
// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
export const logRendererWarning = (message: string, ...args: any[]) => rendererLog.warning(message, ...args);
// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
export const logRendererError = (message: string, ...args: any[]) => rendererLog.error(message, ...args);

export default rendererLog;
