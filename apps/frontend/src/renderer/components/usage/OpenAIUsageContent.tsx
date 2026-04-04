import type { UsageSnapshot } from "@shared/types";
import { formatUsageValue } from "@shared/utils/format-usage";
import { TrendingUp } from "lucide-react";
import { useTranslation } from "react-i18next";

interface OpenAIUsageContentProps {
	readonly usage: UsageSnapshot;
}

export function OpenAIUsageContent({ usage }: OpenAIUsageContentProps) {
	const { t } = useTranslation(["common"]);

	return (
		<div className="py-2 space-y-3">
			<div className="flex items-start gap-2.5 p-2.5 rounded-lg bg-primary/10 border border-primary/20">
				<TrendingUp className="h-4 w-4 text-primary shrink-0 mt-0.5" />
				<div className="space-y-1">
					<p className="text-xs font-medium text-primary">
						{t("common:usage.openaiCostLabel", "Coût OpenAI (mois en cours)")}
					</p>
					<p className="text-[10px] text-muted-foreground leading-relaxed">
						{t(
							"common:usage.openaiCostDescription",
							"Le coût affiché correspond à la consommation OpenAI du mois en cours (estimation).",
						)}
						<br />
						<a
							href="https://platform.openai.com/usage"
							target="_blank"
							rel="noopener noreferrer"
							className="underline text-primary"
						>
							{t("common:usage.openaiDashboard", "Voir le dashboard OpenAI")}
						</a>
					</p>
					<div className="mt-2 text-lg font-bold text-primary">
						${formatUsageValue(usage.weeklyUsageValue)}
					</div>
				</div>
			</div>
			{/* Section détaillée OpenAI Usage */}
			{usage.openaiUsageDetails && (
				<OpenAIUsageDetails details={usage.openaiUsageDetails} />
			)}
		</div>
	);
}

interface OpenAIUsageDetailsProps {
	// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
	readonly details: any;
}

function OpenAIUsageDetails({ details }: OpenAIUsageDetailsProps) {
	const { t } = useTranslation(["common"]);

	return (
		<div className="bg-muted/30 rounded p-2 text-[11px]">
			<div className="font-semibold mb-1">
				{t("common:usage.openaiDetailTitle")}
			</div>
			{details.completions && (
				<div className="mb-1">
					<div className="font-medium">
						{t("common:usage.completionsLabel")}
					</div>
					<ul>
						{details.completions.data && details.completions.data.length > 0 ? (
							// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
							details.completions.data.map((item: any, idx: number) => (
								<li key={`completions-${item.model || idx}`}>
									{item.model}: {item.n_input_tokens_total || 0} in,{" "}
									{item.n_output_tokens_total || 0} out
								</li>
							))
						) : (
							<li>{t("common:usage.noData")}</li>
						)}
					</ul>
				</div>
			)}
			{details.cost && (
				<div className="mb-1">
					<div className="font-medium">
						{t("common:usage.costByModelLabel")}
					</div>
					<ul>
						{details.cost.data && details.cost.data.length > 0 ? (
							// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
							details.cost.data.map((item: any, idx: number) => (
								<li key={`cost-${item.model || idx}`}>
									{item.model}: $
									{item.cost_usd
										? (Math.round(item.cost_usd * 100) / 100).toFixed(2)
										: "0.00"}
								</li>
							))
						) : (
							<li>{t("common:usage.noData")}</li>
						)}
					</ul>
				</div>
			)}
			{details.embeddings && (
				<div className="mb-1">
					<div className="font-medium">{t("common:usage.embeddingsLabel")}</div>
					<ul>
						{details.embeddings.data && details.embeddings.data.length > 0 ? (
							// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
							details.embeddings.data.map((item: any, idx: number) => (
								<li key={`embeddings-${item.model || idx}`}>
									{item.model}: {item.n_input_tokens_total || 0}
								</li>
							))
						) : (
							<li>{t("common:usage.noData")}</li>
						)}
					</ul>
				</div>
			)}
			{details.moderations && (
				<div className="mb-1">
					<div className="font-medium">
						{t("common:usage.moderationsLabel")}
					</div>
					<pre className="whitespace-pre-wrap text-[10px]">
						{JSON.stringify(details.moderations, null, 2)}
					</pre>
				</div>
			)}
		</div>
	);
}
