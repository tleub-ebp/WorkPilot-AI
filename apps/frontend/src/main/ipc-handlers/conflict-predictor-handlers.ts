/**
 * Conflict Predictor IPC Handlers
 * 
 * Handles IPC communication for the Conflict Predictor feature
 */

import { app, ipcMain } from 'electron';
import { spawn, ChildProcess } from 'node:child_process';
import { join } from 'node:path';
import { existsSync } from 'node:fs';
import { projectStore } from '../project-store';
import { getConfiguredPythonPath } from '../python-env-manager';
import { parsePythonCommand } from '../python-detector';

interface ConflictPredictorRequest {
  projectId: string;
}

export function setupConflictPredictorHandlers() {
  let currentProcess: ChildProcess | null = null;

  // Kill existing process when starting a new one
  const killExistingProcess = () => {
    if (currentProcess) {
      currentProcess.kill('SIGTERM');
      currentProcess = null;
    }
  };

  // Resolve backend path once (same logic as agent-process.ts)
  const getBackendPath = (): string => {
    const candidates = [
      ...(app.isPackaged ? [join(process.resourcesPath, 'backend')] : []),
      join(__dirname, '..', '..', '..', 'backend'),
      join(app.getAppPath(), '..', 'backend'),
      join(process.cwd(), 'apps', 'backend'),
    ];
    return candidates.find((p) => existsSync(p)) ?? candidates.at(-1) ?? candidates[0];
  };

  // Handle conflict predictor request
  ipcMain.handle('run-conflict-prediction', async (event, { projectId }: ConflictPredictorRequest) => {
    return new Promise((resolve, reject) => {
      killExistingProcess();

      const project = projectStore.getProject(projectId);
      if (!project) {
        const errorMessage = `Project not found: ${projectId}`;
        event.sender.send('conflict-predictor-error', errorMessage);
        reject(new Error(errorMessage));
        return;
      }

      const backendPath = getBackendPath();
      const runnerPath = join(backendPath, 'runners', 'conflict_predictor_runner.py');

      const [pythonCommand, pythonBaseArgs] = parsePythonCommand(getConfiguredPythonPath());
      const spawnedProcess = spawn(pythonCommand, [
        ...pythonBaseArgs,
        runnerPath,
        '--project-path', project.path
      ], {
        cwd: backendPath,
        env: {
          ...process.env,
          PYTHONPATH: backendPath
        }
      });

      currentProcess = spawnedProcess;

      // biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
      let result: any = null;
      let stdoutError: string | null = null;
      let stderrOutput = '';

      // Handle stdout events
      spawnedProcess.stdout?.on('data', (data: Buffer) => {
        const output = data.toString();

        const lines = output.split('\n');
        for (const line of lines) {
          if (line.startsWith('CONFLICT_PREDICTOR_EVENT:')) {
            try {
              const eventData = JSON.parse(line.substring('CONFLICT_PREDICTOR_EVENT:'.length));
              event.sender.send('conflict-predictor-event', eventData);
            } catch (e) {
              console.error('Failed to parse conflict predictor event:', e);
            }
          } else if (line.startsWith('CONFLICT_PREDICTOR_RESULT:')) {
            try {
              result = JSON.parse(line.substring('CONFLICT_PREDICTOR_RESULT:'.length));
            } catch (e) {
              console.error('Failed to parse conflict predictor result:', e);
            }
          } else if (line.startsWith('CONFLICT_PREDICTOR_ERROR:')) {
            stdoutError = line.substring('CONFLICT_PREDICTOR_ERROR:'.length);
          }
        }
      });

      // Accumulate stderr for error reporting
      spawnedProcess.stderr?.on('data', (data: Buffer) => {
        stderrOutput += data.toString();
        console.error('Conflict Predictor stderr:', data.toString());
      });

      // Handle process completion
      spawnedProcess.on('close', (code: number | null) => {
        currentProcess = null;

        if (code === 0 && result) {
          event.sender.send('conflict-predictor-complete', result);
          resolve(result);
        } else {
          const errorMessage = stdoutError || stderrOutput.trim() || `Process exited with code ${code}`;
          event.sender.send('conflict-predictor-error', errorMessage);
          reject(new Error(errorMessage));
        }
      });

      // Handle process error
      spawnedProcess.on('error', (err: Error) => {
        currentProcess = null;
        const errorMessage = `Failed to start conflict predictor process: ${err.message}`;
        event.sender.send('conflict-predictor-error', errorMessage);
        reject(new Error(errorMessage));
      });
    });
  });

  // Handle process cancellation
  ipcMain.handle('cancel-conflict-prediction', () => {
    killExistingProcess();
    return true;
  });

  return () => {
    killExistingProcess();
    ipcMain.removeAllListeners('run-conflict-prediction');
    ipcMain.removeAllListeners('cancel-conflict-prediction');
  };
}
