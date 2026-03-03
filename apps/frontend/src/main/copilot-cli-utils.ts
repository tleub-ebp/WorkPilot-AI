import * as path from 'node:path';
import { getAugmentedEnv, getAugmentedEnvAsync } from './env-utils';
import { getToolPath, getToolPathAsync } from './cli-tool-manager';
import { isWindows, getPathDelimiter } from './platform';

export type CopilotCliInvocation = {
  command: string;    // Path to gh binary
  args: string[];     // ['copilot', ...] prefix for all copilot subcommands
  env: Record<string, string>;
};

function ensureCommandDirInPath(command: string, env: Record<string, string>): Record<string, string> {
  if (!path.isAbsolute(command)) {
    return env;
  }

  const pathSeparator = getPathDelimiter();
  const commandDir = path.dirname(command);
  const currentPath = env.PATH || '';
  const pathEntries = currentPath.split(pathSeparator);
  const normalizedCommandDir = path.normalize(commandDir);
  const hasCommandDir = isWindows()
    ? pathEntries
      .map((entry) => path.normalize(entry).toLowerCase())
      .includes(normalizedCommandDir.toLowerCase())
    : pathEntries
      .map((entry) => path.normalize(entry))
      .includes(normalizedCommandDir);

  if (hasCommandDir) {
    return env;
  }

  return {
    ...env,
    PATH: [commandDir, currentPath].filter(Boolean).join(pathSeparator),
  };
}

/**
 * Returns the Copilot CLI invocation details: gh path, copilot args prefix, and augmented env.
 *
 * Copilot CLI is invoked as `gh copilot suggest` / `gh copilot explain`, not directly.
 *
 * WARNING: This function uses synchronous subprocess calls that block the main process.
 * For use in Electron main process, prefer getCopilotCliInvocationAsync() instead.
 */
export function getCopilotCliInvocation(): CopilotCliInvocation {
  const command = getToolPath('copilot');
  const env = getAugmentedEnv();

  return {
    command,
    args: ['copilot'],
    env: ensureCommandDirInPath(command, env),
  };
}

/**
 * Returns the Copilot CLI invocation details asynchronously (non-blocking).
 *
 * Safe to call from Electron main process without blocking the event loop.
 * Uses cached values if available for instant response.
 *
 * @example
 * ```typescript
 * const { command, args, env } = await getCopilotCliInvocationAsync();
 * spawn(command, [...args, 'suggest', '-t', 'shell', 'list files'], { env });
 * ```
 */
export async function getCopilotCliInvocationAsync(): Promise<CopilotCliInvocation> {
  // Run both detections in parallel for efficiency
  const [command, env] = await Promise.all([
    getToolPathAsync('copilot'),
    getAugmentedEnvAsync(),
  ]);

  return {
    command,
    args: ['copilot'],
    env: ensureCommandDirInPath(command, env),
  };
}
