import { spawn, type ChildProcess } from 'node:child_process';
import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs';
import path from 'node:path';
import net from 'node:net';
import { EventEmitter } from 'node:events';
import { app } from 'electron';

/**
 * Detected project configuration for the App Emulator.
 */
export interface AppEmulatorConfig {
  type: string;           // 'web' | 'cli' | 'desktop'
  framework: string;      // 'vite' | 'next' | 'django' | 'flask' | etc.
  startCommand: string;   // 'npm run dev', 'python manage.py runserver', etc.
  port: number;           // 3000, 5173, 8000, etc.
  isWeb: boolean;         // Whether the app can be previewed in an iframe
  projectDir?: string;    // Resolved project directory
}

/**
 * Service for App Emulator — manages dev server lifecycle.
 *
 * Events emitted:
 * - 'status' (status: string) — Status update message
 * - 'ready' (url: string) — Server is ready at URL
 * - 'output' (line: string) — Server stdout/stderr line
 * - 'error' (error: string) — Error message
 * - 'stopped' () — Server was stopped
 * - 'config' (config: AppEmulatorConfig) — Project detection result
 */
export class AppEmulatorService extends EventEmitter {
  private activeServerProcess: ChildProcess | null = null;
  private detectionProcess: ChildProcess | null = null;
  private currentConfig: AppEmulatorConfig | null = null;
  private serverUrl: string | null = null;
  private pythonPath = 'python';
  private autoBuildSourcePath: string | null = null;

  /**
   * Configure paths for Python and auto-claude source.
   */
  configure(pythonPath?: string, autoBuildSourcePath?: string): void {
    if (pythonPath) {
      this.pythonPath = pythonPath;
    }
    if (autoBuildSourcePath) {
      this.autoBuildSourcePath = autoBuildSourcePath;
    }
  }

  /**
   * Get the auto-build source path.
   * Uses the same resolution strategy as agent-process.ts.
   */
  private getAutoBuildSourcePath(): string | null {
    if (this.autoBuildSourcePath && existsSync(this.autoBuildSourcePath)) {
      return this.autoBuildSourcePath;
    }

    const possiblePaths = [
      // Packaged app: backend is in extraResources (process.resourcesPath/backend)
      ...(app.isPackaged ? [path.join(process.resourcesPath, 'backend')] : []),
      // Dev mode: from dist/main -> ../../backend (apps/frontend/out/main -> apps/backend)
      path.resolve(__dirname, '..', '..', '..', 'backend'),
      // Alternative: from app root -> apps/backend
      path.resolve(app.getAppPath(), '..', 'backend'),
      // If running from repo root with apps structure
      path.resolve(process.cwd(), 'apps', 'backend'),
    ];

    for (const p of possiblePaths) {
      const runnerPath = path.join(p, 'runners', 'app_emulator_runner.py');
      if (existsSync(runnerPath)) {
        this.autoBuildSourcePath = p;
        return p;
      }
    }

    return null;
  }

  /**
   * Detect project type. Uses fast inline JS detection first,
   * falls back to Python runner for advanced cases.
   */
  async detectProject(projectDirRaw: string): Promise<AppEmulatorConfig> {
    // Decode URI-encoded paths (e.g. spaces stored as %20)
    const projectDir = decodeURIComponent(projectDirRaw);
    console.log('[AppEmulator] detectProject called with projectDir:', projectDir, '(raw:', projectDirRaw, ')');

    if (!existsSync(projectDir)) {
      throw new Error(`Project directory not found: ${projectDir}`);
    }

    // Cancel any existing detection
    if (this.detectionProcess) {
      this.detectionProcess.kill();
      this.detectionProcess = null;
    }

    // Try fast inline JS detection first (no Python needed)
    const jsResult = this.detectProjectInline(projectDir);
    console.log('[AppEmulator] Inline detection result:', jsResult);
    if (jsResult) {
      // Use subdirectory projectDir if detection found a nested project, otherwise use root
      const resolvedProjectDir = (jsResult as any).projectDir || projectDir;
      const config: AppEmulatorConfig = { ...jsResult, projectDir: resolvedProjectDir };
      this.currentConfig = config;
      this.emit('config', config);
      return config;
    }

    // Fallback: Python runner
    return this.detectProjectViaPython(projectDir);
  }

