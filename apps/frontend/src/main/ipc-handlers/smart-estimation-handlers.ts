/**
 * Smart Estimation IPC Handlers
 * 
 * Handles IPC communication for the Smart Estimation feature
 */

import { ipcMain } from 'electron';
import { spawn, ChildProcess } from 'child_process';
import { app } from 'electron';

interface SmartEstimationRequest {
  projectId: string;
  taskDescription: string;
}

export function setupSmartEstimationHandlers() {
  let currentProcess: ChildProcess | null = null;

  // Kill existing process when starting a new one
  const killExistingProcess = () => {
    if (currentProcess) {
      currentProcess.kill('SIGTERM');
      currentProcess = null;
    }
  };

  // Handle smart estimation request
  ipcMain.handle('run-smart-estimation', async (event, { projectId, taskDescription }: SmartEstimationRequest) => {
    return new Promise((resolve, reject) => {
      killExistingProcess();

      const backendPath = resolve(app.getAppPath(), 'apps', 'backend');
      const runnerPath = resolve(backendPath, 'runners', 'smart_estimation_runner.py');

      const spawnedProcess = spawn('python', [
        runnerPath,
        '--project-id', projectId,
        '--task-description', taskDescription
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
        
        // Parse smart estimation events
        const lines = output.split('\n');
        for (const line of lines) {
          if (line.startsWith('SMART_ESTIMATION_EVENT:')) {
            try {
              const eventData = JSON.parse(line.substring('SMART_ESTIMATION_EVENT:'.length));
              event.sender.send('smart-estimation-event', eventData);
            } catch (e) {
              console.error('Failed to parse smart estimation event:', e);
            }
          } else if (line.startsWith('SMART_ESTIMATION_RESULT:')) {
            try {
              result = JSON.parse(line.substring('SMART_ESTIMATION_RESULT:'.length));
            } catch (e) {
              console.error('Failed to parse smart estimation result:', e);
            }
          } else if (line.startsWith('SMART_ESTIMATION_ERROR:')) {
            error = line.substring('SMART_ESTIMATION_ERROR:'.length);
          }
        }
      });

      // Handle stderr
      spawnedProcess.stderr?.on('data', (data: Buffer) => {
        const errorOutput = data.toString();
        console.error('Smart Estimation stderr:', errorOutput);
        event.sender.send('smart-estimation-error', errorOutput);
      });

      // Handle process completion
      spawnedProcess.on('close', (code: number | null) => {
        currentProcess = null;
        
        if (code === 0 && result) {
          event.sender.send('smart-estimation-complete', result);
          resolve(result);
        } else {
          const errorMessage = error || `Process exited with code ${code}`;
          event.sender.send('smart-estimation-error', errorMessage);
          reject(new Error(errorMessage));
        }
      });

      // Handle process error
      spawnedProcess.on('error', (err: Error) => {
        currentProcess = null;
        const errorMessage = `Failed to start smart estimation process: ${err.message}`;
        event.sender.send('smart-estimation-error', errorMessage);
        reject(new Error(errorMessage));
      });
    });
  });

  // Handle process cancellation
  ipcMain.handle('cancel-smart-estimation', () => {
    killExistingProcess();
    return true;
  });

  return () => {
    killExistingProcess();
    ipcMain.removeAllListeners('run-smart-estimation');
    ipcMain.removeAllListeners('cancel-smart-estimation');
  };
}
