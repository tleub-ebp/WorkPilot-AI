import { spawn, type ChildProcess } from 'node:child_process';
import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs';
import path from 'node:path';
import net from 'node:net';
import http from 'node:http';
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
  /** Synchronous guard — prevents concurrent startServer calls (race condition on port check) */
  private startingInProgress = false;

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
        const deps = { ...(pkg.dependencies), ...(pkg.devDependencies ?? {}) };

        let framework = 'node';
        let type = 'web';
        let port = 3000;

        if ('next' in deps) { framework = 'next'; }
        else if ('nuxt' in deps || 'nuxt3' in deps) { framework = 'nuxt'; }
        else if ('react-scripts' in deps) { framework = 'create-react-app'; }
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

        // If the resolved start command uses SSL (common in ASP.NET Core + Angular templates),
        // fall back to a plain ng serve to avoid missing certificate errors
        if (framework === 'angular' && startCommand) {
          const resolvedScript = scripts['start'] ?? scripts['dev'] ?? '';
          if (typeof resolvedScript === 'string' && resolvedScript.includes('--ssl')) {
            console.log('[AppEmulator] Angular start script uses --ssl, falling back to plain ng serve');
            startCommand = `npx ng serve --port ${port}`;
          }
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
      let entry: string;
      if (hasMainPy) {
        entry = 'main.py';
      } else if (hasAppPy) {
        entry = 'app.py';
      } else {
        entry = '';
      }
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
              // Only create deps object if there are actual dependencies
              const hasDeps = (pkg.dependencies && Object.keys(pkg.dependencies).length > 0) || 
                           (pkg.devDependencies && Object.keys(pkg.devDependencies).length > 0);
              
              // Declare variables outside the conditional
              let framework = 'node';
              let type = 'web';
              let port = 3000;

              // Only proceed with framework detection if there are dependencies
              if (hasDeps) {
                const deps = { ...(pkg.dependencies), ...(pkg.devDependencies ?? {}) };
                if ('@angular/core' in deps) { framework = 'angular'; port = 4200; }
                else if ('next' in deps) { framework = 'next'; }
                else if ('nuxt' in deps || 'nuxt3' in deps) { framework = 'nuxt'; }
                else if ('react-scripts' in deps) { framework = 'create-react-app'; }
                else if ('vite' in deps) { framework = 'vite'; port = 5173; }
                else if ('vue' in deps && !('vite' in deps)) { framework = 'vue-cli'; port = 8080; }
                else if ('svelte' in deps || '@sveltejs/kit' in deps) { framework = 'svelte'; port = 5173; }
                else if ('electron' in deps) { framework = 'electron'; type = 'desktop'; port = 0; }
              }
              // If no dependencies, defaults (node, web, 3000) are already set

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

              // If the start script uses --ssl (ASP.NET Core + Angular templates), fall back to plain ng serve
              if (framework === 'angular' && startCommand) {
                const resolvedScript = scripts['start'] ?? scripts['dev'] ?? '';
                if (typeof resolvedScript === 'string' && resolvedScript.includes('--ssl')) {
                  console.log('[AppEmulator] Angular start script uses --ssl, falling back to plain ng serve');
                  startCommand = `npx ng serve --port ${port}`;
                }
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
    // Synchronous guard — prevents race condition when two calls arrive before either awaits
    if (this.startingInProgress) {
      console.log('[AppEmulator] startServer called while already starting — ignoring');
      return;
    }
    this.startingInProgress = true;

    try {
    // Stop any existing server
    this.stopServer();

    this.currentConfig = config;
    const projectDir = config.projectDir || process.cwd();

    if (!config.startCommand) {
      this.emit('error', 'No start command configured');
      return;
    }

    // Check if something is already running on the configured port
    if (config.isWeb && config.port > 0) {
      const portFree = await this.isPortAvailable(config.port);
      if (!portFree) {
        // Port is occupied — check if there's a working HTTP server we can reuse
        const alreadyServing = await this.isHttpReachable(config.port);
        if (alreadyServing) {
          console.log(`[AppEmulator] Port ${config.port} already has a running server — reusing it`);
          this.serverUrl = `http://localhost:${config.port}`;
          this.emit('status', `Running at ${this.serverUrl}`);
          this.emit('ready', this.serverUrl);
          return;
        }

        // Port occupied but no usable HTTP server — find the next available port directly.
        // Avoid killing the occupying process (unreliable on Windows with node process trees).
        const availablePort = await this.findAvailablePort(config.port + 1);
        this.emit('status', `Port ${config.port} in use — using port ${availablePort} instead`);
        config.startCommand = this.replacePortInCommand(config.startCommand, config.port, availablePort);
        config.port = availablePort;
        this.currentConfig = config;
        this.emit('config', config);
      }
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
      // Release startingInProgress so a retry can start immediately
      this.startingInProgress = false;
      if (code !== null && code !== 0) {
        this.emit('error', `Server exited with code ${code}`);
      }
      this.emit('stopped');
    });

    proc.on('error', (err) => {
      this.activeServerProcess = null;
      this.serverUrl = null;
      this.startingInProgress = false;
      this.emit('error', `Failed to start server: ${err.message}`);
    });

    // Wait for the port to become available (for web apps)
    if (config.isWeb && config.port > 0) {
      try {
        await this.waitForPort(config.port, 60000);
      } catch {
        // Port didn't open in time; bail if the process died
        if (!this.activeServerProcess || this.activeServerProcess.killed) return;
      }

      // After TCP is up, wait for the server to actually serve HTTP (e.g. Angular
      // dev-server binds the port immediately but compiles for 30-60 s before
      // responding with 2xx).  We poll for up to 90 s; if still not 2xx we emit
      // 'ready' anyway so the user at least sees the terminal output.
      await this.waitForHttpSuccess(config.port, 90000);

      if (this.activeServerProcess && !this.activeServerProcess.killed) {
        this.serverUrl = `http://localhost:${config.port}`;
        this.emit('ready', this.serverUrl);
      }
    }
    } finally {
      this.startingInProgress = false;
    }
  }

  /**
   * Replace every occurrence of `oldPort` in a start command with `newPort`.
   * Handles both `--port N` and `PORT=N` forms.
   */
  private replacePortInCommand(cmd: string, oldPort: number, newPort: number): string {
    return cmd.replaceAll(
      new RegExp(String.raw`(--port\s+)${oldPort}|(\bPORT=)${oldPort}`, 'g'),
      (_m: string, p1: string, p2: string) => p1 ? `${p1}${newPort}` : `${p2}${newPort}`,
    );
  }

  /**
   * Quick check: is there an HTTP server responding on this port?
   * Returns true if we get any HTTP response within 1.5 s.
   */
  private isHttpReachable(port: number): Promise<boolean> {
    return new Promise((resolve) => {
      const req = http.get(
        { hostname: '127.0.0.1', port, path: '/', timeout: 1500 },
        (res) => {
          res.resume();
          resolve(true);
        },
      );
      req.on('error', () => resolve(false));
      req.on('timeout', () => { req.destroy(); resolve(false); });
    });
  }

  /**
   * Check if a port is available (not in use).
   * Uses `createServer().listen()` — more reliable than connect() because it
   * actually tries to bind the port rather than just probing it.
   */
  private isPortAvailable(port: number): Promise<boolean> {
    return new Promise((resolve) => {
      const server = net.createServer();
      server.unref(); // don't keep the event loop alive
      server.once('error', () => resolve(false)); // EADDRINUSE → in use
      server.listen(port, '127.0.0.1', () => {
        server.close(() => resolve(true)); // successfully bound → free
      });
    });
  }

  /**
   * Find an available port starting from startPort.
   */
  private async findAvailablePort(startPort: number): Promise<number> {
    let port = startPort;
    while (port < startPort + 20) {
      if (await this.isPortAvailable(port)) return port;
      port++;
    }
    return startPort; // fallback
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

        // Bail out immediately if the process died
        if (!this.activeServerProcess || this.activeServerProcess.killed) {
          resolve();
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
   * Poll the server with an HTTP GET until it responds with a 2xx status code
   * (meaning the app is compiled and actually serving content), or until
   * `timeout` ms elapses, whichever comes first.
   */
  private waitForHttpSuccess(port: number, timeout: number): Promise<void> {
    return new Promise((resolve) => {
      const startTime = Date.now();

      const tryGet = () => {
        // Stop polling if the process died
        if (!this.activeServerProcess || this.activeServerProcess.killed) {
          resolve();
          return;
        }

        if (Date.now() - startTime > timeout) {
          // Timed out — emit ready anyway so the user can see what's happening
          resolve();
          return;
        }

        const req = http.get(
          { hostname: '127.0.0.1', port, path: '/', timeout: 3000 },
          (res) => {
            res.resume(); // drain the response body
            if (res.statusCode !== undefined && res.statusCode < 400) {
              resolve();
            } else {
              // Non-2xx (e.g. still compiling) — retry
              setTimeout(tryGet, 2000);
            }
          },
        );

        req.on('error', () => setTimeout(tryGet, 1000));
        req.on('timeout', () => {
          req.destroy();
          setTimeout(tryGet, 1000);
        });
      };

      tryGet();
    });
  }

  /**
   * Stop the dev server.
   */
  stopServer(): void {
    if (!this.activeServerProcess) return;

    const pid = this.activeServerProcess.pid;
    try {
      // On Windows, use taskkill to kill the entire process tree (including node child procs)
      if (process.platform === 'win32' && pid) {
        // Kill synchronously via taskkill; fire-and-forget is sufficient since we also
        // call killPortProcess before the next start to handle any lingering processes.
        spawn('taskkill', ['/pid', String(pid), '/f', '/t'], { stdio: 'ignore' });
      } else {
        this.activeServerProcess.kill('SIGKILL');
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
