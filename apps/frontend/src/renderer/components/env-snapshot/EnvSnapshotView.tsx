import {
	Camera,
	Container,
	Copy,
	Download,
	FileCode2,
	Package,
	Snowflake,
	Terminal,
} from "lucide-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import type { EnvSnapshotFormat } from "../../../preload/api/modules/env-snapshot-api";
import { useEnvSnapshotStore } from "../../stores/env-snapshot-store";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";

const FORMAT_OPTIONS: {
	value: EnvSnapshotFormat;
	icon: typeof Container;
	labelKey: string;
	descriptionKey: string;
}[] = [
	{
		value: "dockerfile",
		icon: Container,
		labelKey: "formats.docker.label",
		descriptionKey: "formats.docker.description",
	},
	{
		value: "nix",
		icon: Snowflake,
		labelKey: "formats.nix.label",
		descriptionKey: "formats.nix.description",
	},
	{
		value: "script",
		icon: Terminal,
		labelKey: "formats.script.label",
		descriptionKey: "formats.script.description",
	},
];

interface Props {
	readonly projectPath?: string;
}

export function EnvSnapshotView({ projectPath }: Props) {
	const { t } = useTranslation(["envSnapshot", "common"]);
	const {
		snapshots,
		selectedId,
		capturing,
		exporting,
		replayPayload,
		lastExportedPath,
		error,
		load,
		capture,
		select,
		replay,
		exportSnapshot,
	} = useEnvSnapshotStore();

	const [label, setLabel] = useState("");
	const [format, setFormat] = useState<EnvSnapshotFormat>("dockerfile");

	useEffect(() => {
		if (projectPath) void load(projectPath);
	}, [projectPath, load]);

	const selected = snapshots.find((s) => s.id === selectedId) ?? null;

	if (!projectPath) {
		return (
			<div className="flex items-center justify-center h-full text-muted-foreground">
				{t("envSnapshot:noProject", "Select a project to view snapshots.")}
			</div>
		);
	}

	const handleCapture = () => {
		void capture(projectPath, { label: label.trim() || undefined });
		setLabel("");
	};

	const handleReplay = () => {
		if (selected) void replay(projectPath, selected.id, format);
	};

	const handleExport = () => {
		if (selected) void exportSnapshot(projectPath, selected.id, format);
	};

	const handleCopy = () => {
		if (replayPayload) void navigator.clipboard.writeText(replayPayload.payload);
	};

	const activeFormat = FORMAT_OPTIONS.find((f) => f.value === format) ?? FORMAT_OPTIONS[0];

	return (
		<div className="flex flex-col gap-4 p-4">
			<div className="flex flex-wrap items-center justify-between gap-3">
				<div className="flex items-center gap-2">
					<Camera className="w-4 h-4" />
					<h3 className="text-base font-semibold">
						{t("envSnapshot:title", "Environment Snapshots")}
					</h3>
				</div>

				<div className="flex flex-col items-end gap-1">
					<Label className="text-xs text-muted-foreground">
						{t("envSnapshot:replayTargetLabel", "Replay target")}
					</Label>
					<div
						role="radiogroup"
						aria-label={t("envSnapshot:replayTargetLabel", "Replay target")}
						className="inline-flex rounded-md border border-border bg-background p-0.5"
					>
						{FORMAT_OPTIONS.map((opt) => {
							const Icon = opt.icon;
							const active = opt.value === format;
							return (
								<button
									key={opt.value}
									type="button"
									role="radio"
									aria-checked={active}
									onClick={() => setFormat(opt.value)}
									title={t(`envSnapshot:${opt.descriptionKey}`)}
									className={`flex items-center gap-1 px-3 py-1 text-xs rounded-sm transition-colors ${
										active
											? "bg-primary text-primary-foreground"
											: "text-muted-foreground hover:text-foreground"
									}`}
								>
									<Icon className="w-3 h-3" />
									{t(`envSnapshot:${opt.labelKey}`)}
								</button>
							);
						})}
					</div>
					<span className="text-[11px] text-muted-foreground">
						{t(`envSnapshot:${activeFormat.descriptionKey}`)}
					</span>
				</div>
			</div>

			<section className="border rounded-md p-3 bg-card flex items-end gap-2">
				<div className="flex-1">
					<Label className="text-xs">
						{t("envSnapshot:labelField", "Label (optional)")}
					</Label>
					<Input
						value={label}
						onChange={(e) => setLabel(e.target.value)}
						placeholder={t("envSnapshot:labelPlaceholder", "Pre-migration baseline")}
					/>
				</div>
				<Button onClick={handleCapture} disabled={capturing} size="sm">
					<Camera className="w-3 h-3 mr-1" />
					{capturing
						? t("envSnapshot:capturing", "Capturing…")
						: t("envSnapshot:capture", "Capture snapshot")}
				</Button>
			</section>

			{error && (
				<p className="text-sm text-destructive" role="alert">
					{error}
				</p>
			)}

			<div className="grid grid-cols-1 md:grid-cols-[280px_1fr] gap-3">
				<aside className="border rounded-md bg-card overflow-y-auto max-h-[60vh]">
					<header className="px-3 py-2 text-xs uppercase tracking-wide text-muted-foreground border-b">
						{t("envSnapshot:history", "History")} ({snapshots.length})
					</header>
					{snapshots.length === 0 ? (
						<p className="p-3 text-sm text-muted-foreground">
							{t("envSnapshot:empty", "No snapshots captured yet.")}
						</p>
					) : (
						<ul className="divide-y">
							{snapshots.map((s) => (
								<li key={s.id}>
									<button
										type="button"
										onClick={() => select(s.id)}
										className={`w-full text-left px-3 py-2 text-sm hover:bg-accent/60 ${selectedId === s.id ? "bg-accent/80" : ""}`}
									>
										<div className="font-medium">{s.label || s.id}</div>
										<div className="text-xs text-muted-foreground">
											{new Date(s.createdAt).toLocaleString()}
										</div>
										<div className="text-xs text-muted-foreground truncate">
											{s.git.branch} @ {s.git.commit.slice(0, 8) || "—"}
										</div>
									</button>
								</li>
							))}
						</ul>
					)}
				</aside>

				<section className="border rounded-md bg-card p-3 space-y-3 min-h-[200px]">
					{selected ? (
						<>
							<header className="flex items-start justify-between gap-2">
								<div>
									<h4 className="font-semibold text-sm flex items-center gap-2">
										<Package className="w-4 h-4" />
										{selected.label || selected.id}
									</h4>
									<p className="text-xs text-muted-foreground">
										{new Date(selected.createdAt).toLocaleString()} — {selected.id}
									</p>
								</div>
								<div className="flex gap-2">
									<Badge variant="outline">{selected.os.system}</Badge>
									{selected.git.dirty.length > 0 && (
										<Badge variant="destructive">
											{t("envSnapshot:dirty", "dirty")}
										</Badge>
									)}
								</div>
							</header>

							<div className="grid grid-cols-2 gap-2 text-xs">
								<div>
									<span className="text-muted-foreground">
										{t("envSnapshot:osLabel", "OS")}
									</span>
									<div>
										{selected.os.system} {selected.os.release}
									</div>
								</div>
								<div>
									<span className="text-muted-foreground">
										{t("envSnapshot:commit", "Commit")}
									</span>
									<div className="font-mono">
										{selected.git.commit.slice(0, 12) || "—"}
									</div>
								</div>
								<div>
									<span className="text-muted-foreground">Node</span>
									<div>{selected.tools.node ?? "—"}</div>
								</div>
								<div>
									<span className="text-muted-foreground">Python</span>
									<div>{selected.tools.python ?? "—"}</div>
								</div>
							</div>

							<div>
								<h5 className="text-xs uppercase tracking-wide text-muted-foreground mb-1">
									{t("envSnapshot:lockfiles", "Lockfiles")}
								</h5>
								{selected.lockfiles.length === 0 ? (
									<p className="text-xs text-muted-foreground">
										{t("envSnapshot:noLockfiles", "No lockfiles detected.")}
									</p>
								) : (
									<ul className="text-xs font-mono space-y-0.5">
										{selected.lockfiles.map((l) => (
											<li key={l.name} className="flex justify-between gap-2">
												<span>{l.name}</span>
												<span className="text-muted-foreground truncate">
													{l.sha256?.slice(0, 12) ?? "—"}
												</span>
											</li>
										))}
									</ul>
								)}
							</div>

							<div className="flex items-center gap-2 pt-2 border-t">
								<span className="text-xs text-muted-foreground mr-auto">
									{t("envSnapshot:targetHint", "Target:")}{" "}
									<span className="font-medium text-foreground">
										{t(`envSnapshot:${activeFormat.labelKey}`)}
									</span>
								</span>
								<Button size="sm" variant="outline" onClick={handleReplay}>
									<FileCode2 className="w-3 h-3 mr-1" />
									{t("envSnapshot:preview", "Preview")}
								</Button>
								<Button size="sm" onClick={handleExport} disabled={exporting}>
									<Download className="w-3 h-3 mr-1" />
									{exporting
										? t("envSnapshot:exporting", "Exporting…")
										: t("envSnapshot:export", "Export")}
								</Button>
							</div>

							{lastExportedPath && (
								<p className="text-xs text-green-600">
									{t("envSnapshot:exportedTo", "Exported to")}{" "}
									<span className="font-mono">{lastExportedPath}</span>
								</p>
							)}

							{replayPayload?.snapId === selected.id && (
								<div className="border rounded-md bg-background">
									<div className="flex items-center justify-between px-2 py-1 border-b">
										<span className="text-xs text-muted-foreground">
											{replayPayload.format}
										</span>
										<Button size="sm" variant="ghost" onClick={handleCopy}>
											<Copy className="w-3 h-3 mr-1" />
											{t("envSnapshot:copy", "Copy")}
										</Button>
									</div>
									<pre className="text-xs p-2 overflow-auto max-h-[220px] font-mono whitespace-pre-wrap">
										{replayPayload.payload}
									</pre>
								</div>
							)}
						</>
					) : (
						<p className="text-sm text-muted-foreground">
							{t("envSnapshot:selectPrompt", "Select a snapshot to see details.")}
						</p>
					)}
				</section>
			</div>
		</div>
	);
}
