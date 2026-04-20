/**
 * Guardrails IPC Handlers
 *
 * Manage user-defined guardrail rules stored in
 * <projectPath>/.workpilot/guardrails.json.
 *
 * Channels:
 *   guardrails:load         → { projectPath } → GuardrailsDoc
 *   guardrails:save         → { projectPath, doc } → void
 *   guardrails:test         → { projectPath, toolName, toolInput } → TestResult
 *
 * We write JSON (not YAML) from the UI because it round-trips cleanly through
 * the DOM. The Python loader accepts both.
 */

import fs from "node:fs";
import path from "node:path";
import { ipcMain } from "electron";

export interface GuardrailRuleDoc {
	id: string;
	description: string;
	action: "allow" | "warn" | "deny" | "require_approval";
	when: {
		tool?: string | string[];
		path_prefix?: string;
		path_regex?: string;
		content_regex?: string;
		command_pattern?: string;
		content_max_lines?: number;
		content_max_bytes?: number;
		forbidden_strings?: string[];
	};
}

export interface GuardrailsDoc {
	version: number;
	rules: GuardrailRuleDoc[];
}

interface TestResult {
	action: "allow" | "warn" | "deny" | "require_approval";
	triggered: string[];
	message: string;
}

function getConfigPath(projectPath: string): string {
	return path.join(projectPath, ".workpilot", "guardrails.json");
}

function readDoc(projectPath: string): GuardrailsDoc {
	const p = getConfigPath(projectPath);
	try {
		if (!fs.existsSync(p)) return { version: 1, rules: [] };
		const raw = fs.readFileSync(p, "utf-8");
		const parsed = JSON.parse(raw) as GuardrailsDoc;
		if (!Array.isArray(parsed.rules)) return { version: 1, rules: [] };
		return { version: parsed.version ?? 1, rules: parsed.rules };
	} catch {
		return { version: 1, rules: [] };
	}
}

function writeDoc(projectPath: string, doc: GuardrailsDoc): void {
	const p = getConfigPath(projectPath);
	fs.mkdirSync(path.dirname(p), { recursive: true });
	fs.writeFileSync(p, JSON.stringify(doc, null, 2), "utf-8");
}

function toArray(v: string | string[] | undefined): string[] {
	if (!v) return [];
	return Array.isArray(v) ? v : [v];
}

function matches(
	rule: GuardrailRuleDoc,
	toolName: string,
	input: Record<string, unknown>,
): boolean {
	const tools = toArray(rule.when.tool);
	if (tools.length > 0 && !tools.includes(toolName)) return false;

	const filePath = String(input.file_path ?? input.path ?? "");
	if (rule.when.path_prefix && !filePath.startsWith(rule.when.path_prefix))
		return false;
	if (
		rule.when.path_regex &&
		!new RegExp(rule.when.path_regex).test(filePath)
	)
		return false;

	if (toolName === "Bash") {
		const cmd = String(input.command ?? "");
		if (
			rule.when.command_pattern &&
			!new RegExp(rule.when.command_pattern).test(cmd)
		)
			return false;
	} else {
		const content = String(input.content ?? input.new_string ?? "");
		if (
			rule.when.content_regex &&
			!new RegExp(rule.when.content_regex).test(content)
		)
			return false;
		if (
			rule.when.content_max_lines !== undefined &&
			content.split("\n").length <= rule.when.content_max_lines
		)
			return false;
		if (
			rule.when.content_max_bytes !== undefined &&
			Buffer.byteLength(content, "utf-8") <= rule.when.content_max_bytes
		)
			return false;
		if (
			rule.when.forbidden_strings?.length &&
			!rule.when.forbidden_strings.some((s) => content.includes(s))
		)
			return false;
	}

	return true;
}

const ACTION_PRIORITY: Record<string, number> = {
	allow: 0,
	warn: 1,
	require_approval: 2,
	deny: 3,
};

export function registerGuardrailsHandlers(): void {
	ipcMain.handle(
		"guardrails:load",
		async (_evt, { projectPath }: { projectPath: string }) =>
			readDoc(projectPath),
	);

	ipcMain.handle(
		"guardrails:save",
		async (
			_evt,
			{ projectPath, doc }: { projectPath: string; doc: GuardrailsDoc },
		) => {
			writeDoc(projectPath, doc);
			return true;
		},
	);

	ipcMain.handle(
		"guardrails:test",
		async (
			_evt,
			{
				projectPath,
				toolName,
				toolInput,
			}: {
				projectPath: string;
				toolName: string;
				toolInput: Record<string, unknown>;
			},
		): Promise<TestResult> => {
			const doc = readDoc(projectPath);
			const triggered = doc.rules.filter((r) => matches(r, toolName, toolInput));
			if (triggered.length === 0)
				return { action: "allow", triggered: [], message: "" };
			const strongest = triggered.reduce((best, r) =>
				ACTION_PRIORITY[r.action] > ACTION_PRIORITY[best.action] ? r : best,
			);
			return {
				action: strongest.action,
				triggered: triggered.map((r) => r.id),
				message: triggered
					.map((r) => `[${r.id}] ${r.description || "(no description)"}`)
					.join("\n"),
			};
		},
	);
}
