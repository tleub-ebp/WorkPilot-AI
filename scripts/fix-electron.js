// scripts/fix-electron.js
// Automates Electron binary repair for Windows users
const fs = require('fs');
const path = require('path');
const https = require('https');
const unzipper = require('unzipper');

const distDir = path.join(__dirname, '../apps/frontend/node_modules/electron/dist');
const exePath = path.join(distDir, 'electron.exe');
const pathTxt = path.join(__dirname, '../apps/frontend/node_modules/electron/path.txt');
const zipUrl = 'https://github.com/electron/electron/releases/download/v40.0.0/electron-v40.0.0-win32-x64.zip';

function downloadAndExtract(url, destDir, cb) {
  https.get(url, (res) => {
    if (res.statusCode !== 200) {
      cb(new Error('Failed to download Electron zip: ' + res.statusCode));
      return;
    }
    res.pipe(unzipper.Extract({ path: destDir }))
      .on('close', cb)
      .on('error', cb);
  }).on('error', cb);
}

function ensureElectronBinary() {
  if (fs.existsSync(exePath)) {
    console.log('✔ Electron binary already present.');
    return;
  }
  if (!fs.existsSync(distDir)) {
    fs.mkdirSync(distDir, { recursive: true });
  }
  console.log('⬇ Downloading Electron binary...');
  downloadAndExtract(zipUrl, distDir, (err) => {
    if (err) {
      console.error('❌ Failed to download or extract Electron:', err.message);
      process.exit(1);
    }
    if (!fs.existsSync(exePath)) {
      console.error('❌ electron.exe not found after extraction.');
      process.exit(1);
    }
    fs.writeFileSync(pathTxt, 'electron.exe');
    console.log('✔ Electron binary installed and path.txt created.');
  });
}

ensureElectronBinary();
