/**
 * Conflict Predictor IPC Handlers
 * 
 * Handles IPC communication for the Conflict Predictor feature
 */

import { ipcMain } from 'electron';
import { spawn, ChildProcess } from 'child_process';
import { resolve } from 'path';
import { app } from 'electron';

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

  // Handle conflict predictor request
  ipcMain.handle('run-conflict-prediction', async (event, { projectId }: ConflictPredictorRequest) => {
    return new Promise((resolve, reject) => {
      killExistingProcess();

      const backendPath = resolve(app.getAppPath(), 'apps', 'backend');
      const runnerPath = resolve(backendPath, 'runners', 'conflict_predictor_runner.py');

      const spawnedProcess = spawn('python', [
        runnerPath,
        '--project-id', projectId
      ], {
        cwd: backendPath,
        env: {
          ...process.env,
          PYTHONPATH: backendPath
        }
      });

      currentProcess = spawnedProcess;

      let result: any = null;
      let error: string | null = null;

      // Handle stdout events
      spawnedProcess.stdout?.on('data', (data: Buffer) => {
        const output = data.toString();
        
        // Parse conflict predictor events
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
            error = line.substring('CONFLICT_PREDICTOR_ERROR:'.length);
          }
        }
      });

      // Handle stderr
      spawnedProcess.stderr?.on('data', (data: Buffer) => {
        const errorOutput = data.toString();
        console.error('Conflict Predictor stderr:', errorOutput);
        event.sender.send('conflict-predictor-error', errorOutput);
      });

      // Handle process completion
      spawnedProcess.on('close', (code: number | null) => {
        currentProcess = null;
        
        if (code === 0 && result) {
          event.sender.send('conflict-predictor-complete', result);
          resolve(result);
        } else {
          const errorMessage = error || `Process exited with code ${code}`;
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
