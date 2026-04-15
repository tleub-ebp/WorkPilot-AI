import type React from "react";
import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import {
	setupOnboardingAgentListeners,
	useOnboardingAgentStore,
} from "../../stores/onboarding-agent-store";
import type { OnboardingGuide } from "../../../shared/types/onboarding";

interface OnboardingGuideViewProps {
	readonly projectPath?: string;
}

function GuideBody({
	guide,
	t,
}: {
	readonly guide: OnboardingGuide;
	readonly t: (key: string, options?: Record<string, unknown>) => string;
}): React.ReactElement {
	return (
		<div className="flex flex-col gap-4">
			<div>
				<p className="text-sm text-(--text-secondary)">
					{guide.projectName} ·{" "}
					{t("duration", { minutes: guide.totalEstimatedMinutes })}
				</p>
				<div className="flex flex-wrap gap-1 mt-1">
					{guide.techStack.map((tech) => (
						<span
							key={tech}
							className="px-2 py-0.5 rounded text-xs bg-blue-500/10 text-blue-400"
						>
							{tech}
						</span>
					))}
				</div>
			</div>

			<div className="space-y-3">
				{guide.steps.map((step, idx) => (
					<div
						key={`${step.section}-${step.title}`}
						className="px-4 py-3 rounded-lg border border-(--border-color)"
					>
						<div className="flex items-center justify-between mb-2">
							<div className="flex items-center gap-2">
								<span className="w-6 h-6 rounded-full bg-blue-500/20 text-blue-400 flex items-center justify-center text-xs font-bold">
									{idx + 1}
								</span>
								<p className="text-sm font-medium">{step.title}</p>
							</div>
							<span className="text-xs text-(--text-secondary)">
								{t("duration", { minutes: step.estimatedMinutes })}
							</span>
						</div>
						<p className="text-sm text-(--text-secondary) mb-2 whitespace-pre-wrap">
							{step.content}
						</p>
						{step.commands.length > 0 && (
							<div className="space-y-1">
								{step.commands.map((cmd) => (
									<pre
										key={`${cmd.slice(0, 20)}`}
										className="px-3 py-1.5 rounded bg-(--bg-secondary) text-xs font-mono text-green-400"
									>
										$ {cmd}
									</pre>
								))}
							</div>
						)}
					</div>
				))}
			</div>

			{guide.summary && (
				<p className="text-sm text-(--text-secondary) italic mt-2">
					{guide.summary}
				</p>
			)}
		</div>
	);
}

export function OnboardingGuideView({
	projectPath,
}: OnboardingGuideViewProps): React.ReactElement {
	const { t } = useTranslation("onboardingAgent");

	useEffect(() => {
		const cleanup = setupOnboardingAgentListeners();
		return cleanup;
	}, []);

	const phase = useOnboardingAgentStore((s) => s.phase);
	const status = useOnboardingAgentStore((s) => s.status);
	const guide = useOnboardingAgentStore((s) => s.guide);
	const error = useOnboardingAgentStore((s) => s.error);
	const startScan = useOnboardingAgentStore((s) => s.startScan);
	const cancelScan = useOnboardingAgentStore((s) => s.cancelScan);
	const reset = useOnboardingAgentStore((s) => s.reset);

	const handleRun = (): void => {
		if (!projectPath) return;
		void startScan(projectPath);
	};

	const isScanning = phase === "scanning";

	return (
		<div className="flex flex-col gap-4 p-6 bg-(--bg-primary) text-(--text-primary)">
			<div className="flex items-center justify-between">
				<h2 className="text-lg font-semibold">{t("title")}</h2>
				<div className="flex gap-2">
					{!isScanning && (
						<button
							type="button"
							onClick={handleRun}
							disabled={!projectPath}
							className="px-3 py-1.5 rounded-md bg-blue-500 hover:bg-blue-600 disabled:bg-gray-500 disabled:cursor-not-allowed text-white text-sm font-medium transition-colors"
						>
							{t("actions.runScan")}
						</button>
					)}
					{isScanning && (
						<button
							type="button"
							onClick={() => void cancelScan()}
							className="px-3 py-1.5 rounded-md bg-red-500 hover:bg-red-600 text-white text-sm font-medium transition-colors"
						>
							{t("actions.cancel")}
						</button>
					)}
					{phase === "complete" && (
						<button
							type="button"
							onClick={reset}
							className="px-3 py-1.5 rounded-md border border-(--border-color) hover:bg-(--bg-secondary) text-sm font-medium transition-colors"
						>
							{t("actions.reset")}
						</button>
					)}
				</div>
			</div>

			{!projectPath && (
				<p className="text-sm text-(--text-secondary)">
					{t("errors.noProject")}
				</p>
			)}

			{isScanning && (
				<p className="text-sm text-(--text-secondary)">
					{status || t("actions.scanning")}
				</p>
			)}

			{phase === "error" && error && (
				<p className="text-sm text-red-400">{t("errors.failed", { error })}</p>
			)}

			{phase === "complete" && !guide && (
				<p className="text-sm text-(--text-secondary)">{t("noData")}</p>
			)}

			{phase === "complete" && guide && <GuideBody guide={guide} t={t} />}
		</div>
	);
}
