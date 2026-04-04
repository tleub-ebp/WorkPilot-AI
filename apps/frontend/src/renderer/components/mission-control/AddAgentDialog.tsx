/**
 * AddAgentDialog — Dialog for creating a new agent slot in Mission Control.
 *
 * Allows selecting: name, role, provider, and model.
 */

import { Brain, Cpu, Rocket, User } from "lucide-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../ui/button";
import {
	Dialog,
	DialogContent,
	DialogFooter,
	DialogHeader,
	DialogTitle,
} from "../ui/dialog";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "../ui/select";

interface AddAgentDialogProps {
	readonly open: boolean;
	readonly onOpenChange: (open: boolean) => void;
	readonly onAdd: (
		name: string,
		role: string,
		provider: string,
		model: string,
		modelLabel: string,
	) => void;
}

const ROLES = [
	{
		value: "architect",
		label: "🏗️ Architect",
		desc: "System design & architecture",
	},
	{ value: "coder", label: "💻 Coder", desc: "Code implementation" },
	{ value: "tester", label: "🧪 Tester", desc: "Testing & QA" },
	{ value: "reviewer", label: "👁️ Reviewer", desc: "Code review" },
	{ value: "documenter", label: "📝 Documenter", desc: "Documentation" },
	{ value: "planner", label: "📋 Planner", desc: "Task planning" },
	{ value: "debugger", label: "🐛 Debugger", desc: "Bug fixing" },
	{ value: "custom", label: "⚙️ Custom", desc: "Custom role" },
];

const PROVIDERS = [
	{
		value: "anthropic",
		label: "Anthropic",
		models: [
			{ value: "claude-opus-4-6", label: "Claude Opus 4.6", tier: "flagship" },
			{
				value: "claude-sonnet-4-6",
				label: "Claude Sonnet 4.6",
				tier: "standard",
			},
			{ value: "claude-haiku-4-6", label: "Claude Haiku 4.6", tier: "fast" },
		],
	},
	{
		value: "openai",
		label: "OpenAI",
		models: [
			{ value: "gpt-5-turbo", label: "GPT-5 Turbo", tier: "flagship" },
			{ value: "gpt-4.1", label: "GPT-4.1", tier: "standard" },
			{ value: "gpt-4.1-mini", label: "GPT-4.1 Mini", tier: "fast" },
		],
	},
	{
		value: "google",
		label: "Google",
		models: [
			{ value: "gemini-2.5-pro", label: "Gemini 2.5 Pro", tier: "flagship" },
			{ value: "gemini-2.5-flash", label: "Gemini 2.5 Flash", tier: "fast" },
		],
	},
	{
		value: "grok",
		label: "Grok (xAI)",
		models: [
			{ value: "grok-3", label: "Grok 3", tier: "flagship" },
			{ value: "grok-3-mini", label: "Grok 3 Mini", tier: "fast" },
		],
	},
	{
		value: "ollama",
		label: "Ollama (Local)",
		models: [
			{ value: "llama3", label: "Llama 3", tier: "standard" },
			{ value: "codellama", label: "Code Llama", tier: "standard" },
			{ value: "mistral", label: "Mistral", tier: "standard" },
		],
	},
	{
		value: "copilot",
		label: "GitHub Copilot",
		models: [
			{ value: "copilot-claude", label: "Copilot Claude", tier: "standard" },
			{ value: "copilot-gpt", label: "Copilot GPT", tier: "standard" },
		],
	},
];

const ROLE_TIER_MAP: Record<string, string> = {
	architect: "flagship",
	planner: "flagship",
	coder: "standard",
	reviewer: "standard",
	debugger: "standard",
	tester: "fast",
	documenter: "fast",
	custom: "standard",
};