  /**
   * Fast inline detection — handles common project types without Python.
   */
  private detectProjectInline(projectDir: string): Omit<AppEmulatorConfig, 'projectDir'> | null {
    // Node.js / frontend projects
    const pkgPath = path.join(projectDir, 'package.json');
    console.log('[AppEmulator] Checking package.json at:', pkgPath, 'exists:', existsSync(pkgPath));
    if (existsSync(pkgPath)) {
      try {
        const pkg = JSON.parse(readFileSync(pkgPath, 'utf-8'));
        const scripts = pkg.scripts ?? {};
        const deps = { ...(pkg.dependencies ?? {}), ...(pkg.devDependencies ?? {}) };

        let framework = 'node';
        let type = 'web';
        let port = 3000;

        if ('next' in deps) { framework = 'next'; port = 3000; }
        else if ('nuxt' in deps || 'nuxt3' in deps) { framework = 'nuxt'; port = 3000; }
        else if ('react-scripts' in deps) { framework = 'create-react-app'; port = 3000; }
        else if ('vite' in deps) { framework = 'vite'; port = 5173; }
        else if ('@angular/core' in deps) { framework = 'angular'; port = 4200; }
        else if ('vue' in deps && !('vite' in deps)) { framework = 'vue-cli'; port = 8080; }
        else if ('svelte' in deps || '@sveltejs/kit' in deps) { framework = 'svelte'; port = 5173; }
        else if ('electron' in deps) { framework = 'electron'; type = 'desktop'; port = 0; }

        // Detect start command from scripts
        let startCommand = '';
        const pm = this.detectPackageManager(projectDir);
        for (const name of ['dev', 'start:dev', 'serve', 'start']) {
          if (name in scripts) {
            startCommand = name === 'start' ? `${pm} start` : `${pm} run ${name}`;
            break;
          }
        }
        if (!startCommand && Object.keys(scripts).length > 0) {
          const first = Object.keys(scripts)[0];
          startCommand = `${pm} run ${first}`;
        }

        return { type, framework, startCommand, port, isWeb: type === 'web' };
      } catch {
        // JSON parse error — skip
      }
    }

    // Python projects
    const hasPyproject = existsSync(path.join(projectDir, 'pyproject.toml'));
    const hasRequirements = existsSync(path.join(projectDir, 'requirements.txt'));
    const hasManagePy = existsSync(path.join(projectDir, 'manage.py'));
    const hasAppPy = existsSync(path.join(projectDir, 'app.py'));
    const hasMainPy = existsSync(path.join(projectDir, 'main.py'));

    if (hasPyproject || hasRequirements || hasManagePy || hasAppPy || hasMainPy) {
      let depsText = '';
      try {
        if (hasRequirements) depsText += readFileSync(path.join(projectDir, 'requirements.txt'), 'utf-8').toLowerCase();
        if (hasPyproject) depsText += '\n' + readFileSync(path.join(projectDir, 'pyproject.toml'), 'utf-8').toLowerCase();
      } catch { /* ignore */ }

      if (hasManagePy || depsText.includes('django')) {
        return { type: 'web', framework: 'django', startCommand: 'python manage.py runserver', port: 8000, isWeb: true };
      }
      if (depsText.includes('fastapi')) {
        const main = hasAppPy ? 'app:app' : 'main:app';
        return { type: 'web', framework: 'fastapi', startCommand: `uvicorn ${main} --reload --port 8000`, port: 8000, isWeb: true };
      }
      if (depsText.includes('flask')) {
        const entry = hasAppPy ? 'app.py' : 'main.py';
        return { type: 'web', framework: 'flask', startCommand: `python ${entry}`, port: 5000, isWeb: true };
      }
      if (depsText.includes('streamlit')) {
        const entry = hasAppPy ? 'app.py' : 'main.py';
        return { type: 'web', framework: 'streamlit', startCommand: `streamlit run ${entry}`, port: 8501, isWeb: true };
      }
      const entry = hasMainPy ? 'main.py' : (hasAppPy ? 'app.py' : '');
      if (entry) {
        return { type: 'cli', framework: 'python', startCommand: `python ${entry}`, port: 0, isWeb: false };
      }
    }

    // Go projects
    if (existsSync(path.join(projectDir, 'go.mod'))) {
      return { type: 'web', framework: 'go', startCommand: 'go run .', port: 8080, isWeb: true };
    }

    // Rust projects
    if (existsSync(path.join(projectDir, 'Cargo.toml'))) {
      return { type: 'cli', framework: 'rust', startCommand: 'cargo run', port: 0, isWeb: false };
    }

    // Docker projects
    if (existsSync(path.join(projectDir, 'docker-compose.yml')) || existsSync(path.join(projectDir, 'docker-compose.yaml'))) {
      return { type: 'web', framework: 'docker-compose', startCommand: 'docker-compose up', port: 3000, isWeb: true };
    }
    if (existsSync(path.join(projectDir, 'Dockerfile'))) {
      return { type: 'web', framework: 'docker', startCommand: 'docker build -t app . && docker run -p 3000:3000 app', port: 3000, isWeb: true };
    }

    // .NET projects (*.sln at root)
    try {
      const rootFiles = readdirSync(projectDir);
      if (rootFiles.some(f => f.endsWith('.sln'))) {
        // .NET solution — look for a frontend project with package.json in subdirectories
        const frontendResult = this.findFrontendInSubdirs(projectDir, 3);
        if (frontendResult) return frontendResult;

        // Pure .NET backend — use dotnet run
        return { type: 'web', framework: 'dotnet', startCommand: 'dotnet run', port: 5000, isWeb: true };
      }
    } catch { /* ignore */ }

    // Last resort: scan subdirectories (up to 3 levels deep) for package.json
    const subResult = this.findFrontendInSubdirs(projectDir, 3);
    if (subResult) return subResult;

    return null;
  }

