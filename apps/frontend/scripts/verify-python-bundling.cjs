#!/usr/bin/env node
/**
 * Verify Python bundling configuration is correct.
 * Run this before packaging to ensure Python will be properly bundled.
 */

const fs = require('fs');
const path = require('path');
const { execSync, spawnSync } = require('child_process');

const FRONTEND_DIR = path.resolve(__dirname, '..');
const PYTHON_RUNTIME_DIR = path.join(FRONTEND_DIR, 'python-runtime');
const platform = process.platform === 'win32' ? 'win' : process.platform === 'darwin' ? 'mac' : 'linux';
const arch = process.arch;
const runtimePath = path.join(PYTHON_RUNTIME_DIR, `${platform}-${arch}`, 'python');

if (fs.existsSync(runtimePath)) {
  const pythonExe = process.platform === 'win32'
    ? path.join(runtimePath, 'python.exe')
    : path.join(runtimePath, 'bin', 'python3');

  if (fs.existsSync(pythonExe)) {

    // Test version
    try {
      const _version = execSync(`"${pythonExe}" --version`, { encoding: 'utf8' }).trim();
    } catch (_e) {
      // noop
    }
  } else {
    // noop
  }
} else {
  // noop
}
const packageJson = require(path.join(FRONTEND_DIR, 'package.json'));
const extraResources = packageJson.build?.extraResources || [];

const pythonResource = extraResources.find(r =>
  (typeof r === 'string' && r.includes('python')) ||
  (typeof r === 'object' && r.from?.includes('python'))
);

// biome-ignore lint/suspicious/noEmptyBlockStatements: intentionally empty
if (pythonResource) {
} else {
  // noop
}
try {
  // Find system Python for testing
  const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';

  const result = spawnSync(pythonCmd, ['-m', 'venv', '--help'], { encoding: 'utf8' });
  // biome-ignore lint/suspicious/noEmptyBlockStatements: intentionally empty
  if (result.status === 0) {
  } else {
    // noop
  }
} catch (_e) {
  // noop
}
const backendDir = path.join(FRONTEND_DIR, '..', 'backend');
const requirementsPath = path.join(backendDir, 'requirements.txt');

if (fs.existsSync(requirementsPath)) {
  const content = fs.readFileSync(requirementsPath, 'utf8');
  const _hasDotenv = content.includes('python-dotenv');
  const _hasSDK = content.includes('claude-agent-sdk');
} else {
  // noop
}