export function AddAgentDialog({
	open,
	onOpenChange,
	onAdd,
}: AddAgentDialogProps) {
	const { t } = useTranslation(["missionControl"]);
	const [name, setName] = useState("");
	const [role, setRole] = useState("coder");
	const [provider, setProvider] = useState("anthropic");
	const [model, setModel] = useState("");

	// Auto-select recommended model when role or provider changes
	useEffect(() => {
		const providerData = PROVIDERS.find((p) => p.value === provider);
		if (!providerData) return;
		const recommendedTier = ROLE_TIER_MAP[role] ?? "standard";
		const recommended = providerData.models.find(
			(m) => m.tier === recommendedTier,
		);
		setModel(recommended?.value ?? providerData.models[0]?.value ?? "");
	}, [role, provider]);

	// Auto-generate name from role
	useEffect(() => {
		if (!name || ROLES.some((r) => name === `Agent ${r.label.split(" ")[1]}`)) {
			const roleData = ROLES.find((r) => r.value === role);
			if (roleData) {
				setName(`Agent ${roleData.label.split(" ")[1]}`);
			}
		}
	}, [role, name]);

	const providerData = PROVIDERS.find((p) => p.value === provider);
	const modelData = providerData?.models.find((m) => m.value === model);

	const handleSubmit = () => {
		if (!name.trim()) return;
		onAdd(name.trim(), role, provider, model, modelData?.label ?? model);
		// Reset form
		setName("");
		setRole("coder");
		setProvider("anthropic");
		setModel("");
	};

	return (
		<Dialog open={open} onOpenChange={onOpenChange}>
			<DialogContent className="sm:max-w-md">
				<DialogHeader>
					<DialogTitle className="flex items-center gap-2">
						<Rocket className="h-5 w-5 text-primary" />
						{t("missionControl:addAgentTitle", "Add Agent")}
					</DialogTitle>
				</DialogHeader>

				<div className="space-y-4 py-2">
					{/* Name */}
					<div className="space-y-2">
						<Label className="flex items-center gap-1.5 text-xs">
							<User className="h-3.5 w-3.5" />
							{t("missionControl:agentName", "Agent Name")}
						</Label>
						<Input
							value={name}
							onChange={(e) => setName(e.target.value)}
							placeholder="e.g. Architecture Agent"
							className="text-sm"
						/>
					</div>

					{/* Role */}
					<div className="space-y-2">
						<Label className="flex items-center gap-1.5 text-xs">
							<Brain className="h-3.5 w-3.5" />
							{t("missionControl:agentRole", "Role")}
						</Label>
						<Select value={role} onValueChange={setRole}>
							<SelectTrigger className="text-sm">
								<SelectValue />
							</SelectTrigger>
							<SelectContent>
								{ROLES.map((r) => (
									<SelectItem key={r.value} value={r.value}>
										<div className="flex items-center gap-2">
											<span>{r.label}</span>
											<span className="text-xs text-muted-foreground">
												{r.desc}
											</span>
										</div>
									</SelectItem>
								))}
							</SelectContent>
						</Select>
					</div>

					{/* Provider */}
					<div className="space-y-2">
						<Label className="flex items-center gap-1.5 text-xs">
							<Cpu className="h-3.5 w-3.5" />
							{t("missionControl:provider", "Provider")}
						</Label>
						<Select value={provider} onValueChange={setProvider}>
							<SelectTrigger className="text-sm">
								<SelectValue />
							</SelectTrigger>
							<SelectContent>
								{PROVIDERS.map((p) => (
									<SelectItem key={p.value} value={p.value}>
										{p.label}
									</SelectItem>
								))}
							</SelectContent>
						</Select>
					</div>

					{/* Model */}
					<div className="space-y-2">
						<Label className="flex items-center gap-1.5 text-xs">
							<Cpu className="h-3.5 w-3.5" />
							{t("missionControl:model", "Model")}
							{modelData && (
								<span className="ml-auto text-[10px] text-muted-foreground capitalize">
									{modelData.tier}
								</span>
							)}
						</Label>
						<Select value={model} onValueChange={setModel}>
							<SelectTrigger className="text-sm">
								<SelectValue />
							</SelectTrigger>
							<SelectContent>
								{providerData?.models.map((m) => (
									<SelectItem key={m.value} value={m.value}>
										<div className="flex items-center gap-2">
											<span>{m.label}</span>
											<span
												className={`text-[10px] capitalize px-1 rounded ${
													m.tier === "flagship"
														? "bg-amber-500/10 text-amber-600"
														: m.tier === "fast"
															? "bg-green-500/10 text-green-600"
															: "bg-blue-500/10 text-blue-600"
												}`}
											>
												{m.tier}
											</span>
										</div>
									</SelectItem>
								))}
							</SelectContent>
						</Select>
					</div>
				</div>

				<DialogFooter>
					<Button variant="outline" onClick={() => onOpenChange(false)}>
						{t("common:cancel", "Cancel")}
					</Button>
					<Button onClick={handleSubmit} disabled={!name.trim()}>
						<Rocket className="h-4 w-4 mr-1.5" />
						{t("missionControl:createAgent", "Create Agent")}
					</Button>
				</DialogFooter>
			</DialogContent>
		</Dialog>
	);
}
