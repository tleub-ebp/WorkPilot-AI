#!/usr/bin/env node
/**
 * Generate a TypeScript module from `config/configured_providers.json` so
 * the frontend has compile-time visibility into the canonical provider
 * list.
 *
 * Output: `apps/frontend/src/shared/types/providers.generated.ts`
 * Inputs: `config/configured_providers.json` (single source of truth)
 *
 * Regenerate with:   pnpm run generate:provider-types
 * CI check:           pnpm run generate:provider-types --check
 *
 * In --check mode, exits non-zero when the generated file is stale —
 * ideal for wiring into a pre-commit or lint-staged hook so nobody ships
 * a JSON change without regenerating the types.
 */

const fs = require("node:fs");
const path = require("node:path");

const ROOT = path.resolve(__dirname, "..");
const SOURCE = path.join(ROOT, "config", "configured_providers.json");
const OUTPUT = path.join(
	ROOT,
	"apps",
	"frontend",
	"src",
	"shared",
	"types",
	"providers.generated.ts",
);

const args = new Set(process.argv.slice(2));
const checkMode = args.has("--check");

function buildContent() {
	const raw = JSON.parse(fs.readFileSync(SOURCE, "utf8"));
	if (!raw || !Array.isArray(raw.providers)) {
		throw new Error(
			`${path.relative(ROOT, SOURCE)}: expected top-level { providers: [...] }`,
		);
	}
	const providers = raw.providers;
	for (const p of providers) {
		for (const field of ["name", "label", "description"]) {
			if (typeof p[field] !== "string") {
				throw new TypeError(
					`Provider ${JSON.stringify(p.name ?? "<unknown>")} is missing required string field "${field}"`,
				);
			}
		}
	}
	const escapedQuote = String.raw`\"`;
	const nameUnion = providers
		.map((p) => `\t| "${p.name.replaceAll('"', escapedQuote)}"`)
		.join("\n");
	const entries = providers
		.map(
			(p) =>
				`\t{ name: "${p.name}", label: ${JSON.stringify(p.label)}, description: ${JSON.stringify(p.description)} },`,
		)
		.join("\n");

	const header = [
		"// AUTO-GENERATED — do not edit by hand.",
		"// Regenerate with: pnpm run generate:provider-types",
		"// Source: config/configured_providers.json",
		"",
		"/**",
		" * Canonical entry for an LLM provider as declared in",
		" * `config/configured_providers.json`. Both the Python backend",
		" * (`apps/backend/provider_api.py`) and the Electron/React frontend",
		" * consume this same JSON file.",
		" */",
		"export interface ConfiguredProvider {",
		"\t/** Stable machine-readable identifier, used in API calls and config keys. */",
		"\treadonly name: ProviderName;",
		"\t/** Human-readable name displayed in the UI. */",
		"\treadonly label: string;",
		"\t/** Short description rendered under the provider in settings. */",
		"\treadonly description: string;",
		"}",
		"",
		"/** Union type of every provider ID declared in the JSON. */",
		"export type ProviderName =",
	].join("\n");

	return [
		header,
		nameUnion + ";",
		"",
		"/** Every provider, frozen so callers cannot mutate the canonical list. */",
		"export const CONFIGURED_PROVIDERS: readonly ConfiguredProvider[] = Object.freeze([",
		entries,
		"]);",
		"",
		"/** `Set` of provider IDs — constant-time membership check. */",
		"export const PROVIDER_NAMES: ReadonlySet<ProviderName> = new Set(",
		"\tCONFIGURED_PROVIDERS.map((p) => p.name),",
		");",
		"",
		"/** Type guard — narrows an arbitrary string to `ProviderName`. */",
		"export function isProviderName(value: string): value is ProviderName {",
		"\treturn (PROVIDER_NAMES as ReadonlySet<string>).has(value);",
		"}",
		"",
	].join("\n");
}

const desired = buildContent();

if (checkMode) {
	const current = fs.existsSync(OUTPUT) ? fs.readFileSync(OUTPUT, "utf8") : "";
	if (current !== desired) {
		console.error(
			`generate-provider-types: ${path.relative(ROOT, OUTPUT)} is stale.\n` +
				`Run \`pnpm run generate:provider-types\` after editing ` +
				`${path.relative(ROOT, SOURCE)}.`,
		);
		process.exit(1);
	}
	console.log(
		`generate-provider-types: OK — ${path.relative(ROOT, OUTPUT)} is up to date.`,
	);
	process.exit(0);
}

fs.mkdirSync(path.dirname(OUTPUT), { recursive: true });
fs.writeFileSync(OUTPUT, desired, "utf8");
console.log(
	`generate-provider-types: wrote ${path.relative(ROOT, OUTPUT)} ` +
		`(${JSON.parse(fs.readFileSync(SOURCE, "utf8")).providers.length} providers).`,
);
