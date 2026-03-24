/**
 * Global type declarations for Electron main process
 */

import { BrowserWindow } from 'electron';

declare global {
  var mainWindow: BrowserWindow | null;
}
