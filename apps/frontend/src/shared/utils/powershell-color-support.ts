/**
 * PowerShell Color Support Utility
 * 
 * Helps diagnose and fix color issues in PowerShell/Windows Terminal
 */

import { supportsColor } from './frontend-colored-logs';

/**
 * Get diagnostic information about color support
 */
export function getColorDiagnostics(): {
  supportsColor: boolean;
  platform: string;
  isTTY: boolean;
  envVars: Record<string, string | undefined>;
  recommendations: string[];
} {
  const recommendations: string[] = [];
  
  // Check DEBUG environment
  const debugEnv = process.env.DEBUG;
  if (!debugEnv || debugEnv !== 'true') {
    recommendations.push('Set DEBUG=true environment variable: $env:DEBUG="true"');
  }
  
  // Check PowerShell specific
  if (process.platform === 'win32') {
    if (!process.env.WT_SESSION && !process.env.ConEmuANSI) {
      recommendations.push('Consider using Windows Terminal for better color support');
    }
    
    // Check if we're in Windows Terminal
    if (process.env.WT_SESSION) {
      recommendations.push('Windows Terminal detected - colors should work');
    } else {
      recommendations.push(
        'Try enabling virtual terminal processing:',
        '  Set-PSReadLineOption -Colors @{Command="Green"}',
        '  Or use: [Console]::OutputEncoding = [System.Text.Encoding]::UTF8'
      );
    }
  }
  
  return {
    supportsColor: supportsColor(),
    platform: process.platform,
    isTTY: process.stdout.isTTY,
    envVars: {
      DEBUG: debugEnv,
      NO_COLOR: process.env.NO_COLOR,
      FORCE_COLOR: process.env.FORCE_COLOR,
      TERM: process.env.TERM,
      WT_SESSION: process.env.WT_SESSION,
      ConEmuANSI: process.env.ConEmuANSI,
      PSModulePath: process.env.PSModulePath,
    },
    recommendations
  };
}

/**
 * Force enable colors for Windows PowerShell
 */
export function forceEnableWindowsColors(): boolean {
  if (process.platform !== 'win32') return false;
  
  try {
    // Try to enable virtual terminal processing
    if (process.stdout?.isTTY) {
      // This is a workaround for Windows PowerShell color issues
      process.env.FORCE_COLOR = '1';
      return true;
    }
  } catch (error) {
    console.error('Failed to enable Windows colors:', error);
  }
  
  return false;
}

/**
 * Print color diagnostics
 */
export function printColorDiagnostics(): void {
  const diagnostics = getColorDiagnostics();
  
  console.log('=== Frontend Color Diagnostics ===');
  console.log(`Platform: ${diagnostics.platform}`);
  console.log(`TTY Support: ${diagnostics.isTTY}`);
  console.log(`Color Support: ${diagnostics.supportsColor}`);
  console.log('\nEnvironment Variables:');
  
  Object.entries(diagnostics.envVars).forEach(([key, value]) => {
    console.log(`  ${key}: ${value || 'undefined'}`);
  });
  
  if (diagnostics.recommendations.length > 0) {
    console.log('\nRecommendations:');
    diagnostics.recommendations.forEach((rec, index) => {
      console.log(`  ${index + 1}. ${rec}`);
    });
  }
  
  console.log('\n=== Test Colors ===');
  console.log('\x1b[31mRed\x1b[0m, \x1b[32mGreen\x1b[0m, \x1b[33mYellow\x1b[0m, \x1b[34mBlue\x1b[0m, \x1b[35mMagenta\x1b[0m, \x1b[36mCyan\x1b[0m');
  console.log('If you see colors above, the terminal supports them');
}