  /**
   * Recursively search subdirectories for a frontend project (package.json with scripts).
   */
  private findFrontendInSubdirs(dir: string, maxDepth: number): Omit<AppEmulatorConfig, 'projectDir'> | null {
    if (maxDepth <= 0) return null;

    try {
      const entries = readdirSync(dir);
      for (const entry of entries) {
        // Skip hidden dirs, node_modules, and common non-project dirs
        if (entry.startsWith('.') || entry === 'node_modules' || entry === 'dist' || entry === 'build' || entry === 'bin' || entry === 'obj') continue;

        const fullPath = path.join(dir, entry);
        try {
          if (!statSync(fullPath).isDirectory()) continue;
        } catch { continue; }

        // Check for package.json in this subdirectory
        const pkgPath = path.join(fullPath, 'package.json');
        if (existsSync(pkgPath)) {
          try {
            const pkg = JSON.parse(readFileSync(pkgPath, 'utf-8'));
            const scripts = pkg.scripts ?? {};
            // Only consider it if it has dev/start scripts (not just a lockfile)
            if (Object.keys(scripts).length > 0) {
              const deps = { ...(pkg.dependencies ?? {}), ...(pkg.devDependencies ?? {}) };

              let framework = 'node';
              let type = 'web';
              let port = 3000;

              if ('@angular/core' in deps) { framework = 'angular'; port = 4200; }
              else if ('next' in deps) { framework = 'next'; port = 3000; }
              else if ('nuxt' in deps || 'nuxt3' in deps) { framework = 'nuxt'; port = 3000; }
              else if ('react-scripts' in deps) { framework = 'create-react-app'; port = 3000; }
              else if ('vite' in deps) { framework = 'vite'; port = 5173; }
              else if ('vue' in deps && !('vite' in deps)) { framework = 'vue-cli'; port = 8080; }
              else if ('svelte' in deps || '@sveltejs/kit' in deps) { framework = 'svelte'; port = 5173; }
              else if ('electron' in deps) { framework = 'electron'; type = 'desktop'; port = 0; }

              const pm = this.detectPackageManager(fullPath);
              let startCommand = '';
              for (const name of ['dev', 'start:dev', 'serve', 'start']) {
                if (name in scripts) {
                  startCommand = name === 'start' ? `${pm} start` : `${pm} run ${name}`;
                  break;
                }
              }
              if (!startCommand) {
                const first = Object.keys(scripts)[0];
                startCommand = `${pm} run ${first}`;
              }

              console.log('[AppEmulator] Found frontend project in subdirectory:', fullPath, 'framework:', framework);
              // Return config with projectDir pointing to the subdirectory where package.json lives
              return { type, framework, startCommand, port, isWeb: type === 'web', projectDir: fullPath } as any;
            }
          } catch { /* ignore parse error */ }
        }

        // Recurse deeper
        const deeper = this.findFrontendInSubdirs(fullPath, maxDepth - 1);
        if (deeper) return deeper;
      }
    } catch { /* ignore readdir error */ }

    return null;
  }

