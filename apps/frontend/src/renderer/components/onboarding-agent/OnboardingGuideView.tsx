import type React from "react";
import { useTranslation } from "react-i18next";
import type { OnboardingGuide } from "../../../shared/types/onboarding";

interface OnboardingGuideViewProps {
	readonly guide?: OnboardingGuide;
}

export function OnboardingGuideView({
	guide,
}: OnboardingGuideViewProps): React.ReactElement {
	const { t } = useTranslation("onboardingAgent");

	if (!guide) {
		return (
			<div className="flex items-center justify-center h-full text-(--text-secondary)">
				<p>{t("noData")}</p>
			</div>
		);
	}
	return (
		<div className="flex flex-col gap-4 p-6 bg-(--bg-primary) text-(--text-primary)">
			<div>
				<h2 className="text-lg font-semibold">{t("title")}</h2>
				<p className="text-sm text-(--text-secondary)">
					{guide.projectName} · {t("duration", { minutes: guide.totalEstimatedMinutes })}
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
						key={`${step.section}-${idx}`}
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
						<p className="text-sm text-(--text-secondary) mb-2">
							{step.content}
						</p>
						{step.commands.length > 0 && (
							<div className="space-y-1">
								{step.commands.map((cmd) => (
									<pre
										key={cmd}
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
