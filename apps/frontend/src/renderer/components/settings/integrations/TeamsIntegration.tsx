import {
	AlertCircle,
	CheckCircle2,
	ExternalLink,
	Eye,
	EyeOff,
	MessageSquare,
} from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import type { ProjectEnvConfig } from "../../../../shared/types";
import { Button } from "../../ui/button";
import { Input } from "../../ui/input";
import { Label } from "../../ui/label";
import { Separator } from "../../ui/separator";
import { Switch } from "../../ui/switch";

interface TeamsIntegrationProps {
	readonly envConfig: ProjectEnvConfig | null;
	readonly updateEnvConfig: (updates: Partial<ProjectEnvConfig>) => void;
}

/**
 * Microsoft Teams notification settings.
 * Sends a message to a Teams channel when:
 * - A Kanban task is completed (moved to done)
 * - A PR is automatically created
 *
 * Uses Teams Incoming Webhooks — no OAuth required.
 */
export function TeamsIntegration({
	envConfig,
	updateEnvConfig,
}: TeamsIntegrationProps) {
	const { t } = useTranslation(["settings", "common"]);
	const [showWebhookUrl, setShowWebhookUrl] = useState(false);
	const [testStatus, setTestStatus] = useState<
		"idle" | "testing" | "success" | "error"
	>("idle");

	if (!envConfig) return null;

	const enabled = envConfig.teamsNotificationsEnabled ?? false;
	const webhookUrl = envConfig.teamsWebhookUrl ?? "";

	const handleTestWebhook = async () => {
		if (!webhookUrl) return;
		setTestStatus("testing");
		try {
			const result = await fetch(webhookUrl, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					type: "message",
					attachments: [
						{
							contentType: "application/vnd.microsoft.card.adaptive",
							content: {
								$schema: "http://adaptivecards.io/schemas/adaptive-card.json",
								type: "AdaptiveCard",
								version: "1.4",
								body: [
									{
										type: "TextBlock",
										text: t("settings:teams.testMessage"),
										weight: "bolder",
										size: "medium",
									},
									{
										type: "TextBlock",
										text: t("settings:teams.testMessageBody"),
										wrap: true,
									},
								],
							},
						},
					],
				}),
			});
			setTestStatus(result.ok ? "success" : "error");
		} catch {
			setTestStatus("error");
		}
		setTimeout(() => setTestStatus("idle"), 3000);
	};

	return (
		<div className="space-y-6">
			{/* Header */}
			<div className="flex items-center gap-3">
				<div className="p-2 rounded-lg bg-[#6264A7]/10">
					<MessageSquare className="h-5 w-5 text-[#6264A7]" />
				</div>
				<div>
					<h3 className="font-medium text-foreground">
						{t("settings:teams.title")}
					</h3>
					<p className="text-sm text-muted-foreground">
						{t("settings:teams.description")}
					</p>
				</div>
			</div>

			<Separator />

			{/* Enable toggle */}
			<div className="flex items-center justify-between">
				<div>
					<Label className="font-normal text-foreground">
						{t("settings:teams.enableNotifications")}
					</Label>
					<p className="text-xs text-muted-foreground mt-0.5">
						{t("settings:teams.enableNotificationsHint")}
					</p>
				</div>
				<Switch
					checked={enabled}
					onCheckedChange={(checked) =>
						updateEnvConfig({ teamsNotificationsEnabled: checked })
					}
				/>
			</div>

			{/* Webhook URL */}
			<div className="space-y-2">
				<Label htmlFor="teams-webhook">{t("settings:teams.webhookUrl")}</Label>
				<div className="relative">
					<Input
						id="teams-webhook"
						type={showWebhookUrl ? "text" : "password"}
						value={webhookUrl}
						onChange={(e) =>
							updateEnvConfig({ teamsWebhookUrl: e.target.value })
						}
						placeholder="https://xxx.webhook.office.com/webhookb2/..."
						className="pr-10 font-mono text-sm"
					/>
					<button
						type="button"
						onClick={() => setShowWebhookUrl(!showWebhookUrl)}
						className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
					>
						{showWebhookUrl ? (
							<EyeOff className="h-4 w-4" />
						) : (
							<Eye className="h-4 w-4" />
						)}
					</button>
				</div>
				<p className="text-xs text-muted-foreground">
					{t("settings:teams.webhookUrlHint")}
				</p>
			</div>

			{/* Actions */}
			<div className="flex items-center gap-3">
				<Button
					variant="outline"
					size="sm"
					disabled={!webhookUrl || testStatus === "testing"}
					onClick={handleTestWebhook}
				>
					{testStatus === "testing"
						? t("common:testing")
						: t("settings:teams.testWebhook")}
				</Button>

				{testStatus === "success" && (
					<span className="flex items-center gap-1 text-sm text-emerald-600">
						<CheckCircle2 className="h-4 w-4" />
						{t("settings:teams.testSuccess")}
					</span>
				)}
				{testStatus === "error" && (
					<span className="flex items-center gap-1 text-sm text-destructive">
						<AlertCircle className="h-4 w-4" />
						{t("settings:teams.testError")}
					</span>
				)}

				<a
					href="https://learn.microsoft.com/en-us/microsoftteams/platform/webhooks-and-connectors/how-to/add-incoming-webhook"
					target="_blank"
					rel="noreferrer"
					className="flex items-center gap-1 text-xs text-muted-foreground hover:text-primary transition-colors ml-auto"
				>
					<ExternalLink className="h-3 w-3" />
					{t("settings:teams.howToCreate")}
				</a>
			</div>

			<Separator />

			{/* What triggers a notification */}
			<div className="space-y-2">
				<Label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
					{t("settings:teams.triggers")}
				</Label>
				<ul className="space-y-1.5 text-sm text-muted-foreground">
					<li className="flex items-center gap-2">
						<CheckCircle2 className="h-3.5 w-3.5 text-emerald-500 shrink-0" />
						{t("settings:teams.triggerTaskDone")}
					</li>
					<li className="flex items-center gap-2">
						<CheckCircle2 className="h-3.5 w-3.5 text-emerald-500 shrink-0" />
						{t("settings:teams.triggerPrCreated")}
					</li>
				</ul>
			</div>
		</div>
	);
}