  /**
   * Detect the package manager from lock files.
   */
  private detectPackageManager(projectDir: string): string {
    if (existsSync(path.join(projectDir, 'pnpm-lock.yaml'))) return 'pnpm';
    if (existsSync(path.join(projectDir, 'yarn.lock'))) return 'yarn';
    if (existsSync(path.join(projectDir, 'bun.lockb')) || existsSync(path.join(projectDir, 'bun.lock'))) return 'bun';
    return 'npm';
  }

  /**
   * Fallback: Detect project type via Python runner.
   */
  private detectProjectViaPython(projectDir: string): Promise<AppEmulatorConfig> {
    const autoBuildSource = this.getAutoBuildSourcePath();
    if (!autoBuildSource) {
      throw new Error(`Could not detect project type in: ${projectDir}`);
    }

    const runnerPath = path.join(autoBuildSource, 'runners', 'app_emulator_runner.py');
    if (!existsSync(runnerPath)) {
      throw new Error(`Could not detect project type in: ${projectDir}`);
    }

    return new Promise((resolve, reject) => {
      const proc = spawn(this.pythonPath, [runnerPath, '--project-dir', projectDir], {
        cwd: autoBuildSource,
        env: { ...process.env } as Record<string, string>,
      });

      this.detectionProcess = proc;
      let stdout = '';
      let stderr = '';

      proc.stdout?.on('data', (data: Buffer) => {
        stdout += data.toString('utf-8');
      });

      proc.stderr?.on('data', (data: Buffer) => {
        stderr += data.toString('utf-8');
      });

      proc.on('close', (code) => {
        this.detectionProcess = null;

        // Parse the result from stdout
        const marker = '__APP_EMULATOR_RESULT__:';
        const markerIdx = stdout.indexOf(marker);

        if (markerIdx >= 0) {
          try {
            const jsonStr = stdout.substring(markerIdx + marker.length).trim();
            const result = JSON.parse(jsonStr);

            if (result.success) {
              const config: AppEmulatorConfig = {
                type: result.type,
                framework: result.framework,
                startCommand: result.startCommand,
                port: result.port,
                isWeb: result.isWeb,
                projectDir,
              };
              this.currentConfig = config;
              this.emit('config', config);
              resolve(config);
            } else {
              reject(new Error(result.error || `Could not detect project type in: ${projectDir}`));
            }
          } catch (parseErr) {
            reject(new Error(`Failed to parse detection result: ${parseErr}`));
          }
        } else {
          reject(new Error(`Detection failed (exit code ${code}): ${stderr.slice(-500)}`));
        }
      });

      proc.on('error', (err) => {
        this.detectionProcess = null;
        reject(new Error(`Failed to start detection: ${err.message}`));
      });
    });
  }

