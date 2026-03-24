#!/usr/bin/env node
/**
 * Simple packaging script that uses electron-builder directly without Python runtime.
 * This script packages the Electron app with the backend included.
 */

const { spawnSync } = require('node:child_process');

function main() {
  const args = process.argv.slice(2);
  
  // Default platforms if none specified
  if (args.length === 0) {
    args.push('--win', '--mac', '--linux');
  }

  console.log('🚀 Starting packaging for platforms:', args.join(' '));
  
  // Run electron-builder with the provided arguments
  const result = spawnSync('electron-builder', args, {
    stdio: 'inherit',
    shell: true,
    cwd: process.cwd()
  });

  if (result.status !== 0) {
    console.error('❌ Packaging failed');
    process.exit(result.status || 1);
  }

  console.log('✅ Packaging completed successfully');
}

if (require.main === module) {
  main();
}
