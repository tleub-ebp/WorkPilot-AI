import {
	AlertTriangle,
	Cpu,
	GitMerge,
	Info,
	Layers,
	RotateCcw,
	Sparkles,
	Zap,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { cn } from "@/lib/utils";
import { useSwarmStore } from "../../stores/swarm-store";
import { Label } from "../ui/label";
import { Switch } from "../ui/switch";
import { SettingsSection } from "./SettingsSection";

/**
 * Swarm Mode settings panel.
 *
 * Master toggle + sub-options for configuring parallel multi-agent execution.
 * Works with any LLM configured in the user's active profile.
 */
export function SwarmModeSettings() {
	const { t } = useTranslation(["swarm", "common"]);
	const { isEnabled, setEnabled, config, setConfig } = useSwarmStore();

	return (
		<SettingsSection title={t("swarm:title")} description={t("swarm:subtitle")}>
			<div className="space-y-6">
				{/* ── Master Toggle ──────────────────────────────── */}
				<div className="flex items-center justify-between rounded-lg border border-border p-4">
					<div className="flex items-center gap-3">
						<div
							className={cn(
								"flex h-10 w-10 items-center justify-center rounded-lg",
								isEnabled
									? "bg-primary/10 text-primary"
									: "bg-muted text-muted-foreground",
							)}
						>
							<Zap className="h-5 w-5" />
						</div>
						<div>
							<Label className="text-sm font-medium">{t("swarm:enable")}</Label>
							<p className="text-xs text-muted-foreground mt-0.5">
								{t("swarm:subtitle")}
							</p>
						</div>
					</div>
					<Switch checked={isEnabled} onCheckedChange={setEnabled} />
				</div>

				{/* ── Info Banner ────────────────────────────────── */}
				{isEnabled && (
					<div className="flex items-start gap-2.5 rounded-lg border border-blue-500/20 bg-blue-500/5 p-3">
						<Info className="h-4 w-4 text-blue-500 mt-0.5 shrink-0" />
						<p className="text-xs text-blue-600 dark:text-blue-400 leading-relaxed">
							{t("swarm:infoBanner")}
						</p>
					</div>
				)}

				{/* ── Sub-options ────────────────────────────────── */}
				{isEnabled && (
					<div className="pl-4 space-y-5 border-l-2 border-primary/20">
						{/* Max Parallel Agents */}
						<div className="space-y-2.5">
							<div className="flex items-center justify-between">
								<Label className="text-sm font-medium flex items-center gap-2">
									<Cpu className="h-3.5 w-3.5 text-primary" />
									{t("swarm:config.maxParallel")}
								</Label>
								<span className="text-sm font-mono tabular-nums bg-muted px-2 py-0.5 rounded">
									{config.maxParallelAgents}
								</span>
							</div>
							<input
								type="range"
								min={2}
								max={8}
								step={1}
								value={config.maxParallelAgents}
								onChange={(e) =>
									setConfig({
										maxParallelAgents: Number.parseInt(e.target.value, 10),
									})
								}
								className="w-full accent-primary"
							/>
							<div className="flex justify-between text-[10px] text-muted-foreground px-0.5">
								<span>2</span>
								<span>4</span>
								<span>6</span>
								<span>8</span>
							</div>
							<p className="text-xs text-muted-foreground">
								{t("swarm:config.maxParallelDesc")}
							</p>
						</div>

						{/* Merge Strategy */}
						<div className="flex items-center justify-between">
							<div>
								<Label className="text-sm font-medium flex items-center gap-2">
									<GitMerge className="h-3.5 w-3.5 text-primary" />
									{t("swarm:config.mergeAfterWave")}
								</Label>
								<p className="text-xs text-muted-foreground mt-0.5">
									{t("swarm:config.mergeAfterWaveDesc")}
								</p>
							</div>
							<Switch
								checked={config.mergeAfterEachWave}
								onCheckedChange={(v) => setConfig({ mergeAfterEachWave: v })}
							/>
						</div>

						{/* AI-Assisted Merge */}
						<div className="flex items-center justify-between">
							<div>
								<Label className="text-sm font-medium flex items-center gap-2">
									<Sparkles className="h-3.5 w-3.5 text-primary" />
									{t("swarm:config.aiMerge")}
								</Label>
								<p className="text-xs text-muted-foreground mt-0.5">
									{t("swarm:config.aiMergeDesc")}
								</p>
							</div>
							<Switch
								checked={config.enableAiMerge}
								onCheckedChange={(v) => setConfig({ enableAiMerge: v })}
							/>
						</div>

						{/* Fail Fast */}
						<div className="flex items-center justify-between">
							<div>
								<Label className="text-sm font-medium flex items-center gap-2">
									<AlertTriangle className="h-3.5 w-3.5 text-primary" />
									{t("swarm:config.failFast")}
								</Label>
								<p className="text-xs text-muted-foreground mt-0.5">
									{t("swarm:config.failFastDesc")}
								</p>
							</div>
							<Switch
								checked={config.failFast}
								onCheckedChange={(v) => setConfig({ failFast: v })}
							/>
						</div>

						{/* Max Retries */}
						<div className="space-y-2.5">
							<div className="flex items-center justify-between">
								<Label className="text-sm font-medium flex items-center gap-2">
									<RotateCcw className="h-3.5 w-3.5 text-primary" />
									{t("swarm:config.maxRetries")}
								</Label>
								<span className="text-sm font-mono tabular-nums bg-muted px-2 py-0.5 rounded">
									{config.maxRetriesPerSubtask}
								</span>
							</div>
							<input
								type="range"
								min={0}
								max={5}
								step={1}
								value={config.maxRetriesPerSubtask}
								onChange={(e) =>
									setConfig({
										maxRetriesPerSubtask: Number.parseInt(e.target.value, 10),
									})
								}
								className="w-full accent-primary"
							/>
							<div className="flex justify-between text-[10px] text-muted-foreground px-0.5">
								<span>0</span>
								<span>1</span>
								<span>2</span>
								<span>3</span>
								<span>4</span>
								<span>5</span>
							</div>
						</div>

						{/* Dry Run */}
						<div className="flex items-center justify-between">
							<div>
								<Label className="text-sm font-medium flex items-center gap-2">
									<Layers className="h-3.5 w-3.5 text-primary" />
									{t("swarm:config.dryRun")}
								</Label>
								<p className="text-xs text-muted-foreground mt-0.5">
									{t("swarm:config.dryRunDesc")}
								</p>
							</div>
							<Switch
								checked={config.dryRun}
								onCheckedChange={(v) => setConfig({ dryRun: v })}
							/>
						</div>
					</div>
				)}
			</div>
		</SettingsSection>
	);
}
