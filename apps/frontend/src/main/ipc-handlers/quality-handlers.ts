/**
 * Quality Scorer IPC Handlers
 * Handles communication between renderer and backend Python Quality Scorer
 */

import { ipcMain, app } from 'electron';
import { spawn } from 'node:child_process';
import path from 'node:path';
import { logger } from '../app-logger';


interface QualityAnalyzeParams {
  files: string[];
  projectDir?: string;
}

interface QualityAnalyzePRParams {
  prNumber: number;
  changedFiles: string[];
  projectDir?: string;
}

export function setupQualityHandlers(): void {
  // Handler: quality:analyze
  ipcMain.handle('quality:analyze', async (_, params: QualityAnalyzeParams) => {
    try {
      logger.info('Quality analysis requested', { files: params.files });

      const projectDir = params.projectDir || process.cwd();
      const backendPath = path.join(app.getAppPath(), '..', '..', 'apps', 'backend');

      // Call Python quality_cli.py script
      return await runQualityAnalysis(params.files, projectDir, backendPath);
    } catch (error) {
      logger.error('Failed to analyze quality', error);
      throw error;
    }
  });

  // Handler: quality:analyze-pr
  ipcMain.handle('quality:analyze-pr', async (_, params: QualityAnalyzePRParams) => {
    try {
      logger.info('PR quality analysis requested', {
        prNumber: params.prNumber,
        files: params.changedFiles
      });

      const projectDir = params.projectDir || process.cwd();
      const backendPath = path.join(app.getAppPath(), '..', '..', 'apps', 'backend');

      // Call Python quality_cli.py script for PR files
      return await runQualityAnalysis(params.changedFiles, projectDir, backendPath);
    } catch (error) {
      logger.error('Failed to analyze PR quality', error);
      throw error;
    }
  });
}

/**
 * Run quality analysis using Python backend
 */
async function runQualityAnalysis(
  files: string[],
  projectDir: string,
  backendPath: string
// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
): Promise<any> {
  return new Promise((resolve, reject) => {
    // Build command to run quality_cli.py
    const scriptPath = path.join(backendPath, '..', '..', 'quality_cli.py');

    // Add backend to PYTHONPATH
    const env = {
      ...process.env,
      PYTHONPATH: backendPath
    };

    const args = [
      scriptPath,
      'score',
      '--files',
      ...files,
      '--project-dir',
      projectDir,
      '--format',
      'json'
    ];

    logger.debug('Running quality analysis', { command: 'python', args });

    const proc = spawn('python', args, {
      cwd: projectDir,
      env
    });

    let stdout = '';
    let stderr = '';

    proc.stdout.on('data', (data) => {
      stdout += data.toString();
    });

    proc.stderr.on('data', (data) => {
      stderr += data.toString();
      logger.warn('Quality analysis stderr', { stderr: data.toString() });
    });

    proc.on('close', (code) => {
      if (code !== 0 && code !== 1) {
        // Code 1 is OK (means quality failed but analysis succeeded)
        logger.error('Quality analysis failed', { code, stderr });
        reject(new Error(`Quality analysis failed with code ${code}: ${stderr}`));
        return;
      }

      try {
        // Parse JSON output from stdout
        // The script outputs the JSON after the initial message
        const jsonStart = stdout.indexOf('{');
        if (jsonStart === -1) {
          throw new Error('No JSON output found');
        }

        const jsonStr = stdout.substring(jsonStart);
        const result = JSON.parse(jsonStr);

        logger.info('Quality analysis completed', {
          score: result.overall_score,
          grade: result.grade,
          issues: result.total_issues
        });

        resolve(result);
      } catch (error) {
        logger.error('Failed to parse quality analysis output', { error, stdout });
        reject(new Error(`Failed to parse output: ${error}`));
      }
    });

    proc.on('error', (error) => {
      logger.error('Failed to spawn quality analysis process', error);
      reject(error);
    });
  });
}

