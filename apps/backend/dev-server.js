// Cross-platform backend dev server launcher for pnpm
// Ensures Python venv is activated and dependencies are installed before running Uvicorn

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const isWin = process.platform === 'win32';
const venvDir = path.resolve(__dirname, '../../.venv');
const requirements = path.resolve(__dirname, 'requirements.txt');

function venvPython() {
  if (isWin) {
    return path.join(venvDir, 'Scripts', 'python.exe');
  } else {
    return path.join(venvDir, 'bin', 'python');
  }
}

function venvActivateCmd() {
  if (isWin) {
    return path.join(venvDir, 'Scripts', 'activate.bat');
  } else {
    return `. ${path.join(venvDir, 'bin', 'activate')}`;
  }
}

function ensureVenv(cb) {
  if (!fs.existsSync(venvPython())) {
    console.log('[INFO] Creating Python venv...');
    const py = isWin ? 'python' : 'python3';
    const proc = spawn(py, ['-m', 'venv', venvDir], { stdio: 'inherit' });
    proc.on('exit', (code) => {
      if (code === 0) cb();
      else process.exit(code);
    });
  } else {
    cb();
  }
}

function ensureDeps(cb) {
  const pip = venvPython();
  const proc = spawn(pip, ['-m', 'pip', 'install', '-r', requirements], { stdio: 'inherit' });
  proc.on('exit', (code) => {
    if (code === 0) cb();
    else process.exit(code);
  });
}

function runUvicorn() {
  const uvicornArgs = ['-m', 'uvicorn', 'provider_api:app', '--host', '127.0.0.1', '--port', '9000', '--reload'];
  const proc = spawn(venvPython(), uvicornArgs, { stdio: 'inherit', cwd: __dirname });
  proc.on('exit', (code) => process.exit(code));
}

ensureVenv(() => ensureDeps(runUvicorn));
