#!/usr/bin/env node
/**
 * Validate that every npm script in the repository points at a file that
 * actually exists. Catches mistakes like:
 *   - "start": "node scripts/runn.js"   (typo, no such file)
 *   - "dev":   "python ../missing.py"
 * after renames/refactors.
 *
 * What is checked:
 *   - Scripts that call `node <path>`, `python <path>`, `sh <path>`,
 *     `bash <path>`, or `ts-node <path>` — first positional argument that
 *     looks like a relative path.
 *   - Paths are resolved relative to the package.json they live in.
 *
 * What is intentionally NOT checked:
 *   - Shell built-ins (cd, ls, echo), tool names resolved via PATH
 *     (pnpm, electron, vite, biome, …) — these rely on node_modules/.bin
 *     or the environment and can't be verified statically.
 *
 * Exit codes:
 *   0 — all script paths resolve to real files.
 *   1 — one or more script paths are missing. Report is printed to stderr.
 *
 * Usage: `node scripts/validate-npm-scripts.js`
 */
"use strict";

const fs = require("node:fs");
const path = require("node:path");

const ROOT = path.resolve(__dirname, "..");

const PACKAGE_JSON_FILES = [
  path.join(ROOT, "package.json"),
  path.join(ROOT, "apps", "frontend", "package.json"),
  path.join(ROOT, "apps", "backend", "package.json"),
];

const RUNNERS = new Set(["node", "python", "python3", "sh", "bash", "ts-node"]);

// Flags that take an inline expression (no file path follows) — when we see
// any of these we bail out and don't try to validate a path.
const INLINE_SCRIPT_FLAGS = new Set(["-e", "-c", "--eval", "--print", "-p"]);

function extractCandidatePath(command) {
  // Split on shell separators conservatively. We only look at the first token
  // and its arguments up to the first separator.
  const firstSegment = command.split(/\s*(?:&&|\|\||;|\|)\s*/)[0].trim();
  const tokens = firstSegment.split(/\s+/);
  if (tokens.length < 2) return null;
  const [runner, ...rest] = tokens;
  if (!RUNNERS.has(runner)) return null;
  // Skip flags (-u, --flag, …) until we find a positional argument.
  // If we hit an inline-script flag first, the command isn't running a file.
  for (const token of rest) {
    if (INLINE_SCRIPT_FLAGS.has(token)) return null;
    if (token.startsWith("-")) continue;
    return token;
  }
  return null;
}

function validatePackage(pkgPath) {
  const problems = [];
  if (!fs.existsSync(pkgPath)) return problems;
  const pkg = JSON.parse(fs.readFileSync(pkgPath, "utf8"));
  const pkgDir = path.dirname(pkgPath);
  const scripts = pkg.scripts || {};
  for (const [name, command] of Object.entries(scripts)) {
    const candidate = extractCandidatePath(command);
    if (!candidate) continue;
    // Drop any shell quoting the scripts might carry.
    const cleaned = candidate.replace(/^["']|["']$/g, "");
    // Skip URLs, absolute paths on POSIX are still checkable but the common
    // case is relative — pass either through resolve().
    const resolved = path.resolve(pkgDir, cleaned);
    if (!fs.existsSync(resolved)) {
      problems.push({
        pkg: path.relative(ROOT, pkgPath),
        script: name,
        command,
        missing: path.relative(ROOT, resolved),
      });
    }
  }
  return problems;
}

const problems = PACKAGE_JSON_FILES.flatMap(validatePackage);

if (problems.length === 0) {
  console.log(
    `validate-npm-scripts: OK — checked ${PACKAGE_JSON_FILES.length} package.json file(s).`,
  );
  process.exit(0);
}

console.error("validate-npm-scripts: missing targets detected");
console.error("-".repeat(60));
for (const p of problems) {
  console.error(`  [${p.pkg}] script "${p.script}"`);
  console.error(`    command: ${p.command}`);
  console.error(`    missing: ${p.missing}`);
}
console.error(`\n${problems.length} problem(s) found.`);
process.exit(1);
