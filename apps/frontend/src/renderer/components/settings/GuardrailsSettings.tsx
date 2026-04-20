import { AlertTriangle, Check, Plus, Trash2, X } from "lucide-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import type { GuardrailAction } from "../../../preload/api/modules/guardrails-api";
import { useGuardrailsStore } from "../../stores/guardrails-store";
import { useProjectStore } from "../../stores/project-store";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { SettingsSection } from "./SettingsSection";

const SELECT_CLASS =
	"h-10 rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring";

const ACTIONS: GuardrailAction[] = [
	"allow",
	"warn",
	"deny",
	"require_approval",
];

const TOOLS = ["Write", "Edit", "Bash"];

export function GuardrailsSettings() {
	const { t } = useTranslation(["settings", "common"]);
	const activeProject = useProjectStore((s) => s.getActiveProject());
	const {
		doc,
		dirty,
		loading,
		error,
		lastTest,
		load,
		save,
		addRule,
		updateRule,
		deleteRule,
		runTest,
		reset,
	} = useGuardrailsStore();

	const [testTool, setTestTool] = useState("Write");
	const [testPath, setTestPath] = useState("");
	const [testContent, setTestContent] = useState("");
	const [testCommand, setTestCommand] = useState("");

	useEffect(() => {
		if (activeProject?.path) load(activeProject.path);
	}, [activeProject?.path, load]);

	const handleSave = () => {
		if (activeProject?.path) save(activeProject.path);
	};

	const handleTest = () => {
		if (!activeProject?.path) return;
		const input: Record<string, unknown> =
			testTool === "Bash"
				? { command: testCommand }
				: { file_path: testPath, content: testContent };
		runTest(activeProject.path, testTool, input);
	};

	if (!activeProject) {
		return (
			<SettingsSection
				title={t("settings:guardrails.title", "Agent Guardrails")}
				description={t(
					"settings:guardrails.selectProject",
					"Select a project to manage its guardrails.",
				)}
			>
				<p className="text-sm text-muted-foreground">
					{t(
						"settings:guardrails.selectProject",
						"Select a project to manage its guardrails.",
					)}
				</p>
			</SettingsSection>
		);
	}

	return (
		<SettingsSection
			title={t("settings:guardrails.title", "Agent Guardrails")}
			description={t(
				"settings:guardrails.description",
				"Rules agents must respect before Write / Edit / Bash. Stored in .workpilot/guardrails.json.",
			)}
		>
			<div className="flex items-center justify-between mb-4">
				<Badge variant="secondary">
					{t("settings:guardrails.activeCount", {
						count: doc.rules.length,
						defaultValue: "{{count}} active rule(s)",
					})}
				</Badge>
				<div className="flex gap-2">
					<Button size="sm" variant="outline" onClick={addRule}>
						<Plus className="w-3 h-3 mr-1" />
						{t("settings:guardrails.addRule", "Add rule")}
					</Button>
					<Button
						size="sm"
						onClick={handleSave}
						disabled={!dirty || loading}
					>
						{t("common:save", "Save")}
					</Button>
				</div>
			</div>

			{error && (
				<p className="text-sm text-destructive mb-2">{error}</p>
			)}

			<div className="space-y-3">
				{doc.rules.length === 0 && (
					<p className="text-sm text-muted-foreground">
						{t(
							"settings:guardrails.empty",
							"No rules yet. Add one to start enforcing policies.",
						)}
					</p>
				)}
				{doc.rules.map((rule, idx) => (
					<div
						key={rule.id || `rule-${idx}`}
						className="border rounded-md p-3 space-y-2 bg-card"
					>
						<div className="flex items-center gap-2">
							<Input
								className="flex-1"
								value={rule.id}
								onChange={(e) =>
									updateRule(idx, { id: e.target.value })
								}
								placeholder={t("settings:guardrails.ruleId", "rule id")}
							/>
							<select
								className={SELECT_CLASS}
								value={rule.action}
								onChange={(e) =>
									updateRule(idx, {
										action: e.target.value as GuardrailAction,
									})
								}
							>
								{ACTIONS.map((a) => (
									<option key={a} value={a}>
										{t(`settings:guardrails.actions.${a}`, a)}
									</option>
								))}
							</select>
							<Button
								size="icon"
								variant="ghost"
								onClick={() => deleteRule(idx)}
							>
								<Trash2 className="w-4 h-4" />
							</Button>
						</div>
						<Input
							value={rule.description}
							onChange={(e) =>
								updateRule(idx, { description: e.target.value })
							}
							placeholder={t(
								"settings:guardrails.description_placeholder",
								"What does this rule enforce?",
							)}
						/>
						<div className="grid grid-cols-2 gap-2">
							<div>
								<Label className="text-xs">
									{t("settings:guardrails.tool", "Tool(s)")}
								</Label>
								<Input
									value={
										Array.isArray(rule.when.tool)
											? rule.when.tool.join(",")
											: (rule.when.tool ?? "")
									}
									onChange={(e) =>
										updateRule(idx, {
											when: {
												tool: e.target.value
													.split(",")
													.map((s) => s.trim())
													.filter(Boolean),
											},
										})
									}
									placeholder="Write,Edit,Bash"
								/>
							</div>
							<div>
								<Label className="text-xs">
									{t("settings:guardrails.pathPrefix", "Path prefix")}
								</Label>
								<Input
									value={rule.when.path_prefix ?? ""}
									onChange={(e) =>
										updateRule(idx, {
											when: { path_prefix: e.target.value || undefined },
										})
									}
									placeholder="migrations/"
								/>
							</div>
							<div>
								<Label className="text-xs">
									{t("settings:guardrails.pathRegex", "Path regex")}
								</Label>
								<Input
									value={rule.when.path_regex ?? ""}
									onChange={(e) =>
										updateRule(idx, {
											when: { path_regex: e.target.value || undefined },
										})
									}
									placeholder="\\.sql$"
								/>
							</div>
							<div>
								<Label className="text-xs">
									{t(
										"settings:guardrails.contentRegex",
										"Content regex",
									)}
								</Label>
								<Input
									value={rule.when.content_regex ?? ""}
									onChange={(e) =>
										updateRule(idx, {
											when: { content_regex: e.target.value || undefined },
										})
									}
									placeholder="^def "
								/>
							</div>
							<div>
								<Label className="text-xs">
									{t(
										"settings:guardrails.maxLines",
										"Max content lines",
									)}
								</Label>
								<Input
									type="number"
									value={rule.when.content_max_lines ?? ""}
									onChange={(e) =>
										updateRule(idx, {
											when: {
												content_max_lines: e.target.value
													? Number(e.target.value)
													: undefined,
											},
										})
									}
									placeholder="500"
								/>
							</div>
							<div>
								<Label className="text-xs">
									{t(
										"settings:guardrails.commandPattern",
										"Bash command pattern",
									)}
								</Label>
								<Input
									value={rule.when.command_pattern ?? ""}
									onChange={(e) =>
										updateRule(idx, {
											when: {
												command_pattern: e.target.value || undefined,
											},
										})
									}
									placeholder="(pip|npm) install .*gpl"
								/>
							</div>
						</div>
					</div>
				))}
			</div>

			<div className="mt-6 border-t pt-4">
				<h4 className="text-sm font-medium mb-2 flex items-center gap-2">
					<AlertTriangle className="w-4 h-4" />
					{t("settings:guardrails.tester", "Test a tool call")}
				</h4>
				<div className="space-y-2">
					<div className="flex gap-2">
						<select
							className={SELECT_CLASS}
							value={testTool}
							onChange={(e) => setTestTool(e.target.value)}
						>
							{TOOLS.map((t0) => (
								<option key={t0} value={t0}>
									{t0}
								</option>
							))}
						</select>
						<Button size="sm" variant="outline" onClick={handleTest}>
							{t("settings:guardrails.runTest", "Run test")}
						</Button>
					</div>
					{testTool === "Bash" ? (
						<Input
							value={testCommand}
							onChange={(e) => setTestCommand(e.target.value)}
							placeholder="rm -rf /"
						/>
					) : (
						<>
							<Input
								value={testPath}
								onChange={(e) => setTestPath(e.target.value)}
								placeholder="migrations/001.sql"
							/>
							<textarea
								className="w-full border rounded-md p-2 text-sm font-mono min-h-20 bg-background"
								value={testContent}
								onChange={(e) => setTestContent(e.target.value)}
								placeholder="file content…"
							/>
						</>
					)}
					{lastTest && (
						<div
							className={`text-sm p-2 rounded-md flex items-start gap-2 ${
								lastTest.action === "allow"
									? "bg-green-500/10 text-green-700 dark:text-green-400"
									: lastTest.action === "warn"
										? "bg-yellow-500/10 text-yellow-700 dark:text-yellow-400"
										: "bg-red-500/10 text-red-700 dark:text-red-400"
							}`}
						>
							{lastTest.action === "allow" ? (
								<Check className="w-4 h-4 mt-0.5" />
							) : (
								<X className="w-4 h-4 mt-0.5" />
							)}
							<div>
								<div className="font-medium">
									{t(
										`settings:guardrails.actions.${lastTest.action}`,
										lastTest.action,
									)}
								</div>
								{lastTest.message && (
									<pre className="text-xs whitespace-pre-wrap">
										{lastTest.message}
									</pre>
								)}
							</div>
							<Button
								size="icon"
								variant="ghost"
								className="ml-auto"
								onClick={reset}
							>
								<X className="w-3 h-3" />
							</Button>
						</div>
					)}
				</div>
			</div>
		</SettingsSection>
	);
}
