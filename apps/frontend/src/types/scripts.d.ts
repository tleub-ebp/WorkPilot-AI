/**
 * Type declarations for CJS scripts outside the src/ directory.
 * These are not auto-resolved by TypeScript's bundler moduleResolution.
 */
declare module "scripts/package-with-python.cjs" {
	export const SHELL_METACHARACTERS: readonly string[];
	export function validateArgs(commandArgs: unknown[]): void;
}
