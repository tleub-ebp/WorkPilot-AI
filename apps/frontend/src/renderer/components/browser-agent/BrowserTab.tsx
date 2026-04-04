import {
	ArrowLeft,
	ArrowRight,
	Camera,
	ExternalLink,
	Globe,
	Loader2,
	MonitorPlay,
	RotateCw,
	Wifi,
	WifiOff,
} from "lucide-react";
import { useCallback, useState } from "react";
import { useTranslation } from "react-i18next";
import { useBrowserAgentStore } from "@/stores/browser-agent-store";

interface BrowserTabProps {
	readonly projectPath: string;
}

export function BrowserTab({ projectPath }: BrowserTabProps) {
	const { t } = useTranslation(["browserAgent"]);
	const {
		currentUrl,
		setCurrentUrl,
		browserStatus,
		browserScreenshot,
		isCapturing,
		captureScreenshot,
	} = useBrowserAgentStore();

	const [screenshotName, setScreenshotName] = useState("");
	const [urlInput, setUrlInput] = useState(currentUrl);
	const [showCaptureBar, setShowCaptureBar] = useState(false);

	const normalizeUrl = useCallback((raw: string) => {
		const trimmed = raw.trim();
		if (!trimmed) return "";
		if (!trimmed.startsWith("http://") && !trimmed.startsWith("https://")) {
			return `https://${trimmed}`;
		}
		return trimmed;
	}, []);

	const handleNavigate = useCallback(() => {
		const url = normalizeUrl(urlInput);
		if (!url) return;
		setCurrentUrl(url);
		captureScreenshot(projectPath, "preview", url);
	}, [urlInput, normalizeUrl, setCurrentUrl, captureScreenshot, projectPath]);

	const handleRefresh = useCallback(() => {
		if (!currentUrl) return;
		captureScreenshot(projectPath, "preview", currentUrl);
	}, [currentUrl, captureScreenshot, projectPath]);

	const handleCapture = useCallback(() => {
		if (!currentUrl) return;
		const name = screenshotName.trim() || `capture_${Date.now()}`;
		captureScreenshot(projectPath, name, currentUrl);
		setScreenshotName("");
		setShowCaptureBar(false);
	}, [currentUrl, screenshotName, captureScreenshot, projectPath]);

	const handleKeyDown = (e: React.KeyboardEvent) => {
		if (e.key === "Enter") handleNavigate();
	};

	const handleOpenExternal = () => {
		if (currentUrl) {
			window.open(currentUrl, "_blank");
		}
	};

	const isNavigating =
		browserStatus === "launching" || browserStatus === "navigating";

	return (
		<div className="flex flex-col gap-0 h-full">
			{/* Browser toolbar */}
			<div className="flex items-center gap-1.5 p-2 rounded-t-lg bg-gradient-to-r from-[var(--bg-secondary)] to-[var(--bg-secondary)] border border-[var(--border-primary)] border-b-0">
				{/* Navigation buttons */}
				<ToolbarButton icon={ArrowLeft} disabled title="Back" />
				<ToolbarButton icon={ArrowRight} disabled title="Forward" />
				<ToolbarButton
					icon={RotateCw}
					onClick={handleRefresh}
					disabled={!currentUrl || isCapturing}
					title={t("browserAgent:browser.refresh")}
					spinning={isNavigating}
					color="blue"
				/>

				{/* URL bar */}
				<div className="flex-1 flex items-center gap-2 px-3 py-1.5 rounded-md bg-[var(--bg-primary)] border border-[var(--border-primary)] focus-within:border-blue-400/50 focus-within:shadow-[0_0_0_1px_rgba(96,165,250,0.15)] transition-all">
					{isNavigating ? (
						<Loader2 className="w-3.5 h-3.5 text-blue-400 animate-spin shrink-0" />
					) : (
						<Globe className="w-3.5 h-3.5 text-cyan-400/70 shrink-0" />
					)}
					<input
						type="text"
						value={urlInput}
						onChange={(e) => setUrlInput(e.target.value)}
						onKeyDown={handleKeyDown}
						placeholder={t("browserAgent:browser.urlPlaceholder")}
						className="flex-1 bg-transparent text-sm text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] focus:outline-none"
					/>
					{urlInput.trim() && (
						<button
							type="button"
							onClick={handleNavigate}
							disabled={isCapturing}
							className="px-2.5 py-0.5 rounded text-xs font-medium bg-blue-500 text-white hover:bg-blue-400 disabled:opacity-50 transition-colors"
						>
							{t("browserAgent:browser.navigate")}
						</button>
					)}
				</div>

				{/* Action buttons */}
				<ToolbarButton
					icon={Camera}
					onClick={() => setShowCaptureBar(!showCaptureBar)}
					disabled={!currentUrl || isCapturing}
					title={t("browserAgent:browser.captureScreenshot")}
					active={showCaptureBar}
					color="purple"
				/>
				<ToolbarButton
					icon={ExternalLink}
					onClick={handleOpenExternal}
					disabled={!currentUrl}
					title={t("browserAgent:browser.openExternal")}
					color="cyan"
				/>
			</div>

			{/* Screenshot capture bar (collapsible) */}
			{showCaptureBar && (
				<div className="flex items-center gap-2 px-3 py-2 bg-purple-500/8 border-x border-purple-500/20">
					<Camera className="w-3.5 h-3.5 text-purple-400 shrink-0" />
					<input
						type="text"
						value={screenshotName}
						onChange={(e) => setScreenshotName(e.target.value)}
						onKeyDown={(e) => {
							if (e.key === "Enter") handleCapture();
						}}
						placeholder={t("browserAgent:browser.screenshotNamePlaceholder")}
						className="flex-1 px-2.5 py-1 rounded bg-[var(--bg-primary)] border border-[var(--border-primary)] text-sm text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] focus:outline-none focus:border-purple-400/50"
					/>
					<button
						type="button"
						onClick={handleCapture}
						disabled={isCapturing}
						className="px-3 py-1 rounded text-xs font-medium bg-purple-500 text-white hover:bg-purple-400 disabled:opacity-50 transition-colors flex items-center gap-1.5"
					>
						{isCapturing && <Loader2 className="w-3 h-3 animate-spin" />}
						{isCapturing
							? t("browserAgent:browser.capturing")
							: t("browserAgent:browser.captureScreenshot")}
					</button>
				</div>
			)}

			{/* Browser viewport */}
			<div className="flex-1 rounded-b-lg border border-[var(--border-primary)] bg-[var(--bg-tertiary)] overflow-hidden flex items-center justify-center min-h-[400px] relative">
				{/* Loading overlay */}
				{isNavigating && browserScreenshot && (
					<div className="absolute inset-0 bg-black/40 flex items-center justify-center z-10 backdrop-blur-[2px]">
						<div className="flex flex-col items-center gap-2 px-5 py-4 rounded-xl bg-[var(--bg-secondary)]/95 backdrop-blur-sm border border-blue-500/20 shadow-lg shadow-blue-500/10">
							<Loader2 className="w-6 h-6 text-blue-400 animate-spin" />
							<p className="text-xs text-[var(--text-secondary)]">
								{browserStatus === "launching"
									? t("browserAgent:browser.launching")
									: t("browserAgent:browser.navigating")}
							</p>
						</div>
					</div>
				)}

				{/* Idle state */}
				{browserStatus === "idle" && !browserScreenshot && (
					<div className="flex flex-col items-center gap-5 text-center max-w-xs">
						<div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-blue-500/15 to-cyan-500/15 border border-blue-500/20 flex items-center justify-center shadow-lg shadow-blue-500/5">
							<MonitorPlay className="w-10 h-10 text-blue-400/70" />
						</div>
						<div>
							<p className="text-sm font-medium text-[var(--text-secondary)] mb-1.5">
								{t("browserAgent:browser.idleTitle")}
							</p>
							<p className="text-xs text-[var(--text-tertiary)] leading-relaxed">
								{t("browserAgent:browser.idleDescription")}
							</p>
						</div>
					</div>
				)}

				{/* Loading without existing screenshot */}
				{isNavigating && !browserScreenshot && (
					<div className="flex flex-col items-center gap-3">
						<div className="w-14 h-14 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center">
							<Loader2 className="w-7 h-7 text-blue-400 animate-spin" />
						</div>
						<p className="text-sm text-blue-300">
							{browserStatus === "launching"
								? t("browserAgent:browser.launching")
								: t("browserAgent:browser.navigating")}
						</p>
					</div>
				)}

				{/* Screenshot display */}
				{browserScreenshot && (
					<img
						src={browserScreenshot}
						alt="Browser screenshot"
						className="max-w-full max-h-full object-contain"
					/>
				)}

				{/* Error state */}
				{browserStatus === "error" && !browserScreenshot && (
					<div className="flex flex-col items-center gap-3 text-center max-w-xs">
						<div className="w-14 h-14 rounded-xl bg-red-500/10 border border-red-500/20 flex items-center justify-center">
							<WifiOff className="w-7 h-7 text-red-400" />
						</div>
						<p className="text-sm font-medium text-red-400">
							{t("browserAgent:errors.screenshotFailed")}
						</p>
						<p className="text-xs text-[var(--text-tertiary)]">
							{t("browserAgent:browser.errorHint")}
						</p>
					</div>
				)}
			</div>

			{/* Status bar */}
			{currentUrl && (
				<div className="flex items-center gap-2 px-3 py-1.5 text-[11px]">
					{browserStatus === "ready" ? (
						<>
							<Wifi className="w-3 h-3 text-emerald-400" />
							<span className="text-emerald-400/80 font-medium">
								{t("browserAgent:browser.ready")}
							</span>
							<span className="text-[var(--text-tertiary)]">·</span>
							<span className="text-[var(--text-tertiary)] truncate">
								{currentUrl}
							</span>
						</>
					) : browserStatus === "error" ? (
						<>
							<WifiOff className="w-3 h-3 text-red-400" />
							<span className="text-red-400/80 font-medium">
								{t("browserAgent:errors.screenshotFailed")}
							</span>
						</>
					) : null}
				</div>
			)}
		</div>
	);
}

// ── ToolbarButton ───────────────────────────────────────────

function ToolbarButton({
	icon: Icon,
	onClick,
	disabled = false,
	title,
	spinning = false,
	active = false,
	color = "default",
}: {
	readonly icon: typeof Globe;
	readonly onClick?: () => void;
	readonly disabled?: boolean;
	readonly title: string;
	readonly spinning?: boolean;
	readonly active?: boolean;
	readonly color?: "default" | "blue" | "purple" | "cyan";
}) {
	const activeColors: Record<string, string> = {
		default: "bg-blue-500/10 text-blue-400",
		blue: "bg-blue-500/10 text-blue-400",
		purple: "bg-purple-500/10 text-purple-400",
		cyan: "bg-cyan-500/10 text-cyan-400",
	};

	return (
		<button
			type="button"
			onClick={onClick}
			disabled={disabled}
			title={title}
			className={`p-1.5 rounded-md transition-colors ${
				active
					? activeColors[color]
					: "text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-hover)]"
			} disabled:opacity-30 disabled:cursor-not-allowed`}
		>
			<Icon className={`w-4 h-4 ${spinning ? "animate-spin" : ""}`} />
		</button>
	);
}
