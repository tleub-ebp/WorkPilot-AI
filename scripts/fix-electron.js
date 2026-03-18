// Automates Electron binary repair for Windows users
import { existsSync, mkdirSync, writeFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { get } from 'node:https';
import { fileURLToPath } from 'node:url';
import pkg from 'unzipper';

const { extract } = pkg;
const __dirname = dirname(fileURLToPath(import.meta.url));
const distDir = join(__dirname, '../apps/frontend/node_modules/electron/dist');
const exePath = join(distDir, 'electron.exe');
const pathTxt = join(__dirname, '../apps/frontend/node_modules/electron/path.txt');
const zipUrl = 'https://github.com/electron/electron/releases/download/v40.0.0/electron-v40.0.0-win32-x64.zip';

function downloadAndExtract(url, destDir, cb) {
  get(url, (res) => {
    if (res.statusCode !== 200) {
      cb(new Error('Failed to download Electron zip: ' + res.statusCode));
      return;
    }
    res.pipe(extract({ path: destDir }))
      .on('close', cb)
      .on('error', cb);
  }).on('error', cb);
}

function ensureElectronBinary() {
  if (existsSync(exePath)) {
    console.log('✔ Electron binary already present.');
    return;
  }
  if (!existsSync(distDir)) {
    mkdirSync(distDir, { recursive: true });
  }
  console.log('⬇ Downloading Electron binary...');
  downloadAndExtract(zipUrl, distDir, (err) => {
    if (err) {
      console.error('❌ Failed to download or extract Electron:', err.message);
      process.exit(1);
    }
    if (!existsSync(exePath)) {
      console.error('❌ electron.exe not found after extraction.');
      process.exit(1);
    }
    writeFileSync(pathTxt, 'electron.exe');
    console.log('✔ Electron binary installed and path.txt created.');
  });
}

ensureElectronBinary();
