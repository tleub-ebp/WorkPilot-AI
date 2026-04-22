import {
	Cloud,
	Home,
	RefreshCw,
	Save,
	ScanLine,
	ShieldCheck,
	Trash2,
	Wifi,
	WifiOff,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useOfflineModeStore } from "../../stores/offline-mode-store";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";

const LOCAL_PROVIDERS = new Set(["ollama", "lm-studio", "llama-cpp"]);

function formatAge(seconds: number): string {
	if (seconds < 60) return `${seconds}s`;
	const min = Math.floor(seconds / 60);
	if (min < 60) return `${min}m`;
	return `${Math.floor(min / 60)}h${min % 60}m`;
}

interface Props {
	readonly projectPath?: string;
}

export function OfflineModeSettings({ projectPath }: Props) {
	const { t } = useTranslation(["offlineMode", "common"]);
	const {
		status,
		policy,
		report,
		catalog,
		loading,
		saving,
		scanning,
		error,
		dirty,
		loadAll,
		refreshStatus,
		scan,
		setAirgap,
		setRouting,
		addRoutingRow,
		removeRoutingRow,
		save,
	} = useOfflineModeStore();

	const [newTask, setNewTask] = useState("");

	useEffect(() => {
		if (projectPath) void loadAll(projectPath);
	}, [projectPath, loadAll]);

	const providerOptions = useMemo(() => {
		const base = catalog?.providers ?? {};
		const names = new Set(Object.keys(base));
		if (policy) {
			for (const entry of Object.values(policy.routing)) names.add(entry.provider);
			names.add(policy.defaultProvider);
		}
		return Array.from(names).sort();
	}, [catalog, policy]);

	const modelsByProvider = (provider: string): string[] => {
		const list = catalog?.providers?.[provider] ?? [];
		return [...list].sort();
	};

	if (!projectPath) {
		return (
			<div className="flex items-center justify-center h-full text-muted-foreground">
				{t("offlineMode:noProject", "Select a project to configure offline mode.")}
			</div>
		);
	}

	const confidentiality = report?.confidentialityLevel ?? "unknown";
	const confidentialityStyle: Record<string, string> = {
		local: "bg-green-500/15 text-green-500 border-green-500/30",
		mixed: "bg-yellow-500/15 text-yellow-500 border-yellow-500/30",
		unknown: "bg-muted text-muted-foreground border-border",
	};
	const confidentialityIcon =
		confidentiality === "local" ? (
			<Home className="w-3 h-3" />
		) : confidentiality === "mixed" ? (
			<Cloud className="w-3 h-3" />
		) : (
			<WifiOff className="w-3 h-3" />
		);

	return (
		<div className="flex flex-col gap-4 p-4">
			<div className="flex items-center justify-between">
				<div className="flex items-center gap-2">
					<Wifi className="w-4 h-4" />
					<h3 className="text-base font-semibold">
						{t("offlineMode:title", "Offline Mode")}
					</h3>
				</div>
				<div className="flex items-center gap-2">
					<Badge
						variant="outline"
						className={`gap-1 ${confidentialityStyle[confidentiality]}`}
					>
						{confidentialityIcon}
						{t(`offlineMode:confidentiality.${confidentiality}`, confidentiality)}
					</Badge>
					<Button
						size="sm"
						variant="outline"
						onClick={() => refreshStatus(projectPath)}
						disabled={loading}
					>
						<RefreshCw className="w-3 h-3 mr-1" />
						{t("offlineMode:refresh", "Refresh")}
					</Button>
				</div>
			</div>

			{error && (
				<p className="text-sm text-destructive" role="alert">
					{error}
				</p>
			)}

			<section className="border rounded-md p-3 bg-card">
				<h4 className="text-sm font-semibold mb-2">
					{t("offlineMode:runtimes", "Local runtimes")}
				</h4>
				{!status ? (
					<p className="text-sm text-muted-foreground">
						{t("offlineMode:loading", "Loading…")}
					</p>
				) : (
					<ul className="space-y-1 text-sm">
						<li className="flex items-center gap-2">
							<span className="w-24">Ollama</span>
							{status.runtimes.ollama.available ? (
								<>
									<Badge variant="outline" className="bg-green-500/10">
										{t("offlineMode:available", "available")}
									</Badge>
									<span className="text-xs text-muted-foreground">
										{status.runtimes.ollama.models?.length ?? 0}{" "}
										{t("offlineMode:modelsInstalled", "models installed")}
									</span>
								</>
							) : (
								<Badge variant="outline">
									{t("offlineMode:notFound", "not found")}
								</Badge>
							)}
						</li>
						<li className="flex items-center gap-2">
							<span className="w-24">llama.cpp</span>
							{status.runtimes.llamaCpp.available ? (
								<Badge variant="outline" className="bg-green-500/10">
									{t("offlineMode:available", "available")}
								</Badge>
							) : (
								<Badge variant="outline">
									{t("offlineMode:notFound", "not found")}
								</Badge>
							)}
						</li>
						<li className="flex items-center gap-2">
							<span className="w-24">LM Studio</span>
							{status.runtimes.lmStudio.available ? (
								<Badge variant="outline" className="bg-green-500/10">
									{t("offlineMode:available", "available")}
								</Badge>
							) : (
								<Badge variant="outline">
									{t("offlineMode:notFound", "not found")}
								</Badge>
							)}
						</li>
					</ul>
				)}
				{status && status.localModels.length > 0 && (
					<div className="mt-2">
						<Label className="text-xs">
							{t("offlineMode:localModels", "Local models")}
						</Label>
						<div className="flex flex-wrap gap-1 mt-1">
							{status.localModels.map((m) => (
								<Badge key={m} variant="secondary" className="text-xs font-mono">
									{m}
								</Badge>
							))}
						</div>
					</div>
				)}
			</section>

			{policy && (
				<section className="border rounded-md p-3 bg-card space-y-3">
					<div className="flex items-center justify-between">
						<h4 className="text-sm font-semibold flex items-center gap-2">
							<ShieldCheck className="w-4 h-4" />
							{t("offlineMode:policy", "Routing policy")}
						</h4>
						<label className="flex items-center gap-2 text-sm">
							<input
								type="checkbox"
								checked={policy.airgapStrict}
								onChange={(e) => setAirgap(e.target.checked)}
							/>
							{t("offlineMode:airgapStrict", "Airgap strict (block all cloud calls)")}
						</label>
					</div>

					<table className="w-full text-sm">
						<thead className="text-xs text-muted-foreground">
							<tr>
								<th className="text-left py-1 pr-2">
									{t("offlineMode:task", "Task")}
								</th>
								<th className="text-left py-1 pr-2">
									{t("offlineMode:providerCol", "Provider")}
								</th>
								<th className="text-left py-1 pr-2">
									{t("offlineMode:modelCol", "Model")}
								</th>
								<th className="w-6" />
							</tr>
						</thead>
						<tbody>
							{Object.entries(policy.routing).map(([task, entry]) => {
								const models = modelsByProvider(entry.provider);
								const modelMissing = !!entry.model && !models.includes(entry.model);
								const isLocal = LOCAL_PROVIDERS.has(entry.provider);
								return (
									<tr key={task} className="border-t">
										<td className="py-1 pr-2 font-medium">
											<span className="flex items-center gap-1">
												{task}
												{isLocal && (
													<Home
														className="w-3 h-3 text-green-500"
														aria-label="local"
													/>
												)}
											</span>
										</td>
										<td className="py-1 pr-2">
											<select
												value={entry.provider}
												onChange={(e) => {
													const nextProvider = e.target.value;
													const nextModels = modelsByProvider(nextProvider);
													const nextModel =
														nextModels.length > 0 ? nextModels[0] : entry.model;
													setRouting(task, nextProvider, nextModel);
												}}
												className="h-7 w-full rounded-md border border-input bg-background px-2 text-sm"
											>
												{providerOptions.length === 0 && (
													<option value={entry.provider}>{entry.provider}</option>
												)}
												{providerOptions.map((p) => (
													<option key={p} value={p}>
														{LOCAL_PROVIDERS.has(p) ? `🏠 ${p}` : `☁ ${p}`}
													</option>
												))}
											</select>
										</td>
										<td className="py-1 pr-2">
											<select
												value={entry.model}
												onChange={(e) =>
													setRouting(task, entry.provider, e.target.value)
												}
												className={`h-7 w-full rounded-md border bg-background px-2 text-sm ${
													modelMissing
														? "border-yellow-500/60"
														: "border-input"
												}`}
											>
												{modelMissing && (
													<option value={entry.model}>
														{entry.model} (not detected)
													</option>
												)}
												{models.length === 0 && !modelMissing && (
													<option value="">
														{t("offlineMode:noModelsForProvider", "No models detected")}
													</option>
												)}
												{models.map((m) => (
													<option key={m} value={m}>
														{m}
													</option>
												))}
											</select>
										</td>
										<td>
											<Button
												size="sm"
												variant="ghost"
												onClick={() => removeRoutingRow(task)}
												aria-label={t("offlineMode:removeRow", "Remove row")}
											>
												<Trash2 className="w-3 h-3" />
											</Button>
										</td>
									</tr>
								);
							})}
						</tbody>
					</table>

					<div className="flex items-end gap-2 pt-2 border-t">
						<div className="flex-1">
							<Label className="text-xs">
								{t("offlineMode:addTask", "Add task type")}
							</Label>
							<Input
								value={newTask}
								onChange={(e) => setNewTask(e.target.value)}
								placeholder="e.g. summary"
								className="h-8"
							/>
						</div>
						<Button
							size="sm"
							variant="outline"
							onClick={() => {
								addRoutingRow(newTask.trim());
								setNewTask("");
							}}
							disabled={!newTask.trim()}
						>
							{t("offlineMode:add", "Add")}
						</Button>
						<Button
							size="sm"
							variant="outline"
							onClick={() => scan(projectPath, true)}
							disabled={scanning}
							title={
								catalog
									? t("offlineMode:catalogAge", "Cached {{age}} ago", {
											age: formatAge(catalog.ageSeconds),
										})
									: ""
							}
						>
							<ScanLine className="w-3 h-3 mr-1" />
							{scanning
								? t("offlineMode:scanning", "Scanning…")
								: t("offlineMode:rescan", "Rescan")}
						</Button>
						<Button
							size="sm"
							onClick={() => save(projectPath)}
							disabled={!dirty || saving}
						>
							<Save className="w-3 h-3 mr-1" />
							{saving
								? t("offlineMode:saving", "Saving…")
								: t("offlineMode:save", "Save policy")}
						</Button>
					</div>
					{catalog && (
						<p className="text-[11px] text-muted-foreground">
							{t(
								"offlineMode:catalogMeta",
								"{{total}} models detected across {{providers}} providers · cached {{age}} ago",
								{
									total: Object.values(catalog.providers).reduce(
										(s, m) => s + m.length,
										0,
									),
									providers: Object.keys(catalog.providers).length,
									age: formatAge(catalog.ageSeconds),
								},
							)}
						</p>
					)}
				</section>
			)}

			{report && (
				<section className="border rounded-md p-3 bg-card">
					<h4 className="text-sm font-semibold mb-2">
						{t("offlineMode:confidentialityReport", "Confidentiality report")}
					</h4>
					<p className="text-xs text-muted-foreground mb-2">
						{t("offlineMode:recentCalls", "Calls recorded")}: {report.total}
					</p>
					{report.total === 0 ? (
						<p className="text-sm text-muted-foreground">
							{t(
								"offlineMode:noCalls",
								"No routing decisions logged yet for this project.",
							)}
						</p>
					) : (
						<ul className="text-xs space-y-0.5">
							{Object.entries(report.mix).map(([provider, share]) => (
								<li key={provider} className="flex justify-between">
									<span>{provider}</span>
									<span className="font-mono">{(share * 100).toFixed(1)}%</span>
								</li>
							))}
						</ul>
					)}
				</section>
			)}
		</div>
	);
}
