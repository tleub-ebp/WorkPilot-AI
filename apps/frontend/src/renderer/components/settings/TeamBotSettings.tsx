import { Check, MessageSquare, Send, X } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useTeamBotStore } from "../../stores/team-bot-store";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";

const SELECT_CLASS =
	"h-9 rounded-md border border-border bg-card px-2 py-1 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring";

export function TeamBotSettings() {
	const { t } = useTranslation(["teamBot", "common"]);
	const { config, testing, lastResult, lastError, setConfig, sendTest } =
		useTeamBotStore();

	return (
		<div className="flex flex-col gap-3 p-4">
			<h3 className="text-base font-semibold flex items-center gap-2">
				<MessageSquare className="w-4 h-4" />
				{t("teamBot:title", "Slack / Teams notifications")}
			</h3>

			<div className="grid grid-cols-1 gap-2">
				<div>
					<Label className="text-xs">
						{t("teamBot:platform", "Platform")}
					</Label>
					<select
						className={SELECT_CLASS}
						value={config.kind}
						onChange={(e) =>
							setConfig({ kind: e.target.value as "slack" | "teams" })
						}
					>
						<option value="slack">Slack</option>
						<option value="teams">Microsoft Teams</option>
					</select>
				</div>

				<div>
					<Label className="text-xs">
						{t("teamBot:webhookUrl", "Webhook URL")}
					</Label>
					<Input
						value={config.webhook_url}
						onChange={(e) => setConfig({ webhook_url: e.target.value })}
						placeholder="https://hooks.slack.com/services/…"
						type="url"
					/>
				</div>

				<label className="flex items-center gap-2 text-sm">
					<input
						type="checkbox"
						checked={config.enabled ?? false}
						onChange={(e) => setConfig({ enabled: e.target.checked })}
					/>
					{t("teamBot:enabled", "Enable notifications")}
				</label>

				<div className="flex items-center gap-2">
					<Button
						size="sm"
						onClick={sendTest}
						disabled={testing || !config.webhook_url.trim()}
					>
						<Send className="w-3 h-3 mr-1" />
						{testing
							? t("teamBot:sending", "Sending…")
							: t("teamBot:sendTest", "Send test message")}
					</Button>
					{lastResult === "ok" && (
						<span className="text-xs text-green-500 flex items-center gap-1">
							<Check className="w-3 h-3" />
							{t("teamBot:ok", "Delivered")}
						</span>
					)}
					{lastResult === "error" && (
						<span className="text-xs text-destructive flex items-center gap-1">
							<X className="w-3 h-3" />
							{lastError ?? t("teamBot:error", "Delivery failed")}
						</span>
					)}
				</div>
			</div>

			<p className="text-xs text-muted-foreground">
				{t(
					"teamBot:help",
					"Notifications are sent when an agent finishes, a cost alert fires, a guardrail blocks an action, or a change has a high blast radius.",
				)}
			</p>
		</div>
	);
}
