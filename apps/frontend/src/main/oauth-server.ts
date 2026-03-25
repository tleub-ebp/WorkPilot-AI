/**
 * OAuth Callback Server
 *
 * Local HTTP server to handle OAuth callbacks for GitHub Copilot.
 * Runs on localhost:3000 to receive GitHub OAuth callbacks.
 */

import { createServer } from 'http';
import { URL } from 'url';
import { handleCopilotOAuthCallback } from './copilot-oauth';

export interface OAuthCallbackData {
  code: string;
  state: string;
  profileName: string;
}

export class OAuthServer {
  // biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
  private server: any;
  private port: number;
  private pendingCallbacks: Map<string, OAuthCallbackData> = new Map();

  constructor(port: number = 3000) {
    this.port = port;
    this.server = null;
  }

  /**
   * Start the OAuth callback server
   */
  async start(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.server = createServer(async (req, res) => {
          await this.handleRequest(req, res);
        });

        this.server.listen(this.port, () => {
          resolve();
        });

        this.server.on('error', (error: Error) => {
          console.error('[OAuth Server] Server error:', error);
          reject(error);
        });
      } catch (error) {
        reject(error);
      }
    });
  }

  /**
   * Stop the OAuth server
   */
  stop(): Promise<void> {
    return new Promise((resolve) => {
      if (this.server) {
        this.server.close(() => {
          this.server = null;
          resolve();
        });
      } else {
        resolve();
      }
    });
  }

  /**
   * Handle incoming HTTP requests
   */
  // biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
  private async handleRequest(req: any, res: any): Promise<void> {
    // biome-ignore lint/style/noNonNullAssertion: value is guaranteed by context
    const url = new URL(req.url!, `http://localhost:${this.port}`);

    // CORS restricted to localhost only
    const origin = req.headers.origin;
    if (origin && (origin.startsWith('http://localhost:') || origin.startsWith('http://127.0.0.1:'))) {
      res.setHeader('Access-Control-Allow-Origin', origin);
    }
    res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
    // Security headers
    res.setHeader('X-Content-Type-Options', 'nosniff');
    res.setHeader('X-Frame-Options', 'DENY');
    res.setHeader('Cache-Control', 'no-store');

    if (req.method === 'OPTIONS') {
      res.writeHead(200);
      res.end();
      return;
    }

    if (req.method === 'GET' && url.pathname === '/oauth/callback') {
      await this.handleOAuthCallback(req, res);
    } else if (req.method === 'GET' && url.pathname === '/oauth/status') {
      this.handleStatusCheck(req, res);
    } else {
      // 404 for unknown routes
      res.writeHead(404, { 'Content-Type': 'text/plain' });
      res.end('Not Found');
    }
  }

  /**
   * Handle OAuth callback from GitHub
   */
  // biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
  private async handleOAuthCallback(req: any, res: any): Promise<void> {
    // biome-ignore lint/style/noNonNullAssertion: value is guaranteed by context
    const url = new URL(req.url!, `http://localhost:${this.port}${req.url}`);
    const code = url.searchParams.get('code');
    const state = url.searchParams.get('state');
    const error = url.searchParams.get('error');
    const errorDescription = url.searchParams.get('error_description');

    if (error) {
      // OAuth error occurred
      const html = this.generateErrorPage(error, errorDescription || 'Unknown error occurred');
      res.writeHead(400, { 'Content-Type': 'text/html' });
      res.end(html);
      return;
    }

    if (!code || !state) {
      const html = this.generateErrorPage('missing_parameters', 'Missing authorization code or state parameter');
      res.writeHead(400, { 'Content-Type': 'text/html' });
      res.end(html);
      return;
    }

    try {
      // Get profile name from state or pending callbacks
      let profileName: string;
      
      // Check if we have a pending callback for this state
      const pendingCallback = this.pendingCallbacks.get(state);
      if (pendingCallback) {
        profileName = pendingCallback.profileName;
        this.pendingCallbacks.delete(state);
      } else {
        // Try to extract profile name from state (base64 encoded)
        try {
          const stateData = Buffer.from(state, 'hex').toString('utf-8');
          const parsed = JSON.parse(stateData);
          profileName = parsed.profileName || 'Default';
        } catch {
          profileName = 'Default';
        }
      }

      // Handle the OAuth callback
      const result = await handleCopilotOAuthCallback(code, state, profileName);

      if (result.success) {
        const html = this.generateSuccessPage(result.username || 'Unknown', result.profileName || profileName);
        res.writeHead(200, { 'Content-Type': 'text/html' });
        res.end(html);
      } else {
        const html = this.generateErrorPage('oauth_failed', result.error || 'OAuth authentication failed');
        res.writeHead(400, { 'Content-Type': 'text/html' });
        res.end(html);
      }
    } catch (error) {
      console.error('[OAuth Server] OAuth callback error:', error);
      const html = this.generateErrorPage('server_error', 'Server error during OAuth callback');
      res.writeHead(500, { 'Content-Type': 'text/html' });
      res.end(html);
    }
  }

  /**
   * Handle status check
   */
  // biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
  private handleStatusCheck(_req: any, res: any): void {
    const status = {
      server: 'running',
      port: this.port,
      pendingCallbacks: this.pendingCallbacks.size,
    };
    
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify(status, null, 2));
  }

  /**
   * Store a pending OAuth callback
   */
  storePendingCallback(state: string, callbackData: OAuthCallbackData): void {
    this.pendingCallbacks.set(state, callbackData);
  }

  /**
   * Generate success HTML page
   */
  private generateSuccessPage(username: string, profileName: string): string {
    return `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GitHub Copilot - Authentication Successful</title>
    <style>
      body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        margin: 0;
        height: 100vh;
        display: flex;
        align-items: center;
        justify-content: center;
        text-align: center;
      }
      .container {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        border-radius: 20px;
        padding: 40px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        max-width: 500px;
      }
      .icon {
        font-size: 48px;
        margin-bottom: 20px;
      }
      h1 {
        margin: 0 0 10px 0;
        font-size: 24px;
        font-weight: 600;
      }
      p {
        margin: 10px 0;
        opacity: 0.9;
        line-height: 1.5;
      }
      .close-hint {
        margin-top: 30px;
        font-size: 14px;
        opacity: 0.7;
      }
    </style>
  </head>
  <body>
    <div class="container">
      <div class="icon">✅</div>
      <h1>Authentication Successful!</h1>
      <p><strong>${username}</strong> has been authenticated for GitHub Copilot</p>
      <p>Profile: <em>${profileName}</em></p>
      <p class="close-hint">You can now close this window and return to WorkPilot AI</p>
    </div>
  </body>
</html>
    `;
  }

  /**
   * Generate error HTML page
   */
  private generateErrorPage(errorType: string, message: string): string {
    return `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GitHub Copilot - Authentication Error</title>
    <style>
      body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
        color: white;
        margin: 0;
        height: 100vh;
        display: flex;
        align-items: center;
        justify-content: center;
        text-align: center;
      }
      .container {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        border-radius: 20px;
        padding: 40px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        max-width: 500px;
      }
      .icon {
        font-size: 48px;
        margin-bottom: 20px;
      }
      h1 {
        margin: 0 0 10px 0;
        font-size: 24px;
        font-weight: 600;
      }
      p {
        margin: 10px 0;
        opacity: 0.9;
        line-height: 1.5;
      }
      .error-type {
        background: rgba(255, 255, 255, 0.2);
        padding: 4px 8px;
        border-radius: 4px;
        font-family: monospace;
        font-size: 12px;
        margin-bottom: 10px;
      }
      .close-hint {
        margin-top: 30px;
        font-size: 14px;
        opacity: 0.7;
      }
    </style>
  </head>
  <body>
    <div class="container">
      <div class="icon">❌</div>
      <h1>Authentication Failed</h1>
      <div class="error-type">${errorType}</div>
      <p>${message}</p>
      <p class="close-hint">You can close this window and try again</p>
    </div>
  </body>
</html>
    `;
  }
}

// Global OAuth server instance
let oauthServer: OAuthServer | null = null;

/**
 * Get or create the OAuth server instance
 */
export function getOAuthServer(): OAuthServer {
  if (!oauthServer) {
    oauthServer = new OAuthServer(3000);
  }
  return oauthServer;
}

/**
 * Start the OAuth server if not already running
 */
export async function ensureOAuthServerRunning(): Promise<void> {
  const server = getOAuthServer();
  
  // Check if server is already running
  try {
    const response = await fetch('http://localhost:3000/oauth/status');
    if (response.ok) {
      return;
    }
  } catch (_error) {
    await server.start();
  }
}