  /**
   * Start the dev server with the given config.
   */
  async startServer(config: AppEmulatorConfig): Promise<void> {
    // Stop any existing server
    this.stopServer();

    this.currentConfig = config;
    const projectDir = config.projectDir || process.cwd();

    if (!config.startCommand) {
      this.emit('error', 'No start command configured');
      return;
    }

    this.emit('status', `Starting: ${config.startCommand}`);

    // Parse command
    const isWindows = process.platform === 'win32';
    const shell = isWindows ? true : undefined;
    const [cmd, ...args] = config.startCommand.split(' ');

    const proc = spawn(cmd, args, {
      cwd: projectDir,
      env: { ...process.env, BROWSER: 'none', PORT: String(config.port) } as Record<string, string>,
      shell,
      stdio: ['ignore', 'pipe', 'pipe'],
    });

    this.activeServerProcess = proc;

    proc.stdout?.on('data', (data: Buffer) => {
      const text = data.toString('utf-8');
      for (const line of text.split('\n')) {
        if (line.trim()) {
          this.emit('output', line);
        }
      }
    });

    proc.stderr?.on('data', (data: Buffer) => {
      const text = data.toString('utf-8');
      for (const line of text.split('\n')) {
        if (line.trim()) {
          this.emit('output', line);
        }
      }
    });

    proc.on('close', (code) => {
      this.activeServerProcess = null;
      this.serverUrl = null;
      if (code !== null && code !== 0) {
        this.emit('error', `Server exited with code ${code}`);
      }
      this.emit('stopped');
    });

    proc.on('error', (err) => {
      this.activeServerProcess = null;
      this.serverUrl = null;
      this.emit('error', `Failed to start server: ${err.message}`);
    });

    // Wait for the port to become available (for web apps)
    if (config.isWeb && config.port > 0) {
      try {
        await this.waitForPort(config.port, 30000);
        this.serverUrl = `http://localhost:${config.port}`;
        this.emit('ready', this.serverUrl);
      } catch {
        // Server might still be starting, emit what we have
        if (this.activeServerProcess && !this.activeServerProcess.killed) {
          this.serverUrl = `http://localhost:${config.port}`;
          this.emit('ready', this.serverUrl);
        }
      }
    }
  }

  /**
   * Wait for a port to accept connections.
   */
  private waitForPort(port: number, timeout: number): Promise<void> {
    return new Promise((resolve, reject) => {
      const startTime = Date.now();

      const tryConnect = () => {
        if (Date.now() - startTime > timeout) {
          reject(new Error(`Timeout waiting for port ${port}`));
          return;
        }

        const socket = new net.Socket();
        socket.setTimeout(1000);

        socket.on('connect', () => {
          socket.destroy();
          resolve();
        });

        socket.on('error', () => {
          socket.destroy();
          setTimeout(tryConnect, 500);
        });

        socket.on('timeout', () => {
          socket.destroy();
          setTimeout(tryConnect, 500);
        });

        socket.connect(port, '127.0.0.1');
      };

      tryConnect();
    });
  }

  /**
   * Stop the dev server.
   */
  stopServer(): void {
    if (!this.activeServerProcess) return;

    try {
      // On Windows, use taskkill to kill the entire process tree
      if (process.platform === 'win32' && this.activeServerProcess.pid) {
        spawn('taskkill', ['/pid', String(this.activeServerProcess.pid), '/f', '/t'], {
          stdio: 'ignore',
        });
      } else {
        this.activeServerProcess.kill('SIGTERM');
      }
    } catch {
      // Process might already be dead
    }

    this.activeServerProcess = null;
    this.serverUrl = null;
    this.currentConfig = null;
    this.emit('stopped');
  }

  /**
   * Check if a server is currently running.
   */
  isRunning(): boolean {
    return this.activeServerProcess !== null && !this.activeServerProcess.killed;
  }

  /**
   * Get the current server URL.
   */
  getUrl(): string | null {
    return this.serverUrl;
  }

  /**
   * Get current configuration.
   */
  getConfig(): AppEmulatorConfig | null {
    return this.currentConfig;
  }

  /**
   * Cancel any active detection.
   */
  cancelDetection(): void {
    if (this.detectionProcess) {
      this.detectionProcess.kill();
      this.detectionProcess = null;
    }
  }
}

// Singleton instance
export const appEmulatorService = new AppEmulatorService();
