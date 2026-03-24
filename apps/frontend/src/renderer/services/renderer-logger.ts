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
  args?: any[];
}

// Service de logging pour le renderer
export const rendererLog = {
  debug: (message: string, ...args: any[]) => {
    const logMessage: LogMessage = {
      level: 'debug',
      message,
      module: 'renderer',
      args
    };
    sendToMainProcess(logMessage);
  },

  info: (message: string, ...args: any[]) => {
    const logMessage: LogMessage = {
      level: 'info',
      message,
      module: 'renderer',
      args
    };
    sendToMainProcess(logMessage);
  },

  success: (message: string, ...args: any[]) => {
    const logMessage: LogMessage = {
      level: 'success',
      message,
      module: 'renderer',
      args
    };
    sendToMainProcess(logMessage);
  },

  warning: (message: string, ...args: any[]) => {
    const logMessage: LogMessage = {
      level: 'warning',
      message,
      module: 'renderer',
      args
    };
    sendToMainProcess(logMessage);
  },

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
    debug: (message: string, ...args: any[]) => {
      sendToMainProcess({ level: 'debug', message, module: 'context', args });
    },
    info: (message: string, ...args: any[]) => {
      sendToMainProcess({ level: 'info', message, module: 'context', args });
    },
    success: (message: string, ...args: any[]) => {
      sendToMainProcess({ level: 'success', message, module: 'context', args });
    },
    warning: (message: string, ...args: any[]) => {
      sendToMainProcess({ level: 'warning', message, module: 'context', args });
    },
    error: (message: string, ...args: any[]) => {
      sendToMainProcess({ level: 'error', message, module: 'context', args });
    },
  },

  github: {
    debug: (message: string, ...args: any[]) => {
      sendToMainProcess({ level: 'debug', message, module: 'github', args });
    },
    info: (message: string, ...args: any[]) => {
      sendToMainProcess({ level: 'info', message, module: 'github', args });
    },
    success: (message: string, ...args: any[]) => {
      sendToMainProcess({ level: 'success', message, module: 'github', args });
    },
    warning: (message: string, ...args: any[]) => {
      sendToMainProcess({ level: 'warning', message, module: 'github', args });
    },
    error: (message: string, ...args: any[]) => {
      sendToMainProcess({ level: 'error', message, module: 'github', args });
    },
  },

  azure: {
    debug: (message: string, ...args: any[]) => {
      sendToMainProcess({ level: 'debug', message, module: 'azure', args });
    },
    info: (message: string, ...args: any[]) => {
      sendToMainProcess({ level: 'info', message, module: 'azure', args });
    },
    success: (message: string, ...args: any[]) => {
      sendToMainProcess({ level: 'success', message, module: 'azure', args });
    },
    warning: (message: string, ...args: any[]) => {
      sendToMainProcess({ level: 'warning', message, module: 'azure', args });
    },
    error: (message: string, ...args: any[]) => {
      sendToMainProcess({ level: 'error', message, module: 'azure', args });
    },
  },

  changelog: {
    debug: (message: string, ...args: any[]) => {
      sendToMainProcess({ level: 'debug', message, module: 'changelog', args });
    },
    info: (message: string, ...args: any[]) => {
      sendToMainProcess({ level: 'info', message, module: 'changelog', args });
    },
    success: (message: string, ...args: any[]) => {
      sendToMainProcess({ level: 'success', message, module: 'changelog', args });
    },
    warning: (message: string, ...args: any[]) => {
      sendToMainProcess({ level: 'warning', message, module: 'changelog', args });
    },
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
export const logRendererDebug = (message: string, ...args: any[]) => rendererLog.debug(message, ...args);
export const logRendererInfo = (message: string, ...args: any[]) => rendererLog.info(message, ...args);
export const logRendererSuccess = (message: string, ...args: any[]) => rendererLog.success(message, ...args);
export const logRendererWarning = (message: string, ...args: any[]) => rendererLog.warning(message, ...args);
export const logRendererError = (message: string, ...args: any[]) => rendererLog.error(message, ...args);

export default rendererLog;
