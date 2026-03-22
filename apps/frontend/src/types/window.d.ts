/**
 * Window interface extensions for Electron APIs
 */

declare global {
  interface Window {
    electronAPI: {
      // Copilot OAuth API methods
      copilotOAuthStart: (profileName: string) => Promise<{
        success: boolean;
        data?: {
          success: boolean;
          username?: string;
          profileName?: string;
        };
        error?: string;
      }>;
      
      copilotOAuthStatus: () => Promise<{
        success: boolean;
        data?: {
          authenticated: boolean;
          profiles: Array<{
            username: string;
            profileName: string;
            createdAt: string;
          }>;
        };
        error?: string;
      }>;
      
      copilotOAuthRevoke: (username: string) => Promise<{
        success: boolean;
        error?: string;
      }>;

      // Generic invoke method
      invoke: (channel: string, ...args: any[]) => Promise<any>;

      // Self-Healing API
      selfHealing: {
        getDashboard(projectPath: string): Promise<{ success: boolean; data?: any }>;
        getIncidents(projectPath: string, mode?: string): Promise<{ success: boolean; data?: any[] }>;
        getOperations(projectPath: string): Promise<{ success: boolean; data?: any[] }>;
        getFragility(projectPath: string): Promise<{ success: boolean; data?: any[] }>;
        cicdEnable(projectPath: string): Promise<{ success: boolean; error?: string }>;
        cicdDisable(projectPath: string): Promise<{ success: boolean; error?: string }>;
        cicdConfig(projectPath: string, config: Record<string, unknown>): Promise<{ success: boolean; config?: any; error?: string }>;
        productionConnect(projectPath: string, sourceConfig: Record<string, unknown>): Promise<{ success: boolean; error?: string }>;
        productionDisconnect(projectPath: string, source: string): Promise<{ success: boolean; error?: string }>;
        productionConfig(projectPath: string, config: Record<string, unknown>): Promise<{ success: boolean; error?: string }>;
        proactiveScan(projectPath: string): Promise<{ success: boolean; error?: string }>;
        proactiveConfig(projectPath: string, config: Record<string, unknown>): Promise<{ success: boolean; error?: string }>;
        triggerFix(projectPath: string, incidentId: string): Promise<{ success: boolean; error?: string }>;
        cancelOperation(projectPath: string, operationId: string): Promise<{ success: boolean; error?: string }>;
        dismissIncident(projectPath: string, incidentId: string): Promise<{ success: boolean; error?: string }>;
        retryIncident(projectPath: string, incidentId: string): Promise<{ success: boolean; error?: string }>;
        onIncidentDetected(callback: (data: unknown) => void): () => void;
        onOperationProgress(callback: (data: unknown) => void): () => void;
        onOperationComplete(callback: (data: unknown) => void): () => void;
      };
    };
  }
}

// Electron webview JSX element type
declare namespace JSX {
  interface IntrinsicElements {
    webview: React.DetailedHTMLProps<React.HTMLAttributes<HTMLElement>, HTMLElement> & {
      src?: string;
      partition?: string;
      allowpopups?: string;
    };
  }
}

export {};
