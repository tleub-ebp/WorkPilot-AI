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
    };
  }
}

export {};
